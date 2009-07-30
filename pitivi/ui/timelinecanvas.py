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
from gettext import gettext as _

from pitivi.log.loggable import Loggable
from pitivi.receiver import receiver, handler
from pitivi.ui.track import Track
from pitivi.ui.trackobject import TrackObject
from pitivi.ui.point import Point
from pitivi.ui.zoominterface import Zoomable
from pitivi.settings import GlobalSettings
from pitivi.ui.prefs import PreferencesDialog
from pitivi.ui.common import TRACK_SPACING, unpack_cairo_pattern, \
        LAYER_HEIGHT_EXPANDED, LAYER_SPACING

# cursors to be used for resizing objects
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
# TODO: replace this with custom cursor
RAZOR_CURSOR = gtk.gdk.Cursor(gtk.gdk.XTERM)

GlobalSettings.addConfigOption('edgeSnapDeadband',
    section = "user-interface",
    key = "edge-snap-deadband",
    default = 5,
    notify = True)

PreferencesDialog.addNumericPreference('edgeSnapDeadband',
    section = _("Behavior"),
    label = _("Snap Distance (pixels)"),
    description = _("Threshold distance (in pixels) used for all snapping "
        "operations"),
    lower = 0)

class TimelineCanvas(goocanvas.Canvas, Zoomable, Loggable):

    __gsignals__ = {
        "scroll-event":"override"
        }

    _tracks = None

    def __init__(self, instance, timeline=None):
        goocanvas.Canvas.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.app = instance
        self._selected_sources = []
        self._tracks = []
        self._height = 0
        self._position = 0

        self._block_size_request = False
        self.props.integer_layout = True
        self.props.automatic_bounds = False

        self._createUI()
        self.timeline = timeline
        self.settings = instance.settings

    def _createUI(self):
        self._cursor = ARROW
        root = self.get_root_item()
        self.tracks = goocanvas.Group()
        root.add_child(self.tracks)
        self._marquee = goocanvas.Rect(
            stroke_pattern = unpack_cairo_pattern(0x33CCFF66),
            fill_pattern = unpack_cairo_pattern(0x33CCFF66),
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
        height = (LAYER_HEIGHT_EXPANDED + TRACK_SPACING + LAYER_SPACING) * 2
        # add some padding for the horizontal scrollbar
        height += 21
        self.set_size_request(-1, height)

    def from_event(self, event):
        return Point(*self.convert_from_pixels(event.x, event.y))

    def setExpanded(self, track_object, expanded):
        track_ui = None
        for track in self._tracks:
            if track.track == track_object:
                track_ui = track
                break

        track_ui.setExpanded(expanded)

    def do_scroll_event(self, event):
        if event.state & gtk.gdk.SHIFT_MASK:
            # shift + scroll => vertical (up/down) scroll
            if event.direction == gtk.gdk.SCROLL_LEFT:
                event.direction = gtk.gdk.SCROLL_UP
            elif event.direction == gtk.gdk.SCROLL_RIGHT:
                event.direction = gtk.gdk.SCROLL_DOWN
            event.state &= ~gtk.gdk.SHIFT_MASK
        elif event.state & gtk.gdk.CONTROL_MASK:
            # zoom + scroll => zooming (up: zoom in)
            if event.direction == gtk.gdk.SCROLL_UP:
                Zoomable.zoomIn()
                return True
            elif event.direction == gtk.gdk.SCROLL_DOWN:
                Zoomable.zoomOut()
                return True
            return False
        else:
            if event.direction == gtk.gdk.SCROLL_UP:
                event.direction = gtk.gdk.SCROLL_LEFT
            elif event.direction == gtk.gdk.SCROLL_DOWN:
                event.direction = gtk.gdk.SCROLL_RIGHT
        return goocanvas.Canvas.do_scroll_event(self, event)

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
        def snap(x):
            pos = self.nsToPixel(self._position)
            if abs(x - pos) <= self.settings.edgeSnapDeadband:
                return pos
            return x
        x, y = self.convert_from_pixels(event.x, event.y)
        self._razor.props.x = snap(self.nsToPixel(self.pixelToNs(x)))
        return True

    def _razorReleasedCb(self, unused_canvas, event):
        self._action.props.active = False

        x, y = self.convert_from_pixels(event.x, event.y)
        bounds = goocanvas.Bounds(x, y, x, y)
        items = self.get_items_in_area(bounds, True, True, True)
        if items:
            for item in items:
                if isinstance(item, TrackObject):
                    self.app.action_log.begin("split object")
                    item.element.split(self._snapToPlayhead(self.pixelToNs(x)))
                    self.app.action_log.commit()

        return True

    def _razorClickedCb(self, unused_canvas, unused_event):
        return True

    def _snapToPlayhead(self, time):
        thresh = self.pixelToNs(self.settings.edgeSnapDeadband)
        if abs(time - self._position) <= thresh:
            return self._position
        return time

    max_duration = 0

    def setMaxDuration(self, duration):
        self.max_duration = duration
        self._request_size()

    def _request_size(self):
        w = Zoomable.nsToPixel(self.max_duration)
        self.set_bounds(0, 0, w, self._height)
        self._razor.props.height = self._height
        self.get_root_item().changed(True)

## Zoomable Override

    def zoomChanged(self):
        if self.timeline:
            self.timeline.dead_band = self.pixelToNs(
                self.settings.edgeSnapDeadband)
            self._request_size()


## settings callbacks

    def _setSettings(self):
        self.zoomChanged()

    settings = receiver(_setSettings)

    @handler(settings, "edgeSnapDeadbandChanged")
    def _edgeSnapDeadbandChangedCb(self, settings):
        self.zoomChanged()

## Timeline callbacks

    def _set_timeline(self):
        while self._tracks:
            self._trackRemoved(None, 0)
        if self.timeline:
            for track in self.timeline.tracks:
                self._trackAdded(None, track)
        self.zoomChanged()

    timeline = receiver(_set_timeline)

    @handler(timeline, "track-added")
    def _trackAdded(self, timeline, track):
        track = Track(self.app, track, self.timeline)
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
        self._height = height
        self._request_size()
