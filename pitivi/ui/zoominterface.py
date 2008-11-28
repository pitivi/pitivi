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
Interface for managing tranformation between timeline timestamps and UI
pixels.
"""

import gst
from pitivi.receiver import receiver, handler

#
# Complex Timeline interfaces v2 (01 Jul 2008)
#
# Zoomable
# -----------------------
# Interface for the Complex Timeline widgets for setting, getting,
# distributing and modifying the zoom ratio and the size of the widget.
#
# A zoomratio is the number of pixels per second
# ex : 10.0 = 10 pixels for a second
# ex : 0.1 = 1 pixel for 10 seconds
# ex : 1.0 = 1 pixel for a second
#
# Class Methods
# . setZoomAdjustment(adj)
# . getZoomAdjustment()
# . getZoomRatio
# . pixelToNs(pixels)
# . nsToPixels(time)
# . setZoomRatio
# Instance Methods
# . zoomChanged()

class Zoomable(object):

    zoomratio = 10
    zoom_adjustment = None
    sigid = None
    __instances = []

    def __init__(self):
        object.__init__(self)
        self.__instances.append(self)

    def __del__(self):
        if self in Zoomable.__instances:
            self.__instances.remove(self)

    @classmethod
    def _zoom_changed_cb(cls, adjustment):
        cls.zoomratio = adjustment.get_value()
        cls.__zoomChanged()

    @classmethod
    def setZoomAdjustment(cls, adjustment):
        if cls.zoom_adjustment:
            cls.zoom_adjustment.disconnect(cls.sigid)
            cls.zoom_adjustment = None
        if adjustment:
            cls.sigid = adjustment.connect("value-changed", 
                cls._zoom_changed_cb)
            cls.zoom_adjustment = adjustment
            cls._zoom_changed_cb(adjustment)

    @classmethod
    def getZoomAdjustment(cls):
        return cls.zoom_adjustment

    @classmethod
    def setZoomRatio(cls, ratio):
        cls.zoom_adjustment.set_value(ratio)

    @classmethod
    def pixelToNs(cls, pixel):
        """
        Returns the pixel equivalent in nanoseconds according to the zoomratio
        """
        return long(pixel * gst.SECOND / cls.zoomratio)

    @classmethod
    def nsToPixel(cls, duration):
        """
        Returns the pixel equivalent of the given duration, according to the
        set zoom ratio
        """
        if duration == gst.CLOCK_TIME_NONE:
            return 0
        return int((float(duration) / gst.SECOND) * cls.zoomratio)

    @classmethod
    def __zoomChanged(cls):
        for inst in cls.__instances:
            inst.zoomChanged()

    def zoomChanged(self):
        pass

