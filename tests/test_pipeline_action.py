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
from pitivi.pipeline import Pipeline, STATE_READY, STATE_PLAYING, STATE_NULL
from pitivi.action import Action, STATE_ACTIVE, STATE_NOT_ACTIVE, ActionError
from pitivi.stream import MultimediaStream, VideoStream
from pitivi.factories.test import VideoTestSourceFactory
from common import TestCase
import common
import gst

class DynamicAction(Action):
    def getDynamicLinks(self, producer, stream):
        links = Action.getDynamicLinks(self, producer, stream)
        consumer = common.FakeSinkFactory()

        links.append((producer, consumer, stream, None))
        gst.debug("Returning link")
        return links

class TestPipelineAction(TestCase):

    def setUp(self):
        gst.debug("Test starting")
        TestCase.setUp(self)

    def testPipelineAction(self):
        """Testing pipeline state interaction"""
        p = Pipeline()
        a = Action()
        src = VideoTestSourceFactory()
        sink = common.FakeSinkFactory()
        sink.addInputStream(MultimediaStream(gst.Caps("any"), pad_name="sink"))

        # set the Action on the Pipeline
        p.setAction(a)
        self.assertEquals(p.actions, [a])

        # set the Producer and Consumer
        a.addProducers(src)
        a.addConsumers(sink)

        a.setLink(src, sink)

        # activate the Action
        a.activate()

        self.failUnlessEqual(src.current_bins, 1)
        self.failUnlessEqual(sink.current_bins, 1)

        # call get*ForFactoryStream(..., automake=False). They will raise
        # exceptions if the action didn't create the elements.
        bin = p.getBinForFactoryStream(src, automake=False)
        p.releaseBinForFactoryStream(src)

        tee = p.getTeeForFactoryStream(src, automake=False)
        p.releaseTeeForFactoryStream(src)

        bin = p.getBinForFactoryStream(sink, automake=False)

        queue = p.getQueueForFactoryStream(sink, automake=False)

        self.failUnlessEqual(queue.get_pad('src').get_peer().get_parent(), bin)

        p.releaseBinForFactoryStream(sink)
        p.releaseQueueForFactoryStream(sink)

        # switch to PLAYING
        p.setState(STATE_PLAYING)

        # wait half a second

        # switch to READY
        p.setState(STATE_READY)

        # deactivate action
        a.deactivate()

        # since we're the last Action to be release, the tees
        # and queues should have gone
        self.failUnlessEqual(src.current_bins, 0)
        self.failUnlessEqual(sink.current_bins, 0)

        # remove the action from the pipeline
        p.removeAction(a)

        # the gst.Pipeline should be empty !
        self.assertEquals(list(p._pipeline.elements()), [])

        p.release()

    def testPendingLink(self):
        a = Action()
        p = Pipeline()
        src = common.FakeGnlFactory()
        src.addOutputStream(VideoStream(gst.Caps("video/x-raw-yuv"),
                                        pad_name="src"))
        sink = common.FakeSinkFactory()
        sink.addInputStream(MultimediaStream(gst.Caps("any"),
                                             pad_name="sink"))

        # set the link, it will be activated once the pad is added
        a.setLink(src, sink)
        # Let's see if the link is present
        self.assertEquals(a._links, [(src, sink, None, None)])

        p.setAction(a)

        gst.debug("about to activate action")
        a.activate()
        # only the producer and the consumer are created, the other elements are
        # created dinamically
        self.assertEquals(len(list(p._pipeline.elements())), 2)

        p.setState(STATE_PLAYING)
        time.sleep(1)
        # and make sure that all other elements were created (4)
        # FIXME  if it's failing here, run the test a few times trying to raise
        # the time.sleep() above, it may just be racy...
        self.assertEquals(len(list(p._pipeline.elements())), 4)

        a.deactivate()
        p.setState(STATE_NULL)
        self.assertEquals(len(list(p._pipeline.elements())), 0)
        p.release()


    def testDynamicLink(self):
        a = DynamicAction()
        p = Pipeline()
        src = common.FakeGnlFactory()
        src.addOutputStream(VideoStream(gst.Caps("video/x-raw-yuv"),
                                        pad_name="src"))

        # the link will be added dynamically
        self.assertEquals(a._links, [])

        p.setAction(a)
        a.addProducers(src)

        self.assertEquals(len(list(p._pipeline.elements())), 0)

        a.activate()
        # theoretically... there shouldn't only be the source, since
        # the pad for the source hasn't been created yet (and therefore not
        # requiring a consumer
        self.assertEquals(len(list(p._pipeline.elements())), 1)

        p.setState(STATE_PLAYING)
        time.sleep(1)
        p.getState()

        # and make sure that all other elements were created (4)
        self.assertEquals(len(list(p._pipeline.elements())), 4)

        p.setState(STATE_READY)
        time.sleep(1)
        a.deactivate()

        self.assertEquals(len(list(p._pipeline.elements())), 0)
        p.setState(STATE_NULL)

        p.release()

if __name__ == "__main__":
    main()
