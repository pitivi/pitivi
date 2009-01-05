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

from pitivi.timeline.timeline import Timeline, TimelineObject, TimelineError
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.stream import AudioStream, VideoStream

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
