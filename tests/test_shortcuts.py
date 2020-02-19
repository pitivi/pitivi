# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Jakub Brindza <jakub.brindza@gmail.com>
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
"""Test the keyboard shortcuts."""
import tempfile
from unittest import mock

from pitivi.shortcuts import ShortcutsManager
from tests import common


class TestShortcutsManager(common.TestCase):
    """Tests for the ShortcutsManager."""

    def test_groups(self):
        """Checks the group in which the shortcut ends up."""
        app = mock.MagicMock()
        manager = ShortcutsManager(app)

        # Test register_group method
        manager.register_group("alpha_group", "One", position=20)
        with self.assertRaises(AssertionError):
            manager.register_group("alpha_group", "", position=0)
        manager.register_group("beta_group", "Two", position=10)
        self.assertEqual(manager.groups, ["beta_group", "alpha_group"])

        # Test grouping using the stripping away group name from action name
        manager.add("alpha_group.first", ["<Primary>A"], None, "First action")
        self.assertIn(("alpha_group.first", "First action", None),
                      manager.group_actions["alpha_group"])
        manager.add("alpha_group.second", ["<Primary>B"], None, "Second action")
        self.assertIn(("alpha_group.second", "Second action", None),
                      manager.group_actions["alpha_group"])
        manager.add("beta_group.first", ["<Primary>C"], None, "First beta action")
        self.assertIn(("beta_group.first", "First beta action", None),
                      manager.group_actions["beta_group"])

        # Test grouping using the group optional argument
        # if group parameter is set, the action prefix can be anything,
        # it should be disregarded in favour of the group value.
        manager.add("anything.third_action", ["<Primary>D"], None, "Third action",
                    group="beta_group")
        self.assertIn(("anything.third_action", "Third action", None),
                      manager.group_actions["beta_group"])

    def test_add_shortcut(self):
        """Checks the number of calls to set_accels_for_action."""
        app = mock.MagicMock()
        with mock.patch("pitivi.shortcuts.xdg_config_home") as xdg_config_home,\
                tempfile.TemporaryDirectory() as temp_dir:
            xdg_config_home.return_value = temp_dir
            manager = ShortcutsManager(app)
            # Test the add is calling set_accels_for_action(),
            # since there is no shortcuts.conf in the directory.
            manager.register_group("prefix", "General group", position=0)
            manager.add("prefix.action1", ["<Primary>P"], None, "Action one")
            self.assertEqual(app.set_accels_for_action.call_count, 1)
            # Save the shortcut to the config file.
            manager.save()
            app.set_accels_for_action.reset_mock()

            manager2 = ShortcutsManager(app)
            # Previously saved shortcut is read from the config file
            # and 'set_accels_for_action' is called.
            self.assertEqual(app.set_accels_for_action.call_count, 1)
            manager2.register_group("prefix", "General group", position=0)
            manager2.register_group("other", "Other group", position=0)
            app.set_accels_for_action.reset_mock()
            manager2.add("prefix.action1", ["<Primary>P"], None, "Action one")
            # Above shortcut has been already loaded from the config file
            # and hence 'set_accels_for_action' is not called.
            self.assertEqual(app.set_accels_for_action.call_count, 0)
            manager2.add("prefix.action2", ["<Primary>W"], None, "Action two")
            self.assertEqual(app.set_accels_for_action.call_count, 1)

    def test_load_save(self):
        """Checks saved shortcuts are loaded by a new instance."""
        app = mock.MagicMock()
        with mock.patch("pitivi.shortcuts.xdg_config_home") as xdg_config_home,\
                tempfile.TemporaryDirectory() as temp_dir:
            xdg_config_home.return_value = temp_dir
            manager = ShortcutsManager(app)
            # No file exists so set_accels_for_action() is not called.
            self.assertEqual(app.set_accels_for_action.call_count, 0)

            # Set default shortcuts
            manager.register_group("group", "Test group", position=0)
            manager.add("group.action1", ["<Primary>i"], None, "Action 1")
            manager.add("group.action2", ["<Shift>p", "<Primary>m"], None, "Action 2")
            manager.add("group.action3", ["<Primary><Shift>a", "a"], None, "Action 3")

            # After saving the shortcuts, the accels should be set when
            # initializing a ShortcutsManger.
            app.get_accels_for_action.side_effect = [(["<Primary>i"]),
                                                     (["<Shift>p", "<Primary>m"]),
                                                     (["<Primary><Shift>a", "a"])]
            manager.save()
            app.reset_mock()
            unused_manager2 = ShortcutsManager(app)
            self.assertEqual(app.set_accels_for_action.call_count, 3)
            calls = [mock.call("group.action1", ["<Primary>i"]),
                     mock.call("group.action2", ["<Shift>p", "<Primary>m"]),
                     mock.call("group.action3", ["<Primary><Shift>a", "a"])]
            app.set_accels_for_action.assert_has_calls(calls, any_order=True)

    def test_reset_accels(self):
        """Checks if accelerators have been reset to the default settings."""
        app = mock.MagicMock()
        with mock.patch("pitivi.shortcuts.xdg_config_home") as xdg_config_home,\
                tempfile.TemporaryDirectory() as temp_dir,\
                mock.patch("os.remove") as os_remove_mock:
            xdg_config_home.return_value = temp_dir
            manager = ShortcutsManager(app)

            # Set default shortcuts - they will be stored in self.defaults_accelerators.
            manager.register_group("group", "Test group", position=0)
            manager.add("group.action1", ["<Primary>i"], None, "Action 1")
            manager.add("group.action2", ["<Shift>p"], None, "Action 2")

            # Test reset of a single action. The shortcuts are saved and no file removed.
            # Only one call to set_accels_for_action() should be made.
            app.reset_mock()
            manager.save = mock.MagicMock()
            manager.reset_accels(action="group.action1")
            self.assertEqual(manager.save.call_count, 1)
            self.assertEqual(os_remove_mock.call_count, 0)
            self.assertEqual(app.set_accels_for_action.call_count, 1)

            # Test reset of all actions. Nothing is saved and the file is removed.
            # Both actions should have accelerators set.
            app.reset_mock()
            os_remove_mock.reset_mock()
            manager.save.reset_mock()
            manager.reset_accels()
            self.assertEqual(manager.save.call_count, 0)
            self.assertEqual(os_remove_mock.call_count, 1)
            self.assertEqual(app.set_accels_for_action.call_count, 2)
