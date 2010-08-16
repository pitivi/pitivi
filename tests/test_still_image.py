# PiTiVi , Non-linear video editor
#
#       tests/test_still_image.py
#
# Copyright (c) 2010, Robert Swain <robert.swain@collabora.co.uk>
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

import os.path
from unittest import TestCase

import gobject
gobject.threads_init()
import gst

import common

from pitivi.factories.file import FileSourceFactory, PictureFileSourceFactory
from pitivi.factories.timeline import TimelineSourceFactory
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.timeline.timeline import Timeline, TimelineObject
from pitivi.encode import RenderSinkFactory, RenderFactory
from pitivi.action import RenderAction
from pitivi.settings import StreamEncodeSettings, RenderSettings
from pitivi.stream import VideoStream
from pitivi.factories.test import VideoTestSourceFactory
from pitivi.pipeline import Pipeline, PipelineError

class TestStillImage(TestCase):
    clip_duration = 3 * gst.SECOND
    def setUp(self):
        self.mainloop = gobject.MainLoop()

        samples = os.path.join(os.path.dirname(__file__), "samples")
        self.facs = []
        self.facs.append([PictureFileSourceFactory('file://' + os.path.join(samples, "flat_colour1_640x480.png")), VideoStream(gst.Caps("video/x-raw-rgb,bpp=(int)24,depth=(int)24,endianness=(int)4321,red_mask=(int)16711680,green_mask=(int)65280,blue_mask=(int)255"))])
        self.facs.append([PictureFileSourceFactory('file://' + os.path.join(samples, "flat_colour2_640x480.png")), VideoStream(gst.Caps("video/x-raw-rgb,bpp=(int)24,depth=(int)24,endianness=(int)4321,red_mask=(int)16711680,green_mask=(int)65280,blue_mask=(int)255"))])
        self.facs.append([PictureFileSourceFactory('file://' + os.path.join(samples, "flat_colour3_320x180.png")), VideoStream(gst.Caps("video/x-raw-rgb,bpp=(int)24,depth=(int)24,endianness=(int)4321,red_mask=(int)16711680,green_mask=(int)65280,blue_mask=(int)255"))])
        # one video with a different resolution
        self.facs.append([VideoTestSourceFactory(), VideoStream(gst.Caps('video/x-raw-yuv,width=(int)640,height=(int)480,format=(fourcc)I420'))])

        # configure durations and add output streams to factories
        for fac in self.facs:
            factory = fac[0]
            stream = fac[1]
            factory.duration = self.clip_duration
            factory.addOutputStream(stream)
        self.track_objects = []
        self.track = Track(self.facs[0][1])
        self.timeline = Timeline()
        self.timeline.addTrack(self.track)

        vsettings = StreamEncodeSettings(encoder="theoraenc")
        rsettings = RenderSettings(settings=[vsettings],
                                   muxer="oggmux")
        self.fakesink = common.FakeSinkFactory()
        rendersink = RenderSinkFactory(RenderFactory(settings=rsettings),
                                       self.fakesink)
        self.render = RenderAction()
        self.pipeline = Pipeline()
        self.pipeline.connect("eos", self._renderEOSCb)
        self.pipeline.connect("error", self._renderErrorCb)
        self.pipeline.addAction(self.render)
        self.render.addConsumers(rendersink)
        timeline_factory = TimelineSourceFactory(self.timeline)
        self.render.addProducers(timeline_factory)

    def tearDown(self):
        self.mainloop.quit()

    def configureStreams(self, inputs, offsets):
        count = 0
        for i in inputs:
            factory = self.facs[i][0]
            stream = self.facs[i][1]
            track_object = SourceTrackObject(factory, stream)
            self.track_objects.append(track_object)
            track_object.start = offsets[count]
            self.track.addTrackObject(track_object)
            count += 1

    def startRender(self):
        self.render.activate()
        self.data_written = 0
        self.fakesink.bins[0].props.signal_handoffs = True
        self.fakesink.bins[0].connect("handoff", self._fakesinkHandoffCb)
        self.pipeline.play()
        self.mainloop.run()

    def _fakesinkHandoffCb(self, fakesink, buf, pad):
        self.data_written += buf.size

    def _renderEOSCb(self, obj):
        self.mainloop.quit()
        # check the render was successful
        self.assertTrue(self.data_written > 0)

    def _renderErrorCb(self, obj, error, details):
        print "Error: %s\nDetails: %s" % (str(error), str(details))
        self.fail("Pipeline rendering error")

    def cleanUp(self):
        self.render.deactivate()
        self.track.removeAllTrackObjects()
        self.track_objects = []

    def testRendering(self):
        # use one of the still image streams
        self.configureStreams(range(1), [0])
        self.startRender()
        self.cleanUp()


        # use two images with the same resolution and concatenate them
        self.configureStreams(range(2), [0, self.clip_duration])
        self.startRender()
        self.cleanUp()


        # concatenate images with different resolutions
        self.configureStreams(range(3), [0, self.clip_duration, 2 * self.clip_duration])
        self.startRender()
        self.cleanUp()


        # mix images and videos with the same resolution
        self.configureStreams([0, 1, 3], [0, self.clip_duration, 2 * self.clip_duration])
        self.startRender()
        self.cleanUp()


        # mix images and videos with different resolutions
        self.configureStreams(range(4), [0, self.clip_duration, 2 * self.clip_duration, 3 * self.clip_duration])
        self.startRender()
        self.cleanUp()

