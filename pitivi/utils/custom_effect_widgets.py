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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
"""Utility methods for custom effect UI."""
import os

from gi.repository import Gdk
from gi.repository import Gtk

from pitivi import configure
from pitivi.utils.loggable import Loggable
from pitivi.utils.widgets import ColorPickerButton


CUSTOM_WIDGETS_DIR = os.path.join(configure.get_ui_dir(), "customwidgets")


def setup_custom_effect_widgets(effect_prop_manager):
    """Sets up the specified effects manager to be able to create custom UI."""
    effect_prop_manager.connect("create_widget", create_custom_widget_cb)
    effect_prop_manager.connect("create_property_widget", create_custom_prop_widget_cb)


def setup_from_ui_file(element_setting_widget, path):
    """Creates and connects the UI for a widget."""
    # Load the ui file using builder
    builder = Gtk.Builder()
    builder.add_from_file(path)
    # Link ui widgets to the corresponding properties of the effect
    element_setting_widget.mapBuilder(builder)
    return builder


def create_custom_prop_widget_cb(unused_effect_prop_manager, effect_widget, effect, prop, prop_value):
    """Creates custom effect property UI."""
    effect_name = effect.get_property("bin-description")
    if effect_name == "alpha":
        return create_custom_alpha_prop_widget(effect_widget, effect, prop, prop_value)


def create_custom_widget_cb(effect_prop_manager, effect_widget, effect):
    """Creates custom effect UI."""
    effect_name = effect.get_property("bin-description")
    path = os.path.join(CUSTOM_WIDGETS_DIR, effect_name + ".ui")
    if not os.path.isfile(path):
        return None

    # Write individual effect callbacks here
    if effect_name == "alpha":
        widget = create_alpha_widget(effect_prop_manager, effect_widget, effect)
        return widget

    # Check if there is a UI file available as a glade file
    # Assuming a GtkGrid called base_table exists
    builder = setup_from_ui_file(effect_widget, path)
    widget = builder.get_object("base_table")
    return widget


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
                widget.setWidgetValue(value)
            finally:
                widget.unblock_signals()
        else:
            widget.setWidgetValue(value)

    element.connect("deep-notify", property_changed_cb)

    return builder.get_object("base_table")


def create_custom_alpha_prop_widget(unused_element_setting_widget, unused_element, unused_prop, unused_prop_value):
    """Not implemented yet."""
    # In the auto-generated UI, replace a property widget with a custom one
    return None
