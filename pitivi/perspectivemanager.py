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
"""Manages UI of Greeter window and Editor window."""
from pitivi.utils.loggable import Loggable


class PerspectiveManager(Loggable):
    """
        Manages the switch between Greeter window and Main window.

        Attributes:
            - main_window: Pitivi's main window.
    """

    def __init__(self, main_window):
        Loggable.__init__(self)

        self.current_active_child = None
        self.__main_window = main_window

    def show_greeter_window(self):
        """Shows Greeter window."""
        if self.current_active_child == "greeter_window":
            return
        if self.current_active_child == "editor_window":
            self.__main_window.remove(self.__main_window.vpaned)
        self.current_active_child = "greeter_window"
        self.__main_window.set_titlebar(self.__main_window.greeter_headerbar)
        self.__main_window.show_recent_projects()
        self.__main_window.add(self.__main_window.scrolled_window)
        self.log("Displaying Greeter window.")

    def show_editor_window(self):
        """Shows Editor window."""
        if self.current_active_child == "editor_window":
            return
        if self.current_active_child == "greeter_window":
            self.__main_window.remove(self.__main_window.scrolled_window)
        self.current_active_child = "editor_window"
        self.__main_window.set_titlebar(self.__main_window.editor_headerbar)
        self.__main_window.add(self.__main_window.vpaned)
        self.log("Displaying Editor window.")
