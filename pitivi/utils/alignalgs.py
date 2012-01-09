# PiTiVi , Non-linear video editor
#
#       timeline/alignalgs.py
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
Algorithms for aligning (i.e. registering, synchronizing) time series
"""

try:
    import numpy
except ImportError:
    numpy = None


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
