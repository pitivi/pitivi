# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (C) 2020 Andrew Hazel, Thomas Braccia, Troy Ogden, Robert Kirkpatrick
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
"""Widgets to control clips properties."""
import os
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.settings import GlobalSettings
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import argb_to_gdk_rgba
from pitivi.utils.ui import gdk_rgba_to_argb
from pitivi.utils.widgets import ColorPickerButton


GlobalSettings.add_config_section("user-interface")

GlobalSettings.add_config_option("ColorClipLength",
                                 section="user-interface",
                                 key="color-clip-length",
                                 default=5000,
                                 notify=True)


class ColorProperties(Gtk.Expander, Loggable):
    """Widget for configuring the properties of a color clip."""

    def __init__(self, app):
        Gtk.Expander.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self.source = None
        self._children_props_handler = None

        self.set_label(_("Color"))
        self.set_expanded(True)

        self._create_ui()

    def _create_ui(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(), "clipcolor.ui"))
        self.builder.connect_signals(self)

        box = self.builder.get_object("color_box")
        self.add(box)

        self.color_button = self.builder.get_object("color_button")

        self.color_picker_button = ColorPickerButton()
        box.add(self.color_picker_button)
        self.color_picker_button.connect(
            "value-changed", self._color_picker_value_changed_cb)

        self.show_all()

    def _set_child_property(self, name, value):
        with self.app.action_log.started("Color change property",
                                         finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline),
                                         toplevel=True):
            res = self.source.set_child_property(name, value)
            assert res

    def _color_picker_value_changed_cb(self, widget):
        argb = widget.calculate_argb()
        self._set_child_property("foreground-color", argb)

    def _color_button_cb(self, widget):
        argb = gdk_rgba_to_argb(widget.get_rgba())
        self._set_child_property("foreground-color", argb)

    def set_source(self, source):
        """Sets the clip source to be edited with this editor.

        Args:
            source (GES.VideoTestSource): The source of the clip.
        """
        self.debug("Source set to %s", source)
        if self._children_props_handler is not None:
            self.source.disconnect(self._children_props_handler)
            self._children_props_handler = None
        self.source = None
        if source:
            assert isinstance(source, GES.VideoTestSource)
            self.source = source
            self._update_color_button()
            self._children_props_handler = self.source.connect("deep-notify",
                                                               self._source_deep_notify_cb)
        self.set_visible(bool(self.source))

    def _source_deep_notify_cb(self, source, unused_gstelement, pspec):
        """Handles updates in the VideoTestSource backing the current TestClip."""
        if pspec.name == "foreground-color":
            self._update_color_button()

    def _update_color_button(self):
        res, argb = self.source.get_child_property("foreground-color")
        assert res
        color = argb_to_gdk_rgba(argb)
        self.color_button.set_rgba(color)
