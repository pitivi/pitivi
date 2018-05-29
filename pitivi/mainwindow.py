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
from pitivi.perspectivemanager import PerspectiveManager
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

        self.__settings = app.settings
        self.perspective_manager = PerspectiveManager(self)

    def setup_ui(self):
        """Sets up UI of Greeter window and Editor window"""
        self.log("Setting up the UI of Greeter window and Editor window.")
        self.setup_greeter_window_ui()
        self.setup_editor_window_ui()

        width = self.__settings.mainWindowWidth
        height = self.__settings.mainWindowHeight

        if height == -1 and width == -1:
            self.maximize()
        else:
            self.set_default_size(width, height)
            self.move(self.__settings.mainWindowX, self.__settings.mainWindowY)

        self.connect("configure-event", self._configure_cb)

    def _configure_cb(self, unused_widget, unused_event):
        """Saves the main window position and size."""
        # Takes window manager decorations into account.
        position = self.get_position()
        self.__settings.mainWindowX = position.root_x
        self.__settings.mainWindowY = position.root_y

        # Does not include the size of the window manager decorations.
        size = self.get_size()
        self.__settings.mainWindowWidth = size.width
        self.__settings.mainWindowHeight = size.height
