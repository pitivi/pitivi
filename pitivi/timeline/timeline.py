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

from bisect import bisect_right

from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.utils import UNKNOWN_DURATION, closest_item, PropertyChangeTracker
from pitivi.timeline.track import SourceTrackObject, TrackError
from pitivi.stream import match_stream_groups_map

# Selection modes
SELECT = 0
"""Set the selection to the given set."""
UNSELECT = 1
"""Remove the given set from the selection."""
SELECT_ADD = 1
"""Extend the selection with the given set"""

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

    def copy(self):
        cls = self.__class__
        other = cls(self.factory)
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
            raise TimelineError()

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

    def setDuration(self, position, snap=False, set_media_stop=True):
        """
        Sets the duration of the object.

        If snap is L{True}, then L{position} will be modified if it is close
        to a timeline edge.

        If set_media_stop is L{False} then the change will not be propagated
        to the C{TrackObject}s this object controls.

        @param position: The duration in nanoseconds.
        @type position: L{long}
        @param snap: Whether to snap to the nearest edge or not.
        @type snap: L{bool}
        @param set_media_stop: propagate changes to track objects.
        @type set_media_stop: L{bool}
        @raises TimelineError: If the object doesn't control any C{TrackObject}s.
        """
        if not self.track_objects:
            raise TimelineError()

        if snap:
            position = self.timeline.snapToEdge(position)

        trimmed_start = self.track_objects[0].trimmed_start
        position = min(position, self.factory.duration - trimmed_start)

        for track_object in self.track_objects:
            track_object.setObjectDuration(position)
            if set_media_stop:
                track_object.setObjectMediaDuration(position)

        self.emit('duration-changed', position)

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
            raise TimelineError()

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
            raise TimelineError()

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
            raise TimelineError()

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
            raise TimelineError()

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
            raise TimelineError()

        if position <= self.start or position >= self.start + self.duration:
            raise TimelineError("can't split at position %s")

        other = self.copy()
        if self.timeline is not None:
            # if self is not yet in a timeline, the caller needs to add "other"
            # as well when it adds self
            self.timeline.addTimelineObject(other)

        self.setDuration(position - self.start, set_media_stop=True)
        other.trimStart(position)

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
            raise TimelineError()

        if obj in self.track_objects:
            # FIXME : couldn't we just silently return ?
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

            # FIXME : We really should be able to support controlling more than
            # one trackobject with offseted start/duration/in-/out-point/priorities
            existing_track_object = self.track_objects[0]
            if obj.start != existing_track_object.start or \
                    obj.duration != existing_track_object.duration:
                raise TimelineError()

        # FIXME: cycle
        obj.timeline_object = self
        self.track_objects.append(obj)

        self.emit("track-object-added", obj)

    def removeTrackObject(self, obj):
        """
        Remove the given object from the list of controlled C{TrackObject}.

        @param obj: The Track Object to remove.
        @type obj: C{TrackObject}
        @raises TimelineError: If the Track object isn't controlled by this TimelineObject.
        """
        if obj.track is None:
            raise TimelineError()

        try:
            self.track_objects.remove(obj)
            obj.timeline_object = None
        except ValueError:
            raise TimelineError()

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

    def setToObj(self, obj, mode):
        """
        Convenience method for calling L{setTo} with a single L{TimelineObject}

        @see: L{setTo}
        """
        self.setTo(set([obj]), mode)

    def addTimelineObject(self, timeline_object):
        """
        Add the given timeline_object to the selection.

        @param timeline_object: The object to add
        @type timeline_object: L{TimelineObject}
        @raises TimelineError: If the object is already controlled by this
        Selection.
        """
        if timeline_object in self.timeline_objects:
            raise TimelineError()

    # FIXME : it took me 10 mins to understand what this method does... a more obvious
    # name would be better :)
    def setTo(self, selection, mode):
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
        # get the L{TrackObject}s for the given TimelineObjects
        selection = set([obj.timeline_object for obj in selection])
        old_selection = self.selected
        if mode == SELECT_ADD:
            selection = self.selected | selection
        elif mode == UNSELECT:
            selection = self.selected - selection
        self.selected = selection

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
            raise TimelineError()

        if timeline_object in self.timeline_objects:
            raise TimelineError()

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
            raise TimelineError()

        tracker = self.property_trackers.pop(timeline_object)
        tracker.disconnectFromObject(timeline_object)
        tracker.disconnect_by_function(self._startChangedCb)

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
class TimelineEdges(object):
    """
    Tracks start/stop values and offers convenience methods to find the
    closest value for a given position.
    """
    def __init__(self):
        self.edges = []

    def addTimelineObject(self, timeline_object):
        """
        Add this object's start/stop values to the edges.

        @param timeline_object: The object whose start/stop we want to track.
        @type timeline_object: L{TimelineObject}
        """
        self.addStartEnd(timeline_object.start,
                timeline_object.start + timeline_object.duration)

    def removeTimelineObject(self, timeline_object):
        """
        Remove this object's start/stop values from the edges.

        @param timeline_object: The object whose start/stop we no longer want
        to track.
        @type timeline_object: L{TimelineObject}
        """
        self.removeStartEnd(timeline_object.start,
                timeline_object.start + timeline_object.duration)

    def addStartEnd(self, start, end=None):
        """
        Add the given start/end values to the list of edges being tracked.

        @param start: A start position to track.
        @type start: L{long}
        @param end: A stop position to track.
        @type end: L{long}
        """
        index = bisect_right(self.edges, start)
        self.edges.insert(index, start)
        if end is not None:
            index = bisect_right(self.edges, end, index)
            self.edges.insert(index, end)

    def removeStartEnd(self, start, end=None):
        """
        Remove the given start/end values from the list of edges being tracked.

        @param start: A start position to stop tracking.
        @type start: L{long}
        @param end: A stop position to stop tracking.
        @type end: L{long}
        """
        if len(self.edges) == 0:
            raise TimelineError()

        val, diff, start_index = closest_item(self.edges, start)
        if val != start:
            raise TimelineError()

        if end is not None and len(self.edges) > 1:
            val, diff, end_index = closest_item(self.edges, end, start_index)
            if val != end:
                raise TimelineError()
        else:
            end_index = None

        del self.edges[start_index]
        if end_index is not None:
            del self.edges[end_index-1]

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
            raise TimelineError()

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
            raise TimelineError()

        # FIXME : wait... what's wrong with having empty timeline objects ??
        # And even if it was.. this shouldn't be checked here imho.
        if not obj.track_objects:
            raise TimelineError()

        self.timeline_objects.append(obj)
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
            raise TimelineError()

        if obj.link is not None:
            obj.link.removeTimelineObject(obj)

        obj.timeline = None
        self.rebuildEdges()
        #self.edges.removeTimelineObject(obj)

        self.emit("timeline-object-removed", obj)

        if deep:
            for track_object in obj.track_objects:
                track = track_object.track
                track.removeTrackObject(track_object)

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
            raise TimelineError()

        if stream_map is None:
            stream_map = self.getSourceFactoryStreamMap(factory)
            if len(stream_map) < len(output_streams):
                # we couldn't assign each stream to a track automatically,
                # error out and require the caller to pass a stream_map
                self.error("Couldn't find a complete stream mapping (self:%d < factory:%d)",
                           len(stream_map), len(output_streams))
                if strict:
                    raise TimelineError()

        timeline_object = TimelineObject(factory)
        start = 0
        for stream, track in stream_map.iteritems():
            start = max(start, track.duration)
            track_object = SourceTrackObject(factory, stream)
            track.addTrackObject(track_object)
            timeline_object.addTrackObject(track_object)

        timeline_object.start = start
        self.addTimelineObject(timeline_object)
        return timeline_object

    # FIXME : Shouldn't this be a private method ??
    def getSourceFactoryStreamMap(self, factory):
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

    def setSelectionToObj(self, obj, mode):
        """
        Update the timeline's selection with the given object and mode.

        @see: L{Selection.setToObj}
        """
        self.selection.setToObj(obj, mode)

    def setSelectionTo(self, selection, mode):
        """
        Update the timeline's selection with the given selection and mode.

        @see: L{Selection.setTo}
        """
        self.selection.setTo(selection, mode)

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

        for i, track_object in enumerate(new_timeline_object.track_objects):
            tracks[i].addTrackObject(track_object)

        self.addTimelineObject(new_timeline_object)

        old_track_objects = []
        for timeline_object in list(self.selection.selected):
            old_track_objects.extend(timeline_object.track_objects)
            self.removeTimelineObject(timeline_object, deep=True)

        self.selection.setTo(old_track_objects, UNSELECT)
        self.selection.setTo(new_timeline_object.track_objects, SELECT_ADD)

    def ungroupSelection(self):
        new_track_objects = []
        for timeline_object in list(self.selection.selected):
            if len(timeline_object.track_objects) == 1:
                continue

            self.selection.setTo(timeline_object.track_objects, UNSELECT)

            for track_object in list(timeline_object.track_objects):
                timeline_object.removeTrackObject(track_object)
                new_timeline_object = TimelineObject(track_object.factory)
                new_timeline_object.addTrackObject(track_object)
                self.addTimelineObject(new_timeline_object)
                new_track_objects.extend(new_timeline_object.track_objects)

            self.removeTimelineObject(timeline_object)

        self.selection.setTo(new_track_objects, SELECT_ADD)

    def deleteSelection(self):
        """
        Removes all the currently selected L{TimelineObject}s from the Timeline.
        """
        self.unlinkSelection()
        for timeline_object in self.selection:
            self.removeTimelineObject(timeline_object, deep=True)
        self.selection.setTo(set([]), SELECT)

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

        self.emit("disable-updates", True)

    def enableUpdates(self):
        """
        Unblock internal updates. Use this after calling L{disableUpdates}.
        """
        for track in self.tracks:
            track.enableUpdates()

        self.emit("disable-updates", False)
