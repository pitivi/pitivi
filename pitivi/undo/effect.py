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

from gi.repository import GObject, GES

from pitivi.undo.undo import UndoableAction
from pitivi.effects import PROPS_TO_IGNORE


class EffectPropertyChanged(UndoableAction):
    def __init__(self, gst_element, property_name, old_value, new_value):
        self.gst_element = gst_element
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def do(self):
        self.gst_element.set_property(self.property_name, self.new_value)
        self._done()

    def undo(self):
        self.gst_element.set_property(self.property_name, self.old_value)
        self._undone()


# FIXME We should refactor pitivi.undo.PropertyChangeTracker so we can use it as
# a baseclass here!
class EffectGstElementPropertyChangeTracker:
    """
    Track effect configuration changes in its list of control effects
    """
    def __init__(self, action_log):
        self._tracked_effects = {}
        self.action_log = action_log
        self.pipeline = None

    def addEffectElement(self, gst_element):
        properties = {}

        if gst_element in self._tracked_effects:
            return

        for prop in GObject.list_properties(gst_element):
            gst_element.connect('notify::' + prop.name,
                                self._propertyChangedCb,
                                gst_element)
            if prop.flags & GObject.PARAM_READABLE:
                properties[prop.name] = gst_element.get_property(prop.name)
        self._tracked_effects[gst_element] = properties

    def getPropChangedFromTrackObj(self, effect):
        prop_changed = []

        for undo_stack in self.action_log.undo_stacks:
            for done_prop_change in undo_stack.done_actions:
                if isinstance(done_prop_change, EffectPropertyChanged):
                    if done_prop_change.gst_element is effect.getElement():
                        prop_changed.append(done_prop_change)

        for redo_stack in self.action_log.redo_stacks:
            for done_prop_change in redo_stack.done_actions:
                if isinstance(done_prop_change, EffectPropertyChanged):
                    if done_prop_change.gst_element is effect.getElement():
                        prop_changed.append(done_prop_change)

        return prop_changed

    def _propertyChangedCb(self, gst_element, pspec, unused):
        old_value = self._tracked_effects[gst_element][pspec.name]
        new_value = gst_element.get_property(pspec.name)
        action = EffectPropertyChanged(gst_element, pspec.name, old_value, new_value)
        self._tracked_effects[gst_element][pspec.name] = new_value
        self.action_log.push(action)


class EffectAdded(UndoableAction):
    # Note: We have a bug if we just remove the Effect from the timeline
    # and keep it saved here and then readd it to corresponding timeline (it
    # freezes everything). So what we are doing is  to free the Effect,
    # keep its settings here when undoing, and instanciate a new one when
    # doing again. We have to keep all EffectPropertyChanged object that refers
    # to the Effect when undoing so we reset theirs gst_element when
    # doing it again. The way of doing it is the same with EffectRemoved
    def __init__(self, clip, effect, properties_watcher):
        self.clip = clip
        self.effect = effect
        self.asset = effect.get_asset()
        self.effect_props = []
        self.gnl_obj_props = []
        self._properties_watcher = properties_watcher
        self._props_changed = []

    def do(self):
        self.effect = self.clip.add_asset(self.asset)
        for prop_name, prop_value in self.effect_props:
            self.effect.set_child_property(prop_name, prop_value)
        self.clip.get_layer().get_timeline().commit()
        self._props_changed = []
        self._done()

    def undo(self):
        props = self.effect.list_children_properties()
        self.effect_props = [(prop.name, self.effect.get_child_property(prop.name)[1])
                          for prop in props
                          if prop.flags & GObject.PARAM_WRITABLE
                          and prop.name not in PROPS_TO_IGNORE]
        self.clip.remove(self.effect)
        self._props_changed =\
            self._properties_watcher.getPropChangedFromTrackObj(self.effect)
        del self.effect
        self.effect = None
        self._undone()


class EffectRemoved(UndoableAction):
    def __init__(self, clip, effect, properties_watcher):
        self.effect = effect
        self.clip = clip
        self.asset = effect.get_asset()
        self.effect_props = []
        self.gnl_obj_props = []
        self._properties_watcher = properties_watcher
        self._props_changed = []

    def do(self):
        props = self.effect.list_children_properties()
        self.effect_props = [(prop.name, self.effect.get_child_property(prop.name)[1])
                          for prop in props
                          if prop.flags & GObject.PARAM_WRITABLE
                          and prop.name not in PROPS_TO_IGNORE]

        self.clip.remove(self.effect)

        self._props_changed =\
            self._properties_watcher.getPropChangedFromTrackObj(self.effect)
        del self.effect
        self.effect = None
        self._done()

    def undo(self):
        self.effect = self.clip.add_asset(self.asset)
        for prop_name, prop_value in self.effect_props:
            self.effect.set_child_property(prop_name, prop_value)
        self.clip.get_layer().get_timeline().commit()
        self._props_changed = []
        self._undone()
