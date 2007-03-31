import unittest
import common
from pitivi.timeline.objects import MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
import gst

class TestTimelineFileSource(unittest.TestCase):

    def testBasic(self):
        self.factory = common.TestFileSourceFactory()
        self.source = common.TestTimelineFileSource(factory=self.factory,
                                                    media_start = gst.SECOND,
                                                    media_duration = gst.SECOND)
        self.assertEquals(self.source.media_start, gst.SECOND)
        self.assertEquals(self.source.media_duration, gst.SECOND)

        self.source.setMediaStartDurationTime()
        self.assertEquals(self.source.media_start, gst.SECOND)
        self.assertEquals(self.source.media_duration, gst.SECOND)

        self.source.setMediaStartDurationTime(start = 2 * gst.SECOND)
        self.assertEquals(self.source.media_start, 2 * gst.SECOND)
        self.assertEquals(self.source.media_duration, gst.SECOND)

        self.source.setMediaStartDurationTime(duration = 2 * gst.SECOND)
        self.assertEquals(self.source.media_start, 2 * gst.SECOND)
        self.assertEquals(self.source.media_duration, 2 * gst.SECOND)

