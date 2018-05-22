# -*- coding: utf-8 -*-
# Pitivi video editor
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

from gi.repository import GObject
from gi.repository import Gtk

from pitivi.mainwindow import MainWindow
from pitivi.utils.loggable import Loggable
from pitivi.welcomewindow import WelcomeWindow


class WindowsManager(Gtk.ApplicationWindow, MainWindow, Loggable):
    """
        Manages UI of Welcome window and Main window.
        It also handles the switch between Welcome window and Main window.
    """

    __gsignals__ = {
        "welcome-window-loaded": (GObject.SIGNAL_RUN_LAST, None, ()),
        "main-window-loaded": (GObject.SIGNAL_RUN_LAST, None, ())
    }

    def __init__(self, app):
        gtksettings = Gtk.Settings.get_default()
        gtksettings.set_property("gtk-application-prefer-dark-theme", True)
        theme = gtksettings.get_property("gtk-theme-name")
        os.environ["GTK_THEME"] = theme + ":dark"

        Gtk.ApplicationWindow.__init__(self)
        MainWindow.__init__(self, app)
        Loggable.__init__(self)

        self.current_active_child = None
        self.__welcome_window = WelcomeWindow(app)

    def setup_ui(self):
        """Sets up UI of Welcome window and Main window"""
        self.log("Setting up the UI of Welcome window and Main window.")
        self.__welcome_window.setup_ui()
        self.setup_main_window_ui()

    def show_welcome_window(self):
        if self.current_active_child == "welcome_window":
            return
        if self.current_active_child == "main_window":
            self.remove(self.vpaned)
        self.current_active_child = "welcome_window"
        self.set_titlebar(self.__welcome_window.headerbar)
        self.__welcome_window.show_recent_projects()
        self.add(self.__welcome_window.scrolled_window)
        self.emit("welcome-window-loaded")
        self.log("Displaying Welcome window.")

    def show_main_window(self):
        if self.current_active_child == "main_window":
            return
        if self.current_active_child == "welcome_window":
            self.remove(self.__welcome_window.scrolled_window)
        self.current_active_child = "main_window"
        self.set_titlebar(self.headerbar)
        self.add(self.vpaned)
        self.emit("main-window-loaded")
        self.log("Displaying Main window.")
