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
        "size-allocate":"override",
        "realize":"override",
        }

    border = 5

    def __init__(self, hadj):
        gst.log("Creating new ScaleRule")
        gtk.Layout.__init__(self)
        self.set_hadjustment(hadj)
        self.pixmap = None

    ## ZoomableWidgetInterface methods are handled by the container (LayerStack)
    ## Except for ZoomChanged

    def zoomChanged(self):
        self.doPixmap()
        self.queue_draw()

    def get_pixel_width(self):
        return ZoomableWidgetInterface.get_pixel_width(self) + 2 * self.border

    ## gtk.Widget overrides

    def do_size_allocate(self, allocation):
        gst.debug("ScaleRuler got %s" % list(allocation))
        gtk.Layout.do_size_allocate(self, allocation)
        width = max(self.get_pixel_width(), allocation.width)
        gst.debug("Setting layout size to %d x %d" % (width, allocation.height))
        self.set_size(width, allocation.height)
        # the size has changed, therefore we want to redo our pixmap
        self.doPixmap()

    def do_realize(self):
        gtk.Layout.do_realize(self)
        # we want to create our own pixmap here
        self.doPixmap()

    def do_expose_event(self, event):
        gst.debug("exposing ScaleRuler %s" % list(event.area))
        x, y, width, height = event.area
        # double buffering power !
        self.bin_window.draw_drawable(self.style.fg_gc[gtk.STATE_NORMAL],
                                      self.pixmap,
                                      x, y, x, y, width, height)
        return False

    def doPixmap(self):
        """ (re)create the buffered drawable for the Widget """
        # we can't create the pixmap if we're not realized
        if not self.flags() & gtk.REALIZED:
            return
        allocation = self.get_allocation()
        lwidth, lheight = self.get_size()
        allocation.width = max(allocation.width, lwidth)
        gst.debug("Creating pixmap(self.window, width:%d, height:%d)" % (allocation.width, allocation.height))
        self.pixmap = gtk.gdk.Pixmap(self.bin_window, allocation.width, allocation.height)
        context = self.pixmap.cairo_create()
        self.draw_background(context, allocation)
        self.draw_ruler(context, allocation)

    def draw(self, context):
        rect = self.get_allocation()
        gst.debug("Ruler draw %s" % list(rect))
        self.draw_background(context, rect)
        self.draw_ruler(context, rect)

    def draw_background(self, context, allocation):
        context.save()
        
        context.set_source_rgb(0.8, 0.8, 0.8)
        context.rectangle(0, 0,
                          allocation.width, allocation.height)
        context.fill()
        context.stroke
        
        context.restore()

    def draw_ruler(self, context, allocation):
        # one tick every second
        # FIXME : respect zoomratio !!!!
        context.save()
        context.set_line_width(0.5 * context.get_line_width())
        context.set_source_rgb(0, 0, 0)
        
        for i in range(self.border, allocation.width, 10):
            context.move_to(i, 0)
            
            if (i - self.border) % 100:
                context.line_to(i, allocation.height / 4)
            elif (i - self.border) % 600:
                context.line_to(i, allocation.height / 2)
            else:
                context.line_to(i, allocation.height)
            
        context.stroke()
        context.restore()
