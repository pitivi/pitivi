# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2012, Jean-François Fortin Tam <nekohayo@gmail.com>
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
"""Tests for the utils.system module."""
# pylint: disable=missing-docstring
from unittest import TestCase

from pitivi.utils.system import System


class TestSystem(TestCase):

    def testGetUniqueFilename(self):
        system = System()
        self.assertNotEqual(system.getUniqueFilename("a/b"),
                            system.getUniqueFilename("a%47b"))
        self.assertNotEqual(system.getUniqueFilename("a%b"),
                            system.getUniqueFilename("a%37b"))
        self.assertNotEqual(system.getUniqueFilename("a%/b"),
                            system.getUniqueFilename("a%37%3747b"))
        self.assertEqual("a b", system.getUniqueFilename("a b"))
