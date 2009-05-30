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

    sigid = None
    _instances = []
    zoom_levels = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5] + range(5, 10, 1) + \
        range(10, 150, 10)
    _cur_zoom = 2
    zoomratio = zoom_levels[_cur_zoom]


    def __init__(self):
        # FIXME: ideally we should deprecate this
        Zoomable.addInstance(self)

    def __del__(self):
        if self in Zoomable._instances:
            # FIXME: ideally we should deprecate this and spit a warning here
            self._instances.remove(self)

    @classmethod
    def addInstance(cls, instance):
        cls._instances.append(instance)

    @classmethod
    def removeInstance(cls, instance):
        cls._instances.remove(instance)

    @classmethod
    def setZoomRatio(cls, ratio):
        cls.zoomratio = ratio
        cls._zoomChanged()

    @classmethod
    def zoomIn(cls):
        cls._cur_zoom = min(len(cls.zoom_levels) - 1, cls._cur_zoom + 1)
        cls.setZoomRatio(cls._computeZoomRatio(cls._cur_zoom))

    @classmethod
    def zoomOut(cls):
        cls._cur_zoom = max(0, cls._cur_zoom - 1)
        cls.setZoomRatio(cls._computeZoomRatio(cls._cur_zoom))

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
        ## DIE YOU CUNTMUNCH CLOCK_TIME_NONE UBER STUPIDITY OF CRACK BINDINGS !!!!!!
        if duration == 18446744073709551615 or \
               long(duration) == long(gst.CLOCK_TIME_NONE):
            return 0
        return int((float(duration) / gst.SECOND) * cls.zoomratio)

    @classmethod
    def _zoomChanged(cls):
        for inst in cls._instances:
            inst.zoomChanged()

    def zoomChanged(self):
        pass
