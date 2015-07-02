"""
A collection of objects to use for testing
"""

from gi.repository import Gst
import os
import gc
import unittest

from pitivi.utils.timeline import Selected

detect_leaks = os.environ.get("PITIVI_TEST_DETECT_LEAKS", "1") not in ("0", "")


class TestCase(unittest.TestCase):
    _tracked_types = (Gst.MiniObject, Gst.Element, Gst.Pad, Gst.Caps)

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
            print(elt)
            for i in gc.get_referrers(elt):
                print("   ", i)

        self.assertFalse(leaked, leaked)
        del self._tracked

    def setUp(self):
        self._num_failures = len(getattr(self._result, 'failures', []))
        self._num_errors = len(getattr(self._result, 'errors', []))
        if detect_leaks:
            self.gctrack()

    def tearDown(self):
        # don't barf gc info all over the console if we have already failed a
        # test case
        if (self._num_failures < len(getattr(self._result, 'failures', [])) or
                self._num_errors < len(getattr(self._result, 'failures', []))):
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

    @staticmethod
    def getSampleUri(sample):
        dir = os.path.dirname(os.path.abspath(__file__))
        return "file://%s/samples/%s" % (dir, sample)


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


def createTestClip(clip_type):
    clip = clip_type()
    clip.selected = Selected()

    return clip
