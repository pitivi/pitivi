# PiTiVi , Non-linear video editor
#
#       pitivi/undo/timeline.py
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

from pitivi.utils.signal import Signallable
from pitivi.undo.undo import PropertyChangeTracker, UndoableAction
from pitivi.undo.effect import EffectAdded, EffectRemoved
from pitivi.undo.effects import EffectGstElementPropertyChangeTracker


class ClipPropertyChangeTracker(PropertyChangeTracker):
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

    def _propertyChangedCb(self, clip, value, property_name):
        if not self._disabled:
            PropertyChangeTracker._propertyChangedCb(self, clip, value, property_name)


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
        pass  # FIXME: this has not been implemented

    def _keyframeMovedCb(self, interpolator, keyframe, old_value=None):
        old_snapshot = self.keyframes[keyframe]
        new_snapshot = self._getKeyframeSnapshot(keyframe)
        self.keyframes[keyframe] = new_snapshot
        self.emit("keyframe-moved", interpolator, keyframe, old_snapshot, new_snapshot)

    def _getKeyframeSnapshot(self, keyframe):
        return (keyframe.mode, keyframe.time, keyframe.value)


class ClipPropertyChanged(UndoableAction):
    def __init__(self, clip, property_name, old_value, new_value):
        self.clip = clip
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def do(self):
        setattr(self.clip, self.property_name.replace("-", "_"), self.new_value)
        self._done()

    def undo(self):
        setattr(self.clip, self.property_name.replace("-", "_"), self.old_value)
        self._undone()


class ClipAdded(UndoableAction):
    def __init__(self, timeline, clip):
        self.timeline = timeline
        self.clip = clip
        self.tracks = dict((track_element, track_element.get_track())
                for track_element in clip.get_track_elements())

    def do(self):
        for track_element, track in self.tracks.iteritems():
            track.addTrackElement(track_element)

        self.timeline.addClip(self.clip)
        self._done()

    def undo(self):
        self.timeline.removeClip(self.clip, deep=True)
        self._undone()


class ClipRemoved(UndoableAction):
    def __init__(self, timeline, clip):
        self.timeline = timeline
        self.clip = clip
        self.tracks = dict((track_element, track_element.get_track())
                for track_element in clip.get_track_elements())

    def do(self):
        self.timeline.removeClip(self.clip, deep=True)
        self._done()

    def undo(self):
        for track_element, track in self.tracks.iteritems():
            track.addTrackElement(track_element)

        self.timeline.addClip(self.clip)
        self._undone()


class InterpolatorKeyframeAdded(UndoableAction):
    def __init__(self, track_element, keyframe):
        self.track_element = track_element
        self.keyframe = keyframe

    def do(self):
        self.track_element.newKeyframe(self.keyframe)
        self._done()

    def undo(self):
        self.track_element.removeKeyframe(self.keyframe)
        self._undone()


class InterpolatorKeyframeRemoved(UndoableAction):
    def __init__(self, track_element, keyframe):
        self.track_element = track_element
        self.keyframe = keyframe

    def do(self):
        self.track_element.removeKeyframe(self.keyframe)
        self._undone()

    def undo(self):
        self.track_element.newKeyframe(self.keyframe.time,
                self.keyframe.value, self.keyframe.mode)
        self._done()


class InterpolatorKeyframeChanged(UndoableAction):
    def __init__(self, track_element, keyframe, old_snapshot, new_snapshot):
        self.track_element = track_element
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
        self.effect_action.track_element.active = self.active
        self.active = not self.active
        self._done()

    def undo(self):
        self.effect_action.track_element.active = self.active
        self.active = not self.active
        self._undone()


class TimelineLogObserver(object):
    timelinePropertyChangedAction = ClipPropertyChanged
    ClipAddedAction = ClipAdded
    ClipRemovedAction = ClipRemoved
    effectAddAction = EffectAdded
    effectRemovedAction = EffectRemoved
    interpolatorKeyframeAddedAction = InterpolatorKeyframeAdded
    interpolatorKeyframeRemovedAction = InterpolatorKeyframeRemoved
    interpolatorKeyframeChangedAction = InterpolatorKeyframeChanged
    activePropertyChangedAction = ActivePropertyChanged

    def __init__(self, log):
        self.log = log
        self.clip_property_trackers = {}
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
            for clip in layer.get_clips():
                self._connectToClip(clip)
                for track_element in clip.track_elements:
                    self._connectToTrackElement(track_element)

    def stopObserving(self, timeline):
        self._disconnectFromTimeline(timeline)
        for clip in timeline.clips:
            self._disconnectFromClip(clip)
            for track_element in clip.track_elements:
                self._disconnectFromTrackElement(track_element)

    def _connectToTimeline(self, timeline):
        for layer in timeline.get_layers():
            layer.connect("clip-added", self._clipAddedCb)
            layer.connect("clip-removed", self._clipRemovedCb)

    def _disconnectFromTimeline(self, timeline):
        timeline.disconnect_by_func(self._clipAddedCb)
        timeline.disconnect_by_func(self._clipRemovedCb)

    def _connectToClip(self, clip):
        tracker = ClipPropertyChangeTracker()
        tracker.connectToObject(clip)
        for property_name in tracker.property_names:
            tracker.connect("notify::" + property_name,
                    self._clipPropertyChangedCb, property_name)
        self.clip_property_trackers[clip] = tracker

        clip.connect("track-element-added", self._clipTrackElementAddedCb)
        clip.connect("track-element-removed", self._clipTrackElementRemovedCb)
        for element in clip.get_track_elements():
            self._connectToTrackElement(element)

    def _disconnectFromClip(self, clip):
        tracker = self.clip_property_trackers.pop(clip)
        tracker.disconnectFromObject(clip)
        tracker.disconnect_by_func(self._clipPropertyChangedCb)

    def _connectToTrackElement(self, track_element):
        # FIXME: keyframes are disabled:
        #for prop, interpolator in track_element.getInterpolators().itervalues():
            #self._connectToInterpolator(interpolator)
        if isinstance(track_element, GES.BaseEffect):
            self.effect_properties_tracker.addEffectElement(track_element.getElement())

    def _disconnectFromTrackElement(self, track_element):
        for prop, interpolator in track_element.getInterpolators().itervalues():
            self._disconnectFromInterpolator(interpolator)

    def _connectToInterpolator(self, interpolator):
        interpolator.connect("keyframe-added", self._interpolatorKeyframeAddedCb)
        interpolator.connect("keyframe-removed", self._interpolatorKeyframeRemovedCb)
        tracker = KeyframeChangeTracker()
        tracker.connectToObject(interpolator)
        tracker.connect("keyframe-moved", self._interpolatorKeyframeMovedCb)
        self.interpolator_keyframe_trackers[interpolator] = tracker

    def _disconnectFromInterpolator(self, interpolator):
        tracker = self.interpolator_keyframe_trackers.pop(interpolator)
        tracker.disconnectFromObject(interpolator)
        tracker.disconnect_by_func(self._interpolatorKeyframeMovedCb)

    def _clipAddedCb(self, timeline, clip):
        self._connectToClip(clip)
        action = self.ClipAddedAction(timeline, clip)
        self.log.push(action)

    def _clipRemovedCb(self, timeline, clip):
        self._disconnectFromClip(clip)
        action = self.ClipRemovedAction(timeline, clip)
        self.log.push(action)

    def _clipPropertyChangedCb(self, tracker, clip,
            old_value, new_value, property_name):
        action = self.timelinePropertyChangedAction(clip,
                property_name, old_value, new_value)
        self.log.push(action)

    def _clipTrackElementAddedCb(self, clip, track_element):
        if isinstance(track_element, GES.BaseEffect):
            action = self.effectAddAction(clip, track_element,
                                          self.effect_properties_tracker)
            # We use the action instead of the track element
            # because the track_element changes when redoing
            track_element.connect("active-changed",
                                 self._trackElementActiveChangedCb, action)
            self.log.push(action)
            element = track_element.getElement()
            if element:
                self.effect_properties_tracker.addEffectElement(element)
        else:
            self._connectToTrackElement(track_element)

    def _clipTrackElementRemovedCb(self, clip, track_element):
        if isinstance(track_element, GES.BaseEffect):
            action = self.effectRemovedAction(clip,
                                              track_element,
                                              self.effect_properties_tracker)
            self.log.push(action)
        else:
            self._disconnectFromTrackElement(track_element)

    def _interpolatorKeyframeAddedCb(self, track_element, keyframe):
        action = self.interpolatorKeyframeAddedAction(track_element, keyframe)
        self.log.push(action)

    def _interpolatorKeyframeRemovedCb(self, track_element, keyframe, old_value=None):
        action = self.interpolatorKeyframeRemovedAction(track_element, keyframe)
        self.log.push(action)

    def _trackElementActiveChangedCb(self, track_element, active, add_effect_action):
        """
        This happens when an effect is (de)activated on a clip in the timeline.
        """
        action = self.activePropertyChangedAction(add_effect_action, active)
        self.log.push(action)

    def _interpolatorKeyframeMovedCb(self, tracker, track_element,
            keyframe, old_snapshot, new_snapshot):
        action = self.interpolatorKeyframeChangedAction(track_element,
                keyframe, old_snapshot, new_snapshot)
        self.log.push(action)
