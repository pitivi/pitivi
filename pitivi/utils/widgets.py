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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
A collection of helper classes and routines for:
    * dynamically creating user interfaces
    * Creating UI from GstElement-s
"""

import imp
import os
import re
import sys

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import GES
from gi.repository import Pango
from gi.repository import GLib
from gi.repository import GObject

from gettext import gettext as _

from pitivi.utils.loggable import Loggable
from pitivi.configure import get_ui_dir
from pitivi.utils.ui import unpack_color, pack_color_32, pack_color_64, \
    time_to_string, SPACING
from pitivi.utils.timeline import Zoomable

ZOOM_FIT = _("Zoom Fit")


class DynamicWidget(object):

    """An interface which provides a uniform way to get, set, and observe
    widget properties"""
    def __init__(self, default):
        self.default = default

    def connectValueChanged(self, callback, *args):
        raise NotImplementedError

    def setWidgetValue(self, value):
        raise NotImplementedError

    def getWidgetValue(self, value):
        raise NotImplementedError

    def getWidgetDefault(self):
        return self.default

    def setWidgetDefault(self, value):
        self.default = value

    def setWidgetToDefault(self):
        if self.default is not None:
            self.setWidgetValue(self.default)


class DefaultWidget(Gtk.Label, DynamicWidget):

    """When all hope fails...."""

    def __init__(self, default=None, *unused, **kw_unused):
        Gtk.Label.__init__(self, _("Implement Me"))
        DynamicWidget.__init__(self, default)

    def connectValueChanged(self, callback, *args):
        pass

    def setWidgetValue(self, value):
        self.set_text(str(value))

    def getWidgetValue(self):
        return self.get_text()


class TextWidget(Gtk.HBox, DynamicWidget):
    """
    A Gtk.Entry which emits a "value-changed" signal only when its input is
    valid (matches the provided regex). If the input is invalid, a warning
    icon is displayed.

    You can also connect to the "activate" signal if you don't want to watch
    for live changes, but it will only be emitted if the input is valid when
    the user presses Enter.
    """

    __gtype_name__ = 'TextWidget'
    __gsignals__ = {
        "value-changed": (GObject.SignalFlags.RUN_LAST, None, (),),
        "activate": (GObject.SignalFlags.RUN_LAST, None, (),)
    }

    __INVALID__ = Gdk.Color(0xFFFF, 0, 0)
    __NORMAL__ = Gdk.Color(0, 0, 0)

    def __init__(self, matches=None, choices=None, default=None, text_widget=None):
        if not default:
            # In the case of text widgets, a blank default is an empty string
            default = ""

        Gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)

        self.set_border_width(0)
        self.set_spacing(0)
        if text_widget is None:
            if choices:
                self.combo = Gtk.combo_box_entry_new_text()
                self.text = self.combo.get_child()
                self.combo.show()
                self.pack_start(self.combo, True, True, 0)
                for choice in choices:
                    self.combo.append_text(choice)
            else:
                self.text = Gtk.Entry()
                self.text.show()
                self.pack_start(self.text, True, True, 0)
        else:
            self.text = text_widget
        self.matches = None
        self.last_valid = None
        self.valid = False
        self.send_signal = True
        self.text.connect("changed", self._textChanged)
        self.text.connect("activate", self._activateCb)
        if matches:
            if type(matches) is str:
                self.matches = re.compile(matches)
            else:
                self.matches = matches
            self._textChanged(None)

    def connectValueChanged(self, callback, *args):
        return self.connect("value-changed", callback, *args)

    def setWidgetValue(self, value, send_signal=True):
        self.send_signal = send_signal
        self.text.set_text(value)

    def getWidgetValue(self):
        if self.matches:
            return self.last_valid
        return self.text.get_text()

    def addChoices(self, choices):
        for choice in choices:
            self.combo.append_text(choice)

    def _textChanged(self, unused_widget):
        text = self.text.get_text()
        if self.matches:
            if self._filter(text):
                self.last_valid = text
                if self.send_signal:
                    self.emit("value-changed")
                if not self.valid:
                    self.text.set_icon_from_stock(1, None)
                self.valid = True
            else:
                if self.valid:
                    self.text.set_icon_from_stock(1, Gtk.STOCK_DIALOG_WARNING)
                self.valid = False
        elif self.send_signal:
            self.emit("value-changed")

        self.send_signal = True

    def _activateCb(self, unused_widget):
        """
        Similar to _textChanged, to account for the case where we connect to
        the "activate" signal instead of "text-changed".

        We don't need to set the icons or anything like that, as _textChanged
        does it already.
        """
        if self.matches and self.send_signal:
            self.emit("activate")

    def _filter(self, text):
        match = self.matches.match(text)
        if match is not None:
            return True
        return False

    def set_width_chars(self, width):
        """Allows setting the width of the text entry widget for compactness."""
        self.text.set_width_chars(width)


class NumericWidget(Gtk.HBox, DynamicWidget):

    """An horizontal Gtk.Scale and a Gtk.SpinButton which share an adjustment.
    The SpinButton is always displayed, while the Scale only appears if both
    lower and upper bounds are defined"""

    def __init__(self, upper=None, lower=None, default=None,
                 adjustment=None):
        Gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)

        self.spacing = SPACING
        self._type = None
        if adjustment is None:
            self.upper = upper
            self.lower = lower
            self.adjustment = Gtk.Adjustment()
            if (lower is not None and upper is not None) and (lower > -5000 and upper < 5000):
                self.slider = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, self.adjustment)
                self.pack_start(self.slider, fill=True, expand=True, padding=0)
                self.slider.show()
                self.slider.props.draw_value = False

            if upper is None:
                upper = GObject.G_MAXDOUBLE
            if lower is None:
                lower = GObject.G_MINDOUBLE
            range = upper - lower
            self.adjustment.props.lower = lower
            self.adjustment.props.upper = upper
            self.spinner = Gtk.SpinButton(adjustment=self.adjustment)
            self.pack_end(self.spinner, fill=True, expand=not hasattr(self, 'slider'), padding=0)
            self.spinner.show()
        else:
            self.adjustment = adjustment
            self.upper = adjustment.get_upper()
            self.lower = adjustment.get_lower()
            self.slider = None
            self.spinner = None

    def connectValueChanged(self, callback, *args):
        self.adjustment.connect("value-changed", callback, * args)

    def getWidgetValue(self):
        if self._type:
            return self._type(self.adjustment.get_value())

        return self.adjustment.get_value()

    def setWidgetValue(self, value):
        # With introspection, we get tuples for GESTrackElement children props
        if type(value) is tuple:
            value = value[-1]  # Grab the last item of the tuple

        self._type = type(value)

        if self._type == int or self._type == long:
            minimum, maximum = (-sys.maxint, sys.maxint)
            step = 1.0
            page = 10.0
        elif self._type == float:
            minimum, maximum = (GObject.G_MINDOUBLE, GObject.G_MAXDOUBLE)
            step = 0.01
            page = 0.1
            if self.spinner:
                self.spinner.props.digits = 2
        if self.lower is not None:
            minimum = self.lower
        if self.upper is not None:
            maximum = self.upper
        self.adjustment.configure(value, minimum, maximum, step, page, 0)
        if self.spinner:
            self.spinner.set_adjustment(self.adjustment)


class TimeWidget(TextWidget, DynamicWidget):
    """
    A widget that contains a time in nanoseconds. Accepts timecode formats
    or a frame number (integer).
    """
    # The "frame number" match rule is ^([0-9]+)$ (with a + to require 1 digit)
    # The "timecode" rule is ^([0-9]:[0-5][0-9]:[0-5][0-9])\.[0-9][0-9][0-9]$"
    # Combining the two, we get:
    regex = re.compile("^([0-9]+)$|^([0-9]:[0-5][0-9]:[0-5][0-9])\.[0-9][0-9][0-9]$")
    __gtype_name__ = 'TimeWidget'

    def __init__(self, default=None):
        DynamicWidget.__init__(self, default)
        TextWidget.__init__(self, self.regex)
        TextWidget.set_width_chars(self, 10)
        self._framerate = None

    def getWidgetValue(self):
        timecode = TextWidget.getWidgetValue(self)

        if ":" in timecode:
            hh, mm, end = timecode.split(":")
            ss, xxx = end.split(".")
            nanosecs = int(hh) * 3.6 * 10e12 \
                + int(mm) * 6 * 10e10 \
                + int(ss) * 10e9 \
                + int(xxx) * 10e6
            nanosecs = nanosecs / 10  # Compensate the 10 factor of e notation
        else:
            # We were given a frame number. Convert from the project framerate.
            frame_no = int(timecode)
            nanosecs = frame_no / float(self._framerate) * Gst.SECOND
        # The seeker won't like floating point nanoseconds!
        return int(nanosecs)

    def setWidgetValue(self, value, send_signal=True):
        TextWidget.setWidgetValue(self, time_to_string(value),
                                send_signal=send_signal)

    # No need to define connectValueChanged as it is inherited from DynamicWidget
    def connectActivateEvent(self, activateCb):
        return self.connect("activate", activateCb)

    def connectFocusEvents(self, focusInCb, focusOutCb):
        fIn = self.text.connect("focus-in-event", focusInCb)
        fOut = self.text.connect("focus-out-event", focusOutCb)

        return [fIn, fOut]

    def setFramerate(self, framerate):
        self._framerate = framerate


class FractionWidget(TextWidget, DynamicWidget):

    """A Gtk.ComboBoxEntry """

    fraction_regex = re.compile(
        "^([0-9]*(\.[0-9]+)?)(([:/][0-9]*(\.[0-9]+)?)|M)?$")
    __gtype_name__ = 'FractionWidget'

    def __init__(self, range=None, presets=None, default=None):
        DynamicWidget.__init__(self, default)

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

    def addPresets(self, presets):
        choices = []
        for preset in presets:
            if type(preset) is str:
                strval = preset
                preset = self._parseText(preset)
            else:
                strval = "%g:%g" % (preset.num, preset.denom)
            fpreset = float(preset)
            if self.low <= fpreset and fpreset <= self.high:
                choices.append(strval)

        self.addChoices(choices)

    def setWidgetValue(self, value):
        if type(value) is str:
            value = self._parseText(value)
        elif not hasattr(value, "denom"):
            value = Gst.Fraction(value)
        if (value.denom / 1001) == 1:
            text = "%gM" % (value.num / 1000)
        else:
            text = "%g:%g" % (value.num, value.denom)

        self.text.set_text(text)

    def getWidgetValue(self):
        if self.last_valid:
            return self._parseText(self.last_valid)
        return Gst.Fraction(1, 1)

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
        return Gst.Fraction(num, denom)


class ToggleWidget(Gtk.CheckButton, DynamicWidget):

    """A Gtk.CheckButton which supports the DynamicWidget interface."""

    def __init__(self, default=None):
        Gtk.CheckButton.__init__(self)
        DynamicWidget.__init__(self, default)

    def connectValueChanged(self, callback, *args):
        self.connect("toggled", callback, *args)

    def setWidgetValue(self, value):
        self.set_active(value)

    def getWidgetValue(self):
        return self.get_active()


class ChoiceWidget(Gtk.HBox, DynamicWidget):

    """Abstractly, represents a choice between a list of named values. The
    association between value names and values is arbitrary. The current
    implementation uses a Gtk.ComboBoxText for simplicity."""

    def __init__(self, choices, default=None):
        Gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)
        self.choices = None
        self.values = None
        self.contents = Gtk.ComboBoxText()
        self.pack_start(self.contents, True, True, 0)
        self.setChoices(choices)
        self.contents.show()
        cell = self.contents.get_cells()[0]
        cell.props.ellipsize = Pango.EllipsizeMode.END

    def connectValueChanged(self, callback, *args):
        return self.contents.connect("changed", callback, *args)

    def setWidgetValue(self, value):
        try:
            self.contents.set_active(self.values.index(value))
        except ValueError:
            raise ValueError("%r not in %r" % (value, self.values))

    def getWidgetValue(self):
        return self.values[self.contents.get_active()]

    def setChoices(self, choices):
        self.choices = [choice[0] for choice in choices]
        self.values = [choice[1] for choice in choices]
        m = Gtk.ListStore(str)
        self.contents.set_model(m)
        for choice, value in choices:
            self.contents.append_text(_(choice))
        if len(choices) <= 1:
            self.contents.set_sensitive(False)
        else:
            self.contents.set_sensitive(True)


class PresetChoiceWidget(Gtk.HBox, DynamicWidget):

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

    def __init__(self, presets, default=None):
        Gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)
        self._block_update = False
        self._widget_map = None

        self.presets = presets
        presets.connect("preset-added", self._presetAdded)
        presets.connect("preset-removed", self._presetRemoved)

        self.combo = Gtk.ComboBoxText()
        self.combo.set_row_separator_func(self._sep_func)
        for preset in presets:
            self.combo.append_text(preset[0])
        self.combo.append_text("-")
        self.combo.append_text(_("Custom"))
        self.pack_start(self.combo, True, True, 0)
        self._custom_row = len(presets) + 1

        save_button = Gtk.Button(stock=Gtk.STOCK_SAVE)
        self._save_button = save_button
        self.pack_start(save_button, False, False, 0)
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
        d = Gtk.Dialog(_("Save Preset"), None, Gtk.DialogFlags.MODAL,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK))
        input = Gtk.Entry()
        ca = d.get_content_area()
        ca.pack_start(input, True, True, 0)
        input.show()
        response = d.run()

        if response == Gtk.ResponseType.OK:
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


class PathWidget(Gtk.FileChooserButton, DynamicWidget):

    """A Gtk.FileChooserButton which supports the DynamicWidget interface."""

    __gtype_name__ = 'PathWidget'

    __gsignals__ = {
        "value-changed": (GObject.SignalFlags.RUN_LAST,
            None,
            ()),
    }

    def __init__(self, action=Gtk.FileChooserAction.OPEN, default=None):
        DynamicWidget.__init__(self, default)
        self.dialog = Gtk.FileChooserDialog(
            action=action,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_CLOSE,
             Gtk.ResponseType.CLOSE))
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        Gtk.FileChooserButton.__init__(self, self.dialog)
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
        if response == Gtk.ResponseType.CLOSE:
            self.uri = self.get_uri()
            self.emit("value-changed")
            self.dialog.hide()


class ColorWidget(Gtk.ColorButton, DynamicWidget):

    def __init__(self, value_type=str, default=None):
        Gtk.ColorButton.__init__(self)
        DynamicWidget.__init__(self, default)
        self.value_type = value_type
        self.set_use_alpha(True)

    def connectValueChanged(self, callback, *args):
        self.connect("color-set", callback, *args)

    def setWidgetValue(self, value):
        type_ = type(value)
        alpha = 0xFFFF

        if type_ is str:
            color = Gdk.Color(value)
        elif (type_ is int) or (type_ is long):
            red, green, blue, alpha = unpack_color(value)
            color = Gdk.Color(red, green, blue)
        elif type_ is Gdk.Color:
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
        elif self.value_type is Gdk.Color:
            return color
        return color.to_string()


class FontWidget(Gtk.FontButton, DynamicWidget):

    def __init__(self, default=None):
        Gtk.FontButton.__init__(self)
        DynamicWidget.__init__(self, default)
        self.set_use_font(True)

    def connectValueChanged(self, callback, *args):
        self.connect("font-set", callback, *args)

    def setWidgetValue(self, font_name):
        self.set_font_name(font_name)

    def getWidgetValue(self):
        return self.get_font_name()


class ResolutionWidget(Gtk.HBox, DynamicWidget):

    def __init__(self, default=None):
        Gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)
        self.props.spacing = SPACING

        self.dwidth = 0
        self.dheight = 0
        self.dwidthWidget = NumericWidget(lower=0)
        self.dheightWidget = NumericWidget(lower=0)
        self.pack_start(self.dwidthWidget, True, True, 0)
        self.pack_start(Gtk.Label("x", True, True, 0))
        self.pack_start(self.dheightWidget, True, True, 0)
        self.setWidgetValue((320, 240))
        self.show_all()

    def connectValueChanged(self, callback, *args):
        self.dwidthWidget.connectValueChanged(callback, *args)
        self.dheightWidget.connectValueChanged(callback, *args)

    def setWidgetValue(self, value):
        width, height = value

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
        (TextWidget, "numbers only", ("^\d+$",
            ("12", "14"))),
        (NumericWidget, 42, (100, 1)),
        (ToggleWidget, True, ()),
        (ChoiceWidget, "banana", ((
            ("banana", "banana"),
            ("apple", "apple"),
            ("pear", "pear")),)),
        (ColorWidget, 0x336699FF, (int,)),
        (FontWidget, "Sans 9", ()),
        (FractionWidget, "30M", (
            Gst.FractionRange(Gst.Fraction(1, 1),
            Gst.Fraction(30000, 1001)),
        )),
        (FractionWidget, Gst.Fraction(25000, 1001), (
            Gst.FractionRange(
                Gst.Fraction(1, 1),
                Gst.Fraction(30000, 1001)
            ),
            ("25:1", Gst.Fraction(30, 1), "30M", ),
        )),
    )

    W = Gtk.Window()
    v = Gtk.VBox()
    t = Gtk.Table()

    for y, (klass, default, args) in enumerate(widgets):
        w = klass(*args)
        w.setWidgetValue(default)
        l = Gtk.Label(label=str(w.getWidgetValue()))
        w.connectValueChanged(valueChanged, w, l)
        w.show()
        l.show()
        t.attach(w, 0, 1, y, y + 1)
        t.attach(l, 1, 2, y, y + 1)
    t.show()

    W.add(t)
    W.show()
    Gtk.main()


def make_property_widget(unused_element, prop, value=None):
    """ Creates a Widget for the given element property """
    # FIXME : implement the case for flags
    type_name = GObject.type_name(prop.value_type.fundamental)

    if value is None:
        value = prop.default_value
    if type_name == "gchararray":
        widget = TextWidget(default=prop.default_value)
    elif type_name in ['guint64', 'gint64', 'guint', 'gint', 'gfloat', 'gulong', 'gdouble']:
        maximum, minimum = None, None
        if hasattr(prop, "minimum"):
            minimum = prop.minimum
        if hasattr(prop, "maximum"):
            maximum = prop.maximum
        widget = NumericWidget(default=prop.default_value, upper=maximum, lower=minimum)
    elif type_name == "gboolean":
        widget = ToggleWidget(default=prop.default_value)
    elif type_name == "GEnum":
        choices = []
        for key, val in prop.enum_class.__enum_values__.iteritems():
            choices.append([val.value_name, int(val)])
        widget = ChoiceWidget(choices, default=prop.default_value)
    elif type_name == "GstFraction":
        widget = FractionWidget(None, presets=["0:1"], default=prop.default_value)
    else:
        widget = DefaultWidget(type_name)

    if value is not None and type_name != "GFlags":
        widget.setWidgetValue(value)

    return widget


def make_widget_wrapper(widget):
    """ Creates a wrapper child of DynamicWidget for @widget """
    if isinstance(widget, Gtk.Entry):
        return TextWidget(text_widget=widget)
    elif isinstance(widget, Gtk.Range):
        return NumericWidget(adjustment=widget.get_adjustment())

    # TODO Implement wrappers for more Gtk.Widget types


class GstElementSettingsWidget(Gtk.VBox, Loggable):
    """
    Widget to view/modify properties of a Gst.Element
    """

    custom_ui_creators = None

    def __init__(self):
        Gtk.VBox.__init__(self)
        Loggable.__init__(self)
        self.element = None
        self.ignore = None
        self.properties = None
        self.buttons = {}
        self._unhandled_properties = []
        if self.custom_ui_creators is None:
            self._fill_custom_ui_creators()

    @classmethod
    def _fill_custom_ui_creators(self):
        """
        Automatically detect available custom GUIs for some effects,
        and use them intead of autogenerated interfaces.
        """
        self.custom_ui_creators = {}
        customwidgets_dir = os.path.join(os.path.dirname(__file__), "customwidgets")
        for f in os.listdir(customwidgets_dir):
            if f.endswith(".py"):
                modulename = f.replace(".py", "")
                try:
                    module = imp.load_source(modulename, os.path.join(customwidgets_dir, f))
                    self.custom_ui_creators[modulename] = module.create_widget
                except AttributeError:
                    # Not create_widget method, do not do anything
                    pass

    def setElement(self, element, properties={}, ignore=['name'],
                   default_btn=False, use_element_props=False):
        """
        Set given element on Widget, with optional properties
        """
        self.info("element:%s, use properties:%s", element, properties)
        self.element = element
        self.ignore = ignore
        self.properties = {}
        self.uncontrolled_properties = {}
        created = False
        if isinstance(element, GES.Effect):
            bin_description = element.props.bin_description
            try:
                # First try to create the widget thanks to a custom python coded
                # "override"
                created = self.custom_ui_creators[bin_description](self, element)
                self.pack_start(created, True, True, 0)
                self.show_all()
            except KeyError:
                pass
            if not created:
                try:
                    # Then try to find a Glade file
                    builder = Gtk.Builder()
                    builder.add_from_file(os.path.join(get_ui_dir(),
                                          "customwidgets", bin_description + ".ui"))
                    self.mapBuilder(builder)
                    created = True
                except GLib.GError:
                    pass

        if not created:
            # Finaly we generate the widget
            self._addWidgets(properties, default_btn, use_element_props)

    def mapBuilder(self, builder):
        """
        Analyze a GtkBuilder object, map the GStreamer element's properties
        to corresponding widgets, and connect signals automatically.

        Prop control widgets should be named "element_name::prop_name", where:
        - element_name is the gstreamer element (ex: the "alpha" effect)
        - prop_name is the name of one of a particular property of the element

        If present, a reset button corresponding to the property will be used
        (the button must be named similarly, with "::reset" after the prop name)
        """
        for prop in self._getProperties():
            widget_name = prop.owner_type.name + "::" + prop.name
            widget = builder.get_object(widget_name)
            reset_name = widget_name + "::" + "reset"
            reset_widget = builder.get_object(widget_name)
            if widget is None:
                self._unhandled_properties.append(prop)
            else:
                self.addPropertyWidget(prop, widget, reset_widget)

    def addPropertyWidget(self, prop, widget, to_default_btn=None):
        """
        Connect an element property to a GTK Widget.
        Optionally, a reset button widget can also be provided.

        Unless you want to connect each widget individually, you should be using
        the "mapBuilder" method instead.
        """
        if isinstance(widget, DynamicWidget):
            # if the widget is already a DynamicWidget we use it as is
            dynamic_widget = widget
        else:
            # if the widget is not dynamic we try to create a wrapper around it
            # so we can control it with the standardized DynamicWidget API
            dynamic_widget = make_widget_wrapper(widget)

        if dynamic_widget:
            self.properties[prop] = dynamic_widget

            self.element.connect('notify::' + prop.name, self._propertyChangedCb,
                    dynamic_widget)
            # The "reset to default" button associated with this property
            if isinstance(to_default_btn, Gtk.Button):
                # The "reset to default" button associated with this property
                to_default_btn.connect('clicked', self._defaultBtnClickedCb,
                                       widget)
                self.buttons[button] = to_default_btn
            elif to_default_btn is not None:
                self.warning("to_default_btn should be either a Gtk.Button or "
                             "None")
        else:
            # If we add a non-standard widget, the creator of the widget is
            # responsible for handling its behaviour "by hand"
            self.info("Can not wrap widget %s for property %s" % (widget, prop))
            # We still keep a ref to that widget, "just in case"
            self.uncontrolled_properties[prop] = widget

        if hasattr(prop, 'blurb'):
            widget.set_tooltip_text(prop.blurb)

    def addIgnoreProperty(self, ignore):
        self.ignore.append(ignore)

    def _getProperties(self):
        if isinstance(self.element, GES.BaseEffect):
            is_effect = True
            return [prop for prop in self.element.list_children_properties() if not prop.name in self.ignore]
        else:
            return [prop for prop in GObject.list_properties(self.element) if not prop.name in self.ignore]

    def _addWidgets(self, properties, default_btn, use_element_props):
        """
        Prepare a gtk table containing the property widgets of an element.
        Each property is on a separate row of the table.
        A row is typically a label followed by the widget and a reset button.

        If there are no properties, returns a table containing the label
        "No properties."
        """
        is_effect = False

        props = self._getProperties()
        if not props:
            table = Gtk.Table(rows=1, columns=1)
            widget = Gtk.Label(label=_("No properties."))
            widget.set_sensitive(False)
            table.attach(widget, 0, 1, 0, 1, yoptions=Gtk.AttachOptions.FILL)
            self.pack_start(table, True, True, 0)
            self.show_all()
            return

        if default_btn:
            table = Gtk.Table(rows=len(props), columns=3)
        else:
            table = Gtk.Table(rows=len(props), columns=2)

        table.set_row_spacings(SPACING)
        table.set_col_spacings(SPACING)
        table.set_border_width(SPACING)

        y = 0
        for prop in props:
            # We do not know how to work with GObjects, so blacklist
            # them to avoid noise in the UI
            if (not prop.flags & GObject.PARAM_WRITABLE or
              not prop.flags & GObject.PARAM_READABLE or
              GObject.type_is_a(prop.value_type, GObject.Object)):
                continue

            if is_effect:
                result, prop_value = self.element.get_child_property(prop.name)
                if result is False:
                    self.debug("Could not get property %s value", prop.name)
            else:
                if use_element_props:
                    prop_value = self.element.get_child_property(prop.name)
                else:
                    prop_value = properties.get(prop.name)

            widget = make_property_widget(self.element, prop, prop_value)
            FILL = Gtk.AttachOptions.FILL  # A shortcut to compact code
            if isinstance(widget, ToggleWidget):
                widget.set_label(prop.nick)
                table.attach(widget, 0, 2, y, y + 1, yoptions=FILL)
            else:
                label = Gtk.Label(label=prop.nick + ":")
                label.set_alignment(0.0, 0.5)
                table.attach(label, 0, 1, y, y + 1, xoptions=FILL, yoptions=FILL)
                table.attach(widget, 1, 2, y, y + 1, yoptions=FILL)

            if hasattr(prop, 'blurb'):
                widget.set_tooltip_text(prop.blurb)

            if default_btn:
                reset = self.getResetToDefaultValueButton(prop, widget)
                table.attach(reset, 2, 3, y, y + 1, xoptions=FILL, yoptions=FILL)
            else:
                default_widget = None

            self.addPropertyWidget(prop, widget, None)
            y += 1

        self.pack_start(table, True, True, 0)
        self.show_all()

    def _propertyChangedCb(self, element, pspec, widget):
        widget.setWidgetValue(self.element.get_property(pspec.name))

    def getResetToDefaultValueButton(self, prop, widget):
        icon = Gtk.Image()
        icon.set_from_icon_name("edit-clear-all-symbolic", Gtk.IconSize.MENU)
        button = Gtk.Button()
        button.add(icon)
        button.set_tooltip_text(_("Reset to default value"))
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.connect('clicked', self._defaultBtnClickedCb, widget)

        # Directly add it to the buttons dictionary
        self.buttons[button] = widget
        return button

    def _defaultBtnClickedCb(self, button, widget):
        widget.setWidgetToDefault()

    def getSettings(self, with_default=False):
        """
        returns the dictionnary of propertyname/propertyvalue
        """
        d = {}
        for prop, widget in self.properties.iteritems():
            if (not prop.flags & GObject.PARAM_WRITABLE
            or isinstance(widget, DefaultWidget)):
                continue
            value = widget.getWidgetValue()
            if value is not None and (value != prop.default_value or with_default):
                d[prop.name] = value
        return d


class GstElementSettingsDialog(Loggable):
    """
    Dialog window for viewing/modifying properties of a Gst.Element
    """

    def __init__(self, elementfactory, properties={}, parent_window=None):
        Loggable.__init__(self)
        self.debug("factory:%s, properties:%s", elementfactory, properties)

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(), "elementsettingsdialog.ui"))
        self.builder.connect_signals(self)
        self.ok_btn = self.builder.get_object("okbutton1")

        self.window = self.builder.get_object("dialog1")
        self.elementsettings = GstElementSettingsWidget()
        self.builder.get_object("viewport1").add(self.elementsettings)

        self.factory = elementfactory
        self.element = self.factory.create("elementsettings")
        if not self.element:
            self.warning("Couldn't create element from factory %s", self.factory)
        self.properties = properties
        self._fillWindow()

        # Try to avoid scrolling, whenever possible.
        screen_height = self.window.get_screen().get_height()
        contents_height = self.elementsettings.size_request().height
        maximum_contents_height = max(500, 0.7 * screen_height)
        if contents_height < maximum_contents_height:
            # The height of the content is small enough, disable the scrollbars.
            default_height = -1
            scrolledwindow = self.builder.get_object("scrolledwindow1")
            scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
            scrolledwindow.set_shadow_type(Gtk.ShadowType.NONE)
        else:
            # If we need to scroll, set a reasonable height for the window.
            default_height = 600
        self.window.set_default_size(400, default_height)

        if parent_window:
            self.window.set_transient_for(parent_window)
        self.window.show()

    def _fillWindow(self):
        # set title and frame label
        self.window.set_title(_("Properties for %s") % self.factory.get_longname())
        self.elementsettings.setElement(self.element, self.properties)

    def getSettings(self):
        """ returns the property/value dictionnary of the selected settings """
        return self.elementsettings.getSettings()

    def _resetValuesClickedCb(self, unused_button):
        self.resetAll()

    def resetAll(self):
        for prop, widget in self.elementsettings.properties.iteritems():
            widget.setWidgetToDefault()


class BaseTabs(Gtk.Notebook):
    def __init__(self, app, hide_hpaned=False):
        """ initialize """
        Gtk.Notebook.__init__(self)
        self.set_border_width(SPACING)

        self.connect("create-window", self._createWindowCb)
        self._hide_hpaned = hide_hpaned
        self.app = app
        self._createUi()

    def _createUi(self):
        """ set up the gui """
        settings = self.get_settings()
        settings.props.gtk_dnd_drag_threshold = 1
        self.set_tab_pos(Gtk.PositionType.TOP)

    def append_page(self, child, label):
        Gtk.Notebook.append_page(self, child, label)
        self._set_child_properties(child, label)
        child.show()
        label.show()

    def _set_child_properties(self, child, label):
        self.child_set_property(child, "detachable", True)
        self.child_set_property(child, "tab-expand", False)
        self.child_set_property(child, "tab-fill", True)
        label.props.xalign = 0.0

    def _detachedComponentWindowDestroyCb(self, window, child,
            original_position, label):
        notebook = window.get_child()
        position = notebook.child_get_property(child, "position")
        notebook.remove_page(position)
        label = Gtk.Label(label=label)
        self.insert_page(child, label, original_position)
        self._set_child_properties(child, label)
        self.child_set_property(child, "detachable", True)

        if self._hide_hpaned:
            self._showSecondHpanedInMainWindow()

    def _createWindowCb(self, from_notebook, child, x, y):
        original_position = self.child_get_property(child, "position")
        label = self.child_get_property(child, "tab-label")
        window = Gtk.Window()
        window.set_type_hint(Gdk.WindowTypeHint.UTILITY)

        window.set_title(label)
        window.set_default_size(600, 400)
        window.connect("destroy", self._detachedComponentWindowDestroyCb,
                child, original_position, label)
        notebook = Gtk.Notebook()
        notebook.props.show_tabs = False
        window.add(notebook)

        window.show_all()
        # set_uposition is deprecated but what should I use instead?
        window.set_uposition(x, y)

        if self._hide_hpaned:
            self._hideSecondHpanedInMainWindow()

        return notebook

    def _hideSecondHpanedInMainWindow(self):
        self.app.gui.mainhpaned.remove(self.app.gui.secondhpaned)
        self.app.gui.secondhpaned.remove(self.app.gui.projecttabs)
        self.app.gui.secondhpaned.remove(self.app.gui.propertiestabs)
        self.app.gui.mainhpaned.pack1(self.app.gui.projecttabs, resize=True,
                                      shrink=False)

    def _showSecondHpanedInMainWindow(self):
        self.app.gui.mainhpaned.remove(self.app.gui.projecttabs)
        self.app.gui.secondhpaned.pack1(self.app.gui.projecttabs,
                                        resize=True, shrink=False)
        self.app.gui.secondhpaned.pack2(self.app.gui.propertiestabs,
                                        resize=True, shrink=False)
        self.app.gui.mainhpaned.pack1(self.app.gui.secondhpaned,
                                      resize=True, shrink=False)


class ZoomBox(Gtk.HBox, Zoomable):
    def __init__(self, timeline):
        """
        This will hold the widgets responsible for zooming.
        """
        Gtk.HBox.__init__(self)
        Zoomable.__init__(self)

        self.timeline = timeline

        zoom_fit_btn = Gtk.Button()
        zoom_fit_btn.set_relief(Gtk.ReliefStyle.NONE)
        zoom_fit_btn.set_tooltip_text(ZOOM_FIT)
        zoom_fit_icon = Gtk.Image()
        zoom_fit_icon.set_from_stock(Gtk.STOCK_ZOOM_FIT, Gtk.IconSize.BUTTON)
        zoom_fit_btn_hbox = Gtk.HBox()
        zoom_fit_btn_hbox.pack_start(zoom_fit_icon, False, True, 0)
        zoom_fit_btn_hbox.pack_start(Gtk.Label(_("Zoom")), False, True, 0)
        zoom_fit_btn.add(zoom_fit_btn_hbox)
        zoom_fit_btn.connect("clicked", self._zoomFitCb)

        self.pack_start(zoom_fit_btn, False, True, 0)

        # zooming slider
        self._zoomAdjustment = Gtk.Adjustment()
        self._zoomAdjustment.set_value(Zoomable.getCurrentZoomLevel())
        self._zoomAdjustment.connect("value-changed", self._zoomAdjustmentChangedCb)
        self._zoomAdjustment.props.lower = 0
        self._zoomAdjustment.props.upper = Zoomable.zoom_steps
        zoomslider = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, adjustment=self._zoomAdjustment)
        zoomslider.props.draw_value = False
        zoomslider.set_tooltip_text(_("Zoom Timeline"))
        zoomslider.connect("scroll-event", self._zoomSliderScrollCb)
        zoomslider.set_size_request(100, 0)  # At least 100px wide for precision
        self.pack_start(zoomslider, True, True, 0)

        self.show_all()

        self._updateZoomSlider = True

    def _zoomAdjustmentChangedCb(self, adjustment):
        # GTK crack
        self._updateZoomSlider = False
        Zoomable.setZoomLevel(int(adjustment.get_value()))
        self.timeline._scrollToPlayhead()
        self.zoomed_fitted = False
        self._updateZoomSlider = True

    def _zoomFitCb(self, button):
        self.timeline.zoomFit()

    def _zoomSliderScrollCb(self, unused, event):
        value = self._zoomAdjustment.get_value()
        if event.direction in [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.RIGHT]:
            self._zoomAdjustment.set_value(value + 1)
        elif event.direction in [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.LEFT]:
            self._zoomAdjustment.set_value(value - 1)

    def zoomChanged(self):
        if self._updateZoomSlider:
            self._zoomAdjustment.set_value(self.getCurrentZoomLevel())
