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
from pitivi.dialogs.browseprojects import BrowseProjectsDialog
from pitivi.dialogs.depsmanager import DepsManager
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import GREETER_PERSPECTIVE_CSS

MAX_RECENT_PROJECTS = 10


class ProjectInfoRow(Gtk.ListBoxRow):
    """Row of Gtk.ListBox displaying a project's info in a custom layout.

    Attributes:
        name: Display name of the project.
        uri: URI of the project.
    """
    def __init__(self, name, uri):
        Gtk.ListBoxRow.__init__(self)
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

        self.app = app
        self._greeter_headerbar = None
        self.__new_project_action = None
        self.__open_project_action = None
        self._greeter_menu_button = None

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "greeter.ui"))

        self.scrolled_window = builder.get_object("scrolled_window")

        self.__recent_projects_listbox = builder.get_object("recent_projects_listbox")
        self.__recent_projects_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__recent_projects_listbox.connect(
            "row_activated", self.__projects_row_activated_cb)

        self.__project_filter = self.__create_project_filter()

        self.__infobar = builder.get_object("infobar")
        fix_infobar(self.__infobar)
        self.__infobar.hide()
        self.__infobar.connect("response", self.__infobar_response_cb)

        if app.getLatest():
            self.__app_version_info_received_cb(app, None)
        else:
            app.connect("version-info-received", self.__app_version_info_received_cb)

    def _setup_greeter_perspective_ui(self):
        """Setup the UI for Greeter perspective"""
        self.__setup_css()
        self._greeter_headerbar = self.__create_headerbar()
        self._greeter_headerbar.show_all()
        self.__set_keyboard_shortcuts()

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(GREETER_PERSPECTIVE_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def __create_headerbar(self):
        headerbar = Gtk.HeaderBar()
        headerbar.props.show_close_button = True
        headerbar.set_title(_("Select a Project"))

        new_project_button = Gtk.Button.new_with_label(_("New"))
        new_project_button.set_tooltip_text(_("Create a new project"))
        new_project_button.set_action_name("win.new-project")

        open_project_button = Gtk.Button.new_with_label(_("Open"))
        open_project_button.set_tooltip_text(_("Open an existing project"))
        open_project_button.set_action_name("win.open-project")

        self._greeter_menu_button = self.__create_menu()

        headerbar.pack_start(new_project_button)
        headerbar.pack_start(open_project_button)
        headerbar.pack_end(self._greeter_menu_button)

        if missing_soft_deps:
            missing_deps_button = Gtk.Button.new_with_label(_("Missing Dependencies"))
            missing_deps_button.connect("clicked", self.__missing_deps_cb)
            headerbar.pack_end(missing_deps_button)

        return headerbar

    def __set_keyboard_shortcuts(self):
        self.__new_project_action = Gio.SimpleAction.new("new-project", None)
        self.__new_project_action.connect("activate", self.__new_project_cb)
        self.app.gui.add_action(self.__new_project_action)
        self.app.shortcuts.add("win.new-project", ["<Primary>n"],
                               _("Create a new project"))

        self.__open_project_action = Gio.SimpleAction.new("open-project", None)
        self.__open_project_action.connect("activate", self.__open_project_cb)
        self.app.gui.add_action(self.__open_project_action)
        self.app.shortcuts.add("win.open-project", ["<Primary>o"],
                               _("Open a project"))

        # Disable shortcuts for now. They will be managed by MainWindow.
        self._disable_greeter_keyboard_shortcuts()

    # pylint: disable=invalid-name
    def _enable_greeter_keyboard_shortcuts(self):
        self.__new_project_action.set_enabled(True)
        self.__open_project_action.set_enabled(True)

    # pylint: disable=invalid-name
    def _disable_greeter_keyboard_shortcuts(self):
        self.__new_project_action.set_enabled(False)
        self.__open_project_action.set_enabled(False)

    def show_recent_projects(self):
        """Displays recent projects in a custom layout."""
        # Clear the currently displayed list.
        for child in self.__recent_projects_listbox.get_children():
            self.__recent_projects_listbox.remove(child)

        n_filtered_projects = 0
        recent_items = self.app.recent_manager.get_items()

        for item in recent_items:
            if item.get_display_name().endswith(self.__project_filter):
                n_filtered_projects += 1
                self.__recent_projects_listbox.add(
                    ProjectInfoRow(item.get_display_name(), item.get_uri()))
            if n_filtered_projects >= MAX_RECENT_PROJECTS:
                break

        self.__recent_projects_listbox.show_all()

    @staticmethod
    def __create_project_filter():
        filter_ = []
        for asset in GES.list_assets(GES.Formatter):
            filter_.append(asset.get_meta(GES.META_FORMATTER_EXTENSION))
        return tuple(filter_)

    @staticmethod
    def __create_menu():
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "mainmenubutton.ui"))
        menu_button = builder.get_object("menubutton")
        # Menu options we want to display.
        visible_options = ["menu_shortcuts", "menu_help", "menu_about"]
        n_visible_options = 0
        for widget in builder.get_object("menu").get_children():
            if Gtk.Buildable.get_name(widget) not in visible_options:
                widget.hide()
            else:
                n_visible_options += 1
        assert n_visible_options == len(visible_options)
        return menu_button

    def __new_project_cb(self, unused_action, unused_param):
        self.app.gui.show_editor_perspective()
        self.app.project_manager.newBlankProject()

    def __open_project_cb(self, unused_action, unused_param):
        browse_projects_dialog = BrowseProjectsDialog(self.app)
        response = browse_projects_dialog.run()
        uri = browse_projects_dialog.get_uri()
        browse_projects_dialog.destroy()

        if response == Gtk.ResponseType.OK:
            self.app.gui.show_editor_perspective()
            self.app.project_manager.loadProject(uri)
        else:
            self.app.gui.show_greeter_perspective()

    def __missing_deps_cb(self, unused_button):
        """Handles a click on the Missing Dependencies button."""
        DepsManager(self.app, parent_window=self.app.gui)

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

    def __infobar_response_cb(self, unused_infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()

    def __projects_row_activated_cb(self, unused_listbox, row):
        if self.app.project_manager.loadProject(row.uri):
            self.app.gui.show_editor_perspective()
