# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Jaden Goter <jadengoter@huskers.unl.edu>
# Copyright (c) 2020, Jessie Guo <jessie.guo@huskers.unl.edu>
# Copyright (c) 2020, Daniel Rudebusch <daniel.rudebusch@huskers.unl.edu>
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
"""Tests for the pitivi.viewer.guidelines module."""
# pylint: disable=protected-access,no-self-use,attribute-defined-outside-init
from pitivi.viewer.guidelines import Guideline
from pitivi.viewer.viewer import ViewerContainer
from tests import common


class GuidelinesPopoverTest(common.TestCase):
    """Tests for the guidelines classes."""

    def setup_viewer_widget(self):
        """Sets a viewer widget up."""
        self.app = common.create_pitivi()
        self.viewer_container = ViewerContainer(self.app)
        project = self.app.project_manager.new_blank_project()
        self.viewer_container.set_project(project)

    def _check_guidelines(self, guidelines, toggled_guidelines):
        overlay = self.viewer_container.guidelines_popover.overlay

        self.assertSetEqual(overlay.active_guidelines, set(guidelines))
        self.assertEqual(overlay.get_visible(), bool(guidelines), guidelines)

        self.viewer_container.toggle_guidelines_action.activate(None)
        self.assertSetEqual(overlay.active_guidelines, set(toggled_guidelines))
        self.assertEqual(overlay.get_visible(), bool(toggled_guidelines), guidelines)

        self.viewer_container.toggle_guidelines_action.activate(None)
        self.assertSetEqual(overlay.active_guidelines, set(guidelines))
        self.assertEqual(overlay.get_visible(), bool(guidelines), guidelines)

    def test_activate_deactivate_toggle(self):
        self.setup_viewer_widget()
        popover = self.viewer_container.guidelines_popover

        self._check_guidelines([], [Guideline.THREE_BY_THREE])

        all_guidelines = set()
        for guideline in Guideline:
            popover.switches[guideline].set_active(True)
            self._check_guidelines([guideline], [])

            popover.switches[guideline].set_active(False)
            self._check_guidelines([], [guideline])

            all_guidelines.add(guideline)

        for guideline in Guideline:
            popover.switches[guideline].set_active(True)
        self._check_guidelines(all_guidelines, [])

        for guideline in Guideline:
            popover.switches[guideline].set_active(False)
            expected = set(all_guidelines)
            expected.remove(guideline)
            self._check_guidelines(expected, [])

            popover.switches[guideline].set_active(True)
            self._check_guidelines(all_guidelines, [])
