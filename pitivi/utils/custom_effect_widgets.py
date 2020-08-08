# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, Thibault Saunier <thibault.saunier@collabora.com>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Utility methods for custom effect UI."""
import os
from colorsys import rgb_to_hsv
from types import MethodType

from gi.repository import Gdk
from gi.repository import Gtk

from pitivi import configure
from pitivi.trackerperspective import EFFECT_TRACKED_OBJECT_ID_META
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import create_model
from pitivi.utils.widgets import ColorPickerButton


CUSTOM_WIDGETS_DIR = os.path.join(configure.get_ui_dir(), "customwidgets")


def setup_from_ui_file(element_setting_widget, path):
    """Creates and connects the UI for a widget."""
    # Load the ui file using builder
    builder = Gtk.Builder()
    builder.add_from_file(path)
    # Link ui widgets to the corresponding properties of the effect
    element_setting_widget.map_builder(builder)
    return builder


def create_custom_prop_widget_cb(unused_effect_prop_manager, effect_widget, effect, prop, prop_value):
    """Creates custom effect property UI."""
    effect_name = effect.get_property("bin-description")
    if effect_name == "alpha":
        return create_custom_alpha_prop_widget(effect_widget, effect, prop, prop_value)
    if effect_name == "frei0r-filter-alphaspot":
        return create_custom_alphaspot_prop_widget(effect_widget, effect, prop, prop_value)
    return None


def create_custom_widget_cb(effect_prop_manager, effect_widget, effect):
    """Creates custom effect UI."""
    tracked_object_id = effect.get_string(EFFECT_TRACKED_OBJECT_ID_META)
    if tracked_object_id:
        widget = object_cover_effect_widget(effect_prop_manager, effect_widget, effect)
        return widget

    effect_name = effect.get_property("bin-description")
    path = os.path.join(CUSTOM_WIDGETS_DIR, effect_name + ".ui")

    # Write individual effect callbacks here
    if effect_name == "alpha":
        widget = create_alpha_widget(effect_prop_manager, effect_widget, effect)
        return widget
    if effect_name == "frei0r-filter-3-point-color-balance":
        widget = create_3point_color_balance_widget(effect_prop_manager, effect_widget, effect)
        return widget
    if effect_name == "frei0r-filter-alphaspot":
        widget = create_alphaspot_widget(effect_prop_manager, effect_widget, effect)
        return widget

    # Check if there is a UI file available as a glade file
    if not os.path.isfile(path):
        return None

    # Assuming a GtkGrid called base_table exists
    builder = setup_from_ui_file(effect_widget, path)
    widget = builder.get_object("base_table")
    return widget


def object_cover_effect_widget(effect_prop_manager, element_setting_widget, element):
    """Creates the UI for the `Object cover` effect."""
    builder = setup_from_ui_file(element_setting_widget, os.path.join(CUSTOM_WIDGETS_DIR, "pitivi:object_effect.ui"))
    base_table = builder.get_object("base_table")

    def set_foreground_color(color):
        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        pipeline = effect_prop_manager.app.project_manager.current_project.pipeline
        action_log = effect_prop_manager.app.action_log
        with action_log.started("Effect property change",
                                finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                toplevel=True):
            element.set_child_property("foreground-color", color)

    def color_picker_value_changed_cb(widget: ColorPickerButton):
        """Handles the selection of a color with the color picker."""
        argb = widget.calculate_argb()
        set_foreground_color(argb)

    color_picker_button = ColorPickerButton()
    base_table.add(color_picker_button)
    handler_value_changed = color_picker_button.connect("value-changed", color_picker_value_changed_cb)

    def color_button_color_set_cb(button: Gtk.ColorButton):
        """Handles the selection of a color with the color button."""
        color = button.get_rgba()
        red = int(color.red * 255)
        green = int(color.green * 255)
        blue = int(color.blue * 255)
        argb = (0xFF << 24) + (red << 16) + (green << 8) + blue
        set_foreground_color(argb)

    color_button = builder.get_object("color_button")
    handler_color_set = color_button.connect("color-set", color_button_color_set_cb)

    def update_ui():
        res, argb = element.get_child_property("foreground-color")
        assert res
        color = Gdk.RGBA()
        color.red = ((argb >> 16) & 0xFF) / 255
        color.green = ((argb >> 8) & 0xFF) / 255
        color.blue = ((argb >> 0) & 0xFF) / 255
        color.alpha = ((argb >> 24) & 0xFF) / 255
        color_button.set_rgba(color)

    update_ui()

    def notify_foreground_color_cb(self, element, param_spec):
        color_picker_button.handler_block(handler_value_changed)
        color_button.handler_block(handler_color_set)
        try:
            update_ui()
        finally:
            color_picker_button.handler_unblock(handler_value_changed)
            color_button.handler_block(handler_color_set)

    element.connect("notify::foreground-color", notify_foreground_color_cb)

    return base_table


def create_alpha_widget(effect_prop_manager, element_setting_widget, element):
    """Creates the UI for the `alpha` effect."""
    builder = setup_from_ui_file(element_setting_widget, os.path.join(CUSTOM_WIDGETS_DIR, "alpha.ui"))

    color_picker = ColorPickerButton(0, 255, 0)
    color_picker_frame = builder.get_object("color_picker_frame")
    color_picker_frame.add(color_picker)

    # Additional Setup

    # All modes other than custom RGB chroma keying are useless to us.
    # "ALPHA_METHOD_CUSTOM" corresponds to "3"
    Loggable().debug("Setting alpha's method to 3 (custom RGB chroma keying)")
    element.set_child_property("method", 3)

    # Color button and picker has to be connected manually!

    def get_current_rgba():
        """Gets the color used by the effect."""
        color = Gdk.RGBA()
        res, red = element.get_child_property("target-r")
        assert res
        res, green = element.get_child_property("target-g")
        assert res
        res, blue = element.get_child_property("target-b")
        assert res
        color.red = red / 255
        color.green = green / 255
        color.blue = blue / 255
        return color

    def color_button_color_set_cb(color_button):
        """Handles the selection of a color with the color button."""
        color = color_button.get_rgba()
        red = int(color.red * 255)
        green = int(color.green * 255)
        blue = int(color.blue * 255)
        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        pipeline = effect_prop_manager.app.project_manager.current_project.pipeline
        action_log = effect_prop_manager.app.action_log
        with action_log.started("Effect property change",
                                finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                toplevel=True):
            element.set_child_property("target-r", red)
            element.set_child_property("target-g", green)
            element.set_child_property("target-b", blue)

    color_button = builder.get_object("colorbutton")
    color_button.connect("color-set", color_button_color_set_cb)

    def color_picker_value_changed_cb(unused_color_picker_button):
        """Handles the selection of a color with the color picker button."""
        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        pipeline = effect_prop_manager.app.project_manager.current_project.pipeline
        action_log = effect_prop_manager.app.action_log
        with action_log.started("Color Picker Change",
                                finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                toplevel=True):
            element.set_child_property("target-r", color_picker.color_r)
            element.set_child_property("target-g", color_picker.color_g)
            element.set_child_property("target-b", color_picker.color_b)

    color_picker.connect("value-changed", color_picker_value_changed_cb)

    def property_changed_cb(unused_effect, gst_element, pspec):
        """Handles the change of a GObject property."""
        if gst_element.get_control_binding(pspec.name):
            Loggable().log("%s controlled, not displaying value", pspec.name)
            return

        widget = element_setting_widget.properties.get(pspec)
        if not widget:
            return

        res, value = element_setting_widget.element.get_child_property(pspec.name)
        assert res

        if pspec.name in ("target-r", "target-g", "target-b"):
            color_button.set_rgba(get_current_rgba())
            widget.block_signals()
            try:
                widget.set_widget_value(value)
            finally:
                widget.unblock_signals()
        else:
            widget.set_widget_value(value)

    element.connect("deep-notify", property_changed_cb)

    return builder.get_object("base_table")


def create_custom_alpha_prop_widget(unused_element_setting_widget, unused_element, unused_prop, unused_prop_value):
    """Not implemented yet."""
    # In the auto-generated UI, replace a property widget with a custom one
    return None


# pylint: disable=invalid-name
def create_3point_color_balance_widget(effect_prop_manager, element_setting_widget, element):
    """Creates a widget for the `frei0r-filter-3-point-color-balance` effect."""
    ui_path = os.path.join(CUSTOM_WIDGETS_DIR, "frei0r-filter-3-point-color-balance.ui")
    builder = setup_from_ui_file(element_setting_widget, ui_path)
    element_setting_widget.map_builder(builder)
    color_balance_grid = builder.get_object("base_table")

    shadows_wheel = Gtk.HSV()
    midtones_wheel = Gtk.HSV()
    highlights_wheel = Gtk.HSV()

    color_balance_grid.attach(shadows_wheel, 1, 1, 1, 1)
    color_balance_grid.attach(midtones_wheel, 2, 1, 1, 1)
    color_balance_grid.attach(highlights_wheel, 3, 1, 1, 1)

    shadows_color_picker_button = ColorPickerButton()
    midtones_color_picker_button = ColorPickerButton()
    highlights_color_picker_button = ColorPickerButton()

    shadows_color_picker_frame = builder.get_object("shadows_color_picker_frame")
    midtones_color_picker_frame = builder.get_object("midtones_color_picker_frame")
    highlights_color_picker_frame = builder.get_object("highlights_color_picker_frame")

    shadows_color_picker_frame.add(shadows_color_picker_button)
    midtones_color_picker_frame.add(midtones_color_picker_button)
    highlights_color_picker_frame.add(highlights_color_picker_button)

    # Manually handle the custom part of the UI.
    # 1) Connecting the color wheel widgets
    # 2) Scale values between to be shown on the UI vs
    #    the actual property values (RGB values here).

    black_r = element_setting_widget.get_widget_of_prop("black-color-r")
    black_g = element_setting_widget.get_widget_of_prop("black-color-g")
    black_b = element_setting_widget.get_widget_of_prop("black-color-b")

    gray_r = element_setting_widget.get_widget_of_prop("gray-color-r")
    gray_g = element_setting_widget.get_widget_of_prop("gray-color-g")
    gray_b = element_setting_widget.get_widget_of_prop("gray-color-b")

    white_r = element_setting_widget.get_widget_of_prop("white-color-r")
    white_g = element_setting_widget.get_widget_of_prop("white-color-g")
    white_b = element_setting_widget.get_widget_of_prop("white-color-b")

    # The UI widget values need to be scaled back to the property.
    # Since for RGB values, 0-255 format is used in the UI
    # where as the property values are actually between 0-1.

    def get_widget_scaled_value(self):
        """Gets the color value for the GES element property."""
        return self.adjustment.get_value() / 255

    black_r.get_widget_value = MethodType(get_widget_scaled_value, black_r)
    black_g.get_widget_value = MethodType(get_widget_scaled_value, black_g)
    black_b.get_widget_value = MethodType(get_widget_scaled_value, black_b)

    gray_r.get_widget_value = MethodType(get_widget_scaled_value, gray_r)
    gray_g.get_widget_value = MethodType(get_widget_scaled_value, gray_g)
    gray_b.get_widget_value = MethodType(get_widget_scaled_value, gray_b)

    white_r.get_widget_value = MethodType(get_widget_scaled_value, white_r)
    white_b.get_widget_value = MethodType(get_widget_scaled_value, white_b)
    white_g.get_widget_value = MethodType(get_widget_scaled_value, white_g)

    # Update underlying GObject color properties when the color widgets change.

    def color_wheel_changed_cb(color_wheel, prop_r, prop_g, prop_b):
        """Handles the selection of a color with a color wheel."""
        hsv_color = color_wheel.get_color()
        rgb_color = color_wheel.to_rgb(hsv_color.h, hsv_color.s, hsv_color.v)
        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        pipeline = effect_prop_manager.app.project_manager.current_project.pipeline
        action_log = effect_prop_manager.app.action_log
        with action_log.started("Effect property change",
                                finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                toplevel=False):
            element.set_child_property(prop_r, rgb_color.r)
            element.set_child_property(prop_g, rgb_color.g)
            element.set_child_property(prop_b, rgb_color.b)

    shadows_wheel.connect("changed", color_wheel_changed_cb, "black-color-r", "black-color-g", "black-color-b")
    midtones_wheel.connect("changed", color_wheel_changed_cb, "gray-color-r", "gray-color-g", "gray-color-b")
    highlights_wheel.connect("changed", color_wheel_changed_cb, "white-color-r", "white-color-g", "white-color-b")

    def color_picker_value_changed_cb(color_picker_button, prop_r, prop_g, prop_b):
        """Handles the selection of a color with the color picker button."""
        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        pipeline = effect_prop_manager.app.project_manager.current_project.pipeline
        action_log = effect_prop_manager.app.action_log
        with action_log.started("Effect property change",
                                finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                toplevel=True):
            element.set_child_property(prop_r, color_picker_button.color_r / 255)
            element.set_child_property(prop_g, color_picker_button.color_g / 255)
            element.set_child_property(prop_b, color_picker_button.color_b / 255)

    shadows_color_picker_button.connect("value-changed", color_picker_value_changed_cb,
                                        "black-color-r", "black-color-g", "black-color-b")
    midtones_color_picker_button.connect("value-changed", color_picker_value_changed_cb,
                                         "gray-color-r", "gray-color-g", "gray-color-b")
    highlights_color_picker_button.connect("value-changed", color_picker_value_changed_cb,
                                           "white-color-r", "white-color-g", "white-color-b")

    def update_wheel(prop_r, prop_g, prop_b, wheel, numeric_widget, value):
        """Updates the widgets with the value from the Gst element."""
        _, r = element_setting_widget.element.get_child_property(prop_r)
        _, g = element_setting_widget.element.get_child_property(prop_g)
        _, b = element_setting_widget.element.get_child_property(prop_b)
        new_hsv = rgb_to_hsv(r, g, b)
        # GtkHSV always emits `changed` signal when set_color is used.
        # But we need to only emit it when the color has actually changed!
        current_hsv = wheel.get_color()
        if current_hsv != new_hsv:
            wheel.set_color(*new_hsv)
        numeric_widget.block_signals()
        try:
            numeric_widget.set_widget_value(round(value * 255))
        finally:
            numeric_widget.unblock_signals()

    def property_changed_cb(unused_effect, gst_element, pspec):
        """Handles the change of a GObject property."""
        if gst_element.get_control_binding(pspec.name):
            Loggable().log("%s controlled, not displaying value", pspec.name)
            return

        widget = element_setting_widget.properties.get(pspec)
        if not widget:
            return

        res, value = element_setting_widget.element.get_child_property(pspec.name)
        assert res

        if pspec.name in ("black-color-r", "black-color-g", "black-color-b"):
            update_wheel("black-color-r", "black-color-g", "black-color-b", shadows_wheel, widget, value)
        elif pspec.name in ("gray-color-r", "gray-color-g", "gray-color-b"):
            update_wheel("gray-color-r", "gray-color-g", "gray-color-b", midtones_wheel, widget, value)
        elif pspec.name in ("white-color-r", "white-color-g", "white-color-b"):
            update_wheel("white-color-r", "white-color-g", "white-color-b", highlights_wheel, widget, value)
        else:
            widget.set_widget_value(value)

    element.connect("deep-notify", property_changed_cb)

    shadows_reset_button = builder.get_object("shadows_reset_button")
    midtones_reset_button = builder.get_object("midtones_reset_button")
    highlights_reset_button = builder.get_object("highlights_reset_button")

    def reset_wheel_cb(unused_arg, wheel, value):
        """Handles the click of a reset button."""
        wheel.set_color(0, 0, value)

    shadows_reset_button.connect("clicked", reset_wheel_cb, shadows_wheel, 0)
    midtones_reset_button.connect("clicked", reset_wheel_cb, midtones_wheel, 0.5)
    highlights_reset_button.connect("clicked", reset_wheel_cb, highlights_wheel, 1)

    # Initialize the wheels with the correct values

    shadows_wheel.set_color(0, 0, 0)
    midtones_wheel.set_color(0, 0, 0.5)
    highlights_wheel.set_color(0, 0, 1)

    return color_balance_grid


def create_alphaspot_widget(effect_prop_manager, element_setting_widget, element):
    """Creates the UI for the `alpha` effect."""
    builder = setup_from_ui_file(element_setting_widget, os.path.join(CUSTOM_WIDGETS_DIR, "frei0r-filter-alphaspot.ui"))

    # Shape picker

    shape_picker = builder.get_object("frei0r-filter-alphaspot::shape")
    shape_list = create_model((str, float), [
        # ouch...
        ("rectangle", 0.0),
        ("ellipse", 0.26),
        ("triangle", 0.51),
        ("diamond shape", 0.76),
    ])
    shape_picker.set_model(shape_list)
    shape_text_renderer = Gtk.CellRendererText()
    shape_picker.pack_start(shape_text_renderer, 0)
    shape_picker.add_attribute(shape_text_renderer, "text", 0)

    def get_current_shape():
        """Gets the shape index used by the effect."""
        res, flid = element.get_child_property("shape")
        assert res
        for index, vals in reversed(list(enumerate(shape_list))):
            if flid >= vals[1]:
                return index
        raise Exception()

    shape_picker.set_active(get_current_shape())

    def shape_picker_value_changed_cb(unused):
        """Handles the selection of shape via combobox."""
        v = shape_list[shape_picker.get_active()][1]

        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        pipeline = effect_prop_manager.app.project_manager.current_project.pipeline
        action_log = effect_prop_manager.app.action_log
        with action_log.started("Effect property change",
                                finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                toplevel=True):
            element.set_child_property("shape", v)

    shape_picker.connect("changed", shape_picker_value_changed_cb)

    # Operation picker

    op_picker = builder.get_object("frei0r-filter-alphaspot::operation")
    op_list = create_model((str, float), [
        # ouch...
        ("write on clear", 0.0),
        ("max", 0.21),
        ("min", 0.41),
        ("add", 0.61),
        ("subtract", 0.81),
    ])
    op_picker.set_model(op_list)
    op_text_renderer = Gtk.CellRendererText()
    op_picker.pack_start(op_text_renderer, 0)
    op_picker.add_attribute(op_text_renderer, "text", 0)

    def get_current_op():
        """Gets the op index used by the effect."""
        res, flid = element.get_child_property("operation")
        assert res
        for index, vals in reversed(list(enumerate(op_list))):
            if flid >= vals[1]:
                return index
        raise Exception()

    op_picker.set_active(get_current_op())

    def op_picker_value_changed_cb(unused):
        """Handles the selection of op via combobox."""
        v = op_list[op_picker.get_active()][1]

        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        pipeline = effect_prop_manager.app.project_manager.current_project.pipeline
        action_log = effect_prop_manager.app.action_log
        with action_log.started("Effect property change",
                                finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                toplevel=True):
            element.set_child_property("operation", v)

    op_picker.connect("changed", op_picker_value_changed_cb)

    def property_changed_cb(unused_effect, gst_element, pspec):
        """Handles the change of a GObject property."""
        if gst_element.get_control_binding(pspec.name):
            Loggable().log("%s controlled, not displaying value", pspec.name)
            return

        widget = element_setting_widget.properties.get(pspec)
        if not widget:
            return

        res, value = element_setting_widget.element.get_child_property(pspec.name)
        assert res

        if pspec.name in ("shape",):
            shape_picker.set_active(get_current_shape())
            widget.block_signals()
            try:
                widget.set_widget_value(value)
            finally:
                widget.unblock_signals()
        elif pspec.name in ("operation",):
            op_picker.set_active(get_current_op())
            widget.block_signals()
            try:
                widget.set_widget_value(value)
            finally:
                widget.unblock_signals()
        else:
            widget.set_widget_value(value)

    element.connect("deep-notify", property_changed_cb)

    return builder.get_object("base_table")


def create_custom_alphaspot_prop_widget(unused_element_setting_widget, unused_element, unused_prop, unused_prop_value):
    """Not implemented yet."""
    # In the auto-generated UI, replace a property widget with a custom one
    return None
