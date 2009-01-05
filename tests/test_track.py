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

from unittest import TestCase
import gst

from pitivi.timeline.track import Track, SourceTrackObject, TrackError
from pitivi.stream import AudioStream, VideoStream
from pitivi.utils import UNKNOWN_DURATION

class StubFactory(object):
    pass

class TrackObjectSignalMonitor(object):
    def __init__(self, track_object):
        self.track_object = track_object
        
        track_object.connect('start-changed', self._signal_cb, 'start_changed')
        track_object.connect('duration-changed', self._signal_cb, 'duration_changed')
        track_object.connect('in-point-changed', self._signal_cb, 'in_point_changed')
        track_object.connect('out-point-changed', self._signal_cb, 'out_point_changed')

        self.start_changed_count = 0
        self.duration_changed_count = 0
        self.in_point_changed_count = 0
        self.out_point_changed_count = 0

    def _signal_cb(self, obj, value, name):
        field = '%s_count' % name
        setattr(self, field, getattr(self, field, 0) + 1)

class TestTrackObject(TestCase):
    def setUp(self):
        factory = StubFactory()
        self.track_object = SourceTrackObject(factory)
        self.monitor = TrackObjectSignalMonitor(self.track_object)

    def testDefaultProperties(self):
        obj = self.track_object
        self.failUnlessEqual(obj.start, 0)
        self.failUnlessEqual(obj.duration, UNKNOWN_DURATION)
        self.failUnlessEqual(obj.in_point, gst.CLOCK_TIME_NONE)
        self.failUnlessEqual(obj.out_point, UNKNOWN_DURATION)

        gnl_object = obj.gnl_object
        self.failUnlessEqual(gnl_object.props.start, 0)
        self.failUnlessEqual(gnl_object.props.duration, UNKNOWN_DURATION)
        self.failUnlessEqual(gnl_object.props.media_start,
                gst.CLOCK_TIME_NONE)
        self.failUnlessEqual(gnl_object.props.media_duration,
                UNKNOWN_DURATION)

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
        
        out_point = 5 * gst.SECOND
        obj.out_point = out_point
        self.failUnlessEqual(obj.out_point, out_point)
        self.failUnlessEqual(gnl_object.props.media_duration, out_point)
        self.failUnlessEqual(self.monitor.out_point_changed_count, 1)

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
        
        out_point = 5 * gst.SECOND
        gnl_object.props.media_duration = out_point
        self.failUnlessEqual(obj.out_point, out_point)
        self.failUnlessEqual(self.monitor.out_point_changed_count, 1)

class TestTrackAddRemoveObjects(TestCase):
    def testAddRemoveObjects(self):
        factory = StubFactory()
        stream = VideoStream(gst.Caps('video/x-raw-rgb'))
        track1 = Track(stream)
        track2 = Track(stream)
        
        # add an object
        obj1 = SourceTrackObject(factory)
        self.failUnlessEqual(obj1.track, None)
        track1.addTrackObject(obj1)
        self.failIfEqual(obj1.track, None)

        # can't add twice
        self.failUnlessRaises(TrackError, track1.addTrackObject, obj1)

        # can't add to two different tracks
        self.failUnlessRaises(TrackError, track2.addTrackObject, obj1)

        # add a second object
        obj2 = SourceTrackObject(factory)
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

