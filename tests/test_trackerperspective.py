# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2022, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.trackerperspective module."""
# pylint: disable=protected-access
from unittest import skipUnless

from gi.repository import GES

from pitivi.check import MISSING_SOFT_DEPS
from pitivi.trackerperspective import ObjectManager
from tests import common


class TestCoverObjectPopover(common.TestCase):
    """Tests for the CoverObjectPopover class."""

    @skipUnless("cvtracker" not in MISSING_SOFT_DEPS, "cvtracker element missing")
    @common.setup_project_with_clips(assets_names=["tears_of_steel.webm"])
    @common.setup_clipproperties
    def test_cover(self):
        clip, = self.layer.get_clips()
        self.click_clip(clip, expect_selected=True)

        expander = self.clipproperties.effect_expander
        expander.cover_object_button.clicked()
        self.assertTrue(expander.cover_popover.props.visible)
        # Only one row containing the Track Objects button should exist.
        self.assertEqual(len(expander.cover_popover.listbox.get_children()), 1)

        expander.cover_object_button.clicked()
        self.assertFalse(expander.cover_popover.props.visible)

        object_manager = ObjectManager(clip.asset)
        object_manager.add_object(1, "object1", "Object 1")
        object_manager.update_object_position("object1", 0, (10, 20, 30, 40))
        object_manager.add_object(2, "object2", "Object 2")
        object_manager.update_object_position("object2", 1, (20, 30, 40, 50))
        object_manager.save()

        expander.cover_object_button.clicked()
        self.assertTrue(expander.cover_popover.props.visible)
        # Two rows for two object and one for Track Objects.
        self.assertEqual(len(expander.cover_popover.listbox.get_children()), 3)

        self.assertEqual(len(clip.get_top_effects()), 0)
        expander.cover_popover.listbox.get_row_at_index(0).emit("activate")
        self.assertFalse(expander.cover_popover.props.visible)
        self.assertEqual(len(clip.get_top_effects()), 1)

        expander.cover_object_button.clicked()
        self.assertTrue(expander.cover_popover.props.visible)
        # One row for the uncovered object and one for the Track Objects button.
        self.assertEqual(len(expander.cover_popover.listbox.get_children()), 2)


class TestObjectManager(common.TestCase):
    """Tests for the ObjectManager class."""

    def test_load_save(self):
        asset = GES.UriClipAsset.request_sync(common.get_sample_uri("tears_of_steel.webm"))
        object_manager1 = ObjectManager(asset)
        object_manager1.add_object(1, "object1", "Object 1")
        object_manager1.update_object_position("object1", 100, (10, 20, 30, 40))
        object_manager1.save()

        object_manager2 = ObjectManager(asset)
        self.assertListEqual(object_manager2.objects, [(1, "object1", "Object 1")])
        self.assertDictEqual(object_manager2.values, {"object1": [(100, (10, 20, 30, 40))]})

        object_manager2.add_object(2, "object2", "Object 2")
        object_manager2.update_object_position("object2", 200, (20, 30, 40, 50))
        object_manager2.save()

        object_manager3 = ObjectManager(asset)
        self.assertListEqual(object_manager3.objects, [(1, "object1", "Object 1"), (2, "object2", "Object 2")])
        self.assertDictEqual(object_manager2.values, {"object1": [(100, (10, 20, 30, 40))],
                                                      "object2": [(200, (20, 30, 40, 50))]})

    def test_update_object_position(self):
        asset = GES.UriClipAsset.request_sync(common.get_sample_uri("tears_of_steel.webm"))
        object_manager = ObjectManager(asset)
        object_manager.add_object(1, "object1", "Object 1")
        object_manager.update_object_position("object1", 200, (20, 30, 40, 50))
        object_manager.update_object_position("object1", 100, (10, 20, 30, 40))
        object_manager.update_object_position("object1", 300, (30, 40, 50, 60))

        self.assertDictEqual(object_manager.values, {"object1": [(100, (10, 20, 30, 40)),
                                                                 (200, (20, 30, 40, 50)),
                                                                 (300, (30, 40, 50, 60))]})

    def test_interpolate(self):
        asset = GES.UriClipAsset.request_sync(common.get_sample_uri("tears_of_steel.webm"))
        object_manager = ObjectManager(asset)
        object_manager.add_object(1, "object1", "Object 1")
        object_manager.update_object_position("object1", 200, (20, 30, 40, 50))
        object_manager.update_object_position("object1", 100, (10, 20, 30, 40))
        object_manager.update_object_position("object1", 300, (30, 40, 50, 60))

        self.assertTupleEqual(object_manager.interpolate("object1", 99), (10, 20, 30, 40))
        self.assertTupleEqual(object_manager.interpolate("object1", 100), (10, 20, 30, 40))
        self.assertTupleEqual(object_manager.interpolate("object1", 150), (15, 25, 35, 45))
        self.assertTupleEqual(object_manager.interpolate("object1", 200), (20, 30, 40, 50))
        self.assertTupleEqual(object_manager.interpolate("object1", 275), (27.5, 37.5, 47.5, 57.5))
        self.assertTupleEqual(object_manager.interpolate("object1", 300), (30, 40, 50, 60))
        self.assertTupleEqual(object_manager.interpolate("object1", 301), (30, 40, 50, 60))
