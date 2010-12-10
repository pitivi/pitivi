# PiTiVi , Non-linear video editor
#
#       ui/gstwidget.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Widget for gstreamer element properties viewing/setting
"""

import gobject
import gtk
import gst
from pitivi.ui.glade import GladeWindow

from gettext import gettext as _
from pitivi.log.loggable import Loggable
import pitivi.ui.dynamic as dynamic

def make_property_widget(unused_element, prop, value=None):
    """ Creates a Widget for the given element property """
    # FIXME : implement the case for flags
    type_name = gobject.type_name(prop.value_type.fundamental)

    if value == None:
        value = prop.default_value
    if (type_name == 'gchararray'):
        widget = dynamic.TextWidget()
    elif (type_name in ['guint64', 'gint64', 'guint', 'gint', 'gfloat',
        'gulong', 'gdouble']):

        maximum , minimum = None, None
        if hasattr(prop, "minimum"):
            minimum = prop.minimum
        if hasattr(prop, "maximum"):
            maximum = prop.maximum
        widget = dynamic.NumericWidget(default=prop.default_value,
                                       upper=maximum, lower=minimum)
    elif (type_name == 'gboolean'):
        widget = dynamic.ToggleWidget(default=prop.default_value)
    elif (type_name == 'GEnum'):
        idx = 0
        choices = []
        for key, val in prop.enum_class.__enum_values__.iteritems():
            choices.append([val.value_name, int(val)])
        widget = dynamic.ChoiceWidget(choices, default=prop.default_value)
    elif type_name == 'GstFraction':
        widget = dynamic.FractionWidget(None, presets=["0:1"], default=prop.default_value)
    else:
        widget = dynamic.DefaultWidget(type_name)

    if value is not None and type_name != 'GFlags':
        widget.setWidgetValue(value)

    return widget

class GstElementSettingsWidget(gtk.VBox, Loggable):
    """
    Widget to view/modify properties of a gst.Element
    """

    def __init__(self):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)
        self.element = None
        self.ignore = None
        self.properties = None
        self.buttons = {}

    def setElement(self, element, properties={}, ignore=['name'],
                   default_btn = False, use_element_props=False):
        """ Set given element on Widget, with optional properties """
        self.info("element:%s, use properties:%s", element, properties)
        self.element = element
        self.ignore = ignore
        self.properties = {}
        self._addWidgets(properties, default_btn, use_element_props)

    def _addWidgets(self, properties, default_btn, use_element_props):
        props = [prop for prop in gobject.list_properties(self.element) if not prop.name in self.ignore]
        if not props:
            table = gtk.Table(rows=1, columns=1)
            widget = gtk.Label(_("No properties..."))
            table.attach(widget, 0, 1, 0, 1, yoptions=gtk.FILL)
            self.pack_start(table)
            self.show_all()
            return

        if default_btn:
            table = gtk.Table(rows=len(props), columns=3)
        else:
            table = gtk.Table(rows=len(props), columns=2)

        table.set_row_spacings(5)
        table.set_col_spacings(5)
        table.set_border_width(5)
        y = 0
        for prop in props:
            if not prop.flags & gobject.PARAM_WRITABLE\
              or not prop.flags & gobject.PARAM_READABLE:
                continue

            label = gtk.Label(prop.nick+":")
            label.set_alignment(0.0, 0.5)
            table.attach(label, 0, 1, y, y+1, xoptions=gtk.FILL, yoptions=gtk.FILL)
            if use_element_props:
                prop_value  = self.element.get_property(prop.name)
            else:
                prop_value = properties.get(prop.name)
            widget = make_property_widget(self.element, prop, prop_value)

            if hasattr(prop, 'description'): #TODO: check that
                widget.set_tooltip_text(prop.description)

            table.attach(widget, 1, 2, y, y+1, yoptions=gtk.FILL)
            self.properties[prop] = widget
            if default_btn:
                button = self._getResetToDefaultValueButton(prop, widget)
                table.attach(button, 2, 3, y, y+1, xoptions=gtk.FILL, yoptions=gtk.FILL)
                self.buttons[button] = widget
            self.element.connect('notify::' + prop.name,
                                 self._propertyChangedCb,
                                 widget)

            y += 1

        self.pack_start(table)
        self.show_all()

    def _propertyChangedCb(self, element, pspec, widget):
        widget.setWidgetValue(self.element.get_property(pspec.name))

    def _getResetToDefaultValueButton(self, prop, widget):
        icon = gtk.Image()
        icon.set_from_stock('gtk-clear', gtk.ICON_SIZE_MENU)
        button = gtk.Button(label='')
        button.set_image(icon)
        button.set_tooltip_text(_("Reset to default value"))
        button.connect('clicked', self._defaultBtnClickedCb, widget)
        return button

    def _defaultBtnClickedCb(self, button, widget):
        widget.setWidgetToDefault()

    def getSettings(self, with_default=False):
        """
        returns the dictionnary of propertyname/propertyvalue
        """
        d = {}
        for prop, widget in self.properties.iteritems():
            if not prop.flags & gobject.PARAM_WRITABLE\
              or isinstance(widget, dynamic.DefaultWidget):
                continue
            value = widget.getWidgetValue()
            if value != None and (value != prop.default_value or with_default):
                d[prop.name] = value
        return d



class GstElementSettingsDialog(GladeWindow, Loggable):
    """
    Dialog window for viewing/modifying properties of a gst.Element
    """
    glade_file = "elementsettingsdialog.glade"

    def __init__(self, elementfactory, properties={}):
        GladeWindow.__init__(self)
        Loggable.__init__(self)
        self.debug("factory:%s, properties:%s", elementfactory, properties)
        self.factory = elementfactory
        self.element = self.factory.create("elementsettings")
        if not self.element:
            self.warning("Couldn't create element from factory %s", self.factory)
        self.properties = properties
        self._fillWindow()

    def _fillWindow(self):
        # set title and frame label
        self.window.set_title(_("Properties for %s") % self.factory.get_longname())
        self.infolabel.set_markup("<b>" + self.factory.get_longname() + "</b>")
        self.elementsettings.setElement(self.element, self.properties)
        self.elementsettings.set_border_width(12)

    def getSettings(self):
        """ returns the property/value dictionnary of the selected settings """
        return self.widgets["elementsettings"].getSettings()
