# PiTiVi , Non-linear video editor
#
#       tests/test_transition.py
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


    def testTransitionProperties(self):
        factory = self.factory
        track1 = self.track1
        track1._update_transitions = False
        stream = self.stream

        test_data = [
            ("a", 0, 10),
            ("b", 5, 15),
        ]

        objs = {}
        names = {}

        for name, start, end in test_data:
            obj = SourceTrackObject(factory, stream)
            obj.start = start * gst.SECOND
            obj.in_point = 0
            obj.duration = end * gst.SECOND - obj.start
            obj.media_duration = obj.duration
            track1.addTrackObject(obj)
            names[obj] = name
            objs[name] = obj

        # add transitions and check that initial properties are properly
        # evaluated
        tr = Transition(objs["a"], objs["b"])

        # move a and b together,
        # check that transition start, duration are updated
        objs["a"].start = 5 * gst.SECOND
        objs["b"].start = 10 * gst.SECOND

        self.failUnlessEqual(tr.start, 10 * gst.SECOND)
        self.failUnlessEqual(tr.duration, 5 * gst.SECOND)

        # make A longer
        objs["a"].duration = 11 * gst.SECOND
        self.failUnlessEqual(tr.start, 10 * gst.SECOND)
        self.failUnlessEqual(tr.duration, 6 * gst.SECOND)

        # move B earlier
        objs["b"].start = 9 * gst.SECOND
        self.failUnlessEqual(tr.start, 9 * gst.SECOND)
        self.failUnlessEqual(tr.duration, 7 * gst.SECOND)

        # update a, b priority
        self.failUnlessEqual(tr.priority, 0)
        self.failUnlessEqual(tr.operation.props.priority, 1)
        objs["a"].priority = 2
        objs["b"].priority = 2
        self.failUnlessEqual(tr.priority, 2)
        self.failUnlessEqual(tr.operation.props.priority, 7)
