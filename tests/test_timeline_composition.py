import unittest
import common
from pitivi.serializable import to_object_from_data_type
from pitivi.timeline.objects import BrotherObjects, MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
from pitivi.objectfactory import ObjectFactory
from pitivi.timeline.composition import TimelineComposition
import gc
import gst

class TestTimelineComposition(unittest.TestCase):

    def setUp(self):
        self.composition = TimelineComposition(name="composition",
                                               media_type=MEDIA_TYPE_VIDEO)
        self.assert_(self.composition)

        self.othercomposition = TimelineComposition(name="othercomposition",
                                                    media_type=MEDIA_TYPE_AUDIO)
        self.assert_(self.othercomposition)

        self.composition.linkObject(self.othercomposition)
        self.assertEquals(self.composition.linked,
                          self.othercomposition)

        self.sigid = self.composition.connect("start-duration-changed",
                                              self._compositionStartDurationChangedCb)
        self.compstart = self.composition.start
        self.compduration = self.composition.duration

        # compositions have initial start==0, duration==0
        self.checkStartDuration(0,0)

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
        gc.collect()

    def tearDown(self):
        gst.log("tearing down")
        # remove all sources and their linked element
        if self.composition:
            self.composition.disconnect(self.sigid)
            self.composition.cleanUp()
            self.assertEquals(self.composition.condensed, [])

        del self.composition

        # there might be some sources only present in the other composition
        if self.othercomposition:
            self.othercomposition.cleanUp()
            self.assertEquals(self.othercomposition.condensed, [])

        del self.othercomposition

        del self.source1
        del self.source2
        del self.source3
        gc.collect()

        # Check all instances were removed
        if BrotherObjects.__instances__:
            print BrotherObjects.__instances__.values()
        self.assertEquals(len(BrotherObjects.__instances__), 0)
        if ObjectFactory.__instances__:
            print ObjectFactory.__instances__.values()
        self.assertEquals(len(ObjectFactory.__instances__), 0)

    def _compositionStartDurationChangedCb(self, comp, start, duration):
        self.compstart = start
        self.compduration = duration

    def checkStartDuration(self, start, duration):
        # convenience function for checking composition
        # start/duration both through object values
        # and through signal emission.
        self.assertEquals(self.composition.start, start)
        self.assertEquals(self.compstart, start)
        self.assertEquals(self.composition.duration, duration)
        self.assertEquals(self.compduration, duration)

    def testRemoveSourceBasic(self):
        self.composition.appendSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother()])
        self.checkStartDuration(0, gst.SECOND)

        self.composition.removeSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [])
        self.assertEquals(self.othercomposition.condensed,
                          [])
        self.checkStartDuration(0, 0)

    def testRemoveSourceCollapseNeighbourLinked(self):
        # [source1, source2] with auto-linked brothers
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother()])
        self.checkStartDuration(0, 2 * gst.SECOND)

        # remove source1 to end up with source2 at the beginning
        self.composition.removeSource(self.source1, collapse_neighbours=True)
        self.assertEquals(self.composition.condensed,
                          [self.source2])
        self.assertEquals(self.source2.start, 0)
        self.assertEquals(self.othercomposition.condensed,
                          [self.source2.getBrother()])
        self.assertEquals(self.source2.getBrother().start, 0)
        self.checkStartDuration(0, gst.SECOND)


    def testRemoveSourceNotCollapseNeighbourLinked(self):
        # [source1, source2] with auto-linked brothers
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother()])
        self.checkStartDuration(0, 2 * gst.SECOND)

        # remove source1 to end up with source2 at the beginning
        self.composition.removeSource(self.source1, collapse_neighbours=False)
        self.assertEquals(self.composition.condensed,
                          [self.source2])
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.othercomposition.condensed,
                          [self.source2.getBrother()])
        self.assertEquals(self.source2.getBrother().start, gst.SECOND)
        self.checkStartDuration(gst.SECOND, gst.SECOND)


    def testRemoveSourceCollapseNeighbourNotLinked(self):
        # [source1, source2] with auto-linked brothers
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [self.source1.getBrother(),
                           self.source2.getBrother()])
        self.checkStartDuration(0, 2 * gst.SECOND)

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
        self.checkStartDuration(0, 2 * gst.SECOND)

        # remove source1 with remove_linked=False, collapse_neighbours=False
        self.composition.removeSource(self.source1, 
                                      collapse_neighbours=False,
                                      remove_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source2])
        self.assertEquals(self.source2.start, gst.SECOND)
        self.checkStartDuration(gst.SECOND, gst.SECOND)
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
        self.checkStartDuration(0, 3 * gst.SECOND)

        # move source2 to the middle position
        self.composition.moveSource(self.source3, 1)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source3, self.source2])
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source3.start, gst.SECOND)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.checkStartDuration(0, 3 * gst.SECOND)


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
        self.checkStartDuration(0, 3 * gst.SECOND)

        # move source3 to the beginning
        self.composition.moveSource(self.source3, 0)
        self.assertEquals(self.composition.condensed,
                          [self.source3, self.source1, self.source2])
        self.assertEquals(self.source3.start, 0)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.checkStartDuration(0, 3 * gst.SECOND)


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
        self.checkStartDuration(0, 3 * gst.SECOND)

        # move source1 just before source3
        self.composition.moveSource(self.source1, 2)
        self.assertEquals(self.composition.condensed,
                          [self.source2, self.source1, self.source3])
        self.assertEquals(self.source2.start, 0)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.source3.start, 2 * gst.SECOND)
        self.checkStartDuration(0, 3 * gst.SECOND)


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
        self.checkStartDuration(0, 3 * gst.SECOND)

        # move source1 to the end
        self.composition.moveSource(self.source1, -1)
        self.assertEquals(self.composition.condensed,
                          [self.source2, self.source3, self.source1])
        self.assertEquals(self.source2.start, 0)
        self.assertEquals(self.source3.start, gst.SECOND)
        self.assertEquals(self.source1.start, 2 * gst.SECOND)
        self.checkStartDuration(0, 3 * gst.SECOND)

    def testMoveSourceSimpleAtBeginning(self):
        self.composition.appendSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.checkStartDuration(0, gst.SECOND)

        # move source1 to the beginning
        self.composition.moveSource(self.source1, 0)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.checkStartDuration(0, gst.SECOND)


    def testMoveSourceSimpleAtEnd(self):
        self.composition.appendSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.checkStartDuration(0, gst.SECOND)

        # move source1 to the end
        self.composition.moveSource(self.source1, -1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.checkStartDuration(0, gst.SECOND)


    def testMoveSourceSimpleReallyFar(self):
        self.composition.appendSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.checkStartDuration(0, gst.SECOND)

        # move source1 to a distant futur
        self.composition.moveSource(self.source1, 100)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.checkStartDuration(0, gst.SECOND)

        # move source1 to prehistoric times
        self.composition.moveSource(self.source1, -100)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.checkStartDuration(0, gst.SECOND)

    def testPrependSource(self):
        # put source1 at the beginning
        self.composition.prependSource(self.source1)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.source1.start, 0)
        self.checkStartDuration(0, gst.SECOND)

        # put source2 before source1
        self.composition.prependSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source2, self.source1])
        self.assertEquals(self.source2.start, 0)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.checkStartDuration(0, 2 * gst.SECOND)

        # put source3 before source2
        self.composition.prependSource(self.source3)
        self.assertEquals(self.composition.condensed,
                          [self.source3, self.source2, self.source1])
        self.assertEquals(self.source3.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.assertEquals(self.source1.start, 2 * gst.SECOND)
        self.checkStartDuration(0, 3 * gst.SECOND)

    def testAppendSourceNotAutoLinked(self):
        self.composition.appendSource(self.source1, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        self.assertEquals(self.othercomposition.condensed,
                          [])
        self.checkStartDuration(0, gst.SECOND)

        self.composition.appendSource(self.source2, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.assertEquals(self.othercomposition.condensed,
                          [])
        self.checkStartDuration(0, 2 * gst.SECOND)

        self.composition.appendSource(self.source3, auto_linked=False)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        self.assertEquals(self.othercomposition.condensed,
                          [])
        self.checkStartDuration(0, 3 * gst.SECOND)

    def testAppendSourceAutoLinked(self):
        self.composition.appendSource(self.source1, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1])
        brother1 = self.source1.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1])
        self.checkStartDuration(0, gst.SECOND)

        self.composition.appendSource(self.source2, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        brother2 = self.source2.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1, brother2])
        self.checkStartDuration(0, 2 * gst.SECOND)

        self.composition.appendSource(self.source3, auto_linked=True)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        brother3 = self.source3.getBrother()
        self.assertEquals(self.othercomposition.condensed,
                          [brother1, brother2, brother3])
        self.checkStartDuration(0, 3 * gst.SECOND)


    def testInsertSourceAfter(self):
        # we want to end up with [source1, source2, source3]

        # first add source2 (after nothing)
        self.composition.insertSourceAfter(self.source2, None)
        self.assertEquals(self.composition.condensed,
                          [self.source2])
        self.checkStartDuration(0, gst.SECOND)

        # put source1 before source2 (after nothing)
        self.composition.insertSourceAfter(self.source1, None)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.checkStartDuration(0, 2 * gst.SECOND)

        # put source3 after source2
        self.composition.insertSourceAfter(self.source3, self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2, self.source3])
        self.checkStartDuration(0, 3 * gst.SECOND)

    def testShiftSources(self):
        # [source1, source2]
        self.composition.appendSource(self.source1)
        self.composition.appendSource(self.source2)
        self.assertEquals(self.composition.condensed,
                          [self.source1, self.source2])
        self.checkStartDuration(0, 2 * gst.SECOND)

        # 1. shift all forward
        self.composition.shiftSources(gst.SECOND, 0)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.checkStartDuration(gst.SECOND, 2 * gst.SECOND)

        # 2. shift all backwards
        self.composition.shiftSources(-gst.SECOND, 0)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.checkStartDuration(0, 2 * gst.SECOND)

        # 3. shift last forward
        self.composition.shiftSources(gst.SECOND, 1)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.checkStartDuration(0, 3 * gst.SECOND)

        # 4. shift first forward
        self.composition.shiftSources(gst.SECOND, 0, 1)
        self.assertEquals(self.source1.start, gst.SECOND)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.checkStartDuration(gst.SECOND, 2 * gst.SECOND)

        # 5. shift first backwards
        self.composition.shiftSources(-gst.SECOND, 0, 1)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, 2 * gst.SECOND)
        self.checkStartDuration(0, 3 * gst.SECOND)

        # 6. shift last backwards
        self.composition.shiftSources(-gst.SECOND, 1)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.checkStartDuration(0, 2 * gst.SECOND)

        # 7. shift with startpos > endpos
        self.assertRaises(Exception,
                          self.composition.shiftSources, gst.SECOND,
                          1, 0)

        # 8. shift object that doesn't exist
        self.composition.shiftSources(gst.SECOND, 2)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.checkStartDuration(0, 2 * gst.SECOND)

        # 9. shift with startpos == endpos => nothing happens
        self.composition.shiftSources(gst.SECOND, 1, 1)
        self.assertEquals(self.source1.start, 0)
        self.assertEquals(self.source2.start, gst.SECOND)
        self.checkStartDuration(0, 2 * gst.SECOND)

    def testAddSource(self):
        # make sure adding a source with invalid start/duration
        # is detected

        # invalid start, valid duration
        self.source1.start = -1
        self.source1.duration = gst.SECOND
        self.assertRaises(Exception,
                          self.composition.addSource, self.source1)

        # no duration, valid start
        self.source1.start = 0
        self.source1.duration = 0
        self.assertRaises(Exception,
                          self.composition.addSource, self.source1)

        # invalid duration, valid start
        self.source1.start = 0
        self.source1.duration = -1
        self.assertRaises(Exception,
                          self.composition.addSource, self.source1)


    def testDefaultsource(self):
        pass

    def testSerializationSingleCompositionSingleSource(self):
        # create a composition with one source in it
        composition = TimelineComposition(name="comp")
        self.assert_(composition)
        factory = common.TestFileSourceFactory(audio=True, video=True)

        source = common.TestTimelineFileSource(factory=factory,
                                               name="source-new",
                                               media_type=common.MEDIA_TYPE_VIDEO,
                                               media_start=0,
                                               media_duration=gst.SECOND)
        self.assert_(source)

        composition.appendSource(source, 1, auto_linked=False)

        # Serialize the composition AND the factory
        data = composition.toDataFormat()
        facdata = factory.toDataFormat()

        # remove everything
        del source
        source = None
        composition.cleanUp()
        del composition
        composition = None
        del factory
        factory = None
        gc.collect()

        # make sure every instance of objects and factories were removed
        self.assertEquals(len(BrotherObjects.__instances__), 0)
        self.assertEquals(len(ObjectFactory.__instances__), 0)

        # recreate factory then composition
        factory = to_object_from_data_type(facdata)
        self.assert_(factory)

        comp = to_object_from_data_type(data)
        self.assert_(comp)

        # checks
        self.assertEquals(comp.name, "comp")
        self.assertEquals(comp.start, 0)
        self.assertEquals(comp.duration, gst.SECOND)
        self.assertEquals(len(comp.condensed), 1)

        # we should have a source
        source = comp.condensed[0]
        self.assertEquals(source.start, 0)
        self.assertEquals(source.duration, gst.SECOND)
        self.assertEquals(source.factory, factory)

        # cleanup
        comp.cleanUp()
        del comp
        del factory

    def testSerializationBasic(self):
        """
        Serializing an empty composition
        """
        # let's just serialize an empty composition
        compdata = self.composition.toDataFormat()
        uid = self.composition.getUniqueID()

        # clean up
        self.composition.disconnect(self.sigid)
        del self.composition
        self.composition = None
        del self.othercomposition
        self.othercomposition = None
        gst.log("collecting!")
        gc.collect()

        newcomp = to_object_from_data_type(compdata)
        self.assert_(newcomp)
        self.assertEquals(newcomp.linked, self.othercomposition)
        self.assertEquals(newcomp.getUniqueID(), uid)
        self.assertEquals(newcomp.media_type, MEDIA_TYPE_VIDEO)

    def testSerializationBasicBothComposition(self):
        # Serialize both compositions
        compdata = self.composition.toDataFormat()
        otherdata = self.othercomposition.toDataFormat()
        uid1 = self.composition.getUniqueID()
        uid2 = self.othercomposition.getUniqueID()

        self.composition.disconnect(self.sigid)
        del self.composition
        self.composition = None
        del self.othercomposition
        self.othercomposition = None
        gc.collect()

        composition = to_object_from_data_type(compdata)
        self.assert_(composition)
        self.assertEquals(composition.getUniqueID(), uid1)
        self.assertEquals(composition.linked, None)
        self.assertEquals(composition.media_type, MEDIA_TYPE_VIDEO)

        othercomposition = to_object_from_data_type(otherdata)
        self.assert_(othercomposition)
        self.assertEquals(othercomposition.getUniqueID(), uid2)
        self.assertEquals(composition.linked, othercomposition)
        self.assertEquals(othercomposition.linked, composition)


    # FIXME : add tests for other methods
