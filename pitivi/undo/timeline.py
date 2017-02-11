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
from pitivi.undo.undo import Action
from pitivi.undo.undo import FinalizingAction
from pitivi.undo.undo import GObjectObserver
from pitivi.undo.undo import MetaContainerObserver
from pitivi.undo.undo import UndoableAction
from pitivi.undo.undo import UndoableAutomaticObjectAction
from pitivi.utils.loggable import Loggable


TRANSITION_PROPS = ["border", "invert", "transition-type"]


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

    def __repr__(self):
        return "<TrackElementPropertyChanged %s.%s: %s -> %s>" % (self.track_element,
                                                                  self.property_name,
                                                                  self.old_value,
                                                                  self.new_value)

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
    """Monitors the props of an element and all its children.

    Reports UndoableActions.

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
        if pspec.name in PROPS_TO_IGNORE:
            return

        if ges_timeline_element.get_control_binding(prop_name):
            self.debug("Property %s controlled", prop_name)
            return

        old_value = self._properties[prop_name]
        res, new_value = ges_timeline_element.get_child_property(prop_name)
        assert res, prop_name
        if old_value == new_value:
            # Nothing to see here.
            return

        action = TrackElementPropertyChanged(
            ges_timeline_element, prop_name, old_value, new_value)
        self._properties[prop_name] = new_value
        self.action_log.push(action)


class TrackElementObserver(TimelineElementObserver):
    """Monitors the props of a track element.

    Reports UndoableActions.

    Args:
        ges_track_element (GES.TrackElement): The object to be monitored.
    """

    def __init__(self, ges_track_element, action_log):
        TimelineElementObserver.__init__(self, ges_track_element, action_log)
        self.gobject_observer = GObjectObserver(ges_track_element, ("active",), action_log)

    def release(self):
        TimelineElementObserver.release(self)
        self.gobject_observer.release()


class TrackElementAction(UndoableAction):

    def __init__(self, clip, track_element):
        UndoableAction.__init__(self)
        self.clip = clip
        self.track_element = track_element
        self.track_element_props = []
        for prop in self.track_element.list_children_properties():
            if not prop.flags & GObject.PARAM_WRITABLE or \
                    prop.name in PROPS_TO_IGNORE:
                continue
            prop_name = child_property_name(prop)
            res, value = self.track_element.get_child_property(prop_name)
            assert res
            self.track_element_props.append((prop_name, value))

    def add(self):
        assert self.clip.add(self.track_element)
        for prop_name, prop_value in self.track_element_props:
            self.track_element.set_child_property(prop_name, prop_value)

    def remove(self):
        self.clip.remove(self.track_element)


class TrackElementAdded(TrackElementAction):

    def __repr__(self):
        return "<TrackElementAdded %s, %s>" % (self.clip, self.track_element)

    def do(self):
        self.add()

    def undo(self):
        self.remove()

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("container-add-child")
        st["container-name"] = self.clip.get_name()
        st["asset-id"] = self.track_element.get_id()
        asset = self.track_element.get_asset()
        if asset:
            st["child-type"] = GObject.type_name(asset.get_extractable_type())
        return st


class TrackElementRemoved(TrackElementAction):

    def __repr__(self):
        return "<TrackElementRemoved %s, %s>" % (self.clip, self.track_element)

    def do(self):
        self.remove()

    def undo(self):
        self.add()

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("container-remove-child")
        st["container-name"] = self.clip.get_name()
        st["child-name"] = self.track_element.get_name()
        return st


class ControlSourceObserver(GObject.Object):
    """Monitors a control source's props and reports UndoableActions.

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


class ClipAction(UndoableAction):

    def __init__(self, layer, clip):
        UndoableAction.__init__(self)
        self.layer = layer
        self.clip = clip

    def add(self):
        self.clip.set_name(None)
        children = self.clip.get_children(False)
        self.layer.add_clip(self.clip)
        # GES adds children if the clip had none. Make sure they are removed.
        for child in self.clip.get_children(False):
            if child not in children:
                self.clip.remove(child)
        self.layer.get_timeline().get_asset().pipeline.commit_timeline()

    def _child_added_cb(self, clip, track_element):
        clip.remove(track_element)

    def remove(self):
        self.layer.remove_clip(self.clip)
        self.layer.get_timeline().get_asset().pipeline.commit_timeline()


class ClipAdded(ClipAction):

    def __repr__(self):
        return "<ClipAdded %s>" % self.clip

    def do(self):
        self.add()

    def undo(self):
        self.remove()

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


class ClipRemoved(ClipAction):

    def __init__(self, layer, clip):
        ClipAction.__init__(self, layer, clip)
        self.transition_removed_actions = []

    def __repr__(self):
        return "<ClipRemoved %s>" % self.clip

    def expand(self, action):
        if not isinstance(action, TransitionClipRemovedAction):
            return False
        self.transition_removed_actions.append(action)
        return True

    def do(self):
        self.remove()

    def undo(self):
        self.add()
        # Update the automatically created transitions.
        for action in self.transition_removed_actions:
            action.undo()

    def asScenarioAction(self):
        timeline = self.layer.get_timeline()
        if hasattr(timeline, "ui") and timeline.ui\
                and timeline.ui.editing_context is not None:
            return None

        st = Gst.Structure.new_empty("remove-clip")
        st.set_value("name", self.clip.get_name())
        return st


class TransitionClipAction(UndoableAction):

    def __init__(self, ges_layer, ges_clip, track_element):
        UndoableAction.__init__(self)
        self.ges_layer = ges_layer
        self.start = ges_clip.props.start
        self.duration = ges_clip.props.duration
        self.track_element = track_element

    @staticmethod
    def get_video_element(ges_clip):
        for track_element in ges_clip.get_children(recursive=True):
            if isinstance(track_element, GES.VideoTransition):
                return track_element
        return None

    def find_video_transition(self):
        for ges_clip in self.ges_layer.get_clips():
            if isinstance(ges_clip, GES.TransitionClip) and \
                    ges_clip.props.start == self.start and \
                    ges_clip.props.duration == self.duration:
                # Got the transition clip, now find its video element, if any.
                track_element = TransitionClipAction.get_video_element(ges_clip)
                if not track_element:
                    # Probably the audio transition clip.
                    continue
                # Double lucky!
                return track_element


class TransitionClipAddedAction(TransitionClipAction):

    @classmethod
    def new(cls, ges_layer, ges_clip):
        track_element = cls.get_video_element(ges_clip)
        if not track_element:
            return None
        return cls(ges_layer, ges_clip, track_element)

    def do(self):
        """Searches the transition clip created automatically to update it."""
        track_element = self.find_video_transition()
        assert track_element
        UndoableAutomaticObjectAction.update_object(self.track_element, track_element)

    def undo(self):
        # The transition is being removed, nothing to do.
        pass


class TransitionClipRemovedAction(TransitionClipAction):

    def __init__(self, ges_layer, ges_clip, track_element):
        UndoableAction.__init__(self)
        self.ges_layer = ges_layer
        self.start = ges_clip.props.start
        self.duration = ges_clip.props.duration
        self.track_element = track_element

        self.properties = []
        for property_name in TRANSITION_PROPS:
            field_name = property_name.replace("-", "_")
            value = self.track_element.get_property(field_name)
            self.properties.append((property_name, value))

    @classmethod
    def new(cls, ges_layer, ges_clip):
        track_element = cls.get_video_element(ges_clip)
        if not track_element:
            return None
        return cls(ges_layer, ges_clip, track_element)

    def do(self):
        # The transition is being removed, nothing to do.
        pass

    def undo(self):
        # Search the transition clip created automatically to update it.
        for ges_clip in self.ges_layer.get_clips():
            if isinstance(ges_clip, GES.TransitionClip) and \
                    ges_clip.props.start == self.start and \
                    ges_clip.props.duration == self.duration:
                # Got the transition clip, now find its video element, if any.
                track_element = self.get_video_element(ges_clip)
                if not track_element:
                    # Probably the audio transition clip.
                    continue
                # Double lucky!
                UndoableAutomaticObjectAction.update_object(self.track_element, track_element)
                for prop_name, value in self.properties:
                    track_element.set_property(prop_name, value)
                break


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

    def __repr__(self):
        return "<LayerRemoved %s>" % self.ges_layer

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

    def __repr__(self):
        return "<LayerMoved %s: %s -> %s>" % (self.ges_layer,
                                              self.old_priority,
                                              self.priority)

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


class ControlSourceSetAction(Action):

    def __init__(self, action_info):
        Action.__init__(self)
        self.action_info = action_info

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("set-control-source")
        for key, value in self.action_info.items():
            st.set_value(key, value)
        st.set_value("binding-type", "direct")
        st.set_value("source-type", "interpolation")
        st.set_value("interpolation-mode", "linear")
        return st


class LayerObserver(MetaContainerObserver, Loggable):
    """Monitors a Layer and reports UndoableActions.

    Args:
        ges_layer (GES.Layer): The layer to observe.

    Attributes:
        action_log (UndoableActionLog): The action log where to report actions.
    """

    def __init__(self, ges_layer, action_log):
        MetaContainerObserver.__init__(self, ges_layer, action_log)
        Loggable.__init__(self)
        self.action_log = action_log
        self.priority = ges_layer.props.priority

        self.keyframe_observers = {}
        self.track_element_observers = {}

        ges_layer.connect("clip-added", self._clipAddedCb)
        ges_layer.connect("clip-removed", self._clipRemovedCb)
        ges_layer.connect("notify::priority", self.__layer_moved_cb)

        self.clip_observers = {}
        for ges_clip in ges_layer.get_clips():
            self._connectToClip(ges_clip)

    def _connectToClip(self, ges_clip):
        ges_clip.connect("child-added", self._clipTrackElementAddedCb)
        ges_clip.connect("child-removed", self._clipTrackElementRemovedCb)

        for track_element in ges_clip.get_children(recursive=True):
            self._connectToTrackElement(track_element)

        if isinstance(ges_clip, GES.TransitionClip):
            return

        props = ["start", "duration", "in-point", "priority"]
        clip_observer = GObjectObserver(ges_clip, props, self.action_log)
        self.clip_observers[ges_clip] = clip_observer

    def _disconnectFromClip(self, ges_clip):
        ges_clip.disconnect_by_func(self._clipTrackElementAddedCb)
        ges_clip.disconnect_by_func(self._clipTrackElementRemovedCb)

        for child in ges_clip.get_children(recursive=True):
            self._disconnectFromTrackElement(child)

        if isinstance(ges_clip, GES.TransitionClip):
            return

        clip_observer = self.clip_observers.pop(ges_clip)
        clip_observer.release()

    def _controlBindingAddedCb(self, track_element, binding):
        self._connectToControlSource(track_element, binding)
        action_info = {"element-name": track_element.get_name(),
                       "property-name": binding.props.name}
        action = ControlSourceSetAction(action_info)
        self.action_log.push(action)

    def _connectToTrackElement(self, track_element):
        if isinstance(track_element, GES.VideoTransition):
            ges_clip = track_element.get_toplevel_parent()
            ges_layer = ges_clip.props.layer
            action = TransitionClipAddedAction(ges_layer, ges_clip,
                                               track_element)
            self.action_log.push(action)

            observer = GObjectObserver(track_element, TRANSITION_PROPS,
                                       self.action_log)
            self.track_element_observers[track_element] = observer
            return

        for prop, binding in track_element.get_all_control_bindings().items():
            self._connectToControlSource(track_element, binding)
        track_element.connect("control-binding-added",
                              self._controlBindingAddedCb)
        if isinstance(track_element, GES.BaseEffect) or \
                isinstance(track_element, GES.VideoSource):
            observer = TrackElementObserver(track_element, self.action_log)
            self.track_element_observers[track_element] = observer

    def _disconnectFromTrackElement(self, track_element):
        for prop, binding in track_element.get_all_control_bindings().items():
            self._disconnectFromControlSource(binding)
        observer = self.track_element_observers.pop(track_element, None)
        # We only keep track of some track_elements.
        if observer:
            observer.release()

    def _connectToControlSource(self, track_element, binding):
        control_source = binding.props.control_source
        action_info = {"element-name": track_element.get_name(),
                       "property-name": binding.props.name}
        observer = ControlSourceObserver(control_source, self.action_log,
                                         action_info)
        self.keyframe_observers[control_source] = observer

    def _disconnectFromControlSource(self, binding):
        control_source = binding.props.control_source
        observer = self.keyframe_observers.pop(control_source)
        observer.release()

    def _clipAddedCb(self, layer, clip):
        self._connectToClip(clip)
        if isinstance(clip, GES.TransitionClip):
            return
        action = ClipAdded(layer, clip)
        self.action_log.push(action)

    def _clipRemovedCb(self, layer, clip):
        self._disconnectFromClip(clip)
        if isinstance(clip, GES.TransitionClip):
            action = TransitionClipRemovedAction.new(layer, clip)
            if action:
                self.action_log.push(action)
            return
        action = ClipRemoved(layer, clip)
        self.action_log.push(action)

    def _clipTrackElementAddedCb(self, clip, ges_track_element):
        self._connectToTrackElement(ges_track_element)
        action = TrackElementAdded(clip, ges_track_element)
        self.action_log.push(action)

    def _clipTrackElementRemovedCb(self, clip, ges_track_element):
        self.debug("%s REMOVED from %s", ges_track_element, clip)
        self._disconnectFromTrackElement(ges_track_element)
        action = TrackElementRemoved(clip, ges_track_element)
        self.action_log.push(action)

    def __layer_moved_cb(self, ges_layer, unused_param):
        current = ges_layer.props.priority
        action = LayerMoved(ges_layer, self.priority, current)
        self.action_log.push(action)
        self.priority = current


class TimelineElementAddedToGroup(UndoableAction):

    def __init__(self, ges_group, ges_timeline_element):
        UndoableAction.__init__(self)
        self.ges_group = ges_group
        self.ges_timeline_element = ges_timeline_element

    def __repr__(self):
        return "<TimelineElementAddedToGroup %s, %s>" % (self.ges_group, self.ges_timeline_element)

    def do(self):
        self.ges_group.add(self.ges_timeline_element)

    def undo(self):
        self.ges_group.remove(self.ges_timeline_element)


class TimelineElementRemovedFromGroup(UndoableAction):

    def __init__(self, ges_group, ges_timeline_element):
        UndoableAction.__init__(self)
        self.ges_group = ges_group
        self.ges_timeline_element = ges_timeline_element

    def __repr__(self):
        return "<TimelineElementRemovedFromGroup %s, %s>" % (self.ges_group, self.ges_timeline_element)

    def do(self):
        self.ges_group.remove(self.ges_timeline_element)

    def undo(self):
        self.ges_group.add(self.ges_timeline_element)


class GroupObserver(Loggable):
    """Monitors a Group and reports UndoableActions.

    Args:
        ges_group (GES.Group): The group to observe.

    Attributes:
        action_log (UndoableActionLog): The action log where to report actions.
    """

    def __init__(self, ges_group, action_log):
        Loggable.__init__(self)
        self.log("INIT %s", ges_group)
        self.ges_group = ges_group
        self.action_log = action_log

        ges_group.connect_after("child-added", self.__child_added_cb)
        ges_group.connect("child-removed", self.__child_removed_cb)

    def __child_added_cb(self, ges_group, ges_timeline_element):
        action = TimelineElementAddedToGroup(ges_group, ges_timeline_element)
        self.action_log.push(action)

    def __child_removed_cb(self, ges_group, ges_timeline_element):
        action = TimelineElementRemovedFromGroup(ges_group, ges_timeline_element)
        self.action_log.push(action)


class TimelineObserver(Loggable):
    """Monitors a project's timeline and reports UndoableActions.

    Attributes:
        ges_timeline (GES.Timeline): The timeline to be monitored.
        action_log (UndoableActionLog): The action log where to report actions.
    """

    def __init__(self, ges_timeline, action_log):
        Loggable.__init__(self)
        self.ges_timeline = ges_timeline
        self.action_log = action_log

        self.layer_observers = {}
        self.group_observers = {}
        for ges_layer in ges_timeline.get_layers():
            self._connect_to_layer(ges_layer)

        ges_timeline.connect("layer-added", self.__layer_added_cb)
        ges_timeline.connect("layer-removed", self.__layer_removed_cb)

        for ges_group in ges_timeline.get_groups():
            self._connect_to_group(ges_group)

        ges_timeline.connect("group-added", self.__group_added_cb)
        # We don't care about the group-removed signal because this greatly
        # simplifies the logic.

    def __layer_added_cb(self, ges_timeline, ges_layer):
        action = LayerAdded(self.ges_timeline, ges_layer)
        self.action_log.push(action)
        self._connect_to_layer(ges_layer)

    def _connect_to_layer(self, ges_layer):
        layer_observer = LayerObserver(ges_layer, self.action_log)
        self.layer_observers[ges_layer] = layer_observer

    def __layer_removed_cb(self, ges_timeline, ges_layer):
        action = LayerRemoved(ges_timeline, ges_layer)
        self.action_log.push(action)

    def _connect_to_group(self, ges_group):
        if not ges_group.props.serialize:
            return False

        # A group is added when it gets its first element, thus
        # when undoing/redoing a group can be added multiple times.
        # This is the only complexity caused by the fact that we keep alive
        # all the GroupObservers which have been created.
        if ges_group not in self.group_observers:
            group_observer = GroupObserver(ges_group, self.action_log)
            self.group_observers[ges_group] = group_observer
        return True

    def __group_added_cb(self, unused_ges_timeline, ges_group):
        if not self._connect_to_group(ges_group):
            return

        # This should be a single clip.
        for ges_clip in ges_group.get_children(recursive=False):
            action = TimelineElementAddedToGroup(ges_group, ges_clip)
            self.action_log.push(action)
