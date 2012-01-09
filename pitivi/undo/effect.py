#!/usr/bin/env python
#
#       effect.py
#
# Copyright (C) 2012 Thibault Saunier <thibaul.saunier@collabora.com>
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
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.

from pitivi.undo.undo import UndoableAction


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

        for prop in gobject.list_properties(gst_element):
            gst_element.connect('notify::' + prop.name,
                                self._propertyChangedCb,
                                gst_element)
            if prop.flags & gobject.PARAM_READABLE:
                properties[prop.name] = gst_element.get_property(prop.name)
        self._tracked_effects[gst_element] = properties

    def getPropChangedFromTrackObj(self, track_effect):
        prop_changed = []

        for undo_stack in self.action_log.undo_stacks:
            for done_prop_change in undo_stack.done_actions:
                if isinstance(done_prop_change, EffectPropertyChanged):
                    if done_prop_change.gst_element is\
                                        track_effect.getElement():
                        prop_changed.append(done_prop_change)

        for redo_stack in self.action_log.redo_stacks:
            for done_prop_change in redo_stack.done_actions:
                if isinstance(done_prop_change, EffectPropertyChanged):
                    if done_prop_change.gst_element is\
                                        track_effect.getElement():
                        prop_changed.append(done_prop_change)

        return prop_changed

    def _propertyChangedCb(self, gst_element, pspec, unused):
        old_value = self._tracked_effects[gst_element][pspec.name]
        new_value = gst_element.get_property(pspec.name)
        action = EffectPropertyChanged(gst_element, pspec.name, old_value,
                                       new_value)
        self._tracked_effects[gst_element][pspec.name] = new_value
        self.action_log.push(action)
