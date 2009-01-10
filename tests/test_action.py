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

from unittest import TestCase, main
from pitivi.pipeline import Pipeline, STATE_READY, STATE_PLAYING
from pitivi.action import Action, STATE_ACTIVE, STATE_NOT_ACTIVE, ActionError
from pitivi.stream import MultimediaStream
import common
import gst

class TestAction(TestCase):

    def testBasic(self):
        # let's make sure Actions are properly created
        ac = Action()
        self.assertEquals(ac.state, STATE_NOT_ACTIVE)
        self.assertEquals(ac.producers, [])
        self.assertEquals(ac.consumers, [])
        self.assertEquals(ac.pipeline, None)

    def testPipelineSimple(self):
        """ Test setPipeline and unsetPipeline """
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

        # remove the Pipeline again
        ac.unsetPipeline()
        self.assertEquals(ac.pipeline, None)

        # internally set the state to ACTIVE
        ac.state = STATE_ACTIVE
        # now setting any Pipeline should fail !
        self.failUnlessRaises(ActionError, ac.setPipeline, p)

        # internally set the state to NOT_ACTIVE
        ac.state = STATE_NOT_ACTIVE
        self.assertEquals(ac.isActive(), False)

        # Set a pipeline
        ac.setPipeline(p)
        self.assertEquals(ac.pipeline, p)

        # interally set the state to ACTIVE
        ac.state = STATE_ACTIVE
        # we shouldn't be able to unset a pipeline from an active Action
        self.failUnlessRaises(ActionError, ac.unsetPipeline)

    def testPipelineAction(self):
        """Testing pipeline state interaction"""
        p = Pipeline()
        a = Action()
        src = common.FakeSourceFactory()
        src.addOutputStream(MultimediaStream(gst.Caps("any"), pad_name="src"))
        sink = common.FakeSinkFactory()
        sink.addInputStream(MultimediaStream(gst.Caps("any"), pad_name="sink"))

        # set the Action on the Pipeline
        p.setAction(a)
        self.assertEquals(p.actions, [a])

        # set the Producer and Consumer
        a.addProducers(src)
        a.addConsumers(sink)

        # set the factories on the Pipeline
        p.addFactory(src, sink)

        # activate the Action
        a.activate()

        # check that all internal objects are created
        # TODO : Add more extensive testing of gst-specific Pipeline
        # methods in test_pipeline.py
        self.assert_(src in p.bins.keys())
        self.assert_(isinstance(p.bins[src], gst.Element))
        self.assert_(sink in p.bins.keys())
        self.assert_(isinstance(p.bins[sink], gst.Element))

        # check that the tees were properly created
        def has_tee(pipeline, factories):
            left = factories[:]
            for f in factories:
                for ps, t in pipeline.tees.iteritems():
                    fact, st = ps
                    if fact in left:
                        left.remove(fact)
            return left
        self.assertEquals(has_tee(p, [src]), [])

        # check that the queues were properly created
        def has_queue(pipeline, factories):
            left = factories[:]
            for f in factories:
                for ps, t in pipeline.queues.iteritems():
                    fact, st = ps
                    if fact in left:
                        left.remove(fact)
            return left
        self.assertEquals(has_queue(p, [sink]), [])

        # check that the tees are linked to the proper queues

        # switch to PLAYING
        p.setState(STATE_PLAYING)

        # wait half a second

        # switch to READY
        p.setState(STATE_READY)

        # deactivate action
        a.deactivate()

        # since we're the last Action to be release, the tees
        # and queues should have gone
        self.assertEquals(p.tees, {})
        self.assertEquals(p.queues, {})

        # remove the action from the pipeline
        p.removeAction(a)

        # remove factories from Pipeline
        p.removeFactory(src, sink)

        # the gst.Pipeline should be empty !
        self.assertEquals(list(p._pipeline.elements()), [])

    def test_isActive(self):
        """ Test isActive() """
        ac = Action()

        self.assertEquals(ac.isActive(), False)

        # Here we cheat, setting manually the state !
        ac.state = STATE_ACTIVE

        self.assertEquals(ac.isActive(), True)

    def testSettingFactoriesSimple(self):
        """Simple add/remove Factory tests"""
        ac = Action()
        p = Pipeline()

        src = common.FakeSourceFactory()
        sink = common.FakeSinkFactory()

        # you can't set a Sink element as a producer
        self.failUnlessRaises(ActionError, ac.addProducers, sink)
        # you can't set a Source element as a consumer
        self.failUnlessRaises(ActionError, ac.addConsumers, src)

        # if the action is active, you can't add anything
        ac.state = STATE_ACTIVE
        self.failUnlessRaises(ActionError, ac.addProducers, src)
        self.failUnlessRaises(ActionError, ac.addConsumers, sink)
        ac.state = STATE_NOT_ACTIVE

        # Set a producer and consumer on the action
        ac.addProducers(src)
        ac.addConsumers(sink)

        self.assertEquals(ac.producers, [src])
        self.assertEquals(ac.consumers, [sink])

        # remove a sink from producers should not do anything
        ac.removeProducers(sink)
        self.assertEquals(ac.producers, [src])
        self.assertEquals(ac.consumers, [sink])

        # remove a source from consumers should not do anything
        ac.removeConsumers(src)
        self.assertEquals(ac.producers, [src])
        self.assertEquals(ac.consumers, [sink])

        # you can't remove anything from an active action
        ac.state = STATE_ACTIVE
        self.failUnlessRaises(ActionError, ac.removeProducers, src)
        self.failUnlessRaises(ActionError, ac.removeConsumers, sink)
        ac.state = STATE_NOT_ACTIVE

        # finally, attempt correct removal
        ac.removeProducers(src)
        self.assertEquals(ac.producers, [])
        self.assertEquals(ac.consumers, [sink])

        ac.removeConsumers(sink)
        self.assertEquals(ac.producers, [])
        self.assertEquals(ac.consumers, [])

if __name__ == "__main__":
    main()
