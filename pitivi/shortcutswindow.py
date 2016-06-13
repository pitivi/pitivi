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
from gi.repository import Gtk

from pitivi.utils.misc import show_user_manual


class ShortcutsWindow(Gtk.ShortcutsWindow):
    group_names = {}
    group_actions = {}
    groups = []

    def __init__(self, app):
        Gtk.ShortcutsWindow.__init__(self)
        self.app = app
        self.populate()
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_modal(True)

    def populate(self):
        """Gathers the accelerators and creates the structure of the window."""
        section = Gtk.ShortcutsSection()
        section.show()
        for group_id in ShortcutsWindow.groups:
            group = Gtk.ShortcutsGroup(title=ShortcutsWindow.group_names[group_id])
            group.show()
            for action, action_description in ShortcutsWindow.group_actions[group_id]:
                accelerators = " ".join(self.app.get_accels_for_action(action))
                short = Gtk.ShortcutsShortcut(title=action_description, accelerator=accelerators)
                short.show()
                group.add(short)
            section.add(group)
        # Method below must be called after the section has been populated,
        # otherwise the shortcuts won't show up in search.
        self.add(section)

    @classmethod
    def add_action(cls, action, accel_description):
        action_prefix = action.split(".")[0]
        try:
            cls.group_actions[action_prefix].append((action, accel_description))
        except KeyError:
            cls.group_actions[action_prefix] = [(action, accel_description)]

    @classmethod
    def register_group(cls, action_prefix, group_name):
        if action_prefix not in cls.groups:
            cls.groups.append(action_prefix)
        cls.group_names[action_prefix] = group_name


def show_shortcuts(app):
    if hasattr(Gtk, "ShortcutsWindow"):
        shortcuts_window = ShortcutsWindow(app)
        shortcuts_window.show()
    else:
        show_user_manual("cheatsheet")
