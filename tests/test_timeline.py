# PiTiVi , Non-linear video editor
#
#       tests/test_timeline.py
#
# Copyright (c) 2008, Alessandro Decina <alessandro.decina@collabora.co.uk>
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
import gst

from pitivi.timeline.timeline import Timeline, TimelineObject, TimelineError, \
        Selection, Link, TimelineEdges
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.stream import AudioStream, VideoStream
from pitivi.utils import UNKNOWN_DURATION

from tests.common import SignalMonitor

class TimelineSignalMonitor(SignalMonitor):
    def __init__(self, track_object):
        SignalMonitor.__init__(self, track_object, 'start-changed',
                'duration-changed', 'in-point-changed', 'out-point-changed')

class StubFactory(object):
    duration = 42 * gst.SECOND

    def makeBin(self, stream=None):
        return gst.element_factory_make('identity')

class TestTimelineObjectAddRemoveTrackObjects(TestCase):
    def testAddRemoveTrackObjects(self):
        factory = StubFactory()
        timeline_object1 = TimelineObject(factory)
        timeline_object2 = TimelineObject(factory)

        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        track = Track(stream)
        track_object1 = SourceTrackObject(factory)
        track_object2 = SourceTrackObject(factory)

        track.addTrackObject(track_object1)
        timeline_object1.addTrackObject(track_object1)

        # can't add twice
        self.failUnlessRaises(TimelineError,
                timeline_object1.addTrackObject, track_object1)

        # can't add to different timeline objects
        self.failUnlessRaises(TimelineError,
                timeline_object2.addTrackObject, track_object1)

        track.addTrackObject(track_object2)
        timeline_object1.addTrackObject(track_object2)

        timeline_object1.removeTrackObject(track_object1)

        # can't remove twice
        self.failUnlessRaises(TimelineError,
                timeline_object1.removeTrackObject, track_object1)

        timeline_object1.removeTrackObject(track_object2)

class TestTimelineObjectProperties(TestCase):
    def setUp(self):
        factory = StubFactory()
        self.timeline_object = TimelineObject(factory)
        self.monitor = SignalMonitor(self.timeline_object, 'start-changed',
                'duration-changed', 'in-point-changed', 'out-point-changed')
        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        self.track = Track(stream)
        self.track_object1 = SourceTrackObject(factory)
        self.track_object2 = SourceTrackObject(factory)
        self.track.addTrackObject(self.track_object1)
        self.track.addTrackObject(self.track_object2)

    def testDefaultProperties(self):
        obj = self.timeline_object
        self.failUnlessEqual(obj.start, 0)
        self.failUnlessEqual(obj.duration, UNKNOWN_DURATION)
        self.failUnlessEqual(obj.in_point, 0)
        self.failUnlessEqual(obj.out_point, UNKNOWN_DURATION)

    def testChangePropertiesFromTimelineObject(self):
        timeline_object = self.timeline_object
        self.track_object1 = self.track_object1
        timeline_object.addTrackObject(self.track_object1)

        start = 1 * gst.SECOND
        timeline_object.start = start
        self.failUnlessEqual(timeline_object.start, start)
        self.failUnlessEqual(self.track_object1.start, start)
        self.failUnlessEqual(self.monitor.start_changed_count, 1)

        duration = 10 * gst.SECOND
        timeline_object.duration = duration
        self.failUnlessEqual(timeline_object.duration, duration)
        self.failUnlessEqual(self.track_object1.duration, duration)
        self.failUnlessEqual(self.monitor.duration_changed_count, 1)

        in_point = 5 * gst.SECOND
        timeline_object.in_point = in_point
        self.failUnlessEqual(timeline_object.in_point, in_point)
        self.failUnlessEqual(self.track_object1.in_point, in_point)
        self.failUnlessEqual(self.monitor.in_point_changed_count, 1)

        out_point = 5 * gst.SECOND
        timeline_object.out_point = out_point
        self.failUnlessEqual(timeline_object.out_point, out_point)
        self.failUnlessEqual(self.track_object1.out_point, out_point)
        self.failUnlessEqual(self.monitor.out_point_changed_count, 1)

    def testChangePropertiesFromTimelineObject2(self):
        timeline_object = self.timeline_object
        self.track_object1 = self.track_object1
        timeline_object.addTrackObject(self.track_object1)
        timeline_object.addTrackObject(self.track_object2)

        start = 1 * gst.SECOND
        timeline_object.start = start
        self.failUnlessEqual(timeline_object.start, start)
        self.failUnlessEqual(self.track_object1.start, start)
        self.failUnlessEqual(self.track_object2.start, start)
        self.failUnlessEqual(self.monitor.start_changed_count, 1)

        duration = 10 * gst.SECOND
        timeline_object.duration = duration
        self.failUnlessEqual(timeline_object.duration, duration)
        self.failUnlessEqual(self.track_object1.duration, duration)
        self.failUnlessEqual(self.track_object2.duration, duration)
        self.failUnlessEqual(self.monitor.duration_changed_count, 1)

        in_point = 5 * gst.SECOND
        timeline_object.in_point = in_point
        self.failUnlessEqual(timeline_object.in_point, in_point)
        self.failUnlessEqual(self.track_object1.in_point, in_point)
        self.failUnlessEqual(self.track_object2.in_point, in_point)
        self.failUnlessEqual(self.monitor.in_point_changed_count, 1)

        out_point = 5 * gst.SECOND
        timeline_object.out_point = out_point
        self.failUnlessEqual(timeline_object.out_point, out_point)
        self.failUnlessEqual(self.track_object1.out_point, out_point)
        self.failUnlessEqual(self.track_object2.out_point, out_point)
        self.failUnlessEqual(self.monitor.out_point_changed_count, 1)

    def testChangePropertiesFromTrackObject(self):
        timeline_object = self.timeline_object
        track_object = self.track_object1
        timeline_object.addTrackObject(track_object)

        start = 1 * gst.SECOND
        track_object.start = start
        self.failUnlessEqual(timeline_object.start, start)
        self.failUnlessEqual(self.monitor.start_changed_count, 1)

        duration = 10 * gst.SECOND
        track_object.duration = duration
        self.failUnlessEqual(timeline_object.duration, duration)
        self.failUnlessEqual(self.monitor.duration_changed_count, 1)

        in_point = 5 * gst.SECOND
        track_object.in_point = in_point
        self.failUnlessEqual(timeline_object.in_point, in_point)
        self.failUnlessEqual(self.monitor.in_point_changed_count, 1)

        out_point = 5 * gst.SECOND
        track_object.out_point = out_point
        self.failUnlessEqual(timeline_object.out_point, out_point)
        self.failUnlessEqual(self.monitor.out_point_changed_count, 1)

    def testSplit(self):
        obj = self.timeline_object
        track_object = self.track_object1
        obj.addTrackObject(track_object)

        obj.start = 3 * gst.SECOND
        obj.duration = 10 * gst.SECOND

        monitor = TimelineSignalMonitor(obj)

        self.failUnlessRaises(TimelineError, obj.split, 2 * gst.SECOND)
        self.failUnlessRaises(TimelineError, obj.split, 14 * gst.SECOND)

        # should these be possible (ie create empty objects) ?
        self.failUnlessRaises(TimelineError, obj.split, 3 * gst.SECOND)
        self.failUnlessRaises(TimelineError, obj.split, 13 * gst.SECOND)

        # split at 4s should result in:
        # obj (start 3, end 4) other1 (start 4, end 13)
        other1 = obj.split(4 * gst.SECOND)

        self.failUnlessEqual(obj.start, 3 * gst.SECOND)
        self.failUnlessEqual(obj.duration, 1 * gst.SECOND)

        self.failUnlessEqual(other1.start, 4 * gst.SECOND)
        self.failUnlessEqual(other1.duration, 9 * gst.SECOND)

        self.failUnlessEqual(monitor.start_changed_count, 0)
        self.failUnlessEqual(monitor.duration_changed_count, 1)

        # split again other1
        monitor = TimelineSignalMonitor(other1)

        other2 = other1.split(11 * gst.SECOND)
        self.failUnlessEqual(other1.start, 4 * gst.SECOND)
        self.failUnlessEqual(other1.duration, 7 * gst.SECOND)

        self.failUnlessEqual(other2.start, 11 * gst.SECOND)
        self.failUnlessEqual(other2.duration, 2 * gst.SECOND)

        self.failUnlessEqual(monitor.start_changed_count, 0)
        self.failUnlessEqual(monitor.duration_changed_count, 1)

class TestTimelineAddRemoveTracks(TestCase):
    def testAddRemoveTracks(self):
        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        track1 = Track(stream)
        track2 = Track(stream)

        timeline = Timeline()

        timeline.addTrack(track1)
        self.failUnlessRaises(TimelineError, timeline.addTrack, track1)

        timeline.addTrack(track2)

        timeline.removeTrack(track1)
        self.failUnlessRaises(TimelineError, timeline.removeTrack, track1)

        timeline.removeTrack(track2)

class TestTimelineAddRemoveTimelineObjects(TestCase):
    def testAddRemoveTimelineObjects(self):
        factory = StubFactory()
        stream = AudioStream(gst.Caps('video/x-raw-rgb'))
        timeline = Timeline()
        track = Track(factory)

        track_object1 = SourceTrackObject(factory)
        track_object2 = SourceTrackObject(factory)
        track.addTrackObject(track_object1)
        track.addTrackObject(track_object2)

        timeline_object1 = TimelineObject(factory)
        timeline_object2 = TimelineObject(factory)

        self.failUnlessRaises(TimelineError,
                timeline.addTimelineObject, timeline_object1)

        timeline_object1.addTrackObject(track_object1)
        timeline.addTimelineObject(timeline_object1)

        self.failUnlessRaises(TimelineError,
                timeline.addTimelineObject, timeline_object1)

        timeline_object2.addTrackObject(track_object2)
        timeline.addTimelineObject(timeline_object2)

        timeline.removeTimelineObject(timeline_object1)
        self.failUnlessRaises(TimelineError,
                timeline.removeTimelineObject, timeline_object1)

        timeline.removeTimelineObject(timeline_object2)

class TestSelectionAddRemoveTimelineObjects(TestCase):
    def testAddRemoveTimelineObjects(self):
        factory = StubFactory()
        timeline_object1 = TimelineObject(factory)
        timeline_object2 = TimelineObject(factory)

        selection = Selection()
        selection.addTimelineObject(timeline_object1)
        self.failUnlessRaises(TimelineError,
                selection.addTimelineObject, timeline_object1)

        selection.addTimelineObject(timeline_object2)

        selection.removeTimelineObject(timeline_object1)
        self.failUnlessRaises(TimelineError,
                selection.removeTimelineObject, timeline_object1)

        selection.removeTimelineObject(timeline_object2)

class TestLink(TestCase):
    def setUp(self):
        self.factory = StubFactory()
        self.stream = AudioStream(gst.Caps('audio/x-raw-int'))
        self.track1 = Track(self.stream)
        self.track2 = Track(self.stream)
        self.track_object1 = SourceTrackObject(self.factory)
        self.track_object2 = SourceTrackObject(self.factory)
        self.track_object3 = SourceTrackObject(self.factory)
        self.track1.addTrackObject(self.track_object1)
        self.track1.addTrackObject(self.track_object2)
        self.track2.addTrackObject(self.track_object3)
        self.timeline_object1 = TimelineObject(self.factory)
        self.timeline_object1.addTrackObject(self.track_object1)
        self.timeline_object2 = TimelineObject(self.factory)
        self.timeline_object2.addTrackObject(self.track_object2)
        self.timeline_object3 = TimelineObject(self.factory)
        self.timeline_object3.addTrackObject(self.track_object3)

    def testLinkAttribute(self):
        timeline_object1 = self.timeline_object1
        timeline_object2 = self.timeline_object2
        timeline_object3 = self.timeline_object3

        self.failUnlessEqual(timeline_object1.link, None)
        self.failUnlessEqual(timeline_object2.link, None)
        self.failUnlessEqual(timeline_object3.link, None)

        link = Link()
        link.addTimelineObject(timeline_object1)
        link.addTimelineObject(timeline_object2)
        link.addTimelineObject(timeline_object3)

        link2 = Link()
        self.failUnlessRaises(TimelineError,
                link2.addTimelineObject, timeline_object1)

        self.failIfEqual(timeline_object1.link, None)
        self.failIfEqual(timeline_object2.link, None)
        self.failIfEqual(timeline_object3.link, None)

        link.removeTimelineObject(timeline_object1)
        self.failUnlessEqual(timeline_object1.link, None)

        link.removeTimelineObject(timeline_object2)
        self.failUnlessEqual(timeline_object2.link, None)

        link.removeTimelineObject(timeline_object3)
        self.failUnlessEqual(timeline_object3.link, None)

    def testLinkJoin(self):
        timeline_object1 = self.timeline_object1
        timeline_object2 = self.timeline_object2
        timeline_object3 = self.timeline_object3

        link1 = Link()
        link1.addTimelineObject(timeline_object1)
        link1.addTimelineObject(timeline_object2)

        link2 = Link()
        link2.addTimelineObject(timeline_object3)

        self.failUnlessEqual(timeline_object1.link, link1)
        self.failUnlessEqual(timeline_object2.link, link1)
        self.failUnlessEqual(timeline_object3.link, link2)

        link3 = link1.join(link2)
        self.failUnlessEqual(timeline_object1.link, link3)
        self.failUnlessEqual(timeline_object2.link, link3)
        self.failUnlessEqual(timeline_object3.link, link3)

    def testChangeStart(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1
        track2 = self.track2
        track_object1 = self.track_object1
        track_object2 = self.track_object2
        track_object3 = self.track_object3

        timeline_object1 = self.timeline_object1
        timeline_object2 = self.timeline_object2
        timeline_object3 = self.timeline_object3

        link = Link()
        link.addTimelineObject(timeline_object1)
        link.addTimelineObject(timeline_object2)

        self.failUnlessEqual(timeline_object1.start, 0)
        self.failUnlessEqual(timeline_object2.start, 0)

        # move start forward
        start = 3 * gst.SECOND
        timeline_object1.start = start
        self.failUnlessEqual(timeline_object1.start, start)
        self.failUnlessEqual(timeline_object2.start, start)

        # move start back
        start = 2 * gst.SECOND
        timeline_object2.start = start
        self.failUnlessEqual(timeline_object1.start, start)
        self.failUnlessEqual(timeline_object2.start, start)

        # add a third object (on a different track)
        timeline_object3.start = 10 * gst.SECOND
        link.addTimelineObject(timeline_object3)

        # move start from 2 to 4, this should shift timeline_object3 from 10 to
        # 12
        start = 4 * gst.SECOND
        timeline_object2.start = start
        self.failUnlessEqual(timeline_object1.start, start)
        self.failUnlessEqual(timeline_object2.start, start)
        self.failUnlessEqual(timeline_object3.start, 12 * gst.SECOND)

        # try to move timeline_object3 5 seconds back (to 7s). It should
        # actually stop the move to 8s so that timeline_object1 and
        # timeline_object2 don't go < 0s.
        start = 7 * gst.SECOND
        timeline_object3.start = start
        self.failUnlessEqual(timeline_object1.start, 0)
        self.failUnlessEqual(timeline_object2.start, 0)
        self.failUnlessEqual(timeline_object3.start, 8 * gst.SECOND)

        # unlink timeline_object1 and move it back to start = 1
        link.removeTimelineObject(timeline_object1)
        timeline_object1.start = 1 * gst.SECOND
        self.failUnlessEqual(timeline_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(timeline_object2.start, 0)
        self.failUnlessEqual(timeline_object3.start, 8 * gst.SECOND)

class TestTimelineEdges(TestCase):
    def setUp(self):
        self.timeline_edges = TimelineEdges()

    def testRemove(self):
        self.timeline_edges.addStartEnd(0, 2000)
        self.timeline_edges.removeStartEnd(0, 2000)

    def testRemoveNotExisting(self):
        self.failUnlessRaises(TimelineError,
                self.timeline_edges.removeStartEnd, 1, 2000)

        self.timeline_edges.addStartEnd(0, 2000)
        self.failUnlessRaises(TimelineError,
                self.timeline_edges.removeStartEnd, 1, 2000)
        self.failUnlessRaises(TimelineError,
                self.timeline_edges.removeStartEnd, 0, 2001)

    def testNoEdges(self):
        self.failUnlessEqual(self.timeline_edges.snapToEdge(500, 1000), (500, 0))

    def testSimple(self):
        self.timeline_edges.addStartEnd(0, 2000)
        self.failUnlessEqual(self.timeline_edges.snapToEdge(500, 1000), (0, 500))

        self.timeline_edges.removeStartEnd(0, 2000)

    def testSamePosition(self):
        self.timeline_edges.addStartEnd(0, 2000)
        self.timeline_edges.addStartEnd(0, 2000)

        self.failUnlessEqual(self.timeline_edges.snapToEdge(500, 1000), (0, 500))

        self.timeline_edges.removeStartEnd(0, 2000)

        self.failUnlessEqual(self.timeline_edges.snapToEdge(500, 1000), (0, 500))

        self.timeline_edges.removeStartEnd(0, 2000)

    def testSnapStart(self):
        self.timeline_edges = TimelineEdges()

        self.timeline_edges.addStartEnd(1000, 2000)

        # match start-left
        self.failUnlessEqual(self.timeline_edges.snapToEdge(900, 1400), (1000, 100))

        # match start
        self.failUnlessEqual(self.timeline_edges.snapToEdge(1000, 1999), (1000, 0))

        # match start-right
        self.failUnlessEqual(self.timeline_edges.snapToEdge(1200, 1400), (1000, 200))

        # match end-left
        self.failUnlessEqual(self.timeline_edges.snapToEdge(1600, 1999), (1601, 1))

        # match end
        self.failUnlessEqual(self.timeline_edges.snapToEdge(1001, 2000), (1001, 0))

        # match end-right
        self.failUnlessEqual(self.timeline_edges.snapToEdge(2100, 3000), (2000, 100))

        # match both start and end, start is returned
        self.failUnlessEqual(self.timeline_edges.snapToEdge(1000, 2000), (1000, 0))

    def testSnapDuration(self):
        self.timeline_edges.addStartEnd(1000, 2000)

        # match start-left
        self.failUnlessEqual(self.timeline_edges.snapToEdge(900), (1000, 100))

        # match start
        self.failUnlessEqual(self.timeline_edges.snapToEdge(1000), (1000, 0))

        # match start-right
        self.failUnlessEqual(self.timeline_edges.snapToEdge(1200), (1000, 200))

        # match end-left
        self.failUnlessEqual(self.timeline_edges.snapToEdge(1999), (2000, 1))

        # match end
        self.failUnlessEqual(self.timeline_edges.snapToEdge(2000), (2000, 0))

        # match end-right
        self.failUnlessEqual(self.timeline_edges.snapToEdge(3000), (2000, 1000))
