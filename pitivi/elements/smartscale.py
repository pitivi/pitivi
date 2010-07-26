# PiTiVi , Non-linear video editor
#
#       pitivi/elements/singledecodebin.py
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

"""
Smart video scaler
"""

# Algorithm logic
#
# PAR is the same in videobox (automatic)
# DAR is the same in videoscale (We need to make sure)
#
# The whole idea is to modify the caps between videobox and videoscale so that
# the

import gobject
import gst

class SmartVideoScale(gst.Bin):
    """
    Element to do proper videoscale.
    Keeps Display Aspect Ratio.
    Adds black borders if needed.
    """

    def __init__(self):
        gst.Bin.__init__(self)
        self.videoscale = gst.element_factory_make("videoscale", "smart-videoscale")
        # set the scaling method to bilinear (cleaner)
        # FIXME : we should figure out if better methods are available in the
        # future, or ask the user which method he wants to use
        # FIXME : Instead of having the set_caps() method, use proper caps negotiation
        self.videoscale.props.method = 1
        self.videoscale.props.add_borders = True
        self.capsfilter = gst.element_factory_make("capsfilter", "smart-capsfilter")
        self.add(self.videoscale, self.capsfilter)
        gst.element_link_many(self.videoscale, self.capsfilter)

        self._sinkpad = gst.GhostPad("sink", self.videoscale.get_pad("sink"))
        self._sinkpad.set_active(True)
        self._srcpad = gst.GhostPad("src", self.capsfilter.get_pad("src"))
        self._srcpad.set_active(True)

        self.add_pad(self._sinkpad)
        self.add_pad(self._srcpad)

        self._sinkpad.set_setcaps_function(self._sinkSetCaps)


        # input/output values
        self.capsin = None
        self.widthin = -1
        self.heightin = -1
        self.parin = gst.Fraction(1, 1)
        self.darin = gst.Fraction(1, 1)
        self.capsout = None
        self.widthout = -1
        self.heightout = -1
        self.parout = gst.Fraction(1, 1)
        self.darout = gst.Fraction(1, 1)

    def set_caps(self, caps):
        """ set the outgoing caps, because gst.BaseTransform is full of CRACK ! """
        self.widthout, self.heightout, self.parout, self.darout = self._getValuesFromCaps(caps, True)
        self.caps_copy = gst.Caps(caps)
        del self.caps_copy[0]["format"]
        del self.caps_copy[0]["framerate"]

    def _sinkSetCaps(self, unused_pad, caps):
        self.log("caps:%s" % caps.to_string())
        self.widthin, self.heightin, self.parin, self.darin = self._getValuesFromCaps(caps)
        self._computeAndSetValues()
        return True

    def _srcSetCaps(self, unused_pad, caps):
        self.log("caps:%s" % caps.to_string())
        self.widthout, self.heightout, self.parout, self.darout = self._getValuesFromCaps(caps)
        res = self.capsfilter.get_pad("src").set_caps(caps)
        if res:
            self.capsout = caps
            self._computeAndSetValues()
        return res

    def _sinkpadCapsNotifyCb(self, pad, unused_prop):
        caps = pad.get_negotiated_caps()
        self.log("caps:%r" % caps)
        self.widthin, self.heightin, self.parin, self.darin = self._getValuesFromCaps(caps)
        self.capsin = caps
        self._computeAndSetValues()

    def _srcpadCapsNotifyCb(self, pad, unused_prop):
        caps = pad.get_negotiated_caps()
        self.log("caps:%r" % caps)
        self.widthout, self.heightout, self.parout, self.darout = self._getValuesFromCaps(caps)
        self.capsout = caps
        self._computeAndSetValues()

    def _getValuesFromCaps(self, caps, force=False):
        """
        returns (width, height, par, dar) from given caps.
        If caps are None, or not negotiated, it will return
        (-1, -1, gst.Fraction(1, 1), gst.Fraction(1, 1))
        """
        width = -1
        height = -1
        par = gst.Fraction(1, 1)
        dar = gst.Fraction(1, 1)
        if force or (caps and caps.is_fixed()):
            struc = caps[0]
            if struc.has_field("width"):
                width = struc["width"]
            if struc.has_field("height"):
                height = struc["height"]
            if struc.has_field('pixel-aspect-ratio'):
                par = struc['pixel-aspect-ratio']
            dar = gst.Fraction(width * par.num, height * par.denom)
        return (width, height, par, dar)

    def _computeAndSetValues(self):
        """ Calculate the new values to set on capsfilter. """
        if self.widthout == -1 or self.heightout == -1:
            # FIXME : should we reset videobox/capsfilter properties here ?
            self.error("We don't have output caps, we can't fix values for videoscale")
            return

        # set properties on elements
        self.debug("Settings filter caps %s" % self.caps_copy.to_string())
        self.capsfilter.props.caps = self.caps_copy
        self.debug("done")

gobject.type_register(SmartVideoScale)
