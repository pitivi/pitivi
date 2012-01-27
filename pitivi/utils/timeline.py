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
import gtk
import gst

from pitivi.utils.misc import infinity
from pitivi.utils.loggable import Loggable
from pitivi.utils.signal import Signallable
from pitivi.utils.receiver import receiver, handler
from pitivi.utils.ui import Point

#from pitivi.utils.align import AutoAligner

# Selection modes
SELECT = 0
"""Set the selection to the given set."""
UNSELECT = 1
"""Remove the given set from the selection."""
SELECT_ADD = 2
"""Extend the selection with the given set"""
SELECT_BETWEEN = 3
"""Select a range of clips"""


#------------------------------------------------------------------------------#
#                          Timeline Object management helper                   #
class TimelineError(Exception):
    """Base Exception for errors happening in L{Timeline}s or L{TimelineObject}s"""
    pass


def previous_track_source(focus, layer, start):
    """
    Get the source before @start in @track
    """
    tckobjs = focus.get_track().get_objects()

    # tckobjs is in order, we want to iter in the reverse order
    #FIXME optimize this algotithm, probably using bisect
    for tckobj in reversed(tckobjs):
        tckstart = tckobj.get_start()
        tckduration = tckobj.get_duration()
        if tckobj != focus and \
                tckobj.get_timeline_object().get_layer() == layer and \
                (tckstart + tckduration < start or\
                (tckstart < start < tckstart + tckduration)) and \
                isinstance(tckobj, ges.TrackSource):
            return tckobj
    return None


def next_track_source(focus, layer, start, duration):
    """
    Get the source before @start in @track
    """
    tckobjs = focus.get_track().get_objects()
    end = start + duration

    #FIXME optimize this algotithm, probably using bisect
    for tckobj in tckobjs:
        tckstart = tckobj.get_start()
        tckduration = tckobj.get_duration()
        if tckobj != focus and \
                tckobj.get_timeline_object().get_layer() == layer and \
                (end < tckstart or (tckstart < end < tckstart + tckduration)) \
                and isinstance(tckobj, ges.TrackSource):
            return tckobj
    return None


class Gap(object):
    """
    """
    def __init__(self, left_object, right_object, start, duration):
        self.left_object = left_object
        self.right_object = right_object
        self.start = start
        self.initial_duration = duration

    def __cmp__(self, other):
        if other is None or other is invalid_gap:
            return -1
        return cmp(self.duration, other.duration)

    @classmethod
    def findAroundObject(self, timeline_object, priority=-1, tracks=None):
        layer = timeline_object.get_layer()
        tlobjs = layer.get_objects()
        index = tlobjs.index(timeline_object)

        try:
            prev = [obj for obj in tlobjs[:index - 1]\
                    if isinstance(obj, ges.TimelineSource) and \
                    obj != timeline_object].pop()
            left_object = prev
            right_object = timeline_object
            start = prev.props.start + prev.props.duration
            duration = timeline_object.props.start - start
        except IndexError:
            left_object = None
            right_object = timeline_object
            start = 0
            duration = timeline_object.props.start

        left_gap = Gap(left_object, right_object, start, duration)

        try:
            next = [obj for obj in tlobjs[index + 1:]\
                   if isinstance(obj, ges.TimelineSource) and \
                    obj != timeline_object][0]

            left_object = timeline_object
            right_object = next
            start = timeline_object.props.start + timeline_object.props.duration
            duration = next.props.start - start

        except IndexError:
            left_object = timeline_object
            right_object = None
            start = timeline_object.props.start + timeline_object.props.duration
            duration = infinity

        right_gap = Gap(left_object, right_object, start, duration)

        return left_gap, right_gap

    @classmethod
    def findAllGaps(self, objs):
        """Find all the gaps in a given set of objects: i.e. find all the
        spans of time which are covered by no object in the given set"""
        duration = 0
        gaps = []
        prev = None

        # examine each object in order of increasing start time
        for obj in sorted(objs, key=lambda x: x.props.start):
            start = obj.props.start
            end = obj.props.start + obj.props.duration

            # only if the current object starts after the total timeline
            # duration is a gap created.
            if start > duration:
                gaps.append(Gap(prev, obj, duration, start - duration))
            duration = max(duration, end)
            prev = obj
        return gaps

    @property
    def duration(self):
        if self.left_object is None and self.right_object is None:
            return self.initial_duration

        if self.initial_duration is infinity:
            return self.initial_duration

        if self.left_object is None:
            return self.right_object.props.start

        if self.right_object is None:
            return infinity

        res = self.right_object.props.start - \
                (self.left_object.props.start + self.left_object.props.duration)
        return res


class InvalidGap(object):
    pass

invalid_gap = InvalidGap()


class SmallestGapsFinder(object):
    def __init__(self, internal_objects):
        self.left_gap = None
        self.right_gap = None
        self.internal_objects = internal_objects

    def update(self, left_gap, right_gap):
        self.updateGap(left_gap, "left_gap")
        self.updateGap(right_gap, "right_gap")

    def updateGap(self, gap, min_gap_name):
        if self.isInternalGap(gap):
            return

        min_gap = getattr(self, min_gap_name)

        if min_gap is invalid_gap or gap.duration < 0:
            setattr(self, min_gap_name, invalid_gap)
            return

        if min_gap is None or gap < min_gap:
            setattr(self, min_gap_name, gap)

    def isInternalGap(self, gap):
        gap_objects = set([gap.left_object, gap.right_object])

        return gap_objects.issubset(self.internal_objects)


class Selection(Signallable):
    """
    A collection of L{ges.TimelineObject}.

    Signals:
     - C{selection-changed} : The contents of the L{ges.Selection} changed.

    @ivar selected: Set of selected L{ges.TrackObject}
    @type selected: C{list}
    """

    __signals__ = {
        "selection-changed": []}

    def __init__(self):
        self.selected = set([])
        self.last_single_obj = None

    def setToObj(self, obj, mode):
        """
        Convenience method for calling L{setSelection} with a single L{ges.TimelineObject}

        @see: L{setSelection}
        """
        self.setSelection(set([obj]), mode)

    def addTimelineObject(self, timeline_object):
        """
        Add the given timeline_object to the selection.

        @param timeline_object: The object to add
        @type timeline_object: L{ges.TimelineObject}
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
            # FIXME GES break, handle the fact that we have unlinked objects in GES
            if isinstance(obj, ges.TrackObject):
                selection.add(obj.get_timeline_object())
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
            for tckobj in obj.get_track_objects():
                if not isinstance(tckobj, ges.TrackEffect):
                    tckobj.selected.selected = True

        for obj in old_selection - self.selected:
            for tckobj in obj.get_track_objects():
                if not isinstance(tckobj, ges.TrackEffect):
                    tckobj.selected.selected = False

        # FIXME : shouldn't we ONLY emit this IFF the selection has changed ?
        self.emit("selection-changed")

    def getSelectedTrackObjs(self):
        """
        Returns the list of L{TrackObject} contained in this selection.
        """
        objects = []
        for timeline_object in self.selected:
            objects.extend(timeline_object.get_track_objects())

        return set(objects)

    def getSelectedTrackEffects(self):
        """
        Returns the list of L{TrackEffect} contained in this selection.
        """
        track_effects = []
        for timeline_object in self.selected:
            for track in timeline_object.get_track_objects():
                if isinstance(track, ges.TrackEffect):
                    track_effects.append(track)

        return track_effects

    def __len__(self):
        return len(self.selected)

    def __iter__(self):
        return iter(self.selected)


#-----------------------------------------------------------------------------#
#                           Timeline edition modes helpers                    #
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
        @type timeline: instance of L{ges.Timeline}

        @param focus: the TimelineObject or TrackObject which is to be the
        main target of interactive editing, such as the object directly under the
        mouse pointer
        @type focus: L{ges.TimelineObject} or
        L{ges.TrackObject}

        @param other: a set of objects which are the secondary targets of
        interactive editing, such as objects in the current selection.
        @type other: a set() of L{TimelineObject}s or L{TrackObject}s

        @returns: An instance of L{pitivi.utils.timeline.TimelineEditContex}
        """

        # make sure focus is not in secondary object list
        other.difference_update(set((focus,)))

        self.other = other
        self.focus = focus
        self.timeline = timeline
        self._snap = True
        self._mode = self.DEFAULT
        self._last_position = focus.props.start
        self._last_priority = focus.props.priority

        self.timeline.enable_update(False)

    def _getOffsets(self, start_offset, priority_offset, timeline_objects):
        offsets = {}
        for tlobj in timeline_objects:
            offsets[tlobj] = (tlobj.props.start - start_offset,
                        tlobj.get_layer().props.priority - priority_offset)

        return offsets

    def _getTimelineObjectValues(self, tlobj):
        return (tlobj.props.start, tlobj.props.duration,
                tlobj.props.in_point,
                tlobj.props.priority)

    def _saveValues(self, timeline_objects):
        return dict(((tlobj,
            self._getTimelineObjectValues(tlobj))
                for tlobj in timeline_objects))

    def _restoreValues(self, values):
        for tlobj, (start, duration, in_point, pri) in \
            values.iteritems():
            tlobj.props.start = start
            tlobj.props.duration = duration
            tlobj.props.in_point = in_point
            tlobj.props.priority = pri

    def _getSpan(self, earliest, objs):
        return max((obj.start + obj.duration for obj in objs)) - earliest

    def finish(self):
        """Clean up timeline for normal editing"""
        # TODO: post undo / redo action here
        self.timeline.enable_update(True)

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
        self.debug("Setting snap to %s", snap)
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

    def _getGapsForLayer(self, timeline_objects):
        gaps = SmallestGapsFinder(timeline_objects)

        for tlobj in timeline_objects:
            left_gap, right_gap = Gap.findAroundObject(tlobj)
            gaps.update(left_gap, right_gap)

        return gaps.left_gap, gaps.right_gap


class MoveContext(EditingContext, Loggable):

    """
    An editing context which sets the start point of the editing targets.
    It has support for ripple, slip-and-slide editing modes.

    @tracks: {track: [earliest: latest]} with @earliest the earliest #TrackObject in @track
            and @latest the latest #TrackObject in @track
    """

    # FIXME Refactor... this is too long!
    def __init__(self, timeline, focus, other):
        EditingContext.__init__(self, timeline, focus, other)
        Loggable.__init__(self)

        min_priority = infinity
        earliest = infinity
        latest = 0
        self.default_originals = {}
        self.timeline_objects = set([])
        self.tracks = {}
        self.tckobjs = set([])
        all_objects = set(other)
        all_objects.add(focus)

        for obj in all_objects:
            if isinstance(obj, ges.TrackObject):
                tlobj = obj.get_timeline_object()
                tckobjs = [obj]
            else:
                tlobj = obj
                tckobjs = tlobj.get_track_objects()

            self.timeline_objects.add(tlobj)
            self.default_originals[tlobj] = \
                    self._getTimelineObjectValues(tlobj)

            # Check TrackObject-s as we can have unlocked objects
            for tckobj in tckobjs:
                track = tckobj.get_track()
                if not tckobj.get_track() in self.tracks:
                    self.tracks[track] = [tckobj, tckobj]

                earliest = min(earliest, tckobj.props.start)
                if earliest == tckobj.props.start:
                    curr_early_late = self.tracks[track]
                    self.tracks[track] = [tckobj, curr_early_late[1]]

                latest = max(latest, tckobj.props.start + tckobj.props.duration)
                if latest == tckobj.props.start:
                    curr_early_late = self.tracks[track]
                    self.tracks[track] = [curr_early_late[0], tckobj]

            self.tckobjs.update(tckobjs)

            # Always work with TimelineObject-s for priorities
            min_priority = min(min_priority, tlobj.props.priority)

        # Get focus various properties we need
        focus_start = focus.props.start
        if isinstance(focus, ges.TrackObject):
            layer = focus.get_timeline_object().get_layer()
        else:
            layer = focus.get_layer()

        focus_prio = layer.props.priority
        self.offsets = self._getOffsets(focus_start,
                focus_prio, self.timeline_objects)

        self.min_priority = focus_prio - min_priority
        self.min_position = focus_start - earliest

        # get the span over all clips for edge snapping
        self.default_span = latest - earliest

        ripple = [obj for obj in layer.get_objects() if obj.props.start >= latest]
        self.ripple_offsets = self._getOffsets(focus_start, focus_prio, ripple)

        # get the span over all clips for ripple editing
        for tlobj in ripple:
            latest = max(latest, tlobj.props.start + tlobj.props.duration)
        self.ripple_span = latest - earliest

        # save default values
        self.ripple_originals = self._saveValues(ripple)

        self.timeline_objects_plus_ripple = set(self.timeline_objects)
        self.timeline_objects_plus_ripple.update(ripple)

    def _getGapsForLayer(self):
        if self._mode == self.RIPPLE:
            timeline_objects = self.timeline_objects_plus_ripple
        else:
            timeline_objects = self.timeline_objects

        return EditingContext._getGapsForLayer(self,
                timeline_objects)

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

        final_priority = focus_timeline_object.props.priority
        final_position = self.focus.props.start

        priority = final_priority

        # special case for transitions. Allow a single object to overlap
        # either of its two neighbors if it overlaps no other objects
        if len(self.timeline_objects) == 1:
            EditingContext.finish(self)
            return

        # adjust layer
        overlap = False
        while True:
            left_gap, right_gap = self._getGapsForLayer()

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
        left_gap, right_gap = self._getGapsForLayer()

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
        for track, earliest_latest in self.tracks.iteritems():
            tckobj = earliest_latest[0]
            prev = previous_track_source(tckobj,
                    tckobj.get_timeline_object().get_layer(), start)

            if prev:
                prev_end = prev.get_start() + prev.get_duration()
                if abs(start - prev_end) < gst.SECOND:
                    self.debug("Snaping to edge frontward, diff=%d",
                            abs(start - prev_end))
                    return prev_end
            elif end:
                tckobj = earliest_latest[1]
                next = next_track_source(tckobj,
                        tckobj.get_timeline_object().get_layer(), start,
                        end - start)

                if next and abs(end - next.get_start()) < gst.SECOND:
                    self.debug("Snaping to edge backward, diff=%d",
                            abs(end - next.get_start()))
                    return next.get_start() - (end - start)

        return start

    def _ensureLayer(self):
        """
        Make sure we have a layer in our timeline

        Returns: The number of layer present in self.timeline
        """
        layers = self.timeline.get_layers()

        if not layers:
            layer = ges.TimelineLayer()
            layer.props.auto_transition = True
            self.timeline.add_layer(layer)
            layers = [layer]

        return layers

    def _defaultTo(self, position, priority):
        if self._snap:
            position = self.snapToEdge(position,
                position + self.default_span)

        self.debug("defaulting to %s with priorty %d", position, priority)

        layers = self._ensureLayer()
        position = max(self.min_position, position)

        # We make sure to work with TimelineObject-s for the drag
        # and drop
        if isinstance(self.focus, ges.TrackSource):
            obj = self.focus.get_timeline_object()
        else:
            obj = self.focus

        # FIXME See what we should do in the case we have
        # have ges.xxxOperation

        self.focus.props.start = long(position)

        for obj, (s_offset, p_offset) in self.offsets.iteritems():
            obj.props.start = max(0, long(position + s_offset))

            # Move between layers
            layers = self.timeline.get_layers()
            priority = min(len(layers), max(0, priority + p_offset))
            if obj.get_layer().props.priority != priority:
                if  priority == len(layers):
                    self.debug("Adding layer")
                    layer = ges.TimelineLayer()
                    layer.props.auto_transition = True
                    layer.props.priority = priority
                    self.timeline.add_layer(layer)
                    obj.move_to_layer(layer)
                else:
                    obj.move_to_layer(layers[priority])

        #Remove empty layer
        last_layer = self.timeline.get_layers()[-1]
        if not last_layer.get_objects():
            self.debug("Removing layer")
            self.timeline.remove_layer(last_layer)

        return position, priority

    def _finishRipple(self):
        self._restoreValues(self.ripple_originals)

    def _rippleTo(self, position, priority):
        self.debug("Ripple from %s", position)
        if self._snap:
            position = self.snapToEdge(position,
                position + self.default_span)

        priority = max(self.min_priority, priority)
        left_gap, right_gap = self._getGapsForLayer()

        if left_gap is invalid_gap or right_gap is invalid_gap:
            if priority == self._last_priority:
                # abort move
                return self._last_position, self._last_priority

            # try to do the same time move, using the current priority
            return self._defaultTo(position, self._last_priority)

        delta = position - self.focus.props.start
        if delta > 0 and right_gap.duration < delta:
            position = self.focus.props.start + right_gap.duration
        elif delta < 0 and left_gap.duration < abs(delta):
            position = self.focus.props.start - left_gap.duration

        #FIXME GES: What about moving between layers?
        self.focus.props.start = position
        for obj, (s_offset, p_offset) in self.offsets.iteritems():
            obj.props.start = position + s_offset

        for obj, (s_offset, p_offset) in self.ripple_offsets.iteritems():
            obj.props.start = position + s_offset

        return position, priority


class TrimStartContext(EditingContext):

    def __init__(self, timeline, focus, other):
        EditingContext.__init__(self, timeline, focus, other)
        self.tracks = set([])

        if isinstance(self.focus, ges.TrackObject):
            focus_timeline_object = self.focus.get_timeline_object()
            self.tracks.add(focus.get_track())
        else:
            focus_timeline_object = self.focus
            tracks = set(track_object.get_track() for track_object in
                        focus.get_track_objects())
            self.tracks.update(tracks)
        self.focus_timeline_object = focus_timeline_object
        self.default_originals = self._saveValues([focus_timeline_object])
        #ripple = self.timeline.getObjsBeforeTime(focus.start)
        #assert not focus.tlobj in ripple or focus.duration == 0
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
            position = self.snapToEdge(position)

        position = min(latest, max(position, earliest))
        self.focus.trimStart(position)
        r_position = max(position, self.ripple_min)
        for obj, (s_offset, p_offset) in self.ripple_offsets.iteritems():
            obj.setStart(r_position + s_offset)

        return position, priority

    def _finishRipple(self):
        self._restoreValues(self.ripple_originals)

    def _defaultTo(self, position, priority):
        earliest = max(0, position - self.focus.starting_start)
        self.focus.props.in_point = earliest
        self.focus.props.start = position
        self.focus.props.duration = self.focus.props.max_duration - \
                self.focus.props.in_point
        return position, priority

    def finish(self):
        if isinstance(self.focus, ges.TrackObject):
            obj = self.focus.get_timeline_object()
        else:
            obj = self.focus

        initial_position = self.default_originals[self.focus_timeline_object][0]
        self.focus.starting_start = self.focus.props.start
        timeline_objects = [self.focus_timeline_object]
        EditingContext.finish(self)

        left_gap, right_gap = self._getGapsForLayer(timeline_objects)

        if left_gap is invalid_gap:
            self._defaultTo(initial_position, obj.priority)
            left_gap, right_gap = Gap.findAroundObject(self.focus_timeline_object)
            position = initial_position - left_gap.duration
            self._defaultTo(position, obj)


class TrimEndContext(EditingContext):
    def __init__(self, timeline, focus, other):
        EditingContext.__init__(self, timeline, focus, other)
        self.tracks = set([])
        if isinstance(self.focus, ges.TrackSource):
            focus_timeline_object = self.focus
            self.tracks.add(focus.get_track())
        else:
            focus_timeline_object = self.focus
            tracks = set(track_object.get_track() for track_object in
                    focus.get_track_objects())
            self.tracks.update(tracks)
        self.focus_timeline_object = focus_timeline_object
        self.default_originals = self._saveValues([focus_timeline_object])

        if isinstance(focus, ges.TrackObject):
            layer = focus.get_timeline_object().get_layer()
        else:
            layer = focus.get_layer()
        reference = focus.props.start + focus.props.duration
        ripple = [obj for obj in layer.get_objects() \
                  if obj.props.start > reference]

        self.ripple_originals = self._saveValues(ripple)
        self.ripple_offsets = self._getOffsets(reference,
            self.focus.get_layer().props.priority, ripple)

    def _rollTo(self, position, priority):
        if self._snap:
            position = self.snapToEdge(position)
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
            position = self.snapToEdge(position)
        position = min(latest, max(position, earliest))
        duration = position - self.focus.start
        self.focus.props.duration = duration
        for obj, (s_offset, p_offset) in self.ripple_offsets.iteritems():
            obj.setStart(position + s_offset)

        return position, priority

    def _finishRipple(self):
        self._restoreValues(self.ripple_originals)

    def _defaultTo(self, position, priority):
        duration = max(0, position - self.focus.props.start)
        duration = min(duration, self.focus.max_duration)
        self.focus.props.duration = duration

        return position, priority

    def finish(self):
        EditingContext.finish(self)

        if isinstance(self.focus, ges.TrackObject):
            obj = self.focus.get_timeline_object()
        else:
            obj = self.focus

        initial_position, initial_duration = \
                self.default_originals[self.focus_timeline_object][0:2]
        absolute_initial_duration = initial_position + initial_duration

        timeline_objects = [self.focus_timeline_object]

        left_gap, right_gap = self._getGapsForLayer(timeline_objects,
                self.tracks)

        if right_gap is invalid_gap:
            self._defaultTo(absolute_initial_duration, obj.props.priority)
            left_gap, right_gap = Gap.findAroundObject(self.focus_timeline_object)
            duration = absolute_initial_duration + right_gap.duration
            self._defaultTo(duration, obj.props.priority)


#-------------------------- Interfaces ----------------------------------------#

ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)


class Controller(Loggable):

    """A controller which implements drag-and-drop bahavior on connected view
    objects in the timeline. Subclasses may override the drag_start, drag_end,
    pos, and set_pos methods"""

    # note we SHOULD be using the gtk function for this, but it doesn't appear
    # to be exposed in pygtk
    __DRAG_THRESHOLD__ = Point(0, 0)

    _view = receiver()

    _dragging = None
    _canvas = None
    _cursor = None
    _ptr_within = False
    _last_click = None
    _initial = None
    _mousedown = None
    _last_event = None
    _pending_drag_start = None
    _pending_drag_end = False
    _shift_down = False
    _control_down = False
    _handle_enter_leave = True
    _handle_mouse_up_down = True
    _handle_motion_notify = True

    def __init__(self, view=None):
        object.__init__(self)
        self._view = view
        Loggable.__init__(self)

## convenience functions

    def from_event(self, event):
        """returns the coordinates of an event"""
        return Point(*self._canvas.convert_from_pixels(event.x, event.y))

    def from_item_event(self, item, event):
        return Point(*self._canvas.convert_from_item_space(item,
            *self.from_event(event)))

    def to_item_space(self, item, point):
        return Point(*self._canvas.convert_to_item_space(item, *point))

    def pos(self, item):
        bounds = item.get_bounds()
        return Point(bounds.x1, bounds.y1)

## signal handlers

    @handler(_view, "enter_notify_event")
    def enter_notify_event(self, item, target, event):
        self._event_common(item, target, event)
        self._canvas.grab_focus(item)
        if self._cursor and item is target:
            event.window.set_cursor(self._cursor)
        if not self._dragging:
            self.enter(item, target)
        self._ptr_within = True
        return self._handle_enter_leave or self._dragging

    @handler(_view, "leave_notify_event")
    def leave_notify_event(self, item, target, event):
        self._event_common(item, target, event)
        self._canvas.keyboard_ungrab(item, event.time)
        self._ptr_within = False
        if not self._dragging:
            self.leave(item, target)
            event.window.set_cursor(ARROW)
        return self._handle_enter_leave or self._dragging

    @handler(_view, "button_press_event")
    def button_press_event(self, item, target, event):
        self._event_common(item, target, event)
        if not self._canvas:
            self._canvas = item.get_canvas()
        self._mousedown = self.pos(item) - self.transform(self.from_item_event(
            item, event))
        self._dragging = target
        self._initial = self.pos(target)
        self._pending_drag_start = (item, target, event)
        return self._handle_mouse_up_down

    @handler(_view, "motion_notify_event")
    def motion_notify_event(self, item, target, event):
        self._event_common(item, target, event)
        if self._dragging:
            if self._pending_drag_start is not None:
                pending_drag_start, self._pending_drag_start = \
                        self._pending_drag_start, None
                self._pending_drag_end = True
                self._drag_start(*pending_drag_start)

            self.set_pos(self._dragging,
                self.transform(self._mousedown + self.from_item_event(item,
                    event)))
            return self._handle_motion_notify
        else:
            self.hover(item, target, event)
        return False

    @handler(_view, "button_release_event")
    def button_release_event(self, item, target, event):
        self._event_common(item, target, event)
        self._drag_end(item, self._dragging, event)
        self._dragging = None
        return self._handle_mouse_up_down

    @handler(_view, "key_press_event")
    def key_press_event(self, item, target, event):
        self._event_common(item, target, event)
        kv = event.keyval
        if kv in (gtk.keysyms.Shift_L, gtk.keysyms.Shift_R):
            self._shift_down = True
        elif kv in (gtk.keysyms.Control_L, gtk.keysyms.Control_R):
            self._control_down = True
        return self.key_press(kv)

    @handler(_view, "key_release_event")
    def key_release_event(self, item, target, event):
        self._event_common(item, target, event)
        kv = event.keyval
        if kv in (gtk.keysyms.Shift_L, gtk.keysyms.Shift_R):
            self._shift_down = False
        elif kv in (gtk.keysyms.Control_L, gtk.keysyms.Control_R):
            self._control_down = False
        return self.key_release(kv)

## internal callbacks

    def _event_common(self, item, target, event):
        if not self._canvas:
            self._canvas = item.get_canvas()
            # might there be a better way to do this?
            self._hadj = self._canvas.app.gui.timeline_ui.hadj
            self._vadj = self._canvas.app.gui.timeline_ui.vadj
        self._last_event = event
        s = event.get_state()
        self._shift_down = s & gtk.gdk.SHIFT_MASK
        self._control_down = s & gtk.gdk.CONTROL_MASK

    def _drag_start(self, item, target, event):
        self.drag_start(item, target, event)

    def _drag_end(self, item, target, event):
        self._pending_drag_start = None
        pending_drag_end, self._pending_drag_end = self._pending_drag_end, False
        if pending_drag_end:
            self.drag_end(item, target, event)

        if self._ptr_within and self._drag_threshold():
            point = self.from_item_event(item, event)
            if self._last_click and (event.time - self._last_click < 400):
                self.double_click(point)
            else:
                self.click(point)
            self._last_click = event.time
            event.window.set_cursor(self._cursor)
        else:
            event.window.set_cursor(ARROW)

    def _drag_threshold(self):
        last = self.pos(self._dragging)
        difference = abs(self._initial - last)
        if abs(self._initial - last) > self.__DRAG_THRESHOLD__:
            return False
        return True

## protected interface for subclasses

    def click(self, pos):
        pass

    def double_click(self, pos):
        pass

    def drag_start(self, item, target, event):
        pass

    def drag_end(self, item, target, event):
        pass

    def set_pos(self, obj, pos):
        obj.props.x, obj.props.y = pos

    def transform(self, pos):
        return pos

    def enter(self, item, target):
        pass

    def leave(self, item, target):
        pass

    def key_press(self, keyval):
        pass

    def key_release(self, keyval):
        pass

    def hover(self, item, target, event):
        pass


class View(object):

    Controller = Controller

    def __init__(self):
        object.__init__(self)
        self._controller = self.Controller(view=self)

## public interface

    def focus(self):
        pass

    def select(self):
        pass

    def activate(self):
        pass

    def normal(self):
        pass


class Zoomable(object):
    """
    Interface for managing tranformation between timeline timestamps and UI
    pixels.

    Complex Timeline interfaces v2 (01 Jul 2008)

    Zoomable
    -----------------------
    Interface for the Complex Timeline widgets for setting, getting,
    distributing and modifying the zoom ratio and the size of the widget.

    A zoomratio is the number of pixels per second
    ex : 10.0 = 10 pixels for a second
    ex : 0.1 = 1 pixel for 10 seconds
    ex : 1.0 = 1 pixel for a second
     Class Methods
    . pixelToNs(pixels)
    . nsToPixels(time)
    . setZoomRatio
    Instance Methods
    . zoomChanged()
    """

    sigid = None
    _instances = []
    max_zoom = 1000.0
    min_zoom = 0.25
    zoom_steps = 100
    zoom_range = max_zoom - min_zoom
    _cur_zoom = 2
    zoomratio = None

    def __init__(self):
        # FIXME: ideally we should deprecate this
        Zoomable.addInstance(self)
        if Zoomable.zoomratio is None:
            Zoomable.zoomratio = self.computeZoomRatio(self._cur_zoom)

    def __del__(self):
        if self in Zoomable._instances:
            # FIXME: ideally we should deprecate this and spit a warning here
            self._instances.remove(self)

    @classmethod
    def addInstance(cls, instance):
        cls._instances.append(instance)

    @classmethod
    def removeInstance(cls, instance):
        cls._instances.remove(instance)

    @classmethod
    def setZoomRatio(cls, ratio):
        if cls.zoomratio != ratio:
            cls.zoomratio = min(cls.max_zoom, max(cls.min_zoom, ratio))
            cls._zoomChanged()

    @classmethod
    def setZoomLevel(cls, level):
        level = min(cls.zoom_steps, max(0, level))
        if level != cls._cur_zoom:
            cls._cur_zoom = level
            cls.setZoomRatio(cls.computeZoomRatio(level))

    @classmethod
    def getCurrentZoomLevel(cls):
        return cls._cur_zoom

    @classmethod
    def zoomIn(cls):
        cls.setZoomLevel(cls._cur_zoom + 1)

    @classmethod
    def zoomOut(cls):
        cls.setZoomLevel(cls._cur_zoom - 1)

    @classmethod
    def computeZoomRatio(cls, x):
        return ((((float(x) / cls.zoom_steps) ** 3) * cls.zoom_range) +
            cls.min_zoom)

    @classmethod
    def computeZoomLevel(cls, ratio):
        return int((
            (max(0, ratio - cls.min_zoom) /
                cls.zoom_range) ** (1.0 / 3.0)) *
                    cls.zoom_steps)

    @classmethod
    def pixelToNs(cls, pixel):
        """
        Returns the pixel equivalent in nanoseconds according to the zoomratio
        """
        return long(pixel * gst.SECOND / cls.zoomratio)

    @classmethod
    def pixelToNsAt(cls, pixel, ratio):
        """
        Returns the pixel equivalent in nanoseconds according to the zoomratio
        """
        return long(pixel * gst.SECOND / ratio)

    @classmethod
    def nsToPixel(cls, duration):
        """
        Returns the pixel equivalent of the given duration, according to the
        set zoom ratio
        """
        ## DIE YOU CUNTMUNCH CLOCK_TIME_NONE UBER STUPIDITY OF CRACK BINDINGS !!!!!!
        if duration == 18446744073709551615 or \
               long(duration) == long(gst.CLOCK_TIME_NONE):
            return 0
        return int((float(duration) / gst.SECOND) * cls.zoomratio)

    @classmethod
    def _zoomChanged(cls):
        for inst in cls._instances:
            inst.zoomChanged()

    def zoomChanged(self):
        pass
