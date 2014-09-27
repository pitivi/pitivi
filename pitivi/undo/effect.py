# Pitivi video editor
#
#       pitivi/undo/effect.py
#
# Copyright (C) 2012 Thibault Saunier <thibault.saunier@collabora.com>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.

from gi.repository import GObject
from gi.repository import Gst

from pitivi.undo.undo import UndoableAction
from pitivi.effects import PROPS_TO_IGNORE


class TrackElementPropertyChanged(UndoableAction):

    def __init__(self, track_element, property_name, old_value, new_value):
        UndoableAction.__init__(self)
        self.track_element = track_element
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def do(self):
        self.track_element.set_child_property(self.property_name, self.new_value)
        self._done()

    def undo(self):
        self.track_element.set_child_property(self.property_name, self.old_value)
        self._undone()

    def serializeLastAction(self):
        st = Gst.Structure.new_empty("set-child-property")
        st['element-name'] = self.track_element.get_name()
        st['property'] = self.property_name
        st['value'] = self.new_value

        return st


# FIXME We should refactor pitivi.undo.PropertyChangeTracker so we can use it as
# a baseclass here!
class TrackElementChildPropertyTracker:

    """
    Track track_element configuration changes in its list of control track_elements
    """

    def __init__(self, action_log):
        self._tracked_track_elements = {}
        self.action_log = action_log
        self.pipeline = None

    def addTrackElement(self, track_element):
        if track_element in self._tracked_track_elements:
            return

        properties = {}

        track_element.connect('deep-notify', self._propertyChangedCb)

        for prop in track_element.list_children_properties():
            properties[prop.name] = track_element.get_child_property(prop.name)[1]

        self._tracked_track_elements[track_element] = properties

    def getPropChangedFromTrackElement(self, track_element):
        return self._tracked_track_elements[track_element]

    def _propertyChangedCb(self, track_element, unused_gstelement, pspec):
        old_value = self._tracked_track_elements[track_element][pspec.name]
        new_value = track_element.get_child_property(pspec.name)[1]
        action = TrackElementPropertyChanged(
            track_element, pspec.name, old_value, new_value)
        self._tracked_track_elements[track_element][pspec.name] = new_value
        self.action_log.push(action)


class TrackElementAdded(UndoableAction):
    # Note: We have a bug if we just remove the Effect from the timeline
    # and keep it saved here and then readd it to corresponding timeline (it
    # freezes everything). So what we are doing is  to free the Effect,
    # keep its settings here when undoing, and instanciate a new one when
    # doing again. We have to keep all TrackElementPropertyChanged object that refers
    # to the Effect when undoing so we reset theirs track_element when
    # doing it again. The way of doing it is the same with EffectRemoved

    def __init__(self, clip, track_element, properties_watcher):
        UndoableAction.__init__(self)
        self.clip = clip
        self.track_element = track_element
        self.asset = track_element.get_asset()
        self.track_element_props = []
        self.gnl_obj_props = []
        self._properties_watcher = properties_watcher
        self._props_changed = []

    def do(self):
        self.track_element = self.clip.add_asset(self.asset)
        for prop_name, prop_value in self.track_element_props:
            self.track_element.set_child_property(prop_name, prop_value)
        self.clip.get_layer().get_timeline().commit()
        self._props_changed = []
        self._done()

    def undo(self):
        props = self.track_element.list_children_properties()
        self.track_element_props = [(prop.name, self.track_element.get_child_property(prop.name)[1])
                             for prop in props
                             if prop.flags & GObject.PARAM_WRITABLE
                             and prop.name not in PROPS_TO_IGNORE]
        self.clip.remove(self.track_element)
        self._props_changed =\
            self._properties_watcher.getPropChangedFromTrackElement(self.track_element)
        del self.track_element
        self.track_element = None
        self._undone()

    def serializeLastAction(self):
        st = Gst.Structure.new_empty("container-add-child")
        st["container-name"] = self.clip.get_name()
        st["asset-id"] = self.track_element.get_id()
        st["child-type"] = GObject.type_name(self.track_element.get_asset().get_extractable_type())

        return st


class TrackElementRemoved(UndoableAction):

    def __init__(self, clip, track_element, properties_watcher):
        UndoableAction.__init__(self)
        self.track_element = track_element
        self.clip = clip
        self.asset = track_element.get_asset()
        self.track_element_props = []
        self.gnl_obj_props = []
        self._properties_watcher = properties_watcher
        self._props_changed = []

    def do(self):
        props = self.track_element.list_children_properties()
        self.track_element_props = [(prop.name, self.track_element.get_child_property(prop.name)[1])
                             for prop in props
                             if prop.flags & GObject.PARAM_WRITABLE
                             and prop.name not in PROPS_TO_IGNORE]

        self.clip.remove(self.track_element)

        self._props_changed =\
            self._properties_watcher.getPropChangedFromTrackElement(self.track_element)
        del self.track_element
        self.track_element = None
        self._done()

    def undo(self):
        self.track_element = self.clip.add_asset(self.asset)
        for prop_name, prop_value in self.track_element_props:
            self.track_element.set_child_property(prop_name, prop_value)
        self.clip.get_layer().get_timeline().commit()
        self._props_changed = []
        self._undone()

    def serializeLastAction(self):
        st = Gst.Structure.new_empty("container-remove-child")
        st["container-name"] = self.clip.get_name()
        st["child-name"] = self.track_element.get_name()

        return st
