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
from unittest import mock
from unittest import TestCase

from gi.repository import GES

from pitivi.undo.undo import GObjectObserver
from pitivi.undo.undo import PropertyChangedAction
from pitivi.undo.undo import UndoableAction
from pitivi.undo.undo import UndoableActionLog
from pitivi.undo.undo import UndoableActionStack
from pitivi.undo.undo import UndoError
from pitivi.undo.undo import UndoWrongStateError


class TestUndoableActionStack(TestCase):

    def testUndoDo(self):
        """
        Test an undo() do() sequence.
        """
        state = {"actions": 2}

        class Action(UndoableAction):

            def do(self):
                state["actions"] += 1

            def undo(self):
                state["actions"] -= 1

        stack = UndoableActionStack("meh")
        action1 = Action()
        action2 = Action()
        stack.push(action1)
        stack.push(action2)

        stack.undo()
        self.assertEqual(state["actions"], 0)

        stack.do()
        self.assertEqual(state["actions"], 2)

    def testUndoError(self):
        """
        Undo a stack containing a failing action.
        """
        stack = UndoableActionStack("meh")
        action1 = mock.Mock(spec=UndoableAction)
        action1.expand.return_value = False
        action2 = mock.Mock(spec=UndoableAction)
        action2.expand.return_value = False
        action2.undo.side_effect = UndoError("meh")
        action3 = mock.Mock(spec=UndoableAction)
        stack.push(action1)
        stack.push(action2)
        stack.push(action3)

        self.assertRaises(UndoError, stack.undo)
        self.assertEqual(action1.undo.call_count, 0)
        self.assertEqual(action2.undo.call_count, 1)
        self.assertEqual(action3.undo.call_count, 1)


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
        for signalName in ("begin", "push", "rollback", "commit", "move"):
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
        self.log.push(mock.Mock(spec=UndoableAction))
        self.assertRaises(UndoWrongStateError, self.log.checkpoint)
        self.log.rollback()
        self.log.checkpoint()
        self.assertNotEqual(self.log._checkpoint, None)

    def testDirty(self):
        self.assertFalse(self.log.dirty())
        self.log.begin("meh")
        self.log.push(mock.Mock(spec=UndoableAction))
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
        self.log.push(mock.Mock(spec=UndoableAction))
        self.log.commit("meh")
        self.assertEqual(len(self.signals), 3)
        name, (stack, action) = self.signals[1]
        self.assertEqual(name, "push")
        name, (stack,) = self.signals[2]
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
        self.log.push(mock.Mock(spec=UndoableAction))
        self.log.commit("nested")
        self.assertEqual(len(self.signals), 4)
        name, (stack, action) = self.signals[2]
        self.assertEqual(name, "push")
        name, (stack,) = self.signals[3]
        self.assertEqual(name, "commit")
        self.assertTrue(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

        self.assertEqual(self.log.undo_stacks, [])
        self.log.commit("meh")
        self.assertEqual(len(self.signals), 5)
        name, (stack,) = self.signals[4]
        self.assertEqual(name, "commit")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 1)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def test_finalizing_action(self):
        action1 = mock.Mock()
        action2 = mock.Mock()
        with self.log.started("one", finalizing_action=action1):
            self.log.push(mock.Mock(spec=UndoableAction))
            with self.log.started("two", finalizing_action=action2):
                self.log.push(mock.Mock(spec=UndoableAction))
        action1.do.assert_called_once_with()
        # For now, we call the finalizing action only for the top stack.
        action2.do.assert_not_called()

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
        action1 = mock.Mock(spec=UndoableAction)
        action1.expand.return_value = False
        self.log.push(action1)
        self.assertEqual(len(self.signals), 2)
        name, (stack, signalAction) = self.signals[1]
        self.assertEqual(name, "push")
        self.assertTrue(action1 is signalAction)

        action2 = mock.Mock(spec=UndoableAction)
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
        self.assertEqual(action1.do.call_count, 0)
        self.assertEqual(action1.undo.call_count, 0)
        self.assertEqual(action2.do.call_count, 0)
        self.assertEqual(action2.undo.call_count, 0)

        # undo what we just committed
        self.log.undo()
        self.assertEqual(len(self.signals), 5)
        name, stack = self.signals[4]
        self.assertEqual(name, "move")
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 1)
        self.assertEqual(action1.do.call_count, 0)
        self.assertEqual(action1.undo.call_count, 1)
        self.assertEqual(action2.do.call_count, 0)
        self.assertEqual(action2.undo.call_count, 1)

        # redo
        self.log.redo()
        self.assertEqual(len(self.signals), 6)
        name, stack = self.signals[5]
        self.assertEqual(name, "move")
        self.assertEqual(len(self.log.undo_stacks), 1)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.assertEqual(action1.do.call_count, 1)
        self.assertEqual(action1.undo.call_count, 1)
        self.assertEqual(action2.do.call_count, 1)
        self.assertEqual(action2.undo.call_count, 1)

    def testOrder(self):
        """
        Test that actions are undone and redone in the correct order.
        """
        order = mock.Mock()
        order.action1 = mock.Mock(spec=UndoableAction)
        order.action1.expand.return_value = False
        order.action2 = mock.Mock(spec=UndoableAction)
        order.action2.expand.return_value = False
        order.action3 = mock.Mock(spec=UndoableAction)
        order.action3.expand.return_value = False

        with self.log.started("meh"):
            self.log.push(order.action1)
            with self.log.started("nested"):
                self.log.push(order.action2)
            self.log.push(order.action3)

        self.log.undo()
        order.assert_has_calls([mock.call.action3.undo(),
                                mock.call.action2.undo(),
                                mock.call.action1.undo()])

        self.log.redo()
        order.assert_has_calls([mock.call.action1.do(),
                                mock.call.action2.do(),
                                mock.call.action3.do()])

        self.log.undo()
        order.assert_has_calls([mock.call.action3.undo(),
                                mock.call.action2.undo(),
                                mock.call.action1.undo()])


class TestGObjectObserver(TestCase):

    def test_property_change(self):
        action_log = UndoableActionLog()
        action_log.begin("complex stuff")
        stack, = action_log.stacks

        clip = GES.TitleClip()
        clip.props.start = 1
        unused_observer = GObjectObserver(clip, ["start"], action_log)

        self.assertEqual(len(stack.done_actions), 0)
        clip.props.start = 2
        self.assertEqual(len(stack.done_actions), 1)

        clip.props.start = 2
        self.assertEqual(len(stack.done_actions), 1)

        clip.props.start = 4
        self.assertEqual(len(stack.done_actions), 1)
        action = stack.done_actions[-1]
        self.assertEqual(action.old_value, 1)
        self.assertEqual(action.new_value, 4)


class TestPropertyChangedAction(TestCase):

    def test_expand(self):
        stack = UndoableActionStack("good one!")
        gobject = mock.Mock()
        stack.push(PropertyChangedAction(gobject, "field", 5, 7))
        stack.push(PropertyChangedAction(gobject, "field", 11, 13))
        self.assertEqual(len(stack.done_actions), 1, stack.done_actions)
        self.assertEqual(stack.done_actions[0].old_value, 5)
        self.assertEqual(stack.done_actions[0].new_value, 13)

        stack.push(PropertyChangedAction(gobject, "field2", 0, 1))
        self.assertEqual(len(stack.done_actions), 2, stack.done_actions)

        stack.push(PropertyChangedAction(mock.Mock(), "field", 0, 1))
        self.assertEqual(len(stack.done_actions), 3, stack.done_actions)
