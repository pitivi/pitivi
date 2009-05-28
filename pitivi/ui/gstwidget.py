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
    if (type_name in ['gfloat']):
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

    def setElement(self, element, properties={}, ignore=['name']):
        """ Set given element on Widget, with optional properties """
        self.info("element:%s, properties:%s", element, properties)
        self.element = element
        self.ignore = ignore
        self.properties = {} #key:name, value:widget
        self._addWidgets(properties)

    def _addWidgets(self, properties):
        props = [x for x in gobject.list_properties(self.element) if not x.name in self.ignore]
        if not props:
            self.pack_start(gtk.Label(_("No properties...")))
            self.show_all()
            return
        table = gtk.Table(rows=len(props), columns=2)
        table.set_row_spacings(5)
        table.set_col_spacings(5)
        table.set_border_width(5)
        y = 0
        for prop in props:
            label = gtk.Label(prop.nick)
            label.set_alignment(0.0, 0.5)
            widget = make_property_widget(self.element, prop, properties.get(prop.name))
            table.attach(label, 0, 1, y, y+1, xoptions=gtk.FILL, yoptions=gtk.FILL)
            table.attach(widget, 1, 2, y, y+1, yoptions=gtk.FILL)
            self.properties[prop] = widget
            y += 1
        self.pack_start(table)
        self.show_all()

    def getSettings(self):
        """
        returns the dictionnary of propertyname/propertyvalue
        """
        d = {}
        for prop, widget in self.properties.iteritems():
            if not prop.flags & gobject.PARAM_WRITABLE:
                continue
            value = get_widget_propvalue(prop, widget)
            if value != None and value != prop.default_value:
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
