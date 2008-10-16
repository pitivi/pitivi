# PiTiVi , Non-linear video editor
#
#       pitivi/elements/videofade.py
#
# Copyright (c) 2008, Edward Hervey <bilboed@bilboed.com>
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
Simple video fade element
"""

import gobject
import gst

class VideoFade(gst.Bin):
    """
    Simple video fade element
    """

    def __init__(self, position=0, duration=2*gst.SECOND, fadefromblack=True):
        gst.Bin.__init__(self)
        self.incsp = gst.element_factory_make("ffmpegcolorspace", "incsp")
        self.outcsp = gst.element_factory_make("ffmpegcolorspace", "outcsp")
        self.alpha = gst.element_factory_make("alpha", "alpha")
        self.vmix = gst.element_factory_make("videomixer", "videomix")
        self.vmix.set_property("background", 1)
        self.add(self.incsp, self.alpha, self.vmix, self.outcsp)
        gst.element_link_many(self.incsp, self.alpha, self.vmix, self.outcsp)

        self._sinkpad = gst.GhostPad("sink", self.incsp.get_pad("sink"))
        self._sinkpad.set_active(True)
        self._srcpad = gst.GhostPad("src", self.outcsp.get_pad("src"))
        self._srcpad.set_active(True)

        self.add_pad(self._sinkpad)
        self.add_pad(self._srcpad)

        self.startposition = position
        self.duration = duration
        self.fadefromblack = fadefromblack

        self.alphacontrol = gst.Controller(self.alpha, "alpha")
        self.alphacontrol.set_interpolation_mode("alpha", gst.INTERPOLATE_LINEAR)

        self._resetControllerValues()

    def setStartPosition(self, position):
        """ Set the position at which the fade should start """
        if position == self.startposition:
            return
        self.startposition = position
        self._resetControllerValues()

    def setDuration(self, duration):
        """ Set the duration (in ns) of the fade """
        if self.duration == duration:
            return
        self.duration = duration
        self._resetControllerValues()

    def setFadeFromBlack(self, fromblack):
        """ Set which directio we should use.
        True : From Black
        False : To Black
        """
        if self.fadefromblack == fromblack:
            return
        self.fadefromblack = fromblack
        self._resetControllerValues()

    def _resetControllerValues(self):
        self.alphacontrol.unset_all("alpha")
        if self.fadefromblack:
            start = 0.0
            stop = 1.0
        else:
            start = 1.0
            stop = 0.0
        self.alphacontrol.set("alpha",
                              self.startposition,
                              start)
        self.alphacontrol.set("alpha",
                              self.startposition + self.duration,
                              stop)

gobject.type_register(VideoFade)
