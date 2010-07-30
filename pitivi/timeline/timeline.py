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

from bisect import bisect_left

from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.utils import UNKNOWN_DURATION, closest_item, PropertyChangeTracker
from pitivi.timeline.track import TrackObject, SourceTrackObject,\
     TrackEffect, TrackError
from pitivi.stream import match_stream_groups_map
from pitivi.utils import start_insort_right, infinity, getPreviousObject, \
        getNextObject
from pitivi.timeline.gap import Gap, SmallestGapsFinder, invalid_gap

# Selection modes
SELECT = 0
"""Set the selection to the given set."""
UNSELECT = 1
"""Remove the given set from the selection."""
SELECT_ADD = 2
"""Extend the selection with the given set"""
SELECT_BETWEEN = 3
"""Select a range of clips"""

class TimelineError(Exception):
    """Base Exception for errors happening in L{Timeline}s or L{TimelineObject}s"""
    pass

class TimelineObject(Signallable, Loggable):
    """
    Base class for contents of a C{Timeline}.

    A L{TimelineObject} controls one or many L{TrackObject}.

    Signals:
     - C{start-changed} : The position changed.
     - C{duration-changed} : The duration changed.
     - C{in-point-changed} : The in-point changed.
     - C{out-point-changed} : The out-point changed.
     - C{media-duration-changed} : The used media duration changed.
     - C{priority-changed} : The priority changed.
     - C{selected-changed} : The selected status changed.

    @ivar start: The position of the object in a timeline (nanoseconds)
    @type start: L{long}
    @ivar duration: The duration of the object in a timeline (nanoseconds)
    @type duration: L{long}
    @ivar in_point: The in-point of the object (nanoseconds)
    @type in_point: L{long}
    @ivar out_point: The out-point of the object (nanoseconds)
    @type out_point: L{long}
    @ivar media_duration: The duration to use from the object (nanoseconds)
    @type media_duration: L{long}
    @ivar priority: The priority of the object in a timeline. 0 is top-priority.
    @type priority: L{int}
    @ivar selected: Whether the object is selected or not.
    @type selected: L{bool}
    @ivar track_objects: The Track objects controlled.
    @type track_objects: list of L{TrackObject}
    @ivar timeline: The L{Timeline} to which this object belongs
    @type timeline: L{Timeline}
    """
    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'in-point-changed': ['in-point'],
        'out-point-changed': ['in-point'],
        'media-duration-changed': ['media-duration'],
        'priority-changed': ['priority'],
        'selected-changed' : ['state'],
        'track-object-added': ["track_object"],
        'track-object-removed': ["track_object"],
    }

    DEFAULT_START = 0
    DEFAULT_DURATION = UNKNOWN_DURATION
    DEFAULT_IN_POINT = 0
    DEFAULT_OUT_POINT = UNKNOWN_DURATION
    DEFAULT_PRIORITY = 0

    def __init__(self, factory):
        Loggable.__init__(self)
        self.factory = factory
        self.track_objects = []
        self.timeline = None
        self.link = None
        self._selected = False

    def copy(self, copy_track_objects=True):
        cls = self.__class__
        other = cls(self.factory)
        other.track_objects = []
        if copy_track_objects:
            for track_object in self.track_objects:
                other.addTrackObject(track_object.copy())

        return other

    #{ Property methods

    def _getStart(self):
        if not self.track_objects:
            return self.DEFAULT_START

        return self.track_objects[0].start

    def setStart(self, position, snap=False):
        """
        Set the start position of the object.

        If snap is L{True}, then L{position} will be modified if it is close
        to a timeline edge.

        @param position: The position in nanoseconds.
        @type position: L{long}
        @param snap: Whether to snap to the nearest edge or not.
        @type snap: L{bool}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        """
        if not self.track_objects:
            raise TimelineError("TimelineObject doesn't control any TrackObjects")

        if snap:
            position = self.timeline.snapToEdge(position, position + self.duration)

        if self.link is not None:
            # if we're part of a link, we need to check if it's necessary to
            # clamp position so that we don't push the earliest element before 0s
            delta = position - self.start
            off = self.link.earliest_start + delta
            if off < 0:
                # clamp so that the earliest element is shifted to 0s
                position -= off

        for track_object in self.track_objects:
            track_object.setObjectStart(position)

        self.emit('start-changed', position)

    def _getDuration(self):
        if not self.track_objects:
            return self.DEFAULT_DURATION

        return self.track_objects[0].duration

    def setDuration(self, duration, snap=False, set_media_stop=True):
        """
        Sets the duration of the object.

        If snap is L{True}, then L{duration} will be modified if it is close
        to a timeline edge.

        If set_media_stop is L{False} then the change will not be propagated
        to the C{TrackObject}s this object controls.

        @param duration: The duration in nanoseconds.
        @type duration: L{long}
        @param snap: Whether to snap to the nearest edge or not.
        @type snap: L{bool}
        @param set_media_stop: propagate changes to track objects.
        @type set_media_stop: L{bool}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        """
        if not self.track_objects:
            raise TimelineError("TimelineObject doesn't control any TrackObjects")

        if snap:
            position = self.start + duration
            position = self.timeline.snapToEdge(position)
            duration = position - self.start

        duration = min(duration, self.factory.duration -
                self.track_objects[0].in_point)

        for track_object in self.track_objects:
            track_object.setObjectDuration(duration)
            if set_media_stop:
                track_object.setObjectMediaDuration(duration)

        self.emit('duration-changed', duration)

    def _getInPoint(self):
        if not self.track_objects:
            return self.DEFAULT_IN_POINT

        return self.track_objects[0].in_point

    # FIXME: 'snap' is a bogus argument here !
    def setInPoint(self, position, snap=False):
        """
        Sets the in-point of the object.

        @param position: The position in nanoseconds.
        @type position: L{long}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        """
        if not self.track_objects:
            raise TimelineError("TimelineObject doesn't control any TrackObjects")

        for track_object in self.track_objects:
            track_object.setObjectInPoint(position)

        self.emit('in-point-changed', position)

    def _getOutPoint(self):
        if not self.track_objects:
            return self.DEFAULT_IN_POINT

        return self.track_objects[0].out_point

    def _getMediaDuration(self):
        if not self.track_objects:
            return self.DEFAULT_OUT_POINT

        return self.track_objects[0].media_duration

    # FIXME: 'snaps' is a bogus argument here !
    def setMediaDuration(self, position, snap=False):
        """
        Sets the media-duration of the object.

        @param position: The position in nanoseconds.
        @type position: L{long}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        """
        if not self.track_objects:
            raise TimelineError("TimelineObject doesn't control any TrackObjects")

        for track_object in self.track_objects:
            track_object.setObjectMediaDuration(position)

        self.emit('media-duration-changed', position)

    def _getPriority(self):
        if not self.track_objects:
            return self.DEFAULT_PRIORITY

        return self.track_objects[0].priority

    def setPriority(self, priority):
        """
        Sets the priority of the object. 0 is the highest priority.

        @param priority: The priority (0 : highest)
        @type priority: L{int}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        """
        if not self.track_objects:
            raise TimelineError("TimelineObject doesn't control any TrackObjects")

        for track_object in self.track_objects:
            track_object.setObjectPriority(priority)

        self.emit('priority-changed', priority)

    # True when the timeline object is part of the track object's current
    # selection.

    def _getSelected(self):
        return self._selected

    def setSelected(self, state):
        """
        Sets the selected state of the object.

        @param state: L{True} if the object should be selected.
        @type state: L{bool}
        """
        self._selected = state

        for obj in self.track_objects:
            obj.setObjectSelected(state)

        self.emit("selected-changed", state)

    #}

    selected = property(_getSelected, setSelected)
    start = property(_getStart, setStart)
    duration = property(_getDuration, setDuration)
    in_point = property(_getInPoint, setInPoint)
    out_point = property(_getOutPoint)
    media_duration = property(_getMediaDuration, setMediaDuration)
    priority = property(_getPriority, setPriority)

    #{ Time-related methods

    def trimStart(self, position, snap=False):
        """
        Trim the beginning of the object to the given L{position} in nanoseconds.

        If snap is L{True}, then L{position} will be modified if it is close
        to a timeline edge.

        @param position: The position in nanoseconds.
        @type position: L{long}
        @param snap: Whether to snap to the nearest edge or not.
        @type snap: L{bool}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        """
        if not self.track_objects:
            raise TimelineError("TimelineObject doesn't control any TrackObjects")

        if snap:
            position = self.timeline.snapToEdge(position)

        for track_object in self.track_objects:
            track_object.trimObjectStart(position)

        self.emit('start-changed', self.start)
        self.emit('duration-changed', self.duration)
        self.emit('in-point-changed', self.in_point)

    def split(self, position, snap=False):
        """
        Split the given object at the given position in nanoseconds.

        The object will be resized to the given position, and another object will
        be created which starts just after and ends at the initial end position.

        If snap is L{True}, then L{position} will be modified if it is close
        to a timeline edge.

        @param position: The position in nanoseconds.
        @type position: L{long}
        @param snap: Whether to snap to the nearest edge or not.
        @type snap: L{bool}
        @returns: The object corresponding to the other half.
        @rtype: L{TimelineObject}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        @postcondition: If the originating object was not yet in a C{Timeline}, then
        it is up to the caller to add the returned 'half' object to a C{Timeline}.
        """
        if not self.track_objects:
            raise TimelineError("TimelineObject doesn't control any TrackObjects")

        other = self.copy(copy_track_objects=False)

        for track_object in self.track_objects:
            try:
                other_track_object = track_object.splitObject(position)
            except TrackError, e:
                # FIXME: hallo exception hierarchy?
                raise TimelineError(str(e))

            other.addTrackObject(other_track_object)

        if self.timeline is not None:
            # if self is not yet in a timeline, the caller needs to add "other"
            # as well when it adds self
            self.timeline.addTimelineObject(other)

        self.emit('duration-changed', self.duration)

        return other

    #{ TrackObject methods

    def addTrackObject(self, obj):
        """
        Add the given C{TrackObject} to the list of controlled track objects.

        @param obj: The track object to add
        @type obj: C{TrackObject}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        @raises TimelineError: If the provided C{TrackObject} is already controlled
        by this L{TimelineObject}
        @raises TimelineError: If the newly provided C{TrackObject} doesn't have the
        same start position as the other objects controlled.
        @raises TimelineError: If the newly provided C{TrackObject} doesn't have the
        same duration as the other objects controlled.
        """
        if obj.timeline_object is not None:
            raise TimelineError("TrackObject already controlled by another TimelineObject")

        if obj in self.track_objects:
            # FIXME : couldn't we just silently return ?
            raise TimelineError("TrackObject already controlled by this TimelineObject")

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

            # FIXME : We really should be able to support controlling more than
            # one trackobject with offseted start/duration/in-/out-point/priorities
            existing_track_object = self.track_objects[0]
            if obj.start != existing_track_object.start or \
                    obj.duration != existing_track_object.duration:
                raise TimelineError("New TrackObject doesn't have same duration as other controlled TrackObjects")

        # FIXME: cycle
        obj.timeline_object = self
        start_insort_right(self.track_objects, obj)

        self.emit("track-object-added", obj)

    def removeTrackObject(self, obj):
        """
        Remove the given object from the list of controlled C{TrackObject}.

        @param obj: The Track Object to remove.
        @type obj: C{TrackObject}
        @raises TimelineError: If the Track object isn't controlled by this TimelineObject.
        """
        if obj.track is None:
            raise TimelineError("TrackObject doesn't belong to any Track")

        try:
            self.track_objects.remove(obj)
            obj.timeline_object = None
        except ValueError:
            raise TimelineError("TrackObject doesn't belong to this TimelineObject")

        self.emit("track-object-removed", obj)

class Selection(Signallable):
    """
    A collection of L{TimelineObject}.

    Signals:
     - C{selection-changed} : The contents of the L{Selection} changed.

    @ivar selected: Set of selected L{TrackObject}
    @type selected: C{list}
    """

    __signals__ = {
        "selection-changed" : []
    }

    def __init__(self):
        self.selected = set([])
        self.last_single_obj = None

    def setToObj(self, obj, mode):
        """
        Convenience method for calling L{setSelection} with a single L{TimelineObject}

        @see: L{setSelection}
        """
        self.setSelection(set([obj]), mode)

    def addTimelineObject(self, timeline_object):
        """
        Add the given timeline_object to the selection.

        @param timeline_object: The object to add
        @type timeline_object: L{TimelineObject}
        @raises TimelineError: If the object is already controlled by this
        Selection.
        """
        if timeline_object in self.timeline_objects:
            raise TimelineError("TrackObject already in this selection")

    def setSelection(self, objs, mode):
        """
        Update the current selection.

        Depending on the value of C{mode}, the selection will be:
         - L{SELECT} : set to the provided selection.
         - L{UNSELECT} : the same minus the provided selection.
         - L{SELECT_ADD} : extended with the provided selection.

        @param selection: The list of timeline objects to update the selection with.
        @param mode: The type of update to apply. Can be C{SELECT},C{UNSELECT} or C{SELECT_ADD}

        @see: L{setToObj}
        """
        # get a list of timeline objects
        selection = set()
        for obj in objs:
            if isinstance(obj, TrackObject):
                selection.add(obj.timeline_object)
            else:
                selection.add(obj)
        old_selection = self.selected
        if mode == SELECT_ADD:
            selection = self.selected | selection
        elif mode == UNSELECT:
            selection = self.selected - selection
        self.selected = selection

        if len(self.selected) == 1:
            self.last_single_obj = iter(selection).next()

        for obj in self.selected - old_selection:
            obj.selected = True
        for obj in old_selection - self.selected:
            obj.selected = False

        # FIXME : shouldn't we ONLY emit this IFF the selection has changed ?
        self.emit("selection-changed")

    def getSelectedTrackObjs(self):
        """
        Returns the list of L{TrackObject} contained in this selection.
        """
        objects = []
        for timeline_object in self.selected:
            objects.extend(timeline_object.track_objects)

        return set(objects)

    def getSelectedTrackEffects(self):
        """
        Returns the list of L{TrackEffect} contained in this selection.
        """
        track_effects = []
        for timeline_object in self.selected:
            for track in timeline_object.track_objects:
                if isinstance(track, TrackEffect):
                    track_effects.append(track)

        return set(track_effects)

    def __len__(self):
        return len(self.selected)

    def __iter__(self):
        return iter(self.selected)


# FIXME : What is this for ? It's not used anywhere AFAICS (Edward)
class LinkEntry(object):
    def __init__(self, start, duration):
        self.start = start
        self.duration = duration



class LinkPropertyChangeTracker(PropertyChangeTracker):
    """
    Tracker for private usage by L{Link}

    @see: L{Link}
    """
    __signals__ = {
        'start-changed': ['old', 'new'],
        'duration-changed': ['old', 'new']
    }

    property_names = ('start', 'duration')

class Link(object):

    def __init__(self):
        self.timeline_objects = set([])
        self.property_trackers = {}
        self.waiting_update = []
        self.earliest_object = None
        self.earliest_start = None

    def addTimelineObject(self, timeline_object):
        if timeline_object.link is not None:
            raise TimelineError("TimelineObject already in a Link")

        if timeline_object in self.timeline_objects:
            raise TimelineError("TimelineObject already controlled by this Link")

        self.timeline_objects.add(timeline_object)

        tracker = LinkPropertyChangeTracker()
        tracker.connectToObject(timeline_object)
        self.property_trackers[timeline_object] = tracker

        tracker.connect('start-changed', self._startChangedCb)

        # FIXME: cycle
        # Edward : maybe use a weak reference instead ? pydoc weakref
        timeline_object.link = self

        if self.earliest_start is None or \
                timeline_object.start < self.earliest_start:
            self.earliest_object = timeline_object
            self.earliest_start = timeline_object.start

    def removeTimelineObject(self, timeline_object):
        try:
            self.timeline_objects.remove(timeline_object)
        except KeyError:
            raise TimelineError("TimelineObject not controlled by this Link")

        tracker = self.property_trackers.pop(timeline_object)
        tracker.disconnectFromObject(timeline_object)

        timeline_object.link = None

    def join(self, other_link):
        """
        Joins this Link with another and returns the resulting link.

        @type other_link: C{Link}
        @postcondition: L{self} and L{other_link} must not be used after
        calling this method !!
        """
        new_link = Link()

        for timeline_object in list(self.timeline_objects):
            self.removeTimelineObject(timeline_object)
            new_link.addTimelineObject(timeline_object)

        for timeline_object in list(other_link.timeline_objects):
            other_link.removeTimelineObject(timeline_object)
            new_link.addTimelineObject(timeline_object)

        return new_link

    def _startChangedCb(self, tracker, timeline_object, old_start, start):
        if not self.waiting_update:
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

# FIXME: This seems overly complicated and (therefore) a potential speed bottleneck.
# It would be much simpler to just track objects, and specify for each object
# which property we would like to track (start, end, both). We could then have
# two lists of those objects, one sorted by start values, and another sorted by
# end values.
# Bonus : GnlComposition already has all this information, we could maybe add
# an action signal to it to drastically speed up this process.
#
# Alessandro: this is faster than having two separate lists. By keeping start
# and end edges in the same list, we reduce the time we scan the list
# of edges. In fact once we find a start edge at pos X, we then scan for an end
# edge by starting at edges[X] and going forward, avoiding to rescan the edges
# from 0 to X.
# I don't see how exposing the gnl lists would make things faster, what's taking
# time here is scanning the lists, and it's something you'd have to do anyway.
class TimelineEdges(object):
    """
    Tracks start/stop values and offers convenience methods to find the
    closest value for a given position.
    """
    def __init__(self):
        self.edges = []
        self.by_start = {}
        self.by_end = {}
        self.by_time = {}
        self.by_object = {}
        self.changed_objects = {}
        self.enable_updates = True

    def addTimelineObject(self, timeline_object):
        """
        Add this object's start/stop values to the edges.

        @param timeline_object: The object whose start/stop we want to track.
        @type timeline_object: L{TimelineObject}
        """
        for obj in timeline_object.track_objects:
            self.addTrackObject(obj)

        self._connectToTimelineObject(timeline_object)

    def removeTimelineObject(self, timeline_object):
        """
        Remove this object's start/stop values from the edges.

        @param timeline_object: The object whose start/stop we no longer want
        to track.
        @type timeline_object: L{TimelineObject}
        """
        self._disconnectFromTimelineObject(timeline_object)
        for obj in timeline_object.track_objects:
             self.removeTrackObject(obj)

    def _connectToTimelineObject(self, timeline_object):
        timeline_object.connect("track-object-added", self._trackObjectAddedCb)
        timeline_object.connect("track-object-removed", self._trackObjectRemovedCb)

    def _disconnectFromTimelineObject(self, timeline_object):
        timeline_object.disconnect_by_func(self._trackObjectAddedCb)
        timeline_object.disconnect_by_func(self._trackObjectRemovedCb)

    def _trackObjectAddedCb(self, timeline_object, track_object):
        self.addTrackObject(track_object)

    def _trackObjectRemovedCb(self, timeline_object, track_object):
        self.removeTrackObject(track_object)

    def addTrackObject(self, track_object):
        if track_object in self.by_object:
            raise TimelineError("TrackObject already controlled by this TimelineEdge")

        start = track_object.start
        end = track_object.start + track_object.duration

        self.addStartEnd(start, end)

        self.by_start.setdefault(start, []).append(track_object)
        self.by_end.setdefault(end, []).append(track_object)
        self.by_time.setdefault(start, []).append(track_object)
        self.by_time.setdefault(end, []).append(track_object)
        self.by_object[track_object] = (start, end)
        self._connectToTrackObject(track_object)

    def removeTrackObject(self, track_object):
        try:
            old_start, old_end = self.by_object.pop(track_object)
        except KeyError:
            raise TimelineError("TrackObject not controlled by this TimelineEdge")

        try:
            del self.changed_objects[track_object]
            start = old_start
            end = old_end
        except KeyError:
            start = track_object.start
            end = track_object.start + track_object.duration

        self.removeStartEnd(start, end)

        # remove start and end from self.by_start, self.by_end and self.by_time
        for time, time_dict in ((start, self.by_start), (end, self.by_end),
                (start, self.by_time), (end, self.by_time)):
            time_dict[time].remove(track_object)
            if not time_dict[time]:
                del time_dict[time]

        self._disconnectFromTrackObject(track_object)

    def _connectToTrackObject(self, track_object):
        track_object.connect("start-changed", self._trackObjectStartChangedCb)
        track_object.connect("duration-changed", self._trackObjectDurationChangedCb)

    def _disconnectFromTrackObject(self, track_object):
        track_object.disconnect_by_func(self._trackObjectStartChangedCb)
        track_object.disconnect_by_func(self._trackObjectDurationChangedCb)

    def _trackObjectStartChangedCb(self, track_object, start):
        start = track_object.start
        end = start + track_object.duration

        self.changed_objects[track_object] = (start, end)

        self._maybeProcessChanges()

    def _trackObjectDurationChangedCb(self, track_object, duration):
        start = track_object.start
        end = start + track_object.duration

        self.changed_objects[track_object] = (start, end)

        self._maybeProcessChanges()

    def addStartEnd(self, start, end=None):
        lo = 0
        index = bisect_left(self.edges, start, lo=lo)
        lo = index
        self.edges.insert(index, start)

        if end is not None:
            index = bisect_left(self.edges, end, lo=lo)
            self.edges.insert(index, end)

    def removeStartEnd(self, start, end=None):
        lo = 0
        index = bisect_left(self.edges, start, lo=lo)
        # check if start is a valid edge
        if index == len(self.edges) or self.edges[index] != start:
            raise TimelineError("Start (%r) is not a valid edge" % start)

        del self.edges[index]
        lo = index

        if end is not None:
            index = bisect_left(self.edges, end, lo=lo)
            # check if end is a valid edge
            if index == len(self.edges) or self.edges[index] != end:
                raise TimelineError("End (%r) is not a valid edge")

            del self.edges[index]

    def enableUpdates(self):
        self.enable_updates = True
        self._maybeProcessChanges()

    def _maybeProcessChanges(self):
        if not self.enable_updates:
            return

        changed, self.changed_objects = self.changed_objects, {}

        for track_object, (start, end) in changed.iteritems():
            old_start, old_end = self.by_object[track_object]

            for old_time, time, time_dict in ((old_start, start, self.by_start),
                    (old_end, end, self.by_end), (old_start, start, self.by_time),
                    (old_end, end, self.by_time)):
                time_dict[old_time].remove(track_object)
                if not time_dict[old_time]:
                    del time_dict[old_time]
                time_dict.setdefault(time, []).append(track_object)

            old_edges = []
            new_edges = []
            if start != old_start:
                old_edges.append(old_start)
                new_edges.append(start)

            if end != old_end:
                old_edges.append(old_end)
                new_edges.append(end)

            if old_edges:
                self.removeStartEnd(*old_edges)
            if new_edges:
                self.addStartEnd(*new_edges)

            self.by_object[track_object] = (start, end)

    def disableUpdates(self):
        self.enable_updates = False

    def snapToEdge(self, start, end=None):
        """
        Returns:
         - the closest edge to the given start/stop position.
         - the difference between the provided position and the returned edge.
        """
        if len(self.edges) == 0:
            return start, 0

        start_closest, start_diff, start_index = \
                closest_item(self.edges, start)

        if end is None or len(self.edges) == 1:
            return start_closest, start_diff,

        end_closest, end_diff, end_index = \
                closest_item(self.edges, end, start_index)

        if start_diff <= end_diff:
            return start_closest, start_diff

        return start + end_diff, end_diff

    def closest(self, position):
        """
        Returns two values:
         - The closest value just *before* the given position.
         - The closest value just *after* the given position.

        @param position: The position to search for.
        @type position: L{long}
        """
        closest, diff, index = closest_item(self.edges, position)
        return self.edges[max(0, index - 2)], self.edges[min(
            len(self.edges) - 1, index + 1)]

    def getObjsIncidentOnTime(self, time):
        """Return a list of all track objects whose start or end (start +
        duration) are exactly equal to a given time"""
        if time in self.by_time:
            return self.by_time[time]
        return []

    def getObjsAdjacentToStart(self, trackobj):
        """Return a list of all track objects whose ends (start + duration)
        are equal to the given track object's start"""
        if trackobj.start in self.by_end:
            return self.by_end[trackobj.start]
        return []

    def getObjsAdjacentToEnd(self, trackobj):
        """Return a list of all track objects whose start property are
        adjacent to the given track object's end (start + duration)"""
        end = trackobj.start + trackobj.duration
        if end in self.by_start:
            return self.by_start[end]
        return []

class EditingContext(object):

    DEFAULT = 0
    ROLL = 1
    RIPPLE = 2
    SLIP_SLIDE = 3

    """Encapsulates interactive editing.

    This is the base class for interactive editing contexts.
    """

    def __init__(self, timeline, focus, other):
        """
        @param timeline: the timeline to edit
        @type timeline: instance of L{pitivi.timeline.timeline.Timeline}

        @param focus: the TimelineObject or TrackObject which is to be the the
        main target of interactive editing, such as the object directly under the
        mouse pointer
        @type focus: L{pitivi.timeline.timeline.TimelineObject} or
        L{pitivi.timeline.trackTrackObject}

        @param other: a set of objects which are the secondary targets of
        interactive editing, such as objects in the current selection.
        @type other: a set() of L{TimelineObject}s or L{TrackObject}s

        @returns: An instance of L{pitivi.timeline.timeline.TimelineEditContex}
        """

        # make sure focus is not in secondary object list
        other.difference_update(set((focus,)))

        self.other = other
        self.focus = focus
        self.timeline = timeline
        self._snap = True
        self._mode = self.DEFAULT
        self._last_position = focus.start
        self._last_priority = focus.priority

        self.timeline.disableUpdates()

    def _getOffsets(self, start_offset, priority_offset, timeline_objects):
        offsets = {}
        for timeline_object in timeline_objects:
            offsets[timeline_object] = (timeline_object.start - start_offset,
                        timeline_object.priority - priority_offset)

        return offsets

    def _getTimelineObjectValues(self, timeline_object):
        return (timeline_object.start, timeline_object.duration,
                timeline_object.in_point, timeline_object.media_duration,
                timeline_object.priority)

    def _saveValues(self, timeline_objects):
        return dict(((timeline_object,
            self._getTimelineObjectValues(timeline_object))
                for timeline_object in timeline_objects))

    def _restoreValues(self, values):
        for timeline_object, (start, duration, in_point, media_dur, pri) in \
            values.iteritems():
            timeline_object.start = start
            timeline_object.duration = duration
            timeline_object.in_point = in_point
            timeline_object.media_duration = media_dur
            timeline_object.priority = pri

    def _getSpan(self, earliest, objs):
        return max((obj.start + obj.duration for obj in objs)) - earliest

    def finish(self):
        """Clean up timeline for normal editing"""
        # TODO: post undo / redo action here
        self.timeline.enableUpdates()

    def setMode(self, mode):
        """Set the current editing mode.
        @param mode: the editing mode. Must be one of DEFAULT, ROLL, or
        RIPPLE.
        """
        if mode != self._mode:
            self._finishMode(self._mode)
            self._beginMode(mode)
            self._mode = mode

    def _finishMode(self, mode):
        if mode == self.DEFAULT:
            self._finishDefault()
        elif mode == self.ROLL:
            self._finishRoll()
        elif mode == self.RIPPLE:
            self._finishRipple()

    def _beginMode(self, mode):
        if self._last_position:
            if mode == self.DEFAULT:
                self._defaultTo(self._last_position, self._last_priority)
            elif mode == self.ROLL:
                self._rollTo(self._last_position, self._last_priority)
            elif mode == self.RIPPLE:
                self._rippleTo(self._last_position, self._last_priority)

    def _finishRoll(self):
        pass

    def _rollTo(self, position, priority):
        return position, priority

    def _finishRipple(self):
        pass

    def _rippleTo(self, position, priority):
        return position, priority

    def _finishDefault(self):
        pass

    def _defaultTo(self, position, priority):
        return position, priority

    def snap(self, snap):
        """Set whether edge snapping is currently enabled"""
        if snap != self._snap:
            self.editTo(self._last_position, self._last_priority)
        self._snap = snap

    def editTo(self, position, priority):
        if self._mode == self.DEFAULT:
            position, priority = self._defaultTo(position, priority)
        if self._mode == self.ROLL:
            position, priority = self._rollTo(position, priority)
        elif self._mode == self.RIPPLE:
            position, priority = self._rippleTo(position, priority)
        self._last_position = position
        self._last_priority = priority

        return position, priority

    def _getGapsAtPriority(self, priority, timeline_objects, tracks=None):
        gaps = SmallestGapsFinder(timeline_objects)
        prio_diff = priority - self.focus.priority

        for timeline_object in timeline_objects:
            left_gap, right_gap = Gap.findAroundObject(timeline_object,
                    timeline_object.priority + prio_diff, tracks)
            gaps.update(left_gap, right_gap)

        return gaps.left_gap, gaps.right_gap


class MoveContext(EditingContext):

    """An editing context which sets the start point of the editing targets.
    It has support for ripple, slip-and-slide editing modes."""

    def __init__(self, timeline, focus, other):
        EditingContext.__init__(self, timeline, focus, other)

        min_priority = infinity
        earliest = infinity
        latest = 0
        self.default_originals = {}
        self.timeline_objects = set([])
        self.tracks = set([])
        all_objects = set(other)
        all_objects.add(focus)
        for obj in all_objects:
            if isinstance(obj, TrackObject):
                timeline_object = obj.timeline_object
                self.tracks.add(obj.track)
            else:
                timeline_object = obj
                timeline_object_tracks = set(track_object.track for track_object
                        in timeline_object.track_objects)
                self.tracks.update(timeline_object_tracks)

            self.timeline_objects.add(timeline_object)

            self.default_originals[timeline_object] = \
                    self._getTimelineObjectValues(timeline_object)

            earliest = min(earliest, timeline_object.start)
            latest = max(latest,
                    timeline_object.start + timeline_object.duration)
            min_priority = min(min_priority, timeline_object.priority)

        self.offsets = self._getOffsets(self.focus.start, self.focus.priority,
                self.timeline_objects)

        self.min_priority = focus.priority - min_priority
        self.min_position = focus.start - earliest

        # get the span over all clips for edge snapping
        self.default_span = latest - earliest

        ripple = timeline.getObjsAfterTime(latest)
        self.ripple_offsets = self._getOffsets(self.focus.start,
            self.focus.priority, ripple)

        # get the span over all clips for ripple editing
        for timeline_object in ripple:
            latest = max(latest, timeline_object.start +
                timeline_object.duration)
        self.ripple_span = latest - earliest

        # save default values
        self.ripple_originals = self._saveValues(ripple)

        self.timeline_objects_plus_ripple = set(self.timeline_objects)
        self.timeline_objects_plus_ripple.update(ripple)

    def _getGapsAtPriority(self, priority):
        if self._mode == self.RIPPLE:
            timeline_objects = self.timeline_objects_plus_ripple
        else:
            timeline_objects = self.timeline_objects

        return EditingContext._getGapsAtPriority(self,
                priority, timeline_objects, self.tracks)

    def setMode(self, mode):
        if mode == self.ROLL:
            raise Exception("invalid mode ROLL")
        EditingContext.setMode(self, mode)

    def _finishDefault(self):
        self._restoreValues(self.default_originals)

    def _overlapsAreTransitions(self, focus, priority):
        left_gap, right_gap = Gap.findAroundObject(focus)

        focus_end = focus.start + focus.duration

        # left_transition
        if left_gap.duration < 0:

            left_obj = left_gap.left_object
            left_end = left_obj.start + left_obj.duration

            if left_end > focus_end:
                return False

            # check that the previous previous object doesn't end after
            # our start time. we shouldn't have to go back further than
            # this because
            #   * we are only moving one object
            #   * if there was more than one clip overlaping the previous
            #   clip, it too would be invalid, since that clip would
            #   overlap the previous and previous previous clips

            try:
                prev_prev = self.timeline.getPreviousTimelineObject(left_obj)
                if prev_prev.start + prev_prev.duration > self.focus.start:
                    return False
            except TimelineError:
                pass

        # right transition
        if right_gap.duration < 0:

            right_obj = right_gap.right_object
            right_end = right_obj.start + right_obj.duration

            if right_end < focus_end:
                return False

            # check that the next next object starts after we end

            try:
                next_next = self.timeline.getNextTimelineObject(right_obj)
                if next_next.start < focus_end:
                    return False
            except TimelineError:
                pass

        return True

    def finish(self):

        if isinstance(self.focus, TrackObject):
            focus_timeline_object = self.focus.timeline_object
        else:
            focus_timeline_object = self.focus
        initial_position = self.default_originals[focus_timeline_object][0]
        initial_priority = self.default_originals[focus_timeline_object][-1]

        final_priority = self.focus.priority
        final_position = self.focus.start

        priority = final_priority

        # special case for transitions. Allow a single object to overlap
        # either of its two neighbors if it overlaps no other objects
        if len(self.timeline_objects) == 1:
            if not self._overlapsAreTransitions(focus_timeline_object,
                priority):
                self._defaultTo (initial_position, initial_priority)
            EditingContext.finish(self)
            return

        # adjust priority
        overlap = False
        while True:
            left_gap, right_gap = self._getGapsAtPriority(priority)

            if left_gap is invalid_gap or right_gap is invalid_gap:
                overlap = True

                if priority == initial_priority:
                    break

                if priority > initial_priority:
                    priority -= 1
                else:
                    priority += 1


                self._defaultTo(final_position, priority)
            else:
                overlap = False
                break

        if not overlap:
            EditingContext.finish(self)
            return

        self._defaultTo(initial_position, priority)
        delta = final_position - initial_position
        left_gap, right_gap = self._getGapsAtPriority(priority)

        if delta > 0 and right_gap.duration < delta:
            final_position = initial_position + right_gap.duration
        elif delta < 0 and left_gap.duration < abs(delta):
            final_position = initial_position - left_gap.duration

        self._defaultTo(final_position, priority)
        EditingContext.finish(self)

    def _defaultTo(self, position, priority):
        if self._snap:
            position = self.timeline.snapToEdge(position,
                position + self.default_span)

        priority = max(self.min_priority, priority)
        position = max(self.min_position, position)

        self.focus.priority = priority
        self.focus.setStart(position, snap = self._snap)

        for obj, (s_offset, p_offset) in self.offsets.iteritems():
            obj.setStart(position + s_offset)
            obj.priority = priority + p_offset

        return position, priority

    def _finishRipple(self):
        self._restoreValues(self.ripple_originals)

    def _rippleTo(self, position, priority):
        if self._snap:
            position = self.timeline.snapToEdge(position,
                position + self.ripple_span)

        priority = max(self.min_priority, priority)
        left_gap, right_gap = self._getGapsAtPriority(priority)

        if left_gap is invalid_gap or right_gap is invalid_gap:
            if priority == self._last_priority:
                # abort move
                return self._last_position, self._last_priority

            # try to do the same time move, using the current priority
            return self._defaultTo(position, self._last_priority)

        delta = position - self.focus.start
        if delta > 0 and right_gap.duration < delta:
            position = self.focus.start + right_gap.duration
        elif delta < 0 and left_gap.duration < abs(delta):
            position = self.focus.start - left_gap.duration

        self.focus.setStart(position)
        self.focus.priority = priority
        for obj, (s_offset, p_offset) in self.offsets.iteritems():
            obj.setStart(position + s_offset)
            obj.priority = priority + p_offset
        for obj, (s_offset, p_offset) in self.ripple_offsets.iteritems():
            obj.setStart(position + s_offset)
            obj.priority = priority + p_offset

        return position, priority

class TrimStartContext(EditingContext):

    def __init__(self, timeline, focus, other):
        EditingContext.__init__(self, timeline, focus, other)
        self.adjacent = timeline.edges.getObjsAdjacentToStart(focus)
        self.adjacent_originals = self._saveValues(self.adjacent)
        self.tracks = set([])
        if isinstance(self.focus, TrackObject):
            focus_timeline_object = self.focus.timeline_object
            self.tracks.add(self.focus.track)
        else:
            focus_timeline_object = self.focus
            tracks = set(track_object.track for track_object in
                    focus.track_objects)
            self.tracks.update(tracks)
        self.focus_timeline_object = focus_timeline_object
        self.default_originals = self._saveValues([focus_timeline_object])

        ripple = self.timeline.getObjsBeforeTime(focus.start)
        assert not focus.timeline_object in ripple or focus.duration == 0
        self.ripple_originals = self._saveValues(ripple)
        self.ripple_offsets = self._getOffsets(focus.start, focus.priority,
            ripple)
        if ripple:
            self.ripple_min = focus.start - min((obj.start for obj in ripple))
        else:
            self.ripple_min = 0

    def _rollTo(self, position, priority):
        earliest = self.focus.start - self.focus.in_point
        self.focus.trimStart(max(position, earliest))
        for obj in self.adjacent:
            duration = max(0, position - obj.start)
            obj.setDuration(duration, snap=False)
        return position, priority

    def _finishRoll(self):
        self._restoreValues(self.adjacent_originals)

    def _rippleTo(self, position, priority):
        earliest = self.focus.start - self.focus.in_point
        latest = earliest + self.focus.factory.duration

        if self.snap:
            position = self.timeline.snapToEdge(position)

        position = min(latest, max(position, earliest))
        self.focus.trimStart(position)
        r_position = max(position, self.ripple_min)
        for obj, (s_offset, p_offset) in self.ripple_offsets.iteritems():
            obj.setStart(r_position + s_offset)

        return position, priority

    def _finishRipple(self):
        self._restoreValues(self.ripple_originals)

    def _defaultTo(self, position, priority):
        earliest = max(0, self.focus.start - self.focus.in_point)
        self.focus.trimStart(max(position, earliest), snap=self.snap)

        return position, priority

    def finish(self):
        initial_position = self.default_originals[self.focus_timeline_object][0]

        timeline_objects = [self.focus_timeline_object]
        left_gap, right_gap = self._getGapsAtPriority(self.focus.priority,
                timeline_objects, self.tracks)

        if left_gap is invalid_gap:
            self._defaultTo(initial_position, self.focus.priority)
            left_gap, right_gap = Gap.findAroundObject(self.focus_timeline_object)
            position = initial_position - left_gap.duration
            self._defaultTo(position, self.focus.priority)
        EditingContext.finish(self)

class TrimEndContext(EditingContext):

    def __init__(self, timeline, focus, other):
        EditingContext.__init__(self, timeline, focus, other)
        self.adjacent = timeline.edges.getObjsAdjacentToEnd(focus)
        self.adjacent_originals = self._saveValues(self.adjacent)
        self.tracks = set([])
        if isinstance(self.focus, TrackObject):
            focus_timeline_object = self.focus.timeline_object
            self.tracks.add(focus.track)
        else:
            focus_timeline_object = self.focus
            tracks = set(track_object.track for track_object in
                    focus.track_objects)
            self.tracks.update(tracks)
        self.focus_timeline_object = focus_timeline_object
        self.default_originals = self._saveValues([focus_timeline_object])

        reference = focus.start + focus.duration
        ripple = self.timeline.getObjsAfterTime(reference)

        self.ripple_originals = self._saveValues(ripple)
        self.ripple_offsets = self._getOffsets(reference, self.focus.priority,
            ripple)

    def _rollTo(self, position, priority):
        if self._snap:
            position = self.timeline.snapToEdge(position)
        duration = max(0, position - self.focus.start)
        self.focus.setDuration(duration)
        for obj in self.adjacent:
            obj.trimStart(position)
        return position, priority

    def _finishRoll(self):
        self._restoreValues(self.adjacent_originals)

    def _rippleTo(self, position, priority):
        earliest = self.focus.start - self.focus.in_point
        latest = earliest + self.focus.factory.duration
        if self.snap:
            position = self.timeline.snapToEdge(position)
        position = min(latest, max(position, earliest))
        duration = position - self.focus.start
        self.focus.setDuration(duration)
        for obj, (s_offset, p_offset) in self.ripple_offsets.iteritems():
            obj.setStart(position + s_offset)

        return position, priority

    def _finishRipple(self):
        self._restoreValues(self.ripple_originals)

    def _defaultTo(self, position, priority):
        duration = max(0, position - self.focus.start)
        self.focus.setDuration(duration, snap=self.snap)

        return position, priority

    def finish(self):
        EditingContext.finish(self)

        initial_position, initial_duration = \
                self.default_originals[self.focus_timeline_object][0:2]
        absolute_initial_duration = initial_position + initial_duration

        timeline_objects = [self.focus_timeline_object]
        left_gap, right_gap = self._getGapsAtPriority(self.focus.priority,
                timeline_objects, self.tracks)

        if right_gap is invalid_gap:
            self._defaultTo(absolute_initial_duration, self.focus.priority)
            left_gap, right_gap = Gap.findAroundObject(self.focus_timeline_object)
            duration = absolute_initial_duration + right_gap.duration
            self._defaultTo(duration, self.focus.priority)

class Timeline(Signallable, Loggable):
    """
    Top-level container for L{TimelineObject}s.

    Signals:
     - C{duration-changed} : The duration changed.
     - C{track-added} : A L{timeline.Track} was added.
     - C{track-removed} : A L{timeline.Track} was removed.
     - C{selection-changed} : The current selection changed.

    @ivar tracks: list of Tracks controlled by the Timeline
    @type tracks: List of L{timeline.Track}
    @ivar duration: Duration of the Timeline in nanoseconds.
    @type duration: C{long}
    @ivar selection: The currently selected TimelineObjects
    @type selection: L{Selection}
    """
    __signals__ = {
        'duration-changed': ['duration'],
        'timeline-object-added': ['timeline_object'],
        'timeline-object-removed': ['timeline_object'],
        'track-added': ['track'],
        'track-removed': ['track'],
        'selection-changed': [],
        'disable-updates': ['bool']
    }

    def __init__(self):
        Loggable.__init__(self)
        self.tracks = []
        self.selection = Selection()
        self.selection.connect("selection-changed", self._selectionChanged)
        self.timeline_objects = []
        self.duration = 0
        self.links = []
        # FIXME : What's the unit of dead_band ?
        self.dead_band = 10
        self.edges = TimelineEdges()
        self.property_trackers = {}

    def addTrack(self, track):
        """
        Add the track to the timeline.

        @param track: The track to add
        @type track: L{timeline.Track}
        @raises TimelineError: If the track is already in the timeline.
        """
        if track in self.tracks:
            raise TimelineError("Provided track already controlled by the timeline")

        self.tracks.append(track)
        self._updateDuration()
        track.connect('start-changed', self._trackDurationChangedCb)
        track.connect('duration-changed', self._trackDurationChangedCb)

        self.emit('track-added', track)

    def removeTrack(self, track, removeTrackObjects=True):
        """
        Remove the track from the timeline.

        @param track: The track to remove.
        @type track: L{timeline.Track}
        @param removeTrackObjects: If C{True}, clear the Track from its objects.
        @type removeTrackObjects: C{bool}
        @raises TimelineError: If the track isn't in the timeline.
        """
        try:
            self.tracks.remove(track)
        except ValueError:
            raise TimelineError("Track not controlled by this Timeline")

        if removeTrackObjects:
            track.removeAllTrackObjects()

        self.emit('track-removed', track)

    def _selectionChanged(self, selection):
        self.emit("selection-changed")

    def _trackStartChangedCb(self, track, duration):
        self._updateDuration()

    def _trackDurationChangedCb(self, track, duration):
        self._updateDuration()

    def _updateDuration(self):
        duration = max([track.start + track.duration for track in self.tracks])
        if duration != self.duration:
            self.duration = duration
            self.emit('duration-changed', duration)

    def addTimelineObject(self, obj):
        """
        Add the TimelineObject to the Timeline.

        @param obj: The object to add
        @type obj: L{TimelineObject}
        @raises TimelineError: if the object is used in another Timeline.
        """
        self.debug("obj:%r", obj)
        if obj.timeline is not None:
            raise TimelineError("TimelineObject already controlled by another Timeline")

        # FIXME : wait... what's wrong with having empty timeline objects ??
        # And even if it was.. this shouldn't be checked here imho.
        if not obj.track_objects:
            raise TimelineError("TimelineObject doesn't have any TrackObject (THIS IS A VERY DUBIOUS CHECK, WE SHOULD ACCEPT THIS)")

        self._connectToTimelineObject(obj)

        start_insort_right(self.timeline_objects, obj)
        obj.timeline = self

        self.edges.addTimelineObject(obj)

        self.emit("timeline-object-added", obj)

    def removeTimelineObject(self, obj, deep=False):
        """
        Remove the given object from the Timeline.

        @param obj: The object to remove
        @type obj: L{TimelineObject}
        @param deep: If C{True}, remove the L{TrackObject}s associated to the object.
        @type deep: C{bool}
        @raises TimelineError: If the object doesn't belong to the timeline.
        """
        try:
            self.timeline_objects.remove(obj)
        except ValueError:
            raise TimelineError("TimelineObject not controlled by this Timeline")

        if obj.link is not None:
            obj.link.removeTimelineObject(obj)

        self._disconnectFromTimelineObject(obj)

        obj.timeline = None

        self.edges.removeTimelineObject(obj)

        self.emit("timeline-object-removed", obj)

        if deep:
            for track_object in obj.track_objects:
                track = track_object.track
                track.removeTrackObject(track_object)

    def removeFactory(self, factory):
        """Remove every instance factory in the timeline
        @param factory: the factory to remove from the timeline
        """
        objs = [obj for obj in self.timeline_objects if obj.factory is
            factory]
        for obj in objs:
            self.removeTimelineObject(obj, deep=True)

    def _timelineObjectStartChangedCb(self, timeline_object, start):
        self.timeline_objects.remove(timeline_object)
        start_insort_right(self.timeline_objects, timeline_object)

    def _timelineObjectDurationChangedCb(self, timeline_object, duration):
        pass

    def _connectToTimelineObject(self, timeline_object):
        timeline_object.connect('start-changed',
                self._timelineObjectStartChangedCb)
        timeline_object.connect('duration-changed',
                self._timelineObjectDurationChangedCb)

    def _disconnectFromTimelineObject(self, timeline_object):
        timeline_object.disconnect_by_function(self._timelineObjectStartChangedCb)
        timeline_object.disconnect_by_function(self._timelineObjectDurationChangedCb)

    # FIXME : shouldn't this be made more generic (i.e. not specific to source factories) ?
    # FIXME : Maybe it should be up to the ObjectFactory to create the TimelineObject since
    #    it would know the exact type of TimelineObject to create with what properties (essential
    #    for being able to create Groups and importing Timelines within Timelines.
    def addSourceFactory(self, factory, stream_map=None, strict=False):
        """
        Creates a TimelineObject for the given SourceFactory and adds it to the timeline.

        @param factory: The factory to add.
        @type factory: L{SourceFactory}
        @param stream_map: A mapping of factory streams to track streams.
        @type stream_map: C{dict} of MultimediaStream => MultimediaStream
        @param strict: If C{True} only add the factory if an exact stream mapping can be
        calculated.
        @type strict: C{bool}
        @raises TimelineError: if C{strict} is True and no exact mapping could be calculated.
        """
        self.debug("factory:%r", factory)
        output_streams = factory.getOutputStreams()
        if not output_streams:
            raise TimelineError("SourceFactory doesn't provide any Output Streams")

        if stream_map is None:
            stream_map = self._getSourceFactoryStreamMap(factory)
            if len(stream_map) < len(output_streams):
                # we couldn't assign each stream to a track automatically,
                # error out and require the caller to pass a stream_map
                self.error("Couldn't find a complete stream mapping (self:%d < factory:%d)",
                           len(stream_map), len(output_streams))
                if strict:
                    raise TimelineError("Couldn't map all streams to available Tracks")

        timeline_object = TimelineObject(factory)
        start = 0
        for stream, track in stream_map.iteritems():
            self.debug( "Stream: " + str(stream) + "\nTrack :" + str(track) +\
                        "\n Track duration:" + str(track.duration))
            start = max(start, track.duration)
            track_object = SourceTrackObject(factory, stream)
            track.addTrackObject(track_object)
            timeline_object.addTrackObject(track_object)

        timeline_object.start = start
        self.addTimelineObject(timeline_object)
        return timeline_object

    def addEffectFactoryOnObject(self, factory, time=0, priority=0, timeline_objects=None):
        """
        Add effectTraks corresponding to the effect from the factory to the corresponding
        L{TimelineObject}s on the timeline

        @param factory: The EffectFactory to add.
        @type factory: L{EffectFactory}
        @param time: Where the effect should be added, if time = -1, we add the effect
                     to the whole layer
        @type time: C{int}
        @priority: An aproximation of the clip we want the effect to be added to.
        @type priority: C{int}
        @raises TimelineError: if the factory doesn't have input or output streams
        @returns: A list of L{TimelineObject}, L{TrackObject} tuples
        """
        #Note: We should maybe be able to handle several streams for effects which
        #are actually working on audio/video streams
        self.debug("factory:%r", factory)

        output_stream = factory.getOutputStreams()
        if not output_stream:
            raise TimelineError()
        output_stream = output_stream[0]

        input_stream = factory.getInputStreams()
        if not input_stream:
            raise TimelineError()
        input_stream = input_stream[0]

        track = self.getEffectTrack(factory)
        if track is None:
          raise TimelineError()

        listTimelineObjectTrackObject = []
        track_object = TrackEffect(factory, input_stream)
        track_object.makeBin()

        if not timeline_objects:
            timeline_objects = self.getObjsToAddEffectTo(time, priority)

        for obj in timeline_objects:
            copy_track_obj = track_object.copy()
            track.addTrackObject(copy_track_obj)
            copy_track_obj.start = obj.start
            copy_track_obj.duration = obj.duration
            copy_track_obj.media_duration = obj.media_duration
            obj.addTrackObject(copy_track_obj)
            listTimelineObjectTrackObject.append((obj, copy_track_obj))

        self.debug("%s", ["TimelineObject %s => Track object: %s |"\
                           %(listTo[0], listTo[1])\
                           for listTo in listTimelineObjectTrackObject])
        return listTimelineObjectTrackObject

    def getEffectTrack(self, factory):
        return [track for track in self.tracks if type (track.stream) == type(factory.input_streams[0])][0]

    def _getSourceFactoryStreamMap(self, factory):
        # track.stream -> track
        track_stream_to_track_map = dict((track.stream, track)
                for track in self.tracks)

        # output_stream -> track.stream
        output_stream_to_track_stream_map = \
                match_stream_groups_map(factory.output_streams,
                        [track.stream for track in self.tracks])

        # output_stream -> track (result)
        output_stream_to_track_map = {}
        for stream, track_stream in output_stream_to_track_stream_map.iteritems():
            output_stream_to_track_map[stream] = \
                    track_stream_to_track_map[track_stream]

        return output_stream_to_track_map

    def getPreviousTimelineObject(self, obj, priority=-1, tracks=None):
        if tracks is None:
            skip = None
        else:
            def skipIfNotInTheseTracks(timeline_object):
                return self._skipIfNotInTracks(timeline_object, tracks)
            skip = skipIfNotInTheseTracks

        prev = getPreviousObject(obj, self.timeline_objects,
                priority, skip=skip)

        if prev is None:
            raise TimelineError("no previous timeline object", obj)

        return prev

    def getNextTimelineObject(self, obj, priority=-1, tracks=None):
        if tracks is None:
            skip = None
        else:
            def skipIfNotInTheseTracks(timeline_object):
                return self._skipIfNotInTracks(timeline_object, tracks)
            skip = skipIfNotInTheseTracks

        next = getNextObject(obj, self.timeline_objects, priority, skip)
        if next is None:
            raise TimelineError("no next timeline object", obj)

        return next

    def _skipIfNotInTracks(self, timeline_object, tracks):
        timeline_object_tracks = set(track_object.track for track_object in
                timeline_object.track_objects)

        return not tracks.intersection(timeline_object_tracks)

    def setSelectionToObj(self, obj, mode):
        """
        Update the timeline's selection with the given object and mode.

        @see: L{Selection.setToObj}
        """
        if mode == SELECT_BETWEEN:
            if self.selection.last_single_obj:
                last = self.selection.last_single_obj
                earliest = min(last.start, obj.start)
                latest = max(last.start + last.duration,
                    obj.start + obj.duration)
                min_priority = min(last.priority, obj.priority)
                max_priority = max(last.priority, obj.priority)
                objs = self.getObjsInRegion(earliest, latest,
                    min_priority, max_priority)
                self.setSelectionTo(objs, SELECT)
                return

        self.selection.setToObj(obj, mode)

    def setSelectionTo(self, selection, mode):
        """
        Update the timeline's selection with the given selection and mode.

        @see: L{Selection.setSelection}
        """
        self.selection.setSelection(selection, mode)

    def linkSelection(self):
        """
        Link the currently selected timeline objects.
        """
        if len(self.selection) < 2:
            return

        # list of links that we joined and so need to be removed
        old_links = []

        # we start with a new empty link and we expand it as we find new objects
        # and links
        link = Link()
        for timeline_object in self.selection:
            if timeline_object.link is not None:
                old_links.append(timeline_object.link)

                link = link.join(timeline_object.link)
            else:
                link.addTimelineObject(timeline_object)

        for old_link in old_links:
            self.links.remove(old_link)

        self.links.append(link)
        self.emit("selection-changed")

    def unlinkSelection(self):
        """
        Unlink the currently selected timeline objects.
        """
        empty_links = set()
        for timeline_object in self.selection:
            if timeline_object.link is None:
                continue

            link = timeline_object.link
            link.removeTimelineObject(timeline_object)
            if not link.timeline_objects:
                empty_links.add(link)

        for link in empty_links:
            self.links.remove(link)
        self.emit("selection-changed")

    def groupSelection(self):
        if len(self.selection.selected) < 2:
            return

        # FIXME: pass a proper factory
        new_timeline_object = TimelineObject(factory=None)

        tracks = []
        for timeline_object in self.selection.selected:
            for track_object in timeline_object.track_objects:
                new_track_object = track_object.copy()
                tracks.append(track_object.track)
                new_timeline_object.addTrackObject(new_track_object)

        self.addTimelineObject(new_timeline_object)

        old_track_objects = []
        for timeline_object in list(self.selection.selected):
            old_track_objects.extend(timeline_object.track_objects)
            self.removeTimelineObject(timeline_object, deep=True)

        self.selection.setSelection(old_track_objects, UNSELECT)
        self.selection.setSelection(new_timeline_object.track_objects, SELECT_ADD)

    def ungroupSelection(self):
        new_track_objects = []
        for timeline_object in list(self.selection.selected):
            if len(timeline_object.track_objects) == 1:
                continue

            self.selection.setSelection(timeline_object.track_objects, UNSELECT)

            for track_object in list(timeline_object.track_objects):
                new_track_object = track_object.copy()
                new_timeline_object = TimelineObject(new_track_object.factory)
                new_timeline_object.addTrackObject(new_track_object)
                self.addTimelineObject(new_timeline_object)
                new_track_objects.extend(new_timeline_object.track_objects)

            self.removeTimelineObject(timeline_object, deep=True)

        self.selection.setSelection(new_track_objects, SELECT_ADD)

    def deleteSelection(self):
        """
        Removes all the currently selected L{TimelineObject}s from the Timeline.
        """
        self.unlinkSelection()
        for timeline_object in self.selection:
            self.removeTimelineObject(timeline_object, deep=True)
        self.selection.setSelection(set([]), SELECT)

    def split(self, time):
        """
        Splits objects under the playehad. If the selection is not empty, the
        split only applies to selected clips. Otherwise it applies to all
        clips"""
        objs = set(self.getObjsAtTime(time))
        if len(self.selection):
            objs = self.selection.selected.intersection(objs)
        for obj in objs:
            obj.split(time)

    def rebuildEdges(self):
        self.edges = TimelineEdges()
        for timeline_object in self.timeline_objects:
            self.edges.addTimelineObject(timeline_object)

    def snapToEdge(self, start, end=None):
        """
        Snaps the given start/end value to the closest edge if it is within
        the timeline's dead_band.

        @param start: The start position to snap.
        @param end: The stop position to snap.
        @returns: The snapped value if within the dead_band.
        """
        edge, diff = self.edges.snapToEdge(start, end)

        if self.dead_band != -1 and diff <= self.dead_band:
            return edge

        return start

    def disableUpdates(self):
        """
        Block internal updates. Use this when doing more than one consecutive
        modification in the pipeline.
        """
        for track in self.tracks:
            track.disableUpdates()

        self.edges.disableUpdates()

        self.emit("disable-updates", True)

    def enableUpdates(self):
        """
        Unblock internal updates. Use this after calling L{disableUpdates}.
        """

        for track in self.tracks:
            track.enableUpdates()

        self.edges.enableUpdates()

        self.emit("disable-updates", False)

    def getObjsAtTime(self, time):
        objects = []
        for obj in self.timeline_objects:
            if obj.start < time:
                if (obj.start + obj.duration) > time:
                    objects.append(obj)
            else:
                break
        return objects

    def getObjsAfterObj(self, obj):
        return self.getObjsAfterTime(obj.start + obj.duration)

    def getObjsAfterTime(self, target):
        objects = []
        for i in range(0, len(self.timeline_objects)):
            if self.timeline_objects[i].start >= target:
                objects.extend(self.timeline_objects[i:])
                break
        return objects

    def getObjsBeforeObj(self, obj):
        return self.getObjsBeforeTime(obj.start)

    def getObjsBeforeTime(self, target):
        objects = []
        for obj in self.timeline_objects:
            if obj.start > target:
                break
            elif obj.start + obj.duration <= target:
                objects.append(obj)
        return objects

    def getObjsInRegion(self, start, end, min_priority=0,
        max_priority=4294967295L):
        objects = []
        for obj in self.timeline_objects:
            if obj.start >= start:
                if ((obj.start + obj.duration) <= end and
                obj.priority >= min_priority and
                obj.priority <= max_priority):
                    objects.append(obj)
            elif obj.start > end:
                break
        return objects

    def getPrevKeyframe(self, time):
        tl_objs = []

        # Exclude objects that start after current position.
        for obj in self.timeline_objects:
                tl_objs.append(obj)
                if obj.start > time:
                    break

        keyframe_positions = self._getKeyframePositions(tl_objs)
        for n in range(len(keyframe_positions) -1, -1, -1):
            if keyframe_positions[n] < time:
                return keyframe_positions[n]
        return None

    def getNextKeyframe(self, time):
        tl_objs = []

        # Include from first object whose end is after the current
        # position onward.
        for obj in self.timeline_objects:
            if (obj.start + obj.duration) > time:
                n = self.timeline_objects.index(obj)
                tl_objs.extend(self.timeline_objects[n:])
                break

        keyframe_positions = self._getKeyframePositions(tl_objs)
        for n in range(0, len(keyframe_positions)):
                if keyframe_positions[n] > time:
                    return keyframe_positions[n]

        return None

    def _getKeyframePositions(self, timeline_objects):
        keyframe_positions = set([])
        for tl_obj in timeline_objects:
            first_track = True
            for track_obj in tl_obj.track_objects:
                start = track_obj.start
                in_point = track_obj.in_point
                if first_track:
                    keyframe_positions.add(start)
                    keyframe_positions.add(start + track_obj.duration)
                    first_track = False

                interpolators = track_obj.getInterpolators()
                for value in interpolators:
                    interpolator = track_obj.getInterpolator(value)
                    keyframes = interpolator.getInteriorKeyframes()
                    for kf in keyframes:
                        position_in_obj = kf.getTime() + start - in_point
                        keyframe_positions.add(position_in_obj)
        keyframe_positions = list(keyframe_positions)
        keyframe_positions.sort()
        return keyframe_positions

    def getObjsToAddEffectTo(self, point, priority):
        timeline_objects = []
        if point == -1:
            for obj in self.timeline_objects:
                if obj.priority == priority:
                    timeline_objects.append(obj)
        else:
            for obj in self.timeline_objects:
                if (obj.start <= point and
                    point <= (obj.start + obj.duration) and\
                    obj.priority == priority):
                    timeline_objects.append(obj)

        return timeline_objects
