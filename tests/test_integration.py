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
        self.source_map = {}
        for source in sources:
            self.addSource(*source)

    def clone(self):
        ret = Configuration()
        for source in self.sources:
            if len(source) == 3:
                name, uri, props = source
                ret.addSource(name, uri, dict(props))
            if len(source) == 2:
                ret.addBadSource(*source)
        return ret

    def addSource(self, name, uri, props=None, error=False):
        if name in self.source_map:
            raise Exception("Duplicate source: '%d' already defined" % name)
        self.sources.append((name, uri, props))
        self.source_map[name] = uri, props

    def updateSource(self, name, uri=None, props=None):
        def findSource(name):
            for i, source in enumerate(self.sources):
                if source[0] == name:
                    return i
            raise Exception("Source %s not in configuration" %
                name)

        i = findSource(name)
        name, orig_uri, orig_props = self.sources[i]
        if not uri:
            uri = orig_uri
        if props:
            orig_props.update(props)

        self.sources[i] = (name, uri, orig_props)
        self.source_map[name] = (uri, orig_props)

    def addBadSource(self, name, uri):
        if name in self.source_map:
            raise Exception("Duplicate source: '%d' already defined" % name)
        self.sources.append((name, uri))
        self.source_map[name] = uri, None

    def getUris(self):
        return set((source[1] for source in self.sources))

    def getGoodUris(self):
        return set((source[1] for source in self.sources if
            len(source) > 2))

    def getGoodSources(self):
        return (source for source in self.sources if len(source) > 2)

    def matches(self, instance_runner):
        for name, uri, props in self.getGoodSources():
            if not hasattr(instance_runner, name):
                raise Exception("Project missing source %s" % name)
            timelineObject = getattr(instance_runner, name)
            if timelineObject.factory.uri != uri:
                raise Exception("%s has wrong factory type!" % name)
            if timelineObject:
                for prop, value in props.iteritems():
                    actual = getattr(timelineObject, prop)
                    if not actual == value:
                        raise Exception("%s.%s: %r != %r" % (name, prop,
                            actual, value))

        names = set((source[0] for source in self.getGoodSources()))
        timelineObjects = set(instance_runner.timelineObjects.iterkeys())
        if names != timelineObjects:
            raise Exception("Project has extra sources: %r" % (timelineObjects -
                names))

    def __iter__(self):
        return (source for source in self.sources if len(source) > 2)

class InstanceRunner(Signallable):

    no_ui = not(os.getenv("ENABLE_UI"))

    class container(object):

        def __init__(self):
            pass

    __signals__ = {
        "sources-loaded" : [],
        "timeline-configured" : [],
    }

    def __init__(self, instance):
        self.instance = instance
        self.watchdog = WatchDog(instance.mainloop, 10000)
        self.factories = set()
        self.errors = set()
        self.project = None
        self.timeline = None
        self.tracks = {}
        self.timelineObjects = {}
        self.pending_configuration = None
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
        container.transitions = {}
        track.connect("transition-added", self._transitionAddedCb, container)
        track.connect("transition-removed", self._transitionRemovedCb,
            container)

    def _transitionAddedCb(self, track, transition, container):
        container.transitions[(transition.a, transition.b)] = transition

    def _transitionRemovedCb(self, track, transition, container):
        del container.transitions[(transition.a, transition.b)]

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
            self.timelineObjects[name] = timelineObject
            for trackObject in timelineObject.track_objects:
                track = self.tracks[trackObject.track]
                setattr(track, name, trackObject)

            if not timelineObject:
                raise Exception("Could not add source '%s' to timeline" %
                    source)
            for prop, value in props.iteritems():
                setattr(timelineObject, prop, value)
        self.emit("timeline-configured")

    def run(self):
        self.watchdog.start()
        if self.no_ui:
            self.instance.run(["--no-ui"])
        else:
            from pitivi.ui.zoominterface import Zoomable
            # set a common zoom ratio so that things like edge snapping values
            # are consistent
            Zoomable.setZoomLevel((3 * Zoomable.zoom_steps) / 4)
            self.instance.run([])

    def shutDown(self):
        gobject.idle_add(self.instance.shutdown)
        self.project._dirty = False

class Brush(Signallable):
    """Scrubs your timelines until they're squeaky clean."""

    __signals__ = {
        "scrub-step" : ["time", "priority"],
        "scrub-done" : [],
    }

    def __init__(self, runner, delay=100, maxtime=7200, maxpriority=10):
        self.context = None
        self.time = 0
        self.priority = 0
        self.maxPriority = maxpriority
        self.maxTime = maxtime
        self.count = 0
        self.steps = 0
        self.delay = delay
        self.runner = runner
        self.watchdog = runner.watchdog

    def scrub(self, context, finalTime, finalPriority, steps=10):
        self.context = context
        self.time = finalTime
        self.priority = finalPriority
        self.count = 0
        self.steps = steps
        gobject.timeout_add(self.delay, self._scrubTimeoutCb)

    def _scrubTimeoutCb(self):
        self.watchdog.keepAlive()
        self.count += 1
        if self.count < self.steps:
            time_ = random.randint(0, self.maxTime)
            priority = random.randint(0, self.maxPriority)
            self.context.editTo(time_, priority)
            self.emit("scrub-step", time_, priority)
            return True
        else:
            self.context.editTo(self.time, self.priority)
            self.emit("scrub-step", self.time, self.priority)
            self.context.finish()
            self.emit("scrub-done")
            return False

class Base(TestCase):
    """
    Creates and runs an InteractivePitivi object, then starts the mainloop.
    Uses a WatchDog to ensure that test cases will eventually terminate with an
    assertion failure if runtime errors occur inside the mainloop."""

    def run(self, result):
        self._result = result
        self._num_failures = len(result.failures)
        self._num_errors = len(result.errors)
        TestCase.run(self, result)

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
        will_fail = False
        if ((self._num_errors == self._result.errors) and
            (self._num_failures == self._result.failures)):
            will_fail = not (pitivi.instance.PiTiVi is None)

        pitivi.instance.PiTiVi = None
        del self.ptv
        del self.runner

        if will_fail:
            raise Exception("Instance was not unset")
        TestCase.tearDown(self)

class TestBasic(Base):

    def testWatchdog(self):
        self.runner.run()
        self.assertTrue(self.runner.watchdog.activated)
        self.runner.watchdog.activated = False

    def testBasic(self):

        def newProjectLoaded(pitivi, project):
            self.runner.shutDown()

        self.ptv.connect("new-project-loaded", newProjectLoaded)
        self.runner.run()

    def testImport(self):

        def sourcesLoaded(runner):
            self.runner.shutDown()

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
            self.runner.shutDown()
 
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
            brush.scrub(context, 10 * gst.SECOND, 1, steps=10)

        def scrubStep(brush, time, priority):
            pass

        def scrubDone(brush):
            final.matches(self.runner)
            self.runner.shutDown()

        self.runner.loadConfiguration(initial)
        self.runner.connect("timeline-configured", timelineConfigured)

        brush = Brush(self.runner)
        brush.connect("scrub-step", scrubStep)
        brush.connect("scrub-done", scrubDone)

        self.runner.run()

    def testRippleMoveSimple(self):

        initial = Configuration()
        initial.addSource('clip1', test1, { 
            "duration" : gst.SECOND,
            "start" : gst.SECOND,
            "priority" : 2})
        initial.addSource('clip2', test1, {
            "duration" : gst.SECOND,
            "start" : 2 * gst.SECOND,
            "priority" : 5})
        final = Configuration()
        final.addSource('clip1', test1, {
            "duration" : gst.SECOND,
            "start" : 11 * gst.SECOND,
            "priority" : 0})
        final.addSource('clip2', test1, {
            "duration" : gst.SECOND,
            "start" : 12 * gst.SECOND,
            "priority" : 3})

        def timelineConfigured(runner):
            initial.matches(self.runner)
            context = MoveContext(self.runner.timeline,
                self.runner.video1.clip1, set())
            context.setMode(context.RIPPLE)
            brush.scrub(context, 11 * gst.SECOND, 0, steps=0)

        def scrubDone(brush):
            final.matches(self.runner)
            self.runner.shutDown()

        self.runner.connect("timeline-configured", timelineConfigured)
        brush = Brush(self.runner)
        brush.connect("scrub-done", scrubDone)

        self.runner.loadConfiguration(initial)
        self.runner.run()

    def testRippleTrimStartSimple(self):
        initial = Configuration()
        initial.addSource('clip1', test1,
            {
                "start" : gst.SECOND,
                "duration" : gst.SECOND,
            })
        initial.addSource('clip2', test1,
            {
                "start" : 2 * gst.SECOND,
                "duration" : gst.SECOND,
            })
        initial.addSource('clip3', test1,
            {
                "start" : 5 * gst.SECOND,
                "duration" : 10 * gst.SECOND,
            })

        final = Configuration()
        final.addSource('clip1', test1,
            {
                "start" : 6 * gst.SECOND,
                "duration": gst.SECOND,
            })
        final.addSource('clip2', test1,
            {
                "start" : 7 * gst.SECOND,
                "duration" : gst.SECOND,
            })
        final.addSource('clip3', test1,
            {
                "start" : 10 * gst.SECOND,
                "duration" : 5 * gst.SECOND,
            })

        self.runner.loadConfiguration(initial)
        def timelineConfigured(runner):
            context = TrimStartContext(self.runner.timeline,
                self.runner.video1.clip3, set())
            context.setMode(context.RIPPLE)
            brush.scrub(context, 10 * gst.SECOND, 0)
        self.runner.connect("timeline-configured", timelineConfigured)

        def scrubDone(brush):
            final.matches(self.runner)
            self.runner.shutDown()

        brush = Brush(self.runner)
        brush.connect("scrub-done", scrubDone)
        self.runner.run()

from pitivi.pipeline import PipelineError

class TestSeeking(Base):

    count = 0
    steps = 0
    cur_pos = 0

    config = Configuration()
    for i in xrange(0, 10):
        config.addSource("clip%d" % i, test1, {
            "start" : i * gst.SECOND,
            "duration" : gst.SECOND,
            "priority" : i % 2,
        })
        

    def _startSeeking(self, interval, steps=10):
        self.count = 0
        self.steps = steps
        self.positions = 0
        self.runner.project.pipeline.connect("position", self._positionCb)
        gobject.timeout_add(interval, self._seekTimeoutCb)

    def _seekTimeoutCb(self):
        if self.count < self.steps:
            self.runner.watchdog.keepAlive()
            self.count += 1
            self.cur_pos = random.randint(0, 
                self.runner.timeline.duration)
            self.runner.project.pipeline.seek(self.cur_pos)
            return True
        self.failUnlessEqual(self.positions, self.count)
        self.runner.shutDown()
        return False

    def _positionCb(self, pipeline, position):
        self.positions += 1
        self.failUnlessEqual(position,
            self.cur_pos)

    def testSeeking(self):

        self.runner.loadConfiguration(self.config)

        def timelineConfigured(runner):
            self._startSeeking(100, 10)

        def timelineConfiguredNoUI(runner):
            self.runner.shutDown()

        if self.runner.no_ui:
            print "UI Disabled: Skipping Seeking Test. " \
                "Use ENABLE_UI to test" \
                " seeking"
            self.runner.connect("timeline-configured", timelineConfiguredNoUI)
        else:
            self.runner.connect("timeline-configured", timelineConfigured)

        self.runner.run()

class TestRippleExtensive(Base):

    """Test suite for ripple editing minutia and corner-cases"""

    def __init__(self, unknown):
        # The following set of tests share common configuration, harness, and
        # business logic. We create the configurations in the constructor to
        # avoid having to re-create them for every test.

        # create a seqence of adjacent clips in staggered formation, each one
        # second long
        self.initial = Configuration()
        self.finals = []
        for i in xrange(0, 10):
            self.initial.addSource('clip%d' % i, test1,
                { 'start' : gst.SECOND * i, 'duration' : gst.SECOND,
                    'priority' : i % 2 })
            # we're going to repeat the same operation using each clip as the
            # focus of the editing context. We create one final
            # configuration for the expected result of each scenario.
            final = Configuration()
            for j in xrange(0, 10):
                if j < i:
                    final.addSource('clip%d' % j, test1,
                        { 'start' : gst.SECOND * j, 
                          'duration' : gst.SECOND,
                          'priority' : j % 2})
                else:
                    final.addSource('clip%d' % j, test1,
                        { 'start' : gst.SECOND * (j + 10), 
                          'duration' : gst.SECOND, 
                          'priority' : (j % 2) + 1})
            self.finals.append(final)
        Base.__init__(self, unknown)

    def setUp(self):
        Base.setUp(self)
        self.cur = 0
        self.context = None
        self.brush = Brush(self.runner)
        self.runner.loadConfiguration(self.initial)
        self.runner.connect("timeline-configured", self.timelineConfigured)
        self.brush.connect("scrub-done", self.scenarioDone)

    # when the timeline is configured, kick off the test by starting the
    # first scenario
    def timelineConfigured(self, runner):
        self.nextScenario()

    # for each scenario, create the context using the specified clip as
    # focus, and not specifying any other clips.
    def nextScenario(self):
        cur = self.cur
        clipname = "clip%d" % cur
        context = MoveContext(self.runner.timeline,
            getattr(self.runner.video1, clipname), set())
        context.snap(False)
        context.setMode(context.RIPPLE)
        self.context = context
        # this isn't a method, but an attribute that will be set by specific
        # test cases
        self.scrub_func(context, (cur + 10) * gst.SECOND, (cur % 2) + 1)

    # when each scrub has finished, verify the current configuration is
    # correct, reset the timeline, and kick off the next scenario. Shut down
    # pitivi when we have finished the last scenario.
    def scenarioDone(self, brush):
        cur = self.cur
        config = self.finals[cur]
        context = self.context
        context.finish()
        config.matches(self.runner)
        restore = MoveContext(self.runner.timeline, context.focus, set())
        restore.setMode(restore.RIPPLE)
        restore.editTo(cur * gst.SECOND, (cur % 2))
        restore.finish()
        self.initial.matches(self.runner)
        self.cur += 1
        if self.cur < 10:
            self.nextScenario()
        else:
            self.runner.shutDown()

    def testRippleMoveComplex(self):
        # in this test we move directly to the given position (steps=0)
        def rippleMoveComplexScrubFunc(context, position, priority):
            self.brush.scrub(context, position, priority, steps=0)
        self.scrub_func = rippleMoveComplexScrubFunc
        self.runner.run()

    def testRippleMoveComplexRandom(self):
        # same as above test, but scrub randomly (steps=100)
        # FIXME: this test fails for unknown reasons
        def rippleMoveComplexRandomScrubFunc(context, position, priority):
            self.brush.scrub(context, position, priority, steps=100)
        self.scrub_func = rippleMoveComplexRandomScrubFunc
        self.runner.run()

if __name__ == "__main__":
    unittest.main()
