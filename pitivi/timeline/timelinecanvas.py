# PiTiVi , Non-linear video editor
#
#       pitivi/ui/timelinecanvas.py
#
# Copyright (c) 2009, Brandon Lewis <brandon_lewis@berkeley.edu>
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

import gtk
import goocanvas
from gettext import gettext as _

from pitivi.settings import GlobalSettings

from pitivi.timeline.track import Track, TrackObject

from pitivi.ui.prefs import PreferencesDialog
from pitivi.timeline.curve import KW_LABEL_Y_OVERFLOW

from pitivi.utils.loggable import Loggable
from pitivi.utils.receiver import receiver, handler
from pitivi.utils.ui import TRACK_SPACING, unpack_cairo_pattern, \
        LAYER_HEIGHT_EXPANDED, LAYER_SPACING, Point
from pitivi.utils.timeline import Controller, Zoomable
from pitivi.utils.ui import SPACING

# cursors to be used for resizing objects
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
# TODO: replace this with custom cursor
PLAYHEAD_CURSOR = gtk.gdk.Cursor(gtk.gdk.SB_H_DOUBLE_ARROW)

GlobalSettings.addConfigOption('edgeSnapDeadband',
    section="user-interface",
    key="edge-snap-deadband",
    default=5,
    notify=True)

PreferencesDialog.addNumericPreference('edgeSnapDeadband',
    section=_("Behavior"),
    label=_("Snap distance"),
    description=_("Threshold (in pixels) at which two clips will snap together "
        "when dragging or trimming."),
    lower=0)


class PlayheadController(Controller, Zoomable):

    _cursor = PLAYHEAD_CURSOR

    def __init__(self, *args, **kwargs):
        Controller.__init__(self, *args, **kwargs)

    def set_pos(self, item, pos):
        x, y = pos
        x += self._hadj.get_value()
        self._canvas.app.current.seeker.seek(Zoomable.pixelToNs(x))


class TimelineCanvas(goocanvas.Canvas, Zoomable, Loggable):

    __gtype_name__ = 'TimelineCanvas'
    __gsignals__ = {
        "expose-event": "override",
    }

    _tracks = None

    def __init__(self, instance, timeline=None):
        goocanvas.Canvas.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.app = instance
        self._selected_sources = []
        self._tracks = []
        self.height = 0
        self._position = 0

        self._block_size_request = False
        self.props.integer_layout = True
        self.props.automatic_bounds = False
        self.props.clear_background = False
        self.get_root_item().set_simple_transform(0, 2.0, 1.0, 0)

        self._createUI()
        self._timeline = timeline
        self.settings = instance.settings

    def _createUI(self):
        self._cursor = ARROW
        root = self.get_root_item()
        self.tracks = goocanvas.Group()
        self.tracks.set_simple_transform(0, KW_LABEL_Y_OVERFLOW, 1.0, 0)
        root.add_child(self.tracks)
        self._marquee = goocanvas.Rect(
            parent=root,
            stroke_pattern=unpack_cairo_pattern(0x33CCFF66),
            fill_pattern=unpack_cairo_pattern(0x33CCFF66),
            visibility=goocanvas.ITEM_INVISIBLE)
        self._playhead = goocanvas.Rect(
            y=-10,
            parent=root,
            line_width=1,
            fill_color_rgba=0x000000FF,
            stroke_color_rgba=0xFFFFFFFF,
            width=3)
        self._playhead_controller = PlayheadController(self._playhead)
        self.connect("size-allocate", self._size_allocate_cb)
        root.connect("motion-notify-event", self._selectionDrag)
        root.connect("button-press-event", self._selectionStart)
        root.connect("button-release-event", self._selectionEnd)
        self.height = (LAYER_HEIGHT_EXPANDED + TRACK_SPACING +
                LAYER_SPACING) * 2
        # add some padding for the horizontal scrollbar
        self.height += 21
        self.set_size_request(-1, self.height)

    def from_event(self, event):
        x, y = event.x, event.y
        x += self.app.gui.timeline.hadj.get_value()
        return Point(*self.convert_from_pixels(x, y))

    def setExpanded(self, track_object, expanded):
        track_ui = None
        for track in self._tracks:
            if track.track == track_object:
                track_ui = track
                break

        track_ui.setExpanded(expanded)

## sets the cursor as appropriate

    def _mouseEnterCb(self, unused_item, unused_target, event):
        event.window.set_cursor(self._cursor)
        return True

    def do_expose_event(self, event):
        allocation = self.get_allocation()
        width = allocation.width
        height = allocation.height
        # draw the canvas background
        # we must have props.clear_background set to False

        self.style.apply_default_background(event.window,
            True,
            gtk.STATE_ACTIVE,
            event.area,
            event.area.x, event.area.y,
            event.area.width, event.area.height)

        goocanvas.Canvas.do_expose_event(self, event)

## implements selection marquee

    _selecting = False
    _mousedown = None
    _marquee = None
    _got_motion_notify = False

    def getItemsInArea(self, x1, y1, x2, y2):
        '''
        Permits to get the Non UI L{Track}/L{TrackObject} in a list of set
        corresponding to the L{Track}/L{TrackObject} which are in the are

        @param x1: The horizontal coordinate of the up left corner of the area
        @type x1: An C{int}
        @param y1: The vertical coordinate of the up left corner of the area
        @type y1: An C{int}
        @param x2: The horizontal coordinate of the down right corner of the
                   area
        @type x2: An C{int}
        @param x2: The vertical coordinate of the down right corner of the area
        @type x2: An C{int}

        @returns: A list of L{Track}, L{TrackObject} tuples
        '''
        items = self.get_items_in_area(goocanvas.Bounds(x1, y1, x2, y2), True,
            True, True)
        if not items:
            return [], []

        tracks = set()
        track_objects = set()

        for item in items:
            if isinstance(item, Track):
                tracks.add(item.track)
            elif isinstance(item, TrackObject):
                track_objects.add(item.element)

        return tracks, track_objects

    def _normalize(self, p1, p2, adjust=0):
        w, h = p2 - p1
        x, y = p1
        if w - adjust < 0:
            w = abs(w - adjust)
            x -= w
        else:
            w -= adjust
        if h < 0:
            h = abs(h)
            y -= h
        return (x, y), (w, h)

    def _selectionDrag(self, item, target, event):
        if self._selecting:
            self._got_motion_notify = True
            cur = self.from_event(event)
            pos, size = self._normalize(self._mousedown, cur,
                self.app.gui.timeline.hadj.get_value())
            self._marquee.props.x, self._marquee.props.y = pos
            self._marquee.props.width, self._marquee.props.height = size
            return True
        return False

    def _selectionStart(self, item, target, event):
        self._selecting = True
        self._marquee.props.visibility = goocanvas.ITEM_VISIBLE
        self._mousedown = self.from_event(event)
        self._marquee.props.width = 0
        self._marquee.props.height = 0
        self.pointer_grab(self.get_root_item(), gtk.gdk.POINTER_MOTION_MASK |
            gtk.gdk.BUTTON_RELEASE_MASK, self._cursor, event.time)
        return True

    def _selectionEnd(self, item, target, event):
        seeker = self.app.current.seeker
        self.pointer_ungrab(self.get_root_item(), event.time)
        self._selecting = False
        self._marquee.props.visibility = goocanvas.ITEM_INVISIBLE
        if not self._got_motion_notify:
            self._timeline.selection.setSelection([], 0)
            seeker.seek(Zoomable.pixelToNs(event.x))
        else:
            self._got_motion_notify = False
            mode = 0
            if event.get_state() & gtk.gdk.SHIFT_MASK:
                mode = 1
            if event.get_state() & gtk.gdk.CONTROL_MASK:
                mode = 2
            selected = self._objectsUnderMarquee()
            self.app.projectManager.current.emit("selected-changed", selected)
            self._timeline.selection.setSelection(self._objectsUnderMarquee(), mode)
        return True

    def _objectsUnderMarquee(self):
        items = self.get_items_in_area(self._marquee.get_bounds(), True, True,
            True)
        if items:
            return set((item.element for item in items if isinstance(item,
                TrackObject) and item.bg in items))
        return set()

## playhead implementation

    position = 0

    def timelinePositionChanged(self, position):
        self.position = position
        self._playhead.props.x = self.nsToPixel(position)

    max_duration = 0

    def setMaxDuration(self, duration):
        self.max_duration = duration
        self._request_size()

    def _request_size(self):
        alloc = self.get_allocation()
        self.set_bounds(0, 0, alloc.width, alloc.height)
        self._playhead.props.height = (self.height + SPACING)

    def _size_allocate_cb(self, widget, allocation):
        self._request_size()

    def zoomChanged(self):
        self.queue_draw()
        if self._timeline:
            self._timeline.dead_band = self.pixelToNs(
                self.settings.edgeSnapDeadband)
            #self._timelinePositionChanged(self.position)

## settings callbacks

    def _setSettings(self):
        self.zoomChanged()

    settings = receiver(_setSettings)

    @handler(settings, "edgeSnapDeadbandChanged")
    def _edgeSnapDeadbandChangedCb(self, settings):
        self.zoomChanged()

## Timeline callbacks

    def setTimeline(self, timeline):
        while self._tracks:
            self._trackRemoved(None, 0)

        self._timeline = timeline
        if self._timeline:
            for track in self._timeline.get_tracks():
                self._trackAdded(None, track)
            self._timeline.connect("track-added", self._trackAdded)
            self._timeline.connect("track-removed", self._trackRemoved)
        self.zoomChanged()

    def getTimeline(self):
        return self._timeline

    timeline = property(getTimeline, setTimeline, None, "The timeline property")

    def _trackAdded(self, timeline, track):
        track = Track(self.app, track, self._timeline)
        self._tracks.append(track)
        track.set_canvas(self)
        self.tracks.add_child(track)
        self.regroupTracks()

    def _trackRemoved(self, unused_timeline, position):
        track = self._tracks[position]
        del self._tracks[position]
        track.remove()
        self.regroupTracks()

    def regroupTracks(self):
        height = 0
        for i, track in enumerate(self._tracks):
            track.set_simple_transform(0, height, 1, 0)
            height += track.height + TRACK_SPACING
        self.height = height
        self._request_size()
