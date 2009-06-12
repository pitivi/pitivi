# PiTiVi , Non-linear video editor
#
#       tests/test_undo.py
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

from unittest import TestCase

from pitivi.undo import UndoError, UndoWrongStateError, UndoableAction, \
        UndoableActionStack, UndoableActionLog

class DummyUndoableAction(UndoableAction):
    done_ = True

    def do(self):
        self.done_ = True
        self._done()

    def undo(self):
        self.done_ = False
        self._undone()

class TestUndoableAction(TestCase):
    def testSimpleSignals(self):
        """
        Test signal emission from _done() and _undone().
        """
        state = {"done": False}
        def doneCb(action, val):
            state["done"] = val

        action = DummyUndoableAction()
        action.connect("done", doneCb, True)
        action.connect("undone", doneCb, False)

        action.undo()
        self.failIf(state["done"])

        action.do()
        self.failUnless(state["done"])


class TestUndoableActionStack(TestCase):
    def testDoUndoEmpty(self):
        """
        Undo an empty stack.
        """
        state = {"done": True}
        def doneCb(action, value):
            state["done"] = value

        stack = UndoableActionStack("meh")
        stack.connect("done", doneCb, True)
        stack.connect("undone", doneCb, False)

        stack.undo()
        self.failIf(state["done"])

        stack.do()
        self.failUnless(state["done"])

    def testUndoDo(self):
        """
        Test an undo() do() sequence.
        """
        state = {"done": True, "actions": 2}
        def doneCb(action, value):
            state["done"] = value

        state["done"] = 2
        class Action(UndoableAction):
            def do(self):
                state["actions"] += 1
                self._done()

            def undo(self):
                state["actions"] -= 1
                self._undone()

        stack = UndoableActionStack("meh")
        stack.connect("done", doneCb, True)
        stack.connect("undone", doneCb, False)
        action1 = Action()
        action2 = Action()
        stack.push(action1)
        stack.push(action2)

        stack.undo()
        self.failUnlessEqual(state["actions"], 0)
        self.failIf(state["done"])

        stack.do()
        self.failUnlessEqual(state["actions"], 2)
        self.failUnless(state["done"])

    def testUndoError(self):
        """
        Undo a stack containing a failing action.
        """
        state = {"done": True}
        def doneCb(action, value):
            state["done"] = value

        state["actions"] = 2
        class Action(UndoableAction):
            def undo(self):
                state["actions"] -= 1
                if state["actions"] == 1:
                    self.__class__.undo = self.__class__.undo_fail

                self._undone()

            def undo_fail(self):
                raise UndoError("meh")

        stack = UndoableActionStack("meh")
        stack.connect("done", doneCb)
        action1 = Action()
        action2 = Action()
        stack.push(action1)
        stack.push(action2)

        self.failUnlessRaises(UndoError, stack.undo)
        self.failUnlessEqual(state["actions"], 1)
        self.failUnless(state["done"])


class TestUndoableActionLog(TestCase):
    def setUp(self):
        self.log = UndoableActionLog()
        self._connectToUndoableActionLog(self.log)
        self.signals = []

    def tearDown(self):
        self._disconnectFromUndoableActionLog(self.log)

    def _undoActionLogSignalCb(self, log, *args):
        args = list(args)
        signalName = args.pop(-1)
        self.signals.append((signalName, args))

    def _connectToUndoableActionLog(self, log):
        for signalName in ("begin", "push", "rollback", "commit",
                    "undo", "redo"):
            log.connect(signalName, self._undoActionLogSignalCb, signalName)

    def _disconnectFromUndoableActionLog(self, log):
        self.log.disconnect_by_func(self._undoActionLogSignalCb)

    def testRollbackWrongState(self):
        self.failUnlessRaises(UndoWrongStateError, self.log.rollback)

    def testCommitWrongState(self):
        self.failUnlessRaises(UndoWrongStateError, self.log.commit)

    def testPushWrongState(self):
        # no error in this case
        self.log.push(None)

    def testUndoWrongState(self):
        self.failUnlessRaises(UndoWrongStateError, self.log.undo)

    def testRedoWrongState(self):
        self.failUnlessRaises(UndoWrongStateError, self.log.redo)

    def testCheckpoint(self):
        self.log.begin("meh")
        self.log.push(DummyUndoableAction())
        self.failUnlessRaises(UndoWrongStateError, self.log.checkpoint)
        self.log.rollback()
        self.log.checkpoint()
        self.failIfEqual(self.log._checkpoint, None)

    def testDirty(self):
        self.failIf(self.log.dirty())
        self.log.begin("meh")
        self.log.push(DummyUndoableAction())
        self.log.commit()
        self.failUnless(self.log.dirty())
        self.log.checkpoint()
        self.failIf(self.log.dirty())
        self.log.undo()
        self.failUnless(self.log.dirty())
        self.log.redo()
        self.failIf(self.log.dirty())

    def testCommit(self):
        """
        Commit a stack.
        """
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.failUnlessEqual(len(self.signals), 1)
        name, (stack, nested) = self.signals[0]
        self.failUnlessEqual(name, "begin")
        self.failIf(nested)

        self.failUnlessEqual(self.log.undo_stacks, [])
        self.log.commit()
        self.failUnlessEqual(len(self.signals), 2)
        name, (stack, nested) = self.signals[1]
        self.failUnlessEqual(name, "commit")
        self.failIf(nested)
        self.failUnlessEqual(len(self.log.undo_stacks), 1)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)

    def testNestedCommit(self):
        """
        Do two nested commits.
        """
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.failUnlessEqual(len(self.signals), 1)
        name, (stack, nested) = self.signals[0]
        self.failUnlessEqual(name, "begin")
        self.failIf(nested)

        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)
        self.log.begin("nested")
        self.failUnlessEqual(len(self.signals), 2)
        name, (stack, nested) = self.signals[1]
        self.failUnlessEqual(name, "begin")
        self.failUnless(nested)

        self.failUnlessEqual(self.log.undo_stacks, [])
        self.log.commit()
        self.failUnlessEqual(len(self.signals), 3)
        name, (stack, nested) = self.signals[2]
        self.failUnlessEqual(name, "commit")
        self.failUnless(nested)
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)

        self.failUnlessEqual(self.log.undo_stacks, [])
        self.log.commit()
        self.failUnlessEqual(len(self.signals), 4)
        name, (stack, nested) = self.signals[3]
        self.failUnlessEqual(name, "commit")
        self.failIf(nested)
        self.failUnlessEqual(len(self.log.undo_stacks), 1)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)

    def testRollback(self):
        """
        Test a rollback.
        """
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.failUnlessEqual(len(self.signals), 1)
        name, (stack, nested) = self.signals[0]
        self.failUnlessEqual(name, "begin")
        self.failIf(nested)

        self.log.rollback()
        self.failUnlessEqual(len(self.signals), 2)
        name, (stack, nested) = self.signals[1]
        self.failUnlessEqual(name, "rollback")
        self.failIf(nested)
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)

    def testNestedRollback(self):
        """
        Test two nested rollbacks.
        """
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.failUnlessEqual(len(self.signals), 1)
        name, (stack, nested) = self.signals[0]
        self.failUnlessEqual(name, "begin")
        self.failIf(nested)

        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)
        self.log.begin("nested")
        self.failUnlessEqual(len(self.signals), 2)
        name, (stack, nested) = self.signals[1]
        self.failUnlessEqual(name, "begin")
        self.failUnless(nested)

        self.log.rollback()
        self.failUnlessEqual(len(self.signals), 3)
        name, (stack, nested) = self.signals[2]
        self.failUnlessEqual(name, "rollback")
        self.failUnless(nested)
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)

        self.log.rollback()
        self.failUnlessEqual(len(self.signals), 4)
        name, (stack, nested) = self.signals[3]
        self.failUnlessEqual(name, "rollback")
        self.failIf(nested)
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)

    def testUndoRedo(self):
        """
        Try an undo() redo() sequence.
        """
        # begin
        self.log.begin("meh")
        self.failUnlessEqual(len(self.signals), 1)
        name, (stack, nested) = self.signals[0]
        self.failUnlessEqual(name, "begin")
        self.failIf(nested)

        # push two actions
        action1 = DummyUndoableAction()
        self.log.push(action1)
        self.failUnlessEqual(len(self.signals), 2)
        name, (stack, signalAction) = self.signals[1]
        self.failUnlessEqual(name, "push")
        self.failUnless(action1 is signalAction)

        action2 = DummyUndoableAction()
        self.log.push(action2)
        self.failUnlessEqual(len(self.signals), 3)
        name, (stack, signalAction) = self.signals[2]
        self.failUnlessEqual(name, "push")
        self.failUnless(action2 is signalAction)

        # commit
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)
        self.log.commit()
        self.failUnlessEqual(len(self.signals), 4)
        name, (stack, nested) = self.signals[3]
        self.failUnlessEqual(name, "commit")
        self.failIf(nested)
        self.failUnlessEqual(len(self.log.undo_stacks), 1)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)

        self.failUnless(action1.done_)
        self.failUnless(action2.done_)

        # undo what we just committed
        self.log.undo()
        self.failUnlessEqual(len(self.signals), 5)
        name, stack = self.signals[4]
        self.failUnlessEqual(name, "undo")
        self.failUnlessEqual(len(self.log.undo_stacks), 0)
        self.failUnlessEqual(len(self.log.redo_stacks), 1)

        self.failIf(action1.done_)
        self.failIf(action2.done_)

        # redo
        self.log.redo()
        self.failUnlessEqual(len(self.signals), 6)
        name, stack = self.signals[5]
        self.failUnlessEqual(name, "redo")
        self.failUnlessEqual(len(self.log.undo_stacks), 1)
        self.failUnlessEqual(len(self.log.redo_stacks), 0)

        self.failUnless(action1.done_)
        self.failUnless(action2.done_)

    def testOrder(self):
        """
        Test that actions are undone and redone in the correct order.
        """
        call_sequence = []
        class Action(UndoableAction):
            def __init__(self, n):
                self.n = n

            def do(self):
               call_sequence.append("do%s" % self.n)
               self._done()

            def undo(self):
               call_sequence.append("undo%s" % self.n)
               self._undone()

        action1 = Action(1)
        action2 = Action(2)
        action3 = Action(3)

        self.log.begin("meh")
        self.log.push(action1)
        self.log.begin("nested")
        self.log.push(action2)
        self.log.commit()
        self.log.push(action3)
        self.log.commit()

        self.log.undo()
        self.failUnlessEqual(call_sequence, ["undo3", "undo2", "undo1"])

        call_sequence[:] = []
        self.log.redo()
        self.failUnlessEqual(call_sequence, ["do1", "do2", "do3"])

        call_sequence[:] = []
        self.log.undo()
        self.failUnlessEqual(call_sequence, ["undo3", "undo2", "undo1"])

