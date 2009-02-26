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
# . pixelToNs(pixels)
# . nsToPixels(time)
# . setZoomRatio
# Instance Methods
# . zoomChanged()

class Zoomable(object):

    zoomratio = 10
    sigid = None
    __instances = []
    zoom_levels = (1, 5, 10, 20, 50, 100, 150) 
    __cur_zoom = 2


    def __init__(self):
        # FIXME: ideally we should deprecate this
        Zoomable.addInstance(self)

    def __del__(self):
        if self in Zoomable.__instances:
            # FIXME: ideally we should deprecate this and spit a warning here
            self.__instances.remove(self)

    @classmethod
    def addInstance(cls, instance):
        cls.__instances.append(instance)

    @classmethod
    def removeInstance(cls, instance):
        cls.__instances.remove(instance)

    @classmethod
    def setZoomRatio(cls, ratio):
        cls.zoomratio = ratio
        cls.__zoomChanged()

    @classmethod
    def zoomIn(cls):
        cls.__cur_zoom = min(len(cls.zoom_levels) - 1, cls.__cur_zoom + 1)
        cls.setZoomRatio(cls._computeZoomRatio(cls.__cur_zoom))

    @classmethod
    def zoomOut(cls):
        cls.__cur_zoom = max(0, cls.__cur_zoom - 1)
        cls.setZoomRatio(cls._computeZoomRatio(cls.__cur_zoom))

    @classmethod
    def _computeZoomRatio(cls, index):
        return cls.zoom_levels[index]

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
        if long(duration) == long(gst.CLOCK_TIME_NONE):
            return 0
        return int((float(duration) / gst.SECOND) * cls.zoomratio)

    @classmethod
    def __zoomChanged(cls):
        for inst in cls.__instances:
            inst.zoomChanged()

    def zoomChanged(self):
        pass

