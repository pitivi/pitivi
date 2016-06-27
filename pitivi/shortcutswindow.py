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


class ShortcutsWindow(Gtk.ShortcutsWindow):
    """Dialog for displaying the accelerators."""

    group_titles = {}
    group_actions = {}
    groups = []

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
        for group_id in ShortcutsWindow.groups:
            group = Gtk.ShortcutsGroup(title=ShortcutsWindow.group_titles[group_id])
            group.show()
            for action, title in ShortcutsWindow.group_actions[group_id]:
                accelerators = " ".join(self.app.get_accels_for_action(action))
                short = Gtk.ShortcutsShortcut(title=title, accelerator=accelerators)
                short.show()
                group.add(short)
            section.add(group)
        # Method below must be called after the section has been populated,
        # otherwise the shortcuts won't show up in search.
        self.add(section)

    @classmethod
    def add_action(cls, action, title, group=None):
        """Adds an action to be displayed.

        Args:
            action (str): The name identifying the action, formatted like
                "prefix.name".
            title (str): The title of the action.
            group (Optional[str]): The group id registered with `register_group`
                to be used instead of the one extracted from `action`.
        """
        action_prefix = group or action.split(".")[0]
        if action_prefix not in cls.group_actions:
            cls.group_actions[action_prefix] = []
        cls.group_actions[action_prefix].append((action, title))

    @classmethod
    def register_group(cls, action_prefix, title):
        """Registers a group of shortcuts to be displayed.

        Args:
            action_prefix (str): The group id.
            title (str): The title of the group.
        """
        if action_prefix not in cls.groups:
            cls.groups.append(action_prefix)
        cls.group_titles[action_prefix] = title


def show_shortcuts(app):
    """Shows the shortcuts window or the user manual page with the shortcuts."""
    if hasattr(Gtk, "ShortcutsWindow"):
        shortcuts_window = ShortcutsWindow(app)
        shortcuts_window.show()
    else:
        show_user_manual("cheatsheet")
