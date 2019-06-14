# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
# Copyright (c) 2014, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the markers module."""
from unittest import mock

from gi.repository import Gdk
from gi.repository import Gtk

from pitivi.timeline.timeline import TimelineContainer
from pitivi.utils.timeline import Zoomable
from tests import common


class BaseTestUndoTimeline(common.TestCase):
    """Base class"""

    def setUp(self):
        """setUp method"""
        super(BaseTestUndoTimeline, self).setUp()
        self.app = common.create_pitivi()
        project = self.app.project_manager.new_blank_project()
        self.timeline = project.ges_timeline
        self.action_log = self.app.action_log
        self.timeline_container = TimelineContainer(self.app)

    def setup_timeline_container(self):
        """setup timelone method"""
        project = self.app.project_manager.current_project
        self.timeline_container.setProject(project)

        timeline = self.timeline_container.timeline
        timeline.app.project_manager.current_project = project
        timeline.get_parent = mock.MagicMock(return_value=self.timeline_container)


class TestMarkers(BaseTestUndoTimeline):
    """Class for markers tests"""

    def assert_markers(self, ges_marker_list, expected_properties):
        """Checks the actual markers with the expected markers"""
        positions = [ges_marker.props.position for ges_marker in ges_marker_list.get_markers()]
        expected_positions = [properties[0] for properties in expected_properties]
        self.assertListEqual(positions, expected_positions)

        comments = [ges_marker.get_string("comment") for ges_marker in ges_marker_list.get_markers()]
        expected_comments = [properties[1] for properties in expected_properties]
        self.assertListEqual(comments, expected_comments)

    def test_marker_added_ui(self):
        "Checks the add marker ui"
        self.setup_timeline_container()
        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers
        marker_box.markers_container = markers

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

        position = Zoomable.pixelToNs(event.x)
        self.assert_markers(markers, [(position, None)])

    def test_marker_removed_ui(self):
        "Checks the remove marker ui"
        self.setup_timeline_container()
        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers
        marker_box.markers_container = markers

        x = 200
        position = Zoomable.pixelToNs(x)
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

    def test_marker_moved_ui(self):
        "Checks the move marker ui"
        self.setup_timeline_container()
        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers
        marker_box.markers_container = markers

        x1 = 300
        position1 = Zoomable.pixelToNs(x1)
        marker = marker_box.markers_container.add(position1)
        self.assert_markers(markers, [(position1, None)])

        x2 = 400
        position2 = Zoomable.pixelToNs(x2)

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

    # pylint: disable=unbalanced-tuple-unpacking
    def test_marker_comment_ui(self):
        "Checks the comments marker ui"
        self.setup_timeline_container()
        markers = self.timeline.get_marker_list("markers")
        marker_box = self.timeline_container.markers
        marker_box.markers_container = markers

        x = 500
        position = Zoomable.pixelToNs(x)
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
