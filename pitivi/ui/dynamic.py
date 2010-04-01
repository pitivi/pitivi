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
import gst
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

    def __init__(self, matches = None, choices = None):
        gtk.HBox.__init__(self)
        self.set_border_width(0)
        self.set_spacing(0)
        if choices:
            self.combo = gtk.combo_box_entry_new_text()
            self.text = self.combo.child
            self.combo.show()
            self.pack_start(self.combo)
            for choice in choices:
                self.combo.append_text(choice)
        else:
            self.text = gtk.Entry()
            self.text.show()
            self.pack_start(self.text)
        self.matches = None
        self.last_valid = None
        self.valid = False
        self.text.connect("changed", self._textChanged)
        if matches:
            if type(matches) is str:
                self.matches = re.compile(matches)
            else:
                self.matches = matches
            self._textChanged(None)

    def connectValueChanged(self, callback, *args):
        return self.connect("value-changed", callback, *args)

    def setWidgetValue(self, value):
        self.text.set_text(value)

    def getWidgetValue(self):
        if self.matches:
            return self.last_valid
        return self.text.get_text()

    def _textChanged(self, unused_widget):
        text = self.text.get_text()
        if self.matches:
            if self._filter(text):
                self.last_valid = text
                self.emit("value-changed")
                if not self.valid:
                    self.text.set_icon_from_stock(1, None)
                self.valid = True
            else:
                if self.valid:
                    self.text.set_icon_from_stock(1, gtk.STOCK_DIALOG_WARNING)
                self.valid = False
        else:
            self.emit("value-changed")

    def _filter(self, text):
        match = self.matches.match(text)
        if match is not None:
            return True
        return False

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
            self.slider.props.draw_value = False

        if upper is None:
            upper = gobject.G_MAXDOUBLE
        if lower is None:
            lower = gobject.G_MINDOUBLE
        range = upper - lower
        self.adjustment.props.lower = lower
        self.adjustment.props.upper = upper
        self.spinner = gtk.SpinButton(self.adjustment)
        self.pack_start(self.spinner)
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
            self.spinner.props.digits = 2
        if self.lower is not None:
            minimum = self.lower
        if self.upper is not None:
            maximum = self.upper
        self.adjustment.set_all(value, minimum, maximum, step, page, 0)
        self.spinner.props.climb_rate = 0.01 * abs(min(maximum, 1000) -
            max(minimum, -1000))

class FractionWidget(TextWidget):

    """A gtk.ComboBoxEntry """

    fraction_regex = re.compile(
        "^([0-9]*(\.[0-9]+)?)(([:/][0-9]*(\.[0-9]+)?)|M)?$")
    __gtype_name__ = 'FractionWidget'

    def __init__(self, range=None, presets=None):
        if range:
            flow = float(range.low)
            fhigh = float(range.high)
        else:
            flow = float("-Infinity")
            fhigh = float("Infinity")
        choices = []
        if presets:
            for preset in presets:
                if type(preset) is str:
                    strval = preset
                    preset = self._parseText(preset)
                else:
                    strval = "%g:%g" % (preset.num, preset.denom)
                fpreset = float(preset)
                if flow <= fpreset and fpreset <= fhigh:
                    choices.append(strval)
        self.low = flow
        self.high = fhigh
        TextWidget.__init__(self, self.fraction_regex, choices)

    def _filter(self, text):
        if TextWidget._filter(self, text):
            value = self._parseText(text)
            if self.low <= float(value) and float(value) <= self.high:
                return True
        return False

    def setWidgetValue(self, value):
        if type(value) is str:
            value = self._parseText(value)
        elif not hasattr(value, "denom"):
            value = gst.Fraction(value)
        if (value.denom / 1001) == 1:
            text = "%gM" % (value.num / 1000)
        else:
            text = "%g:%g" % (value.num, value.denom)

        self.text.set_text(text)

    def getWidgetValue(self):
        if self.last_valid:
            return self._parseText(self.last_valid)
        return gst.Fraction(1, 1)

    def _parseText(self, text):
        match = self.fraction_regex.match(text)
        groups = match.groups()
        num = 1.0
        denom = 1.0
        if groups[0]:
            num = float(groups[0])
        if groups[2]:
            if groups[2] == "M":
                num = num * 1000
                denom = 1001
            elif groups[2][1:]:
                denom = float(groups[2][1:])
        return gst.Fraction(num, denom)

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

class ChoiceWidget(gtk.HBox):

    """Abstractly, represents a choice between a list of named values. The
    association between value names and values is arbitrary. The current
    implementation uses a gtk.ComboBox."""

    def __init__(self, choices):
        gtk.HBox.__init__(self)
        self.choices = [choice[0] for choice in choices]
        self.values = [choice[1] for choice in choices]
        self.contents = gtk.combo_box_new_text()
        for choice, value in choices:
            self.contents.append_text(_(choice))
        if len(choices) <= 1:
            self.contents.set_sensitive(False)
        self.pack_start(self.contents)
        self.contents.show()

    def connectValueChanged(self, callback, *args):
        return self.contents.connect("changed", callback, *args)

    def setWidgetValue(self, value):
        self.contents.set_active(self.values.index(value))

    def getWidgetValue(self):
        return self.values[self.contents.get_active()]

class PresetChoiceWidget(gtk.HBox):

    """A popup which manages preset settings on a group of widgets supporting
    the dynamic interface"""

    class WidgetMap(object):

        """A helper class for mapping data from a preset to a set of
        widgets"""

        def __init__(self):
            raise NotImplementedError

        def getWidgets(self):
            raise NotImplementedError

        def map(self, preset):
            raise NotImplementedError

    class SeqWidgetMap(WidgetMap):

        """Maps widgets positionally to a sequence of values. None can be used
        if the given position should not map to a widget"""

        def __init__(self, *widgets):
            self.widgets = widgets

        def getWidgets(self):
            return (w for w in self.widgets if w)

        def map(self, preset):
            for w, p in zip(self.widgets, preset):
                if w:
                    w.setWidgetValue(p)

        def unmap(self):
            return [w.getWidgetValue() for w in self.widgets if w]

    def __init__(self, presets):
        gtk.HBox.__init__(self)
        self._block_update = False
        self._widget_map = None

        self.presets = presets
        presets.connect("preset-added", self._presetAdded)
        presets.connect("preset-removed", self._presetRemoved)

        self.combo = gtk.combo_box_new_text()
        self.combo.set_row_separator_func(self._sep_func)
        for preset in presets:
            self.combo.append_text(preset[0])
        self.combo.append_text("-")
        self.combo.append_text(_("Custom"))
        self.pack_start(self.combo)
        self._custom_row = len(presets) + 1

        save_button = gtk.Button(stock=gtk.STOCK_SAVE)
        self._save_button = save_button
        self.pack_start(save_button, False, False)
        save_button.connect("clicked", self._savePreset)
        self.show_all()

    def _sep_func(self, model, iter):
        return model[iter][0] == "-"

    def _presetAdded(self, presetlist, preset):
        row = self._custom_row - 1
        self._custom_row += 1
        self.combo.insert_text(row, preset[0])
        self.combo.set_active(row)

    def _presetRemoved(self, presetlist, preset, index):
        self.combo.remove_text(index)
        self._custom_row -= 1

    def _savePreset(self, unused_button):
        d = gtk.Dialog(_("Save Preset"), None, gtk.DIALOG_MODAL,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE,
                gtk.RESPONSE_OK))
        input = gtk.Entry()
        ca = d.get_content_area()
        ca.pack_start(input)
        input.show()
        response = d.run()

        if response == gtk.RESPONSE_OK:
            name = input.get_text()
            values = self._widget_map.unmap()
            self.presets.addPreset(name, values)
        d.destroy()

    def setWidgetMap(self, map):
        self._widget_map = map
        for widget in self._widget_map.getWidgets():
            widget.connectValueChanged(self._slaveWidgetValueChanged)
        self.combo.connect("changed", self._comboChanged)

    def mapWidgetsToSeq(self, *args):
        self.setWidgetMap(self.SeqWidgetMap(*args))

    def _slaveWidgetValueChanged(self, unused_widget):
        # gtk isn't very friendly to this sort of thing
        if not self._block_update:
            self.combo.set_active(self._custom_row)

    def _comboChanged(self, combo):
        active = combo.get_active()
        if active > len(self.presets):
            self._save_button.set_sensitive(True)
            return
        preset = self.presets[active][1]

        self._save_button.set_sensitive(False)

        self._block_update = True
        self._widget_map.map(preset)
        self._block_update = False

    def connectValueChanged(self, callback, *args):
        self.combo.connect("changed", callback, *args)

    def setWidgetValue(self, preset_index):
        self.combo.set_active(preset_index)


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

class ResolutionWidget(gtk.HBox):

    def __init__ (self):
        gtk.HBox.__init__(self)
        self.props.spacing = 6

        self.dwidth = 0
        self.dheight = 0
        self.dwidthWidget = NumericWidget(lower=0)
        self.dheightWidget = NumericWidget(lower=0)
        self.pack_start(self.dwidthWidget)
        self.pack_start(gtk.Label("x"))
        self.pack_start(self.dheightWidget)
        self.setWidgetValue((320, 240))
        self.show_all()

    def connectValueChanged(self, callback, *args):
        self.dwidthWidget.connectValueChanged(callback, *args)
        self.dheightWidget.connectValueChanged(callback, *args)

    def setWidgetValue(self, value):
        width, height = value
        dar = gst.Fraction(width, height)

        self.dwidthWidget.setWidgetValue(width)
        self.dheightWidget.setWidgetValue(height)

    def getWidgetValue(self):
        return self.dwidthWidget.getWidgetValue(),\
            self.dheightWidget.getWidgetValue()

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
        (FractionWidget, gst.Fraction(25000, 10001), 
            (gst.FractionRange(gst.Fraction(1, 1), 
                gst.Fraction(30000, 1001)),)),
        (FractionWidget, gst.Fraction(25000, 10001), 
            (gst.FractionRange(gst.Fraction(1, 1), 
                gst.Fraction(30000, 1001)),
                (gst.Fraction(25,1), gst.Fraction(30,1))))
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
