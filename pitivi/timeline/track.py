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
import gobject

from pitivi.signalinterface import Signallable
from pitivi.utils import get_controllable_properties, getPreviousObject, \
        getNextObject, start_insort_right, between
from pitivi.log.loggable import Loggable
from pitivi.stream import VideoStream, AudioStream
from pitivi.factories.test import VideoTestSourceFactory, \
        AudioTestSourceFactory
from pitivi.elements.mixer import SmartAdderBin, SmartVideomixerBin
from pitivi.timeline.gap import Gap

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
        'keyframe-removed' : ['keyframe', 'old_value'],
        'keyframe-moved' : ['keyframe', 'old_value'],
    }

    def __init__(self, trackobject, element, prop, minimum=None, maximum=None,
        format=None):
        Loggable.__init__(self)
        self.debug("track:%r, element:%r, property:%r", trackobject, element, prop)
        self._keyframes = []
        self.trackobject = trackobject

        if minimum is None:
            minimum = prop.minimum
        if maximum is None:
            maximum = prop.maximum
        assert not ((minimum is None) or (maximum is None))
        self.lower = minimum
        self.upper = maximum
        self.range = maximum - minimum

        # FIXME: don't necessarily want to create separate controllers for
        # each Interpolator. We should instead create a ControlSource for each
        # element. We can't do this until the new controller interface is
        # exposed in gst-python.
        self.attachToElementProperty(prop, element)
        self._default = self._element.get_property(prop.name)
        self.start = FixedKeyframe(self)
        self.end = FixedKeyframe(self)
        self.start.value = self._default
        self.start.setObjectTime(trackobject.in_point)
        self._keyframeTimeValueChanged(self.start, 0, self.start.value)
        self.end.value = self._default
        if trackobject.in_point == trackobject.out_point:
            self.end.setObjectTime(trackobject.in_point + 1)
        else:
            self.end.setObjectTime(trackobject.out_point)
        self._keyframeTimeValueChanged(self.end, self.end.time, self.end.value)
        self.format = format if format else str

    def attachToElementProperty(self, prop, element):
        self._element = element
        self._property = prop
        self.debug("Creating a GstController for element %r and property %s",
            self._element, prop.name)
        self._controller = gst.Controller(self._element, prop.name)
        self._controller.set_interpolation_mode(prop.name, gst.INTERPOLATE_LINEAR)

    def newKeyframe(self, time_or_keyframe, value=None, mode=None):
        """add a new keyframe at the specified time, optionally with specified
        value and specified mode. If not specified, these will be computed so
        that the new keyframe likes on the existing curve at that timestampi

        returns: the keyframe object"""

        if isinstance(time_or_keyframe, Keyframe):
            keyframe = time_or_keyframe
        else:
            if value is None:
                value = self._controller.get(self._property.name,
                    time_or_keyframe)
            if mode is None:
                # FIXME: Controller.get_interpolation_mode is not wrapped in
                # gst-python, so for now we assume the default is linear.
                # Use the following code to get the current mode when this method becomes
                # available.
                # mode = self._controller.get_interpolation_mode()
                mode = gst.INTERPOLATE_LINEAR

            keyframe = Keyframe(self)
            keyframe._time = time_or_keyframe
            keyframe._value = value
            keyframe._mode = mode

        self.debug("time:%s, value:%r, mode:%r",
                   gst.TIME_ARGS(keyframe.time), keyframe.value, keyframe.mode)

        self._keyframes.append(keyframe)
        self._keyframes.sort()

        self._controller.set(self._property.name, keyframe.time, keyframe.value)

        self.emit("keyframe-added", keyframe)

        return keyframe

    def removeKeyframe(self, keyframe):
        old_value = self._controller.get(self._property.name, keyframe.time)
        self._controller.unset(self._property.name, keyframe.time)
        if keyframe is not self.start and keyframe is not self.end:
            self._keyframes.remove(keyframe)
            self.emit("keyframe-removed", keyframe, old_value)

    def setKeyframeMode(self, kf, mode):
        # FIXME: currently InterpolationSourceControllers only support a
        # single mode. Suporting per-keyframe modes would require implementing
        # a custom interplation source controller.
        # For now, whenever one keyframe's mode changes, we'll set the mode
        # globally.
        for keyframe in self.keyframes:
            keyframe.setObjectMode(mode)
        self._controller.set_interpolation_mode(self._property.name, mode)

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
        old_value = self._controller.get(self._property.name, ptime)
        self._controller.set(self._property.name, ptime, value)
        if kf.time != ptime:
            self._controller.unset(self._property.name, kf.time)
        self.emit("keyframe-moved", kf, old_value)

    def getKeyframes(self):
        yield self.start
        for kf in self._keyframes:
            yield kf
        yield self.end

    def getInteriorKeyframes(self):
        """Same as above but does not include start, or end points"""
        for kf in self._keyframes:
            yield kf

    def getVisibleKeyframes(self):
        """Return start, end and any keyframes included in between"""
        yield self.start
        start_time = self.start.time
        end_time = self.end.time
        for kf in sorted(self._keyframes):
            if between(start_time, kf.time, end_time):
                yield kf
        yield self.end

    def updateMediaStart(self, start):
        self._keyframeTimeValueChanged(self.start, start, self.start.value)
        self.start.setObjectTime(start)

    def updateMediaStop(self, stop):
        self._keyframeTimeValueChanged(self.end, stop, self.end.value)
        self.end.setObjectTime(stop)

    def valueAt(self, time):
        return self._controller.get(self._property.name, time)

    def formatValue(self, value):
        return self.format(value)

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
        'stagger-changed' : ['stagger'],
        'active-changed' : ['active'],
    }

    def __init__(self, factory, stream, start=0,
            duration=0, in_point=0,
            media_duration=0, priority=0):
        Loggable.__init__(self)
        self.debug("factory:%r", factory)
        self.factory = factory
        self.stream = stream
        self.stream_type = type(stream)
        self.track = None
        self.timeline_object = None
        self.interpolators = {}
        self._rebuild_interpolators = False
        self._public_priority = priority
        self._position = 0
        self._stagger = 0
        self.gnl_object = obj = self._makeGnlObject()
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
        self._updatePriority(self._public_priority)

    def getInterpolator(self, property_name):
        self._maybeBuildInterpolators()

        try:
            return self.interpolators[property_name][1]
        except KeyError:
            raise TrackError("no interpolator for '%s'" % property_name)

    def getInterpolators(self):
        self._maybeBuildInterpolators()
        return self.interpolators

    def _maybeBuildInterpolators(self):
        if not self._rebuild_interpolators:
            return

        if not list(self.gnl_object.elements()):
            raise TrackError("makeBin hasn't been called yet")

        self._rebuild_interpolators = False

        factory_properties = self.factory.getInterpolatedProperties(self.stream)

        old_interpolators = self.interpolators
        self.interpolators = {}
        for gst_object, gst_object_property in \
                get_controllable_properties(self.gnl_object):
            prop_name = gst_object_property.name
            if prop_name not in factory_properties:
                continue

            try:
                interpolator = old_interpolators[prop_name][1]
            except KeyError:
                if factory_properties[prop_name]:
                    lower, upper, formatstr = factory_properties[prop_name]
                else:
                    lower, upper, formatstr = None, None, None
                interpolator = Interpolator(self, gst_object,
                    gst_object_property, lower, upper, formatstr)
            else:
                # remove and add again the keyframes so they are set on the
                # current controller
                keyframes = list(interpolator.keyframes)
                for keyframe in keyframes:
                    interpolator.removeKeyframe(keyframe)

                interpolator.attachToElementProperty(gst_object_property,
                        gst_object)
                interpolator.updateMediaStop(self.out_point)

                for keyframe in keyframes:
                    interpolator.newKeyframe(keyframe)

            self.interpolators[gst_object_property.name] = \
                    (gst_object_property, interpolator)

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

        if self.track is not None:
            self.track.addTrackObject(other)
            other.gnl_object.set_property("active",
                                          self.gnl_object.get_property("active"))

        interpolators = self.getInterpolators()
        for property, interpolator in interpolators.itervalues():
            other_interpolator = other.getInterpolator(property.name)
            other_interpolator.start.value = interpolator.start.value
            other_interpolator.start.mode = interpolator.start.mode
            other_interpolator.end.value = interpolator.end.value
            other_interpolator.end.mode = interpolator.end.mode
            for kf in interpolator.getInteriorKeyframes():
                other_interpolator.newKeyframe(kf.time,
                    kf.value,
                    kf.mode)

        return other

    def snapStartDurationTime(self, *args):
        return

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

    def _getActive(self):
        return self.gnl_object.props.active

    def setActive(self, active):
        self.gnl_object.props.active = active

    active = property(_getActive, setActive)

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
        return self._public_priority

    def setPriority(self, priority):
        if self.timeline_object is not None:
            self.timeline_object.setPriority(priority)
        else:
            self.setObjectPriority(priority)

    def setObjectPriority(self, priority):
        if priority != self._public_priority:
            self._updatePriority(priority)

    def _updatePriority(self, priority):
        # The priority of an effect should always be higher than the priority of 
        # the track it is applied to. Those priority are affected when we add a 
        # TrackObject to timeline
        if type(self) is TrackEffect:
            if self.stream_type is VideoStream:
                true_priority = 2 + self._stagger + (3 * priority)
            elif self.stream_type is AudioStream:
                true_priority  = 3 + (2 * self._stagger) + (4 * priority)
        elif self.stream_type is VideoStream:
            true_priority = 3 + self._stagger + (3 * priority)
        elif self.stream_type is AudioStream:
            true_priority  = 3 + (2 * self._stagger) + (4 * priority)

        if self.gnl_object.props.priority != true_priority:
            self.gnl_object.props.priority = true_priority

        self.debug("New priority: %r", self.gnl_object.props.priority)

    priority = property(_getPriority, setPriority)

    def _getStagger(self):
        return self._stagger

    stagger = property(_getStagger)

    def trimStart(self, position, snap=False):
        if self.timeline_object is not None:
            self.timeline_object.trimStart(position, snap)
        else:
            self.trimObjectStart(position)

    def trimObjectStart(self, position):
        # clamp position to be inside the object
        position = max(self.start - self.in_point, position)
        position = min(position, self.start + self.duration)
        new_duration = max(0, self.start + self.duration - position)

        delta = position - self.start
        in_point = self.in_point
        in_point += delta
        self.setObjectStart(position)
        self.setObjectDuration(new_duration)
        self.setObjectInPoint(in_point)
        self.setObjectMediaDuration(new_duration)

    def split(self, position, snap=False):
        if self.timeline_object is not None:
            return self.timeline_object.split(position, snap)
        else:
            return self.splitObject(position)

    def splitObject(self, position):
        start = self.gnl_object.props.start
        duration = self.gnl_object.props.duration
        in_point = self.gnl_object.props.media_start
        if position <= start or position >= start + duration:
            raise TrackError("can't split at position %s" % gst.TIME_ARGS(position))

        other = self.copy()

        # update interpolators
        for prop, i in self.interpolators.itervalues():
            value = i.valueAt(position)
            i.end.setValue(value)
            keyframes = i.getInteriorKeyframes()
            duplicates = []
            for kf in keyframes:
                if kf.getTime() >= (position - start + in_point):
                    duplicates.append(kf)
            for kf in duplicates:
                i.removeKeyframe(kf)

        for prop, i in other.interpolators.itervalues():
            value = i.valueAt(position)
            i.start.setValue(value)
            keyframes = i.getInteriorKeyframes()
            duplicates = []
            for kf in keyframes:
                if kf.getTime() <= (position - start + in_point):
                    duplicates.append(kf)
            for kf in duplicates:
                i.removeKeyframe(kf)

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
            raise TrackError()
        if self.gnl_object is None:
            raise TrackError()

        bin = self._getBin()
        self.gnl_object.add(bin)
        self._rebuild_interpolators = True
        self._maybeBuildInterpolators()

    def _getBin(self):
        return self.factory.makeBin(self.stream)

    def releaseBin(self):
        for bin in list(self.gnl_object.elements()):
            self.gnl_object.remove(bin)
            bin.set_state(gst.STATE_NULL)
            self.factory.releaseBin(bin)
        self._rebuild_interpolators = True

    def _notifyStartCb(self, obj, pspec):
        self.emit('start-changed', obj.props.start)

    def _notifyDurationCb(self, obj, pspec):
        self.emit('duration-changed', obj.props.duration)

    def _notifyMediaStartCb(self, obj, pspec):
        start = obj.props.media_start
        self.emit('in-point-changed', start)
        for p, i in self.interpolators.itervalues():
            i.updateMediaStart(start)

    def _notifyMediaDurationCb(self, obj, pspec):
        self.emit('media-duration-changed', obj.props.media_duration)

    def _notifyMediaStopCb(self, obj, pspec):
        stop = obj.props.media_stop
        self.emit('out-point-changed', stop)
        for p, i in self.interpolators.itervalues():
            i.updateMediaStop(stop)

    def _notifyPriorityCb(self, obj, pspec):
        if self.stream_type is VideoStream:
            true_priority = obj.props.priority
            public_priority = (true_priority - 2 - self._stagger) // 3
        elif self.stream_type is AudioStream:
            true_priority = obj.props.priority
            public_priority = (true_priority - 2 - (2 * self._stagger))// 4
        if self._public_priority != public_priority:
            self._public_priority = public_priority
            self.emit('priority-changed', public_priority)

    def _notifyActiveCb(self, obj, pspec):
        self.emit('active-changed', obj.props.active)

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
        gnl_object.connect('notify::active',
                self._notifyActiveCb)

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

    def updatePosition(self, position):
        if position != self._position:
            self._position = position
            self._stagger = position & 1
            self._updatePriority(self._public_priority)
            self.emit("stagger-changed", self._stagger)

class SourceTrackObject(TrackObject):

    numobjs = 0

    def _makeGnlObject(self):
        source = gst.element_factory_make('gnlsource',
            "gnlsource: " + self.factory.__class__.__name__ +
            str(SourceTrackObject.numobjs))
        SourceTrackObject.numobjs += 1
        return source

class TrackEffect(TrackObject):

    numobjs = 0

    def __init__(self, factory, stream, start=0,
            duration=0, in_point=0,
            media_duration=0, priority=0):
        TrackObject.__init__(self, factory, stream, start=0,
                             duration=0, in_point=0,
                             media_duration=0, priority=0)
        self._element = None

    def _makeGnlObject(self):
        effect = gst.element_factory_make('gnloperation',
            "gnloperation: " + self.factory.__class__.__name__ +
            str(TrackEffect.numobjs))
        TrackEffect.numobjs += 1
        return effect

    def _getBin(self):
        bin, fx = self.factory.makeBin(self.stream)
        self._element = fx

        return bin

    def copy(self):
        other = TrackObject.copy(self)

        if self.track is not None:
            element = self.getElement()
            new_element = other.getElement()
            for prop in gobject.list_properties(element):
                value = element.get_property(prop.name)
                if value != prop.default_value:
                    new_element.set_property(prop.name, value)

        return other

    def getElement(self):
        """
        Permit to get the gst.Element inside the gnl_object that correspond
        to the track factory
        """
        return self._element

class Transition(Signallable):

    __signals__ = {
        "start-changed" : ["start"],
        "duration-changed" : ["duration"],
        "priority-changed" : ["priority"],
    }

    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.start = 0
        self.duration = 0
        self.priority = 0
        self._makeGnlObject()
        self._connectToTrackObjects(a, b)

    def _makeGnlObject(self):
        pass

    def _connectToTrackObjects(self, a, b):
        a.connect("start-changed", self._updateStartDuration)
        a.connect("duration-changed", self._updateStartDuration)
        a.connect("priority-changed", self._updatePriority)
        b.connect("start-changed", self._updateStartDuration)
        b.connect("priority-changed", self._updatePriority)
        a.connect("stagger-changed", self._staggerChanged)
        b.connect("stagger-changed", self._staggerChanged)
        self._updateStartDuration()
        self._updatePriority()

    def _updateStartDuration(self, *unused):
        start = self.b.start
        end = self.a.start + self.a.duration
        duration = max(0, end - start)

        if start != self.start:
            self._updateOperationStart(start)
            self.start = start
            self.emit("start-changed", start)

        if duration != self.duration:
            self._updateOperationDuration(duration)
            self.duration = duration
            self.emit("duration-changed", duration)

        self._updateController()

    def _updatePriority(self, *unused):
        if self.a.priority == self.b.priority:
            priority = self.a.priority
            self._updateOperationPriority(priority)
            self.priority = priority
            self.emit("priority-changed", priority)

    def _staggerChanged(self, *unused):
        self._updateController()

    def _updateController(self):
        pass

    def _updateOperationStart(self, start):
        pass

    def _updateOperationDuration(self, duration):
        pass

    def _updateOperationPriority(self, priority):
        pass

    def addThyselfToComposition(self, composition):
        pass

    def removeThyselfFromComposition(self, composition):
        pass

class VideoTransition(Transition):

    caps = gst.Caps("video/x-raw-yuv,format=(fourcc)AYUV")

    def _makeGnlObject(self):
        trans = gst.element_factory_make("alpha")
        self.controller = gst.Controller(trans, "alpha")
        self.controller.set_interpolation_mode("alpha", gst.INTERPOLATE_LINEAR)

        self.operation = gst.element_factory_make("gnloperation")
        self.operation.add(trans)
        self.operation.props.media_start = 0
        self.operation.props.caps = self.caps

    def addThyselfToComposition(self, composition):
        composition.add(self.operation)

    def removeThyselfFromComposition(self, composition):
        composition.remove(self.operation)
        self.operation.set_state(gst.STATE_NULL)

    def _updateOperationStart(self, start):
        self.operation.props.start = start

    def _updateOperationDuration(self, duration):
        self.operation.props.duration = duration
        self.operation.props.media_duration = duration

    def _updateOperationPriority(self, priority):
        self.operation.props.priority = 1 + 3 * priority

    def _updateController(self):
        if self.a.stagger > self.b.stagger:
            # source a is under source b (higher priority)
            # we fade source B in
            self.controller.unset_all("alpha")
            self.controller.set("alpha", 0, 0.0)
            self.controller.set("alpha", self.duration, 1.0)
        elif self.a.stagger < self.b.stagger:
            # source a is over source b (lower priority)
            # we fade source a out
            self.controller.unset_all("alpha")
            self.controller.set("alpha", 0, 1.0)
            self.controller.set("alpha", self.duration, 0.0)

class AudioTransition(Transition):

    def _makeGnlObject(self):
        trans = gst.element_factory_make("volume")
        self.a_controller = gst.Controller(trans, "volume")
        self.a_controller.set_interpolation_mode("volume", gst.INTERPOLATE_LINEAR)

        self.a_operation = gst.element_factory_make("gnloperation")
        self.a_operation.add(trans)

        trans = gst.element_factory_make("volume")
        self.b_controller = gst.Controller(trans, "volume")
        self.b_controller.set_interpolation_mode("volume", gst.INTERPOLATE_LINEAR)

        self.b_operation = gst.element_factory_make("gnloperation")
        self.b_operation.add(trans)

        self.a_operation.props.media_start = 0

        self.b_operation.props.media_start = 0


    def addThyselfToComposition(self, composition):
        composition.add(self.a_operation, self.b_operation)

    def removeThyselfFromComposition(self, composition):
        composition.remove(self.a_operation)
        composition.remove(self.b_operation)
        self.a_operation.set_state(gst.STATE_NULL)
        self.b_operation.set_state(gst.STATE_NULL)

    def _updateOperationStart(self, start):
        self.a_operation.props.start = start
        self.b_operation.props.start = start

    def _updateOperationDuration(self, duration):
        self.a_operation.props.duration = duration
        self.a_operation.props.media_duration = duration
        self.b_operation.props.duration = duration
        self.b_operation.props.media_duration = duration

    def _staggerChanged(self, *unused):
        self._updateOperationPriority(self.priority)

    def _updateOperationPriority(self, priority):
        self.a_operation.props.priority = 1 + 2 * self.a.stagger + 4 * priority
        self.b_operation.props.priority = 1 + 2 * self.b.stagger + 4 * priority

    def _updateController(self):
        self.a_controller.set("volume", 0, 1.0)
        self.a_controller.set("volume", self.duration, 0.0)
        self.b_controller.set("volume", 0, 0.0)
        self.b_controller.set("volume", self.duration, 1.0)

class Track(Signallable, Loggable):
    logCategory = "track"

    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'track-object-added': ['track_object'],
        'track-object-removed': ['track_object'],
        'max-priority-changed': ['track_object'],
        'transition-added' : ['transition'],
        'transition-removed' : ['transition'],
    }

    def __init__(self, stream):
        self.stream = stream
        if type(self.stream) is VideoStream:
            self.TransitionClass = VideoTransition
        elif type(self.stream) is AudioStream:
            self.TransitionClass = AudioTransition
        self.composition = gst.element_factory_make('gnlcomposition')
        self.composition.connect('notify::start', self._compositionStartChangedCb)
        self.composition.connect('notify::duration', self._compositionDurationChangedCb)
        self.track_objects = []
        self.transitions = {}
        self._update_transitions = True
        self._max_priority = 0

        self.mixer = self._getMixerForStream(stream)
        if self.mixer:
            self.composition.add(self.mixer)
        self.default_sources = []

    def _getDefaultTrackObjectForStream(self, stream):
        if isinstance(stream, VideoStream):
            ret = self._getDefaultVideoTrackObject(stream)
        elif isinstance(stream, AudioStream):
            ret = self._getDefaultAudioTrackObject(stream)
        else:
            return None

        ret.makeBin()
        ret.gnl_object.props.priority = 2 ** 32 - 1
        self.debug("Track Object %r, priority: %r:", ret, ret.gnl_object.props.priority)
        return ret

    def _getDefaultVideoTrackObject(self, stream):
        factory = VideoTestSourceFactory(pattern='black')
        track_object = SourceTrackObject(factory, stream)

        return track_object

    def _getDefaultAudioTrackObject(self, stream):
        factory = AudioTestSourceFactory(wave='silence')
        track_object = SourceTrackObject(factory, stream)

        return track_object

    def _defaultSourceBlockedCb(self, pad, blocked):
        pass

    def _shutdownDefaultSource(self, source):
        source = list(source.elements())[0]
        for srcpad in source.src_pads():
            srcpad = source.get_pad('src')
            srcpad.set_blocked_async(True, self._defaultSourceBlockedCb)
            srcpad.push_event(gst.event_new_flush_start())

    def _sourceDebug(self, source):
        t = gst.TIME_ARGS
        return "%s [%s - %s]" % (source, t(source.props.start),
                t(source.props.start + source.props.duration))

    def _updateDefaultSourcesUnchecked(self):
        for source in self.default_sources:
            self.debug("removing default source %s", self._sourceDebug(source))
            self._shutdownDefaultSource(source)
            self.composition.remove(source)
            source.set_state(gst.STATE_NULL)
        gaps = Gap.findAllGaps(self.track_objects)

        self.default_sources = []
        for gap in gaps:
            source = self._getDefaultTrackObjectForStream(self.stream)
            gnl_object = source.gnl_object
            gnl_object.props.start = gap.start
            gnl_object.props.duration = gap.initial_duration
            self.debug("adding default source %s",
                    self._sourceDebug(source.gnl_object))
            self.composition.add(gnl_object)
            self.default_sources.append(gnl_object)

    def updateDefaultSources(self):
        if not self.composition.props.update:
            return

        self.updateDefaultSourcesReal()

    def updateDefaultSourcesReal(self):
        update = self.composition.props.update
        self.composition.props.update = True
        try:
            self._updateDefaultSourcesUnchecked()
        finally:
            self.composition.props.update = update

    def _getMixerForStream(self, stream):
        if isinstance(stream, AudioStream):
            gnl = gst.element_factory_make("gnloperation", "top-level-audio-mixer")
            m = SmartAdderBin()
            gnl.add(m)
            gnl.props.expandable = True
            gnl.props.priority = 0
            self.debug("Props priority: %s", gnl.props.priority)
            return gnl
        elif isinstance(stream, VideoStream):
            gnl = gst.element_factory_make("gnloperation", "top-level-video-mixer")
            m = SmartVideomixerBin(self)
            gnl.add(m)
            gnl.props.expandable = True
            gnl.props.priority = 0
            gnl.connect("input-priority-changed",
                        self._videoInputPriorityChangedCb, m)
            return gnl
        return None

    def _videoInputPriorityChangedCb(self, operation, pad, priority, mixer):
        self.debug("operation %s pad %s priority changed %s",
                operation, pad, priority)
        mixer.update_priority(pad, priority)

    def _getStart(self):
        return self.composition.props.start

    def getPreviousTrackObject(self, obj, priority=-1):
        prev = getPreviousObject(obj, self.track_objects, priority)
        if prev is None:
            raise TrackError("no previous track object", obj)

        return prev

    def getNextTrackObject(self, obj, priority=-1):
        next = getNextObject(obj, self.track_objects, priority)
        if next is None:
            raise TrackError("no next track object", obj)

        return next

    start = property(_getStart)

    def _getDuration(self):
        return self.composition.props.duration

    duration = property(_getDuration)

    def _getMaxPriority(self):
        return self._max_priority

    max_priority = property(_getMaxPriority)

    def _trackObjectPriorityCb(self, trackobject, priority):
        op = self._max_priority
        self._max_priority = max((obj.priority for obj in self.track_objects))
        if op != self._max_priority:
            self.emit("max-priority-changed", self._max_priority)

    def _connectToTrackObjectSignals(self, track_object):
        track_object.connect("priority-changed", self._trackObjectPriorityCb)

    def _disconnectTrackObjectSignals(self, track_object):
        track_object.disconnect_by_function(self._trackObjectPriorityCb)

    def addTrackObject(self, track_object):
        if track_object.track is not None:
            raise TrackError()

        if track_object.gnl_object in list(self.composition):
            raise TrackError()
        track_object.makeBin()

        track_object.track = self

        start_insort_right(self.track_objects, track_object)
        self.updateDefaultSources()

        try:
            self.composition.add(track_object.gnl_object)
        except gst.AddError:
            raise TrackError()

        self._connectToTrackObjectSignals(track_object)

        self._updateMaxPriority()
        self._connectToTrackObject(track_object)

        self.emit('track-object-added', track_object)
        if self._update_transitions:
            self.updateTransitions()

    def removeTrackObject(self, track_object):
        if track_object.track is None:
            raise TrackError()

        try:
            self.composition.remove(track_object.gnl_object)
            track_object.gnl_object.set_state(gst.STATE_NULL)
        except gst.RemoveError:
            raise TrackError()

        self._disconnectFromTrackObject(track_object)
        track_object.releaseBin()

        self.track_objects.remove(track_object)
        track_object.track = None

        self._disconnectTrackObjectSignals(track_object)

        self._updateMaxPriority()
        self.updateDefaultSources()

        self.emit('track-object-removed', track_object)
        if self._update_transitions:
            self.updateTransitions()

    def removeAllTrackObjects(self):
        for track_object in list(self.track_objects):
            self.removeTrackObject(track_object)

    def _updateMaxPriority(self):
        priorities = [track_object.priority for track_object in
            self.track_objects]
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

    def _trackObjectStartChangedCb(self, track_object, start):
        self.track_objects.remove(track_object)
        start_insort_right(self.track_objects, track_object)

    def _trackObjectDurationChangedCb(self, track_object, duration):
        pass

    def _connectToTrackObject(self, track_object):
        track_object.connect('priority-changed',
                self._trackObjectPriorityChangedCb)
        track_object.connect('start-changed',
                self._trackObjectStartChangedCb)
        track_object.connect('duration-changed',
                self._trackObjectDurationChangedCb)

    def _disconnectFromTrackObject(self, track_object):
        track_object.disconnect_by_function(self._trackObjectPriorityChangedCb)
        track_object.disconnect_by_function(self._trackObjectStartChangedCb)
        track_object.disconnect_by_function(self._trackObjectDurationChangedCb)

    def enableUpdates(self):
        self.composition.props.update = True
        self.updateDefaultSources()
        self._update_transitions = True
        self.updateTransitions()

    def disableUpdates(self):
        self.composition.props.update = False
        self._update_transitions = False

    def addTransition(self, transition):
        a, b = transition.a, transition.b
        if not ((a in self.track_objects) and
                (b in self.track_objects)):
            raise TrackError("One or both track objects not in track")
        if (a, b) in self.transitions:
            raise TrackError(
                "A transition is already defined for these objects")
        transition.addThyselfToComposition(self.composition)
        self.transitions[a, b] = transition
        self.emit("transition-added", transition)

    def removeTransition(self, transition):
        a, b = transition.a, transition.b
        transition.removeThyselfFromComposition(self.composition)
        del self.transitions[a, b]
        self.emit("transition-removed", transition)

    def getTrackObjectsGroupedByLayer(self):
        layers = [[] for x in xrange(0, self.max_priority + 1)]
        for track_object in self.track_objects:
            if not isinstance(track_object, TrackEffect):
                layers[int(track_object.priority)].append(track_object)
        return layers

    def getValidTransitionSlots(self, objs):
        prev = None
        safe = 0
        duration = 0
        slots = []
        valid = True

        def pop():
            if len(slots):
                slots.pop(-1)
        for obj in objs:
            end = obj.start + obj.duration
            if obj.start >= duration:
                safe = obj.start
                duration = end
                prev = obj
            elif end >= duration and obj.start >= safe:
                slots.append((prev, obj))
                safe = duration
                duration = end
                prev = obj
            elif end >= duration and obj.start < safe:
                pop()
                valid = False
                safe = duration
                duration = end
                prev = obj
            elif end < duration and obj.start >= safe:
                safe = end
                valid = False
            elif end < duration and obj.start < safe:
                pop()
                valid = False
                safe = end

        return slots, valid

    valid_arrangement = True

    def updateTransitions(self):
        # create all new transitions
        valid_slots = set()
        all_valid = True
        for layer in self.getTrackObjectsGroupedByLayer():
            pos = 0
            prev = None
            slots, is_valid = self.getValidTransitionSlots(layer)
            all_valid &= is_valid
            for slot in slots:
                a, b = slot
                if a == prev:
                    b.updatePosition(pos)
                    pos += 1
                else:
                    a.updatePosition(pos)
                    b.updatePosition(pos + 1)
                    pos += 2
                prev = b
                valid_slots.add(slot)
                if not slot in self.transitions:
                    tr = self.TransitionClass(a, b)
                    self.addTransition(tr)
        current_slots = set(self.transitions.iterkeys())
        for slot in current_slots - valid_slots:
            self.removeTransition(self.transitions[slot])
        self.valid_arrangement = all_valid
