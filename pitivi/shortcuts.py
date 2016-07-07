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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
"""Accelerators info."""
from gi.repository import Gtk

from pitivi.utils.misc import show_user_manual


class ShortcutsManager:
    """Manager storing the shortcuts from all across the app."""

    def __init__(self, app):
        self.app = app
        self.groups = []
        self.group_titles = {}
        self.group_actions = {}

    def add(self, action, accelerators, title=None, group=None):
        """Adds an action to be displayed.

        Args:
            action (str): The name identifying the action, formatted like
                "prefix.name".
            accelerators ([str]): List of accelerators corresponding to the action
            title (Optional(str)): The title of the action.
            group (Optional[str]): The group id registered with `register_group`
                to be used instead of the one extracted from `action`.
        """
        self.app.set_accels_for_action(action, accelerators)

        if title:
            action_prefix = group or action.split(".")[0]
            if action_prefix not in self.group_actions:
                self.group_actions[action_prefix] = []
            self.group_actions[action_prefix].append((action, title))

    def register_group(self, action_prefix, title):
        """Registers a group of shortcuts to be displayed.

        Args:
            action_prefix (str): The group id.
            title (str): The title of the group.
        """
        if action_prefix not in self.groups:
            self.groups.append(action_prefix)
        self.group_titles[action_prefix] = title


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
            group = Gtk.ShortcutsGroup(title=self.app.shortcuts.group_titles[group_id])
            group.show()
            for action, title in self.app.shortcuts.group_actions[group_id]:
                accelerators = " ".join(self.app.get_accels_for_action(action))
                short = Gtk.ShortcutsShortcut(title=title, accelerator=accelerators)
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
