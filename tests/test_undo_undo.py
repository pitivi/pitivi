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
"""Tests for the pitivi.undo.undo module."""
# pylint: disable=protected-access
from unittest import mock

from gi.repository import GES
from gi.repository import Gst

from pitivi.undo.base import UndoableAction
from pitivi.undo.undo import UndoableActionLog
from pitivi.undo.undo import UndoableActionStack
from pitivi.undo.undo import UndoError
from pitivi.undo.undo import UndoWrongStateError
from tests import common


class TestUndoableActionStack(common.TestCase):
    """Tests for the UndoableActionStack class."""

    def test_undo_do(self):
        """Checks an undo() and do() sequence."""
        state = {"actions": 2}

        class Action(UndoableAction):

            def do(self):
                state["actions"] += 1

            def undo(self):
                state["actions"] -= 1

        stack = UndoableActionStack("meh", mergeable=False)
        action1 = Action()
        action2 = Action()
        stack.push(action1)
        stack.push(action2)

        stack.undo()
        self.assertEqual(state["actions"], 0)

        stack.do()
        self.assertEqual(state["actions"], 2)

    def test_undo_error(self):
        """Checks undo a stack containing a failing action."""
        stack = UndoableActionStack("meh", mergeable=False)
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


class TestUndoableActionLog(common.TestCase):
    """Tests for the UndoableActionLog class."""

    def setUp(self):
        self.log = UndoableActionLog()
        self._connect_to_undoable_action_log(self.log)
        self.signals = []

    def tearDown(self):
        self._disconnect_from_undoable_action_log()

    def check_signals(self, *expected_signals):
        signals = [item[0] for item in self.signals]
        self.assertListEqual(signals, list(expected_signals))

    def _undo_action_log_signal_cb(self, log, *args):
        args = list(args)
        signal_name = args.pop(-1)
        self.signals.append((signal_name, args))

    def _connect_to_undoable_action_log(self, log):
        for signal_name in ("begin", "push", "rollback", "commit", "move"):
            log.connect(signal_name, self._undo_action_log_signal_cb, signal_name)

    def _disconnect_from_undoable_action_log(self):
        self.log.disconnect_by_func(self._undo_action_log_signal_cb)

    def test_rollback_wrong_state(self):
        self.assertRaises(UndoWrongStateError, self.log.rollback)

    def test_commit_wrong_state(self):
        self.assertRaises(UndoWrongStateError, self.log.commit, "")

    def test_push_wrong_state(self):
        # no error in this case
        self.log.push(None)

    def test_undo_wrong_state(self):
        self.assertRaises(UndoWrongStateError, self.log.undo)

    def test_redo_wrong_state(self):
        self.assertRaises(UndoWrongStateError, self.log.redo)

    def test_checkpoint(self):
        self.log.begin("meh")
        self.log.push(mock.Mock(spec=UndoableAction))
        self.assertRaises(UndoWrongStateError, self.log.checkpoint)
        self.log.rollback()
        self.log.checkpoint()
        self.assertNotEqual(self.log._checkpoint, None)

    def test_dirty(self):
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

    def test_commit(self):
        """Checks committing a stack."""
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (_stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.assertEqual(self.log.undo_stacks, [])
        self.log.push(mock.Mock(spec=UndoableAction))
        self.log.commit("meh")
        self.assertEqual(len(self.signals), 3)
        name, (_stack, _action) = self.signals[1]
        self.assertEqual(name, "push")
        name, (_stack,) = self.signals[2]
        self.assertEqual(name, "commit")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 1)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def test_commit_proper(self):
        self.log.begin("meh")
        self.assertRaises(UndoWrongStateError, self.log.commit, "notmeh")

    def test_nested_commit(self):
        """Checks two nested commits."""
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (_stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("nested")
        self.assertEqual(len(self.signals), 2)
        name, (_stack,) = self.signals[1]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.assertEqual(self.log.undo_stacks, [])
        self.log.push(mock.Mock(spec=UndoableAction))
        self.log.commit("nested")
        self.assertEqual(len(self.signals), 4)
        name, (_stack, _action) = self.signals[2]
        self.assertEqual(name, "push")
        name, (_stack,) = self.signals[3]
        self.assertEqual(name, "commit")
        self.assertTrue(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

        self.assertEqual(self.log.undo_stacks, [])
        self.log.commit("meh")
        self.assertEqual(len(self.signals), 5)
        name, (_stack,) = self.signals[4]
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

    def test_rollback(self):
        """Checks a rollback."""
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.check_signals("begin")
        name, (_stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        action = mock.Mock(spec=UndoableAction)
        self.log.push(action)

        self.log.rollback()

        action.undo.assert_called_once_with()

        self.check_signals("begin", "push", "rollback")
        name, (_stack,) = self.signals[2]
        self.assertEqual(name, "rollback")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def test_rollback_noop(self):
        """Checks a rollback which does not act."""
        self.log.begin("meh")

        action = mock.Mock(spec=UndoableAction)
        self.log.push(action)

        self.log.rollback(undo=False)
        action.undo.assert_not_called()

    def test_nested_rollback(self):
        """Checks two nested rollbacks."""
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (_stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.begin("nested")
        self.assertEqual(len(self.signals), 2)
        name, (_stack,) = self.signals[1]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        self.log.rollback()
        self.assertEqual(len(self.signals), 3)
        name, (_stack,) = self.signals[2]
        self.assertEqual(name, "rollback")
        self.assertTrue(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

        self.log.rollback()
        self.assertEqual(len(self.signals), 4)
        name, (_stack,) = self.signals[3]
        self.assertEqual(name, "rollback")
        self.assertFalse(self.log.is_in_transaction())
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def test_undo_redo(self):
        """Tries an undo() redo() sequence."""
        # begin
        self.log.begin("meh")
        self.assertEqual(len(self.signals), 1)
        name, (_stack,) = self.signals[0]
        self.assertEqual(name, "begin")
        self.assertTrue(self.log.is_in_transaction())

        # push two actions
        action1 = mock.Mock(spec=UndoableAction)
        action1.expand.return_value = False
        self.log.push(action1)
        self.assertEqual(len(self.signals), 2)
        name, (_stack, signal_action) = self.signals[1]
        self.assertEqual(name, "push")
        self.assertTrue(action1 is signal_action)

        action2 = mock.Mock(spec=UndoableAction)
        self.log.push(action2)
        self.assertEqual(len(self.signals), 3)
        name, (_stack, signal_action) = self.signals[2]
        self.assertEqual(name, "push")
        self.assertTrue(action2 is signal_action)

        # commit
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.log.commit("meh")
        self.assertEqual(len(self.signals), 4)
        name, (_stack,) = self.signals[3]
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
        name, _args = self.signals[4]
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
        name, _args = self.signals[5]
        self.assertEqual(name, "move")
        self.assertEqual(len(self.log.undo_stacks), 1)
        self.assertEqual(len(self.log.redo_stacks), 0)
        self.assertEqual(action1.do.call_count, 1)
        self.assertEqual(action1.undo.call_count, 1)
        self.assertEqual(action2.do.call_count, 1)
        self.assertEqual(action2.undo.call_count, 1)

    def test_order(self):
        """Checks actions are undone and redone in the correct order."""
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

    def test_toplevel_operation(self):
        """Checks the toplevel operations nesting."""
        self.log.begin("one", toplevel=False)
        self.log.commit("one")

        self.log.begin("two", toplevel=True)
        self.log.commit("two")

        self.log.begin("three")
        self.assertRaises(UndoWrongStateError,
                          self.log.begin,
                          "four", toplevel=True)
        self.log.begin("nested1")
        self.log.begin("nested2", toplevel=False)

    def test_failing_operation_rollback(self):
        """Checks that failing operations are rolled back."""
        action = mock.Mock(spec=UndoableAction)

        class WatchingError(Exception):
            pass

        with self.assertRaises(WatchingError):
            with self.log.started("failing_op"):
                self.log.push(action)
                raise WatchingError()

        # Check the rollback happened
        self.assertEqual(action.do.call_count, 0)
        self.assertEqual(action.undo.call_count, 1)
        # Check the undo and redo stacks are empty
        self.assertEqual(len(self.log.undo_stacks), 0)
        self.assertEqual(len(self.log.redo_stacks), 0)

    def test_merging(self):
        with self.log.started("one", mergeable=False):
            action = mock.Mock(spec=UndoableAction)
            action.expand.side_effect = Exception("should not have been called")
            self.log.push(action)
        self.assertEqual(len(self.log.undo_stacks), 1)

        with self.log.started("one", mergeable=True):
            action = mock.Mock(spec=UndoableAction)
            action.expand.return_value = False
            self.log.push(action)
        self.assertEqual(len(self.log.undo_stacks), 2)

        with self.log.started("one", mergeable=True):
            action = mock.Mock(spec=UndoableAction)
            action.expand.return_value = True
            self.log.push(action)
        self.assertEqual(len(self.log.undo_stacks), 3)

        with self.log.started("one", mergeable=True):
            action = mock.Mock(spec=UndoableAction)
            action.expand.return_value = True
            self.log.push(action)
        self.assertEqual(len(self.log.undo_stacks), 3)

        with self.log.started("one", mergeable=False):
            action = mock.Mock(spec=UndoableAction)
            action.expand.side_effect = Exception("should not have been called")
            self.log.push(action)
        self.assertEqual(len(self.log.undo_stacks), 4)


class TestRollback(common.TestCase):

    @common.setup_timeline
    def test_rollback_of_nested_operation_does_not_add_actions_to_parent(self):
        clip1 = GES.TitleClip()
        clip1.set_start(0 * Gst.SECOND)
        clip1.set_duration(1 * Gst.SECOND)

        clip2 = GES.TitleClip()
        clip2.set_start(1 * Gst.SECOND)
        clip2.set_duration(1 * Gst.SECOND)

        # begin parent operation
        self.action_log.begin("parent")

        # push one parent action
        self.layer.add_clip(clip1)
        stack_snapshot = self.action_log._get_last_stack().done_actions[::]

        # begin nested operation
        self.action_log.begin("nested")

        # push one nested action
        self.layer.add_clip(clip2)

        self.action_log.rollback()
        self.assertListEqual(self.action_log._get_last_stack().done_actions, stack_snapshot)
