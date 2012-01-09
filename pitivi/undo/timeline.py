# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/timeline_undo.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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

import gobject

from pitivi.utils.signal import Signallable
from pitivi.undo.undo import PropertyChangeTracker
from pitivi.undo.undo import UndoableAction

from pitivi.ui.effectsconfiguration import PROPS_TO_IGNORE
from pitivi.undo.effects import EffectGstElementPropertyChangeTracker


class TimelineObjectPropertyChangeTracker(PropertyChangeTracker):
    # no out-point
    property_names = ["start", "duration", "in-point",
            "media-duration", "priority", "selected"]

    _disabled = False

    def connectToObject(self, obj):
        PropertyChangeTracker.connectToObject(self, obj)
        self.timeline = obj.timeline
        self.timeline.connect("disable-updates", self._timelineDisableUpdatesCb)

    def disconnectFromObject(self, obj):
        return
        self.timeline.disconnect_by_func(self._timelineDisableUpdatesCb)
        PropertyChangeTracker.disconnectFromObject(self, obj)

    def _timelineDisableUpdatesCb(self, timeline, disabled):
        if self._disabled and not disabled:
            self._disabled = disabled
            properties = self._takeCurrentSnapshot(self.obj)
            for property_name, property_value in properties.iteritems():
                old_value = self.properties[property_name]
                if old_value != property_value:
                    self._propertyChangedCb(self.obj, property_value, property_name)
        else:
            self._disabled = disabled

    def _propertyChangedCb(self, timeline_object, value, property_name):
        if not self._disabled:
            PropertyChangeTracker._propertyChangedCb(self,
                    timeline_object, value, property_name)


class KeyframeChangeTracker(Signallable):
    __signals__ = {
        "keyframe-moved": ["keyframe"]
    }

    def __init__(self):
        self.keyframes = None
        self.obj = None

    def connectToObject(self, obj):
        self.obj = obj
        self.keyframes = self._takeCurrentSnapshot(obj)
        obj.connect("keyframe-added", self._keyframeAddedCb)
        obj.connect("keyframe-removed", self._keyframeRemovedCb)
        obj.connect("keyframe-moved", self._keyframeMovedCb)

    def _takeCurrentSnapshot(self, obj):
        keyframes = {}
        for keyframe in self.obj.getKeyframes():
            keyframes[keyframe] = self._getKeyframeSnapshot(keyframe)

        return keyframes

    def disconnectFromObject(self, obj):
        self.obj = None
        obj.disconnect_by_func(self._keyframeMovedCb)

    def _keyframeAddedCb(self, interpolator, keyframe):
        self.keyframes[keyframe] = self._getKeyframeSnapshot(keyframe)

    def _keyframeRemovedCb(self, interpolator, keyframe, old_value=None):
        pass

    def _keyframeMovedCb(self, interpolator, keyframe, old_value=None):
        old_snapshot = self.keyframes[keyframe]
        new_snapshot = self._getKeyframeSnapshot(keyframe)
        self.keyframes[keyframe] = new_snapshot

        self.emit("keyframe-moved", interpolator,
                keyframe, old_snapshot, new_snapshot)

    def _getKeyframeSnapshot(self, keyframe):
        return (keyframe.mode, keyframe.time, keyframe.value)


class TimelineObjectPropertyChanged(UndoableAction):
    def __init__(self, timeline_object, property_name, old_value, new_value):
        self.timeline_object = timeline_object
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def do(self):
        setattr(self.timeline_object,
                self.property_name.replace("-", "_"), self.new_value)
        self._done()

    def undo(self):
        setattr(self.timeline_object,
                self.property_name.replace("-", "_"), self.old_value)
        self._undone()


class TimelineObjectAdded(UndoableAction):
    def __init__(self, timeline, timeline_object):
        self.timeline = timeline
        self.timeline_object = timeline_object
        self.tracks = dict((track_object, track_object.get_track())
                for track_object in timeline_object.get_track_objects())

    def do(self):
        for track_object, track in self.tracks.iteritems():
            track.addTrackObject(track_object)

        self.timeline.addTimelineObject(self.timeline_object)
        self._done()

    def undo(self):
        self.timeline.removeTimelineObject(self.timeline_object, deep=True)
        self._undone()


class TimelineObjectRemoved(UndoableAction):
    def __init__(self, timeline, timeline_object):
        self.timeline = timeline
        self.timeline_object = timeline_object
        self.tracks = dict((track_object, track_object.get_track())
                for track_object in timeline_object.get_track_objects())

    def do(self):
        self.timeline.removeTimelineObject(self.timeline_object, deep=True)
        self._done()

    def undo(self):
        for track_object, track in self.tracks.iteritems():
            track.addTrackObject(track_object)

        self.timeline.addTimelineObject(self.timeline_object)

        self._undone()


class TrackEffectAdded(UndoableAction):
    # Note: We have a bug if we just remove the TrackEffect from the timeline
    # and keep it saved here and then readd it to corresponding timeline (it
    # freezes everything). So what we are doing is  to free the TrackEffect,
    # keep its settings here when undoing, and instanciate a new one when
    # doing again. We have to keep all EffectPropertyChanged object that refers
    # to the TrackEffect when undoing so we reset theirs gst_element when
    # doing it again. The way of doing it is the same with TrackEffectRemoved
    def __init__(self, timeline_object, track_object, properties_watcher):
        self.timeline_object = timeline_object
        self.track_object = track_object
        self.factory = track_object.factory
        self.effect_props = []
        self.gnl_obj_props = []
        self._properties_watcher = properties_watcher
        self._props_changed = []

    def do(self):
        timeline = self.timeline_object.timeline
        tl_obj_track_obj = timeline.addEffectFactoryOnObject(self.factory,
                                            timeline_objects=[self.timeline_object])

        self.track_object = tl_obj_track_obj[0][1]
        element = self.track_object.getElement()
        for prop_name, prop_value in self.effect_props:
            element.set_property(prop_name, prop_value)
        for prop_name, prop_value in self.gnl_obj_props:
            self.track_object.gnl_object.set_property(prop_name, prop_value)
        for prop_changed in self._props_changed:
            prop_changed.gst_element = self.track_object.getElement()
        self._props_changed = []

        self._done()

    def undo(self):
        element = self.track_object.getElement()
        props = gobject.list_properties(element)
        self.effect_props = [(prop.name, element.get_property(prop.name))
                              for prop in props
                              if prop.flags & gobject.PARAM_WRITABLE
                              and prop.name not in PROPS_TO_IGNORE]
        gnl_props = gobject.list_properties(self.track_object.gnl_object)
        gnl_obj = self.track_object.gnl_object
        self.gnl_obj_props = [(prop.name, gnl_obj.get_property(prop.name))
                              for prop in gnl_props
                              if prop.flags & gobject.PARAM_WRITABLE]

        self.timeline_object.removeTrackObject(self.track_object)
        self.track_object.track.removeTrackObject(self.track_object)
        self._props_changed =\
            self._properties_watcher.getPropChangedFromTrackObj(self.track_object)
        del self.track_object
        self.track_object = None

        self._undone()


class TrackEffectRemoved(UndoableAction):
    def __init__(self, timeline_object, track_object, properties_watcher):
        self.track_object = track_object
        self.timeline_object = timeline_object
        self.factory = track_object.factory
        self.effect_props = []
        self.gnl_obj_props = []
        self._properties_watcher = properties_watcher
        self._props_changed = []

    def do(self):
        element = self.track_object.getElement()
        props = gobject.list_properties(element)
        self.effect_props = [(prop.name, element.get_property(prop.name))
                              for prop in props
                              if prop.flags & gobject.PARAM_WRITABLE
                              and prop.name not in PROPS_TO_IGNORE]

        gnl_props = gobject.list_properties(self.track_object.gnl_object)
        gnl_obj = self.track_object.gnl_object
        self.gnl_obj_props = [(prop.name, gnl_obj.get_property(prop.name))
                              for prop in gnl_props
                              if prop.flags & gobject.PARAM_WRITABLE]

        self.timeline_object.removeTrackObject(self.track_object)
        self.track_object.track.removeTrackObject(self.track_object)
        self._props_changed =\
            self._properties_watcher.getPropChangedFromTrackObj(self.track_object)
        del self.track_object
        self.track_object = None

        self._done()

    def undo(self):
        timeline = self.timeline_object.timeline
        tl_obj_track_obj = timeline.addEffectFactoryOnObject(self.factory,
                                            timeline_objects=[self.timeline_object])

        self.track_object = tl_obj_track_obj[0][1]
        element = self.track_object.getElement()
        for prop_name, prop_value in self.effect_props:
            element.set_property(prop_name, prop_value)
        for prop_name, prop_value in self.gnl_obj_props:
            self.track_object.gnl_object.set_property(prop_name, prop_value)
        for prop_changed in self._props_changed:
            prop_changed.gst_element = self.track_object.getElement()
        self._props_changed = []

        self._undone()


class InterpolatorKeyframeAdded(UndoableAction):
    def __init__(self, track_object, keyframe):
        self.track_object = track_object
        self.keyframe = keyframe

    def do(self):
        self.track_object.newKeyframe(self.keyframe)
        self._done()

    def undo(self):
        self.track_object.removeKeyframe(self.keyframe)
        self._undone()


class InterpolatorKeyframeRemoved(UndoableAction):
    def __init__(self, track_object, keyframe):
        self.track_object = track_object
        self.keyframe = keyframe

    def do(self):
        self.track_object.removeKeyframe(self.keyframe)
        self._undone()

    def undo(self):
        self.track_object.newKeyframe(self.keyframe.time,
                self.keyframe.value, self.keyframe.mode)
        self._done()


class InterpolatorKeyframeChanged(UndoableAction):
    def __init__(self, track_object, keyframe, old_snapshot, new_snapshot):
        self.track_object = track_object
        self.keyframe = keyframe
        self.old_snapshot = old_snapshot
        self.new_snapshot = new_snapshot

    def do(self):
        self._setSnapshot(self.new_snapshot)
        self._done()

    def undo(self):
        self._setSnapshot(self.old_snapshot)
        self._undone()

    def _setSnapshot(self, snapshot):
        mode, time, value = snapshot
        self.keyframe.setMode(mode)
        self.keyframe.setTime(time)
        self.keyframe.setValue(value)


class ActivePropertyChanged(UndoableAction):
    def __init__(self, effect_action, active):
        self.effect_action = effect_action
        self.active = not active

    def do(self):
        self.effect_action.track_object.active = self.active
        self.active = not self.active
        self._done()

    def undo(self):
        self.effect_action.track_object.active = self.active
        self.active = not self.active
        self._undone()


class TimelineLogObserver(object):
    timelinePropertyChangedAction = TimelineObjectPropertyChanged
    timelineObjectAddedAction = TimelineObjectAdded
    timelineObjectRemovedAction = TimelineObjectRemoved
    trackEffectAddAction = TrackEffectAdded
    trackEffectRemovedAction = TrackEffectRemoved
    interpolatorKeyframeAddedAction = InterpolatorKeyframeAdded
    interpolatorKeyframeRemovedAction = InterpolatorKeyframeRemoved
    interpolatorKeyframeChangedAction = InterpolatorKeyframeChanged
    activePropertyChangedAction = ActivePropertyChanged

    def __init__(self, log):
        self.log = log
        self.timeline_object_property_trackers = {}
        self.interpolator_keyframe_trackers = {}
        self.effect_properties_tracker = EffectGstElementPropertyChangeTracker(log)
        self._pipeline = None

    def setPipeline(self, pipeline):
        self._pipeline = pipeline
        self.effect_properties_tracker.pipeline = pipeline

    def getPipeline(self):
        return self._pipeline

    pipeline = property(getPipeline, setPipeline)

    def startObserving(self, timeline):
        self._connectToTimeline(timeline)
        for layer in timeline.get_layers():
            for timeline_object in layer.get_objects():
                self._connectToTimelineObject(timeline_object)
                for track_object in timeline_object.track_objects:
                    self._connectToTrackObject(track_object)

    def stopObserving(self, timeline):
        self._disconnectFromTimeline(timeline)
        for timeline_object in timeline.timeline_objects:
            self._disconnectFromTimelineObject(timeline_object)
            for track_object in timeline_object.track_objects:
                self._disconnectFromTrackObject(track_object)

    def _connectToTimeline(self, timeline):
        for layer in timeline.get_layers():
            layer.connect("object-added", self._timelineObjectAddedCb)
            layer.connect("object-removed", self._timelineObjectRemovedCb)

    def _disconnectFromTimeline(self, timeline):
        timeline.disconnect_by_func(self._timelineObjectAddedCb)
        timeline.disconnect_by_func(self._timelineObjectRemovedCb)

    def _connectToTimelineObject(self, timeline_object):
        tracker = TimelineObjectPropertyChangeTracker()
        tracker.connectToObject(timeline_object)
        for property_name in tracker.property_names:
            tracker.connect("notify::" + property_name,
                    self._timelineObjectPropertyChangedCb, property_name)
        self.timeline_object_property_trackers[timeline_object] = tracker

        timeline_object.connect("track-object-added", self._timelineObjectTrackObjectAddedCb)
        #timeline_object.connect("track-object-removed", self._timelineObjectTrackObjectRemovedCb)
        for obj in timeline_object.get_track_objects():
            self._connectToTrackObject(obj)

    def _disconnectFromTimelineObject(self, timeline_object):
        tracker = self.timeline_object_property_trackers.pop(timeline_object)
        tracker.disconnectFromObject(timeline_object)
        tracker.disconnect_by_func(self._timelineObjectPropertyChangedCb)

    def _connectToTrackObject(self, track_object):
        #for prop, interpolator in track_object.getInterpolators().itervalues():
            #self._connectToInterpolator(interpolator)
        if isinstance(track_object, TrackEffect):
            self.effect_properties_tracker.addEffectElement(track_object.getElement())

    def _disconnectFromTrackObject(self, track_object):
        for prop, interpolator in track_object.getInterpolators().itervalues():
            self._disconnectFromInterpolator(interpolator)

    def _connectToInterpolator(self, interpolator):
        interpolator.connect("keyframe-added", self._interpolatorKeyframeAddedCb)
        interpolator.connect("keyframe-removed",
                self._interpolatorKeyframeRemovedCb)

        tracker = KeyframeChangeTracker()
        tracker.connectToObject(interpolator)
        tracker.connect("keyframe-moved", self._interpolatorKeyframeMovedCb)
        self.interpolator_keyframe_trackers[interpolator] = tracker

    def _disconnectFromInterpolator(self, interpolator):
        tracker = self.interpolator_keyframe_trackers.pop(interpolator)
        tracker.disconnectFromObject(interpolator)
        tracker.disconnect_by_func(self._interpolatorKeyframeMovedCb)

    def _timelineObjectAddedCb(self, timeline, timeline_object):
        self._connectToTimelineObject(timeline_object)
        action = self.timelineObjectAddedAction(timeline, timeline_object)
        self.log.push(action)

    def _timelineObjectRemovedCb(self, timeline, timeline_object):
        self._disconnectFromTimelineObject(timeline_object)
        action = self.timelineObjectRemovedAction(timeline, timeline_object)
        self.log.push(action)

    def _timelineObjectPropertyChangedCb(self, tracker, timeline_object,
            old_value, new_value, property_name):
        action = self.timelinePropertyChangedAction(timeline_object,
                property_name, old_value, new_value)
        self.log.push(action)

    def _timelineObjectTrackObjectAddedCb(self, timeline_object, track_object):
        if isinstance(track_object, TrackEffect):
            action = self.trackEffectAddAction(timeline_object, track_object,
                                               self.effect_properties_tracker)
            #We use the action instead of the track object
            #because the track_object changes when redoing
            track_object.connect("active-changed",
                                 self._trackObjectActiveChangedCb, action)
            self.log.push(action)
            element = track_object.getElement()
            if element:
                self.effect_properties_tracker.addEffectElement(element)
        else:
            self._connectToTrackObject(track_object)

    def _timelineObjectTrackObjectRemovedCb(self, timeline_object,
                                            track_object):
        if isinstance(track_object, TrackEffect):
            action = self.trackEffectRemovedAction(timeline_object,
                                                track_object,
                                                self.effect_properties_tracker)
            self.log.push(action)
        else:
            self._disconnectFromTrackObject(track_object)

    def _interpolatorKeyframeAddedCb(self, track_object, keyframe):
        action = self.interpolatorKeyframeAddedAction(track_object, keyframe)
        self.log.push(action)

    def _interpolatorKeyframeRemovedCb(self, track_object, keyframe,
            old_value=None):
        action = self.interpolatorKeyframeRemovedAction(track_object, keyframe)
        self.log.push(action)

    def _trackObjectActiveChangedCb(self, track_object, active, add_effect_action):
        action = self.activePropertyChangedAction(add_effect_action, active)
        self.log.push(action)

    def _interpolatorKeyframeMovedCb(self, tracker, track_object,
            keyframe, old_snapshot, new_snapshot):
        action = self.interpolatorKeyframeChangedAction(track_object,
                keyframe, old_snapshot, new_snapshot)
        self.log.push(action)
