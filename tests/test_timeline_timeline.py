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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
from unittest import mock

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.timeline.timeline import TimelineContainer
from pitivi.utils.timeline import UNSELECT
from pitivi.utils.ui import LAYER_HEIGHT
from pitivi.utils.ui import SEPARATOR_HEIGHT
from tests import common

THIN = LAYER_HEIGHT / 2
THICK = LAYER_HEIGHT


class BaseTestTimeline(common.TestCase):
    """Test case with tools for setting up a timeline."""

    def add_clip(self, layer, start, inpoint=0, duration=10, clip_type=GES.TrackType.UNKNOWN):
        """Creates a clip on the specified layer."""
        asset = GES.UriClipAsset.request_sync(
            common.get_sample_uri("tears_of_steel.webm"))
        clip = layer.add_asset(asset, start, inpoint, duration, clip_type)
        self.assertIsNotNone(clip)

        return clip

    def addClipsSimple(self, timeline, num_clips):
        """Creates a number of clips on a new layer."""
        layer = timeline.ges_timeline.append_layer()
        clips = [self.add_clip(layer, i * 10) for i in range(num_clips)]
        self.assertEqual(len(clips), num_clips)
        return clips


class TestLayers(BaseTestTimeline):
    """Tests for the layers."""

    def testDraggingLayer(self):
        self.checkGetLayerAt([THIN, THIN, THIN], 1, True,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THICK, THICK], 1, True,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THIN, THICK, THIN], 1, True,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THIN, THICK], 1, True,
                             [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2])

    def testDraggingClipFromLayer(self):
        self.checkGetLayerAt([THIN, THIN, THIN], 1, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THICK, THICK], 1, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THIN, THICK, THIN], 1, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THIN, THICK], 1, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])

    def testDraggingClipFromOuterSpace(self):
        self.checkGetLayerAt([THIN, THIN, THIN], None, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THICK, THICK], None, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.checkGetLayerAt([THIN, THICK, THIN], None, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THIN, THICK], None, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])

    def checkGetLayerAt(self, heights, preferred, past_middle_when_adjacent, expectations):
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
        s = SEPARATOR_HEIGHT

        def assertLayerAt(ges_layer, y):
            result = timeline._get_layer_at(
                int(y),
                prefer_ges_layer=preferred_ges_layer,
                past_middle_when_adjacent=past_middle_when_adjacent)
            self.assertEqual(
                ges_layer,
                result[0],
                "Expected %d, got %d at %d" % (ges_layers.index(ges_layer), ges_layers.index(result[0]), y))

        # y on the top layer.
        assertLayerAt(ges_layers[expectations[0]], 0)
        assertLayerAt(ges_layers[expectations[1]], h[0] / 2 - 1)
        assertLayerAt(ges_layers[expectations[2]], h[0] / 2)
        assertLayerAt(ges_layers[expectations[3]], h[0] - 1)

        # y on the separator.
        assertLayerAt(ges_layers[expectations[4]], h[0])
        assertLayerAt(ges_layers[expectations[5]], h[0] + s - 1)

        # y on the middle layer.
        assertLayerAt(ges_layers[expectations[6]], h[0] + s)
        assertLayerAt(ges_layers[expectations[7]], h[0] + s + h[1] / 2 - 1)
        assertLayerAt(ges_layers[expectations[8]], h[0] + s + h[1] / 2)
        assertLayerAt(ges_layers[expectations[9]], h[0] + s + h[1] - 1)

        # y on the separator.
        assertLayerAt(ges_layers[expectations[10]], h[0] + s + h[1])
        assertLayerAt(ges_layers[expectations[11]], h[0] + s + h[1] + s - 1)

        # y on the bottom layer.
        assertLayerAt(ges_layers[expectations[12]], h[0] + s + h[1] + s)
        assertLayerAt(ges_layers[expectations[13]], h[0] + s + h[1] + s + h[2] / 2 - 1)
        assertLayerAt(ges_layers[expectations[14]], h[0] + s + h[1] + s + h[2] / 2)
        assertLayerAt(ges_layers[expectations[15]], h[0] + s + h[1] + s + h[2] - 1)

    def testSetSeparatorsPrelight(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        timeline.__on_separators = [mock.Mock()]
        timeline._setSeparatorsPrelight(False)
        self.assertEqual(len(timeline.__on_separators), 1,
                         "The separators must be forgotten only in dragEnd()")

    def test_media_types(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline

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

    def check_priorities_and_positions(self, timeline, ges_layers,
                                       expected_priorities):
        layers_vbox = timeline.layout.layers_vbox

        # Check the layers priorities.
        priorities = [ges_layer.props.priority for ges_layer in ges_layers]
        self.assertListEqual(priorities, expected_priorities)

        # Check the positions of the Layer widgets.
        positions = [layers_vbox.child_get_property(ges_layer.ui, "position")
                     for ges_layer in ges_layers]
        expected_positions = [priority * 2 + 1
                              for priority in expected_priorities]
        self.assertListEqual(positions, expected_positions, layers_vbox.get_children())

        # Check the positions of the LayerControl widgets.
        controls_vbox = timeline._layers_controls_vbox
        positions = [controls_vbox.child_get_property(ges_layer.control_ui, "position")
                     for ges_layer in ges_layers]
        self.assertListEqual(positions, expected_positions)

        # Check the number of the separators.
        count = len(ges_layers) + 1
        self.assertEqual(len(timeline._separators), count)
        controls_separators, layers_separators = list(zip(*timeline._separators))

        # Check the positions of the LayerControl separators.
        expected_positions = [2 * index for index in range(count)]
        positions = [layers_vbox.child_get_property(separator, "position")
                     for separator in layers_separators]
        self.assertListEqual(positions, expected_positions)

        # Check the positions of the Layer separators.
        positions = [controls_vbox.child_get_property(separator, "position")
                     for separator in controls_separators]
        self.assertListEqual(positions, expected_positions)

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

        timeline.moveLayer(ges_layers[from_priority], to_priority)
        self.check_priorities_and_positions(timeline, ges_layers, expected_priorities)


class TestGrouping(BaseTestTimeline):

    def __check_can_group_ungroup(self, timeline_container, can_group, can_ungroup):
        self.assertEqual(timeline_container.group_action.props.enabled, can_group)
        self.assertEqual(timeline_container.ungroup_action.props.enabled, can_ungroup)

    def test_can_group_ungroup(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        self.__check_can_group_ungroup(timeline_container, False, False)
        ges_clip, = self.addClipsSimple(timeline, 1)
        self.toggle_clip_selection(ges_clip, expect_selected=True)
        self.__check_can_group_ungroup(timeline_container, False, True)

        timeline_container.ungroup_action.emit("activate", None)
        self.__check_can_group_ungroup(timeline_container, False, False)

        layer, = timeline.ges_timeline.get_layers()
        ges_clip0, ges_clip1 = layer.get_clips()
        self.toggle_clip_selection(ges_clip0, expect_selected=True)
        self.__check_can_group_ungroup(timeline_container, False, False)

        # Press <ctrl> so selecting in ADD mode
        event = mock.Mock()
        event.keyval = Gdk.KEY_Control_L
        timeline_container.do_key_press_event(event)

        self.toggle_clip_selection(ges_clip1, expect_selected=True)
        self.__check_can_group_ungroup(timeline_container, True, False)

        timeline_container.group_action.emit("activate", None)
        self.__check_can_group_ungroup(timeline_container, False, True)

    def group_clips(self, timeline_container, clips):
        timeline = timeline_container.timeline
        timeline.app.settings.leftClickAlsoSeeks = False

        # Press <ctrl> so selecting in ADD mode
        event = mock.Mock()
        event.keyval = Gdk.KEY_Control_L
        timeline_container.do_key_press_event(event)
        timeline.get_clicked_layer_and_pos = mock.Mock()
        timeline.get_clicked_layer_and_pos.return_value = (None, None)

        # Select the 2 clips
        for clip in clips:
            self.assertIsNone(clip.get_parent())
            self.toggle_clip_selection(clip, expect_selected=True)

        timeline_container.group_action.emit("activate", None)

        for clip in clips:
            # Check that we created a new group
            self.assertTrue(isinstance(clip.get_parent(), GES.Group))
            # The newly created group has been selected
            for selected_clip in timeline.selection:
                self.assertEqual(clip.get_toplevel_parent(), selected_clip.get_toplevel_parent())

            self.assertEqual(clips[0].get_parent(), clip.get_parent())
            self.assertTrue(bool(clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED))
            self.assertTrue(clip.selected.selected)

        group = clips[0].get_parent()
        self.assertEqual(len(group.get_children(False)), len(clips))

    def testGroup(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.addClipsSimple(timeline, 2)
        self.group_clips(timeline_container, clips)

    def testGroupSelection(self):
        num_clips = 2
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.addClipsSimple(timeline, num_clips)
        self.group_clips(timeline_container, clips)
        layer = timeline.ges_timeline.get_layers()[0]
        clips = layer.get_clips()
        self.assertEqual(len(clips), num_clips)

        # Deselect one grouped clip clips
        self.toggle_clip_selection(clips[0], expect_selected=False)

        # Make sure all the clips have been deselected
        for clip in clips:
            self.assertFalse(bool(clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED))
            self.assertFalse(clip.selected.selected)

    def testGroupUngroup(self):
        num_clips = 2
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.addClipsSimple(timeline, num_clips)
        self.group_clips(timeline_container, clips)

        self.assertEqual(len(timeline.selection.selected), num_clips)

        timeline_container.ungroup_action.emit("activate", None)
        layer = timeline.ges_timeline.get_layers()[0]
        clips = layer.get_clips()
        self.assertEqual(len(clips), num_clips)

        for clip in clips:
            self.assertIsNone(clip.get_parent())

    def testGroupSplittedClipAndSelectGroup(self):
        position = 5

        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.addClipsSimple(timeline, 1)
        self.toggle_clip_selection(clips[0], expect_selected=True)

        timeline.ges_timeline.get_asset().pipeline.getPosition = mock.Mock(return_value=position)
        layer = timeline.ges_timeline.get_layers()[0]

        # Split
        timeline_container.split_action.emit("activate", None)
        clips = layer.get_clips()
        self.assertEqual(len(clips), 2)

        # Only the first clip is selected so select the
        # second one
        self.assertTrue(clips[0].selected.selected)
        self.assertFalse(clips[1].selected.selected)

        event = mock.Mock()
        event.keyval = Gdk.KEY_Control_L
        timeline_container.do_key_press_event(event)
        timeline.get_clicked_layer_and_pos = mock.Mock()
        timeline.get_clicked_layer_and_pos.return_value = (None, None)
        self.toggle_clip_selection(clips[1], expect_selected=True)
        timeline_container.do_key_release_event(event)

        for clip in clips:
            self.assertTrue(clip.selected.selected)

        # Group the two parts
        timeline_container.group_action.emit("activate", None)

        self.toggle_clip_selection(clips[1], expect_selected=True)

    def testUngroupClip(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_clip, = self.addClipsSimple(timeline, 1)

        self.toggle_clip_selection(ges_clip, expect_selected=True)

        timeline_container.ungroup_action.emit("activate", None)
        layer = timeline.ges_timeline.get_layers()[0]
        ges_clip0, ges_clip1 = layer.get_clips()

        self.assertEqual(ges_clip0.props.start, ges_clip1.props.start)
        self.assertEqual(ges_clip0.props.duration, ges_clip1.props.duration)

        bTrackElem0, = ges_clip0.get_children(recursive=False)
        bTrackElem1, = ges_clip1.get_children(recursive=False)

        if bTrackElem0.get_track_type() == GES.TrackType.AUDIO:
            aclip = ges_clip0.ui
            atrackelem = bTrackElem0.ui
            vclip = ges_clip1.ui
            vtrackelem = bTrackElem1.ui
        else:
            aclip = ges_clip1.ui
            atrackelem = bTrackElem1.ui

            vclip = ges_clip0.ui
            vtrackelem = bTrackElem0.ui

        self.assertEqual(aclip._audioSource, atrackelem)
        self.assertEqual(vclip._videoSource, vtrackelem)

    def test_dragging_group_on_separator(self):
        # Create two clips on different layers and group them.
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clip1, = self.addClipsSimple(timeline, 1)
        layer1 = clip1.get_layer()

        # Add another clip on a new layer.
        clip2, = self.addClipsSimple(timeline, 1)
        self.assertEqual(len(timeline.ges_timeline.get_layers()), 2)

        self.group_clips(timeline_container, [clip1, clip2])

        # Click the first clip in the group.
        with mock.patch.object(Gtk, 'get_event_widget') as get_event_widget:
            event = mock.Mock()
            event.x = 100
            event.get_button.return_value = True, 1
            get_event_widget.return_value = clip1.ui
            timeline._button_press_event_cb(None, event)
            self.assertIsNotNone(timeline.draggingElement)

            # Move it to the right, on the separator below.
            event = mock.Mock()
            event.x = 101
            event.get_state.return_value = Gdk.ModifierType.BUTTON1_MASK
            with mock.patch.object(clip1.ui, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (40, 0)
                with mock.patch.object(timeline, "_get_layer_at") as _get_layer_at:
                    _get_layer_at.return_value = layer1, timeline._separators[1]
                    timeline._motion_notify_event_cb(None, event)
            self.assertTrue(timeline.got_dragged)

        # Release the mouse button.
        event = mock.Mock()
        event.get_button.return_value = True, 1
        timeline._button_release_event_cb(None, event)
        self.assertEqual(len(timeline.ges_timeline.get_layers()), 2,
                         "No new layer should have been created")


class TestCopyPaste(BaseTestTimeline):

    def copyClips(self, num_clips):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline

        clips = self.addClipsSimple(timeline, num_clips)

        # Press <ctrl> so selecting in ADD mode
        event = mock.Mock()
        event.keyval = Gdk.KEY_Control_L
        timeline_container.do_key_press_event(event)
        timeline.get_clicked_layer_and_pos = mock.Mock()
        timeline.get_clicked_layer_and_pos.return_value = (None, None)

        # Select the 2 clips
        for clip in clips:
            self.toggle_clip_selection(clip, expect_selected=True)

        self.assertTrue(timeline_container.copy_action.props.enabled)
        self.assertFalse(timeline_container.paste_action.props.enabled)
        timeline_container.copy_action.emit("activate", None)
        self.assertTrue(timeline_container.paste_action.props.enabled)

        return timeline_container

    def testCopyPaste(self):
        timeline_container = self.copyClips(2)
        timeline = timeline_container.timeline
        layer = timeline.ges_timeline.get_layers()[0]
        project = timeline.ges_timeline.get_asset()

        clips = layer.get_clips()
        self.assertEqual(len(clips), 2)

        # Pasting clips for the first time.
        position = 20
        project.pipeline.getPosition = mock.Mock(return_value=position)
        timeline_container.paste_action.emit("activate", None)

        n_clips = layer.get_clips()
        self.assertEqual(len(n_clips), 4)

        copied_clips = [clip for clip in n_clips if clip not in clips]
        self.assertEqual(len(copied_clips), 2)
        self.assertEqual(copied_clips[0].props.start, position)
        self.assertEqual(copied_clips[1].props.start, position + 10)

        # Pasting same clips second time.
        position = 40
        project.pipeline.getPosition = mock.Mock(return_value=position)
        timeline_container.paste_action.emit("activate", None)

        n_clips = layer.get_clips()
        self.assertEqual(len(n_clips), 6)

        copied_clips = [clip for clip in n_clips if clip not in clips]
        self.assertEqual(len(copied_clips), 4)
        self.assertEqual(copied_clips[2].props.start, position)
        self.assertEqual(copied_clips[3].props.start, position + 10)

    def test_paste_not_possible(self):
        timeline_container = self.copyClips(1)
        timeline = timeline_container.timeline
        layer = timeline.ges_timeline.get_layers()[0]
        project = timeline.ges_timeline.get_asset()
        self.assertEqual(len(layer.get_clips()), 1)

        position = 0
        project.pipeline.getPosition = mock.Mock(return_value=position)
        timeline_container.paste_action.emit("activate", None)
        self.assertEqual(len(layer.get_clips()), 1)


class TestEditing(BaseTestTimeline):

    def test_trimming_on_layer_separator(self):
        # Create a clip
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clip, = self.addClipsSimple(timeline, 1)
        layer = clip.get_layer()

        # Click the right trim handle of the clip.
        with mock.patch.object(Gtk, 'get_event_widget') as get_event_widget:
            event = mock.Mock()
            event.x = 100
            event.get_button.return_value = True, 1
            get_event_widget.return_value = clip.ui.rightHandle
            timeline._button_press_event_cb(None, event)
            self.assertIsNotNone(timeline.draggingElement)

            # Drag it to the left, on the separator below.
            event = mock.Mock()
            event.x = 99
            event.get_state.return_value = Gdk.ModifierType.BUTTON1_MASK
            with mock.patch.object(clip.ui.rightHandle, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (0, 0)
                with mock.patch.object(timeline, "_get_layer_at") as _get_layer_at:
                    _get_layer_at.return_value = layer, timeline._separators[1]
                    timeline._motion_notify_event_cb(None, event)
            self.assertTrue(timeline.got_dragged)

        # Release the mouse button.
        event = mock.Mock()
        event.get_button.return_value = True, 1
        timeline._button_release_event_cb(None, event)
        self.assertEqual(len(timeline.ges_timeline.get_layers()), 1,
                         "No new layer should have been created")


class TestShiftSelection(BaseTestTimeline):

    def __reset_clips_selection(self, timeline):
        """Unselects all clips in the timeline."""
        layers = timeline.ges_timeline.get_layers()
        for layer in layers:
            clips = layer.get_clips()
            timeline.selection.setSelection(clips, UNSELECT)
            timeline.set_selection_meta_info(layer, 0, UNSELECT)

    def __check_selected(self, selected_clips, not_selected_clips):
        for clip in selected_clips:
            self.assertEqual(clip.selected._selected, True)
        for clip in not_selected_clips:
            self.assertEqual(clip.selected._selected, False)

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
            timeline.get_parent()._shiftMask = True
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
        timeline.get_parent()._shiftMask = True
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
        timeline.get_parent()._shiftMask = True
        timeline._seek = mock.Mock()
        timeline._seek.return_value = True
        timeline.get_clicked_layer_and_pos = mock.Mock()

        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = timeline

            timeline.get_clicked_layer_and_pos.return_value = (ges_layer2, 3 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer1, 9 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip11, ges_clip22], [ges_clip12, ges_clip13,
                ges_clip21, ges_clip23, ges_clip31, ges_clip32, ges_clip33])
            timeline.get_clicked_layer_and_pos.return_value = (ges_layer3, 12 * Gst.SECOND)
            timeline._button_release_event_cb(None, event)
            self.__check_selected([ges_clip22, ges_clip31, ges_clip32], [ges_clip11,
                ges_clip12, ges_clip13, ges_clip21, ges_clip23, ges_clip33])
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
                ges_clip31, ges_clip32, ges_clip33], [ges_clip21])

    def test_shift_selection_multiple_layers(self):
        self.__check_shift_selection_multiple_layers(left_click_also_seeks=False)
        self.__check_shift_selection_multiple_layers(left_click_also_seeks=True)


class TestTimelineContainer(BaseTestTimeline):
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
        timeline_container.update_clips_asset(mock.Mock(), mock.Mock())


class TestClipsEdges(BaseTestTimeline):

    def test_clips_edges(self):
        """Test function for function clips_edges."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clips = self.addClipsSimple(timeline, 5)
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
