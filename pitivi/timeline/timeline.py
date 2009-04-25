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
from pitivi.log.loggable import Loggable
from pitivi.utils import UNKNOWN_DURATION, closest_item, PropertyChangeTracker
from pitivi.timeline.track import Track, SourceTrackObject, TrackError
from bisect import bisect_right

SELECT = 0
SELECT_ADD = 2
UNSELECT = 1

class TimelineError(Exception):
    pass

class TimelineObject(Signallable, Loggable):
    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'in-point-changed': ['in-point'],
        'out-point-changed': ['in-point'],
        'media-duration-changed': ['media-duration'],
        'priority-changed': ['priority'],
        'selected-changed' : ['state'],
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
        other.track_objects = [track_object.copy() for track_object in
                self.track_objects]

        return other

    def _getStart(self):
        if not self.track_objects:
            return self.DEFAULT_START

        return self.track_objects[0].start

    def setStart(self, position, snap=False):
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

    start = property(_getStart, setStart)

    def _getDuration(self):
        if not self.track_objects:
            return self.DEFAULT_DURATION

        return self.track_objects[0].duration

    def setDuration(self, position, snap=False, set_media_stop=True):
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

    duration = property(_getDuration, setDuration)

    def _getInPoint(self):
        if not self.track_objects:
            return self.DEFAULT_IN_POINT

        return self.track_objects[0].in_point

    def setInPoint(self, position, snap=False):
        if not self.track_objects:
            raise TimelineError()

        for track_object in self.track_objects:
            track_object.setObjectInPoint(position)

        self.emit('in-point-changed', position)

    in_point = property(_getInPoint, setInPoint)

    def _getOutPoint(self):
        if not self.track_objects:
            return self.DEFAULT_IN_POINT

        return self.track_objects[0].out_point

    out_point = property(_getOutPoint)

    def _getMediaDuration(self):
        if not self.track_objects:
            return self.DEFAULT_OUT_POINT

        return self.track_objects[0].media_duration

    def setMediaDuration(self, position, snap=False):
        if not self.track_objects:
            raise TimelineError()

        for track_object in self.track_objects:
            track_object.setObjectMediaDuration(position)

        self.emit('media-duration-changed', position)

    media_duration = property(_getMediaDuration, setMediaDuration)

    def _getPriority(self):
        if not self.track_objects:
            return self.DEFAULT_PRIORITY

        return self.track_objects[0].priority

    def setPriority(self, priority):
        if not self.track_objects:
            raise TimelineError()

        for track_object in self.track_objects:
            track_object.setObjectPriority(priority)

        self.emit('priority-changed', priority)

    priority = property(_getPriority, setPriority)

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

    selected = property(_getSelected, setSelected)

    def trimStart(self, position, snap=False):
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
        if not self.track_objects:
            raise TimelineError()

        other = self.copy()
        # ditch track objects. This is a bit weird, will be more clear when we
        # use other uses of TimelineObject.copy
        other.track_objects = []

        for track_object in self.track_objects:
            try:
                other_track_object = track_object.splitObject(position)
            except TrackError, e:
                # FIXME: hallo exception hierarchy?
                raise TimelineError(str(e))

            other.addTrackObject(other_track_object)
            track_object.track.addTrackObject(other_track_object)

        if self.timeline is not None:
            # if self is not yet in a timeline, the caller needs to add "other"
            # as well when it adds self
            self.timeline.addTimelineObject(other)

        self.emit('duration-changed', self.duration)

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

class Selection(Signallable):

    __signals__ = {
        "selection-changed" : []
    }

    def __init__(self):
        self.selected = set([])

    def setToObj(self, obj, mode):
        self.setTo(set([obj]), mode)

    def setTo(self, selection, mode):
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

        self.emit("selection-changed")

    def getSelectedTrackObjs(self):
        objects = []
        for timeline_object in self.selected:
            objects.extend(timeline_object.track_objects)

        return set(objects)

    def __len__(self):
        return len(self.selected)

    def __iter__(self):
        return iter(self.selected)

class LinkEntry(object):
    def __init__(self, start, duration):
        self.start = start
        self.duration = duration

class LinkPropertyChangeTracker(PropertyChangeTracker):
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

        tracker = LinkPropertyChangeTracker(timeline_object)
        self.property_trackers[timeline_object] = tracker

        tracker.connect('start-changed', self._startChangedCb)

        # FIXME: cycle
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
        tracker.disconnect_by_function(self._startChangedCb)

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

class TimelineEdges(object):
    def __init__(self):
        self.edges = []

    def addTimelineObject(self, timeline_object):
        self.addStartEnd(timeline_object.start,
                timeline_object.start + timeline_object.duration)

    def removeTimelineObject(self, timeline_object):
        self.removeStartEnd(timeline_object.start,
                timeline_object.start + timeline_object.duration)

    def addStartEnd(self, start, end=None):
        index = bisect_right(self.edges, start)
        self.edges.insert(index, start)
        if end is not None:
            index = bisect_right(self.edges, end, index)
            self.edges.insert(index, end)

    def removeStartEnd(self, start, end=None):
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
        closest, diff, index = closest_item(self.edges, position)
        return self.edges[max(0, index - 2)], self.edges[min(
            len(self.edges) - 1, index + 1)]


class Timeline(Signallable, Loggable):
    __signals__ = {
        'duration-changed': ['duration'],
        'track-added': ['track'],
        'track-removed': ['track'],
        'selection-changed': [],
    }

    def __init__(self):
        Loggable.__init__(self)
        self.tracks = []
        self.selection = Selection()
        self.selection.connect("selection-changed", self._selectionChanged)
        self.timeline_objects = []
        self.duration = 0
        self.links = []
        self.dead_band = 10
        self.edges = TimelineEdges()
        self.property_trackers = {}

    def addTrack(self, track):
        if track in self.tracks:
            raise TimelineError()

        self.tracks.append(track)
        self._updateDuration()
        track.connect('start-changed', self._trackDurationChangedCb)
        track.connect('duration-changed', self._trackDurationChangedCb)

        self.emit('track-added', track)

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

    def removeTrack(self, track, removeTrackObjects=True):
        try:
            self.tracks.remove(track)
        except ValueError:
            raise TimelineError()

        if removeTrackObjects:
            track.removeAllTrackObjects()

        self.emit('track-removed', track)

    def addTimelineObject(self, obj):
        self.debug("obj:%r", obj)
        if obj.timeline is not None:
            raise TimelineError()

        if not obj.track_objects:
            raise TimelineError()

        self.timeline_objects.append(obj)
        obj.timeline = self

        self.edges.addTimelineObject(obj)

    def removeTimelineObject(self, obj, deep=False):
        try:
            self.timeline_objects.remove(obj)
        except ValueError:
            raise TimelineError()

        if obj.link is not None:
            obj.link.removeTimelineObject(obj)

        obj.timeline = None
        self.rebuildEdges()
        #self.edges.removeTimelineObject(obj)

        if deep:
            for track_object in obj.track_objects:
                track = track_object.track
                track.removeTrackObject(track_object)

    def addSourceFactory(self, factory, stream_map=None, strict=False):
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

    def getSourceFactoryStreamMap(self, factory):
        self.debug("factory:%r", factory)
        mapped_tracks = []
        timeline_object = TimelineObject(factory)

        stream_map = {}
        output_streams = factory.getOutputStreams()
        for output_stream in output_streams:
            track = self._getTrackForFactoryStream(factory,
                    output_stream, mapped_tracks)
            if track is None:
                self.debug("no track found for stream %s", output_stream)
                # couldn't find a track for this stream
                continue

            stream_map[output_stream] = track

            # we don't want to reuse the same track for different streams coming
            # from the same source
            mapped_tracks.append(track)

        return stream_map

    def _getTrackForFactoryStream(self, factory, stream, mapped_tracks):
        self.debug("factory:%r, stream:%s", factory, stream)
        for track in self.tracks:
            if track not in mapped_tracks:
                self.debug("track.stream:%s", track.stream)
                if track.stream.isCompatible(stream):
                    return track
                else:
                    self.debug("Stream not compatible")
            else:
                self.debug("Track already present in mapped_tracks")

        return None

    def setSelectionToObj(self, obj, mode):
        self.selection.setToObj(obj, mode)

    def setSelectionTo(self, selection, mode):
        self.selection.setTo(selection, mode)

    def linkSelection(self):
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
        self.unlinkSelection()
        for timeline_object in self.selection:
            self.removeTimelineObject(timeline_object, deep=True)
        self.selection.setTo(set([]), SELECT)

    def rebuildEdges(self):
        self.edges = TimelineEdges()
        for timeline_object in self.timeline_objects:
            self.edges.addTimelineObject(timeline_object)

    def snapToEdge(self, start, end=None):
        edge, diff = self.edges.snapToEdge(start, end)

        if self.dead_band != -1 and diff <= self.dead_band:
            return edge

        return start

    def disableUpdates(self):
        for track in self.tracks:
            track.disableUpdates()

    def enableUpdates(self):
        for track in self.tracks:
            track.enableUpdates()
