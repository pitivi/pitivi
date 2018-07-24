# -*- coding: utf-8 -*-
# Pitivi Developer Console
# Copyright (c) 2017-2018, Fabian Orccon <cfoch.fabian@gmail.com>
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
import sys
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas
from utils import Namespace
from widgets import ConsoleWidget


class PitiviNamespace(Namespace):
    """Easy to shape Python namespace."""

    def __init__(self, app):
        Namespace.__init__(self)
        self._app = app

    @property
    @Namespace.shortcut
    def app(self):
        """The Pitivi instance."""
        return self._app

    @property
    @Namespace.shortcut
    def plugin_manager(self):
        """The Plugin Manager instance."""
        return self._app.plugin_manager

    @property
    @Namespace.shortcut
    def project(self):
        """The current project."""
        return self._app.project_manager.current_project

    @property
    @Namespace.shortcut
    def timeline(self):
        """The GES.Timeline of the current project."""
        return self._app.gui.editor.timeline_ui.timeline.ges_timeline


class Console(GObject.GObject, Peas.Activatable):
    """Plugin which adds a Python console for development purposes."""

    __gtype_name__ = "ConsolePlugin"
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        GObject.GObject.__init__(self)
        self.window = None
        self.terminal = None
        self.menu_item = None
        self.app = None

        # Set prompt.
        sys.ps1 = ">>> "
        sys.ps2 = "... "

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
        """Inserts a menu item into the Pitivi menu."""
        menu = self.app.gui.editor.builder.get_object("menu")
        self.menu_item = Gtk.MenuItem.new_with_label(_("Developer Console"))
        self.menu_item.connect("activate", self.__menu_item_activate_cb)
        menu.add(self.menu_item)

    def remove_menu_item(self):
        """Removes a menu item from the Pitivi menu."""
        menu = self.app.gui.editor.builder.get_object("menu")
        menu.remove(self.menu_item)
        self.menu_item = None

    def _setup_dialog(self):
        namespace = PitiviNamespace(self.app)
        self.window = Gtk.Window()
        welcome_message = "".join(self.create_welcome_message(namespace))
        self.terminal = ConsoleWidget(namespace, welcome_message)
        self.terminal.connect("eof", self.__eof_cb)

        self.window.set_default_size(600, 400)
        self.window.set_title(_("Pitivi Console"))
        self.window.connect("delete-event", self.__delete_event_cb)
        self.window.add(self.terminal)

    def create_welcome_message(self, namespace):
        console_plugin_info = self.app.plugin_manager.get_plugin_info("console")
        name = console_plugin_info.get_name()
        version = console_plugin_info.get_version() or ""
        yield "%s %s\n\n" % (name, version)
        yield console_plugin_info.get_help_uri()
        yield "\n\n"
        yield _("You can use the following shortcuts:")
        yield "\n"
        for shortcut in namespace.get_shortcuts():
            yield " - %s\n" % shortcut
        yield "\n"
        yield _("Type \"{help}(<command>)\" for more information.").format(help="help")
        yield "\n\n"

    def __menu_item_activate_cb(self, unused_data):
        self.window.show_all()
        self.window.set_keep_above(True)

    def __eof_cb(self, unused_widget):
        self.window.hide()
        return True

    def __delete_event_cb(self, unused_widget, unused_data):
        return self.window.hide_on_delete()
