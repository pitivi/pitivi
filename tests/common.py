"""
A collection of objects to use for testing
"""

import os
import gc
import unittest
import tempfile

from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import Gtk

from unittest import mock
from pitivi import check

from pitivi.application import Pitivi
from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import Selected
from pitivi.utils.validate import Event

detect_leaks = os.environ.get("PITIVI_TEST_DETECT_LEAKS", "0") not in ("0", "")
os.environ["PITIVI_USER_CACHE_DIR"] = tempfile.mkdtemp("pitiviTestsuite")


def cleanPitiviMock(ptv):
    ptv.settings = None


def getPitiviMock(settings=None):
    ptv = mock.MagicMock()

    ptv.write_action = mock.MagicMock(spec=Pitivi.write_action)
    check.check_requirements()

    if not settings:
        settings = mock.MagicMock()

    ptv.settings = settings

    return ptv


class TestCase(unittest.TestCase, Loggable):
    _tracked_types = (Gst.MiniObject, Gst.Element, Gst.Pad, Gst.Caps)

    def __init__(self, *args):
        Loggable.__init__(self)
        unittest.TestCase.__init__(self, *args)

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

    def toggleClipSelection(self, bClip, expect_selected):
        '''
        Toggle selection state of @bClip.
        '''
        selected = bool(bClip.ui.get_state_flags() & Gtk.StateFlags.SELECTED)
        self.assertEqual(bClip.selected.selected, selected)

        bClip.ui.sendFakeEvent(
            Event(Gdk.EventType.BUTTON_PRESS, button=1), bClip.ui)
        bClip.ui.sendFakeEvent(
            Event(Gdk.EventType.BUTTON_RELEASE, button=1), bClip.ui)

        self.assertEqual(bool(bClip.ui.get_state_flags() & Gtk.StateFlags.SELECTED),
                         expect_selected)
        self.assertEqual(bClip.selected.selected, expect_selected)


def getSampleUri(sample):
    assets_dir = os.path.dirname(os.path.abspath(__file__))
    return "file://%s/samples/%s" % (assets_dir, sample)


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
