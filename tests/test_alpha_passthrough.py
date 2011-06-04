# PiTiVi , Non-linear video editor
#
#       tests/test_alpha_passthrough.py
#
# Copyright (c) 2010, Robert Swain <robert.swain@collabora.co.uk>
# Copyright (c) 2010, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

def set_one_keyframe(track_object, value):
    interpolator = track_object.getInterpolator("alpha")
    kf = list(interpolator.getKeyframes())[0]
    interpolator.setKeyframeValue(kf, value)

def set_all_keyframes(track_object, value):
    interpolator = track_object.getInterpolator("alpha")
    if interpolator is not None:
        for kf in interpolator.getKeyframes():
            if callable(value):
                val = value()
            else:
                val = value
            interpolator.setKeyframeValue(kf, val)

def yuv(fourcc):
    caps = gst.Caps("video/x-raw-yuv,format=(fourcc)%s" % fourcc)
    return VideoStream(caps)

def rgb():
    caps = gst.Caps("video/x-raw-rgb,bpp=(int)24,depth=(int)24,"
            "endianness=(int)4321,red_mask=(int)16711680,"
            "green_mask=(int)65280,blue_mask=(int)255")
    return VideoStream(caps)

def make_track_object(stream):
    factory = VideoTestSourceFactory()
    factory.duration = 15 * gst.SECOND
    return SourceTrackObject(factory, stream)

class TestAlpha(TestCase):
    def setUp(self):
        # create a pipeline
        self.pipeline = gst.Pipeline()

        self.track1 = Track(yuv("I420"))
        track_object1 = make_track_object(yuv("I420"))
        track_object2 = make_track_object(yuv("Y42B"))
        track_object3 = make_track_object(yuv("Y444"))
        track_object4 = make_track_object(rgb())
        track_object5 = make_track_object(yuv("AYUV"))

        for i, track_object in enumerate((track_object1, track_object2,
                    track_object3, track_object4, track_object5)):
            self.track1.addTrackObject(track_object)

            # set priorities from 1 to 5
            track_object.priority = i + 1

        # track_object5 falls outside (0s, 15s) so it isn't linked to videomixer
        track_object5.start = 15 * gst.SECOND

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
        msg = bus.timed_pop_filtered(gst.CLOCK_TIME_NONE,
                gst.MESSAGE_ASYNC_DONE | gst.MESSAGE_ERROR)
        if msg.type == gst.MESSAGE_ERROR:
            gerror, debug = msg.parse_error()
            print "\nError message: %s\nDebug info: %s" % (gerror, debug)
        self.failUnlessEqual(msg.type, gst.MESSAGE_ASYNC_DONE)

        self.svmbin = list(self.track1.mixer.elements())[0]

    def tearDown(self):
        self.pipeline.set_state(gst.STATE_NULL)
        TestCase.tearDown(self)

    def failUnlessAlphaIsSet(self):
        # check that each SmartVideomixerBin input has alpha set on its
        # capsfilter
        for input in self.svmbin.inputs.values():
            capsfilter = input[2]
            self.failUnless(capsfilter.props.caps[0].has_key("format"))

    def failUnlessAlphaIsNotSet(self):
        # check that each SmartVideomixerBin input has alpha _not_ set on its
        # capsfilter
        for input in self.svmbin.inputs.values():
            capsfilter = input[2]
            self.failIf(capsfilter.props.caps[0].has_key("format"))

    def testKeyframesOnDifferentObjects(self):
        # no alpha < 1.0 keyframes
        for track_obj in self.track1.track_objects:
            set_all_keyframes(track_obj, 1.0)
        self.failUnlessAlphaIsNotSet()

        track_object1 = self.track1.track_objects[0]
        track_object2 = self.track1.track_objects[1]

        # one alpha < 1.0 keyframe
        set_one_keyframe(track_object1, 0.8)
        self.failUnlessAlphaIsSet()

        # two alpha < 1.0 keyframes
        set_one_keyframe(track_object2, 0.5)
        self.failUnlessAlphaIsSet()

        # one alpha < 1.0 keyframe
        set_one_keyframe(track_object1, 1.0)
        self.failUnlessAlphaIsSet()

        # no alpha < 1.0 keyframes
        set_one_keyframe(track_object2, 1.0)

        self.failUnlessAlphaIsNotSet()

    def testKeyframesOnSameObject(self):
        for track_obj in self.track1.track_objects:
            set_all_keyframes(track_obj, 1.0)
        self.failUnlessAlphaIsNotSet()

        track_object1 = self.track1.track_objects[0]
        interpolator1 = track_object1.getInterpolator("alpha")

        keyframe1 = interpolator1.newKeyframe(1 * gst.SECOND, 0.8)
        self.failUnlessAlphaIsSet()

        keyframe2 = interpolator1.newKeyframe(2 * gst.SECOND, 0.5)
        self.failUnlessAlphaIsSet()

        interpolator1.setKeyframeValue(keyframe1, 1.0)
        self.failUnlessAlphaIsSet()

        interpolator1.removeKeyframe(keyframe2)
        self.failUnlessAlphaIsNotSet()

    def testRemoveTrackObjects(self):
        for track_obj in self.track1.track_objects:
            set_all_keyframes(track_obj, 1.0)

        self.failUnlessAlphaIsNotSet()

        track_object1 = self.track1.track_objects[0]
        track_object2 = self.track1.track_objects[1]

        # set one keyframe below 1.0
        set_one_keyframe(track_object1, 0.8)
        self.failUnlessAlphaIsSet()

        # track_object2 has no alpha < 1.0 keyframes, removing it shouldn't
        # trigger an alpha change
        self.track1.removeTrackObject(track_object2)
        self.failUnlessAlphaIsSet()

        # track_object1 does have an alpha < 1.0 keyframe, removing it should
        # trigger an alpha change
        self.track1.removeTrackObject(track_object1)

        self.failUnlessAlphaIsNotSet()

    def testRequestPads(self):
        # requesting a new pad should never trigger an alpha change

        template = gst.PadTemplate("sink_%u", gst.PAD_SINK, gst.PAD_REQUEST,
                gst.Caps("video/x-raw-yuv;video/x-raw-rgb"))

        for track_obj in self.track1.track_objects:
            set_all_keyframes(track_obj, 1.0)

        # when unset, should remain unset
        self.failUnlessAlphaIsNotSet()
        test_pad1 = self.svmbin.do_request_new_pad(template)
        self.failUnlessAlphaIsNotSet()

        obj = self.track1.track_objects[0]
        set_one_keyframe(obj, 0.8)

        # when set, should remain set
        self.failUnlessAlphaIsSet()
        test_pad2 = self.svmbin.do_request_new_pad(template)
        self.failUnlessAlphaIsSet()

    def testTransitions(self):
        for track_obj in self.track1.track_objects:
            set_all_keyframes(track_obj, 1.0)
        self.failUnlessAlphaIsNotSet()

        track_object1 = self.track1.track_objects[0]
        track_object2 = self.track1.track_objects[1]

        track_object1.start = 0
        track_object2.start = 10 * gst.SECOND

        old_priority = track_object2.priority
        track_object2.priority = track_object1.priority
        self.track1.updateTransitions()
        self.failUnlessAlphaIsSet()

        track_object2.priority = old_priority
        self.track1.updateTransitions()
        self.failUnlessAlphaIsNotSet()
