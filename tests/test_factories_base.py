#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       test_factories_base.py
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

import gst
from unittest import TestCase

from pitivi.factories.base import ObjectFactory, ObjectFactoryError, \
        SourceFactory, RandomAccessSourceFactory, LiveSourceFactory
from pitivi.stream import AudioStream, VideoStream

from common import SignalMonitor

class TestObjectFactory(TestCase):
    def setUp(self):
        self.factory = ObjectFactory('name', 'displayname')

    def testIcon(self):
        # by default icon is None
        self.failUnlessEqual(self.factory.icon, None)

        # assign and check the result. This may seem stupid but icon is a
        # property so it has a setter method that we want to exercise.
        self.factory.icon = 'icon'
        self.failUnlessEqual(self.factory.icon, 'icon')

        # icon is inherited from parents
        factory1 = ObjectFactory('name', 'displayname')
        self.failUnlessEqual(factory1.icon, None)
        factory1.parent = self.factory
        self.failUnlessEqual(factory1.icon, 'icon')

        # setting it directly doesn't make it go up to the parent anymore
        factory1.icon = 'icon1'
        self.failUnlessEqual(factory1.icon, 'icon1')
        self.failUnlessEqual(self.factory.icon, 'icon')

    def testDuration(self):
        # if default_duration isn't set explicitly, it defaults to duration
        self.failUnlessEqual(self.factory.duration, gst.CLOCK_TIME_NONE)
        self.failUnlessEqual(self.factory.default_duration, gst.CLOCK_TIME_NONE)
        self.factory.duration = 60 * gst.SECOND
        self.failUnlessEqual(self.factory.default_duration, 60 * gst.SECOND)

        # assigning to default_duration shouldn't influence duration
        self.factory.default_duration = 10 * gst.SECOND
        self.failUnlessEqual(self.factory.default_duration, 10 * gst.SECOND)
        self.failUnlessEqual(self.factory.duration, 60 * gst.SECOND)

class StubSourceFactory(SourceFactory):
    def _makeBin(self, output_stream=None):
        return gst.Bin()

class TestSourceFactory(TestCase):
    def setUp(self):
        self.factory = StubSourceFactory('name', 'displayname')
        caps = gst.Caps('video/x-raw-rgb')
        self.stream = VideoStream(caps, pad_name='src0')
        # source factories can't have input streams
        self.failUnlessRaises(AssertionError,
                self.factory.addInputStream, self.stream)
        self.factory.addOutputStream(self.stream)
        self.monitor = SignalMonitor(self.factory, 'bin-created', 'bin-released')

    def testMakeAndReleaseBin(self):
        caps = gst.Caps('video/x-raw-yuv')
        stream1 = VideoStream(caps)
        # calling factory.makeBin(stream) with a stream that doesn't belong to a
        # factory should result in an error
        self.failUnlessRaises(ObjectFactoryError,
                self.factory.makeBin, stream1)

        self.failUnlessEqual(self.factory.current_bins, 0)
        self.failUnlessEqual(self.monitor.bin_created_count, 0)
        # check makeBin with a specific stream
        bin1 = self.factory.makeBin(self.stream)
        self.failUnlessEqual(self.factory.current_bins, 1)
        self.failUnlessEqual(self.monitor.bin_created_count, 1)
        self.failUnless(isinstance(bin1, gst.Bin))
        # now check the "default" bin case
        bin2 = self.factory.makeBin()
        self.failUnlessEqual(self.factory.current_bins, 2)
        self.failUnlessEqual(self.monitor.bin_created_count, 2)
        self.failUnless(isinstance(bin2, gst.Bin))

        self.factory.releaseBin(bin1)
        self.failUnlessEqual(self.factory.current_bins, 1)
        self.failUnlessEqual(self.monitor.bin_released_count, 1)
        self.factory.releaseBin(bin2)
        self.failUnlessEqual(self.factory.current_bins, 0)
        self.failUnlessEqual(self.monitor.bin_released_count, 2)

class TestLiveSourceFactory(TestCase):
    def testDefaultDuration(self):
        # pass an explicit default_duration
        factory = LiveSourceFactory('name', 'displayname', 10 * gst.SECOND)
        self.failUnlessEqual(factory.default_duration, 10 * gst.SECOND)
        
        # check that if a LiveSourceFactory derived class doesn't pass a
        # default_duration it's still set to 5 seconds
        factory = LiveSourceFactory('name', 'displayname')
        self.failUnlessEqual(factory.duration, gst.CLOCK_TIME_NONE)
        self.failUnlessEqual(factory.default_duration, 5 * gst.SECOND)

class TestRandomAccessSourceFactory(TestCase):
    def testOffsetAndLength(self):
        # no offset and length
        factory = RandomAccessSourceFactory('name', 'displayname')
        self.failUnlessEqual(factory.offset, 0)
        self.failUnlessEqual(factory.offset_length, gst.CLOCK_TIME_NONE)
        self.failUnlessEqual(factory.abs_offset, 0)
        self.failUnlessEqual(factory.abs_offset_length, gst.CLOCK_TIME_NONE)

        # offset and length without parent
        factory.offset = 5 * gst.SECOND
        factory.offset_length = 10 * gst.SECOND
        self.failUnlessEqual(factory.offset, 5 * gst.SECOND)
        self.failUnlessEqual(factory.abs_offset, 5 * gst.SECOND)
        self.failUnlessEqual(factory.offset_length, 10 * gst.SECOND)
        self.failUnlessEqual(factory.abs_offset_length, 10 * gst.SECOND)

        # parent offset
        relative = RandomAccessSourceFactory('name1', 'displayname1')
        relative.parent = factory
        self.failUnlessEqual(relative.offset, 0)
        self.failUnlessEqual(relative.offset_length, gst.CLOCK_TIME_NONE)
        self.failUnlessEqual(relative.abs_offset, 5 * gst.SECOND)
        self.failUnlessEqual(relative.abs_offset_length, 10 * gst.SECOND)

        # parent + local
        relative.offset = 1 * gst.SECOND
        relative.offset_length = 2 * gst.SECOND
        self.failUnlessEqual(relative.offset, 1 * gst.SECOND)
        self.failUnlessEqual(relative.offset_length, 2 * gst.SECOND)
        self.failUnlessEqual(relative.abs_offset, 6 * gst.SECOND)
        self.failUnlessEqual(relative.abs_offset_length, 2 * gst.SECOND)
        # unparent
        relative.parent = None
        self.failUnlessEqual(relative.abs_offset, 1 * gst.SECOND)
        self.failUnlessEqual(relative.abs_offset_length, 2 * gst.SECOND)
        relative.parent = factory

        # offset out of boundary
        relative.offset = 11 * gst.SECOND
        self.failUnlessEqual(relative.abs_offset, 15 * gst.SECOND)
        self.failUnlessEqual(relative.abs_offset_length, 0)

        # length out
        relative.offset = 5 * gst.SECOND
        relative.offset_length = 6 * gst.SECOND
        self.failUnlessEqual(relative.abs_offset, 10 * gst.SECOND)
        self.failUnlessEqual(relative.abs_offset_length, 5 * gst.SECOND)
        # move offset back
        relative.offset = 4 * gst.SECOND
        self.failUnlessEqual(relative.abs_offset, 9 * gst.SECOND)
        self.failUnlessEqual(relative.abs_offset_length, 6 * gst.SECOND)
