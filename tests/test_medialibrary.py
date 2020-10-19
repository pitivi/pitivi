# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2015, Thibault Saunier <tsaunier@gnome.org>
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
"""Tests for the pitivi.medialibrary module."""
# pylint: disable=attribute-defined-outside-init,protected-access
import os
import tempfile
from unittest import mock

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gst

from pitivi.medialibrary import AssetThumbnail
from pitivi.medialibrary import MediaLibraryWidget
from pitivi.medialibrary import ViewType
from pitivi.project import ProjectManager
from pitivi.utils.misc import ASSET_DURATION_META
from pitivi.utils.misc import asset_get_duration
from pitivi.utils.proxy import ProxyingStrategy
from pitivi.utils.validate import create_event
from tests import common


class BaseTestMediaLibrary(common.TestCase):

    def __init__(self, *args):
        common.TestCase.__init__(self, *args)
        self.app = None
        self.medialibrary = None
        self.mainloop = None

    def tearDown(self):
        self.clean()
        common.TestCase.tearDown(self)

    def clean(self):
        self.mainloop = None
        self.app = None

        if self.medialibrary:
            self.medialibrary.finalize()
            self.medialibrary = None

    def _custom_set_up(self, project_uri=None, **settings):
        # Always make sure we start with a clean medialibrary, and no other
        # is connected to some assets.
        self.clean()

        self.mainloop = common.create_main_loop()
        self.check_no_transcoding = False
        self.app = common.create_pitivi_mock(**settings)
        self.app.project_manager = ProjectManager(self.app)
        self.medialibrary = MediaLibraryWidget(self.app)

        if project_uri:
            self.app.project_manager.load_project(project_uri)
        else:
            self.app.project_manager.new_blank_project()

        self.app.project_manager.current_project.connect(
            "loaded", self.project_loaded_cb)
        self.mainloop.run()

    def project_loaded_cb(self, unused_project, unused_timeline):
        self.mainloop.quit()

    def _progress_bar_cb(self, progressbar, unused_pspec):
        if self.check_no_transcoding:
            self.assertTrue(progressbar.props.fraction == 1.0 or
                            progressbar.props.fraction == 0.0,
                            "Some transcoding is happening, got progress: %f"
                            % progressbar.props.fraction)

        if progressbar.props.fraction == 1.0:
            self.assertEqual(self.medialibrary.store.get_n_items(),
                             len(self.samples))
            self.mainloop.quit()

    def _create_assets(self, samples):
        self.samples = samples
        for sample_name in samples:
            self.app.project_manager.current_project.create_asset(
                common.get_sample_uri(sample_name), GES.UriClip)

    def check_import(self, samples, proxying_strategy=ProxyingStrategy.ALL,
                     check_no_transcoding=False, auto_scaling_enabled=False):
        """Simulates the user importing an asset."""
        self._custom_set_up(proxying_strategy=proxying_strategy,
                            num_transcoding_jobs=4,
                            last_clip_view=ViewType.LIST,
                            auto_scaling_enabled=auto_scaling_enabled)
        self.check_no_transcoding = check_no_transcoding

        self.medialibrary._progressbar.connect(
            "notify::fraction", self._progress_bar_cb)

        self._create_assets(samples)
        self.mainloop.run()
        self.assertFalse(self.medialibrary._progressbar.props.visible)

    def check_add_proxy(self, asset, scaled=False, w=160, h=120,
                        check_progress=True):
        """Simulates the user requesting an asset to be proxied."""
        self.assertFalse(self.app.proxy_manager.is_proxy_asset(asset))

        # Check the initial state of the asset, nothing should be going on.
        self.assertNotIn("Proxy creation progress:",
                         self.medialibrary.store[0].infotext)
        self.assertIn(
            self.medialibrary.store[0].thumb_decorator.state,
            [AssetThumbnail.NO_PROXY, AssetThumbnail.UNSUPPORTED])

        # Check proxy creation.
        was_in_progress = False

        project = self.app.project_manager.current_project
        project.scaled_proxy_width = w
        project.scaled_proxy_height = h

        def check_set_state(self):
            old_set_state(self)
            if self.state == self.IN_PROGRESS:
                nonlocal was_in_progress
                was_in_progress = True

        old_set_state = AssetThumbnail._set_state
        AssetThumbnail._set_state = check_set_state
        try:
            project.use_proxies_for_assets([asset], scaled)

            self.assertIn("Proxy creation progress:",
                          self.medialibrary.store[0].infotext)

            self.mainloop.run(timeout_seconds=10)
        finally:
            AssetThumbnail._set_state = old_set_state

        if check_progress:
            self.assertTrue(was_in_progress)

        # Finally, check the final status of the asset after proxying.
        self.assertNotIn("Proxy creation progress:",
                         self.medialibrary.store[0].infotext)
        if scaled:
            self.assertEqual(
                self.medialibrary.store[0].thumb_decorator.state,
                AssetThumbnail.SCALED)
        else:
            self.assertEqual(
                self.medialibrary.store[0].thumb_decorator.state,
                AssetThumbnail.PROXIED)

        proxy = self.medialibrary.store[0].asset
        self.assertEqual(proxy.props.proxy_target.props.id, asset.props.id)
        # Check if the asset is video or not
        if w:
            stream = proxy.get_info().get_video_streams()[0]
            resolution = [stream.get_width(), stream.get_height()]
            if scaled:
                self.assertEqual(resolution, [w, h])

        return proxy

    def check_disable_proxy(self, proxy, asset, delete=False):
        self.assertFalse(self.app.proxy_manager.is_proxy_asset(asset))
        self.assertTrue(self.app.proxy_manager.is_proxy_asset(proxy))

        self.app.project_manager.current_project.disable_proxies_for_assets(
            [proxy], delete_proxy_file=delete)

        self.assertIsNone(asset.get_proxy())
        self.assertEqual(self.medialibrary.store[0].uri,
                         asset.props.id)

        self.assertEqual(os.path.exists(Gst.uri_get_location(proxy.props.id)),
                         not delete)


class TestMediaLibrary(BaseTestMediaLibrary):

    def test_import_dialog_proxy_filter(self):
        mock_filter = mock.Mock()
        mock_filter.mime_type = "video/mp4"

        self._custom_set_up()
        mlib = self.medialibrary

        # Test HQ Proxies are filtered
        mock_filter.uri = "file:///home/user/Videos/video.mp4.2360382.proxy.mov"
        self.assertFalse(mlib._filter_unsupported(mock_filter))

        # Test Scaled Proxies are filtered
        mock_filter.uri = "file:///home/user/Videos/video.mp4.2360382.300x300.scaledproxy.mov"
        self.assertFalse(mlib._filter_unsupported(mock_filter))

    def stop_using_proxies(self, delete_proxies=False):
        sample_name = "30fps_numeroted_frames_red.mkv"
        self.check_import([sample_name])

        asset_uri = common.get_sample_uri(sample_name)
        proxy = self.medialibrary.store[0].asset

        self.assertEqual(proxy.props.proxy_target.props.id, asset_uri)

        project = self.app.project_manager.current_project
        self.assertIn(proxy, project.list_assets(GES.UriClip))
        project.disable_proxies_for_assets([proxy], delete_proxies)
        self.assertNotIn(proxy, project.list_assets(GES.UriClip))
        self.assertEqual(self.medialibrary.store.get_n_items(),
                         len(self.samples))

        self.assertEqual(self.medialibrary.store[0].uri,
                         asset_uri)

    def test_transcoding_and_reusing(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            # Create proxies.
            self.check_import([sample_name])

            # Try to import again, checking that no transcoding is done.
            self.check_import([sample_name],
                              check_no_transcoding=True)

    def test_disable_proxies(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name],
                              proxying_strategy=ProxyingStrategy.NOTHING,
                              check_no_transcoding=True)

    def test_save_project_with_removed_proxy(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name])

            project = self.app.project_manager.current_project
            asset = GES.UriClipAsset.request_sync(common.get_sample_uri(sample_name))
            target = asset.get_proxy_target()
            self.assertEqual(set(project.list_assets(GES.Extractable)), set([target, asset]))

            # Remove the asset
            self.medialibrary.remove_assets_action.emit("activate", None)

            # Make sure that the project has not assets anymore
            self.assertEqual(project.list_assets(GES.Extractable), [])

            # Save the project and reload it, making sure there is no asset
            # in that new project
            project_uri = Gst.filename_to_uri(tempfile.NamedTemporaryFile().name)
            project.save(project.ges_timeline, project_uri, None, True)

            self._custom_set_up(project_uri)
            self.assertNotEqual(project, self.app.project_manager.current_project)
            project = self.app.project_manager.current_project
            self.assertEqual(project.list_assets(GES.Extractable), [])

    def check_selection_post_import(self, **kwargs):
        samples = ["30fps_numeroted_frames_red.mkv",
                   "30fps_numeroted_frames_blue.webm"]
        with common.cloned_sample(*samples):
            self.check_import(samples, **kwargs)
        self.assertEqual(len(list(self.medialibrary.get_selected_paths())),
                         len(self.samples))

    def test_newly_imported_asset_selected_optimize_all(self):
        self.check_selection_post_import(proxying_strategy=ProxyingStrategy.ALL)

    def test_newly_imported_asset_selected_optimize_automatic(self):
        self.check_selection_post_import(proxying_strategy=ProxyingStrategy.AUTOMATIC)

    def test_newly_imported_asset_selected_optimize_nothing(self):
        self.check_selection_post_import(proxying_strategy=ProxyingStrategy.NOTHING)

    def test_stop_using_proxies(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.stop_using_proxies()

    def test_delete_proxy(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.stop_using_proxies(delete_proxies=True)

            asset = self.medialibrary.store[0].asset
            proxy_uri = self.app.proxy_manager.get_proxy_uri(asset)

            # Requesting UriClip sync will return None if the asset is not in cache
            # this way we make sure that this asset used to exist
            proxy = GES.Asset.request(GES.UriClip, proxy_uri)
            self.assertIsNotNone(proxy)
            self.assertFalse(os.path.exists(Gst.uri_get_location(proxy_uri)))

            self.assertIsNone(asset.get_proxy())

            # And let's recreate the proxy file.
            self.app.project_manager.current_project.use_proxies_for_assets([asset])
            self.assertEqual(asset.creation_progress, 0)

            # Check that the info column notifies the user about progress
            self.assertTrue("Proxy creation progress:" in
                            self.medialibrary.store[0].infotext)

            # Run the mainloop and let _progress_bar_cb stop it when the proxy is
            # ready
            self.mainloop.run()

            self.assertEqual(asset.creation_progress, 100)
            self.assertEqual(asset.get_proxy(), proxy)

    def test_create_and_delete_scaled_proxy(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)
            asset = self.medialibrary.store[0].asset

            # Create scaled proxy
            proxy = self.check_add_proxy(asset, scaled=True)

            # Delete scaled proxy
            self.check_disable_proxy(proxy, asset, delete=True)

    def test_mixed_proxies(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)
            asset = self.medialibrary.store[0].asset

            # Create and disable scaled proxy
            proxy = self.check_add_proxy(asset, scaled=True)
            scaled_uri = self.app.proxy_manager.get_proxy_uri(asset, scaled=True)
            self.check_disable_proxy(proxy, asset)

            # Create and disable HQ proxy
            proxy = self.check_add_proxy(asset)
            hq_uri = self.app.proxy_manager.get_proxy_uri(asset)
            self.check_disable_proxy(proxy, asset)

            # Check both files exist
            self.assertTrue(os.path.exists(Gst.uri_get_location(hq_uri)))
            self.assertTrue(os.path.exists(Gst.uri_get_location(scaled_uri)))

            # Enable and delete scaled proxy
            proxy = self.check_add_proxy(asset, scaled=True,
                                         check_progress=False)
            self.check_disable_proxy(proxy, asset, delete=True)

            # Check that only HQ Proxy exists
            self.assertFalse(os.path.exists(Gst.uri_get_location(scaled_uri)))
            self.assertTrue(os.path.exists(Gst.uri_get_location(hq_uri)))

            # Enable and delete HQ proxy
            proxy = self.check_add_proxy(asset, check_progress=False)
            self.check_disable_proxy(proxy, asset, delete=True)

    def test_proxy_duration_mismatch(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)
            timeline = self.app.project_manager.current_project.ges_timeline

            asset = self.medialibrary.store[0].asset
            clip = timeline.append_layer().add_asset(asset, 0, 0, Gst.CLOCK_TIME_NONE, GES.TrackType.VIDEO)

            duration = 2.5 * Gst.SECOND
            fake_duration = 3 * Gst.SECOND

            asset.set_uint64(ASSET_DURATION_META, fake_duration)
            clip.props.max_duration = fake_duration
            clip.props.duration = fake_duration
            self.assertEqual(clip.props.duration, fake_duration)
            proxy = self.check_add_proxy(asset)

            self.assertEqual(asset_get_duration(asset), duration)
            self.assertEqual(asset_get_duration(proxy), duration)
            self.assertEqual(clip.props.duration, duration)
            self.assertEqual(clip.props.max_duration, duration)

    def test_timeline_proxy_switching(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)

            common.create_timeline_container(self.app)
            timeline = self.app.project_manager.current_project.ges_timeline

            asset = self.medialibrary.store[0].asset
            timeline.append_layer().add_asset(asset, 0, 0, Gst.CLOCK_TIME_NONE,
                                              GES.TrackType.VIDEO)

            def check_timeline_clip(expected_asset):
                for layer in timeline.layers:
                    for clip in layer.get_clips():
                        self.assertEqual(clip.get_asset(), expected_asset)

            # Check asset is in the timeline
            check_timeline_clip(asset)

            # Check asset is replaced by scaled proxy
            scaled_proxy = self.check_add_proxy(asset, scaled=True)
            check_timeline_clip(scaled_proxy)

            # Check proxy is replaced back by asset
            self.check_disable_proxy(scaled_proxy, asset, delete=True)
            check_timeline_clip(asset)

            # Check asset is replaced by HQ proxy
            hq_proxy = self.check_add_proxy(asset)
            check_timeline_clip(hq_proxy)

            # Check proxy was replaced back by asset
            self.check_disable_proxy(hq_proxy, asset, delete=True)
            check_timeline_clip(asset)

    def test_regenerate_scaled_proxy(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)
            asset = self.medialibrary.store[0].asset
            asset_uri = common.get_sample_uri(sample_name)

            # Create scaled proxy
            proxy = self.check_add_proxy(asset, scaled=True)
            proxy_uri = self.app.proxy_manager.get_proxy_uri(asset, scaled=True)

            # Change target resolution and trigger regeneration (1/4 Asset width)
            self.app.project_manager.current_project.scaled_proxy_width = 80
            self.app.project_manager.current_project.scaled_proxy_height = 60

            self.app.project_manager.current_project.regenerate_scaled_proxies()
            self.assertTrue("Proxy creation progress:" in
                            self.medialibrary.store[0].infotext)
            self.mainloop.run()

            proxy = self.medialibrary.store[0].asset
            self.assertNotEqual(proxy.props.id, proxy_uri)

            stream = proxy.get_info().get_video_streams()[0]
            resolution = [stream.get_width(), stream.get_height()]
            self.assertEqual(resolution, [80, 60])
            self.assertEqual(proxy.props.proxy_target.props.id, asset_uri)

            # Delete proxy
            self.check_disable_proxy(proxy, asset, delete=True)
            self.assertFalse(os.path.exists(Gst.uri_get_location(proxy_uri)))

    def test_scaled_proxy_for_unsupported_asset(self):
        sample_name = "1sec_simpsons_trailer.mp4"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.AUTOMATIC)
            asset = self.medialibrary.store[0].asset

            # Mark all formats as unsupported
            with mock.patch.object(self.app.proxy_manager,
                                   "is_asset_format_well_supported",
                                   return_value=False):
                # Create scaled proxy
                proxy = self.check_add_proxy(asset, scaled=True, w=80, h=34)
                proxy_uri = self.app.proxy_manager.get_proxy_uri(asset, scaled=True)
                self.mainloop.run(until_empty=True)

                # Check that HQ proxy was created
                hq_uri = self.app.proxy_manager.get_proxy_uri(asset)
                self.assertTrue(os.path.exists(Gst.uri_get_location(hq_uri)))

                # Delete scaled proxy
                self.check_disable_proxy(proxy, asset, delete=True)
                self.mainloop.run()

                # Check that we revert to HQ proxy
                proxy = self.medialibrary.store[0].asset
                proxy_uri = self.app.proxy_manager.get_proxy_uri(asset, scaled=False)
                self.assertEqual(proxy.props.id, proxy_uri)

                # Delete HQ Proxy
                self.check_disable_proxy(proxy, asset, delete=True)

    def test_load_audio_only(self):
        audio_sample = "mp3_sample.mp3"
        with common.cloned_sample(audio_sample):
            asset_uri = common.get_sample_uri(audio_sample)
            with common.created_project_file(asset_uri) as uri:
                self._custom_set_up(project_uri=uri)

    def test_scale_proxy_audio_post_import(self):
        sample = "mp3_sample.mp3"
        with common.cloned_sample(sample):
            self.check_import([sample], proxying_strategy=ProxyingStrategy.NOTHING)
            asset = self.medialibrary.store[0].asset

            project = self.app.project_manager.current_project
            project.use_proxies_for_assets([asset], scaled=True)

    def test_supported_out_of_container_audio(self):
        sample = "mp3_sample.mp3"
        with common.cloned_sample(sample):
            self.check_import([sample], check_no_transcoding=True,
                              proxying_strategy=ProxyingStrategy.AUTOMATIC)

    def test_import_supported_forced_scaled_audio(self):
        sample = "mp3_sample.mp3"
        with common.cloned_sample(sample):
            self.check_import([sample], auto_scaling_enabled=True)

    def test_missing_uri_displayed(self):
        asset_uri = common.get_sample_uri("image-which-does-not-exist.png")
        with common.created_project_file(asset_uri) as uri:
            self._custom_set_up(project_uri=uri)
        self.assertTrue(self.medialibrary._import_warning_infobar.props.visible)

    def test_right_click_on_media_library(self):
        self._custom_set_up()
        mlib = self.medialibrary

        # Release click
        event = create_event(Gdk.EventType.BUTTON_RELEASE, button=3)
        mlib._flowbox_button_release_event_cb(mlib.flowbox, event)
