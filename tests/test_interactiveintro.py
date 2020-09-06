# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.interactiveintro module."""
# pylint: disable=protected-access,unused-argument
from gi.repository import GLib

from tests import common


class TestInteractiveIntro(common.TestCase):

    def test_overview(self):
        app = common.create_pitivi()
        app.gui = None
        app.create_main_window()
        intro = app.gui.editor.intro
        app.project_manager.new_blank_project()

        intro.intro_action.activate()

        def timeout_add(timeout, func, *args):
            func(*args)

        original_timeout_add = GLib.timeout_add
        GLib.timeout_add = timeout_add
        try:
            intro._overview_button_clicked_cb(None)
        finally:
            GLib.timeout_add = original_timeout_add

        self.assertListEqual(intro.tips, [])
