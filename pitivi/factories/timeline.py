# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/timeline.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

import gst
from pitivi.factories.base import SourceFactory

class TimelineSourceFactory(SourceFactory):
    def __init__(self, timeline):
        SourceFactory.__init__(self, 'timeline', 'timeline')
        self.bin = gst.Bin()
        self.max_bins = 1
        self.timeline = timeline
        self.pad_num = 0
        self.ghosts = {}

        self.duration = timeline.duration

        for track in self.timeline.tracks:
            self._addTrack(track)

        self._connectTimeline()

    def _makeBin(self, output_stream=None):
        if output_stream is not None:
            raise ObjectFactoryError('not implemented yet')

        return self.bin

    def _connectTimeline(self):
        self.timeline.connect('track-added', self._timelineTrackAddedCb)
        self.timeline.connect('track-removed', self._timelineTrackRemovedCb)
        self.timeline.connect('duration-changed',
                self._timelineDurationChangedCb)

    def _disconnectTimeline(self):
        self.timeline.disconnect_by_function(self._timelineTrackAddedCb)
        self.timeline.disconnect_by_function(self._timelineTrackRemovedCb)
        self.timeline.disconnect_by_function(self._timelineDurationChangedCb)

    def _addTrack(self, track):
        composition = track.composition
        composition.connect('pad-added',
                self._trackCompositionPadAddedCb, track)
        composition.connect('pad-removed',
                self._trackCompositionPadRemovedCb, track)
        
        self.bin.add(composition)

        self.addOutputStream(track.stream)

    def _removeTrack(self, track):
        composition = track.composition
        composition.disconnect_by_func(self._trackCompositionPadAddedCb)
        composition.disconnect_by_func(self._trackCompositionPadRemovedCb)
        
        self.bin.remove(composition)

        self.removeOutputStream(track.stream)

    def _newGhostPad(self, pad):
        pad_id = str(pad)
        ghost = gst.GhostPad('src%d' % self.pad_num, pad)
        ghost.set_active(True)
        self.ghosts[pad_id] = ghost
        self.pad_num += 1

        return ghost

    def _removeGhostPad(self, pad):
        pad_id = str(pad)
        ghost = self.ghosts.pop(pad_id)
        self.bin.remove_pad(ghost)
        ghost.set_active(False)

    def _timelineTrackAddedCb(self, timeline, track):
        self._addTrack(track)
    
    def _timelineTrackRemovedCb(self, timeline, track):
        self._removeTrack(track)

    def _trackCompositionPadAddedCb(self, composition, pad, track):
        ghost = self._newGhostPad(pad)
        self.bin.add_pad(ghost)
    
    def _trackCompositionPadRemovedCb(self, composition, pad, track):
        self._removeGhostPad(pad)

    def _timelineDurationChangedCb(self, timeline, duration):
        self.duration = duration
