#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       test_factories_file.py
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
from common import TestCase

from pitivi.factories.file import FileSourceFactory, PictureFileSourceFactory
from pitivi.stream import AudioStream, VideoStream
from pitivi.elements.imagefreeze import ImageFreeze

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
        TestCase.setUp(self)
        self.factory = StubFileSourceFactory('file:///path/to/file')

    def tearDown(self):
        self.factory = None
        TestCase.tearDown(self)

    def testFileSourceFilename(self):
        self.failUnlessEqual(self.factory.filename, 'file:///path/to/file')
        self.failUnlessEqual(self.factory.name, 'file')

    def testDefaultMakeBin(self):
        # the default bin for FileSource is a bin containing decodebin
        # TODO?: what we're testing here is that the method does return a bin and
        # doesn't rise exceptions. We're NOT changing the state of the bin.
        bin = self.factory.makeBin()
        self.failUnless(isinstance(bin, gst.Bin))
        self.factory.releaseBin(bin)

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
        video = VideoStream(gst.Caps('video/x-raw-rgb'), pad_name='src0')
        audio = AudioStream(gst.Caps('audio/x-raw-int'), pad_name='src1')
        self.factory.addOutputStream(video)
        self.factory.addOutputStream(audio)
        bin = self.factory.makeBin(video)
        self.failUnless(hasattr(bin, "decodebin"))
        self.failUnless(isinstance(bin.decodebin, StubSingleDecodeBin))
        self.failUnlessEqual(bin.decodebin.uri, 'file:///path/to/file')
        self.failUnlessEqual(video.caps, bin.decodebin.caps)
        self.failUnlessEqual(video, bin.decodebin.stream)
        self.factory.releaseBin(bin)

class StubPictureFileSourceFactory(PictureFileSourceFactory):
    singleDecodeBinClass = StubSingleDecodeBin

class TestPictureFileSourceFactory(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.factory = StubPictureFileSourceFactory('file:///path/to/file')

    def tearDown(self):
        self.factory = None
        TestCase.tearDown(self)

    def test(self):
        pass

    def testFileSourceFilename(self):
        self.failUnlessEqual(self.factory.filename, 'file:///path/to/file')
        self.failUnlessEqual(self.factory.name, 'file')

    def testDefaultMakeBin(self):
        # the default bin for FileSource is a bin containing decodebin
        # what we're testing here is that the method does return a bin and
        # doesn't rise exceptions. We're NOT changing the state of the bin.
        video1 = VideoStream(gst.Caps('video/x-raw-rgb, width=2048'),
                pad_name='src0')
        self.factory.addOutputStream(video1)
        bin = self.factory.makeBin()
        self.failUnless(isinstance(bin, gst.Bin))
        self.factory.releaseBin(bin)

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
        video1 = VideoStream(gst.Caps('video/x-raw-rgb, width=2048'),
                pad_name='src0')
        video2 = VideoStream(gst.Caps('video/x-raw-rgb, width=320'),
                pad_name='src1')
        audio = AudioStream(gst.Caps('audio/x-raw-int'), pad_name='src2')
        self.factory.addOutputStream(video1)
        self.factory.addOutputStream(video2)
        self.factory.addOutputStream(audio)

        if gst.registry_get_default().find_feature('ffvideoscale',
                gst.ElementFactory):
            bin = self.factory.makeBin(video2)
            # for width < 2048 we should use ffvideoscale
            scale = bin.get_by_name("scale")
            self.failUnlessEqual(scale.get_factory().get_name(), 'ffvideoscale')
            self.factory.releaseBin(bin)

        # if ffvideoscale isn't available we should still fallback to videoscale
        self.factory.ffscale_factory = 'meh'
        bin = self.factory.makeBin(video2)
        scale = bin.get_by_name("scale")
        self.failUnlessEqual(scale.get_factory().get_name(), 'videoscale')
        self.factory.releaseBin(bin)

        bin = self.factory.makeBin(video1)
        # here we expect videoscale instead
        scale = bin.get_by_name("scale")
        self.failUnlessEqual(scale.get_factory().get_name(), 'videoscale')
        self.factory.releaseBin(bin)
