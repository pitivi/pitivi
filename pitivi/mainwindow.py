# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
"""Pitivi's main window."""
import os
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import Gtk

from pitivi.configure import get_pixmap_dir
from pitivi.dialogs.about import AboutDialog
from pitivi.editorperspective import EditorPerspective
from pitivi.greeterperspective import GreeterPerspective
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import show_user_manual


GlobalSettings.addConfigOption('mainWindowX',
                               section="main-window",
                               key="X", default=0, type_=int)
GlobalSettings.addConfigOption('mainWindowY',
                               section="main-window",
                               key="Y", default=0, type_=int)
GlobalSettings.addConfigOption('mainWindowWidth',
                               section="main-window",
                               key="width", default=-1, type_=int)
GlobalSettings.addConfigOption('mainWindowHeight',
                               section="main-window",
                               key="height", default=-1, type_=int)

GlobalSettings.addConfigSection('export')
GlobalSettings.addConfigOption('lastExportFolder',
                               section='export',
                               key="last-export-folder",
                               environment="PITIVI_EXPORT_FOLDER",
                               default=os.path.expanduser("~"))

GlobalSettings.addConfigSection("version")
GlobalSettings.addConfigOption('displayCounter',
                               section='version',
                               key='info-displayed-counter',
                               default=0)
GlobalSettings.addConfigOption('lastCurrentVersion',
                               section='version',
                               key='last-current-version',
                               default='')

GREETER_PERSPECTIVE, EDITOR_PERSPECTIVE = range(2)


class MainWindow(Gtk.ApplicationWindow, GreeterPerspective,
                 EditorPerspective, Loggable):
    """Pitivi's main window.

    It manages the UI and handles the switch between different perspectives,
    such as the default GreeterPerspective, and the EditorPerspective.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        gtksettings = Gtk.Settings.get_default()
        gtksettings.set_property("gtk-application-prefer-dark-theme", True)
        theme = gtksettings.get_property("gtk-theme-name")
        os.environ["GTK_THEME"] = theme + ":dark"

        # Pulseaudio "role"
        # (http://0pointer.de/blog/projects/tagging-audio.htm)
        os.environ["PULSE_PROP_media.role"] = "production"
        os.environ["PULSE_PROP_application.icon_name"] = "pitivi"

        Gtk.IconTheme.get_default().append_search_path(get_pixmap_dir())

        Gtk.ApplicationWindow.__init__(self)
        GreeterPerspective.__init__(self, app)
        EditorPerspective.__init__(self, app)
        Loggable.__init__(self)

        self.log("Creating main window")
        self.perspective = None
        self.app = app
        self.__help_action = None
        self.__about_action = None
        self.__main_menu_action = None

    def setup_ui(self):
        """Sets up the various perspectives's UI."""
        self.log("Setting up the UI of Greeter and Editor perspective.")

        self.set_icon_name("pitivi")
        self._setup_greeter_perspective_ui()
        self._setup_editor_perspective_ui()
        self.__check_screen_constraints()
        self.__set_keyboard_shortcuts()

        width = self.app.settings.mainWindowWidth
        height = self.app.settings.mainWindowHeight

        if height == -1 and width == -1:
            self.maximize()
        else:
            self.set_default_size(width, height)
            self.move(self.app.settings.mainWindowX, self.app.settings.mainWindowY)

        self.connect("configure-event", self.__configure_cb)

    def __check_screen_constraints(self):
        """Measures the approximate minimum size required by the main window.

        Shrinks some widgets to fit better on smaller screen resolutions.
        """
        # This code works, but keep in mind get_preferred_size's output
        # is only an approximation. As of 2015, GTK still does not have
        # a way, even with client-side decorations, to tell us the exact
        # minimum required dimensions of a window.
        min_size, _ = self.get_preferred_size()
        screen_width = self.get_screen().get_width()
        screen_height = self.get_screen().get_height()
        self.debug("Minimum UI size is %sx%s", min_size.width, min_size.height)
        self.debug("Screen size is %sx%s", screen_width, screen_height)
        if min_size.width >= 0.9 * screen_width:
            self.medialibrary.activateCompactMode()
            self.viewer.activateCompactMode()
            min_size, _ = self.get_preferred_size()
            self.info("Minimum UI size has been reduced to %sx%s",
                      min_size.width, min_size.height)

    def __set_keyboard_shortcuts(self):
        self.__help_action = Gio.SimpleAction.new("help", None)
        self.__help_action.connect("activate", self.__user_manual_cb)
        self.add_action(self.__help_action)
        self.app.shortcuts.add("win.help", ["F1"], _("Help"), group="app")

        self.__about_action = Gio.SimpleAction.new("about", None)
        self.__about_action.connect("activate", self.__about_cb)
        self.add_action(self.__about_action)
        self.app.shortcuts.add("win.about", ["<Primary><Shift>a"], _("About"), group="app")

        self.__main_menu_action = Gio.SimpleAction.new("menu-button", None)
        self.__main_menu_action.connect("activate", self.__menu_cb)
        self.add_action(self.__main_menu_action)
        self.app.shortcuts.add("win.menu-button", ["F10"],
                               _("Show the menu button content"), group="app")

    @staticmethod
    def __user_manual_cb(unused_action, unused_param):
        show_user_manual()

    def __about_cb(self, unused_action, unused_param):
        about_dialog = AboutDialog(self.app)
        about_dialog.show()

    def __menu_cb(self, unused_action, unused_param):
        if self.perspective == GREETER_PERSPECTIVE:
            self._greeter_menu_button.set_active(not self._greeter_menu_button.get_active())
        elif self.perspective == EDITOR_PERSPECTIVE:
            self._editor_menu_button.set_active(not self._editor_menu_button.get_active())

    def __configure_cb(self, unused_widget, unused_event):
        """Saves the main window position and size."""
        # Takes window manager decorations into account.
        position = self.get_position()
        self.app.settings.mainWindowX = position.root_x
        self.app.settings.mainWindowY = position.root_y

        # Does not include the size of the window manager decorations.
        size = self.get_size()
        self.app.settings.mainWindowWidth = size.width
        self.app.settings.mainWindowHeight = size.height

    def show_greeter_perspective(self):
        """Shows Greeter perspective."""
        if self.perspective == GREETER_PERSPECTIVE:
            return
        self.__remove_current_perspective()
        self.perspective = GREETER_PERSPECTIVE
        self.set_titlebar(self._greeter_headerbar)
        self.show_recent_projects()
        self._enable_greeter_keyboard_shortcuts()
        self.add(self.scrolled_window)
        self.log("Displaying Greeter perspective.")

    def show_editor_perspective(self):
        """Shows Editor perspective."""
        if self.perspective == EDITOR_PERSPECTIVE:
            return
        self.__remove_current_perspective()
        self.perspective = EDITOR_PERSPECTIVE
        self.set_titlebar(self._editor_headerbar)
        self._enable_editor_keyboard_shortcuts()
        self.add(self.vpaned)
        self.log("Displaying Editor perspective.")

    def __remove_current_perspective(self):
        if self.perspective == GREETER_PERSPECTIVE:
            self._disable_greeter_keyboard_shortcuts()
            self.remove(self.scrolled_window)
        elif self.perspective == EDITOR_PERSPECTIVE:
            self._disable_editor_keyboard_shortcuts()
            self.remove(self.vpaned)
