# PiTiVi , Non-linear video editor
#
#       tests/test_pipeline.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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

from unittest import TestCase, main
from pitivi.pipeline import Pipeline, STATE_NULL, STATE_READY, STATE_PAUSED, STATE_PLAYING, PipelineError
from pitivi.action import Action
from common import SignalMonitor, FakeSourceFactory, FakeSinkFactory

class BogusAction(Action):
    pass

class WeirdAction(Action):
    pass

class TestPipeline(TestCase):

    def setUp(self):
        self.pipeline = Pipeline()
        self.monitor = SignalMonitor(self.pipeline, 'action-added',
                                     'action-removed', 'factory-added',
                                     'factory-removed', 'state-changed')
        self.assertEquals(self.monitor.action_added_count, 0)
        self.assertEquals(self.monitor.action_added_collect, [])

    def cleanUp(self):
        self.pipeline.setState(STATE_NULL)
        del self.pipeline

    def testAddRemoveActionSimple(self):
        """ Simple add/remove of Actions """
        ac1 = BogusAction()

        # add the action to the pipeline
        res = self.pipeline.addAction(ac1)
        # the returned value should be the given action
        self.assertEquals(res, ac1)
        # it should now be in the list of actions...
        self.failUnlessEqual(self.pipeline.actions, [ac1])
        # ... and the action should be set to that pipeline
        self.failUnlessEqual(ac1.pipeline, self.pipeline)
        # the 'action-added' signal should be triggered once
        self.assertEquals(self.monitor.action_added_count, 1)
        # And it contained our action
        self.assertEquals(self.monitor.action_added_collect, [(ac1, )])

        # if we try to add that action again, it should be silently ignored
        res = self.pipeline.addAction(ac1)
        self.assertEquals(res, ac1)
        # the list of actions shouldn't have changed
        self.failUnlessEqual(self.pipeline.actions, [ac1])
        # it shouldn't have changed the pipeline set on action
        self.failUnlessEqual(ac1.pipeline, self.pipeline)
        # the 'action-added' signal should NOT have been triggered again
        self.assertEquals(self.monitor.action_added_count, 1)

        # And now to remove it
        self.pipeline.removeAction(ac1)
        # the 'action-removed' signal should have been triggered once..
        self.assertEquals(self.monitor.action_removed_count, 1)
        # .. with the action as an argument
        self.assertEquals(self.monitor.action_removed_collect, [(ac1, )])
        # And there should be no actions left on the pipeline
        self.assertEquals(self.pipeline.actions, [])

    def testAddRemoveActionAdvanced(self):
        """ Advanced add/remove of Actions """
        ac1 = BogusAction()
        ac2 = BogusAction()
        p2 = Pipeline()

        res = self.pipeline.addAction(ac1)
        self.assertEquals(self.pipeline.actions, [ac1])

        # we can't add an action to two pipelines at the same time
        self.failUnlessRaises(PipelineError, p2.addAction, ac1)

        self.pipeline.removeAction(ac1)
        self.assertEquals(self.pipeline.actions, [])

        res = self.pipeline.setAction(ac1)
        self.assertEquals(res, ac1)
        self.assertEquals(self.pipeline.actions, [ac1])
        # calling setAction while a similar action is already set should
        # return the existing action and not change anything else
        res = self.pipeline.setAction(ac2)
        self.assertEquals(res, ac1)
        self.assertEquals(self.pipeline.actions, [ac1])

        # we can't remove actions while in PAUSED/PLAYING
        self.pipeline.setState(STATE_PAUSED)
        self.assertEquals(self.pipeline.state, STATE_PAUSED)
        self.failUnlessRaises(PipelineError, self.pipeline.removeAction, ac1)

        # but we can add some
        res = self.pipeline.addAction(ac2)
        self.assertEquals(res, ac2)
        self.assertEquals(self.pipeline.actions, [ac1, ac2])

    def testStateChange(self):
        """ State Changes """
        self.pipeline.setState(STATE_PLAYING)
        # change should have happened instantly... except not, because
        # the bus is asynchronous. We are therefore not guaranteed when
        # the message will be received on the mainloop bus.
        # Not sure how to check that efficiently.
        self.assertEquals(self.pipeline.getState(), STATE_PLAYING)
        self.assertEquals(self.pipeline.state, STATE_PLAYING)

        # the 'state-changed' signal should have been emitted with the
        # correct state
        self.assertEquals(self.monitor.state_changed_count, 1)
        self.assertEquals(self.monitor.state_changed_collect, [(STATE_PLAYING, )])

        # Setting to the same state again shouldn't change anything
        self.pipeline.setState(STATE_PLAYING)
        self.assertEquals(self.pipeline.getState(), STATE_PLAYING)
        self.assertEquals(self.pipeline.state, STATE_PLAYING)
        self.assertEquals(self.monitor.state_changed_count, 1)
        self.assertEquals(self.monitor.state_changed_collect, [(STATE_PLAYING, )])

        # back to NULL
        self.pipeline.setState(STATE_NULL)
        self.assertEquals(self.pipeline.getState(), STATE_NULL)
        self.assertEquals(self.pipeline.state, STATE_NULL)
        self.assertEquals(self.monitor.state_changed_count, 2)
        self.assertEquals(self.monitor.state_changed_collect, [(STATE_PLAYING, ),
                                                               (STATE_NULL, )])

        # .play()
        self.pipeline.play()
        self.assertEquals(self.pipeline.getState(), STATE_PLAYING)
        self.assertEquals(self.pipeline.state, STATE_PLAYING)
        self.assertEquals(self.monitor.state_changed_count, 3)
        self.assertEquals(self.monitor.state_changed_collect, [(STATE_PLAYING, ),
                                                               (STATE_NULL, ),
                                                               (STATE_PLAYING, )])

        # .pause()
        self.pipeline.pause()
        self.assertEquals(self.pipeline.getState(), STATE_PAUSED)
        self.assertEquals(self.pipeline.state, STATE_PAUSED)
        self.assertEquals(self.monitor.state_changed_count, 4)
        self.assertEquals(self.monitor.state_changed_collect, [(STATE_PLAYING, ),
                                                               (STATE_NULL, ),
                                                               (STATE_PLAYING, ),
                                                               (STATE_PAUSED, )])

        # .stop()
        self.pipeline.stop()
        self.assertEquals(self.pipeline.getState(), STATE_READY)
        self.assertEquals(self.pipeline.state, STATE_READY)
        self.assertEquals(self.monitor.state_changed_count, 5)
        self.assertEquals(self.monitor.state_changed_collect, [(STATE_PLAYING, ),
                                                               (STATE_NULL, ),
                                                               (STATE_PLAYING, ),
                                                               (STATE_PAUSED, ),
                                                               (STATE_READY, )])

    def testAddRemoveFactoriesSimple(self):
        """ Test adding and removing factories without any
        Actions involved"""
        src = FakeSourceFactory()
        sink = FakeSinkFactory()

        ## ADDING FACTORIES
        # We can't set factories on pipelines that are in
        # PAUSED or PLAYING
        self.pipeline.setState(STATE_PAUSED)
        self.assertEquals(self.pipeline.getState(), STATE_PAUSED)
        self.failUnlessRaises(PipelineError, self.pipeline.addFactory, src)
        self.pipeline.setState(STATE_PLAYING)
        self.assertEquals(self.pipeline.getState(), STATE_PLAYING)
        self.failUnlessRaises(PipelineError, self.pipeline.addFactory, src)

        # let's add some factories
        self.pipeline.setState(STATE_NULL)
        self.assertEquals(self.pipeline.getState(), STATE_NULL)
        self.pipeline.addFactory(src)
        self.assertEquals(self.pipeline.factories, [src])
        self.pipeline.addFactory(sink)
        self.assertEquals(self.pipeline.factories, [src, sink])

        # adding the same factory again doesn't do anything
        # FIXME : Does that make sense ???
        self.pipeline.addFactory(sink)
        self.assertEquals(self.pipeline.factories, [src, sink])

        ## REMOVE FACTORIES
        # can't remove factories in PAUSED or PLAYING
        self.pipeline.setState(STATE_PAUSED)
        self.assertEquals(self.pipeline.getState(), STATE_PAUSED)
        self.failUnlessRaises(PipelineError, self.pipeline.removeFactory, src)
        self.pipeline.setState(STATE_PLAYING)
        self.assertEquals(self.pipeline.getState(), STATE_PLAYING)
        self.failUnlessRaises(PipelineError, self.pipeline.removeFactory, src)

        self.pipeline.setState(STATE_NULL)
        self.assertEquals(self.pipeline.getState(), STATE_NULL)
        self.pipeline.removeFactory(src)
        self.assertEquals(self.pipeline.factories, [sink])
        # removing the same factory twice shouldn't do anything
        self.pipeline.removeFactory(src)
        self.assertEquals(self.pipeline.factories, [sink])

        self.pipeline.removeFactory(sink)
        self.assertEquals(self.pipeline.factories, [])

if __name__ == "__main__":
    main()

