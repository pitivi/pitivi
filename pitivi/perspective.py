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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Interface for different perspectives."""


class Perspective():
    """Interface for different perspectives."""

    def __init__(self):
        self.toplevel_widget = None
        self.headerbar = None
        self.menu_button = None

    def setup_ui(self):
        """Sets up the UI of the perspective.

        Populates the toplevel_widget, headerbar and menu_button attributes.
        """
        raise NotImplementedError()

    def activate_compact_mode(self):
        """Shrinks widgets to suit better a small screen."""

    def refresh(self):
        """Refreshes the perspective while activating it."""
        raise NotImplementedError()
