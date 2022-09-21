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
import contextlib

from gi.repository import GObject

from pitivi.undo.base import ConditionsNotReadyYetError
from pitivi.undo.base import UndoableAction
from pitivi.undo.base import UndoError
from pitivi.undo.base import UndoWrongStateError
from pitivi.utils.loggable import Loggable


class UndoableActionStack(UndoableAction, Loggable):
    """A stack of UndoableAction objects.

    Attributes:
        action_group_name (str): The name of the operation.
        done_actions (List[UndoableAction]): The UndoableActions pushed in
            the stack.
        mergeable (bool): Whether this stack accepts merges with other
            compatible stacks.
        finalizing_action (FinalizingAction): The action to be performed
            at the end of undoing or redoing the stacked actions.
    """

    def __init__(self, action_group_name, mergeable, finalizing_action=None):
        UndoableAction.__init__(self)
        Loggable.__init__(self)
        self.action_group_name = action_group_name
        self.done_actions = []
        self.mergeable = mergeable
        self.finalizing_action = finalizing_action

    def __len__(self):
        return len(self.done_actions)

    def __repr__(self):
        return "%s: %s" % (self.action_group_name, self.done_actions)

    def attempt_merge(self, stack, action):
        """Merges the action into the previous one if possible.

        Returns:
            bool: Whether the merge has been done.
        """
        if not self.mergeable:
            return False

        if not self.done_actions:
            return False

        if not self.action_group_name == stack.action_group_name:
            return False

        return self.attempt_expand_action(action)

    def attempt_expand_action(self, action):
        """Expands the last action with the specified action if possible."""
        if not self.done_actions:
            return False

        last_action = self.done_actions[-1]
        return last_action.expand(action)

    def push(self, action):
        """Adds an action unless it's possible to expand the previous."""
        if self.attempt_expand_action(action):
            # The action has been merged into the last one.
            return

        self.done_actions.append(action)

    def _perform_actions(self, actions, method_name):
        delayed_actions = []
        delayed_reasons = {}
        for action in actions:
            self.log("Performing %s.%s()", action, method_name)
            method = getattr(action, method_name)
            try:
                method()
                for delayed_action in list(delayed_actions):
                    self.log("Performing delayed %s.%s()", action, method_name)
                    delayed_method = getattr(delayed_action, method_name)
                    try:
                        delayed_method()
                        self.log("Succeeded performing action")
                        delayed_actions.remove(delayed_action)
                        delayed_reasons.pop(delayed_action)
                    except ConditionsNotReadyYetError:
                        self.log("Further delaying action")
            except ConditionsNotReadyYetError as e:
                self.log("Delaying action")
                delayed_actions.append(action)
                delayed_reasons[action] = e
        if delayed_actions:
            raise UndoError("Delayable actions failed to apply: {} {}".format(delayed_actions, delayed_reasons))
        self.finish_operation()

    def do(self):
        self._perform_actions(self.done_actions, "do")

    def undo(self):
        self._perform_actions(self.done_actions[::-1], "undo")

    def finish_operation(self):
        if not self.finalizing_action:
            return
        self.finalizing_action.do()


class UndoableActionLog(GObject.Object, Loggable):
    """The undo/redo manager.

    A separate instance should be created for each Project instance.
    """

    __gsignals__ = {
        "begin": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "pre-push": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "push": (GObject.SignalFlags.RUN_LAST, None, (object, object)),
        "rollback": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "commit": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "move": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self.undo_stacks = []
        self.redo_stacks = []
        self.stacks = []
        self.running = False
        self.rolling_back = False
        self._checkpoint = self._take_snapshot()

    @contextlib.contextmanager
    def started(self, action_group_name, **kwargs):
        """Gets a context manager which commits the transaction at the end."""
        self.begin(action_group_name, **kwargs)
        try:
            yield
        except:
            self.warning("An exception occurred while recording a "
                         "high-level operation. Rolling back.")
            self.rollback()
            raise
        else:
            self.commit(action_group_name)

    def begin(self, action_group_name, finalizing_action=None, mergeable=False, toplevel=False):
        """Starts recording a high-level operation which later can be undone.

        The recording can be stopped by calling the `commit` method or
        canceled by calling the `rollback` method.

        The operation will be composed of all the actions which have been
        pushed and also of the committed sub-operations.

        Args:
            action_group_name (str): The name of the operation.
            finalizing_action (FinalizingAction): The action to be performed
                at the end of undoing or redoing the stacked actions.
            mergeable (bool): Whether this stack accepts merges with future
                compatible stacks.
            toplevel (bool): If true, throws error if this operation is
                started while another one is being recorded.
        """
        if self.running:
            self.debug("Abort because running")
            return

        if toplevel and self.is_in_transaction():
            raise UndoWrongStateError("Toplevel operation started as suboperation", self.stacks)

        stack = UndoableActionStack(action_group_name, mergeable, finalizing_action)
        self.stacks.append(stack)
        self.debug("begin action group %s, nested %s",
                   stack.action_group_name, len(self.stacks))
        self.emit("begin", stack)

    def push(self, action):
        """Records a change noticed by the monitoring system.

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

        if self.rolling_back:
            self.debug("Ignore push because rolling back: %s", action)
            return

        try:
            stack = self._get_last_stack()
        except UndoWrongStateError as e:
            self.warning("Failed pushing '%s' because no transaction started: %s", action, e)
            return

        merged = False
        if stack.mergeable and len(self.stacks[0]) == 0 and self.undo_stacks:
            # The current undoable operation is empty, this is the first action.
            # Check if it can be merged with the previous operation.
            previous_operation = self.undo_stacks[-1]
            if previous_operation.attempt_merge(stack, action):
                self.debug("Merging undoable operations")
                self.stacks = [self.undo_stacks.pop()]
                merged = True

        if not merged:
            stack.push(action)
            self.debug("push action %s in action group %s",
                       action, stack.action_group_name)

        self.emit("push", stack, action)

    def rollback(self, undo=True):
        """Forgets about the last started operation.

        Args:
            undo (bool): Whether to undo the last started operation.
                If False, it's disregarded without any action.
        """
        if self.running:
            self.debug("Ignore rollback because running")
            return

        self.debug("Rolling back, undo=%s", undo)
        self.rolling_back = True
        try:
            stack = self._get_last_stack(pop=True)
            self.debug("rollback action group %s, nested %s",
                       stack.action_group_name, len(self.stacks))
            self.emit("rollback", stack)
            if undo:
                stack.undo()
        finally:
            self.rolling_back = False

    def try_rollback(self, action_group_name):
        """Do rollback if the last started operation is @action_group_name."""
        try:
            last_operation = self._get_last_stack().action_group_name
        except UndoWrongStateError:
            return

        if last_operation == action_group_name:
            self.rollback()

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

    def _take_snapshot(self):
        return list(self.undo_stacks)

    def checkpoint(self):
        if self.stacks:
            raise UndoWrongStateError("Recording a transaction", self.stacks)

        self._checkpoint = self._take_snapshot()

    def dirty(self):
        current_snapshot = self._take_snapshot()
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
        except IndexError as e:
            raise UndoWrongStateError("No transaction") from e

        return stack

    def is_in_transaction(self):
        """Gets whether currently recording an operation."""
        return bool(self.stacks)

    def has_assets_operations(self):
        """Checks whether user added/removed assets while working on the project."""
        for stack in self.undo_stacks:
            if stack.action_group_name in ["assets-addition", "assets-removal"]:
                return True
        return False
