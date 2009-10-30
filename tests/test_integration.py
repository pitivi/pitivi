# PiTiVi , Non-linear video editor
#
#       tests/test_integration.py
#
# Copyright (c) 2008, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

"""Test pitivi core objects at the API level, simulating the UI input for
QA scenarios """

import unittest
TestCase = unittest.TestCase
from pitivi.application import InteractivePitivi
from pitivi.timeline.timeline import MoveContext, TrimStartContext,\
    TrimEndContext
from pitivi.signalinterface import Signallable
import pitivi.instance
import gobject
import os.path
import gst
import random

base_uri = "file:///" + os.getcwd() + "/media/"
test1 = base_uri + "test1.ogg"
test2 = base_uri + "test2.ogg"
test3 = base_uri + "test3.ogg"

class WatchDog(object):

    """A simple watchdog timer to aid developing integration tests. If
    keepAlive() is not called every <timeout> ms, then the watchdog timer will
    quit the specified mainloop."""

    def __init__(self, mainloop, timeout=10000):
        self.timeout = timeout
        self.mainloop = mainloop
        self.will_quit = False
        self.keep_going = True
        self.activated = False

    def start(self):
        self.will_quit = False
        self.keep_going = True
        gobject.timeout_add(self.timeout, self._timeoutcb)

    def suspend(self):
        self.keepAlive()
        self.keep_going = False

    def _timeoutcb(self):
        if self.will_quit:
            self.mainloop.quit()
            self.activated = True
            self.keep_going = False
        self.will_quit = True
        return self.keep_going

    def keepAlive(self):
        self.will_quit = False

class TestWatchdog(TestCase):

    def testWatchdog(self):
        self.ml = gobject.MainLoop()
        wd = WatchDog(self.ml, 100)
        self.timeout_called = False
        wd.start()
        gobject.timeout_add(2000, self._timeoutCb)
        self.ml.run()
        self.assertFalse(self.timeout_called)
        self.assertTrue(wd.activated)

    def testKeepAlive(self):
        self.ml = gobject.MainLoop()
        wd = WatchDog(self.ml, 2000)
        self.timeout_called = False
        wd.start()
        gobject.timeout_add(500, wd.keepAlive)
        gobject.timeout_add(2500, self._timeoutCb)
        self.ml.run()
        self.assertTrue(self.timeout_called)
        self.assertFalse(wd.activated)

    def testSuspend(self):
        self.ml = gobject.MainLoop()
        wd = WatchDog(self.ml, 500)
        self.timeout_called = False
        wd.start()
        wd.suspend()
        gobject.timeout_add(2000, self._timeoutCb)
        self.ml.run()
        self.assertTrue(self.timeout_called)
        self.assertFalse(wd.activated)

    def _timeoutCb(self):
        self.ml.quit()
        self.timeout_called = True
        return False

class Base(TestCase):
    """
    Creates and runs an InteractivePitivi object, then starts the mainloop.
    Uses a WatchDog to ensure that test cases will eventually terminate with an
    assertion failure if runtime errors occur inside the mainloop."""

    watchdog_timeout = 1000
    no_ui = True

    def setUp(self):
        TestCase.setUp(self)
        ptv = InteractivePitivi()
        # was the pitivi object created
        self.assert_(ptv)

        # were the contents of pitivi properly created
        self.assertEqual(ptv.current, None)

        # was the unique instance object properly set
        self.assertEquals(pitivi.instance.PiTiVi, ptv)
        self.ptv = ptv

        # setup a watchdog timer
        self.watchdog = WatchDog(ptv.mainloop, self.watchdog_timeout)

        # connect to the new-project-loaded signal
        self.ptv.connect("new-project-loaded", self._projectLoadedCb)

    def testPiTiVi(self):
        self.runPitivi()

    def runPitivi(self):
        self.watchdog.start()
        if self.no_ui:
            self.ptv.run(["--no-ui"])
        else:
            self.ptv.run([])

    def _projectLoadedCb(self, pitivi, project):
        gobject.idle_add(self.ptv.shutdown)

    def tearDown(self):
        # make sure we aren't exiting because our watchdog activated
        self.assertFalse(self.watchdog.activated)
        # make sure the instance has been unset
        self.assertEquals(pitivi.instance.PiTiVi, None)
        del self.ptv
        TestCase.tearDown(self)

class TestImport(Base):

    """Test discoverer, sourcelist, and project integration. When the new
    project loads, attempt to add both existing and non-existing sources. Make
    sure that an error is emitted when a source fails to load, and that
    source-added is emitted when sources are loaded successfully."""

    def setUp(self):
        self.factories = set()
        self.errors = set()
        Base.setUp(self)

    def _sourceAdded(self, sourcelist, factory):
        self.factories.add(factory.uri)

    def _discoveryError(self, sourcelist, uri, reason, unused):
        self.errors.add(uri)

    def _readyCb(self, soucelist):
        self.failUnlessEqual(self.factories, set((test1, test2)))
        self.failUnlessEqual(self.errors, set((test3,)))
        self.ptv.current._dirty = False
        self.ptv.shutdown()

    def _projectLoadedCb(self, pitivi, project):
        self.ptv.current.sources.connect("source-added", self._sourceAdded)
        self.ptv.current.sources.connect("discovery-error", self._discoveryError)
        self.ptv.current.sources.connect("ready", self._readyCb)
        self.ptv.current.sources.addUri(test1)
        self.ptv.current.sources.addUri(test2)
        self.ptv.current.sources.addUri(test3)

class TestTimeline(Base):

    """Base test case for tests involving the timeline. Imports several
    sources to the project and adds them to the timeline, optionally setting
    their start, media-start, and duration properties."""

    sources = (
        (
            "timelineObject1", 
            test1, 
            {
                "start" : 0,
                "duration" : gst.SECOND,
                "media-start" : gst.SECOND,
            }
        ),
        (
            "timelineObject2", 
            test2,
            {
                "start" : gst.SECOND,
                "duration" : gst.SECOND,
            }
        ),
    )

    def setUp(self):
        self.timelineObjects = set()
        Base.setUp(self)

    def _projectLoadedCb(self, pitivi, project):
        self.ptv.current.sources.connect("ready", self._readyCb)
        for name, uri, props in self.sources:
            self.ptv.current.sources.addUri(uri)

    def _timelineSetup(self):
        self.ptv.current.timeline.connect("timeline-object-added",
            self._timelineObjectAddedCb)

        for name, uri, props in self.sources:
            factory = self.ptv.current.sources.getUri(uri)
            if not factory:
                raise Exception("Could not find '%s' in sourcelist" %
                    source)
            timelineObject = self.ptv.current.timeline.addSourceFactory(factory)
            setattr(self, name, timelineObject)
            if not timelineObject:
                raise Exception("Could not add source '%s' to timeline" %
                    source)
            if props:
                for prop, value in props.iteritems():
                    setattr(timelineObject, prop, value)

    def _timelineObjectAddedCb(self, timeline, object):
        self.timelineObjects.add(object)

    def _readyCb(self, unused_sourcelist):
        self._timelineSetup()
        self._verifyTimeline()
        self._interactiveTest()

    def _interactiveTest(self):
        self.ptv.current._dirty = False
        self.ptv.shutdown()

    def _verifyTimeline(self):
        for name, uri, props in self.sources:
            timelineObject = getattr(self, name)
            if timelineObject:
                for prop, value in props.iteritems():
                    if not getattr(timelineObject, prop) == value:
                        raise Exception("'%s'.%s != %r" % (uri, prop, value))

    def scrubContext(self, context, finalTime, finalPriority, callback=None,
        delay=100, maxtime = 7200 * gst.SECOND, maxpriority =10, steps = 10):
        """ Scrubs an editing context as if a user were frantically dragging a
        clips with the mouse """

        self._scrubContext = context
        self._scrubTime = finalTime
        self._scrubPriority = finalPriority
        self._scrubMaxPriority = maxpriority
        self._scrubMaxTime = maxtime
        self._scrubCount = 0
        self._scrubSteps = steps
        self._scrubCallback = callback

        self.watchdog.keepAlive()
        gobject.timeout_add(delay, self._scrubTimeoutCb)

    def _scrubTimeoutCb(self):
        time_ = random.randint(0, self._scrubMaxTime)
        priority = random.randint(0, self._scrubMaxPriority)
        self._scrubContext.editTo(time_, priority)
        self._scrubCount += 1
        self.watchdog.keepAlive()

        if self._scrubCount < self._scrubSteps:
            return True
        else:
            self._scrubContext.editTo(self._scrubTime, self._scrubPriority)
            self._scrubCallback()
            return False

class TestMoveSources(TestTimeline):

    def _finish(self):
        self.context.finish()
        self.assertEquals(self.timelineObject1.start, 10 * gst.SECOND)
        self.assertEquals(self.timelineObject1.priority, 2)
        self.assertEquals(self.timelineObject2.start, 11 * gst.SECOND)
        self.assertEquals(self.timelineObject2.priority, 2)
        self.ptv.current.dirty = False
        self.ptv.shutdown()

    def _interactiveTest(self):
        timeline = self.ptv.current.timeline
        self.context = MoveContext(timeline, self.timelineObject1,
            set((self.timelineObject2,)))
        self.scrubContext(self.context, 10 * gst.SECOND, 2, self._finish)

if __name__ == "__main__":
    unittest.main()
