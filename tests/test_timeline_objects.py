import unittest
import common
from pitivi.serializable import to_object_from_data_type
from pitivi.timeline.objects import BrotherObjects, TimelineObject, MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
import gc
import weakref
import gst

class TestTimelineObjects(unittest.TestCase):
    """
    Test the behaviour of pitivi.timeline.objects classes
    """

    def setUp(self):
        self.factory1 = common.TestObjectFactory()
        self.object1 = common.TestTimelineObject(factory=self.factory1,
                                                 start = 0,
                                                 duration = gst.SECOND,
                                                 media_type = MEDIA_TYPE_VIDEO,
                                                 name="test1")
        self.object2 = common.TestTimelineObject(factory=self.factory1,
                                                 start = 0,
                                                 duration = gst.SECOND,
                                                 media_type = MEDIA_TYPE_AUDIO,
                                                 name="test2")
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 0)

    def tearDown(self):
        del self.object1
        del self.object2
        del self.factory1
        gc.collect()

    def testLinkedObject(self):
        # Link object1 to object2
        self.object1.linkObject(self.object2)
        self.assertEquals(self.object1.linked,
                          self.object2)
        self.assertEquals(self.object2.linked,
                          self.object1)

        # and now unlink them
        self.object1.unlinkObject()
        self.assertEquals(self.object1.linked,
                          None)
        self.assertEquals(self.object2.linked,
                          None)

    def testBrotherNotLinked(self):
        # get the brother of object1
        brother1 = self.object1.getBrother(autolink=False)

        # if we ask again, it should be the same
        self.assertEquals(self.object1.getBrother(autolink=False),
                          brother1)

        # the linked object should be None since it was not autolinked
        self.assertEquals(self.object1.linked,
                          None)

    def testBrotherLinked(self):
        # get the brother of object1
        brother1 = self.object1.getBrother(autolink=False)

        # if we ask again, it should be the same
        self.assertEquals(self.object1.getBrother(),
                          brother1)

        # the linked object should be brother1 since it was autolinked
        self.assertEquals(self.object1.linked,
                          brother1)

        # unlink the objects
        self.object1.unlinkObject()

        # object1 shouldn't be linked anymore
        self.assertEquals(self.object1.linked,
                          None)

    def testSingleSerialization(self):
        self.assertEquals(self.object1._brother, None)
        data1 = self.object1.toDataFormat()
        del self.object1
        self.object1 = None
        # we need to force garbage collection for pygobject < 2.13
        gc.collect()
        obj1 = to_object_from_data_type(data1)
        self.assert_(obj1)
        self.assertEquals(obj1.factory, self.factory1)
        self.assertEquals(obj1.start, 0)
        self.assertEquals(obj1.duration, gst.SECOND)
        self.assertEquals(obj1.media_type, MEDIA_TYPE_VIDEO)
        self.assertEquals(obj1.name, "test1")
        self.assertEquals(obj1.linked, None)
        self.assertEquals(obj1._brother, None)
        self.assert_(not obj1.gnlobject == None)

    def testLinkedBrotherSerialization(self):
        # get the brother of object1
        brother1 = self.object1.getBrother()

        self.assertEquals(self.object1._brother, brother1)
        self.assertEquals(self.object1.linked, brother1)
        self.assertEquals(brother1.linked, self.object1)

        data1 = self.object1.toDataFormat()
        brotherdata1 = brother1.toDataFormat()

        # delete object1 and its brother
        del self.object1
        self.object1 = None
        del brother1
        gc.collect()

        # create object...
        pobj = to_object_from_data_type(data1)
        self.assertEquals(pobj._brother, None)
        self.assertEquals(pobj.linked, None)

        # ... and brother
        pbro = to_object_from_data_type(brotherdata1)

        # check it's really the linked brother
        self.assertEquals(pobj._brother, pbro)
        self.assertEquals(pobj.linked, pbro)
        self.assertEquals(pbro.linked, pobj)

    def testBrotherObjectSerialization(self):
        a = BrotherObjects()
        id = a.getUniqueID()
        data = a.toDataFormat()

        del a
        # we need to force garbage collection with pygobject < 2.13
        gc.collect()

        b = to_object_from_data_type(data)
        self.assert_(b)
        self.assertEquals(b.getUniqueID(), id)

    # uniqueness tests

    def test00(self):
        self.object1.getUniqueID()
        self.assertEquals(len(BrotherObjects.__instances__), 1)
        self.object2.getUniqueID()
        self.assertEquals(len(BrotherObjects.__instances__), 2)

        del self.object1
        self.object1 = None
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 1)

        del self.object2
        self.object2 = None
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 0)

    def test01(self):
        self.object1.getUniqueID()
        self.assertEquals(len(BrotherObjects.__instances__), 1)
        self.object2.getUniqueID()
        self.assertEquals(len(BrotherObjects.__instances__), 2)

        brother = self.object1.getBrother()
        self.assertEquals(len(BrotherObjects.__instances__), 2)

        brother.getUniqueID()
        self.assertEquals(len(BrotherObjects.__instances__), 3)

        del brother
        self.object1.brother = None
        self.object1.unlinkObject()
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 2)

        del self.object1
        self.object1 = None
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 1)

        del self.object2
        self.object2 = None
        gc.collect()
        self.assertEquals(len(BrotherObjects.__instances__), 0)
