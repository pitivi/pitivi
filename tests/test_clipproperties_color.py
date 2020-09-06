# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (C) 2020 Andrew Hazel, Thomas Braccia, Troy Ogden, Robert Kirkpatrick
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
"""Tests for the pitivi.clip_properties.color module."""
# pylint: disable=protected-access
from unittest import mock

from gi.repository import GES

from tests import common


class ColorPropertiesTest(common.TestCase):
    """Tests for the ColorProperties class."""

    @common.setup_timeline
    @common.setup_clipproperties
    def test_create_hard_coded(self):
        """Exercise creation of a color test clip."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)

        self.clipproperties.create_color_clip_cb(None)
        clips = self.layer.get_clips()
        pattern = clips[0].get_vpattern()
        self.assertEqual(pattern, GES.VideoTestPattern.SOLID_COLOR)

        self.action_log.undo()
        self.assertListEqual(self.layer.get_clips(), [])

        self.action_log.redo()
        self.assertListEqual(self.layer.get_clips(), clips)

    @common.setup_timeline
    @common.setup_clipproperties
    def test_color_change(self):
        """Exercise the changing of colors for color clip."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)

        self.clipproperties.create_color_clip_cb(None)

        mainloop = common.create_main_loop()
        mainloop.run(until_empty=True)

        color_expander = self.clipproperties.color_expander
        color_picker_mock = mock.Mock()
        color_picker_mock.calculate_argb.return_value = 1 << 24 | 2 << 16 | 3 << 8 | 4
        color_expander._color_picker_value_changed_cb(color_picker_mock)
        color = color_expander.source.get_child_property("foreground-color")[1]
        self.assertEqual(color, 0x1020304)
