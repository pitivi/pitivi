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

import gobject
import gtk
import os
import ges
import re
import sys
import gst
import pango

from gettext import gettext as _

from pitivi.utils.loggable import Loggable
from pitivi.configure import get_ui_dir
from pitivi.utils.ui import unpack_color, pack_color_32, pack_color_64, \
    time_to_string, SPACING


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


class DefaultWidget(gtk.Label, DynamicWidget):

    """When all hope fails...."""

    def __init__(self, default=None, *unused, **kw_unused):
        gtk.Label.__init__(self, _("Implement Me"))
        DynamicWidget.__init__(self, default)

    def connectValueChanged(self, callback, *args):
        pass

    def setWidgetValue(self, value):
        self.set_text(value)

    def getWidgetValue(self):
        return self.get_text()


class TextWidget(gtk.HBox, DynamicWidget):

    """A gtk.Entry which emits a value-changed signal only when its input is
    valid (matches the provided regex). If the input is invalid, a warning
    icon is displayed."""

    __gtype_name__ = 'TextWidget'
    __gsignals__ = {
        "value-changed": (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (),)
    }

    __INVALID__ = gtk.gdk.Color(0xFFFF, 0, 0)
    __NORMAL__ = gtk.gdk.Color(0, 0, 0)

    def __init__(self, matches=None, choices=None, default=None):
        gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)

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
        self.send_signal = True
        self.text.connect("changed", self._textChanged)
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
                    self.text.set_icon_from_stock(1, gtk.STOCK_DIALOG_WARNING)
                self.valid = False
        elif self.send_signal:
            self.emit("value-changed")

        self.send_signal = True

    def _filter(self, text):
        match = self.matches.match(text)
        if match is not None:
            return True
        return False

    def set_width_chars(self, width):
        """Allows setting the width of the text entry widget for compactness."""
        self.text.set_width_chars(width)


class NumericWidget(gtk.HBox, DynamicWidget):

    """A gtk.HScale and a gtk.SpinButton which share an adjustment. The
    SpinButton is always displayed, while the HScale only appears if both
    lower and upper bounds are defined"""

    def __init__(self, upper=None, lower=None, default=None):
        gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)

        self.spacing = SPACING
        self.adjustment = gtk.Adjustment()
        self.upper = upper
        self.lower = lower
        self._type = None
        if (upper != None) and (lower != None) and\
            (upper < 5000) and (lower > -5000):
            self.slider = gtk.HScale(self.adjustment)
            self.pack_start(self.slider, fill=True, expand=True)
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
        self.pack_end(self.spinner, expand=not hasattr(self, 'slider'))
        self.spinner.show()

    def connectValueChanged(self, callback, *args):
        self.adjustment.connect("value-changed", callback, *args)

    def getWidgetValue(self):
        if self._type:
            return self._type(self.adjustment.get_value())

        return self.adjustment.get_value()

    def setWidgetValue(self, value):
        type_ = type(value)
        if self._type is None:
            self._type = type_

        if type_ == int or type_ == long:
            minimum, maximum = (-sys.maxint, sys.maxint)
            step = 1.0
            page = 10.0
        elif type_ == float:
            minimum, maximum = (gobject.G_MINDOUBLE, gobject.G_MAXDOUBLE)
            step = 0.01
            page = 0.1
            self.spinner.props.digits = 2
        if self.lower is not None:
            minimum = self.lower
        if self.upper is not None:
            maximum = self.upper
        self.adjustment.set_all(value, minimum, maximum, step, page, 0)
        self.spinner.set_adjustment(self.adjustment)


class TimeWidget(TextWidget, DynamicWidget):
    """ A widget that contains a time in nanosconds"""

    regex = re.compile("^([0-9]:[0-5][0-9]:[0-5][0-9])\.[0-9][0-9][0-9]$")
    __gtype_name__ = 'TimeWidget'

    def __init__(self, default=None):
        DynamicWidget.__init__(self, default)
        TextWidget.__init__(self, self.regex)
        TextWidget.set_width_chars(self, 10)

    def getWidgetValue(self):
        timecode = TextWidget.getWidgetValue(self)

        hh, mm, end = timecode.split(":")
        ss, xxx = end.split(".")
        nanosecs = int(hh) * 3.6 * 10e12 \
            + int(mm) * 6 * 10e10 \
            + int(ss) * 10e9 \
            + int(xxx) * 10e6

        nanosecs = nanosecs / 10  # Compensate the 10 factor of e notation

        return nanosecs

    def setWidgetValue(self, value, send_signal=True):
        TextWidget.setWidgetValue(self, time_to_string(value),
                                send_signal=send_signal)

    def connectFocusEvents(self, focusInCb, focusOutCb):
        fIn = self.text.connect("button-press-event", focusInCb)
        fOut = self.text.connect("focus-out-event", focusOutCb)

        return [fIn, fOut]


class FractionWidget(TextWidget, DynamicWidget):

    """A gtk.ComboBoxEntry """

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


class ToggleWidget(gtk.CheckButton, DynamicWidget):

    """A gtk.CheckButton which supports the DynamicWidget interface."""

    def __init__(self, default=None):
        gtk.CheckButton.__init__(self)
        DynamicWidget.__init__(self, default)

    def connectValueChanged(self, callback, *args):
        self.connect("toggled", callback, *args)

    def setWidgetValue(self, value):
        self.set_active(value)

    def getWidgetValue(self):
        return self.get_active()


class ChoiceWidget(gtk.HBox, DynamicWidget):

    """Abstractly, represents a choice between a list of named values. The
    association between value names and values is arbitrary. The current
    implementation uses a gtk.ComboBox."""

    def __init__(self, choices, default=None):
        gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)
        self.choices = None
        self.values = None
        self.contents = gtk.combo_box_new_text()
        self.pack_start(self.contents)
        self.setChoices(choices)
        self.contents.show()
        cell = self.contents.get_cells()[0]
        cell.props.ellipsize = pango.ELLIPSIZE_END

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
        m = gtk.ListStore(str)
        self.contents.set_model(m)
        for choice, value in choices:
            self.contents.append_text(_(choice))
        if len(choices) <= 1:
            self.contents.set_sensitive(False)
        else:
            self.contents.set_sensitive(True)


class PresetChoiceWidget(gtk.HBox, DynamicWidget):

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
        gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)
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


class PathWidget(gtk.FileChooserButton, DynamicWidget):

    """A gtk.FileChooserButton which supports the DynamicWidget interface."""

    __gtype_name__ = 'PathWidget'

    __gsignals__ = {
        "value-changed": (gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            ()),
    }

    def __init__(self, action=gtk.FILE_CHOOSER_ACTION_OPEN, default=None):
        DynamicWidget.__init__(self, default)
        self.dialog = gtk.FileChooserDialog(
            action=action,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_CLOSE,
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


class ColorWidget(gtk.ColorButton, DynamicWidget):

    def __init__(self, value_type=str, default=None):
        gtk.ColorButton.__init__(self)
        DynamicWidget.__init__(self, default)
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


class FontWidget(gtk.FontButton, DynamicWidget):

    def __init__(self, default=None):
        gtk.FontButton.__init__(self)
        DynamicWidget.__init__(self, default)
        self.set_use_font(True)

    def connectValueChanged(self, callback, *args):
        self.connect("font-set", callback, *args)

    def setWidgetValue(self, font_name):
        self.set_font_name(font_name)

    def getWidgetValue(self):
        return self.get_font_name()


class ResolutionWidget(gtk.HBox, DynamicWidget):

    def __init__(self, default=None):
        gtk.HBox.__init__(self)
        DynamicWidget.__init__(self, default)
        self.props.spacing = SPACING

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
        (FractionWidget, "30M",
            (gst.FractionRange(gst.Fraction(1, 1),
                gst.Fraction(30000, 1001)),)),
        (FractionWidget, gst.Fraction(25000, 1001),
            (
                gst.FractionRange(
                    gst.Fraction(1, 1),
                    gst.Fraction(30000, 1001)
                ),
                ("25:1", gst.Fraction(30, 1), "30M", ),
            )
        ),
    )

    W = gtk.Window()
    v = gtk.VBox()
    t = gtk.Table()

    for y, (klass, default, args) in enumerate(widgets):
        w = klass(*args)
        w.setWidgetValue(default)
        l = gtk.Label(str(w.getWidgetValue()))
        w.connectValueChanged(valueChanged, w, l)
        w.show()
        l.show()
        t.attach(w, 0, 1, y, y + 1)
        t.attach(l, 1, 2, y, y + 1)
    t.show()

    W.add(t)
    W.show()
    gtk.main()


def make_property_widget(unused_element, prop, value=None):
    """ Creates a Widget for the given element property """
    # FIXME : implement the case for flags
    type_name = gobject.type_name(prop.value_type.fundamental)

    if value == None:
        value = prop.default_value
    if (type_name == 'gchararray'):
        widget = TextWidget()
    elif (type_name in ['guint64', 'gint64', 'guint', 'gint', 'gfloat',
        'gulong', 'gdouble']):

        maximum, minimum = None, None
        if hasattr(prop, "minimum"):
            minimum = prop.minimum
        if hasattr(prop, "maximum"):
            maximum = prop.maximum
        widget = NumericWidget(default=prop.default_value,
                                       upper=maximum, lower=minimum)
    elif (type_name == 'gboolean'):
        widget = ToggleWidget(default=prop.default_value)
    elif (type_name == 'GEnum'):
        idx = 0
        choices = []
        for key, val in prop.enum_class.__enum_values__.iteritems():
            choices.append([val.value_name, int(val)])
        widget = ChoiceWidget(choices, default=prop.default_value)
    elif type_name == 'GstFraction':
        widget = FractionWidget(None, presets=["0:1"], default=prop.default_value)
    else:
        widget = DefaultWidget(type_name)

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
                   default_btn=False, use_element_props=False):
        """
        Set given element on Widget, with optional properties
        """
        self.info("element:%s, use properties:%s", element, properties)
        self.element = element
        self.ignore = ignore
        self.properties = {}
        self._addWidgets(properties, default_btn, use_element_props)

    def _addWidgets(self, properties, default_btn, use_element_props):
        """
        Prepare a gtk table containing the property widgets of an element.
        Each property is on a separate row of the table.
        A row is typically a label followed by the widget and a reset button.

        If there are no properties, returns a table containing the label
        "No properties."
        """
        is_effect = False
        if isinstance(self.element, ges.TrackParseLaunchEffect):
            is_effect = True
            props = [prop for prop in self.element.list_children_properties() if not prop.name in self.ignore]
        else:
            props = [prop for prop in gobject.list_properties(self.element) if not prop.name in self.ignore]
        if not props:
            table = gtk.Table(rows=1, columns=1)
            widget = gtk.Label(_("No properties."))
            widget.set_sensitive(False)
            table.attach(widget, 0, 1, 0, 1, yoptions=gtk.FILL)
            self.pack_start(table)
            self.show_all()
            return

        if default_btn:
            table = gtk.Table(rows=len(props), columns=3)
        else:
            table = gtk.Table(rows=len(props), columns=2)

        table.set_row_spacings(SPACING)
        table.set_col_spacings(SPACING)
        table.set_border_width(SPACING)

        y = 0
        for prop in props:
            if not prop.flags & gobject.PARAM_WRITABLE\
              or not prop.flags & gobject.PARAM_READABLE:
                continue

            if is_effect:
                prop_value = self.element.get_child_property(prop.name)
            else:
                if use_element_props:
                    prop_value = self.element.get_property(prop.name)
                else:
                    prop_value = properties.get(prop.name)

            widget = make_property_widget(self.element, prop, prop_value)
            if isinstance(widget, ToggleWidget):
                widget.set_label(prop.nick)
                table.attach(widget, 0, 2, y, y + 1, yoptions=gtk.FILL)
            else:
                label = gtk.Label(prop.nick + ":")
                label.set_alignment(0.0, 0.5)
                table.attach(label, 0, 1, y, y + 1, xoptions=gtk.FILL, yoptions=gtk.FILL)
                table.attach(widget, 1, 2, y, y + 1, yoptions=gtk.FILL)

            if hasattr(prop, 'blurb'):
                widget.set_tooltip_text(prop.blurb)

            self.properties[prop] = widget

            # The "reset to default" button associated with this property
            if default_btn:
                button = self._getResetToDefaultValueButton(prop, widget)
                table.attach(button, 2, 3, y, y + 1, xoptions=gtk.FILL, yoptions=gtk.FILL)
                self.buttons[button] = widget
            self.element.connect('notify::' + prop.name, self._propertyChangedCb, widget)

            y += 1

        self.pack_start(table)
        self.show_all()

    def _propertyChangedCb(self, element, pspec, widget):
        widget.setWidgetValue(self.element.get_property(pspec.name))

    def _getResetToDefaultValueButton(self, prop, widget):
        icon = gtk.Image()
        icon.set_from_stock('gtk-clear', gtk.ICON_SIZE_MENU)
        button = gtk.Button()
        button.add(icon)
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
              or isinstance(widget, DefaultWidget):
                continue
            value = widget.getWidgetValue()
            if value != None and (value != prop.default_value or with_default):
                d[prop.name] = value
        return d


class GstElementSettingsDialog(Loggable):
    """
    Dialog window for viewing/modifying properties of a gst.Element
    """

    def __init__(self, elementfactory, properties={}):
        Loggable.__init__(self)
        self.debug("factory:%s, properties:%s", elementfactory, properties)

        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(),
            "elementsettingsdialog.ui"))
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
        contents_height = self.elementsettings.size_request()[1]
        maximum_contents_height = max(500, 0.7 * screen_height)
        if contents_height < maximum_contents_height:
            # The height of the content is small enough, disable the scrollbars.
            default_height = -1
            scrolledwindow = self.builder.get_object("scrolledwindow1")
            scrolledwindow.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
            scrolledwindow.set_shadow_type(gtk.SHADOW_NONE)
        else:
            # If we need to scroll, set a reasonable height for the window.
            default_height = 600
        self.window.set_default_size(300, default_height)

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


class BaseTabs(gtk.Notebook):
    def __init__(self, app, hide_hpaned=False):
        """ initialize """
        gtk.Notebook.__init__(self)
        self.set_border_width(SPACING)

        self.connect("create-window", self._createWindowCb)
        self._hide_hpaned = hide_hpaned
        self.app = app
        self._createUi()

    def _createUi(self):
        """ set up the gui """
        settings = self.get_settings()
        settings.props.gtk_dnd_drag_threshold = 1
        self.set_tab_pos(gtk.POS_TOP)

    def append_page(self, child, label):
        gtk.Notebook.append_page(self, child, label)
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
        notebook = window.child
        position = notebook.child_get_property(child, "position")
        notebook.remove_page(position)
        label = gtk.Label(label)
        self.insert_page(child, label, original_position)
        self._set_child_properties(child, label)
        self.child_set_property(child, "detachable", True)

        if self._hide_hpaned:
            self._showSecondHpanedInMainWindow()

    def _createWindowCb(self, from_notebook, child, x, y):
        original_position = self.child_get_property(child, "position")
        label = self.child_get_property(child, "tab-label")
        window = gtk.Window()
        window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)

        window.set_title(label)
        window.set_default_size(600, 400)
        window.connect("destroy", self._detachedComponentWindowDestroyCb,
                child, original_position, label)
        notebook = gtk.Notebook()
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
