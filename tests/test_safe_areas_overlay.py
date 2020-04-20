# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2014, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.viewer.safe_areas_overlay module."""
# pylint: disable=protected-access,no-self-use
import numpy

from pitivi.editorperspective import EditorPerspective
from pitivi.utils.pipeline import SimplePipeline
from pitivi.viewer.overlay_stack import OverlayStack
from pitivi.viewer.safe_areas_overlay import SafeAreasOverlay
from tests import common


class TestSafeAreasOverlay(common.TestCase):
    """Tests for the SafeAreasOverlay class."""

    def test_compute_new_safe_area_position(self):
        """Checks the safe areas repositioning calculation."""
        project_width = 200
        project_height = 100
        safe_area_width = 100
        safe_area_height = 50
        x_position = (project_width - safe_area_width) / 2
        y_position = (project_height - safe_area_height) / 2
        safe_area_position = numpy.array([x_position, y_position])

        numpy.testing.assert_array_equal(safe_area_position, SafeAreasOverlay.compute_new_safe_area_position(
            self, project_width, project_height, safe_area_width, safe_area_height))

    def test_compute_new_safe_area_size(self):
        """Checks the safe areas resizing calculation."""
        project_width = 200
        project_height = 100
        new_width_percentage = 1.50
        new_height_percentage = 0.80
        safe_area_width = project_width * new_width_percentage
        safe_area_height = project_height * new_height_percentage
        safe_area_size = numpy.array([safe_area_width, safe_area_height])

        numpy.testing.assert_array_equal(safe_area_size, SafeAreasOverlay.compute_new_safe_area_size(
            self, project_width, project_height, new_width_percentage, new_height_percentage))

    def test_widget_is_shown(self):
        """Checks to ensure that, upon the user turning a safe area on, the safe areas overlay is added to the overlay stack."""
        app = common.create_pitivi_mock()
        editor_perspective = EditorPerspective(app)
        editor_perspective.setup_ui()

        _, sink = SimplePipeline.create_sink(self)
        overlay_stack = OverlayStack(app, sink)

        editor_perspective.viewer.overlay_stack = overlay_stack

        editor_perspective.viewer.overlay_stack.safe_areas_overlay.toggle_safe_areas()

        self.assertEqual(editor_perspective.viewer.overlay_stack.safe_areas_overlay.get_visible(), True)

    def test_widget_is_hidden(self):
        """Checks to ensure that, upon the user turning a safe area off, the safe areas overlay is removed from the overlay stack."""
        app = common.create_pitivi_mock()
        editor_perspective = EditorPerspective(app)
        editor_perspective.setup_ui()

        _, sink = SimplePipeline.create_sink(self)
        overlay_stack = OverlayStack(app, sink)

        editor_perspective.viewer.overlay_stack = overlay_stack

        self.assertEqual(editor_perspective.viewer.overlay_stack.safe_areas_overlay.get_visible(), False)
