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

from gi.repository import Gtk

from pitivi import configure


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


def create_custom_widget_cb(unused_effect_prop_manager, effect_widget, effect):
    """Creates custom effect UI."""
    effect_name = effect.get_property("bin-description")
    path = os.path.join(CUSTOM_WIDGETS_DIR, effect_name + ".ui")
    if not os.path.isfile(path):
        return None

    # Check if there is a UI file available as a glade file
    # Assuming a GtkGrid called base_table exists
    builder = setup_from_ui_file(effect_widget, path)
    widget = builder.get_object("base_table")
    return widget


def create_alpha_widget(unused_element_setting_widget, unused_element):
    """Not implemented yet."""
    # Main alpha widget would go here
    return None


def create_custom_alpha_prop_widget(unused_element_setting_widget, unused_element, unused_prop, unused_prop_value):
    """Not implemented yet."""
    # In the auto-generated UI, replace a property widget with a custom one
    return None
