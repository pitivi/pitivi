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

# cursors to be used for resizing objects
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
# TODO: replace this with custom cursor
RAZOR_CURSOR = gtk.gdk.Cursor(gtk.gdk.XTERM)

# In pixels
DEADBAND = 5

class TimelineCanvas(goocanvas.Canvas, Zoomable):

    __tracks = None

    def __init__(self, timeline):
        goocanvas.Canvas.__init__(self)
        Zoomable.__init__(self)
        self._selected_sources = []
        self.__tracks = []

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
        self.__marquee = goocanvas.Rect(
            stroke_color_rgba=0x33CCFF66,
            fill_color_rgba=0x33CCFF66,
            visibility = goocanvas.ITEM_INVISIBLE)
        self.__razor = goocanvas.Rect(
            line_width=0,
            fill_color="orange",
            width=1,
            visibility=goocanvas.ITEM_INVISIBLE)
        root.add_child(self.__marquee)
        root.add_child(self.__razor)
        root.connect("motion-notify-event", self.__selectionDrag)
        root.connect("button-press-event", self.__selectionStart)
        root.connect("button-release-event", self.__selectionEnd)

    def from_event(self, event):
        return Point(*self.convert_from_pixels(event.x, event.y))

## sets the cursor as appropriate

    def _mouseEnterCb(self, unused_item, unused_target, event):
        event.window.set_cursor(self._cursor)
        return True

## implements selection marquee

    __selecting = False
    __mousedown = None
    __marquee = None

    def __normalize(self, p1, p2):
        w, h = p2 - p1
        x, y = p1
        if w < 0:
            w = abs(w)
            x -= w
        if h < 0:
            h = abs(h)
            y -= h
        return (x, y), (w, h)


    def __selectionDrag(self, item, target, event):
        if self.__selecting:
            cur = self.from_event(event)
            pos, size = self.__normalize(self.__mousedown, cur)
            m = self.__marquee
            m.props.x, m.props.y = pos
            m.props.width, m.props.height = size
            return True
        return False

    def __selectionStart(self, item, target, event):
        self.__selecting = True
        self.__marquee.props.visibility = goocanvas.ITEM_VISIBLE
        self.__mousedown = self.from_event(event)
        self.__marquee.props.width = 0
        self.__marquee.props.height = 0
        self.pointer_grab(self.get_root_item(), gtk.gdk.POINTER_MOTION_MASK |
            gtk.gdk.BUTTON_RELEASE_MASK, self._cursor, event.time)
        return True

    def __selectionEnd(self, item, target, event):
        self.pointer_ungrab(self.get_root_item(), event.time)
        self.__selecting = False
        self.__marquee.props.visibility = goocanvas.ITEM_INVISIBLE
        mode = 0
        if event.get_state() & gtk.gdk.SHIFT_MASK:
            mode = 1
        if event.get_state() & gtk.gdk.CONTROL_MASK:
            mode = 2
        self.timeline.setSelectionTo(self.__objectsUnderMarquee(), mode)
        return True

    def __objectsUnderMarquee(self):
        items = self.get_items_in_area(self.__marquee.get_bounds(), True, True,
            True)
        if items:
            return set((item.element for item in items if isinstance(item,
                TrackObject)))
        return set()

## Razor Tool Implementation

    def activateRazor(self, action):
        self.__razor_sigid = self.connect("button_press_event",
            self.__razorClickedCb)
        self.__razor_release_sigid = self.connect("button_release_event",
            self.__razorReleasedCb)
        self.__razor_motion_sigid = self.connect("motion_notify_event",
            self.__razorMovedCb)
        self.__razor.props.visibility = goocanvas.ITEM_VISIBLE
        self.__action = action
        return True

    def deactivateRazor(self):
        self.disconnect(self.__razor_sigid)
        self.disconnect(self.__razor_motion_sigid)
        self.disconnect(self.__razor_release_sigid)
        self.__razor.props.visibility = goocanvas.ITEM_INVISIBLE

    def __razorMovedCb(self, canvas, event):
        x, y = self.convert_from_pixels(event.x, event.y)
        self.__razor.props.x = self.nsToPixel(self.pixelToNs(x))
        return True

    def __razorReleasedCb(self, unused_canvas, event):
        self.__action.props.active = False

        x, y = self.convert_from_pixels(event.x, event.y)
        bounds = goocanvas.Bounds(x, y, x, y)
        items = self.get_items_in_area(bounds, True, True, True)
        if items:
            for item in items:
                if isinstance(item, TrackObject):
                    item.element.split(self.pixelToNs(x))

        return True

    def __razorClickedCb(self, unused_canvas, unused_event):
        return True

## Zoomable Override

    def zoomChanged(self):
        if self.timeline:
            self.timeline.dead_band = self.pixelToNs(DEADBAND)
            self._request_size()

## Timeline callbacks

    def __set_timeline(self):
        while self.__tracks:
            self._trackRemoved(None, 0)
        if self.timeline:
            for track in self.timeline.tracks:
                self._trackAdded(None, track)

    timeline = receiver(__set_timeline)

    @handler(timeline, "duration-changed")
    def _start_duration_cb(self, unused_item, unused_dur):
        self._request_size()

    def _request_size(self):
        tl, br = Point.from_widget_bounds(self)
        pw, ph = br - tl
        w = Zoomable.nsToPixel(self.timeline.duration)
        h = 60 * len(self.__tracks)
        if (w > pw) or (h > ph):
            self.set_bounds(0, 0, w, h)
        self.__razor.props.height = h
        self.get_root_item().changed(True)

    @handler(timeline, "track-added")
    def _trackAdded(self, timeline, track):
        track = Track(track, self.timeline)
        self.__tracks.append(track)
        track.set_canvas(self)
        self.tracks.add_child(track)
        self._regroup_tracks()

    @handler(timeline, "track-removed")
    def _trackRemoved(self, unused_timeline, position):
        track = self.__tracks[position]
        del self.__tracks[position]
        track.remove()
        self._regroup_tracks()

    def _regroup_tracks(self):
        for i, track in enumerate(self.__tracks):
            # FIXME: hard-coding track height, because this won't be updated
            # later
            height = 50
            track.set_simple_transform(0, i * (height + 10), 1, 0)
        self._request_size()
