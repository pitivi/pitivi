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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import ges

from pitivi.utils import infinity

#from pitivi.timeline.align import AutoAligner

# Selection modes
SELECT = 0
"""Set the selection to the given set."""
UNSELECT = 1
"""Remove the given set from the selection."""
SELECT_ADD = 2
"""Extend the selection with the given set"""
SELECT_BETWEEN = 3
"""Select a range of clips"""


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
        self._snap = False
        self._mode = self.DEFAULT
        self._last_position = focus.get_property("start")
        self._last_priority = focus.get_property("priority")

        #self.timeline.disableUpdates()

    def _getOffsets(self, start_offset, priority_offset, timeline_objects):
        offsets = {}
        for timeline_object in timeline_objects:
            offsets[timeline_object] = (timeline_object.get_property("start") - start_offset,
                        timeline_object.get_property("priority") - priority_offset)

        return offsets

    def _getTimelineObjectValues(self, timeline_object):
        return (timeline_object.get_property("start"), timeline_object.get_property("duration"),
                timeline_object.get_property("in_point"),
                timeline_object.get_property("priority"))

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
        return
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
        self.layersList = []
        for obj in all_objects:
            if isinstance(obj, ges.TrackObject):
                timeline_object = obj.get_timeline_object()
                self.tracks.add(obj.get_track())
            else:
                timeline_object = obj
                timeline_object_tracks = set(track_object.get_track() for track_object
                        in timeline_object.get_track_objects())
                self.tracks.update(timeline_object_tracks)

            self.timeline_objects.add(timeline_object)

            self.default_originals[timeline_object] = \
                    self._getTimelineObjectValues(timeline_object)

            earliest = min(earliest, timeline_object.get_property("start"))
            latest = max(latest,
                    timeline_object.get_property("start") + timeline_object.get_property("duration"))
            min_priority = min(min_priority, timeline_object.get_property("priority"))

        self.offsets = self._getOffsets(self.focus.get_property("start"), self.focus.get_property("priority"),
                self.timeline_objects)

        self.min_priority = focus.get_property("priority") - min_priority
        self.min_position = focus.get_property("start") - earliest

        # get the span over all clips for edge snapping
        self.default_span = latest - earliest

        #ripple = timeline.getObjsAfterTime(latest)
        #self.ripple_offsets = self._getOffsets(self.focus.get_property("start"),
            #self.focus.get_property("priority"), ripple)

        # get the span over all clips for ripple editing
        #for timeline_object in ripple:
            #latest = max(latest, timeline_object.get_property("start") +
                #timeline_object.get_property("duration"))
        #self.ripple_span = latest - earliest

        # save default values
        #self.ripple_originals = self._saveValues(ripple)

        #self.timeline_objects_plus_ripple = set(self.timeline_objects)
        #self.timeline_objects_plus_ripple.update(ripple)

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

    def finish(self):

        if isinstance(self.focus, ges.TrackObject):
            focus_timeline_object = self.focus.get_timeline_object()
        else:
            focus_timeline_object = self.focus
        initial_position = self.default_originals[focus_timeline_object][0]
        initial_priority = self.default_originals[focus_timeline_object][-1]

        final_priority = self.focus.get_property("priority")
        final_position = self.focus.get_property("start")

        priority = final_priority

        # special case for transitions. Allow a single object to overlap
        # either of its two neighbors if it overlaps no other objects
        if len(self.timeline_objects) == 1:
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

    def _defaultTo(self, position, priority):
        if self._snap:
            position = self.timeline.snapToEdge(position,
                position + self.default_span)

        priority = max(self.min_priority, priority)
        obj = self.focus
        if isinstance(self.focus, ges.TrackFileSource):
            obj = self.focus.get_timeline_object()
        if obj.get_layer().get_property("priority") != priority:
            origin_layer = obj.get_layer()
            moved = False
            for layer in self.timeline.get_layers():
                if layer.get_property("priority") == priority:
                    obj.move_to_layer(layer)
                    moved = True
            if not moved:
                layer = ges.TimelineLayer()
                layer.set_property("auto-transition", True)
                self.timeline.add_layer(layer)
                layer.set_property("priority", priority)
                obj.move_to_layer(layer)
                self.layersList.append(layer)
        if position < 0:
            position = 0
        self.focus.set_property("start", long(position))

        for obj, (s_offset, p_offset) in self.offsets.iteritems():
            obj.set_property("start", long(position + s_offset))
            #obj.get_layer().set_property ("priority", priority + p_offset)

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
        #self.adjacent = timeline.edges.getObjsAdjacentToStart(focus)
        #self.adjacent_originals = self._saveValues(self.adjacent)
        self.tracks = set([])
        #if isinstance(self.focus, TrackObject):
            #focus_timeline_object = self.focus.timeline_object
            #self.tracks.add(self.focus.track)
        #else:
        if isinstance(self.focus, ges.TrackFileSource):
            focus_timeline_object = self.focus
            self.tracks.add(focus.get_track())
        else:
            focus_timeline_object = self.focus
            tracks = set(track_object.get_track() for track_object in
                        focus.get_track_objects())
            self.tracks.update(tracks)
        self.focus_timeline_object = focus_timeline_object
        self.default_originals = self._saveValues([focus_timeline_object])
        #ripple = self.timeline.getObjsBeforeTime(focus.start)
        #assert not focus.timeline_object in ripple or focus.duration == 0
        #self.ripple_originals = self._saveValues(ripple)
        #self.ripple_offsets = self._getOffsets(focus.start, focus.priority,
            #ripple)
        #if ripple:
            #self.ripple_min = focus.start - min((obj.start for obj in ripple))
        #else:
            #self.ripple_min = 0

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
        start = self.focus.get_property("start")
        earliest = max(0, position - self.focus.starting_start)
        self.focus.set_property("in-point", earliest)
        self.focus.set_property("start", position)
        self.focus.set_property("duration", self.focus.get_property("max-duration") - self.focus.get_property("in-point"))
        return position, priority

    def finish(self):
        initial_position = self.default_originals[self.focus_timeline_object][0]
        self.focus.starting_start = self.focus.get_property("start")
        timeline_objects = [self.focus_timeline_object]
        EditingContext.finish(self)
        return
        left_gap, right_gap = self._getGapsAtPriority(self.focus.priority,
                timeline_objects, self.tracks)

        if left_gap is invalid_gap:
            self._defaultTo(initial_position, self.focus.priority)
            left_gap, right_gap = Gap.findAroundObject(self.focus_timeline_object)
            position = initial_position - left_gap.duration
            self._defaultTo(position, self.focus.priority)


class TrimEndContext(EditingContext):
    def __init__(self, timeline, focus, other):
        EditingContext.__init__(self, timeline, focus, other)
        #self.adjacent = timeline.edges.getObjsAdjacentToEnd(focus)
        #self.adjacent_originals = self._saveValues(self.adjacent)
        self.tracks = set([])
        if isinstance(self.focus, ges.TrackFileSource):
            focus_timeline_object = self.focus
            self.tracks.add(focus.get_track())
        else:
            focus_timeline_object = self.focus
            tracks = set(track_object.get_track() for track_object in
                    focus.get_track_objects())
            self.tracks.update(tracks)
        self.focus_timeline_object = focus_timeline_object
        self.default_originals = self._saveValues([focus_timeline_object])

        reference = focus.get_property("start") + focus.get_property("duration")
        #ripple = self.timeline.getObjsAfterTime(reference)

        #self.ripple_originals = self._saveValues(ripple)
        #self.ripple_offsets = self._getOffsets(reference, self.focus.get_priority(),
            #ripple)

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
        duration = max(0, position - self.focus.get_property("start"))
        duration = min(duration, self.focus.max_duration)
        self.focus.set_property("duration", duration)

        return position, priority

    def finish(self):
        EditingContext.finish(self)

        initial_position, initial_duration = \
                self.default_originals[self.focus_timeline_object][0:2]
        absolute_initial_duration = initial_position + initial_duration

        timeline_objects = [self.focus_timeline_object]
        return
        left_gap, right_gap = self._getGapsAtPriority(self.focus.priority,
                timeline_objects, self.tracks)

        if right_gap is invalid_gap:
            self._defaultTo(absolute_initial_duration, self.focus.priority)
            left_gap, right_gap = Gap.findAroundObject(self.focus_timeline_object)
            duration = absolute_initial_duration + right_gap.duration
            self._defaultTo(duration, self.focus.priority)
