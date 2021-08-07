# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2021, Piotr Brzeziński <thewildtreee@gmail.com>
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
from gi.repository import Gst

from pitivi.timeline.markers import ClipMarkersBox
from pitivi.utils.markers import DEFAULT_LIST_KEY
from tests import common


class TestMarkerListManager(common.TestCase):
    def add_single_clip(self):
        clip = GES.TitleClip()
        clip.set_start(5 * Gst.SECOND)
        clip.set_duration(20 * Gst.SECOND)
        self.layer.add_clip(clip)
        return clip

    @common.setup_timeline
    def test_manager_created_with_default(self):
        clip = self.add_single_clip()
        source, = clip.get_children(False)

        manager = source.markers_manager
        self.assertTrue(manager)

        self.assertTrue(manager.list_exists(DEFAULT_LIST_KEY))
        self.assertEqual(manager.current_list_key, DEFAULT_LIST_KEY)

    @common.setup_timeline
    def test_manager_list_add(self):
        clip = self.add_single_clip()
        source, = clip.get_children(False)
        manager = source.markers_manager

        self.assertRaises(ValueError, manager.add_list, DEFAULT_LIST_KEY)
        self.assertRaises(ValueError, manager.add_list, "key with spaces")
        self.assertRaises(ValueError, manager.add_list, None)

        test_key = "test_list"
        markers = [1, 5, 10]
        test_list = manager.add_list(test_key, markers)

        self.assertTrue(manager.list_exists(test_key))
        self.assertEqual(test_list, source.get_marker_list(test_key))
        self.assert_markers(test_list, [(pos, None) for pos in markers])

    @common.setup_timeline
    def test_manager_list_remove(self):
        clip = self.add_single_clip()
        source, = clip.get_children(False)
        manager = source.markers_manager

        self.assertRaises(ValueError, manager.remove_list, DEFAULT_LIST_KEY)
        self.assertRaises(ValueError, manager.remove_list, None)

        test_key = "test_list"
        manager.add_list(test_key)
        manager.current_list_key = test_key

        self.assertEqual(manager.current_list_key, test_key)
        manager.remove_list(test_key)
        self.assertEqual(manager.current_list_key, DEFAULT_LIST_KEY)
        self.assertIsNone(source.get_marker_list(test_key))

    @common.setup_timeline
    def test_manager_default_snappability(self):
        clip = self.add_single_clip()
        source, = clip.get_children(False)
        manager = source.markers_manager

        test_key = "test_list"
        default_snappable = self.app.settings.markersSnappableByDefault

        manager.add_list(test_key)
        manager.current_list_key = test_key
        self.assertEqual(manager.snappable, default_snappable)

    @common.setup_timeline
    def test_manager_current_list(self):
        clip = self.add_single_clip()
        source, = clip.get_children(False)
        manager = source.markers_manager

        test_key = "test_list"
        manager.add_list(test_key)

        # Toggle snappability on the default list, switch to a diff. one,
        # turn off snappability there, and test if they're both
        # correctly kept between active list changes.
        manager.snappable = True
        manager.current_list_key = test_key
        manager.snappable = False

        manager.current_list_key = DEFAULT_LIST_KEY
        self.assertEqual(manager.current_list, source.get_marker_list(DEFAULT_LIST_KEY))
        self.assertTrue(manager.snappable)
        manager.current_list_key = test_key
        self.assertEqual(manager.current_list, source.get_marker_list(test_key))
        self.assertFalse(manager.snappable)
        manager.current_list_key = ""
        self.assertIsNone(manager.current_list)
        self.assertFalse(manager.snappable)
        manager.current_list_key = DEFAULT_LIST_KEY
        self.assertEqual(manager.current_list, source.get_marker_list(DEFAULT_LIST_KEY))
        self.assertTrue(manager.snappable)

    @common.setup_timeline
    def test_manager_marker_box(self):
        clip = self.add_single_clip()
        source, = clip.get_children(False)
        manager = source.markers_manager
        box = ClipMarkersBox(self.app, source)

        test_key = "test_list"
        manager.add_list(test_key)

        self.assertIsNone(box.markers_container)
        manager.set_markers_box(box)
        self.assertEqual(box.markers_container, manager.current_list)
        manager.current_list_key = test_key
        self.assertEqual(box.markers_container, manager.current_list)
        manager.current_list_key = ""
        self.assertIsNone(box.markers_container)

        # Disconnect the box, make a few changes and attach again.
        manager.set_markers_box(None)
        manager.current_list_key = DEFAULT_LIST_KEY
        self.assertIsNone(box.markers_container)
        manager.current_list_key = test_key
        manager.set_markers_box(box)
        self.assertEqual(box.markers_container, manager.current_list)
