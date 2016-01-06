# -*- coding: utf-8 -*-
#
#       tests/test_undo_timeline.py
#
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

from unittest import TestCase

from gi.repository import GES
from gi.repository import Gst

from tests import common

from pitivi.undo.timeline import TimelineLogObserver, \
    ClipAdded, ClipRemoved, \
    ClipPropertyChanged, TrackElementAdded
from pitivi.undo.undo import UndoableActionLog
from pitivi.application import Pitivi


class TimelineLogObserverSpy(TimelineLogObserver):

    def _connectToTimeline(self, timeline):
        TimelineLogObserver._connectToTimeline(self, timeline)
        timeline.connected = True

    def _disconnectFromTimeline(self, timeline):
        TimelineLogObserver._disconnectFromTimeline(self, timeline)
        timeline.connected = False

    def _connectToClip(self, clip):
        TimelineLogObserver._connectToClip(self, clip)
        clip.connected = True

    def _disconnectFromClip(self, clip):
        TimelineLogObserver._disconnectFromClip(self, clip)
        clip.connected = False

    def _connectToTrackElement(self, track_element):
        TimelineLogObserver._connectToTrackElement(self, track_element)
        track_element.connected = True

    def _disconnectFromTrackElement(self, track_element):
        TimelineLogObserver._disconnectFromTrackElement(self, track_element)
        track_element.connected = False


class TestTimelineLogObserver(TestCase):

    def setUp(self):
        self.action_log = UndoableActionLog()
        self.observer = TimelineLogObserverSpy(self.action_log)

    def testConnectionAndDisconnection(self):
        timeline = GES.Timeline.new_audio_video()
        layer = GES.Layer()
        timeline.add_layer(layer)
        self.observer.startObserving(timeline)
        self.assertTrue(timeline.connected)

        clip1 = GES.TitleClip()

        layer.add_clip(clip1)
        track_element1 = clip1.get_children(False)[0]
        self.assertTrue(timeline.connected)
        self.assertTrue(clip1.connected)
        self.assertTrue(track_element1.connected)

        layer.remove_clip(clip1)
        self.assertTrue(timeline.connected)
        self.assertFalse(clip1.connected)
        self.assertFalse(track_element1.connected)

        layer.add_clip(clip1)
        track_element2 = clip1.get_children(False)[0]
        self.assertTrue(timeline.connected)
        self.assertTrue(clip1.connected)
        self.assertFalse(track_element1.connected)
        self.assertTrue(track_element2.connected)

        self.observer.stopObserving(timeline)
        self.assertFalse(timeline.connected)
        self.assertFalse(clip1.connected)
        self.assertFalse(track_element1.connected)
        self.assertFalse(track_element2.connected)


class TestTimelineUndo(TestCase):

    def setUp(self):
        app = Pitivi()
        app._startupCb(app)
        app.project_manager.newBlankProject()

        self.timeline = app.project_manager.current_project.timeline
        self.layer = GES.Layer()
        self.timeline.add_layer(self.layer)
        self.action_log = UndoableActionLog()
        self.observer = TimelineLogObserverSpy(self.action_log)
        self.observer.startObserving(self.timeline)

    def getTimelineClips(self):
        for layer in self.timeline.layers:
            for clip in layer.get_clips():
                yield clip

    @staticmethod
    def commitCb(action_log, stack, nested, stacks):
        stacks.append(stack)

    def testAddClip(self):
        stacks = []
        self.action_log.connect("commit", TestTimelineUndo.commitCb, stacks)

        clip1 = GES.TitleClip()
        self.action_log.begin("add clip")
        self.layer.add_clip(clip1)
        self.action_log.commit()

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions))
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, ClipAdded))
        self.assertTrue(clip1 in self.getTimelineClips())

        self.action_log.undo()
        self.assertFalse(clip1 in self.getTimelineClips())

        self.action_log.redo()
        self.assertTrue(clip1 in self.getTimelineClips())

    def testRemoveClip(self):
        stacks = []
        self.action_log.connect("commit", TestTimelineUndo.commitCb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)
        self.action_log.begin("remove clip")
        self.layer.remove_clip(clip1)
        self.action_log.commit()

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

    def testAddEffectToClip(self):
        stacks = []
        self.action_log.connect("commit", TestTimelineUndo.commitCb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        self.action_log.begin("add effect")
        clip1.add(effect1)
        self.action_log.commit()

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
        self.action_log.connect("commit", TestTimelineUndo.commitCb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        self.action_log.begin("add effect")
        clip1.add(effect1)
        self.action_log.commit()

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions), stack.done_actions)
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, TrackElementAdded))

        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        self.action_log.begin("remove effect")
        clip1.remove(effect1)
        self.action_log.commit()

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

    def testChangeEffectProperty(self):
        stacks = []
        self.action_log.connect("commit", TestTimelineUndo.commitCb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)

        effect1 = GES.Effect.new("agingtv")
        self.action_log.begin("add effect")
        clip1.add(effect1)
        self.action_log.commit()

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions), stack.done_actions)
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, TrackElementAdded))

        self.assertTrue(effect1 in clip1.get_children(True))
        self.assertEqual(1, len([effect for effect in
                                 clip1.get_children(True)
                                 if isinstance(effect, GES.Effect)]))

        self.action_log.begin("change child property")
        effect1.set_child_property("scratch-lines", 0)
        self.action_log.commit()

        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 0)
        self.action_log.undo()
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 7)
        self.action_log.redo()
        self.assertEqual(effect1.get_child_property("scratch-lines")[1], 0)
        self.action_log.undo()
        self.assertTrue(effect1 in clip1.get_children(True))
        self.action_log.undo()
        self.assertFalse(effect1 in clip1.get_children(True))

    def testClipPropertyChange(self):
        stacks = []
        self.action_log.connect("commit", TestTimelineUndo.commitCb, stacks)

        clip1 = GES.TitleClip()
        self.layer.add_clip(clip1)
        clip1.set_start(5 * Gst.SECOND)
        clip1.set_duration(20 * Gst.SECOND)
        self.layer.add_clip(clip1)
        self.action_log.begin("modify clip")
        clip1.set_start(10 * Gst.SECOND)
        self.action_log.commit()

        self.assertEqual(1, len(stacks))
        stack = stacks[0]
        self.assertEqual(1, len(stack.done_actions))
        action = stack.done_actions[0]
        self.assertTrue(isinstance(action, ClipPropertyChanged))
        self.assertEqual(10 * Gst.SECOND, clip1.get_start())

        self.action_log.undo()
        self.assertEqual(5 * Gst.SECOND, clip1.get_start())
        self.action_log.redo()
        self.assertEqual(10 * Gst.SECOND, clip1.get_start())

        clip1.set_priority(10)
        self.action_log.begin("priority change")
        clip1.set_priority(20)
        self.action_log.commit()

        self.assertEqual(20, clip1.get_priority())
        self.action_log.undo()
        self.assertEqual(10, clip1.get_priority())
        self.action_log.redo()
        self.assertEqual(20, clip1.get_priority())

    def testUngroup(self):
        uri = common.getSampleUri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        clip1 = asset.extract()
        self.layer.add_clip(clip1)

        clip1.set_start(5 * Gst.SECOND)
        clip1.set_duration(0.5 * Gst.SECOND)
        timeline_clips = list(self.getTimelineClips())
        self.assertEqual(1, len(timeline_clips), timeline_clips)
        self.assertEqual(5 * Gst.SECOND, timeline_clips[0].get_start())
        self.assertEqual(0.5 * Gst.SECOND, timeline_clips[0].get_duration())

        self.action_log.begin("ungroup")
        ungrouped = GES.Container.ungroup(clip1, False)
        self.assertEqual(2, len(ungrouped), ungrouped)
        self.action_log.commit()
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

        self.action_log.begin("split clip")
        clip1 = clip.split(10 * Gst.SECOND)
        self.assertEqual(2, len(self.layer.get_clips()))
        self.action_log.commit()

        self.action_log.begin("split clip")
        clip2 = clip1.split(15 * Gst.SECOND)
        self.assertEqual(3, len(self.layer.get_clips()))
        self.action_log.commit()

        self.action_log.undo()
        self.assertEqual(2, len(self.layer.get_clips()))
        self.action_log.undo()
        self.assertEqual(1, len(self.layer.get_clips()))

        self.action_log.redo()
        self.assertEqual(2, len(self.layer.get_clips()))
        self.action_log.redo()
        self.assertEqual(3, len(self.layer.get_clips()))
