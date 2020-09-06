# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2012, Matas Brazdeikis <matas@brazdeikis.lt>
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
"""Widgets to control title clip properties."""
import html
import os
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_ui_dir
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import argb_to_gdk_rgba
from pitivi.utils.ui import gdk_rgba_to_argb
from pitivi.utils.widgets import ColorPickerButton


GlobalSettings.add_config_option("titleClipLength",
                                 section="user-interface",
                                 key="title-clip-length",
                                 default=5000,
                                 notify=True)

PreferencesDialog.add_numeric_preference("titleClipLength",
                                         section="timeline",
                                         label=_("Title clip duration"),
                                         description=_(
                                             "Default clip length (in milliseconds) of titles when inserting on the timeline."),
                                         lower=1)


class TitleProperties(Gtk.Expander, Loggable):
    """Widget for configuring a title.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Loggable.__init__(self)
        Gtk.Expander.__init__(self)
        self.set_label(_("Title"))
        self.set_expanded(True)
        self.app = app
        self.settings = {}
        self.source = None
        self._setting_props = False
        self._children_props_handler = None

        self._create_ui()

    def _create_ui(self):
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "titleeditor.ui"))
        builder.connect_signals(self)
        # Create UI
        self.add(builder.get_object("box1"))
        self.editing_box = builder.get_object("base_table")

        self.textarea = builder.get_object("textview")

        self.textbuffer = self.textarea.props.buffer
        self.textbuffer.connect("changed", self._text_changed_cb)

        self.font_button = builder.get_object("fontbutton1")
        self.foreground_color_button = builder.get_object("fore_text_color")
        self.background_color_button = builder.get_object("back_color")

        self.color_picker_foreground_widget = ColorPickerButton()
        self.color_picker_foreground_widget.show()
        self.color_picker_foreground = builder.get_object("color_picker_foreground")
        self.color_picker_foreground.add(self.color_picker_foreground_widget)
        self.color_picker_foreground_widget.connect("value-changed", self._color_picker_value_changed_cb, self.foreground_color_button, "color")

        self.color_picker_background_widget = ColorPickerButton()
        self.color_picker_background_widget.show()
        self.background_color_picker = builder.get_object("color_picker_background")
        self.background_color_picker.add(self.color_picker_background_widget)
        self.color_picker_background_widget.connect("value-changed", self._color_picker_value_changed_cb, self.background_color_button, "foreground-color")

        for widget_id in ("valignment", "halignment", "x-absolute", "y-absolute"):
            self.settings[widget_id] = builder.get_object(widget_id)

        for value_id, text in (("absolute", _("Absolute")),
                               ("top", _("Top")),
                               ("center", _("Center")),
                               ("bottom", _("Bottom")),
                               ("baseline", _("Baseline"))):
            self.settings["valignment"].append(value_id, text)

        for value_id, text in (("absolute", _("Absolute")),
                               ("left", _("Left")),
                               ("center", _("Center")),
                               ("right", _("Right"))):
            self.settings["halignment"].append(value_id, text)

        self.show_all()

    def _set_child_property(self, name, value):
        with self.app.action_log.started("Title change property",
                                         toplevel=True):
            self._setting_props = True
            try:
                res = self.source.set_child_property(name, value)
                assert res
            finally:
                self._setting_props = False

    def _color_picker_value_changed_cb(self, widget, color_button, color_layer):
        argb = widget.calculate_argb()
        self.debug("Setting text %s to %x", color_layer, argb)
        self._set_child_property(color_layer, argb)
        rgba = argb_to_gdk_rgba(argb)
        color_button.set_rgba(rgba)

    def _background_color_button_cb(self, widget):
        color = gdk_rgba_to_argb(widget.get_rgba())
        self.debug("Setting title background color to %x", color)
        self._set_child_property("foreground-color", color)

    def _front_text_color_button_cb(self, widget):
        color = gdk_rgba_to_argb(widget.get_rgba())
        self.debug("Setting title foreground color to %x", color)
        # TODO: Use set_text_color when we work with TitleSources instead of
        # TitleClips
        self._set_child_property("color", color)

    def _font_button_cb(self, widget):
        font_desc = widget.get_font_desc().to_string()
        self.debug("Setting font desc to %s", font_desc)
        self._set_child_property("font-desc", font_desc)

    def _update_from_source(self, source):
        self.textbuffer.props.text = html.unescape(source.get_child_property("text")[1] or "")
        self.settings["x-absolute"].set_value(source.get_child_property("x-absolute")[1])
        self.settings["y-absolute"].set_value(source.get_child_property("y-absolute")[1])
        self.settings["valignment"].set_active_id(
            source.get_child_property("valignment")[1].value_name)
        self.settings["halignment"].set_active_id(
            source.get_child_property("halignment")[1].value_name)
        self._update_widgets_visibility()

        font_desc = Pango.FontDescription.from_string(
            source.get_child_property("font-desc")[1])
        self.font_button.set_font_desc(font_desc)

        color = argb_to_gdk_rgba(source.get_child_property("color")[1])
        self.foreground_color_button.set_rgba(color)

        color = argb_to_gdk_rgba(source.get_child_property("foreground-color")[1])
        self.background_color_button.set_rgba(color)

    def _text_changed_cb(self, unused_updated_obj):
        if not self.source:
            # Nothing to update.
            return

        escaped_text = html.escape(self.textbuffer.props.text)
        self.log("Source text updated to %s", escaped_text)
        self._set_child_property("text", escaped_text)

    def _update_source_cb(self, updated_obj):
        """Handles changes in the advanced property widgets at the bottom."""
        if not self.source:
            # Nothing to update.
            return

        for name, obj in list(self.settings.items()):
            if obj == updated_obj:
                if name == "valignment":
                    value = obj.get_active_id()
                    self._update_widgets_visibility()
                elif name == "halignment":
                    value = obj.get_active_id()
                    self._update_widgets_visibility()
                else:
                    value = obj.get_value()
                self._set_child_property(name, value)
                return

    def _update_widgets_visibility(self):
        visible = self.settings["valignment"].get_active_id() == "absolute"
        self.settings["y-absolute"].set_visible(visible)
        visible = self.settings["halignment"].get_active_id() == "absolute"
        self.settings["x-absolute"].set_visible(visible)

    def set_source(self, source):
        """Sets the clip to be edited with this editor.

        Args:
            source (GES.TitleSource): The source of the clip.
        """
        self.debug("Setting source to %s", source)
        if self.source:
            self.source.disconnect(self._children_props_handler)
            self._children_props_handler = None

        self.source = source

        if source:
            assert isinstance(source, (GES.TextOverlay, GES.TitleSource))
            self._update_from_source(source)
            self._children_props_handler = self.source.connect("deep-notify",
                                                               self._source_deep_notify_cb)
        self.set_visible(bool(self.source))

    def _source_deep_notify_cb(self, source, unused_gstelement, pspec):
        """Handles updates in the TitleSource backing the current TitleClip."""
        if self._setting_props:
            self.app.project_manager.current_project.pipeline.commit_timeline()
            return

        control_binding = self.source.get_control_binding(pspec.name)
        if control_binding:
            self.debug("Not handling %s as it is being interpolated",
                       pspec.name)
            return

        if pspec.name == "text":
            res, escaped_text = self.source.get_child_property(pspec.name)
            assert res, pspec.name
            text = html.unescape(escaped_text)
            if self.textbuffer.props.text == text or "":
                return
            self.textbuffer.props.text = text
        elif pspec.name in ["x-absolute", "y-absolute"]:
            res, value = self.source.get_child_property(pspec.name)
            assert res, pspec.name
            if self.settings[pspec.name].get_value() == value:
                return
            self.settings[pspec.name].set_value(value)
        elif pspec.name in ["valignment", "halignment"]:
            res, value = self.source.get_child_property(pspec.name)
            assert res, pspec.name
            value = value.value_name
            if self.settings[pspec.name].get_active_id() == value:
                return
            self.settings[pspec.name].set_active_id(value)
        elif pspec.name == "font-desc":
            res, value = self.source.get_child_property(pspec.name)
            assert res, pspec.name
            if self.font_button.get_font_desc() == value:
                return
            font_desc = Pango.FontDescription.from_string(value)
            self.font_button.set_font_desc(font_desc)
        elif pspec.name == "color":
            res, value = self.source.get_child_property(pspec.name)
            assert res, pspec.name
            color = argb_to_gdk_rgba(value)
            if color == self.foreground_color_button.get_rgba():
                return
            self.foreground_color_button.set_rgba(color)
        elif pspec.name == "foreground-color":
            res, value = self.source.get_child_property(pspec.name)
            assert res, pspec.name
            color = argb_to_gdk_rgba(value)
            if color == self.background_color_button.get_rgba():
                return
            self.background_color_button.set_rgba(color)

        self.app.project_manager.current_project.pipeline.commit_timeline()
