# PiTiVi , Non-linear video editor
#
#       pitivi/ui/complextimeline.py
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
from complexstack import LayerStack, InfoLayout
from complexlayer import LayerInfoList

#
# Complex Timeline Design v1 (01 Feb 2006)
#
#
# Tree of contents (ClassName(ParentClass))
# -----------------------------------------
#
# ComplexTimelineWidget (gtk.HBox)
# |  Top container
# |
# +- InfoStack (gtk.VBox)
# |  |  Left side Stack. Tool and information on the streams
# |  |
# |  +- TopWidget (gtk.Label)
# |  |    Global information, could contain tools
# |  |
# |  +- InfoLayout (gtk.Layout)
# |     |  Uses the Timeline Vertical Adjustment
# |     |  
# |     +- InfoLayer (?, possibly gtk.DrawingArea or gtk.Expander)
# |          Information on the associated layer
# |
# +- LayerStack (gtk.Layout)
#    |  Uses the Timeline Horizontal Adjustment
#    |
#    +- ScaleRuler (gtk.DrawingArea)
#    |    Imitates the behaviour of a gtk.Ruler but for Time/Frames
#    |
#    +- TrackLayout (gtk.Layout)
#       |  Uses the Timeline Vertical Adjustment
#       |
#       +- TrackLayer (gtk.Layout)
#            The actual timeline layer containing the sources/effects/...
#
# -----------------------------------------
#

class ComplexTimelineWidget(gtk.HBox):
    __gsignals__ = {
         "size-request":"override",
         "size-allocate":"override",
        }
    _minheight = 200

    def __init__(self, pitivi, hadj, vadj):
        gst.log("creating")
        gtk.HBox.__init__(self)
        self.pitivi = pitivi
        self.set_spacing(5)
        self.hadj = hadj
        self.vadj = vadj

        # common LayerInfoList
        self.layerInfoList = LayerInfoList(pitivi.current.timeline)

        # Left Stack
        self.leftStack = gtk.VBox()
        self.leftTopWidget = self._getLeftTopWidget()
        self.leftStack.pack_start(self.leftTopWidget, expand=False)
        self.layerInfoList.topSizeGroup.add_widget(self.leftTopWidget)
        self.infoLayout = InfoLayout(self.layerInfoList, self.vadj)
        self.leftStack.pack_start(self.infoLayout, expand=True)

        self.pack_start(self.leftStack, expand=False, fill=True)

        # Right Stack
        self.rightStack = LayerStack(self.layerInfoList, self.hadj, self.vadj)

        self.pack_start(self.rightStack, expand=True, fill=True)

    ## left TopWidget methods

    def _getLeftTopWidget(self):
        # return the widget that goes at the top of the left stack
        # TODO : something better than a Label
        return gtk.Label("Layers")

    ## gtk.Widget overrides
        
    def do_size_request(self, requisition):
        gst.debug("timeline requisition %s" % list(requisition))
        ret = gtk.HBox.do_size_request(self, requisition)
        gst.debug("returning %s" % list(requisition))
        return ret

    def do_size_allocate(self, allocation):
        gst.debug("timeline got allocation:%s" % list(allocation))
        ret = gtk.HBox.do_size_allocate(self, allocation)
        return ret
