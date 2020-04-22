# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2014, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.clipalignment module."""
# pylint: disable=protected-access,no-self-use
# from unittest import mock
# from gi.repository import Gtk
# from tests.test_timeline_timeline import BaseTestTimeline
from pitivi.clipalignment import AlignmentEditor
from tests import common


class AlignmentEditorTest(common.TestCase):
    """Tests for the AlignmentEditor class."""

    def setup_custom_widget(self):
        timeline_container = common.create_timeline_container()
        app = timeline_container.app
        widget = AlignmentEditor(app)
        # project = timeline_container._project

        return widget

    def test_practice_test(self):
        test = self.setup_custom_widget()
        print(test)

    def test_get_cursor_positions(self):
        pass
        # widget = self.setup_custom_widget()
        # self._mouse_x = 50
        # self._mouse_y = 70
        # self.assertEqual([1, 1], 20, 40, AlignmentEditor.get_cursor_positons(self))
