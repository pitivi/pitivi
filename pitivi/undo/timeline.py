# -*- coding: utf-8 -*-
# Pitivi video editor
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
from gi.repository import Gst

from pitivi.effects import PROPS_TO_IGNORE
from pitivi.undo.undo import FinalizingAction
from pitivi.undo.undo import GObjectObserver
from pitivi.undo.undo import UndoableAction
from pitivi.utils.loggable import Loggable


def child_property_name(pspec):
    return "%s::%s" % (pspec.owner_type.name, pspec.name)


class CommitTimelineFinalizingAction(FinalizingAction):
    def __init__(self, pipeline):
        self.__pipeline = pipeline

    def do(self):
        self.__pipeline.commit_timeline()


class TrackElementPropertyChanged(UndoableAction):

    def __init__(self, track_element, property_name, old_value, new_value):
        UndoableAction.__init__(self)
        self.track_element = track_element
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def do(self):
        self.track_element.set_child_property(
            self.property_name, self.new_value)

    def undo(self):
        self.track_element.set_child_property(
            self.property_name, self.old_value)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("set-child-property")
        st['element-name'] = self.track_element.get_name()
        st['property'] = self.property_name
        value = self.new_value
        if isinstance(self.new_value, GObject.GFlags) or\
                isinstance(self.new_value, GObject.GEnum):
            value = int(self.new_value)
        st['value'] = value

        return st


class TimelineElementObserver(Loggable):
    """
    Monitors the props of a GES.TimelineElement and all its children and reports UndoableActions.

    Attributes:
        ges_timeline_element (GES.TimelineElement): The object to be monitored.
    """

    def __init__(self, ges_timeline_element, action_log):
        Loggable.__init__(self)
        self.ges_timeline_element = ges_timeline_element
        self.action_log = action_log

        self._properties = {}
        for prop in ges_timeline_element.list_children_properties():
            if prop.name in PROPS_TO_IGNORE:
                continue

            prop_name = child_property_name(prop)
            res, value = ges_timeline_element.get_child_property(prop_name)
            assert res, prop_name
            self._properties[prop_name] = value

        ges_timeline_element.connect('deep-notify', self._property_changed_cb)

    def release(self):
        self.ges_timeline_element.disconnect_by_func(self._property_changed_cb)
        self.ges_timeline_element = None

    def _property_changed_cb(self, ges_timeline_element, unused_gst_element, pspec):
        prop_name = child_property_name(pspec)
        if ges_timeline_element.get_control_binding(prop_name):
            self.debug("Property %s controlled", prop_name)
            return

        old_value = self._properties[prop_name]
        res, new_value = ges_timeline_element.get_child_property(prop_name)
        assert res, prop_name
        action = TrackElementPropertyChanged(
            ges_timeline_element, prop_name, old_value, new_value)
        self._properties[prop_name] = new_value
        self.action_log.push(action)


class TrackElementAdded(UndoableAction):
    # Note: We have a bug if we just remove the Effect from the timeline
    # and keep it saved here and then readd it to corresponding timeline (it
    # freezes everything). So what we are doing is  to free the Effect,
    # keep its settings here when undoing, and instanciate a new one when
    # doing again. We have to keep all EffectPropertyChanged object that refers
    # to the Effect when undoing so we reset theirs track_element when
    # doing it again. The way of doing it is the same with EffectRemoved

    def __init__(self, clip, track_element):
        UndoableAction.__init__(self)
        self.clip = clip
        self.track_element = track_element
        self.asset = track_element.get_asset()
        self.track_element_props = []

    def do(self):
        self.track_element = self.clip.add_asset(self.asset)
        for prop_name, prop_value in self.track_element_props:
            self.track_element.set_child_property(prop_name, prop_value)

    def undo(self):
        props = self.track_element.list_children_properties()
        self.track_element_props = [(child_property_name(prop), self.track_element.get_child_property(child_property_name(prop))[1])
                                    for prop in props
                                    if prop.flags & GObject.PARAM_WRITABLE and prop.name not in PROPS_TO_IGNORE]
        self.clip.remove(self.track_element)
        del self.track_element
        self.track_element = None

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("container-add-child")
        st["container-name"] = self.clip.get_name()
        st["asset-id"] = self.track_element.get_id()
        st["child-type"] = GObject.type_name(
            self.track_element.get_asset().get_extractable_type())

        return st


class TrackElementRemoved(UndoableAction):

    def __init__(self, clip, track_element):
        UndoableAction.__init__(self)
        self.track_element = track_element
        self.clip = clip
        self.asset = track_element.get_asset()
        self.track_element_props = []

    def do(self):
        props = self.track_element.list_children_properties()
        self.track_element_props = [(child_property_name(prop), self.track_element.get_child_property(child_property_name(prop))[1])
                                    for prop in props
                                    if prop.flags & GObject.PARAM_WRITABLE and prop.name not in PROPS_TO_IGNORE]

        self.clip.remove(self.track_element)
        del self.track_element
        self.track_element = None

    def undo(self):
        self.track_element = self.clip.add_asset(self.asset)
        for prop_name, prop_value in self.track_element_props:
            self.track_element.set_child_property(prop_name, prop_value)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("container-remove-child")
        st["container-name"] = self.clip.get_name()
        st["child-name"] = self.track_element.get_name()

        return st


class ControlSourceObserver(GObject.Object):
    """
    Monitors a control source's props and reports UndoableActions.

    Attributes:
        control_source (GstController.TimedValueControlSource): The object to be
            monitored.
    """

    def __init__(self, control_source, action_log, action_info):
        GObject.Object.__init__(self)

        self.action_log = action_log
        self.action_info = action_info
        self.control_source = control_source

        self.keyframes = {}
        for keyframe in self.control_source.get_all():
            self.keyframes[keyframe.timestamp] = (keyframe.timestamp, keyframe.value)

        control_source.connect("value-added", self._keyframe_added_cb)
        control_source.connect("value-changed", self._keyframe_moved_cb)
        control_source.connect("value-removed", self._keyframe_removed_cb)

    def release(self):
        self.control_source.disconnect_by_func(self._keyframe_added_cb)
        self.control_source.disconnect_by_func(self._keyframe_moved_cb)
        self.control_source.disconnect_by_func(self._keyframe_removed_cb)
        self.control_source = None

    def _keyframe_added_cb(self, control_source, keyframe):
        self.keyframes[keyframe.timestamp] = (keyframe.timestamp, keyframe.value)

        action = KeyframeAddedAction(control_source, keyframe, self.action_info)
        self.action_log.push(action)

    def _keyframe_moved_cb(self, control_source, keyframe):
        old_snapshot = self.keyframes[keyframe.timestamp]
        new_snapshot = (keyframe.timestamp, keyframe.value)
        self.keyframes[keyframe.timestamp] = new_snapshot

        action = KeyframeChangedAction(control_source,
                                       old_snapshot, new_snapshot)
        self.action_log.push(action)

    def _keyframe_removed_cb(self, control_source, keyframe):
        del self.keyframes[keyframe.timestamp]

        action = KeyframeRemovedAction(control_source, keyframe,
                                       self.action_info)
        self.action_log.push(action)


class ClipAdded(UndoableAction):

    def __init__(self, layer, clip):
        UndoableAction.__init__(self)
        self.layer = layer
        self.clip = clip

    def do(self):
        self.clip.set_name(None)
        self.layer.add_clip(self.clip)
        self.layer.get_timeline().get_asset().pipeline.commit_timeline()

    def undo(self):
        self.layer.remove_clip(self.clip)
        self.layer.get_timeline().get_asset().pipeline.commit_timeline()

    def asScenarioAction(self):
        timeline = self.layer.get_timeline()
        if hasattr(self.layer, "splitting_object") and \
                self.layer.splitting_object is True:
            return None
        elif hasattr(timeline, "ui") and timeline.ui and timeline.ui.editing_context is not None:
            return None

        st = Gst.Structure.new_empty("add-clip")
        st.set_value("name", self.clip.get_name())
        st.set_value("layer-priority", self.layer.props.priority)
        st.set_value("asset-id", self.clip.get_asset().get_id())
        st.set_value("type", GObject.type_name(self.clip))
        st.set_value("start", float(self.clip.props.start / Gst.SECOND))
        st.set_value("inpoint", float(self.clip.props.in_point / Gst.SECOND))
        st.set_value("duration", float(self.clip.props.duration / Gst.SECOND))
        return st


class ClipRemoved(UndoableAction):

    def __init__(self, layer, clip):
        UndoableAction.__init__(self)
        self.layer = layer
        self.clip = clip

    def do(self):
        self.layer.remove_clip(self.clip)
        self.layer.get_timeline().get_asset().pipeline.commit_timeline()

    def undo(self):
        self.clip.set_name(None)
        self.layer.add_clip(self.clip)
        self.layer.get_timeline().get_asset().pipeline.commit_timeline()

    def asScenarioAction(self):
        timeline = self.layer.get_timeline()
        if hasattr(timeline, "ui") and timeline.ui\
                and timeline.ui.editing_context is not None:
            return None

        st = Gst.Structure.new_empty("remove-clip")
        st.set_value("name", self.clip.get_name())
        return st


class LayerAdded(UndoableAction):

    def __init__(self, ges_timeline, ges_layer):
        UndoableAction.__init__(self)
        self.ges_timeline = ges_timeline
        self.ges_layer = ges_layer

    def do(self):
        self.ges_timeline.add_layer(self.ges_layer)

    def undo(self):
        self.ges_timeline.remove_layer(self.ges_layer)
        self.ges_timeline.get_asset().pipeline.commit_timeline()

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("add-layer")
        st.set_value("priority", self.ges_layer.props.priority)
        st.set_value("auto-transition", self.ges_layer.props.auto_transition)
        return st


class LayerRemoved(UndoableAction):

    def __init__(self, ges_timeline, ges_layer):
        UndoableAction.__init__(self)
        self.ges_timeline = ges_timeline
        self.ges_layer = ges_layer

    def do(self):
        self.ges_timeline.remove_layer(self.ges_layer)
        self.ges_timeline.get_asset().pipeline.commit_timeline()

    def undo(self):
        self.ges_timeline.add_layer(self.ges_layer)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("remove-layer")
        st.set_value("priority", self.ges_layer.props.priority)
        return st


class LayerMoved(UndoableAction):

    def __init__(self, ges_layer, old_priority, priority):
        UndoableAction.__init__(self)
        self.ges_layer = ges_layer
        self.old_priority = old_priority
        self.priority = priority

    def do(self):
        self.ges_layer.props.priority = self.priority

    def undo(self):
        self.ges_layer.props.priority = self.old_priority

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("move-layer")
        st.set_value("priority", self.ges_layer.props.priority)
        return st


class KeyframeAddedAction(UndoableAction):

    def __init__(self, control_source, keyframe, action_info):
        UndoableAction.__init__(self)
        self.control_source = control_source
        self.keyframe = keyframe
        self.action_info = action_info

    def do(self):
        self.control_source.set(self.keyframe.timestamp, self.keyframe.value)

    def undo(self):
        self.control_source.unset(self.keyframe.timestamp)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("add-keyframe")
        for key, value in self.action_info.items():
            st.set_value(key, value)
        st.set_value("timestamp", float(self.keyframe.timestamp / Gst.SECOND))
        st.set_value("value", self.keyframe.value)
        return st


class KeyframeRemovedAction(UndoableAction):

    def __init__(self, control_source, keyframe, action_info):
        UndoableAction.__init__(self)
        self.control_source = control_source
        self.keyframe = keyframe
        self.action_info = action_info

    def do(self):
        self.control_source.unset(self.keyframe.timestamp)

    def undo(self):
        self.control_source.set(self.keyframe.timestamp, self.keyframe.value)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("remove-keyframe")
        for key, value in self.action_info.items():
            st.set_value(key, value)
        st.set_value("timestamp", float(self.keyframe.timestamp / Gst.SECOND))
        st.set_value("value", self.keyframe.value)
        return st


class KeyframeChangedAction(UndoableAction):

    def __init__(self, control_source, old_snapshot, new_snapshot):
        UndoableAction.__init__(self)
        self.control_source = control_source
        self.old_snapshot = old_snapshot
        self.new_snapshot = new_snapshot

    def do(self):
        self._applySnapshot(self.new_snapshot)

    def undo(self):
        self._applySnapshot(self.old_snapshot)

    def _applySnapshot(self, snapshot):
        time, value = snapshot
        self.control_source.set(time, value)


class ActivePropertyChanged(UndoableAction):

    def __init__(self, effect_action, active):
        UndoableAction.__init__(self)
        self.effect_action = effect_action
        self.active = not active

    def do(self):
        self.effect_action.track_element.active = self.active
        self.active = not self.active

    def undo(self):
        self.effect_action.track_element.active = self.active
        self.active = not self.active


class TimelineObserver(Loggable):
    """Monitors a project's timeline and reports UndoableActions.

    Attributes:
        action_log (UndoableActionLog): The action log where to report actions.
    """

    def __init__(self, action_log, app):
        Loggable.__init__(self)
        self.action_log = action_log
        self.app = app
        self.clip_property_trackers = {}
        self.keyframe_observers = {}
        self.track_element_observers = {}
        self._layers_priorities = {}

    def startObserving(self, ges_timeline):
        """Starts monitoring the specified timeline.

        Args:
            ges_timeline (GES.Timeline): The timeline to be monitored.
        """
        for ges_layer in ges_timeline.get_layers():
            self._connect_to_layer(ges_layer)

        ges_timeline.connect("layer-added", self._layerAddedCb)
        ges_timeline.connect("layer-removed", self._layerRemovedCb)

    def _connect_to_layer(self, ges_layer):
        self._layers_priorities[ges_layer] = ges_layer.props.priority
        ges_layer.connect("clip-added", self._clipAddedCb)
        ges_layer.connect("clip-removed", self._clipRemovedCb)
        ges_layer.connect("notify::priority", self._layer_moved_cb)

        for ges_clip in ges_layer.get_clips():
            self._connectToClip(ges_clip)

    def _disconnect_from_layer(self, ges_layer):
        del self._layers_priorities[ges_layer]
        ges_layer.disconnect_by_func(self._clipAddedCb)
        ges_layer.disconnect_by_func(self._clipRemovedCb)
        ges_layer.disconnect_by_func(self._layer_moved_cb)

    def _connectToClip(self, ges_clip):
        tracker = GObjectObserver(ges_clip,
            ["start", "duration", "in-point", "priority"],
            self.action_log)
        self.clip_property_trackers[ges_clip] = tracker

        ges_clip.connect("child-added", self._clipTrackElementAddedCb)
        ges_clip.connect("child-removed", self._clipTrackElementRemovedCb)
        for track_element in ges_clip.get_children(True):
            self._connectToTrackElement(track_element)

    def _disconnectFromClip(self, clip):
        if isinstance(clip, GES.TransitionClip):
            return

        for child in clip.get_children(True):
            self._disconnectFromTrackElement(child)

        clip.disconnect_by_func(self._clipTrackElementAddedCb)
        clip.disconnect_by_func(self._clipTrackElementRemovedCb)
        tracker = self.clip_property_trackers.pop(clip)
        tracker.release()

    def _controlBindingAddedCb(self, track_element, binding):
        self._connectToControlSource(track_element, binding)

    def _connectToTrackElement(self, track_element):
        for prop, binding in track_element.get_all_control_bindings().items():
            self._connectToControlSource(track_element, binding,
                                         existed=True)
        track_element.connect("control-binding-added",
                              self._controlBindingAddedCb)
        if isinstance(track_element, GES.BaseEffect) or \
                isinstance(track_element, GES.VideoSource):
            observer = TimelineElementObserver(track_element, self.action_log)
            self.track_element_observers[track_element] = observer

    def _disconnectFromTrackElement(self, track_element):
        for prop, binding in track_element.get_all_control_bindings().items():
            self._disconnectFromControlSource(binding)
        observer = self.track_element_observers.pop(track_element, None)
        # We only keep track of some track_elements.
        if observer:
            observer.release()

    def _connectToControlSource(self, track_element, binding, existed=False):
        control_source = binding.props.control_source
        action_info = {"element-name": track_element.get_name(),
                       "property-name": binding.props.name}
        observer = ControlSourceObserver(control_source, self.action_log,
                                         action_info)
        self.keyframe_observers[control_source] = observer

        if not existed:
            properties = {"binding-type": "direct",
                          "source-type": "interpolation",
                          "interpolation-mode": "linear"}
            properties.update(action_info)
            self.app.write_action("set-control-source", properties)

    def _disconnectFromControlSource(self, binding):
        control_source = binding.props.control_source
        observer = self.keyframe_observers.pop(control_source)
        observer.release()

    def _clipAddedCb(self, layer, clip):
        if isinstance(clip, GES.TransitionClip):
            return
        self._connectToClip(clip)
        action = ClipAdded(layer, clip)
        self.action_log.push(action)

    def _clipRemovedCb(self, layer, clip):
        if isinstance(clip, GES.TransitionClip):
            return
        self._disconnectFromClip(clip)
        action = ClipRemoved(layer, clip)
        self.action_log.push(action)

    def _clipTrackElementAddedCb(self, clip, track_element):
        self._connectToTrackElement(track_element)
        if isinstance(track_element, GES.BaseEffect):
            action = TrackElementAdded(clip, track_element)
            self.action_log.push(action)

    def _clipTrackElementRemovedCb(self, clip, track_element):
        self.debug("%s REMOVED from (%s)" % (track_element, clip))
        self._disconnectFromTrackElement(track_element)
        if isinstance(track_element, GES.BaseEffect):
            action = TrackElementRemoved(clip, track_element)
            self.action_log.push(action)

    def _trackElementActiveChangedCb(self, track_element, active, add_effect_action):
        """
        This happens when an effect is (de)activated on a clip in the timeline.
        """
        action = ActivePropertyChanged(add_effect_action, active)
        self.action_log.push(action)

    def _layer_moved_cb(self, ges_layer, unused_param):
        previous = self._layers_priorities[ges_layer]
        current = ges_layer.props.priority
        self._layers_priorities[ges_layer] = current
        action = LayerMoved(ges_layer, previous, current)
        self.action_log.push(action)

    def _layerAddedCb(self, ges_timeline, ges_layer):
        self._connect_to_layer(ges_layer)
        action = LayerAdded(ges_timeline, ges_layer)
        self.action_log.push(action)

    def _layerRemovedCb(self, ges_timeline, ges_layer):
        self._disconnect_from_layer(ges_layer)
        action = LayerRemoved(ges_timeline, ges_layer)
        self.action_log.push(action)
