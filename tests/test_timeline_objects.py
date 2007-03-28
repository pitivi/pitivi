import unittest
import common
from pitivi.timeline.objects import MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
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

    def testLinkedObject(self):
        # Link object1 to object2
        self.object1.linkObject(self.object2)
        self.assertEquals(self.object1.getLinkedObject(),
                          self.object2)
        self.assertEquals(self.object2.getLinkedObject(),
                          self.object1)

        # and now unlink them
        self.object1.unlinkObject()
        self.assertEquals(self.object1.getLinkedObject(),
                          None)
        self.assertEquals(self.object2.getLinkedObject(),
                          None)

    def testBrotherNotLinked(self):
        # get the brother of object1
        brother1 = self.object1.getBrother(autolink=False)

        # if we ask again, it should be the same
        self.assertEquals(self.object1.getBrother(autolink=False),
                          brother1)

        # the linked object should be None since it was not autolinked
        self.assertEquals(self.object1.getLinkedObject(),
                          None)

    def testBrotherLinked(self):
        # get the brother of object1
        brother1 = self.object1.getBrother(autolink=False)

        # if we ask again, it should be the same
        self.assertEquals(self.object1.getBrother(),
                          brother1)

        # the linked object should be brother1 since it was autolinked
        self.assertEquals(self.object1.getLinkedObject(),
                          brother1)

        # unlink the objects
        self.object1.unlinkObject()

        # object1 shouldn't be linked anymore
        self.assertEquals(self.object1.getLinkedObject(),
                          None)
