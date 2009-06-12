# PiTiVi , Non-linear video editor
#
#       pitivi/undo.py
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable

class UndoError(Exception):
    pass

class UndoWrongStateError(UndoError):
    pass

class UndoableAction(Signallable):
    __signals__ = {
        "done": [],
        "undone": [],
        "undone": [],
    }

    def do(self):
        raise NotImplementedError()

    def undo(self):
        raise NotImplementedError()

    def clean(self):
        pass

    def _done(self):
        self.emit("done")

    def _undone(self):
        self.emit("undone")

class UndoableActionStack(UndoableAction):
    __signals__ = {
        "done": [],
        "undone": [],
        "cleaned": [],
    }

    def __init__(self, action_group_name):
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


class UndoableActionLog(Signallable):
    __signals__ = {
        "begin": ["stack", "nested"],
        "push": ["stack", "action"],
        "rollback": ["stack", "nested"],
        "commit": ["stack", "nested"],
        "undo": ["stack"],
        "redo": ["stack"],
        "cleaned": [],
    }
    def __init__(self):
        self.undo_stacks = []
        self.redo_stacks = []
        self.stacks = []
        self.running = False
        self._checkpoint = self._takeSnapshot()

    def begin(self, action_group_name):
        if self.running:
            return

        stack = UndoableActionStack(action_group_name)
        nested = self._stackIsNested(stack)
        self.stacks.append(stack)
        self.emit("begin", stack, nested)

    def push(self, action):
        if self.running:
            return

        try:
            stack = self._getTopmostStack()
        except UndoWrongStateError:
            return

        stack.push(action)
        self.emit("push", stack, action)

    def rollback(self):
        if self.running:
            return

        stack = self._getTopmostStack(pop=True)
        if stack is None:
            return
        nested = self._stackIsNested(stack)
        self.emit("rollback", stack, nested)
        stack.undo()

    def commit(self):
        if self.running:
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

    def _runStack(self, stack, run):
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

    def _stackIsNested(self, stack):
        return bool(len(self.stacks))

class DebugActionLogObserver(Loggable):
    def startObserving(self, log):
        self._connectToActionLog(log)

    def stopObserving(self, log):
        self._disconnectFromActionLog(log)

    def _connectToActionLog(self, log):
        log.connect("begin", self._actionLogBeginCb)
        log.connect("commit", self._actionLogCommitCb)
        log.connect("rollback", self._actionLogRollbackCb)
        log.connect("push", self._actionLogPushCb)

    def _disconnectFromActionLog(self, log):
        for method in (self._actionLogBeginCb, self._actionLogCommitCb,
                self._actionLogrollbackCb, self._actionLogPushCb):
            log.disconnect_by_func(method)

    def _actionLogBeginCb(self, log, stack, nested):
        self.debug("begin action %s nested %s",
                stack.action_group_name, nested)

    def _actionLogCommitCb(self, log, stack, nested):
        self.debug("commit action %s nested %s",
                stack.action_group_name, nested)

    def _actionLogRollbackCb(self, log, stack, nested):
        self.debug("rollback action %s nested %s",
                stack.action_group_name, nested)

    def _actionLogPushCb(self, log, stack, action):
        self.debug("push %s in %s", action, stack.action_group_name)
