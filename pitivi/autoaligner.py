# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2011, Benjamin M. Schwartz <bens@alum.mit.edu>
# Copyright (c) 2022, Thejas Kiran P S <thejaskiranps@gmail.com>
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
import os.path
from typing import List

import numpy.typing
from gi.repository import GES
from scipy.signal import correlate
from scipy.signal import correlation_lags

from pitivi.timeline.previewers import get_wavefile_location_for_uri
from pitivi.timeline.previewers import SAMPLE_DURATION
from pitivi.utils.loggable import Loggable


class AutoAligner(Loggable):
    """Logic for aligning clips based on their audio."""

    def __init__(self, selection):
        Loggable.__init__(self)
        # Remove transition clips if any.
        clips = [clip for clip in selection if isinstance(clip, GES.UriClip)]
        # Sorting the clip in descending order according to their length
        self._clips: List[GES.Clip] = sorted(clips,
                                             key=lambda clip: clip.props.duration,
                                             reverse=True)

    def _get_peaks(self,
                   clips: List[GES.Clip]
                   ) -> List[numpy.typing.NDArray[numpy.float64]]:
        """Returns peak values of each clip from its wave cache."""
        peaks = []
        for clip in clips:
            wavefile = get_wavefile_location_for_uri(clip.get_uri())
            clip_peaks = numpy.load(wavefile)

            # Slice out samples of trimmed part.
            start = clip.inpoint // SAMPLE_DURATION
            end = (clip.inpoint + clip.duration) // SAMPLE_DURATION
            peaks.append(clip_peaks[start:end])
        return peaks

    @staticmethod
    def can_align(clips: List[GES.Clip]) -> bool:
        """Checks if auto alignment of the clips is possible."""
        if len(clips) < 2:
            return False

        # Check all clips have an audio track.
        if not (all(c.get_track_types() & GES.TrackType.AUDIO
                for c in clips)):
            return False

        # Check every clip is from a different layer.
        layers = [clip.get_layer() for clip in clips]
        if len(set(layers)) < len(layers):
            return False

        # Check if peaks data have been generated by the previewer.
        for clip in clips:
            peaks_file_uri = get_wavefile_location_for_uri(clip.get_uri())
            if not os.path.isfile(peaks_file_uri):
                return False

        return True

    def _xalign(self,
                peaks1: numpy.typing.NDArray[numpy.float64],
                peaks2: numpy.typing.NDArray[numpy.float64]
                ) -> numpy.int64:
        """Calculates lag in peak-arrays of a pair of clips using cross correlation."""
        corr = correlate(peaks1, peaks2)
        lags = correlation_lags(peaks1.size, peaks2.size)
        lag = lags[numpy.argmax(corr)]
        return lag

    def _calculate_shifts(self,
                          peaks: List[numpy.typing.NDArray[numpy.float64]]
                          ) -> List[numpy.int64]:
        """Calculates the shift required by target clips wrt to reference clip.

        Args:
            peaks: List of peak values of each clip.
        """
        # Select peaks of largest clip as reference.
        reference = peaks[0]
        reference -= reference.mean()

        shifts = []
        # Adding 0 shift for the reference clip.
        shifts.append(numpy.int64(0))
        for clip_peaks in peaks[1:]:
            clip_peaks -= clip_peaks.mean()
            shift = self._xalign(reference, clip_peaks)
            # Converting shift to time to be shifted in ns.
            shift *= SAMPLE_DURATION
            shifts.append(shift)

        return shifts

    def run(self) -> None:
        if not self.can_align(self._clips):
            return

        peaks = self._get_peaks(self._clips)

        shifts = self._calculate_shifts(peaks)
        self._perform_shifts(shifts)

    def _perform_shifts(self, shifts: List[numpy.int64]) -> None:
        reference = self._clips[0]
        starts = [reference.props.start + shift for shift in shifts]

        min_start = min(starts)
        if min_start < 0:
            # Adjust the starts to avoid placing clips at a negative position.
            starts = [start - min_start for start in starts]

        for clip, start in zip(self._clips, starts):
            clip.props.start = start
