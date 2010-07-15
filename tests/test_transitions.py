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

from common import TestCase
import gst

from pitivi.timeline.track import Track, SourceTrackObject, TrackError
from pitivi.stream import AudioStream, VideoStream
from common import SignalMonitor, StubFactory
from pitivi.factories.test import AudioTestSourceFactory
from pitivi.timeline.track import TrackError, \
    Transition, AudioTransition, VideoTransition

class TestTransitions(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.factory = StubFactory()
        self.stream = VideoStream(gst.Caps('video/x-raw-rgb'))
        self.factory.addOutputStream(self.stream)
        self.track1 = Track(self.stream)

    def tearDown(self):
        self.factory = None
        self.stream = None
        self.track1 = None
        TestCase.tearDown(self)

    def testAddRemoveTransitions(self):
        factory = self.factory
        track1 = self.track1
        track1._update_transitions = False
        stream = self.stream

        test_data = [
            ("a", 0, 10),
            ("b", 5, 15),
            ("c", 15, 20),
            ("d", 30, 35),
            ("e", 30, 35),
        ]

        transitions = [
            ("a", "b"),
            ("d", "e"),
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

        result = []
        transition_objects = {}

        def addTransition(b, c):
            tr = Transition(objs[b], objs[c])
            track1.addTransition(tr)

        def transitionAddedCb(track, transition):
            values =(names[transition.a], names[transition.b])
            result.append(values)
            transition_objects[values] = transition

        def transitionRemovedCb(track, transition):
            values =(names[transition.a], names[transition.b])
            result.remove(values)

        track1.connect("transition-added", transitionAddedCb)
        track1.connect("transition-removed", transitionRemovedCb)

        # add transitions and check that initial properties are properly
        # evaluated
        for a, b in transitions:
            addTransition(a, b)

        self.failUnlessEqual(result, transitions)

        # check that adding a transition with a bogus track object raises an
        # error
        track1.removeTrackObject(objs["c"])
        self.failUnlessRaises(TrackError, addTransition, "b", "c")

        # check that adding a transition that already exists raises an error
        self.failUnlessRaises(TrackError, addTransition, "d", "e")

        # check that removing a transition directly works
        track1.removeTransition(transition_objects["d", "e"])
        self.failUnlessEqual(result, [("a", "b")])

        # check tht we can restore a transition after deleting it
        addTransition("d", "e")
        self.failUnlessEqual(result, [("a", "b"), ("d", "e")])

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
        at = AudioTransition(objs["a"], objs["b"])
        vt = VideoTransition(objs["a"], objs["b"])

        # move a and b together,
        # check that transition start, duration are updated
        objs["a"].start = 5 * gst.SECOND
        objs["b"].start = 10 * gst.SECOND

        self.failUnlessEqual(vt.start, 10 * gst.SECOND)
        self.failUnlessEqual(vt.duration, 5 * gst.SECOND)
        self.failUnlessEqual(vt.operation.props.start, 10 * gst.SECOND)
        self.failUnlessEqual(vt.operation.props.duration, 5 * gst.SECOND)

        self.failUnlessEqual(at.start, 10 * gst.SECOND)
        self.failUnlessEqual(at.duration, 5 * gst.SECOND)
        self.failUnlessEqual(at.a_operation.props.start, 10 * gst.SECOND)
        self.failUnlessEqual(at.a_operation.props.duration, 5 * gst.SECOND)
        self.failUnlessEqual(at.b_operation.props.start, 10 * gst.SECOND)
        self.failUnlessEqual(at.b_operation.props.duration, 5 * gst.SECOND)


 
        # make A longer
        objs["a"].duration = 11 * gst.SECOND
        self.failUnlessEqual(vt.start, 10 * gst.SECOND)
        self.failUnlessEqual(vt.duration, 6 * gst.SECOND)
        self.failUnlessEqual(vt.operation.props.start, 10 * gst.SECOND)
        self.failUnlessEqual(vt.operation.props.duration, 6 * gst.SECOND)

        self.failUnlessEqual(at.start, 10 * gst.SECOND)
        self.failUnlessEqual(at.duration, 6 * gst.SECOND)
        self.failUnlessEqual(at.a_operation.props.start, 10 * gst.SECOND)
        self.failUnlessEqual(at.a_operation.props.duration, 6 * gst.SECOND)
        self.failUnlessEqual(at.b_operation.props.start, 10 * gst.SECOND)
        self.failUnlessEqual(at.b_operation.props.duration, 6 * gst.SECOND)



        # move B earlier
        objs["b"].start = 9 * gst.SECOND
        self.failUnlessEqual(vt.start, 9 * gst.SECOND)
        self.failUnlessEqual(vt.duration, 7 * gst.SECOND)
        self.failUnlessEqual(vt.operation.props.start, 9 * gst.SECOND)
        self.failUnlessEqual(vt.operation.props.duration, 7 * gst.SECOND)
        self.failUnlessEqual(vt.operation.props.media_duration, 7 * gst.SECOND)

        self.failUnlessEqual(at.start, 9 * gst.SECOND)
        self.failUnlessEqual(at.duration, 7 * gst.SECOND)
        self.failUnlessEqual(at.a_operation.props.start, 9 * gst.SECOND)
        self.failUnlessEqual(at.a_operation.props.duration, 7 * gst.SECOND)
        self.failUnlessEqual(at.a_operation.props.media_duration, 7 * gst.SECOND)
        self.failUnlessEqual(at.b_operation.props.start, 9 * gst.SECOND)
        self.failUnlessEqual(at.b_operation.props.duration, 7 * gst.SECOND)
        self.failUnlessEqual(at.b_operation.props.media_duration, 7 * gst.SECOND)

        # check priority is currently zero
        self.failUnlessEqual(vt.priority, 0)

        # check video transition priority basic properties
        self.failUnlessEqual(vt.operation.props.priority, 1)
        vt.a.priority = 2
        vt.b.priority = 2
        self.failUnlessEqual(vt.priority, 2)
        self.failUnlessEqual(vt.operation.props.priority, 7)

        self.failUnlessEqual(at.priority, 2)

        # check controller for even - odd stagger
        vt.a.updatePosition(0)
        vt.b.updatePosition(1)

        self.failUnlessEqual(vt.a.gnl_object.props.priority, 9)
        self.failUnlessEqual(at.a._stagger, 0)
        self.failUnlessEqual(at.b._stagger, 1)
        self.failUnlessEqual(vt.b.gnl_object.props.priority, 10)

        self.failUnlessEqual(vt.controller.get("alpha", 0), 1.0)
        self.failUnlessEqual(vt.controller.get("alpha", vt.duration),
            0.0)

        self.failUnlessEqual(at.a_controller.get("volume", 0), 1.0)
        self.failUnlessEqual(at.a_controller.get("volume", vt.duration),
            0.0)
        self.failUnlessEqual(at.b_controller.get("volume", 0), 0.0)
        self.failUnlessEqual(at.b_controller.get("volume", vt.duration),
            1.0)
        self.failUnlessEqual(at.a_operation.props.priority, 9)
        self.failUnlessEqual(at.b_operation.props.priority, 11)


        # check controller for odd - even stagger
        vt.a.updatePosition(1)
        vt.b.updatePosition(2)
        self.failUnlessEqual(vt.controller.get("alpha", 0), 0.0)
        self.failUnlessEqual(vt.controller.get("alpha",
            vt.duration), 1.0)

        self.failUnlessEqual(at.a_controller.get("volume", 0), 1.0)
        self.failUnlessEqual(at.a_controller.get("volume", vt.duration),
            0.0)
        self.failUnlessEqual(at.b_controller.get("volume", 0), 0.0)
        self.failUnlessEqual(at.b_controller.get("volume", vt.duration),
            1.0)
        self.failUnlessEqual(at.a_operation.props.priority, 11)
        self.failUnlessEqual(at.b_operation.props.priority, 9)

    def testGetTrackObjectsGroupedByLayer(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1

        test_data = [
            ("a", 0, 10, 0),
            ("b", 5, 15, 0),
            ("c", 20, 25, 0),
            ("d", 30, 35, 0),
            ("e", 30, 35, 2),
            ("f", 35, 45, 0),
            ("g", 40, 50, 0),
            ("h", 50, 60, 0),
            ("i", 55, 65, 1),
            ("j", 57, 60, 2),
            ("k", 62, 70, 3),
            ("l", 63, 67, 0),
        ]

        expected = [
            ["a", "b", "c", "d", "f", "g", "h", "l"], 
            ["i"],
            ["e", "j"],
            ["k"]
        ]

        objs = {}

        for name, start, end, priority in test_data:
            obj = SourceTrackObject(factory, stream)
            obj.start = start * gst.SECOND
            obj.duration = end * gst.SECOND - obj.start
            obj.priority = priority
            track1.addTrackObject(obj)
            objs[obj] = name

        result = [[objs[obj] for obj in layer] for layer in 
            track1.getTrackObjectsGroupedByLayer()]

        self.failUnlessEqual(result, expected)

    def testGetValidTransitionSlots(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1

        test_data = [
            ("a", 0, 10),
            ("b", 5, 15),
            ("c", 20, 25),
            ("d", 30, 35),
            ("e", 30, 35),
            ("f", 35, 45),
            ("g", 40, 50),
            ("h", 50, 60),
            ("i", 55, 65),
            ("j", 57, 60),
            ("k", 62, 70),
            ("l", 63, 67),
        ]

        expected = [["a", "b"], ["d", "e"], ["f", "g"]]

        objs = {}
        names = {}
        ordered = []

        for name, start, end in test_data:
            obj = SourceTrackObject(factory, stream)
            obj.start = start * gst.SECOND
            obj.duration = end * gst.SECOND - obj.start
            track1.addTrackObject(obj)
            objs[name] = obj
            names[obj] = name
            ordered.append(obj)

        slots, valid = track1.getValidTransitionSlots(ordered)
        result = [[names[obj] for obj in layer] for layer in 
            slots]

        self.failUnlessEqual(result, expected)
        self.failUnlessEqual(track1.valid_arrangement, False)

        test_data = [
            ("a", 0, 5),
            ("b", 9, 12),
            ("c", 8, 13)
        ]

        ordered = []
        for name, start, end in test_data:
            ordered.append(objs[name])
            objs[name].start = gst.SECOND * start
            objs[name].duration = gst.SECOND * (end - start)

        slots, valid = track1.getValidTransitionSlots(ordered)
        self.failUnlessEqual(valid, False)

        test_data = [
            ("a", 0, 5),
            ("b", 1, 4),
            ("c", 8, 13),
        ]

        ordered = []
        for name, start, end in test_data:
            ordered.append(objs[name])
            objs[name].start = gst.SECOND * start
            objs[name].duration = gst.SECOND * (end - start)

        slots, valid = track1.getValidTransitionSlots(ordered)
        self.failUnlessEqual(valid, False)

    def testUpdateTransitions(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1
        track1._update_transitions = False

        test_data = [
            ("a", 0, 10),
            ("b", 5, 15),
            ("c", 20, 25),
            ("d", 30, 35),
            ("e", 30, 35),
            ("f", 35, 45),
            ("g", 40, 50),
            ("h", 50, 60),
            ("i", 55, 65),
            ("j", 57, 60),
            ("k", 62, 70),
            ("l", 63, 67),
        ]

        expected = [("a", "b"), ("d", "e"), ("f", "g")]

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

        result = []
        added = set()
        removed = set()

        def transitionAddedCb(track, transition):
            pair =(names[transition.a], names[transition.b])
            result.append(pair)
            added.add(pair)

        def transitionRemovedCb(track, transition):
            pair = (names[transition.a], names[transition.b])
            result.remove(pair)
            removed.add(pair)

        track1.connect("transition-added", transitionAddedCb)
        track1.connect("transition-removed", transitionRemovedCb)

        track1.updateTransitions()
        self.failUnlessEqual(result, expected)

        # move c so that it overlaps with b
        # move g so that it overlaps d, e, f
        # update the transitions, check that we have the expected
        # configuration
        test_data = [
            ("c", 12, 20),
            ("g", 30, 46),
        ]

        expected = [("a", "b"), ("b", "c")]
        added = set()
        removed = set()

        for name, start, end in test_data:
            objs[name].start = start * gst.SECOND
            objs[name].duration = (end - start) * gst.SECOND

        track1.updateTransitions()

        self.failUnlessEqual(result, expected)

        # check that *only* (b, c) was added in the update
        self.failUnlessEqual(added, set([("b", "c")]))

        # check that *only* (d, e) was removed in the update
        self.failUnlessEqual(removed, set([("d", "e"), ("f", "g")]))

        # move c to a different layer. check that (b, c) transition is removed
        added = set()
        removed = set()

        objs["c"].priority = 1
        expected = [("a", "b")]
        track1.updateTransitions()

        self.failUnlessEqual(result, expected)
        self.failUnlessEqual(added, set())
        self.failUnlessEqual(removed, set([("b", "c")]))

    def testUpdateAfterAddingAndRemovingTrackObjects(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1

        test_data = [
            ("a", 0, 10),
            ("b", 5, 15),
            ("c", 20, 25),
            ("d", 30, 35),
            ("f", 35, 45),
            ("g", 40, 50),
            ("e", 30, 35),
            ("h", 50, 60),
            ("i", 55, 65),
            ("j", 57, 60),
            ("k", 62, 70),
            ("l", 63, 67),
        ]

        # object j makes track arrangment invalid
        valid_in_order = [True for x in "abcdefghi"]
        valid_in_order.extend([False, False, False])

        added_in_order = [("a", "b"), ("f", "g"), ("d", "e"),
            ("h", "i"), ("i", "k"), ("h", "i")]

        removed_in_order = [("h", "i"), ("i", "k")]

        objs = {}
        names = {}

        added = []
        removed = []

        def transitionAddedCb(track, transition):
            added.append((names[transition.a], 
                names[transition.b]))

        def transitionRemovedCb(track, transition):
            removed.append((names[transition.a],
                names[transition.b]))
        track1.connect("transition-added", transitionAddedCb)
        track1.connect("transition-removed", transitionRemovedCb)

        valid = []

        for name, start, end in test_data:
            obj = SourceTrackObject(factory, stream)
            obj.start = start * gst.SECOND
            obj.in_point = 0
            obj.duration = end * gst.SECOND - obj.start
            obj.media_duration = obj.duration
            names[obj] = name
            objs[name] = obj
            track1.addTrackObject(obj)
            valid.append(track1.valid_arrangement)

        # removing this object brings (h, i) back
        track1.removeTrackObject(objs["j"])

        self.failUnlessEqual(added, added_in_order)
        self.failUnlessEqual(removed, removed_in_order)
        self.failUnlessEqual(valid, valid_in_order)

        # removing this should make the track valid again
        track1.removeTrackObject(objs["l"])
        self.failUnlessEqual(track1.valid_arrangement,
            True)


    def testUpdatesAfterEnablingUpdates(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1

        test_data = [
            ("a", 0, 10),
            ("b", 5, 15),
            ("c", 20, 25),
            ("d", 30, 35),
            ("e", 30, 35),
            ("f", 35, 45),
            ("g", 40, 50),
            ("h", 50, 60),
            ("i", 55, 65),
            ("j", 57, 60),
            ("k", 62, 70),
            ("l", 63, 67),
        ]

        expected = [("a", "b"), ("d", "e"), ("f", "g")]

        result = []
        added = set()
        removed = set()

        def transitionAddedCb(track, transition):
            pair =(names[transition.a], names[transition.b])
            result.append(pair)
            added.add(pair)

        def transitionRemovedCb(track, transition):
            pair = (names[transition.a], names[transition.b])
            result.remove(pair)
            removed.add(pair)

        track1.connect("transition-added", transitionAddedCb)
        track1.connect("transition-removed", transitionRemovedCb)

        objs = {}
        names = {}

        for name, start, end in test_data:
            obj = SourceTrackObject(factory, stream)
            obj.start = start * gst.SECOND
            obj.in_point = 0
            obj.duration = end * gst.SECOND - obj.start
            obj.media_duration = obj.duration
            names[obj] = name
            objs[name] = obj
            track1.addTrackObject(obj)

        self.failUnlessEqual(result, expected)

        track1.disableUpdates()

        # move c so that it overlaps with b
        # move g so that it overlaps d, e, f
        # update the transitions, check that we have the expected
        # configuration
        test_data = [
            ("c", 12, 20),
            ("g", 30, 46),
        ]

        expected = [("a", "b"), ("b", "c")]
        added = set()
        removed = set()

        for name, start, end in test_data:
            objs[name].start = start * gst.SECOND
            objs[name].duration = (end - start) * gst.SECOND

        track1.enableUpdates()

        self.failUnlessEqual(result, expected)

        # check that *only* (b, c) was added in the update
        self.failUnlessEqual(added, set([("b", "c")]))

        # check that *only* (d, e) was removed in the update
        self.failUnlessEqual(removed, set([("d", "e"), ("f", "g")]))

        # move c to a different layer. check that (b, c) transition is removed

        track1.disableUpdates()
        added = set()
        removed = set()

        objs["c"].priority = 1
        expected = [("a", "b")]
        track1.enableUpdates()

        self.failUnlessEqual(result, expected)
        self.failUnlessEqual(added, set())
        self.failUnlessEqual(removed, set([("b", "c")]))

    def testTrackObjectStagger(self):
        factory = self.factory
        stream = self.stream
        track1 = self.track1

        test_data = [
            ("a", 0, 10),
            ("b", 8, 18),
            ("c", 16, 26),
            ("d", 24, 32),
            ("e", 30, 40),
            ("f", 38, 48),
            # ---
            ("g", 50, 60),
            ("h", 58, 68),
            # ---
            ("i", 70, 80),
            # ---
            ("j", 80, 90),
            ("k", 88, 98),
            # ---
            ("l", 100, 110),
        ]

        transitions = ["ab", "cd", "ef", "gh", "ik"]

        objs = {}
        names = {}

        def addClip(name, start, end):
            obj = SourceTrackObject(factory, stream)
            obj.start = start * gst.SECOND
            obj.in_point = 0
            obj.duration = end * gst.SECOND - obj.start
            obj.media_duration = obj.duration
            obj.name = name
            names[obj] = name
            objs[name] = obj
            track1.addTrackObject(obj)

        for name, start, end in test_data:
            addClip(name, start, end)

        def verify_result(expected):
            expected_stagger = [(name, pos % 2) for name, pos in
                zip(*expected)]

            result = ["", []]
            for obj in track1.track_objects:
                result[0] += names[obj]
                result[1].append(obj._position) 
            resulting_stagger = [(names[obj], obj._stagger) for obj in
                track1.track_objects]
            self.failUnlessEqual(result, expected)
            self.failUnlessEqual(resulting_stagger, expected_stagger)

        # check that intiial configuration matches

        expected = ["abcdefghijkl", [0, 1, 2, 3, 4, 5, 6, 7, 0, 8, 9,0]]
        verify_result(expected)

        # remove a clip, which removes its associated transition

        track1.removeTrackObject(objs["e"])
        expected = ["abcdfghijkl", [0, 1, 2, 3, 5, 4, 5, 0, 6, 7, 0]]
        verify_result(expected)

        # add a clip

        addClip('m', 16, 17)
        expected = ["abcmdfghijkl", [0, 1, 2, 0, 3, 5, 4, 5, 0, 6, 7, 0]]
        verify_result(expected)
 
        # re-order a few clips

        track1.disableUpdates()
        objs["d"].start = 18 * gst.SECOND
        objs["i"].start = 25 * gst.SECOND
        track1.enableUpdates()
        expected = ["abcmdifghjkl", [0, 1, 2, 0, 3, 0, 5, 2, 3, 4, 5, 0]]
        verify_result(expected)
