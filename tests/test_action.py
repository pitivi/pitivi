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
from pitivi.action import Action, STATE_ACTIVE, STATE_NOT_ACTIVE, ActionError, RenderAction
from pitivi.stream import MultimediaStream
from pitivi.factories.base import SourceFactory
from pitivi.encode import RenderSinkFactory, RenderFactory
from pitivi.settings import StreamEncodeSettings, RenderSettings
import common
import gst

class BinSourceFactory(SourceFactory):
    def _makeBin(self, output_stream=None):
        return gst.element_factory_make('bin')

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


    def testLinksSimple(self):
        """ Testing simple usage of Links """
        a = Action()
        src = common.FakeSourceFactory()
        src.addOutputStream(MultimediaStream(gst.Caps("any"), pad_name="src"))
        sink = common.FakeSinkFactory()
        sink.addInputStream(MultimediaStream(gst.Caps("any"), pad_name="sink"))

        a.setLink(src, sink)
        # Let's see if the link is present
        self.assertEquals(a._links, [(src, sink, None, None)])

        # It should have added both the producer and consumer
        self.assertEquals(a.producers, [src])
        self.assertEquals(a.consumers, [sink])

        # adding it again  should raise an exception
        self.failUnlessRaises(ActionError, a.setLink, src, sink)

        # remove the link
        a.removeLink(src, sink)
        self.assertEquals(a._links, [])


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

        self.failUnlessRaises(ActionError, ac.removeProducers, sink)
        self.failUnlessRaises(ActionError, ac.removeConsumers, src)
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

class TestRenderAction(TestCase):

    def setUp(self):
        self.vsrc = common.FakeSourceFactory("videotestsrc")
        self.vsrc.addOutputStream(MultimediaStream(gst.Caps("video/x-raw-yuv"),
                                                   pad_name="src"))
        self.asrc = common.FakeSourceFactory("audiotestsrc")
        self.asrc.addOutputStream(MultimediaStream(gst.Caps("audio/x-raw-float"),
                                                   pad_name="src"))
        self.vsettings = StreamEncodeSettings(encoder="theoraenc")
        self.asettings = StreamEncodeSettings(encoder="vorbisenc")

    def testSimple(self):
        """Tests a simple one stream encoding"""
        settings = RenderSettings(settings=[self.vsettings],
                                  muxer="oggmux")
        sf = RenderSinkFactory(RenderFactory(settings=settings),
                               common.FakeSinkFactory())
        a = RenderAction()
        a.addConsumers(sf)
        a.addProducers(self.vsrc)

        p = Pipeline()
        a.setPipeline(p)

        a.activate()



if __name__ == "__main__":
    main()
