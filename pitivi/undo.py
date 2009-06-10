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
        "error": ["exception"]
    }

    def do(self):
        raise NotImplementedError()

    def undo(self):
        raise NotImplementedError()

    def _done(self):
        self.emit("done")

    def _undone(self):
        self.emit("undone")

    def _error(self, exception):
        self.emit("error", exception)

class UndoableActionStack(UndoableAction):
    __signals__ = {
        "done": [],
        "undone": [],
        "error": ["exception"],
    }

    def __init__(self, action_group_name):
        self.action_group_name = action_group_name
        self.done_actions = []
        self.undone_actions = []
        self.actions = []

    def push(self, action):
        self.done_actions.append(action)

    def _runAction(self, action_list, methodName, signalName,
            continueCallback, finishCallback):
        try:
            action = action_list.pop(-1)
        except IndexError:
            finishCallback()
            return

        if action_list is self.done_actions:
            self.undone_actions.append(action)
        else:
            self.done_actions.append(action)

        self._connectToAction(action, action_list,
                signalName, continueCallback, finishCallback)

        method = getattr(action, methodName)
        try:
            method()
        except Exception, e:
            self._actionErrorCb(action, e, finishCallback)

    def do(self):
        self._runAction(self.undone_actions, "do", "done",
                continueCallback=self.do, finishCallback=self._done)

    def undo(self):
        self._runAction(self.done_actions, "undo", "undone",
                continueCallback=self.undo, finishCallback=self._undone)

    def _connectToAction(self, action, action_list, signalName,
            continueCallback, finishCallback):
        action.connect(signalName, self._actionDoneOrUndoneCb,
                action_list, continueCallback, finishCallback)
        action.connect("error", self._actionErrorCb, finishCallback)

    def _disconnectFromAction(self, action):
        action.disconnect_by_func(self._actionDoneOrUndoneCb)
        action.disconnect_by_func(self._actionErrorCb)

    def _actionDoneOrUndoneCb(self, action, action_list,
            continueCallback, finishCallback):
        self._disconnectFromAction(action)

        if not action_list:
            finishCallback()
            return

        continueCallback()

    def _actionErrorCb(self, action, exception, finishCallback):
        self._disconnectFromAction(action)

        self._error(exception)

    def _done(self):
        self.emit("done")

    def _undone(self):
        self.emit("undone")

    def _error(self, exception):
        self.emit("error", exception)

class UndoableActionLog(Signallable):
    __signals__ = {
        "begin": ["stack", "nested"],
        "push": ["stack", "action"],
        "rollback": ["stack", "nested"],
        "commit": ["stack", "nested"],
        "undo": ["stack"],
        "redo": ["stack"],
        "can-undo": ["bool"],
        "can-redo": ["bool"],
        "error": ["exception"]
    }
    def __init__(self):
        self.undo_stacks = []
        self.redo_stacks = []
        self.stacks = []
        self.running = False

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

        stack = self._getTopmostStack()
        if stack is None:
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
            self.emit("can-undo", True)
        else:
            self.stacks[-1].push(stack)

        self.emit("commit", stack, nested)

    def undo(self):
        if self.stacks or not self.undo_stacks:
            self._error(UndoWrongStateError())
            return

        stack = self.undo_stacks.pop(-1)
        if not self.undo_stacks:
            self.emit("can-undo", False)

        self._runStack(stack, stack.undo)

        self.redo_stacks.append(stack)
        self.emit("undo", stack)
        self.emit("can-redo", True)

    def redo(self):
        if self.stacks or not self.redo_stacks:
            return self._error(UndoWrongStateError())

        stack = self.redo_stacks.pop(-1)
        if not self.redo_stacks:
            self.emit("can-redo", False)

        self._runStack(stack, stack.do)
        self.undo_stacks.append(stack)
        self.emit("redo", stack)
        self.emit("can-undo", True)

    def _runStack(self, stack, run):
        self._connectToRunningStack(stack)
        self.running = True
        run()

    def _connectToRunningStack(self, stack):
        stack.connect("done", self._stackDoneCb)
        stack.connect("undone", self._stackUndoneCb)
        stack.connect("error", self._stackErrorCb)

    def _disconnectFromRunningStack(self, stack):
        for method in (self._stackDoneCb, self._stackUndoneCb,
                self._stackErrorCb):
            stack.disconnect_by_func(method)

    def _stackDoneCb(self, stack):
        self.running = False
        self._disconnectFromRunningStack(stack)

    def _stackUndoneCb(self, stack):
        self.running = False
        self._disconnectFromRunningStack(stack)

    def _stackErrorCb(self, stack, exception):
        self.running = False
        self._disconnectFromRunningStack(stack)

        self.emit("error", exception)

    def _getTopmostStack(self, pop=False):
        stack = None
        try:
            if pop:
                stack = self.stacks.pop(-1)
            else:
                stack = self.stacks[-1]
        except IndexError:
            return self._error(UndoWrongStateError())

        return stack

    def _stackIsNested(self, stack):
        return bool(len(self.stacks))

    def _error(self, exception):
        self.emit("error", exception)

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
        log.connect("error", self._actionLogErrorCb)

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

    def _actionLogErrorCb(self, log, exception):
        self.warning("error %r: %s", exception, exception)
