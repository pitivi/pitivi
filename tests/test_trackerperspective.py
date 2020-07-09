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
from gi.repository import GES

from pitivi.trackerperspective import ObjectManager
from tests import common


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
