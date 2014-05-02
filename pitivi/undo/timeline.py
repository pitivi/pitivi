# Pitivi video editor
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

from gi.repository import GES
from gi.repository import GObject

from pitivi.undo.undo import PropertyChangeTracker, UndoableAction
from pitivi.undo.effect import EffectAdded, EffectRemoved
from pitivi.undo.effect import EffectGstElementPropertyChangeTracker


class ClipPropertyChangeTracker(PropertyChangeTracker):
    # no out-point
    property_names = ["start", "duration", "in-point", "priority"]

    def __init__(self):
        PropertyChangeTracker.__init__(self)

    def connectToObject(self, obj):
        PropertyChangeTracker.connectToObject(self, obj)
        self.timeline = obj.timeline
        self.timeline.connect("commited", self._timelineCommitedCb)

    def disconnectFromObject(self, obj):
        self.timeline.disconnect_by_func(self._timelineCommitedCb)
        PropertyChangeTracker.disconnectFromObject(self, obj)

    def _timelineCommitedCb(self, timeline):
        properties = self._takeCurrentSnapshot(self.obj)
        for property_name, property_value in properties.items():
            old_value = self.properties[property_name]
            if old_value != property_value:
                self._propertyChangedCb(self.obj, property_value, property_name)


class KeyframeChangeTracker(GObject.Object):

    __gsignals__ = {
        "keyframe-moved": (GObject.SIGNAL_RUN_LAST, None, (object, object, object, object)),
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
        UndoableAction.__init__(self)
        self.clip = clip
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def do(self):
        self.clip.set_property(self.property_name.replace("-", "_"), self.new_value)
        self._done()

    def undo(self):
        self.clip.set_property(self.property_name.replace("-", "_"), self.old_value)
        self._undone()


class ClipAdded(UndoableAction):

    def __init__(self, layer, clip):
        UndoableAction.__init__(self)
        self.layer = layer
        self.clip = clip

    def do(self):
        self.layer.add_clip(self.clip)
        self.layer.get_timeline().commit()
        self._done()

    def undo(self):
        self.layer.remove_clip(self.clip)
        self._undone()


class ClipRemoved(UndoableAction):

    def __init__(self, layer, clip):
        UndoableAction.__init__(self)
        self.layer = layer
        self.clip = clip

    def do(self):
        self.layer.remove_clip(self.clip)
        self._done()

    def undo(self):
        self.layer.add_clip(self.clip)
        self.layer.get_timeline().commit()
        self._undone()


class LayerAdded(UndoableAction):
    def __init__(self, timeline, layer):
        self.timeline = timeline
        self.layer = layer

    def do(self):
        self.timeline.add_layer(self.layer)

    def undo(self):
        self.timeline.remove_layer(self.layer)


class LayerRemoved(UndoableAction):
    def __init__(self, timeline, layer):
        self.timeline = timeline
        self.layer = layer

    def do(self):
        self.timeline.remove_layer(self.layer)

    def undo(self):
        self.timeline.add_layer(self.layer)


class InterpolatorKeyframeAdded(UndoableAction):

    def __init__(self, track_element, keyframe):
        UndoableAction.__init__(self)
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
        UndoableAction.__init__(self)
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
        UndoableAction.__init__(self)
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
        UndoableAction.__init__(self)
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

    def stopObserving(self, timeline):
        self._disconnectFromTimeline(timeline)
        for layer in timeline.layers:
            for clip in layer.get_clips():
                self._disconnectFromClip(clip)
                for track_element in clip.get_children(True):
                    self._disconnectFromTrackElement(track_element)

    def _connectToTimeline(self, timeline):
        for layer in timeline.get_layers():
            layer.connect("clip-added", self._clipAddedCb)
            layer.connect("clip-removed", self._clipRemovedCb)

        timeline.connect("layer-added", self._layerAddedCb)
        timeline.connect("layer-removed", self._layerRemovedCb)

    def _disconnectFromTimeline(self, timeline):
        for layer in timeline.get_layers():
            layer.disconnect_by_func(self._clipAddedCb)
            layer.disconnect_by_func(self._clipRemovedCb)

        timeline.disconnect_by_func(self._layerAddedCb)
        timeline.disconnect_by_func(self._layerRemovedCb)

    def _connectToClip(self, clip):
        tracker = ClipPropertyChangeTracker()
        tracker.connectToObject(clip)
        for property_name in tracker.property_names:
            attr_name = "last-%s" % property_name
            last_value = clip.get_property(property_name)
            setattr(tracker, attr_name, last_value)
        tracker.connect("monitored-property-changed", self._clipPropertyChangedCb)
        self.clip_property_trackers[clip] = tracker

        clip.connect("child-added", self._clipTrackElementAddedCb)
        clip.connect("child-removed", self._clipTrackElementRemovedCb)
        for track_element in clip.get_children(True):
            self._connectToTrackElement(track_element)

    def _disconnectFromClip(self, clip):
        tracker = self.clip_property_trackers.pop(clip)
        tracker.disconnectFromObject(clip)
        tracker.disconnect_by_func(self._clipPropertyChangedCb)

    def _connectToTrackElement(self, track_element):
        # FIXME: keyframes are disabled:
        # for prop, interpolator in track_element.getInterpolators().itervalues():
            # self._connectToInterpolator(interpolator)
        if isinstance(track_element, GES.BaseEffect):
            self.effect_properties_tracker.addEffectElement(track_element)

    def _disconnectFromTrackElement(self, track_element):
        pass
        # for prop, interpolator in track_element.getInterpolators().values():
        #    self._disconnectFromInterpolator(interpolator)

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

    def _clipAddedCb(self, layer, clip):
        self._connectToClip(clip)
        action = ClipAdded(layer, clip)
        self.log.push(action)

    def _clipRemovedCb(self, layer, clip):
        self._disconnectFromClip(clip)
        action = ClipRemoved(layer, clip)
        self.log.push(action)

    def _clipPropertyChangedCb(self, tracker, clip,
            property_name, old_value, new_value):
        attr_name = "last-%s" % property_name
        new_value = clip.get_property(property_name)
        old_value = getattr(tracker, attr_name)
        action = self.timelinePropertyChangedAction(clip, property_name,
                 old_value, new_value)
        setattr(tracker, attr_name, new_value)
        self.log.push(action)

    def _clipTrackElementAddedCb(self, clip, track_element):
        self._connectToTrackElement(track_element)
        if isinstance(track_element, GES.BaseEffect):
            action = EffectAdded(clip, track_element,
                                 self.effect_properties_tracker)
            self.log.push(action)

    def _clipTrackElementRemovedCb(self, clip, track_element):
        self._disconnectFromTrackElement(track_element)
        if isinstance(track_element, GES.BaseEffect):
            action = EffectRemoved(clip,
                                   track_element,
                                   self.effect_properties_tracker)
            self.log.push(action)

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

    def _layerAddedCb(self, timeline, layer):
        layer.connect("clip-added", self._clipAddedCb)
        layer.connect("clip-removed", self._clipRemovedCb)
        action = LayerAdded(timeline, layer)
        self.log.push(action)

    def _layerRemovedCb(self, timeline, layer):
        layer.disconnect_by_func(self._clipAddedCb)
        layer.disconnect_by_func(self._clipRemovedCb)
        action = LayerRemoved(timeline, layer)
        self.log.push(action)
