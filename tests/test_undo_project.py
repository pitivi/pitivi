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
from unittest import TestCase

from gi.repository import GES
from gi.repository import Gtk

from pitivi.project import ProjectSettingsDialog
from tests import common


class TestProjectUndo(TestCase):

    def setUp(self):
        self.app = common.create_pitivi()
        self.assertTrue(self.app.project_manager.newBlankProject())

        self.project = self.app.project_manager.current_project
        self.action_log = self.app.action_log

    def test_new_project_has_nothing_to_undo(self):
        mainloop = common.create_main_loop()

        def loaded_cb(project, timeline):
            mainloop.quit()

        self.project.connect_after("loaded", loaded_cb)

        mainloop.run()

        self.assertFalse(self.action_log.is_in_transaction())
        self.assertFalse(self.action_log.undo_stacks)

    def test_asset_added(self):
        mainloop = common.create_main_loop()

        def commit_cb(unused_action_log, stack):
            self.assertEqual(stack.action_group_name, "Adding assets")
            mainloop.quit()

        self.action_log.connect("commit", commit_cb)

        def loaded_cb(unused_project, unused_timeline):
            uris = [common.get_sample_uri("tears_of_steel.webm")]
            self.project.addUris(uris)

        self.project.connect_after("loaded", loaded_cb)

        mainloop.run()

        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 1)
        self.action_log.undo()
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 0)
        self.action_log.redo()
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 1)

    def test_use_proxy(self):
        # Import an asset.
        uris = [common.get_sample_uri("tears_of_steel.webm")]
        mainloop = common.create_main_loop()

        def commit_cb(unused_action_log, stack):
            self.assertEqual(stack.action_group_name, "Adding assets")
            mainloop.quit()
        self.action_log.connect("commit", commit_cb)

        def loaded_cb(unused_project, unused_timeline):
            self.project.addUris(uris)
        self.project.connect_after("loaded", loaded_cb)

        mainloop.run()
        self.action_log.disconnect_by_func(commit_cb)
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
            uris.remove(asset.props.id)
            if not uris:
                mainloop.quit()
        self.app.proxy_manager.connect("proxy-ready", proxy_ready_cb)

        self.project.useProxiesForAssets(assets)
        mainloop.run()

        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 2)
        self.action_log.undo()
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 1)
        self.action_log.redo()
        self.assertEqual(len(self.project.list_assets(GES.Extractable)), 2)

    def test_project_settings(self):
        window = Gtk.Window()
        dialog = ProjectSettingsDialog(parent_window=window,
                                       project=self.project,
                                       app=self.app)

        def assert_meta(title, author, year):
            self.assertEqual(self.project.name, title)
            self.assertEqual(self.project.author, author)
            self.assertEqual(self.project.year, year)

        dialog.title_entry.set_text("t1")
        dialog.author_entry.set_text("a1")
        dialog.year_spinbutton.set_value(2001)
        dialog.updateProject()
        assert_meta("t1", "a1", "2001")

        dialog.title_entry.set_text("t2")
        dialog.author_entry.set_text("a2")
        dialog.year_spinbutton.set_value(2002)
        dialog.updateProject()
        assert_meta("t2", "a2", "2002")

        self.action_log.undo()
        assert_meta("t1", "a1", "2001")

        self.action_log.redo()
        assert_meta("t2", "a2", "2002")
