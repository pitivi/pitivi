import unittest
import common
from pitivi.serializable import to_object_from_data_type
from pitivi.timeline.composition import TimelineComposition
import gc
import gst

class TestTimelineComposition(unittest.TestCase):

    def setUp(self):
        self.composition = TimelineComposition(name="composition")
        self.assert_(self.composition)

        self.othercomposition = TimelineComposition(name="othercomposition")
        self.assert_(self.othercomposition)

        self.composition.linkObject(self.othercomposition)
        self.assertEquals(self.composition.getLinkedObject(),
                          self.othercomposition)

        self.composition.connect("start-duration-changed",
                                 self._compositionStartDurationChangedCb)
        self.compstart = self.composition.start
        self.compduration = self.composition.duration

        factory = common.TestFileSourceFactory(audio=True, video=True)
        self.source1 = common.TestTimelineFileSource(factory=factory,
                                                     name="source1",
                                                     media_type=common.MEDIA_TYPE_VIDEO,
                                                     media_start=0,
                                                     media_duration=gst.SECOND)
        self.source2 = common.TestTimelineFileSource(factory=factory,
                                                     name="source2",
                                                     media_type=common.MEDIA_TYPE_VIDEO,
                                                     media_start=0,
                                                     media_duration=gst.SECOND)
        self.source3 = common.TestTimelineFileSource(factory=factory,
                                                     name="source3",
                                                     media_type=common.MEDIA_TYPE_VIDEO,
                                                     media_start=0,
                                                     media_duration=gst.SECOND)

    def _compositionStartDurationChangedCb(self, comp, start, duration):
        self.compstart = start
        self.compduration = duration

    def tearDown(self):
        # remove all sources and their linked element
        if self.composition:
            for source in self.composition.condensed:
                self.composition.removeSource(source)
            self.assertEquals(self.composition.condensed, [])

        del self.composition

        # there might be some sources only present in the other composition
        for source in self.othercomposition.condensed:
            self.othercomposition.removeSource(source)
        self.assertEquals(self.othercomposition.condensed, [])

        del self.othercomposition

        del self.source1
        del self.source2
        del self.source3
        gc.collect()

    def testRemoveSourceBasic(self):
        self.composition.appendSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother()])
        self.assertEquals(self.compduration, gst.SECOND)

        self.composition.removeSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [])
        self.assertEquals(self.othercomposition.condensed,
                          [])
        self.assertEquals(self.compduration, 0)

    def testRemoveSourceCollapseNeighbourLinked(self):
        # [source1, source2] with auto-linked brothers
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother()])
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # remove source1 to end up with source2 at the beginning
        self.composition.removeSource(self.source1, collapse_neighbours=True)
        self.assertEquals(self.composition.condensed,
                          [self.source2])
        self.assertEquals(self.source2.start, 0)
        self.assertEquals(self.othercomposition.condensed,
                          [self.source2.getBrother()])
        self.assertEquals(self.source2.getBrother().start, 0)
        self.assertEquals(self.compduration, gst.SECOND)


    def testRemoveSourceNotCollapseNeighbourLinked(self):
        # [source1, source2] with auto-linked brothers
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother()])
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # remove source1 to end up with source2 at the beginning
        self.composition.removeSource(self.source1, collapse_neighbours=False)
        self.assertEquals(self.composition.condensed,
                          [self.source2])
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.othercomposition.condensed,
                          [self.source2.getBrother()])
        self.assertEquals(self.source2.getBrother().start, gst.SECOND)
        self.assertEquals(self.compstart, gst.SECOND)
        self.assertEquals(self.compduration, gst.SECOND)


    def testRemoveSourceCollapseNeighbourNotLinked(self):
        # [source1, source2] with auto-linked brothers
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother()])
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # remove source1 with remove_linked=False, collapse_neighbours=True
        self.assertRaises(Exception,
                          self.composition.removeSource, self.source1,
                          remove_linked=False,
                          collapse_neighbours=True)


    def testRemoveSourceNotCollapseNeighbourNotLinked(self):
        # [source1, source2] with auto-linked brothers
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother()])
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # remove source1 with remove_linked=False, collapse_neighbours=False
        self.composition.removeSource(self.source1, 
                                      collapse_neighbours=False,
                                      remove_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source2])
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.compstart, gst.SECOND)
        self.assertEquals(self.compduration, gst.SECOND)
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother()])
        self.assertEquals(self.source1.getBrother().start, 0)
        self.assertEquals(self.source2.getBrother().start, gst.SECOND)




    def testMoveSource1(self):
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.composition.appendSource(self.source3)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother(),
                           self.source3.getBrother()])
        self.assertEquals(self.compduration, 3 * gst.SECOND)

        # move source2 to the middle position
        self.composition.moveSource(self.source3, 1)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source3, self.source2])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source3.start, gst.SECOND)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.assertEquals(self.compduration, 3 * gst.SECOND)


    def testMoveSource2(self):
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.composition.appendSource(self.source3)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother(),
                           self.source3.getBrother()])
        self.assertEquals(self.compduration, 3 * gst.SECOND)

        # move source3 to the beginning
        self.composition.moveSource(self.source3, 0)
        self.assertEquals(self.composition.condensed,
                          [self.source3, self.source1, self.source2])
        self.assertEquals(self.source3.start, 0)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.assertEquals(self.compduration, 3 * gst.SECOND)


    def testMoveSource3(self):
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.composition.appendSource(self.source3)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother(),
                           self.source3.getBrother()])
        self.assertEquals(self.compduration, 3 * gst.SECOND)

        # move source1 just before source3
        self.composition.moveSource(self.source1, 2)
        self.assertEquals(self.composition.condensed,
                          [self.source2, self.source1, self.source3])
        self.assertEquals(self.source2.start, 0)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.source3.start, 2 * gst.SECOND)
        self.assertEquals(self.compduration, 3 * gst.SECOND)


    def testMoveSource4(self):
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.composition.appendSource(self.source3)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother(),
                           self.source3.getBrother()])
        self.assertEquals(self.compduration, 3 * gst.SECOND)

        # move source1 to the end
        self.composition.moveSource(self.source1, -1)
        self.assertEquals(self.composition.condensed,
                          [self.source2, self.source3, self.source1])
        self.assertEquals(self.source2.start, 0)
        self.assertEquals(self.source3.start, gst.SECOND)
        self.assertEquals(self.source1.start, 2 * gst.SECOND)
        self.assertEquals(self.compduration, 3 * gst.SECOND)

    def testMoveSourceSimpleAtBeginning(self):
        self.composition.appendSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.compduration, gst.SECOND)

        # move source1 to the beginning
        self.composition.moveSource(self.source1, 0)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.compduration, gst.SECOND)

    def testMoveSourceSimpleAtEnd(self):
        self.composition.appendSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.compduration, gst.SECOND)

        # move source1 to the end
        self.composition.moveSource(self.source1, -1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.compduration, gst.SECOND)

    def testMoveSourceSimpleReallyFar(self):
        self.composition.appendSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.compduration, gst.SECOND)

        # move source1 to a distant futur
        self.composition.moveSource(self.source1, 100)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.compduration, gst.SECOND)

        # move source1 to prehistoric times
        self.composition.moveSource(self.source1, -100)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.compduration, gst.SECOND)

    def testPrependSource(self):
        # put source1 at the beginning
        self.composition.prependSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.compduration, gst.SECOND)

        # put source2 before source1
        self.composition.prependSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source2, self.source1])
        self.assertEquals(self.source2.start, 0)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # put source3 before source2
        self.composition.prependSource(self.source3)
        self.assertEquals(self.composition.condensed,
                          [self.source3, self.source2, self.source1])
        self.assertEquals(self.source3.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.source1.start, 2 * gst.SECOND)
        self.assertEquals(self.compduration, 3 * gst.SECOND)

    def testAppendSourceNotAutoLinked(self):
        self.composition.appendSource(self.source1, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.othercomposition.condensed,
                          [])
        self.assertEquals(self.compduration, gst.SECOND)

        self.composition.appendSource(self.source2, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [])
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        self.composition.appendSource(self.source3, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        self.assertEquals(self.othercomposition.condensed,
                          [])
        self.assertEquals(self.compduration, 3 * gst.SECOND)

    def testAppendSourceAutoLinked(self):
        self.composition.appendSource(self.source1, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        brother1 = self.source1.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1])
        self.assertEquals(self.compduration, gst.SECOND)

        self.composition.appendSource(self.source2, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        brother2 = self.source2.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1, brother2])
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        self.composition.appendSource(self.source3, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        brother3 = self.source3.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1, brother2, brother3])
        self.assertEquals(self.compduration, 3 * gst.SECOND)


    def testInsertSourceAfter(self):
        # we want to end up with [source1, source2, source3]

        # first add source2 (after nothing)
        self.composition.insertSourceAfter(self.source2, None)
        self.assertEquals(self.composition.condensed,
                          [self.source2])
        self.assertEquals(self.compduration, gst.SECOND)

        # put source1 before source2 (after nothing)
        self.composition.insertSourceAfter(self.source1, None)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # put source3 after source2
        self.composition.insertSourceAfter(self.source3, self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        self.assertEquals(self.compduration, 3 * gst.SECOND)

    def testShiftSources(self):
        # [source1, source2]
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # 1. shift all forward
        self.composition.shiftSources(gst.SECOND, 0)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.assertEquals(self.compstart, gst.SECOND)
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # 2. shift all backwards
        self.composition.shiftSources(-gst.SECOND, 0)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.compstart, 0)
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # 3. shift last forward
        self.composition.shiftSources(gst.SECOND, 1)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.assertEquals(self.compstart, 0)
        self.assertEquals(self.compduration, 3 * gst.SECOND)

        # 4. shift first forward
        self.composition.shiftSources(gst.SECOND, 0, 1)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.assertEquals(self.compstart, gst.SECOND)
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # 5. shift first backwards
        self.composition.shiftSources(-gst.SECOND, 0, 1)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.assertEquals(self.compstart, 0)
        self.assertEquals(self.compduration, 3 * gst.SECOND)

        # 6. shift last backwards
        self.composition.shiftSources(-gst.SECOND, 1)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.compstart, 0)
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # 7. shift with startpos > endpos
        self.assertRaises(Exception,
                          self.composition.shiftSources, gst.SECOND,
                          1, 0)

        # 8. shift object that doesn't exist
        self.composition.shiftSources(gst.SECOND, 2)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.compstart, 0)
        self.assertEquals(self.compduration, 2 * gst.SECOND)

        # 9. shift with startpos == endpos => nothing happens
        self.composition.shiftSources(gst.SECOND, 1, 1)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.compstart, 0)
        self.assertEquals(self.compduration, 2 * gst.SECOND)

    def testAddSource(self):
        pass

    def testDefaultsource(self):
        pass

    def testSerializationBasic(self):
        # let's just serialize an empty composition
        compdata = self.composition.toDataFormat()

        del self.composition
        self.composition = None
        gc.collect()

        newcomp = to_object_from_data_type(compdata)
        self.assert_(newcomp)

    # FIXME : add tests for other methods
