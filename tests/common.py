"""
A collection of objects to use for testing
"""

import gobject
gobject.threads_init()
import gst
import os
import gc
import unittest
from pitivi.factories.base import ObjectFactory, SourceFactory, SinkFactory
from pitivi.factories.operation import EffectFactory
from pitivi.pipeline import Pipeline

detect_leaks = os.environ.get("PITIVI_TEST_DETECT_LEAKS", "1") not in ("0", "")

class TestCase(unittest.TestCase):
    _tracked_types = (gst.MiniObject, gst.Element, gst.Pad, gst.Caps,
            ObjectFactory, Pipeline)

    def gctrack(self):
        self.gccollect()
        self._tracked = []
        for obj in gc.get_objects():
            if not isinstance(obj, self._tracked_types):
                continue

            self._tracked.append(obj)

    def gccollect(self):
        ret = 0
        while True:
            c = gc.collect()
            ret += c
            if c == 0:
                break
        return ret

    def gcverify(self):
        new = []
        leaked = []
        for obj in gc.get_objects():
            if not isinstance(obj, self._tracked_types) or \
                    obj in self._tracked:
                continue

            leaked.append(obj)

        # we collect again here to get rid of temporary objects created in the
        # above loop
        self.gccollect()

        for elt in leaked:
            print elt
            for i in gc.get_referrers(elt):
                print "   ", i

        self.failIf(leaked, leaked)
        del self._tracked

    def setUp(self):
        self._num_failures = len(getattr(self._result, 'failures', []))
        self._num_errors = len(getattr(self._result, 'errors', []))
        if detect_leaks:
            self.gctrack()

    def tearDown(self):
        # don't barf gc info all over the console if we have already failed a
        # test case
        if (self._num_failures < len(getattr(self._result, 'failures', []))
            or self._num_errors < len(getattr(self._result, 'failures', []))):
            return
        if detect_leaks:
            self.gccollect()
            self.gcverify()

    # override run() to save a reference to the test result object
    def run(self, result=None):
        if not result:
            result = self.defaultTestResult()
        self._result = result
        unittest.TestCase.run(self, result)

# Some fake factories
class FakeSourceFactory(SourceFactory):
    def __init__(self, factoryname="fakesrc", *args, **kwargs):
        SourceFactory.__init__(self, "fakesrc://", *args, **kwargs)
        self._factoryname = factoryname

    def _makeBin(self, output_stream=None):
        return gst.element_factory_make(self._factoryname)

    def _releaseBin(self, bin):
        pass

class FakeSinkFactory(SinkFactory):
    def __init__(self, factoryname="fakesink", *args, **kwargs):
        SinkFactory.__init__(self, *args, **kwargs)
        self.__factoryname=factoryname

    def _makeBin(self, output_stream=None):
        return gst.element_factory_make(self.__factoryname)

class FakeGnlFactory(SourceFactory):

    def __init__(self, duration=10*gst.SECOND, media_duration=10*gst.SECOND,
                 *args, **kwargs):
        self.__duration = duration
        self.__media_duration = media_duration
        SourceFactory.__init__(self, "fakegnl://", *args, **kwargs)

    def _makeBin(self, output_stream=None):
        # let's make a gnlsource with videotestsrc inside of it
        gnl = gst.element_factory_make("gnlsource")
        vs = gst.element_factory_make("videotestsrc")
        gnl.add(vs)
        gnl.props.duration=self.__duration
        gnl.props.media_duration=self.__media_duration
        return gnl

    def _releaseBin(self, bin):
        pass

class SignalMonitor(object):
    def __init__(self, obj, *signals):
        self.signals = signals
        self.connectToObj(obj)

    def connectToObj(self, obj):
        self.obj = obj
        for signal in self.signals:
            obj.connect(signal, self._signalCb, signal)
            setattr(self, self._getSignalCounterName(signal), 0)
            setattr(self, self._getSignalCollectName(signal), [])

    def disconnectFromObj(self, obj):
        obj.disconnect_by_func(self._signalCb)
        del self.obj

    def _getSignalCounterName(self, signal):
        field = '%s_count' % signal.replace('-', '_')
        return field

    def _getSignalCollectName(self, signal):
        field = '%s_collect' % signal.replace('-', '_')
        return field

    def _signalCb(self, obj, *args):
        name = args[-1]
        field = self._getSignalCounterName(name)
        setattr(self, field, getattr(self, field, 0) + 1)
        field = self._getSignalCollectName(name)
        setattr(self, field, getattr(self, field, []) + [args[:-1]])

class StubFactory(SourceFactory):
    def __init__(self):
        SourceFactory.__init__(self, "stub://")
        self.duration = 42 * gst.SECOND

    def _makeBin(self, stream=None):
        return gst.element_factory_make('fakesrc')

    def _releaseBin(self, bin):
        pass

class FakeEffectFactory(EffectFactory):
    def __init__(self):
        EffectFactory.__init__(self, 'identity', "identity")
        self.duration = 42 * gst.SECOND
