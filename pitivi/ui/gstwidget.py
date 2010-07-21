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
from pitivi.ui.glade import GladeWindow

from gettext import gettext as _
import pitivi.log.log as log
from pitivi.log.loggable import Loggable

def get_widget_propvalue(prop, widget):
    """ returns the value of the given propertywidget """
    # FIXME : implement the case for flags
    type_name = gobject.type_name(prop.value_type.fundamental)

    if (type_name == 'gchararray'):
        return widget.get_text()
    if (type_name in ['guint64', 'gint64', 'gint', 'gulong']):
        return widget.get_value_as_int()
    if (type_name in ['gfloat', 'gdouble']):
        return widget.get_value()
    if (type_name in ['gboolean']):
        return widget.get_active()
    if type_name in ['GEnum']:
        # we don't want to have typed enums wondering around,
        # we therefore convert it to it's numerical equivalent
        return int(widget.get_model()[widget.get_active()][1])
    return None

def make_property_widget(unused_element, prop, value=None):
    """ Creates a Widget for the given element property """
    # FIXME : implement the case for flags
    type_name = gobject.type_name(prop.value_type.fundamental)

    if value == None:
        value = prop.default_value
    if (type_name == 'gchararray'):
        widget = gtk.Entry()
        widget.set_text(str(value))
    elif (type_name in ['guint64', 'gint64', 'guint', 'gint', 'gfloat',
        'gdouble', 'gulong']):
        widget = gtk.SpinButton()
        if type_name == 'gint':
            minimum, maximum = (-(2**31), 2**31 - 1)
            widget.set_increments(1.0, 10.0)
        elif type_name == 'guint':
            minimum, maximum = (0, 2**32 - 1)
            widget.set_increments(1.0, 10.0)
        elif type_name == 'gint64':
            minimum, maximum = (-(2**63), 2**63 - 1)
            widget.set_increments(1.0, 10.0)
        elif type_name in ['gulong', 'guint64']:
            minimum, maximum = (0, 2**64 - 1)
            widget.set_increments(1.0, 10.0)
        elif type_name == 'gfloat' or type_name == 'gdouble':
            minimum, maximum = (float("-Infinity"), float("Infinity"))
            widget.set_increments(0.00001, 0.01)
            widget.set_digits(5)
        if hasattr(prop, "minimum"):
            minimum = prop.minimum
        if hasattr(prop, "maximum"):
            maximum = prop.maximum
        widget.set_range(minimum, maximum)
        widget.props.climb_rate = 0.01 * abs(min(maximum, 1000) -
            max(minimum, -1000))
        widget.set_value(float(value))
    elif (type_name == 'gboolean'):
        widget = gtk.CheckButton()
        if value:
            widget.set_active(True)
    elif (type_name == 'GEnum'):
        model = gtk.ListStore(gobject.TYPE_STRING, prop.value_type)
        widget = gtk.ComboBox(model)
        cell = gtk.CellRendererText()
        widget.pack_start(cell, True)
        widget.add_attribute(cell, 'text', 0)

        idx = 0
        for key, val in prop.enum_class.__enum_values__.iteritems():
            log.log("gstwidget", "adding %s / %s", val.value_name, val)
            model.append([val.value_name, val])
            if val == value or key == value:
                selected = idx
            idx = idx + 1
        widget.set_active(selected)
    else:
        widget = gtk.Label(type_name)
        widget.set_alignment(1.0, 0.5)

    if not prop.flags & gobject.PARAM_WRITABLE:
        widget.set_sensitive(False)
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
        self.buttons = []

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
                self.buttons.append(button)
            y += 1

        self.pack_start(table)
        self.show_all()

    def _getResetToDefaultValueButton(self, prop, widget):
        icon = gtk.Image()
        icon.set_from_stock('gtk-clear', gtk.ICON_SIZE_MENU)
        button = gtk.Button(label='')
        button.set_image(icon)
        button.set_tooltip_text(_("Reset to default value"))
        button.connect('clicked', self._defaultBtnClickedCb, prop.default_value, widget)
        return button

    def _defaultBtnClickedCb(self, button,  default_value, widget):
        self._set_prop(widget, default_value)

    def _set_prop(self, widget, value):
        def check_combobox_value(model, path, iter, widget_value):
            if model.get_value(iter, 0) == str(widget_value[1].value_name):
                widget_value[0].set_active_iter(iter)

        if type(widget) in [gtk.SpinButton]:
            widget.set_value(float(value))
        elif type(widget) in [gtk.Entry]:
            widget.set_text(str(value))
        elif type(widget) in [gtk.ComboBox]:
            model = widget.get_model()
            model.foreach(check_combobox_value, [widget, value])
        elif type(widget) in [gtk.CheckButton]:
            widget.set_active(bool(value))

    def getSettings(self, with_default=False):
        """
        returns the dictionnary of propertyname/propertyvalue
        """
        d = {}
        for prop, widget in self.properties.iteritems():
            if not prop.flags & gobject.PARAM_WRITABLE:
                continue
            value = get_widget_propvalue(prop, widget)
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
        self.desclabel = self.widgets["descriptionlabel"]
        self.authlabel = self.widgets["authorlabel"]
        self.properties = properties
        self._fillWindow()

    def _fillWindow(self):
        # set title and frame label
        self.window.set_title(_("Properties for %s") % self.factory.get_longname())
        self.widgets["infolabel"].set_markup("<b>" + self.factory.get_longname() + "</b>")
        self.desclabel.set_text(self.factory.get_description())
        self.authlabel.set_text('\n'.join(self.factory.get_author().split(",")))
        self.authlabel.set_justify(gtk.JUSTIFY_RIGHT)
        self.widgets["elementsettings"].setElement(self.element, self.properties)

    def getSettings(self):
        """ returns the property/value dictionnary of the selected settings """
        return self.widgets["elementsettings"].getSettings()
