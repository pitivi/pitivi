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

from pitivi.signalinterface import Signallable
from pitivi.utils import UNKNOWN_DURATION
from pitivi.timeline.track import Track, SourceTrackObject, TrackError

SELECT = 0
SELECT_ADD = 2
UNSELECT = 1

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
        self.timeline = None
        self.link = None

    def copy(self):
        cls = self.__class__
        other = cls(self.factory)
        other.track_objects = [track_object.copy() for track_object in
                self.track_objects]

        return other

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

        if self.link is not None:
            # if we're part of a link, we need to check if it's necessary to
            # clamp time so that we don't push the earliest element before 0s
            delta = time - self.start
            off = self.link.earliest_start + delta
            if off < 0:
                # clamp so that the earliest element is shifted to 0s
                time -= off

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
        
        time = min(time, self.factory.duration)
        
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

    def trimStart(self, time, snap=False):
        if not self.track_objects:
            raise TimelineError()

        for track_object in self.track_objects:
            track_object.trimObjectStart(time)

        self.emit('start-changed', self.start)
        self.emit('in-point-changed', self.in_point)
    
    def split(self, time, snap=False):
        if not self.track_objects:
            raise TimelineError()

        other = self.copy()
        # ditch track objects. This is a bit weird, will be more clear when we
        # use other uses of TimelineObject.copy
        other.track_objects = []

        for track_object in self.track_objects:
            try:
                other_track_object = track_object.splitObject(time)
            except TrackError, e:
                # FIXME: hallo exception hierarchy?
                raise TimelineError(str(e))

            other.addTrackObject(other_track_object)
            track_object.track.addTrackObject(other_track_object)

        if self.timeline is not None:
            # if self is not yet in a timeline, the caller needs to add "other"
            # as well when it adds self
            self.timeline.addTimelineObject(other)

        return other

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

        # FIXME: cycle
        obj.timeline_object = self
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
    def __init__(self, start, duration):
        self.start = start
        self.duration = duration

class Link(Selection):
    def __init__(self):
        Selection.__init__(self)
        self.link_entries = {}
        self.waiting_update = []
        self.earliest_object = None
        self.earliest_start = None

    def addTimelineObject(self, timeline_object):
        if timeline_object.link is not None:
            raise TimelineError()

        Selection.addTimelineObject(self, timeline_object)

        # connect to signals to update link entries
        timeline_object.connect('start-changed', self._startChangedCb)
        timeline_object.connect('duration-changed', self._durationChangedCb)

        # create a link entry, saving the initial start and duration
        link_entry = LinkEntry(timeline_object.start, timeline_object.duration)
        self.link_entries[timeline_object] = link_entry

        # FIXME: cycle
        timeline_object.link = self

        if self.earliest_start is None or \
                timeline_object.start < self.earliest_start:
            self.earliest_object = timeline_object
            self.earliest_start = timeline_object.start

    def removeTimelineObject(self, timeline_object):
        Selection.removeTimelineObject(self, timeline_object)

        # remove link entry
        link_entry = self.link_entries[timeline_object]
        timeline_object.disconnect_by_function(self._startChangedCb)
        timeline_object.disconnect_by_function(self._durationChangedCb)

        timeline_object.link = None

    def join(self, other_link):
        new_link = Link()

        for timeline_object in list(self.timeline_objects):
            self.removeTimelineObject(timeline_object)
            new_link.addTimelineObject(timeline_object)
        
        for timeline_object in list(other_link.timeline_objects):
            other_link.removeTimelineObject(timeline_object)
            new_link.addTimelineObject(timeline_object)

        return new_link

    def _startChangedCb(self, timeline_object, start):
        link_entry = self.link_entries[timeline_object]

        if not self.waiting_update:
            old_start = link_entry.start
            delta = start - old_start
            earliest = timeline_object

            self.waiting_update = list(self.timeline_objects)
            # we aren't waiting
            self.waiting_update.remove(timeline_object)
            for linked_object in list(self.waiting_update):
                # this will trigger signals that modify self.waiting_update so
                # we iterate over a copy
                linked_object.start += delta

                if linked_object.start < earliest.start:
                    earliest = linked_object

            assert not self.waiting_update

            self.earliest_object = earliest
            self.earliest_start = earliest.start

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
        self.timeline_selection = set()
        self.links = []

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
        if obj.timeline is not None:
            raise TimelineError()

        if not obj.track_objects:
            raise TimelineError()

        self.timeline_objects.append(obj)
        obj.timeline = self

    def removeTimelineObject(self, obj):
        try:
            self.timeline_objects.remove(obj)
        except ValueError:
            raise TimelineError()

        obj.timeline = None

    # FIXME: find a better name?
    def addFactory(self, factory):
        track_object = SourceTrackObject(factory)
        timeline_object = TimelineObject(factory)
        timeline_object.addTrackObject(track_object)
        self.addTimelineObject(timeline_object)

        if len(self.tracks[0].track_objects) < \
                len(self.tracks[1].track_objects):
            track = self.tracks[0]
        else:
            track = self.tracks[1]

        duration = track.duration
        track.addTrackObject(track_object)

        timeline_object.setStart(duration)

    def setSelectionToObj(self, obj, mode):
        self.setSelectionTo(set([obj]), mode)

    def setSelectionTo(self, selection, mode):
        selection = set([obj.timeline_object for obj in selection])
        if mode == SELECT:
            self.timeline_selection = selection
        elif mode == SELECT_ADD:
            self.timeline_selection.update(selection)
        elif mode == UNSELECT:
            self.timeline_selection.difference(selection)

    def linkSelection(self):
        if len(self.timeline_selection) < 2:
            return

        # list of links that we joined and so need to be removed
        old_links = []

        # we start with a new empty link and we expand it as we find new objects
        # and links
        link = Link()
        for timeline_object in self.timeline_selection:
            if timeline_object.link is not None:
                old_links.append(timeline_object.link)

                link = link.join(timeline_object.link)
            else:
                link.addTimelineObject(timeline_object)

        for old_link in old_links:
            self.links.remove(old_link)

        self.links.append(link)

    def unlinkSelection(self):
        empty_links = set()
        for timeline_object in self.timeline_selection:
            if timeline_object.link is None:
                continue

            link = timeline_object.link
            link.removeTimelineObject(timeline_object)
            if not link.timeline_objects:
                empty_links.add(link)

        for link in empty_links:
            self.links.remove(link)

    def deleteSelection(self):
        self.unlinkSelection()
        for timeline_object in self.timeline_selection:
            self.removeTimelineObject(timeline_object)

            for track_object in timeline_object.track_objects:
                track = track_object.track
                track.removeTrackObject(track_object)

        self.timeline_selection = set()
