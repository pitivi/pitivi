#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       pitivi/ui/tracklayer.py
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
from complexsource import ComplexTimelineSource

#
# TrackLayer
#
# The TrackLayer is the graphical representation of a top-level composition.
#

class TrackLayer(gtk.Layout, ZoomableWidgetInterface):

    __gsignals__ = {
#        "size-request":"override",
        "size-allocate":"override",
        "expose-event":"override"
        }

    # Safe adding zone on the left/right
    border = 5
    effectgutter = 5
    layergutter = 5

    def __init__(self, layerInfo, hadj):
        gst.log("new TrackLayer for composition %r" % layerInfo.composition)
        gtk.Layout.__init__(self)
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(20000,20000,16000))

        self.set_hadjustment(hadj)
        self.sources = {}
        
        self.layerInfo = layerInfo
        self.layerInfo.composition.connect('start-duration-changed', self.compStartDurationChangedCb)
        self.layerInfo.composition.connect('source-added', self.compSourceAddedCb)
        self.set_property("width-request", self.get_pixel_width())


    ## composition signal callbacks

    def compStartDurationChangedCb(self, composition, start, duration):
        gst.info("setting width-request to %d" % self.get_pixel_width())
        self.set_property("width-request", self.get_pixel_width())
        self.set_size(self.get_pixel_width(), self.allocation.height)
        #self.set_property("height-request", self.layerInfo.currentHeight)
        self.start_duration_changed()

    def compSourceAddedCb(self, composition, source):
        gst.debug("Got a new source to put in %s !!" % list(self.get_size()))
        # create new widget
        widget = ComplexTimelineSource(source, self.layerInfo)
        
        # add it to self at the correct position
        self.sources[source] = widget
        if self.layerInfo.expanded:
            height = 100
        else:
            height = self.allocation.height - self.effectgutter - 2 * self.layergutter
        # TODO : set Y position depending on layer it's on
        self.put(widget, widget.get_pixel_position() + self.border,
                 self.effectgutter + self.layergutter)
        # we need to force the size_allocation
        widget.size_allocate(gtk.gdk.Rectangle(widget.get_pixel_position() + self.border,
                                               self.effectgutter + self.layergutter,
                                               widget.get_pixel_width(),
                                               height))
        #widget.set_property("height-request", height)
        #self.queue_draw()

    ## ZoomableWidgetInterface methods

    def get_duration(self):
        return self.layerInfo.composition.duration

    def get_start_time(self):
        return self.layerInfo.composition.start

    def get_pixel_width(self):
        return ZoomableWidgetInterface.get_pixel_width(self) + 2 * self.border

    ## virtual methods overrides
            
    def do_size_allocate(self, allocation):
        gst.debug("%r got allocation %s" % (self, list(allocation)))
        for source in self.sources:
            if self.layerInfo.expanded:
                height = 100
            else:
                height = allocation.height - self.effectgutter - 2 * self.layergutter
            self.sources[source].set_property("height-request", height)
        gtk.Layout.do_size_allocate(self, allocation)

    def do_expose_event(self, event):
        gst.debug("TrackLayer %s" % list(event.area))
        gtk.Layout.do_expose_event(self, event)

    ## methods needed by the container (CompositionLayer)

    def getNeededHeight(self):
        """ return the needed height """
        if self.layerInfo.expanded:
            # TODO : update this formula
            # height = effectgutter + layergutter + n * (layerheight + layergutter)
            height = self.effectgutter + 2 * self.layergutter + 100
            return height
        return 0
