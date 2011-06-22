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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

from common import TestCase
from pitivi.stream import AudioStream, VideoStream, match_stream, \
        match_stream_groups, StreamGroupWalker, \
        STREAM_MATCH_SAME_CAPS, STREAM_MATCH_COMPATIBLE_CAPS, \
        STREAM_MATCH_NONE, STREAM_MATCH_SAME_PAD_NAME, \
        STREAM_MATCH_SAME_TYPE
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


class TestMatchStream(TestCase):
    def testMatchStreamNoMatch(self):
        s1 = AudioStream(gst.Caps("audio/x-vorbis"))
        s2 = VideoStream(gst.Caps("video/x-theora"))

        stream, rank = match_stream(s1, [])
        self.failUnlessEqual(stream, None)
        self.failUnlessEqual(rank, STREAM_MATCH_NONE)

        stream, rank = match_stream(s1, [s2])
        self.failUnlessEqual(stream, None)
        self.failUnlessEqual(rank, STREAM_MATCH_NONE)

    def testMatchStreamSameCaps(self):
        s1 = AudioStream(gst.Caps("audio/x-vorbis, a=1"))
        s2 = AudioStream(gst.Caps("audio/x-vorbis, a=2"))
        stream, rank = match_stream(s1, [s1, s2])
        self.failUnlessEqual(id(s1), id(stream))
        self.failUnlessEqual(rank, STREAM_MATCH_SAME_CAPS)

    def testMatchSamePadName(self):
        s1 = AudioStream(gst.Caps("audio/x-vorbis"), pad_name="src0")
        s2 = AudioStream(gst.Caps("audio/x-speex"), pad_name="src0")
        stream, rank = match_stream(s1, [s2])
        self.failUnlessEqual(id(s2), id(stream))
        self.failUnlessEqual(rank, STREAM_MATCH_SAME_PAD_NAME +
                STREAM_MATCH_SAME_TYPE)

    def testMatchStreamCompatibleCaps(self):
        s1 = AudioStream(gst.Caps("audio/x-vorbis, a={1, 2}"))
        s2 = AudioStream(gst.Caps("audio/x-vorbis, a={2, 3}"))
        stream, rank = match_stream(s1, [s2])
        self.failUnlessEqual(id(s2), id(stream))
        self.failUnlessEqual(rank, STREAM_MATCH_COMPATIBLE_CAPS)

    def testMatchStreamSameNameAndSameCaps(self):
        s1 = AudioStream(gst.Caps("audio/x-vorbis"), pad_name="src0")
        s2 = AudioStream(gst.Caps("audio/x-vorbis"), pad_name="src0")
        stream, rank = match_stream(s1, [s2])
        self.failUnlessEqual(id(s2), id(stream))
        self.failUnlessEqual(rank,
                STREAM_MATCH_SAME_PAD_NAME + STREAM_MATCH_SAME_CAPS)

    def testMatchStreamSameNameAndCompatibleCaps(self):
        s1 = AudioStream(gst.Caps("audio/x-vorbis, a={1, 2}"), pad_name="src0")
        s2 = AudioStream(gst.Caps("audio/x-vorbis, a={2, 3}"), pad_name="src0")
        stream, rank = match_stream(s1, [s2])
        self.failUnlessEqual(id(s2), id(stream))
        self.failUnlessEqual(rank,
                STREAM_MATCH_SAME_PAD_NAME + STREAM_MATCH_COMPATIBLE_CAPS)


class TestStreamGroupMatching(TestCase):
    def testEmptyGroups(self):
        group_a = []
        group_b = []

        walker = StreamGroupWalker(group_a, group_b)
        self.failUnlessEqual(walker.advance(), [])
        self.failUnlessEqual(walker.getMatches(), {})

        stream = AudioStream(gst.Caps("audio/x-vorbis"))
        group_a = [stream]
        group_b = []
        walker = StreamGroupWalker(group_a, group_b)
        self.failUnlessEqual(walker.advance(), [])
        self.failUnlessEqual(walker.getMatches(), {})

        group_a = []
        group_b = [stream]
        walker = StreamGroupWalker(group_a, group_b)
        self.failUnlessEqual(walker.advance(), [])
        self.failUnlessEqual(walker.getMatches(), {})

    def testSimpleMatch(self):
        stream1 = AudioStream(gst.Caps("audio/x-vorbis"))
        stream2 = AudioStream(gst.Caps("audio/x-raw-int"))
        stream3 = AudioStream(gst.Caps("audio/x-vorbis, meh=asd"))

        group_a = [stream1, stream2]
        group_b = [stream3]

        walker = StreamGroupWalker(group_a, group_b)
        walkers = walker.advance()
        self.failUnlessEqual(len(walkers), 2)

        walker = walkers[0]
        self.failUnlessEqual(walker.advance(), [])
        self.failUnlessEqual(walker.getMatches(),
                {(stream1, stream3): STREAM_MATCH_COMPATIBLE_CAPS})

        walker = walkers[1]
        self.failUnlessEqual(walker.advance(), [])
        self.failUnlessEqual(walker.getMatches(),
                {(stream2, stream3): STREAM_MATCH_SAME_TYPE})

    def testMatchStreamGroupsOrder(self):
        stream1 = AudioStream(gst.Caps("audio/x-vorbis"))
        stream2 = AudioStream(gst.Caps("audio/x-vorbis"))
        stream3 = AudioStream(gst.Caps("audio/x-vorbis"))

        known_best_map = {(stream1, stream2): STREAM_MATCH_SAME_CAPS}

        group_a = [stream1]
        group_b = [stream2, stream3]
        best_map = match_stream_groups(group_a, group_b)
        self.failUnlessEqual(known_best_map, best_map)

    def testMatchStreamGroupsBestMatch(self):
        stream1 = AudioStream(gst.Caps("video/x-theora"))
        stream2 = AudioStream(gst.Caps("audio/x-vorbis, meh={FAIL, WIN}"))
        stream3 = AudioStream(gst.Caps("audio/x-vorbis"))
        stream4 = AudioStream(gst.Caps("video/x-theora"))
        stream5 = AudioStream(gst.Caps("audio/x-vorbis, meh=WIN"))
        stream6 = AudioStream(gst.Caps("audio/x-vorbis"))

        known_best_map = {(stream1, stream4): STREAM_MATCH_SAME_CAPS,
                (stream2, stream5): STREAM_MATCH_COMPATIBLE_CAPS,
                (stream3, stream6): STREAM_MATCH_SAME_CAPS}

        group_a = [stream1, stream2, stream3]
        group_b = [stream4, stream5, stream6]
        best_map = match_stream_groups(group_a, group_b)
        self.failUnlessEqual(known_best_map, best_map)

        group_a = [stream1, stream2, stream3]
        group_b = [stream6, stream5, stream4]
        best_map = match_stream_groups(group_a, group_b)
        self.failUnlessEqual(known_best_map, best_map)

        group_a = [stream1, stream2, stream3]
        group_b = [stream5, stream6, stream4]
        best_map = match_stream_groups(group_a, group_b)
        self.failUnlessEqual(known_best_map, best_map)
