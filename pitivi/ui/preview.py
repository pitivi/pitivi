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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Custom canvas item for timeline object previews. This code is just a thin
canvas-item wrapper which ensures that the preview is updated appropriately.
The actual drawing is done by the pitivi.previewer.Previewer class.  """

import gtk
import cairo
import goocanvas
import gobject
import gst
from gettext import gettext as _
from pitivi.receiver import receiver, handler
from pitivi.objectfactory import FileSourceFactory
from zoominterface import Zoomable

def between(a, b, c):
    return (a <= b) and (b <= c)

def intersect(b1, b2):
    return goocanvas.Bounds(max(b1.x1, b2.x1), max(b1.y1, b2.y1),
        min(b1.x2, b2.x2), min(b1.y2, b2.y2))

class Preview(goocanvas.ItemSimple, goocanvas.Item, Zoomable):

    __gtype_name__ = 'Preview'

    def __init__(self, element, height=50, **kwargs):
        super(Preview, self).__init__(**kwargs)
        Zoomable.__init__(self)
        self.height = float(height)
        self.element = element
        self.props.pointer_events = False

## properties

    def __get_height(self):
        return self.__height
    def __set_height (self, value):
        self.__height = value
        self.changed(True)
    height = gobject.property(__get_height, __set_height, type=float)

## element callbacks

    def __set_element(self):
        self.previewer = self.element.factory.preview
    element = receiver(setter=__set_element)

    @handler(element, "media-start-duration-changed")
    def __media_props_changed(self, obj, start, duration):
        self.changed(True)

## previewer callbacks

    previewer = receiver()

    @handler(previewer, "update")
    def __update_preview(self, previewer, stream):
        if self.element.media_type == stream:
            #TODO: check timestamps and stream info to prevent unecessary updates
            self.changed(False)

## Zoomable interface overries

    def zoomChanged(self):
        self.changed(True)

## goocanvas item methods

    def do_simple_update(self,cr):
        # TODO: bounds intersection
        self.bounds = goocanvas.Bounds(0, 0,
            Zoomable.nsToPixel(self.element.duration), self.height)

    def do_simple_paint(self, cr, bounds):
        cr.identity_matrix()
        self.previewer.render_cairo(cr, intersect(self.bounds, bounds),
            self.element)

    def do_simple_is_item_at(self, x, y, cr, pointer_event):
        return (between(0, x, self.nsToPixel(self.element.duration)) and
            between(0, y, self.height))

