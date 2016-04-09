# Pitivi video editor
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
from unittest import TestCase

from pitivi.undo.undo import UndoableAction
from pitivi.undo.undo import UndoableActionLog
from pitivi.undo.undo import UndoableActionStack
from pitivi.undo.undo import UndoError
from pitivi.undo.undo import UndoWrongStateError


class DummyUndoableAction(UndoableAction):
    done_ = True

    def __init__(self):
        UndoableAction.__init__(self)

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
        self.assertFalse(state["done"])

        action.do()
        self.assertTrue(state["done"])


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
        self.assertFalse(state["done"])

        stack.do()
        self.assertTrue(state["done"])

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
        self.assertEqual(state["actions"], 0)
        self.assertFalse(state["done"])

        stack.do()
        self.assertEqual(state["actions"], 2)
        self.assertTrue(state["done"])

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

        self.assertRaises(UndoError, stack.undo)
        self.assertEqual(state["actions"], 1)
        self.assertTrue(state["done"])


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
        self.assertRaises(UndoWrongStateError, self.log.rollback)

    def testCommitWrongState(self):
        self.assertRaises(UndoWrongStateError, self.log.commit, "")

    def testPushWrongState(self):
        # no error in this case
        self.log.push(None)

    def testUndoWrongState(self):
        self.assertRaises(UndoWrongStateError, self.log.undo)

    def testRedoWrongState(self):
        self.assertRaises(UndoWrongStateError, self.log.redo)

    def testCheckpoint(self):
        self.log.begin("meh")
        self.log.push(DummyUndoableAction())
        self.assertRaises(UndoWrongStateError, self.log.checkpoint)
        self.log.rollback()
        self.log.checkpoint()
        self.assertNotEqual(self.log._checkpoint, None)

    def testDirty(self):
        self.assertFalse(self.log.dirty())
        self.log.begin("meh")
        self.log.push(DummyUndoableAction())
        self.log.commit("meh")
        self.assertTrue(self.log.dirty())
        self.log.checkpoint()
        self.assertFalse(self.log.dirty())
        self.log.undo()
        self.assertTrue(self.log.dirty())
        self.log.redo()
        self.assertFalse(self.log.dirty())

    def testCommit(self):
        """
        Commit a stack.
        """
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.assertEqual(self.log.undo_stacks, [])
        self.log.commit("meh")
        self.assertEqual(len(self.signals), 2)
        name, (stack,) = self.signals[1]
        self.assertEqual(name, "commit")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 1)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def test_commit_proper(self):
        self.log.begin("meh")
        self.assertRaises(UndoWrongStateError, self.log.commit, "notmeh")

    def testNestedCommit(self):
        """
        Do two nested commits.
        """
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("nested")
        self.assertEqual(len(self.signals), 2)
        name, (stack,) = self.signals[1]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.assertEqual(self.log.undo_stacks, [])
        self.log.commit("nested")
        self.assertEqual(len(self.signals), 3)
        name, (stack,) = self.signals[2]
        self.assertEqual(name, "commit")
        self.assertTrue(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

        self.assertEqual(self.log.undo_stacks, [])
        self.log.commit("meh")
        self.assertEqual(len(self.signals), 4)
        name, (stack,) = self.signals[3]
        self.assertEqual(name, "commit")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 1)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def testRollback(self):
        """
        Test a rollback.
        """
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.log.rollback()
        self.assertEqual(len(self.signals), 2)
        name, (stack,) = self.signals[1]
        self.assertEqual(name, "rollback")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def testNestedRollback(self):
        """
        Test two nested rollbacks.
        """
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("nested")
        self.assertEqual(len(self.signals), 2)
        name, (stack,) = self.signals[1]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.log.rollback()
        self.assertEqual(len(self.signals), 3)
        name, (stack,) = self.signals[2]
        self.assertEqual(name, "rollback")
        self.assertTrue(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

        self.log.rollback()
        self.assertEqual(len(self.signals), 4)
        name, (stack,) = self.signals[3]
        self.assertEqual(name, "rollback")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def testUndoRedo(self):
        """
        Try an undo() redo() sequence.
        """
        # begin
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        # push two actions
        action1 = DummyUndoableAction()
        self.log.push(action1)
        self.assertEqual(len(self.signals), 2)
        name, (stack, signalAction) = self.signals[1]
        self.assertEqual(name, "push")
        self.assertTrue(action1 is signalAction)

        action2 = DummyUndoableAction()
        self.log.push(action2)
        self.assertEqual(len(self.signals), 3)
        name, (stack, signalAction) = self.signals[2]
        self.assertEqual(name, "push")
        self.assertTrue(action2 is signalAction)

        # commit
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.commit("meh")
        self.assertEqual(len(self.signals), 4)
        name, (stack,) = self.signals[3]
        self.assertEqual(name, "commit")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 1)
        self.assertEqual(len(self.log.redo_stacks), 0)

        self.assertTrue(action1.done_)
        self.assertTrue(action2.done_)

        # undo what we just committed
        self.log.undo()
        self.assertEqual(len(self.signals), 5)
        name, stack = self.signals[4]
        self.assertEqual(name, "undo")
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 1)

        self.assertFalse(action1.done_)
        self.assertFalse(action2.done_)

        # redo
        self.log.redo()
        self.assertEqual(len(self.signals), 6)
        name, stack = self.signals[5]
        self.assertEqual(name, "redo")
        self.assertEqual(len(self.log.undo_stacks), 1)
        self.assertEqual(len(self.log.redo_stacks), 0)

        self.assertTrue(action1.done_)
        self.assertTrue(action2.done_)

    def testOrder(self):
        """
        Test that actions are undone and redone in the correct order.
        """
        call_sequence = []

        class Action(UndoableAction):

            def __init__(self, n):
                UndoableAction.__init__(self)
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
        self.log.commit("nested")
        self.log.push(action3)
        self.log.commit("meh")

        self.log.undo()
        self.assertEqual(call_sequence, ["undo3", "undo2", "undo1"])

        call_sequence[:] = []
        self.log.redo()
        self.assertEqual(call_sequence, ["do1", "do2", "do3"])

        call_sequence[:] = []
        self.log.undo()
        self.assertEqual(call_sequence, ["undo3", "undo2", "undo1"])
