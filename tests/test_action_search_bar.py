# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Ayush Mittal <ayush.mittal9398@gmail.com>
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
"""Test for Action Search Bar."""
from gi.repository import Gio

from pitivi.action_search_bar import ActionSearchBar
from pitivi.shortcuts import ShortcutsManager
from tests import common


class TestActionSearchBar(common.TestCase):
    """Tests for ActionSearchBar."""

    def test_action_search(self):
        app = common.create_pitivi()
        shortcut_manager = ShortcutsManager(app)

        shortcut_manager.register_group("alpha_group", "One", position=10)
        shortcut_manager.register_group("beta_group", "Two", position=20)

        action = Gio.SimpleAction.new("remove-effect", None)
        shortcut_manager.add("alpha_group.first", ["<Primary>A"], action, "First action")
        shortcut_manager.add("alpha_group.second", ["<Primary>B"], action, "Second action")
        shortcut_manager.add("beta_group.first", ["<Primary>C"], action, "First beta action")

        app.shortcuts = shortcut_manager
        action_search_bar = ActionSearchBar(app)

        # When entry is empty initially.
        all_vals = ["First action", "Second action", "First beta action"]
        self.assertEqual(self.result_vals(action_search_bar), all_vals)

        # When entry is "First".
        self.assertEqual(self.result_vals(action_search_bar, "First action"), ["First action", "First beta action"])

        # When entry is "Second".
        self.assertEqual(self.result_vals(action_search_bar, "Second"), ["Second action"])

    def result_vals(self, action_search_bar, entry=''):
        action_search_bar.entry.set_text(entry)
        result_actions = []
        row_iter = action_search_bar.model_filter.get_iter_first()

        while row_iter is not None:
            result_actions.append(action_search_bar.model_filter.get_value(row_iter, 0))
            row_iter = action_search_bar.model_filter.iter_next(row_iter)

        return result_actions
