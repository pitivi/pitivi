# PiTiVi , Non-linear video editor
#
#       tests/test_encode.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gst
from unittest import TestCase, main
from pitivi.encode import EncoderFactory
from pitivi.settings import StreamEncodeSettings

class TestEncoderFactory(TestCase):

    def testSimple(self):
        set = StreamEncodeSettings(encoder="theoraenc")
        b = EncoderFactory(settings=set)

        self.assertEquals(b.settings, set)

    def testMakeBin(self):
        set = StreamEncodeSettings(encoder="theoraenc")
        b = EncoderFactory(settings=set)

        bin = b.makeBin()

        # it should just be a bin containing theoraenc
        self.assertEquals(type(bin), gst.Bin)

        elements = list(bin.elements())
        self.assertEquals(len(elements), 1)

        elfact = elements[0].get_factory()
        self.assertEquals(elfact.get_name(), "theoraenc")


