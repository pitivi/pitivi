import unittest
import common
import gc
import weakref
from pitivi.serializable import to_object_from_data_type
from pitivi.timeline.objects import BrotherObjects, MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
import gst

class TestTimelineFileSource(unittest.TestCase):

    def setUp(self):
        gst.log("setting up")
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 0)
        self.factory = common.TestFileSourceFactory(duration=2 * gst.SECOND)
        self.source = common.TestTimelineFileSource(factory=self.factory,
                                                    start = 0,
                                                    duration = gst.SECOND,
                                                    media_start = gst.SECOND,
                                                    media_duration = gst.SECOND,
                                                    media_type = MEDIA_TYPE_VIDEO,
                                                    name="self.source")
        self.source.connect("media-start-duration-changed",
                            self._mediaStartDurationChangedCb)
        self._mstart = self.source.media_start
        self._mduration = self.source.media_duration
        gc.collect()

    def tearDown(self):
        gst.log("tearing down")
        if self.factory:
            del self.factory
        if self.source:
            del self.source
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 0)

    def _mediaStartDurationChangedCb(self, source, mstart, mduration):
        self._mstart = mstart
        self._mduration = mduration

    def testBasic(self):
        self.assertEquals(self.source.media_start, gst.SECOND)
        self.assertEquals(self.source.media_duration, gst.SECOND)
        self.assertEquals(self._mstart, gst.SECOND)
        self.assertEquals(self._mduration, gst.SECOND)

        self.source.setMediaStartDurationTime()
        self.assertEquals(self.source.media_start, gst.SECOND)
        self.assertEquals(self.source.media_duration, gst.SECOND)
        self.assertEquals(self._mstart, gst.SECOND)
        self.assertEquals(self._mduration, gst.SECOND)

        self.source.setMediaStartDurationTime(start = 2 * gst.SECOND)
        self.assertEquals(self.source.media_start, 2 * gst.SECOND)
        self.assertEquals(self.source.media_duration, gst.SECOND)
        self.assertEquals(self._mstart, 2 * gst.SECOND)
        self.assertEquals(self._mduration, gst.SECOND)

        self.source.setMediaStartDurationTime(duration = 2 * gst.SECOND)
        self.assertEquals(self.source.media_start, 2 * gst.SECOND)
        self.assertEquals(self.source.media_duration, 2 * gst.SECOND)
        self.assertEquals(self._mstart, 2 * gst.SECOND)
        self.assertEquals(self._mduration, 2 * gst.SECOND)

        # when setting start < 0 or duration <= 0 , values shouldn't change
        self.source.setMediaStartDurationTime(start = -1 * gst.SECOND)
        self.assertEquals(self.source.media_start, 2 * gst.SECOND)
        self.assertEquals(self.source.media_duration, 2 * gst.SECOND)
        self.assertEquals(self._mstart, 2 * gst.SECOND)
        self.assertEquals(self._mduration, 2 * gst.SECOND)

        self.source.setMediaStartDurationTime(duration = 0)
        self.assertEquals(self.source.media_start, 2 * gst.SECOND)
        self.assertEquals(self.source.media_duration, 2 * gst.SECOND)
        self.assertEquals(self._mstart, 2 * gst.SECOND)
        self.assertEquals(self._mduration, 2 * gst.SECOND)

    def testBrotherSources(self):
        brother = self.source.getBrother()

        # Make sure it's the right brother
        self.assertEquals(self.source._brother, brother)
        self.assertEquals(self.source.linked, brother)
        self.assertEquals(brother.media_type, MEDIA_TYPE_AUDIO)
        self.assertEquals(self.source.media_start, brother.media_start)
        self.assertEquals(self.source.media_duration, brother.media_duration)

        # now same tests as above.
        # Changing on the source, but checking on the brother.
        self.assertEquals(brother.media_start, gst.SECOND)
        self.assertEquals(brother.media_duration, gst.SECOND)

        self.source.setMediaStartDurationTime()
        self.assertEquals(brother.media_start, gst.SECOND)
        self.assertEquals(brother.media_duration, gst.SECOND)

        self.source.setMediaStartDurationTime(start = 2 * gst.SECOND)
        self.assertEquals(brother.media_start, 2 * gst.SECOND)
        self.assertEquals(brother.media_duration, gst.SECOND)

        self.source.setMediaStartDurationTime(duration = 2 * gst.SECOND)
        self.assertEquals(brother.media_start, 2 * gst.SECOND)
        self.assertEquals(brother.media_duration, 2 * gst.SECOND)

        # when setting start < 0 or duration <= 0 , values shouldn't change
        self.source.setMediaStartDurationTime(start = -1 * gst.SECOND)
        self.assertEquals(brother.media_start, 2 * gst.SECOND)
        self.assertEquals(brother.media_duration, 2 * gst.SECOND)

        self.source.setMediaStartDurationTime(duration = 0)
        self.assertEquals(brother.media_start, 2 * gst.SECOND)
        self.assertEquals(brother.media_duration, 2 * gst.SECOND)

        del brother

    def testSimpleSerialization(self):
        self.assertEquals(len(BrotherObjects.__instances__), 0)
        data = self.source.toDataFormat()
        self.assertEquals(len(BrotherObjects.__instances__), 1)
        del self.source
        self.source = None
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 0)

        source = to_object_from_data_type(data)
        self.assertEquals(source.start, 0)
        self.assertEquals(source.duration, gst.SECOND)
        self.assertEquals(source.media_start, gst.SECOND)
        self.assertEquals(source.media_duration, gst.SECOND)
        self.assertEquals(source.factory, self.factory)
        self.assertEquals(source.media_type, MEDIA_TYPE_VIDEO)
        self.assertEquals(source.linked, None)
        self.assertEquals(source._brother, None)

    def testBrotherSerialization(self):
        brother = self.source.getBrother()

        self.assertEquals(len(BrotherObjects.__instances__), 0)

        self.assertEquals(self.source._brother, brother)
        self.assertEquals(self.source.linked, brother)
        self.assertEquals(brother.linked, self.source)

        brodata = brother.toDataFormat()

        self.assertEquals(len(BrotherObjects.__instances__), 2)

        del brother
        del self.source
        self.source = None
        gc.collect()

        self.assertEquals(len(BrotherObjects.__instances__), 0)

        gst.log("recreating brother !")
        brother = to_object_from_data_type(brodata)
        gst.log("recreating source")
        self.assert_(brother)
        # the brother no longer exists !
        self.assertEquals(brother.linked, None)

        # we only have one instance, and it's the brother
        self.assertEquals(len(BrotherObjects.__instances__), 1)
        self.assertEquals(BrotherObjects.__instances__[brother.uid], brother)

        del brother

    def testLinkedBrotherSerialization(self):
        # create a brother and check all values are properly set
        brother = self.source.getBrother()
        self.assertEquals(self.source._brother, brother)
        self.assertEquals(self.source.linked, brother)
        self.assertEquals(brother.linked, self.source)

        # serialize both objects
        data1 = self.source.toDataFormat()
        brotherdata1 = brother.toDataFormat()

        # delete the objects
        del self.source
        self.source = None
        del brother
        gc.collect()

        self.assertEquals(len(BrotherObjects.__instances__), 0)

        # recreate object
        gst.log("recreating source !")
        source = to_object_from_data_type(data1)
        self.assertEquals(source._brother, None)
        self.assertEquals(source.linked, None)

        # recreate brother
        gst.log("recreating brother")
        brothernew = to_object_from_data_type(brotherdata1)
        gst.log("done")

        # and now lets check if they were properly recreated
        self.assertEquals(source.start, 0)
        self.assertEquals(source.duration, gst.SECOND)
        self.assertEquals(source.media_start, gst.SECOND)
        self.assertEquals(source.media_duration, gst.SECOND)
        self.assertEquals(source.factory, self.factory)
        self.assertEquals(source.media_type, MEDIA_TYPE_VIDEO)
        self.assertEquals(source.linked, brothernew)
        self.assertEquals(source._brother, brothernew)

        self.assertEquals(brothernew.start, 0)
        self.assertEquals(brothernew.duration, gst.SECOND)
        self.assertEquals(brothernew.media_start, gst.SECOND)
        self.assertEquals(brothernew.media_duration, gst.SECOND)
        self.assertEquals(brothernew.factory, self.factory)
        self.assertEquals(brothernew.media_type, MEDIA_TYPE_AUDIO)
        self.assertEquals(brothernew.linked, source)
        self.assertEquals(brothernew._brother, source)

    # uniqueness tests

    def test00(self):
        self.source.getUniqueID()
        # the unique id has been added to the list
        self.assertEquals(len(BrotherObjects.__instances__), 1)

    def test01(self):
        data = self.source.toDataFormat()
        self.assertEquals(len(BrotherObjects.__instances__), 1)

        del self.source
        gc.collect()
        self.source = None
        self.assertEquals(len(BrotherObjects.__instances__), 0)

    def test02(self):
        brother = self.source.getBrother()
        gst.log("%r" % BrotherObjects.__instances__.values())
        self.assertEquals(len(BrotherObjects.__instances__), 0)

        data = self.source.toDataFormat()
        # 2 instances: self.source and brother
        gst.log("%r" % BrotherObjects.__instances__.values())
        self.assertEquals(len(BrotherObjects.__instances__), 2)

        del self.source
        self.source = None
        gc.collect()

        # brother still has a reference to self.source
        gst.log("%r" % BrotherObjects.__instances__.values())
        self.assertEquals(len(BrotherObjects.__instances__), 2)

        del brother
        gc.collect()

        # we have released our reference to brother
        # we shouldn't have anything left
        gst.log("%r" % BrotherObjects.__instances__.values())
        self.assertEquals(len(BrotherObjects.__instances__), 0)
