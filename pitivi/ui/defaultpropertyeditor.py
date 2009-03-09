# PiTiVi , Non-linear video editor
#
#       ui/propertyeditor.py
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
Editor for aribtrary properties of timeline objects
"""

import gtk
from gettext import gettext as _
from gettext import ngettext

def get_widget_propvalue(widget):

    """ returns the value of the given propertywidget """
    # FIXME : implement the case for flags
    t = type(widget)

    if (t == gtk.TextEntry):
        return widget.get_text()
    if (t == gtk.SpinButton):
        return widget.get_value()
    if (t == gtk.CheckButton):
        return widget.get_active()
    if t == gtk.ComboBox:
        return widget.get_model()[widget.get_active()][1]
    return None

def make_property_widget(t, value=None):
    """ Creates a Widget for the given element property """
    if (t == str):
        widget = gtk.Entry()
        widget.set_text(str(value))
    elif (t in [int, float, long]):
        widget = gtk.SpinButton()
        if t == int:
            widget.set_range(-(2**31), 2**31 - 1)
        elif t == long:
            widget.set_range(float("-Infinity"),float("Infinity"))
        elif t == float:
            widget.set_range(0.0, 2**64 - 1)
            widget.set_digits(5)
        #widget.set_value(float(value))
    elif (t == 'gboolean'):
        widget = gtk.CheckButton()
        if value:
            widget.set_active(True)
    #elif (t == tuple):
    #    model = gtk.ListStore(gobject.TYPE_STRING, prop.value_type)
    #    widget = gtk.ComboBox(model)
    #    cell = gtk.CellRendererText()
    #    widget.pack_start(cell, True)
    #    widget.add_attribute(cell, 'text', 0)
    #    idx = 0
    #    for key, val in prop.enum_class.__enum_values__.iteritems():
    #        gst.log("adding %s / %s" % (val.value_name, val))
    #        model.append([val.value_name, val])
    #        if val == value:
    #            selected = idx
    #        idx = idx + 1
    #    widget.set_active(selected)
    else:
        widget = gtk.Label(repr(t))
        widget.set_alignment(1.0, 0.5)

    return widget


class DefaultPropertyEditor(gtk.Viewport):

    def __init__(self, *args, **kwargs):
        gtk.Viewport.__init__(self, *args, **kwargs)
        self._properties = {}
        self._createUi()

    def _createUi(self):
        self.text = gtk.Label()
        self.table = gtk.Table(rows=1, columns=2)
        self.table.attach(self.text, 0, 2, 0, 1)
        self.table.set_row_spacings(5)
        self.table.set_col_spacings(5)
        self.table.set_border_width(5)
        self.add(self.table)
        self.show_all()

    def setObjects(self, objs):
        self.text.set_text(ngettext("Properties For: %d object",
                                    "Properties For: %d objects",
                                    len(objs)) % len(objs))

        # we may have a non-homogeneous set of objects selected
        # so take the intersection of the properties they have in common
        assert len(objs) > 0
        i = iter(objs)
        properties = set(i.next().__editable_properties__)
        for obj in i:
            properties &= set(obj.__editable_properties__)
        self._addWidgets(properties)

    def _addWidgets(self, props):
        if not props:
            self.text.set_text(_("No properties..."))
        for widget in self._properties.values():
            self.table.remove(widget)
        self.table.resize(len(props) + 1, 2)
        y = 1
        for name, type, minval, contrlbl in sorted(props):
            label = gtk.Label(_(name))
            label.set_alignment(0.0, 0.5)
            widget = make_property_widget(type)
            self.table.attach(label, 0, 1, y, y+1, xoptions=gtk.FILL, yoptions=gtk.FILL)
            self.table.attach(widget, 1, 2, y, y+1, yoptions=gtk.FILL)
            self._properties[name] = widget
        self.show_all()
