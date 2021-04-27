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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
from gi.repository import GES
from gi.repository import Gtk

from pitivi.dialogs.projectsettings import ProjectSettingsDialog
from tests import common


class TestProjectUndo(common.TestCase):

    def setUp(self):
        super().setUp()
        self.app = common.create_pitivi()
        self.project = self.app.project_manager.new_blank_project()
        self.action_log = self.app.action_log

    def test_new_project_nothing_to_undo(self):
        mainloop = common.create_main_loop()

        def loaded_cb(project, timeline):
            mainloop.quit()

        self.project.connect_after("loaded", loaded_cb)

        mainloop.run()

        self.assertFalse(self.action_log.is_in_transaction())
        self.assertFalse(self.action_log.undo_stacks)

    def test_asset_added(self):
        uris = [common.get_sample_uri("tears_of_steel.webm")]
        mainloop = common.create_main_loop()

        def loaded_cb(unused_project, unused_timeline):
            self.project.add_uris(uris)

        self.project.connect_after("loaded", loaded_cb)

        def progress_cb(unused_project, progress, unused_estimated_time):
            if progress == 100:
                mainloop.quit()

        self.project.connect_after("asset-loading-progress", progress_cb)

        mainloop.run()

        self.assertTrue(self.action_log.has_assets_operations())
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 1)
        self.action_log.undo()
        self.assertFalse(self.action_log.has_assets_operations())
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 0)
        self.action_log.redo()
        self.assertTrue(self.action_log.has_assets_operations())
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 1)

    def test_use_proxy(self):
        # Import an asset.
        uris = [common.get_sample_uri("tears_of_steel.webm")]
        mainloop = common.create_main_loop()

        def loaded_cb(unused_project, unused_timeline):
            # The new project has been loaded, add some assets.
            self.project.add_uris(uris)
        self.project.connect_after("loaded", loaded_cb)

        def progress_cb(unused_project, progress, unused_estimated_time):
            if progress == 100:
                # The assets have been loaded.
                mainloop.quit()
        self.project.connect_after("asset-loading-progress", progress_cb)

        mainloop.run()
        self.project.disconnect_by_func(progress_cb)
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 1)

        # Make sure the asset is not a proxy.
        assets = [GES.UriClipAsset.request_sync(uri) for uri in uris]
        for asset in assets:
            self.assertIsNone(asset.get_proxy_target(), "Asset is proxy")

        # Use proxy instead of the asset.
        mainloop = common.create_main_loop()

        def error_cb(proxy_manager, asset, proxy, error):
            self.fail("Failed to create proxy: %s" % error)
        self.app.proxy_manager.connect("error-preparing-asset", error_cb)

        def proxy_ready_cb(proxy_manager, asset, proxy):
            mainloop.quit()
        self.app.proxy_manager.connect("proxy-ready", proxy_ready_cb)

        self.project.use_proxies_for_assets(assets)
        mainloop.run()

        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 2)

        # Undo proxying.
        self.action_log.undo()
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 1)

        # Redo proxying.
        self.action_log.redo()
        # Wait for the proxy to be signalled as ready.
        mainloop.run()
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 2)

    def test_project_settings(self):
        window = Gtk.Window()
        dialog = ProjectSettingsDialog(parent_window=window,
                                       project=self.project,
                                       app=self.app)

        def assert_meta(author, year):
            self.assertEqual(self.project.author, author)
            self.assertEqual(self.project.year, year)

        dialog.author_entry.set_text("a1")
        dialog.year_spinbutton.set_value(2001)
        dialog.update_project()
        assert_meta("a1", "2001")

        dialog.author_entry.set_text("a2")
        dialog.year_spinbutton.set_value(2002)
        dialog.update_project()
        assert_meta("a2", "2002")

        self.action_log.undo()
        assert_meta("a1", "2001")

        self.action_log.redo()
        assert_meta("a2", "2002")
