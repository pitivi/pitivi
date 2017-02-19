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
from unittest import mock
from unittest import skip
from unittest import TestCase

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import Gtk

from pitivi.timeline.layer import Layer
from pitivi.timeline.timeline import Timeline
from pitivi.timeline.timeline import TimelineContainer
from pitivi.undo.project import AssetAddedAction
from pitivi.undo.timeline import ClipAdded
from pitivi.undo.timeline import ClipRemoved
from pitivi.undo.timeline import TrackElementAdded
from pitivi.undo.undo import PropertyChangedAction
from pitivi.utils.ui import LAYER_HEIGHT
from pitivi.utils.ui import URI_TARGET_ENTRY
from tests import common


class BaseTestUndoTimeline(TestCase):

    def setUp(self):
        self.app = common.create_pitivi()
        self.app.project_manager.newBlankProject()

        self.timeline = self.app.project_manager.current_project.ges_timeline
        self.layer = self.timeline.append_layer()
        self.action_log = self.app.action_log

    def setup_timeline_container(self):
        project = self.app.project_manager.current_project
        self.timeline_container = TimelineContainer(self.app)
        self.timeline_container.setProject(project)

        timeline = self.timeline_container.timeline
        timeline.app.project_manager.current_project = project
        timeline.get_parent = mock.MagicMock(return_value=self.timeline_container)

    def getTimelineClips(self):
        for layer in self.timeline.layers:
            for clip in layer.get_clips():
                yield clip

    @staticmethod
    def commit_cb(action_log, stack, stacks):
        stacks.append(stack)

    def _wait_until_project_loaded(self):
        # Run the mainloop so the project is set up properly so that
        # the timeline creates transitions automatically.
        mainloop = common.create_main_loop()

        def projectLoadedCb(unused_project, unused_timeline):
            mainloop.quit()
        self.app.project_manager.current_project.connect("loaded", projectLoadedCb)
        mainloop.run()
        self.assertTrue(self.timeline.props.auto_transition)

    def assert_effect_count(self, clip, count):
        effects = [effect for effect in clip.get_children(True)
                   if isinstance(effect, GES.Effect)]
        self.assertEqual(len(effects), count)

    def get_transition_element(self, ges_layer):
        """"Gets the first found GES.VideoTransition clip."""
        for clip in ges_layer.get_clips():
            if isinstance(clip, GES.TransitionClip):
                for element in clip.get_children(False):
                    if isinstance(element, GES.VideoTransition):
                        return element

    def check_layers(self, layers):
        self.assertEqual(self.timeline.get_layers(), layers)
        # Import TestLayers locally, otherwise its tests are discovered and
        # run twice.
        from tests.test_timeline_timeline import TestLayers
        TestLayers.check_priorities_and_positions(self, self.timeline.ui, layers, list(range(len(layers))))


class TestTimelineObserver(BaseTestUndoTimeline):

    def test_layer_removed(self):
        self.setup_timeline_container()

        layer1 = self.layer
        layer2 = self.timeline.append_layer()
        layer3 = self.timeline.append_layer()
        self.check_layers([layer1, layer2, layer3])
        self.check_removal(self.timeline.get_layers())

    def check_removal(self, ges_layers):
        if len(ges_layers) == 1:
            # We don't support removing the last remaining layer.
            return
        for ges_layer in ges_layers:
            remaining_layers = list(ges_layers)
            remaining_layers.remove(ges_layer)

            ges_layer.control_ui.delete_layer_action.activate(None)
            self.check_layers(remaining_layers)

            self.action_log.undo()
            self.check_layers(ges_layers)

            self.action_log.redo()
            self.check_layers(remaining_layers)

            self.check_removal(remaining_layers)

            self.action_log.undo()
            self.check_layers(ges_layers)

    def test_group_ungroup_clips(self):
        self.setup_timeline_container()

        clip1 = common.create_test_clip(GES.TitleClip)
        clip1.set_start(0 * Gst.SECOND)
        clip1.set_duration(1 * Gst.SECOND)

        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip2 = asset.extract()

        self.layer.add_clip(clip1)
        self.layer.add_clip(clip2)
        # The selection does not care about GES.Groups, only about GES.Clips.
        self.timeline_container.timeline.selection.select([clip1, clip2])

        self.timeline_container.group_action.activate(None)
        self.assertTrue(isinstance(clip1.get_parent(), GES.Group))
        self.assertEqual(clip1.get_parent(), clip2.get_parent())

        self.timeline_container.ungroup_action.activate(None)
        self.assertIsNone(clip1.get_parent())
        self.assertIsNone(clip2.get_parent())

        for i in range(4):
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

    def test_ungroup_group_clip(self):
        self.setup_timeline_container()
        timeline = self.timeline_container.timeline

        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip = asset.extract()
        self.layer.add_clip(clip)
        clips = list(self.getTimelineClips())
        self.assertEqual(len(clips), 1, clips)
        self.assertEqual(len(clips[0].get_children(False)), 2)

        timeline.selection.select([clip])
        timeline.resetSelectionGroup()
        timeline.current_group.add(clip)
        self.timeline_container.ungroup_action.activate(None)
        clips = list(self.getTimelineClips())
        self.assertEqual(len(clips), 2, clips)
        self.assertEqual(len(clips[0].get_children(False)), 1)
        self.assertEqual(len(clips[1].get_children(False)), 1)

        timeline.selection.select(clips)
        timeline.resetSelectionGroup()
        for clip in clips:
            timeline.current_group.add(clip)
        self.timeline_container.group_action.activate(None)
        clips = list(self.getTimelineClips())
        self.assertEqual(len(clips), 1, clips)
        self.assertEqual(len(clips[0].get_children(False)), 2)

        for i in range(2):
            # Undo grouping.
            self.action_log.undo()
            clips = list(self.getTimelineClips())
            self.assertEqual(len(clips), 2, clips)
            self.assertEqual(len(clips[0].get_children(False)), 1)
            self.assertEqual(len(clips[1].get_children(False)), 1)

            # Undo ungrouping.
            self.action_log.undo()
            clips = list(self.getTimelineClips())
            self.assertEqual(len(clips), 1, clips)
            self.assertEqual(len(clips[0].get_children(False)), 2)

            # Redo ungrouping.
            self.action_log.redo()
            clips = list(self.getTimelineClips())
            self.assertEqual(len(clips), 2, clips)
            self.assertEqual(len(clips[0].get_children(False)), 1)
            self.assertEqual(len(clips[1].get_children(False)), 1)

            # Redo grouping.
            self.action_log.redo()
            clips = list(self.getTimelineClips())
            self.assertEqual(len(clips), 1, clips)
            self.assertEqual(len(clips[0].get_children(False)), 2)


class TestLayerObserver(BaseTestUndoTimeline):

    def testLayerMoved(self):
        layer1 = self.layer
        layer2 = self.timeline.append_layer()
        layer3 = self.timeline.append_layer()
        self.assertEqual(self.timeline.get_layers(), [layer1, layer2, layer3])

        timeline_ui = Timeline(app=self.app, size_group=mock.Mock())
        timeline_ui.setProject(self.app.project_manager.current_project)

        # Click and drag a layer control box to move the layer.
        with mock.patch.object(Gtk, 'get_event_widget') as get_event_widget:
            event = mock.Mock()
            event.get_button.return_value = True, 1

            get_event_widget.return_value = layer1.control_ui
            timeline_ui._button_press_event_cb(None, event=event)

            with mock.patch.object(layer1.control_ui, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (0, 0)
                with mock.patch.object(timeline_ui, "_get_layer_at") as _get_layer_at:
                    _get_layer_at.return_value = layer3, None
                    timeline_ui._motion_notify_event_cb(None, event=event)

            timeline_ui._button_release_event_cb(None, event=event)
        self.check_layers([layer2, layer3, layer1])

        self.action_log.undo()
        self.check_layers([layer1, layer2, layer3])

        self.action_log.redo()
        self.check_layers([layer2, layer3, layer1])

    def test_layer_renamed(self):
        layer = Layer(self.layer, timeline=mock.Mock())
        self.assertIsNone(layer._nameIfSet())

        with self.app.action_log.started("change layer name"):
            layer.setName("Beautiful name")
        self.assertEqual(layer._nameIfSet(), "Beautiful name")

        self.action_log.undo()
        self.assertIsNone(layer._nameIfSet())

        self.action_log.redo()
        self.assertEqual(layer._nameIfSet(), "Beautiful name")

    def test_add_clip(self):
        clip1 = GES.TitleClip()
        with self.action_log.started("add clip"):
            self.layer.add_clip(clip1)

        stack, = self.action_log.undo_stacks
        self.assertEqual(len(stack.done_actions), 2, stack.done_actions)
        self.assertTrue(isinstance(stack.done_actions[0], ClipAdded))
        self.assertTrue(clip1 in self.getTimelineClips())

        self.action_log.undo()
        self.assertFalse(clip1 in self.getTimelineClips())

        self.action_log.redo()
        self.assertTrue(clip1 in self.getTimelineClips())

    def testRemoveClip(self):
        stacks = []
        self.action_log.connect("commit", BaseTestUndoTimeline.commit_cb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)
        with self.action_log.started("remove clip"):
            self.layer.remove_clip(clip1)

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions))
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, ClipRemoved))
        self.assertFalse(clip1 in self.getTimelineClips())

        self.action_log.undo()
        self.assertTrue(clip1 in self.getTimelineClips())

        self.action_log.redo()
        self.assertFalse(clip1 in self.getTimelineClips())

    def test_ungroup_group_clip(self):
        # This test is in TestLayerObserver because the relevant operations
        # recorded are clip-added and clip-removed.
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip1 = asset.extract()
        self.layer.add_clip(clip1)

        clip1.set_start(5 * Gst.SECOND)
        clip1.set_duration(0.5 * Gst.SECOND)
        timeline_clips = list(self.getTimelineClips())
        self.assertEqual(1, len(timeline_clips), timeline_clips)
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())

        with self.action_log.started("ungroup"):
            ungrouped = GES.Container.ungroup(clip1, False)
            self.assertEqual(2, len(ungrouped), ungrouped)
        timeline_clips = list(self.getTimelineClips())
        self.assertEqual(2, len(timeline_clips), timeline_clips)
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())
        self.assertEqual(5 * Gst.SECOND, timeline_clips[1].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[1].get_duration())

        self.action_log.undo()
        timeline_clips = list(self.getTimelineClips())
        self.assertEqual(1, len(timeline_clips))
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())

        self.action_log.redo()
        timeline_clips = list(self.getTimelineClips())
        self.assertEqual(2, len(timeline_clips), timeline_clips)
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())
        self.assertEqual(5 * Gst.SECOND, timeline_clips[1].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[1].get_duration())

    def testSplitClip(self):
        clip = GES.TitleClip()
        clip.set_start(0 * Gst.SECOND)
        clip.set_duration(20 * Gst.SECOND)

        self.layer.add_clip(clip)

        with self.action_log.started("split clip"):
            clip1 = clip.split(10 * Gst.SECOND)
            self.assertEqual(2, len(self.layer.get_clips()))

        with self.action_log.started("split clip"):
            clip2 = clip1.split(15 * Gst.SECOND)
            self.assertEqual(3, len(self.layer.get_clips()))

        self.action_log.undo()
        self.assertEqual(2, len(self.layer.get_clips()))
        self.action_log.undo()
        self.assertEqual(1, len(self.layer.get_clips()))

        self.action_log.redo()
        self.assertEqual(2, len(self.layer.get_clips()))
        self.action_log.redo()
        self.assertEqual(3, len(self.layer.get_clips()))

    def testAddEffectToClip(self):
        stacks = []
        self.action_log.connect("commit", BaseTestUndoTimeline.commit_cb, stacks)

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

    def testRemoveEffectFromClip(self):
        stacks = []
        self.action_log.connect("commit", BaseTestUndoTimeline.commit_cb, stacks)

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

        with self.action_log.started("move clip"):
            clip2.set_start(20 * Gst.SECOND)
        self.assertEqual(clip2.get_start(), 20 * Gst.SECOND)
        self.assertEqual(len(self.layer.get_clips()), 2)

        self.action_log.undo()
        self.assertEqual(clip2.get_start(), 5 * Gst.SECOND)
        self.assertEqual(len(self.layer.get_clips()), 3)

        self.action_log.redo()
        self.assertEqual(clip2.get_start(), 20 * Gst.SECOND)
        self.assertEqual(len(self.layer.get_clips()), 2)

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
        clip2.set_duration(10 * Gst.SECOND)
        with self.action_log.started("add second clip"):
            self.layer.add_clip(clip2)

        # Make sure the transition asset is ignored.
        stack, = self.action_log.undo_stacks
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


class TestControlSourceObserver(BaseTestUndoTimeline):

    def testControlSourceValueAdded(self):
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip = asset.extract()
        self.layer.add_clip(clip)
        source = clip.get_children(False)[1]
        self.assertTrue(isinstance(source, GES.VideoUriSource))

        control_source = GstController.InterpolationControlSource()
        control_source.props.mode = GstController.InterpolationMode.LINEAR
        source.set_control_source(control_source, "alpha", "direct")

        with self.action_log.started("keyframe added"):
            self.assertTrue(control_source.set(Gst.SECOND * 0.5, 0.2))

        self.assertEqual(1, len(control_source.get_all()))
        self.action_log.undo()
        self.assertEqual(0, len(control_source.get_all()))
        self.action_log.redo()
        keyframes = control_source.get_all()
        self.assertEqual(1, len(keyframes))
        self.assertEqual(Gst.SECOND * 0.5, keyframes[0].timestamp)
        self.assertEqual(0.2, keyframes[0].value)

    def testControlSourceValueRemoved(self):
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip = asset.extract()
        self.layer.add_clip(clip)
        source = clip.get_children(False)[1]
        self.assertTrue(isinstance(source, GES.VideoUriSource))

        control_source = GstController.InterpolationControlSource()
        control_source.props.mode = GstController.InterpolationMode.LINEAR
        source.set_control_source(control_source, "alpha", "direct")
        self.assertTrue(control_source.set(Gst.SECOND * 0.5, 0.2))

        with self.action_log.started("keyframe removed"):
            self.assertTrue(control_source.unset(Gst.SECOND * 0.5))

        self.assertEqual(0, len(control_source.get_all()))
        self.action_log.undo()
        keyframes = control_source.get_all()
        self.assertEqual(1, len(keyframes))
        self.assertEqual(Gst.SECOND * 0.5, keyframes[0].timestamp)
        self.assertEqual(0.2, keyframes[0].value)
        self.action_log.redo()
        self.assertEqual(0, len(control_source.get_all()))

    def testControlSourceValueChanged(self):
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip = asset.extract()
        self.layer.add_clip(clip)
        source = clip.get_children(False)[1]
        self.assertTrue(isinstance(source, GES.VideoUriSource))

        control_source = GstController.InterpolationControlSource()
        control_source.props.mode = GstController.InterpolationMode.LINEAR
        source.set_control_source(control_source, "alpha", "direct")
        self.assertTrue(control_source.set(Gst.SECOND * 0.5, 0.2))

        with self.action_log.started("keyframe changed"):
            self.assertTrue(control_source.set(Gst.SECOND * 0.5, 0.9))

        self.assertEqual(0.9, control_source.get_all()[0].value)
        self.action_log.undo()
        self.assertEqual(0.2, control_source.get_all()[0].value)
        self.action_log.redo()
        self.assertEqual(0.9, control_source.get_all()[0].value)


class TestTimelineElementObserver(BaseTestUndoTimeline):

    def testTrackElementPropertyChanged(self):
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

    def test_add_effect_change_property(self):
        stacks = []
        self.action_log.connect("commit", BaseTestUndoTimeline.commit_cb, stacks)

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


class TestGObjectObserver(BaseTestUndoTimeline):

    def testClipPropertyChange(self):
        stacks = []
        self.action_log.connect("commit", BaseTestUndoTimeline.commit_cb, stacks)

        # We are not dropping clips here...
        self.app.gui.timeline_ui.timeline.dropping_clips = False

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


class TestDragDropUndo(BaseTestUndoTimeline):

    def test_clip_dragged_to_create_layer_below(self):
        self.setup_timeline_container()
        timeline_ui = self.timeline_container.timeline
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)

        clip = GES.TitleClip()
        self.layer.add_clip(clip)

        # Drag a clip on a separator to create a layer.
        with mock.patch.object(Gtk, 'get_event_widget') as get_event_widget:
            get_event_widget.return_value = clip.ui

            event = mock.Mock()
            event.x = 0
            event.get_button.return_value = True, 1
            timeline_ui._button_press_event_cb(None, event)

            def translate_coordinates(widget, x, y):
                return x, y
            clip.ui.translate_coordinates = translate_coordinates
            event = mock.Mock()
            event.get_state.return_value = Gdk.ModifierType.BUTTON1_MASK
            event.x = 1
            event.y = LAYER_HEIGHT * 2
            event.get_button.return_value = True, 1
            timeline_ui._motion_notify_event_cb(None, event)

        timeline_ui._button_release_event_cb(None, event)

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.check_layers(layers)
        self.assertEqual(layers[0].get_clips(), [])
        self.assertEqual(layers[1].get_clips(), [clip])

        self.action_log.undo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0], self.layer)
        self.check_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])

        self.action_log.redo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.check_layers(layers)
        self.assertEqual(layers[0].get_clips(), [])
        self.assertEqual(layers[1].get_clips(), [clip])

    def test_clip_dragged_to_create_layer_above(self):
        self.setup_timeline_container()
        timeline_ui = self.timeline_container.timeline
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)

        clip = GES.TitleClip()
        self.layer.add_clip(clip)

        # Drag a clip on a separator to create a layer.
        with mock.patch.object(Gtk, 'get_event_widget') as get_event_widget:
            get_event_widget.return_value = clip.ui

            event = mock.Mock()
            event.x = 0
            event.get_button.return_value = True, 1
            timeline_ui._button_press_event_cb(None, event)

            def translate_coordinates(widget, x, y):
                return x, y
            clip.ui.translate_coordinates = translate_coordinates
            event = mock.Mock()
            event.get_state.return_value = Gdk.ModifierType.BUTTON1_MASK
            event.x = 1
            event.y = -1
            event.get_button.return_value = True, 1
            timeline_ui._motion_notify_event_cb(None, event)

        timeline_ui._button_release_event_cb(None, event)

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[1], self.layer)
        self.check_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])
        self.assertEqual(layers[1].get_clips(), [])

        self.action_log.undo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.check_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])

        self.action_log.redo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[1], self.layer)
        self.check_layers(layers)
        self.assertEqual(layers[0].get_clips(), [clip])
        self.assertEqual(layers[1].get_clips(), [])

    def test_media_library_asset_dragged_on_separator(self):
        """Simulate dragging an asset from the media library to the timeline."""
        self.setup_timeline_container()
        timeline_ui = self.timeline_container.timeline
        project = self.app.project_manager.current_project
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)

        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        self.assertTrue(project.add_asset(asset))

        # Events emitted while dragging an asset on a separator in the timeline:
        # motion, receive, motion, leave, drop.
        with mock.patch.object(Gdk, "drag_status") as drag_status_mock:
            with mock.patch.object(Gtk, "drag_finish") as drag_finish_mock:
                target = mock.Mock()
                target.name.return_value = URI_TARGET_ENTRY.target
                timeline_ui.drag_dest_find_target = mock.Mock(return_value=target)
                timeline_ui.drag_get_data = mock.Mock()
                timeline_ui._drag_motion_cb(None, None, 0, 0, 0)
                self.assertTrue(timeline_ui.drag_get_data.called)

                self.assertFalse(timeline_ui.dropDataReady)
                selection_data = mock.Mock()
                selection_data.get_data_type = mock.Mock(return_value=target)
                selection_data.get_uris.return_value = [asset.props.id]
                self.assertIsNone(timeline_ui.dropData)
                self.assertFalse(timeline_ui.dropDataReady)
                timeline_ui._drag_data_received_cb(None, None, 0, 0, selection_data, None, 0)
                self.assertEqual(timeline_ui.dropData, [asset.props.id])
                self.assertTrue(timeline_ui.dropDataReady)

                timeline_ui.drag_get_data.reset_mock()
                self.assertIsNone(timeline_ui.draggingElement)
                self.assertFalse(timeline_ui.dropping_clips)

                def translate_coordinates(widget, x, y):
                    return x, y
                timeline_ui.translate_coordinates = translate_coordinates
                timeline_ui._drag_motion_cb(timeline_ui, None, 0, LAYER_HEIGHT * 2, 0)
                self.assertFalse(timeline_ui.drag_get_data.called)
                self.assertIsNotNone(timeline_ui.draggingElement)
                self.assertTrue(timeline_ui.dropping_clips)

                timeline_ui._drag_leave_cb(None, None, None)
                self.assertIsNone(timeline_ui.draggingElement)
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
