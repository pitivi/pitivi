# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2021, Tyler Senne <tsenne2@huskers.unl.edu>
# Copyright (c) 2021, Michael Ervin <michael.ervin@huskers.unl.edu>
# Copyright (c) 2021, Aaron Friesen <afriesen4@huskers.unl.edu>
# Copyright (c) 2021, Andres Ruiz <andres.ruiz3210@gmail.com>
# Copyright (c) 2021, Dalton Hulett <hulettdalton@gmail.com>
# Copyright (c) 2021, Reed Lawrence <reed.lawrence@zenofchem.com>
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
import os
from gettext import gettext as _
from typing import Iterable
from typing import Optional

from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import disconnect_all_by_func


# The threshold for the lower value of a keyframe segment to consider it a fade.
FADE_OPACITY_THRESHOLD = 0.9


class CompositingProperties(Gtk.Expander, Loggable):
    """Widget for setting the opacity and compositing properties of a clip.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app: Gtk.Application) -> None:
        Gtk.Expander.__init__(self)
        Loggable.__init__(self)

        self.app: Gtk.Application = app

        self.set_expanded(True)
        self.set_label(_("Compositing"))

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "clipcompositing.ui"))
        builder.connect_signals(self)

        compositing_box = builder.get_object("compositing_box")
        self._fade_in_adjustment = builder.get_object("fade_in_adjustment")
        self._fade_out_adjustment = builder.get_object("fade_out_adjustment")

        self._video_source: Optional[GES.VideoSource] = None
        self._control_source: Optional[Gst.ControlSource] = None

        self._fade_in: int = 0
        self._fade_out: int = 0

        self._applying_fade: bool = False
        self._updating_adjustments: bool = False

        self.blending_combo = builder.get_object("blending_mode")
        # Translators: These are compositing operators.
        # See https://www.cairographics.org/operators/ for explanation and
        # visualizations.
        for value_id, text in (("source", _("Source")),
                               ("over", _("Over")),
                               # TODO: Add back when https://gitlab.freedesktop.org/gstreamer/gstreamer/-/issues/1199 is fixed
                               # ("add", _("Add")),
                               ):
            self.blending_combo.append(value_id, text)

        self.add(compositing_box)
        compositing_box.show_all()

    def set_source(self, video_source: GES.VideoSource) -> None:
        self.debug("Source set to %s", video_source)
        if self._control_source:
            disconnect_all_by_func(self._control_source, self.__keyframe_changed_cb)
            self._video_source.disconnect_by_func(self._source_deep_notify_cb)
            self._video_source.disconnect_by_func(self.__keyframe_changed_cb)
            self._control_source = None

        self._video_source = video_source

        if self._video_source:
            assert isinstance(self._video_source, GES.VideoSource)

            control_binding = self._video_source.get_control_binding("alpha")
            assert control_binding
            self._control_source = control_binding.props.control_source
            self._control_source.connect("value-added", self.__keyframe_changed_cb)
            self._control_source.connect("value-changed", self.__keyframe_changed_cb)
            self._control_source.connect("value-removed", self.__keyframe_changed_cb)
            self._video_source.connect("notify::duration", self.__keyframe_changed_cb)
            self._update_adjustments()

            self._video_source.connect("deep-notify", self._source_deep_notify_cb)
            self._update_blending()

        self.props.visible = bool(self._video_source)

    @property
    def _duration(self) -> int:
        return self._video_source.duration

    def _update_adjustments(self) -> None:
        """Updates the UI to reflect the current opacity keyframes."""
        assert self._video_source
        assert self._control_source

        keyframes = self._control_source.get_all()
        if len(keyframes) < 2:
            self._fade_in = 0
            self._fade_out = 0
            return

        start_opacity = keyframes[0].value
        end_opacity = keyframes[-1].value

        fade_in = keyframes[-1].timestamp
        fade_out = keyframes[0].timestamp

        if len(keyframes) >= 3:
            fade_in = keyframes[1].timestamp
            fade_out = keyframes[-2].timestamp

        self._fade_in = fade_in if start_opacity <= FADE_OPACITY_THRESHOLD else 0
        self._fade_out = self._duration - fade_out if end_opacity <= FADE_OPACITY_THRESHOLD else 0

        self._updating_adjustments = True
        try:
            self._fade_in_adjustment.props.value = self._fade_in / Gst.SECOND
            self._fade_out_adjustment.props.value = self._fade_out / Gst.SECOND
        finally:
            self._updating_adjustments = False

        self._fade_in_adjustment.props.upper = (self._duration - self._fade_out) / Gst.SECOND
        self._fade_out_adjustment.props.upper = (self._duration - self._fade_in) / Gst.SECOND

    def _fade_in_adjustment_value_changed_cb(self, adjustment: Gtk.Adjustment) -> None:
        if not self._updating_adjustments:
            fade_timestamp: int = int(self._fade_in_adjustment.props.value * Gst.SECOND)
            self._move_keyframe(self._fade_in, fade_timestamp, 0, self._duration - self._fade_out)
            self._update_adjustments()

    def _fade_out_adjustment_value_changed_cb(self, adjustment: Gtk.Adjustment) -> None:
        if not self._updating_adjustments:
            fade_timestamp: int = self._duration - int(self._fade_out_adjustment.props.value * Gst.SECOND)
            self._move_keyframe(self._duration - self._fade_out, fade_timestamp, self._duration, self._fade_in)
            self._update_adjustments()

    def _reset_fade_in_clicked_cb(self, button: Gtk.Button) -> None:
        self._fade_in_adjustment.props.value = 0

    def _reset_fade_out_clicked_cb(self, button: Gtk.Button) -> None:
        self._fade_out_adjustment.props.value = 0

    def __keyframe_changed_cb(self, control_source: GstController.TimedValueControlSource, timed_value: GstController.ControlPoint) -> None:
        if not self._applying_fade:
            self._update_adjustments()

    def _get_keyframe(self, timestamp: int) -> Gst.TimedValue:
        assert self._control_source
        for keyframe in self._control_source.get_all():
            if keyframe.timestamp == timestamp:
                return keyframe
        return None

    def _get_keyframes_in_range(self, start: int, end: int) -> Iterable[Gst.TimedValue]:
        assert self._control_source
        for keyframe in self._control_source.get_all():
            if start <= keyframe.timestamp <= end:
                yield keyframe
            elif keyframe.timestamp > end:
                break

    def _move_keyframe(self, current_fade_timestamp: int, fade_timestamp: int, edge_timestamp: int, middle_timestamp: int) -> None:
        """Moves a fade keyframe.

        Args:
            current_fade_timestamp: The current position of the keyframe.
            fade_timestamp: The new position of the keyframe.
            edge_timestamp: 0 for fade-in, duration for fade-out.
            middle_timestamp: The position of the keyframe of the other fade.
        """
        if current_fade_timestamp == fade_timestamp:
            return

        assert self._video_source

        pipeline = self.app.project_manager.current_project.pipeline
        with self.app.action_log.started("apply fade",
                                         finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                         toplevel=True, mergeable=True):
            self._applying_fade = True
            try:
                keyframe = self._get_keyframe(current_fade_timestamp)
                assert keyframe
                opacity = keyframe.value

                # Unset the keyframes in the delta interval.
                start = min(current_fade_timestamp, fade_timestamp)
                end = max(current_fade_timestamp, fade_timestamp)
                for keyframe in self._get_keyframes_in_range(start, end):
                    timestamp = keyframe.timestamp
                    if 0 < timestamp < self._duration:
                        self._control_source.unset(timestamp)

                self._control_source.set(fade_timestamp, opacity)

                if current_fade_timestamp == middle_timestamp:
                    # The keyframe at current_fade_timestamp was being used for
                    # both fade-in and fade-out. Make sure it persists.
                    self._control_source.set(middle_timestamp, opacity)
                elif current_fade_timestamp == edge_timestamp:
                    # The fade has just been created.
                    # Make sure the edge keyframe is transparent.
                    self._control_source.set(edge_timestamp, 0)
            finally:
                self._applying_fade = False

    def _update_blending(self) -> None:
        res, value = self._video_source.get_child_property("operator")
        assert res
        self.blending_combo.handler_block_by_func(self._blending_property_changed_cb)
        try:
            self.blending_combo.set_active_id(value.value_nick)
        finally:
            self.blending_combo.handler_unblock_by_func(self._blending_property_changed_cb)

    def _source_deep_notify_cb(self, element: GES.TimelineElement, obj: GObject.Object, prop: GObject.ParamSpec) -> None:
        self._update_blending()

    def _blending_property_changed_cb(self, combo: Gtk.ComboBox) -> None:
        pipeline = self.app.project_manager.current_project.pipeline
        with self.app.action_log.started("set operator",
                                         finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                         toplevel=True):
            self._video_source.handler_block_by_func(self._source_deep_notify_cb)
            try:
                self._video_source.set_child_property("operator", self.blending_combo.get_active_id())
            finally:
                self._video_source.handler_unblock_by_func(self._source_deep_notify_cb)
