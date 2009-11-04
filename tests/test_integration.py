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
from pitivi.stream import AudioStream, VideoStream
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

class Configuration(object):

    def __init__(self, *sources):
        self.sources = []
        for source in sources:
            self.addSource(*source)

    def addSource(self, name, uri, props=None, error=False):
        self.sources.append((name, uri, props))

    def addBadSource(self, name, uri):
        self.sources.append((name, uri))

    def getUris(self):
        return set((source[1] for source in self.sources))

    def getGoodUris(self):
        return set((source[1] for source in self.sources if
            len(source) > 2))

    def matches(self, instance_runner):
        for name, uri, props in self.sources:
            timelineObject = getattr(instance_runner, name)
            if timelineObject.factory.uri != uri:
                raise Exception("%s has wrong factory type!" % name)
            if timelineObject:
                for prop, value in props.iteritems():
                    if not getattr(timelineObject, prop) == value:
                        raise Exception("'%s'.%s != %r" % (uri, prop, value))

    def __iter__(self):
        return (source for source in self.sources if len(source) > 2)

class InstanceRunner(Signallable):

    no_ui = True

    class container(object):

        def __init__(self):
            pass

    __signals__ = {
        "sources-loaded" : [],
        "timeline-configured" : [],
        "scrub-done" : [],
    }

    def __init__(self, instance):
        self.instance = instance
        self.watchdog = WatchDog(instance.mainloop, 10000)
        self.factories = set()
        self.errors = set()
        self.project = None
        self.timeline = None
        self.tracks = {}
        self.pending_configuration = None
        self.scrubContext = None
        self.scrubTime = 0
        self.scrubPriority = 0
        self.scrubMaxPriority = 0
        self.scrubMaxTime = 0
        self.scrubCount = 0
        self.scrubSteps = 0
        self.audioTracks = 0
        self.videoTracks = 0
        instance.connect("new-project-loaded", self._newProjectLoadedCb)

    def loadConfiguration(self, configuration):
        self.pending_configuration = configuration

    def _newProjectLoadedCb(self, instance, project):
        self.project = instance.current
        self.timeline = self.project.timeline
        for track in self.timeline.tracks:
            self._trackAddedCb(self.timeline, track)
        self.project.sources.connect("source-added", self._sourceAdded)
        self.project.sources.connect("discovery-error", self._discoveryError)
        self.project.sources.connect("ready", self._readyCb)
        self.timeline.connect("track-added", self._trackAddedCb)

        if self.pending_configuration:
            self._loadSources(self.pending_configuration)

    def _sourceAdded(self, sourcelist, factory):
        self.factories.add(factory.uri)

    def _discoveryError(self, sourcelist, uri, reason, unused):
        self.errors.add(uri)

    def _readyCb(self, soucelist):
        assert self.factories == self.pending_configuration.getGoodUris()
        if self.pending_configuration:
            self._setupTimeline(self.pending_configuration)
        self.emit("sources-loaded")

    def _loadSources(self, configuration):
        for uri in configuration.getUris():
            self.project.sources.addUri(uri)

    def _trackAddedCb(self, timeline, track):
        if type(track.stream) is AudioStream:
            self.audioTracks += 1
            attrname = "audio%d" % self.audioTracks
        elif type(track.stream) is VideoStream:
            self.videoTracks += 1
            attrname = "video%d" % self.videoTracks
        container = self.container()
        setattr(self, attrname, container)
        self.tracks[track] = container 

    def _setupTimeline(self, configuration):
        for name, uri, props in configuration:
            factory = self.project.sources.getUri(uri)
            if not factory:
                raise Exception("Could not find '%s' in sourcelist" %
                    source)

            if not props:
                continue

            timelineObject = self.timeline.addSourceFactory(factory)
            setattr(self, name, timelineObject)
            for trackObject in timelineObject.track_objects:
                track = self.tracks[trackObject.track]
                setattr(track, name, trackObject)

            if not timelineObject:
                raise Exception("Could not add source '%s' to timeline" %
                    source)
            for prop, value in props.iteritems():
                setattr(timelineObject, prop, value)
        self.emit("timeline-configured")

    def scrub(self, context, finalTime, finalPriority, delay=100, maxtime = 7200 * gst.SECOND, maxpriority =10, steps = 10):
        """ Scrubs an editing context as if a user were frantically dragging a
        clips with the mouse """
 
        self.scrubContext = context
        self.scrubTime = finalTime
        self.scrubPriority = finalPriority
        self.scrubMaxPriority = maxpriority
        self.scrubMaxTime = maxtime
        self.scrubCount = 0
        self.scrubSteps = steps
 
        self.watchdog.keepAlive()
        gobject.timeout_add(delay, self._scrubTimeoutCb)
 
    def _scrubTimeoutCb(self):
        time_ = random.randint(0, self.scrubMaxTime)
        priority = random.randint(0, self.scrubMaxPriority)
        self.scrubContext.editTo(time_, priority)
        self.scrubCount += 1
        self.watchdog.keepAlive()
 
        if self.scrubCount < self.scrubSteps:
            return True
        else:
            self.scrubContext.editTo(self.scrubTime, self.scrubPriority)
            self.scrubContext.finish()
            self.emit("scrub-done")
            return False

    def run(self):
        self.watchdog.start()
        if self.no_ui:
            self.instance.run(["--no-ui"])
        else:
            self.instance.run([])

class Base(TestCase):
    """
    Creates and runs an InteractivePitivi object, then starts the mainloop.
    Uses a WatchDog to ensure that test cases will eventually terminate with an
    assertion failure if runtime errors occur inside the mainloop."""

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

        # create an instance runner
        self.runner = InstanceRunner(ptv)

    def tearDown(self):
        # make sure we aren't exiting because our watchdog activated
        self.assertFalse(self.runner.watchdog.activated)
        # make sure the instance has been unset
        self.assertEquals(pitivi.instance.PiTiVi, None)
        del self.ptv
        del self.runner
        TestCase.tearDown(self)

    def testWatchdog(self):
        self.runner.run()
        self.assertTrue(self.runner.watchdog.activated)
        self.runner.watchdog.activated = False

    def testBasic(self):

        def newProjectLoaded(pitivi, project):
            gobject.idle_add(self.ptv.shutdown)

        self.ptv.connect("new-project-loaded", newProjectLoaded)
        self.runner.run()

    def testImport(self):

        def sourcesLoaded(runner):
            gobject.idle_add(self.ptv.shutdown)

        config = Configuration()
        config.addSource("test1", test1)
        config.addSource("test2", test2)
        config.addBadSource("test3", test3)

        self.runner.connect("sources-loaded", sourcesLoaded)
        self.runner.loadConfiguration(config)
        self.runner.run()

        self.assertFalse(hasattr(self.runner,test1))
        self.assertFalse(hasattr(self.runner,test2))
        self.failUnlessEqual(self.runner.factories, set((test1, test2)))
        self.failUnlessEqual(self.runner.errors, set((test3,)))

    def testConfigureTimeline(self):
 
        config = Configuration()
        config.addSource(
            "object1", 
            test1, 
            {
                "start" : 0,
                "duration" : gst.SECOND,
                "media-start" : gst.SECOND,
            })
        config.addSource(
            "object2", 
            test2,
            {
                "start" : gst.SECOND,
                "duration" : gst.SECOND,
            })
 
        def timelineConfigured(runner):
            config.matches(self.runner)
            gobject.idle_add(self.ptv.shutdown)
 
        self.runner.loadConfiguration(config)
        self.runner.connect("timeline-configured", timelineConfigured)
        self.runner.run()

        self.assertTrue(self.runner.object1)
        self.assertTrue(self.runner.object2)
        self.assertTrue(self.runner.video1.object1)
        self.assertTrue(self.runner.audio1.object2)

    def testMoveSources(self):
        initial = Configuration()
        initial.addSource(
            "object1", 
            test1, 
            {
                "start" : 0,
                "duration" : gst.SECOND,
                "media-start" : gst.SECOND,
                "priority" : 0
            })
        initial.addSource(
            "object2", 
            test2,
            {
                "start" : gst.SECOND,
                "duration" : gst.SECOND,
                "priority" : 1,
            })
        final = Configuration()
        final.addSource(
            "object1",
            test1,
            {
                "start" : 10 * gst.SECOND,
            })
        final.addSource(
            "object2",
            test2,
            {
                "start" : 11 * gst.SECOND,
                "priority" : 2,
            })

        def timelineConfigured(runner):
            context = MoveContext(self.runner.timeline, 
                self.runner.video1.object1,
                set((self.runner.audio1.object2,)))
            self.runner.scrub(context, 10 * gst.SECOND, 1, steps=10)

        def scrubDone(runner):
            final.matches(runner)
            gobject.idle_add(self.ptv.shutdown)

        self.runner.loadConfiguration(initial)
        self.runner.connect("timeline-configured", timelineConfigured)
        self.runner.connect("scrub-done", scrubDone)

        self.runner.run()

if __name__ == "__main__":
    unittest.main()
