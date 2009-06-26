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
from pitivi.utils import UNKNOWN_DURATION, get_controllable_properties
from pitivi.log.loggable import Loggable
from pitivi.stream import VideoStream, AudioStream
from pitivi.factories.test import VideoTestSourceFactory, \
        AudioTestSourceFactory
from pitivi.elements.mixer import SmartAdderBin

class TrackError(Exception):
    pass

class Keyframe(Signallable):

    """Represents a single point on an interpolation curve"""

    __signals__ = {
        "value-changed" : ['value'],
        "time-changed" : ['time'],
        "mode-changed" : ['mode'],
    }

    def __init__(self, parent):
        self.parent = parent

## Properties

    _mode = gst.INTERPOLATE_LINEAR

    def setMode(self, mode):
        if self.parent:
            self.parent.setKeyframeMode(self, mode)
        else:
            self.setObjectMode(mode)

    def setObjectMode(self, mode):
        self._mode = mode
        self.emit("mode-changed", mode)

    def getMode(self):
        return self._mode

    mode = property(getMode, setMode)

    _time = 0

    def setTime(self, time):
        if self.parent:
            self.parent.setKeyframeTime(self, time)
        else:
            self.setObjectTime(time)

    def setObjectTime(self, time):
        self._time = time
        self.emit("time-changed", time)

    def getTime(self):
        return self._time

    time = property(getTime, setTime)

    _value = None

    def setValue(self, value):
        if self.parent:
            self.parent.setKeyframeValue(self, value)
        else:
            self.setObjectValue(value)

    def setObjectValue(self, value):
        self._value = value
        self.emit("value-changed", value)

    def getValue(self):
        return self._value

    value = property(getValue, setValue)

    def __cmp__(self, other):
        if other:
            return cmp(self.time, other.time)
        return self

class FixedKeyframe(Keyframe):

    def setTime(self, time):
        pass

    time = property(Keyframe.getTime, setTime)

class Interpolator(Signallable, Loggable):

    """The bridge between the gstreamer dynamic property API and pitivi track
    objects.

    * creates gnl.Controller() objects
    * binds controller to track object's gnlobject
    * allows client code to manipulate the interpolation curve by adding,
      removing, and mutating discrete keyframe objects

    There are two special control points: the start and end points, which are
    "fixed" to the start and end of the clip in the timeline. 

    Timestamps given are assumed to be relative to the start of the clip. This
    seems to be the normal behavior when the element being controlled is
    internal to the gnlsource or gnloperation.
    """

    __signals__ = {
        'keyframe-added' : ['keyframe'],
        'keyframe-removed' : ['keyframe'],
        'keyframe-moved' : ['keyframe'],
    }

    def __init__(self, trackobject, element, prop):
        Loggable.__init__(self)
        self.debug("track:%r, element:%r, property:%r", trackobject, element, prop)
        self._element = element
        self._default = self._element.get_property(prop.name)
        #self._default = 0
        self._property = prop
        self._keyframes = []
        # FIXME: get this from the property's param spec
        # NOTE: keyframes necessarily work only on a closed range
        self.lower = 0
        self.upper = 1

        # FIXME: don't create separate controllers for each Interpolator
        # FIXME: uncomment this when back-end support works
        self.debug("Creating a GstController for element %r and property %s",
                   self._element, prop.name)
        self._controller = gst.Controller(self._element, prop.name)
        self._controller.set_interpolation_mode(prop.name, gst.INTERPOLATE_LINEAR)

        self.start = FixedKeyframe(self)
        self.end = FixedKeyframe(self)
        self.start.value = self._default
        self.start.setObjectTime(0)
        self.end.value = self._default
        self.end.setObjectTime(trackobject.factory.duration)

        #data = ((self.start.time, self.start.value), (self.end.time,
        #    self.end.value))
        #self._controller.set_from_list(prop.name, data)

    def newKeyFrame(self, time, value=None, mode=None):
        """add a new keyframe at the specified time, optionally with specified
        value and specified mode. If not specified, these will be computed so
        that the new keyframe likes on the existing curve at that timestampi

        returns: the keyframe object"""
        self.debug("time:%s, value:%r, mode:%r",
                   gst.TIME_ARGS(time), value, mode)
        #TODO: calculate value
        if value is None:
            value = self._default
        if mode is None:
            # FIXME: uncomment this when back-end support works
            #mode = self._controller.get_interpolation_mode()
            mode = gst.INTERPOLATE_LINEAR

        kf = Keyframe(self)
        kf._time = time
        kf._value = value
        kf._mode = mode

        self._keyframes.append(kf)

        self._controller.set(self._property.name, kf.time, kf.value)

        self.emit("keyframe-added", kf)

        return kf

    def removeKeyFrame(self, keyframe):
        # FIXME: uncomment this when back-end support works
        self._controller.unset(self._property.name, keyframe.time)
        if keyframe is not self.start and keyframe is not self.end:
            self._keyframes.remove(keyframe)
            self.emit("keyframe-removed", keyframe)

    def setKeyframeMode(self, kf, mode):
        # FIXME: currently InterpolationSourceControllers only support a
        # single mode. Suporting per-keyframe modes would require implementing
        # a custom interplation source controller.
        # For now, whenever one keyframe's mode changes, we'll set the mode
        # globally
        for keyframe in self.keyframes:
            keyframe.setObjectMode(mode)
        # FIXME: uncomment when backend works
        #self._controller.set_interpolation_mode(mode)

    def setKeyframeTime(self, kf, time):
        time = max(self.start.time, min(self.end.time, time))
        self._keyframeTimeValueChanged(kf, time, kf.value)
        kf.setObjectTime(time)

    def setKeyframeValue(self, kf, value):
        value = max(self.lower, min(self.upper, value))
        self._keyframeTimeValueChanged(kf, kf.time, value)
        kf.setObjectValue(value)

    def _keyframeTimeValueChanged(self, kf, ptime, value):
        self.debug("kf.time:%s, ptime:%s, value:%r",
                   gst.TIME_ARGS(kf.time),
                   gst.TIME_ARGS(ptime), value)
        # FIXME: uncomment this when back-end support works
        if kf.time != ptime:
            self._controller.unset(self._property.name, kf.time)
        self._controller.set(self._property.name, ptime, value)
        self.emit("keyframe-moved", kf)

    def getKeyframes(self):
        # FIXME: make this more efficient
        yield self.start
        for kf in sorted(self._keyframes):
            yield kf
        yield self.end

    def getInteriorKeyframes(self):
        """Same as above but does not include start, or end points"""
        for kf in sorted(self._keyframes):
            yield kf

    keyframes = property(getKeyframes)

class TrackObject(Signallable, Loggable):

    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'in-point-changed': ['in-point'],
        'out-point-changed': ['out-point'],
        'media-duration-changed': ['media-duration'],
        'priority-changed': ['priority'],
        'selected-changed' : ['state'],
    }

    def __init__(self, factory, stream, start=0,
            duration=0, in_point=0,
            media_duration=0, priority=0):
        Loggable.__init__(self)
        self.debug("factory:%r", factory)
        self.factory = factory
        self.stream = stream
        self.track = None
        self.timeline_object = None
        self.gnl_object = obj = self._makeGnlObject()
        self.makeBin()
        self.trimmed_start = 0
        self.keyframes = []

        if start != 0:
            obj.props.start = start

        if duration == 0:
            if factory.duration != gst.CLOCK_TIME_NONE:
                duration = factory.duration
            elif factory.default_duration != gst.CLOCK_TIME_NONE:
                duration = factory.default_duration

        obj.props.duration = duration

        obj.props.media_start = in_point
        if media_duration != 0:
            obj.props.media_duration = media_duration
        else:
            obj.props.media_duration = duration

        obj.props.priority = priority

        self._connectToSignals(obj)

        self.interpolators = {}

        wprops = factory.getInterpolatedProperties(stream).keys()
        if stream:
            for sobj, prop in get_controllable_properties(self.gnl_object):
                if prop.name in wprops:
                    self.interpolators[prop] = Interpolator(self, sobj, prop)

    def getInterpolator(self, property_name):
        for prop, interpolator in self.interpolators.iteritems():
            if property_name == prop.name:
                return interpolator
        return None

    def release(self):
        self._disconnectFromSignals()
        self.releaseBin()
        self.gnl_object = None
        self.factory = None

    def copy(self):
        cls = self.__class__
        other = cls(self.factory, self.stream, start=self.start,
            duration=self.duration, in_point=self.in_point,
            media_duration=self.media_duration, priority=self.priority)
        other.trimmed_start = self.trimmed_start

        for property, interpolator in self.interpolators.iteritems():
            other_interpolator = other.getInterpolator(property.name)
            other_interpolator.start.value = interpolator.start.value
            other_interpolator.start.mode = interpolator.start.mode
            other_interpolator.end.value = interpolator.end.value
            other_interpolator.end.mode = interpolator.end.mode
            for kf in interpolator.getInteriorKeyframes():
                other_interpolator.newKeyFrame(kf.time,
                    kf.value,
                    kf.mode)

        return other

    def snapStartDurationTime(self, *args):
        return

    # FIXME: there's a lot of boilerplate here that could be factored in a
    # metaclass.  Do we like metaclasses in pitivi?
    def _getStart(self):
        return self.gnl_object.props.start

    def setStart(self, position, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setStart(position, snap)
        else:
            if snap:
                raise TrackError()

            self.setObjectStart(position)

    def setObjectStart(self, position):
        if self.gnl_object.props.start != position:
            self.gnl_object.props.start = position

    start = property(_getStart, setStart)

    def _getDuration(self):
        return self.gnl_object.props.duration

    def setDuration(self, position, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setDuration(position, snap)
        else:
            if snap:
                raise TrackError()

            self.setObjectDuration(position)

    def setObjectDuration(self, position):
        if self.gnl_object.props.duration != position:
            self.gnl_object.props.duration = position

    duration = property(_getDuration, setDuration)

    def _getInPoint(self):
        return self.gnl_object.props.media_start

    def setInPoint(self, position, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setInPoint(position, snap)
        else:
            self.setObjectInPoint(position)

    def setObjectInPoint(self, value):
        if self.gnl_object.props.media_start != value:
            self.gnl_object.props.media_start = value

    in_point = property(_getInPoint, setInPoint)

    def _getOutPoint(self):
        return self.gnl_object.props.media_stop

    out_point = property(_getOutPoint)

    def _getMediaDuration(self):
        return self.gnl_object.props.media_duration

    def setMediaDuration(self, position, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.setMediaDuration(position, snap)
        else:
            self.setObjectMediaDuration(position)

    def setObjectMediaDuration(self, position):
        if self.gnl_object.props.media_duration != position:
            self.gnl_object.props.media_duration = position

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
        if self.gnl_object.props.priority != priority:
            self.gnl_object.props.priority = priority

    priority = property(_getPriority, setPriority)

    def trimStart(self, position, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.trimStart(position, snap)
        else:
            self.trimObjectStart(position)

    def trimObjectStart(self, position):
        # clamp position to be inside the object
        position = max(self.start - self.trimmed_start, position)
        position = min(position, self.start + self.duration)
        new_duration = max(0, self.start + self.duration - position)

        delta = position - self.start
        self.trimmed_start += delta
        self.setObjectStart(position)
        self.setObjectDuration(new_duration)
        self.setObjectInPoint(self.trimmed_start)
        self.setObjectMediaDuration(new_duration)

    def split(self, position, snap=False):
        if self.timeline_object is not None:
            return self.timeline_object.split(position, snap)
        else:
            return self.splitObject(position)

    def splitObject(self, position):
        start = self.gnl_object.props.start
        duration = self.gnl_object.props.duration
        if position <= start or position >= start + duration:
            raise TrackError("can't split at position %s" % gst.TIME_ARGS(position))

        other = self.copy()

        other.trimObjectStart(position)
        self.setObjectDuration(position - self.gnl_object.props.start)
        self.setObjectMediaDuration(position - self.gnl_object.props.start)

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
        if self.stream is None:
            raise TrackError
        if self.gnl_object is None:
            raise TrackError

        bin = self.factory.makeBin(self.stream)
        self.gnl_object.add(bin)

    def releaseBin(self):
        elts = list(self.gnl_object.elements())
        if elts:
            bin = elts[0]
            self.gnl_object.remove(bin)
            bin.set_state(gst.STATE_NULL)
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


class Track(Signallable):
    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'track-object-added': ['track_object'],
        'track-object-removed': ['track_object'],
        'max-priority-changed': ['track_object']
    }

    def __init__(self, stream):
        self.stream = stream
        self.composition = gst.element_factory_make('gnlcomposition')
        self.composition.connect('notify::start', self._compositionStartChangedCb)
        self.composition.connect('notify::duration', self._compositionDurationChangedCb)
        self.track_objects = []
        self.default_track_object = None
        self._max_priority = 0

        default_track_object = self._getDefaultTrackObjectForStream(stream)
        if default_track_object:
            self.setDefaultTrackObject(default_track_object)

        self.mixer = self._getMixerForStream(stream)
        if self.mixer:
            self.composition.add(self.mixer)

    def _getDefaultTrackObjectForStream(self, stream):
        if isinstance(stream, VideoStream):
            return self._getDefaultVideoTrackObject(stream)
        elif isinstance(stream, AudioStream):
            return self._getDefaultAudioTrackObject(stream)

        return None

    def _getDefaultVideoTrackObject(self, stream):
        factory = VideoTestSourceFactory(pattern='black')
        track_object = SourceTrackObject(factory, stream)

        return track_object

    def _getDefaultAudioTrackObject(self, stream):
        factory = AudioTestSourceFactory(wave='silence')
        track_object = SourceTrackObject(factory, stream)

        return track_object

    def _getMixerForStream(self, stream):
        if isinstance(stream, AudioStream):
            gnl = gst.element_factory_make("gnloperation", "top-level-audio-mixer")
            m = SmartAdderBin()
            gnl.add(m)
            gnl.props.expandable = True
            gnl.props.priority = 0
            return gnl
        return None

    def _getStart(self):
        return self.composition.props.start

    def setDefaultTrackObject(self, track_object):
        if self.default_track_object is not None:
            self.removeTrackObject(self.default_track_object)

        self.default_track_object = None
        # FIXME: implement TrackObject.priority
        track_object.gnl_object.props.priority = 2**32-1
        self.default_track_object = track_object
        try:
            self.addTrackObject(track_object)
        except:
            self.default_track_object = None
            raise

    start = property(_getStart)

    def _getDuration(self):
        return self.composition.props.duration

    duration = property(_getDuration)

    def _getMaxPriority(self):
        return self._max_priority

    max_priority = property(_getMaxPriority)

    _max_priority = 0

    @property
    def max_priority(self):
        return self._max_priority

    def _trackObjectPriorityCb(self, trackobject, priority):
        op = self._max_priority
        self._max_priority = max((obj.priority for obj in self.track_objects
            if obj is not self.default_track_object))
        if op != self._max_priority:
            self.emit("max-priority-changed", self._max_priority)

    def _connectToTrackObjectSignals(self, track_object):
        track_object.connect("priority-changed", self._trackObjectPriorityCb)

    def _disconnectTrackObjectSignals(self, track_object):
        track_object.disconnect_by_function(self._trackObjectPriorityCb)

    def addTrackObject(self, track_object):
        if track_object.track is not None:
            raise TrackError()

        try:
            self.composition.add(track_object.gnl_object)
        except gst.AddError:
            raise TrackError()

        track_object.track = weakref.proxy(self)
        self.track_objects.append(track_object)

        self._connectToTrackObjectSignals(track_object)

        self._updateMaxPriority()
        self._connectToTrackObject(track_object)

        self.emit('track-object-added', track_object)

    def removeTrackObject(self, track_object):
        if track_object.track is None:
            raise TrackError()

        try:
            self.composition.remove(track_object.gnl_object)
            track_object.gnl_object.set_state(gst.STATE_NULL)
        except gst.RemoveError:
            raise TrackError()

        self._disconnectFromTrackObject(track_object)
        track_object.release()

        self.track_objects.remove(track_object)
        track_object.track = None
        self._disconnectTrackObjectSignals(track_object)

        self._updateMaxPriority()

        self.emit('track-object-removed', track_object)

    def removeAllTrackObjects(self):
        for track_object in list(self.track_objects):
            self.removeTrackObject(track_object)

    def _updateMaxPriority(self):
        priorities = [track_object.priority for track_object in
            self.track_objects if track_object is not self.default_track_object]
        if not priorities:
            max_priority = 0
        else:
            max_priority = max(priorities)
        if max_priority != self._max_priority:
            self._max_priority = max_priority
            self.emit('max-priority-changed', self._max_priority)

    def _compositionStartChangedCb(self, composition, pspec):
        start = composition.props.start
        self.emit('start-changed', start)

    def _compositionDurationChangedCb(self, composition, pspec):
        duration = composition.props.duration
        self.emit('duration-changed', duration)

    def _trackObjectPriorityChangedCb(self, track_object, priority):
        self._updateMaxPriority()

    def _connectToTrackObject(self, track_object):
        track_object.connect('priority-changed',
                self._trackObjectPriorityChangedCb)

    def _disconnectFromTrackObject(self, track_object):
        track_object.disconnect_by_function(self._trackObjectPriorityChangedCb)

    def enableUpdates(self):
        self.composition.props.update = True

    def disableUpdates(self):
        self.composition.props.update = False
