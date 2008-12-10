#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       test_objectfactory.py
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

from pitivi.objectfactory import ObjectFactory, ObjectFactoryError, \
        SourceFactory, RandomAccessSourceFactory, LiveSourceFactory, \
        FileSourceFactory, PictureFileSourceFactory
from pitivi.stream import AudioStream, VideoStream
from pitivi.elements.imagefreeze import ImageFreeze

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

class TestSourceFactory(TestCase):
    def testSourceFactory(self):
        class StubSourceFactory(SourceFactory):
            def _makeBin(self, output_stream=None):
                return gst.Bin()
        
        factory = StubSourceFactory('name', 'displayname')
        caps = gst.Caps('video/x-raw-rgb')
        stream = VideoStream(caps)
        # source factories can't have input streams
        self.failUnlessRaises(AssertionError, factory.addInputStream, stream)
        factory.addOutputStream(stream)
        
        caps = gst.Caps('video/x-raw-yuv')
        stream1 = VideoStream(caps)
        # calling factory.makeBin(stream) with a stream that doesn't belong to a
        # factory should result in an error
        self.failUnlessRaises(ObjectFactoryError,
                factory.makeBin, stream1)
       
        # check makeBin with a specific stream
        bin = factory.makeBin(stream)
        self.failUnless(isinstance(bin, gst.Bin))
        # now check the "default" bin case
        bin = factory.makeBin()
        self.failUnless(isinstance(bin, gst.Bin))

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

class StubSingleDecodeBin(gst.Bin):
    def __init__(self, uri, caps, stream):
        self.uri = uri
        self.caps = caps
        self.stream = stream
        gst.Bin.__init__(self)

class StubFileSourceFactory(FileSourceFactory):
    singleDecodeBinClass = StubSingleDecodeBin

class TestFileSourceFactory(TestCase):
    def setUp(self):
        self.factory = StubFileSourceFactory('file:///path/to/file')

    def testFileSourceFilename(self):
        self.failUnlessEqual(self.factory.filename, 'file:///path/to/file')
        self.failUnlessEqual(self.factory.displayname, 'file')

    def testDefaultMakeBin(self):
        # the default bin for FileSource is a bin containing decodebin
        # TODO?: what we're testing here is that the method does return a bin and
        # doesn't rise exceptions. We're NOT changing the state of the bin.
        bin = self.factory.makeBin()
        self.failUnless(isinstance(bin, gst.Bin))

    def testDefaultBinGhostPads(self):
        bin = gst.Bin()
        pad = gst.Pad('meh', gst.PAD_SRC)
        pad.set_caps(gst.Caps('audio/x-raw-float'))
        self.factory._binNewDecodedPadCb(None, pad, None, bin)
        self.failIfEqual(bin.get_pad('meh'), None)
        self.factory._binRemovedDecodedPadCb(None, pad, bin)
        self.failUnlessEqual(bin.get_pad('meh'), None)

    def testMakeStreamBin(self):
        # streams are usually populated by the discoverer so here we have to do
        # that ourselves
        video = VideoStream(gst.Caps('video/x-raw-rgb'))
        audio = AudioStream(gst.Caps('audio/x-raw-int'))
        self.factory.addOutputStream(video)
        self.factory.addOutputStream(audio)
       
        bin = self.factory.makeBin(video)
        self.failUnless(isinstance(bin, StubSingleDecodeBin))
        self.failUnlessEqual(bin.uri, 'file:///path/to/file')
        self.failUnlessEqual(video.caps, bin.caps)
        self.failUnlessEqual(video, bin.stream)

class StubPictureFileSourceFactory(PictureFileSourceFactory):
    singleDecodeBinClass = StubSingleDecodeBin

class TestPictureFileSourceFactory(TestCase):
    def setUp(self):
        self.factory = StubPictureFileSourceFactory('file:///path/to/file')

    def testFileSourceFilename(self):
        self.failUnlessEqual(self.factory.filename, 'file:///path/to/file')
        self.failUnlessEqual(self.factory.displayname, 'file')

    def testDefaultMakeBin(self):
        # the default bin for FileSource is a bin containing decodebin
        # TODO?: what we're testing here is that the method does return a bin and
        # doesn't rise exceptions. We're NOT changing the state of the bin.
        bin = self.factory.makeBin()
        self.failUnless(isinstance(bin, gst.Bin))

    def testDefaultBinGhostPads(self):
        bin = gst.Bin()
        pad = gst.Pad('meh', gst.PAD_SRC)
        pad.set_caps(gst.Caps('audio/x-raw-float'))
        scale = gst.element_factory_make('identity')
        freeze = ImageFreeze()
        self.factory._dbinPadAddedCb(None, pad, scale, freeze, bin)
        self.failIfEqual(bin.get_pad('src'), None)
        self.factory._dbinPadRemovedCb(None, pad, scale, freeze, bin)
        self.failUnlessEqual(bin.get_pad('src'), None)

    def testMakeStreamBin(self):
        # streams are usually populated by the discoverer so here we have to do
        # that ourselves
        video1 = VideoStream(gst.Caps('video/x-raw-rgb, width=2048'))
        video2 = VideoStream(gst.Caps('video/x-raw-rgb, width=320'))
        audio = AudioStream(gst.Caps('audio/x-raw-int'))
        self.factory.addOutputStream(video1)
        self.factory.addOutputStream(video2)
        self.factory.addOutputStream(audio)
       
        bin = self.factory.makeBin(video2)
        # for width < 2048 we should use ffvideoscale
        scale = bin.get_by_name("scale")
        self.failUnlessEqual(scale.get_factory().get_name(), 'ffvideoscale')

        # if ffvideoscale isn't available we should still fallback to videoscale
        self.factory.ffscale_factory = 'meh'
        bin = self.factory.makeBin(video2)
        scale = bin.get_by_name("scale")
        self.failUnlessEqual(scale.get_factory().get_name(), 'videoscale')
       
        bin = self.factory.makeBin(video1)
        # here we expect videoscale instead
        scale = bin.get_by_name("scale")
        self.failUnlessEqual(scale.get_factory().get_name(), 'videoscale')
