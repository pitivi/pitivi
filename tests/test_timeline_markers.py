# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Millan Castro <m.castrovilarino@gmail.com>
# Copyright (c) 2021, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the timeline.markers module."""
from unittest import mock

from gi.repository import Gdk
from gi.repository import Gtk

from pitivi.utils.timeline import Zoomable
from tests import common


class TestMarkers(common.TestCase):
    """Tests for markers."""

    @common.setup_timeline
    def test_marker_added_ui(self):
        """Checks the add marker UI."""
        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers

        x = 100
        event = mock.Mock(spec=Gdk.EventButton)
        event.x = x
        event.y = 1
        event.button = Gdk.BUTTON_PRIMARY

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = marker_box
            event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
            marker_box.do_button_press_event(event)
            event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_RELEASE)
            marker_box.do_button_release_event(event)

        position = Zoomable.pixel_to_ns(event.x)
        self.assert_markers(markers, [(position, None)])

    @common.setup_timeline
    def test_marker_removed_ui(self):
        """Checks the remove marker UI."""
        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers

        x = 200
        position = Zoomable.pixel_to_ns(x)
        marker = marker_box.markers_container.add(position)
        self.assert_markers(markers, [(position, None)])

        event = mock.Mock(spec=Gdk.EventButton)
        event.x = x
        event.y = 1
        event.button = Gdk.BUTTON_SECONDARY

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = marker.ui
            event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
            marker_box.do_button_press_event(event)
            event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_RELEASE)
            marker_box.do_button_release_event(event)

        self.assert_markers(markers, [])

    @common.setup_timeline
    def test_marker_moved_ui(self):
        """Checks the move marker UI."""
        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers

        x1 = 300
        position1 = Zoomable.pixel_to_ns(x1)
        marker = marker_box.markers_container.add(position1)
        self.assert_markers(markers, [(position1, None)])

        x2 = 400
        position2 = Zoomable.pixel_to_ns(x2)

        event = mock.Mock(spec=Gdk.EventButton)
        event.x = x2
        event.y = 1
        event.type = Gdk.EventType.BUTTON_PRESS
        event.button = Gdk.BUTTON_PRIMARY

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = marker.ui
            event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
            marker_box.do_button_press_event(event)

            with mock.patch.object(marker.ui, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (x2, 0)
                marker_box.do_motion_notify_event(event)
                marker_box.do_button_release_event(event)

        self.assert_markers(markers, [(position2, None)])

    @common.setup_timeline
    def test_marker_comment_ui(self):
        """Checks the comments marker UI."""
        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers

        x = 500
        position = Zoomable.pixel_to_ns(x)
        marker = marker_box.markers_container.add(position)
        self.assert_markers(markers, [(position, None)])

        event = mock.Mock(spec=Gdk.EventButton)
        event.x = x
        event.y = 1
        event.type = Gdk.EventType.BUTTON_PRESS
        event.button = Gdk.BUTTON_PRIMARY

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = marker.ui

            def popup(markerpopover):
                text_buffer = markerpopover.text_view.get_buffer()
                text_buffer.set_text("com")
                text_buffer.set_text("comment")
                markerpopover.popdown()
            original_popover_menu = Gtk.Popover.popup
            Gtk.Popover.popup = popup
            try:
                event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
                marker_box.do_button_press_event(event)
                event.guiEvent = Gdk.Event.new(Gdk.EventType.DOUBLE_BUTTON_PRESS)
                event.type = Gdk.EventType.DOUBLE_BUTTON_PRESS
                marker_box.do_button_press_event(event)
            finally:
                Gtk.Popover.popup = original_popover_menu

        stack, = self.action_log.undo_stacks
        self.assertEqual(len(stack.done_actions), 1, stack.done_actions)

        self.assert_markers(markers, [(position, "comment")])

    def check_seek(self, action, current_position, expected_position):
        pipeline = self.project.pipeline
        with mock.patch.object(pipeline, "get_position") as get_position:
            get_position.return_value = current_position
            with mock.patch.object(pipeline, "simple_seek") as simple_seek:
                action.activate()
                if expected_position is None:
                    simple_seek.assert_not_called()
                else:
                    simple_seek.assert_called_once_with(expected_position)

    @common.setup_timeline
    def test_seeking_actions(self):
        """Checks the seeking actions."""
        # The seek logic ignores the markers past the timeline duration
        # since it's not possible to seek there.
        self.add_clip(self.timeline.layers[0], start=0, duration=20)

        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers

        marker_box.markers_container.add(10)
        marker_box.markers_container.add(12)
        self.assert_markers(markers, [(10, None), (12, None)])

        self.check_seek(marker_box.seek_forward_marker_action, 9, 10)
        self.check_seek(marker_box.seek_forward_marker_action, 10, 12)
        self.check_seek(marker_box.seek_forward_marker_action, 11, 12)
        self.check_seek(marker_box.seek_forward_marker_action, 12, None)
        self.check_seek(marker_box.seek_forward_marker_action, 13, None)

        self.check_seek(marker_box.seek_backward_marker_action, 9, None)
        self.check_seek(marker_box.seek_backward_marker_action, 10, None)
        self.check_seek(marker_box.seek_backward_marker_action, 11, 10)
        self.check_seek(marker_box.seek_backward_marker_action, 12, 10)
        self.check_seek(marker_box.seek_backward_marker_action, 13, 12)
