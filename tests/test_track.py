# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/timeline.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

from common import TestCase
import gst

from pitivi.timeline.track import Track, SourceTrackObject, TrackError
from pitivi.stream import AudioStream, VideoStream
from common import SignalMonitor, StubFactory
from pitivi.factories.test import AudioTestSourceFactory

class TrackSignalMonitor(SignalMonitor):
    def __init__(self, track_object):
        SignalMonitor.__init__(self, track_object, 'start-changed',
                'duration-changed', 'in-point-changed', 'out-point-changed',
                'media-duration-changed', 'priority-changed')

class TestTrackObject(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        stream = AudioStream(gst.Caps("audio/x-raw-int"))
        self.factory = StubFactory()
        gst.debug("%r" % self.factory.duration)
        self.factory.addOutputStream(stream)
        self.track_object = SourceTrackObject(self.factory, stream)
        self.monitor = TrackSignalMonitor(self.track_object)

    def tearDown(self):
        self.monitor = None
        self.track_object.release()
        self.track_oject = None
        self.factory = None
        TestCase.tearDown(self)

    def testDefaultProperties(self):
        obj = self.track_object
        self.failUnlessEqual(obj.start, 0)
        self.failUnlessEqual(obj.duration, self.factory.duration)
        self.failUnlessEqual(obj.in_point, 0)
        self.failUnlessEqual(obj.out_point, self.factory.duration)
        self.failUnlessEqual(obj.media_duration, self.factory.duration)
        self.failUnlessEqual(obj.rate, 1)
        self.failUnlessEqual(obj.priority, 0)

        gnl_object = obj.gnl_object
        self.failUnlessEqual(gnl_object.props.start, 0)
        self.failUnlessEqual(gnl_object.props.duration, self.factory.duration)
        self.failUnlessEqual(gnl_object.props.media_start, 0)
        self.failUnlessEqual(gnl_object.props.media_stop,
                self.factory.duration)
        self.failUnlessEqual(gnl_object.props.media_duration,
                self.factory.duration)
        self.failUnlessEqual(gnl_object.props.rate, 1)
        self.failUnlessEqual(obj.priority, 0)

    def testChangePropertiesFromTrackObject(self):
        obj = self.track_object
        gnl_object = obj.gnl_object

        start = 1 * gst.SECOND
        obj.start = start
        self.failUnlessEqual(obj.start, start)
        self.failUnlessEqual(gnl_object.props.start, start)
        self.failUnlessEqual(self.monitor.start_changed_count, 1)

        duration = 10 * gst.SECOND
        obj.duration = duration
        self.failUnlessEqual(obj.duration, duration)
        self.failUnlessEqual(gnl_object.props.duration, duration)
        self.failUnlessEqual(self.monitor.duration_changed_count, 1)

        in_point = 5 * gst.SECOND
        obj.in_point = in_point
        self.failUnlessEqual(obj.in_point, in_point)
        self.failUnlessEqual(gnl_object.props.media_start, in_point)
        self.failUnlessEqual(self.monitor.in_point_changed_count, 1)

        media_duration = 5 * gst.SECOND
        obj.media_duration = media_duration
        self.failUnlessEqual(obj.media_duration, media_duration)
        self.failUnlessEqual(gnl_object.props.media_duration, media_duration)
        self.failUnlessEqual(obj.out_point, in_point + media_duration)
        self.failUnlessEqual(gnl_object.props.media_stop,
                in_point + media_duration)
        self.failUnlessEqual(self.monitor.media_duration_changed_count, 1)
        self.failUnlessEqual(self.monitor.out_point_changed_count, 1)

        # test video stream$
        obj.stream_type = VideoStream
        priority = 100
        gnl_priority = 3 * 100 + 2 + obj._stagger
        obj.priority = priority
        self.failUnlessEqual(obj.priority, priority)
        self.failUnlessEqual(gnl_object.props.priority, gnl_priority)
        self.failUnlessEqual(self.monitor.priority_changed_count, 1)

        # test audio stream
        obj.stream_type = AudioStream
        priority = 55
        gnl_priority = 4 * 55 + 2 + 2 * obj._stagger
        obj.priority = priority
        self.failUnlessEqual(obj.priority, priority)
        self.failUnlessEqual(gnl_object.props.priority, gnl_priority)
        self.failUnlessEqual(self.monitor.priority_changed_count, 2)


    def testChangePropertiesFromGnlObject(self):
        obj = self.track_object
        gnl_object = obj.gnl_object

        start = 1 * gst.SECOND
        gnl_object.props.start = start
        self.failUnlessEqual(obj.start, start)
        self.failUnlessEqual(self.monitor.start_changed_count, 1)

        duration = 10 * gst.SECOND
        gnl_object.props.duration = duration
        self.failUnlessEqual(obj.duration, duration)
        self.failUnlessEqual(self.monitor.duration_changed_count, 1)

        in_point = 5 * gst.SECOND
        gnl_object.props.media_start = in_point
        self.failUnlessEqual(obj.in_point, in_point)
        self.failUnlessEqual(self.monitor.in_point_changed_count, 1)

        media_duration = 5 * gst.SECOND
        gnl_object.props.media_duration = media_duration
        self.failUnlessEqual(obj.media_duration, media_duration)
        self.failUnlessEqual(self.monitor.media_duration_changed_count, 1)
        self.failUnlessEqual(obj.out_point, in_point + media_duration)
        self.failUnlessEqual(self.monitor.media_duration_changed_count, 1)
        self.failUnlessEqual(self.monitor.out_point_changed_count, 1)

        # video stream
        obj.stream_type = VideoStream
        gnl_priority = 100
        priority = (100 - 2 - obj._stagger) // 3
        gnl_object.props.priority = gnl_priority
        self.failUnlessEqual(obj.priority, priority)
        self.failUnlessEqual(gnl_object.props.priority, gnl_priority)
        self.failUnlessEqual(self.monitor.priority_changed_count, 1)

        # video stream
        obj.stream_type = AudioStream
        gnl_priority = 55
        priority = (55 - 2 - obj._stagger) // 4
        gnl_object.props.priority = gnl_priority
        self.failUnlessEqual(obj.priority, priority)
        self.failUnlessEqual(gnl_object.props.priority, gnl_priority)
        self.failUnlessEqual(self.monitor.priority_changed_count, 2)


    def testTrimStart(self):
        obj = self.track_object

        # start at 2 seconds with length 10 seconds
        obj.start = 2 * gst.SECOND
        obj.in_point = 1 * gst.SECOND
        obj.duration = 10 * gst.SECOND

        self.failUnlessEqual(self.monitor.duration_changed_count, 1)

        # trim at lower edge
        monitor = TrackSignalMonitor(obj)
        time = 2 * gst.SECOND
        obj.trimStart(time)
        self.failUnlessEqual(obj.start, time)
        self.failUnlessEqual(obj.in_point, 1 * gst.SECOND)
        self.failUnlessEqual(obj.duration, 10 * gst.SECOND)
        self.failUnlessEqual(obj.rate, 1)
        # we didn't change the start/in-point/duration (it was the same as before)
        self.failUnlessEqual(monitor.start_changed_count, 0)
        self.failUnlessEqual(monitor.in_point_changed_count, 0)
        self.failUnlessEqual(monitor.duration_changed_count, 0)

        # trim at upper edge
        monitor = TrackSignalMonitor(obj)
        time = 12 * gst.SECOND
        obj.trimStart(time)
        self.failUnlessEqual(obj.start, time)
        self.failUnlessEqual(obj.in_point, 11 * gst.SECOND)
        self.failUnlessEqual(obj.duration, 0)
        self.failUnlessEqual(obj.rate, 1)
        self.failUnlessEqual(monitor.start_changed_count, 1)
        self.failUnlessEqual(monitor.in_point_changed_count, 1)
        self.failUnlessEqual(monitor.duration_changed_count, 1)

        # trim before lower edge, should clamp
        monitor = TrackSignalMonitor(obj)
        time = 0 * gst.SECOND
        obj.trimStart(time)
        self.failUnlessEqual(obj.start, 1 * gst.SECOND)
        self.failUnlessEqual(obj.in_point, 0)
        self.failUnlessEqual(obj.duration, 11 * gst.SECOND)
        self.failUnlessEqual(obj.rate, 1)
        self.failUnlessEqual(monitor.start_changed_count, 1)
        self.failUnlessEqual(monitor.in_point_changed_count, 1)
        self.failUnlessEqual(monitor.duration_changed_count, 1)

        # trimp past upper edge, should clamp
        monitor = TrackSignalMonitor(obj)
        time = 13 * gst.SECOND
        obj.trimStart(time)
        self.failUnlessEqual(obj.start, 12 * gst.SECOND)
        self.failUnlessEqual(obj.in_point, 11 * gst.SECOND)
        self.failUnlessEqual(obj.duration, 0)
        self.failUnlessEqual(obj.rate, 1)
        self.failUnlessEqual(monitor.start_changed_count, 1)
        self.failUnlessEqual(monitor.in_point_changed_count, 1)
        self.failUnlessEqual(monitor.duration_changed_count, 1)

        # trim somewhere in the middle
        monitor = TrackSignalMonitor(obj)
        time = 7 * gst.SECOND
        obj.trimStart(time)
        self.failUnlessEqual(obj.start, time)
        self.failUnlessEqual(obj.in_point, 6 * gst.SECOND)
        self.failUnlessEqual(obj.duration, 5 * gst.SECOND)
        self.failUnlessEqual(obj.rate, 1)
        self.failUnlessEqual(monitor.start_changed_count, 1)
        self.failUnlessEqual(monitor.in_point_changed_count, 1)
        self.failUnlessEqual(monitor.duration_changed_count, 1)

        obj.start = 10 * gst.SECOND
        obj.in_point = 11 * gst.SECOND
        obj.duration = 15 * gst.SECOND

        # this should be possible
        monitor = TrackSignalMonitor(obj)
        time = 0 * gst.SECOND
        obj.trimStart(time)
        self.failUnlessEqual(obj.start, 0 * gst.SECOND)
        self.failUnlessEqual(obj.in_point, 1 * gst.SECOND)
        self.failUnlessEqual(obj.duration, 25 * gst.SECOND)
        self.failUnlessEqual(obj.rate, 1)
        self.failUnlessEqual(monitor.start_changed_count, 1)
        self.failUnlessEqual(monitor.in_point_changed_count, 1)
        self.failUnlessEqual(monitor.duration_changed_count, 1)


    def testSplitObject(self):
        DURATION = 10 * gst.SECOND

        factory = AudioTestSourceFactory()
        factory.duration = DURATION
        stream_ = AudioStream(gst.Caps("audio/x-raw-int"))
        obj = SourceTrackObject(factory, stream_)
        track = Track(stream_)
        track.addTrackObject(obj)

        obj.start = 3 * gst.SECOND
        obj.duration = DURATION


        # create a zig-zag volume curve
        interpolator = obj.getInterpolator("volume")
        expected = dict(((t * gst.SECOND, (t % 2, gst.INTERPOLATE_LINEAR))
            for t in xrange(3, 10, 3)))
        for time, (value, mode) in expected.iteritems():
            interpolator.newKeyframe(time, value, mode)

        def getKeyframes(obj):
            keyframes = obj.getInterpolator("volume").getInteriorKeyframes()
            return dict(((kf.time, (kf.value, kf.mode)) for kf in keyframes))

        monitor = TrackSignalMonitor(obj)

        self.failUnlessRaises(TrackError, obj.splitObject, 2 * gst.SECOND)
        self.failUnlessRaises(TrackError, obj.splitObject, 14 * gst.SECOND)

        # should these be possible (ie create empty objects) ?
        self.failUnlessRaises(TrackError, obj.splitObject, 3 * gst.SECOND)
        self.failUnlessRaises(TrackError, obj.splitObject, 13 * gst.SECOND)

        # splitObject at 4s should result in:
        # obj (start 3, end 4) other1 (start 4, end 13)
        other1 = obj.splitObject(4 * gst.SECOND)
        self.failUnlessEqual(expected, getKeyframes(other1))

        self.failUnlessEqual(obj.start, 3 * gst.SECOND)
        self.failUnlessEqual(obj.in_point, 0 * gst.SECOND)
        self.failUnlessEqual(obj.duration, 1 * gst.SECOND)
        self.failUnlessEqual(obj.rate, 1)

        self.failUnlessEqual(other1.start, 4 * gst.SECOND)
        self.failUnlessEqual(other1.in_point, 1 * gst.SECOND)
        self.failUnlessEqual(other1.duration, 9 * gst.SECOND)
        self.failUnlessEqual(other1.rate, 1)

        self.failUnlessEqual(monitor.start_changed_count, 0)
        self.failUnlessEqual(monitor.duration_changed_count, 1)

        # move other1 back to start = 1
        other1.start = 1 * gst.SECOND

        # splitObject again other1
        monitor = TrackSignalMonitor(other1)

        other2 = other1.splitObject(6 * gst.SECOND)
        self.failUnlessEqual(expected, getKeyframes(other2))
        self.failUnlessEqual(other1.start, 1 * gst.SECOND)
        self.failUnlessEqual(other1.in_point, 1 * gst.SECOND)
        self.failUnlessEqual(other1.duration, 5 * gst.SECOND)
        self.failUnlessEqual(other1.rate, 1)

        self.failUnlessEqual(other2.start, 6 * gst.SECOND)
        self.failUnlessEqual(other2.in_point, 6 * gst.SECOND)
        self.failUnlessEqual(other2.duration, 4 * gst.SECOND)
        self.failUnlessEqual(other2.rate, 1)

        self.failUnlessEqual(monitor.start_changed_count, 0)
        self.failUnlessEqual(monitor.duration_changed_count, 1)


class TestTrack(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.factory = StubFactory()
        self.stream = VideoStream(gst.Caps('video/x-raw-rgb'))
        self.factory.addOutputStream(self.stream)
        self.track1 = Track(self.stream)
        self.track2 = Track(self.stream)

    def tearDown(self):
        self.factory = None
        self.stream = None
        self.track1 = None
        self.track2 = None
        TestCase.tearDown(self)

    def testAddRemoveObjects(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1
        track2 = self.track2

        # add an object
        obj1 = SourceTrackObject(factory, stream)
        self.failUnlessEqual(obj1.track, None)
        track1.addTrackObject(obj1)
        self.failIfEqual(obj1.track, None)

        # can't add twice
        self.failUnlessRaises(TrackError, track1.addTrackObject, obj1)

        # can't add to two different tracks
        self.failUnlessRaises(TrackError, track2.addTrackObject, obj1)

        # add a second object
        obj2 = SourceTrackObject(factory, stream)
        self.failUnlessEqual(obj2.track, None)
        track1.addTrackObject(obj2)
        self.failIfEqual(obj2.track, None)

        # remove
        track1.removeTrackObject(obj1)
        self.failUnlessEqual(obj1.track, None)

        # can't remove twice
        self.failUnlessRaises(TrackError, track1.removeTrackObject, obj1)

        track1.removeTrackObject(obj2)
        self.failUnlessEqual(obj2.track, None)

    def testRemoveAllTrackObjects(self):
        track = self.track1
        factory = self.factory

        # check that can be called on an empty track
        track.removeAllTrackObjects()

        objs = []
        for i in xrange(10):
            obj = SourceTrackObject(factory, self.stream)
            objs.append(obj)
            track.addTrackObject(obj)

        for obj in objs:
            self.failIfEqual(obj.track, None)

        track.removeAllTrackObjects()

        for obj in objs:
            self.failUnlessEqual(obj.track, None)

    def testMaxPriority(self):
        track = self.track1
        factory = self.factory

        obj1 = SourceTrackObject(factory, self.stream)
        obj1.priority = 10

        self.failUnlessEqual(track.max_priority, 0)
        track.addTrackObject(obj1)
        self.failUnlessEqual(track.max_priority, 10)

        obj2 = SourceTrackObject(factory, self.stream)
        obj2.priority = 5
        track.addTrackObject(obj2)
        self.failUnlessEqual(track.max_priority, 10)

        obj3 = SourceTrackObject(factory, self.stream)
        obj3.priority = 14
        track.addTrackObject(obj3)
        self.failUnlessEqual(track.max_priority, 14)

        obj3.priority = 9
        self.failUnlessEqual(track.max_priority, 10)

        obj2.priority = 11
        self.failUnlessEqual(track.max_priority, 11)

        track.removeTrackObject(obj1)
        self.failUnlessEqual(track.max_priority, 11)

        track.removeTrackObject(obj2)
        self.failUnlessEqual(track.max_priority, 9)

        track.removeTrackObject(obj3)
        self.failUnlessEqual(track.max_priority, 0)

    def testGetPreviousTrackObject(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1

        obj1 = SourceTrackObject(factory, stream)
        track1.addTrackObject(obj1)

        obj2 = SourceTrackObject(factory, stream)
        track1.addTrackObject(obj2)

        obj3 = SourceTrackObject(factory, stream)
        track1.addTrackObject(obj3)

        obj4 = SourceTrackObject(factory, stream)
        track1.addTrackObject(obj4)

        obj1.start = 1 * gst.SECOND
        obj1.duration = 5 * gst.SECOND
        obj1.priority = 1

        obj2.start = 8 * gst.SECOND
        obj2.duration = 5 * gst.SECOND
        obj2.priority = 1

        obj3.start = 6 * gst.SECOND
        obj3.duration = 5 * gst.SECOND
        obj3.priority = 2

        obj4.start = 7 * gst.SECOND
        obj4.duration = 5 * gst.SECOND
        obj4.priority = 3

        # no previous object
        self.failUnlessRaises(TrackError, track1.getPreviousTrackObject, obj4)

        # same priority
        prev = track1.getPreviousTrackObject(obj2)
        self.failUnlessEqual(prev, obj1)

        # given priority
        prev = track1.getPreviousTrackObject(obj2, priority=2)
        self.failUnlessEqual(prev, obj3)

        # any priority
        prev = track1.getPreviousTrackObject(obj2, priority=None)
        self.failUnlessEqual(prev, obj4)

        obj3.start = 8 * gst.SECOND
        # same start
        prev = track1.getPreviousTrackObject(obj2, priority=None)
        self.failUnlessEqual(prev, obj3)

    def testGetNextTrackObject(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1

        obj1 = SourceTrackObject(factory, stream)
        track1.addTrackObject(obj1)

        obj2 = SourceTrackObject(factory, stream)
        track1.addTrackObject(obj2)

        obj3 = SourceTrackObject(factory, stream)
        track1.addTrackObject(obj3)

        obj4 = SourceTrackObject(factory, stream)
        track1.addTrackObject(obj4)

        obj1.start = 1 * gst.SECOND
        obj1.duration = 5 * gst.SECOND
        obj1.priority = 1

        obj2.start = 8 * gst.SECOND
        obj2.duration = 5 * gst.SECOND
        obj2.priority = 1

        obj3.start = 6 * gst.SECOND
        obj3.duration = 5 * gst.SECOND
        obj3.priority = 2

        obj4.start = 7 * gst.SECOND
        obj4.duration = 5 * gst.SECOND
        obj4.priority = 3

        # no next object
        self.failUnlessRaises(TrackError, track1.getNextTrackObject, obj2)

        # same priority
        prev = track1.getNextTrackObject(obj1)
        self.failUnlessEqual(prev, obj2)

        # given priority
        prev = track1.getNextTrackObject(obj1, priority=2)
        self.failUnlessEqual(prev, obj3)

        # any priority
        prev = track1.getNextTrackObject(obj3, priority=None)
        self.failUnlessEqual(prev, obj4)

    def testCopyMakeBinNotCalled(self):
        factory = self.factory
        stream = self.stream
        obj1 = SourceTrackObject(factory, stream)
        # this used to raise an exception
        obj2 = obj1.copy()
        self.failUnlessEqual(obj1.start, obj2.start)
