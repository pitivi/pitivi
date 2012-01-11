# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/curve.py
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Custom canvas item for track object keyframe curves."""

import goocanvas
import gobject
import gtk

from pitivi.utils.receiver import receiver, handler
from pitivi.utils.timeline import View, Controller, Zoomable
from pitivi.utils.ui import LAYER_HEIGHT_EXPANDED, roundedrec, Point
from pitivi.utils.misc import between


def intersect(b1, b2):
    return goocanvas.Bounds(max(b1.x1, b2.x1), max(b1.y1, b2.y1),
        min(b1.x2, b2.x2), min(b1.y2, b2.y2))

KW_WIDTH = 10
KW_HEIGHT = 10
KW_WIDTH2 = KW_WIDTH / 2
KW_HEIGHT2 = KW_HEIGHT / 2
KW_MOUSE_WIDTH = KW_WIDTH2 + 1
KW_MOUSE_HEIGHT = KW_HEIGHT2 + 1
KW_LABEL_X_OFFSET = KW_WIDTH2 + 5
KW_LABEL_Y_OFFSET = -10
KW_LABEL_X_OVERFLOW = 50
KW_LABEL_Y_OVERFLOW = 12
KW_LABEL_HPAD = 6
KW_LABEL_VPAD = 4
KW_LABEL_HPAD2 = KW_LABEL_VPAD / 2
KW_LABEL_VPAD2 = KW_LABEL_VPAD / 2
CURVE_STROKE_WIDTH = 2.0
HAND = gtk.gdk.Cursor(gtk.gdk.HAND2)


class Curve(goocanvas.ItemSimple, goocanvas.Item, View, Zoomable):

    __gtype_name__ = 'Curve'

    class Controller(Controller):

        _cursor = HAND
        _kf = None
        _handle_enter_leave = False

        def drag_start(self, item, target, event):
            self._view.app.action_log.begin("volume change")
            initial = self.from_item_event(item, event)
            if self._kf:
                self._mousedown = self._view.keyframes[self._kf] - initial
            if not self._kf:
                # we are moving the entire curve, so we need to know the
                # inital position of each keyframe
                self._offsets = dict(self._view.keyframes)
                self._segment = self._view.findSegment(
                    self.xyToTimeValue(initial)[0])

        def drag_end(self, item, target, event):
            self._view.app.action_log.commit()

        def set_pos(self, obj, pos):
            interpolator = self._view.interpolator
            if self._kf:
                time, value = self.xyToTimeValue(pos)
                self._kf.time = time
                self._kf.value = value
            else:
                for kf in self._segment:
                    time, value = self.xyToTimeValue(self._offsets[kf] + pos
                        - self.pos(self._view))
                    kf.value = value

        def hover(self, item, target, event):
            coords = self.from_item_event(item, event)
            self._kf = self._view.findKeyframe(coords)
            self._view.setFocusedKf(self._kf)

        def double_click(self, pos):
            interpolator = self._view.interpolator
            kf = self._view.findKeyframe(pos)
            if kf is None:
                time, value = self.xyToTimeValue(pos)
                self._view.app.action_log.begin("add volume point")
                kf = interpolator.newKeyframe(time)
                self._view.setFocusedKf(kf)
                self._view.app.action_log.commit()
            else:
                self._view.app.action_log.begin("remove volume point")
                self._view.interpolator.removeKeyframe(kf)
                self._view.app.action_log.commit()

        def xyToTimeValue(self, pos):
            view = self._view
            interpolator = view.interpolator
            bounds = view.bounds
            time = (Zoomable.pixelToNs(pos[0] - bounds.x1) +
                view.element.in_point)
            value = ((1 - (pos[1] - KW_LABEL_Y_OVERFLOW - bounds.y1 -
                view._min) / view._range) *
                    interpolator.range) + interpolator.lower
            return time, value

        def enter(self, item, target):
            coords = self.from_item_event(item, self._last_event)
            self._kf = self._view.findKeyframe(coords)
            self._view.setFocusedKf(self._kf)
            self._view.focus()

        def leave(self, item, target):
            self._view.normal()

    def __init__(self, instance, element, interpolator, height=LAYER_HEIGHT_EXPANDED,
        **kwargs):
        super(Curve, self).__init__(**kwargs)
        View.__init__(self)
        Zoomable.__init__(self)
        self.app = instance
        self.keyframes = {}
        self.height = float(height)
        self.element = element
        self.props.pointer_events = goocanvas.EVENTS_STROKE
        self.interpolator = interpolator
        self._focused_kf = None
        self.normal()
        self.set_simple_transform(0, -KW_LABEL_Y_OVERFLOW, 1.0, 0)

## properties

    def _get_height(self):
        return self._height

    def _set_height(self, value):
        self._height = value
        self._min = CURVE_STROKE_WIDTH / 2
        self._max = value - (CURVE_STROKE_WIDTH / 2)
        self._range = self._max - self._min
        self.changed(True)
    height = gobject.property(_get_height, _set_height, type=float)

## element callbacks

    element = receiver()

    @handler(element, "in-point-changed")
    @handler(element, "media-duration-changed")
    def _media_props_changed(self, obj, unused_start_duration):
        self.changed(True)

## interpolator callbacks

    interpolator = receiver()

    @handler(interpolator, "keyframe-removed")
    def keyframeRemoved(self, unused_interpolator, keyframe, old_value=None):
        if keyframe in self.keyframes:
            del self.keyframes[keyframe]
            if keyframe is self._focused_kf:
                self._focused_kf = None
        self.changed(False)

    @handler(interpolator, "keyframe-added")
    def curveChanged(self, unused_interpolator, unused_keyframe):
        self.changed(False)

    @handler(interpolator, "keyframe-moved")
    def curveChanged(self, unused_interpolator, unused_keyframe, old_value=None):
        self.changed(False)

## Zoomable interface overries

    def zoomChanged(self):
        self.changed(True)

## goocanvas item methods

    def do_simple_update(self, cr):
        cr.identity_matrix()
        if self.element.factory:
            self.visible_width = self.nsToPixel(self.element.duration)
            self.bounds = goocanvas.Bounds(0, 0,
                self.visible_width + KW_LABEL_X_OVERFLOW,
                self.height + KW_LABEL_Y_OVERFLOW)

    def _getKeyframeXY(self, kf):
        interp = self.interpolator
        x = self.nsToPixel(kf.time - self.element.in_point)
        y = KW_LABEL_Y_OVERFLOW + self._range - (((kf.value -
            interp.lower) / interp.range) * self._range)
        return Point(x + self.bounds.x1, y + self.bounds.y1 + self._min)

    def _controlPoint(self, cr, kf):
        pos = self._getKeyframeXY(kf)
        x, y = pos
        cr.rectangle(x - KW_WIDTH2, y - KW_HEIGHT2, KW_WIDTH, KW_HEIGHT)
        self.keyframes[kf] = pos

    def do_simple_paint(self, cr, bounds):
        cr.identity_matrix()
        if self.interpolator:
            cr.save()
            # set clipping region to the visible portion of the clip
            vis_bounds = intersect(
                goocanvas.Bounds(
                    self.bounds.x1, self.bounds.y1 + KW_LABEL_Y_OVERFLOW,
                    self.bounds.x2 - KW_LABEL_X_OVERFLOW, self.bounds.y2), bounds)
            vis_width = vis_bounds.x2 - vis_bounds.x1
            vis_height = vis_bounds.y2 - vis_bounds.y1
            cr.rectangle(vis_bounds.x1, vis_bounds.y1, vis_width, vis_height)
            cr.clip()

            self.make_curve(cr)
            cr.set_line_width(self.line_width)
            cr.set_source_rgb(1, 0, 0)
            cr.stroke()
            self.make_keyframes(cr)
            cr.set_line_width(1.0)
            cr.set_source_rgb(1, 1, 1)
            cr.fill_preserve()
            cr.set_source_rgb(1, 0, 0)
            cr.stroke()

            # re-draw the focused keyframe, if it exists, inverted
            if self._focused_kf:

                self._controlPoint(cr, self._focused_kf)
                cr.set_source_rgb(1, 0, 0)
                cr.fill_preserve()
                cr.set_source_rgb(1, 1, 1)
                cr.stroke()

                x, y = self.keyframes[self._focused_kf]
                x += KW_LABEL_X_OFFSET
                y += KW_LABEL_Y_OFFSET
                text = self.interpolator.formatValue(self._focused_kf.value)
                w, h = cr.text_extents("0" * len(text))[2:4]

                # reset clip region to the full bounds of the item
                bounds = intersect(self.bounds, bounds)
                width = bounds.x2 - bounds.x1
                height = bounds.y2 - bounds.y1
                # cr.reset_clip()
                cr.restore()
                cr.rectangle(bounds.x1, bounds.y1, width, height)
                cr.clip()

                # draw the value label
                roundedrec(cr, x - KW_LABEL_HPAD2, y - KW_LABEL_VPAD2,
                    w + KW_LABEL_HPAD, h + KW_LABEL_VPAD, r=10)
                cr.set_source_rgb(1, 1, 1)
                cr.fill()
                cr.set_source_rgb(1, 0, 0)
                cr.move_to(x, y + h)
                cr.show_text(text)
            else:
                cr.restore()

    def make_curve(self, cr):
        if not self.interpolator:
            return
        iterator = self.interpolator.getVisibleKeyframes()
        cr.move_to(*self._getKeyframeXY(iterator.next()))
        for kf in iterator:
            cr.line_to(*self._getKeyframeXY(kf))
        cr.line_to(*self._getKeyframeXY(self.interpolator.end))

    def make_keyframes(self, cr):
        for kf in self.interpolator.getVisibleKeyframes():
            self._controlPoint(cr, kf)

    def do_simple_is_item_at(self, x, y, cr, pointer_event):
        if (between(0, x, self.visible_width) and
            between(KW_LABEL_Y_OVERFLOW, y, self.height +
            KW_LABEL_Y_OVERFLOW)):
            x += self.bounds.x1
            y += self.bounds.y1
            cr.new_path()
            self.make_curve(cr)
            self.make_keyframes(cr)
            cr.set_line_width(10.0)
            return cr.in_stroke(x, y) or bool(self.findKeyframe((x, y)))
        return False

## public

    def setFocusedKf(self, kf):
        if self._focused_kf is not kf:
            self.changed(False)
        self._focused_kf = kf

    def focus(self):
        self.line_width = CURVE_STROKE_WIDTH * 1.5
        self.changed(False)

    def normal(self):
        self.line_width = CURVE_STROKE_WIDTH
        self.setFocusedKf(None)
        self.changed(False)

    def findKeyframe(self, pos):
        x, y = pos
        for keyframe, value in self.keyframes.iteritems():
            kx, ky = value
            if (between(kx - KW_MOUSE_WIDTH, x, kx + KW_MOUSE_WIDTH) and
                between(ky - KW_MOUSE_HEIGHT, y, ky + KW_MOUSE_HEIGHT)):
                return keyframe
        return None

    def findSegment(self, time):
        before = self.interpolator.start
        after = self.interpolator.end
        for keyframe in self.keyframes.iterkeys():
            if between(before.time, keyframe.time, time):
                before = keyframe
            if between(time, keyframe.time, after.time):
                after = keyframe
        assert before.time <= after.time
        return before, after
