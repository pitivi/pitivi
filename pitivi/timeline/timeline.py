# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/timeline.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
import weakref

from pitivi.signalinterface import Signallable
from pitivi.utils import UNKNOWN_DURATION
from pitivi.timeline.track import Track, SourceTrackObject

class TimelineError(Exception):
    pass

class TimelineObject(object, Signallable):
    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'in-point-changed': ['in-point'],
        'out-point-changed': ['out-point']
    }

    DEFAULT_START = 0
    DEFAULT_DURATION = UNKNOWN_DURATION
    DEFAULT_IN_POINT = 0
    DEFAULT_OUT_POINT = UNKNOWN_DURATION

    def __init__(self, factory):
        self.factory = factory
        self.track_objects = []
    
    def _getStart(self):
        if not self.track_objects:
            return self.DEFAULT_START

        return self.track_objects[0].start

    def setStart(self, time, snap=False):
        if not self.track_objects:
            raise TimelineError()
        
        if snap:
            # FIXME: implement me
            pass

        for track_object in self.track_objects:
            track_object.setObjectStart(time)
        
        self.emit('start-changed', time)

    start = property(_getStart, setStart)

    def _getDuration(self):
        if not self.track_objects:
            return self.DEFAULT_DURATION
        
        return self.track_objects[0].duration
    
    def setDuration(self, time, snap=False):
        if not self.track_objects:
            raise TimelineError()
        
        if snap:
            # FIXME: implement me
            pass
        
        for track_object in self.track_objects:
            track_object.setObjectDuration(time)

        self.emit('duration-changed', time)
    
    duration = property(_getDuration, setDuration)

    def _getInPoint(self):
        if not self.track_objects:
            return self.DEFAULT_IN_POINT
        
        return self.track_objects[0].in_point
    
    def setInPoint(self, time, snap=False):
        if not self.track_objects:
            raise TimelineError()
        
        for track_object in self.track_objects:
            track_object.setObjectInPoint(time)
        
        self.emit('in-point-changed', time)

    in_point = property(_getInPoint, setInPoint)

    def _getOutPoint(self):
        if not self.track_objects:
            return self.DEFAULT_OUT_POINT
        
        return self.track_objects[0].out_point
    
    def setOutPoint(self, time, snap=False):
        if not self.track_objects:
            raise TimelineError()
        
        for track_object in self.track_objects:
            track_object.setObjectOutPoint(time)
        
        self.emit('out-point-changed', time)

    out_point = property(_getOutPoint, setOutPoint)

    def addTrackObject(self, obj):
        if obj.timeline_object is not None:
            raise TimelineError()

        if obj in self.track_objects:
            raise TimelineError()

        if self.track_objects:
            # multiple track objects are used for groups.
            # For example if you have the timeline:
            #
            # |sourceA|gap|sourceB|
            # | sourceC |gap
            #
            # If you group A B and C the group will create two gnl compositions,
            # one [A, B] with start A.start and duration B.duration and another
            # [C] with start C.start and duration B.duration (with silence used
            # as padding).
            # The compositions will always be aligned with the same start and
            # duration.
            existing_track_object = self.track_objects[0]
            if obj.start != existing_track_object.start or \
                    obj.duration != existing_track_object.duration:
                raise TimelineError()

        obj.timeline_object = weakref.proxy(self)
        self.track_objects.append(obj)

    def removeTrackObject(self, obj):
        if obj.track is None:
            raise TimelineError()

        try:
            self.track_objects.remove(obj)
            obj.timeline_object = None
        except ValueError:
            raise TimelineError()

class Selection(object):
    def __init__(self):
        self.timeline_objects = set([])

    def addTimelineObject(self, timeline_object):
        if timeline_object in self.timeline_objects:
            raise TimelineError()

        self.timeline_objects.add(timeline_object)

    def removeTimelineObject(self, timeline_object):
        try:
            self.timeline_objects.remove(timeline_object)
        except KeyError:
            raise TimelineError()

class LinkEntry(object):
    def __init__(self, start, duration,
            start_changed_sig_id, duration_changed_sig_id):
        self.start = start
        self.duration = duration
        self.start_changed_sig_id = start_changed_sig_id
        self.duration_changed_sig_id = duration_changed_sig_id

class Link(Selection):
    def __init__(self):
        Selection.__init__(self)
        self.link_entries = {}
        self.waiting_update = []

    def addTimelineObject(self, timeline_object):
        Selection.addTimelineObject(self, timeline_object)

        # connect to signals to update link entries
        start_changed_sig_id = timeline_object.connect('start-changed',
                self._startChangedCb)
        duration_changed_sig_id = timeline_object.connect('duration-changed',
                self._durationChangedCb)

        # create a link entry, saving the initial start and duration
        link_entry = LinkEntry(timeline_object.start, timeline_object.duration,
                start_changed_sig_id, duration_changed_sig_id)

        self.link_entries[timeline_object] = link_entry

    def removeTimelineObject(self, timeline_object):
        Selection.removeTimelineObject(self, timeline_object)

        # remove link entry
        link_entry = self.link_entries[timeline_object]
        #timeline_object.disconnect(link_entry.start_changed_sig_id)
        #timeline_object.disconnect(link_entry.duration_changed_sig_id)
        timeline_object.disconnect_by_function(self._startChangedCb)
        timeline_object.disconnect_by_function(self._durationChangedCb)

    def _startChangedCb(self, timeline_object, start):
        link_entry = self.link_entries[timeline_object]
        
        if not self.waiting_update:
            old_start = link_entry.start
            delta = start - old_start

            self.waiting_update = list(self.timeline_objects)
            # we aren't waiting
            self.waiting_update.remove(timeline_object)
            for linked_object in list(self.waiting_update):
                # this will trigger signals that modify self.waiting_update so
                # we iterate over a copy
                linked_object.start += delta

            assert not self.waiting_update
        else:
            self.waiting_update.remove(timeline_object)
        
        link_entry.start = start

    def _durationChangedCb(self, timeline_object, duration):
        link_entry = self.link_entries[timeline_object]
        link_entry.duration = duration

class Timeline(object ,Signallable):
    __signals__ = {
        'duration-changed': ['duration'],
        'track-added': ['track'],
        'track-removed': ['track']
    }

    def __init__(self):
        self.tracks = []
        self.selections = []
        self.timeline_objects = []
        self.duration = 0

    def addTrack(self, track):
        if track in self.tracks:
            raise TimelineError()

        self.tracks.append(track)
        self._updateDuration()
        track.connect('start-changed', self._trackDurationChangedCb)
        track.connect('duration-changed', self._trackDurationChangedCb)

        self.emit('track-added', track)

    def _trackStartChangedCb(self, track, duration):
        self._updateDuration()
    
    def _trackDurationChangedCb(self, track, duration):
        self._updateDuration()
    
    def _updateDuration(self):
        duration = max([track.start + track.duration for track in self.tracks])
        if duration != self.duration:
            self.duration = duration
            self.emit('duration-changed', duration)

    def removeTrack(self, track, removeTrackObjects=True):
        try:
            self.tracks.remove(track)
        except ValueError:
            raise TimelineError()

        if removeTrackObjects:
            track.removeAllTrackObjects()

        self.emit('track-removed', track)

    def addTimelineObject(self, obj):
        if obj in self.timeline_objects:
            raise TimelineError()

        if not obj.track_objects:
            raise TimelineError()

        self.timeline_objects.append(obj)

    def removeTimelineObject(self, obj):
        try:
            self.timeline_objects.remove(obj)
        except ValueError:
            raise TimelineError()

    # FIXME: find a better name?
    def addFactory(self, factory):
        track_object = SourceTrackObject(factory)
        timeline_object = TimelineObject(factory)
        timeline_object.addTrackObject(track_object)
        self.addTimelineObject(timeline_object)

        track = self.tracks[0]
        duration = track.duration
        self.tracks[0].addTrackObject(track_object)

        timeline_object.setStart(duration)

    def setSelectionTo(self, selection, *args):
        pass
    
    def setSelectionToObj(self, selection, *args):
        pass
