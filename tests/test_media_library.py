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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import os
import tempfile
from gettext import gettext as _
from unittest import mock

from gi.repository import GES
from gi.repository import Gst

from pitivi import medialibrary
from pitivi.project import ProjectManager
from pitivi.timeline import timeline
from pitivi.utils.proxy import ProxyingStrategy
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

    def _customSetUp(self, project_uri=None, **kwargs):
        # Always make sure we start with a clean medialibrary, and no other
        # is connected to some assets.
        self.clean()

        self.mainloop = common.create_main_loop()
        self.check_no_transcoding = False
        self.app = common.create_pitivi_mock(**kwargs)
        self.app.project_manager = ProjectManager(self.app)
        self.medialibrary = medialibrary.MediaLibraryWidget(self.app)

        if project_uri:
            self.app.project_manager.loadProject(project_uri)
        else:
            self.app.project_manager.newBlankProject()

        self.app.project_manager.current_project.connect(
            "loaded", self.projectLoadedCb)
        self.mainloop.run()

    def projectLoadedCb(self, unused_project, unused_timeline):
        self.mainloop.quit()

    def _progressBarCb(self, progressbar, unused_pspec):
        if self.check_no_transcoding:
            self.assertTrue(progressbar.props.fraction == 1.0 or
                            progressbar.props.fraction == 0.0,
                            "Some transcoding is happening, got progress: %f"
                            % progressbar.props.fraction)

        if progressbar.props.fraction == 1.0:
            self.assertEqual(len(self.medialibrary.storemodel),
                             len(self.samples))
            self.mainloop.quit()

    def _createAssets(self, samples):
        self.samples = samples
        for sample_name in samples:
            self.app.project_manager.current_project.create_asset(
                common.get_sample_uri(sample_name), GES.UriClip)

    def check_import(self, assets, proxying_strategy=ProxyingStrategy.ALL,
                     check_no_transcoding=False):
        self._customSetUp(proxyingStrategy=proxying_strategy,
                          numTranscodingJobs=4,
                          lastClipView=medialibrary.SHOW_TREEVIEW)
        self.check_no_transcoding = check_no_transcoding

        self.medialibrary._progressbar.connect(
            "notify::fraction", self._progressBarCb)

        self._createAssets(assets)
        self.mainloop.run()
        self.assertFalse(self.medialibrary._progressbar.props.visible)

    def check_add_proxy(self, asset, asset_uri, scaled=False, w=160, h=120,
            check_progress=True):
        proxy_uri = self.app.proxy_manager.getProxyUri(asset, scaled=scaled)
        was_in_progress = False

        self.app.project_manager.current_project.scaled_proxy_width = w
        self.app.project_manager.current_project.scaled_proxy_height = h

        project = self.app.project_manager.current_project

        def check_set_state(self):
            old_set_state(self)
            if self.state == self.IN_PROGRESS:
                nonlocal was_in_progress
                was_in_progress = True

        try:
            old_set_state = medialibrary.AssetThumbnail._setState

            # Check proxy creation progress and thumbnail icon
            self.assertFalse("Proxy creation progress:" in
                self.medialibrary.storemodel[0][medialibrary.COL_INFOTEXT])
            no_proxy = medialibrary.AssetThumbnail.NO_PROXY
            unsupported = medialibrary.AssetThumbnail.UNSUPPORTED
            # Check that inital state of asset is no-proxy or unsupported
            self.assertTrue(
                self.medialibrary.storemodel[0][medialibrary.COL_THUMB_DECORATOR].state == no_proxy or
                self.medialibrary.storemodel[0][medialibrary.COL_THUMB_DECORATOR].state == unsupported)

            medialibrary.AssetThumbnail._setState = check_set_state
            project.use_proxies_for_assets([asset], scaled)

            self.assertTrue("Proxy creation progress:" in
                self.medialibrary.storemodel[0][medialibrary.COL_INFOTEXT])

            self.mainloop.run(timeout_seconds=10)
        finally:
            medialibrary.AssetThumbnail._setState = old_set_state

        if check_progress:
            self.assertTrue(was_in_progress)

        self.assertFalse("Proxy creation progress:" in
            self.medialibrary.storemodel[0][medialibrary.COL_INFOTEXT])
        if scaled:
            self.assertEqual(medialibrary.AssetThumbnail.SCALED,
                self.medialibrary.storemodel[0][medialibrary.COL_THUMB_DECORATOR].state)
        else:
            self.assertEqual(medialibrary.AssetThumbnail.PROXIED,
                self.medialibrary.storemodel[0][medialibrary.COL_THUMB_DECORATOR].state)

        proxy = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]
        stream = proxy.get_info().get_video_streams()[0]
        resolution = [stream.get_width(), stream.get_height()]
        self.assertEqual(proxy.props.proxy_target.props.id, asset_uri)
        if scaled:
            self.assertEqual(resolution, [w, h])

        return proxy

    def check_disable_proxy(self, asset, asset_uri, proxy, proxy_uri, delete=False):
        self.app.project_manager.current_project.disable_proxies_for_assets([proxy],
            delete_proxy_file=delete)

        self.assertIsNone(asset.get_proxy())
        self.assertEqual(self.medialibrary.storemodel[0][medialibrary.COL_URI],
                         asset_uri)

        if delete:
            self.assertFalse(os.path.exists(Gst.uri_get_location(proxy_uri)))


class TestMediaLibrary(BaseTestMediaLibrary):
    def test_import_dialog_proxy_filter(self):
        mock_filter = mock.Mock()
        mock_filter.mime_type = "video/mp4"

        self._customSetUp()
        mlib = self.medialibrary

        # Test HQ Proxies are filtered
        mock_filter.uri = "file:///home/user/Videos/video.mp4.2360382.proxy.mkv"
        self.assertFalse(mlib._filter_unsupported(mock_filter))

        # Test Scaled Proxies are filtered
        mock_filter.uri = "file:///home/user/Videos/video.mp4.2360382.300x300.scaledproxy.mkv"
        self.assertFalse(mlib._filter_unsupported(mock_filter))

    def stop_using_proxies(self, delete_proxies=False):
        sample_name = "30fps_numeroted_frames_red.mkv"
        self.check_import([sample_name])

        asset_uri = common.get_sample_uri(sample_name)
        proxy = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]

        self.assertEqual(proxy.props.proxy_target.props.id, asset_uri)

        project = self.app.project_manager.current_project
        self.assertIn(proxy, project.list_assets(GES.UriClip))
        project.disable_proxies_for_assets([proxy], delete_proxies)
        self.assertNotIn(proxy, project.list_assets(GES.UriClip))
        self.assertEqual(len(self.medialibrary.storemodel),
                         len(self.samples))

        self.assertEqual(self.medialibrary.storemodel[0][medialibrary.COL_URI],
                         asset_uri)

    def test_transcoding_and_reusing(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            # Create proxies.
            self.check_import([sample_name])

            # Try to import again, checking that no transcoding is done.
            self.check_import([sample_name],
                              check_no_transcoding=True)

    def testDisableProxies(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name],
                              proxying_strategy=ProxyingStrategy.NOTHING,
                              check_no_transcoding=True)

    def testSaveProjectWithRemovedProxy(self):
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

            self._customSetUp(project_uri)
            self.assertNotEqual(project, self.app.project_manager.current_project)
            project = self.app.project_manager.current_project
            self.assertEqual(project.list_assets(GES.Extractable), [])

    def testNewlyImportedAssetSelected(self):
        samples = ["30fps_numeroted_frames_red.mkv",
                   "30fps_numeroted_frames_blue.webm"]
        with common.cloned_sample(*samples):
            self.check_import(samples)

        self.assertEqual(len(list(self.medialibrary.getSelectedPaths())),
                         len(self.samples))

    def test_stop_using_proxies(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.stop_using_proxies()

    def test_delete_proxy(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.stop_using_proxies(delete_proxies=True)

            asset = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]
            proxy_uri = self.app.proxy_manager.getProxyUri(asset)

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
                self.medialibrary.storemodel[0][medialibrary.COL_INFOTEXT])

            # Run the mainloop and let _progressBarCb stop it when the proxy is
            # ready
            self.mainloop.run()

            self.assertEqual(asset.creation_progress, 100)
            self.assertEqual(asset.get_proxy(), proxy)

    def test_create_and_delete_scaled_proxy(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)
            asset = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]
            asset_uri = common.get_sample_uri(sample_name)

            # Create scaled proxy
            proxy = self.check_add_proxy(asset, asset_uri, scaled=True)
            proxy_uri = self.app.proxy_manager.getProxyUri(asset, scaled=True)

            # Delete scaled proxy
            self.check_disable_proxy(asset, asset_uri, proxy, proxy_uri, delete=True)

    def test_mixed_proxies(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)
            asset = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]
            asset_uri = common.get_sample_uri(sample_name)

            # Create and disable scaled proxy
            proxy = self.check_add_proxy(asset, asset_uri, scaled=True)
            scaled_uri = self.app.proxy_manager.getProxyUri(asset, scaled=True)
            self.check_disable_proxy(asset, asset_uri, proxy, scaled_uri)

            # Create and disable HQ proxy
            proxy = self.check_add_proxy(asset, asset_uri)
            hq_uri = self.app.proxy_manager.getProxyUri(asset)
            self.check_disable_proxy(asset, asset_uri, proxy, hq_uri)

            # Check both files exist
            self.assertTrue(os.path.exists(Gst.uri_get_location(hq_uri)))
            self.assertTrue(os.path.exists(Gst.uri_get_location(scaled_uri)))

            # Enable and delete scaled proxy
            proxy = self.check_add_proxy(asset, asset_uri, scaled=True,
                check_progress=False)
            self.check_disable_proxy(asset, asset_uri, proxy, scaled_uri, delete=True)

            # Check that only HQ Proxy exists
            self.assertFalse(os.path.exists(Gst.uri_get_location(scaled_uri)))
            self.assertTrue(os.path.exists(Gst.uri_get_location(hq_uri)))

            # Enable and delete HQ proxy
            proxy = self.check_add_proxy(asset, asset_uri, check_progress=False)
            self.check_disable_proxy(asset, asset_uri, proxy, hq_uri, delete=True)

    def test_regenerate_scaled_proxy(self):
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)
            asset = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]
            asset_uri = common.get_sample_uri(sample_name)

            # Create scaled proxy
            proxy = self.check_add_proxy(asset, asset_uri, scaled=True)
            proxy_uri = self.app.proxy_manager.getProxyUri(asset, scaled=True)

            # Change target resolution and trigger regeneration (1/4 Asset width)
            self.app.project_manager.current_project.scaled_proxy_width = 80
            self.app.project_manager.current_project.scaled_proxy_height = 60

            self.app.project_manager.current_project.regenerate_scaled_proxies()
            self.assertTrue("Proxy creation progress:" in
                self.medialibrary.storemodel[0][medialibrary.COL_INFOTEXT])
            self.mainloop.run()

            proxy = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]

            stream = proxy.get_info().get_video_streams()[0]
            resolution = [stream.get_width(), stream.get_height()]
            self.assertEqual(resolution, [80, 60])
            self.assertEqual(proxy.props.proxy_target.props.id, asset_uri)

            # Delete proxy
            self.check_disable_proxy(asset, asset_uri, proxy, proxy_uri, delete=True)

    def test_scaled_proxy_for_unsupported_asset(self):
        sample_name = "1sec_simpsons_trailer.mp4"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.AUTOMATIC)
            asset = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]
            asset_uri = common.get_sample_uri(sample_name)

            # Mark all formats as unsupported
            SUPPORTED_FORMATS = self.app.proxy_manager.WHITELIST_FORMATS
            self.app.proxy_manager.WHITELIST_FORMATS = []

            # Create scaled proxy
            proxy = self.check_add_proxy(asset, asset_uri, scaled=True, w=80, h=34)
            proxy_uri = self.app.proxy_manager.getProxyUri(asset, scaled=True)
            self.mainloop.run(until_empty=True)

            # Check that HQ proxy was created
            hq_uri = self.app.proxy_manager.getProxyUri(asset)
            self.assertTrue(os.path.exists(Gst.uri_get_location(hq_uri)))

            # Delete scaled proxy
            self.check_disable_proxy(asset, asset_uri, proxy, proxy_uri, delete=True)
            self.mainloop.run()

            # Check that we revert to HQ proxy
            proxy = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]
            proxy_uri = self.app.proxy_manager.getProxyUri(asset, scaled=False)
            self.assertEqual(proxy.props.id, proxy_uri)

            # Delete HQ Proxy
            self.check_disable_proxy(asset, asset_uri, proxy, proxy_uri, delete=True)

            self.app.proxy_manager.WHITELIST_FORMATS = SUPPORTED_FORMATS

    def test_supported_out_of_container_audio(self):
        sample = "mp3_sample.mp3"
        with common.cloned_sample(sample):
            self.check_import([sample], check_no_transcoding=True,
                proxying_strategy=ProxyingStrategy.AUTOMATIC)

    def test_missing_uri_displayed(self):
        with common.cloned_sample():
            asset_uri = common.get_sample_uri("missing.png")
            with common.created_project_file(asset_uri) as uri:
                self._customSetUp(project_uri=uri)
        self.assertTrue(self.medialibrary._import_warning_infobar.props.visible)
