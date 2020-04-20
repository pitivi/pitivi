# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Guy Richard <guy.richard99@gmail.com>
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
"""Tests for the pitivi.viewer.safe_areas_overlay module."""
# pylint: disable=protected-access,no-self-use
from pitivi.viewer.safe_areas_overlay import SafeAreasOverlay
from tests import common


class TestSafeAreasOverlay(common.TestCase):
    """Tests for the SafeAreasOverlay class."""

    def test_compute_rect(self):
        """Checks the safe areas Cairo rect calculation."""
        self.assertEqual(SafeAreasOverlay._compute_rect(200, 100, 1, 0.5), (0.5, 25.5, 200, 50))
        self.assertEqual(SafeAreasOverlay._compute_rect(200, 100, 0.5, 1), (50.5, 0.5, 100, 100))
