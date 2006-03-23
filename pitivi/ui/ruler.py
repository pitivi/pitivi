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

"""
Widget for the complex view ruler
"""

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
        # position is in nanoseconds
        self.position = 0

    ## ZoomableWidgetInterface methods are handled by the container (LayerStack)
    ## Except for ZoomChanged

    def zoomChanged(self):
        self.doPixmap()
        self.queue_draw()

    def getPixelWidth(self):
        return ZoomableWidgetInterface.getPixelWidth(self) + 2 * self.border


    ## timeline position changed method

    def timelinePositionChanged(self, value, frame):
        previous = self.position
        self.position = value
        self.queue_draw_area(max(self.nsToPixel(min(value, previous)) - 5, 0),
                             0,
                             self.nsToPixel(max(value, previous)) + 5,
                             self.get_allocation().height)

    ## gtk.Widget overrides

    def do_size_allocate(self, allocation):
        gst.debug("ScaleRuler got %s" % list(allocation))
        gtk.Layout.do_size_allocate(self, allocation)
        width = max(self.getPixelWidth(), allocation.width)
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
        # draw the position
        context = self.bin_window.cairo_create()
        self.drawPosition(context, self.get_allocation())
        return False


    ## Drawing methods
    
    def doPixmap(self):
        """ (re)create the buffered drawable for the Widget """
        # we can't create the pixmap if we're not realized
        if not self.flags() & gtk.REALIZED:
            return
        allocation = self.get_allocation()
        lwidth, lheight = self.get_size()
        allocation.width = max(allocation.width, lwidth)
        gst.debug("Creating pixmap(self.window, width:%d, height:%d)" % (allocation.width, allocation.height))
        if self.pixmap:
            del self.pixmap
        self.pixmap = gtk.gdk.Pixmap(self.bin_window, allocation.width, allocation.height)
        context = self.pixmap.cairo_create()
        self.drawBackground(context, allocation)
        self.drawRuler(context, allocation)

    def draw(self, context):
        rect = self.get_allocation()
        gst.debug("Ruler draw %s" % list(rect))
        self.drawBackground(context, rect)
        self.drawRuler(context, rect)

    def drawBackground(self, context, allocation):
        context.save()

        context.set_source_rgb(0.5, 0.5, 0.5)
        context.rectangle(0, 0,
                          allocation.width, allocation.height)
        context.fill()
        context.stroke()

        if self.getDuration() > 0:
            context.set_source_rgb(0.8, 0.8, 0.8)
            context.rectangle(0, 0,
                              self.getPixelWidth(), allocation.height)
            context.fill()
            context.stroke
        
        context.restore()

    def drawRuler(self, context, allocation):
        # one tick every second
        # FIXME : respect zoomratio !!!!
        context.save()
        context.set_line_width(0.5 * context.get_line_width())
        context.set_source_rgb(0, 0, 0)

        zoomRatio = self.getZoomRatio()
        
        for i in range(self.border, allocation.width, zoomRatio):
            context.move_to(i, 0)
            
            if (i - self.border) % (10 * zoomRatio):
                # second
                context.line_to(i, allocation.height / 4)
            elif (i - self.border) % (60 * zoomRatio):
                # 10 seconds
                context.line_to(i, allocation.height / 2)
            else:
                # minute
                context.line_to(i, allocation.height)
            
        context.stroke()
        context.restore()

    def drawPosition(self, context, allocation):
        if self.getDuration() <= 0:
            return
        # a simple RED line will do for now
        xpos = self.nsToPixel(self.position) + self.border
        context.save()
        context.set_source_rgb(1.0, 0, 0)

        context.move_to(xpos, 0)
        context.line_to(xpos, allocation.height)
        context.stroke()
        
        context.restore()
