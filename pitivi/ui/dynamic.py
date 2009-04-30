# PiTiVi , Non-linear video editor
#
#       ui/dynamic.py
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
A collection of helper classes and routines for dynamically creating user
interfaces
"""
import gobject
import gtk
import re
import sys
from gettext import gettext as _
from pitivi.ui.common import unpack_color, pack_color_32, pack_color_64

class DynamicWidget(object):

    """An interface which provides a uniform way to get, set, and observe
    widget properties"""

    def connectValueChanged(self, callback, *args):
        raise NotImplementedError

    def setWidgetValue(self, value):
        raise NotImplementedError

    def getWidgetValue(self, value):
        raise NotImplementedError

class DefaultWidget(gtk.Label):

    """When all hope fails...."""

    def __init__(self, *unused, **kw_unused):
        gtk.Label.__init__(self, _("Implement Me"))

    def connectValueChanged(self, callback, *args):
        pass

    def setWidgetValue(self, value):
        self.set_text(value)

    def getWidgetValue(self):
        return self.get_text()


class TextWidget(gtk.HBox):

    """A gtk.Entry which emits a value-changed signal only when its input is
    valid (matches the provided regex). If the input is invalid, a warning
    icon is displayed."""

    __gtype_name__ = 'TextWidget'
    __gsignals__ = {
        "value-changed" : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (),)
    }

    __INVALID__ = gtk.gdk.Color(0xFFFF, 0, 0)
    __NORMAL__ = gtk.gdk.Color(0, 0, 0)

    def __init__(self, matches = None):
        gtk.HBox.__init__(self)
        self.text = gtk.Entry()
        self.text.show()
        self.pack_start(self.text)
        self.matches = None
        self.last_valid = None
        self.valid = True
        self.image = gtk.Image()
        self.image.set_from_stock(gtk.STOCK_DIALOG_WARNING, 
            gtk.ICON_SIZE_BUTTON)
        self.pack_start(self.image)
        self.text.connect("changed", self._filter)
        if matches:
            self.matches = re.compile(matches)
            self._filter(None)

    def connectValueChanged(self, callback, *args):
        return self.connect("value-changed", callback, *args)

    def setWidgetValue(self, value):
        self.text.set_text(value)

    def getWidgetValue(self):
        if self.matches:
            return self.last_valid
        return self.text.get_text()

    def _filter(self, unused_widget):
        text = self.text.get_text()
        if self.matches:
            if self.matches.match(text):
                self.last_valid = text
                self.emit("value-changed")
                if not self.valid:
                    self.image.hide()
                self.valid = True
            else:
                if self.valid:
                    self.image.show()
                self.valid = False
        else:
            self.emit("value-changed")

class NumericWidget(gtk.HBox):

    """A gtk.HScale and a gtk.SpinButton which share an adjustment. The
    SpinButton is always displayed, while the HScale only appears if both
    lower and upper bounds are defined"""

    def __init__(self, upper = None, lower = None):
        gtk.HBox.__init__(self)

        self.adjustment = gtk.Adjustment()
        self.upper = upper
        self.lower = lower
        if (upper != None) and (lower != None):
            self.slider = gtk.HScale(self.adjustment)
            self.pack_end(self.slider)
            self.slider.show()

        if upper is None:
            upper = gobject.G_MAXDOUBLE
        if lower is None:
            lower = gobject.G_MINDOUBLE
        self.adjustment.props.lower = lower
        self.adjustment.props.upper = upper
        self.spinner = gtk.SpinButton(self.adjustment)
        self.pack_start(self.spinner, False, False)
        self.spinner.show()


    def connectValueChanged(self, callback, *args):
        self.adjustment.connect("value-changed", callback, *args)

    def getWidgetValue(self):
        return self.adjustment.get_value()

    def setWidgetValue(self, value):
        type_ = type(value)
        if type_ == int:
            minimum, maximum = (-sys.maxint, sys.maxint)
            step = 1.0
            page = 10.0
        elif type_ == float:
            minimum, maximum = (gobject.G_MINDOUBLE, gobject.G_MAXDOUBLE)
            step = 0.00001
            page = 0.01
        if self.lower is not None:
            minimum = self.lower
        if self.upper is not None:
            maximum = self.upper
        self.adjustment.set_all(value, minimum, maximum, step, page, 0)
        self.spinner.props.climb_rate = 0.01 * abs(min(maximum, 1000) -
            max(minimum, -1000))

class ToggleWidget(gtk.CheckButton):

    """A gtk.CheckButton which supports the DynamicWidget interface."""

    def __init__(self):
        gtk.CheckButton.__init__(self)

    def connectValueChanged(self, callback, *args):
        self.connect("toggled", callback, *args)

    def setWidgetValue(self, value):
        self.set_active(value)

    def getWidgetValue(self):
        return self.get_active()

class ChoiceWidget(gtk.VBox):

    """Abstractly, represents a choice between a list of named values. The
    association between value names and values is arbitrary. The current
    implementation uses a gtk.ComboBox."""

    def __init__(self, choices):
        gtk.VBox.__init__(self)
        self.choices = [choice[0] for choice in choices]
        self.values = [choice[1] for choice in choices]
        self.contents = gtk.combo_box_new_text()
        for choice, value in choices:
            self.contents.append_text(_(choice))
        self.pack_start(self.contents)
        self.contents.show()

    def connectValueChanged(self, callback, *args):
        return self.contents.connect("changed", callback, *args)

    def setWidgetValue(self, value):
        self.contents.set_active(self.values.index(value))

    def getWidgetValue(self):
        return self.values[self.contents.get_active()]

class PathWidget(gtk.FileChooserButton):

    """A gtk.FileChooserButton which supports the DynamicWidget interface."""

    __gtype_name__ = 'PathWidget'

    __gsignals__ = {
        "value-changed" : (gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            ()),
    }

    def __init__(self, action = gtk.FILE_CHOOSER_ACTION_OPEN):
        self.dialog = gtk.FileChooserDialog(
            action = action,
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_CLOSE,
            gtk.RESPONSE_CLOSE))
        self.dialog.set_default_response(gtk.RESPONSE_OK)
        gtk.FileChooserButton.__init__(self, self.dialog)
        self.set_title(_("Choose..."))
        self.dialog.connect("response", self._responseCb)
        self.uri = ""

    def connectValueChanged(self, callback, *args):
        return self.connect("value-changed", callback, *args)

    def setWidgetValue(self, value):
        self.set_uri(value)
        self.uri = value

    def getWidgetValue(self):
        return self.uri

    def _responseCb(self, unused_dialog, response):
        if response == gtk.RESPONSE_CLOSE:
            self.uri = self.get_uri()
            self.emit("value-changed")
            self.dialog.hide()

class ColorWidget(gtk.ColorButton):

    def __init__(self, value_type=str):
        gtk.ColorButton.__init__(self)
        self.value_type = value_type
        self.set_use_alpha(True)

    def connectValueChanged(self, callback, *args):
        self.connect("color-set", callback, *args)

    def setWidgetValue(self, value):
        type_ = type(value)
        alpha = 0xFFFF

        if type_ is str:
            color = gtk.gdk.Color(value)
        elif (type_ is int) or (type_ is long):
            red, green, blue, alpha = unpack_color(value)
            color = gtk.gdk.Color(red, green, blue)
        elif type_ is gtk.gdk.Color:
            color = value
        else:
            raise TypeError("%r is not something we can convert to a color" %
                value)
        self.set_color(color)
        self.set_alpha(alpha)

    def getWidgetValue(self):
        color = self.get_color()
        alpha = self.get_alpha()
        if self.value_type is int:
            return pack_color_32(color.red, color.green, color.blue, alpha)
        if self.value_type is long:
            return pack_color_64(color.red, color.green, color.blue, alpha)
        elif self.value_type is gtk.gdk.Color:
            return color
        return color.to_string()

class FontWidget(gtk.FontButton):

    def __init__(self):
        gtk.FontButton.__init__(self)
        self.set_use_font(True)

    def connectValueChanged(self, callback, *args):
        self.connect("font-set", callback, *args)

    def setWidgetValue(self, font_name):
        self.set_font_name(font_name)

    def getWidgetValue(self):
        return self.get_font_name()

if __name__ == '__main__':

    def valueChanged(unused_widget, widget, target):
        target.set_text(str(widget.getWidgetValue()))

    widgets = (
        (PathWidget, "file:///home/", ()),
        (TextWidget, "banana", ()),
        (TextWidget, "words only", ("^([a-zA-Z]+\s*)+$",)),
        (NumericWidget, 42, (100, 1)),
        (ToggleWidget, True, ()),
        (ChoiceWidget, "banana", ((
            ("banana", "banana"),
            ("apple", "apple"),
            ("pear", "pear")),)),
        (ColorWidget, 0x336699FF, (int,)),
        (FontWidget, "Sans 9", ()),
    )

    W = gtk.Window()
    v = gtk.VBox()
    t = gtk.Table()

    for y, (klass, default, args) in enumerate(widgets):
        w = klass(*args)
        l = gtk.Label(str(default))
        w.setWidgetValue(default)
        w.connectValueChanged(valueChanged, w, l)
        w.show()
        l.show()
        t.attach(w, 0, 1, y, y + 1)
        t.attach(l, 1, 2, y, y + 1)
    t.show()

    W.add(t)
    W.show()
    gtk.main()
