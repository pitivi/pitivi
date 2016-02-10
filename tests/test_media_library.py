# -*- coding: utf-8 -*-
#
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

from unittest import mock
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gst
from gi.repository import GLib

from pitivi import medialibrary
from pitivi.project import ProjectManager
from pitivi.timeline import timeline
from pitivi.utils.proxy import ProxyingStrategy

from tests import common


def fakeSwitchProxies(asset):
    timeline.TimelineContainer.switchProxies(mock.MagicMock(), asset)


class TestMediaLibrary(common.TestCase):
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

        if self.app:
            self.app = common.cleanPitiviMock(self.app)

        if self.medialibrary:
            self.medialibrary.finalize()
            self.medialibrary = None

    def _customSetUp(self, settings, project_uri=None):
        # Always make sure we start with a clean medialibrary, and no other
        # is connected to some assets.
        self.clean()

        self.mainloop = GLib.MainLoop.new(None, False)
        self.check_no_transcoding = False
        self.app = common.getPitiviMock(settings)
        self.app.project_manager = ProjectManager(self.app)
        self.medialibrary = medialibrary.MediaLibraryWidget(self.app)

        if project_uri:
            self.app.project_manager.loadProject(project_uri)
        else:
            self.app.project_manager.newBlankProject(ignore_unsaved_changes=True)

        self.app.project_manager.current_project.connect(
            "loaded", self.projectLoadedCb)
        self.mainloop.run()

    def projectLoadedCb(self, unused_project, unused_timeline):
        self.mainloop.quit()

    def _progressBarCb(self, progressbar, unused_pspecunused):
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
                common.getSampleUri(sample_name), GES.UriClip,)

    def runCheckImport(self, assets, proxying_strategy=ProxyingStrategy.ALL,
                       check_no_transcoding=False, clean_proxies=True):
        settings = mock.MagicMock()
        settings.proxyingStrategy = proxying_strategy
        settings.numTranscodingJobs = 4
        settings.lastClipView = medialibrary.SHOW_TREEVIEW

        self._customSetUp(settings)
        self.check_no_transcoding = check_no_transcoding

        self.medialibrary._progressbar.connect(
            "notify::fraction", self._progressBarCb)

        if clean_proxies:
            common.cleanProxySamples()

        self._createAssets(assets)
        self.mainloop.run()
        self.assertFalse(self.medialibrary._progressbar.props.visible)

    def stopUsingProxies(self, delete_proxies=False):
        sample_name = "30fps_numeroted_frames_red.mkv"
        self.runCheckImport([sample_name])

        asset_uri = common.getSampleUri(sample_name)
        proxy = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]

        self.assertEqual(proxy.props.proxy_target.props.id, asset_uri)

        self.app.project_manager.current_project.disableProxiesForAssets(
            [proxy], delete_proxies)
        self.assertEqual(len(self.medialibrary.storemodel),
                         len(self.samples))

        self.assertEqual(self.medialibrary.storemodel[0][medialibrary.COL_URI],
                         asset_uri)

    def testTranscoding(self):
        self.runCheckImport(["30fps_numeroted_frames_red.mkv"])

    def testDisableProxies(self):
        self.runCheckImport(["30fps_numeroted_frames_red.mkv"],
                            ProxyingStrategy.NOTHING, True)

    def testReuseProxies(self):
        # Create proxies
        self.runCheckImport(["30fps_numeroted_frames_red.mkv"])
        self.info("Now trying to import again, checking that no"
                  " transcoding is done.")
        self.runCheckImport(["30fps_numeroted_frames_red.mkv"],
                            check_no_transcoding=True,
                            clean_proxies=False)

    def testNewlyImportedAssetSelected(self):
        self.runCheckImport(["30fps_numeroted_frames_red.mkv",
                            "30fps_numeroted_frames_blue.webm"])

        self.assertEqual(len(list(self.medialibrary.getSelectedPaths())),
                         len(self.samples))

    def testStopUsingProxies(self, delete_proxies=False):
        self.stopUsingProxies()

    def testDeleteProxy(self):
        self.stopUsingProxies(True)

        asset = self.medialibrary.storemodel[0][medialibrary.COL_ASSET]
        proxy_uri = self.app.proxy_manager.getProxyUri(asset)

        # Requesting UriClip sync will return None if the asset is not in cache
        # this way we make sure that this asset used to exist
        proxy = GES.Asset.request(GES.UriClip, proxy_uri)
        self.assertIsNotNone(proxy)
        self.assertFalse(os.path.exists(Gst.uri_get_location(proxy_uri)))

        self.assertIsNone(asset.get_proxy())

        # And let's recreate the proxy file.
        self.app.project_manager.current_project.useProxiesForAssets(
            [asset])
        self.assertEqual(asset.creation_progress, 0)

        # Check that the info column notifies the user about progress
        self.assertTrue(_("Proxy creation progress: ") in
                        self.medialibrary.storemodel[0][medialibrary.COL_INFOTEXT])

        # Run the mainloop and let _progressBarCb stop it when the proxy is
        # ready
        self.mainloop.run()

        self.assertEqual(asset.creation_progress, 100)
        self.assertEqual(asset.get_proxy(), proxy)

    def testMissingUriDisplayed(self):
        xges_path, uri = self.createTempProject()

        try:
            self._customSetUp(None, project_uri=uri)
            self.assertTrue(self.medialibrary._import_warning_infobar.props.visible)
        finally:
            os.remove(xges_path)
