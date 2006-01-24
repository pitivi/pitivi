#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       pitivi/ui/complexstack.py
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
from complexlayer import ComplexTimelineInfoLayer, ComplexTimelineTrackLayer
    
class ComplexTimelineStack(gtk.Layout):

    __gsignals__ = {
        "expose-event":"override",
        "size-request":"override",
        }
    layerclass = None

    def __init__(self, widthflexible=False):
        self.widthflexible = self.layerclass.resizeable
        gtk.Layout.__init__(self)
        self.layers = []
        self.compositions = []

    def do_expose_event(self, event):
        gst.debug("stack expose %s" % list(event.area))
        gst.debug("size %s" % list(self.get_size()))
        ypos = 0
        width,height = self.get_size()
        for widget in self.layers:
            nw, nh = widget.size_request()
            # draw handle at 0, ypos + nh
            # w x h == width, 10
            self.style.paint_handle(self.bin_window,
                                    gtk.STATE_NORMAL,
                                    gtk.SHADOW_NONE,
                                    None, self, "paned",
                                    0, ypos + nh,
                                    width, 10,
                                    gtk.ORIENTATION_VERTICAL)
        return False

    def do_size_request(self, requisition):
        gst.info("stack requisition %s" % list(requisition))
        width = 0
        height = 0
        for widget in self.layers:
            nw, nh = widget.size_request()
            nx, ny = self.child_get(widget, "x", "y")
            if (nw + nx) > width:
                width = nw + nx
            if (nh + ny) > height:
                height = nh + ny
        if not self.widthflexible:
            requisition.width = width
        gst.debug("setting width to %d" % width)
        self.set_size(width, height)
        #requisition.height = height

    def _update_compositions(self):
        # update the position/size of the compositions
        ypos = 0
        for layer in self.layers:
            # position correctly
            nw, nh = layer.size_request()
            self.move(layer, 0, ypos)
            ypos += nh + 10

    def __delitem__(self, pos):
        # del x[pos]
        self._update_compositions()
        pass

    def __getitem__(self, pos):
        # x[pos]
        pass

    def __iter__(self):
        return self.compositions.__iter__()

    def append(self, composition):
        # TODO : do type checking here
        self.compositions.append(composition)
        layer = self.layerclass(composition)
        self.layers.append(layer)
        self.put(layer, 0, 0)
        self._update_compositions()

    def insert(self, pos, composition):
        # insert composition before pos
        self.compositions.insert(pos, composition)
        layer = self.layerclass(composition)
        self.layers.insert(pos, layer)
        self.put(layer, 0, 0)
        self._update_compositions()

class ComplexTimelineInfoStack(ComplexTimelineStack):

    layerclass = ComplexTimelineInfoLayer

class ComplexTimelineTrackStack(ComplexTimelineStack):

    layerclass = ComplexTimelineTrackLayer
