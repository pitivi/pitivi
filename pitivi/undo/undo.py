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

import weakref

from gi.repository import GObject

from pitivi.utils.loggable import Loggable


class UndoError(Exception):

    """ Any exception related to the undo/redo feature."""
    pass


class UndoWrongStateError(UndoError):

    """ Exception related to the current state of the undo/redo stack. """
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

    def clean(self):
        # Meant to be overridden by UndoableActionStack?
        pass

    def asScenarioAction(self):
        raise NotImplementedError()

    def _done(self):
        self.emit("done")

    def _undone(self):
        self.emit("undone")


class UndoableActionStack(UndoableAction):

    """
    Simply a stack of UndoableAction objects.
    """

    __gsignals__ = {
        "cleaned": (GObject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self, action_group_name):
        UndoableAction.__init__(self)
        self.action_group_name = action_group_name
        self.done_actions = []
        self.undone_actions = []
        self.actions = []

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

    def undo(self):
        self._runAction(self.done_actions, "undo")
        self.undone_actions = self.done_actions[::-1]
        self.emit("undone")

    def clean(self):
        actions = self.done_actions + self.undone_actions
        self.undone_actions = []
        self.done_actions = []
        self._runAction(actions, "clean")
        self.emit("cleaned")


class UndoableActionLog(GObject.Object, Loggable):

    """
    This is the "master" class that handles all the undo/redo system. There is
    only one instance of it in Pitivi: application.py's "action_log" property.
    """
    __gsignals__ = {
        "begin": (GObject.SIGNAL_RUN_LAST, None, (object, bool)),
        "push": (GObject.SIGNAL_RUN_LAST, None, (object, object)),
        "rollback": (GObject.SIGNAL_RUN_LAST, None, (object, bool)),
        "commit": (GObject.SIGNAL_RUN_LAST, None, (object, bool)),
        "undo": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "redo": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "cleaned": (GObject.SIGNAL_RUN_LAST, None, ()),
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

    def begin(self, action_group_name):
        self.debug("Beginning %s", action_group_name)
        if self.running:
            self.debug("Abort because already running")
            return

        stack = UndoableActionStack(action_group_name)
        nested = self._stackIsNested(stack)
        self.stacks.append(stack)
        self.debug("begin action group %s, nested %s",
                   stack.action_group_name, nested)
        self.emit("begin", stack, nested)

    def push(self, action):
        self.debug("Pushing %s", action)

        try:
            if action is not None:
                st = action.asScenarioAction()
                if self.app is not None and st is not None:
                    self.app.write_action(st)
        except NotImplementedError:
            self.warning("No serialization method for that action")

        if self.running:
            self.debug("Abort because already running")
            return

        try:
            stack = self._getTopmostStack()
        except UndoWrongStateError:
            return

        stack.push(action)
        self.debug("push action %s in action group %s",
                   action, stack.action_group_name)
        self.emit("push", stack, action)

    def rollback(self):
        self.debug("Rolling back")
        if self.running:
            self.debug("Abort because already running")
            return

        stack = self._getTopmostStack(pop=True)
        if stack is None:
            return
        nested = self._stackIsNested(stack)
        self.debug("rollback action group %s, nested %s",
                   stack.action_group_name, nested)
        self.emit("rollback", stack, nested)
        stack.undo()

    def commit(self):
        self.debug("Committing")
        if self.running:
            self.debug("Abort because already running")
            return

        stack = self._getTopmostStack(pop=True)
        if stack is None:
            return
        nested = self._stackIsNested(stack)
        if not self.stacks:
            self.undo_stacks.append(stack)
        else:
            self.stacks[-1].push(stack)

        if self.redo_stacks:
            self.redo_stacks = []

        self.debug("commit action group %s nested %s",
                   stack.action_group_name, nested)
        self.emit("commit", stack, nested)

    def undo(self):
        if self.stacks or not self.undo_stacks:
            raise UndoWrongStateError()

        stack = self.undo_stacks.pop(-1)
        self._runStack(stack, stack.undo)
        self.redo_stacks.append(stack)
        self.emit("undo", stack)

    def redo(self):
        if self.stacks or not self.redo_stacks:
            raise UndoWrongStateError()

        stack = self.redo_stacks.pop(-1)
        self._runStack(stack, stack.do)
        self.undo_stacks.append(stack)
        self.emit("redo", stack)

    def clean(self):
        stacks = self.redo_stacks + self.undo_stacks
        self.redo_stacks = []
        self.undo_stacks = []

        for stack in stacks:
            self._runStack(stack, stack.clean)
        self.emit("cleaned")

    def _takeSnapshot(self):
        return list(self.undo_stacks)

    def checkpoint(self):
        if self.stacks:
            raise UndoWrongStateError()

        self._checkpoint = self._takeSnapshot()

    def dirty(self):
        current_snapshot = self._takeSnapshot()
        return current_snapshot != self._checkpoint

    def _runStack(self, unused_stack, run):
        self.running = True
        try:
            run()
        finally:
            self.running = False

    def _getTopmostStack(self, pop=False):
        stack = None
        try:
            if pop:
                stack = self.stacks.pop(-1)
            else:
                stack = self.stacks[-1]
        except IndexError:
            raise UndoWrongStateError()

        return stack

    def _stackIsNested(self, unused_stack):
        return bool(len(self.stacks))


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
