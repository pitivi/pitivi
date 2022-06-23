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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Undo/redo."""
from gi.repository import GObject

from pitivi.utils.loggable import Loggable


class UndoError(Exception):
    """Base class for undo/redo exceptions."""


class UndoWrongStateError(UndoError):
    """Exception related to the current state of the undo/redo stack."""


class ConditionsNotReadyYetError(UndoError):
    """The operation cannot be performed at the moment, maybe later."""


class Action(GObject.Object, Loggable):
    """Something which might worth logging in a scenario."""

    def __init__(self):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

    def as_scenario_action(self):
        """Converts the action to a Gst.Structure for a `.scenario` file."""
        return None


class UndoableAction(Action):
    """An action that can be undone.

    When your object's state changes, create an UndoableAction to allow
    reverting the change later on.
    """

    def do(self):
        raise NotImplementedError()

    def undo(self):
        raise NotImplementedError()

    # pylint: disable=unused-argument
    def expand(self, action):
        """Allows the action to expand by including the specified action.

        Args:
            action (UndoableAction): The action to include.

        Returns:
            bool: Whether the action has been included, in which case
                it should not be used for anything else.
        """
        return False


class UndoableAutomaticObjectAction(UndoableAction):
    """An action on an automatically created object.

    Attributes:
        auto_object (object): The object which has been automatically created
            and might become obsolete later.
    """

    # pylint: disable=abstract-method

    __updates = {}

    def __init__(self, auto_object):
        UndoableAction.__init__(self)
        self.__auto_object = auto_object

    @property
    def auto_object(self):
        """The latest object which identifies the same thing as the original."""
        return self.__updates.get(self.__auto_object, self.__auto_object)

    @classmethod
    def update_object(cls, auto_object, new_auto_object):
        """Provides a replacement for an object.

        Args:
            auto_object (object): The object being replaced.
            new_auto_object (object): The replacement.
        """
        cls.__updates[auto_object] = new_auto_object
        others = [key
                  for key, value in cls.__updates.items()
                  if value == auto_object]
        for other in others:
            cls.__updates[other] = new_auto_object


class FinalizingAction:
    """Base class for actions applied when an undo or redo is performed."""

    def do(self):
        raise NotImplementedError()


class PropertyChangedAction(UndoableAutomaticObjectAction):

    def __init__(self, gobject, field_name, old_value, new_value):
        UndoableAutomaticObjectAction.__init__(self, gobject)
        self.field_name = field_name
        self.old_value = old_value
        self.new_value = new_value

    def __repr__(self):
        return "<PropertyChanged %s.%s: %s -> %s>" % (self.auto_object, self.field_name, self.old_value, self.new_value)

    def do(self):
        self.auto_object.set_property(self.field_name, self.new_value)

    def undo(self):
        self.auto_object.set_property(self.field_name, self.old_value)

    def expand(self, action):
        if not isinstance(action, PropertyChangedAction) or \
                self.auto_object != action.auto_object or \
                self.field_name != action.field_name:
            return False

        self.new_value = action.new_value
        return True


class GObjectObserver(GObject.Object):
    """Monitor for GObject.Object's props, reporting UndoableActions.

    Attributes:
        gobject (GObject.Object): The object to be monitored.
        property_names (List[str]): The props to be monitored.
    """

    def __init__(self, gobject, property_names, action_log):
        GObject.Object.__init__(self)
        self.gobject = gobject
        self.property_names = property_names
        self.action_log = action_log

        self.properties = {}
        for property_name in self.property_names:
            field_name = property_name.replace("-", "_")
            self.properties[property_name] = gobject.get_property(field_name)
            # Connect to obj to keep track when the monitored props change.
            signal_name = "notify::%s" % property_name
            gobject.connect(signal_name, self._property_changed_cb,
                            property_name, field_name)

    def release(self):
        self.gobject.disconnect_by_func(self._property_changed_cb)
        self.gobject = None

    def _property_changed_cb(self, gobject, pspec, property_name, field_name):
        old_value = self.properties[property_name]
        property_value = gobject.get_property(field_name)
        if old_value == property_value:
            return
        self.properties[property_name] = property_value
        action = PropertyChangedAction(gobject, field_name,
                                       old_value, property_value)
        self.action_log.push(action)
