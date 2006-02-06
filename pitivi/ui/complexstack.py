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
from complexlayer import InfoLayer, TrackLayer
from ruler import ScaleRuler
from complexinterface import LayeredWidgetInterface, ZoomableWidgetInterface

class TrackLayout(gtk.Layout, LayeredWidgetInterface, ZoomableWidgetInterface):
    __gsignals = {
        "size-allocate":"override",
        }

    def __init__(self, layerInfoList, vadj):
        gtk.Layout.__init__(self)
        self.tracks = []
        LayeredWidgetInterface.__init__(self, layerInfoList)
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(32000,0,0))
        self.set_vadjustment(vadj)

        # TODO : implement size-request/allocation

        # TODO : implement LayeredWidgetInterface vmethods
        
        # TODO : implement ZoomableWidgetInterface vmethods


    ## gtk.Widget overrides

    def do_size_allocate(self, allocation):
        gst.debug("TrackLayout got allocation %s" % list(allocation))
        gtk.Layout.do_size_allocate(self, allocation)

    def __updateLayoutHeight(self):
        width, height = max(self.get_size(), self.allocation.width)
        self.set_size(width, self.layerinfolist.totalHeight)
        self.queue_resize()

    ## gtk.Layout overrides

    def set_size(self, width, height):
        gst.debug("Setting TrackLayout size to %d x %d" % (width, height))
        gtk.Layout.set_size(self, width, height)
        
    ## LayeredWidgetInterface methods
        
    def layerExpanded(self, layerposition, expanded):
        # TODO : resize track
        # modify layout size
        self.__updateLayoutHeight()

    def layerHeightChanged(self, layerposition):
        # TODO : resize track
        self.tracks[layerposition].set_property("height-request",
                                                self.layerinfolist[layerposition].currentHeight)
        # modify layout size
        self.__updateLayoutHeight()

    def layerAdded(self, layerposition):
        gst.debug("Adding a layer to TrackLayout")
        layerinfo = self.layerinfolist[layerposition]
        track = TrackLayer(layerinfo)
        track.set_property("height-request",
                           layerinfo.currentHeight)
        self.tracks.insert(layerposition, track)
        self.__updateLayoutHeight()
        self.put(track, 0, layerinfo.yposition)
        # TODO : force redraw

    def layerRemoved(self, layerposition):
        track = self.tracks.pop(layerposition)
        self.remove(track)
        self.__updateLayoutHeight()
        # TOOD : force redraw    


    ## ZoomableWidgetInterface methods

    def get_duration(self):
        if len(self.tracks):
            return max([track.get_duration() for track in self.tracks])
        return 0

    def get_start_time(self):
        if len(self.tracks):
            return min([track.get_start_time() for track in self.tracks])
        return 0

    def zoomChanged(self):
        # propagate to childs
        for track in self.tracks:
            track.zoomChanged()
        # resize ourself
        w, h = self.get_size()
        self.set_size(self.get_pixel_width(),
                      h)

class LayerStack(gtk.Layout, ZoomableWidgetInterface):
    __gsignals__ = {
         "size-allocate":"override",
        }

    def __init__(self, layerInfoList, hadj, vadj):
        gtk.Layout.__init__(self)

        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(16000,16000,16000))
        
        self.horizontalAdj = hadj
        self.verticalAdj = vadj
        self.set_hadjustment(self.horizontalAdj)

        # top Scale Ruler
        self.scaleRuler = ScaleRuler()
        self.scaleRuler.get_duration = self.get_duration
        self.scaleRuler.get_start_time = self.get_start_time
        self.put(self.scaleRuler, 0, 0)
        layerInfoList.topSizeGroup.add_widget(self.scaleRuler)
        width, self.offset = self.scaleRuler.size_request()

        # track Layout
        self.trackLayout = TrackLayout(layerInfoList, vadj)
        self.put(self.trackLayout, 0, self.offset)

    ## gtk.Widget overrides

    def do_size_allocate(self, allocation):
        gst.debug("LayerStack got allocation:%s" % list(allocation))
        # The height of this layout needs to be the same as what is allocated
        # set the child size_request before calling parent size_allocate

        # width is the greatest of:
        #   _ allocated area
        #   _ timeline pixel width
        width = max(allocation.width, self.get_pixel_width())
        
        self.set_size(width, allocation.height)
        self.scaleRuler.set_property("width-request", width)
        #self.scaleRuler.set_property("height-request", self.offset)
        gst.debug("LayerStack is giving %d x %d request to TrackLayout" % (width, allocation.height - self.offset))
        self.trackLayout.set_property("width-request", width)
        self.trackLayout.set_property("height-request", allocation.height-self.offset)
        ret = gtk.Layout.do_size_allocate(self, allocation)
        return ret

    ## ZoomableWidgetInterface methodse

    def get_duration(self):
        return self.trackLayout.get_duration()

    def get_start_time(self):
        return self.trackLayout.get_start_time()

    def zoomChanged(self):
        # propagate to childs
        self.scaleRuler.zoomChanged()
        self.trackLayout.zoomChanged()
        # resize ourself
        w,h = self.get_size()
        self.set_size(self.get_pixel_width(),
                      h)

class InfoLayout(gtk.Layout, LayeredWidgetInterface):
    __gsignals__ = {
         "size-request":"override",
         "size-allocate":"override",
        }

    def __init__(self, layerInfoList, vadj):
        gtk.Layout.__init__(self)
        self.tracks = []
        LayeredWidgetInterface.__init__(self, layerInfoList)
        self.set_vadjustment(vadj)

    ## gtk.Widget overrides

    def do_size_request(self, requisition):
        gst.debug("InfoLayout requisition %s" % list(requisition))
        width = 0
        # figure out width
        for i in range(len(self.tracks)):
            track = self.tracks[i]
            childwidth, childheight = track.size_request()
            width = max(width, childwidth)
        # set child requisition
        for i in range(len(self.tracks)):        
            self.tracks[i].set_size_request(width,
                                            self.layerinfolist[i].currentHeight)
        # inform container of required width
        requisition.width = width
        gst.debug("returning %s" % list(requisition))

    def do_size_allocate(self, allocation):
        # TODO : We should expand the layers height if we have more allocation
        # height than needed
        gst.debug("InfoLayout got allocation:%s" % list(allocation))
        ret = gtk.Layout.do_size_allocate(self, allocation)
        return ret

    def __updateLayoutHeight(self):
        width, height = self.get_size()
        self.set_size(width, self.layerinfolist.totalHeight)

    ## gtk.Layout overrides

    def set_size(self, width, height):
        gst.debug("InfoLayout setting size to %dx%d" % (width, height))
        gtk.Layout.set_size(self, width, height)


    ## LayeredWidgetInterface methods

    def layerAdded(self, layerposition):
        track = InfoLayer(self.layerinfolist[layerposition])
        self.tracks.insert(layerposition, track)
        self.__updateLayoutHeight()
        self.put(track, 0, self.layerinfolist[layerposition].yposition)
        # TODO : force redraw

    def layerRemoved(self, layerposition):
        track = self.tracks.pop(layerposition)
        self.remove(track)
        self.__updateLayoutHeight()
        # TODO : force redraw

    # TODO : implement other LayeredWidgetInterface methods


