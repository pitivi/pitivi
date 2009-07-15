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

import gst

from tests.common import FakeSourceFactory
from pitivi.timeline.timeline import Timeline, TimelineObject, TimelineError, \
        Selection, Link, TimelineEdges, MoveContext, TrimStartContext, \
        TrimEndContext
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.stream import AudioStream, VideoStream
from pitivi.utils import UNKNOWN_DURATION

from common import SignalMonitor, TestCase, StubFactory

def scrubTo(lower, upper, steps, final):
    """Simulate the user scrubbing the cursor by generating a stream of random
    integers, enter """
    for i in xrange(0, steps):
        yield random.randint(lower, upper)
    yield final

class TimelineSignalMonitor(SignalMonitor):
    def __init__(self, track_object):
        SignalMonitor.__init__(self, track_object, 'start-changed',
                'duration-changed', 'in-point-changed', 'media-duration-changed')

class TestTimelineObjectAddRemoveTrackObjects(TestCase):
    def testAddRemoveTrackObjects(self):
        factory = StubFactory()
        timeline_object1 = TimelineObject(factory)
        timeline_object2 = TimelineObject(factory)

        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        factory.addOutputStream(stream)
        track = Track(stream)
        track_object1 = SourceTrackObject(factory, stream)
        track_object2 = SourceTrackObject(factory, stream)

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
        TestCase.setUp(self)
        factory = StubFactory()
        self.timeline_object = TimelineObject(factory)
        self.monitor = SignalMonitor(self.timeline_object, 'start-changed',
                'duration-changed', 'in-point-changed', 'out-point-changed',
                'media-duration-changed', 'priority-changed')
        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        factory.addOutputStream(stream)
        self.track = Track(stream)
        self.track_object1 = SourceTrackObject(factory, stream)
        self.track_object2 = SourceTrackObject(factory, stream)
        self.track.addTrackObject(self.track_object1)
        self.track.addTrackObject(self.track_object2)

    def tearDown(self):
        self.track.removeTrackObject(self.track_object1)
        self.track.removeTrackObject(self.track_object2)
        del self.track
        del self.track_object1
        del self.track_object2
        del self.monitor
        del self.timeline_object
        TestCase.tearDown(self)

    def testDefaultProperties(self):
        obj = self.timeline_object
        self.failUnlessEqual(obj.start, 0)
        self.failUnlessEqual(obj.duration, UNKNOWN_DURATION)
        self.failUnlessEqual(obj.in_point, 0)
        self.failUnlessEqual(obj.out_point, 0)
        self.failUnlessEqual(obj.media_duration, UNKNOWN_DURATION)
        self.failUnlessEqual(obj.priority, 0)

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

        media_duration = 5 * gst.SECOND
        timeline_object.media_duration = media_duration
        self.failUnlessEqual(timeline_object.media_duration, media_duration)
        self.failUnlessEqual(self.track_object1.media_duration, media_duration)
        self.failUnlessEqual(self.monitor.media_duration_changed_count, 1)
        self.failUnlessEqual(timeline_object.out_point,
                in_point + media_duration)
        self.failUnlessEqual(self.track_object1.out_point,
                in_point + media_duration)
        # FIXME
        #self.failUnlessEqual(self.monitor.out_point_changed_count, 1)

        priority = 100
        timeline_object.priority = priority
        self.failUnlessEqual(timeline_object.priority, priority)
        self.failUnlessEqual(self.track_object1.priority, priority)
        self.failUnlessEqual(self.monitor.priority_changed_count, 1)

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

        media_duration = 5 * gst.SECOND
        timeline_object.media_duration = media_duration
        self.failUnlessEqual(timeline_object.media_duration, media_duration)
        self.failUnlessEqual(self.track_object1.media_duration, media_duration)
        self.failUnlessEqual(self.track_object2.media_duration, media_duration)
        self.failUnlessEqual(self.monitor.media_duration_changed_count, 1)

        priority = 100
        timeline_object.priority = priority
        self.failUnlessEqual(timeline_object.priority, priority)
        self.failUnlessEqual(self.track_object1.priority, priority)
        self.failUnlessEqual(self.track_object2.priority, priority)
        self.failUnlessEqual(self.monitor.priority_changed_count, 1)

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

        media_duration = 5 * gst.SECOND
        track_object.media_duration = media_duration
        self.failUnlessEqual(timeline_object.media_duration, media_duration)
        self.failUnlessEqual(self.monitor.media_duration_changed_count, 1)

        priority = 100
        track_object.priority = priority
        self.failUnlessEqual(timeline_object.priority, priority)
        self.failUnlessEqual(self.monitor.priority_changed_count, 1)

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
        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        factory.addOutputStream(stream)
        timeline = Timeline()
        track = Track(stream)

        track_object1 = SourceTrackObject(factory, stream)
        track_object2 = SourceTrackObject(factory, stream)
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

    def testRemoveFactory(self):
        factory = StubFactory()
        stream = AudioStream(gst.Caps("audio/x-raw-int"))
        factory.addOutputStream(stream)
        track = Track(stream)
        track_object1 = SourceTrackObject(factory, stream)
        track.addTrackObject(track_object1)
        track_object2 = SourceTrackObject(factory, stream)
        track.addTrackObject(track_object2)
        track_object3 = SourceTrackObject(factory, stream)
        track.addTrackObject(track_object3)
        timeline_object1 = TimelineObject(factory)
        timeline_object1.addTrackObject(track_object1)
        timeline_object2 = TimelineObject(factory)
        timeline_object2.addTrackObject(track_object2)
        timeline_object3 = TimelineObject(factory)
        timeline_object3.addTrackObject(track_object3)
        timeline = Timeline()
        timeline.addTrack(track)
        timeline.addTimelineObject(timeline_object1)
        timeline.addTimelineObject(timeline_object2)
        timeline.addTimelineObject(timeline_object3)

        self.failUnlessEqual(len(timeline.timeline_objects), 3)
        timeline.removeFactory(factory)
        self.failUnlessEqual(len(timeline.timeline_objects), 0)

class TestLink(TestCase):

    def test(self):
        pass

    def testAddRemoveTimelineObjects(self):
        factory = StubFactory()
        factory.addOutputStream(VideoStream(gst.Caps("video/x-raw-yuv")))
        timeline_object1 = TimelineObject(factory)
        timeline_object2 = TimelineObject(factory)

        link = Link()
        link.addTimelineObject(timeline_object1)
        self.failUnlessRaises(TimelineError,
                link.addTimelineObject, timeline_object1)

        link.addTimelineObject(timeline_object2)

        link.removeTimelineObject(timeline_object1)
        self.failUnlessRaises(TimelineError,
                link.removeTimelineObject, timeline_object1)

        link.removeTimelineObject(timeline_object2)

    def setUp(self):
        TestCase.setUp(self)
        self.factory = StubFactory()
        self.stream = AudioStream(gst.Caps('audio/x-raw-int'))
        self.factory.addOutputStream(self.stream)
        self.track1 = Track(self.stream)
        self.track2 = Track(self.stream)
        self.track_object1 = SourceTrackObject(self.factory, self.stream)
        self.track_object2 = SourceTrackObject(self.factory, self.stream)
        self.track_object3 = SourceTrackObject(self.factory, self.stream)
        self.track1.addTrackObject(self.track_object1)
        self.track1.addTrackObject(self.track_object2)
        self.track2.addTrackObject(self.track_object3)
        self.timeline_object1 = TimelineObject(self.factory)
        self.timeline_object1.addTrackObject(self.track_object1)
        self.timeline_object2 = TimelineObject(self.factory)
        self.timeline_object2.addTrackObject(self.track_object2)
        self.timeline_object3 = TimelineObject(self.factory)
        self.timeline_object3.addTrackObject(self.track_object3)

    def tearDown(self):
        self.timeline_object3.removeTrackObject(self.track_object3)
        self.timeline_object2.removeTrackObject(self.track_object2)
        self.timeline_object1.removeTrackObject(self.track_object1)
        self.track1.removeTrackObject(self.track_object1)
        self.track1.removeTrackObject(self.track_object2)
        self.track2.removeTrackObject(self.track_object3)
        del self.timeline_object3
        del self.timeline_object2
        del self.timeline_object1
        del self.track_object1
        del self.track_object2
        del self.track_object3
        del self.track1
        del self.track2
        del self.stream
        del self.factory
        TestCase.tearDown(self)

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
        TestCase.setUp(self)
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
        self.failUnlessEqual(self.timeline_edges.snapToEdge(500, 1000), (500, 0))

    def testSamePosition(self):
        self.timeline_edges.addStartEnd(0, 2000)
        self.timeline_edges.addStartEnd(0, 2000)

        self.failUnlessEqual(self.timeline_edges.snapToEdge(500, 1000), (0, 500))

        self.timeline_edges.removeStartEnd(0, 2000)

        self.failUnlessEqual(self.timeline_edges.snapToEdge(500, 1000), (0, 500))

        self.timeline_edges.removeStartEnd(0, 2000)
    
        self.failUnlessEqual(self.timeline_edges.snapToEdge(500, 1000), (500, 0))

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

    def testAdjacenctObjs(self):
        factory = FakeSourceFactory()
        stream = AudioStream(gst.Caps("meh"))
        track_object1 = SourceTrackObject(factory, stream)
        track_object2 = SourceTrackObject(factory, stream)
        track_object1.start = 500 
        track_object1.duration = 500
        track_object2.start = 1000
        track_object2.duration = 500
        self.timeline_edges.addTrackObject(track_object1)
        self.timeline_edges.addTrackObject(track_object2)
        self.assertEquals(self.timeline_edges.getObjsIncidentOnTime(1000),
            [track_object1, track_object2])
        self.assertEquals(self.timeline_edges.getObjsAdjacentToStart(track_object2),
            [track_object1])
        self.assertEquals(self.timeline_edges.getObjsAdjacentToEnd(track_object1),
            [track_object2])

        self.timeline_edges.removeTrackObject(track_object2)
        self.assertEquals(self.timeline_edges.getObjsIncidentOnTime(1000),
                [track_object1])

        self.timeline_edges.removeTrackObject(track_object1)
        self.assertEquals(self.timeline_edges.getObjsIncidentOnTime(1000), [])

        track_object1.release()
        track_object2.release()
        del factory

class TestTimelineAddFactory(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.audio_stream1 = AudioStream(gst.Caps('audio/x-raw-int'))
        self.audio_stream2 = AudioStream(gst.Caps('audio/x-raw-int'))
        self.audio_stream3 = AudioStream(gst.Caps('audio/x-raw-int'))
        self.video_stream1 = VideoStream(gst.Caps('video/x-raw-rgb'))
        self.video_stream2 = VideoStream(gst.Caps('video/x-raw-rgb'))
        self.audio_track1 = Track(self.audio_stream1)
        self.audio_track2 = Track(self.audio_stream2)
        self.video_track1 = Track(self.video_stream1)
        self.video_track2 = Track(self.video_stream2)
        self.timeline = Timeline()
        self.timeline.addTrack(self.audio_track1)
        self.timeline.addTrack(self.audio_track2)
        self.timeline.addTrack(self.video_track1)
        self.timeline.addTrack(self.video_track2)

        self.factory = StubFactory()

    def tearDown(self):
        del self.audio_stream1
        del self.audio_stream2
        del self.audio_stream3
        del self.video_stream1
        del self.video_stream2
        del self.audio_track1
        del self.audio_track2
        del self.video_track1
        del self.video_track2
        del self.timeline
        del self.factory
        TestCase.tearDown(self)

    def testNoStreams(self):
        self.failUnlessRaises(TimelineError, self.timeline.addSourceFactory, self.factory)

    def testAudioOnly(self):
        self.factory.addOutputStream(self.audio_stream1)
        self.timeline.addSourceFactory(self.factory)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 2)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 1)
        self.failUnlessEqual(len(self.video_track1.track_objects), 1)
        self.failUnlessEqual(len(self.video_track2.track_objects), 1)

    def testVideoOnly(self):
        self.factory.addOutputStream(self.video_stream1)
        self.timeline.addSourceFactory(self.factory)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 1)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 1)
        self.failUnlessEqual(len(self.video_track1.track_objects), 2)
        self.failUnlessEqual(len(self.video_track2.track_objects), 1)

    def test1Audio1Video(self):
        self.factory.addOutputStream(self.audio_stream1)
        self.factory.addOutputStream(self.video_stream1)
        self.timeline.addSourceFactory(self.factory)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 2)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 1)
        self.failUnlessEqual(len(self.video_track1.track_objects), 2)
        self.failUnlessEqual(len(self.video_track2.track_objects), 1)

    def testConflictNotEnoughTracks(self):
        # 3 audio streams, only 2 audio tracks in the timeline
        self.factory.addOutputStream(self.audio_stream1)
        self.factory.addOutputStream(self.audio_stream2)
        self.factory.addOutputStream(self.audio_stream3)
        self.failUnlessRaises(TimelineError, self.timeline.addSourceFactory,
                self.factory, strict=True)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 1)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 1)
        self.failUnlessEqual(len(self.video_track1.track_objects), 1)
        self.failUnlessEqual(len(self.video_track2.track_objects), 1)

class TestContexts(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.timeline = Timeline()
        self.factory = StubFactory()
        self.stream = AudioStream(gst.Caps('audio/x-raw-int'))
        self.factory.addOutputStream(self.stream)
        self.track1 = Track(self.stream)
        self.track2 = Track(self.stream)
        self.track_object1 = SourceTrackObject(self.factory, self.stream)
        self.track_object2 = SourceTrackObject(self.factory, self.stream)
        self.track_object3 = SourceTrackObject(self.factory, self.stream)
        self.track1.addTrackObject(self.track_object1)
        self.track1.addTrackObject(self.track_object2)
        self.track2.addTrackObject(self.track_object3)
        self.timeline_object1 = TimelineObject(self.factory)
        self.timeline_object1.addTrackObject(self.track_object1)
        self.timeline_object2 = TimelineObject(self.factory)
        self.timeline_object2.addTrackObject(self.track_object2)
        self.timeline_object3 = TimelineObject(self.factory)
        self.timeline_object3.addTrackObject(self.track_object3)
        self.timeline.addTimelineObject(self.timeline_object1)
        self.timeline.addTimelineObject(self.timeline_object2)
        self.timeline.addTimelineObject(self.timeline_object3)
        self.focus = self.track_object1
        self.other = set([self.track_object2, self.track_object3])

    def testMoveContext(self):
        # set up the initial state of the timeline and create the track object
        # [focus]     [t2   ]     [t3     ]
        self.focus.start = 0
        self.focus.duration = gst.SECOND * 5
        self.track_object2.start = 15 * gst.SECOND
        self.track_object3.start = 25 * gst.SECOND
        context = MoveContext(self.timeline, self.focus, set())

        # make an edit, check that the edit worked as expected
        #    [focus]  [t2   ]     [t3     ]
        context.editTo(gst.SECOND * 10, 0)
        self.failUnlessEqual(self.focus.start, gst.SECOND * 10)
        self.failUnlessEqual(self.focus.duration,  gst.SECOND * 5)
        self.failUnlessEqual(self.focus.in_point, 0)
        self.failUnlessEqual(self.track_object2.start, gst.SECOND * 15)
        self.failUnlessEqual(self.track_object3.start, gst.SECOND * 25)

        # change to the ripple mode, check that the edit worked as expected
        #            [focus]  [t2   ]     [t3     ]
        context.setMode(context.RIPPLE)
        context.editTo(gst.SECOND * 20, 0)
        self.failUnlessEqual(self.focus.start, gst.SECOND * 20)
        self.failUnlessEqual(self.focus.duration,  gst.SECOND * 5)
        self.failUnlessEqual(self.focus.in_point, 0)
        self.failUnlessEqual(self.track_object2.start, gst.SECOND * 35)
        self.failUnlessEqual(self.track_object3.start, gst.SECOND * 45)

        # change back to default mode, and make sure this works as expected
        #             [t2   ]     [t3     ]
        #            [focus]
        context.setMode(context.DEFAULT)
        self.failUnlessEqual(self.focus.start, gst.SECOND * 20)
        self.failUnlessEqual(self.focus.duration,  gst.SECOND * 5)
        self.failUnlessEqual(self.focus.in_point, 0)
        self.failUnlessEqual(self.track_object2.start, gst.SECOND * 15)
        self.failUnlessEqual(self.track_object3.start, gst.SECOND * 25)

        context.finish()

        self.failUnlessEqual(self.focus.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 25 * gst.SECOND)

    def testMoveContextFocusNotEarliest(self):
        #     [t2  ][focus]  [t3     ]
        self.focus.start = 10 * gst.SECOND
        self.focus.duration = 5 * gst.SECOND
        self.track_object2.start = 1 * gst.SECOND
        self.track_object2.duration = 9 * gst.SECOND
        self.track_object3.start = 15 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        other = set([self.track_object2])

        context = MoveContext(self.timeline, self.focus, other)
        context.editTo(20 * gst.SECOND, 0)

        #                           [t2  ][focus] 
        #                    [t3     ]
        self.failUnlessEqual(self.focus.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)

        context.setMode(context.RIPPLE)

        #                            [t2  ][focus]  [t3     ]
        self.failUnlessEqual(self.focus.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 25 * gst.SECOND)

        context.setMode(context.DEFAULT)

        #                           [t2  ][focus] 
        #                    [t3     ]
        self.failUnlessEqual(self.focus.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)

        context.finish()

    def testNothingToRipple(self):
        self.focus.start = 20 * gst.SECOND
        self.focus.duration = 5 * gst.SECOND
        self.track_object2.start = 10 * gst.SECOND
        self.track_object2.duration = 1 * gst.SECOND
        self.track_object3.start = 11 * gst.SECOND
        self.track_object3.duration = 1 * gst.SECOND

        context = MoveContext(self.timeline, self.focus, set())
        context.setMode(context.RIPPLE)
        context.editTo(10 * gst.SECOND, 0)

        self.failUnlessEqual(self.focus.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 11 * gst.SECOND)


        #TODO: test trim context ripple modes when implemented

    def testTrimStartContext(self):
        self.focus.start = 1 * gst.SECOND
        self.focus.in_point = 3 * gst.SECOND
        self.focus.duration = 20 * gst.SECOND
        self.track_object2.start = 1 * gst.SECOND
        self.track_object2.in_point = 10 * gst.SECOND
        self.track_object3.start = 15 * gst.SECOND
        self.track_object3.in_point = 20 * gst.SECOND

        # set up the initial state of the timeline and create the track object
        # [focus]     [t2   ]     [t3     ]
        context = TrimStartContext(self.timeline, self.focus, self.other)
        context.editTo(gst.SECOND * 10, 0)
        context.finish()

        self.failUnlessEqual(self.focus.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.focus.in_point, 12 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.in_point, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.in_point, 20 * gst.SECOND)


    def testTrimEndContext(self):
        self.focus.start = 1 * gst.SECOND
        self.focus.in_point = 3 * gst.SECOND
        self.focus.duration = 15 * gst.SECOND
        self.track_object2.start = 1 * gst.SECOND
        self.track_object2.in_point = 10 * gst.SECOND
        self.track_object2.duration = 16 * gst.SECOND
        self.track_object3.start = 15 * gst.SECOND
        self.track_object3.in_point = 19 * gst.SECOND
        self.track_object3.duration = 23 * gst.SECOND

        context = TrimEndContext(self.timeline, self.focus, self.other)
        context.editTo(gst.SECOND * 10, 0)
        context.finish()

        self.failUnlessEqual(self.focus.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.focus.in_point, 3 * gst.SECOND)
        self.failUnlessEqual(self.focus.duration, 9 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.in_point, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration, 16 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.in_point, 19 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration, 23 * gst.SECOND)

    def testEmptyOther(self):
        context = MoveContext(self.timeline, self.focus, set())
        context.finish()
        context = TrimStartContext(self.timeline, self.focus, set())
        context.finish()
        context = TrimEndContext(self.timeline, self.focus, set())
        context.finish()

    def tearDown(self):
        del self.timeline_object1
        del self.timeline_object2
        del self.timeline_object3
        del self.track_object1
        del self.track_object2
        del self.track_object3
        del self.track1
        del self.track2
        del self.factory
        del self.stream
        del self.timeline
        del self.focus
        del self.other
        TestCase.tearDown(self)
