# PiTiVi , Non-linear video editor
#
#       tests/test_timeline_undo.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from unittest import TestCase

import gobject
gobject.threads_init()
import gst

from pitivi.timeline.timeline import Timeline, TimelineObject
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.factories.test import VideoTestSourceFactory
from pitivi.stream import VideoStream
from pitivi.timeline.timeline_undo import TimelineLogObserver, \
        TimelineObjectAdded, TimelineObjectRemoved, \
        TimelineObjectPropertyChanged
from pitivi.undo import UndoableActionLog

class TestTimelineLogObserver(TimelineLogObserver):
    def _connectToTimeline(self, timeline):
        TimelineLogObserver._connectToTimeline(self, timeline)
        timeline.connected = True

    def _disconnectFromTimeline(self, timeline):
        TimelineLogObserver._disconnectFromTimeline(self, timeline)
        timeline.connected = False

    def _connectToTimelineObject(self, timeline_object):
        TimelineLogObserver._connectToTimelineObject(self, timeline_object)
        timeline_object.connected = True
    
    def _disconnectFromTimelineObject(self, timeline_object):
        TimelineLogObserver._disconnectFromTimelineObject(self, timeline_object)
        timeline_object.connected = False

def new_stream():
    return VideoStream(gst.Caps("video/x-raw-rgb"))

def new_factory():
    return VideoTestSourceFactory()

class TestTimelineLogObserverConnections(TestCase):
    def setUp(self):
        self.action_log = UndoableActionLog()
        self.observer = TestTimelineLogObserver(self.action_log)

    def testConnectionAndDisconnection(self):
        timeline = Timeline()
        stream = new_stream()
        factory = new_factory()
        track = Track(stream)
        track_object1 = SourceTrackObject(factory, stream)
        track.addTrackObject(track_object1)
        timeline.addTrack(track)
        timeline_object1 = TimelineObject(factory)
        timeline_object1.addTrackObject(track_object1)
        timeline.addTimelineObject(timeline_object1)

        self.observer.startObserving(timeline)
        self.failUnless(timeline.connected)
        self.failUnless(timeline_object1.connected)

        timeline.removeTimelineObject(timeline_object1)
        self.failIf(timeline_object1.connected)

        timeline.addTimelineObject(timeline_object1)
        self.failUnless(timeline_object1)

        self.observer.stopObserving(timeline)
        self.failIf(timeline.connected)
        self.failIf(timeline_object1.connected)

class  TestTimelineUndo(TestCase):
    def setUp(self):
        self.stream = new_stream()
        self.factory = new_factory()
        self.track1 = Track(self.stream)
        self.track2 = Track(self.stream)
        self.timeline = Timeline()
        self.timeline.addTrack(self.track1)
        self.timeline.addTrack(self.track2)
        self.track_object1 = SourceTrackObject(self.factory, self.stream)
        self.track_object2 = SourceTrackObject(self.factory, self.stream)
        self.track1.addTrackObject(self.track_object1)
        self.track2.addTrackObject(self.track_object2)
        self.timeline_object1 = TimelineObject(self.factory)
        self.timeline_object1.addTrackObject(self.track_object1)
        self.timeline_object1.addTrackObject(self.track_object2)
        self.action_log = UndoableActionLog()
        self.observer = TestTimelineLogObserver(self.action_log)
        self.observer.startObserving(self.timeline)

    def testAddTimelineObject(self):
        stacks = []
        def commitCb(action_log, stack, nested):
            stacks.append(stack)
        self.action_log.connect("commit", commitCb)

        self.action_log.begin("add clip")
        self.timeline.addTimelineObject(self.timeline_object1)
        self.action_log.commit()

        self.failUnlessEqual(len(stacks), 1)
        stack = stacks[0]
        self.failUnlessEqual(len(stack.done_actions), 1)
        action = stack.done_actions[0]
        self.failUnless(isinstance(action, TimelineObjectAdded))

        self.failUnless(self.timeline_object1 \
                in self.timeline.timeline_objects)
        self.action_log.undo()
        self.failIf(self.timeline_object1 \
                in self.timeline.timeline_objects)

        self.action_log.redo()
        self.failUnless(self.timeline_object1 \
                in self.timeline.timeline_objects)

    def testRemoveTimelineObject(self):
        stacks = []
        def commitCb(action_log, stack, nested):
            stacks.append(stack)
        self.action_log.connect("commit", commitCb)

        self.timeline.addTimelineObject(self.timeline_object1)
        self.action_log.begin("remove clip")
        self.timeline.removeTimelineObject(self.timeline_object1)
        self.action_log.commit()

        self.failUnlessEqual(len(stacks), 1)
        stack = stacks[0]
        self.failUnlessEqual(len(stack.done_actions), 1)
        action = stack.done_actions[0]
        self.failUnless(isinstance(action, TimelineObjectRemoved))

        self.failIf(self.timeline_object1 \
                in self.timeline.timeline_objects)
        self.action_log.undo()
        self.failUnless(self.timeline_object1 \
                in self.timeline.timeline_objects)

        self.action_log.redo()
        self.failIf(self.timeline_object1 \
                in self.timeline.timeline_objects)

    def testTimelineObjectPropertyChange(self):
        stacks = []
        def commitCb(action_log, stack, nested):
            stacks.append(stack)
        self.action_log.connect("commit", commitCb)

        self.timeline_object1.start = 5 * gst.SECOND
        self.timeline_object1.duration = 20 * gst.SECOND
        self.timeline.addTimelineObject(self.timeline_object1)
        self.action_log.begin("modify clip")
        self.timeline_object1.start = 10 * gst.SECOND
        self.action_log.commit()

        self.failUnlessEqual(len(stacks), 1)
        stack = stacks[0]
        self.failUnlessEqual(len(stack.done_actions), 1)
        action = stack.done_actions[0]
        self.failUnless(isinstance(action, TimelineObjectPropertyChanged))

        self.failUnlessEqual(self.timeline_object1.start, 10 * gst.SECOND)
        self.action_log.undo()
        self.failUnlessEqual(self.timeline_object1.start, 5 * gst.SECOND)
        self.action_log.redo()
        self.failUnlessEqual(self.timeline_object1.start, 10 * gst.SECOND)
