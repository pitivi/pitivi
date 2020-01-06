# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the mainwindow module."""
# pylint: disable=no-self-use,protected-access
from unittest import mock

from pitivi.application import Pitivi
from pitivi.mainwindow import MainWindow
from tests import common


class MainWindowTest(common.TestCase):
    """Tests for the MainWindow class."""

    def test_create(self):
        """Exercise creating the main window."""
        app = Pitivi()
        app._setup()
        app.create_main_window()

    def test_create_small(self):
        """Exercise creating the main window when the screen is small."""
        with mock.patch.object(MainWindow, "_small_screen") as small_screen:
            small_screen.return_value = True
            with mock.patch.object(MainWindow, "get_preferred_size") as get:
                get.return_value = mock.Mock(), None
                app = Pitivi()
                app._setup()
                app.create_main_window()
