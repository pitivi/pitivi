# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2010 Mathieu Duponchelle <seeed@laposte.net>
# Copyright (c) 2018 Harish Fulara <harishfulara1996@gmail.com>
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
"""Pitivi's Welcome/Greeter perspective."""
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import Gtk

from pitivi.check import missing_soft_deps
from pitivi.configure import get_ui_dir
from pitivi.dialogs.about import AboutDialog
from pitivi.dialogs.browseprojects import BrowseProjectsDialog
from pitivi.dialogs.depsmanager import DepsManager
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import WELCOME_WINDOW_CSS


class RecentProjectRow(Gtk.ListBoxRow):
    """Row of list box displaying recent projects.

    Attributes:
        name: Display name of the project.
        uri: URI of the project.
    """
    def __init__(self, name, uri):
        Gtk.ListBoxRow.__init__(self, selectable=False)
        self.uri = uri
        self.add(Gtk.Label(name, xalign=0))


# pylint: disable=too-many-instance-attributes
class GreeterPerspective(Gtk.Widget):
    """Pitivi's Welcome/Greeter perspective.

    Allows the user to create a new project or open an existing one.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Gtk.Widget.__init__(self)

        self.__app = app
        self.greeter_headerbar = Gtk.HeaderBar()
        self.__builder_handler_ids = []
        self.__new_project_action = None
        self.__open_project_action = None
        self.__menu_button_action = None
        self.__menu_button = None

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "welcomewindow.ui"))

        self.scrolled_window = builder.get_object("scrolled_window")

        self.__recent_projects_listbox = builder.get_object("recent_projects_listbox")
        self.__recent_projects_listbox.connect(
            'row_activated', self.__recent_projects_row_activated_cb)

        self.__infobar = builder.get_object("infobar")
        fix_infobar(self.__infobar)
        self.__infobar.hide()
        self.__infobar.connect("response", self.__infobar_close_button_clicked_cb)

        if self.__app.getLatest():
            self.__app_version_info_received_cb(self.__app, None)
        else:
            self.__app.connect(
                "version-info-received", self.__app_version_info_received_cb)

    def setup_greeter_perspective_ui(self):
        """Setup the UI for Greeter perspective"""
        self.__setup_css()
        self.__create_headerbar()
        self.__setup_keyboard_shortcuts()
        self.app.gui.connect("destroy", self.__destroyed_cb)

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(WELCOME_WINDOW_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.__app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def __create_headerbar(self):
        self.greeter_headerbar.props.show_close_button = True
        self.greeter_headerbar.set_title(_("Select a Project"))
        self.__create_headerbar_buttons()
        self.greeter_headerbar.show_all()

    def __setup_keyboard_shortcuts(self):
        self.__new_project_action = Gio.SimpleAction.new("new-project", None)
        self.__new_project_action.connect("activate", self.__new_project_shortcut_cb)
        self.__app.shortcuts.add("win.new-project", ["<Primary>n"],
                                 _("Create a new project"))

        self.__open_project_action = Gio.SimpleAction.new("open-project", None)
        self.__open_project_action.connect("activate", self.__open_project_shortcut_cb)
        self.__app.shortcuts.add("win.open-project", ["<Primary>o"],
                                 _("Open a project"))

        self.__menu_button_action = Gio.SimpleAction.new("menu-button", None)
        self.__menu_button_action.connect("activate", self.__menu_cb)

    def _add_greeter_keyboard_shortcuts(self):
        self.__app.gui.add_action(self.__new_project_action)
        self.__app.gui.add_action(self.__open_project_action)
        self.__app.gui.add_action(self.__menu_button_action)

    # pylint: disable=invalid-name
    def _remove_greeter_keyboard_shortcuts(self):
        self.__app.gui.remove_action("new-project")
        self.__app.gui.remove_action("open-project")
        self.__app.gui.remove_action("menu-button")

    def show_recent_projects(self):
        """Displays recent projects in a custom layout."""
        # Clear the currently displayed list.
        for child in self.__recent_projects_listbox.get_children():
            self.__recent_projects_listbox.remove(child)

        filter_ = []
        for asset in GES.list_assets(GES.Formatter):
            filter_.append(asset.get_meta(GES.META_FORMATTER_EXTENSION))

        recent_items = self.__app.recent_manager.get_items()[:10]    # Show upto 10 recent projects.
        for item in recent_items:
            if item.get_display_name().endswith(tuple(filter_)):
                self.__recent_projects_listbox.add(
                    RecentProjectRow(item.get_display_name(), item.get_uri()))

        self.__recent_projects_listbox.show_all()

    def __create_headerbar_buttons(self):
        new_project_button = Gtk.Button.new_with_label(_("New"))
        new_project_button.set_tooltip_text(_("Create a new project"))
        new_project_button.connect("clicked", self.__new_project_cb)

        open_project_button = Gtk.Button.new_with_label(_("Open"))
        open_project_button.set_tooltip_text(_("Open an existing project"))
        open_project_button.connect("clicked", self.__open_project_cb)

        self.__menu_button = self.__create_menu()

        self.greeter_headerbar.pack_start(new_project_button)
        self.greeter_headerbar.pack_start(open_project_button)
        self.greeter_headerbar.pack_end(self.__menu_button)

        if missing_soft_deps:
            missing_deps_button = Gtk.Button.new_with_label(_("Missing Dependencies"))
            missing_deps_button.connect("clicked", self.__missing_deps_cb)
            self.greeter_headerbar.pack_end(missing_deps_button)

    def __create_menu(self):
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "mainmenubutton.ui"))
        menu_button = builder.get_object("menubutton")
        # Menu options we want to display.
        display_children = ["menu_shortcuts", "menu_help", "menu_about"]
        for widget in builder.get_object("menu").get_children():
            if Gtk.Buildable.get_name(widget) not in display_children:
                widget.hide()
        builder.connect_signals_full(self.__builder_connect_cb, self)
        return menu_button

    # pylint: disable=too-many-arguments
    def __builder_connect_cb(self, builder, gobject, signal_name, handler_name,
                             connect_object, flags, user_data):
        id_ = gobject.connect(signal_name, getattr(self, handler_name))
        self.__builder_handler_ids.append((gobject, id_))

    def _aboutCb(self, unused_action):
        about_dialog = AboutDialog(self.__app)
        about_dialog.show()

    def __new_project_shortcut_cb(self, unused_action, unused_param):
        self.__new_project_cb(None)

    def __new_project_cb(self, unused_button):
        """Handles a click on the New (Project) button."""
        self.__app.gui.show_editor_perspective()
        self.__app.project_manager.newBlankProject()

    def __open_project_shortcut_cb(self, unused_action, unused_param):
        self.__open_project_cb(None)

    def __open_project_cb(self, unused_button):
        """Handles a click on the Open (Project) button."""
        BrowseProjectsDialog(self.__app)

    def __missing_deps_cb(self, unused_button):
        """Handles a click on the Missing Dependencies button."""
        DepsManager(self.__app, parent_window=self.__app.gui)

    def __menu_cb(self, unused_action, unused_param):
        self.__menu_button.set_active(not self.__menu_button.get_active())

    def __app_version_info_received_cb(self, app, unused_version_information):
        """Handles new version info."""
        if app.isLatest():
            # current version, don't show message
            return

        latest_version = app.getLatest()
        if app.settings.lastCurrentVersion != latest_version:
            # new latest version, reset counter
            app.settings.lastCurrentVersion = latest_version
            app.settings.displayCounter = 0

        if app.settings.displayCounter >= 5:
            # current version info already showed 5 times, don't show again
            return

        # increment counter, create infobar and show info
        app.settings.displayCounter = app.settings.displayCounter + 1
        text = _("Pitivi %s is available.") % latest_version
        label = Gtk.Label(label=text)
        self.__infobar.get_content_area().add(label)
        self.__infobar.set_message_type(Gtk.MessageType.INFO)
        self.__infobar.show_all()

    # pylint: disable=invalid-name
    def __infobar_close_button_clicked_cb(self, unused_infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()

    # pylint: disable=invalid-name
    def __recent_projects_row_activated_cb(self, unused_listbox, row):
        if self.__app.project_manager.loadProject(row.uri):
            self.__app.gui.show_editor_perspective()

    def __destroyed_cb(self, unused_main_window):
        self.__recent_projects_listbox.disconnect_by_func(
            self.__recent_projects_row_activated_cb)
        self.__infobar.disconnect_by_func(self.__infobar_close_button_clicked_cb)
        self.__new_project_action.disconnect_by_func(self.__new_project_shortcut_cb)
        self.__open_project_action.disconnect_by_func(self.__open_project_shortcut_cb)
        self.__menu_button_action.disconnect_by_func(self.__menu_cb)
        for gobject, id_ in self.__builder_handler_ids:
            gobject.disconnect(id_)
        if not self.__app.getLatest():
            self.__app.disconnect_by_func(self.__app_version_info_received_cb)
        self.disconnect_by_func(self.__destroyed_cb)
