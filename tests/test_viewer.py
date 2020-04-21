# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Jaden Goter <jadengoter@huskers.unl.edu>,
#                     Jessie Guo <jessie.guo@huskers.unl.edu>,
#                     Daniel Rudebusch <daniel.rudebusch@huskers.unl.edu>
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
# pylint: disable=protected-access,no-self-use,attribute-defined-outside-init
from tests import common

from pitivi.viewer.viewer import ViewerContainer


class ViewerContainerTest(common.TestCase):
    """Tests for the ViewerContainer class."""

    def setup_viewer_widget(self):
        """Sets a viewer widget up."""
        self.app = common.create_pitivi()
        viewer_container = ViewerContainer(self.app)
        viewer_container.set_project(self.app.project_manager.new_blank_project())
        return viewer_container

    def test_enable_three_by_three_guidelines(self):
        """Checks that the 3x3 composition guidelines toggle adds the overlay to the drawing set of the composition guidelines overlay."""
        viewer_container = self.setup_viewer_widget()
        viewer_container.three_by_three_toggle.set_widget_value(True)

        self.assertEqual(viewer_container.overlay_stack.composition_guidelines_overlay.guidelines_to_draw,
                         {viewer_container.overlay_stack.composition_guidelines_overlay.three_by_three})

    def test_enable_all_guidelines(self):
        """Checks that all composition guidelines toggles adds the overlay to the drawing set of the composition guidelines overlay at once."""
        viewer_container = self.setup_viewer_widget()
        viewer_container.three_by_three_toggle.set_widget_value(True)
        viewer_container.diagonals_toggle.set_widget_value(True)
        viewer_container.vert_horiz_center_toggle.set_widget_value(True)

        self.assertEqual(viewer_container.overlay_stack.composition_guidelines_overlay.guidelines_to_draw,
                         {viewer_container.overlay_stack.composition_guidelines_overlay.three_by_three, viewer_container.overlay_stack.composition_guidelines_overlay.diagonals, viewer_container.overlay_stack.composition_guidelines_overlay.vertical_horizontal_center})

    def test_disable_three_by_three_guidelines(self):
        """Checks that toggling the 3x3 composition guidelines on and off removes the overlay to the drawing set of the composition guidelines overlay."""
        viewer_container = self.setup_viewer_widget()
        viewer_container.three_by_three_toggle.set_widget_value(True)
        viewer_container.three_by_three_toggle.set_widget_value(False)

        self.assertEqual(viewer_container.overlay_stack.composition_guidelines_overlay.guidelines_to_draw, set())

    def test_show_guidelines(self):
        """Checks that the show guidelines toggle properly hides the guidelines overlay."""
        viewer_container = self.setup_viewer_widget()

        self.assertEqual(viewer_container.overlay_stack.composition_guidelines_overlay.is_visible(), True)

        viewer_container.three_by_three_toggle.set_widget_value(True)
        viewer_container.vert_horiz_center_toggle.set_widget_value(True)
        viewer_container.show_guidelines_toggle.set_widget_value(False)

        self.assertEqual(viewer_container.overlay_stack.composition_guidelines_overlay.is_visible(), False)
        self.assertEqual(viewer_container.overlay_stack.composition_guidelines_overlay.guidelines_to_draw,
                         {viewer_container.overlay_stack.composition_guidelines_overlay.three_by_three, viewer_container.overlay_stack.composition_guidelines_overlay.vertical_horizontal_center})

    def test_disable_show_guidelines(self):
        """Checks that the show guidelines toggle properly desensitizes other guideline toggle buttons when disabled."""
        viewer_container = self.setup_viewer_widget()

        self.assertEqual(viewer_container.three_by_three_toggle.switch_button.is_sensitive(), True)
        self.assertEqual(viewer_container.vert_horiz_center_toggle.switch_button.is_sensitive(), True)
        self.assertEqual(viewer_container.diagonals_toggle.switch_button.is_sensitive(), True)

        viewer_container.show_guidelines_toggle.set_widget_value(False)

        self.assertEqual(viewer_container.three_by_three_toggle.switch_button.is_sensitive(), False)
        self.assertEqual(viewer_container.vert_horiz_center_toggle.switch_button.is_sensitive(), False)
        self.assertEqual(viewer_container.diagonals_toggle.switch_button.is_sensitive(), False)

    def test_toggle_guidelines_shortcut(self):
        """Checks that the toggle guidelines shortcut properly toggles the composition guidelines."""
        viewer_container = self.setup_viewer_widget()

        viewer_container.three_by_three_toggle.set_widget_value(True)

        self.assertEqual(viewer_container.show_guidelines_toggle.get_widget_value(), True)
        self.assertEqual(viewer_container.overlay_stack.composition_guidelines_overlay.is_visible(), True)

        # Call the control binding that is called by the shortcut from timeline/timeline.py
        viewer_container.toggle_composition_guidelines_cb(None, None)

        self.assertEqual(viewer_container.show_guidelines_toggle.get_widget_value(), False)
        self.assertEqual(viewer_container.overlay_stack.composition_guidelines_overlay.is_visible(), False)
