# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016 Jakub Brindza<jakub.brindza@gmail.com>
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
"""Accelerators info."""
import os.path

from gi.repository import GObject
from gi.repository import Gtk

from pitivi.settings import xdg_config_home
from pitivi.utils.misc import show_user_manual


class ShortcutsManager(GObject.Object):
    """Manager storing the shortcuts from all across the app."""

    __gsignals__ = {
        "accel-changed": (GObject.SignalFlags.RUN_LAST, None, (str,))
    }

    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app
        self.__groups = []
        self.group_titles = {}
        self.group_actions = {}
        self.default_accelerators = {}
        self.titles = {}
        self.config_path = os.path.join(xdg_config_home(), "shortcuts.conf")
        self.__loaded_actions = list(self.__load())

    @property
    def groups(self):
        """The group ids ordered as they should be displayed."""
        return [item[1] for item in self.__groups]

    def __load(self):
        """Loads the shortcuts from the config file and sets them.

        Yields:
            string: The shortcuts loaded from the config file.
        """
        if not os.path.isfile(self.config_path):
            return

        with open(self.config_path, "r", encoding="UTF-8") as conf_file:
            for line in conf_file:
                action, accelerators = line.split(":", 1)
                accelerators = accelerators.strip("\n").split(",")
                # Filter out invalid accelerators coming from the config file.
                accelerators = [a for a in accelerators if Gtk.accelerator_parse(a).accelerator_key]
                self.app.set_accels_for_action(action, accelerators)
                yield action

    def save(self):
        """Saves the accelerators for each action to the config file.

        Only the actions added using `add` with a title are considered.
        """
        with open(self.config_path, "w", encoding="UTF-8") as conf_file:
            for unused_group_id, actions in self.group_actions.items():
                for action, unused_title, unused_action_object in actions:
                    accels = ",".join(self.app.get_accels_for_action(action))
                    conf_file.write(action + ":" + accels + "\n")

    def add(self, action, accelerators, action_object, title, group=None):
        """Adds an action to be displayed.

        Args:
            action (str): The name identifying the action, formatted like
                "prefix.name".
            accelerators ([str]): The default accelerators corresponding to
                the action. They are set as the accelerators of the action
                only if no accelerators have been loaded from the config file
                initially, when the current manager instance has been created.
            action_object (Gio.SimpleAction): The object of the action.
            title (str): The title of the action.
            group (Optional[str]): The group id registered with `register_group`
                to be used instead of that extracted from `action`.
        """
        self.default_accelerators[action] = accelerators
        self.titles[action] = title
        if action not in self.__loaded_actions:
            self.app.set_accels_for_action(action, accelerators)

        action_prefix = group or action.split(".")[0]
        self.group_actions[action_prefix].append((action, title, action_object))

    def set(self, action, accelerators):
        """Sets accelerators for a shortcut.

        Args:
            action (str): The name identifying the action, formatted like
                "prefix.name".
            accelerators ([str]): The array containing accelerators to be set.
        """
        self.app.set_accels_for_action(action, accelerators)
        self.emit("accel-changed", action)

    def is_changed(self, action):
        """Checks whether the accelerators for an action have been changed.

        Args:
            action (str): The "prefix.name" identifying the action.

        Returns:
            bool: True iff the current accelerators are not the default ones.
        """
        accelerators = self.app.get_accels_for_action(action)
        return set(accelerators) != set(self.default_accelerators[action])

    def get_conflicting_action(self, action, keyval, mask):
        """Looks for a conflicting action using the specified accelerator.

        If an accelerator is used by another action in the same group or
        in the "win" and "app" global groups, it is not clear which of them
        will trigger when the accelerator is pressed.

        Args:
            action (str): The "prefix.name" identifying the action for which
                the accelerator will be set if there is no conflict.
            keyval (int): The key value of the accelerator.
            mask (int): The mask value of the accelerator.

        Returns:
            str: The name of the conflicting action using the accelerator, or None.
        """
        group_name = action.split(".")[0]
        for group in (group_name, "app", "win"):
            for neighbor_action, unused_title, unused_action_object in self.group_actions[group]:
                if neighbor_action == action:
                    continue
                for accel in self.app.get_accels_for_action(neighbor_action):
                    if (keyval, mask) == Gtk.accelerator_parse(accel):
                        return neighbor_action
        return None

    def register_group(self, action_prefix, title, position):
        """Registers a group of shortcuts to be displayed.

        Args:
            action_prefix (str): The group id.
            title (str): The title of the group.
            position (int): The position used to sort the groups for display.
        """
        assert action_prefix not in self.group_titles
        self.group_titles[action_prefix] = title
        self.group_actions[action_prefix] = []
        self.__groups.append((position, action_prefix))
        self.__groups.sort()

    # pylint: disable=redefined-argument-from-local
    def reset_accels(self, action=None):
        """Resets accelerators to their default values.

        Args:
            action (Optional(str)): The action name.
                If specified, reset the specified action's accelerators.
                Otherwise reset accelerators for all actions.
        """
        if action:
            self.app.set_accels_for_action(action, self.default_accelerators[action])
            self.save()
            self.emit("accel-changed", action)
        else:
            for action, accelerators in self.default_accelerators.items():
                self.app.set_accels_for_action(action, accelerators)
            try:
                os.remove(self.config_path)
            except FileNotFoundError:
                pass
            self.emit("accel-changed", None)


class ShortcutsWindow(Gtk.ShortcutsWindow):
    """Dialog for displaying the accelerators."""

    def __init__(self, app):
        Gtk.ShortcutsWindow.__init__(self)
        self.app = app
        self.set_transient_for(self.app.gui)
        self.set_modal(True)
        self.populate()

    def populate(self):
        """Gathers the accelerators and populates the window."""
        section = Gtk.ShortcutsSection()
        section.show()
        for group_id in self.app.shortcuts.groups:
            actions = self.app.shortcuts.group_actions.get(group_id)
            if not actions:
                continue

            group = Gtk.ShortcutsGroup(title=self.app.shortcuts.group_titles[group_id])
            group.show()
            for action, title, _ in actions:
                # Show only the first accelerator which is the main one.
                # Don't bother with the others, to keep the dialog pretty.
                try:
                    accelerator = self.app.get_accels_for_action(action)[0]
                except IndexError:
                    accelerator = ""
                short = Gtk.ShortcutsShortcut(title=title, accelerator=accelerator)
                short.show()
                group.add(short)
            section.add(group)
        # Method below must be called after the section has been populated,
        # otherwise the shortcuts won't show up in search.
        self.add(section)


def show_shortcuts(app):
    """Shows the shortcuts window or the user manual page with the shortcuts."""
    if hasattr(Gtk, "ShortcutsWindow"):
        shortcuts_window = ShortcutsWindow(app)
        shortcuts_window.show()
    else:
        show_user_manual("cheatsheet")
