# PiTiVi , Non-linear video editor
#
#       timeline/align.py
#
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Classes for automatic alignment of L{TimelineObject}s
"""

import array
import time
try:
    import numpy
except ImportError:
    numpy = None

import gobject
import gst
from pitivi.utils.misc import beautify_ETA, call_false
from pitivi.log.loggable import Loggable
from pitivi.utils.alignalgs import rigidalign


def getAudioTrack(timeline_object):
    """Helper function for getting an audio track from a TimelineObject

    @param timeline_object: The TimelineObject from which to locate an
        audio track
    @type timeline_object: L{TimelineObject}
    @returns: An audio track from timeline_object, or None if
        timeline_object has no audio track
    @rtype: audio L{TrackObject} or L{NoneType}

    """
    for track in timeline_object.track_objects:
        if track.stream_type == AudioStream:
            return track
    return None


class ProgressMeter:

    """Abstract interface representing a progress meter."""

    def addWatcher(self, function):
        """ Add a progress watching callback function.  This callback will
        always be called from the main thread.

        @param function: a function to call with progress updates.
        @type function: callable(fractional_progress, time_remaining_text).
            fractional_progress is a float normalized to [0,1].
            time_remaining_text is a localized text string indicating the
            estimated time remaining.
        """
        raise NotImplementedError


class ProgressAggregator(ProgressMeter):

    """A ProgressMeter that aggregates progress reports.

    Reports from multiple sources are combined into a unified progress
    report.

    """

    def __init__(self):
        # _targets is a list giving the size of each task.
        self._targets = []
        # _portions is a list of the same length as _targets, indicating
        # the portion of each task that as been completed (initially 0).
        self._portions = []
        self._start = time.time()
        self._watchers = []

    def getPortionCB(self, target):
        """Prepare a new input for the Aggregator.

        Given a target size
        (in arbitrary units, but should be consistent across all calls on
        a single ProgressAggregator object), it returns a callback that
        can be used to update progress on this portion of the task.

        @param target: the total task size for this portion
        @type target: number
        @returns: a callback that can be used to inform the Aggregator of
            subsequent updates to this portion
        @rtype: function(x), where x should be a number indicating the
            absolute amount of this subtask that has been completed.

        """
        i = len(self._targets)
        self._targets.append(target)
        self._portions.append(0)

        def cb(thusfar):
            self._portions[i] = thusfar
            gobject.idle_add(self._callForward)
        return cb

    def addWatcher(self, function):
        self._watchers.append(function)

    def _callForward(self):
        # This function always returns False so that it may be safely
        # invoked via gobject.idle_add(). Use of idle_add() is necessary
        # to ensure that watchers are always called from the main thread,
        # even if progress updates are received from other threads.
        total_target = sum(self._targets)
        total_completed = sum(self._portions)
        if total_target == 0:
            return False
        frac = min(1.0, float(total_completed) / total_target)
        now = time.time()
        remaining = (now - self._start) * (1 - frac) / frac
        for function in self._watchers:
            function(frac, beautify_ETA(int(remaining * gst.SECOND)))
        return False


class EnvelopeExtractee(Extractee, Loggable):

    """Class that computes the envelope of a 1-D signal (audio).

    The envelope is defined as the sum of the absolute value of the signal
    over each block.  This class computes the envelope incrementally,
    so that the entire signal does not ever need to be stored.

    """

    def __init__(self, blocksize, callback, *cbargs):
        """
        @param blocksize: the number of samples in a block
        @type blocksize: L{int}
        @param callback: a function to call when the extraction is complete.
            The function's first argument will be a numpy array
            representing the envelope, and any later argument to this
            function will be passed as subsequent arguments to callback.

        """
        Loggable.__init__(self)
        self._blocksize = blocksize
        self._cb = callback
        self._cbargs = cbargs
        self._blocks = numpy.zeros((0,), dtype=numpy.float32)
        self._empty = array.array('f', [])
        # self._samples buffers up to self._threshold samples, before
        # their envelope is computed and store in self._blocks, in order
        # to amortize some of the function call overheads.
        self._samples = array.array('f', [])
        self._threshold = 2000 * blocksize
        self._progress_watchers = []

    def receive(self, a):
        self._samples.extend(a)
        if len(self._samples) < self._threshold:
            return
        else:
            self._process_samples()

    def addWatcher(self, w):
        """
        Add a function to call with progress updates.

        @param w: callback function
        @type w: function(# of samples received so far)

        """
        self._progress_watchers.append(w)

    def _process_samples(self):
        excess = len(self._samples) % self._blocksize
        if excess != 0:
            samples_to_process = self._samples[:-excess]
            self._samples = self._samples[-excess:]
        else:
            samples_to_process = self._samples
            self._samples = array.array('f', [])
        self.debug("Adding %s samples to %s blocks",
                   len(samples_to_process), len(self._blocks))
        newblocks = len(samples_to_process) // self._blocksize
        samples_abs = numpy.abs(
                samples_to_process).reshape((newblocks, self._blocksize))
        self._blocks.resize((len(self._blocks) + newblocks,))
        # This numpy.sum() call relies on samples_abs being a
        # floating-point type. If samples_abs.dtype is int16
        # then the sum may overflow.
        self._blocks[-newblocks:] = numpy.sum(samples_abs, 1)
        for w in self._progress_watchers:
            w(self._blocksize * len(self._blocks) + excess)

    def finalize(self):
        self._process_samples()  # absorb any remaining buffered samples
        self._cb(self._blocks, *self._cbargs)


class AutoAligner(Loggable):

    """
    Class for aligning a set of L{TimelineObject}s automatically.

    The alignment is based on their contents, so that the shifted tracks
    are synchronized.  The current implementation only analyzes audio
    data, so timeline objects without an audio track cannot be aligned.

    """

    BLOCKRATE = 25
    """
    @ivar BLOCKRATE: The number of amplitude blocks per second.

    The AutoAligner works by computing the "amplitude envelope" of each
    audio stream.  We define an amplitude envelope as the absolute value
    of the audio samples, downsampled to a low samplerate.  This
    samplerate, in Hz, is given by BLOCKRATE.  (It is given this name
    because the downsampling filter is implemented by very simple
    averaging over blocks, i.e. a box filter.)  25 Hz appears to be a
    good choice because it evenly divides all common audio samplerates
    (e.g. 11025 and 8000). Lower blockrate requires less CPU time but
    produces less accurate alignment.  Higher blockrate is the reverse
    (and also cannot evenly divide all samplerates).

    """

    def __init__(self, timeline_objects, callback):
        """
        @param timeline_objects: an iterable of L{TimelineObject}s.
            In this implementation, only L{TimelineObject}s with at least one
            audio track will be aligned.
        @type timeline_objects: iter(L{TimelineObject})
        @param callback: A function to call when alignment is complete.  No
            arguments will be provided.
        @type callback: function

        """
        Loggable.__init__(self)
        # self._timeline_objects maps each object to its envelope.  The values
        # are initially None prior to envelope extraction.
        self._timeline_objects = dict.fromkeys(timeline_objects)
        self._callback = callback
        # stack of (Track, Extractee) pairs waiting to be processed
        # When start() is called, the stack will be populated, and then
        # processed sequentially.  Only one item from the stack will be
        # actively in process at a time.
        self._extraction_stack = []

    @staticmethod
    def canAlign(timeline_objects):
        """
        Can an AutoAligner align these objects?

        Determine whether a group of timeline objects can all
        be aligned together by an AutoAligner.

        @param timeline_objects: a group of timeline objects
        @type timeline_objects: iterable(L{TimelineObject})
        @returns: True iff the objects can aligned.
        @rtype: L{bool}

        """
        # numpy is a "soft dependency".  If you're running without numpy,
        # this False return value is your only warning not to
        # use the AutoAligner, which will crash immediately.
        return all(getAudioTrack(t) is not None for t in timeline_objects)

    def _extractNextEnvelope(self):
        audiotrack, extractee = self._extraction_stack.pop()
        r = RandomAccessAudioExtractor(audiotrack.factory,
                                       audiotrack.stream)
        r.extract(extractee, audiotrack.in_point,
                  audiotrack.out_point - audiotrack.in_point)
        return False

    def _envelopeCb(self, array, timeline_object):
        self.debug("Receiving envelope for %s", timeline_object)
        self._timeline_objects[timeline_object] = array
        if self._extraction_stack:
            self._extractNextEnvelope()
        else:  # This was the last envelope
            self._performShifts()
            self._callback()

    def start(self):
        """
        Initiate the auto-alignment process.

        @returns: a L{ProgressMeter} indicating the progress of the
            alignment
        @rtype: L{ProgressMeter}

        """
        progress_aggregator = ProgressAggregator()
        pairs = []  # (TimelineObject, {audio}TrackObject) pairs
        for timeline_object in self._timeline_objects.keys():
            audiotrack = getAudioTrack(timeline_object)
            if audiotrack is not None:
                pairs.append((timeline_object, audiotrack))
            else:  # forget any TimelineObject without an audio track
                self._timeline_objects.pop(timeline_object)
        if len(pairs) >= 2:
            for timeline_object, audiotrack in pairs:
                # blocksize is the number of samples per block
                blocksize = audiotrack.stream.rate // self.BLOCKRATE
                extractee = EnvelopeExtractee(blocksize, self._envelopeCb,
                                              timeline_object)
                # numsamples is the total number of samples in the track,
                # which is used by progress_aggregator to determine
                # the percent completion.
                numsamples = ((audiotrack.duration / gst.SECOND) *
                              audiotrack.stream.rate)
                extractee.addWatcher(
                        progress_aggregator.getPortionCB(numsamples))
                self._extraction_stack.append((audiotrack, extractee))
            # After we return, start the extraction cycle.
            # This gobject.idle_add call should not be necessary;
            # we should be able to invoke _extractNextEnvelope directly
            # here.  However, there is some as-yet-unexplained
            # race condition between the Python GIL, GTK UI updates,
            # GLib mainloop, and pygst multithreading, resulting in
            # occasional deadlocks during autoalignment.
            # This call to idle_add() reportedly eliminates the deadlock.
            # No one knows why.
            gobject.idle_add(self._extractNextEnvelope)
        else:  # We can't do anything without at least two audio tracks
            # After we return, call the callback function (once)
            gobject.idle_add(call_false, self._callback)
        return progress_aggregator

    def _chooseReference(self):
        """
        Chooses the timeline object to use as a reference.

        This function currently selects the one with lowest priority,
        i.e. appears highest in the GUI.  The behavior of this function
        affects user interaction, because the user may want to
        determine which object moves and which stays put.

        @returns: the timeline object with lowest priority.
        @rtype: L{TimelineObject}

        """
        def priority(timeline_object):
            return timeline_object.priority
        return min(self._timeline_objects.iterkeys(), key=priority)

    def _performShifts(self):
        self.debug("performing shifts")
        reference = self._chooseReference()
        # By using pop(), this line also removes the reference
        # TimelineObject and its envelope from further consideration,
        # saving some CPU time in rigidalign.
        reference_envelope = self._timeline_objects.pop(reference)
        # We call list() because we need a reliable ordering of the pairs
        # (In python 3, dict.items() returns an unordered dictview)
        pairs = list(self._timeline_objects.items())
        envelopes = [p[1] for p in pairs]
        offsets = rigidalign(reference_envelope, envelopes)
        for (movable, envelope), offset in zip(pairs, offsets):
            # tshift is the offset rescaled to units of nanoseconds
            tshift = int((offset * gst.SECOND) / self.BLOCKRATE)
            self.debug("Shifting %s to %i ns from %i",
                       movable, tshift, reference.start)
            newstart = reference.start + tshift
            if newstart >= 0:
                movable.start = newstart
            else:
                # Timeline objects always must have a positive start point, so
                # if alignment would move an object to start at negative time,
                # we instead make it start at zero and chop off the required
                # amount at the beginning.
                movable.start = 0
                movable.in_point = movable.in_point - newstart
                movable.duration += newstart
