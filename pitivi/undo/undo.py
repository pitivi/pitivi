# Pitivi video editor
#
#       pitivi/undo/undo.py
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
"""
Base classes for undo/redo.
"""
import contextlib
import weakref

from gi.repository import GObject

from pitivi.utils.loggable import Loggable


class UndoError(Exception):
    """
    Base class for undo/redo exceptions.
    """
    pass


class UndoWrongStateError(UndoError):
    """
    Exception related to the current state of the undo/redo stack.
    """
    pass


class UndoableAction(GObject.Object, Loggable):
    """
    An action that can be undone.
    In other words, when your object's state changes, create an UndoableAction
    to allow reverting the change if needed later on.
    """

    __gsignals__ = {
        "done": (GObject.SIGNAL_RUN_LAST, None, ()),
        "undone": (GObject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

    def do(self):
        raise NotImplementedError()

    def undo(self):
        raise NotImplementedError()

    def asScenarioAction(self):
        raise NotImplementedError()

    def _done(self):
        self.emit("done")

    def _undone(self):
        self.emit("undone")


class FinalizingAction:
    """
    Base class for actions to happen when an UndoableActionStack is
    done or undone.
    """
    def do(self):
        raise NotImplementedError()


class UndoableActionStack(UndoableAction):
    """
    Simply a stack of UndoableAction objects.
    """

    def __init__(self, action_group_name, finalizing_action=None):
        UndoableAction.__init__(self)
        self.action_group_name = action_group_name
        self.done_actions = []
        self.undone_actions = []
        self.finalizing_action = finalizing_action

    def __repr__(self):
        return "%s: %s" % (self.action_group_name, self.done_actions)

    def push(self, action):
        self.done_actions.append(action)

    def _runAction(self, action_list, method_name):
        for action in action_list[::-1]:
            method = getattr(action, method_name)
            method()

    def do(self):
        self._runAction(self.undone_actions, "do")
        self.done_actions = self.undone_actions[::-1]
        self.emit("done")

        if self.finalizing_action:
            self.finalizing_action.do()

    def undo(self):
        self._runAction(self.done_actions, "undo")
        self.undone_actions = self.done_actions[::-1]
        self.emit("undone")

        if self.finalizing_action:
            self.finalizing_action.do()


class UndoableActionLog(GObject.Object, Loggable):
    """
    The undo/redo manager.

    A separate instance should be created for each Project instance.
    """

    __gsignals__ = {
        "begin": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "push": (GObject.SIGNAL_RUN_LAST, None, (object, object)),
        "rollback": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "commit": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "undo": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "redo": (GObject.SIGNAL_RUN_LAST, None, (object,)),
    }

    def __init__(self, app=None):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        if app is not None:
            self.app = weakref.proxy(app)
        else:
            self.app = None
        self.undo_stacks = []
        self.redo_stacks = []
        self.stacks = []
        self.running = False
        self._checkpoint = self._takeSnapshot()

    @contextlib.contextmanager
    def started(self, action_group_name, finalizing_action=None):
        """
        Returns a context manager which commits the transaction at the end.
        """
        self.begin(action_group_name, finalizing_action)
        yield
        self.commit()

    def begin(self, action_group_name, finalizing_action=None):
        """
        Starts a transaction aka a high-level operation.
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
        """
        Adds an action to the current transaction.
        """
        if action is not None:
            try:
                st = action.asScenarioAction()
                if self.app is not None and st is not None:
                    self.app.write_action(st)
            except NotImplementedError:
                self.warning("No serialization method for that action")

        if self.running:
            self.debug("Ignore push because running")
            return

        try:
            stack = self._get_last_stack()
        except UndoWrongStateError as e:
            self.debug("Ignore push because %s", e)
            return
        stack.push(action)
        self.debug("push action %s in action group %s",
                   action, stack.action_group_name)
        self.emit("push", stack, action)

    def rollback(self):
        """
        Forgets about the last started transaction.
        """
        if self.running:
            self.debug("Ignore rollback because running")
            return

        self.debug("Rolling back")
        stack = self._get_last_stack(pop=True)
        self.debug("rollback action group %s, nested %s",
                   stack.action_group_name, len(self.stacks))
        self.emit("rollback", stack)
        stack.undo()

    def commit(self):
        """
        Commits the last started transaction.
        """
        if self.running:
            self.debug("Ignore commit because running")
            return

        self.debug("Committing")
        stack = self._get_last_stack(pop=True)
        if not self.stacks:
            self.undo_stacks.append(stack)
        else:
            self.stacks[-1].push(stack)

        if self.redo_stacks:
            self.redo_stacks = []

        self.debug("commit action group %s nested %s",
                   stack.action_group_name, len(self.stacks))
        self.emit("commit", stack)

    def undo(self):
        """
        Undo the last recorded operation.
        """
        if self.stacks:
            raise UndoWrongStateError("Recording a transaction", self.stacks)
        if not self.undo_stacks:
            raise UndoWrongStateError("Nothing to undo")

        stack = self.undo_stacks.pop(-1)
        self._run(stack.undo)
        self.redo_stacks.append(stack)
        self.emit("undo", stack)

    def redo(self):
        """
        Redo the last undone operation.
        """
        if self.stacks:
            raise UndoWrongStateError("Recording a transaction", self.stacks)
        if not self.redo_stacks:
            raise UndoWrongStateError("Nothing to redo")

        stack = self.redo_stacks.pop(-1)
        self._run(stack.do)
        self.undo_stacks.append(stack)
        self.emit("redo", stack)

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
        """
        Whether currently recording an operation.
        """
        return bool(self.stacks)


class PropertyChangeTracker(GObject.Object):
    """
    BaseClass to track a class property, Used for undo/redo
    """

    __gsignals__ = {
        "monitored-property-changed": (GObject.SIGNAL_RUN_LAST, None, (object, str, object, object)),
    }

    # The properties monitored by this class
    property_names = []

    def __init__(self):
        GObject.Object.__init__(self)
        self.properties = {}
        self.obj = None

    def connectToObject(self, obj):
        self.obj = obj
        self.properties = self._takeCurrentSnapshot(obj)
        # Connect to obj to keep track when the monitored properties
        # are changed.
        for property_name in self.property_names:
            signal_name = "notify::%s" % property_name
            obj.connect(signal_name, self._propertyChangedCb, property_name)

    @classmethod
    def _takeCurrentSnapshot(cls, obj):
        properties = {}
        for property_name in cls.property_names:
            properties[property_name] = obj.get_property(
                property_name.replace("-", "_"))

        return properties

    def disconnectFromObject(self, obj):
        self.obj = None
        obj.disconnect_by_func(self._propertyChangedCb)

    def _propertyChangedCb(self, object, property_value, property_name):
        old_value = self.properties[property_name]
        self.properties[property_name] = property_value
        self.emit("monitored-property-changed", object,
                  property_name, old_value, property_value)
