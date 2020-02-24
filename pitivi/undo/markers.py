# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Millan Castro <m.castrovilarino@gmail.com>
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
"""Undo/redo logic for markers."""
from gi.repository import Gst

from pitivi.undo.undo import MetaContainerObserver
from pitivi.undo.undo import UndoableAutomaticObjectAction
from pitivi.utils.loggable import Loggable


class MarkerListObserver(Loggable):
    """Monitors a MarkerList and reports UndoableActions.

    Args:
        ges_marker_list (GES.MarkerList): The markerlist to observe.

    Attributes:
        action_log (UndoableActionLog): The action log where to report actions.
    """

    def __init__(self, ges_marker_list, action_log):
        Loggable.__init__(self)

        self.action_log = action_log

        self.marker_observers = {}

        ges_marker_list.connect("marker-added", self._marker_added_cb)
        ges_marker_list.connect("marker-removed", self._marker_removed_cb)
        ges_marker_list.connect("marker-moved", self._marker_moved_cb)

        ges_markers = ges_marker_list.get_markers()
        for ges_marker in ges_markers:
            self._connect(ges_marker)

    def _connect(self, ges_marker):
        marker_observer = MetaContainerObserver(ges_marker, self.action_log)
        self.marker_observers[ges_marker] = marker_observer

    def _marker_added_cb(self, ges_marker_list, position, ges_marker):
        action = MarkerAdded(ges_marker_list, ges_marker)
        self.action_log.push(action)
        self._connect(ges_marker)

    def _marker_removed_cb(self, ges_marker_list, ges_marker):
        action = MarkerRemoved(ges_marker_list, ges_marker)
        self.action_log.push(action)
        marker_observer = self.marker_observers.pop(ges_marker)
        marker_observer.release()

    def _marker_moved_cb(self, ges_marker_list, old_position, position, ges_marker):
        action = MarkerMoved(ges_marker_list, ges_marker, old_position)
        self.action_log.push(action)


# pylint: disable=abstract-method
class MarkerAction(UndoableAutomaticObjectAction):
    """Base class for marker actions."""

    def __init__(self, ges_marker_list, ges_marker):
        UndoableAutomaticObjectAction.__init__(self, ges_marker)
        self.ges_marker_list = ges_marker_list
        self.position = ges_marker.props.position
        self.ges_marker = ges_marker

    def add(self):
        """Adds a marker and updates the auto-object."""
        ges_marker = self.ges_marker_list.add(self.position)
        comment = self.auto_object.get_string("comment")
        if comment:
            ges_marker.set_string("comment", comment)
        UndoableAutomaticObjectAction.update_object(self.auto_object, ges_marker)

    def remove(self):
        """Removes the marker represented by the auto_object."""
        self.ges_marker_list.remove(self.auto_object)


class MarkerAdded(MarkerAction):
    """Action for added markers."""

    def do(self):
        self.add()

    def undo(self):
        self.remove()

    def as_scenario_action(self):
        st = Gst.Structure.new_empty("add-marker")
        return st


class MarkerRemoved(MarkerAction):
    """Action for removed markers."""

    def do(self):
        self.remove()

    def undo(self):
        self.add()

    def as_scenario_action(self):
        st = Gst.Structure.new_empty("remove-marker")
        return st


class MarkerMoved(UndoableAutomaticObjectAction):
    """Action for moved markers."""

    def __init__(self, ges_marker_list, ges_marker, old_position):
        UndoableAutomaticObjectAction.__init__(self, ges_marker)
        self.ges_marker_list = ges_marker_list
        self.new_position = ges_marker.props.position
        self.old_position = old_position

    def do(self):
        self.ges_marker_list.move(self.auto_object, self.new_position)

    def undo(self):
        self.ges_marker_list.move(self.auto_object, self.old_position)

    def as_scenario_action(self):
        st = Gst.Structure.new_empty("move-marker")
        return st

    def expand(self, action):
        if not isinstance(action, MarkerMoved):
            return False

        self.new_position = action.new_position
        return True
