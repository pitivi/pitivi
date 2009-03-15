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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gtk
import goocanvas

from pitivi.receiver import receiver, handler
from pitivi.ui.track import Track
from pitivi.ui.trackobject import TrackObject
from pitivi.ui.point import Point
from pitivi.ui.zoominterface import Zoomable
from common import TRACK_SPACING
import gtk

# cursors to be used for resizing objects
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
# TODO: replace this with custom cursor
RAZOR_CURSOR = gtk.gdk.Cursor(gtk.gdk.XTERM)

# In pixels
DEADBAND = 5

class TimelineCanvas(goocanvas.Canvas, Zoomable):

    _tracks = None

    def __init__(self, timeline):
        goocanvas.Canvas.__init__(self)
        Zoomable.__init__(self)
        self._selected_sources = []
        self._tracks = []

        self._block_size_request = False
        self.props.integer_layout = True
        self.props.automatic_bounds = False

        self._createUI()
        self.timeline = timeline

    def _createUI(self):
        self._cursor = ARROW
        root = self.get_root_item()
        self.tracks = goocanvas.Group()
        root.add_child(self.tracks)
        self._marquee = goocanvas.Rect(
            stroke_color_rgba=0x33CCFF66,
            fill_color_rgba=0x33CCFF66,
            visibility = goocanvas.ITEM_INVISIBLE)
        self._razor = goocanvas.Rect(
            line_width=0,
            fill_color="orange",
            width=1,
            visibility=goocanvas.ITEM_INVISIBLE)
        root.add_child(self._marquee)
        root.add_child(self._razor)
        root.connect("motion-notify-event", self._selectionDrag)
        root.connect("button-press-event", self._selectionStart)
        root.connect("button-release-event", self._selectionEnd)

    def from_event(self, event):
        return Point(*self.convert_from_pixels(event.x, event.y))

## sets the cursor as appropriate

    def _mouseEnterCb(self, unused_item, unused_target, event):
        event.window.set_cursor(self._cursor)
        return True

## implements selection marquee

    _selecting = False
    _mousedown = None
    _marquee = None

    def _normalize(self, p1, p2):
        w, h = p2 - p1
        x, y = p1
        if w < 0:
            w = abs(w)
            x -= w
        if h < 0:
            h = abs(h)
            y -= h
        return (x, y), (w, h)


    def _selectionDrag(self, item, target, event):
        if self._selecting:
            cur = self.from_event(event)
            pos, size = self._normalize(self._mousedown, cur)
            m = self._marquee
            m.props.x, m.props.y = pos
            m.props.width, m.props.height = size
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
        self.pointer_ungrab(self.get_root_item(), event.time)
        self._selecting = False
        self._marquee.props.visibility = goocanvas.ITEM_INVISIBLE
        mode = 0
        if event.get_state() & gtk.gdk.SHIFT_MASK:
            mode = 1
        if event.get_state() & gtk.gdk.CONTROL_MASK:
            mode = 2
        self.timeline.setSelectionTo(self._objectsUnderMarquee(), mode)
        return True

    def _objectsUnderMarquee(self):
        items = self.get_items_in_area(self._marquee.get_bounds(), True, True,
            True)
        if items:
            return set((item.element for item in items if isinstance(item,
                TrackObject)))
        return set()

## Razor Tool Implementation

    def activateRazor(self, action):
        self._razor_sigid = self.connect("button_press_event",
            self._razorClickedCb)
        self._razor_release_sigid = self.connect("button_release_event",
            self._razorReleasedCb)
        self._razor_motion_sigid = self.connect("motion_notify_event",
            self._razorMovedCb)
        self._razor.props.visibility = goocanvas.ITEM_VISIBLE
        self._action = action
        return True

    def deactivateRazor(self):
        self.disconnect(self._razor_sigid)
        self.disconnect(self._razor_motion_sigid)
        self.disconnect(self._razor_release_sigid)
        self._razor.props.visibility = goocanvas.ITEM_INVISIBLE

    def _razorMovedCb(self, canvas, event):
        x, y = self.convert_from_pixels(event.x, event.y)
        self._razor.props.x = self.nsToPixel(self.pixelToNs(x))
        return True

    def _razorReleasedCb(self, unused_canvas, event):
        self._action.props.active = False

        x, y = self.convert_from_pixels(event.x, event.y)
        bounds = goocanvas.Bounds(x, y, x, y)
        items = self.get_items_in_area(bounds, True, True, True)
        if items:
            for item in items:
                if isinstance(item, TrackObject):
                    item.element.split(self.pixelToNs(x))

        return True

    def _razorClickedCb(self, unused_canvas, unused_event):
        return True

    max_duration = 0

    def setMaxDuration(self, duration):
        self.max_duration = duration
        self._request_size()

    def _request_size(self):
        w = Zoomable.nsToPixel(self.max_duration)
        h = 60 * len(self._tracks)
        self.set_bounds(0, 0, w, h)
        self._razor.props.height = h
        self.get_root_item().changed(True)

## Zoomable Override

    def zoomChanged(self):
        if self.timeline:
            self.timeline.dead_band = self.pixelToNs(DEADBAND)
            self._request_size()

## Timeline callbacks

    def _set_timeline(self):
        while self._tracks:
            self._trackRemoved(None, 0)
        if self.timeline:
            for track in self.timeline.tracks:
                self._trackAdded(None, track)

    timeline = receiver(_set_timeline)

    @handler(timeline, "track-added")
    def _trackAdded(self, timeline, track):
        track = Track(track, self.timeline)
        self._tracks.append(track)
        track.set_canvas(self)
        self.tracks.add_child(track)
        self.regroupTracks()

    @handler(timeline, "track-removed")
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
        self._request_size()
