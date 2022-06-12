# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Alex B <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.undo.base module."""
# pylint: disable=protected-access
from unittest import mock

from gi.repository import GES

from pitivi.undo.base import GObjectObserver
from pitivi.undo.base import PropertyChangedAction
from pitivi.undo.undo import UndoableActionLog
from pitivi.undo.undo import UndoableActionStack
from tests import common


class TestGObjectObserver(common.TestCase):
    """Tests for the GObjectObserver class."""

    def test_property_change(self):
        action_log = UndoableActionLog()
        action_log.begin("complex stuff")
        stack = action_log.stacks[0]

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


class TestPropertyChangedAction(common.TestCase):

    def test_expand(self):
        stack = UndoableActionStack("good one!", mergeable=False)
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
