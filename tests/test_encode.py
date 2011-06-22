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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import gst
from unittest import main
from common import TestCase
from pitivi.stream import VideoStream
from pitivi.encode import EncoderFactory, RenderFactory
from pitivi.settings import StreamEncodeSettings, RenderSettings


class TestEncoderFactory(TestCase):

    def testSimple(self):
        set = StreamEncodeSettings(encoder="theoraenc")
        b = EncoderFactory(settings=set)

        self.assertEquals(b.settings, set)

    def testMakeBin(self):
        set = StreamEncodeSettings(encoder="theoraenc")
        b = EncoderFactory(settings=set)

        bin = b.makeBin()
        self.assertEquals(bin.factory, b)

        # it should just be a bin containing theoraenc
        self.assertEquals(type(bin), gst.Bin)

        elements = list(bin.elements())
        self.assertEquals(len(elements), 1)

        elfact = elements[0].get_factory()
        self.assertEquals(elfact.get_name(), "theoraenc")

    def testMakeBinFiltered(self):
        filtstream = VideoStream(caps=gst.Caps("video/x-raw-yuv,width=320,height=240"))
        set = StreamEncodeSettings(encoder="theoraenc",
                                   input_stream=filtstream)
        b = EncoderFactory(settings=set)

        bin = b.makeBin()
        self.assertEquals(bin.factory, b)

        # it should just be a bin containing the modifierbin and theoraenc
        self.assertEquals(type(bin), gst.Bin)

        elements = list(bin.elements())
        self.assertEquals(len(elements), 2)

        for elt in elements:
            if not isinstance(elt, gst.Bin):
                self.assertEquals(elt.get_factory().get_name(),
                                  "theoraenc")

    def testEncoderSettings(self):
        encsettings = {
            "bitrate": 40000,
            }
        set = StreamEncodeSettings(encoder="theoraenc",
                                   encodersettings=encsettings)
        b = EncoderFactory(settings=set)

        bin = b.makeBin()
        encoder = list(bin.elements())[0]
        for k, v in encsettings.iteritems():
            self.assertEquals(encoder.get_property(k), v)


class TestRenderFactory(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.audiosettings = StreamEncodeSettings(encoder="vorbisenc")
        self.videosettings = StreamEncodeSettings(encoder="theoraenc")

    def tearDown(self):
        self.audiosettings = None
        self.videosettings = None
        TestCase.tearDown(self)

    def testSimple(self):
        rset = RenderSettings(settings=[self.audiosettings,
                                        self.videosettings],
                              muxer="oggmux")
        f = RenderFactory(settings=rset)
        self.assertEquals(f.settings, rset)

    def testMakeBin(self):
        rset = RenderSettings(settings=[self.audiosettings,
                                        self.videosettings],
                              muxer="oggmux")
        f = RenderFactory(settings=rset)

        bin = f.makeBin()
        self.assertEquals(bin.factory, f)

        # it should be a bin...
        self.assertEquals(type(bin), gst.Bin)

        # containing 2 bins (encoders) and the muxer
        elements = list(bin.elements())
        self.assertEquals(len(elements), 3)

        for elt in elements:
            if type(elt) == gst.Bin:
                # it's one of our encoders
                self.assertEquals(len(list(elt.elements())), 1)
            else:
                # it's our muxer !
                self.assertEquals(elt.get_factory().get_name(),
                                  "oggmux")
