# PiTiVi , Non-linear video editor
#
#       pitivi/ui/ruler.py
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

import gtk
import gst
from complexinterface import ZoomableWidgetInterface

class ScaleRuler(gtk.Layout, ZoomableWidgetInterface):

    __gsignals__ = {
        "expose-event":"override",
        "size-allocate":"override"
        }

    def __init__(self, hadj):
        gst.log("Creating new ScaleRule")
        gtk.Layout.__init__(self)
        self.set_hadjustment(hadj)
        # TODO : Implement drawing, size request and drawing

    ## ZoomableWidgetInterface methods are handled by the container (LayerStack)

    ## gtk.Widget overrides

    def do_size_allocate(self, allocation):
        gst.debug("ScaleRuler got %s" % list(allocation))
        gtk.Layout.do_size_allocate(self, allocation)
        width = max(self.get_pixel_width(), allocation.width)
        gst.debug("Setting layout size to %d x %d" % (width, allocation.height))
        self.set_size(width, allocation.height)

    def do_expose_event(self, event):
        gst.debug("exposing ScaleRuler %s" % list(event.area))
        self.context = self.bin_window.cairo_create()
        self.context.rectangle(*event.area)
        self.context.clip()
        self.draw(self.context)
        return False

    def draw(self, context):
        rect = self.get_allocation()
        gst.debug("Ruler draw %s" % list(rect))
        context.set_source_rgb(0.8, 0.8, 0.8)
        context.rectangle(0, 0, rect.width, rect.height)
        context.fill()
        context.stroke
