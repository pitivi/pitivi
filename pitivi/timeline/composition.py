# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/composition.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Timeline Composition object
"""

import gobject
import gst

from source import TimelineSource
from objects import BrotherObjects, MEDIA_TYPE_AUDIO
from pitivi.serializable import to_object_from_data_type

class Layer(BrotherObjects):
    """
    Base class for composition layers (effects, sources, ...)
    """

    __data_type__ = "timeline-layer"

    def __init__(self):
        gobject.GObject.__init__(self)


class EffectsLayer(Layer):
    """
    Layers of the composition that have only one priority
    """

    __data_type__ = "timeline-effects-layer"

    def __init__(self, priority):
        Layer.__init__(self)
        self._priority = priority
        self._effects = []

    def __len__(self):
        return len(self._effects)

    def __getitem__(self, x):
        return self._effects.__getitem__(x)

class SourcesLayer(Layer):
    """
    Layers of the composition that have minimum and maximum priority
    Sources are sorted by start time and then by priority
    """

    __data_type__ = "timeline-sources-layer"

    def __init__(self, minprio, maxprio):
        Layer.__init__(self)
        self._minprio = minprio
        self._maxprio = maxprio
        self._sources = []

    def __len__(self):
        return len(self._sources)

    def __contains__(self, source):
        return self._sources.__contains__(source)

    def index(self, source):
        return self._sources.index(source)


class TimelineComposition(TimelineSource):
    """
    Combines sources and effects
    _ Sets the priority of the GnlObject(s) contained within
    _ Effects have always got priorities higher than the sources
    _ Can contain global effects that have the highest priority
      _ Those global effect spread the whole duration of the composition
    _ Simple effects (applies on one source), can overlap each other
    _ Complex Effect(s) have a lower priority than Simple Effect(s)
      _ For sanity reasons, Complex Effect(s) can't overlap each other
    _ Transitions have the lowest effect priority
    _ Source(s) contained in it follow each other if possible
    _ Source can overlap each other
      _ Knows the "visibility" of the sources contained within

    _ Provides a "condensed list" of the objects contained within
      _ Allows to quickly show a top-level view of the composition

    * Sandwich view example (top: high priority):
             [ Global Simple Effect(s) (RGB, YUV, Speed,...)    ]
             [ Simple Effect(s), can be several layers          ]
             [ Complex Effect(s), non-overlapping               ]
             [ Transition(s), non-overlapping                   ]
             [ Layers of sources                                ]

    * Properties:
      _ Global Simple Effect(s) (Optionnal)
      _ Simple Effect(s)
      _ Complex Effect(s)
      _ Transition(s)
      _ Condensed list

    * Signals:
      _ 'condensed-list-changed' : condensed list
      _ 'global-effect-added' : a global-effect was added to the composition
      _ 'global-effect-removed' : a global-effect was removed from the composition
      _ 'simple-effect-added' : a simple-effect was added to the composition
      _ 'simple-effect-removed' : a simple-effect was removed from the composition
      _ 'complex-effect-added' : a complex-effect was added to the composition
      _ 'complex-effect-removed' : a complex-effect was removed from the composition
      _ 'transition-added' : a transition was added to the composition
      _ 'transition-removed' : a transitions was removed from the composition
      _ 'source-added' : a TimelineSource was added to the composition
      _ 'source-removed' : a TimelineSource was removed from the composition

    Save/Load properties:
    * (optional) 'global-effects' (list of TimelineSimpleEffect) : list of global effects
    * (optional) 'simple-effects' (list of list of TimelineSimpleEffect) : list of list of simple effects
    * (optional) 'complex-effects' (list of TimelineComplexEffect) : list of complex effects
    * (optional) 'transitions' (list of TimelineTransition) : list of transitions
    * 'sources' (list of list of sources) : layers of sources of the composition
    * (optional) 'default-source' (TimelineSource) : Default source for the composition.
    """

    __gsignals__ = {
        'condensed-list-changed' : ( gobject.SIGNAL_RUN_LAST,
                                     gobject.TYPE_NONE,
                                     (gobject.TYPE_PYOBJECT, )),
        'global-effect-added' : ( gobject.SIGNAL_RUN_LAST,
                                  gobject.TYPE_NONE,
                                  (gobject.TYPE_PYOBJECT, )),
        'global-effect-removed' : ( gobject.SIGNAL_RUN_LAST,
                                    gobject.TYPE_NONE,
                                    (gobject.TYPE_PYOBJECT, )),
        'simple-effect-added' : ( gobject.SIGNAL_RUN_LAST,
                                  gobject.TYPE_NONE,
                                  (gobject.TYPE_PYOBJECT, )),
        'simple-effect-removed' : ( gobject.SIGNAL_RUN_LAST,
                                    gobject.TYPE_NONE,
                                    (gobject.TYPE_PYOBJECT, )),
        'complex-effect-added' : ( gobject.SIGNAL_RUN_LAST,
                                   gobject.TYPE_NONE,
                                   (gobject.TYPE_PYOBJECT, )),
        'complex-effect-removed' : ( gobject.SIGNAL_RUN_LAST,
                                     gobject.TYPE_NONE,
                                     (gobject.TYPE_PYOBJECT, )),
        'transitions-added' : ( gobject.SIGNAL_RUN_LAST,
                                gobject.TYPE_NONE,
                                (gobject.TYPE_PYOBJECT, )),
        'transition-removed' : ( gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject.TYPE_PYOBJECT, )),
        'source-added' : ( gobject.SIGNAL_RUN_LAST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_PYOBJECT, )),
        'source-removed' : ( gobject.SIGNAL_RUN_LAST,
                             gobject.TYPE_NONE,
                             (gobject.TYPE_PYOBJECT, )),
        }

    __data_type__ = "timeline-composition"
    __requires_factory__ = False

    # mid-level representation/storage of sources/effecst lists
    #
    # Global effects:
    #   Apply on the whole duration of the composition.
    #   Sorted by priority (first: most important)
    #
    # Simple effects:
    #   2 dimensional list
    #   Priority, then time
    #
    # Complex effect:
    # Transitions:
    #   Simple list sorted by time
    #
    # Source List:
    #   List of layers
    #   Layers:
    #      Handles priority attribution to contained sources
    #      3-tuple:
    #      _ minimum priority
    #      _ maximum priority
    #      _ list of sources sorted by time

    def __init__(self, **kw):
        self.global_effects = [] # list of effects starting from highest priority
        self.simple_effects = [] # list of layers of simple effects (order: priority, then time)
        self.complex_effects = [] # complex effect sorted by time
        self.transitions = [] # transitions sorted by time
        # list of layers of simple effects (order: priority, then time)
        self.condensed = [] # list of sources/transitions seen from a top-level view
        # each layer contains (min priority, max priority, list objects)
        #sources = [(2048, 2060, [])]
        self.sources = [(2048, 2060, [])]
        self.defaultSource = None
        TimelineSource.__init__(self, **kw)
        self.setStartDurationTime(0,0)

    def __len__(self):
        """ return the number of sources in this composition """
        l = 0
        for min, max, sources in self.sources:
            l += len(sources)
        return l

    def __nonzero__(self):
        """ Always returns True, else bool(object) will return False if len(object) == 0 """
        return True

    def _makeGnlObject(self):
        return gst.element_factory_make("gnlcomposition", "composition-" + self.name)

    # global effects

    def addGlobalEffect(self, global_effect, order, auto_linked=True):
        """
        add a global effect
        order :
           n : put at the given position (0: first)
           -1 : put at the end (lowest priority)
        auto_linked : if True will add the brother (if any) of the given effect
                to the linked composition with the same order
        """
        raise NotImplementedError

    def removeGlobalEffect(self, global_effect, remove_linked=True):
        """
        remove a global effect
        If remove_linked is True and the effect has a linked effect, will remove
        it from the linked composition
        """
        raise NotImplementedError

    # simple effects

    def addSimpleEffect(self, simple_effect, order, auto_linked=True):
        """
        add a simple effect

        order works if there's overlapping:
           n : put at the given position (0: first)
           -1 : put underneath all other simple effects
        auto_linked : if True will add the brother (if any) of the given effect
                to the linked composition with the same order
        """
        raise NotImplementedError

    def removeSimpleEffect(self, simple_effect, remove_linked=True):
        """
        removes a simple effect
        If remove_linked is True and the effect has a linked effect, will remove
        it from the linked composition
        """
        raise NotImplementedError

    # complex effect

    def addComplexEffect(self, complex_effect, auto_linked=True):
        """
        adds a complex effect
        auto_linked : if True will add the brother (if any) of the given effect
                to the linked composition with the same order
        """
        # if it overlaps with existing complex effect, raise exception
        raise NotImplementedError

    def removeComplexEffect(self, complex_effect, remove_linked=True):
        """
        removes a complex effect
        If remove_linked is True and the effect has a linked effect, will remove
        it from the linked composition
        """
        raise NotImplementedError

    def _makeCondensedList(self):
        """ makes a condensed list """
        def condensed_sum(list1, list2):
            """ returns a condensed list of the two given lists """
            self.gnlobject.info( "condensed_sum")
            self.gnlobject.info( "comparing %s with %s" % (list1, list2))
            if not len(list1):
                return list2[:]
            if not len(list2):
                return list1[:]

            res = list1[:]

            # find the objects in list2 that go under list1 and insert them at
            # the good position in res
            for obj in list2:
                # go through res to see if it can go somewhere
                for pos in range(len(res)):
                    if obj.start <= res[pos].start:
                        res.insert(pos, obj)
                        break
                if pos == len(res) and obj.start > res[-1].start:
                    res.append(obj)
            self.gnlobject.info("returning %s" % res)
            return res


        lists = [x[2] for x in self.sources]
        lists.insert(0, self.transitions)
        return reduce(condensed_sum, lists)

    def _updateCondensedList(self):
        """ updates the condensed list """
        self.gnlobject.info("_update_condensed_list")
        # build a condensed list
        clist = self._makeCondensedList()
        self.gnlobject.info("clist:%r" % clist)
        if self.condensed:
            # compare it to the self.condensed
            list_changed = False
            if not len(clist) == len(self.condensed):
                list_changed = True
            else:
                for a, b in zip(clist, self.condensed):
                    if not a == b:
                        list_changed = True
                        break
        else:
            list_changed = True
        self.gnlobject.log("list_change : %s" % list_changed)
        # if it's different or new, set it to self.condensed and emit the signal
        if list_changed:
            self.condensed = clist
            self.emit("condensed-list-changed", self.condensed)

    # Transitions

    def addTransition(self, transition, source1, source2, auto_linked=True):
        """
        adds a transition between source1 and source2
        auto_linked : if True will add the brother (if any) of the given transition
                to the linked composition with the same parameters
        """
        # if it overlaps with existing transition, raise exception
        raise NotImplementedError

    def moveTransition(self, transition, source1, source2):
        """ move a transition between source1 and source2 """
        # if it overlays with existing transition, raise exception
        raise NotImplementedError

    def removeTransition(self, transition, reorder_sources=True, remove_linked=True):
        """
        removes a transition,
        If reorder sources is True it puts the sources
        between which the transition was back one after the other
        If remove_linked is True and the transition has a linked effect, will remove
        it from the linked composition
        """
        raise NotImplementedError

    # Sources

    def getSourceLayerPosition(self, source):
        """
        Returns the layer position of the given source in the timeline.
        First position = 1
        Not found = 0
        """
        position = 0
        foundit = False
        for slist in self.sources:
            if source in slist[2]:
                foundit = True
                break
            position = position + 1
        if foundit:
            return position + 1
        return 0

    def getSimpleSourcePosition(self, source):
        """
        Returns the position of the given source in the timeline.
        First position = 1
        Not found = 0
        """
        layer = self.getSourceLayerPosition(source)
        if not layer:
            return 0
        return self.sources[layer - 1][2].index(source) + 1

    def _haveGotThisSource(self, source):
        for slist in self.sources:
            if source in slist[2]:
                return True
        return False


    def _addSource(self, source, position):
        """ private version of addSource """
        def my_add_sorted(sources, object):
            slist = sources[2]
            i = 0
            for item in slist:
                if item.start > object.start:
                    break
                i = i + 1
            object.gnlobject.set_property("priority", sources[0])
            slist.insert(i, object)

        # TODO : add functionnality to add above/under
        # For the time being it's hardcoded to a single layer
        position = 1

        # add it to the correct self.sources[position]
        my_add_sorted(self.sources[position-1], source)

        # add it to self.gnlobject
        self.gnlobject.info("adding %s to our composition" % source.gnlobject)
        self.gnlobject.add(source.gnlobject)

        self.gnlobject.info("added source %s" % source.gnlobject)
        gst.info("%s" % str(self.sources))
        self.emit('source-added', source)

        # update the condensed list
        self._updateCondensedList()

    def addSource(self, source, position, auto_linked=True):
        """
        add a source (with correct start/duration time already set)
        position : the vertical position
          _ 0 : insert above all other layers
          _ n : insert at the given position (1: top row)
          _ -1 : insert at the bottom, under all sources
        auto_linked : if True will add the brother (if any) of the given source
                to the linked composition with the same parameters
        """
        self.gnlobject.info("source %s , position:%d, self.sources:%s" %(source, position, self.sources))

        # make sure object to add has valid start/duration
        if source.start == -1 or source.duration <= 0:
            self.gnlobject.warning("Trying to add a source with non-valid start/duration")
            raise Exception("Source has invalid start[%s] or duration[%s]" % (gst.TIME_ARGS(source.start),
                                                                              gst.TIME_ARGS(source.duration)))

        self._addSource(source, position)

        # if auto_linked and self.linked, add brother to self.linked with same parameters
        if auto_linked and self.linked:
            if source.getBrother():
                self.linked._addSource(source.brother, position)

    def insertSourceAfter(self, source, existingsource, push_following=True, auto_linked=True):
        """
        inserts a source after the existingsource, pushing the following ones
        if existingsource is None, it puts the source at the beginning
        """
        if existingsource:
            self.gnlobject.info("insert_source after %s" % existingsource.gnlobject)
        else:
            self.gnlobject.info("insert_source at the beginning")

        # find the time where it's going to be added
        if not existingsource or not self._haveGotThisSource(existingsource):
            start = 0
            position = 1
            existorder = 0
        else:
            start = existingsource.start + existingsource.duration
            position = self.getSourceLayerPosition(existingsource)
            existorder = self.sources[position - 1][2].index(existingsource) + 1

        gst.info("start=%s, position=%d, existorder=%d, sourcelength=%s" % (gst.TIME_ARGS(start),
                                                                            position,
                                                                            existorder,
                                                                            gst.TIME_ARGS(source.factory.length)))
        # set the correct start/duration time
        duration = source.factory.length
        source.setStartDurationTime(start, duration)

        # pushing following
        if push_following and not position in [-1, 0]:
            #print self.gnlobject, "pushing following", existorder, len(self.sources[position - 1][2])
            self.shiftSources(source.factory.length, existorder, len(self.sources[position - 1][2]))

        self.addSource(source, position, auto_linked=auto_linked)

    def appendSource(self, source, position=1, auto_linked=True):
        """
        puts a source after all the others.
        position is the layer number
        """
        self.gnlobject.info("source:%s" % source.gnlobject)

        # find the source with the highest duration time on the first layer
        if self.sources[position - 1] and len(self.sources[position - 1][2]):
            existingsource = self.sources[position - 1][2][-1]
        else:
            existingsource = None

        self.insertSourceAfter(source, existingsource, push_following=False,
                               auto_linked=auto_linked)

    def prependSource(self, source, push_following=True, auto_linked=True):
        """
        adds a source to the beginning of the sources
        """
        self.gnlobject.info("source:%s" % source.gnlobject)
        self.insertSourceAfter(source, None, push_following, auto_linked)

    def moveSource(self, source, newpos, move_linked=True, push_neighbours=True, collapse_neighbours=True):
        """
        Moves the source to the new position. The position is the existing source before which to move
        the source.

        If move_linked is True and the source has a linked source, the linked source will
        be moved to the same position.
        If collapse_neighbours is True, all sources located AFTER the OLD position of the
        source will be shifted in the past by the duration of the removed source.
        If push_neighbours is True, then sources located AFTER the NEW position will be shifted
        forward in time, in order to have enough free space to insert the source.
        """
        self.gnlobject.info("source:%s , newpos:%d, move_linked:%s, push_neighbours:%s, collapse_neighbours:%s" % (source,
                                                                                                                   newpos,
                                                                                                                   move_linked,
                                                                                                                   push_neighbours,
                                                                                                                   collapse_neighbours))
        sources = self.sources[0][2]
        oldpos = sources.index(source)

        # limit newpos to sane values
        if (newpos == -1) or (newpos > len(sources)):
            # we want to move the source at the end
            newpos = len(sources)
        elif (newpos < -1):
            # we want to move the source at the beginning
            newpos = 0

        self.gnlobject.info("source was at position %d in his layer" % oldpos)

        # if we're not moving, return
        if (oldpos == newpos) or ((newpos == len(sources)) and (oldpos == newpos - 1)):
            self.gnlobject.warning("source is already at the correct position, not moving")
            return

        # 0. Temporarily remove moving source from composition
        self.gnlobject.log("Setting source priority at maximum [%d]" % self.sources[0][1])
        source.gnlobject.set_property("priority", self.sources[0][1])

        # 1. if collapse_neighbours, shift all downstream sources by duration
        if collapse_neighbours and oldpos != len(sources) - 1:
            self.gnlobject.log("collapsing all following neighbours after the old position [%d]" % oldpos)
            self.shiftSources(-source.duration, oldpos + 1)

        # 2. if push_neighbours, make sure there's enough room at the new position
        if push_neighbours and newpos != len(sources):
            pushmin = source.duration
            if newpos != 0:
                pushmin += sources[newpos - 1].start + sources[newpos - 1].duration
            self.gnlobject.log("We need to make sure sources after newpos are at or after %s" % gst.TIME_ARGS(pushmin))
            if sources[newpos].start < pushmin:
                # don't push sources after old position
                if oldpos > newpos:
                    stoppos = oldpos
                else:
                    stoppos = len(sources)
                self.gnlobject.log("pushing neighbours between new position [%d] and stop [%d]" % (newpos, stoppos))
                for i in range(newpos, stoppos):
                    obj = sources[i]
                    obj.setStartDurationTime(start = pushmin)
                    pushmin += obj.duration

        # 3. move the source
        newtimepos = 0
        if newpos:
            newtimepos += sources[newpos - 1].start + sources[newpos - 1].duration
        self.gnlobject.log("Setting source start position to %s" % gst.TIME_ARGS(newtimepos))
        source.setStartDurationTime(start = newtimepos)

        # take into account the offset of removing the source from the list
        if oldpos < newpos:
            newpos -= 1

        self.gnlobject.log("Inserting source to position [%d]" % (newpos))
        del sources[oldpos]
        sources.insert(newpos, source)
        source.gnlobject.set_property("priority", self.sources[0][0])

        # 4. same thing for brother
        # FIXME : TODO

        # 5. update condensed list
        self.gnlobject.log("Done moving %s , updating condensed list" % source)
        self._updateCondensedList()

    def removeSource(self, source, remove_linked=True, collapse_neighbours=False):
        """
        Removes a source.

        If remove_linked is True and the source has a linked source, will remove
        it from the linked composition.
        If collapse_neighbours is True, then all object after the removed source
        will be shifted in the past by the duration of the removed source.

        You cannot have remove_linked=False and collapse_neighbours=True !
        """
        if collapse_neighbours and not remove_linked:
            raise Exception("You cannot use remove_linked=False and collapse_neighbourse=True")
        self.gnlobject.info("source:%s, remove_linked:%s, collapse_neighbours:%s" % (source, remove_linked, collapse_neighbours))
        sources = self.sources[0]

        pos = sources[2].index(source)
        self.gnlobject.info("source was at position %d in his layer" % pos)

        # actually remove it
        self.gnlobject.info("Really removing %s from our composition" % source.gnlobject)
        self.gnlobject.remove(source.gnlobject)
        del sources[2][pos]

        # collapse neighbours, changing the start/duration will automatically
        # change it for the linked sources
        if collapse_neighbours:
            self.gnlobject.info("Collapsing neighbours")
            self.shiftSources(-source.duration, pos)

        # if we have a brother
        if remove_linked and self.linked and source.linked:
            sources = self.linked.sources[0]
            if source.linked in sources[2]:
                pos = sources[2].index(source.linked)
                del sources[2][pos]
                self.linked.gnlobject.remove(source.linked.gnlobject)
                self.linked.emit('source-removed', source.linked)
                self.linked._updateCondensedList()

        self.emit('source-removed', source)
        # update the condensed list
        self._updateCondensedList()

    def shiftSources(self, offset, startpos, endpos=-1):
        """
        Shifts by offset ns (can be negative) all sources from the given start
        position to the given end position.
        If no end position is specified (default:-1) all sources starting from
        the given start position will be shifted.
        """
        self.gnlobject.info("offset:%d, startpos:%d, endpos:%d" % (offset, startpos, endpos))
        sources = self.sources[0]
        if endpos == -1:
            endpos = len(sources[2])
        if startpos > endpos:
            raise Exception("startpos needs to be smaller or equal to endpos !")
        for i in range(startpos, endpos):
            obj = sources[2][i]
            obj.gnlobject.log("Position %d , setting start from %d to %d" % (i, obj.start, obj.start + offset))
            obj.setStartDurationTime(start = (obj.start + offset))

    def shiftSourcesBySource(self, offset, startsource, endsource=None):
        """
        Shifts by offset ns (can be negative) all sources from the given start
        position to the given end position.
        If no end position is specified (default:-1) all sources starting from
        the given start position will be shifted.
        """
        self.gnlobject.info("offset:%d, startsource:%s, endsource:%s" % (offset, startsource, endsource))
        startpos = self.getSourcePosition(startsource)
        if endsource:
            endpos = self.getSourcePosition(endsource)
        else:
            endpos = -1
        self.shiftSources(offset, startpos, endpos)

    def cleanUp(self):
        """
        Removes all sources/effects from the composition
        """
        self.gnlobject.info("cleaning up")
        # effects

        for fx in self.global_effects:
            self.removeGlobalEffect(fx)
        for layer in self.simple_effects:
            for fx in layer:
                self.removeSimpleEffect(fx)
        for fx in self.complex_effects:
            self.removeComplexEffect(fx)
        for fx in self.transitions:
            self.removeTransition(fx)

        # sources
        for layer in self.sources:
            min, max, sources = layer
            for source in sources[:]:
                self.removeSource(source)

    # Default Source methods

    def setDefaultSource(self, source):
        """
        Adds a default source to the composition.
        Default sources will be used for gaps within the composition.
        """
        if self.defaultSource:
            self.gnlobject.remove(self.defaultSource)
        source.props.priority = 2 ** 32 - 1
        self.gnlobject.add(source)
        self.defaultSource = source

    def getDefaultSource(self):
        """
        Returns the default source.
        """
        return self.defaultSource


    # AutoSettings methods

    def _autoVideoSettings(self):
        # return a ExportSettings in which all videos of the composition
        # will be able to be exported without loss
        biggest = None
        # FIXME : we suppose we only have only source layer !!!
        # FIXME : we in fact return the first file's settings
        for source in self.sources[0][2]:
            if not biggest:
                biggest = source.getExportSettings()
            else:
                sets = source.getExportSettings()
                for prop in ['videowidth', 'videoheight',
                             'videopar', 'videorate']:
                    if sets.__getattribute__(prop) != biggest.__getattribute__(prop):
                        return biggest
        return biggest

    def _autoAudioSettings(self):
        # return an ExportSettings in which all audio source of the composition
        # will be able to be exported without (too much) loss
        biggest = None
        # FIXME : we suppose we only have only source layer !!!
        # FIXME : we in fact return the first file's settings
        for source in self.sources[0][2]:
            if not biggest:
                biggest = source.getExportSettings()
            else:
                sets = source.getExportSettings()
                for prop in ['audiorate', 'audiochannels', 'audiodepth']:
                    if sets.__getattribute__(prop) != biggest.__getattribute__(prop):
                        return biggest
        return biggest


    def _getAutoSettings(self):
        gst.log("len(self) : %d" % len(self))
        if not len(self):
            return None
        if len(self) == 1:
            # return the settings of our only source
            return self.sources[0][2][0].getExportSettings()
        else:
            if self.media_type == MEDIA_TYPE_AUDIO:
                return self._autoAudioSettings()
            else:
                return self._autoVideoSettings()

    # Serializable methods

    def toDataFormat(self):
        ret = TimelineSource.toDataFormat(self)

        # effects (optional)
        if self.global_effects:
            ret["global-effects"] = [fx.toDataFormat() for fx in self.global_effects]
        if self.simple_effects and len(self.simple_effects[0]):
            ret["simple-effects"] = [[fx.toDataFormat() for fx in ls] for ls in self.simple_effects]
        if self.complex_effects:
            ret["complex-effects"] = [fx.toDataFormat() for fx in self.complex_effects]
        if self.transitions:
            ret["transitions"] = [fx.toDataFormat() for fx in self.transitions]

        # sources
        # WARNING / FIXME / TODO : This is a temporary format !!!
        tmp = []
        for layer in self.sources:
            lay = []
            for source in layer[2]:
                lay.append(source.toDataFormat())
            tmp.append(lay)
        ret["sources"] = tmp

        # default source
        if self.defaultSource:
            ret["default-source"] = self.defaultSource.toDataFormat()
        return ret

    def fromDataFormat(self, obj):
        TimelineSource.fromDataFormat(self, obj)

        # effects
        if "global-effects" in obj:
            for fx in obj["global-effects"]:
                self.global_effects.append(to_object_from_data_type(fx))
        if "simple-effects" in obj:
            for line in obj["simple-effects"]:
                tmp = []
                for fx in line:
                    tmp.append(to_object_from_data_type(fx))
                self.simple_effects.append(tmp)
        if "complex-effects" in obj:
            for fx in obj["complex-effects"]:
                self.complex_effects.append(to_object_from_data_type(fx))
        if "transitions" in obj:
            for fx in obj["transitions"]:
                self.transitions.append(to_object_from_data_type(fx))

        # sources
        # WARNING / FIXME / TODO : This is a temporary format !!!
        gst.log("recreating sources")
        pos = 1
        for layer in obj["sources"]:
            for source in layer:
                self.addSource(to_object_from_data_type(source), pos)
            pos += 1

        # default source
        if "default-source" in obj:
            self.setDefaultSource(to_object_from_data_type(obj["default-source"]))
