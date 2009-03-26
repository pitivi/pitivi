# PiTiVi , Non-linear video editor
#
#       tests/test_timeline.py
#
# Copyright (c) 2008, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

import gobject
gobject.threads_init()
import gst
from common import TestCase
from pitivi.factories.base import ObjectFactoryError
from pitivi.factories.timeline import TimelineSourceFactory
from pitivi.factories.test import VideoTestSourceFactory, \
        AudioTestSourceFactory
from pitivi.timeline.timeline import Timeline
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.stream import AudioStream, VideoStream

class TestTimelineSourceFactory(TestCase):
    def testEmpty(self):
        timeline = Timeline()
        factory = TimelineSourceFactory(timeline)
        bin = factory.makeBin()
        self.failUnlessRaises(ObjectFactoryError, factory.makeBin)

        self.failUnlessEqual(len(list(bin)), 0)

        factory.clean()

    def testTracks(self):
        timeline = Timeline()
        stream1 = VideoStream(gst.Caps('video/x-raw-rgb'), 'src0')
        stream2 = AudioStream(gst.Caps('audio/x-raw-int'), 'src1')
        track1 = Track(stream1)
        track2 = Track(stream2)

        # start with 2 tracks
        timeline.addTrack(track1)
        timeline.addTrack(track2)

        factory = TimelineSourceFactory(timeline)
        bin = factory.makeBin()
        self.failUnlessEqual(len(list(bin)), 2)
        self.failUnlessEqual(set(factory.getOutputStreams()),
                set([stream1, stream2]))

        # add a new track
        stream3 = AudioStream(gst.Caps('audio/x-raw-int'), 'src2')
        track3 = Track(stream3)
        timeline.addTrack(track3)
        self.failUnlessEqual(len(list(bin)), 3)
        self.failUnlessEqual(set(factory.getOutputStreams()),
                set([stream1, stream2, stream3]))

        # remove a track
        timeline.removeTrack(track3)
        self.failUnlessEqual(len(list(bin)), 2)
        self.failUnlessEqual(set(factory.getOutputStreams()),
                set([stream1, stream2]))

        factory.clean()

    def testPads(self):
        timeline = Timeline()
        stream1 = VideoStream(gst.Caps('video/x-raw-rgb'), 'src0')
        stream2 = AudioStream(gst.Caps('audio/x-raw-int'), 'src1')
        track1 = Track(stream1)
        track2 = Track(stream2)

        timeline.addTrack(track1)
        timeline.addTrack(track2)

        factory = TimelineSourceFactory(timeline)
        bin = factory.makeBin()

        self.failUnlessEqual(len(list(bin.src_pads())), 0)

        pad1 = gst.Pad('src0', gst.PAD_SRC)
        pad1.set_caps(gst.Caps('asd'))
        pad1.set_active(True)
        track1.composition.add_pad(pad1)

        pad2 = gst.Pad('src0', gst.PAD_SRC)
        pad2.set_caps(gst.Caps('asd'))
        pad2.set_active(True)
        track2.composition.add_pad(pad2)

        self.failUnlessEqual(len(list(bin.src_pads())), 2)
        track1.composition.remove_pad(pad1)
        self.failUnlessEqual(len(list(bin.src_pads())), 1)
        track2.composition.remove_pad(pad2)
        self.failUnlessEqual(len(list(bin.src_pads())), 0)

        factory.clean()

class MainLoopTestCaseMeta(type):
    def __new__(cls, name, bases, dic):
        import sys, inspect

        def wrapTest(method):
            def wrapper(self):
                method(self)
                if self._pending_exc_info is not None:
                    e = self._pending_exc_info
                    raise e[0], e[1], e[2]

            wrapper.__name__ = method.__name__
            wrapper.__doc__ = method.__doc__
            return wrapper

        for name, value in dic.items():
            if name.startswith('test') and inspect.isfunction(value):
                dic[name] = wrapTest(value)

        cls = type.__new__(cls, name, bases, dic)
        cls._pending_exc_info = None

        def wrapFail(method):
            def wrapper(self, *args):
                self.loop.quit()
                try:
                    method(self, *args)
                except:
                    if self._pending_exc_info is None:
                        # we're only interested in the first exception
                        self._pending_exc_info = sys.exc_info()

            wrapper.__name__ = method.__name__
            wrapper.__doc__ = method.__doc__
            return wrapper

        for fail in ('fail', 'failIf', 'failUnless',
                'failIfEqual', 'failUnlessEqual',
                'failIfAlmostEqual', 'failUnlessAlmostEqual',
                'failUnlessRaises'):
            setattr(cls, fail, wrapFail(getattr(cls, fail)))

        return cls

class MainLoopTestCase(TestCase):
    __metaclass__ = MainLoopTestCaseMeta

    def __init__(self, methodName='runTest'):
        self.loop = gobject.MainLoop()
        TestCase.__init__(self, methodName)

class TestTimelineSourceFactoryPipeline(MainLoopTestCase):
    def testVideoOnly(self):
        video_factory1 = VideoTestSourceFactory(3)
        video_factory1.duration = 3 * gst.SECOND
        stream = VideoStream(gst.Caps('video/x-raw-rgb'), 'src0')
        video_factory1.addOutputStream(stream)

        timeline = Timeline()
        track = Track(stream)
        track_object1 = SourceTrackObject(video_factory1, stream)
        track_object1.start = 1 * gst.SECOND
        track.addTrackObject(track_object1)
        timeline.addTrack(track)

        factory = TimelineSourceFactory(timeline)
        bin = factory.makeBin()
        self.failUnlessEqual(len(list(bin)), 1)
        self.failUnlessEqual(factory.duration, 4 * gst.SECOND)

        fakesink = gst.element_factory_make('fakesink')

        def bin_pad_added_cb(bin, pad):
            pad.link(fakesink.get_pad('sink'))

        bin.connect('pad-added', bin_pad_added_cb)

        def error_cb(bus, message):
            gerror, debug = message.parse_error()
            self.fail('%s: %s' % (gerror.message, debug))

        def eos_cb(bus, message):
            self.loop.quit()

        pipeline = gst.Pipeline()
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::error', error_cb)
        bus.connect('message::eos', eos_cb)

        pipeline.add(bin)
        pipeline.add(fakesink)

        pipeline.set_state(gst.STATE_PLAYING)
        self.loop.run()
        pipeline.set_state(gst.STATE_NULL)

        factory.clean()

    def testAudioOnly(self):
        audio_factory1 = AudioTestSourceFactory(3)
        audio_factory1.duration = 10 * gst.SECOND
        stream = AudioStream(gst.Caps('audio/x-raw-int'), 'src0')
        audio_factory1.addOutputStream(stream)

        timeline = Timeline()
        track = Track(stream)
        track_object1 = SourceTrackObject(audio_factory1, stream)
        track_object1.start = 2 * gst.SECOND
        track.addTrackObject(track_object1)
        timeline.addTrack(track)

        factory = TimelineSourceFactory(timeline)
        bin = factory.makeBin()
        self.failUnlessEqual(len(list(bin)), 1)
        self.failUnlessEqual(factory.duration, 12 * gst.SECOND)

        fakesink = gst.element_factory_make('fakesink')

        def bin_pad_added_cb(bin, pad):
            pad.link(fakesink.get_pad('sink'))

        bin.connect('pad-added', bin_pad_added_cb)

        def error_cb(bus, message):
            gerror, debug = message.parse_error()
            self.fail('%s: %s' % (gerror.message, debug))

        def eos_cb(bus, message):
            self.loop.quit()

        pipeline = gst.Pipeline()
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::error', error_cb)
        bus.connect('message::eos', eos_cb)

        pipeline.add(bin)
        pipeline.add(fakesink)

        pipeline.set_state(gst.STATE_PLAYING)
        self.loop.run()
        pipeline.set_state(gst.STATE_NULL)

        factory.clean()

    def testAudioVideo(self):
        audio_factory1 = AudioTestSourceFactory(3)
        audio_factory1.duration = 10 * gst.SECOND
        audio_stream = AudioStream(gst.Caps('audio/x-raw-int'), 'src0')
        audio_factory1.addOutputStream(audio_stream)

        video_factory1 = VideoTestSourceFactory(3)
        video_factory1.duration = 3 * gst.SECOND
        video_stream = VideoStream(gst.Caps('video/x-raw-rgb'), 'src1')
        video_factory1.addOutputStream(video_stream)

        timeline = Timeline()
        video_track = Track(video_stream)
        audio_track = Track(audio_stream)

        track_object1 = SourceTrackObject(audio_factory1, audio_stream)
        track_object1.start = 2 * gst.SECOND
        audio_track.addTrackObject(track_object1)
        timeline.addTrack(audio_track)

        track_object2 = SourceTrackObject(video_factory1, video_stream)
        track_object2.start = 2 * gst.SECOND
        video_track.addTrackObject(track_object2)
        timeline.addTrack(video_track)

        factory = TimelineSourceFactory(timeline)
        bin = factory.makeBin()
        self.failUnlessEqual(len(list(bin)), 2)
        self.failUnlessEqual(factory.duration, 12 * gst.SECOND)

        fakesink1 = gst.element_factory_make('fakesink')
        fakesink2 = gst.element_factory_make('fakesink')
        fakesinks = [fakesink1, fakesink2]

        def bin_pad_added_cb(bin, pad):
            pad.link(fakesinks.pop(0).get_pad('sink'))

        bin.connect('pad-added', bin_pad_added_cb)

        def error_cb(bus, message):
            gerror, debug = message.parse_error()
            self.fail('%s: %s' % (gerror.message, debug))

        def eos_cb(bus, message):
            self.loop.quit()

        pipeline = gst.Pipeline()
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::error', error_cb)
        bus.connect('message::eos', eos_cb)

        pipeline.add(bin)
        pipeline.add(fakesink1)
        pipeline.add(fakesink2)

        pipeline.set_state(gst.STATE_PLAYING)
        self.loop.run()
        pipeline.set_state(gst.STATE_NULL)

        factory.clean()

