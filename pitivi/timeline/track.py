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
        
        if start != 0:
            obj.props.start = start

        if duration != UNKNOWN_DURATION or obj.props.duration == 0:
            obj.props.duration = duration

        if in_point != gst.CLOCK_TIME_NONE:
            obj.props.media_start = in_point

        if out_point != 0:
            obj.props.media_duration = out_point
        
        self._connectToSignals(obj)

    # FIXME: there's a lot of boilerplate here that could be factored in a
    # metaclass.  Do we like metaclasses in pitivi?
    def _getStart(self):
        return self.gnl_object.props.start
    
    def _setStart(self, value):
        self.gnl_object.props.start = value

    start = property(_getStart, _setStart)

    def _getDuration(self):
        return self.gnl_object.props.duration
    
    def _setDuration(self, value):
        self.gnl_object.props.duration = value
    
    duration = property(_getDuration, _setDuration)

    def _getInPoint(self):
        return self.gnl_object.props.media_start
    
    def _setInPoint(self, value):
        self.gnl_object.props.media_start = value
    
    in_point = property(_getInPoint, _setInPoint)

    def _getOutPoint(self):
        return self.gnl_object.props.media_duration
    
    def _setOutPoint(self, value):
        self.gnl_object.props.media_duration = value

    out_point = property(_getOutPoint, _setOutPoint)

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
        return source

# FIXME: effects?

class Track(object, Signallable):
    def __init__(self, stream):
        self.stream = stream
        self.composition = gst.element_factory_make('gnlcomposition')
        self.track_objects = []

    def addTrackObject(self, track_object):
        if track_object.track is not None:
            raise TrackError()

        try:
            self.composition.add(track_object.gnl_object)
        except gst.AddError:
            raise TrackError()

        track_object.track = weakref.proxy(self)
        self.track_objects.append(track_object)

    def removeTrackObject(self, track_object):
        if track_object.track is None:
            raise TrackError()
        
        try:
            self.composition.remove(track_object.gnl_object)
        except gst.RemoveError:
            raise TrackError()

        self.track_objects.remove(track_object)
        track_object.track = None

    def removeAllTrackObjects(self):
        for track_object in list(self.track_objects):
            self.removeTrackObject(track_object)
