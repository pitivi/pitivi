import unittest
import common
from pitivi.timeline.composition import TimelineComposition
import gst

class TestTimelineComposition(unittest.TestCase):

    def setUp(self):
        self.composition = TimelineComposition()
        self.assert_(self.composition)

        self.othercomposition = TimelineComposition()
        self.assert_(self.othercomposition)

        self.composition.linkObject(self.othercomposition)
        self.assertEquals(self.composition.getLinkedObject(),
                          self.othercomposition)

        factory = common.TestFileSourceFactory(audio=True, video=True)
        self.source1 = common.TestTimelineFileSource(factory=factory,
                                                     media_type=common.MEDIA_TYPE_VIDEO,
                                                     media_start=0,
                                                     media_duration=gst.SECOND)
        self.source2 = common.TestTimelineFileSource(factory=factory,
                                                     media_type=common.MEDIA_TYPE_VIDEO,
                                                     media_start=0,
                                                     media_duration=gst.SECOND)
        self.source3 = common.TestTimelineFileSource(factory=factory,
                                                     media_type=common.MEDIA_TYPE_VIDEO,
                                                     media_start=0,
                                                     media_duration=gst.SECOND)


    def testRemoveSource(self):
        pass

    def testMoveSource(self):
        pass

    def testPrependSource(self):
        pass

    def testAppendSourceNotAutoLinked(self):
        self.composition.appendSource(self.source1, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.othercomposition.condensed,
                          [])

        self.composition.appendSource(self.source2, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [])

        self.composition.appendSource(self.source3, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])        
        self.assertEquals(self.othercomposition.condensed,
                          [])

    def testAppendSourceAutoLinked(self):
        self.composition.appendSource(self.source1, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        brother1 = self.source1.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1])

        self.composition.appendSource(self.source2, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        brother2 = self.source2.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1, brother2])

        self.composition.appendSource(self.source3, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])        
        brother3 = self.source3.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1, brother2, brother3])        


    def testInsertSourceAfter(self):
        pass

    def testAddSource(self):
        pass

    def testDefaultsource(self):
        pass

    # FIXME : add tests for other methods
