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
from typing import Optional
from typing import Union

from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_ui_dir
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.settings import GlobalSettings
from pitivi.undo.timeline import CommitTimelineFinalizingAction
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
        self.source: Optional[GES.TitleSource] = None
        # Whether the source's props are being set as a result of UI
        # interactions.
        self._setting_props = False
        # Whether the UI is being updated as a result of the props changes
        # performed not by this class.
        self._setting_ui = False
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
        self.outline_color_button = builder.get_object("outline_color")

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

        self.color_picker_outline_widget = ColorPickerButton()
        self.color_picker_outline_widget.show()
        self.outline_color_picker = builder.get_object("color_picker_outline")
        self.outline_color_picker.add(self.color_picker_outline_widget)
        self.color_picker_outline_widget.connect("value-changed", self._color_picker_value_changed_cb, self.outline_color_button, "outline-color")

        self.drop_shadow_checkbox = builder.get_object("check_drop_shadow")

        self.valignment_combo = builder.get_object("valignment")
        self.halignment_combo = builder.get_object("halignment")
        self.x_absolute_spin = builder.get_object("x-absolute")
        self.y_absolute_spin = builder.get_object("y-absolute")

        # TODO: Remove when we upgrade pylint https://github.com/PyCQA/pylint/issues/4962
        # pylint: disable=superfluous-parens
        for value_id, text in (("absolute", _("Absolute")),
                               ("top", _("Top")),
                               ("center", _("Center")),
                               ("bottom", _("Bottom")),
                               ("baseline", _("Baseline"))):
            self.valignment_combo.append(value_id, text)

        for value_id, text in (("absolute", _("Absolute")),
                               ("left", _("Left")),
                               ("center", _("Center")),
                               ("right", _("Right"))):
            self.halignment_combo.append(value_id, text)

        self.show_all()

    def _set_child_property(self, name, value, mergeable=False):
        with self.app.action_log.started("Title change property %s" % name,
                                         finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline),
                                         mergeable=mergeable,
                                         toplevel=True):
            self._setting_props = True
            try:
                res = self.source.set_child_property(name, value)
                assert res
            finally:
                self._setting_props = False

    def _drop_shadow_checkbox_cb(self, checkbox):
        if self._setting_ui:
            return

        active = checkbox.get_active()
        self.debug("Setting drop shadow checkbox to %s", active)
        self._set_child_property("draw-shadow", active)

    def _color_picker_value_changed_cb(self, widget, color_button, color_layer):
        if self._setting_ui:
            return

        argb = widget.calculate_argb()
        self.debug("Setting text %s to %x", color_layer, argb)
        self._set_child_property(color_layer, argb)
        rgba = argb_to_gdk_rgba(argb)
        color_button.set_rgba(rgba)

    def _background_color_button_cb(self, widget):
        if self._setting_ui:
            return

        color = gdk_rgba_to_argb(widget.get_rgba())
        self.debug("Setting title background color to %x", color)
        self._set_child_property("foreground-color", color)

    def _front_text_color_button_cb(self, widget):
        if self._setting_ui:
            return

        color = gdk_rgba_to_argb(widget.get_rgba())
        self.debug("Setting title foreground color to %x", color)
        # TODO: Use set_text_color when we work with TitleSources instead of
        # TitleClips
        self._set_child_property("color", color)

    def _front_text_outline_color_button_cb(self, widget):
        if self._setting_ui:
            return

        color = gdk_rgba_to_argb(widget.get_rgba())
        self.debug("Setting title outline color to %x", color)
        self._set_child_property("outline-color", color)

    def _font_button_cb(self, widget):
        if self._setting_ui:
            return

        font_desc = widget.get_font_desc().to_string()
        self.debug("Setting font desc to %s", font_desc)
        self._set_child_property("font-desc", font_desc)

    def __update_from_source(self, source):
        res, text = source.get_child_property("text")
        assert res
        self.textbuffer.props.text = html.unescape(text or "")

        res, x_absolute = source.get_child_property("x-absolute")
        assert res
        self.x_absolute_spin.set_value(x_absolute)

        res, y_absolute = source.get_child_property("y-absolute")
        assert res
        self.y_absolute_spin.set_value(y_absolute)

        res, valignment = source.get_child_property("valignment")
        assert res
        self.valignment_combo.set_active_id(valignment.value_name)

        res, halignment = source.get_child_property("halignment")
        assert res
        self.halignment_combo.set_active_id(halignment.value_name)

        self._update_absolute_alignment_widgets_visibility()

        res, font = source.get_child_property("font-desc")
        assert res
        font_desc = Pango.FontDescription.from_string(font)
        self.font_button.set_font_desc(font_desc)

        res, argb = source.get_child_property("color")
        assert res
        color = argb_to_gdk_rgba(argb)
        self.foreground_color_button.set_rgba(color)

        res, argb = source.get_child_property("foreground-color")
        assert res
        color = argb_to_gdk_rgba(argb)
        self.background_color_button.set_rgba(color)

        res, draw_shadow = source.get_child_property("draw-shadow")
        assert res
        self.drop_shadow_checkbox.set_active(draw_shadow)

        res, argb = source.get_child_property("outline-color")
        assert res
        color = argb_to_gdk_rgba(argb)
        self.outline_color_button.set_rgba(color)

    def _text_changed_cb(self, unused_text_buffer):
        if self._setting_ui:
            return

        escaped_text = html.escape(self.textbuffer.props.text)
        self.log("Source text updated to %s", escaped_text)
        self._set_child_property("text", escaped_text, mergeable=True)

    def _alignment_changed_cb(self, combo):
        """Handles changes in the h/v alignment widgets."""
        if self._setting_ui:
            return

        if combo == self.valignment_combo:
            prop_name = "valignment"
        else:
            prop_name = "halignment"
        value = combo.get_active_id()
        self._set_child_property(prop_name, value)

        self._update_absolute_alignment_widgets_visibility()

    def _absolute_alignment_value_changed_cb(self, spin):
        """Handles changes in the absolute alignment widgets."""
        if self._setting_ui:
            return

        if spin == self.x_absolute_spin:
            prop_name = "x-absolute"
        else:
            prop_name = "y-absolute"
        value = spin.get_value()
        self._set_child_property(prop_name, value, mergeable=True)

    def _update_absolute_alignment_widgets_visibility(self):
        visible = self.valignment_combo.get_active_id() == "absolute"
        self.y_absolute_spin.set_visible(visible)
        visible = self.halignment_combo.get_active_id() == "absolute"
        self.x_absolute_spin.set_visible(visible)

    def set_source(self, source: Optional[Union[GES.TextOverlay, GES.TitleSource]]):
        """Sets the clip to be edited with this editor.

        Args:
            source (GES.TitleSource): The source of the clip.
        """
        self.debug("Setting source to %s", source)
        if self.source:
            self.source.disconnect(self._children_props_handler)
            self._children_props_handler = None

        self.source = None

        if source:
            assert isinstance(source, (GES.TextOverlay, GES.TitleSource))
            self._setting_ui = True
            try:
                self.__update_from_source(source)
            finally:
                self._setting_ui = False
            self._children_props_handler = source.connect("deep-notify",
                                                          self._source_deep_notify_cb)
            self.source = source

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

        self._setting_ui = True
        try:
            self.__update_ui_for_prop(pspec)
        finally:
            self._setting_ui = False

        self.app.project_manager.current_project.pipeline.commit_timeline()

    def __update_ui_for_prop(self, pspec: GObject.ParamSpec):
        res, value = self.source.get_child_property(pspec.name)
        assert res, pspec.name
        if pspec.name == "text":
            text = html.unescape(value)
            if self.textbuffer.props.text == text:
                return
            self.textbuffer.props.text = text
        elif pspec.name in ["x-absolute", "y-absolute"]:
            if pspec.name == "x-absolute":
                widget = self.x_absolute_spin
            else:
                widget = self.y_absolute_spin
            if widget.get_value() == value:
                return
            widget.set_value(value)
        elif pspec.name in ["valignment", "halignment"]:
            if pspec.name == "valignment":
                widget = self.valignment_combo
            else:
                widget = self.halignment_combo
            value = value.value_name
            if widget.get_active_id() == value:
                return
            widget.set_active_id(value)
        elif pspec.name == "font-desc":
            if self.font_button.get_font_desc() == value:
                return
            font_desc = Pango.FontDescription.from_string(value)
            self.font_button.set_font_desc(font_desc)
        elif pspec.name == "color":
            color = argb_to_gdk_rgba(value)
            if color == self.foreground_color_button.get_rgba():
                return
            self.foreground_color_button.set_rgba(color)
        elif pspec.name == "foreground-color":
            color = argb_to_gdk_rgba(value)
            if color == self.background_color_button.get_rgba():
                return
            self.background_color_button.set_rgba(color)
        elif pspec.name == "outline-color":
            color = argb_to_gdk_rgba(value)
            if color == self.outline_color_button.get_rgba():
                return
            self.outline_color_button.set_rgba(color)
        elif pspec.name == "draw-shadow":
            self.drop_shadow_checkbox.set_active(value)
