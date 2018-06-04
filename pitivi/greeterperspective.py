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

from pitivi.configure import get_ui_dir
from pitivi.dialogs.browseprojects import BrowseProjectsDialog
from pitivi.perspective import Perspective
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import GREETER_PERSPECTIVE_CSS

MAX_RECENT_PROJECTS = 10


class ProjectInfoRow(Gtk.ListBoxRow):
    """Displays a project's info.

    Attributes:
        project: Project's meta-data.
    """
    def __init__(self, project):
        Gtk.ListBoxRow.__init__(self)
        self.uri = project.get_uri()
        self.add(Gtk.Label(project.get_display_name(), xalign=0))


# pylint: disable=too-many-instance-attributes
class GreeterPerspective(Gtk.Widget, Perspective):
    """Pitivi's Welcome/Greeter perspective.

    Allows the user to create a new project or open an existing one.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Gtk.Widget.__init__(self)
        Perspective.__init__(self)

        self.app = app
        self.__new_project_action = None
        self.__open_project_action = None

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "greeter.ui"))

        self.toplevel_widget = builder.get_object("scrolled_window")

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
            self.__show_newer_available_version()
        else:
            app.connect("version-info-received", self.__app_version_info_received_cb)

    def setup_ui(self):
        """Sets up the UI."""
        self.__setup_css()
        self.headerbar = self.__create_headerbar()
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
        headerbar.set_show_close_button(True)
        headerbar.set_title(_("Select a Project"))

        new_project_button = Gtk.Button.new_with_label(_("New"))
        new_project_button.set_tooltip_text(_("Create a new project"))
        new_project_button.set_action_name("win.new-project")

        open_project_button = Gtk.Button.new_with_label(_("Open"))
        open_project_button.set_tooltip_text(_("Open an existing project"))
        open_project_button.set_action_name("win.open-project")

        self.menu_button = self.__create_menu()

        headerbar.pack_start(new_project_button)
        headerbar.pack_start(open_project_button)
        headerbar.pack_end(self.menu_button)
        headerbar.show_all()

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
        self.set_actions_enabled(False)

    def set_actions_enabled(self, enabled):
        """Enables/Disables actions."""
        self.__new_project_action.set_enabled(enabled)
        self.__open_project_action.set_enabled(enabled)

    def show_recent_projects(self):
        """Displays recent projects."""
        # Clear the currently displayed list.
        for child in self.__recent_projects_listbox.get_children():
            self.__recent_projects_listbox.remove(child)

        recent_items = [item for item in self.app.recent_manager.get_items()
                        if item.get_display_name().endswith(self.__project_filter)]

        for item in recent_items[:MAX_RECENT_PROJECTS]:
            self.__recent_projects_listbox.add(ProjectInfoRow(item))

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
        for widget in builder.get_object("menu").get_children():
            if Gtk.Buildable.get_name(widget) not in visible_options:
                widget.hide()
            else:
                visible_options.remove(Gtk.Buildable.get_name(widget))
        assert not visible_options
        return menu_button

    def __new_project_cb(self, unused_action, unused_param):
        self.app.project_manager.newBlankProject()

    def __open_project_cb(self, unused_action, unused_param):
        dialog = BrowseProjectsDialog(self.app)
        response = dialog.run()
        uri = dialog.get_uri()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.app.project_manager.loadProject(uri)

    def __app_version_info_received_cb(self, app, unused_version_information):
        """Handles new version info."""
        if app.isLatest():
            # current version, don't show message
            return
        self.__show_newer_available_version()

    def __show_newer_available_version(self):
        latest_version = self.app.getLatest()

        if self.app.settings.lastCurrentVersion != latest_version:
            # new latest version, reset counter
            self.app.settings.lastCurrentVersion = latest_version
            self.app.settings.displayCounter = 0

        if self.app.settings.displayCounter >= 5:
            # current version info already showed 5 times, don't show again
            return

        # increment counter, create infobar and show info
        self.app.settings.displayCounter += 1
        text = _("Pitivi %s is available.") % latest_version
        label = Gtk.Label(label=text)
        self.__infobar.get_content_area().add(label)
        self.__infobar.set_message_type(Gtk.MessageType.INFO)
        self.__infobar.show_all()

    def __infobar_response_cb(self, unused_infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()

    def __projects_row_activated_cb(self, unused_listbox, row):
        self.app.project_manager.loadProject(row.uri)
