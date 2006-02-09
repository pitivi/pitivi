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

from pitivi.timeline import TimelineSource
from complexinterface import ZoomableWidgetInterface

# TODO : We might need an abstract class for ComplexTimelineObjects....

class ComplexTimelineSource(gtk.DrawingArea, ZoomableWidgetInterface):
    __gsignals__ = {
        "expose-event":"override",
        "size-request":"override",
        }

    modelclass = TimelineSource

    def __init__(self, source, layerInfo):
        gtk.DrawingArea.__init__(self)
        self.layerInfo = layerInfo
        #self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0,0,0))
        self.source = source
        self.source.connect("start-duration-changed", self._start_duration_changed_cb)


    def get_height(self):
        # TODO, maybe this should be zoomable too ?
        return 50

    ## gtk.Widget overrides

    def do_expose_event(self, event):
        gst.debug("timelinesource %s" % list(event.area))
        # TODO : we need to check to see if a redraw is necessary
        self.context = self.window.cairo_create()
        self.context.rectangle(*event.area)
        self.context.clip()
        self.draw(self.context)
        return False

    def do_size_request(self, requisition):
        gst.debug("source, requisition:%s" % list(requisition))
        requisition.width=self.get_pixel_width()
        if self.layerInfo.expanded:
            requisition.height=self.get_height()

    def draw(self, context):
        rect = self.get_allocation()
        gst.debug("Source draw %s" % list(rect))
        context.set_source_rgb(1, 0, 0)
        context.rectangle(0, 0, rect.width, rect.height)
        context.stroke()

    ## ZoomableWidgetInterface methods

    def get_duration(self):
        return self.source.duration

    def get_start_time(self):
        return self.source.start

    def _start_duration_changed_cb(self, source, start, duration):
        self.start_duration_changed()
