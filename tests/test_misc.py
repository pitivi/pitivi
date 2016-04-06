# -*- coding: utf-8 -*-
#
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import unittest

from pitivi.utils.misc import binary_search


class BinarySearchTest(unittest.TestCase):

    def testEmptyList(self):
        self.assertEqual(binary_search([], 10), -1)

    def testExisting(self):
        A = [10, 20, 30]
        for index, element in enumerate(A):
            self.assertEqual(binary_search([10, 20, 30], element), index)

    def testMissingLeft(self):
        self.assertEqual(binary_search([10, 20, 30], 1), 0)
        self.assertEqual(binary_search([10, 20, 30], 16), 1)
        self.assertEqual(binary_search([10, 20, 30], 29), 2)

    def testMissingRight(self):
        self.assertEqual(binary_search([10, 20, 30], 11), 0)
        self.assertEqual(binary_search([10, 20, 30], 24), 1)
        self.assertEqual(binary_search([10, 20, 30], 40), 2)
