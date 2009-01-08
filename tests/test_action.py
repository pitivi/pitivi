# PiTiVi , Non-linear video editor
#
#       tests/test_action.py
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
from pitivi.pipeline import Pipeline
from pitivi.action import Action, STATE_ACTIVE, STATE_NOT_ACTIVE, ActionError

class TestAction(TestCase):

    def testBasic(self):
        # let's make sure Actions are properly created
        ac = Action()
        self.assertEquals(ac.state, STATE_NOT_ACTIVE)
        self.assertEquals(ac.producers, [])
        self.assertEquals(ac.consumers, [])
        self.assertEquals(ac.pipeline, None)

    def testPipeline(self):
        ac = Action()
        p = Pipeline()
        p2 = Pipeline()

        # set a Pipeline
        ac.setPipeline(p)
        self.assertEquals(ac.pipeline, p)

        # Setting a different Pipeline should fail...
        self.failUnlessRaises(ActionError, ac.setPipeline, p2)

        # ... but setting the same Pipeline again should silently succeed
        ac.setPipeline(p)

        # remove the Pipeline
        ac.unsetPipeline()
        self.assertEquals(ac.pipeline, None)

        # and now setting the other Pipeline should succeed
        ac.setPipeline(p2)
        self.assertEquals(ac.pipeline, p2)

