# PiTiVi , Non-linear video editor
#
#       tests/test_alpha_passthrough.py
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

from unittest import TestCase

import random

import gobject
gobject.threads_init()
import gst

from pitivi.factories.test import VideoTestSourceFactory
from pitivi.stream import VideoStream
from pitivi.timeline.track import Track, SourceTrackObject, Interpolator
from pitivi.elements.mixer import SmartVideomixerBinPropertyHelper
from pitivi.utils import infinity

class TestAlpha(TestCase):
    def setUp(self):
        # create a pipeline
        self.pipeline = gst.Pipeline()

        # define some streams
        streams = []
        streams.append([VideoStream(gst.Caps('video/x-raw-yuv,format=(fourcc)I420')), VideoTestSourceFactory()])
        streams.append([VideoStream(gst.Caps('video/x-raw-yuv,format=(fourcc)Y444')), VideoTestSourceFactory()])
        streams.append([VideoStream(gst.Caps('video/x-raw-yuv,format=(fourcc)AYUV')), VideoTestSourceFactory()])

        # make a track, make track objects from the streams and add the track objects to the track
        offset = 0
        self.track1 = Track(streams[0][0])
        for item in streams:
            stream = item[0]
            factory = item[1]
            factory.duration = 15 * gst.SECOND
            factory.addOutputStream(stream)
            track_object = SourceTrackObject(factory, stream)
            track_object.start = offset
            self.track1.addTrackObject(track_object)
            offset += 15 * gst.SECOND

        # make a fakesink for the pipeline and connect it as necessary with a callback
        composition = self.track1.composition
        fakesink = gst.element_factory_make('fakesink')
        def bin_pad_added_cb(composition, pad):
            pad.link(fakesink.get_pad('sink'))
        composition.connect("pad-added", bin_pad_added_cb)

        # add the composition and fakesink to the pipeline and set state to paused to preroll
        self.pipeline.add(composition)
        self.pipeline.add(fakesink)
        self.pipeline.set_state(gst.STATE_PAUSED)
 
        # wait for preroll to complete
        bus = self.pipeline.get_bus()
        msg = bus.timed_pop_filtered(gst.CLOCK_TIME_NONE, gst.MESSAGE_ASYNC_DONE | gst.MESSAGE_ERROR)
        if msg.type == gst.MESSAGE_ERROR:
            gerror, debug = msg.parse_error()
            print "\nError message: %s\nDebug info: %s" % (gerror, debug)
        self.failUnlessEqual(msg.type, gst.MESSAGE_ASYNC_DONE)

    def tearDown(self):
        self.pipeline.set_state(gst.STATE_NULL)
        TestCase.tearDown(self)

    def testAlphaAggregation(self):
        svmbin_inputs = list(self.track1.mixer.elements())[0].inputs.values()

        # adjust all up to 1.0
        for track_obj in self.track1.track_objects:
            interpolator = track_obj.getInterpolator("alpha")
            if interpolator is not None:
                for kf in interpolator.getKeyframes():
                    interpolator.setKeyframeValue(kf, 1.0)
        # check that each SmartVideomixerBin input has alpha _not_ set on its capsfilter
        for input in svmbin_inputs:
            svmbin_input_capsfilter = input[2]
            self.failIf(svmbin_input_capsfilter.props.caps[0].has_key("format"))

        # adjust one below 1.0
        obj = self.track1.track_objects[1]
        interpolator = obj.getInterpolator("alpha")
        for kf in interpolator.getKeyframes():
            interpolator.setKeyframeValue(kf, 0.8)
            break
        # check that each SmartVideomixerBin input has alpha set on its capsfilter
        for input in svmbin_inputs:
            svmbin_input_capsfilter = input[2]
            self.failUnlessEqual(svmbin_input_capsfilter.props.caps[0]["format"], gst.Fourcc('AYUV'))

        # adjust all below 1.0
        for track_obj in self.track1.track_objects:
            interpolator = track_obj.getInterpolator("alpha")
            if interpolator is not None:
                for kf in interpolator.getKeyframes():
                    # random() should return a value in the range [0.0, 1.0)
                    interpolator.setKeyframeValue(kf, 0.9 * random.random())
        # check that each SmartVideomixerBin input has alpha set on its capsfilter
        for input in svmbin_inputs:
            svmbin_input_capsfilter = input[2]
            self.failUnlessEqual(svmbin_input_capsfilter.props.caps[0]["format"], gst.Fourcc('AYUV'))

        # adjust first one to 1.0
        obj = self.track1.track_objects[0]
        interpolator = obj.getInterpolator("alpha")
        for kf in interpolator.getKeyframes():
            interpolator.setKeyframeValue(kf, 1.0)
            break
        # check that each SmartVideomixerBin input has alpha set on its capsfilter
        for input in svmbin_inputs:
            svmbin_input_capsfilter = input[2]
            self.failUnlessEqual(svmbin_input_capsfilter.props.caps[0]["format"], gst.Fourcc('AYUV'))

        # adjust all up to 1.0 again
        for track_obj in self.track1.track_objects:
            interpolator = track_obj.getInterpolator("alpha")
            if interpolator is not None:
                for kf in interpolator.getKeyframes():
                    interpolator.setKeyframeValue(kf, 1.0)
        # check that each SmartVideomixerBin input has alpha _not_ set on its capsfilter
        for input in svmbin_inputs:
            svmbin_input_capsfilter = input[2]
            self.failIf(svmbin_input_capsfilter.props.caps[0].has_key("format"))

