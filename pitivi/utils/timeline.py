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
    """Base Exception for errors happening in L{Timeline}s or L{TimelineObject}s"""
    pass


class Selection(Signallable):
    """
    A collection of L{GES.TimelineObject}.

    Signals:
     - C{selection-changed} : The contents of the L{GES.Selection} changed.

    @ivar selected: Set of selected L{GES.TrackObject}
    @type selected: C{list}
    """

    __signals__ = {
        "selection-changed": []}

    def __init__(self):
        self.selected = set([])
        self.last_single_obj = None

    def setToObj(self, obj, mode):
        """
        Convenience method for calling L{setSelection} with a single L{GES.TimelineObject}

        @see: L{setSelection}
        """
        self.setSelection(set([obj]), mode)

    def addTimelineObject(self, timeline_object):
        """
        Add the given timeline_object to the selection.

        @param timeline_object: The object to add
        @type timeline_object: L{GES.TimelineObject}
        @raises TimelineError: If the object is already controlled by this
        Selection.
        """
        if timeline_object in self.timeline_objects:
            raise TimelineError("TrackObject already in this selection")

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
            if isinstance(obj, GES.TrackObject):
                selection.add(obj.get_timeline_object())
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
            for tckobj in obj.get_track_objects():
                if not isinstance(tckobj, GES.TrackEffect) and not isinstance(tckobj, GES.TrackTextOverlay):
                    tckobj.selected.selected = False

        for obj in self.selected - old_selection:
            for tckobj in obj.get_track_objects():
                if not isinstance(tckobj, GES.TrackEffect) and not isinstance(tckobj, GES.TrackTextOverlay):
                    tckobj.selected.selected = True

        self.emit("selection-changed")

    def getSelectedTrackObjs(self):
        """
        Returns the list of L{TrackObject} contained in this selection.
        """
        objects = []
        for timeline_object in self.selected:
            objects.extend(timeline_object.get_track_objects())

        return set(objects)

    def getSelectedTrackEffects(self):
        """
        Returns the list of L{TrackEffect} contained in this selection.
        """
        track_effects = []
        for timeline_object in self.selected:
            for track in timeline_object.get_track_objects():
                if isinstance(track, GES.TrackEffect):
                    track_effects.append(track)

        return track_effects

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
        @param focus: the TimelineObject or TrackObject which is to be the
        main target of interactive editing, such as the object directly under the
        mouse pointer
        @type focus: L{GES.TimelineObject} or L{GES.TrackObject}

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
        @type other: a set() of L{TimelineObject}s or L{TrackObject}s

        @param setting: The PiTiVi settings, used to get the snap_distance
        parametter

        @returns: An instance of L{pitivi.utils.timeline.EditingContext}
        """
        Signallable.__init__(self)

        # make sure focus is not in secondary object list
        other.difference_update(set((focus,)))

        self.other = other
        if isinstance(focus, GES.TrackObject):
            self.focus = focus.get_timeline_object()
        else:
            self.focus = focus
        self.timeline = timeline

        self.edge = edge
        self.mode = mode

        self.timeline.enable_update(False)

    def finish(self):
        """Clean up timeline for normal editing"""
        # TODO: post undo / redo action here
        self.timeline.enable_update(True)
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


class Controller(Loggable):

    """
        A controller which implements drag-and-drop bahavior on connected view
        objects in the timeline. Subclasses may override the drag_start, drag_end,
        pos, and set_pos methods
    """

    # note we SHOULD be using the gtk function for this, but it doesn't appear
    # to be exposed in pygtk
    __DRAG_THRESHOLD__ = Point(0, 0)

    _view = receiver()

    _dragging = None
    _canvas = None
    _cursor = None
    _ptr_within = False
    _last_click = None
    _initial = None
    _mousedown = None
    _last_event = None
    _pending_drag_start = None
    _pending_drag_end = False
    _shift_down = False
    _control_down = False
    _handle_enter_leave = True
    _handle_mouse_up_down = True
    _handle_motion_notify = True

    def __init__(self, instance, view=None):
        object.__init__(self)
        self._view = view
        self.app = instance
        Loggable.__init__(self)

## convenience functions

    def from_event(self, event):
        """returns the coordinates of an event"""
        return Point(*self._canvas.convert_from_pixels(event.x, event.y))

    def from_item_event(self, item, event):
        return Point(*self._canvas.convert_from_item_space(item,
            *self.from_event(event)))

    def to_item_space(self, item, point):
        return Point(*self._canvas.convert_to_item_space(item, *point))

    def pos(self, item):
        bounds = item.get_bounds()
        return Point(bounds.x1, bounds.y1)

## signal handlers

    @handler(_view, "enter_notify_event")
    def enter_notify_event(self, item, target, event):
        self._event_common(item, target, event)
        self._canvas.grab_focus(item)
        if self._cursor and item is target:
            event.window.set_cursor(self._cursor)
        if not self._dragging:
            self.enter(item, target)
        self._ptr_within = True
        return self._handle_enter_leave or self._dragging

    @handler(_view, "leave_notify_event")
    def leave_notify_event(self, item, target, event):
        self._event_common(item, target, event)
        self._canvas.keyboard_ungrab(item, event.time)
        self._ptr_within = False
        if not self._dragging:
            self.leave(item, target)
            event.window.set_cursor(ARROW)
        return self._handle_enter_leave or self._dragging

    @handler(_view, "button_press_event")
    def button_press_event(self, item, target, event):
        self._event_common(item, target, event)
        if not self._canvas:
            self._canvas = item.get_canvas()
        self._mousedown = self.pos(item) - self.transform(self.from_item_event(item, event))
        self._dragging = target
        self._initial = self.pos(target)
        self._pending_drag_start = (item, target, event)
        return self._handle_mouse_up_down

    @handler(_view, "motion_notify_event")
    def motion_notify_event(self, item, target, event):
        self._event_common(item, target, event)
        if self._dragging:
            if self._pending_drag_start is not None:
                pending_drag_start, self._pending_drag_start = self._pending_drag_start, None
                self._pending_drag_end = True
                self._drag_start(*pending_drag_start)

            self.set_pos(self._dragging,
                self.transform(self._mousedown + self.from_item_event(item, event)))
            return self._handle_motion_notify
        else:
            self.hover(item, target, event)
        return False

    @handler(_view, "button_release_event")
    def button_release_event(self, item, target, event):
        self._event_common(item, target, event)
        self._drag_end(item, self._dragging, event)
        self._dragging = None
        return self._handle_mouse_up_down

    @handler(_view, "key_press_event")
    def key_press_event(self, item, target, event):
        self._event_common(item, target, event)
        kv = event.keyval
        if kv in (Gdk.KEY_Shift_L, Gdk.KEY_Shift_R):
            self._shift_down = True
        elif kv in (Gdk.KEY_Control_L, Gdk.KEY_Control_R):
            self._control_down = True
        return self.key_press(kv)

    @handler(_view, "key_release_event")
    def key_release_event(self, item, target, event):
        self._event_common(item, target, event)
        kv = event.keyval
        if kv in (Gdk.KEY_Shift_L, Gdk.KEY_Shift_R):
            self._shift_down = False
        elif kv in (Gdk.KEY_Control_L, Gdk.KEY_Control_R):
            self._control_down = False
        return self.key_release(kv)

## internal callbacks

    def _event_common(self, item, target, event):
        if not self._canvas:
            self._canvas = item.get_canvas()
            # might there be a better way to do this?
            self._hadj = self._canvas.app.gui.timeline_ui.hadj
            self._vadj = self._canvas.app.gui.timeline_ui.vadj
        self._last_event = event
        _, s = event.get_state()
        self._shift_down = s & Gdk.ModifierType.SHIFT_MASK
        self._control_down = s & Gdk.ModifierType.CONTROL_MASK

    def _drag_start(self, item, target, event):
        self.drag_start(item, target, event)

    def _drag_end(self, item, target, event):
        self._pending_drag_start = None
        pending_drag_end, self._pending_drag_end = self._pending_drag_end, False
        if pending_drag_end:
            self.drag_end(item, target, event)

        if self._ptr_within and self._drag_threshold():
            point = self.from_item_event(item, event)
            if self._last_click and (event.time - self._last_click < 400):
                self.double_click(point)
            else:
                self.click(point)
            self._last_click = event.time
            event.window.set_cursor(self._cursor)
        else:
            event.window.set_cursor(ARROW)

    def _drag_threshold(self):
        last = self.pos(self._dragging)
        if abs(self._initial - last) > self.__DRAG_THRESHOLD__:
            return False
        return True

## protected interface for subclasses

    def click(self, pos):
        pass

    def double_click(self, pos):
        pass

    def drag_start(self, item, target, event):
        pass

    def drag_end(self, item, target, event):
        pass

    def set_pos(self, obj, pos):
        obj.props.x, obj.props.y = pos

    def transform(self, pos):
        return pos

    def enter(self, item, target):
        pass

    def leave(self, item, target):
        pass

    def key_press(self, keyval):
        pass

    def key_release(self, keyval):
        pass

    def hover(self, item, target, event):
        pass


class View(object):

    Controller = Controller

    def __init__(self, instance, default_mode=GES.EditMode.EDIT_NORMAL):
        object.__init__(self)
        self._controller = self.Controller(instance, default_mode, view=self)

## public interface

    def focus(self):
        pass

    def select(self):
        pass

    def activate(self):
        pass

    def normal(self):
        pass


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
    _cur_zoom = 2
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
