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

from unittest import TestCase
from pitivi.pipeline import Pipeline, STATE_NULL, STATE_PLAYING
from pitivi.action import Action
from common import SignalMonitor

class BogusAction(Action):
    pass

class WeirdAction(Action):
    pass

class TestPipeline(TestCase):

    def setUp(self):
        self.pipeline = Pipeline()
        self.monitor = SignalMonitor(self.pipeline, 'action-added',
                                     'action-removed')
        self.assertEquals(self.monitor.action_added_count, 0)
        self.assertEquals(self.monitor.action_added_collect, [])

    def cleanUp(self):
        del self.pipeline

    def testAddRemoveActionSimple(self):
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

        # And now to remove it
        self.pipeline.removeAction(ac1)
        # the 'action-removed' signal should have been triggered once..
        self.assertEquals(self.monitor.action_removed_count, 1)
        # .. with the action as an argument
        self.assertEquals(self.monitor.action_removed_collect, [(ac1, )])
        # And there should be no actions left on the pipeline
        self.assertEquals(self.pipeline.actions, [])

    def testStateChange(self):
        self.pipeline.setState(STATE_PLAYING)
        # change should have happened instantly... except not, because
        # the bus is asynchronous. Not sure how to check that efficiently.
        #self.assertEquals(self.pipeline.state, STATE_PLAYING)
