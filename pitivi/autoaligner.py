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

# TODO reimplement after GES port
"""
Classes for automatic alignment of L{TimelineObject}s
"""

import gobject
import gst
import array
import time
import gtk
import os


try:
    import numpy
except ImportError:
    numpy = None

from gettext import gettext as _

import pitivi.configure as configure

from pitivi.utils.ui import beautify_ETA
from pitivi.utils.misc import call_false
from pitivi.utils.extract import Extractee
from pitivi.utils.loggable import Loggable


def nextpow2(x):
    a = 1
    while a < x:
        a *= 2
    return a


def submax(left, middle, right):
    """
    Find the maximum of a quadratic function from three samples.

    Given samples from a quadratic P(x) at x=-1, 0, and 1, find the x
    that extremizes P.  This is useful for determining the subsample
    position of the extremum given three samples around the observed
    extreme.

    @param left: value at x=-1
    @type left: L{float}
    @param middle: value at x=0
    @type middle: L{float}
    @param right: value at x=1
    @type right: L{float}
    @returns: value of x that extremizes the interpolating quadratic
    @rtype: L{float}

    """
    L = middle - left   # L and R are both positive if middle is the
    R = middle - right  # observed max of the integer samples
    return 0.5 * (R - L) / (R + L)
    # Derivation: Consider a quadratic q(x) := P(0) - P(x).  Then q(x) has
    # two roots, one at 0 and one at z, and the extreme is at (0+z)/2
    # (i.e. at z/2)
    # q(x) = bx*(x-z) # a may be positive or negative
    # q(1) = b*(1 - z) = R
    # q(-1) = b*(1 + z) = L
    # (1+z)/(1-z) = L/R  (from here it's just algebra to find a)
    # z + 1 = R/L - (R/L)*z
    # z*(1+R/L) = R/L - 1
    # z = (R/L - 1)/(R/L + 1) = (R-L)/(R+L)


def rigidalign(reference, targets):
    """
    Estimate the relative shift between reference and targets.

    The algorithm works by subtracting the mean, and then locating
    the maximum of the cross-correlation.  For inputs of length M{N},
    the running time is M{O(C{len(targets)}*N*log(N))}.

    @param reference: the waveform to regard as fixed
    @type reference: Sequence(Number)
    @param targets: the waveforms that should be aligned to reference
    @type targets: Sequence(Sequence(Number))
    @returns: The shift necessary to bring each target into alignment
        with the reference.  The returned shift may not be an integer,
        indicating that the best alignment would be achieved by a
        non-integer shift and appropriate interpolation.
    @rtype: Sequence(Number)

    """
    # L is the maximum size of a cross-correlation between the
    # reference and any of the targets.
    L = len(reference) + max(len(t) for t in targets) - 1
    # We round up L to the next power of 2 for speed in the FFT.
    L = nextpow2(L)
    reference = reference - numpy.mean(reference)
    fref = numpy.fft.rfft(reference, L).conj()
    shifts = []
    for t in targets:
        t = t - numpy.mean(t)
        # Compute cross-correlation
        xcorr = numpy.fft.irfft(fref * numpy.fft.rfft(t, L))
        # shift maximizes dotproduct(t[shift:],reference)
        # int() to convert numpy.int32 to python int
        shift = int(numpy.argmax(xcorr))
        subsample_shift = submax(xcorr[(shift - 1) % L],
                                 xcorr[shift],
                                 xcorr[(shift + 1) % L])
        shift = shift + subsample_shift
        # shift is now a float indicating the interpolated maximum
        if shift >= len(t):  # Negative shifts appear large and positive
            shift -= L       # This corrects them to be negative
        shifts.append(-shift)
        # Sign reversed to move the target instead of the reference
    return shifts


def _findslope(a):
    # Helper function for affinealign
    # The provided matrix a contains a bright line whose slope we want to know,
    # against a noisy background.
    # The line starts at 0,0.  If the slope is positive, it runs toward the
    # center of the matrix (i.e. toward (-1,-1))
    # If the slope is negative, it wraps from 0,0 to 0,-1 and continues toward
    # the center, (i.e. toward (-1,0)).
    # The line segment terminates at the midline along the X direction.
    # We locate the line by simply checking the sum along each possible line
    # up to the Y-max edge of a.  The caller sets the limit by choosing the
    # size of a.
    # The function returns a floating-point slope assuming that the matrix
    # has "square pixels".
    Y, X = a.shape
    X /= 2
    x_pos = numpy.arange(1, X)
    x_neg = numpy.arange(2 * X - 1, X, -1)
    best_end = 0
    max_sum = 0
    for end in xrange(Y):
        y = (x_pos * end) // X
        s = numpy.sum(a[y, x_pos])
        if s > max_sum:
            max_sum = s
            best_end = end
        s = numpy.sum(a[y, x_neg])
        if s > max_sum:
            max_sum = s
            best_end = -end
    return float(best_end) / X


def affinealign(reference, targets, max_drift=0.02):
    """ EXPERIMENTAL FUNCTION.

    Perform an affine registration between a reference and a number of
    targets.  Designed for aligning the amplitude envelopes of recordings of
    the same event by different devices.

    NOTE: This method is currently NOT USED by PiTiVi, as it has proven both
    unnecessary and unusable.  So far every test case has been registered
    successfully by rigidalign, and until PiTiVi supports time-stretching of
    audio, the drift calculation cannot actually be used.

    @param reference: the reference signal to which others will be registered
    @type reference: array(number)
    @param targets: the signals to register
    @type targets: ordered iterable(array(number))
    @param max_drift: the maximum absolute clock drift rate
                  (i.e. stretch factor) that will be considered during search
    @type max_drift: positive L{float}
    @return: (offsets, drifts).  offsets[i] is the point in reference at which
           targets[i] starts.  drifts[i] is the speed of targets[i] relative to
           the reference (positive is faster, meaning the target should be
           slowed down to be in sync with the reference)
    """
    L = len(reference) + max(len(t) for t in targets) - 1
    L2 = nextpow2(L)
    bsize = int(20. / max_drift)  # NEEDS TUNING
    num_blocks = nextpow2(1.0 * len(reference) // bsize)  # NEEDS TUNING
    bspace = (len(reference) - bsize) // num_blocks
    reference -= numpy.mean(reference)

    # Construct FFT'd reference blocks
    freference_blocks = numpy.zeros((L2 / 2 + 1, num_blocks),
                                    dtype=numpy.complex)
    for i in xrange(num_blocks):
        s = i * bspace
        tmp = numpy.zeros((L2,))
        tmp[s:s + bsize] = reference[s:s + bsize]
        freference_blocks[:, i] = numpy.fft.rfft(tmp, L2).conj()
    freference_blocks[:10, :] = 0  # High-pass to ignore slow volume variations

    offsets = []
    drifts = []
    for t in targets:
        t -= numpy.mean(t)
        ft = numpy.fft.rfft(t, L2)
        #fxcorr is the FFT'd cross-correlation with the reference blocks
        fxcorr_blocks = numpy.zeros((L2 / 2 + 1, num_blocks),
                                    dtype=numpy.complex)
        for i in xrange(num_blocks):
            fxcorr_blocks[:, i] = ft * freference_blocks[:, i]
            fxcorr_blocks[:, i] /= numpy.sqrt(numpy.sum(
                    fxcorr_blocks[:, i] ** 2))
        del ft
        # At this point xcorr_blocks would show a distinct bright line, nearly
        # orthogonal to time, indicating where each of these blocks found their
        # peak.  Each point on this line represents the time in t where block i
        # found its match.  The time-intercept gives the time in b at which the
        # reference starts, and the slope gives the amount by which the
        # reference is faster relative to b.

        # The challenge now is to find this line.  Our strategy is to reduce the
        # search to one dimension by first finding the slope.
        # The Fourier Transform of a smooth real line in 2D is an orthogonal
        # line through the origin, with phase that gives its position.
        # Unfortunately this line is not clearly visible in fxcorr_blocks, so
        # we discard the phase (by taking the absolute value) and then inverse
        # transform.  This places the line at the origin, so we can find its
        # slope.

        # Construct the half-autocorrelation matrix
        # (A true autocorrelation matrix would be ifft(abs(fft(x))**2), but this
        # is just ifft(abs(fft(x))).)
        # Construction is stepwise partly in an attempt to save memory
        # The width is 2*num_blocks in order to avoid overlapping positive and
        # negative correlations
        halfautocorr = numpy.fft.fft(fxcorr_blocks, 2 * num_blocks, 1)
        halfautocorr = numpy.abs(halfautocorr)
        halfautocorr = numpy.fft.ifft(halfautocorr, None, 1)
        halfautocorr = numpy.fft.irfft(halfautocorr, None, 0)
        # Now it's actually the half-autocorrelation.
        # Chop out the bit we don't care about
        halfautocorr = halfautocorr[:bspace * num_blocks * max_drift, :]
        # Remove the local-correlation peak.
        halfautocorr[-1:2, -1:2] = 0  # NEEDS TUNING
        # Normalize each column (appears to be necessary)
        for i in xrange(2 * num_blocks):
            halfautocorr[:, i] /= numpy.sqrt(numpy.sum(
                    halfautocorr[:, i] ** 2))
        #from matplotlib.pyplot import imshow,show
        #imshow(halfautocorr,interpolation='nearest',aspect='auto');show()
        drift = _findslope(halfautocorr) / bspace
        del halfautocorr

        #inverse transform and shift everything into alignment
        xcorr_blocks = numpy.fft.irfft(fxcorr_blocks, None, 0)
        del fxcorr_blocks
        #TODO: see if phase ramps are worthwhile here
        for i in xrange(num_blocks):
            blockcenter = i * bspace + bsize / 2
            shift = int(blockcenter * drift)
            if shift > 0:
                temp = xcorr_blocks[:shift, i].copy()
                xcorr_blocks[:-shift, i] = xcorr_blocks[shift:, i].copy()
                xcorr_blocks[-shift:, i] = temp
            elif shift < 0:
                temp = xcorr_blocks[shift:, i].copy()
                xcorr_blocks[-shift:, i] = xcorr_blocks[:shift, i].copy()
                xcorr_blocks[:-shift, i] = temp

        #from matplotlib.pyplot import imshow,show
        #imshow(xcorr_blocks,interpolation='nearest',aspect='auto');show()

        # xcorr is the drift-compensated cross-correlation
        xcorr = numpy.sum(xcorr_blocks, axis=1)
        del xcorr_blocks

        offset = numpy.argmax(xcorr)
        #from matplotlib.pyplot import plot,show
        #plot(xcorr);show()
        del xcorr
        if offset >= len(t):
            offset -= L2

        # now offset is the point in target at which reference starts and
        # drift is the speed with which the reference drifts relative to the
        # target.  We reverse these relationships for the caller.
        slope = 1 + drift
        offsets.append(-offset / slope)
        drifts.append(1 / slope - 1)
    return offsets, drifts


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


class AlignmentProgressDialog:
    """ Dialog indicating the progress of the auto-alignment process.
        Code derived from L{EncodingProgressDialog}, but greatly simplified
        (read-only, no buttons)."""

    def __init__(self, app):
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(configure.get_ui_dir(),
                                   "alignmentprogress.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("align-progress")
        self.progressbar = self.builder.get_object("progressbar")
        # Parent this dialog with mainwindow
        # set_transient_for allows this dialog to properly
        # minimize together with the mainwindow.  This method is
        # taken from EncodingProgressDialog.  In both cases, it appears
        # to work correctly, although there is a known bug for Gnome 3 in
        # EncodingProgressDialog (bug #652917)
        self.window.set_transient_for(app.gui)

        # UI widgets
        # We currently reuse the render icon for this dialog.
        icon_path = os.path.join(configure.get_pixmap_dir(),
                                 "pitivi-render-16.png")
        self.window.set_icon_from_file(icon_path)

        # FIXME: Add a cancel button

    def updatePosition(self, fraction, estimated):
        self.progressbar.set_fraction(fraction)
        self.window.set_title(_("%d%% Analyzed") % int(100 * fraction))
        if estimated:
            # Translators: This string indicates the estimated time
            # remaining until the action completes.  The "%s" is an
            # already-localized human-readable duration description like
            # "31 seconds".
            self.progressbar.set_text(_("About %s left") % estimated)


if __name__ == '__main__':
    # Simple command-line test
    from sys import argv
    names = argv[1:]
    envelopes = [numpy.fromfile(n) for n in names]
    reference = envelopes[-1]
    offsets, drifts = affinealign(reference, envelopes, 0.02)
    print offsets, drifts
    from matplotlib.pyplot import *
    clf()
    for i in xrange(len(envelopes)):
        t = offsets[i] + (1 + drifts[i]) * numpy.arange(len(envelopes[i]))
        plot(t, envelopes[i] / numpy.sqrt(numpy.sum(envelopes[i] ** 2)))
    show()
