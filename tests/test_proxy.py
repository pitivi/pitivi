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
import os
import tempfile
from unittest import mock

from gi.repository import GES
from gi.repository import Gst

from pitivi.utils.proxy import ENCODING_FORMAT_JPEG
from pitivi.utils.proxy import ENCODING_FORMAT_NVENC
from pitivi.utils.proxy import ProxyingStrategy
from pitivi.utils.proxy import ProxyManager
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
        self._check_get_target_uri("file:///home/file.name.mp4.1927006.proxy.nv.mkv",
                                   "file:///home/file.name.mp4")

    def _check_get_proxy_uri(self, asset_uri, expected_uri, size=10, scaled=False,
                             scaled_res=(1280, 720), encoding_target=ENCODING_FORMAT_JPEG):
        app = common.create_pitivi_mock()
        manager = app.proxy_manager
        # Force encoding target so extension selection is deterministic regardless
        # of whether NVENC is available on the test host.
        manager._ProxyManager__encoding_target_file = encoding_target

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

    def test_get_proxy_uri_nvenc_extension(self):
        """BUG-003: NVENC encoding target always uses .proxy.nv.mkv."""
        self._check_get_proxy_uri(
            "file:///home/file.name.mp4",
            "file:///home/file.name.mp4.10.proxy.nv.mkv",
            encoding_target=ENCODING_FORMAT_NVENC)

        # Even with strategy=NOTHING, force_proxying path must still get mkv ext
        # when the encoding target is NVENC (container/extension match).
        app = common.create_pitivi_mock(proxying_strategy=ProxyingStrategy.NOTHING)
        manager = app.proxy_manager
        manager._ProxyManager__encoding_target_file = ENCODING_FORMAT_NVENC
        asset = mock.Mock()
        asset.get_id.return_value = "file:///home/clip.mp4"
        asset.force_proxying = True
        with mock.patch("pitivi.utils.proxy.Gio.File") as gio:
            gio.new_for_uri.return_value = gio
            gio.query_info().get_size.return_value = 42
            result = manager.get_proxy_uri(asset)
        self.assertTrue(result.endswith("." + ProxyManager.nvenc_proxy_extension))
        self.assertFalse(result.endswith("." + ProxyManager.hq_proxy_extension))

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

    def _make_mock_transcoder(self, src_uri, dest_uri, part_path=None):
        """Builds a mock GstTranscoder-like object for queue tests."""
        # Use a plain object so __grefcount__ is a real attribute (Mock mangles
        # dunder names and cancel_job logs transcoder.__grefcount__).
        transcoder = mock.Mock()
        transcoder.props.src_uri = src_uri
        transcoder.props.dest_uri = dest_uri
        transcoder.props.position_update_interval = 1000
        transcoder.props.pipeline = mock.Mock()
        transcoder.get_signal_adapter.return_value = transcoder
        transcoder.__dict__["__grefcount__"] = 1
        return transcoder

    def test_transcoder_error_cb_cleans_up_and_advances_queue(self):
        """BUG-001: error callback frees the slot and starts the next job."""
        app = common.create_pitivi_mock()
        manager = app.proxy_manager

        asset = mock.Mock()
        asset.props.id = "file:///a.mp4"
        asset.get_id.return_value = asset.props.id

        with tempfile.NamedTemporaryFile(
                suffix=".proxy.mov.part", delete=False) as tmp:
            part_path = tmp.name
            tmp.write(b"partial")

        failed = self._make_mock_transcoder(
            asset.props.id, Gst.filename_to_uri(part_path))
        next_job = self._make_mock_transcoder(
            "file:///b.mp4", "file:///b.mp4.10.proxy.mov.part")

        manager._ProxyManager__running_transcoders = [failed]
        manager._ProxyManager__pending_transcoders = [next_job]
        manager._transcoded_durations = {asset: 1.0}
        manager._total_time_to_transcode = 10
        manager._start_proxying_time = 1

        errors = []
        manager.connect("error-preparing-asset",
                        lambda *args: errors.append(args))

        with mock.patch.object(manager, "_ProxyManager__start_transcoder") as start:
            manager._ProxyManager__transcoder_error_cb(
                failed, RuntimeError("boom"), None, asset, failed)

        self.assertEqual(manager._ProxyManager__running_transcoders, [])
        self.assertNotIn(failed, manager._ProxyManager__pending_transcoders)
        self.assertFalse(os.path.exists(part_path))
        self.assertEqual(len(errors), 1)
        start.assert_called_once_with(next_job)
        self.assertNotIn(asset, manager._transcoded_durations)

    def test_cancel_job_stops_pipeline_and_deletes_part(self):
        """BUG-002: cancel stops the pipeline, disconnects, deletes .part."""
        app = common.create_pitivi_mock()
        manager = app.proxy_manager

        asset = mock.Mock()
        asset.props.id = "file:///clip.mp4"

        with tempfile.NamedTemporaryFile(
                suffix=".proxy.mov.part", delete=False) as tmp:
            part_path = tmp.name
            tmp.write(b"partial")

        # dest_uri must end with optimisation/scaling/nvenc + .part so
        # is_asset_queued recognizes the job.
        dest_uri = Gst.filename_to_uri(part_path)
        t1 = self._make_mock_transcoder(asset.props.id, dest_uri)
        t1.props.position_update_interval = 1000

        # Shadow HQ sibling — must also be cancelled (list-copy iteration).
        # Use a second temp path so delete of one does not affect the other.
        with tempfile.NamedTemporaryFile(
                suffix=".proxy.mov.part", delete=False) as tmp2:
            part_path2 = tmp2.name
            tmp2.write(b"partial2")
        dest_uri2 = Gst.filename_to_uri(part_path2)
        t2 = self._make_mock_transcoder(asset.props.id, dest_uri2)
        t2.props.position_update_interval = 1001
        t2.props.pipeline = mock.Mock()
        t2.get_signal_adapter.return_value = t2

        manager._ProxyManager__running_transcoders = [t1, t2]
        manager._ProxyManager__pending_transcoders = []
        manager._transcoded_durations = {asset: 2.0}

        cancelled = []
        manager.connect("asset-preparing-cancelled",
                        lambda *args: cancelled.append(args))

        manager.cancel_job(asset)

        self.assertEqual(manager._ProxyManager__running_transcoders, [])
        self.assertEqual(len(cancelled), 1)
        t1.props.pipeline.set_state.assert_called_with(Gst.State.NULL)
        t2.props.pipeline.set_state.assert_called_with(Gst.State.NULL)
        self.assertFalse(os.path.exists(part_path))
        self.assertFalse(os.path.exists(part_path2))
        self.assertNotIn(asset, manager._transcoded_durations)

        # Late "done" after cancel must not raise or rename.
        with mock.patch("pitivi.utils.proxy.os.rename") as rename:
            manager._ProxyManager__transcoder_done_cb(t1, asset, t1)
        rename.assert_not_called()

    def test_emit_progress_zero_transcoded_seconds(self):
        """BUG-005: ETA must not divide by zero when position is still 0."""
        app = common.create_pitivi_mock()
        manager = app.proxy_manager
        asset = mock.Mock()
        asset.creation_progress = 0

        manager._start_proxying_time = 0
        manager._total_time_to_transcode = 100
        manager._transcoded_durations = {asset: 0}

        progresses = []
        manager.connect("progress", lambda _m, a, p, eta: progresses.append(eta))

        # time.time() - 0 is large; divisor is 0 → must not raise.
        manager._ProxyManager__emit_progress(asset, 0)
        self.assertEqual(progresses, [0])

    def test_raw_video_caps_typo_fixed(self):
        """BUG-006: raw video caps short-circuit uses video/x-raw(ANY)."""
        # Static source inspection — the typo string must be gone.
        import inspect
        source = inspect.getsource(ProxyManager._ProxyManager__get_encoding_profile)
        self.assertNotIn("audio/x-video(ANY)", source)
        self.assertIn("video/x-raw(ANY)", source)
