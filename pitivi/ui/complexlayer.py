#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       pitivi/ui/timeline.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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

class ComplexTimelineLayer(gtk.Layout):
    __gsignals__ = {"expose-event":"override",
                    "size-request":"override"
                    }

    minwidth = 100

    def __init__(self, composition):
        gtk.Layout.__init__(self)
        self.composition = composition
        
##     def do_size_allocate(self, allocation):
##         print "layer allocation", list(allocation)
##         self.allocation = allocation
##         if self.flags() & gtk.REALIZED:
##             self.window.move_resize(*allocation)

    def do_size_request(self, requisition):
        gst.debug("layer requisition %s" % list(requisition))
        gtk.Layout.do_size_request(self, requisition)
        requisition.width = self.minwidth
        requisition.height = 200

    def do_expose_event(self, event):
        gst.debug("layer expose %s" % list(event.area))
        if not event.window == self.bin_window:
            return
        self.context = self.bin_window.cairo_create()
        self.context.rectangle(*event.area)
        self.context.clip()
        self.draw(self.context)
        return False

    def draw(self, context):
        rect = self.get_allocation()
        gst.debug("layer draw %s" % list(rect))

        bg_gc = self.style.bg[gtk.STATE_NORMAL]
        fg_gc = self.style.fg[gtk.STATE_NORMAL]
        
        context.set_line_width(1)
        context.set_source_rgb(bg_gc.red, bg_gc.green, bg_gc.blue)
        context.rectangle(0, 0, rect.width, rect.height)
        context.fill()
        context.stroke()
        
        context.set_source_rgb(fg_gc.red, fg_gc.green, fg_gc.blue)
        context.set_line_width(5)
        context.rectangle(5, 5, rect.width-10, rect.height-10)
        context.stroke()
        

class ComplexTimelineInfoLayer(ComplexTimelineLayer):

    resizeable = False
    minwidth = 100

class ComplexTimelineTrackLayer(ComplexTimelineLayer):

    resizeable = True
    minwidth = 800

    def __init__(self, composition):
        ComplexTimelineLayer.__init__(self, composition)
