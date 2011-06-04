# PiTiVi , Non-linear video editor
#
#       tests/test_timeline.py
#
# Copyright (c) 2008,2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

import pygst
pygst.require("0.10")
import gst

from tests.common import FakeSourceFactory, FakeEffectFactory
from pitivi.timeline.timeline import Timeline, TimelineObject, TimelineError, \
        Link, TimelineEdges, MoveContext, TrimStartContext, \
        TrimEndContext
from pitivi.timeline.track import Track, SourceTrackObject, TrackEffect
from pitivi.stream import AudioStream, VideoStream
from pitivi.utils import UNKNOWN_DURATION
from pitivi.factories.test import AudioTestSourceFactory

from common import SignalMonitor, TestCase, StubFactory

class TimelineSignalMonitor(SignalMonitor):
    def __init__(self, track_object):
        SignalMonitor.__init__(self, track_object, 'start-changed',
                'duration-changed', 'in-point-changed', 'media-duration-changed')

class TestTimelineObjectAddRemoveTrackObjects(TestCase):
    def testAddRemoveTrackObjects(self):
        source_factory = StubFactory()
        timeline_object1 = TimelineObject(source_factory)
        timeline_object2 = TimelineObject(source_factory)

        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        source_factory.addOutputStream(stream)
        track = Track(stream)
        track_object1 = SourceTrackObject(source_factory, stream)
        track_object2 = SourceTrackObject(source_factory, stream)

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
        source_factory = StubFactory()
        self.timeline_object = TimelineObject(source_factory)
        self.monitor = SignalMonitor(self.timeline_object, 'start-changed',
                'duration-changed', 'in-point-changed', 'out-point-changed',
                'media-duration-changed', 'priority-changed')
        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        source_factory.addOutputStream(stream)
        self.track = Track(stream)
        self.track_object1 = SourceTrackObject(source_factory, stream)
        self.track_object2 = SourceTrackObject(source_factory, stream)
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
        source_factory = StubFactory()
        stream = AudioStream(gst.Caps('audio/x-raw-int'))
        source_factory.addOutputStream(stream)
        timeline = Timeline()
        track = Track(stream)

        track_object1 = SourceTrackObject(source_factory, stream)
        track_object2 = SourceTrackObject(source_factory, stream)
        track.addTrackObject(track_object1)
        track.addTrackObject(track_object2)

        timeline_object1 = TimelineObject(source_factory)
        timeline_object2 = TimelineObject(source_factory)

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
        source_factory = StubFactory()
        stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source_factory.addOutputStream(stream)
        track = Track(stream)
        track_object1 = SourceTrackObject(source_factory, stream)
        track.addTrackObject(track_object1)
        track_object2 = SourceTrackObject(source_factory, stream)
        track.addTrackObject(track_object2)
        track_object3 = SourceTrackObject(source_factory, stream)
        track.addTrackObject(track_object3)
        timeline_object1 = TimelineObject(source_factory)
        timeline_object1.addTrackObject(track_object1)
        timeline_object2 = TimelineObject(source_factory)
        timeline_object2.addTrackObject(track_object2)
        timeline_object3 = TimelineObject(source_factory)
        timeline_object3.addTrackObject(track_object3)
        timeline = Timeline()
        timeline.addTrack(track)
        timeline.addTimelineObject(timeline_object1)
        timeline.addTimelineObject(timeline_object2)
        timeline.addTimelineObject(timeline_object3)

        self.failUnlessEqual(len(timeline.timeline_objects), 3)
        timeline.removeFactory(source_factory)
        self.failUnlessEqual(len(timeline.timeline_objects), 0)

class TestTimelineAddRemoveEffectsTracks(TestCase):
    def testAddRemoveEffectTracks(self):
        stream = VideoStream(gst.Caps("video/x-raw-rgb"))
        source_factory = StubFactory()
        source_factory.addOutputStream(stream)
        effect_factory = FakeEffectFactory()
        effect_factory.addInputStream(stream)
        effect_factory.addOutputStream(stream)
        timeline = Timeline()
        track = Track(stream)

        track_effect1 = TrackEffect(effect_factory, stream)
        track_effect2 = TrackEffect(effect_factory, stream)

        track_object1 = SourceTrackObject(source_factory, stream)
        track.addTrackObject(track_object1)
        timeline_object1 = TimelineObject(source_factory)
        timeline_object1.addTrackObject(track_object1)
        timeline.addTimelineObject(timeline_object1)

        track.addTrackObject(track_effect1)
        timeline_object1.addTrackObject(track_effect1)
        self.failUnlessRaises(TimelineError,
                timeline_object1.addTrackObject, track_effect1)
        track.addTrackObject(track_effect2)
        timeline_object1.addTrackObject(track_effect2)
        self.failUnlessRaises(TimelineError,
                timeline_object1.addTrackObject, track_effect2)

        timeline_object1.removeTrackObject(track_effect1)
        self.failUnlessRaises(TimelineError,
                timeline_object1.removeTrackObject, track_effect1)
        timeline_object1.removeTrackObject(track_effect2)
        self.failUnlessRaises(TimelineError,
                timeline_object1.removeTrackObject, track_effect2)


        track.removeTrackObject(track_effect1)
        track.removeTrackObject(track_effect2)
        timeline.removeTimelineObject(timeline_object1)

    def testRemoveEffectFactory(self):
        effect_factory = FakeEffectFactory()
        stream = AudioStream(gst.Caps("audio/x-raw-int"))
        effect_factory.addInputStream(stream)
        effect_factory.addOutputStream(stream)
        track = Track(stream)
        track_effect1 = TrackEffect(effect_factory, stream)
        track.addTrackObject(track_effect1)
        track_effect2 = TrackEffect(effect_factory, stream)
        track.addTrackObject(track_effect2)
        track_effect3 = TrackEffect(effect_factory, stream)
        track.addTrackObject(track_effect3)
        timeline_object1 = TimelineObject(effect_factory)
        timeline_object1.addTrackObject(track_effect1)
        timeline_object1.addTrackObject(track_effect2)
        timeline_object1.addTrackObject(track_effect3)
        timeline = Timeline()
        timeline.addTrack(track)
        timeline.addTimelineObject(timeline_object1)

        self.failUnlessEqual(len(timeline_object1.track_objects), 3)
        self.failUnlessEqual(len(timeline.timeline_objects), 1)
        self.failUnlessEqual(len(track.track_objects), 3)
        timeline.removeFactory(effect_factory)
        self.failUnlessEqual(len(track.track_objects), 0)
        self.failUnlessEqual(len(timeline.timeline_objects), 0)

class TestTimeline(TestCase):
    def setUp(self):
        self.source_factory = StubFactory()
        self.stream = AudioStream(gst.Caps('audio/x-raw-int'))
        self.source_factory.addOutputStream(self.stream)
        self.track1 = Track(self.stream)
        self.timeline = Timeline()
        TestCase.setUp(self)

    def tearDown(self):
        del self.source_factory
        del self.stream
        del self.track1
        del self.timeline

    def makeTimelineObject(self):
        track_object = SourceTrackObject(self.source_factory, self.stream)
        self.track1.addTrackObject(track_object)
        timeline_object = TimelineObject(self.source_factory)
        timeline_object.addTrackObject(track_object)
        self.timeline.addTimelineObject(timeline_object)

        return timeline_object

    def testGetPreviousTimelineObject(self):
        timeline_object1 = self.makeTimelineObject()
        timeline_object2 = self.makeTimelineObject()
        timeline_object3 = self.makeTimelineObject()
        timeline_object4 = self.makeTimelineObject()

        timeline_object1.start = 1 * gst.SECOND
        timeline_object1.duration = 5 * gst.SECOND
        timeline_object1.priority = 1

        timeline_object2.start = 8 * gst.SECOND
        timeline_object2.duration = 5 * gst.SECOND
        timeline_object2.priority = 1

        timeline_object3.start = 6 * gst.SECOND
        timeline_object3.duration = 5 * gst.SECOND
        timeline_object3.priority = 2

        timeline_object4.start = 7 * gst.SECOND
        timeline_object4.duration = 5 * gst.SECOND
        timeline_object4.priority = 3

        timeline = self.timeline

        # no previous track_objectect
        self.failUnlessRaises(TimelineError,
                timeline.getPreviousTimelineObject, timeline_object4)

        # same priority
        prev = timeline.getPreviousTimelineObject(timeline_object2)
        self.failUnlessEqual(prev, timeline_object1)

        # given priority
        prev = timeline.getPreviousTimelineObject(timeline_object2, priority=2)
        self.failUnlessEqual(prev, timeline_object3)

        # any priority
        prev = timeline.getPreviousTimelineObject(timeline_object2, priority=None)
        self.failUnlessEqual(prev, timeline_object4)

    def testGetPreviousTimelineObjectSameStart(self):
        timeline_object1 = self.makeTimelineObject()
        timeline_object2 = self.makeTimelineObject()
        timeline = self.timeline

        timeline_object1.start = 1 * gst.SECOND
        timeline_object1.duration = 5 * gst.SECOND
        timeline_object1.priority = 1

        timeline_object2.start = 1 * gst.SECOND
        timeline_object2.duration = 5 * gst.SECOND
        timeline_object2.priority = 2

        self.failUnlessRaises(TimelineError,
                timeline.getPreviousTimelineObject, timeline_object1)
        self.failUnlessRaises(TimelineError,
                timeline.getPreviousTimelineObject, timeline_object2)

        prev = timeline.getPreviousTimelineObject(timeline_object2, priority=None)
        self.failUnlessEqual(prev, timeline_object1)

        prev = timeline.getPreviousTimelineObject(timeline_object1, priority=None)
        self.failUnlessEqual(prev, timeline_object2)

    def testGetNextTrackObject(self):
        timeline_object1 = self.makeTimelineObject()
        timeline_object2 = self.makeTimelineObject()
        timeline_object3 = self.makeTimelineObject()
        timeline_object4 = self.makeTimelineObject()

        timeline_object1.start = 1 * gst.SECOND
        timeline_object1.duration = 5 * gst.SECOND
        timeline_object1.priority = 1

        timeline_object2.start = 8 * gst.SECOND
        timeline_object2.duration = 5 * gst.SECOND
        timeline_object2.priority = 1

        timeline_object3.start = 6 * gst.SECOND
        timeline_object3.duration = 5 * gst.SECOND
        timeline_object3.priority = 2

        timeline_object4.start = 7 * gst.SECOND
        timeline_object4.duration = 5 * gst.SECOND
        timeline_object4.priority = 3

        timeline = self.timeline

        # no next timeline_objectect
        self.failUnlessRaises(TimelineError, timeline.getNextTimelineObject, timeline_object2)

        # same priority
        prev = timeline.getNextTimelineObject(timeline_object1)
        self.failUnlessEqual(prev, timeline_object2)

        # given priority
        prev = timeline.getNextTimelineObject(timeline_object1, priority=2)
        self.failUnlessEqual(prev, timeline_object3)

        # any priority
        prev = timeline.getNextTimelineObject(timeline_object3, priority=None)
        self.failUnlessEqual(prev, timeline_object4)

    def testGetObjsAtTime(self):
        # we're going use this time as our test time
        time1 = 0
        time2 = 3 * gst.SECOND
        time3 = 6 * gst.SECOND
        time4 = 10 * gst.SECOND

        clip1 = self.makeTimelineObject()
        clip1.start = 2 * gst.SECOND
        clip1.duration = 5 * gst.SECOND

        # clip2 -- overlaps left edge of clip1
        clip2 = self.makeTimelineObject()
        clip2.start = 1 * gst.SECOND
        clip2.duration = 4 * gst.SECOND

        # clip 3 -- overlaps right edge of clip1
        clip3 = self.makeTimelineObject()
        clip3.start = long(2.5 * gst.SECOND)
        clip3.duration = 5 * gst.SECOND

        # clip 4 -- doesn't overlap at all
        clip4 = self.makeTimelineObject()
        clip4.start = 10 * gst.SECOND
        clip4.duration = 4 * gst.SECOND

        result = set(self.timeline.getObjsAtTime(time1))
        self.failUnlessEqual(result, set())

        result = set(self.timeline.getObjsAtTime(time2))
        self.failUnlessEqual(result, set((clip1, clip2, clip3)))

        result = set(self.timeline.getObjsAtTime(time3))
        self.failUnlessEqual(result, set((clip1, clip3)))

        result = set(self.timeline.getObjsAtTime(time4))
        self.failUnlessEqual(result, set())

    def testSplitSelection(self):
        # we're going use this time as our test time
        noclips = 7 * gst.SECOND
        oneclip = long(6.5 * gst.SECOND)
        threeclips = long(4.5 * gst.SECOND)
        fourclipsoneselected = long(2.5 * gst.SECOND)

        clip1 = self.makeTimelineObject()
        clip1.start = 2 * gst.SECOND
        clip1.duration = 5 * gst.SECOND

        clip2 = self.makeTimelineObject()
        clip2.start = 2 * gst.SECOND
        clip2.duration = 4 * gst.SECOND

        clip3 = self.makeTimelineObject()
        clip3.start = 2 * gst.SECOND
        clip3.duration = 3 * gst.SECOND

        clip4 = self.makeTimelineObject()
        clip4.start = 2 * gst.SECOND
        clip4.duration = 2 * gst.SECOND

        # test split no clips
        self.timeline.split(noclips)
        for i, clip in enumerate([clip1,clip2,clip3,clip4]):
            self.failUnlessEqual(clip.start, 2 * gst.SECOND)
            self.failUnlessEqual(clip.duration,
                (5 - i) * gst.SECOND)

        # test split one clip
        self.timeline.split(oneclip)
        self.failUnlessEqual(clip1.start, 2 * gst.SECOND)
        self.failUnlessEqual(clip1.duration, oneclip - 2 * gst.SECOND)
        for i, clip in enumerate([clip2,clip3,clip4]):
            self.failUnlessEqual(clip.start, 2 * gst.SECOND)
            self.failUnlessEqual(clip.duration,
                (5 - (i + 1)) * gst.SECOND)

        # test split three clips
        self.timeline.split(threeclips)
        for i, clip in enumerate([clip1,clip2,clip3]):
            self.failUnlessEqual(clip.start, 2 * gst.SECOND)
            self.failUnlessEqual(clip.start + clip.duration, threeclips)
        self.failUnlessEqual(clip4.start, 2 * gst.SECOND)
        self.failUnlessEqual(clip4.duration, 2 * gst.SECOND)

        # test split three clips, one selected
        self.timeline.selection.selected = set((clip4,))
        self.timeline.split(fourclipsoneselected)
        for i, clip in enumerate([clip1,clip2,clip3]):
            self.failUnlessEqual(clip.start, 2 * gst.SECOND)
            self.failUnlessEqual(clip.start + clip.duration, threeclips)
        self.failUnlessEqual(clip4.start, 2 * gst.SECOND)
        self.failUnlessEqual(clip4.duration + clip4.start,
            fourclipsoneselected)

    def testGetObjs(self):
        obj1 = self.makeTimelineObject()
        obj2 = self.makeTimelineObject()
        obj3 = self.makeTimelineObject()
        obj4 = self.makeTimelineObject()

        obj1.start = 0 * gst.SECOND
        obj1.duration = 5 * gst.SECOND
        obj1.priority = 1

        obj2.start = 5 * gst.SECOND
        obj2.duration = 5 * gst.SECOND
        obj2.priority = 2

        obj3.start = 8 * gst.SECOND
        obj3.duration = 5 * gst.SECOND
        obj3.priority = 3

        obj4.start = 15 * gst.SECOND
        obj4.duration = 5 * gst.SECOND
        obj4.priority = 4

        timeline = self.timeline

        time1 = 0 * gst.SECOND
        time2 = 5 * gst.SECOND
        time3 = 9 * gst.SECOND
        time4 = 14 * gst.SECOND
        tmp_obj_list = []

        # Objects before time.
        tmp_obj_list = []
        result = timeline.getObjsBeforeTime(time1)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = [obj1]
        result = timeline.getObjsBeforeTime(time2)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = [obj1]
        result = timeline.getObjsBeforeTime(time3)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = [obj1, obj2, obj3]
        result = timeline.getObjsBeforeTime(time4)
        self.failUnlessEqual(result, tmp_obj_list)

        # Objects after time.
        tmp_obj_list = [obj1, obj2, obj3, obj4]
        result = timeline.getObjsAfterTime(time1)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = [obj2, obj3, obj4]
        result = timeline.getObjsAfterTime(time2)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = [obj4]
        result = timeline.getObjsAfterTime(time3)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = [obj4]
        result = timeline.getObjsAfterTime(time4)
        self.failUnlessEqual(result, tmp_obj_list)

        # Objects at time.
        tmp_obj_list = []
        result = timeline.getObjsAtTime(time1)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = []
        result = timeline.getObjsAtTime(time2)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = [obj2, obj3]
        result = timeline.getObjsAtTime(time3)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = []
        result = timeline.getObjsAtTime(time4)
        self.failUnlessEqual(result, tmp_obj_list)

        # Objects in region.
        tmp_obj_list = [obj1]
        result = timeline.getObjsInRegion(time1, time2)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = []
        result = timeline.getObjsInRegion(time3, time4)
        self.failUnlessEqual(result, tmp_obj_list)
        tmp_obj_list = [obj3]
        result = timeline.getObjsInRegion(time1, time4, \
            min_priority=3, max_priority=4)
        self.failUnlessEqual(result, tmp_obj_list)

    def testGetKeyframe(self):
        timeline_object0 = self.makeTimelineObject()
        timeline_object1 = self.makeTimelineObject()
        timeline_object3 = self.makeTimelineObject()

        timeline_object0.start = 0 * gst.SECOND
        timeline_object0.duration = 1 * gst.SECOND
        timeline_object0.priority = 0

        timeline_object1.start = 1 * gst.SECOND
        timeline_object1.duration = 5 * gst.SECOND
        timeline_object1.priority = 1

        timeline_object3.start = 15 * gst.SECOND
        timeline_object3.duration = 5 * gst.SECOND
        timeline_object3.priority = 2

        factory = AudioTestSourceFactory()
        stream = AudioStream(gst.Caps("audio/x-raw-int"))
        track_object = SourceTrackObject(factory, stream)
        self.track1.addTrackObject(track_object)
        timeline_object2 = TimelineObject(factory)
        timeline_object2.addTrackObject(track_object)
        self.timeline.addTimelineObject(timeline_object2)
        timeline_object2.start = 3 * gst.SECOND
        timeline_object2.duration = 10 * gst.SECOND
        timeline_object2.priority = 1

        interpolator = track_object.getInterpolator("volume")
        keyframe_position = 7 * gst.SECOND - timeline_object2.start
        interpolator.newKeyframe(keyframe_position, 0.0, "mode")

        timeline = self.timeline

        time1 = 0
        time2 = 0.5 * gst.SECOND
        time3 = 2 * gst.SECOND
        time4 = 6.5 * gst.SECOND
        time5 = 10 * gst.SECOND
        time6 = 14 * gst.SECOND
        time7 = 25 * gst.SECOND

        result = timeline.getPrevKeyframe(time1)
        self.failUnlessEqual(result, None)
        result = timeline.getPrevKeyframe(time2)
        self.failUnlessEqual(result, 0 * gst.SECOND)
        result = timeline.getPrevKeyframe(time3)
        self.failUnlessEqual(result, 1 * gst.SECOND)
        result = timeline.getPrevKeyframe(time4)
        self.failUnlessEqual(result, 6 * gst.SECOND)
        result = timeline.getPrevKeyframe(time5)
        self.failUnlessEqual(result, 7 * gst.SECOND)
        result = timeline.getPrevKeyframe(time6)
        self.failUnlessEqual(result, 13 * gst.SECOND)
        result = timeline.getPrevKeyframe(time7)
        self.failUnlessEqual(result, 20 * gst.SECOND)

        result = timeline.getNextKeyframe(time1)
        self.failUnlessEqual(result, 1 * gst.SECOND)
        result = timeline.getNextKeyframe(time2)
        self.failUnlessEqual(result, 1 * gst.SECOND)
        result = timeline.getNextKeyframe(time3)
        self.failUnlessEqual(result, 3 * gst.SECOND)
        result = timeline.getNextKeyframe(time4)
        self.failUnlessEqual(result, 7 * gst.SECOND)
        result = timeline.getNextKeyframe(time5)
        self.failUnlessEqual(result, 13 * gst.SECOND)
        result = timeline.getNextKeyframe(time6)
        self.failUnlessEqual(result, 15 * gst.SECOND)
        result = timeline.getNextKeyframe(time7)
        self.failUnlessEqual(result, None)

        other_object2 = timeline_object2.split(8 * gst.SECOND)
        timeline_object2.start = 5 * gst.SECOND
        other_object2.start = 7 * gst.SECOND
        time1 = 7 * gst.SECOND
        time2 = 10 * gst.SECOND
        result = timeline.getNextKeyframe(time1)
        self.failUnlessEqual(result, 9 * gst.SECOND)
        result = timeline.getNextKeyframe(time2)
        self.failUnlessEqual(result, 12 * gst.SECOND)

        position = 8.5 * gst.SECOND
        interpolator = other_object2.track_objects[0].getInterpolator("volume")
        interpolator.newKeyframe(position)
        result = timeline.getNextKeyframe(time2)
        self.failUnlessEqual(result, 10.5 * gst.SECOND)

class TestLink(TestCase):

    def test(self):
        pass

    def testAddRemoveTimelineObjects(self):
        source_factory = StubFactory()
        source_factory.addOutputStream(VideoStream(gst.Caps("video/x-raw-yuv")))
        timeline_object1 = TimelineObject(source_factory)
        timeline_object2 = TimelineObject(source_factory)

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
        self.source_factory = StubFactory()
        self.stream = AudioStream(gst.Caps('audio/x-raw-int'))
        self.source_factory.addOutputStream(self.stream)
        self.track1 = Track(self.stream)
        self.track2 = Track(self.stream)
        self.track_object1 = SourceTrackObject(self.source_factory, self.stream)
        self.track_object2 = SourceTrackObject(self.source_factory, self.stream)
        self.track_object3 = SourceTrackObject(self.source_factory, self.stream)
        self.track1.addTrackObject(self.track_object1)
        self.track1.addTrackObject(self.track_object2)
        self.track2.addTrackObject(self.track_object3)
        self.timeline_object1 = TimelineObject(self.source_factory)
        self.timeline_object1.addTrackObject(self.track_object1)
        self.timeline_object2 = TimelineObject(self.source_factory)
        self.timeline_object2.addTrackObject(self.track_object2)
        self.timeline_object3 = TimelineObject(self.source_factory)
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
        del self.source_factory
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
        source_factory = self.source_factory
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
        source_factory = FakeSourceFactory()
        stream = AudioStream(gst.Caps("meh"))
        track_object1 = SourceTrackObject(source_factory, stream)
        track_object2 = SourceTrackObject(source_factory, stream)
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
        del source_factory

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

        self.source_factory = StubFactory()
        self.effect_factory = FakeEffectFactory()

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
        del self.source_factory
        del self.effect_factory
        TestCase.tearDown(self)

    def testNoStreams(self):
        self.failUnlessRaises(TimelineError, self.timeline.addSourceFactory, self.source_factory)

    def testAudioOnly(self):
        self.source_factory.addOutputStream(self.audio_stream1)
        self.timeline.addSourceFactory(self.source_factory)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 1)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 0)
        self.failUnlessEqual(len(self.video_track1.track_objects), 0)
        self.failUnlessEqual(len(self.video_track2.track_objects), 0)

    def testVideoOnly(self):
        self.source_factory.addOutputStream(self.video_stream1)
        self.timeline.addSourceFactory(self.source_factory)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 0)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 0)
        self.failUnlessEqual(len(self.video_track1.track_objects), 1)
        self.failUnlessEqual(len(self.video_track2.track_objects), 0)

    def testVideoStreamVideoEffect(self):
        self.source_factory.addOutputStream(self.video_stream1)
        self.timeline.addSourceFactory(self.source_factory)
        self.effect_factory.addInputStream(self.video_stream1)
        self.effect_factory.addOutputStream(self.video_stream2)
        self.timeline.addEffectFactoryOnObject(self.effect_factory, self.timeline.timeline_objects)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 0)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 0)
        self.failUnlessEqual(len(self.video_track1.track_objects), 2)
        self.failUnlessEqual(len(self.video_track2.track_objects), 0)

    def testAudioStreamAudioEffect(self):
        self.source_factory.addOutputStream(self.audio_stream1)
        self.timeline.addSourceFactory(self.source_factory)
        self.effect_factory.addInputStream(self.audio_stream1)
        self.effect_factory.addOutputStream(self.audio_stream2)
        self.timeline.addEffectFactoryOnObject(self.effect_factory, self.timeline.timeline_objects)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 2)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 0)
        self.failUnlessEqual(len(self.video_track1.track_objects), 0)
        self.failUnlessEqual(len(self.video_track2.track_objects), 0)

    def test1Audio1Video(self):
        self.source_factory.addOutputStream(self.audio_stream1)
        self.source_factory.addOutputStream(self.video_stream1)
        self.timeline.addSourceFactory(self.source_factory)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 1)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 0)
        self.failUnlessEqual(len(self.video_track1.track_objects), 1)
        self.failUnlessEqual(len(self.video_track2.track_objects), 0)

    def testConflictNotEnoughTracks(self):
        # 3 audio streams, only 2 audio tracks in the timeline
        self.source_factory.addOutputStream(self.audio_stream1)
        self.source_factory.addOutputStream(self.audio_stream2)
        self.source_factory.addOutputStream(self.audio_stream3)
        self.failUnlessRaises(TimelineError, self.timeline.addSourceFactory,
                self.source_factory, strict=True)
        self.failUnlessEqual(len(self.audio_track1.track_objects), 0)
        self.failUnlessEqual(len(self.audio_track2.track_objects), 0)
        self.failUnlessEqual(len(self.video_track1.track_objects), 0)
        self.failUnlessEqual(len(self.video_track2.track_objects), 0)

class TestContexts(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.timeline = Timeline()
        self.source_factory = StubFactory()
        self.stream = AudioStream(gst.Caps('audio/x-raw-int'))
        self.source_factory.addOutputStream(self.stream)
        self.track1 = Track(self.stream)
        self.track2 = Track(self.stream)
        self.track_object1 = SourceTrackObject(self.source_factory, self.stream)
        self.track_object2 = SourceTrackObject(self.source_factory, self.stream)
        self.track_object3 = SourceTrackObject(self.source_factory, self.stream)
        self.track1.addTrackObject(self.track_object1)
        self.track1.addTrackObject(self.track_object2)
        self.track2.addTrackObject(self.track_object3)
        self.timeline_object1 = TimelineObject(self.source_factory)
        self.timeline_object1.addTrackObject(self.track_object1)
        self.timeline_object2 = TimelineObject(self.source_factory)
        self.timeline_object2.addTrackObject(self.track_object2)
        self.timeline_object3 = TimelineObject(self.source_factory)
        self.timeline_object3.addTrackObject(self.track_object3)
        self.timeline.addTimelineObject(self.timeline_object1)
        self.timeline.addTimelineObject(self.timeline_object2)
        self.timeline.addTimelineObject(self.timeline_object3)
        self.other = set([self.track_object2, self.track_object3])

    def testMoveContext(self):
        # set up the initial state of the timeline and create the track object
        # [focus]     [t2   ]     [t3     ]
        self.track_object1.start = 0
        self.track_object1.duration = gst.SECOND * 5
        self.track_object2.start = 15 * gst.SECOND
        self.track_object3.start = 25 * gst.SECOND
        context = MoveContext(self.timeline, self.track_object1, set())

        # make an edit, check that the edit worked as expected
        #    [focus]  [t2   ]     [t3     ]
        context.editTo(gst.SECOND * 10, 0)
        self.failUnlessEqual(self.track_object1.start, gst.SECOND * 10)
        self.failUnlessEqual(self.track_object1.duration,  gst.SECOND * 5)
        self.failUnlessEqual(self.track_object1.in_point, 0)
        self.failUnlessEqual(self.track_object2.start, gst.SECOND * 15)
        self.failUnlessEqual(self.track_object3.start, gst.SECOND * 25)

        # change to the ripple mode, check that the edit worked as expected
        #            [focus]  [t2   ]     [t3     ]
        context.setMode(context.RIPPLE)
        context.editTo(gst.SECOND * 20, 0)
        self.failUnlessEqual(self.track_object1.start, gst.SECOND * 20)
        self.failUnlessEqual(self.track_object1.duration,  gst.SECOND * 5)
        self.failUnlessEqual(self.track_object1.in_point, 0)
        self.failUnlessEqual(self.track_object2.start, gst.SECOND * 35)
        self.failUnlessEqual(self.track_object3.start, gst.SECOND * 45)

        # change back to default mode, and make sure this works as expected
        #             [t2   ]     [t3     ]
        #            [focus]
        context.setMode(context.DEFAULT)
        self.failUnlessEqual(self.track_object1.start, gst.SECOND * 20)
        self.failUnlessEqual(self.track_object1.duration,  gst.SECOND * 5)
        self.failUnlessEqual(self.track_object1.in_point, 0)
        self.failUnlessEqual(self.track_object2.start, gst.SECOND * 15)
        self.failUnlessEqual(self.track_object3.start, gst.SECOND * 25)
        context.finish()

    def testMoveContextOverlapDifferentTracks(self):
        # start
        # track1:          [focus][t2]
        # track2:  [t3 ]
        self.track_object1.start = 20 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object1.priority = 1
        self.track_object2.start = 30 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1
        self.track_object3.start = 1 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        # move to
        # track1:     [focus][t2]
        # track2:  [t3 ]
        context = MoveContext(self.timeline, self.track_object1,
                set([self.track_object2]))
        context.editTo(gst.SECOND * 1, 0)
        context.finish()
        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration,  10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration,  10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration,  10 * gst.SECOND)

        # move to
        # track1:     [focus][t2]
        # track2:             [t3 ]
        context = MoveContext(self.timeline, self.track_object3,
                set([]))
        context.editTo(gst.SECOND * 10, 0)
        context.finish()
        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration,  10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration,  10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration,  10 * gst.SECOND)

    def testMoveContextOverlapTransition(self):
        # start
        # track1:  [focus  ][  t2  ]
        # track2:  [t3 ]
        self.track_object1.start = 0 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object1.priority = 1
        self.track_object2.start = 10 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1
        self.track_object3.start = 0 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        # move to
        # track1:  [focus[  ]t2  ]
        # track2:  [t3 ]
        context = MoveContext(self.timeline, self.track_object2, set([]))
        context.editTo(gst.SECOND * 5, 1)
        context.finish()
        self.failUnlessEqual(self.track_object1.start, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration,  10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration,  10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration,  10 * gst.SECOND)

    def testMoveContextFocusNotEarliest(self):
        #     [t2  ][focus]  [t3     ]
        self.track_object1.start = 10 * gst.SECOND
        self.track_object1.duration = 5 * gst.SECOND
        self.track_object2.start = 1 * gst.SECOND
        self.track_object2.duration = 9 * gst.SECOND
        self.track_object3.start = 15 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1
        other = set([self.track_object2])

        context = MoveContext(self.timeline, self.track_object1, other)
        context.editTo(20 * gst.SECOND, 0)

        #                           [t2  ][focus]
        #                    [t3     ]
        self.failUnlessEqual(self.track_object1.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)

        context.setMode(context.RIPPLE)

        #                            [t2  ][focus]  [t3     ]
        self.failUnlessEqual(self.track_object1.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 25 * gst.SECOND)

        context.setMode(context.DEFAULT)

        #                           [t2  ][focus]
        #                    [t3     ]
        self.failUnlessEqual(self.track_object1.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)

        context.finish()

    def testMoveContextMargins(self):
        self.other = set([self.track_object3])

        self.track_object1.start = 16 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND

        self.track_object2.start = 10 * gst.SECOND
        self.track_object2.duration = 5 * gst.SECOND

        self.track_object3.start = 3 * gst.SECOND
        self.track_object3.duration = 7 * gst.SECOND

        # move before left margin, should clamp
        context = MoveContext(self.timeline, self.track_object1, self.other)
        context.editTo(8 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 2 * gst.SECOND)

        # move back, no clamp
        context = MoveContext(self.timeline, self.track_object1, self.other)
        context.editTo(16 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 16 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 3 * gst.SECOND)

        # move past right margin, should clamp
        context = MoveContext(self.timeline, self.track_object2, self.other)
        context.editTo(20 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 16 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 4 * gst.SECOND)

    def testMoveContextMarginsPriorityChange(self):
        self.other = set([self.track_object3])

        self.track_object1.start = 5 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object1.priority = 0

        self.track_object2.start = 5 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1

        self.track_object3.start = 15 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        # same start, priority bump
        context = MoveContext(self.timeline, self.track_object2, self.other)
        context.editTo(5 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.priority, 0)
        self.failUnlessEqual(self.track_object2.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.priority, 1)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.priority, 1)

        # collapse left
        self.track_object2.start = 4 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1

        context = MoveContext(self.timeline, self.track_object2, self.other)
        context.editTo(4 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.priority, 0)
        self.failUnlessEqual(self.track_object2.start, 4 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.priority, 1)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.priority, 1)

        # collapse right
        self.track_object2.start = 6 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1

        context = MoveContext(self.timeline, self.track_object2, self.other)
        context.editTo(6 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.priority, 0)
        self.failUnlessEqual(self.track_object2.start, 6 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.priority, 1)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.priority, 1)

    def testMoveContextMarginsPriorityChangeMore(self):
        self.other = set([self.track_object3])

        self.track_object1.start = 20 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object1.priority = 0

        self.track_object2.start = 10 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1

        self.track_object3.start = 20 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        # same start, priority bump
        context = MoveContext(self.timeline, self.track_object2, self.other)
        context.editTo(10 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.priority, 0)
        self.failUnlessEqual(self.track_object2.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.priority, 1)
        self.failUnlessEqual(self.track_object3.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.priority, 1)

        # collapse left
        self.track_object2.start = 9 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1

        self.track_object3.start = 19 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        context = MoveContext(self.timeline, self.track_object2, self.other)
        context.editTo(9 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.priority, 0)
        self.failUnlessEqual(self.track_object2.start, 9 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.priority, 1)
        self.failUnlessEqual(self.track_object3.start, 19 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.priority, 1)

        # collapse right
        self.track_object2.start = 21 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1

        self.track_object3.start = 31 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        context = MoveContext(self.timeline,
                self.track_object3, set([self.track_object2]))
        context.editTo(31 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.priority, 0)
        self.failUnlessEqual(self.track_object2.start, 21 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.priority, 1)
        self.failUnlessEqual(self.track_object3.start, 31 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.priority, 1)

    def testMoveContextMarginsZigZag(self):
        self.track_object4 = SourceTrackObject(self.source_factory, self.stream)
        self.track1.addTrackObject(self.track_object4)
        self.timeline_object4 = TimelineObject(self.source_factory)
        self.timeline_object4.addTrackObject(self.track_object4)
        self.timeline.addTimelineObject(self.timeline_object4)

        self.track_object1.start = 0 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object1.priority = 0

        self.track_object2.start = 15 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 0

        self.track_object3.start = 10 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        self.track_object4.start = 25 * gst.SECOND
        self.track_object4.duration = 10 * gst.SECOND
        self.track_object4.priority = 1

        context = MoveContext(self.timeline, self.track_object2,
                set([self.track_object3]))
        context.editTo(9 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.priority, 0)
        self.failUnlessEqual(self.track_object2.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.priority, 0)
        self.failUnlessEqual(self.track_object3.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.priority, 1)
        self.failUnlessEqual(self.track_object4.start, 25 * gst.SECOND)
        self.failUnlessEqual(self.track_object4.priority, 1)

        context = MoveContext(self.timeline, self.track_object2,
                set([self.track_object3]))
        context.editTo(25 * gst.SECOND, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.priority, 0)
        self.failUnlessEqual(self.track_object2.start, 20 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.priority, 0)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.priority, 1)
        self.failUnlessEqual(self.track_object4.start, 25 * gst.SECOND)
        self.failUnlessEqual(self.track_object4.priority, 1)

        del self.timeline_object4
        del self.track_object4

    def testTrimStartContext(self):
        self.track_object1.start = 1 * gst.SECOND
        self.track_object1.in_point = 3 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object2.start = 11 * gst.SECOND
        self.track_object2.in_point = 10 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object3.start = 25 * gst.SECOND
        self.track_object3.in_point = 20 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND

        # set up the initial state of the timeline and create the track object
        # [focus]     [t2   ]     [t3     ]
        context = TrimStartContext(self.timeline, self.track_object1, self.other)
        context.editTo(gst.SECOND * 5, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 7 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.in_point, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 25 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.in_point, 20 * gst.SECOND)

    def testTrimStartContextMargins(self):
        self.track_object1.start = 1 * gst.SECOND
        self.track_object1.in_point = 2 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object2.start = 12 * gst.SECOND
        self.track_object2.in_point = 3 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND

        context = TrimStartContext(self.timeline, self.track_object2, self.other)
        context.editTo(gst.SECOND * 9, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 2 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.in_point, 2 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration, 11 * gst.SECOND)

    def testTrimStartContextMarginsDifferentTracks(self):
        # start
        # track1:        [focus][t2]
        # track2:  [t3 ]
        self.track_object1.start = 20 * gst.SECOND
        self.track_object1.in_point = 15 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object1.priority = 1
        self.track_object2.start = 30 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.priority = 1
        self.track_object3.start = 1 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        # trim back to
        # track1:    [     focus][t2]
        # track2:  [t3 ]
        context = TrimStartContext(self.timeline, self.track_object1, set([]))
        context.editTo(gst.SECOND * 5, 0)
        context.finish()
        self.failUnlessEqual(self.track_object1.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration,  25 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 30 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration,  10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration,  10 * gst.SECOND)

    def testTrimEndContext(self):
        self.track_object1.start = 1 * gst.SECOND
        self.track_object1.in_point = 3 * gst.SECOND
        self.track_object1.duration = 15 * gst.SECOND
        self.track_object2.start = 16 * gst.SECOND
        self.track_object2.in_point = 10 * gst.SECOND
        self.track_object2.duration = 16 * gst.SECOND
        self.track_object3.start = 32 * gst.SECOND
        self.track_object3.in_point = 19 * gst.SECOND
        self.track_object3.duration = 23 * gst.SECOND

        context = TrimEndContext(self.timeline, self.track_object1, self.other)
        context.editTo(gst.SECOND * 10, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 3 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration, 9 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 16 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.in_point, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration, 16 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 32 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.in_point, 19 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration, 23 * gst.SECOND)

    def testTrimEndContextMargins(self):
        self.track_object1.start = 1 * gst.SECOND
        self.track_object1.in_point = 2 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object2.start = 12 * gst.SECOND
        self.track_object2.in_point = 3 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND

        context = TrimEndContext(self.timeline, self.track_object1, self.other)
        context.editTo(gst.SECOND * 13, 0)
        context.finish()

        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 2 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 12 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.in_point, 3 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration, 10 * gst.SECOND)

    def testTrimEndContextMarginsDifferentTracks(self):
        # start
        # track1:  [t1][t2 ]
        # track2:             [t3 ]
        self.track_object1.start = 1 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object1.priority = 1
        self.track_object2.start = 10 * gst.SECOND
        self.track_object2.duration = 10 * gst.SECOND
        self.track_object2.timeline_object.factory.duration = 30 * gst.SECOND
        self.track_object2.priority = 1
        self.track_object3.start = 25 * gst.SECOND
        self.track_object3.duration = 10 * gst.SECOND
        self.track_object3.priority = 1

        # extend to
        # track1:  [t1][t2    ]
        # track2:           [t3 ]
        context = TrimEndContext(self.timeline, self.track_object2, set([]))
        context.editTo(gst.SECOND * 30, 0)
        context.finish()
        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration,  10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration,  20 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 25 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration,  10 * gst.SECOND)

    def testTrimStartRipple(self):
        # [t2]  [t3]  [t1]

        self.track_object2.start = 1 * gst.SECOND
        self.track_object2.duration = 4 * gst.SECOND

        self.track_object3.start = 10 * gst.SECOND
        self.track_object3.duration = 5 * gst.SECOND

        self.track_object1.start = 15 * gst.SECOND
        self.track_object1.duration = 10 * gst.SECOND
        self.track_object1.trimStart(20 * gst.SECOND)
        # set maximum duration on focus
        self.track_object1.factory.duration = 10 * gst.SECOND

        self.failUnlessEqual(self.track_object1.start,20 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration, 5 * gst.SECOND)

        # test basic trim

        context = TrimStartContext(self.timeline, self.track_object1, self.other)
        context.editTo(gst.SECOND * 15, 0)

        self.failUnlessEqual(self.track_object1.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.in_point, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.in_point, 0 * gst.SECOND)

        # switch to ripple mode

        context.setMode(context.RIPPLE)

        self.failUnlessEqual(self.track_object1.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.in_point, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 9 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.in_point, 0 * gst.SECOND)

        # ripple right

        context.editTo(25 * gst.SECOND, 0)
        self.failUnlessEqual(self.track_object1.start, 25 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 6 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)

        # check that ripple is clamped to object duration

        context.editTo(30 * gst.SECOND, 0)
        self.failUnlessEqual(self.track_object1.start, 25 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 6 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)

        # test switch back to default

        context.setMode(context.DEFAULT)
        self.failUnlessEqual(self.track_object1.start, 25 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 10 * gst.SECOND)

        # test switch back to ripple

        context.setMode(context.RIPPLE)
        self.failUnlessEqual(self.track_object1.start, 25 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.in_point, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 6 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)

        context.finish()

    def testTrimEndContextRipple(self):
        # [t1][t2][t3]

        self.track_object1.start = 1 * gst.SECOND
        self.track_object1.duration = 4 * gst.SECOND
        self.track_object1.factory.duration = 10 * gst.SECOND
        self.track_object2.start = 5 * gst.SECOND
        self.track_object2.duration = 5 * gst.SECOND
        self.track_object3.start = 10 * gst.SECOND
        self.track_object3.duration = 5 * gst.SECOND

        # test default trim

        context = TrimEndContext(self.timeline, self.track_object1, self.other)
        context.editTo(gst.SECOND * 10, 0)

        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration, 9 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration, 5 * gst.SECOND)

        # switch to ripple mode

        context.setMode(context.RIPPLE)

        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration, 9 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 15 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration, 5 * gst.SECOND)

        context.editTo(gst.SECOND * 10, 0)

        # check that we can't ripple past focal object duration

        context.editTo(gst.SECOND * 15, 0)
        self.failUnlessEqual(self.track_object1.duration, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 11 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 16 * gst.SECOND)

        # check that we can't ripple before initial start of focal object

        context.editTo(0, 0)
        self.failUnlessEqual(self.track_object1.duration, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 6 * gst.SECOND)

        # switch back to default mode

        context.setMode(context.DEFAULT)

        self.failUnlessEqual(self.track_object1.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object1.duration, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.duration, 5 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.duration, 5 * gst.SECOND)

        # switch back to ripple mode

        context.setMode(context.RIPPLE)

        self.failUnlessEqual(self.track_object1.duration, 0 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 1 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 6 * gst.SECOND)

        context.finish()

    def testEmptyOther(self):
        context = MoveContext(self.timeline, self.track_object1, set())
        context.finish()
        context = TrimStartContext(self.timeline, self.track_object1, set())
        context.finish()
        context = TrimEndContext(self.timeline, self.track_object1, set())
        context.finish()

    def testNothingToRipple(self):
        self.track_object1.start = 20 * gst.SECOND
        self.track_object1.duration = 5 * gst.SECOND
        self.track_object2.start = 10 * gst.SECOND
        self.track_object2.duration = 1 * gst.SECOND
        self.track_object2.priority = 1
        self.track_object3.start = 11 * gst.SECOND
        self.track_object3.duration = 1 * gst.SECOND
        self.track_object3.priority = 1

        context = MoveContext(self.timeline, self.track_object1, set())
        context.setMode(context.RIPPLE)
        context.editTo(10 * gst.SECOND, 0)

        self.failUnlessEqual(self.track_object1.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object2.start, 10 * gst.SECOND)
        self.failUnlessEqual(self.track_object3.start, 11 * gst.SECOND)

    def tearDown(self):
        del self.timeline_object1
        del self.timeline_object2
        del self.timeline_object3
        del self.track_object1
        del self.track_object2
        del self.track_object3
        del self.track1
        del self.track2
        del self.source_factory
        del self.stream
        del self.timeline
        del self.other
        TestCase.tearDown(self)
