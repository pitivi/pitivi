# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/gap.py
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

from pitivi.utils import infinity


class Gap(object):
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
        from pitivi.timeline.timeline import TimelineError

        timeline = timeline_object.timeline
        try:
            prev = timeline.getPreviousTimelineObject(timeline_object,
                    priority, tracks)
        except TimelineError:
            left_object = None
            right_object = timeline_object
            start = 0
            duration = timeline_object.start
        else:
            left_object = prev
            right_object = timeline_object
            start = prev.start + prev.duration
            duration = timeline_object.start - start

        left_gap = Gap(left_object, right_object, start, duration)

        try:
            next = timeline.getNextTimelineObject(timeline_object,
                    priority, tracks)
        except TimelineError:
            left_object = timeline_object
            right_object = None
            start = timeline_object.start + timeline_object.duration
            duration = infinity
        else:
            left_object = timeline_object
            right_object = next
            start = timeline_object.start + timeline_object.duration
            duration = next.start - start

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
        for obj in sorted(objs, key=lambda x: x.start):
            start = obj.start
            end = obj.start + obj.duration

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
            return self.right_object.start

        if self.right_object is None:
            return infinity

        res = self.right_object.start - \
                (self.left_object.start + self.left_object.duration)
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
