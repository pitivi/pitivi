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
"""Interface for different perspectives."""
from gi.repository import Gtk


class Perspective(Gtk.Widget):
    """Interface for different perspectives."""

    def __init__(self):
        Gtk.Widget.__init__(self)
        self.parent_widget = None
        self.headerbar = None
        self.menu_button = None

    def setup_ui(self):
        """Sets up the UI of the perspective."""
        raise NotImplementedError()

    def setup_css(self):
        """Sets up CSS for the perspective."""
        raise NotImplementedError()

    def create_headerbar(self):
        """Creates headerbar for the perspective."""
        raise NotImplementedError()

    def set_keyboard_shortcuts(self):
        """Sets up keyboard shortcuts for the perspective."""
        raise NotImplementedError()

    def enable_keyboard_shortcuts(self):
        """Enables perspective's keyboard shortcuts."""
        raise NotImplementedError()

    def disable_keyboard_shortcuts(self):
        """Disables perspective's keyboard shortcuts."""
        raise NotImplementedError()
