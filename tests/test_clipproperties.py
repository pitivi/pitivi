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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
"""Tests for the pitivi.clipproperties module."""
# pylint: disable=protected-access,no-self-use,too-many-locals
from gi.repository import Gtk

from pitivi.clipproperties import EffectProperties
from tests import common


class EffectPropertiesTest(common.TestCase):
    """Tests for the EffectProperties class."""

    def test_calculate_effect_priority(self):
        """Checks the effect priority calculation."""
        # Dragging 1 onto itself and nearby.
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            1, 0, Gtk.TreeViewDropPosition.AFTER))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            1, 1, Gtk.TreeViewDropPosition.BEFORE))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            1, 1, Gtk.TreeViewDropPosition.INTO_OR_BEFORE))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            1, 1, Gtk.TreeViewDropPosition.INTO_OR_AFTER))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            1, 1, Gtk.TreeViewDropPosition.AFTER))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            1, 2, Gtk.TreeViewDropPosition.BEFORE))

        # Dragging 0 and 3 between rows 1 and 2.
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            0, 1, Gtk.TreeViewDropPosition.AFTER))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            0, 2, Gtk.TreeViewDropPosition.BEFORE))
        self.assertEqual(2, EffectProperties.calculateEffectPriority(
            3, 1, Gtk.TreeViewDropPosition.AFTER))
        self.assertEqual(2, EffectProperties.calculateEffectPriority(
            3, 2, Gtk.TreeViewDropPosition.BEFORE))

        # Dragging 0 and 2 onto 1.
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            0, 1, Gtk.TreeViewDropPosition.INTO_OR_BEFORE))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            0, 1, Gtk.TreeViewDropPosition.INTO_OR_AFTER))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            2, 1, Gtk.TreeViewDropPosition.INTO_OR_BEFORE))
        self.assertEqual(1, EffectProperties.calculateEffectPriority(
            2, 1, Gtk.TreeViewDropPosition.INTO_OR_AFTER))
