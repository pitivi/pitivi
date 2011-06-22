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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import gobject
gobject.threads_init()
import gst
from unittest import main
from pitivi.pipeline import Pipeline, STATE_NULL, STATE_READY, STATE_PAUSED, STATE_PLAYING, PipelineError
from pitivi.action import Action, STATE_ACTIVE, STATE_NOT_ACTIVE
from pitivi.stream import AudioStream, VideoStream
from common import TestCase, SignalMonitor, FakeSinkFactory, FakeEffectFactory
from pitivi.factories.test import VideoTestSourceFactory


class BogusAction(Action):
    pass


class WeirdAction(Action):
    pass


class TestPipeline(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        gst.debug("start")
        self.pipeline = Pipeline()
        self.monitor = SignalMonitor(self.pipeline, 'action-added',
                                     'action-removed', 'factory-added',
                                     'factory-removed', 'state-changed')
        self.assertEquals(self.monitor.action_added_count, 0)
        self.assertEquals(self.monitor.action_added_collect, [])

    def tearDown(self):
        self.pipeline.setState(STATE_NULL)
        self.pipeline.release()
        self.monitor.disconnectFromObj(self.pipeline)
        del self.pipeline
        del self.monitor
        TestCase.tearDown(self)

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

        # we can't remove active actions while in PAUSED/PLAYING
        self.pipeline.setState(STATE_PAUSED)
        ac1.state = STATE_ACTIVE
        self.assertEquals(self.pipeline.getState(), STATE_PAUSED)
        self.failUnlessRaises(PipelineError, self.pipeline.removeAction, ac1)

        # but we can remove deactivated actions while in PAUSED/PLAYING
        self.pipeline.setState(STATE_PAUSED)
        ac1.state = STATE_NOT_ACTIVE
        self.assertEquals(self.pipeline.getState(), STATE_PAUSED)
        self.pipeline.removeAction(ac1)

        # we can add actions while in PAUSED/PLAYING
        res = self.pipeline.addAction(ac2)
        self.assertEquals(res, ac2)
        self.assertEquals(self.pipeline.actions, [ac2])

        self.pipeline.removeAction(ac2)
        p2.release()

    def testStateChange(self):
        loop = gobject.MainLoop()

        bag = {"last_state": None}

        def state_changed_cb(pipeline, state, bag, loop):
            bag["last_state"] = state
            loop.quit()

        self.pipeline.connect('state-changed', state_changed_cb, bag, loop)

        # playing
        self.pipeline.setState(STATE_PLAYING)
        loop.run()
        self.failUnlessEqual(bag["last_state"], STATE_PLAYING)
        self.failUnlessEqual(self.pipeline.getState(), STATE_PLAYING)
        self.assertEquals(self.monitor.state_changed_count, 1)

        # playing again
        self.pipeline.setState(STATE_PLAYING)
        self.assertEquals(self.monitor.state_changed_count, 1)

        # ready
        self.pipeline.setState(STATE_READY)
        loop.run()
        self.failUnlessEqual(bag["last_state"], STATE_READY)
        self.failUnlessEqual(self.pipeline.getState(), STATE_READY)
        self.assertEquals(self.monitor.state_changed_count, 2)

        # PLAYING
        self.pipeline.play()
        loop.run()
        self.failUnlessEqual(bag["last_state"], STATE_PLAYING)
        self.failUnlessEqual(self.pipeline.getState(), STATE_PLAYING)
        self.assertEquals(self.monitor.state_changed_count, 3)

        # PAUSE
        self.pipeline.pause()
        loop.run()
        self.failUnlessEqual(bag["last_state"], STATE_PAUSED)
        self.failUnlessEqual(self.pipeline.getState(), STATE_PAUSED)
        self.assertEquals(self.monitor.state_changed_count, 4)

        self.pipeline.stop()
        loop.run()
        self.failUnlessEqual(bag["last_state"], STATE_READY)
        self.failUnlessEqual(self.pipeline.getState(), STATE_READY)
        self.assertEquals(self.monitor.state_changed_count, 5)

    def testGetReleaseBinForFactoryStream(self):
        factory = VideoTestSourceFactory()
        stream = VideoStream(gst.Caps('video/x-raw-rgb; video/x-raw-yuv'),
                'src0')
        factory.addOutputStream(stream)

        # try to get a cached instance
        self.failUnlessRaises(PipelineError,
                self.pipeline.getBinForFactoryStream, factory, stream, False)

        # create a bin
        bin1 = self.pipeline.getBinForFactoryStream(factory, stream, True)
        self.failUnless(isinstance(bin1, gst.Element))
        # return the cached instance
        bin2 = self.pipeline.getBinForFactoryStream(factory, stream, True)
        self.failUnlessEqual(id(bin1), id(bin2))

        self.pipeline.releaseBinForFactoryStream(factory, stream)
        self.pipeline.releaseBinForFactoryStream(factory, stream)

        # the bin has been destroyed at this point
        self.failUnlessRaises(PipelineError,
                self.pipeline.releaseBinForFactoryStream, factory, stream)

        # we should get a new instance
        bin2 = self.pipeline.getBinForFactoryStream(factory, stream, True)
        self.pipeline.releaseBinForFactoryStream(factory, stream)

    def testGetReleaseTeeForFactoryStream(self):
        factory = VideoTestSourceFactory()
        stream = VideoStream(gst.Caps('video/x-raw-rgb; video/x-raw-yuv'),
                'src')
        factory.addOutputStream(stream)

        self.failUnlessRaises(PipelineError,
            self.pipeline.getTeeForFactoryStream, factory, stream, True)

        # getBinForFactoryStream(factory, stream) must be called before
        self.failUnlessRaises(PipelineError,
            self.pipeline.getTeeForFactoryStream, factory, stream, True)

        # create the bin
        bin1 = self.pipeline.getBinForFactoryStream(factory, stream, True)

        # try to get a cached tee
        self.failUnlessRaises(PipelineError,
            self.pipeline.getTeeForFactoryStream, factory, stream, False)

        # create tee
        tee1 = self.pipeline.getTeeForFactoryStream(factory, stream, True)
        self.failUnless(isinstance(tee1, gst.Element))

        # get the cached instance
        tee2 = self.pipeline.getTeeForFactoryStream(factory, stream, True)
        self.failUnlessEqual(id(tee1), id(tee2))

        # release
        self.pipeline.releaseTeeForFactoryStream(factory, stream)

        # there's still a tee alive, so we can't release the bin
        #self.failUnlessRaises(PipelineError,
        #        self.pipeline.releaseBinForFactoryStream, factory, stream)

        self.pipeline.releaseTeeForFactoryStream(factory, stream)
        self.failUnlessRaises(PipelineError,
                self.pipeline.releaseTeeForFactoryStream, factory, stream)

        # should always fail with a sink bin
        factory2 = FakeSinkFactory()
        stream2 = VideoStream(gst.Caps('video/x-raw-rgb; video/x-raw-yuv'),
                'src')
        factory2.addInputStream(stream2)

        self.failUnlessRaises(PipelineError,
            self.pipeline.getTeeForFactoryStream, factory2, stream2, True)
        self.pipeline.releaseBinForFactoryStream(factory, stream)

    def testGetReleaseQueueForFactoryStream(self):
        factory = FakeSinkFactory()
        stream = VideoStream(gst.Caps('any'), 'sink')
        factory.addInputStream(stream)

        self.failUnlessRaises(PipelineError,
            self.pipeline.getQueueForFactoryStream, factory, stream, True)

        # getBinForFactoryStream(factory, stream) must be called before
        self.failUnlessRaises(PipelineError,
            self.pipeline.getQueueForFactoryStream, factory, stream, True)

        # create the bin
        bin1 = self.pipeline.getBinForFactoryStream(factory, stream, True)

        # try to get a cached queue
        self.failUnlessRaises(PipelineError,
            self.pipeline.getQueueForFactoryStream, factory, stream, False)

        # create queue
        queue1 = self.pipeline.getQueueForFactoryStream(factory, stream, True)
        self.failUnless(isinstance(queue1, gst.Element))

        gst.debug("pouet")

        # get the cached instance
        queue2 = self.pipeline.getQueueForFactoryStream(factory, stream, True)
        self.failUnlessEqual(id(queue1), id(queue2))

        # release
        self.pipeline.releaseQueueForFactoryStream(factory, stream)

        gst.debug("pouet")

        # there's still a queue alive, so we can't release the bin
        self.failUnlessRaises(PipelineError,
                self.pipeline.releaseBinForFactoryStream, factory, stream)

        self.pipeline.releaseQueueForFactoryStream(factory, stream)

        gst.debug("pouet2")
        self.failUnlessRaises(PipelineError,
                self.pipeline.releaseQueueForFactoryStream, factory, stream)

        # should always fail with a src bin
        factory2 = VideoTestSourceFactory()
        stream2 = VideoStream(gst.Caps('any'), 'src')
        factory2.addOutputStream(stream2)

        bin1 = self.pipeline.getBinForFactoryStream(factory, stream, True)
        self.failUnlessRaises(PipelineError,
            self.pipeline.getQueueForFactoryStream, factory2, stream2, True)
        self.pipeline.releaseBinForFactoryStream(factory, stream)

        self.pipeline.releaseBinForFactoryStream(factory, stream)
        self.assertEquals(factory.current_bins, 0)


if __name__ == "__main__":
    main()
