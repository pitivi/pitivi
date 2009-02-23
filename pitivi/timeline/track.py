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
from pitivi.stream import VideoStream, AudioStream
from pitivi.factories.test import VideoTestSourceFactory, \
        AudioTestSourceFactory

class TrackError(Exception):
    pass

class TrackObject(object, Signallable):
    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'in-point-changed': ['in-point'],
        'out-point-changed': ['out-point'],
        'media-duration-changed': ['media-duration'],
        'priority-changed': ['priority'],
        'selected-changed' : ['state'],
    }

    def __init__(self, factory, start=0,
            duration=0, in_point=0,
            media_duration=0, priority=0):
        self.factory = factory
        self.track = None
        self.timeline_object = None
        self.gnl_object = obj = self._makeGnlObject()
        self.trimmed_start = 0

        if start != 0:
            obj.props.start = start

        if duration == 0:
            if factory.duration != gst.CLOCK_TIME_NONE:
                duration = factory.duration

        obj.props.duration = duration

        obj.props.media_start = in_point
        if media_duration != 0:
            obj.props.media_duration = media_duration
        else:
            obj.props.media_duration = duration

        obj.props.priority = priority

        self._connectToSignals(obj)

    def release(self):
        self._disconnectFromSignals()
        self.releaseBin()
        self.gnl_object = None
        self.factory = None

    def copy(self):
        cls = self.__class__
        other = cls(self.factory, start=self.start - self.trimmed_start,
            duration=self.duration + self.trimmed_start, in_point=self.in_point,
            media_duration=self.media_duration, priority=self.priority)

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
        return self.gnl_object.props.media_stop

    out_point = property(_getOutPoint)

    def _getMediaDuration(self):
        return self.gnl_object.props.media_duration

    def setMediaDuration(self, time, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setMediaDuration(time, snap)
        else:
            self.setObjectMediaDuration(time)

    def setObjectMediaDuration(self, time):
        self.gnl_object.props.media_duration = time

    media_duration = property(_getMediaDuration, setMediaDuration)

    def _getRate(self):
        return self.gnl_object.props.rate

    rate = property(_getRate)

    def _getPriority(self):
        return self.gnl_object.props.priority

    def setPriority(self, priority):
        if self.timeline_object is not None:
            self.timeline_object.setPriority(priority)
        else:
            self.setObjectPriority(priority)

    def setObjectPriority(self, priority):
        self.gnl_object.props.priority = priority

    priority = property(_getPriority, setPriority)

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
        self.setObjectInPoint(self.trimmed_start)
        self.setObjectMediaDuration(new_duration)

    def split(self, time, snap=False):
        if self.timeline_object is not None:
            return self.timeline_object.split(time, snap)
        else:
            return self.splitObject(time)

    def splitObject(self, time):
        start = self.gnl_object.props.start
        duration = self.gnl_object.props.duration
        if time <= start or time >= start + duration:
            raise TrackError("can't split at time %s" % gst.TIME_ARGS(time))

        other = self.copy()

        other.trimObjectStart(time)
        self.setObjectDuration(time - start)
        self.setObjectMediaDuration(time - start)

        return other

    # True when the track object is part of the timeline's current selection
    __selected = False

    def _getSelected(self):
        return self.__selected

    def setObjectSelected(self, state):
        """Sets the object's selected property to the specified value. This
        should only be called by the track object's parent timeline object."""
        self.__selected = state
        self.emit("selected-changed", state)

    selected = property(_getSelected)

    def makeBin(self):
        if self.track is None:
            raise TrackError()

        bin = self.factory.makeBin(self.track.stream)
        self.gnl_object.add(bin)

    def releaseBin(self):
        elts = list(self.gnl_object.elements())
        if elts:
            bin = elts[0]
            self.gnl_object.remove(bin)
            self.factory.releaseBin(bin)

    def _notifyStartCb(self, obj, pspec):
        self.emit('start-changed', obj.props.start)

    def _notifyDurationCb(self, obj, pspec):
        self.emit('duration-changed', obj.props.duration)

    def _notifyMediaStartCb(self, obj, pspec):
        self.emit('in-point-changed', obj.props.media_start)

    def _notifyMediaDurationCb(self, obj, pspec):
        self.emit('media-duration-changed', obj.props.media_duration)

    def _notifyMediaStopCb(self, obj, pspec):
        self.emit('out-point-changed', obj.props.media_stop)

    def _notifyPriorityCb(self, obj, pspec):
        self.emit('priority-changed', obj.props.priority)

    def _connectToSignals(self, gnl_object):
        gnl_object.connect('notify::start', self._notifyStartCb)
        gnl_object.connect('notify::duration', self._notifyDurationCb)
        gnl_object.connect('notify::media-start', self._notifyMediaStartCb)
        gnl_object.connect('notify::media-duration',
                self._notifyMediaDurationCb)
        gnl_object.connect('notify::media-stop',
                self._notifyMediaStopCb)
        gnl_object.connect('notify::priority',
                self._notifyPriorityCb)

    def _disconnectFromSignals(self):
        if self.gnl_object:
            self.gnl_object.disconnect_by_func(self._notifyStartCb)
            self.gnl_object.disconnect_by_func(self._notifyDurationCb)
            self.gnl_object.disconnect_by_func(self._notifyMediaStartCb)
            self.gnl_object.disconnect_by_func(self._notifyMediaDurationCb)
            self.gnl_object.disconnect_by_func(self._notifyMediaStopCb)
            self.gnl_object.disconnect_by_func(self._notifyPriorityCb)

    def _makeGnlObject(self):
        raise NotImplementedError()


class SourceTrackObject(TrackObject):
    def _makeGnlObject(self):
        source = gst.element_factory_make('gnlsource')
        return source


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
        self.default_track_object = None

        default_track_object = self._getDefaultTrackObjectForStream(stream)
        if default_track_object:
            self.setDefaultTrackObject(default_track_object)

    def _getDefaultTrackObjectForStream(self, stream):
        if isinstance(stream, VideoStream):
            return self._getDefaultVideoTrackObject()
        elif isinstance(stream, AudioStream):
            return self._getDefaultAudioTrackObject()

        return None

    def _getDefaultVideoTrackObject(self):
        factory = VideoTestSourceFactory(pattern='black')
        track_object = SourceTrackObject(factory)

        return track_object

    def _getDefaultAudioTrackObject(self):
        factory = AudioTestSourceFactory(wave='silence')
        track_object = SourceTrackObject(factory)

        return track_object

    def _getStart(self):
        return self.composition.props.start

    def setDefaultTrackObject(self, track_object):
        if self.default_track_object is not None:
            self.removeTrackObject(self.default_track_object)

        self.default_track_object = None
        # FIXME: implement TrackObject.priority
        track_object.gnl_object.props.priority = 2**32-1
        self.addTrackObject(track_object)
        self.default_track_object = track_object

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

        track_object.makeBin()

        self.emit('track-object-added', track_object)

    def removeTrackObject(self, track_object):
        if track_object.track is None:
            raise TrackError()

        try:
            self.composition.remove(track_object.gnl_object)
        except gst.RemoveError:
            raise TrackError()

        track_object.release()

        self.track_objects.remove(track_object)
        track_object.track = None

        self.emit('track-object-removed', track_object)

    def removeAllTrackObjects(self):
        for track_object in list(self.track_objects):
            self.removeTrackObject(track_object)
