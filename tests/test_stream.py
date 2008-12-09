#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       test_stream.py
#
# Copyright (c) 2008 Alessandro Decina <alessandro.decina@collabora.co.uk>
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

from unittest import TestCase
from pitivi.stream import AudioStream, VideoStream, TextStream
import gst

class TestMultimediaStream(object):
    """
    Base mixin for stream tests.
    """
    
    streamClass = None
    unfixed_caps = None
    fixed_caps = None
    non_raw_caps = None

    def testCommonProperties(self):
        stream = self.streamClass(self.fixed_caps)
        self.failUnless(stream.fixed)
        self.failUnless(stream.raw)

        stream = self.streamClass(self.unfixed_caps)
        self.failIf(stream.fixed)
        self.failUnless(stream.raw)

        stream = self.streamClass(self.non_raw_caps)
        self.failIf(stream.raw)
    
    def checkProperties(self, stream, expected):
        for name, expected in expected.iteritems():
            value = getattr(stream, name)
            
            if isinstance(value, gst.Fourcc) and \
                    gst.pygst_version < (0, 10, 13, 1):
                # gst.Fourcc didn't implement __eq__
                value = value.fourcc
                expected = expected.fourcc

            self.failUnlessEqual(value, expected, 'caps: %s property %s: %s != %s'
                    % (stream, name, value, expected))


class TestAudioStream(TestMultimediaStream, TestCase):
    streamClass = AudioStream
    unfixed_caps = gst.Caps('audio/x-raw-float, rate=48000, channels=2,' 
            'width=32, depth=32, endianness=4321; '
            'audio/x-raw-int, rate=44100, channels=2, width=32, depth=32, '
            'endianness=4321')

    fixed_caps = gst.Caps('audio/x-raw-int, rate=44100, channels=2, '
            'width=32, depth=32, endianness=4321')

    non_raw_caps = gst.Caps('audio/x-vorbis')

    def testAudioProperties(self):
        expected = {'audiotype': 'audio/x-raw-float',
                'rate': 48000, 'channels': 2, 'width': 32, 'depth': 32}
        stream = AudioStream(self.unfixed_caps)
        self.checkProperties(stream, expected)
        
        expected = {'audiotype': 'audio/x-raw-int',
                'rate': 44100, 'channels': 2, 'width': 32, 'depth': 32}
        stream = AudioStream(self.fixed_caps)
        self.checkProperties(stream, expected)

        # get None when trying to access these properties with non raw streams
        # NOTE: this is the current behaviour. Does it really make sense to try
        # to access these properties for non raw streams? Should we rather error
        # out?
        expected = dict((name, None) for name in expected.keys())
        expected['audiotype'] = 'audio/x-vorbis'
        stream = AudioStream(self.non_raw_caps)
        self.checkProperties(stream, expected)

class TestVideoStream(TestMultimediaStream, TestCase):
    streamClass = VideoStream
    unfixed_caps = gst.Caps('video/x-raw-rgb, width=320, height=240, '
            'framerate=30/1; '
            'video/x-raw-yuv, width=320, height=240, framerate=30/1, '
            'format=(fourcc)I420')
    fixed_caps = gst.Caps('video/x-raw-yuv, width=320, height=240, '
            'framerate=30/1, format=(fourcc)I420')
    non_raw_caps = gst.Caps('video/x-theora')

    def testVideoProperties(self):
        expected = {'videotype': 'video/x-raw-rgb', 'width': 320, 'height': 240,
                'framerate': gst.Fraction(30, 1), 'format': None,
                'par': gst.Fraction(1, 1), 'dar': gst.Fraction(4, 3)}
        stream = VideoStream(self.unfixed_caps)
        self.checkProperties(stream, expected)

        expected['videotype'] = 'video/x-raw-yuv'
        expected['format'] = gst.Fourcc('I420')
        stream = VideoStream(self.fixed_caps)
        self.checkProperties(stream, expected)

        expected['videotype'] = 'video/x-theora'
        expected['width'] = None
        expected['height'] = None
        expected['format'] = None
        expected['framerate'] = gst.Fraction(1, 1)
        stream = VideoStream(self.non_raw_caps)
        self.checkProperties(stream, expected)

    def testParAndDar(self):
        caps = gst.Caps('video/x-raw-int, width=320, height=240, '
                'pixel-aspect-ratio=2/1')
        stream = VideoStream(caps)
        self.failUnlessEqual(stream.par, gst.Fraction(2, 1))
        self.failUnlessEqual(stream.dar, gst.Fraction(640, 240))

        caps = gst.Caps('video/x-raw-int, width=320, height=240')
        stream = VideoStream(caps)
        self.failUnlessEqual(stream.par, gst.Fraction(1, 1))
        self.failUnlessEqual(stream.dar, gst.Fraction(320, 240))

        # no width and height, default to 4/3
        caps = gst.Caps('video/x-raw-int')
        stream = VideoStream(caps)
        self.failUnlessEqual(stream.par, gst.Fraction(1, 1))
        self.failUnlessEqual(stream.dar, gst.Fraction(4, 3))
