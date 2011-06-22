# PiTiVi , Non-linear video editor
#
#       pitivi/ui/preview.py
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
Custom canvas item for timeline object previews. This code is just a thin
canvas-item wrapper which ensures that the preview is updated appropriately.
The actual drawing is done by the pitivi.previewer.Previewer class.  """

import goocanvas
import gobject

from pitivi.receiver import receiver, handler
from pitivi.ui.zoominterface import Zoomable
import pitivi.ui.previewer as previewer


def between(a, b, c):
    return (a <= b) and (b <= c)


def intersect(b1, b2):
    return goocanvas.Bounds(max(b1.x1, b2.x1), max(b1.y1, b2.y1),
        min(b1.x2, b2.x2), min(b1.y2, b2.y2))


class Preview(goocanvas.ItemSimple, goocanvas.Item, Zoomable):

    __gtype_name__ = 'Preview'

    def __init__(self, instance, element, height=46, **kwargs):
        super(Preview, self).__init__(**kwargs)
        Zoomable.__init__(self)
        self.app = instance
        self.height = float(height)
        self.element = element
        self.props.pointer_events = False
        # ghetto hack
        self.hadj = instance.gui.timeline.hadj

## properties

    def _get_height(self):
        return self._height

    def _set_height(self, value):
        self._height = value
        self.changed(True)
    height = gobject.property(_get_height, _set_height, type=float)

## element callbacks

    def _set_element(self):
        self.previewer = previewer.get_preview_for_object(self.app,
            self.element)
    element = receiver(setter=_set_element)

    @handler(element, "in-point-changed")
    @handler(element, "media-duration-changed")
    def _media_props_changed(self, obj, unused_start_duration):
        self.changed(True)

## previewer callbacks

    previewer = receiver()

    @handler(previewer, "update")
    def _update_preview(self, previewer, segment):
        # if segment is none we are not just drawing a new thumbnail, so we
        # should update bounds
        if segment == None:
            self.changed(True)
        else:
            self.changed(False)

## Zoomable interface overries

    def zoomChanged(self):
        self.changed(True)

## goocanvas item methods

    def do_simple_update(self, cr):
        cr.identity_matrix()
        if self.element.factory:
            border_width = self.previewer._spacing()
            self.bounds = goocanvas.Bounds(border_width, 4,
            max(0, Zoomable.nsToPixel(self.element.duration) -
                border_width), self.height)

    def do_simple_paint(self, cr, bounds):
        x1 = -self.hadj.get_value()
        cr.identity_matrix()
        if self.element.factory:
            self.previewer.render_cairo(cr, intersect(self.bounds, bounds),
            self.element, x1, self.bounds.y1)

    def do_simple_is_item_at(self, x, y, cr, pointer_event):
        return (between(0, x, self.nsToPixel(self.element.duration)) and
            between(0, y, self.height))
