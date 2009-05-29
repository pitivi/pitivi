# PiTiVi , Non-linear video editor
#
#       pitivi/ui/curve.py
#
# Copyright (c) 2006, Edward Hervey <bilboed@bilboed.com>
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
Custom canvas item for track object keyframe curves."""

import goocanvas
import gobject

from pitivi.receiver import receiver, handler
from pitivi.ui.zoominterface import Zoomable
import pitivi.ui.previewer as previewer
from pitivi.ui.view import View
from pitivi.ui.controller import Controller
from pitivi.ui.common import LAYER_HEIGHT_EXPANDED

def between(a, b, c):
    return (a <= b) and (b <= c)

def intersect(b1, b2):
    return goocanvas.Bounds(max(b1.x1, b2.x1), max(b1.y1, b2.y1),
        min(b1.x2, b2.x2), min(b1.y2, b2.y2))

class Curve(goocanvas.ItemSimple, goocanvas.Item, View, Zoomable):

    __gtype_name__ = 'Curve'

    class Controller(Controller):

        def _drag_start(self, item, target, event):
            self._kf = self._view.findKeyframe(self.from_item_event(item,
                event))
            Controller._drag_start(self, item, target, event)

        def _drag_end(self, item, target, event):
            self._kf = None
            Controller._drag_end(self, item, target, event)

        def set_pos(self, obj, pos):
            time, value = self.xyToTimeValue(*pos)
            if self._kf:
                self._kf.time = time
                self._kf.value = value

        def xyToTimeValue(self, x, y):
            time = Zoomable.pixelToNs(x)
            value = (max(0, min(y, LAYER_HEIGHT_EXPANDED)) /
                LAYER_HEIGHT_EXPANDED)
            return time, value

        def enter(self, item ,target):
            self._view.focus()

        def leave(self, item, target):
            self._view.normal()

    def __init__(self, element, interpolator, height=LAYER_HEIGHT_EXPANDED,
        **kwargs):
        super(Curve, self).__init__(**kwargs)
        View.__init__(self)
        Zoomable.__init__(self)
        self.keyframes = {}
        self.height = float(height)
        self.element = element
        self.props.pointer_events = goocanvas.EVENTS_STROKE
        self.interpolator = interpolator
        self.normal()

## properties

    def _get_height(self):
        return self._height
    def _set_height (self, value):
        self._height = value
        self.changed(True)
    height = gobject.property(_get_height, _set_height, type=float)

## element callbacks

    def _set_element(self):
        self.previewer = previewer.get_preview_for_object(self.element)
    element = receiver(setter=_set_element)

    @handler(element, "in-point-changed")
    @handler(element, "media-duration-changed")
    def _media_props_changed(self, obj, unused_start_duration):
        self.changed(True)

## interpolator callbacks

    interpolator = receiver()

    @handler(interpolator, "keyframe-added")
    @handler(interpolator, "keyframe-removed")
    @handler(interpolator, "keyframe-moved")
    def curveChanged(self, keyframe, unused):
        self.changed(False)

## Zoomable interface overries

    def zoomChanged(self):
        self.changed(True)

## goocanvas item methods

    def do_simple_update(self, cr):
        cr.identity_matrix()
        if self.element.factory:
            self.bounds = goocanvas.Bounds(0, 0,
            Zoomable.nsToPixel(self.element.duration), self.height)

    def _getKeyframeXY(self, kf):
        x = self.nsToPixel(kf.time + self.element.start)
        y = kf.value * self._height
        return x, y

    def _controlPoint(self, cr, kf):
        x, y = self._getKeyframeXY(kf)
        cr.rectangle(x - 5, y - 5, 10, 10)
        self.keyframes[kf] = x, y

    def do_simple_paint(self, cr, bounds):
        bounds = intersect(self.bounds, bounds)
        cr.identity_matrix()
        cr.set_line_width(self.line_width)
        if self.interpolator:
            cr.set_source_rgb(1, 0, 0)
            self.make_path(cr, bounds)
            cr.stroke()
            cr.set_source_rgb(1, 1, 1)
            cr.fill()

    def make_path(self, cr,  bounds):
        if not self.interpolator:
            return
        height = bounds.y2 - bounds.y1
        width = bounds.x2 - bounds.x1
        cr.rectangle(bounds.x1, bounds.y1, width, height)
        cr.clip()
        cr.move_to(*self._getKeyframeXY(self.interpolator.start))
        for kf in self.interpolator.keyframes:
            cr.line_to(*self._getKeyframeXY(kf))
        cr.line_to(*self._getKeyframeXY(self.interpolator.end))
        self._controlPoint(cr, self.interpolator.start)
        for kf in self.interpolator.keyframes:
            self._controlPoint(cr, kf)
        self._controlPoint(cr, self.interpolator.end)

    def do_simple_is_item_at(self, x, y, cr, pointer_event):
        if (between(0, x, self.nsToPixel(self.element.duration)) and
            between(0, y, self.height)):
            cr.set_line_width(self.line_width)
            self.make_path(cr, self.get_bounds())
            return cr.in_stroke(x, y)
        return False

## public

    def focus(self):
        self.line_width = 3.0
        self.changed(False)

    def normal(self):
        self.line_width = 2.0
        self.changed(False)

    def findKeyframe(self, pos):
        x, y = pos
        for keyframe, value in self.keyframes.iteritems():
            kx, ky = value
            if (between(kx - 5, x, kx + 5) and
                between(ky - 5, y, ky + 5)):
                return keyframe
        return None
