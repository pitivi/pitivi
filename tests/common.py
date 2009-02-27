"""
A collection of objects to use for testing
"""

import gobject
gobject.threads_init()
import gst
import gc
import unittest
from pitivi.timeline.objects import TimelineObject, MEDIA_TYPE_NONE, MEDIA_TYPE_VIDEO, MEDIA_TYPE_AUDIO
from pitivi.timeline.source import TimelineSource, TimelineFileSource
from pitivi.factories.base import ObjectFactory, SourceFactory, SinkFactory
from pitivi.pipeline import Pipeline

class TestCase(unittest.TestCase):

    _tracked_types = [gst.MiniObject, gst.Element, gst.Pad, gst.Caps, ObjectFactory, Pipeline]

    def gctrack(self):
        self.gccollect()
        self._tracked = {}
        for c in self._tracked_types:
            self._tracked[c] = [o for o in gc.get_objects() if isinstance(o, c)]

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
        objs = gc.get_objects()
        for c in self._tracked_types:
            new.extend([o for o in objs if isinstance(o, c) and not o in self._tracked[c]])

        self.failIf(new, new)
        del self._tracked

    def setUp(self):
        self.gctrack()

    def tearDown(self):
        self.gccollect()
        self.gcverify()

class TestTimelineObject(TimelineObject):

    __data_type__ = "test-timeline-object"

    def _makeBrother(self):
        if self.media_type == MEDIA_TYPE_AUDIO:
            return TestTimelineObject(factory=self.factory,
                                      start=self.start,
                                      duration=self.duration,
                                      media_type=MEDIA_TYPE_VIDEO,
                                      name=self.name)
        if self.media_type == MEDIA_TYPE_VIDEO:
            return TestTimelineObject(factory=self.factory,
                                      start=self.start,
                                      duration=self.duration,
                                      media_type=MEDIA_TYPE_AUDIO,
                                      name=self.name)

    def _makeGnlObject(self):
        if self.media_type == MEDIA_TYPE_AUDIO:
            return self.factory.makeAudioBin()
        if self.media_type == MEDIA_TYPE_VIDEO:
            return self.factory.makeVideoBin()

class TestTimelineSource(TimelineSource):
    __data_type__ = "test-timeline-source"

    pass

# Some fake factories
class FakeSourceFactory(SourceFactory):
    def __init__(self, factoryname="fakesrc", *args, **kwargs):
        SourceFactory.__init__(self, *args, **kwargs)
        self.__factoryname=factoryname

    def _makeBin(self, output_stream=None):
        return gst.element_factory_make(self.__factoryname)

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
        SourceFactory.__init__(self, *args, **kwargs)

    def _makeBin(self, output_stream=None):
        # let's make a gnlsource with videotestsrc inside of it
        gnl = gst.element_factory_make("gnlsource")
        vs = gst.element_factory_make("videotestsrc")
        gnl.add(vs)
        gnl.props.duration=self.__duration
        gnl.props.media_duration=self.__media_duration
        return gnl


class SignalMonitor(object):
    def __init__(self, obj, *signals):
        self.obj = obj

        for signal in signals:
            obj.connect(signal, self._signalCb, signal)
            setattr(self, self._getSignalCounterName(signal), 0)
            setattr(self, self._getSignalCollectName(signal), [])

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

