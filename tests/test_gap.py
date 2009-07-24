# PiTiVi , Non-linear video editor
#
#       tests/test_gap.py
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

from unittest import TestCase

import gobject
gobject.threads_init()
import gst

from common import StubFactory
from pitivi.stream import AudioStream
from pitivi.timeline.track import Track, SourceTrackObject
from pitivi.timeline.timeline import Timeline, TimelineObject
from pitivi.timeline.gap import Gap, SmallestGapsFinder, invalid_gap
from pitivi.utils import infinity

class TestGap(TestCase):
    def setUp(self):
        self.factory = StubFactory()
        self.stream = AudioStream(gst.Caps('audio/x-raw-int'))
        self.factory.addOutputStream(self.stream)
        self.track1 = Track(self.stream)
        self.timeline = Timeline()

    def makeTimelineObject(self):
        track_object = SourceTrackObject(self.factory, self.stream)
        self.track1.addTrackObject(track_object)
        timeline_object = TimelineObject(self.factory)
        timeline_object.addTrackObject(track_object)
        self.timeline.addTimelineObject(timeline_object)

        return timeline_object

    def testGapCmp(self):
        gap1 = Gap(None, None, start=10, duration=5)
        gap2 = Gap(None, None, start=10, duration=5)
        self.failUnlessEqual(gap1, gap2)

        gap2 = Gap(None, None, start=15, duration=4)
        self.failUnless(gap1 > gap2)
        self.failUnless(gap2 < gap1)

    def testFindAroundObject(self):
        timeline_object1 = self.makeTimelineObject()
        timeline_object2 = self.makeTimelineObject()

        timeline_object1.start = 5 * gst.SECOND
        timeline_object1.duration = 10 * gst.SECOND
        timeline_object2.start = 20 * gst.SECOND
        timeline_object2.duration = 10 * gst.SECOND

        left_gap, right_gap = Gap.findAroundObject(timeline_object1)
        self.failUnlessEqual(left_gap.left_object, None)
        self.failUnlessEqual(left_gap.right_object, timeline_object1)
        self.failUnlessEqual(left_gap.start, 0 * gst.SECOND)
        self.failUnlessEqual(left_gap.duration, 5 * gst.SECOND)
        self.failUnlessEqual(right_gap.left_object, timeline_object1)
        self.failUnlessEqual(right_gap.right_object, timeline_object2)
        self.failUnlessEqual(right_gap.start, 15 * gst.SECOND)
        self.failUnlessEqual(right_gap.duration, 5 * gst.SECOND)

        left_gap, right_gap = Gap.findAroundObject(timeline_object2)
        self.failUnlessEqual(left_gap.left_object, timeline_object1)
        self.failUnlessEqual(left_gap.right_object, timeline_object2)
        self.failUnlessEqual(left_gap.start, 15 * gst.SECOND)
        self.failUnlessEqual(left_gap.duration, 5 * gst.SECOND)
        self.failUnlessEqual(right_gap.left_object, timeline_object2)
        self.failUnlessEqual(right_gap.right_object, None)
        self.failUnlessEqual(right_gap.start, 30 * gst.SECOND)
        self.failUnlessEqual(right_gap.duration, infinity)

        # make the objects overlap
        timeline_object2.start = 10 * gst.SECOND
        left_gap, right_gap = Gap.findAroundObject(timeline_object1)
        self.failUnlessEqual(right_gap.left_object, timeline_object1)
        self.failUnlessEqual(right_gap.right_object, timeline_object2)
        self.failUnlessEqual(right_gap.start, 15 * gst.SECOND)
        self.failUnlessEqual(right_gap.duration, -5 * gst.SECOND)

    def testGapFinder(self):
        timeline_object1 = self.makeTimelineObject()
        timeline_object2 = self.makeTimelineObject()
        timeline_object3 = self.makeTimelineObject()
        timeline_object4 = self.makeTimelineObject()
        
        timeline_object1.start = 5 * gst.SECOND
        timeline_object1.duration = 10 * gst.SECOND
        timeline_object1.priority = 1

        timeline_object2.start = 20 * gst.SECOND
        timeline_object2.duration = 10 * gst.SECOND
        timeline_object2.priority = 1

        timeline_object3.start = 31 * gst.SECOND
        timeline_object3.duration = 10 * gst.SECOND
        timeline_object3.priority = 2

        timeline_object4.start = 50 * gst.SECOND
        timeline_object4.duration = 10 * gst.SECOND
        timeline_object4.priority = 2

        gap_finder = SmallestGapsFinder(set([timeline_object2,
                timeline_object3]))
        gap_finder.update(*Gap.findAroundObject(timeline_object2))
        gap_finder.update(*Gap.findAroundObject(timeline_object3))

        left_gap = gap_finder.left_gap
        right_gap = gap_finder.right_gap
        self.failUnlessEqual(left_gap.left_object, timeline_object1)
        self.failUnlessEqual(left_gap.right_object, timeline_object2)
        self.failUnlessEqual(left_gap.start, 15 * gst.SECOND)
        self.failUnlessEqual(left_gap.duration, 5 * gst.SECOND)
        self.failUnlessEqual(right_gap.left_object, timeline_object3)
        self.failUnlessEqual(right_gap.right_object, timeline_object4)
        self.failUnlessEqual(right_gap.start, 41 * gst.SECOND)
        self.failUnlessEqual(right_gap.duration, 9 * gst.SECOND)

        # make timeline_object3 and timeline_object4 overlap
        timeline_object3.duration = 20 * gst.SECOND

        gap_finder = SmallestGapsFinder(set([timeline_object4]))
        gap_finder.update(*Gap.findAroundObject(timeline_object4))
        left_gap = gap_finder.left_gap
        right_gap = gap_finder.right_gap
        self.failUnlessEqual(left_gap, invalid_gap)
        self.failUnlessEqual(right_gap.left_object, timeline_object4)
        self.failUnlessEqual(right_gap.right_object, None)
        self.failUnlessEqual(right_gap.start, 60 * gst.SECOND)
        self.failUnlessEqual(right_gap.duration, infinity)

        gap_finder = SmallestGapsFinder(set([timeline_object3]))
        gap_finder.update(*Gap.findAroundObject(timeline_object3))
        left_gap = gap_finder.left_gap
        right_gap = gap_finder.right_gap
        self.failUnlessEqual(left_gap.left_object, None)
        self.failUnlessEqual(left_gap.right_object, timeline_object3)
        self.failUnlessEqual(left_gap.start, 0 * gst.SECOND)
        self.failUnlessEqual(left_gap.duration, 31 * gst.SECOND)
        self.failUnlessEqual(right_gap, invalid_gap)

