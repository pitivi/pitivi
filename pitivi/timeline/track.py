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

import gst
import weakref

from pitivi.signalinterface import Signallable
from pitivi.utils import UNKNOWN_DURATION

class TrackError(Exception):
    pass

class TrackObject(object, Signallable):
    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'in-point-changed': ['in-point'],
        'out-point-changed': ['out-point']
    }

    def __init__(self, factory, start=0,
            duration=UNKNOWN_DURATION, in_point=gst.CLOCK_TIME_NONE,
            out_point=0, priority=0):
        self.factory = factory
        self.track = None
        self.timeline_object = None
        self.gnl_object = obj = self._makeGnlObject()
        self.trimmed_start = 0
        
        if start != 0:
            obj.props.start = start

        if duration != UNKNOWN_DURATION or obj.props.duration == 0:
            obj.props.duration = duration

        if in_point != gst.CLOCK_TIME_NONE:
            obj.props.media_start = in_point

        if out_point != 0:
            obj.props.media_duration = out_point
        
        self.priority = priority

        self._connectToSignals(obj)
        
    def copy(self):
        cls = self.__class__
        other = cls(self.factory, start=self.start - self.trimmed_start,
            duration=self.duration + self.trimmed_start, in_point=self.in_point,
            out_point=self.out_point, priority=self.priority)

        return other

    def snapStartDurationTime(self, *args):
        return

    # FIXME: there's a lot of boilerplate here that could be factored in a
    # metaclass.  Do we like metaclasses in pitivi?
    def _getStart(self):
        return self.gnl_object.props.start

    def setStart(self, time, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setStart(time, snap)
        else:
            if snap:
                raise TrackError()

            self.setObjectStart(time)

    def setObjectStart(self, time):
        self.gnl_object.props.start = time

    start = property(_getStart, setStart)

    def _getDuration(self):
        return self.gnl_object.props.duration

    def setDuration(self, time, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setDuration(time, snap)
        else:
            if snap:
                raise TrackError()

            self.setObjectDuration(time)

    def setObjectDuration(self, time):
        self.gnl_object.props.duration = time

    duration = property(_getDuration, setDuration)

    def _getInPoint(self):
        return self.gnl_object.props.media_start

    def setInPoint(self, time, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setInPoint(time, snap)
        else:
            self.setObjectInPoint(time)

    def setObjectInPoint(self, value):
        self.gnl_object.props.media_start = value

    in_point = property(_getInPoint, setInPoint)

    def _getOutPoint(self):
        return self.gnl_object.props.media_duration

    def setOutPoint(self, time, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setOutPoint(time, snap)
        else:
            self.setObjectOutPoint(time)

    def trimStart(self, time, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.trimStart(time, snap)
        else:
            self.trimObjectStart(time)

    def trimObjectStart(self, time):
        # clamp time to be inside the object
        time = max(self.start - self.trimmed_start, time)
        time = min(time, self.start + self.duration)
        new_duration = max(0, self.start + self.duration - time)

        delta = time - self.start
        self.trimmed_start += delta
        self.setObjectStart(time)
        self.setObjectDuration(new_duration)
        old_in_point = self.in_point
        if old_in_point == gst.CLOCK_TIME_NONE:
            old_in_point = 0

        new_in_point = max(old_in_point + delta, 0)
        self.setObjectInPoint(new_in_point)

    def split(self, time, snap=False):
        if self.timeline_object is not None:
            return self.timeline_object.split(time, snap)
        else:
            return self.splitObject(time)

    def splitObject(self, time):
        if time <= self.start or time >= self.start + self.duration:
            raise TrackError("can't split at time %s" % gst.TIME_ARGS(time))

        other = self.copy()
        other.trimStart(time)
        self.setDuration(time - self.start)

        return other

    def setObjectOutPoint(self, time):
        self.gnl_object.props.media_duration = time

    out_point = property(_getOutPoint, setOutPoint)

    def _notifyStartCb(self, obj, pspec):
        self.emit('start-changed', obj.props.start)

    def _notifyDurationCb(self, obj, pspec):
        self.emit('duration-changed', obj.props.duration)

    def _notifyMediaStartCb(self, obj, pspec):
        self.emit('in-point-changed', obj.props.media_start)

    def _notifyMediaDurationCb(self, obj, pspec):
        self.emit('out-point-changed', obj.props.media_duration)

    def _connectToSignals(self, gnl_object):
        gnl_object.connect('notify::start', self._notifyStartCb)
        gnl_object.connect('notify::duration', self._notifyDurationCb)
        gnl_object.connect('notify::media-start', self._notifyMediaStartCb)
        gnl_object.connect('notify::media-duration',
                self._notifyMediaDurationCb)

    def _makeGnlObject(self):
        raise NotImplementedError()


class SourceTrackObject(TrackObject):
    def _makeGnlObject(self):
        source = gst.element_factory_make('gnlsource')
        # FIXME: set in-point and out-point
        source.props.duration = self.factory.duration
        bin = self.factory.makeBin()
        source.add(bin)
        return source

# FIXME: effects?

class Track(object, Signallable):
    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'track-object-added': ['track_object'],
        'track-object-removed': ['track_object']
    }

    def __init__(self, stream):
        self.stream = stream
        self.composition = gst.element_factory_make('gnlcomposition')
        self.composition.connect('notify::start', self._startChangedCb)
        self.composition.connect('notify::duration', self._durationChangedCb)
        self.track_objects = []

    def _getStart(self):
        return self.composition.props.start

    start = property(_getStart)

    def _getDuration(self):
        return self.composition.props.duration

    duration = property(_getDuration)

    def _startChangedCb(self, composition, pspec):
        start = composition.props.start
        self.emit('start-changed', start)

    def _durationChangedCb(self, composition, pspec):
        duration = composition.props.duration
        self.emit('duration-changed', duration)

    def addTrackObject(self, track_object):
        if track_object.track is not None:
            raise TrackError()

        try:
            self.composition.add(track_object.gnl_object)
        except gst.AddError:
            raise TrackError()

        track_object.track = weakref.proxy(self)
        self.track_objects.append(track_object)
        self.emit('track-object-added', track_object)

    def removeTrackObject(self, track_object):
        if track_object.track is None:
            raise TrackError()

        try:
            self.composition.remove(track_object.gnl_object)
        except gst.RemoveError:
            raise TrackError()

        self.track_objects.remove(track_object)
        track_object.track = None
        self.emit('track-object-removed', track_object)

    def removeAllTrackObjects(self):
        for track_object in list(self.track_objects):
            self.removeTrackObject(track_object)
