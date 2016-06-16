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
from unittest import TestCase

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import Gtk

from pitivi.timeline.layer import Layer
from pitivi.timeline.timeline import Timeline
from pitivi.undo.project import AssetAddedAction
from pitivi.undo.timeline import ClipAdded
from pitivi.undo.timeline import ClipRemoved
from pitivi.undo.timeline import EffectAddedAction
from pitivi.undo.undo import PropertyChangedAction
from pitivi.utils.ui import CONTROL_WIDTH
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


class TestTimelineObserver(BaseTestUndoTimeline):

    def test_layer_removed(self):
        timeline_ui = Timeline(container=None, app=None)
        timeline_ui.setProject(self.app.project_manager.current_project)

        layer1 = self.layer
        layer2 = self.timeline.append_layer()
        layer3 = self.timeline.append_layer()

        self.assertEqual([layer1, layer2, layer3], self.timeline.get_layers())
        self.assertEqual([l.props.priority for l in [layer1, layer2, layer3]],
                        list(range(3)))

        with self.action_log.started("layer removed"):
            self.timeline.remove_layer(layer2)

        self.assertEqual([layer1, layer3], self.timeline.get_layers())
        self.assertEqual([l.props.priority for l in [layer1, layer3]],
                        list(range(2)))

        self.action_log.undo()
        self.assertEqual([layer1, layer2, layer3], self.timeline.get_layers())
        self.assertEqual([l.props.priority for l in [layer1, layer2, layer3]],
                        list(range(3)))
        self.action_log.redo()
        self.assertEqual([layer1, layer3], self.timeline.get_layers())
        self.assertEqual([l.props.priority for l in [layer1, layer3]],
                        list(range(2)))


class TestLayerObserver(BaseTestUndoTimeline):

    def testLayerMoved(self):
        layer1 = self.layer
        layer2 = self.timeline.append_layer()
        layer3 = self.timeline.append_layer()
        self.assertEqual(self.timeline.get_layers(), [layer1, layer2, layer3])

        timeline_ui = Timeline(container=None, app=self.app)
        timeline_ui.setProject(self.app.project_manager.current_project)

        # Click and drag a layer control box to move the layer.
        with mock.patch.object(timeline_ui, 'get_event_widget') as get_event_widget:
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
        self.assertEqual(self.timeline.get_layers(), [layer2, layer3, layer1])

        self.action_log.undo()
        self.assertEqual(self.timeline.get_layers(), [layer1, layer2, layer3])

        self.action_log.redo()
        self.assertEqual(self.timeline.get_layers(), [layer2, layer3, layer1])

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

    def testAddClip(self):
        stacks = []
        self.action_log.connect("commit", BaseTestUndoTimeline.commit_cb, stacks)

        clip1 = GES.TitleClip()
        with self.action_log.started("add clip"):
            self.layer.add_clip(clip1)

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(2, len(stack.done_actions), stack.done_actions)
        self.assertTrue(isinstance(stack.done_actions[0], ClipAdded))
        self.assertTrue(isinstance(stack.done_actions[1], AssetAddedAction))
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

    def testUngroup(self):
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
        self.assertTrue(isinstance(action, EffectAddedAction))

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
        self.assertTrue(isinstance(action, EffectAddedAction))

        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        with self.action_log.started("remove effect"):
            clip1.remove(effect1)

        self.assertEqual(0, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        self.action_log.undo()
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        self.action_log.redo()
        self.assertEqual(0, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

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

    def testChangeEffectProperty(self):
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
        self.assertTrue(isinstance(action, EffectAddedAction))

        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        with self.action_log.started("change child property"):
            effect1.set_child_property("scratch-lines", 0)

        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 0)
        self.action_log.undo()
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 7)
        self.action_log.redo()
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 0)
        self.action_log.undo()
        self.assertTrue(effect1 in clip1.get_children(True))
        self.action_log.undo()
        self.assertFalse(effect1 in clip1.get_children(True))


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


class TestDragDropUndo(BaseTestUndoTimeline):

    def test_clip_dragged_to_create_layer(self):
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)

        clip = GES.TitleClip()
        self.layer.add_clip(clip)

        timeline_ui = Timeline(None, self.app)
        timeline_ui.setProject(self.app.project_manager.current_project)
        timeline_ui.get_parent = mock.MagicMock()

        # Drag a clip on a separator to create a layer.
        timeline_ui.get_event_widget = mock.Mock(return_value=clip.ui)
        event = mock.Mock()
        event.x = 0
        event.get_button.return_value = True, 1
        timeline_ui._button_press_event_cb(None, event)

        def translate_coordinates(widget, x, y):
            return x, y
        clip.ui.translate_coordinates = translate_coordinates
        event.get_state.return_value = Gdk.ModifierType.BUTTON1_MASK
        event.x = 1
        event.y = LAYER_HEIGHT * 2
        timeline_ui._motion_notify_event_cb(None, event)

        timeline_ui._button_release_event_cb(None, event)

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.assertEqual(layers[0].get_clips(), [])
        self.assertEqual(layers[1].get_clips(), [clip])

        self.action_log.undo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0], self.layer)
        self.assertEqual(layers[0].get_clips(), [clip])

        self.action_log.redo()
        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0], self.layer)
        self.assertEqual(layers[0].get_clips(), [])
        self.assertEqual(layers[1].get_clips(), [clip])

    def test_media_library_asset_dragged_on_separator(self):
        """Simulate dragging an asset from the media library to the timeline."""
        project = self.app.project_manager.current_project

        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        self.assertTrue(project.add_asset(asset))

        timeline_ui = Timeline(container=None, app=self.app)
        timeline_ui.setProject(project)
        timeline_ui.get_parent = mock.MagicMock()
        timeline_ui.parent = mock.MagicMock()

        layers = self.timeline.get_layers()
        self.assertEqual(len(layers), 1)

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
                timeline_ui._drag_motion_cb(None, None, CONTROL_WIDTH, LAYER_HEIGHT * 2, 0)
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
