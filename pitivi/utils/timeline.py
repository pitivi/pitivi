# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/timeline.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

from gi.repository import GES
from gi.repository import Gdk
from gi.repository import Gst

from pitivi.utils.loggable import Loggable
from pitivi.utils.signal import Signallable
from pitivi.utils.receiver import receiver, handler
from pitivi.utils.ui import Point

#from pitivi.utils.align import AutoAligner

# Selection modes
SELECT = 0
"""Set the selection to the given set."""
UNSELECT = 1
"""Remove the given set from the selection."""
SELECT_ADD = 2
"""Extend the selection with the given set"""
SELECT_BETWEEN = 3
"""Select a range of clips"""


#------------------------------------------------------------------------------#
#                          Timeline Object management helper                   #
class TimelineError(Exception):
    """Base Exception for errors happening in L{Timeline}s or L{Clip}s"""
    pass


class Selected(Signallable):
    """
    A simple class that let us emit a selected-changed signal
    when needed, and that can be check directly to know if the
    object is selected or not.

    This is meant only for individual elements, do not confuse this with
    utils.timeline's "Selection" class.
    """

    __signals__ = {
        "selected-changed": []}

    def __init__(self):
        self._selected = False
        self.movable = True

    def __nonzero__(self):
        """
        checking a Selected object is the same as checking its _selected
        property
        """
        return self._selected

    def getSelected(self):
        return self._selected

    def setSelected(self, selected):
        self._selected = selected
        self.emit("selected-changed", selected)

    selected = property(getSelected, setSelected)


class Selection(Signallable):
    """
    A collection of L{GES.Clip}.

    Signals:
     - C{selection-changed} : The contents of the L{GES.Selection} changed.

    @ivar selected: Set of selected L{GES.TrackElement}
    @type selected: C{list}
    """

    __signals__ = {
        "selection-changed": []}

    def __init__(self):
        self.selected = set([])
        self.last_single_obj = None

    def setToObj(self, obj, mode):
        """
        Convenience method for calling L{setSelection} with a single L{GES.Clip}

        @see: L{setSelection}
        """
        self.setSelection(set([obj]), mode)

    def addClip(self, clip):
        """
        Add the given clip to the selection.

        @param clip: The object to add
        @type clip: L{GES.Clip}
        @raises TimelineError: If the object is already controlled by this
        Selection.
        """
        if clip in self.clips:
            raise TimelineError("TrackElement already in this selection")

    def setSelection(self, objs, mode):
        """
        Update the current selection.

        Depending on the value of C{mode}, the selection will be:
         - L{SELECT} : set to the provided selection.
         - L{UNSELECT} : the same minus the provided selection.
         - L{SELECT_ADD} : extended with the provided selection.

        @param selection: The list of timeline objects to update the selection with.
        @param mode: The type of update to apply. Can be C{SELECT},C{UNSELECT} or C{SELECT_ADD}

        @see: L{setToObj}
        """
        # get a list of timeline objects
        selection = set()
        for obj in objs:
            # FIXME GES break, handle the fact that we have unlinked objects in GES
            if isinstance(obj, GES.TrackElement):
                selection.add(obj.get_parent())
            else:
                selection.add(obj)

        old_selection = self.selected
        if mode == SELECT_ADD:
            selection = self.selected | selection
        elif mode == UNSELECT:
            selection = self.selected - selection

        if selection == old_selection:
            # The user clicked on the same clip
            return
        self.selected = selection

        if len(self.selected) == 1:
            self.last_single_obj = iter(selection).next()

        for obj in old_selection - self.selected:
            for element in obj.get_children(False):
                if not isinstance(element, GES.BaseEffect) and not isinstance(element, GES.TextOverlay):
                    element.selected.selected = False

        for obj in self.selected - old_selection:
            for element in obj.get_children(False):
                if not isinstance(element, GES.BaseEffect) and not isinstance(element, GES.TextOverlay):
                    element.selected.selected = True

        self.emit("selection-changed")

    def getSelectedTrackElements(self):
        """
        Returns the list of L{TrackElement} contained in this selection.
        """
        objects = []
        for clip in self.selected:
            objects.extend(clip.get_children(False))

        return set(objects)

    def getSelectedEffects(self):
        """
        Returns the list of L{GES.BaseEffect} contained in this selection.
        """
        effects = []
        for clip in self.selected:
            for element in clip.get_children(False):
                if isinstance(element, GES.BaseEffect):
                    effects.append(element)

        return effects

    def __len__(self):
        return len(self.selected)

    def __iter__(self):
        return iter(self.selected)


#-----------------------------------------------------------------------------#
#                       Timeline edition modes helper                         #
class EditingContext(Signallable):
    """
        Encapsulates interactive editing.

        This is the main class for interactive edition.
    """

    __signals__ = {
        "clip-trim": ["uri", "position"],
        "clip-trim-finished": [],
    }

    def __init__(self, focus, timeline, mode, edge, other, settings):
        """
        @param focus: the Clip or TrackElement which is to be the
        main target of interactive editing, such as the object directly under the
        mouse pointer
        @type focus: L{GES.Clip} or L{GES.TrackElement}

        @param timeline: the timeline to edit
        @type timeline: instance of L{GES.Timeline}

        @param edge: The edge on which the edition will happen, this parametter
        can be change during the time using the same context.
        @type edge: L{GES.Edge}

        @param mode: The mode in which the edition will happen, this parametter
        can be change during the time using the same context.
        @type mode: L{GES.EditMode}

        @param other: a set of objects which are the secondary targets of
        interactive editing, such as objects in the current selection.
        @type other: a set() of L{Clip}s or L{TrackElement}s

        @param setting: The PiTiVi settings, used to get the snap_distance
        parametter

        @returns: An instance of L{pitivi.utils.timeline.EditingContext}
        """
        Signallable.__init__(self)

        # make sure focus is not in secondary object list
        other.difference_update(set((focus,)))

        self.other = other
        if isinstance(focus, GES.TrackElement):
            self.focus = focus.get_parent()
        else:
            self.focus = focus
        self.timeline = timeline

        self.edge = edge
        self.mode = mode

    def finish(self):
        """Clean up timeline for normal editing"""
        # TODO: post undo / redo action here
        self.timeline.commit()
        self.emit("clip-trim-finished")

    def setMode(self, mode):
        """Set the current editing mode.
        @param mode: the editing mode. Must be a GES.EditMode
        """
        self.mode = mode

    def editTo(self, position, priority):
        position = max(0, position)
        if self.edge in [GES.Edge.EDGE_START, GES.Edge.EDGE_END]:
            priority = -1
        else:
            priority = max(0, priority)

        res = self.focus.edit([], priority, self.mode, self.edge, long(position))
        if res and self.mode == GES.EditMode.EDIT_TRIM:
            if self.edge == GES.Edge.EDGE_START:
                self.emit("clip-trim", self.focus, self.focus.props.in_point)
            elif self.edge == GES.Edge.EDGE_END:
                self.emit("clip-trim", self.focus, self.focus.props.duration)


#-------------------------- Interfaces ----------------------------------------#

ARROW = Gdk.Cursor.new(Gdk.CursorType.ARROW)


class Zoomable(object):
    """
    Interface for managing tranformation between timeline timestamps and UI
    pixels.

    Complex Timeline interfaces v2 (01 Jul 2008)

    Zoomable
    -----------------------
    Interface for the Complex Timeline widgets for setting, getting,
    distributing and modifying the zoom ratio and the size of the widget.

    A zoomratio is the number of pixels per second
    ex : 10.0 = 10 pixels for a second
    ex : 0.1 = 1 pixel for 10 seconds
    ex : 1.0 = 1 pixel for a second
     Class Methods
    . pixelToNs(pixels)
    . nsToPixels(time)
    . setZoomRatio
    Instance Methods
    . zoomChanged()
    """

    sigid = None
    _instances = []
    max_zoom = 1000.0
    min_zoom = 0.25
    zoom_steps = 100
    zoom_range = max_zoom - min_zoom
    _cur_zoom = 20
    zoomratio = None

    def __init__(self):
        # FIXME: ideally we should deprecate this
        Zoomable.addInstance(self)
        if Zoomable.zoomratio is None:
            Zoomable.zoomratio = self.computeZoomRatio(self._cur_zoom)

    def __del__(self):
        if self in Zoomable._instances:
            # FIXME: ideally we should deprecate this and spit a warning here
            self._instances.remove(self)

    @classmethod
    def addInstance(cls, instance):
        cls._instances.append(instance)

    @classmethod
    def removeInstance(cls, instance):
        cls._instances.remove(instance)

    @classmethod
    def setZoomRatio(cls, ratio):
        if cls.zoomratio != ratio:
            cls.zoomratio = min(cls.max_zoom, max(cls.min_zoom, ratio))
            cls._zoomChanged()

    @classmethod
    def setZoomLevel(cls, level):
        level = min(cls.zoom_steps, max(0, level))
        if level != cls._cur_zoom:
            cls._cur_zoom = level
            cls.setZoomRatio(cls.computeZoomRatio(level))

    @classmethod
    def getCurrentZoomLevel(cls):
        return cls._cur_zoom

    @classmethod
    def zoomIn(cls):
        cls.setZoomLevel(cls._cur_zoom + 1)

    @classmethod
    def zoomOut(cls):
        cls.setZoomLevel(cls._cur_zoom - 1)

    @classmethod
    def computeZoomRatio(cls, x):
        return ((((float(x) / cls.zoom_steps) ** 3) * cls.zoom_range) +
            cls.min_zoom)

    @classmethod
    def computeZoomLevel(cls, ratio):
        return int((
            (max(0, ratio - cls.min_zoom) /
                cls.zoom_range) ** (1.0 / 3.0)) * cls.zoom_steps)

    @classmethod
    def pixelToNs(cls, pixel):
        """
        Returns the pixel equivalent in nanoseconds according to the zoomratio
        """
        return long(pixel * Gst.SECOND / cls.zoomratio)

    @classmethod
    def pixelToNsAt(cls, pixel, ratio):
        """
        Returns the pixel equivalent in nanoseconds according to the zoomratio
        """
        return long(pixel * Gst.SECOND / ratio)

    @classmethod
    def nsToPixel(cls, duration):
        """
        Returns the pixel equivalent of the given duration, according to the
        set zoom ratio
        """
        ## DIE YOU CUNTMUNCH CLOCK_TIME_NONE UBER STUPIDITY OF CRACK BINDINGS !!!!!!
        if duration == Gst.CLOCK_TIME_NONE:
            return 0
        return int((float(duration) / Gst.SECOND) * cls.zoomratio)

    @classmethod
    def _zoomChanged(cls):
        for inst in cls._instances:
            inst.zoomChanged()

    def zoomChanged(self):
        pass
