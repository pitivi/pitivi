# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Alex Băluț <alexandru.balut@gmail.com>
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
from pitivi.utils.misc import round05
from tests import common


class TestMisc(common.TestCase):

    def test_round05(self):
        self.assertEqual(round05(0), 0.5)
        self.assertEqual(round05(0.999), 0.5)

        self.assertEqual(round05(1), 1.5)
        self.assertEqual(round05(1.999), 1.5)

        self.assertEqual(round05(2), 2.5)
        self.assertEqual(round05(2.999), 2.5)
