# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2015, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.timeline.timeline module."""
# pylint: disable=protected-access
from unittest import mock

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.undo.timeline import TimelineObserver
from pitivi.undo.undo import UndoableActionLog
from pitivi.utils.timeline import UNSELECT
from pitivi.utils.ui import LAYER_HEIGHT
from pitivi.utils.ui import SEPARATOR_HEIGHT
from pitivi.utils.ui import URI_TARGET_ENTRY
from tests import common

THIN = LAYER_HEIGHT / 2
THICK = LAYER_HEIGHT


class TestLayers(common.TestCase):
    """Tests for the layers."""

    def test_dragging_layer(self):
        self.check_get_layer_at([THIN, THIN, THIN], 1, True,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.check_get_layer_at([THICK, THICK, THICK], 1, True,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.check_get_layer_at([THIN, THICK, THIN], 1, True,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.check_get_layer_at([THICK, THIN, THICK], 1, True,
                                [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2])

    def test_dragging_clip_from_layer(self):
        self.check_get_layer_at([THIN, THIN, THIN], 1, False,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.check_get_layer_at([THICK, THICK, THICK], 1, False,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.check_get_layer_at([THIN, THICK, THIN], 1, False,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.check_get_layer_at([THICK, THIN, THICK], 1, False,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])

    def test_dragging_clip_from_outer_space(self):
        self.check_get_layer_at([THIN, THIN, THIN], None, False,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.check_get_layer_at([THICK, THICK, THICK], None, False,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.check_get_layer_at([THIN, THICK, THIN], None, False,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.check_get_layer_at([THICK, THIN, THICK], None, False,
                                [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])

    def check_get_layer_at(self, heights, preferred, past_middle_when_adjacent, expectations):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline

        # Allocate layers
        y = 0
        for priority, height in enumerate(heights):
            ges_layer = timeline.create_layer(priority=priority)
            rect = Gdk.Rectangle()
            rect.y = y
            rect.height = height
            ges_layer.ui.set_allocation(rect)
            y += height + SEPARATOR_HEIGHT

        ges_layers = timeline.ges_timeline.get_layers()
        if preferred is None:
            preferred_ges_layer = None
        else:
            preferred_ges_layer = ges_layers[preferred]
        # The heights of the layers.
        h = [ges_layer.ui.get_allocation().height for ges_layer in ges_layers]

        def assert_layer_at(ges_layer, y):
            result = timeline.get_layer_at(
                int(y),
                prefer_ges_layer=preferred_ges_layer,
                past_middle_when_adjacent=past_middle_when_adjacent)
            self.assertEqual(
                ges_layer,
                result[0],
                "Expected %d, got %d at %d" % (ges_layers.index(ges_layer), ges_layers.index(result[0]), y))

        # y on the top layer.
        assert_layer_at(ges_layers[expectations[0]], 0)
        assert_layer_at(ges_layers[expectations[1]], h[0] / 2 - 1)
        assert_layer_at(ges_layers[expectations[2]], h[0] / 2)
        assert_layer_at(ges_layers[expectations[3]], h[0] - 1)

        # y on the separator.
        assert_layer_at(ges_layers[expectations[4]], h[0])
        assert_layer_at(ges_layers[expectations[5]], h[0] + SEPARATOR_HEIGHT - 1)

        # y on the middle layer.
        assert_layer_at(ges_layers[expectations[6]], h[0] + SEPARATOR_HEIGHT)
        assert_layer_at(ges_layers[expectations[7]], h[0] + SEPARATOR_HEIGHT + h[1] / 2 - 1)
        assert_layer_at(ges_layers[expectations[8]], h[0] + SEPARATOR_HEIGHT + h[1] / 2)
        assert_layer_at(ges_layers[expectations[9]], h[0] + SEPARATOR_HEIGHT + h[1] - 1)

        # y on the separator.
        assert_layer_at(ges_layers[expectations[10]], h[0] + SEPARATOR_HEIGHT + h[1])
        assert_layer_at(ges_layers[expectations[11]], h[0] + SEPARATOR_HEIGHT + h[1] + SEPARATOR_HEIGHT - 1)

        # y on the bottom layer.
        assert_layer_at(ges_layers[expectations[12]], h[0] + SEPARATOR_HEIGHT + h[1] + SEPARATOR_HEIGHT)
        assert_layer_at(ges_layers[expectations[13]], h[0] + SEPARATOR_HEIGHT + h[1] + SEPARATOR_HEIGHT + h[2] / 2 - 1)
        assert_layer_at(ges_layers[expectations[14]], h[0] + SEPARATOR_HEIGHT + h[1] + SEPARATOR_HEIGHT + h[2] / 2)
        assert_layer_at(ges_layers[expectations[15]], h[0] + SEPARATOR_HEIGHT + h[1] + SEPARATOR_HEIGHT + h[2] - 1)

    def test_set_separators_prelight(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        timeline.__on_separators = [mock.Mock()]
        timeline._set_separators_prelight(False)
        self.assertEqual(len(timeline.__on_separators), 1,
                         "The separators must be forgotten only in drag_end()")

    @common.setup_timeline
    def test_media_types(self):
        timeline = self.timeline_container.timeline

        ges_layer_1 = timeline.ges_timeline.append_layer()
        ges_layer_2 = timeline.ges_timeline.append_layer()

        # Timeline should contain no media_types.
        self.assertEqual(timeline.media_types, GES.TrackType(0))

        # Timeline should now contain only audio media type.
        ges_clip_audio = self.add_clip(ges_layer_1, 10, clip_type=GES.TrackType.AUDIO)
        self.assertEqual(timeline.media_types, GES.TrackType.AUDIO)

        ges_layer_1.remove_clip(ges_clip_audio)
        ges_clip_video = self.add_clip(ges_layer_2, 20, clip_type=GES.TrackType.VIDEO)
        self.assertEqual(timeline.media_types, GES.TrackType.VIDEO)

        # Timeline should contain no media_types.
        ges_layer_2.remove_clip(ges_clip_video)
        self.assertEqual(timeline.media_types, GES.TrackType(0))

        # Timeline should contain both clips.
        ges_clip_audio = self.add_clip(ges_layer_1, 10, clip_type=GES.TrackType.AUDIO)
        ges_clip_video = self.add_clip(ges_layer_2, 20, clip_type=GES.TrackType.VIDEO)
        self.assertEqual(timeline.media_types,
                         GES.TrackType.VIDEO | GES.TrackType.AUDIO)

        # Timeline should contain no clips.
        ges_layer_1.remove_clip(ges_clip_audio)
        ges_layer_2.remove_clip(ges_clip_video)
        self.assertEqual(timeline.media_types, GES.TrackType(0))

    def test_create_layer(self):
        self.check_create_layer([0, 0, 0, 0], [3, 2, 1, 0])
        self.check_create_layer([0, 1, 1, 1], [0, 3, 2, 1])
        self.check_create_layer([0, 1, 1, 2], [0, 3, 1, 2])
        self.check_create_layer([0, 1, 0, 2], [1, 3, 0, 2])
        self.check_create_layer([0, 1, 2, 3], [0, 1, 2, 3])

    def check_create_layer(self, start_priorities, expected_priorities):
        timeline = common.create_timeline_container().timeline
        ges_layers = []
        for priority in start_priorities:
            ges_layer = timeline.create_layer(priority)
            self.assertEqual(ges_layer.props.priority, priority)
            ges_layers.append(ges_layer)
        self.check_priorities_and_positions(timeline, ges_layers, expected_priorities)

    def test_remove_layer(self):
        self.check_remove_layer([0, 0, 0])
        self.check_remove_layer([0, 0, 1])
        self.check_remove_layer([0, 1, 0])
        self.check_remove_layer([0, 2, 1])
        self.check_remove_layer([1, 0, 1])
        self.check_remove_layer([2, 2, 0])
        self.check_remove_layer([3, 2, 1])

    def check_remove_layer(self, removal_order):
        timeline = common.create_timeline_container().timeline

        # Add layers to remove them later.
        ges_layers = []
        # Pitivi doesn't support removing the last remaining layer,
        # that's why we create an extra layer.
        for priority in range(len(removal_order) + 1):
            ges_layer = timeline.create_layer(priority)
            ges_layers.append(ges_layer)

        # Remove layers one by one in the specified order.
        for priority in removal_order:
            ges_layer = ges_layers[priority]
            ges_layer.control_ui.delete_layer_action.activate(None)
            ges_layers.remove(ges_layer)
            self.check_priorities_and_positions(timeline, ges_layers, list(range(len(ges_layers))))

    def test_move_layer(self):
        self.check_move_layer(0, 0, [0, 1, 2, 3, 4])
        self.check_move_layer(0, 1, [1, 0, 2, 3, 4])
        self.check_move_layer(0, 4, [4, 0, 1, 2, 3])
        self.check_move_layer(2, 0, [1, 2, 0, 3, 4])
        self.check_move_layer(2, 3, [0, 1, 3, 2, 4])
        self.check_move_layer(4, 0, [1, 2, 3, 4, 0])
        self.check_move_layer(4, 3, [0, 1, 2, 4, 3])

    def check_move_layer(self, from_priority, to_priority, expected_priorities):
        timeline = common.create_timeline_container().timeline

        # Add layers to move them later.
        ges_layers = []
        for priority in range(len(expected_priorities)):
            ges_layer = timeline.create_layer(priority)
            ges_layers.append(ges_layer)

        timeline.move_layer(ges_layers[from_priority], to_priority)
        self.check_priorities_and_positions(timeline, ges_layers, expected_priorities)


class TestGrouping(common.TestCase):

    def __check_can_group_ungroup(self, timeline_container, can_group, can_ungroup):
        self.assertEqual(timeline_container.group_action.props.enabled, can_group)
        self.assertEqual(timeline_container.ungroup_action.props.enabled, can_ungroup)

    def test_can_group_ungroup(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        # Timeline empty.
        self.__check_can_group_ungroup(timeline_container, False, False)

        ges_clip, = self.add_clips_simple(timeline, 1)
        # No clip selected.
        self.__check_can_group_ungroup(timeline_container, False, False)

        self.click_clip(ges_clip, expect_selected=True)
        # An audio-video clip is selected.
        self.__check_can_group_ungroup(timeline_container, False, True)

        timeline_container.ungroup_action.activate()
        # The resulting audio clip and video clip should both be selected.
        self.__check_can_group_ungroup(timeline_container, True, False)

        layer, = timeline.ges_timeline.get_layers()
        ges_clip0, ges_clip1 = layer.get_clips()
        self.click_clip(ges_clip0, expect_selected=False, ctrl_key=True)
        # Only one of the clips remains selected.
        self.__check_can_group_ungroup(timeline_container, False, False)

        self.click_clip(ges_clip0, expect_selected=True)
        self.click_clip(ges_clip1, expect_selected=True, ctrl_key=True)
        # Both clip are selected.
        self.__check_can_group_ungroup(timeline_container, True, False)

        timeline_container.group_action.activate()
        # The resulting audio-video clip should be selected.
        self.__check_can_group_ungroup(timeline_container, False, True)

    def group_clips(self, timeline_container, clips):
        timeline = timeline_container.timeline
        timeline.app.settings.leftClickAlsoSeeks = False

        # Select the 2 clips
        for clip in clips:
            self.assertIsNone(clip.get_parent())
            self.click_clip(clip, expect_selected=True, ctrl_key=True)

        timeline_container.group_action.activate()

        for clip in clips:
            # Check that we created a new group
            self.assertTrue(isinstance(clip.get_parent(), GES.Group))
            # The newly created group has been selected
            for selected_clip in timeline.selection:
                self.assertEqual(clip.get_toplevel_parent(), selected_clip.get_toplevel_parent())

            self.assertEqual(clips[0].get_parent(), clip.get_parent())
            self.assert_clip_selected(clip, expect_selected=True)

        group = clips[0].get_parent()
        self.assertEqual(len(group.get_children(False)), len(clips))

        self.assertEqual(len(timeline.selection), len(clips))

    def test_group(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.add_clips_simple(timeline, 2)
        self.group_clips(timeline_container, clips)

    def test_group_selection(self):
        num_clips = 2
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.add_clips_simple(timeline, num_clips)
        self.group_clips(timeline_container, clips)
        layer, = timeline.ges_timeline.get_layers()
        clips = layer.get_clips()
        self.assertEqual(len(clips), num_clips)

        # Deselect one of the clips in the group.
        self.click_clip(clips[0], expect_selected=False, ctrl_key=True)
        for clip in clips:
            self.assert_clip_selected(clip, expect_selected=False)

        # Select one of the clips in the group.
        self.click_clip(clips[0], expect_selected=True)
        for clip in clips:
            self.assert_clip_selected(clip, expect_selected=True)

    def test_group_ungroup(self):
        num_clips = 2
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.add_clips_simple(timeline, num_clips)
        self.group_clips(timeline_container, clips)

        # Selecting a clip selects all the clips in its group.
        self.click_clip(clips[0], expect_selected=True)

        timeline_container.ungroup_action.activate()
        layer = timeline.ges_timeline.get_layers()[0]
        clips = layer.get_clips()
        self.assertEqual(len(clips), num_clips)

        for clip in clips:
            self.assertIsNone(clip.get_parent())

    def test_group_splitted_clip_and_select_group(self):
        # Create a clip and select it
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.add_clips_simple(timeline, 1)
        clips[0].props.duration = timeline.ges_timeline.get_frame_time(4)
        self.click_clip(clips[0], expect_selected=True)

        # Split the clip
        position = timeline.ges_timeline.get_frame_time(2)
        timeline.ges_timeline.get_asset().pipeline.get_position = mock.Mock(return_value=position)
        timeline_container.split_action.activate()
        layer = timeline.ges_timeline.get_layers()[0]
        clips = layer.get_clips()
        self.assertEqual(len(clips), 2)

        # Only the first clip is selected
        self.assert_clip_selected(clips[0], expect_selected=True)
        self.assert_clip_selected(clips[1], expect_selected=False)

        # Select the second clip
        event = mock.Mock()
        event.keyval = Gdk.KEY_Control_L
        timeline_container.do_key_press_event(event)
        self.click_clip(clips[1], expect_selected=True)
        timeline.get_clicked_layer_and_pos = mock.Mock()
        timeline.get_clicked_layer_and_pos.return_value = (None, None)
        timeline_container.do_key_release_event(event)

        # Both clips are selected
        self.assert_clip_selected(clips[0], expect_selected=True)
        self.assert_clip_selected(clips[1], expect_selected=True)

        # Group the two selected clips
        timeline_container.group_action.activate()

        # Deselect the first clip, notice both clips have been deselected
        self.click_clip(clips[0], expect_selected=False, ctrl_key=True)
        self.assert_clip_selected(clips[1], expect_selected=False)

        # Select the first clip, notice both clips have been selected
        self.click_clip(clips[0], expect_selected=True)
        self.assert_clip_selected(clips[1], expect_selected=True)

        # Deselect the second clip, notice both clips have been deselected
        self.click_clip(clips[1], expect_selected=False, ctrl_key=True)
        self.assert_clip_selected(clips[0], expect_selected=False)

        # Select the second clip, notice both clips have been selected
        self.click_clip(clips[1], expect_selected=True)
        self.assert_clip_selected(clips[0], expect_selected=True)

    def test_ungroup_clip(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_clip, = self.add_clips_simple(timeline, 1)

        self.click_clip(ges_clip, expect_selected=True)

        timeline_container.ungroup_action.activate()
        layer = timeline.ges_timeline.get_layers()[0]
        ges_clip0, ges_clip1 = layer.get_clips()

        self.assertEqual(ges_clip0.props.start, ges_clip1.props.start)
        self.assertEqual(ges_clip0.props.duration, ges_clip1.props.duration)

        track_elem_0, = ges_clip0.get_children(recursive=False)
        track_elem_1, = ges_clip1.get_children(recursive=False)

        if track_elem_0.get_track_type() == GES.TrackType.AUDIO:
            aclip = ges_clip0.ui
            atrackelem = track_elem_0.ui
            vclip = ges_clip1.ui
            vtrackelem = track_elem_1.ui
        else:
            aclip = ges_clip1.ui
            atrackelem = track_elem_1.ui

            vclip = ges_clip0.ui
            vtrackelem = track_elem_0.ui

        self.assertEqual(aclip.audio_widget, atrackelem)
        self.assertEqual(vclip.video_widget, vtrackelem)

    def test_dragging_group_on_separator(self):
        # Create two clips on different layers and group them.
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clip1, = self.add_clips_simple(timeline, 1)
        layer1 = clip1.get_layer()

        # Add another clip on a new layer.
        clip2, = self.add_clips_simple(timeline, 1)
        self.assertEqual(len(timeline.ges_timeline.get_layers()), 2)

        self.group_clips(timeline_container, [clip1, clip2])

        # Click the first clip in the group.
        with mock.patch.object(Gtk, 'get_event_widget') as get_event_widget:
            event = mock.Mock()
            event.x = 100
            event.get_button.return_value = True, 1
            get_event_widget.return_value = clip1.ui
            timeline._button_press_event_cb(None, event)
            self.assertIsNotNone(timeline.dragging_element)

            # Move it to the right, on the separator below.
            event = mock.Mock()
            event.x = 101
            event.get_state.return_value = Gdk.ModifierType.BUTTON1_MASK
            with mock.patch.object(clip1.ui, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (40, 0)
                with mock.patch.object(timeline, "get_layer_at") as get_layer_at:
                    get_layer_at.return_value = layer1, timeline._separators[1]
                    timeline._motion_notify_event_cb(None, event)
            self.assertTrue(timeline.got_dragged)

        # Release the mouse button.
        event = mock.Mock()
        event.get_button.return_value = True, 1
        timeline._button_release_event_cb(None, event)
        self.assertEqual(len(timeline.ges_timeline.get_layers()), 2,
                         "No new layer should have been created")


class TestCutCopyPaste(common.TestCase):

    @common.setup_project_with_clips(assets_names=["mp3_sample.mp3", "tears_of_steel.webm"])
    def test_cut_paste(self):
        # Cut the clips.
        clips = self.layer.get_clips()
        for clip in clips:
            self.click_clip(clip, expect_selected=True, ctrl_key=True)
        self.timeline_container.cut_action.activate()

        # Check no clip is present.
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 0)

        # Paste the clips.
        position = 0
        self.project.pipeline.get_position = mock.Mock(return_value=position)
        self.timeline_container.paste_action.activate()

        # Check the clips are pasted at the given position and are selected.
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 2)
        self.assert_clip_selected(clips[0], expect_selected=True)
        self.assert_clip_selected(clips[1], expect_selected=True)

        first_clip_start = clips[0].props.start
        second_clip_start = clips[1].props.start
        self.assertEqual(first_clip_start, position)
        self.assertEqual(second_clip_start, position + clips[0].props.duration)

        # Cut the first clip.
        self.click_clip(clips[1], expect_selected=False, ctrl_key=True)
        # TODO: Remove this line when https://gitlab.gnome.org/GNOME/pitivi/-/issues/2433 is fixed.
        self.click_clip(clips[0], expect_selected=True)
        self.timeline_container.cut_action.activate()

        # Check only the second clip is present.
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 1)
        self.assert_clip_selected(clips[0], expect_selected=False)
        self.assertEqual(clips[0].props.start, second_clip_start)

        # Paste the clip again.
        self.project.pipeline.get_position = mock.Mock(return_value=first_clip_start)
        self.timeline_container.paste_action.activate()

        # Check both clips are present.
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 2)
        self.assert_clip_selected(clips[0], expect_selected=True)
        self.assert_clip_selected(clips[1], expect_selected=False)
        self.assertEqual(clips[0].props.start, first_clip_start)
        self.assertEqual(clips[1].props.start, second_clip_start)

    @common.setup_project_with_clips(assets_names=["mp3_sample.mp3", "tears_of_steel.webm"])
    def test_copy_paste(self):
        # Copy the clips.
        clips = self.layer.get_clips()
        for clip in clips:
            self.click_clip(clip, expect_selected=True, ctrl_key=True)
        self.timeline_container.copy_action.activate()

        # Paste the clips for the first time.
        position = self.project.pipeline.get_duration()
        self.project.pipeline.get_position = mock.Mock(return_value=position)
        self.timeline_container.paste_action.activate()

        new_clips = self.layer.get_clips()
        self.assertEqual(len(new_clips), 4)

        copied_clips = [clip for clip in new_clips if clip not in clips]
        self.assertEqual(len(copied_clips), 2)
        self.assertEqual(copied_clips[0].props.start, position, new_clips)
        self.assertEqual(copied_clips[1].props.start, position + copied_clips[0].props.duration, new_clips)

        # Paste the same clips for the second time.
        position = self.project.pipeline.get_duration()
        self.project.pipeline.get_position = mock.Mock(return_value=position)
        self.timeline_container.paste_action.activate()

        new_clips = self.layer.get_clips()
        self.assertEqual(len(new_clips), 6)

        copied_clips = [clip for clip in new_clips if clip not in clips]
        self.assertEqual(len(copied_clips), 4)
        self.assertEqual(copied_clips[2].props.start, position)
        self.assertEqual(copied_clips[3].props.start, position + copied_clips[2].props.duration)

    @common.setup_project_with_clips(assets_names=["tears_of_steel.webm"])
    def test_paste_not_possible(self):
        # Copy the clip.
        clip, = self.layer.get_clips()
        self.click_clip(clip, expect_selected=True)
        self.timeline_container.copy_action.activate()

        # Try to paste the clip at the same position.
        position = 0
        self.project.pipeline.get_position = mock.Mock(return_value=position)
        self.timeline_container.paste_action.activate()

        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 1)

    @common.setup_project_with_clips(assets_names=["tears_of_steel.webm"])
    def test_paste_selection(self):
        # Copy the clip.
        clip, = self.layer.get_clips()
        self.click_clip(clip, expect_selected=True)
        self.timeline_container.copy_action.activate()

        # Paste the clip.
        position = self.project.pipeline.get_duration()
        self.project.pipeline.get_position = mock.Mock(return_value=position)
        self.timeline_container.paste_action.activate()

        clips = self.layer.get_clips()
        self.assert_clip_selected(clips[0], expect_selected=False)
        self.assert_clip_selected(clips[1], expect_selected=True)

        # Add the first clip to the selection.
        self.click_clip(clips[0], expect_selected=True, ctrl_key=True)
        self.timeline_container.copy_action.activate()

        # Paste both clips.
        position = self.project.pipeline.get_duration()
        self.project.pipeline.get_position = mock.Mock(return_value=position)
        self.timeline_container.paste_action.activate()

        clips = self.layer.get_clips()
        self.assert_clip_selected(clips[0], expect_selected=False)
        self.assert_clip_selected(clips[1], expect_selected=False)
        self.assert_clip_selected(clips[2], expect_selected=True)
        self.assert_clip_selected(clips[3], expect_selected=True)

    @common.setup_project_with_clips(assets_names=["tears_of_steel.webm"])
    def test_actions_enabled_status(self):
        # Check status after the initialization.
        self.assertFalse(self.timeline_container.cut_action.props.enabled)
        self.assertFalse(self.timeline_container.copy_action.props.enabled)
        self.assertFalse(self.timeline_container.paste_action.props.enabled)

        # Check status after selecting the clip.
        clip, = self.layer.get_clips()
        self.click_clip(clip, expect_selected=True)

        self.assertTrue(self.timeline_container.cut_action.props.enabled)
        self.assertTrue(self.timeline_container.copy_action.props.enabled)
        self.assertFalse(self.timeline_container.paste_action.props.enabled)

        # Check status after copying the clip.
        self.timeline_container.copy_action.activate()

        self.assertTrue(self.timeline_container.cut_action.props.enabled)
        self.assertTrue(self.timeline_container.copy_action.props.enabled)
        self.assertTrue(self.timeline_container.paste_action.props.enabled)

        # Check status after cutting the clip.
        self.timeline_container.cut_action.activate()

        self.assertFalse(self.timeline_container.cut_action.props.enabled)
        self.assertFalse(self.timeline_container.copy_action.props.enabled)
        self.assertTrue(self.timeline_container.paste_action.props.enabled)

        # Check status after pasting the clip.
        position = 0
        self.project.pipeline.get_position = mock.Mock(return_value=position)
        self.timeline_container.paste_action.activate()

        self.assertTrue(self.timeline_container.cut_action.props.enabled)
        self.assertTrue(self.timeline_container.copy_action.props.enabled)
        self.assertTrue(self.timeline_container.paste_action.props.enabled)

        # Check status after deleting the clip.
        self.timeline_container.delete_action.activate()

        self.assertFalse(self.timeline_container.cut_action.props.enabled)
        self.assertFalse(self.timeline_container.copy_action.props.enabled)
        self.assertTrue(self.timeline_container.paste_action.props.enabled)


class TestEditing(common.TestCase):

    def test_trimming_on_layer_separator(self):
        # Create a clip
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clip, = self.add_clips_simple(timeline, 1)
        layer = clip.get_layer()

        # Click the right trim handle of the clip.
        with mock.patch.object(Gtk, 'get_event_widget') as get_event_widget:
            event = mock.Mock()
            event.x = 100
            event.get_button.return_value = True, 1
            get_event_widget.return_value = clip.ui.right_handle
            timeline._button_press_event_cb(None, event)
            self.assertIsNotNone(timeline.dragging_element)

            # Drag it to the left, on the separator below.
            event = mock.Mock()
            event.x = 99
            event.get_state.return_value = Gdk.ModifierType.BUTTON1_MASK
            with mock.patch.object(clip.ui.right_handle, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (0, 0)
                with mock.patch.object(timeline, "get_layer_at") as get_layer_at:
                    get_layer_at.return_value = layer, timeline._separators[1]
                    timeline._motion_notify_event_cb(None, event)
            self.assertTrue(timeline.got_dragged)

        # Release the mouse button.
        event = mock.Mock()
        event.get_button.return_value = True, 1
        timeline._button_release_event_cb(None, event)
        self.assertEqual(len(timeline.ges_timeline.get_layers()), 1,
                         "No new layer should have been created")


class TestClipsSelection(common.TestCase):

    def __reset_clips_selection(self, timeline):
        """Unselects all clips in the timeline."""
        layers = timeline.ges_timeline.get_layers()
        for layer in layers:
            clips = layer.get_clips()
            timeline.selection.set_selection(clips, UNSELECT)
            timeline.set_selection_meta_info(layer, 0, UNSELECT)

    def __check_selected(self, selected_clips, not_selected_clips):
        for clip in selected_clips:
            self.assert_clip_selected(clip, expect_selected=True)
        for clip in not_selected_clips:
            self.assert_clip_selected(clip, expect_selected=False)

    def __check_simple(self, left_click_also_seeks):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        timeline.app.settings.leftClickAlsoSeeks = left_click_also_seeks
        ges_layer = timeline.ges_timeline.append_layer()
        asset = GES.UriClipAsset.request_sync(
            common.get_sample_uri("1sec_simpsons_trailer.mp4"))
        ges_clip1 = ges_layer.add_asset(asset, 0 * Gst.SECOND, 0,
                                        1 * Gst.SECOND, GES.TrackType.UNKNOWN)
        ges_clip2 = ges_layer.add_asset(asset, 1 * Gst.SECOND, 0,
                                        1 * Gst.SECOND, GES.TrackType.UNKNOWN)

        event = mock.Mock()
        event.get_button.return_value = (True, 1)
        timeline._seek = mock.Mock()
        timeline._seek.return_value = True
        timeline.get_clicked_layer_and_pos = mock.Mock()

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = timeline

            # Simulate click on first and shift+click on second clip.
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 0.5 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_parent().shift_mask = True
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 1.5 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip1, ges_clip2], [])

    def test_simple(self):
        self.__check_simple(left_click_also_seeks=False)
        self.__check_simple(left_click_also_seeks=True)

    def __check_shift_selection_single_layer(self, left_click_also_seeks):
        """Checks group clips selection across a single layer."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        timeline.app.settings.leftClickAlsoSeeks = left_click_also_seeks
        ges_layer = timeline.ges_timeline.append_layer()
        ges_clip1 = self.add_clip(ges_layer, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip2 = self.add_clip(ges_layer, 15 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip3 = self.add_clip(ges_layer, 25 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip4 = self.add_clip(ges_layer, 35 * Gst.SECOND, duration=2 * Gst.SECOND)

        event = mock.Mock()
        event.get_button.return_value = (True, 1)
        timeline.get_parent().shift_mask = True
        timeline._seek = mock.Mock()
        timeline._seek.return_value = True
        timeline.get_clicked_layer_and_pos = mock.Mock()

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = timeline

            # Simulate shift+click before first and on second clip.
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 1 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 17 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip1, ges_clip2], [ges_clip3, ges_clip4])
            self.__reset_clips_selection(timeline)

            # Simiulate shift+click before first and after fourth clip.
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 1 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 39 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip1, ges_clip2, ges_clip3, ges_clip4], [])
            self.__reset_clips_selection(timeline)

            # Simiulate shift+click on first, after fourth and before third clip.
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 6 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 40 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 23 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip1, ges_clip2], [ges_clip3, ges_clip4])
            self.__reset_clips_selection(timeline)

            # Simulate shift+click twice on the same clip.
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 6 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer, 6.5 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip1], [ges_clip2, ges_clip3, ges_clip4])

    def test_shift_selection_single_layer(self):
        self.__check_shift_selection_single_layer(left_click_also_seeks=False)
        self.__check_shift_selection_single_layer(left_click_also_seeks=True)

    def __check_shift_selection_multiple_layers(self, left_click_also_seeks):
        """Checks group clips selection across multiple layers."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        timeline.app.settings.leftClickAlsoSeeks = left_click_also_seeks
        ges_layer1 = timeline.ges_timeline.append_layer()
        ges_clip11 = self.add_clip(ges_layer1, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip12 = self.add_clip(ges_layer1, 15 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip13 = self.add_clip(ges_layer1, 25 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_layer2 = timeline.ges_timeline.append_layer()
        ges_clip21 = self.add_clip(ges_layer2, 0 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip22 = self.add_clip(ges_layer2, 6 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip23 = self.add_clip(ges_layer2, 21 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_layer3 = timeline.ges_timeline.append_layer()
        ges_clip31 = self.add_clip(ges_layer3, 3 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip32 = self.add_clip(ges_layer3, 10 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip33 = self.add_clip(ges_layer3, 18 * Gst.SECOND, duration=2 * Gst.SECOND)

        event = mock.Mock()
        event.get_button.return_value = (True, 1)
        timeline.get_parent().shift_mask = True
        timeline._seek = mock.Mock()
        timeline._seek.return_value = True
        timeline.get_clicked_layer_and_pos = mock.Mock()

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = timeline

            timeline.get_clicked_layer_and_pos.return_value = (ges_layer2, 3 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer1, 9 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip11, ges_clip22],
                                  [ges_clip12, ges_clip13, ges_clip21, ges_clip23, ges_clip31, ges_clip32, ges_clip33])
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer3, 12 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip22, ges_clip31, ges_clip32],
                                  [ges_clip11, ges_clip12, ges_clip13, ges_clip21, ges_clip23, ges_clip33])
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer1, 22 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip11, ges_clip12, ges_clip22, ges_clip23],
                                  [ges_clip13, ges_clip21, ges_clip31, ges_clip32, ges_clip33])
            self.__reset_clips_selection(timeline)

            timeline.get_clicked_layer_and_pos.return_value = (ges_layer1, 3 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer2, 26 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip11, ges_clip12, ges_clip13, ges_clip22, ges_clip23],
                                  [ges_clip21, ges_clip31, ges_clip32, ges_clip33])
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer3, 30 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip11, ges_clip12, ges_clip13, ges_clip22, ges_clip23,
                                   ges_clip31, ges_clip32, ges_clip33],
                                  [ges_clip21])

    def test_shift_selection_multiple_layers(self):
        self.__check_shift_selection_multiple_layers(left_click_also_seeks=False)
        self.__check_shift_selection_multiple_layers(left_click_also_seeks=True)

    def test_clip_unselection(self):
        """Tests whether the clips are unselected properly."""
        timeline = common.create_timeline_container().timeline

        clip1, clip2 = self.add_clips_simple(timeline, 2)
        self.click_clip(clip1, expect_selected=True, ctrl_key=True)
        self.click_clip(clip2, expect_selected=True, ctrl_key=True)
        self.__check_selected([clip1, clip2], [])

        # Unselect clip2.
        self.click_clip(clip2, expect_selected=False, ctrl_key=True)
        self.__check_selected([clip1], [clip2])

    def test_grouped_clips_unselection(self):
        """Tests grouped clips are unselected together."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline

        clip1, clip2, clip3 = self.add_clips_simple(timeline, 3)
        self.click_clip(clip1, expect_selected=True, ctrl_key=True)
        self.click_clip(clip2, expect_selected=True, ctrl_key=True)
        timeline_container.group_action.activate()

        self.click_clip(clip3, expect_selected=True, ctrl_key=True)
        self.__check_selected([clip1, clip2, clip3], [])

        # Unselect the group.
        self.click_clip(clip1, expect_selected=False, ctrl_key=True)
        self.__check_selected([clip3], [clip1, clip2])


class TestTimelineContainer(common.TestCase):
    """Tests for the TimelineContainer class."""

    def test_update_clips_asset(self):
        timeline_container = common.create_timeline_container()
        mainloop = common.create_main_loop()
        mainloop.run(until_empty=True)
        ges_timeline = timeline_container.ges_timeline
        layer, = ges_timeline.get_layers()
        title_clip = GES.TitleClip()
        title_clip.props.duration = 100
        layer.add_clip(title_clip)
        self.assertListEqual(list(timeline_container.timeline.clips()), [title_clip])

        # Check the title clips are ignored.
        timeline_container.update_clips_asset(mock.Mock())


class TestClipsEdges(common.TestCase):

    def test_clips_edges(self):
        """Test function for function clips_edges."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.add_clips_simple(timeline, 5)
        timeline.ges_timeline.layers[0].remove_clip(clips[0])
        self.add_clip(timeline.ges_timeline.layers[0], 5, 0, 10)

        self.assertEqual(timeline_container.first_clip_edge(after=0), 5)
        self.assertEqual(timeline_container.first_clip_edge(after=9), 10)
        self.assertEqual(timeline_container.first_clip_edge(after=10), 15)
        self.assertEqual(timeline_container.first_clip_edge(after=48), 50)
        self.assertEqual(timeline_container.first_clip_edge(after=49), 50)

        self.assertEqual(timeline_container.first_clip_edge(before=0), None)
        self.assertEqual(timeline_container.first_clip_edge(before=1), 0)
        self.assertEqual(timeline_container.first_clip_edge(before=9), 5)
        self.assertEqual(timeline_container.first_clip_edge(before=10), 5)
        self.assertEqual(timeline_container.first_clip_edge(before=11), 10)
        self.assertEqual(timeline_container.first_clip_edge(before=20), 15)


class TestDragFromOutside(common.TestCase):

    def setUp(self):
        super().setUp()

        timeline_container = common.create_timeline_container()
        self.ges_timeline = timeline_container.timeline.ges_timeline

        timeline_container.app.action_log = UndoableActionLog()
        self.timeline_observer = TimelineObserver(timeline_container.ges_timeline, timeline_container.app.action_log)

    def check_drag_assets_to_timeline(self, timeline_ui, assets):
        # Events emitted while dragging assets over a clip in the timeline:
        # motion, receive, motion.
        with mock.patch.object(Gdk, "drag_status") as _drag_status_mock:
            with mock.patch.object(Gtk, "drag_finish") as _drag_finish_mock:
                target = mock.Mock()
                target.name.return_value = URI_TARGET_ENTRY.target
                timeline_ui.drag_dest_find_target = mock.Mock(return_value=target)
                timeline_ui.drag_get_data = mock.Mock()
                timeline_ui._drag_motion_cb(None, None, 0, 0, 0)
                self.assertTrue(timeline_ui.drag_get_data.called)

                self.assertFalse(timeline_ui.drop_data_ready)
                selection_data = mock.Mock()
                selection_data.get_data_type = mock.Mock(return_value=target)
                selection_data.get_uris.return_value = [asset.props.id for asset in assets]
                self.assertIsNone(timeline_ui.drop_data)
                self.assertFalse(timeline_ui.drop_data_ready)
                timeline_ui._drag_data_received_cb(None, None, 0, 0, selection_data, None, 0)
                self.assertEqual(timeline_ui.drop_data, [asset.props.id for asset in assets])
                self.assertTrue(timeline_ui.drop_data_ready)

                timeline_ui.drag_get_data.reset_mock()
                self.assertIsNone(timeline_ui.dragging_element)
                self.assertFalse(timeline_ui.dropping_clips)

                # Drag on the first layer.
                def translate_coordinates_func(widget, x, y):
                    return x, y
                timeline_ui.translate_coordinates = translate_coordinates_func
                timeline_ui._drag_motion_cb(timeline_ui, None, 0, SEPARATOR_HEIGHT, 0)
                self.assertFalse(timeline_ui.drag_get_data.called)
                self.assertIsNone(timeline_ui.dragging_element)
                self.assertFalse(timeline_ui.dropping_clips)

    def test_adding_overlap_clip(self):
        """Checks asset drag&drop on top of an existing clip."""
        asset = GES.UriClipAsset.request_sync(
            common.get_sample_uri("tears_of_steel.webm"))

        layer, = self.ges_timeline.get_layers()
        layer.add_asset(asset, 0, 0, 10, GES.TrackType.UNKNOWN)
        clips = layer.get_clips()

        self.check_drag_assets_to_timeline(self.ges_timeline.ui, [asset])
        self.assertEqual(layer.get_clips(), clips)

    def test_dragging_multiple_clips_over_timeline(self):
        """Checks drag&drop two assets when only the first one can be placed."""
        asset = GES.UriClipAsset.request_sync(
            common.get_sample_uri("tears_of_steel.webm"))

        layer, = self.ges_timeline.get_layers()
        start = asset.get_duration()
        layer.add_asset(asset, start, 0, 10, GES.TrackType.UNKNOWN)
        clips = layer.get_clips()

        # Use same asset to mimic dragging multiple assets
        self.check_drag_assets_to_timeline(self.ges_timeline.ui, [asset, asset])
        self.assertEqual(layer.get_clips(), clips)


class TestKeyboardShiftClips(common.TestCase):

    def check_frame_shift_clips(self, *ges_clips):
        """Checks that clips shifted forwards then backwards work properly."""
        clip_original_starts = [clip.start for clip in ges_clips]
        delta = self.timeline.get_frame_time(1)

        event = mock.Mock()
        event.keyval = Gdk.KEY_Control_L
        self.timeline_container.do_key_press_event(event)
        for clip in ges_clips:
            self.click_clip(clip, expect_selected=True)
        self.timeline_container.do_key_release_event(event)

        self.timeline_container.shift_forward_action.activate()
        self.assertListEqual([clip.start - delta for clip in ges_clips], clip_original_starts)

        self.timeline_container.shift_backward_action.activate()
        self.assertListEqual([clip.start for clip in ges_clips], clip_original_starts)

    @common.setup_project(["tears_of_steel.webm"])
    def test_clip_shift(self):
        """Checks that shift methods change position of a single clip by one frame."""
        ges_clip1 = self.add_clip(self.layer, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        self.check_frame_shift_clips(ges_clip1)

    @common.setup_project(["tears_of_steel.webm"])
    def test_shift_disjoint_clips(self):
        """Checks that disjoint clips are able to be shifted."""
        ges_clip1 = self.add_clip(self.layer, 5 * Gst.SECOND, duration=1 * Gst.SECOND)
        ges_clip2 = self.add_clip(self.layer, 9 * Gst.SECOND, duration=1 * Gst.SECOND)
        self.check_frame_shift_clips(ges_clip1, ges_clip2)

    @common.setup_project(["tears_of_steel.webm"])
    def test_shift_adjacent_clips(self):
        """Checks that adjacent clips are able to be shifted as well."""
        ges_clip1 = self.add_clip(self.layer, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip2 = self.add_clip(self.layer, 7 * Gst.SECOND, duration=2 * Gst.SECOND)
        self.check_frame_shift_clips(ges_clip1, ges_clip2)

    @common.setup_project(["tears_of_steel.webm"])
    def test_triple_overlap_causes_rollback(self):
        """Checks that rollback works properly in the event of triple overlap."""
        ges_clip1 = self.add_clip(self.layer, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip2 = self.add_clip(self.layer, 10 * Gst.SECOND, duration=2 * Gst.SECOND)
        self.add_clip(self.layer, start=11 * Gst.SECOND, duration=2 * Gst.SECOND)
        self.add_clip(self.layer, start=12 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip3 = self.add_clip(self.layer, 13 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip4 = self.add_clip(self.layer, 15 * Gst.SECOND, duration=2 * Gst.SECOND)

        self.click_clip(ges_clip1, expect_selected=True, ctrl_key=True)
        self.click_clip(ges_clip2, expect_selected=True, ctrl_key=True)
        self.click_clip(ges_clip3, expect_selected=True, ctrl_key=True)
        self.click_clip(ges_clip4, expect_selected=True, ctrl_key=True)

        self.timeline_container.shift_forward_action.activate()

        self.assertEqual(5 * Gst.SECOND, ges_clip1.start)
        self.assertEqual(10 * Gst.SECOND, ges_clip2.start)
        self.assertEqual(13 * Gst.SECOND, ges_clip3.start)
        self.assertEqual(15 * Gst.SECOND, ges_clip4.start)

        self.timeline_container.shift_backward_action.activate()

        self.assertEqual(5 * Gst.SECOND, ges_clip1.start)
        self.assertEqual(10 * Gst.SECOND, ges_clip2.start)
        self.assertEqual(13 * Gst.SECOND, ges_clip3.start)
        self.assertEqual(15 * Gst.SECOND, ges_clip4.start)


class TestSnapClips(common.TestCase):

    @common.setup_timeline
    def test_snap_clip_single_layer_single_clip(self):
        """Test whether a single clip is able to snap right, and left to an adjacent clip."""
        ges_clip1 = self.add_clip(self.layer, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip2 = self.add_clip(self.layer, 9 * Gst.SECOND, duration=2 * Gst.SECOND)

        self.click_clip(ges_clip1, expect_selected=True)

        self.timeline_container.snap_clips_forward_action.activate()
        self.assertEqual(ges_clip1.start, ges_clip2.start - ges_clip1.duration)

        self.timeline_container.snap_clips_backward_action.activate()
        self.assertEqual(ges_clip1.start, 0)

    @common.setup_timeline
    def test_snap_single_layer_multiple_clips_adjacent(self):
        """Tests whether a single clip can snap to multiple adjacent clips."""
        ges_clip1 = self.add_clip(self.layer, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip2 = self.add_clip(self.layer, 7 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip3 = self.add_clip(self.layer, 11 * Gst.SECOND, duration=2 * Gst.SECOND)

        self.click_clip(ges_clip1, expect_selected=True, ctrl_key=True)
        self.click_clip(ges_clip2, expect_selected=True, ctrl_key=True)

        self.timeline_container.snap_clips_forward_action.activate()
        self.assertEqual(ges_clip2.start, ges_clip3.start - ges_clip2.duration)
        self.assertEqual(ges_clip1.start, ges_clip2.start - ges_clip1.duration)

        self.timeline_container.snap_clips_backward_action.activate()
        self.assertEqual(ges_clip1.start, 0)
        self.assertEqual(ges_clip2.start, ges_clip1.start + ges_clip1.duration)

    @common.setup_timeline
    def test_snap_multiple_layers_not_affected_by_other_layer(self):
        """Tests whether a clip snap is affected by a clip in another layer."""
        layer2 = self.timeline.append_layer()
        self.add_clip(self.layer, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        self.add_clip(self.layer, 7 * Gst.SECOND, duration=2 * Gst.SECOND)
        self.add_clip(self.layer, 11 * Gst.SECOND, duration=2 * Gst.SECOND)
        clip = self.add_clip(layer2, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        end_clip = self.add_clip(layer2, 30 * Gst.SECOND, duration=2 * Gst.SECOND)

        self.click_clip(clip, expect_selected=True)

        self.timeline_container.snap_clips_forward_action.activate()
        self.assertEqual(clip.start, end_clip.start - clip.duration)

        self.timeline_container.snap_clips_backward_action.activate()
        self.assertEqual(clip.start, 0)

    @common.setup_timeline
    def test_single_clip_snap_right_does_nothing(self):
        """Tests whether the last clip snapped forward remains in place."""
        ges_clip = self.add_clip(self.layer, 5 * Gst.SECOND, duration=2 * Gst.SECOND)
        clip_start = ges_clip.start

        self.click_clip(ges_clip, expect_selected=True)

        self.timeline_container.snap_clips_forward_action.activate()
        self.assertEqual(ges_clip.start, clip_start)

    @common.setup_timeline
    def test_clip_snaps_to_timeline_duration(self):
        """Tests whether a clip snaps to the timeline duration."""
        layer2 = self.timeline.append_layer()
        self.add_clip(self.layer, 30 * Gst.SECOND, duration=2 * Gst.SECOND)
        ges_clip = self.add_clip(layer2, 5 * Gst.SECOND, duration=2 * Gst.SECOND)

        self.click_clip(ges_clip, expect_selected=True)

        self.timeline_container.snap_clips_forward_action.activate()
        self.assertEqual(ges_clip.start, self.timeline.get_duration() - ges_clip.duration)
