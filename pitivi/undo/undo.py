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
"""Undo/redo."""
import contextlib

from gi.repository import GObject

from pitivi.utils.loggable import Loggable


class UndoError(Exception):
    """Base class for undo/redo exceptions."""
    pass


class UndoWrongStateError(UndoError):
    """Exception related to the current state of the undo/redo stack."""
    pass


class Action(GObject.Object, Loggable):
    """Something which might worth logging in a scenario."""

    def __init__(self):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

    def asScenarioAction(self):
        raise NotImplementedError()


class UndoableAction(Action):
    """An action that can be undone.

    When your object's state changes, create an UndoableAction to allow
    reverting the change later on.
    """

    def do(self):
        raise NotImplementedError()

    def undo(self):
        raise NotImplementedError()

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


class UndoableActionStack(UndoableAction):
    """A stack of UndoableAction objects.

    Attributes:
        action_group_name (str): The name of the operation.
        done_actions (List[UndoableAction]): The UndoableActions pushed in
            the stack.
        finalizing_action (FinalizingAction): The action to be performed
            at the end of undoing or redoing the stacked actions.
    """

    def __init__(self, action_group_name, finalizing_action=None):
        UndoableAction.__init__(self)
        self.action_group_name = action_group_name
        self.done_actions = []
        self.finalizing_action = finalizing_action

    def __repr__(self):
        return "%s: %s" % (self.action_group_name, self.done_actions)

    def push(self, action):
        if self.done_actions:
            last_action = self.done_actions[-1]
            if last_action.expand(action):
                # The action has been included in the previous one.
                return
        self.done_actions.append(action)

    def _run_action(self, actions, method_name):
        for action in actions:
            method = getattr(action, method_name)
            method()
        self.finish_operation()

    def do(self):
        self._run_action(self.done_actions, "do")

    def undo(self):
        self._run_action(self.done_actions[::-1], "undo")

    def finish_operation(self):
        if not self.finalizing_action:
            return
        self.finalizing_action.do()


class UndoableActionLog(GObject.Object, Loggable):
    """The undo/redo manager.

    A separate instance should be created for each Project instance.
    """

    __gsignals__ = {
        "begin": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "pre-push": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "push": (GObject.SIGNAL_RUN_LAST, None, (object, object)),
        "rollback": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "commit": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "move": (GObject.SIGNAL_RUN_LAST, None, (object,)),
    }

    def __init__(self):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self.undo_stacks = []
        self.redo_stacks = []
        self.stacks = []
        self.running = False
        self._checkpoint = self._takeSnapshot()

    @contextlib.contextmanager
    def started(self, action_group_name, finalizing_action=None):
        """Gets a context manager which commits the transaction at the end."""
        self.begin(action_group_name, finalizing_action)
        yield
        self.commit(action_group_name)

    def begin(self, action_group_name, finalizing_action=None):
        """Starts recording a high-level operation which later can be undone.

        The recording can be stopped by calling the `commit` method or
        canceled by calling the `rollback` method.

        The operation will be composed of all the actions which have been
        pushed and also of the committed sub-operations.
        """
        if self.running:
            self.debug("Abort because running")
            return

        stack = UndoableActionStack(action_group_name, finalizing_action)
        self.stacks.append(stack)
        self.debug("begin action group %s, nested %s",
                   stack.action_group_name, len(self.stacks))
        self.emit("begin", stack)

    def push(self, action):
        """Reports a change.

        Args:
            action (Action): The action representing the change.
                If it's an UndoableAction, it's added to the current
                operation, if any.
        """
        self.emit("pre-push", action)

        if not isinstance(action, UndoableAction):
            # Nothing else to do with it.
            return

        if self.running:
            self.debug("Ignore push because running: %s", action)
            return

        try:
            stack = self._get_last_stack()
        except UndoWrongStateError as e:
            self.warning("Failed pushing '%s' because: %s", action, e)
            return
        stack.push(action)
        self.debug("push action %s in action group %s",
                   action, stack.action_group_name)
        self.emit("push", stack, action)

    def rollback(self):
        """Forgets about the last started operation."""
        if self.running:
            self.debug("Ignore rollback because running")
            return

        self.debug("Rolling back")
        stack = self._get_last_stack(pop=True)
        self.debug("rollback action group %s, nested %s",
                   stack.action_group_name, len(self.stacks))
        self.emit("rollback", stack)
        stack.undo()

    def commit(self, action_group_name):
        """Commits the last started operation."""
        if self.running:
            self.debug("Ignore commit because running")
            return

        self.debug("Committing %s", action_group_name)
        stack = self._get_last_stack(pop=True)
        if action_group_name != stack.action_group_name:
            raise UndoWrongStateError("Unexpected commit", action_group_name, stack, self.stacks)
        if not stack.done_actions:
            self.debug("Ignore empty stack %s", stack.action_group_name)
            return
        if not self.stacks:
            self.undo_stacks.append(stack)
            stack.finish_operation()
        else:
            self.stacks[-1].push(stack)

        if self.redo_stacks:
            self.redo_stacks = []

        self.debug("commit action group %s nested %s",
                   stack.action_group_name, len(self.stacks))
        self.emit("commit", stack)

    def undo(self):
        """Undoes the last recorded operation."""
        if self.stacks:
            raise UndoWrongStateError("Recording a transaction", self.stacks)
        if not self.undo_stacks:
            raise UndoWrongStateError("Nothing to undo")

        stack = self.undo_stacks.pop(-1)
        self.debug("Undo %s", stack)
        self._run(stack.undo)
        self.redo_stacks.append(stack)
        self.emit("move", stack)

    def redo(self):
        """Redoes the last undone operation."""
        if self.stacks:
            raise UndoWrongStateError("Recording a transaction", self.stacks)
        if not self.redo_stacks:
            raise UndoWrongStateError("Nothing to redo")

        stack = self.redo_stacks.pop(-1)
        self.debug("Redo %s", stack)
        self._run(stack.do)
        self.undo_stacks.append(stack)
        self.emit("move", stack)

    def _takeSnapshot(self):
        return list(self.undo_stacks)

    def checkpoint(self):
        if self.stacks:
            raise UndoWrongStateError("Recording a transaction", self.stacks)

        self._checkpoint = self._takeSnapshot()

    def dirty(self):
        current_snapshot = self._takeSnapshot()
        return current_snapshot != self._checkpoint

    def _run(self, operation):
        self.running = True
        try:
            operation()
        finally:
            self.running = False

    def _get_last_stack(self, pop=False):
        try:
            if pop:
                stack = self.stacks.pop(-1)
            else:
                stack = self.stacks[-1]
        except IndexError:
            raise UndoWrongStateError("No transaction")

        return stack

    def is_in_transaction(self):
        """Gets whether currently recording an operation."""
        return bool(self.stacks)


class MetaChangedAction(UndoableAction):

    def __init__(self, meta_container, item, current_value, new_value):
        UndoableAction.__init__(self)
        self.meta_container = meta_container
        self.item = item
        self.old_value = current_value
        self.new_value = new_value

    def do(self):
        self.meta_container.set_meta(self.item, self.new_value)

    def undo(self):
        self.meta_container.set_meta(self.item, self.old_value)


class MetaContainerObserver(GObject.Object):
    """Monitor for MetaContainer changes.

    Attributes:
        meta_container (GES.MetaContainer): The object to be monitored.
        action_log (UndoableActionLog): The action log where to report actions.
    """

    def __init__(self, meta_container, action_log):
        self.meta_container = meta_container
        self.action_log = action_log

        self.metas = {}

        def set_meta(unused_meta_container, item, value):
            self.metas[item] = value
        meta_container.foreach(set_meta)

        meta_container.connect("notify-meta", self._notify_meta_cb)

    def _notify_meta_cb(self, meta_container, item, value):
        current_value = self.metas.get(item)
        action = MetaChangedAction(meta_container, item, current_value, value)
        self.metas[item] = value
        self.action_log.push(action)

    def release(self):
        self.meta_container.disconnect_by_func(self._notify_meta_cb)
        self.meta_container = None


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
