# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2011 Google <aleb@google.com>
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
import pitivi.utils.ui as ui_common
from tests import common


class TestColors(common.TestCase):

    def test_pack_color_32(self):
        self.assertEqual(
            0x01020408,
            ui_common.pack_color_32(0x01FF, 0x02FF, 0x04FF, 0x08FF))

    def test_pack_color_64(self):
        self.assertEqual(
            0x01FF02FF04FF08FF,
            ui_common.pack_color_64(0x01FF, 0x02FF, 0x04FF, 0x08FF))

    def test_unpack_color_32(self):
        self.assertEqual(
            (0x0100, 0x0200, 0x0400, 0x0800),
            ui_common.unpack_color_32(0x01020408))

    def test_unpack_color_64(self):
        self.assertEqual(
            (0x01FF, 0x02FF, 0x04FF, 0x08FF),
            ui_common.unpack_color_64(0x01FF02FF04FF08FF))
