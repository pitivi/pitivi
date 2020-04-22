# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.editorperspective module."""
from unittest import mock

from gi.repository import GES

from pitivi.dialogs.missingasset import MissingAssetDialog
from pitivi.editorperspective import EditorPerspective
from pitivi.project import ProjectManager
from pitivi.utils.misc import disconnect_all_by_func
from tests import common


class TestEditorPerspective(common.TestCase):
    """Tests for the EditorPerspective class."""

    # pylint: disable=protected-access
    def test_switch_context_tab(self):
        """Checks tab switches."""
        app = common.create_pitivi_mock()
        editorperspective = EditorPerspective(app)
        editorperspective.setup_ui()
        for expected_tab, b_element in [
                (0, GES.TitleClip()),
                (0, GES.SourceClip()),
                (1, GES.TransitionClip())]:
            editorperspective.switch_context_tab(b_element)
            self.assertEqual(editorperspective.context_tabs.get_current_page(),
                             expected_tab,
                             b_element)
            # Make sure the tab does not change when using an invalid argument.
            editorperspective.switch_context_tab("invalid")
            self.assertEqual(editorperspective.context_tabs.get_current_page(),
                             expected_tab)

    def __loading_failure(self, has_proxy):
        mainloop = common.create_main_loop()

        app = common.create_pitivi_mock(lastProjectFolder="/tmp",
                                        edgeSnapDeadband=32)
        app.project_manager = ProjectManager(app)
        editorperspective = EditorPerspective(app)
        editorperspective.setup_ui()
        editorperspective.viewer = mock.MagicMock()
        editorperspective.medialibrary._import_warning_infobar = mock.MagicMock()
        editorperspective.clipconfig.effect_expander._infobar = mock.MagicMock()

        def __pm_missing_uri_cb(project_manager, project, error, asset):
            nonlocal mainloop
            nonlocal editorperspective
            nonlocal self
            nonlocal app
            nonlocal has_proxy

            with mock.patch.object(MissingAssetDialog, "__new__") as constructor:
                failed_cb = mock.MagicMock()
                app.project_manager.connect("new-project-failed", failed_cb)

                dialog = constructor.return_value
                dialog.get_new_uri.return_value = None

                # Call the actual callback
                app.proxy_manager.check_proxy_loading_succeeded =  \
                    mock.MagicMock(return_value=has_proxy)

                editorperspective._project_manager_missing_uri_cb(
                    project_manager, project, error, asset)

                self.assertTrue(constructor.called)
                self.assertTrue(dialog.get_new_uri.called)
                self.assertEqual(failed_cb.called, not has_proxy)

            app.project_manager.connect("missing-uri",
                                        editorperspective._project_manager_missing_uri_cb)
            mainloop.quit()

        disconnect_all_by_func(app.project_manager,
                               editorperspective._project_manager_missing_uri_cb)

        app.project_manager.connect("missing-uri", __pm_missing_uri_cb)

        with common.cloned_sample():
            asset_uri = common.get_sample_uri("missing.png")
            with common.created_project_file(asset_uri) as uri:
                app.project_manager.load_project(uri)

        mainloop.run()

    def test_loading_project_no_proxy(self):
        """Checks loading failure without proxies."""
        self.__loading_failure(has_proxy=False)

    def test_loading_project_with_proxy(self):
        """Checks loading failure with proxies."""
        self.__loading_failure(has_proxy=True)
