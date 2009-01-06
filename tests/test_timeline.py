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
        Selection, Link
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.stream import AudioStream, VideoStream
from pitivi.utils import UNKNOWN_DURATION

# FIXME: put this somewhere else
from tests.test_track import TimePropertiesSignalMonitor

class StubFactory(object):
    pass

class TestTimelineObjectAddRemoveTrackObjects(TestCase):
    def testAddRemoveTrackObjects(self):
        factory = StubFactory()
        timeline_object1 = TimelineObject(factory)
        timeline_object2 = TimelineObject(factory)

        stream = AudioStream(gst.Caps('video/x-raw-rgb'))
        track = Track(stream)
        track_object1 = SourceTrackObject(factory)
        track_object2 = SourceTrackObject(factory)

        # track_object1 doesn't belong to any track
        self.failUnlessRaises(TimelineError,
                timeline_object1.addTrackObject, track_object1)

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
        self.monitor = TimePropertiesSignalMonitor(self.timeline_object)
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
        track_object = self.track_object1
        timeline_object.addTrackObject(track_object)
        
        start = 1 * gst.SECOND
        timeline_object.start = start
        self.failUnlessEqual(timeline_object.start, start)
        self.failUnlessEqual(track_object.start, start)
        self.failUnlessEqual(self.monitor.start_changed_count, 1)

        duration = 10 * gst.SECOND
        timeline_object.duration = duration
        self.failUnlessEqual(timeline_object.duration, duration)
        self.failUnlessEqual(track_object.duration, duration)
        self.failUnlessEqual(self.monitor.duration_changed_count, 1)

        in_point = 5 * gst.SECOND
        timeline_object.in_point = in_point
        self.failUnlessEqual(timeline_object.in_point, in_point)
        self.failUnlessEqual(track_object.in_point, in_point)
        self.failUnlessEqual(self.monitor.in_point_changed_count, 1)
        
        out_point = 5 * gst.SECOND
        timeline_object.out_point = out_point
        self.failUnlessEqual(timeline_object.out_point, out_point)
        self.failUnlessEqual(track_object.out_point, out_point)
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

class TestTimelineAddRemoveTracks(TestCase):
    def testAddRemoveTracks(self):
        stream = AudioStream(gst.Caps('video/x-raw-rgb'))
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
    def testChangeStart(self):
        factory = StubFactory()
        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        track = Track(stream)
        track_object1 = SourceTrackObject(factory)
        track_object2 = SourceTrackObject(factory)
        track.addTrackObject(track_object1)
        track.addTrackObject(track_object2)

        timeline_object1 = TimelineObject(factory)
        timeline_object1.addTrackObject(track_object1)
        timeline_object2 = TimelineObject(factory)
        timeline_object2.addTrackObject(track_object2)

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

        # reset to 0
        start = 0
        timeline_object2.start = start
        self.failUnlessEqual(timeline_object1.start, start)
        self.failUnlessEqual(timeline_object2.start, start)

