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
"""Tests for the render module."""
from unittest import mock
from unittest import TestCase

from pitivi.preset import RenderPresetManager
from pitivi.render import Encoders
from pitivi.render import extension_for_muxer


class TestRender(TestCase):
    """Tests for functions."""

    def test_extensions_supported(self):
        """Checks we associate file extensions to the well supported muxers."""
        for muxer, unused_audio, unused_video in Encoders.SUPPORTED_ENCODERS_COMBINATIONS:
            self.assertIsNotNone(extension_for_muxer(muxer), muxer)

    def test_extensions_presets(self):
        """Checks we associate file extensions to the muxers of the presets."""
        with mock.patch("pitivi.preset.xdg_data_home") as xdg_data_home:
            xdg_data_home.return_value = "/pitivi-dir-which-does-not-exist"
            preset_manager = RenderPresetManager(system=None, encoders=Encoders())
            preset_manager.loadAll()
            self.assertTrue(preset_manager.presets)
            for unused_name, preset in preset_manager.presets.items():
                muxer = preset["container"]
                self.assertIsNotNone(extension_for_muxer(muxer), preset)
