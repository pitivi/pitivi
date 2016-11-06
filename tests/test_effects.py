# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the effects module."""
import unittest

from pitivi.effects import EffectInfo


class EffectInfoTest(unittest.TestCase):
    """Tests for the EffectInfo class."""

    def test_bin_description(self):
        """Tests the bin_description property."""
        effect_info = EffectInfo("name", None, None, None, None)
        self.assertEqual(effect_info.bin_description, "name")

        effect_info = EffectInfo("glname", None, None, None, None)
        self.assertEqual(effect_info.bin_description, "glupload ! glname ! gldownload")

    def test_name_from_bin_description(self):
        """Tests the name_from_bin_description method."""
        self.assertEqual(EffectInfo.name_from_bin_description("name"), "name")
        self.assertEqual(EffectInfo.name_from_bin_description("glupload ! glname ! gldownload"), "glname")
