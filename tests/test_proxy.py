# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Yatin Maan <yatinmaan1@gmail.com>
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
"""Tests for the utils.proxy module."""
# pylint: disable=protected-access
from unittest import mock

from gi.repository import GES

from tests import common


class TestProxyManager(common.TestCase):
    """Tests for the ProxyManager class."""

    def _check_scale_asset_resolution(self, asset_res, max_res, expected_res):
        app = common.create_pitivi_mock()
        manager = app.proxy_manager

        stream = mock.Mock()
        stream.get_width.return_value = asset_res[0]
        stream.get_height.return_value = asset_res[1]

        asset = mock.Mock()
        asset.get_info().get_video_streams.return_value = [stream]

        result = manager._scale_asset_resolution(asset, max_res[0], max_res[1])
        self.assertEqual(result, expected_res)

    def test_scale_asset_resolution(self):
        """Checks the _scale_asset_resolution method."""
        self._check_scale_asset_resolution((1920, 1080), (100, 100), (96, 54))
        self._check_scale_asset_resolution((1080, 1920), (100, 100), (54, 96))
        self._check_scale_asset_resolution((1000, 1000), (100, 100), (100, 100))

        # Unscalable resolutions.
        self._check_scale_asset_resolution((1000, 10), (100, 100), (1000, 10))
        self._check_scale_asset_resolution((10, 1000), (100, 100), (10, 1000))
        self._check_scale_asset_resolution((100, 100), (200, 200), (100, 100))

    def _check_get_target_uri(self, proxy_uri, expected_uri):
        app = common.create_pitivi_mock()
        manager = app.proxy_manager

        asset = mock.Mock(spec=GES.Asset)
        asset.props.id = proxy_uri

        result = manager.get_target_uri(asset)
        self.assertEqual(result, expected_uri)

    def test_get_target_uri(self):
        """Checks the get_target_uri method."""
        self._check_get_target_uri("file:///home/filename.ext.size.scaled_res.scaledproxy.mov",
                                   "file:///home/filename.ext")
        self._check_get_target_uri("file:///home/filename.ext.size.proxy.mov",
                                   "file:///home/filename.ext")
        self._check_get_target_uri("file:///home/file.name.mp4.1927006.1280x720.scaledproxy.mov",
                                   "file:///home/file.name.mp4")
        self._check_get_target_uri("file:///home/file.name.mp4.1927006.proxy.mov",
                                   "file:///home/file.name.mp4")

    def _check_get_proxy_uri(self, asset_uri, expected_uri, size=10, scaled=False, scaled_res=(1280, 720)):
        app = common.create_pitivi_mock()
        manager = app.proxy_manager

        asset = mock.Mock()
        asset.get_id.return_value = asset_uri
        with mock.patch.object(manager, "_scale_asset_resolution") as s_res:
            s_res.return_value = scaled_res
            with mock.patch("pitivi.utils.proxy.Gio.File") as gio:
                gio.new_for_uri.return_value = gio
                gio.query_info().get_size.return_value = size

                result = manager.get_proxy_uri(asset, scaled=scaled)
                self.assertEqual(result, expected_uri)

    def test_get_proxy_uri(self):
        """Checks the get_proxy_uri method."""
        self._check_get_proxy_uri("file:///home/file.name.mp4",
                                  "file:///home/file.name.mp4.10.proxy.mov")
        self._check_get_proxy_uri("file:///home/file.name.mp4",
                                  "file:///home/file.name.mp4.10.1280x720.scaledproxy.mov",
                                  scaled=True)

    def test_asset_matches_target_res(self):
        """Checks the asset_matches_target_res method."""
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        stream = asset.get_info().get_video_streams()[0]
        app = common.create_pitivi_mock()

        for dw in (-1, 0, 1):
            for dh in (-1, 0, 1):
                app.project_manager.current_project.scaled_proxy_width = stream.get_width() + dw
                app.project_manager.current_project.scaled_proxy_height = stream.get_height() + dh
                matches = dw >= 0 and dh >= 0
                self.assertEqual(app.proxy_manager.asset_matches_target_res(asset), matches, (dw, dh))

    def test_asset_can_be_proxied(self):
        """Checks the asset_can_be_proxied method."""
        app = common.create_pitivi_mock()
        manager = app.proxy_manager

        uri = common.get_sample_uri("flat_colour3_320x180.png")
        image = GES.UriClipAsset.request_sync(uri)
        self.assertFalse(manager.asset_can_be_proxied(image))

        uri = common.get_sample_uri("mp3_sample.mp3")
        audio = GES.UriClipAsset.request_sync(uri)
        self.assertTrue(manager.asset_can_be_proxied(audio))
        self.assertFalse(manager.asset_can_be_proxied(audio, scaled=True))
        with mock.patch.object(manager, "is_hq_proxy") as hq:
            hq.return_value = True
            self.assertFalse(manager.asset_can_be_proxied(audio))
            self.assertFalse(manager.asset_can_be_proxied(audio, scaled=True))

        uri = common.get_sample_uri("30fps_numeroted_frames_blue.webm")
        video = GES.UriClipAsset.request_sync(uri)
        self.assertTrue(manager.asset_can_be_proxied(video, scaled=True))
        self.assertTrue(manager.asset_can_be_proxied(video))
        with mock.patch.object(manager, "is_hq_proxy") as hq:
            hq.return_value = True
            self.assertTrue(manager.asset_can_be_proxied(video, scaled=True))
            self.assertFalse(manager.asset_can_be_proxied(video))
        with mock.patch.object(manager, "is_scaled_proxy") as scaled:
            scaled.return_value = True
            with mock.patch.object(manager, "asset_matches_target_res") as matches:
                matches.return_value = False
                self.assertFalse(manager.asset_can_be_proxied(video, scaled=True))
                self.assertTrue(manager.asset_can_be_proxied(video))
                matches.return_value = True
                self.assertTrue(manager.asset_can_be_proxied(video, scaled=True))
                self.assertTrue(manager.asset_can_be_proxied(video))
