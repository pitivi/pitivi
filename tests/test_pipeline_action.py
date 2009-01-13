# PiTiVi , Non-linear video editor
#
#       tests/test_pipeline_action.py
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

"""
Tests for interaction between action and pipeline
"""

import time
from unittest import TestCase, main
from pitivi.pipeline import Pipeline, STATE_READY, STATE_PLAYING
from pitivi.action import Action, STATE_ACTIVE, STATE_NOT_ACTIVE, ActionError
from pitivi.stream import MultimediaStream, VideoStream
import common
import gst

class TestPipelineAction(TestCase):

    def setUp(self):
        gst.debug("Test starting")

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

    def testDynamicProducer(self):
        a = Action()
        p = Pipeline()
        src = common.FakeGnlFactory()
        src.addOutputStream(VideoStream(gst.Caps("video/x-raw-yuv"),
                                        pad_name="src"))
        sink = common.FakeSinkFactory()
        sink.addInputStream(MultimediaStream(gst.Caps("any"),
                                             pad_name="sink"))
        a.setLink(src, sink)
        # Let's see if the link is present
        self.assertEquals(a._links, [(src, sink, None, None)])

        p.setAction(a)
        p.addFactory(src, sink)

        gst.debug("about to activate action")
        a.activate()
        # theoretically... there shouldn't only be the source, since
        # the pad for the source hasn't been created yet (and therefore not
        # requiring a consumer
        self.assert_(src in p.bins.keys())
        self.assert_(sink not in p.bins.keys())

        p.setState(STATE_PLAYING)
        time.sleep(0.5)
        p.getState()
        self.assert_(src in p.bins.keys())
        self.assert_(sink in p.bins.keys())
        # and make sure that all other elements were created (4)
        self.assertEquals(len(list(p._pipeline.elements())), 4)

if __name__ == "__main__":
    main()
