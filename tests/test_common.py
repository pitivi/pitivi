# PiTiVi , Non-linear video editor
#
#       tests/test_common.py
#
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import common
from unittest import main
from pitivi.ui import common as ui_common

class TestColors(common.TestCase):

    def test_pack_color_32(self):
        self.assertEquals(
                0x01020408,
                ui_common.pack_color_32(0x01FF, 0x02FF, 0x04FF, 0x08FF))

    def test_pack_color_64(self):
        self.assertEquals(
                0x01FF02FF04FF08FF,
                ui_common.pack_color_64(0x01FF, 0x02FF, 0x04FF, 0x08FF))

    def test_unpack_color_32(self):
        self.assertEquals(
                (0x0100, 0x0200, 0x0400, 0x0800),
                ui_common.unpack_color_32(0x01020408))

    def test_unpack_color_64(self):
        self.assertEquals(
                (0x01FF, 0x02FF, 0x04FF, 0x08FF),
                ui_common.unpack_color_64(0x01FF02FF04FF08FF))

if __name__ == "__main__":
    main()
