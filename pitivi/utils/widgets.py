# -*- coding: utf-8 -*-
# Pitivi video editor
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
"""Classes and routines for creating widgets from `Gst.Element`s."""
import math
import os
import re
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_ui_dir
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import is_valid_file
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import beautify_length
from pitivi.utils.ui import disable_scroll
from pitivi.utils.ui import SPACING
from pitivi.utils.ui import time_to_string


ZOOM_SLIDER_PADDING = SPACING * 4 / 5


class DynamicWidget(Loggable):
    """Abstract widget providing a way to get, set and observe properties."""

    def __init__(self, default):
        super().__init__()
        self.default = default

    def connectValueChanged(self, callback, *args):
        raise NotImplementedError

    def setWidgetValue(self, value):
        raise NotImplementedError

    def getWidgetValue(self):
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
        self.props.halign = Gtk.Align.START

    def connectValueChanged(self, callback, *args):
        pass

    def setWidgetValue(self, value):
        pass

    def getWidgetValue(self):
        pass

    def setWidgetToDefault(self):
        pass


class TextWidget(Gtk.Box, DynamicWidget):
    """Widget for entering text.

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

    def __init__(self, matches=None, choices=None, default=None, combobox=False, widget=None):
        if not default:
            # In the case of text widgets, a blank default is an empty string
            default = ""

        Gtk.Box.__init__(self)
        DynamicWidget.__init__(self, default)

        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_border_width(0)
        self.set_spacing(0)
        if widget is None:
            if choices:
                self.combo = Gtk.ComboBoxText.new_with_entry()
                self.text = self.combo.get_child()
                self.combo.show()
                disable_scroll(self.combo)
                self.pack_start(self.combo, expand=False, fill=False, padding=0)
                for choice in choices:
                    self.combo.append_text(choice)
            elif combobox:
                self.combo = Gtk.ComboBox.new_with_entry()
                self.text = self.combo.get_child()
                self.combo.show()
                self.pack_start(self.combo, expand=False, fill=False, padding=0)
            else:
                self.text = Gtk.Entry()
                self.text.show()
                self.pack_start(self.text, expand=False, fill=False, padding=0)
        else:
            self.text = widget

        self.matches = None
        self.last_valid = None
        self.valid = False
        self.send_signal = True
        self.text.connect("changed", self.__text_changed_cb)
        self.text.connect("activate", self.__activate_cb)
        if matches:
            if type(matches) is str:
                self.matches = re.compile(matches)
            else:
                self.matches = matches
            self.__text_changed_cb(None)

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

    def __text_changed_cb(self, unused_widget):
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

    def __activate_cb(self, unused_widget):
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
    """Widget for entering a number.

    Contains both a Gtk.Scale and a Gtk.SpinButton for adjusting the value.
    The SpinButton is always displayed, while the Scale only appears if both
    lower and upper bounds are defined.

    Args:
        upper (Optional[int]): The upper limit for this widget.
        lower (Optional[int]): The lower limit for this widget.
    """

    def __init__(self, upper=None, lower=None, default=None, adjustment=None):
        Gtk.Box.__init__(self)
        DynamicWidget.__init__(self, default)

        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_spacing(SPACING)
        self._type = None
        self.spinner = None
        self.handler_id = None

        if adjustment:
            self.adjustment = adjustment
            return
        reasonable_limit = 5000
        with_slider = (lower is not None and lower > -reasonable_limit and
                       upper is not None and upper < reasonable_limit)
        self.adjustment = Gtk.Adjustment()
        if upper is None:
            upper = GLib.MAXINT32
        if lower is None:
            lower = GLib.MININT32
        self.adjustment.props.lower = lower
        self.adjustment.props.upper = upper

        if with_slider:
            self.slider = Gtk.Scale.new(
                Gtk.Orientation.HORIZONTAL, self.adjustment)
            self.pack_end(self.slider, expand=False, fill=False, padding=0)
            self.slider.show()
            disable_scroll(self.slider)
            self.slider.set_size_request(width=100, height=-1)
            self.slider.props.draw_value = False
            # Abuse GTK3's progressbar "fill level" feature to provide
            # a visual indication of the default value on property sliders.
            if default is not None:
                self.slider.set_restrict_to_fill_level(False)
                self.slider.set_fill_level(float(default))
                self.slider.set_show_fill_level(True)

        self.spinner = Gtk.SpinButton(adjustment=self.adjustment)
        self.pack_start(self.spinner, expand=False, fill=False, padding=0)
        self.spinner.show()
        disable_scroll(self.spinner)

    def block_signals(self):
        if self.handler_id:
            self.adjustment.handler_block(self.handler_id)

    def unblock_signals(self):
        if self.handler_id:
            self.adjustment.handler_unblock(self.handler_id)

    def connectValueChanged(self, callback, *args):
        self.handler_id = self.adjustment.connect("value-changed", callback, *args)

    def getWidgetValue(self):
        if self._type:
            return self._type(self.adjustment.get_value())

        return self.adjustment.get_value()

    def setWidgetValue(self, value):
        type_ = type(value)
        if self._type is None:
            self._type = type_

        if type_ == int:
            step = 1.0
            page = 10.0
        elif type_ == float:
            step = 0.01
            page = 0.1
            if self.spinner:
                self.spinner.props.digits = 2
        else:
            raise Exception('Unsupported property type: %s' % type_)
        lower = min(self.adjustment.props.lower, value)
        upper = max(self.adjustment.props.upper, value)
        self.adjustment.configure(value, lower, upper, step, page, 0)


class TimeWidget(TextWidget, DynamicWidget):
    """Widget for entering a time value.

    Accepts timecode formats or a frame number (integer).
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
        self.text.connect("focus-out-event", self._focus_out_cb)

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
        return int(nanosecs)

    def setWidgetValue(self, timeNanos, send_signal=True):
        self.default = timeNanos
        timecode = time_to_string(timeNanos)
        if timecode.startswith("0:"):
            timecode = timecode[2:]
        TextWidget.setWidgetValue(self, timecode, send_signal=send_signal)

    def _focus_out_cb(self, widget, event):
        """Reset the text to display the current position of the playhead."""
        if self.default is not None:
            self.setWidgetValue(self.default)

    def connectActivateEvent(self, activateCb):
        return self.connect("activate", activateCb)

    def connectFocusEvents(self, focusInCb, focusOutCb):
        fIn = self.text.connect("focus-in-event", focusInCb)
        fOut = self.text.connect("focus-out-event", focusOutCb)

        return [fIn, fOut]

    def setFramerate(self, framerate):
        self._framerate = framerate


class FractionWidget(TextWidget, DynamicWidget):
    """Widget for entering a fraction."""

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
        if value.denom == 1001:
            text = "%dM" % (value.num / 1000)
        else:
            text = "%d:%d" % (value.num, value.denom)

        self.text.set_text(text)

    def getWidgetValue(self):
        if self.last_valid:
            return self._parseText(self.last_valid)
        return Gst.Fraction(1, 1)

    @classmethod
    def _parseText(cls, text):
        match = cls.fraction_regex.match(text)
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


class ToggleWidget(Gtk.Box, DynamicWidget):
    """Widget for entering an on/off value."""

    def __init__(self, default=None, switch_button=None):
        Gtk.Box.__init__(self)
        DynamicWidget.__init__(self, default)
        if switch_button is None:
            self.switch_button = Gtk.Switch()
            self.pack_start(self.switch_button, expand=False, fill=False, padding=0)
            self.switch_button.show()
        else:
            self.switch_button = switch_button
            self.setWidgetToDefault()

    def connectValueChanged(self, callback, *args):
        self.switch_button.connect("activate", callback, *args)

    def setWidgetValue(self, value):
        self.switch_button.set_active(value)

    def getWidgetValue(self):
        return self.switch_button.get_active()


class ChoiceWidget(Gtk.Box, DynamicWidget):
    """Widget for making a choice between a list of named values."""

    def __init__(self, choices, default=None):
        Gtk.Box.__init__(self)
        DynamicWidget.__init__(self, default)
        self.choices = None
        self.values = None
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.contents = Gtk.ComboBoxText()
        self.pack_start(self.contents, expand=False, fill=False, padding=0)
        self.setChoices(choices)
        self.contents.show()
        disable_scroll(self.contents)
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
    """Widget for entering a path."""

    __gtype_name__ = 'PathWidget'

    __gsignals__ = {
        "value-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
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

    def __init__(self, default=None):
        Gtk.ColorButton.__init__(self)
        DynamicWidget.__init__(self, default)

    def connectValueChanged(self, callback, *args):
        self.connect("color-set", callback, *args)

    def setWidgetValue(self, value):
        self.set_rgba(value)

    def getWidgetValue(self):
        return self.get_rgba()


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


class InputValidationWidget(Gtk.Box, DynamicWidget):
    """Widget for validating the input of another widget.

    It shows a warning sign if the input is not valid and rolls back to
    the default widget value (which should always be valid).

    Args:
        widget (DynamicWidget): widget whose input needs validation.
        validation_function (function): function which receives the input of the
            widget and returns True iff the input is valid.
    """

    def __init__(self, widget, validation_function):
        Gtk.Box.__init__(self)
        DynamicWidget.__init__(self, widget.default)
        self._widget = widget
        self._validation_function = validation_function
        self._warning_sign = Gtk.Image.new_from_icon_name("dialog-warning", 3)

        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.pack_start(self._widget, expand=False, fill=False, padding=0)
        self.pack_start(self._warning_sign, expand=False, fill=False, padding=SPACING)
        self._warning_sign.set_no_show_all(True)

        self._widget.connectValueChanged(self._widget_value_changed_cb)

    def connectValueChanged(self, callback, *args):
        return self._widget.connectValueChanged(callback, args)

    def setWidgetValue(self, value):
        self._widget.setWidgetValue(value)

    def getWidgetValue(self):
        value = self._widget.getWidgetValue()
        if self._validation_function(value):
            return value
        return self.getWidgetDefault()

    def _widget_value_changed_cb(self, unused_widget):
        value = self._widget.getWidgetValue()
        if self._validation_function(value):
            self._warning_sign.hide()
        else:
            self._warning_sign.show()


def make_widget_wrapper(prop, widget):
    """Creates a wrapper child of DynamicWidget for @widget."""
    # Respect Object hierarchy here
    if isinstance(widget, Gtk.SpinButton):
        widget_adjustment = widget.get_adjustment()
        widget_lower = widget_adjustment.props.lower
        widget_upper = widget_adjustment.props.upper
        return NumericWidget(upper=widget_upper, lower=widget_lower, adjustment=widget_adjustment, default=prop.default_value)
    elif isinstance(widget, Gtk.Entry):
        return TextWidget(widget=widget)
    elif isinstance(widget, Gtk.Range):
        widget_adjustment = widget.get_adjustment()
        widget_lower = widget_adjustment.props.lower
        widget_upper = widget_adjustment.props.upper
        return NumericWidget(upper=widget_upper, lower=widget_lower, adjustment=widget_adjustment, default=prop.default_value)
    elif isinstance(widget, Gtk.CheckButton):
        return ToggleWidget(prop.default_value, widget)
    else:
        Loggable().fixme("%s has not been wrapped into a Dynamic Widget", widget)


class GstElementSettingsWidget(Gtk.Box, Loggable):
    """Widget to modify the properties of a Gst.Element.

    Can be used to configure an effect or an encoder, etc.

    Args:
        controllable (bool): Whether the properties being controlled by
            keyframes is allowed.
    """

    # Dictionary that maps tuples of (element_name, property_name) to a
    # validation function.
    INPUT_VALIDATION_FUNCTIONS = {
        ("x264enc", "multipass-cache-file"): is_valid_file
    }

    # Dictionary that references the GstCaps field to expose in the UI
    # for a well known set of elements.
    CAP_FIELDS_TO_EXPOSE = {
        "x264enc": {"profile": Gst.ValueList(["high", "main", "baseline"])}
    }

    def __init__(self, element, props_to_ignore=["name"], controllable=True):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)
        self.element = element
        self.ignore = props_to_ignore
        self.properties = {}
        # Maps caps fields to the corresponding widgets.
        self.caps_widgets = {}
        self.__controllable = controllable
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.__bindings_by_keyframe_button = {}
        self.__widgets_by_keyframe_button = {}
        self.__widgets_by_reset_button = {}
        self._unhandled_properties = []
        self.uncontrolled_properties = {}
        self.updating_property = False

    def deactivate_keyframe_toggle_buttons(self):
        """Makes sure the keyframe togglebuttons are deactivated."""
        self.log("Deactivating all keyframe toggle buttons")
        for keyframe_button in self.__widgets_by_keyframe_button.keys():
            if keyframe_button.get_active():
                # Deactivate the button. The only effect should be that
                # the keyframe curve will control again the default property.
                keyframe_button.set_active(False)
                # There can be only one active keyframes button.
                break

    def show_widget(self, widget):
        self.pack_start(widget, True, True, 0)
        self.show_all()

    def mapBuilder(self, builder):
        """Maps the GStreamer element's properties to corresponding widgets in @builder.

        Prop control widgets should be named "element_name::prop_name", where:
        - element_name is the gstreamer element (ex: the "alpha" effect)
        - prop_name is the name of one of a particular property of the element
        If present, a reset button corresponding to the property will be used
        (the button must be named similarly, with "::reset" after the prop name)
        A button named reset_all_button can also be provided and will be used as
        a fallback for each property without an individual reset button.
        Similarly, the keyframe control button corresponding to the property (if controllable)
        can be used whose name is to be "element_name::prop_name::keyframe".
        """
        reset_all_button = builder.get_object("reset_all_button")
        for prop in self._getProperties():
            widget_name = prop.owner_type.name + "::" + prop.name
            widget = builder.get_object(widget_name)
            if widget is None:
                self._unhandled_properties.append(prop)
                self.warning("No custom widget found for %s property \"%s\"" %
                             (prop.owner_type.name, prop.name))
            else:
                reset_name = widget_name + "::" + "reset"
                reset_widget = builder.get_object(reset_name)
                if not reset_widget:
                    # If reset_all_button is not found, it will be None
                    reset_widget = reset_all_button
                keyframe_name = widget_name + "::" + "keyframe"
                keyframe_widget = builder.get_object(keyframe_name)
                self.addPropertyWidget(prop, widget, reset_widget, keyframe_widget)

    def addPropertyWidget(self, prop, widget, to_default_btn=None, keyframe_btn=None):
        """Connects an element property to a GTK Widget.

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
            dynamic_widget = make_widget_wrapper(prop, widget)

        if dynamic_widget:
            self.properties[prop] = dynamic_widget

            self.element.connect("notify::" + prop.name, self._propertyChangedCb,
                                 dynamic_widget)
            # The "reset to default" button associated with this property
            if isinstance(to_default_btn, Gtk.Button):
                self.__widgets_by_reset_button[to_default_btn] = widget
                to_default_btn.connect("clicked", self.__reset_to_default_clicked_cb, dynamic_widget, keyframe_btn)
            elif to_default_btn is not None:
                self.warning("to_default_btn should be Gtk.Button or None, got %s", to_default_btn)

            # The "keyframe toggle" button associated with this property
            if not isinstance(widget, (ToggleWidget, ChoiceWidget)):
                res, element, pspec = self.element.lookup_child(prop.name)
                assert res
                binding = GstController.DirectControlBinding.new(
                    element, prop.name,
                    GstController.InterpolationControlSource())
                if binding.pspec:
                    # The prop can be controlled (keyframed).
                    if isinstance(keyframe_btn, Gtk.ToggleButton):
                        keyframe_btn.connect("toggled", self.__keyframes_toggled_cb, prop)
                        self.__widgets_by_keyframe_button[keyframe_btn] = widget
                        prop_binding = self.element.get_control_binding(prop.name)
                        self.__bindings_by_keyframe_button[keyframe_btn] = prop_binding
                        self.__display_controlled(keyframe_btn, bool(prop_binding))
                    elif keyframe_btn is not None:
                        self.warning("keyframe_btn should be Gtk.ToggleButton or None, got %s", to_default_btn)
        else:
            # If we add a non-standard widget, the creator of the widget is
            # responsible for handling its behaviour "by hand"
            self.info("Can not wrap widget %s for property %s" % (widget, prop))
            # We still keep a ref to that widget, "just in case"
            self.uncontrolled_properties[prop] = widget

        if hasattr(prop, "blurb"):
            widget.set_tooltip_text(prop.blurb)

    def _getProperties(self):
        if isinstance(self.element, GES.BaseEffect):
            props = self.element.list_children_properties()
        else:
            props = GObject.list_properties(self.element)
        return [prop for prop in props if prop.name not in self.ignore]

    def __add_widget_to_grid(self, grid, nick, widget, y):
        if isinstance(widget, ToggleWidget):
            widget.set_label(nick)
            grid.attach(widget, 0, y, 2, 1)
        else:
            text = _("%(preference_label)s:") % {"preference_label": nick}
            label = Gtk.Label(label=text)
            label.props.yalign = 0.5
            grid.attach(label, 0, y, 1, 1)
            grid.attach(widget, 1, y, 1, 1)

    def add_widgets(self, create_property_widget, values={}, with_reset_button=False, caps_values=None):
        """Prepares a Gtk.Grid containing the property widgets of an element.

        Each property is on a separate row.
        A row is typically a label followed by the widget and a reset button.

        If there are no properties, returns a "No properties" label.

        Args:
            create_property_widget (function): The function that gets the widget for an effect property.
            values (dict): The current values of the element props, by name.
                If empty, the default values will be used.
            with_reset_button (bool): Whether to show a reset button for each
                property.
        """
        self.info("element: %s, use values: %s", self.element, values)
        self.properties.clear()
        self.__bindings_by_keyframe_button = {}
        self.__widgets_by_keyframe_button = {}
        is_effect = isinstance(self.element, GES.Effect)
        if is_effect:
            props = [prop for prop in self.element.list_children_properties()
                     if prop.name not in self.ignore]
        else:
            props = [prop for prop in GObject.list_properties(self.element)
                     if prop.name not in self.ignore]
        if not props:
            widget = Gtk.Label(label=_("No properties."))
            self.pack_start(widget, expand=False, fill=False, padding=0)
            widget.show()
            return

        grid = Gtk.Grid()
        grid.props.row_spacing = SPACING
        grid.props.column_spacing = SPACING
        grid.props.border_width = SPACING

        element_name = None
        if isinstance(self.element, Gst.Element):
            element_name = self.element.get_factory().get_name()

        src_caps_fields = self.CAP_FIELDS_TO_EXPOSE.get(element_name)
        y = 0
        if src_caps_fields:
            srccaps = self.element.get_static_pad('src').get_pad_template().caps

            for field, prefered_value in src_caps_fields.items():
                gvalue = srccaps[0][field]
                if isinstance(gvalue, Gst.ValueList) and isinstance(prefered_value, Gst.ValueList):
                    prefered_value = Gst.ValueList([v for v in prefered_value if v in gvalue])
                    gvalue = Gst.ValueList.merge(prefered_value, gvalue)

                widget = self._make_widget_from_gvalue(gvalue, prefered_value)
                if caps_values.get(field):
                    widget.setWidgetValue(caps_values[field])
                self.__add_widget_to_grid(grid, field.capitalize(), widget, y)
                y += 1

                self.caps_widgets[field] = widget

        for y, prop in enumerate(props, start=y):
            # We do not know how to work with GObjects, so blacklist
            # them to avoid noise in the UI
            if (not prop.flags & GObject.ParamFlags.WRITABLE or
                    not prop.flags & GObject.ParamFlags.READABLE or
                    GObject.type_is_a(prop.value_type, GObject.Object)):
                continue

            if is_effect:
                result, prop_value = self.element.get_child_property(prop.name)
                if not result:
                    self.debug(
                        "Could not get value for property: %s", prop.name)
            else:
                if prop.name not in values.keys():
                    # Use the default value.
                    prop_value = self.element.get_property(prop.name)
                else:
                    prop_value = values[prop.name]

            prop_widget = create_property_widget(self, prop, prop_value)
            element_name = None
            if isinstance(self.element, Gst.Element):
                element_name = self.element.get_factory().get_name()
            try:
                validation_func = self.INPUT_VALIDATION_FUNCTIONS[(element_name, prop.name)]
                widget = InputValidationWidget(prop_widget, validation_func)
                self.debug("Input validation widget created for (%s, %s)", element_name, prop.name)
            except KeyError:
                widget = prop_widget

            if isinstance(prop_widget, ToggleWidget):
                prop_widget.check_button.set_label(prop.nick)
                grid.attach(widget, 0, y, 2, 1)
            else:
                text = _("%(preference_label)s:") % {"preference_label": prop.nick}
                label = Gtk.Label(label=text)
                label.set_alignment(0.0, 0.5)
                grid.attach(label, 0, y, 1, 1)
                grid.attach(widget, 1, y, 1, 1)
            if hasattr(prop, 'blurb'):
                widget.set_tooltip_text(prop.blurb)

            self.properties[prop] = widget

            if not self.__controllable or isinstance(prop_widget, DefaultWidget):
                continue

            keyframe_button = None
            if not isinstance(prop_widget, (ToggleWidget, ChoiceWidget)):
                res, element, pspec = self.element.lookup_child(prop.name)
                assert res
                binding = GstController.DirectControlBinding.new(
                    element, prop.name,
                    GstController.InterpolationControlSource())
                if binding.pspec:
                    # The prop can be controlled (keyframed).
                    keyframe_button = self.__create_keyframe_toggle_button(prop, widget)
                    grid.attach(keyframe_button, 2, y, 1, 1)

            # The "reset to default" button associated with this property
            if with_reset_button:
                button = self.__create_reset_to_default_button(prop, widget,
                                                               keyframe_button)
                grid.attach(button, 3, y, 1, 1)

        self.element.connect('deep-notify', self._propertyChangedCb)
        self.pack_start(grid, expand=False, fill=False, padding=0)
        self.show_all()

    def _make_widget_from_gvalue(self, gvalue, default):
        if type(gvalue) == Gst.ValueList:
            choices = []
            for val in gvalue:
                choices.append([val, val])
            widget = ChoiceWidget(choices, default=default[0])
            widget.setWidgetValue(default[0])
        else:
            # TODO: implement widgets for other types.
            self.fixme("Unsupported value type: %s", type(gvalue))
            widget = DefaultWidget()

        return widget

    def _propertyChangedCb(self, effect, gst_element, pspec):
        if gst_element.get_control_binding(pspec.name):
            self.log("%s controlled, not displaying value", pspec.name)
            return

        widget = self.properties[pspec]
        res, value = self.element.get_child_property(pspec.name)
        assert res
        widget.setWidgetValue(value)

    def __create_keyframe_toggle_button(self, prop, widget):
        keyframe_button = Gtk.ToggleButton()
        keyframe_button.props.focus_on_click = False  # Avoid the ugly selection outline
        keyframe_button.set_tooltip_text(_("Show keyframes for this value"))
        keyframe_button.set_relief(Gtk.ReliefStyle.NONE)
        keyframe_button.connect('toggled', self.__keyframes_toggled_cb, prop)
        self.__widgets_by_keyframe_button[keyframe_button] = widget
        prop_binding = self.element.get_control_binding(prop.name)
        self.__bindings_by_keyframe_button[keyframe_button] = prop_binding
        self.__display_controlled(keyframe_button, bool(prop_binding))
        return keyframe_button

    def __create_reset_to_default_button(self, unused_prop, widget,
                                         keyframe_button):
        icon = Gtk.Image()
        icon.set_from_icon_name("edit-clear-all-symbolic", Gtk.IconSize.MENU)
        button = Gtk.Button()
        button.add(icon)
        button.set_tooltip_text(_("Reset to default value"))
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.connect('clicked', self.__reset_to_default_clicked_cb, widget,
                       keyframe_button)
        self.__widgets_by_reset_button[button] = widget
        return button

    def __set_keyframe_active(self, toggle_button, active):
        """Updates the specified button without triggering signals.

        Args:
            toggle_button (Gtk.ToggleButton): The toggle button enabling controlling
                the property by keyframes.
            active (bool): The desired status of the `toggle_button`.
        """
        self.log("Manually resetting the UI state of %s", toggle_button)
        toggle_button.handler_block_by_func(self.__keyframes_toggled_cb)
        toggle_button.set_active(active)
        toggle_button.handler_unblock_by_func(self.__keyframes_toggled_cb)

    def __display_controlled(self, toggle_button, controlled):
        """Displays whether the prop is keyframed."""
        widget = self.__widgets_by_keyframe_button[toggle_button]
        # The displayed value means nothing if the prop is controlled.
        widget.set_sensitive(not controlled)
        # The full disc label indicates the property is controlled (keyframed).
        toggle_button.set_label("◆" if controlled else "◇")

    def __keyframes_toggled_cb(self, keyframe_button, prop):
        self.log("keyframes togglebutton clicked for %s", prop)
        active = keyframe_button.get_active()
        # Now change the state of the *other* togglebuttons.
        for toggle_keyframe_button in self.__widgets_by_keyframe_button.keys():
            if toggle_keyframe_button != keyframe_button:
                # Don't use set_active directly on the buttons; doing so will
                # fire off signals that will toggle the others/confuse the UI
                self.__set_keyframe_active(toggle_keyframe_button, False)
        # The only way to *deactivate* keyframes (not just hide them) is to use
        # the separate reset button.
        self.__display_controlled(keyframe_button, True)

        track_element = self.__get_track_element_of_same_type(self.element)
        if not track_element:
            return

        if active:
            track_element.ui_element.showKeyframes(self.element, prop)
            binding = self.element.get_control_binding(prop.name)
            self.__bindings_by_keyframe_button[keyframe_button] = binding
        else:
            track_element.ui_element.showDefaultKeyframes()

    def __reset_to_default_clicked_cb(self, unused_button, widget,
                                      keyframe_button=None):
        if keyframe_button:
            # The prop is controllable (keyframmable).
            binding = self.__bindings_by_keyframe_button.get(keyframe_button)
            if binding:
                # The prop has been keyframed
                binding.props.control_source.unset_all()
                if keyframe_button.get_active():
                    track_element = self.__get_track_element_of_same_type(
                        self.element)
                    if track_element:
                        track_element.ui_element.showDefaultKeyframes()
                self.__set_keyframe_active(keyframe_button, False)
                self.__display_controlled(keyframe_button, False)

        widget.setWidgetToDefault()

    def __get_track_element_of_same_type(self, effect):
        track_type = effect.get_track_type()
        for track_element in effect.get_parent().get_children(False):
            if hasattr(track_element, "ui_element") and \
                    track_element.get_track_type() == track_type:
                return track_element
        self.warning("Failed to find track element of type %s", track_type)
        return None

    def getSettings(self, with_default=False):
        """Gets a name/value dict with the properties."""
        values = {}
        for prop, widget in self.properties.items():
            if not prop.flags & GObject.ParamFlags.WRITABLE:
                continue
            value = widget.getWidgetValue()
            if value is not None and (value != prop.default_value or with_default):
                values[prop.name] = value
        return values

    def get_caps_values(self):
        values = {}
        for field, widget in self.caps_widgets.items():
            value = widget.getWidgetValue()
            if value is not None:
                values[field] = value

        return values

    def make_property_widget(self, prop, value=None):
        """Creates a widget for the specified element property."""
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
        if value is not None:
            widget.setWidgetValue(value)

        return widget

    def get_widget_of_prop(self, prop_name):
        for prop in self.properties:
            if prop.name == prop_name:
                return self.properties[prop]


class GstElementSettingsDialog(Loggable):
    """Dialog window for viewing/modifying properties of a Gst.Element."""

    def __init__(self, elementfactory, properties, parent_window=None,
                 caps=None):
        Loggable.__init__(self)
        self.debug("factory: %s, properties: %s", elementfactory, properties)

        self.factory = elementfactory
        self.element = self.factory.create("elementsettings")
        if not self.element:
            self.warning(
                "Couldn't create element from factory %s", self.factory)
        self.properties = properties
        self.__caps = caps

        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "elementsettingsdialog.ui"))
        self.builder.connect_signals(self)
        self.ok_btn = self.builder.get_object("okbutton1")

        self.window = self.builder.get_object("dialog1")
        self.elementsettings = GstElementSettingsWidget(self.element, self.properties, controllable=False)
        self.builder.get_object("viewport1").add(self.elementsettings)

        # set title and frame label
        self.window.set_title(
            _("Properties for %s") % self.factory.get_longname())

        caps_values = {}
        if self.__caps:
            element_name = None
            if isinstance(self.element, Gst.Element):
                element_name = self.element.get_factory().get_name()
            src_caps_fields = GstElementSettingsWidget.CAP_FIELDS_TO_EXPOSE.get(element_name)
            if src_caps_fields:
                for field in src_caps_fields.keys():
                    val = caps[0][field]
                    if val is not None and Gst.value_is_fixed(val):
                        caps_values[field] = val
        self.elementsettings.add_widgets(GstElementSettingsWidget.make_property_widget,
                                         with_reset_button=True,
                                         caps_values=caps_values)

        # Try to avoid scrolling, whenever possible.
        screen_height = self.window.get_screen().get_height()
        contents_height = self.elementsettings.get_preferred_size()[0].height
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

    def getSettings(self):
        """Gets the settings of the `element`.

        Returns:
            dict: A property name to value map."""
        return self.elementsettings.getSettings()

    def get_caps(self):
        values = self.elementsettings.get_caps_values()
        if self.__caps and values:
            caps = Gst.Caps(self.__caps.to_string())

            for field, value in values.items():
                caps.set_value(field, value)

            return caps
        return None

    def _resetValuesClickedCb(self, unused_button):
        self.resetAll()

    def resetAll(self):
        for prop, widget in self.elementsettings.properties.items():
            widget.setWidgetToDefault()


class ZoomBox(Gtk.Grid, Zoomable):
    """Container holding the widgets for zooming.

    Attributes:
        timeline (TimelineContainer): The timeline container this belongs to.
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
            "zoom-fit-best", Gtk.IconSize.BUTTON)
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
        self.show_all()

    def _zoomAdjustmentChangedCb(self, adjustment):
        Zoomable.setZoomLevel(adjustment.get_value())
        self.timeline.app.write_action("set-zoom-level",
                                       level=adjustment.get_value(),
                                       optional_action_type=True)

        if self._manual_set is False:
            self.timeline.timeline.scrollToPlayhead()

    def _zoomFitCb(self, unused_button):
        self.timeline.timeline.set_best_zoom_ratio(allow_zoom_in=True)

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


DROPPER_BITS = (
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377\377\377\377\377\377\377\377"
    b"\377\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377\377\0\0\0\377"
    b"\0\0\0\377\0\0\0\377\377\377\377\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377"
    b"\377\0\0\0\377\0\0\0\377\0\0\0\377\0\0\0\377\0\0\0\377\377\377\377\377"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377"
    b"\377\377\377\377\377\377\377\377\377\377\377\0\0\0\377\0\0\0\377\0\0"
    b"\0\377\0\0\0\377\0\0\0\377\377\377\377\377\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377\377\0\0\0\377\0\0\0\377\0"
    b"\0\0\377\0\0\0\377\0\0\0\377\0\0\0\377\0\0\0\377\0\0\0\377\377\377\377"
    b"\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\377\377\377\377\0\0\0\377\0\0\0\377\0\0\0\377\0\0\0\377\0\0\0\377\0"
    b"\0\0\377\377\377\377\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377\377\377\0\0\0\377\0\0"
    b"\0\377\0\0\0\377\377\377\377\377\377\377\377\377\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377"
    b"\377\377\377\377\377\377\377\377\377\377\0\0\0\377\0\0\0\377\377\377"
    b"\377\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\377\377\377\377\377\377\377\377\377\377\377\377\377"
    b"\0\0\0\377\377\377\377\377\0\0\0\377\377\377\377\377\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377\377"
    b"\377\377\377\377\377\377\377\377\377\0\0\0\377\0\0\0\0\0\0\0\0\377\377"
    b"\377\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\377\377\377\377\377\377\377\377\377\377\377\377\377\0\0\0"
    b"\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377\377\377\377\377\377\377\377"
    b"\377\377\377\0\0\0\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377\377\377"
    b"\377\377\377\377\377\377\377\377\0\0\0\377\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\377\377\377\377\377\377\377\377\377\377\377\377\377\0\0\0\377\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\377\377\377\377\377\377\377\377\0\0"
    b"\0\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\0\0\0\0\0\0\0\377\0\0\0"
    b"\377\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\377\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
    b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0")

DROPPER_WIDTH = 17
DROPPER_HEIGHT = 17
DROPPER_X_HOT = 2
DROPPER_Y_HOT = 16


class ColorPickerButton(Gtk.Button):

    # This ported ColorPickerButton borrows from deprecated GtkColorsel widget

    __gsignals__ = {
        "value-changed": (GObject.SignalFlags.RUN_LAST, None, (),),
    }

    color_r = GObject.Property(type=int, default=0)
    color_g = GObject.Property(type=int, default=0)
    color_b = GObject.Property(type=int, default=0)

    def __init__(self, r=0, g=0, b=0):
        Gtk.Button.__init__(self)
        self.color_r = r
        self.color_g = g
        self.color_b = b
        self.dropper_grab_widget = None
        self.pointer_device = None
        self.is_picking = False
        picker_image = Gtk.Image.new_from_icon_name("gtk-color-picker", Gtk.IconSize.BUTTON)
        self.set_image(picker_image)
        self.connect("clicked", self.clicked_cb)

    def clicked_cb(self, button):
        device = Gtk.get_current_event_device()
        # Allow picking color using mouse only
        if device == Gdk.InputSource.KEYBOARD:
            return
        self.pointer_device = device
        screen = self.get_screen()
        if self.dropper_grab_widget is None:
            grab_widget = Gtk.Window(Gtk.WindowType.POPUP)
            grab_widget.set_screen(screen)
            grab_widget.resize(1, 1)
            grab_widget.move(-100, -100)
            grab_widget.show()
            grab_widget.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
            top_level = self.get_toplevel()
            if isinstance(top_level, Gtk.Window):
                if top_level.has_group():
                    top_level.get_group().add_window(grab_widget)
            self.dropper_grab_widget = grab_widget

        window = self.dropper_grab_widget.get_window()
        picker_cursor = self.make_cursor_picker(screen)
        # Connect to button release event else unnecessary events are triggered
        grab_status = self.pointer_device.grab(window, Gdk.GrabOwnership.APPLICATION, False,
                                               Gdk.EventMask.BUTTON_RELEASE_MASK,
                                               picker_cursor, Gdk.CURRENT_TIME)
        if grab_status != Gdk.GrabStatus.SUCCESS:
            return
        # Start tracking the mouse events
        self.dropper_grab_widget.grab_add()
        self.dropper_grab_widget.connect("button-release-event", self.button_release_event_cb)

    def make_cursor_picker(self, screen):
        # Get color-picker cursor if it exists in the current theme else fallback to generating it ourself
        try:
            cursor = Gdk.Cursor.new_from_name(screen.get_display(), "color-picker")
        except:
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(DROPPER_BITS, GdkPixbuf.Colorspace.RGB, True, 8, DROPPER_WIDTH,
                                                    DROPPER_HEIGHT, DROPPER_WIDTH * 4)
            cursor = Gdk.Cursor.new_from_pixbuf(screen.get_display(), pixbuf, DROPPER_X_HOT, DROPPER_Y_HOT)
        return cursor

    def button_release_event_cb(self, widget, event):
        if event.button != Gdk.BUTTON_PRIMARY:
            return False
        self.grab_color_at_pointer(event.get_screen(), event.get_device(), event.x_root, event.y_root)
        self.emit("value-changed")
        self.shutdown_eyedropper()

    def grab_color_at_pointer(self, screen, device, x, y, *args):
        root_window = screen.get_root_window()
        pixbuf = Gdk.pixbuf_get_from_window(root_window, x, y, 1, 1)
        pixels = pixbuf.get_pixels()
        self.color_r = pixels[0]
        self.color_g = pixels[1]
        self.color_b = pixels[2]

    def shutdown_eyedropper(self):
        self.is_picking = False
        self.pointer_device.ungrab(Gdk.CURRENT_TIME)
        self.dropper_grab_widget.grab_remove()
        self.pointer_device = None
        self.dropper_grab_widget = None
