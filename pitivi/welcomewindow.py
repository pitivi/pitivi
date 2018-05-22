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
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gtk

from pitivi.check import missing_soft_deps
from pitivi.configure import get_ui_dir
from pitivi.dialogs.browseprojects import BrowseProjectsDialog
from pitivi.dialogs.depsmanager import DepsManager
from pitivi.settings import GlobalSettings
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import WELCOME_WINDOW_CSS


GlobalSettings.addConfigSection("welcome-window")
GlobalSettings.addConfigOption('welcome_window_X',
                               section="welcome-window",
                               key="X", default=0, type_=int)
GlobalSettings.addConfigOption('welcome_window_Y',
                               section="welcome-window",
                               key="Y", default=0, type_=int)
GlobalSettings.addConfigOption('welcome_window_width',
                               section="welcome-window",
                               key="width", default=-1, type_=int)
GlobalSettings.addConfigOption('welcome_window_height',
                               section="welcome-window",
                               key="height", default=-1, type_=int)


class RecentProjectRow(Gtk.ListBoxRow):
    """Row of list box displaying recent projects.

    Attributes:
        name: Display name of the project.
        uri: URI of the project.
    """
    def __init__(self, name, uri):
        Gtk.ListBoxRow.__init__(self, selectable=False)
        self.uri = uri
        self.add(Gtk.Label(name))


class WelcomeWindow(Gtk.Widget):
    """Pitivi's Welcome Window.

    Allows the user to:
        - create a new project (New button),
        - load a project (Browse Projects button),
        - load a recently opened project,
        - star a recent project via drag and drop,
        - search through recent or starred projects

    Attributes:
        - app (Pitivi): The app.
    """

    def __init__(self, app):
        Gtk.Widget.__init__(self)

        self.__app = app
        self.__settings = app.settings

        self.__builder = Gtk.Builder()
        self.__builder.add_from_file(os.path.join(get_ui_dir(), "welcomewindow.ui"))

        self.scrolled_window = self.__builder.get_object("scrolled_window")

        self.__recent_projects_listbox = self.__builder.get_object("recent_projects_listbox")
        self.__recent_projects_listbox.connect(
            'row_activated', self.__recent_projects_row_activated_cb)

        self.__infobar = self.__builder.get_object("infobar")
        fix_infobar(self.__infobar)
        self.__infobar.hide()
        self.__infobar.connect("response", self.__infobar_close_button_clicked_cb)

        if self.__app.getLatest():
            self.__app_version_info_received_cb(self.__app, None)
        else:
            self.__app.connect(
                "version-info-received", self.__app_version_info_received_cb)

    def setup_ui(self):
        """Setup the UI for Welcome window."""
        self.__setup_css()
        self.__create_headerbar()

        width = self.__settings.welcome_window_width
        height = self.__settings.welcome_window_height
        if height == -1 and width == -1:
            self.__app.gui.maximize()
        else:
            self.__app.gui.set_default_size(width, height)
            self.__app.gui.move(
                self.__settings.welcome_window_X, self.__settings.welcome_window_Y)

        self.__app.gui.connect("configure-event", self.__configure_cb)

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(WELCOME_WINDOW_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.__app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def __create_headerbar(self):
        self.headerbar = Gtk.HeaderBar()
        self.headerbar.props.show_close_button = True
        self.headerbar.set_title(_("Select a Project"))
        self.__create_headerbar_buttons()
        self.headerbar.show_all()

    def show_recent_projects(self):
        # Clear the currently displayed list.
        for child in self.__recent_projects_listbox.get_children():
            self.__recent_projects_listbox.remove(child)

        filter = []
        for asset in GES.list_assets(GES.Formatter):
            filter.append(asset.get_meta(GES.META_FORMATTER_EXTENSION))

        recent_items = self.__app.recent_manager.get_items()[:10]    # Show upto 10 recent projects.
        for item in recent_items:
            if item.get_display_name().endswith(tuple(filter)):
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

        if missing_soft_deps:
            missing_deps_button = Gtk.Button.new_with_label(_("Missing Dependencies"))
            missing_deps_button.connect("clicked", self.__missing_deps_cb)
            self.headerbar.pack_end(missing_deps_button)

        self.headerbar.pack_start(new_project_button)
        self.headerbar.pack_start(open_project_button)

    def __new_project_cb(self, unused_button):
        """Handles a click on the New (Project) button."""
        self.__app.gui.show_main_window()
        self.__app.project_manager.newBlankProject()

    def __open_project_cb(self, unused_button):
        """Handles a click on the Open (Project) button."""
        BrowseProjectsDialog(self.__app)

    def __missing_deps_cb(self, unused_button):
        """Handles a click on the Missing Dependencies button."""
        DepsManager(self.__app, parent_window=self.__app.gui)

    def __configure_cb(self, unused_widget, unused_event):
        """Saves the welcome window position and size."""
        position = self.__app.gui.get_position()
        self.__settings.welcome_window_X = position.root_x
        self.__settings.welcome_window_Y = position.root_y

        size = self.__app.gui.get_size()
        self.__settings.welcome_window_width = size.width
        self.__settings.welcome_window_height = size.height

    def __app_version_info_received_cb(self, app, unused_version_information):
        """Handles new version info."""
        if app.isLatest():
            # current version, don't show message
            return

        latest_version = app.getLatest()
        if self.__settings.lastCurrentVersion != latest_version:
            # new latest version, reset counter
            self.__settings.lastCurrentVersion = latest_version
            self.__settings.displayCounter = 0

        if self.__settings.displayCounter >= 5:
            # current version info already showed 5 times, don't show again
            return

        # increment counter, create infobar and show info
        self.__settings.displayCounter = self.__settings.displayCounter + 1
        text = _("Pitivi %s is available.") % latest_version
        label = Gtk.Label(label=text)
        self.__infobar.get_content_area().add(label)
        self.__infobar.set_message_type(Gtk.MessageType.INFO)
        self.__infobar.show_all()

    def __infobar_close_button_clicked_cb(self, unused_infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()

    def __recent_projects_row_activated_cb(self, unused_listbox, row):
        if self.__app.project_manager.loadProject(row.uri):
            self.__app.gui.show_main_window()
