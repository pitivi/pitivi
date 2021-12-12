# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Millan Castro <m.castrovilarino@gmail.com>
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
"""Markers display and management."""
import os
from typing import Optional

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import Zoomable

TIMELINE_MARKER_SIZE = 10
CLIP_MARKER_HEIGHT = 12
CLIP_MARKER_WIDTH = 10


class Marker(Gtk.EventBox, Loggable):
    """Widget representing a marker."""

    def __init__(self, ges_marker, class_name, width, height):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK)

        self.ges_marker = ges_marker
        self.ges_marker.ui = self
        self.position_ns = self.ges_marker.props.position
        self.width = width
        self.height = height

        self.get_style_context().add_class(class_name)
        self.ges_marker.connect("notify-meta", self._notify_meta_cb)

        self._selected = False

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_get_preferred_height(self):
        return self.height, self.height

    def do_get_preferred_width(self):
        return self.width, self.width

    def do_enter_notify_event(self, unused_event):
        self.set_state_flags(Gtk.StateFlags.PRELIGHT, clear=False)

    def do_leave_notify_event(self, unused_event):
        self.unset_state_flags(Gtk.StateFlags.PRELIGHT)

    def _notify_meta_cb(self, unused_ges_marker, item, value):
        self.set_tooltip_text(self.comment)

    @property
    def position(self):
        """Returns the position of the marker, in nanoseconds."""
        return self.ges_marker.props.position

    @property
    def comment(self) -> str:
        """Returns a comment from ges_marker."""
        return self.ges_marker.get_string("comment") or ""

    @comment.setter
    def comment(self, text: str):
        if text == self.comment:
            return

        self.ges_marker.set_string("comment", text)

    @property
    def selected(self):
        """Returns whether the marker is selected."""
        return self._selected

    @selected.setter
    def selected(self, selected):
        self._selected = selected
        if self._selected:
            self.set_state_flags(Gtk.StateFlags.SELECTED, clear=False)
        else:
            self.unset_state_flags(Gtk.StateFlags.SELECTED)


class MarkersBox(Gtk.EventBox, Zoomable, Loggable):
    """Container for displaying and managing markers."""

    def __init__(self, app, hadj=None):
        Gtk.EventBox.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.layout = Gtk.Layout()
        self.add(self.layout)
        self.get_style_context().add_class("MarkersBox")

        self.app = app

        if hadj:
            hadj.connect("value-changed", self._hadj_value_changed_cb)
        self.props.hexpand = True
        self.props.valign = Gtk.Align.START

        self._offset = 0
        self.props.height_request = TIMELINE_MARKER_SIZE

        self.__markers_container: Optional[GES.MarkerList] = None
        self.marker_moving: Optional[Marker] = None
        self.marker_new: Optional[Marker] = None

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)

    def first_marker(self, before: Optional[int] = None, after: Optional[int] = None) -> Optional[int]:
        """Returns position of the closest marker found before or after the given timestamp.

        None is returned if no such marker is found.
        """
        assert (after is not None) != (before is not None)

        if not self.markers_container:
            return None

        if after is not None:
            start = after + 1
            end = self.app.project_manager.current_project.ges_timeline.props.duration
        else:
            start = 0
            end = before

        if start >= end:
            return None

        markers_positions = list(ges_marker.props.position
                                 for ges_marker in self.markers_container.get_markers()
                                 if start <= ges_marker.props.position < end)
        if not markers_positions:
            return None

        if after is not None:
            return min(markers_positions)
        else:
            return max(markers_positions)

    def add_at_timeline_time(self, position):
        """Adds a marker at the given timeline position."""
        if not self.markers_container:
            return

        self.markers_container.add(position)

    @property
    def markers_container(self):
        """Gets the GES.MarkerList."""
        return self.__markers_container

    @markers_container.setter
    def markers_container(self, ges_markers_container):
        if self.__markers_container:
            for marker in self.layout.get_children():
                self.layout.remove(marker)
            self.__markers_container.disconnect_by_func(self._marker_added_cb)
            self.__markers_container.disconnect_by_func(self._marker_removed_cb)
            self.__markers_container.disconnect_by_func(self._marker_moved_cb)

        self.__markers_container = ges_markers_container
        if self.__markers_container:
            self.__create_marker_widgets()
            self.__markers_container.connect("marker-added", self._marker_added_cb)
            self.__markers_container.connect("marker-removed", self._marker_removed_cb)
            self.__markers_container.connect("marker-moved", self._marker_moved_cb)

    def release(self):
        if self.__markers_container:
            self.__markers_container.disconnect_by_func(self._marker_added_cb)
            self.__markers_container.disconnect_by_func(self._marker_removed_cb)
            self.__markers_container.disconnect_by_func(self._marker_moved_cb)

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        if self.offset == value:
            return

        self._offset = value
        self._update_position()

    def __create_marker_widgets(self):
        markers = self.__markers_container.get_markers()

        for ges_marker in markers:
            position = ges_marker.props.position
            self._add_marker(position, ges_marker)

    def _hadj_value_changed_cb(self, hadj):
        """Handles the adjustment value change."""
        self.offset = hadj.get_value()

    def zoom_changed(self):
        self._update_position()

    def _update_position(self):
        for marker in self.layout.get_children():
            position = self.ns_to_pixel(marker.position) - self.offset - marker.width / 2
            self.layout.move(marker, position, 0)

    def do_button_press_event(self, event):
        if not self.markers_container:
            return False

        if event.button == Gdk.BUTTON_PRIMARY:
            event_widget = Gtk.get_event_widget(event)
            if isinstance(event_widget, Marker):
                if event.type == Gdk.EventType.BUTTON_PRESS:
                    self.marker_moving = event_widget
                    self.marker_moving.selected = True
                    self.app.action_log.begin("Move marker", toplevel=True)
                    return True

                if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
                    self.marker_moving = None
                    self.app.action_log.rollback()
                    marker_popover = MarkerPopover(self.app, event_widget, self.__markers_container)
                    marker_popover.popup()
                    return True

            else:
                position = self.pixel_to_ns(event.x + self.offset)
                with self.app.action_log.started("Added marker", toplevel=True):
                    self.__markers_container.add(position)
                    self.marker_new.selected = True
                return True

        return False

    def do_button_release_event(self, event):
        if not self.markers_container:
            return False

        if event.button == Gdk.BUTTON_PRIMARY:
            if self.marker_moving:
                self.marker_moving.selected = False
                self.marker_moving = None
                self.app.action_log.commit("Move marker")
                return True

            if self.marker_new:
                self.marker_new.selected = False
                self.marker_new = None
                return True

        return False

    def do_motion_notify_event(self, event):
        if not self.markers_container:
            return False

        event_widget = Gtk.get_event_widget(event)
        if event_widget is self.marker_moving:
            event_x, unused_y = event_widget.translate_coordinates(self, event.x, event.y)
            event_x = max(0, event_x)
            position_ns = self.pixel_to_ns(event_x + self.offset)
            self.__markers_container.move(self.marker_moving.ges_marker, position_ns)
            return True

        return False

    def _marker_added_cb(self, unused_markers, position, ges_marker):
        self._add_marker(position, ges_marker)

    def _create_marker(self, ges_marker):
        return Marker(ges_marker, "Marker", TIMELINE_MARKER_SIZE, TIMELINE_MARKER_SIZE)

    def _add_marker(self, position, ges_marker):
        marker = self._create_marker(ges_marker)
        x = self.ns_to_pixel(position) - self.offset - marker.width / 2
        self.layout.put(marker, x, 0)
        marker.show()
        self.marker_new = marker

    def _marker_removed_cb(self, unused_markers, ges_marker):
        self._remove_marker(ges_marker)

    def _remove_marker(self, ges_marker):
        if not ges_marker.ui:
            return

        self.layout.remove(ges_marker.ui)
        ges_marker.ui = None

    def _marker_moved_cb(
            self, unused_markers, unused_prev_position, position, ges_marker):
        self._move_marker(position, ges_marker)

    def _move_marker(self, position, ges_marker):
        x = self.ns_to_pixel(position) - self.offset - ges_marker.ui.width / 2
        self.layout.move(ges_marker.ui, x, 0)


@Gtk.Template(filename=os.path.join(get_ui_dir(), "markerpopover.ui"))
class MarkerPopover(Gtk.Popover):
    """A popover to edit a marker's metadata or to remove the marker."""

    __gtype_name__ = "MarkerPopover"

    comment_textview = Gtk.Template.Child()
    remove_button = Gtk.Template.Child()

    def __init__(self, app, marker: Marker, markers_container: GES.MarkerList):
        Gtk.Popover.__init__(self)

        self.app = app
        self.marker: Optional[Marker] = marker
        self.markers_container: GES.MarkerList = markers_container

        self.comment_textview.get_buffer().set_text(self.marker.comment)

        self.set_position(Gtk.PositionType.TOP)
        self.set_relative_to(self.marker)
        self.show_all()

    @Gtk.Template.Callback()
    def remove_button_clicked_cb(self, event):
        with self.app.action_log.started("Removed marker", toplevel=True):
            self.markers_container.remove(self.marker.ges_marker)

        self.marker = None

        self.hide()

    def do_closed(self):
        if not self.marker:
            # The user clicked the Remove button so no need to update the text.
            return

        buffer = self.comment_textview.get_buffer()
        if buffer.props.text != self.marker.comment:
            with self.app.action_log.started("marker comment", toplevel=True):
                self.marker.comment = buffer.props.text
        self.marker.selected = False


class ClipMarkersBox(MarkersBox):
    """Bar at the top of a clip for displaying and editing clip markers."""

    def __init__(self, app, ges_elem: GES.Source, hadj: Optional[Gtk.Adjustment] = None):
        MarkersBox.__init__(self, app, hadj=hadj)

        self.ges_elem = ges_elem
        # We need a GESClip to convert timestamps.
        self.ges_clip = self.ges_elem.get_parent()

        self.props.height_request = CLIP_MARKER_HEIGHT

        self.get_style_context().add_class("ClipMarkersBox")

    def _create_marker(self, ges_marker):
        return Marker(ges_marker, "ClipMarker", CLIP_MARKER_WIDTH, CLIP_MARKER_HEIGHT)

    def __internal_to_timeline(self, timestamp):
        return self.ges_clip.get_timeline_time_from_internal_time(self.ges_elem, timestamp)

    def __timeline_to_internal(self, timestamp):
        return self.ges_clip.get_internal_time_from_timeline_time(self.ges_elem, timestamp)

    def first_marker(self, before: Optional[int] = None, after: Optional[int] = None) -> Optional[int]:
        assert (after is not None) != (before is not None)

        if not self.markers_container:
            return None

        # Limit search to visible markers
        clip_start = self.ges_clip.props.start
        clip_end = self.ges_clip.props.start + self.ges_clip.props.duration

        if after is not None:
            start = max(after + 1, clip_start)
            end = clip_end
        else:
            start = clip_start
            end = min(before, clip_end)

        if start >= end:
            return None

        markers_positions = [self.__internal_to_timeline(marker.props.position)
                             for marker in self.markers_container.get_markers()
                             if start <= self.__internal_to_timeline(marker.props.position) < end]
        if not markers_positions:
            return None

        if after is not None:
            return min(markers_positions)
        else:
            return max(markers_positions)

    def add_at_timeline_time(self, position):
        if not self.markers_container:
            return

        start = self.ges_clip.props.start
        inpoint = self.ges_clip.props.in_point
        duration = self.ges_clip.props.duration

        # Prevent timestamp conversion failing due to negative result.
        if position < start:
            return

        internal_end = self.__timeline_to_internal(start + duration)
        timestamp = self.__timeline_to_internal(position)

        # Check if marker would land in the 'visible' part of the clip.
        if not inpoint <= timestamp <= internal_end:
            return

        self.markers_container.add(timestamp)

    def do_button_press_event(self, event):
        """Ignore press events unless the clip is the only one selected."""
        if not self.ges_clip.selected:
            return False

        selection = self.app.gui.editor.timeline_ui.timeline.selection
        if selection.get_single_clip() is not self.ges_clip:
            return False

        return MarkersBox.do_button_press_event(self, event)
