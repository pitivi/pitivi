# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2022, Thejas Kiran P S <thejaskiranps@gmail.com>
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
# pylint: disable=protected-access
"""Tests for the pitivi.timeline.ruler module."""
from tests import common


class TestRuler(common.TestCase):
    """Tests for the ScaleRuler class."""

    def test_ruler_scales_sorted(self):
        scales = common.create_timeline_container().ruler._scales

        # Check the scales are sorted correctly.
        self.assertListEqual(sorted(scales), scales)

        # Check the ticks are sorted correctly.
        for unused_interval, ticks in scales:
            self.assertListEqual(sorted(ticks), ticks)
