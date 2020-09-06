# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Guy Richard <guy.richard99@gmail.com>
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
"""Tests for the pitivi.viewer.viewer module."""
# pylint: disable=protected-access,no-self-use
from pitivi.project import ProjectManager
from pitivi.viewer.viewer import ViewerContainer
from tests import common


class TestViewerContainer(common.TestCase):

    def test_toggle_safe_areas_action(self):
        """Checks the effect of the toggle_safe_areas_action."""
        app = common.create_pitivi_mock()
        app.project_manager = ProjectManager(app)
        viewer_container = ViewerContainer(app)

        project = app.project_manager.new_blank_project()
        viewer_container.set_project(project)
        self.assertFalse(viewer_container.overlay_stack.safe_areas_overlay.get_visible())

        viewer_container.toggle_safe_areas_action.activate()
        self.assertTrue(viewer_container.overlay_stack.safe_areas_overlay.get_visible())

        viewer_container.toggle_safe_areas_action.activate()
        self.assertFalse(viewer_container.overlay_stack.safe_areas_overlay.get_visible())
