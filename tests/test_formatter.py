# PiTiVi , Non-linear video editor
#
#       test_formatter.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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
from StringIO import StringIO
import gst

from pitivi.reflect import qual, namedAny
from pitivi.formatters.etree import ElementTreeFormatter
from pitivi.stream import VideoStream, AudioStream
from pitivi.factories.file import FileSourceFactory

class FakeElementTreeFormatter(ElementTreeFormatter):
    pass

class TestFormatterSave(TestCase):
    def setUp(self):
        self.formatter = FakeElementTreeFormatter()

    def testSaveStream(self):
        stream = VideoStream(gst.Caps("video/x-raw-rgb, blah=meh"))
        element = self.formatter._saveStream(stream)
        self.failUnlessEqual(element.tag, "stream")
        self.failUnless("id" in element.attrib)
        self.failUnlessEqual(element.attrib["type"], qual(stream.__class__))
        self.failUnlessEqual(element.attrib["caps"], str(stream.caps))

    def testSaveSource(self):
        video_stream = VideoStream(gst.Caps("video/x-raw-yuv"))
        audio_stream = AudioStream(gst.Caps("audio/x-raw-int"))
        source = FileSourceFactory("file.ogg")
        source.addOutputStream(video_stream)
        source.addOutputStream(audio_stream)

        element = self.formatter._saveSource(source)
        self.failUnlessEqual(element.tag, "source")
        self.failUnlessEqual(element.attrib["type"], qual(source.__class__))
        self.failUnlessEqual(element.attrib["filename"], "file.ogg")

        streams = element.find("output-streams")
        self.failUnlessEqual(len(streams), 2)

    def testSaveFactories(self):
        raise NotImplementedError()

    def testSaveTrackObject(self):
        raise NotImplementedError()

    def testSaveTrack(self):
        raise NotImplementedError()

    def testSaveTimeline(self):
        raise NotImplementedError()
