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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Tests for the pitivi.undo.timeline module."""
# pylint: disable=protected-access
from unittest import mock

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import Gtk

from pitivi.timeline.layer import FullLayer
from pitivi.undo.base import PropertyChangedAction
from pitivi.undo.project import AssetAddedAction
from pitivi.undo.timeline import ClipAdded
from pitivi.undo.timeline import ClipRemoved
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.undo.timeline import TrackElementAdded
from pitivi.utils.timeline import EditingContext
from pitivi.utils.ui import LAYER_HEIGHT
from pitivi.utils.ui import URI_TARGET_ENTRY
from tests import common


class TestSelectionResetWhenRemovingClip(common.TestCase):

    def add_clips_separately(self):
        for i in range(3):
            clip = GES.TitleClip()
            clip.set_start(i * Gst.SECOND)
            clip.set_duration(1 * Gst.SECOND)

            with self.action_log.started("add clip {}".format(i)):
                self.layer.add_clip(clip)

    def check_selection(self, *expected_selected_clips):
        self.assertSetEqual(set(self.timeline_container.timeline.selection), set(expected_selected_clips))
        for clip in self.get_timeline_clips():
            self.assert_clip_selected(clip, expect_selected=clip in expected_selected_clips)

    @common.setup_timeline
    def test_redo_delete_when_selected(self):
        self.add_clips_separately()
        clip1, clip2, clip3 = self.get_timeline_clips()

        # Delete clip1.
        self.timeline_container.timeline.selection.select([clip1])
        self.timeline_container.delete_action.activate(None)
        self.check_selection()

        # Undo clip1 deletion.
        self.action_log.undo()

        # Redo clip1 deletion when selected.
        self.timeline_container.timeline.selection.select([clip1, clip2, clip3])
        self.action_log.redo()
        self.check_selection()

    @common.setup_timeline
    def test_redo_delete_when_unselected(self):
        self.add_clips_separately()
        clip1, clip2, clip3 = self.get_timeline_clips()

        # Delete clip1.
        self.timeline_container.timeline.selection.select([clip1])
        self.timeline_container.delete_action.activate(None)
        self.check_selection()

        # Undo clip1 deletion.
        self.action_log.undo()

        # Redo clip1 deletion when unselected.
        self.timeline_container.timeline.selection.select([clip2, clip3])
        self.action_log.redo()
        self.check_selection(clip2, clip3)

    @common.setup_timeline
    def test_undo_add_when_selected(self):
        self.add_clips_separately()
        clip1, clip2, clip3 = self.get_timeline_clips()

        # Undo clip3 creation when selected.
        self.timeline_container.timeline.selection.select([clip1, clip2, clip3])
        self.action_log.undo()
        self.check_selection()

    @common.setup_timeline
    def test_undo_add_when_unselected(self):
        self.add_clips_separately()
        clip1, clip2, _ = self.get_timeline_clips()

        # Undo clip3 creation when unselected.
        self.timeline_container.timeline.selection.select([clip1, clip2])
        self.action_log.undo()
        self.check_selection(clip1, clip2)


class TestTimelineObserver(common.TestCase):

    @common.setup_timeline
    def test_layer_removed(self):
        layer1 = self.layer
        layer2 = self.timeline.append_layer()
        layer3 = self.timeline.append_layer()
        self.assert_layers([layer1, layer2, layer3])
        self.check_removal(self.timeline.get_layers())

    def check_removal(self, ges_layers):
        if len(ges_layers) == 1:
            # We don't support removing the last remaining layer.
            return
        for ges_layer in ges_layers:
            remaining_layers = list(ges_layers)
            remaining_layers.remove(ges_layer)

            ges_layer.control_ui.delete_layer_action.activate(None)
            self.assert_layers(remaining_layers)

            self.action_log.undo()
            self.assert_layers(ges_layers)

            self.action_log.redo()
            self.assert_layers(remaining_layers)

            self.check_removal(remaining_layers)

            self.action_log.undo()
            self.assert_layers(ges_layers)

    @common.setup_timeline
    def test_group_ungroup_clips(self):
        clip1 = common.create_test_clip(GES.TitleClip)
        clip1.set_start(0 * Gst.SECOND)
        clip1.set_duration(1 * Gst.SECOND)

        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip2 = asset.extract()
        clip2.props.start = 1 * Gst.SECOND

        self.assertTrue(self.layer.add_clip(clip1))
        self.assertTrue(self.layer.add_clip(clip2))
        self.assertEqual(clip1.get_timeline(), self.layer.get_timeline())
        self.assertEqual(clip2.get_timeline(), self.layer.get_timeline())

        self.timeline_container.timeline.selection.select([clip1, clip2])
        self.timeline_container.group_action.activate(None)
        self.assertEqual(clip1.get_parent(), clip2.get_parent())
        self.assertTrue(isinstance(clip1.get_parent(), GES.Group), type(clip1.get_parent()))

        self.timeline_container.ungroup_action.activate(None)
        self.assertIsNone(clip1.get_parent())
        self.assertIsNone(clip2.get_parent())

        for _ in range(4):
            # Undo ungrouping.
            self.action_log.undo()
            self.assertTrue(isinstance(clip1.get_parent(), GES.Group))
            self.assertEqual(clip1.get_parent(), clip2.get_parent())

            # Undo grouping.
            self.action_log.undo()
            self.assertIsNone(clip1.get_parent())
            self.assertIsNone(clip2.get_parent())

            # Redo grouping.
            self.action_log.redo()
            self.assertTrue(isinstance(clip1.get_parent(), GES.Group))
            self.assertEqual(clip1.get_parent(), clip2.get_parent())

            # Redo ungrouping.
            self.action_log.redo()
            self.assertIsNone(clip1.get_parent())
            self.assertIsNone(clip2.get_parent())

    @common.setup_timeline
    def test_ungroup_group_clip(self):
        timeline = self.timeline_container.timeline

        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip = asset.extract()
        self.layer.add_clip(clip)
        clips = list(self.get_timeline_clips())
        self.assertEqual(len(clips), 1, clips)
        self.assertEqual(len(clips[0].get_children(False)), 2)

        self.click_clip(clips[0], expect_selected=True)
        self.timeline_container.ungroup_action.activate(None)
        clips = list(self.get_timeline_clips())
        self.assertEqual(len(clips), 2, clips)
        self.assertEqual(len(clips[0].get_children(False)), 1)
        self.assertEqual(len(clips[1].get_children(False)), 1)

        timeline.selection.select(clips)
        self.timeline_container.group_action.activate(None)
        clips = list(self.get_timeline_clips())
        self.assertEqual(len(clips), 1, clips)
        self.assertEqual(len(clips[0].get_children(False)), 2)

        for _ in range(2):
            # Undo grouping.
            self.action_log.undo()
            clips = list(self.get_timeline_clips())
            self.assertEqual(len(clips), 2, clips)
            self.assertEqual(len(clips[0].get_children(False)), 1)
            self.assertEqual(len(clips[1].get_children(False)), 1)

            # Undo ungrouping.
            self.action_log.undo()
            clips = list(self.get_timeline_clips())
            self.assertEqual(len(clips), 1, clips)
            self.assertEqual(len(clips[0].get_children(False)), 2)

            # Redo ungrouping.
            self.action_log.redo()
            clips = list(self.get_timeline_clips())
            self.assertEqual(len(clips), 2, clips)
            self.assertEqual(len(clips[0].get_children(False)), 1)
            self.assertEqual(len(clips[1].get_children(False)), 1)

            # Redo grouping.
            self.action_log.redo()
            clips = list(self.get_timeline_clips())
            self.assertEqual(len(clips), 1, clips)
            self.assertEqual(len(clips[0].get_children(False)), 2)

    @common.setup_timeline
    def test_insert_on_first_layer(self):
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip1 = asset.extract()
        self.timeline_container.insert_clips_on_first_layer(clips=[clip1], position=0)
        clips = list(self.get_timeline_clips())
        self.assertEqual(len(clips), 1, clips)

        # Undo insert on first layer
        self.action_log.undo()
        clips = list(self.get_timeline_clips())
        self.assertEqual(len(clips), 0, clips)

        # Redo insert on first layer
        self.action_log.redo()
        clips = list(self.get_timeline_clips())
        self.assertEqual(len(clips), 1, clips)

        # Insert new clip to create a layer
        clip2 = common.create_test_clip(GES.TitleClip)
        clip2.set_start(0 * Gst.SECOND)
        clip2.set_duration(1 * Gst.SECOND)
        self.timeline_container.insert_clips_on_first_layer(clips=[clip2], position=0)
        layers = self.timeline.get_layers()
        self.assert_layers([layers[0], self.layer])
        self.assertEqual(layers[0].get_clips(), [clip2])
        self.assertEqual(layers[1].get_clips(), [clip1])

        # Undo insert to create a layer
        self.action_log.undo()
        layers = self.timeline.get_layers()
        self.assert_layers([self.layer])
        self.assertEqual(layers[0].get_clips(), [clip1])

        # Redo insert to create a layer
        self.action_log.redo()
        layers = self.timeline.get_layers()
        self.assert_layers([layers[0], self.layer])
        self.assertEqual(layers[0].get_clips(), [clip2])
        self.assertEqual(layers[1].get_clips(), [clip1])


class TestLayerObserver(common.TestCase):

    @common.setup_timeline
    def test_layer_moved(self):
        layer1 = self.layer
        layer2 = self.timeline.append_layer()
        layer3 = self.timeline.append_layer()
        self.assertEqual(self.timeline.get_layers(), [layer1, layer2, layer3])

        timeline = self.timeline_container.timeline

        # Click and drag a layer control box to move the layer.
        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            event = mock.Mock()
            event.get_button.return_value = True, 1

            get_event_widget.return_value = layer1.control_ui
            timeline._button_press_event_cb(None, event=event)

            with mock.patch.object(layer1.control_ui, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (0, 0)
                with mock.patch.object(timeline, "get_layer_at") as get_layer_at:
                    get_layer_at.return_value = layer3, None
                    timeline._motion_notify_event_cb(None, event=event)

            timeline._button_release_event_cb(None, event=event)
        self.assert_layers([layer2, layer3, layer1])

        self.action_log.undo()
        self.assert_layers([layer1, layer2, layer3])

        self.action_log.redo()
        self.assert_layers([layer2, layer3, layer1])

    @common.setup_timeline
    def test_layer_renamed(self):
        layer = FullLayer(self.layer, timeline=mock.Mock())
        self.assertIsNone(layer._name_if_set())

        with self.app.action_log.started("change layer name"):
            layer.set_name("Beautiful name")
        self.assertEqual(layer._name_if_set(), "Beautiful name")

        self.action_log.undo()
        self.assertIsNone(layer._name_if_set())

        self.action_log.redo()
        self.assertEqual(layer._name_if_set(), "Beautiful name")

    @common.setup_timeline
    def test_add_clip(self):
        clip1 = GES.TitleClip()
        with self.action_log.started("add clip"):
            self.layer.add_clip(clip1)

        stack = self.action_log.undo_stacks[0]
        self.assertEqual(len(stack.done_actions), 9, stack.done_actions)
        self.assertTrue(isinstance(stack.done_actions[0], ClipAdded))
        self.assertTrue(clip1 in self.get_timeline_clips())

        self.action_log.undo()
        self.assertFalse(clip1 in self.get_timeline_clips())

        self.action_log.redo()
        self.assertTrue(clip1 in self.get_timeline_clips())

    @common.setup_timeline
    def test_remove_clip(self):
        stacks = []
        self.action_log.connect("commit", common.TestCase.commit_cb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)
        with self.action_log.started("remove clip"):
            self.layer.remove_clip(clip1)

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions))
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, ClipRemoved))
        self.assertFalse(clip1 in self.get_timeline_clips())

        self.action_log.undo()
        self.assertTrue(clip1 in self.get_timeline_clips())

        self.action_log.redo()
        self.assertFalse(clip1 in self.get_timeline_clips())

    @common.setup_timeline
    def test_layer_added(self):
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)

        clip = GES.TitleClip()
        self.layer.add_clip(clip)

        self.timeline_container.update_actions()
        self.timeline_container.add_layer_action.activate()

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])
        self.assertEqual(layers[1].get_clips(), [])

        self.action_log.undo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])

        self.action_log.redo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])
        self.assertEqual(layers[1].get_clips(), [])

    @common.setup_timeline
    def test_ungroup_group_clip(self):
        # This test is in TestLayerObserver because the relevant operations
        # recorded are clip-added and clip-removed.
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip1 = asset.extract()
        self.layer.add_clip(clip1)

        clip1.set_start(5 * Gst.SECOND)
        clip1.set_duration(0.5 * Gst.SECOND)
        timeline_clips = list(self.get_timeline_clips())
        self.assertEqual(1, len(timeline_clips), timeline_clips)
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())

        with self.action_log.started("ungroup"):
            ungrouped = GES.Container.ungroup(clip1, False)
            self.assertEqual(2, len(ungrouped), ungrouped)
        timeline_clips = list(self.get_timeline_clips())
        self.assertEqual(2, len(timeline_clips), timeline_clips)
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())
        self.assertEqual(5 * Gst.SECOND, timeline_clips[1].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[1].get_duration())

        self.action_log.undo()
        timeline_clips = list(self.get_timeline_clips())
        self.assertEqual(1, len(timeline_clips))
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())

        self.action_log.redo()
        timeline_clips = list(self.get_timeline_clips())
        self.assertEqual(2, len(timeline_clips), timeline_clips)
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())
        self.assertEqual(5 * Gst.SECOND, timeline_clips[1].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[1].get_duration())

    @common.setup_timeline
    def test_split_clip(self):
        clip = GES.TitleClip()
        clip.set_start(0 * Gst.SECOND)
        clip.set_duration(20 * Gst.SECOND)

        self.layer.add_clip(clip)

        with self.action_log.started("split clip"):
            clip1 = clip.split(10 * Gst.SECOND)
            self.assertEqual(2, len(self.layer.get_clips()))

        with self.action_log.started("split clip"):
            _clip2 = clip1.split(15 * Gst.SECOND)
            self.assertEqual(3, len(self.layer.get_clips()))

        self.action_log.undo()
        self.assertEqual(2, len(self.layer.get_clips()))
        self.action_log.undo()
        self.assertEqual(1, len(self.layer.get_clips()))

        self.action_log.redo()
        self.assertEqual(2, len(self.layer.get_clips()))
        self.action_log.redo()
        self.assertEqual(3, len(self.layer.get_clips()))

    @common.setup_timeline
    def test_add_effect_to_clip(self):
        stacks = []
        self.action_log.connect("commit", common.TestCase.commit_cb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        with self.action_log.started("add effect"):
            clip1.add(effect1)

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions), stack.done_actions)
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, TrackElementAdded))

        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        self.action_log.undo()
        self.assertFalse(effect1 in clip1.get_children(True))

        self.action_log.redo()
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

    @common.setup_timeline
    def test_remove_effect_from_clip(self):
        stacks = []
        self.action_log.connect("commit", common.TestCase.commit_cb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        with self.action_log.started("add effect"):
            clip1.add(effect1)

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions), stack.done_actions)
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, TrackElementAdded))

        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        with self.action_log.started("remove effect"):
            clip1.remove(effect1)
        self.assert_effect_count(clip1, 0)

        self.action_log.undo()
        self.assert_effect_count(clip1, 1)

        self.action_log.redo()
        self.assert_effect_count(clip1, 0)

    @common.setup_timeline
    def test_move_clip(self):
        self._wait_until_project_loaded()

        clip1 = GES.TitleClip()
        clip1.set_start(0 * Gst.SECOND)
        clip1.set_duration(10 * Gst.SECOND)
        clip2 = GES.TitleClip()
        clip2.set_start(5 * Gst.SECOND)
        clip2.set_duration(10 * Gst.SECOND)

        self.layer.add_clip(clip1)
        self.assertEqual(len(self.layer.get_clips()), 1)
        self.layer.add_clip(clip2)
        self.assertEqual(len(self.layer.get_clips()), 3)

        with self.action_log.started("move clip",
                                     finalizing_action=CommitTimelineFinalizingAction(self.project.pipeline)):
            clip2.set_start(20 * Gst.SECOND)
        self.assertEqual(clip2.get_start(), 20 * Gst.SECOND)
        self.assertEqual(len(self.layer.get_clips()), 2,
                         "The two title clips don't overlap so there should be no transition clip")

        self.action_log.undo()
        self.assertEqual(clip2.get_start(), 5 * Gst.SECOND)
        self.assertEqual(len(self.layer.get_clips()), 3)

        self.action_log.redo()
        self.assertEqual(clip2.get_start(), 20 * Gst.SECOND)
        self.assertEqual(len(self.layer.get_clips()), 2)

    @common.setup_project(assets_names=["mp3_sample.mp3"])
    def test_move_transition_to_different_layer_audio(self):
        uri = common.get_sample_uri("mp3_sample.mp3")
        asset = GES.UriClipAsset.request_sync(uri)
        self.__check_move_transition_to_different_layer(asset)

    @common.setup_project(assets_names=["30fps_numeroted_frames_red.mkv"])
    def test_move_transition_to_different_layer_video(self):
        uri = common.get_sample_uri("30fps_numeroted_frames_red.mkv")
        asset = GES.UriClipAsset.request_sync(uri)
        self.__check_move_transition_to_different_layer(asset,
                                                        border=123,
                                                        invert=True,
                                                        transition_type=GES.VideoStandardTransitionType.BAR_WIPE_LR)

    def __check_move_transition_to_different_layer(self, asset, **props):
        clip1 = asset.extract()
        clip1.set_start(0 * Gst.SECOND)
        self.layer.add_clip(clip1)
        self.assertEqual(len(self.layer.get_clips()), 1)

        clip2 = asset.extract()
        clip2.set_start(clip1.props.duration * 9 // 10)
        self.layer.add_clip(clip2)
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 3)

        # Click all three clips including the transition clip to make sure
        # it's not included in the group.
        for clip in clips:
            self.click_clip(clip, expect_selected=True, ctrl_key=True)
        self.timeline_container.group_action.activate()

        track_element = self.get_transition_element(self.layer)
        for name, value in props.items():
            track_element.set_property(name, value)

        layer2 = self.timeline.append_layer()
        with self.action_log.started("move clips to different layer"):
            editing_context = EditingContext(clip1, self.timeline, GES.EditMode.EDIT_NORMAL, GES.Edge.EDGE_NONE, self.app)
            editing_context.edit_to(0, layer2)
            editing_context.finish()
        self.assertEqual(len(self.layer.get_clips()), 0)
        self.assertEqual(len(layer2.get_clips()), 3)
        self.__check_transition_element(layer2, props)

        with self.project.pipeline.commit_timeline_after():
            self.action_log.undo()
        self.assertEqual(len(self.layer.get_clips()), 3)
        self.assertEqual(len(layer2.get_clips()), 0)
        self.__check_transition_element(self.layer, props)

        with self.project.pipeline.commit_timeline_after():
            self.action_log.redo()
        self.assertEqual(len(self.layer.get_clips()), 0)
        self.assertEqual(len(layer2.get_clips()), 3)
        self.__check_transition_element(layer2, props)

    def __check_transition_element(self, layer: GES.Layer, props):
        track_element = self.get_transition_element(layer)
        for name, value in props.items():
            self.assertEqual(track_element.get_property(name), value)

    @common.setup_timeline
    def test_transition_type(self):
        """Checks the transitions keep their type."""
        self._wait_until_project_loaded()
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)

        clip1 = asset.extract()
        clip1.set_start(0 * Gst.SECOND)
        self.layer.add_clip(clip1)

        clip2 = asset.extract()
        clip2.set_start(clip1.props.duration / 2)
        clip2.set_duration(clip2.props.max_duration)
        with self.action_log.started("add second clip"):
            self.layer.add_clip(clip2)

        # Make sure the transition asset is ignored.
        stack = self.action_log.undo_stacks[0]
        for action in stack.done_actions:
            self.assertNotIsInstance(action, AssetAddedAction,
                                     stack.done_actions)

        transition_element = self.get_transition_element(self.layer)
        self.assertEqual(transition_element.get_transition_type(),
                         GES.VideoStandardTransitionType.CROSSFADE)

        with self.action_log.started("set transition type"):
            transition_element.set_transition_type(GES.VideoStandardTransitionType.BAR_WIPE_LR)
        self.assertEqual(transition_element.get_transition_type(),
                         GES.VideoStandardTransitionType.BAR_WIPE_LR)

        # Undo setting the transition type.
        self.action_log.undo()
        self.assertEqual(transition_element.get_transition_type(),
                         GES.VideoStandardTransitionType.CROSSFADE)

        # Redo setting the transition type.
        self.action_log.redo()
        self.assertEqual(transition_element.get_transition_type(),
                         GES.VideoStandardTransitionType.BAR_WIPE_LR)

        for unused_repeat in range(4):
            # Remove the clip and add it back.
            # This recreates the transition clip.
            with self.action_log.started("remove clip"):
                self.layer.remove_clip(clip2)
            self.action_log.undo()
            transition_element = self.get_transition_element(self.layer)
            self.assertEqual(transition_element.get_transition_type(),
                             GES.VideoStandardTransitionType.BAR_WIPE_LR)

            # Undo a transition change operation done on a now obsolete
            # transition clip.
            self.action_log.undo()
            transition_element = self.get_transition_element(self.layer)
            self.assertEqual(transition_element.get_transition_type(),
                             GES.VideoStandardTransitionType.CROSSFADE)

            self.action_log.redo()
            transition_element = self.get_transition_element(self.layer)
            self.assertEqual(transition_element.get_transition_type(),
                             GES.VideoStandardTransitionType.BAR_WIPE_LR,
                             "The auto objects map in "
                             "UndoableAutomaticObjectAction is not updated when "
                             "undoing clip remove.")

        for unused_repeat in range(4):
            # Undo the transition change.
            self.action_log.undo()
            # Undo adding the second clip.
            self.action_log.undo()
            # Redo adding the second clip.
            self.action_log.redo()
            transition_element = self.get_transition_element(self.layer)
            self.assertEqual(transition_element.get_transition_type(),
                             GES.VideoStandardTransitionType.CROSSFADE)
            # Redo the transition change.
            self.action_log.redo()
            transition_element = self.get_transition_element(self.layer)
            self.assertEqual(transition_element.get_transition_type(),
                             GES.VideoStandardTransitionType.BAR_WIPE_LR,
                             "The auto objects map in "
                             "UndoableAutomaticObjectAction is not updated when "
                             "redoing clip add.")

    @common.setup_timeline
    def test_transition_found(self):
        self._wait_until_project_loaded()
        uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")
        asset = GES.UriClipAsset.request_sync(uri)

        clip1 = asset.extract()
        clip1.set_start(0)
        self.layer.add_clip(clip1)

        clip2 = asset.extract()
        clip2.set_start(clip1.props.duration)
        self.layer.add_clip(clip2)

        self.assertIsNone(self.get_transition_element(self.layer))
        with self.action_log.started("move clip1"):
            clip1.edit([], -1, GES.EditMode.EDIT_NORMAL, GES.Edge.EDGE_NONE, clip1.props.duration / 2)
        self.assertIsNotNone(self.get_transition_element(self.layer))

        self.action_log.undo()
        self.assertIsNone(self.get_transition_element(self.layer))

        self.action_log.redo()
        self.assertIsNotNone(self.get_transition_element(self.layer))

    @common.setup_timeline
    def test_paste_undo(self):
        """Checks a paste operation can be undone."""
        timeline = self.timeline_container.timeline
        project = timeline.ges_timeline.get_asset()

        # Create test clip
        clip = common.create_test_clip(GES.TitleClip)
        clip.props.start = 0
        clip.props.duration = 10
        self.layer.add_clip(clip)
        self.assertEqual(len(self.layer.get_clips()), 1)

        # Select the test clip
        event = mock.Mock()
        event.get_button.return_value = (True, 1)
        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = clip.ui
            clip.ui.timeline._button_press_event_cb(None, event)
        clip.ui._button_release_event_cb(None, event)

        self.timeline_container.copy_action.activate()

        position = 10
        project.pipeline.get_position = mock.Mock(return_value=position)
        self.timeline_container.paste_action.activate()
        self.assertEqual(len(self.layer.get_clips()), 2)

        self.action_log.undo()
        self.assertEqual(len(self.layer.get_clips()), 1)

        self.action_log.redo()
        self.assertEqual(len(self.layer.get_clips()), 2)


class TestControlSourceObserver(common.TestCase):

    @common.setup_timeline
    def test_control_source_value_added(self):
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip = asset.extract()
        self.layer.add_clip(clip)
        source = self.get_clip_element(clip, GES.VideoUriSource)

        control_source = GstController.InterpolationControlSource()
        control_source.props.mode = GstController.InterpolationMode.LINEAR
        self.assert_control_source_values(control_source, [], [])

        source.set_control_source(control_source, "alpha", "direct")
        self.assert_control_source_values(control_source, [1, 1], [0, 2003000000])

        with self.action_log.started("keyframe added"):
            self.assertTrue(control_source.set(Gst.SECOND * 0.5, 0.2))
        self.assert_control_source_values(control_source, [1, 0.2, 1], [0, Gst.SECOND * 0.5, 2003000000])

        self.action_log.undo()
        self.assert_control_source_values(control_source, [1, 1], [0, 2003000000])

        self.action_log.redo()
        self.assert_control_source_values(control_source, [1, 0.2, 1], [0, Gst.SECOND * 0.5, 2003000000])

    @common.setup_timeline
    def test_control_source_value_removed(self):
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip = asset.extract()
        self.layer.add_clip(clip)
        source = self.get_clip_element(clip, GES.VideoUriSource)

        control_source = GstController.InterpolationControlSource()
        control_source.props.mode = GstController.InterpolationMode.LINEAR
        self.assert_control_source_values(control_source, [], [])

        source.set_control_source(control_source, "alpha", "direct")
        self.assert_control_source_values(control_source, [1, 1], [0, 2003000000])

        self.assertTrue(control_source.set(Gst.SECOND * 0.5, 0.2))
        self.assert_control_source_values(control_source, [1, 0.2, 1], [0, Gst.SECOND * 0.5, 2003000000])

        with self.action_log.started("keyframe removed"):
            self.assertTrue(control_source.unset(Gst.SECOND * 0.5))
        self.assert_control_source_values(control_source, [1, 1], [0, 2003000000])

        self.action_log.undo()
        self.assert_control_source_values(control_source, [1, 0.2, 1], [0, Gst.SECOND * 0.5, 2003000000])

        self.action_log.redo()
        self.assert_control_source_values(control_source, [1, 1], [0, 2003000000])

    @common.setup_timeline
    def test_control_source_value_changed(self):
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip = asset.extract()
        self.layer.add_clip(clip)
        source = self.get_clip_element(clip, GES.VideoUriSource)

        control_source = GstController.InterpolationControlSource()
        control_source.props.mode = GstController.InterpolationMode.LINEAR
        self.assert_control_source_values(control_source, [], [])

        source.set_control_source(control_source, "alpha", "direct")
        self.assert_control_source_values(control_source, [1, 1], [0, 2003000000])

        self.assertTrue(control_source.set(Gst.SECOND * 0.5, 0.2))
        self.assert_control_source_values(control_source, [1, 0.2, 1], [0, Gst.SECOND * 0.5, 2003000000])

        with self.action_log.started("keyframe changed"):
            self.assertTrue(control_source.set(Gst.SECOND * 0.5, 0.9))
        self.assert_control_source_values(control_source, [1, 0.9, 1], [0, Gst.SECOND * 0.5, 2003000000])

        self.action_log.undo()
        self.assert_control_source_values(control_source, [1, 0.2, 1], [0, Gst.SECOND * 0.5, 2003000000])

        self.action_log.redo()
        self.assert_control_source_values(control_source, [1, 0.9, 1], [0, Gst.SECOND * 0.5, 2003000000])


class TestTrackElementObserver(common.TestCase):

    def assert_effects(self, clip, *effects):
        # Make sure there are no other effects.
        actual_effects = set()
        for track_element in clip.get_children(recursive=True):
            if isinstance(track_element, GES.BaseEffect):
                actual_effects.add(track_element)
        self.assertEqual(actual_effects, set(effects))

        # Make sure their order is correct.
        indexes = [clip.get_top_effect_index(effect)
                   for effect in effects]
        self.assertEqual(indexes, list(range(len(effects))))

    @common.setup_timeline
    def test_effects_index(self):
        stacks = []
        self.action_log.connect("commit", common.TestCase.commit_cb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        effect2 = GES.Effect.new("edgetv")
        clip1.add(effect1)
        clip1.add(effect2)
        self.assert_effects(clip1, effect1, effect2)

        with self.action_log.started("move effect"):
            assert clip1.set_top_effect_index(effect2, 0)

        self.assertEqual(len(stacks), 1)
        self.assert_effects(clip1, effect2, effect1)

        self.action_log.undo()
        self.assert_effects(clip1, effect1, effect2)

        self.action_log.redo()
        self.assert_effects(clip1, effect2, effect1)

    @common.setup_timeline
    def test_effects_index_with_removal(self):
        stacks = []
        self.action_log.connect("commit", common.TestCase.commit_cb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        effect2 = GES.Effect.new("dicetv")
        effect3 = GES.Effect.new("edgetv")
        with self.action_log.started("Add effect1"):
            clip1.add(effect1)
        with self.action_log.started("Add effect2"):
            clip1.add(effect2)
        with self.action_log.started("Add effect3"):
            clip1.add(effect3)
        self.assert_effects(clip1, effect1, effect2, effect3)
        self.action_log.undo()
        self.assert_effects(clip1, effect1, effect2)
        self.action_log.redo()
        self.assert_effects(clip1, effect1, effect2, effect3)

        with self.action_log.started("Remove effect"):
            assert clip1.remove(effect2)
        self.assertEqual(len(stacks), 4)
        self.assert_effects(clip1, effect1, effect3)

        self.action_log.undo()
        self.assert_effects(clip1, effect1, effect2, effect3)

        self.action_log.redo()
        self.assert_effects(clip1, effect1, effect3)

        self.action_log.undo()
        self.assert_effects(clip1, effect1, effect2, effect3)
        self.action_log.undo()
        self.assert_effects(clip1, effect1, effect2)
        self.action_log.undo()
        self.assert_effects(clip1, effect1)
        self.action_log.undo()
        self.assert_effects(clip1)

        self.action_log.redo()
        self.assert_effects(clip1, effect1)
        self.action_log.redo()
        self.assert_effects(clip1, effect1, effect2)
        self.action_log.redo()
        self.assert_effects(clip1, effect1, effect2, effect3)
        self.action_log.redo()
        self.assert_effects(clip1, effect1, effect3)

        self.action_log.undo()
        self.assert_effects(clip1, effect1, effect2, effect3)
        self.action_log.redo()
        self.assert_effects(clip1, effect1, effect3)


class TestTimelineElementObserver(common.TestCase):

    @common.setup_timeline
    def test_track_element_property_changed(self):
        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        with self.action_log.started("Title text change"):
            source = clip1.get_children(False)[0]
            source.set_child_property("text", "pigs fly!")
            self.assertEqual(source.get_child_property("text")[1], "pigs fly!")

        self.action_log.undo()
        self.assertEqual(source.get_child_property("text")[1], "")
        self.action_log.redo()
        self.assertEqual(source.get_child_property("text")[1], "pigs fly!")

    @common.setup_timeline
    def test_add_effect_change_property(self):
        stacks = []
        self.action_log.connect("commit", common.TestCase.commit_cb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        with self.action_log.started("add effect"):
            clip1.add(effect1)

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions), stack.done_actions)
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, TrackElementAdded))

        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        with self.action_log.started("change child property"):
            effect1.set_child_property("scratch-lines", 0)
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 0)

        # Undo effect property change.
        self.action_log.undo()
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 7)

        # Redo effect property change.
        self.action_log.redo()
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 0)

        # Undo effect property change.
        self.action_log.undo()
        self.assertTrue(effect1 in clip1.get_children(True))

        # Undo effect add.
        self.action_log.undo()
        self.assertFalse(effect1 in clip1.get_children(True))

        # Redo effect add.
        self.action_log.redo()
        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 7)

        # Redo effect property change.
        self.action_log.redo()
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 0)


class TestGObjectObserver(common.TestCase):

    @common.setup_timeline
    def test_clip_property_change(self):
        stacks = []
        self.action_log.connect("commit", common.TestCase.commit_cb, stacks)

        # We are not dropping clips here...
        self.app.gui.editor.timeline_ui.timeline.dropping_clips = False

        clip1 = GES.TitleClip()
        clip1.set_start(5 * Gst.SECOND)
        clip1.set_duration(20 * Gst.SECOND)
        self.layer.add_clip(clip1)
        with self.action_log.started("modify clip"):
            clip1.set_start(10 * Gst.SECOND)

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions))
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, PropertyChangedAction))
        self.assertEqual(10 * Gst.SECOND, clip1.get_start())

        self.action_log.undo()
        self.assertEqual(5 * Gst.SECOND, clip1.get_start())
        self.action_log.redo()
        self.assertEqual(10 * Gst.SECOND, clip1.get_start())

        clip1.set_priority(10)
        with self.action_log.started("priority change"):
            clip1.set_priority(20)

        self.assertEqual(20, clip1.get_priority())
        self.action_log.undo()
        self.assertEqual(10, clip1.get_priority())
        self.action_log.redo()
        self.assertEqual(20, clip1.get_priority())

    @common.setup_timeline
    def test_effect_toggling(self):
        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        with self.action_log.started("add effect"):
            clip1.add(effect1)
        self.assertTrue(effect1.props.active)
        self.assert_effect_count(clip1, 1)

        with self.action_log.started("toggle effect"):
            effect1.props.active = False
        self.assertFalse(effect1.props.active)

        with self.action_log.started("remove effect"):
            clip1.remove(effect1)
        self.assert_effect_count(clip1, 0)

        # Undo effect removing.
        self.action_log.undo()
        self.assert_effect_count(clip1, 1)

        # Undo effect toggling.
        self.action_log.undo()
        self.assertTrue(effect1.props.active)

        # Redo effect toggling.
        self.action_log.redo()
        self.assertFalse(effect1.props.active)

        # Undo effect toggling.
        self.action_log.undo()
        self.assertTrue(effect1.props.active)

        # Undo effect add.
        self.action_log.undo()
        self.assertFalse(effect1 in clip1.get_children(True))

        # Redo effect add.
        self.action_log.redo()
        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertTrue(effect1.props.active)

        # Redo effect toggling.
        self.action_log.redo()
        self.assertFalse(effect1.props.active)


class TestDragDropUndo(common.TestCase):

    def clip_dragged_to_create_layer(self, below):
        """Simulates dragging a clip on a separator, without dropping it."""
        timeline_ui = self.timeline_container.timeline
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)

        clip = GES.TitleClip()
        self.layer.add_clip(clip)

        # Drag a clip on a separator to create a layer.
        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = clip.ui

            event = mock.Mock()
            event.x = 0
            event.get_button.return_value = True, 1
            timeline_ui._button_press_event_cb(None, event)

            def translate_coordinates_func(widget, x, y):
                return x, y
            clip.ui.translate_coordinates = translate_coordinates_func
            event = mock.Mock()
            event.get_state.return_value = Gdk.ModifierType.BUTTON1_MASK
            event.x = 1
            if below:
                event.y = LAYER_HEIGHT * 2
            else:
                event.y = -1
            event.get_button.return_value = True, 1
            timeline_ui._motion_notify_event_cb(None, event)

        return clip, event, timeline_ui

    @common.setup_timeline
    def test_clip_dragged_to_create_layer_below_denied(self):
        """Checks clip dropped onto the separator below without hovering."""
        clip, event, timeline_ui = self.clip_dragged_to_create_layer(True)

        timeline_ui._button_release_event_cb(None, event)

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])

        stack = self.action_log.undo_stacks[0]
        # Only the clip creation action should be on the stack.
        self.assertEqual(len(stack.done_actions), 1, stack.done_actions)

    @common.setup_timeline
    def test_clip_dragged_to_create_layer_below(self):
        """Checks clip dropped onto the separator below after hovering."""
        clip, event, timeline_ui = self.clip_dragged_to_create_layer(True)

        timeline_ui._separator_accepting_drop_timeout_cb()
        timeline_ui._button_release_event_cb(None, event)

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [])
        self.assertEqual(layers[1].get_clips(), [clip])

        self.action_log.undo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])

        self.action_log.redo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [])
        self.assertEqual(layers[1].get_clips(), [clip])

    @common.setup_timeline
    def test_clip_dragged_to_create_layer_above_denied(self):
        """Checks clip dropped onto the separator above without hovering."""
        clip, event, timeline_ui = self.clip_dragged_to_create_layer(False)

        timeline_ui._button_release_event_cb(None, event)

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])

        stack = self.action_log.undo_stacks[0]
        # Only the clip creation action should be on the stack.
        self.assertEqual(len(stack.done_actions), 1, stack.done_actions)

    @common.setup_timeline
    def test_clip_dragged_to_create_layer_above(self):
        """Checks clip dropped onto the separator above after hovering."""
        clip, event, timeline_ui = self.clip_dragged_to_create_layer(False)

        timeline_ui._separator_accepting_drop_timeout_cb()
        timeline_ui._button_release_event_cb(None, event)

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[1], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])
        self.assertEqual(layers[1].get_clips(), [])

        self.action_log.undo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])

        self.action_log.redo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[1], self.layer)
        self.assert_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])
        self.assertEqual(layers[1].get_clips(), [])

    @common.setup_timeline
    def test_media_library_asset_dragged_on_separator(self):
        """Simulate dragging an asset from the media library to the timeline."""
        timeline_ui = self.timeline_container.timeline
        project = self.app.project_manager.current_project
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)

        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        self.assertTrue(project.add_asset(asset))

        # Events emitted while dragging an asset on a separator in the timeline:
        # motion, receive, motion, leave, drop.
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
                selection_data.get_uris.return_value = [asset.props.id]
                self.assertIsNone(timeline_ui.drop_data)
                self.assertFalse(timeline_ui.drop_data_ready)
                timeline_ui._drag_data_received_cb(None, None, 0, 0, selection_data, None, 0)
                self.assertEqual(timeline_ui.drop_data, [asset.props.id])
                self.assertTrue(timeline_ui.drop_data_ready)

                timeline_ui.drag_get_data.reset_mock()
                self.assertIsNone(timeline_ui.dragging_element)
                self.assertFalse(timeline_ui.dropping_clips)

                def translate_coordinates_func(widget, x, y):
                    return x, y
                timeline_ui.translate_coordinates = translate_coordinates_func
                timeline_ui._drag_motion_cb(timeline_ui, None, 0, LAYER_HEIGHT * 2, 0)
                self.assertFalse(timeline_ui.drag_get_data.called)
                self.assertIsNotNone(timeline_ui.dragging_element)
                self.assertTrue(timeline_ui.dropping_clips)

                timeline_ui._drag_leave_cb(None, None, None)
                self.assertIsNone(timeline_ui.dragging_element)
                self.assertFalse(timeline_ui.dropping_clips)

                timeline_ui._drag_drop_cb(None, None, 0, 0, 0)

        # A clip has been created on a new layer below the existing layer.
        layers = self.timeline.get_layers()
        self.assertEqual(layers[0], self.layer)
        self.assertEqual(layers[0].get_clips(), [])
        self.assertEqual(len(layers), 2)
        self.assertEqual(len(layers[1].get_clips()), 1)

        self.action_log.undo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0], self.layer)
        self.assertEqual(layers[0].get_clips(), [])

        self.action_log.redo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.assertEqual(layers[0].get_clips(), [])
        self.assertEqual(len(layers[1].get_clips()), 1)
