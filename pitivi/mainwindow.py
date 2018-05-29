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

from gi.repository import Gtk

from pitivi.editorperspective import EditorPerspective
from pitivi.greeterperspective import GreeterPerspective
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable


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

        Gtk.ApplicationWindow.__init__(self)
        GreeterPerspective.__init__(self, app)
        EditorPerspective.__init__(self, app)
        Loggable.__init__(self)

        self.log("Creating main window")
        self.current_active_child = None

    def setup_ui(self):
        """Sets up the various perspectives's UI."""
        self.log("Setting up the UI of Greeter and Editor perspective.")
        self.setup_greeter_perspective_ui()
        self.setup_editor_perspective_ui()

        width = self.app.settings.mainWindowWidth
        height = self.app.settings.mainWindowHeight

        if height == -1 and width == -1:
            self.maximize()
        else:
            self.set_default_size(width, height)
            self.move(self.app.settings.mainWindowX, self.app.settings.mainWindowY)

        self.connect("configure-event", self._configure_cb)

    def _configure_cb(self, unused_widget, unused_event):
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
        if self.current_active_child == "greeter_perspective":
            return
        if self.current_active_child == "editor_perspective":
            self.remove(self.vpaned)
        self.current_active_child = "greeter_perspective"
        self.set_titlebar(self.greeter_headerbar)
        self.show_recent_projects()
        self.add(self.scrolled_window)
        self.log("Displaying Greeter perspective.")

    def show_editor_perspective(self):
        """Shows Editor perspective."""
        if self.current_active_child == "editor_perspective":
            return
        if self.current_active_child == "greeter_perspective":
            self.remove(self.scrolled_window)
        self.current_active_child = "editor_perspective"
        self.set_titlebar(self.editor_headerbar)
        self.add(self.vpaned)
        self.log("Displaying Editor perspective.")
