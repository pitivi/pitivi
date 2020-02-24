# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2011, Benjamin M. Schwartz <bens@alum.mit.edu>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""
Classes for extracting decoded contents of streams into Python

Code derived from ui/previewer.py.
"""
# FIXME reimplement after GES port
from collections import deque

from gi.repository import Gst

from pitivi.utils.loggable import Loggable
# from pitivi.elements.singledecodebin import SingleDecodeBin
# from pitivi.elements.extractionsink import ExtractionSink


def linkDynamic(element, target):

    def pad_added(unused_bin, pad, target):
        compatpad = target.get_compatible_pad(pad)
        if compatpad:
            pad.link_full(compatpad, Gst.PAD_LINK_CHECK_NOTHING)
    element.connect("pad-added", pad_added, target)


def pipeline(graph):
    E = iter(graph.items())
    V = iter(graph.keys())
    p = Gst.Pipeline()
    p.add(*V)
    for u, v in E:
        if v:
            try:
                u.link(v)
            except Gst.LinkError:
                linkDynamic(u, v)
    return p


class Extractee:

    """Abstract base class for receiving raw data from an L{Extractor}."""

    def receive(self, array):
        """
        Receive a chunk of data from an Extractor.

        @param array: The chunk of data as an array
        @type array: any kind of numeric array

        """
        raise NotImplementedError

    def finalize(self):
        """
        Inform the Extractee that receive() will not be called again.

        Indicates that the extraction is complete, so the Extractee should
            process the data it has received.

        """
        raise NotImplementedError


class Extractor(Loggable):

    """
    Abstract base class for extraction of raw data from a stream.

    Closely modeled on L{Previewer}.

    """

    def __init__(self, factory, stream_):
        """
        Create a new Extractor.

        @param factory: the factory with which to decode the stream
        @type factory: L{ObjectFactory}
        @param stream_: the stream to decode
        @type stream_: L{Stream}
        """
        Loggable.__init__(self)
        self.debug("Initialized with %s %s", factory, stream_)

    def extract(self, extractee, start, duration):
        """
        Extract the raw data corresponding to a segment of the stream.

        @param extractee: the L{Extractee} that will receive the raw data
        @type extractee: L{Extractee}
        @param start: The point in the stream at which the segment starts
            (nanoseconds)
        @type start: L{long}
        @param duration: The duration of the segment (nanoseconds)
        @type duration: L{long}

        """
        raise NotImplementedError


class RandomAccessExtractor(Extractor):

    """
    Abstract class for L{Extractor}s of random access streams.

    Closely inspired by L{RandomAccessPreviewer}.

    """

    def __init__(self, factory, stream_):
        Extractor.__init__(self, factory, stream_)
        # FIXME:
        # why doesn't this work?
        # bin = factory.makeBin(stream_)
        uri = factory.uri
        caps = stream_.caps
        bin = SingleDecodeBin(uri=uri, caps=caps, stream=stream_)

        self._pipelineInit(factory, bin)

    def _pipelineInit(self, factory, bin):
        """
        Create the pipeline for the preview process.

        Subclasses should
        override this method and create a pipeline, connecting to
        callbacks to the appropriate signals, and prerolling the
        pipeline if necessary.

        """
        raise NotImplementedError


class RandomAccessAudioExtractor(RandomAccessExtractor):

    """
    L{Extractor} for random access audio streams.

    Closely inspired by L{RandomAccessAudioPreviewer}.

    """

    def __init__(self, factory, stream_):
        self._queue = deque()
        RandomAccessExtractor.__init__(self, factory, stream_)
        self._ready = False

    def _pipelineInit(self, factory, sbin):
        self.audioSink = ExtractionSink()
        self.audioSink.set_stopped_cb(self._finishSegment)
        # This audiorate element ensures that the extracted raw-data
        # timeline matches the timestamps used for seeking, even if the
        # audio source has gaps or other timestamp abnormalities.
        audiorate = Gst.ElementFactory.make("audiorate")
        conv = Gst.ElementFactory.make("audioconvert")
        q = Gst.ElementFactory.make("queue")
        self.audioPipeline = pipeline({
            sbin: audiorate,
            audiorate: conv,
            conv: q,
            q: self.audioSink,
            self.audioSink: None})
        bus = self.audioPipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self._busMessageErrorCb)
        self._donecb_id = bus.connect("message::async-done",
                                      self._busMessageAsyncDoneCb)

        self.audioPipeline.set_state(Gst.State.PAUSED)
        # The audiopipeline.set_state() method does not take effect
        # immediately, but the extraction process (and in particular
        # self._startSegment) will not work properly until
        # self.audioPipeline reaches the desired state (State.PAUSED).
        # To ensure that this is the case, we wait until the ASYNC_DONE
        # message is received before setting self._ready = True,
        # which enables extraction to proceed.

    def _busMessageErrorCb(self, unused_bus, message):
        error, debug = message.parse_error()
        self.error("Event bus error: %s; %s", error, debug)

        return Gst.BusSyncReply.PASS

    def _busMessageAsyncDoneCb(self, bus, unused_message):
        self.debug("Pipeline is ready for seeking")
        bus.disconnect(self._donecb_id)  # Don't call me again
        self._ready = True
        if self._queue:  # Someone called .extract() before we were ready
            self._run()

    def _startSegment(self, timestamp, duration):
        self.debug("processing segment with timestamp=%i and duration=%i",
                   timestamp, duration)
        res = self.audioPipeline.seek(1.0,
                                      Gst.Format.TIME,
                                      Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                                      Gst.SeekType.SET, timestamp,
                                      Gst.SeekType.SET, timestamp + duration)
        if not res:
            self.warning("seek failed %s", timestamp)
        self.audioPipeline.set_state(Gst.State.PLAYING)

        return res

    def _finishSegment(self):
        self.audioSink.extractee.finalize()
        self.audioSink.reset()
        self._queue.popleft()
        # If there's more to do, keep running
        if self._queue:
            self._run()

    def extract(self, extractee, start, duration):
        stopped = not self._queue
        self._queue.append((extractee, start, duration))
        if stopped and self._ready:
            self._run()
        # if self._ready is False, self._run() will be called from
        # self._busMessageDoneCb().

    def _run(self):
        # Control flows in a cycle:
        # _run -> _startSegment -> busMessageSegmentDoneCb -> _finishSegment -> _run
        # This forms a loop that extracts an entire segment (i.e. satisfies an
        # extract request) in each cycle. The cycle
        # runs until the queue of Extractees empties.  If the cycle is not
        # running, extract() will kick it off again.
        extractee, start, duration = self._queue[0]
        self.audioSink.set_extractee(extractee)
        self._startSegment(start, duration)
