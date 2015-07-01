# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/utils/widgets.py
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

import math
import os
import re
import sys

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import GES
from gi.repository import Pango
from gi.repository import GObject

from gettext import gettext as _

from pitivi.utils.loggable import Loggable
from pitivi.configure import get_ui_dir
from pitivi.utils.ui import beautify_length, \
    unpack_color, pack_color_32, pack_color_64, \
    time_to_string, SPACING, CONTROL_WIDTH
from pitivi.utils.timeline import Zoomable


ZOOM_SLIDER_PADDING = SPACING * 4 / 5


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

    def setWidgetToDefault(self):
        if self.default is not None:
            self.setWidgetValue(self.default)


class DefaultWidget(Gtk.Label):

    """When all hope fails...."""

    def __init__(self, *unused, **unused_kwargs):
        Gtk.Label.__init__(self, _("Implement Me"))

    def setWidgetToDefault(self):
        pass


class TextWidget(Gtk.Box, DynamicWidget):

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

    def __init__(self, matches=None, choices=None, default=None):
        if not default:
            # In the case of text widgets, a blank default is an empty string
            default = ""

        Gtk.Box.__init__(self)
        DynamicWidget.__init__(self, default)

        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_border_width(0)
        self.set_spacing(0)
        if choices:
            self.combo = Gtk.ComboBoxText.new_with_entry()
            self.text = self.combo.get_child()
            self.combo.show()
            self.pack_start(self.combo, expand=True, fill=True, padding=0)
            for choice in choices:
                self.combo.append_text(choice)
        else:
            self.text = Gtk.Entry()
            self.text.show()
            self.pack_start(self.text, expand=True, fill=True, padding=0)
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
                    self.text.set_icon_from_icon_name(1, None)
                self.valid = True
            else:
                if self.valid:
                    self.text.set_icon_from_icon_name(1, "dialog-warning")
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


class NumericWidget(Gtk.Box, DynamicWidget):

    """An horizontal Gtk.Scale and a Gtk.SpinButton which share an adjustment.
    The SpinButton is always displayed, while the Scale only appears if both
    lower and upper bounds are defined"""

    def __init__(self, upper=None, lower=None, default=None):
        Gtk.Box.__init__(self)
        DynamicWidget.__init__(self, default)

        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_spacing(SPACING)
        self.adjustment = Gtk.Adjustment()
        self.upper = upper
        self.lower = lower
        self._type = None
        if (lower is not None and upper is not None) and (lower > -5000 and upper < 5000):
            self.slider = Gtk.Scale.new(
                Gtk.Orientation.HORIZONTAL, self.adjustment)
            self.pack_start(self.slider, expand=True, fill=True, padding=0)
            self.slider.show()
            self.slider.props.draw_value = False
            # Abuse GTK3's progressbar "fill level" feature to provide
            # a visual indication of the default value on property sliders.
            if default is not None:
                self.slider.set_restrict_to_fill_level(False)
                self.slider.set_fill_level(float(default))
                self.slider.set_show_fill_level(True)

        if upper is None:
            upper = GObject.G_MAXDOUBLE
        if lower is None:
            lower = GObject.G_MINDOUBLE
        self.adjustment.props.lower = lower
        self.adjustment.props.upper = upper
        self.spinner = Gtk.SpinButton(adjustment=self.adjustment)
        self.pack_end(self.spinner, fill=True,
                      expand=not hasattr(self, 'slider'), padding=0)
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

        if type_ == int or type_ == int:
            minimum, maximum = (-sys.maxsize, sys.maxsize)
            step = 1.0
            page = 10.0
        elif type_ == float:
            minimum, maximum = (GObject.G_MINDOUBLE, GObject.G_MAXDOUBLE)
            step = 0.01
            page = 0.1
            self.spinner.props.digits = 2
        if self.lower is not None:
            minimum = self.lower
        if self.upper is not None:
            maximum = self.upper
        self.adjustment.configure(value, minimum, maximum, step, page, 0)
        self.spinner.set_adjustment(self.adjustment)


class TimeWidget(TextWidget, DynamicWidget):

    """
    A widget that contains a time in nanoseconds. Accepts timecode formats
    or a frame number (integer).
    """
    # The "frame number" match rule is ^([0-9]+)$ (with a + to require 1 digit)
    # The "timecode" rule is ^([0-9]:[0-5][0-9]:[0-5][0-9])\.[0-9][0-9][0-9]$"
    # Combining the two, we get:
    VALID_REGEX = re.compile(
        "^([0-9]+)$|^([0-9]:)?([0-5][0-9]:[0-5][0-9])\.[0-9][0-9][0-9]$")

    __gtype_name__ = 'TimeWidget'

    def __init__(self, default=None):
        DynamicWidget.__init__(self, default)
        TextWidget.__init__(self, self.VALID_REGEX)
        TextWidget.set_width_chars(self, 10)
        self._framerate = None

    def getWidgetValue(self):
        timecode = TextWidget.getWidgetValue(self)

        if ":" in timecode:
            parts = timecode.split(":")
            if len(parts) == 2:
                hh = 0
                mm, end = parts
            else:
                hh, mm, end = parts
            ss, millis = end.split(".")
            nanosecs = int(hh) * 3.6 * 10e12 \
                + int(mm) * 6 * 10e10 \
                + int(ss) * 10e9 \
                + int(millis) * 10e6
            nanosecs = nanosecs / 10  # Compensate the 10 factor of e notation
        else:
            # We were given a frame number. Convert from the project framerate.
            frame_no = int(timecode)
            nanosecs = frame_no / float(self._framerate) * Gst.SECOND
        # The seeker won't like floating point nanoseconds!
        return int(nanosecs)

    def setWidgetValue(self, timeNanos, send_signal=True):
        timecode = time_to_string(timeNanos)
        if timecode.startswith("0:"):
            timecode = timecode[2:]
        TextWidget.setWidgetValue(self, timecode, send_signal=send_signal)

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


class ChoiceWidget(Gtk.Box, DynamicWidget):

    """Abstractly, represents a choice between a list of named values. The
    association between value names and values is arbitrary. The current
    implementation uses a Gtk.ComboBoxText for simplicity."""

    def __init__(self, choices, default=None):
        Gtk.Box.__init__(self)
        DynamicWidget.__init__(self, default)
        self.choices = None
        self.values = None
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.contents = Gtk.ComboBoxText()
        self.pack_start(self.contents, expand=True, fill=True, padding=0)
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
        self.dialog = Gtk.FileChooserDialog(action=action)
        self.dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        Gtk.FileChooserButton.__init__(self, dialog=self.dialog)
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
        elif (type_ is int) or (type_ is int):
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
        if self.value_type is int:
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


class GstElementSettingsWidget(Gtk.Box, Loggable):

    """
    Widget to view/modify properties of a Gst.Element
    """

    def __init__(self, isControllable=True):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)
        self.element = None
        self.ignore = None
        self.properties = None
        self.buttons = {}
        self.isControllable = isControllable
        self.set_orientation(Gtk.Orientation.VERTICAL)

    def resetKeyframeToggleButtons(self, widget=None):
        """
        Reset all the keyframe togglebuttons for all properties.
        If a property widget is specified, reset only its keyframe togglebutton.
        """
        if widget:
            # Use the dynamic widget (that has been provided as an argument)
            # to find which of the togglebuttons is the related one.
            self.log("Resetting one keyframe button")
            for togglebutton in list(self.keyframeToggleButtons.keys()):
                if self.keyframeToggleButtons[togglebutton] is widget:
                    # The dynamic widget matches the one
                    # related to the current to the current togglebutton
                    togglebutton.set_label("◇")
                    self._setKeyframeToggleButtonState(togglebutton, False)
                    break  # Stop searching
        else:
            self.log("Resetting all keyframe buttons")
            for togglebutton in list(self.keyframeToggleButtons.keys()):
                togglebutton.set_label("◇")
                self._setKeyframeToggleButtonState(togglebutton, False)

        effect = self.element
        parent = effect.get_parent()
        if not parent:
            self.log("Effect has no parent (it has been removed?)")
            return

    def setElement(self, element, properties={}, ignore=['name'],
                   default_btn=False, use_element_props=False):
        """
        Set given element on Widget, with optional properties
        """
        self.info("element: %s, use properties: %s", element, properties)
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
        self.bindings = {}
        self.keyframeToggleButtons = {}
        is_effect = False
        if isinstance(self.element, GES.Effect):
            is_effect = True
            props = [
                prop for prop in self.element.list_children_properties() if prop.name not in self.ignore]
        else:
            props = [prop for prop in GObject.list_properties(
                self.element) if prop.name not in self.ignore]
        if not props:
            table = Gtk.Table(n_rows=1, n_columns=1)
            widget = Gtk.Label(label=_("No properties."))
            widget.set_sensitive(False)
            table.attach(widget, 0, 1, 0, 1, yoptions=Gtk.AttachOptions.FILL)
            self.pack_start(table, expand=True, fill=True, padding=0)
            self.show_all()
            return

        if default_btn:
            table = Gtk.Table(n_rows=len(props), n_columns=4)
        else:
            table = Gtk.Table(n_rows=len(props), n_columns=3)

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
                    self.debug(
                        "Could not get value for property: %s", prop.name)
            else:
                if use_element_props:
                    prop_value = self.element.get_property(prop.name)
                else:
                    prop_value = properties.get(prop.name)

            widget = self._makePropertyWidget(prop, prop_value)
            if isinstance(widget, ToggleWidget):
                widget.set_label(prop.nick)
                table.attach(
                    widget, 0, 2, y, y + 1, yoptions=Gtk.AttachOptions.FILL)
            else:
                label = Gtk.Label(label=prop.nick + ":")
                label.set_alignment(0.0, 0.5)
                table.attach(
                    label, 0, 1, y, y + 1, xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL)
                table.attach(
                    widget, 1, 2, y, y + 1, yoptions=Gtk.AttachOptions.FILL)

            if not isinstance(widget, ToggleWidget) and not isinstance(widget, ChoiceWidget) and self.isControllable:
                button = self._getKeyframeToggleButton(prop)
                self.keyframeToggleButtons[button] = widget
                table.attach(
                    button, 3, 4, y, y + 1, xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL)

            if hasattr(prop, 'blurb'):
                widget.set_tooltip_text(prop.blurb)

            self.properties[prop] = widget

            # The "reset to default" button associated with this property
            if default_btn:
                widget.propName = prop.name.split("-")[0]

                if self.isControllable:
                    # If this element is controlled, the value means nothing
                    # anymore.
                    binding = self.element.get_control_binding(prop.name)
                    if binding:
                        widget.set_sensitive(False)
                        self.bindings[widget] = binding
                button = self._getResetToDefaultValueButton(prop, widget)
                table.attach(
                    button, 2, 3, y, y + 1, xoptions=Gtk.AttachOptions.FILL, yoptions=Gtk.AttachOptions.FILL)
                self.buttons[button] = widget

            y += 1

        self.element.connect('deep-notify', self._propertyChangedCb)
        self.pack_start(table, expand=True, fill=True, padding=0)
        self.show_all()

    def _propertyChangedCb(self, effect, gst_element, pspec):
        widget = self.properties[pspec]
        widget.setWidgetValue(self.element.get_child_property(pspec.name)[1])

    def _getKeyframeToggleButton(self, prop):
        button = Gtk.ToggleButton()
        button.set_label("◇")
        button.props.focus_on_click = False  # Avoid the ugly selection outline
        button.set_tooltip_text(_("Show keyframes for this value"))
        button.connect('toggled', self._showKeyframesToggledCb, prop)
        return button

    def _getResetToDefaultValueButton(self, unused_prop, widget):
        icon = Gtk.Image()
        icon.set_from_icon_name("edit-clear-all-symbolic", Gtk.IconSize.MENU)
        button = Gtk.Button()
        button.add(icon)
        button.set_tooltip_text(_("Reset to default value"))
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.connect('clicked', self._defaultBtnClickedCb, widget)
        return button

    def _setKeyframeToggleButtonState(self, button, active_state):
        """
        This is meant for programmatically (un)pushing the provided keyframe
        togglebutton, without triggering its signals.
        """
        self.log("Manually resetting the UI state of %s" % button)
        button.handler_block_by_func(self._showKeyframesToggledCb)
        button.set_active(active_state)
        button.handler_unblock_by_func(self._showKeyframesToggledCb)

    def _showKeyframesToggledCb(self, button, prop):
        self.log("keyframes togglebutton clicked for %s" % prop)
        active = button.get_active()
        # Disable the related dynamic gst property widget
        widget = self.keyframeToggleButtons[button]
        widget.set_sensitive(False)
        # Now change the state of the *other* togglebuttons.
        for togglebutton in list(self.keyframeToggleButtons.keys()):
            if togglebutton != button:
                # Don't use set_active directly on the buttons; doing so will
                # fire off signals that will toggle the others/confuse the UI
                self._setKeyframeToggleButtonState(togglebutton, False)
        # We always set this label, since the only way to *deactivate* keyframes
        # (not just hide them temporarily) is to use the separate reset button.
        button.set_label("◆")

        effect = self.element
        track_type = effect.get_track_type()
        for track_element in effect.get_parent().get_children(False):
            if active and hasattr(track_element, "ui_element") and track_type == track_element.get_track_type():
                track_element.ui_element.showKeyframes(effect, prop)
                binding = self.element.get_control_binding(prop.name)
                self.bindings[widget] = binding
            elif hasattr(track_element, "ui_element") and track_type == track_element.get_track_type():
                track_element.ui_element.hideKeyframes()

    def _defaultBtnClickedCb(self, unused_button, widget):
        try:
            binding = self.bindings[widget]
        except KeyError:
            binding = None
        if binding:
            effect = self.element
            track_type = effect.get_track_type()
            for track_element in effect.get_parent().get_children(False):
                if hasattr(track_element, "ui_element") and track_type == track_element.get_track_type():
                    binding.props.control_source.unset_all()
                    track_element.ui_element.updateKeyframes()

        widget.set_sensitive(True)
        widget.setWidgetToDefault()
        self.resetKeyframeToggleButtons(widget)

    def getSettings(self, with_default=False):
        """
        returns the dictionnary of propertyname/propertyvalue
        """
        d = {}
        for prop, widget in self.properties.items():
            if not prop.flags & GObject.PARAM_WRITABLE:
                continue
            if isinstance(widget, DefaultWidget):
                continue
            value = widget.getWidgetValue()
            if value is not None and (value != prop.default_value or with_default):
                d[prop.name] = value
        return d

    def _makePropertyWidget(self, prop, value=None):
        """ Creates a Widget for the specified element property """
        type_name = GObject.type_name(prop.value_type.fundamental)
        if type_name == "gchararray":
            widget = TextWidget(default=prop.default_value)
        elif type_name in ['guint64', 'gint64', 'guint', 'gint', 'gfloat', 'gulong', 'gdouble']:
            maximum, minimum = None, None
            if hasattr(prop, "minimum"):
                minimum = prop.minimum
            if hasattr(prop, "maximum"):
                maximum = prop.maximum
            widget = NumericWidget(
                default=prop.default_value, upper=maximum, lower=minimum)
        elif type_name == "gboolean":
            widget = ToggleWidget(default=prop.default_value)
        elif type_name == "GEnum":
            choices = []
            for key, val in prop.enum_class.__enum_values__.items():
                choices.append([val.value_name, int(val)])
            widget = ChoiceWidget(choices, default=prop.default_value)
        elif type_name == "GstFraction":
            widget = FractionWidget(
                None, presets=["0:1"], default=prop.default_value)
        else:
            # TODO: implement widgets for: GBoxed, GFlags
            self.fixme("Unsupported property type: %s", type_name)
            widget = DefaultWidget()

        if value is None:
            value = prop.default_value
        if value is not None and not isinstance(widget, DefaultWidget):
            widget.setWidgetValue(value)

        return widget


class GstElementSettingsDialog(Loggable):

    """
    Dialog window for viewing/modifying properties of a Gst.Element
    """

    def __init__(self, elementfactory, properties, parent_window=None, isControllable=True):
        Loggable.__init__(self)
        self.debug("factory: %s, properties: %s", elementfactory, properties)

        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "elementsettingsdialog.ui"))
        self.builder.connect_signals(self)
        self.ok_btn = self.builder.get_object("okbutton1")

        self.window = self.builder.get_object("dialog1")
        self.elementsettings = GstElementSettingsWidget(isControllable)
        self.builder.get_object("viewport1").add(self.elementsettings)

        self.factory = elementfactory
        self.element = self.factory.create("elementsettings")
        if not self.element:
            self.warning(
                "Couldn't create element from factory %s", self.factory)
        self.properties = properties
        self._fillWindow()

        # Try to avoid scrolling, whenever possible.
        screen_height = self.window.get_screen().get_height()
        contents_height = self.elementsettings.size_request().height
        maximum_contents_height = max(500, 0.7 * screen_height)
        if contents_height < maximum_contents_height:
            # The height of the content is small enough, disable the
            # scrollbars.
            default_height = -1
            scrolledwindow = self.builder.get_object("scrolledwindow1")
            scrolledwindow.set_policy(
                Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
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
        self.window.set_title(
            _("Properties for %s") % self.factory.get_longname())
        self.elementsettings.setElement(self.element, self.properties)

    def getSettings(self):
        """ returns the property/value dictionnary of the selected settings """
        return self.elementsettings.getSettings()

    def _resetValuesClickedCb(self, unused_button):
        self.resetAll()

    def resetAll(self):
        for prop, widget in self.elementsettings.properties.items():
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

    def _createWindowCb(self, unused_from_notebook, child, x, y):
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


class ZoomBox(Gtk.Grid, Zoomable):

    """
    Container holding the widgets for zooming.

    @type timeline: TimelineContainer
    """

    def __init__(self, timeline):
        Gtk.Grid.__init__(self)
        Zoomable.__init__(self)

        self._manual_set = False
        self.timeline = timeline

        zoom_fit_btn = Gtk.Button()
        zoom_fit_btn.set_relief(Gtk.ReliefStyle.NONE)
        zoom_fit_btn.set_tooltip_text(_("Zoom Fit"))
        zoom_fit_btn_grid = Gtk.Grid()
        zoom_fit_icon = Gtk.Image.new_from_icon_name(
            "zoom-best-fit", Gtk.IconSize.BUTTON)
        zoom_fit_btn_grid.add(zoom_fit_icon)
        zoom_fit_btn_label = Gtk.Label(label=_("Zoom"))
        zoom_fit_btn_grid.add(zoom_fit_btn_label)
        zoom_fit_btn_grid.set_column_spacing(SPACING / 2)
        zoom_fit_btn.add(zoom_fit_btn_grid)
        zoom_fit_btn.connect("clicked", self._zoomFitCb)
        self.attach(zoom_fit_btn, 0, 0, 1, 1)

        # zooming slider
        self._zoomAdjustment = Gtk.Adjustment()
        self._zoomAdjustment.props.lower = 0
        self._zoomAdjustment.props.upper = Zoomable.zoom_steps
        zoomslider = Gtk.Scale.new(
            Gtk.Orientation.HORIZONTAL, adjustment=self._zoomAdjustment)
        # Setting _zoomAdjustment's value must be done after we create the
        # zoom slider, otherwise the slider remains at the leftmost position.
        self._zoomAdjustment.set_value(Zoomable.getCurrentZoomLevel())
        zoomslider.props.draw_value = False
        zoomslider.connect("scroll-event", self._zoomSliderScrollCb)
        zoomslider.connect("value-changed", self._zoomAdjustmentChangedCb)
        zoomslider.connect("query-tooltip", self._sliderTooltipCb)
        zoomslider.set_has_tooltip(True)
        # At least 100px wide for precision
        zoomslider.set_size_request(100, 0)
        zoomslider.set_hexpand(True)
        self.attach(zoomslider, 1, 0, 1, 1)

        # Empty label so we have some spacing at the right of the zoomslider
        self.attach(Gtk.Label(label=""), 2, 0, 1, 1)

        self.set_hexpand(False)
        self.set_column_spacing(ZOOM_SLIDER_PADDING)
        self.set_size_request(CONTROL_WIDTH, -1)
        self.show_all()

    def _zoomAdjustmentChangedCb(self, adjustment):
        Zoomable.setZoomLevel(adjustment.get_value())
        self.timeline.app.write_action("set-zoom-level",
                                       {"level": adjustment.get_value(),
                                        "optional-action-type": True})

        if self._manual_set is False:
            self.timeline.scrollToPlayhead()

    def _zoomFitCb(self, unused_button):
        self.timeline.zoomFit()

    def _zoomSliderScrollCb(self, unused, event):
        delta = 0
        if event.direction in [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.RIGHT]:
            delta = 1
        elif event.direction in [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.LEFT]:
            delta = -1
        elif event.direction in [Gdk.ScrollDirection.SMOOTH]:
            unused_res, delta_x, delta_y = event.get_scroll_deltas()
            if delta_x:
                delta = math.copysign(1, delta_x)
            elif delta_y:
                delta = math.copysign(1, -delta_y)
        if delta:
            Zoomable.setZoomLevel(Zoomable.getCurrentZoomLevel() + delta)

    def zoomChanged(self):
        zoomLevel = self.getCurrentZoomLevel()
        if int(self._zoomAdjustment.get_value()) != zoomLevel:
            self._manual_set = True
            self._zoomAdjustment.set_value(zoomLevel)
            self._manual_set = False

    def _sliderTooltipCb(self, unused_slider, unused_x, unused_y, unused_keyboard_mode, tooltip):
        # We assume the width of the ruler is exactly the width of the
        # timeline.
        width_px = self.timeline.ruler.get_allocated_width()
        timeline_width_ns = Zoomable.pixelToNs(width_px)
        if timeline_width_ns >= Gst.SECOND:
            # Translators: %s represents a duration, for example "10 minutes"
            tip = _("%s displayed") % beautify_length(timeline_width_ns)
        else:
            # Translators: This is a tooltip
            tip = _(
                "%d nanoseconds displayed, because we can") % timeline_width_ns
        tooltip.set_text(tip)
        return True
