#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       pitivi/ui/complexlayer.py
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

import gst

#
# Complex Timeline interfaces v1 (01 Feb 2006)
#
#
# ZoomableWidgetInterface
# -----------------------
# Interface for the Complex Timeline widgets for setting, getting,
# distributing and modifying the zoom ratio and the size of the widget.
#
# A zoomratio is the number of pixels per second
# ex : 10.0 = 10 pixels for a second
# ex : 0.1 = 1 pixel for 10 seconds
# ex : 1.0 = 1 pixel for a second
#
# Methods:
# . set_zoomratio(ratio)
# . get_zoomratio(ratio)
# . pixel_to_ns(pixels)
# . ns_to_pixels(time)
# . get_pixel_width()
#
#
# LayeredWidgetInterface
# ----------------
# Interface for 'layered' widgets.
# The layers correspond to the top-level Composition of the Timeline Model.
# It's purpose is to handle the contained layers' height and position
# It uses the LayerInfoList which is shared across the various widgets
# implementing the LayeredInterface, so that those widgets have layers which
# are synchronized (in height, number and content).
#
# The widgets implementing this interface should use it's methods to request
# expansion/resize/adding of layers, and should implement the needed virtual
# methods for actually resizing the layers.
#
# . set_layerinfo(layerinfo)
# . expand_layer(layerposition, boolean)
# . change_layer_height(layerposition, newheight)
# . layer_expanded(layerposition, boolean) Implement
# . layer_height_changed(layerposition, newheight)
# . add_layer(layerposition, composition)
#

class ZoomableWidgetInterface:

    zoomratio = 10.0
    
    def get_pixel_width(self):
        """
        Returns the width in pixels corresponding to the duration of the object
        """
        dur = self.get_duration()
        width = self.ns_to_pixel(dur)
        gst.log("Got time %s, returning width : %d" % (gst.TIME_ARGS(dur), width))
        return width

    def get_pixel_position(self):
        """
        Returns the pixel offset of the widget in it's container, according to:
        _ the start position of the object in it's timeline container,
        _ and the set zoom ratio
        """
        start = self.get_start_time()
        pos = self.ns_to_pixel(start)
        gst.log("Got start time %s, returning offset %d" % (gst.TIME_ARGS(start), pos))
        return pos

    def pixel_to_ns(self, pixel):
        """
        Returns the pixel equivalent in nanoseconds according to the zoomratio
        """
        return int(pixel * gst.SECOND / self.zoomratio)

    def ns_to_pixel(self, duration):
        """
        Returns the pixel equivalent of the given duration, according to the
        set zoom ratio
        """
        if duration == gst.CLOCK_TIME_NONE:
            return 0
        return int((float(duration) / gst.SECOND) * self.zoomratio)
        
    def get_duration(self):
        """
        Return the duration in nanoseconds of the object
        To be implemented by subclasses
        """
        raise NotImplementedError

    def get_start_time(self):
        """
        Return the start time in nanosecond of the object
        To be implemented by subclasses
        """
        raise NotImplementedError

    def duration_changed(self):
        self.queue_resize()

    def start_changed(self):
        self.queue_resize()

    def start_duration_changed(self):
        gst.info("start/duration changed")
        self.queue_resize()
    
    def get_zoom_ratio(self):
        return self.zoomratio

    def set_zoom_ratio(self, zoomratio):
        if self.zoomratio == zoomratio:
            return
        gst.debug("Changing zoomratio to %f" % zoomratio)
        self.zoomratio = zoomratio
        self.zoomChanged()

    def zoomChanged(self):
        raise NotImplementedError

class LayeredWidgetInterface:

    def __init__(self, infolist):
        self.layerinfolist = None
        self.__expandedSig = 0
        self.__heightChangedSig = 0
        self.__addedSig = 0
        self.__removedSig = 0
        
        self.setLayerInfoList(infolist)
        
    def setLayerInfoList(self, infolist):
        """ set the LayerInfoList and connect the signal handlers """
        if self.layerinfolist:
            # remove existing signal handlers
            for sigid in [self.__expandedSig, self.__heightChangedSig,
                          self.__addedSig, self.__removedSig]:
                self.layerinfolist.disconnect(sigid)
        # save list and set signal handlers
        self.layerinfolist = infolist
        self.__expandedSig = self.layerinfolist.connect('layer-expanded',
                                                        self.__expanded_cb)
        self.__heightChangedSig = self.layerinfolist.connect('layer-height-changed',
                                                             self.__layer_height_changed_cb)
        self.__addedSig = self.layerinfolist.connect('layer-added',
                                                     self.__layer_added_cb)
        self.__removedSig = self.layerinfolist.connect('layer-removed',
                                                     self.__layer_removed_cb)
        
        gst.info("calling layerAdded for all the existing layers")
        for i in range(len(self.layerinfolist)):
            self.layerAdded(i)
            

    def expandLayer(self, layerposition, expanded):
        """ expand (or reduce) the layer at given position """
        self.layerinfolist.expandLayer(layerposition, expanded)

    def changeLayerHeight(self, layerposition, height):
        """ set the layer at the given position to the requested height """
        self.layerinfolist.changeLayerHeight(layerposition, height)

    def __expanded_cb(self, list, layerposition, expanded):
        self.layerExpanded(layerposition, expanded)

    def __layer_height_changed_cb(self, list, layerposition):
        self.layerHeightChanged(layerposition)

    def __layer_added_cb(self, list, position):
        self.layerAdded(position)

    def __layer_removed_cb(self, list, position):
        self.layerRemoved(position)

    def layerExpanded(self, layerposition, expanded):
        raise NotImplementedError

    def layerHeightChanged(self, layerposition):
        raise NotImplementedError

    def layerAdded(self, position):
        """
        A layer was added, position is the position where it was added
        """
        raise NotImplementedError

    def layerRemoved(self, position):
        """
        A layer was removed, position is the position where it previously was
        """
        raise NotImplementedError

    
