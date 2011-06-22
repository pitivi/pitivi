#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       test_discoverer.py
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import gobject
gobject.threads_init()
import gst

from common import TestCase
from pitivi.discoverer import Discoverer
from pitivi.factories.file import FileSourceFactory, PictureFileSourceFactory


class AddUrisStubDiscoverer(Discoverer):
    analysis_scheduled = 0
    current_uri = "bar"

    def _scheduleAnalysis(self):
        self.analysis_scheduled += 1

    def _finishAnalysis(self, reason):
        self.analysis_scheduled -= 1
        return Discoverer._finishAnalysis(self, reason)


class TestAnalysisQueue(TestCase):
    def testAddUri(self):
        discoverer = AddUrisStubDiscoverer()
        self.failIf(discoverer.working)
        # add a file, should start working
        discoverer.addUri('meh')
        self.failUnless(discoverer.working)
        self.failUnlessEqual(discoverer.analysis_scheduled, 1)

        # finish analysis, no other files queued
        discoverer._finishAnalysis("foo")
        self.failIf(discoverer.working)
        self.failUnlessEqual(discoverer.analysis_scheduled, 0)

        # add another file, should start working
        discoverer.addUri('meh1')
        self.failUnless(discoverer.working)
        self.failUnlessEqual(discoverer.analysis_scheduled, 1)

        # queue another while the first isn't finished yet
        discoverer.addUri('meh2')
        # this shouldn't trigger a new analysis until the previous is done
        self.failUnless(discoverer.analysis_scheduled, 1)

        discoverer._finishAnalysis("foo")
        # something queued, keep working
        self.failUnless(discoverer.working)
        self.failUnlessEqual(discoverer.analysis_scheduled, 1)

        discoverer._finishAnalysis("foo")
        self.failIf(discoverer.working)
        self.failUnlessEqual(discoverer.analysis_scheduled, 0)


class Discoverer1(Discoverer):
    use_decodebin2 = True
    timeout_scheduled = False
    timeout_expired = True
    timeout_cancelled = False
    new_video_pad_cb = 0
    new_pad_cb = 0

    def _scheduleAnalysis(self):
        # we call _analyze manually so we don't have to do tricks to keep test
        # methods alive across mainloop iterations
        pass

    def _scheduleTimeout(self):
        self.timeout_scheduled = True
        self.timeout_id = 1
        if self.timeout_expired:
            self._timeoutCb()

    def _removeTimeout(self):
        self.timeout_id = 0
        self.timeout_cancelled = True

    def _useDecodeBinTwo(self):
        return self.use_decodebin2

    def _createSource(self):
        if self.current_uri == 'foo':
            # create something that will go to paused
            source = gst.element_factory_make('videotestsrc')
            source.props.num_buffers = 1
        else:
            source = Discoverer._createSource(self)

        return source

    def _newVideoPadCb(self, pad):
        Discoverer._newVideoPadCb(self, pad)
        self.new_video_pad_cb += 1

    def _newPadCb(self, pad):
        Discoverer._newPadCb(self, pad)
        self.new_pad_cb += 1


class TestAnalysis(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.discoverer = Discoverer1()
        self.discoverer.current_uri = "meh"
        self.discoverer.pipeline = gst.Bin()

    def tearDown(self):
        self.discoverer = None
        TestCase.tearDown(self)

    def testNoSource(self):
        """
        Check that discoverer errors out if it can't create a source element.
        """
        bag = {'error': None}

        def no_media_file_cb(disc, uri, error, error_detail):
            bag['error'] = error

        self.discoverer.addUri('buh://asd')
        self.discoverer.connect('discovery-error', no_media_file_cb)
        self.discoverer._analyze()
        self.failUnlessEqual(bag['error'], 'No available source handler.')

    def testErrorSettingPaused(self):
        """
        Check for errors setting the state of the pipeline to PAUSED.
        """
        bag = {'error': None}

        def no_media_file_cb(disc, uri, error, error_detail):
            bag['error'] = error

        self.discoverer.addUri('file://i/cant/possibly/exist/and/if/you/'
            'really/have/a/file/named/like/this/you/deserve/a/faillure')
        self.discoverer.connect('discovery-error', no_media_file_cb)
        self.discoverer._analyze()
        self.failUnlessEqual(bag['error'], 'Pipeline didn\'t want '
                'to go to PAUSED.')

    def testSetTimeout(self):
        """
        Check that a timeout is set when analyzing a file.
        """
        bag = {'error': None}

        def discovery_error_cb(disc, uri, error, error_detail):
            bag['error'] = error

        self.discoverer.connect('discovery-error', discovery_error_cb)
        self.discoverer.addUri('foo')
        self.failUnlessEqual(bag['error'], None)
        self.discoverer._analyze()
        # check that a timeout is scheduled once we start analyzing so we don't
        # hang on one single file
        self.failUnless(self.discoverer.timeout_scheduled)
        self.failIf(self.discoverer.working)
        self.failUnless(bag['error'])

        self.discoverer.timeout_expired = False
        self.discoverer.addUri('foo')
        self.discoverer._analyze()
        # at this point the timeout is scheduled but not expired, so the
        # discoverer should still be working
        self.failUnless(self.discoverer.timeout_scheduled)
        self.failIf(self.discoverer.timeout_cancelled)
        self.failUnless(self.discoverer.working)
        # a call go _finishAnalysis() cancels the timeout
        self.discoverer._finishAnalysis("foo")
        self.failUnless(self.discoverer.timeout_cancelled)
        self.failIf(self.discoverer.working)

    def testQueryDuration(self):
        def pad_query_fail(pad, query):
            return pad.query_default(query)

        def pad_query_succeed(pad, query):
            if query.type == gst.QUERY_DURATION:
                query.set_duration(gst.FORMAT_TIME, 10 * gst.SECOND)
                return True

            return pad.query_default(query)

        def pad_query_succeed2(pad, query):
            if query.type == gst.QUERY_DURATION:
                query.set_duration(gst.FORMAT_TIME, 20 * gst.SECOND)
                return True

            return pad.query_default(query)

        pad = gst.Pad('src', gst.PAD_SRC)
        self.failUnlessEqual(self.discoverer.current_duration,
                gst.CLOCK_TIME_NONE)

        pad.set_query_function(pad_query_fail)
        self.discoverer._maybeQueryDuration(pad)
        self.failUnlessEqual(self.discoverer.current_duration,
                gst.CLOCK_TIME_NONE)

        # retry on other pads
        pad.set_query_function(pad_query_succeed)
        self.discoverer._maybeQueryDuration(pad)
        self.failUnlessEqual(self.discoverer.current_duration,
                10 * gst.SECOND)

        # duration should be cached
        pad.set_query_function(pad_query_succeed2)
        self.discoverer._maybeQueryDuration(pad)
        self.failUnlessEqual(self.discoverer.current_duration,
                10 * gst.SECOND)

    def testGetThumbnailFilenameFromPad(self):
        pad = gst.Pad('src0', gst.PAD_SRC)
        pad1 = gst.Pad('src1', gst.PAD_SRC)
        self.discoverer.current_uri = "meh"
        filename1 = self.discoverer._getThumbnailFilenameFromPad(pad)
        filename2 = self.discoverer._getThumbnailFilenameFromPad(pad)
        self.discoverer.current_uri = "boo"
        filename3 = self.discoverer._getThumbnailFilenameFromPad(pad1)
        self.failUnlessEqual(filename1, filename2)
        self.failIfEqual(filename2, filename3)
        # TODO: check for non ascii filenames (which is half broken in python
        # on UNIX anyway...)

    def testBusEos(self):
        bag = {'called': False}

        def finish_analysis(reason):
            bag['called'] = True

        self.discoverer._finishAnalysis = finish_analysis
        self.discoverer._busMessageEosCb(None, None)
        self.failUnless(bag['called'], True)

    def testBusElement(self):
        bag = {'called': False}

        def finish_analysis(reason):
            bag['called'] = True

        self.discoverer._finishAnalysis = finish_analysis
        self.failUnlessEqual(self.discoverer.error, None)
        src = gst.Pad('src', gst.PAD_SRC)
        # we ignore non-redirect messages
        structure = gst.Structure('meh')
        message = gst.message_new_element(src, structure)
        self.discoverer._busMessageElementCb(None, message)
        self.failUnlessEqual(self.discoverer.error, None)
        self.failUnlessEqual(bag['called'], False)

        # error out on redirects
        structure = gst.Structure('redirect')
        message = gst.message_new_element(src, structure)
        self.discoverer._busMessageElementCb(None, message)
        self.failIfEqual(self.discoverer.error, None)
        self.failUnlessEqual(bag['called'], True)

    def testBusError(self):
        def discovery_error_cb(discoverer, uri, error, debug, dic):
            dic['uri'] = uri
            dic['error'] = error
            dic['debug'] = debug

        dic = {}
        self.discoverer.connect('discovery-error', discovery_error_cb, dic)

        src = gst.Pad('src', gst.PAD_SRC)
        gerror = gst.GError(gst.STREAM_ERROR, gst.STREAM_ERROR_FAILED, 'meh')
        message = gst.message_new_error(src, gerror, 'debug1')

        self.failUnlessEqual(self.discoverer.error, None)
        self.discoverer.addUri('popme')
        self.discoverer._busMessageErrorCb(None, message)
        self.failUnlessEqual(dic['debug'], 'debug1')

        # errors shouldn't be overridden
        gerror = gst.GError(gst.STREAM_ERROR, gst.STREAM_ERROR_FAILED, 'muh')
        message = gst.message_new_error(src, gerror, 'debug2')
        self.discoverer.addUri('popme')
        self.discoverer._busMessageErrorCb(None, message)
        self.failUnlessEqual(dic['debug'], 'debug2')

    def testNewDecodedPadFixed(self):
        video = gst.Pad('video_00', gst.PAD_SRC)
        video.set_caps(gst.Caps('video/x-raw-rgb'))
        audio = gst.Pad('audio_00', gst.PAD_SRC)
        audio.set_caps(gst.Caps('audio/x-raw-int'))

        self.failUnlessEqual(self.discoverer.current_streams, [])
        self.discoverer._newDecodedPadCb(None, video, False)
        self.failUnlessEqual(len(self.discoverer.current_streams), 1)
        self.failUnlessEqual(self.discoverer.new_video_pad_cb, 1)

        self.discoverer._newDecodedPadCb(None, audio, False)
        self.failUnlessEqual(len(self.discoverer.current_streams), 2)
        self.failUnlessEqual(self.discoverer.new_video_pad_cb, 1)

    def testNewDecodedPadNotFixed(self):
        video_template = gst.PadTemplate('video_00', gst.PAD_SRC,
                gst.PAD_ALWAYS, gst.Caps('video/x-raw-rgb, '
                        'framerate=[0/1, %d/1]' % ((2 ** 31) - 1)))
        audio_template = gst.PadTemplate('audio_00', gst.PAD_SRC,
                gst.PAD_ALWAYS, gst.Caps('audio/x-raw-int, '
                        'rate=[1, %d]' % ((2 ** 31) - 1)))

        video = gst.Pad(video_template)
        audio = gst.Pad(audio_template)
        video_ghost = gst.GhostPad("video", video)
        audio_ghost = gst.GhostPad("audio", audio)

        self.failUnlessEqual(self.discoverer.current_streams, [])
        self.discoverer._newDecodedPadCb(None, video_ghost, False)
        self.failUnlessEqual(len(self.discoverer.current_streams), 0)
        self.failUnlessEqual(self.discoverer.new_video_pad_cb, 1)

        self.discoverer._newDecodedPadCb(None, audio_ghost, False)
        self.failUnlessEqual(len(self.discoverer.current_streams), 0)
        self.failUnlessEqual(self.discoverer.new_video_pad_cb, 1)

        # fix the caps
        video.set_caps(gst.Caps('video/x-raw-rgb, framerate=25/1'))
        self.failUnlessEqual(len(self.discoverer.current_streams), 1)
        self.failUnlessEqual(self.discoverer.new_video_pad_cb, 1)

        audio.set_caps(gst.Caps('audio/x-raw-int, rate=44100'))
        self.failUnlessEqual(len(self.discoverer.current_streams), 2)
        self.failUnlessEqual(self.discoverer.new_video_pad_cb, 1)


class TestStateChange(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.discoverer = Discoverer1()
        self.discoverer.current_uri = "meh"
        # don't plug the thumbnailing branch
        self.discoverer.current_uri = 'file:///foo/bar'
        self.src = gst.Bin()
        self.discoverer.pipeline = self.src
        self.discoverer.current_duration = 10 * gst.SECOND
        self.factories = []
        self.error = None
        self.error_detail = None

        self.discoverer.connect('discovery-error', self.discoveryErrorCb)
        self.discoverer.connect('discovery-done',
                self.discoveryDoneCb)

    def tearDown(self):
        self.discoverer.disconnect_by_function(self.discoveryErrorCb)
        self.discoverer.disconnect_by_function(self.discoveryDoneCb)
        self.discoverer = None
        self.factories = None
        self.error = None
        self.src = None
        TestCase.tearDown(self)

    def discoveryErrorCb(self, disc, uri, error, debug):
        self.error = error
        self.error_detail = debug

    def discoveryDoneCb(self, disc, uri, factory):
        self.factories.append(factory)

    def testBusStateChangedIgnored(self):
        ignore_src = gst.Bin()

        # ignore element
        ignored = gst.message_new_state_changed(ignore_src,
               gst.STATE_READY, gst.STATE_PAUSED, gst.STATE_VOID_PENDING)
        self.discoverer._busMessageStateChangedCb(None, ignored)
        self.failUnlessEqual(self.factories, [])

        # ignore transition
        ignored = gst.message_new_state_changed(self.src,
                gst.STATE_NULL, gst.STATE_READY, gst.STATE_PAUSED)
        self.discoverer._busMessageStateChangedCb(None, ignored)
        self.failUnlessEqual(self.factories, [])

    def testBusStateChangedNoStreams(self):
        # no streams found
        message = gst.message_new_state_changed(self.src,
                gst.STATE_READY, gst.STATE_PAUSED, gst.STATE_VOID_PENDING)
        self.discoverer.addUri('illbepopped')
        self.failUnlessEqual(self.error, None)
        self.discoverer._busMessageStateChangedCb(None, message)
        self.failUnlessEqual(self.factories, [])
        # FIXME: be more strict about the error here
        self.failUnless(self.error)

    def testBusStateChangedVideoOnly(self):
        # only video
        pad = gst.Pad('src', gst.PAD_SRC)
        pad.set_caps(gst.Caps('video/x-raw-rgb'))
        self.discoverer._newDecodedPadCb(None, pad, False)

        self.failUnlessEqual(self.error, None)
        message = gst.message_new_state_changed(self.src,
                gst.STATE_READY, gst.STATE_PAUSED, gst.STATE_VOID_PENDING)
        self.discoverer.addUri('illbepopped')
        self.failUnlessEqual(self.error, None)
        self.discoverer._busMessageStateChangedCb(None, message)
        # should go to PLAYING to do thumbnails
        self.failUnlessEqual(self.src.get_state(0)[2], gst.STATE_PLAYING)
        self.discoverer._finishAnalysis("foo")
        self.failUnlessEqual(len(self.factories), 1)
        factory = self.factories[0]
        self.failUnless(isinstance(factory, FileSourceFactory))
        self.failUnlessEqual(len(factory.output_streams), 1)

    def testBusStateChangedAudioOnly(self):
        # only audio
        pad = gst.Pad('src', gst.PAD_SRC)
        pad.set_caps(gst.Caps('audio/x-raw-int'))
        self.discoverer._newDecodedPadCb(None, pad, False)

        self.failUnlessEqual(self.error, None)
        message = gst.message_new_state_changed(self.src,
                gst.STATE_READY, gst.STATE_PAUSED, gst.STATE_VOID_PENDING)
        self.discoverer.addUri('illbepopped')
        self.failUnlessEqual(self.error, None)
        self.discoverer._busMessageStateChangedCb(None, message)
        self.failUnlessEqual(len(self.factories), 1)
        factory = self.factories[0]
        self.failUnless(isinstance(factory, FileSourceFactory))
        self.failUnlessEqual(len(factory.output_streams), 1)

    def testBusStateChangedImageOnly(self):
        # only image
        pngdec = gst.element_factory_make('pngdec')
        self.discoverer.pipeline.add(pngdec)
        # images don't have duration
        self.discoverer.current_duration = gst.CLOCK_TIME_NONE
        pad = pngdec.get_pad('src')
        caps = gst.Caps(pad.get_caps()[0])
        caps[0]['width'] = 320
        caps[0]['height'] = 240
        caps[0]['framerate'] = gst.Fraction(0, 1)
        pad.set_caps(caps)
        self.discoverer._newDecodedPadCb(None, pad, False)

        self.failUnlessEqual(self.error, None)
        message = gst.message_new_state_changed(self.src,
                gst.STATE_READY, gst.STATE_PAUSED, gst.STATE_VOID_PENDING)
        self.discoverer.addUri('illbepopped')
        self.failUnlessEqual(self.error, None)
        self.discoverer._busMessageStateChangedCb(None, message)
        # should go to PLAYING to do thumbnails
        self.failUnlessEqual(self.src.get_state(0)[2], gst.STATE_PLAYING)
        self.discoverer._finishAnalysis("foo")
        self.failUnlessEqual(len(self.factories), 1)
        factory = self.factories[0]
        self.failUnless(isinstance(factory, PictureFileSourceFactory))
        self.failUnlessEqual(len(factory.output_streams), 1)

    def testDurationCheckImage(self):
        self.discoverer.current_duration = gst.CLOCK_TIME_NONE
        pngdec = gst.element_factory_make('pngdec')
        self.discoverer.pipeline.add(pngdec)
        pad = pngdec.get_pad('src')
        caps = gst.Caps(pad.get_caps()[0])
        caps[0]['width'] = 320
        caps[0]['height'] = 240
        caps[0]['framerate'] = gst.Fraction(0, 1)
        pad.set_caps(caps)
        self.discoverer._newDecodedPadCb(None, pad, False)
        self.discoverer.addUri('illbepopped')
        self.discoverer._finishAnalysis("foo")

        self.failUnlessEqual(self.error, None)
        self.failUnlessEqual(self.discoverer.current_duration,
                gst.CLOCK_TIME_NONE)

    def testDurationCheckNonImage(self):
        self.discoverer.current_duration = gst.CLOCK_TIME_NONE
        pad = gst.Pad('src', gst.PAD_SRC)
        pad.set_caps(gst.Caps('audio/x-raw-int'))
        self.discoverer._newDecodedPadCb(None, pad, False)
        self.discoverer.addUri('illbepopped')
        self.discoverer._finishAnalysis("foo")

        self.failUnlessEqual(self.error,
                "Could not establish the duration of the file.")
        self.failUnlessEqual(self.discoverer.current_duration,
                gst.CLOCK_TIME_NONE)
