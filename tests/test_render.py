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

from gi.repository import GES
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.preset import RenderPresetManager
from pitivi.render import Encoders
from pitivi.render import extension_for_muxer
from tests import common


class TestRender(common.TestCase):
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

    def test_launching_rendering(self):
        """"Checks no exception is raised when clicking the render button."""
        timeline_container = common.create_timeline_container()
        app = timeline_container.app
        project = app.project_manager.current_project

        mainloop = common.create_main_loop()
        def asset_added_cb(project, asset):
            mainloop.quit()

        project.connect("asset-added", asset_added_cb)
        uris = [common.get_sample_uri("tears_of_steel.webm")]
        project.addUris(uris)
        mainloop.run()

        layer, = project.ges_timeline.get_layers()
        layer.add_asset(project.list_assets(GES.UriClip)[0],
                        0, 0, Gst.CLOCK_TIME_NONE, GES.TrackType.UNKNOWN)

        from pitivi.render import RenderDialog, RenderingProgressDialog

        with mock.patch.object(Gtk.Builder, "__new__"):
            dialog = RenderDialog(app, project)
        with mock.patch.object(dialog, "startAction"):
            with mock.patch.object(RenderingProgressDialog, "__new__"):
                with mock.patch.object(dialog, "_pipeline"):
                    dialog._renderButtonClickedCb(None)
