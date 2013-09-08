# Pitivi video editor
#
#       tests/test_timeline_undo.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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


####
#
# FIXME: This should all be reimplemented after the port to GES
#
####

#from unittest import TestCase

#from gi.repository import Gst

#from pitivi.pipeline import Pipeline
#from pitivi.utils.timeline import Timeline, Clip, SELECT_ADD
#from pitivi.utils.track import Track, SourceTrackElement, BaseEffect
#from pitivi.factories.test import VideoTestSourceFactory, TestEffectFactory
#from pitivi.stream import VideoStream
#from pitivi.undo.timeline import TimelineLogObserver, \
        #ClipAdded, ClipRemoved, \
        #ClipPropertyChanged, EffectAdded
#from pitivi.undo.undo import UndoableActionLog

#class TestTimelineLogObserver(TimelineLogObserver):
    #def _connectToTimeline(self, timeline):
        #TimelineLogObserver._connectToTimeline(self, timeline)
        #timeline.connected = True

    #def _disconnectFromTimeline(self, timeline):
        #TimelineLogObserver._disconnectFromTimeline(self, timeline)
        #timeline.connected = False

    #def _connectToClip(self, clip):
        #TimelineLogObserver._connectToClip(self, clip)
        #clip.connected = True

    #def _disconnectFromClip(self, clip):
        #TimelineLogObserver._disconnectFromClip(self, clip)
        #clip.connected = False


#def new_stream():
    #return VideoStream(Gst.Caps("video/x-raw-rgb"))


#def new_source_factory():
    #return VideoTestSourceFactory()


#class TestTimelineLogObserverConnections(TestCase):
    #def setUp(self):
        #self.action_log = UndoableActionLog()
        #self.observer = TestTimelineLogObserver(self.action_log)

    #def testConnectionAndDisconnection(self):
        #timeline = Timeline()
        #stream = new_stream()
        #factory = new_source_factory()
        #track = Track(stream)
        #track_element1 = SourceTrackElement(factory, stream)
        #track.addTrackElement(track_element1)
        #timeline.addTrack(track)
        #clip1 = Clip(factory)
        #clip1.addTrackElement(track_element1)
        #timeline.addClip(clip1)

        #self.observer.startObserving(timeline)
        #self.failUnless(timeline.connected)
        #self.failUnless(clip1.connected)

        #timeline.removeClip(clip1)
        #self.failIf(clip1.connected)

        #timeline.addClip(clip1)
        #self.failUnless(clip1)

        #self.observer.stopObserving(timeline)
        #self.failIf(timeline.connected)
        #self.failIf(clip1.connected)


#class  TestTimelineUndo(TestCase):
    #def setUp(self):
        #self.stream = new_stream()
        #self.factory = new_source_factory()
        #self.effect_factory = TestEffectFactory(self.stream)
        #self.track1 = Track(self.stream)
        #self.track2 = Track(self.stream)
        #self.timeline = Timeline()
        #self.timeline.addTrack(self.track1)
        #self.timeline.addTrack(self.track2)
        #self.track_element1 = SourceTrackElement(self.factory, self.stream)
        #self.track_element2 = SourceTrackElement(self.factory, self.stream)
        #self.base_effect1 = BaseEffect(self.effect_factory, self.stream)
        #self.base_effect2 = BaseEffect(self.effect_factory, self.stream)
        #self.track1.addTrackElement(self.track_element1)
        #self.track2.addTrackElement(self.track_element2)
        #self.clip1 = Clip(self.factory)
        #self.clip1.addTrackElement(self.track_element1)
        #self.clip1.addTrackElement(self.track_element2)
        #self.action_log = UndoableActionLog()
        #self.observer = TestTimelineLogObserver(self.action_log)
        #self.observer.startObserving(self.timeline)

    #def testAddClip(self):
        #stacks = []

        #def commitCb(action_log, stack, nested):
            #stacks.append(stack)
        #self.action_log.connect("commit", commitCb)

        #self.action_log.begin("add clip")
        #self.timeline.addClip(self.clip1)
        #self.action_log.commit()

        #self.failUnlessEqual(len(stacks), 1)
        #stack = stacks[0]
        #self.failUnlessEqual(len(stack.done_actions), 1)
        #action = stack.done_actions[0]
        #self.failUnless(isinstance(action, ClipAdded))

        #self.failUnless(self.clip1 \
                #in self.timeline.clips)
        #self.action_log.undo()
        #self.failIf(self.clip1 \
                #in self.timeline.clips)

        #self.action_log.redo()
        #self.failUnless(self.clip1 \
                #in self.timeline.clips)

    #def testRemoveClip(self):
        #stacks = []

        #def commitCb(action_log, stack, nested):
            #stacks.append(stack)
        #self.action_log.connect("commit", commitCb)

        #self.timeline.addClip(self.clip1)
        #self.action_log.begin("remove clip")
        #self.timeline.removeClip(self.clip1, deep=True)
        #self.action_log.commit()

        #self.failUnlessEqual(len(stacks), 1)
        #stack = stacks[0]
        #self.failUnlessEqual(len(stack.done_actions), 1)
        #action = stack.done_actions[0]
        #self.failUnless(isinstance(action, ClipRemoved))

        #self.failIf(self.clip1 \
                #in self.timeline.clips)
        #self.action_log.undo()
        #self.failUnless(self.clip1 \
                #in self.timeline.clips)

        #self.action_log.redo()
        #self.failIf(self.clip1 \
                #in self.timeline.clips)

    #def testAddEffectToClip(self):
        #stacks = []
        #pipeline = Pipeline()

        #def commitCb(action_log, stack, nested):
            #stacks.append(stack)
        #self.action_log.connect("commit", commitCb)
        #self.observer.pipeline = pipeline

        ##FIXME Should I commit it and check there are 2 elements
        ##in the stacks
        #self.timeline.addClip(self.clip1)
        #self.track1.addTrackElement(self.base_effect1)

        #self.action_log.begin("add effect")
        #self.clip1.addTrackElement(self.base_effect1)
        #self.action_log.commit()

        #self.failUnlessEqual(len(stacks), 1)
        #stack = stacks[0]
        #self.failUnlessEqual(len(stack.done_actions), 1)
        #action = stack.done_actions[0]
        #self.failUnless(isinstance(action, EffectAdded))

        #self.failUnless(self.base_effect1 \
                #in self.clip1.track_elements)
        #self.failUnless(self.base_effect1 \
                #in self.track1.track_elements)
        #self.failUnless(len([effect for effect in \
                                #self.clip1.track_elements
                                #if isinstance(effect, BaseEffect)]) == 1)
        #self.failUnless(len([effect for effect in self.track1.track_elements
                             #if isinstance(effect, BaseEffect)]) == 1)

        #self.action_log.undo()
        #self.failIf(self.base_effect1 \
                #in self.clip1.track_elements)
        #self.failIf(self.base_effect1 \
                #in self.track1.track_elements)

        #self.action_log.redo()
        #self.failUnless(len([effect for effect in
                                #self.clip1.track_elements
                                #if isinstance(effect, BaseEffect)]) == 1)
        #self.failUnless(len([effect for effect in self.track1.track_elements
                             #if isinstance(effect, BaseEffect)]) == 1)

        #self.timeline.removeClip(self.clip1, deep=True)

    #def testClipPropertyChange(self):
        #stacks = []

        #def commitCb(action_log, stack, nested):
            #stacks.append(stack)
        #self.action_log.connect("commit", commitCb)

        #self.clip1.start = 5 * Gst.SECOND
        #self.clip1.duration = 20 * Gst.SECOND
        #self.timeline.addClip(self.clip1)
        #self.action_log.begin("modify clip")
        #self.clip1.start = 10 * Gst.SECOND
        #self.action_log.commit()

        #self.failUnlessEqual(len(stacks), 1)
        #stack = stacks[0]
        #self.failUnlessEqual(len(stack.done_actions), 1)
        #action = stack.done_actions[0]
        #self.failUnless(isinstance(action, ClipPropertyChanged))

        #self.failUnlessEqual(self.clip1.start, 10 * Gst.SECOND)
        #self.action_log.undo()
        #self.failUnlessEqual(self.clip1.start, 5 * Gst.SECOND)
        #self.action_log.redo()
        #self.failUnlessEqual(self.clip1.start, 10 * Gst.SECOND)

        #self.clip1.priority = 10
        #self.action_log.begin("priority change")
        #self.clip1.priority = 20
        #self.action_log.commit()

        #self.failUnlessEqual(self.clip1.priority, 20)
        #self.action_log.undo()
        #self.failUnlessEqual(self.clip1.priority, 10)
        #self.action_log.redo()
        #self.failUnlessEqual(self.clip1.priority, 20)

    #def testUngroup(self):
        #self.clip1.start = 5 * Gst.SECOND
        #self.clip1.duration = 20 * Gst.SECOND

        #self.timeline.addClip(self.clip1)
        #self.timeline.setSelectionToObj(self.track_element1, SELECT_ADD)

        #self.failUnlessEqual(len(self.timeline.clips), 1)
        #self.failUnlessEqual(self.timeline.clips[0].start,
                #5 * Gst.SECOND)
        #self.failUnlessEqual(self.timeline.clips[0].duration,
                #20 * Gst.SECOND)

        #self.action_log.begin("ungroup")
        #self.timeline.ungroupSelection()
        #self.action_log.commit()

        #self.failUnlessEqual(len(self.timeline.clips), 2)
        #self.failUnlessEqual(self.timeline.clips[0].start,
                #5 * Gst.SECOND)
        #self.failUnlessEqual(self.timeline.clips[0].duration,
                #20 * Gst.SECOND)
        #self.failUnlessEqual(self.timeline.clips[1].start,
                #5 * Gst.SECOND)
        #self.failUnlessEqual(self.timeline.clips[1].duration,
                #20 * Gst.SECOND)

        #self.action_log.undo()

        #self.failUnlessEqual(len(self.timeline.clips), 1)
        #self.failUnlessEqual(self.timeline.clips[0].start,
                #5 * Gst.SECOND)
        #self.failUnlessEqual(self.timeline.clips[0].duration,
                #20 * Gst.SECOND)
