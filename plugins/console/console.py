# -*- coding: utf-8 -*-
# Pitivi Developer Console
# Copyright (c) 2017, Fabian Orccon <cfoch.fabian@gmail.com>
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
"""Python console for inspecting and interacting with Pitivi and the project."""
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas
from widgets import ConsoleWidget


class Console(GObject.GObject, Peas.Activatable):
    """Plugin which adds a Python console for development purposes."""

    __gtype_name__ = "ConsolePlugin"
    object = GObject.Property(type=GObject.Object)

    MENU_LABEL = _("Developer Console")
    TITLE = _("Pitivi Console")

    def __init__(self):
        GObject.GObject.__init__(self)
        self.window = None
        self.terminal = None
        self.menu_item = None
        self.app = None

    def do_activate(self):
        api = self.object
        self.app = api.app
        self._setup_dialog()
        self.add_menu_item()
        self.menu_item.show()

    def do_deactivate(self):
        self.window.destroy()
        self.remove_menu_item()
        self.window = None
        self.terminal = None
        self.menu_item = None
        self.app = None

    def add_menu_item(self):
        """Inserts a menu item into the Pitivi menu"""
        menu = self.app.gui.editor.builder.get_object("menu")
        self.menu_item = Gtk.MenuItem.new_with_label(Console.MENU_LABEL)
        self.menu_item.connect("activate", self.__menu_item_activate_cb)
        menu.add(self.menu_item)

    def remove_menu_item(self):
        """Removes a menu item from the Pitivi menu"""
        menu = self.app.gui.editor.builder.get_object("menu")
        menu.remove(self.menu_item)
        self.menu_item = None

    def _setup_dialog(self):
        namespace = {"app": self.app}
        self.window = Gtk.Window()
        self.terminal = ConsoleWidget(namespace)

        self.window.set_default_size(600, 400)
        self.window.set_title(Console.TITLE)
        self.window.connect("delete-event", self.__delete_event_cb)
        self.window.add(self.terminal)

    def __menu_item_activate_cb(self, unused_data):
        self.window.show_all()
        self.window.set_keep_above(True)

    def __delete_event_cb(self, unused_widget, unused_data):
        return self.window.hide_on_delete()
