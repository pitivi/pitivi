"""
A collection of objects to use for testing
"""

import pitivi
import gst

class TestTimelineObject(pitivi.timeline.objects.TimelineObject):

    def _makeBrother(self):
        if self.media_type == pitivi.timeline.objects.MEDIA_TYPE_AUDIO:
            return TestTimelineObject(factory=self.factory,
                                      start=self.start,
                                      duration=self.duration,
                                      media_type=pitivi.timeline.objects.MEDIA_TYPE_VIDEO,
                                      name=self.name)
        if self.media_type == pitivi.timeline.objects.MEDIA_TYPE_VIDEO:
            return TestTimelineObject(factory=self.factory,
                                      start=self.start,
                                      duration=self.duration,
                                      media_type=pitivi.timeline.objects.MEDIA_TYPE_AUDIO,
                                      name=self.name)

    def _makeGnlObject(self):
        if self.media_type == pitivi.timeline.objects.MEDIA_TYPE_AUDIO:
            return self.factory.makeAudioBin()
        if self.media_type == pitivi.timeline.objects.MEDIA_TYPE_VIDEO:
            return self.factory.makeVideoBin()

class TestTimelineSource(pitivi.timeline.source.TimelineSource):
    pass

class TestTimelineFileSource(pitivi.timeline.source.TimelineFileSource):
    """
    Dummy TimelineFileSource
    """

    # we only override the gnlobject creation since we want to test all
    # other behaviour.

    def _makeGnlObject(self):
        gnlobject = gst.element_factory_make("gnlsource")
        fakesrc = gst.element_factory_make("fakesrc")
        gnlobject.add(fakesrc)
        return gnlobject

class TestObjectFactory(pitivi.objectfactory.ObjectFactory):
    """
    Test pitivi.objectfactory.ObjectFactory
    """

    def __init__(self, audio=True, video=False):
        self.__audio = audio
        self.__video = video
        self.__id = 0

    def makeAudioBin(self):
        gnlobj = gst.element_factory_make("gnlsource", "test-audio-%d" % self.__id)
        self.__id = self.__id + 1
        gnlobj.add(gst.element_factory_make("audiotestsrc"))
        return gnlobj

    def makeVideoBin(self):
        gnlobj = gst.element_factory_make("gnlsource", "test-video-%d" % self.__id)
        self.__id = self.__id + 1
        gnlobj.add(gst.element_factory_make("videotestsrc"))
        return gnlobj

class TestFileSourceFactory(TestObjectFactory):

    def __init__(self, *args, **kwargs):
        TestObjectFactory.__init__(self, *args, **kwargs)
        self.length = 0

