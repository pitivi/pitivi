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

"""
Interfaces for complex view elements
"""

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
# . setZoomRatio(ratio)
# . getZoomRatio(ratio)
# . pixelToNs(pixels)
# . nsToPixels(time)
# . getPixelWidth()
#
#

class ZoomableWidgetInterface:

    def getPixelWidth(self):
        """
        Returns the width in pixels corresponding to the duration of the object
        """
        dur = self.getDuration()
        width = self.nsToPixel(dur)
        gst.log("Got time %s, returning width : %d" % (gst.TIME_ARGS(dur), width))
        return width

    def getPixelPosition(self):
        """
        Returns the pixel offset of the widget in it's container, according to:
        _ the start position of the object in it's timeline container,
        _ and the set zoom ratio
        """
        start = self.getStartTime()
        pos = self.nsToPixel(start)
        gst.log("Got start time %s, returning offset %d" % (gst.TIME_ARGS(start), pos))
        return pos

    def pixelToNs(self, pixel):
        """
        Returns the pixel equivalent in nanoseconds according to the zoomratio
        """
        return int(pixel * gst.SECOND / self.getZoomRatio())

    def nsToPixel(self, duration):
        """
        Returns the pixel equivalent of the given duration, according to the
        set zoom ratio
        """
        if duration == gst.CLOCK_TIME_NONE:
            return 0
        return int((float(duration) / gst.SECOND) * self.getZoomRatio())

    ## Methods to implement in subclasses
        
    def getDuration(self):
        """
        Return the duration in nanoseconds of the object
        To be implemented by subclasses
        """
        raise NotImplementedError

    def getStartTime(self):
        """
        Return the start time in nanosecond of the object
        To be implemented by subclasses
        """
        raise NotImplementedError

    def zoomChanged(self):
        raise NotImplementedError

    def durationChanged(self):
        self.queue_resize()

    def startChanged(self):
        self.queue_resize()

    def startDurationChanged(self):
        gst.info("start/duration changed")
        self.queue_resize()
    
    def getZoomRatio(self):
        # either the current object is the top-level object that contains the zoomratio
        if hasattr(self, 'zoomratio'):
            return self.zoomratio
        # chain up to the parent
        parent = self.parent
        while not hasattr(parent, 'getZoomRatio'):
            parent = parent.parent
        return parent.getZoomRatio()

    def setZoomRatio(self, zoomratio):
        if hasattr(self, 'zoomratio'):
            if self.zoomratio == zoomratio:
                return
            gst.debug("Changing zoomratio to %f" % zoomratio)
            self.zoomratio = zoomratio
            self.zoomChanged()
        else:
            self.parent.setZoomRatio(zoomratio)
