# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Jakub Brindza <jakub.brindza@gmail.com>
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
"""Tests for the timeline.elements module."""
# pylint: disable=protected-access,no-self-use
from unittest import mock

from gi.overrides import GObject
from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gst
from gi.repository import Gtk
from matplotlib.backend_bases import MouseButton
from matplotlib.backend_bases import MouseEvent

from pitivi.timeline.elements import GES_TYPE_UI_TYPE
from pitivi.undo.undo import UndoableActionLog
from pitivi.utils.timeline import SELECT
from pitivi.utils.timeline import UNSELECT
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import LAYER_HEIGHT
from tests import common


class TestKeyframeCurve(common.TestCase):
    """Tests for the KeyframeCurve class."""

    def test_keyframe_toggle(self):
        """Checks keyframes toggling at the playhead position."""
        timeline_container = common.create_timeline_container()
        timeline_container.app.action_log = UndoableActionLog()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        ges_clip1 = self.add_clip(ges_layer, 0, duration=Gst.SECOND)
        ges_clip2 = self.add_clip(ges_layer, Gst.SECOND, duration=Gst.SECOND)
        ges_clip3 = self.add_clip(ges_layer, 2 * Gst.SECOND, inpoint=Gst.SECOND, duration=Gst.SECOND)

        # For variety, add TitleClip to the list of clips.
        ges_clip4 = common.create_test_clip(GES.TitleClip)
        ges_clip4.props.start = 3 * Gst.SECOND
        ges_clip4.props.duration = Gst.SECOND
        self.assertTrue(ges_layer.add_clip(ges_clip4))

        self.check_keyframe_toggle(ges_clip1, timeline_container)
        self.check_keyframe_toggle(ges_clip2, timeline_container)
        self.check_keyframe_toggle(ges_clip3, timeline_container)
        self.check_keyframe_toggle(ges_clip4, timeline_container)

        self.check_keyframe_ui_toggle(ges_clip1, timeline_container)
        self.check_keyframe_ui_toggle(ges_clip2, timeline_container)
        self.check_keyframe_ui_toggle(ges_clip3, timeline_container)
        self.check_keyframe_ui_toggle(ges_clip4, timeline_container)

    def check_keyframe_toggle(self, ges_clip, timeline_container):
        """Checks keyframes toggling on the specified clip."""
        timeline = timeline_container.timeline
        pipeline = timeline._project.pipeline

        start = ges_clip.props.start
        inpoint = ges_clip.props.in_point
        duration = ges_clip.props.duration
        offsets = (1, int(duration / 2), int(duration) - 1)
        timeline.selection.select([ges_clip])

        ges_video_source = ges_clip.find_track_element(None, GES.VideoSource)
        binding = ges_video_source.get_control_binding("alpha")
        control_source = binding.props.control_source

        values = [item.timestamp for item in control_source.get_all()]
        self.assertEqual(values, [inpoint, inpoint + duration])

        # Add keyframes.
        for offset in offsets:
            position = start + offset
            pipeline.get_position = mock.Mock(return_value=position)
            timeline_container._keyframe_cb(None, None)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertIn(inpoint + offset, values)

        # Remove keyframes.
        for offset in offsets:
            position = start + offset
            pipeline.get_position = mock.Mock(return_value=position)
            timeline_container._keyframe_cb(None, None)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertNotIn(inpoint + offset, values, offset)

        # Make sure the keyframes at the start and end of the clip
        # cannot be toggled.
        for offset in [0, duration]:
            position = start + offset
            pipeline.get_position = mock.Mock(return_value=position)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertIn(inpoint + offset, values)
            timeline_container._keyframe_cb(None, None)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertIn(inpoint + offset, values)

        # Test out of clip range.
        for offset in [-1, duration + 1]:
            position = min(max(0, start + offset),
                           timeline.ges_timeline.props.duration)
            pipeline.get_position = mock.Mock(return_value=position)
            timeline_container._keyframe_cb(None, None)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertEqual(values, [inpoint, inpoint + duration])

    def check_keyframe_ui_toggle(self, ges_clip, timeline_container):
        """Checks keyframes toggling by click events."""
        timeline = timeline_container.timeline

        start = ges_clip.props.start
        start_px = Zoomable.ns_to_pixel(start)
        inpoint = ges_clip.props.in_point
        duration = ges_clip.props.duration
        duration_px = Zoomable.ns_to_pixel(duration)
        offsets_px = (1, int(duration_px / 2), int(duration_px) - 1)
        timeline.selection.select([ges_clip])

        ges_video_source = ges_clip.find_track_element(None, GES.VideoSource)
        binding = ges_video_source.get_control_binding("alpha")
        control_source = binding.props.control_source
        keyframe_curve = ges_video_source.ui.keyframe_curve

        values = [item.timestamp for item in control_source.get_all()]
        self.assertEqual(values, [inpoint, inpoint + duration])

        # Add keyframes by simulating mouse clicks.
        for offset_px in offsets_px:
            offset = Zoomable.pixel_to_ns(start_px + offset_px) - start
            xdata, ydata = inpoint + offset, 1
            x, y = keyframe_curve._ax.transData.transform((xdata, ydata))

            event = MouseEvent(
                name="button_press_event",
                canvas=keyframe_curve,
                x=x,
                y=y,
                button=1
            )
            keyframe_curve.translate_coordinates = \
                mock.Mock(return_value=(start_px + offset_px, None))

            with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
                get_event_widget.return_value = keyframe_curve
                event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
                keyframe_curve._mpl_button_press_event_cb(event)

                event.name = "button_release_event"
                event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_RELEASE)
                keyframe_curve._mpl_button_release_event_cb(event)

            values = [item.timestamp for item in control_source.get_all()]
            self.assertIn(inpoint + offset, values)

        for offset_px in offsets_px:
            offset = Zoomable.pixel_to_ns(start_px + offset_px) - start
            xdata, ydata = inpoint + offset, 1
            x, y = keyframe_curve._ax.transData.transform((xdata, ydata))

            event = MouseEvent(
                name="button_press_event",
                canvas=keyframe_curve,
                x=x,
                y=y,
                button=1
            )
            keyframe_curve.translate_coordinates = \
                mock.Mock(return_value=(start_px + offset_px, None))
            with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
                get_event_widget.return_value = keyframe_curve
                event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
                keyframe_curve._mpl_button_press_event_cb(event)

                event.name = "button_release_event"
                event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_RELEASE)
                keyframe_curve._mpl_button_release_event_cb(event)

                event.name = "button_press_event"
                event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
                keyframe_curve._mpl_button_press_event_cb(event)

                event.guiEvent = Gdk.Event.new(Gdk.EventType._2BUTTON_PRESS)
                keyframe_curve._mpl_button_press_event_cb(event)

                event.name = "button_release_event"
                event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_RELEASE)
                keyframe_curve._mpl_button_release_event_cb(event)

            values = [item.timestamp for item in control_source.get_all()]
            self.assertNotIn(inpoint + offset, values)

    def test_axis_lock(self):
        """Checks keyframes moving."""
        timeline_container = common.create_timeline_container()
        timeline_container.app.action_log = UndoableActionLog()
        timeline = timeline_container.timeline
        timeline.get_window = mock.Mock()
        pipeline = timeline._project.pipeline
        ges_layer = timeline.ges_timeline.append_layer()
        ges_clip = self.add_clip(ges_layer, 0, duration=Gst.SECOND)

        start = ges_clip.props.start
        inpoint = ges_clip.props.in_point
        duration = ges_clip.props.duration
        timeline.selection.select([ges_clip])

        ges_video_source = ges_clip.find_track_element(None, GES.VideoSource)
        binding = ges_video_source.get_control_binding("alpha")
        control_source = binding.props.control_source
        keyframe_curve = ges_video_source.ui.keyframe_curve
        values = [item.timestamp for item in control_source.get_all()]
        self.assertEqual(values, [inpoint, inpoint + duration])

        # Add a keyframe.
        position = start + int(duration / 2)
        with mock.patch.object(pipeline, "get_position") as get_position:
            get_position.return_value = position
            timeline_container._keyframe_cb(None, None)

        # Start dragging the keyframe.
        x, y = keyframe_curve._ax.transData.transform((position, 1))
        event = MouseEvent(
            name="button_press_event",
            canvas=keyframe_curve,
            x=x,
            y=y,
            button=MouseButton.LEFT
        )
        event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        self.assertIsNone(keyframe_curve._offset)
        keyframe_curve._mpl_button_press_event_cb(event)
        self.assertIsNotNone(keyframe_curve._offset)

        # Drag and make sure x and y are not locked.
        timeline_container.control_mask = False
        event = mock.Mock(
            x=x + 1,
            y=y + 1,
            xdata=position + 1,
            ydata=0.9,
        )
        with mock.patch.object(keyframe_curve,
                               "_move_keyframe") as _move_keyframe:
            keyframe_curve._mpl_motion_event_cb(event)
            # Check the keyframe is moved exactly where the cursor is.
            _move_keyframe.assert_called_once_with(position, position + 1, 0.9)

        # Drag locked horizontally.
        timeline_container.control_mask = True
        event = mock.Mock(
            x=x + 1,
            y=y + 2,
            xdata=position + 2,
            ydata=0.8,
        )
        with mock.patch.object(keyframe_curve,
                               "_move_keyframe") as _move_keyframe:
            keyframe_curve._mpl_motion_event_cb(event)
            # Check the keyframe is kept on the same timestamp.
            _move_keyframe.assert_called_once_with(position + 1, position, 0.8)

        # Drag locked vertically.
        timeline_container.control_mask = True
        event = mock.Mock(
            x=x + 2,
            y=y + 1,
            xdata=position + 3,
            ydata=0.7,
        )
        with mock.patch.object(keyframe_curve,
                               "_move_keyframe") as _move_keyframe:
            keyframe_curve._mpl_motion_event_cb(event)
            # Check the keyframe is kept on the same value.
            _move_keyframe.assert_called_once_with(position, position + 3, 1)

    def test_no_clip_selected(self):
        """Checks nothing happens when no clip is selected."""
        timeline_container = common.create_timeline_container()
        # Make sure this does not raise any exception
        timeline_container._keyframe_cb(None, None)

    def test_clip_deselect(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        ges_clip1 = self.add_clip(ges_layer, 0, duration=Gst.SECOND)
        ges_clip2 = self.add_clip(ges_layer, Gst.SECOND, duration=Gst.SECOND)

        # Select clip1 to show its keyframes widget.
        timeline.selection.select([ges_clip1])
        # Select both clips. Now clip1 still has the keyframes visible.
        timeline.selection.select([ges_clip1, ges_clip2])

        ges_video_source = ges_clip1.find_track_element(None, GES.VideoSource)
        binding = ges_video_source.get_control_binding("alpha")
        control_source = binding.props.control_source
        keyframe_curve = ges_video_source.ui.keyframe_curve

        # Simulate a mouse click.
        xdata, ydata = 1, LAYER_HEIGHT // 2
        x, y = keyframe_curve._ax.transData.transform((xdata, ydata))

        event = MouseEvent(
            name="button_press_event",
            canvas=keyframe_curve,
            x=x,
            y=y,
            button=1
        )
        keyframe_curve.translate_coordinates = mock.Mock(return_value=(1, None))

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = keyframe_curve
            event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
            keyframe_curve._mpl_button_press_event_cb(event)

            event.name = "button_release_event"
            event.guiEvent = Gdk.Event.new(Gdk.EventType.BUTTON_RELEASE)
            keyframe_curve._mpl_button_release_event_cb(event)

        self.assertListEqual([item.timestamp for item in control_source.get_all()], [0, 1000000000])


class TestVideoSource(common.TestCase):
    """Tests for the VideoSource class."""

    def test_video_source_scaling(self):
        """Checks the size of the scaled clips."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        project = timeline.app.project_manager.current_project

        clip = self.add_clips_simple(timeline, 1)[0]

        video_source = clip.find_track_element(None, GES.VideoUriSource)
        sinfo = video_source.get_asset().get_stream_info()

        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(sinfo.get_width(), 960)
        self.assertEqual(sinfo.get_height(), 400)
        self.assertEqual(project.videowidth, sinfo.get_width())
        self.assertEqual(project.videoheight, sinfo.get_height())
        self.assertEqual(project.videowidth, width)
        self.assertEqual(project.videoheight, height)

        project.set_video_properties(sinfo.get_width() * 2, sinfo.get_height() * 2, project.videorate)
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(project.videowidth, width)
        self.assertEqual(project.videoheight, height)

        # GES won't ever break aspect ratio, neither should we!
        project.set_video_properties(150, 200, project.videorate)
        self.assertEqual(video_source.get_child_property("width").value, width)
        self.assertEqual(video_source.get_child_property("height").value, height)

    def test_rotation(self):
        """Checks the size of the clips flipped 90 degrees."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline

        clip = self.add_clips_simple(timeline, 1)[0]

        video_source = clip.find_track_element(None, GES.VideoUriSource)
        sinfo = video_source.get_asset().get_stream_info()

        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(sinfo.get_width(), 960)
        self.assertEqual(sinfo.get_height(), 400)
        self.assertEqual(width, 960)
        self.assertEqual(height, 400)

        videoflip = GES.Effect.new("videoflip")
        videoflip.set_child_property("method", 1)  # clockwise

        clip.add(videoflip)
        # The video is flipped 90 degrees
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, 167)
        self.assertEqual(height, 400)

        videoflip.props.active = False
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, 960)
        self.assertEqual(height, 400)

        videoflip.props.active = True
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, 167)
        self.assertEqual(height, 400)

        clip.remove(videoflip)
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, 960)
        self.assertEqual(height, 400)

    @common.setup_project_with_clips(assets_names=["1sec_simpsons_trailer.mp4"])
    @common.setup_clipproperties
    def test_change_set_project_size(self):
        """Checks the size of the scaled clips after project settings changes."""
        clip, = self.layer.get_clips()

        def assert_child_props(clip, expectations):
            # ellipsize position in expectation means 0
            for prop in ['posx', 'posy']:
                if prop not in expectations:
                    expectations[prop] = 0
            res = {}
            for propname in expectations.keys():
                res[propname] = clip.get_child_property(propname).value
            self.assertEqual(res, expectations)

        source = clip.find_track_element(None, GES.VideoUriSource)
        sinfo = source.get_asset().get_stream_info()
        # Check that the clip has its natural size
        assert_child_props(clip, {"width": sinfo.get_width(), "height": sinfo.get_height()})

        reset_clip_properties_button = self.transformation_box.builder.get_object("clear_button")

        def check_set_pos_and_project_size(new_position, new_project_width,
                                           new_project_height, expected_position):
            self.timeline_container.timeline.selection.select([clip])
            self.transformation_box.set_source(source)
            reset_clip_properties_button.clicked()

            assert_child_props(source, {"width": self.project.videowidth, "height": self.project.videoheight})

            for propname, value in new_position.items():
                source.set_child_property(propname, value)
            self.project.set_video_properties(new_project_width, new_project_height, self.project.videorate)
            assert_child_props(source, expected_position)

        # Rescale to half the size
        check_set_pos_and_project_size(
            {},
            sinfo.get_width() / 2,
            sinfo.get_height() / 2,
            {"width": sinfo.get_width() / 2, "height": sinfo.get_height() / 2}
        )

        # Back to natural size
        check_set_pos_and_project_size(
            {},
            sinfo.get_width(),
            sinfo.get_height(),
            {"width": sinfo.get_width(), "height": sinfo.get_height()}
        )

        # Put the video in the bottom left at its half size and rescale project
        # to half, meaning video should be 1/4th of its size now
        check_set_pos_and_project_size(
            {
                "width": sinfo.get_width() / 2,
                "height": sinfo.get_height() / 2,
                "posx": sinfo.get_width() / 2,
                "posy": sinfo.get_height() / 2,
            },
            sinfo.get_width() / 2, sinfo.get_height() / 2,
            {
                "width": sinfo.get_width() / 4,
                "height": sinfo.get_height() / 4,
                "posx": sinfo.get_width() / 4,
                "posy": sinfo.get_height() / 4,
            },
        )


class TestClip(common.TestCase):
    """Tests for the Clip class."""

    def test_selection_status_persists_when_clip_changes_layer(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        selection = timeline.selection
        layer1 = timeline.ges_timeline.append_layer()
        layer2 = timeline.ges_timeline.append_layer()

        clip = self.add_clip(layer1, start=0)
        selection.set_selection([clip], SELECT)
        self.assertEqual(selection.get_single_clip(), clip)
        self.assert_clip_selected(clip, expect_selected=True)

        clip.move_to_layer_full(layer2)
        clip2, = layer2.get_clips()
        self.assert_clip_selected(clip2, expect_selected=True)

    def test_clip_subclasses(self):
        """Checks the constructors of the Clip class."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()

        for gtype, widget_class in GES_TYPE_UI_TYPE.items():
            ges_object = GObject.new(gtype)
            widget = widget_class(ges_layer.ui, ges_object)
            self.assertEqual(ges_object.ui, widget, widget_class)

    def test_mini_selection(self):
        """Checks whether both ui and mini_ui gets selected."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline

        clip1, = self.add_clips_simple(timeline, 1)

        timeline.selection.set_selection([clip1], SELECT)
        self.assertTrue(clip1.ui.get_state_flags() & Gtk.StateFlags.SELECTED)
        self.assertTrue(clip1.mini_ui.get_state_flags() & Gtk.StateFlags.SELECTED)

        timeline.selection.set_selection([clip1], UNSELECT)
        self.assertFalse(clip1.ui.get_state_flags() & Gtk.StateFlags.SELECTED)
        self.assertFalse(clip1.mini_ui.get_state_flags() & Gtk.StateFlags.SELECTED)
