# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the mediafilespreviewer module."""
# pylint: disable=attribute-defined-outside-init,protected-access
from unittest import mock

from gi.repository import GLib

from pitivi.dialogs.missingasset import MissingAssetDialog
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.utils.proxy import ProxyingStrategy
from tests import common


class PreviewWidgetTest(common.TestCase):
    """Tests for the PreviewWidget class."""

    def test_select_missing_asset(self):
        """Exercise the MissingAssetDialog when loading a project."""
        app = common.create_pitivi(proxying_strategy=ProxyingStrategy.NOTHING,
                                   FCpreviewWidth=640,
                                   FCpreviewHeight=480)

        proj_uri = self.create_project_file_from_xges("""<ges version='0.3'>
            <project properties='properties;' metadatas='metadatas;'>
                <ressources>
                    <asset id='file://this/is/a/moved/asset.mp4' extractable-type-name='GESUriClip'
                        properties='properties, supported-formats=(int)6, duration=(guint64)1228000000;' metadatas='metadatas' />
                </ressources>
            </project>
            </ges>""")
        project_manager = app.project_manager

        # Use a cloned sample so the asset is not in GES's asset cache.
        # This combination of calls can lead to a mainloop freeze:
        # - MissingAssetDialog.get_new_uri() through the "missing-uri" signal handler,
        # - MissingAssetDialog.run() through MissingAssetDialog.get_new_uri(),
        # - GES.UriClipAsset.request_sync() through PreviewWidget.preview_uri,
        with common.cloned_sample("1sec_simpsons_trailer.mp4"):
            asset_uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")

            mainloop = common.create_main_loop()

            def missing_uri_cb(project_manager, project, unused_error, asset):
                with mock.patch.object(MissingAssetDialog, "set_transient_for"):
                    mad = MissingAssetDialog(app, asset, asset.get_id())
                mad._chooser.select_uri(asset_uri)
                # Close the dialog when idle so get_new_uri does not get stuck.
                GLib.idle_add(mad.close)
                uri = mad.get_new_uri()
                return uri

            project_manager.connect("missing-uri", missing_uri_cb)

            preview_loaded_for_uri = ""

            def preview_uri(preview_widget, uri):
                nonlocal preview_loaded_for_uri
                original_preview_uri(preview_widget, uri)
                # If it gets past the original_preview_uri call, it's all fine!
                preview_loaded_for_uri = uri
                mainloop.quit()

            original_preview_uri = PreviewWidget.preview_uri
            PreviewWidget.preview_uri = preview_uri
            try:
                # Our mainloop timeout mechanism cannot be used,
                # because the mainloop gets blocked.
                with common.CheckedOperationDuration(seconds=2):
                    project_manager.load_project(proj_uri)
                    mainloop.run()
                self.assertEqual(preview_loaded_for_uri, asset_uri)
            finally:
                PreviewWidget.preview_uri = original_preview_uri
