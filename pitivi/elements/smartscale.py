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
        self.videobox = gst.element_factory_make("videobox", "smart-videobox")
        self.capsfilter = gst.element_factory_make("capsfilter", "smart-capsfilter")
        self.add(self.videoscale, self.capsfilter, self.videobox)
        gst.element_link_many(self.videoscale, self.capsfilter, self.videobox)

        self._sinkpad = gst.GhostPad("sink", self.videoscale.get_pad("sink"))
        self._sinkpad.set_active(True)
        self._srcpad = gst.GhostPad("src", self.videobox.get_pad("src"))
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

    def _sinkSetCaps(self, unused_pad, caps):
        self.log("caps:%s" % caps.to_string())
        self.widthin, self.heightin, self.parin, self.darin = self._getValuesFromCaps(caps)
        self._computeAndSetValues()
        res = self.videoscale.get_pad("sink").set_caps(caps)
        return res

    def _srcSetCaps(self, unused_pad, caps):
        self.log("caps:%s" % caps.to_string())
        self.widthout, self.heightout, self.parout, self.darout = self._getValuesFromCaps(caps)
        res = self.videobox.get_pad("src").set_caps(caps)
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
            width = struc["width"]
            height = struc["height"]
            if struc.has_field('pixel-aspect-ratio'):
                par = struc['pixel-aspect-ratio']
            dar = gst.Fraction(width * par.num, height * par.denom)
        return (width, height, par, dar)

    def _computeAndSetValues(self):
        """ Calculate the new values to set on capsfilter and videobox. """
        if self.widthin == -1 or self.heightin == -1 or self.widthout == -1 or self.heightout == -1:
            # FIXME : should we reset videobox/capsfilter properties here ?
            self.error("We don't have input and output caps, we can't calculate videobox values")
            return

        self.log("incoming width/height/PAR/DAR : %d/%d/%r/%r" % (self.widthin, self.heightin,
                                                                  self.parin, self.darin))
        self.log("outgoing width/height/PAR/DAR : %d/%d/%r/%r" % (self.widthout, self.heightout,
                                                                  self.parout, self.darout))


        # for core <= 0.10.22 we always set caps != any, see 574805 for the
        # details
        if self.darin == self.darout and gst.version() >= (0, 10, 23):
            self.log("We have same input and output caps, resetting capsfilter and videobox settings")
            # same DAR, set inputcaps on capsfilter, reset videobox values
            caps = gst.caps_new_any()
            left = 0
            right = 0
            top = 0
            bottom = 0
        else:
            par = self.parout
            dar = self.darin
            if float(self.darin) > float(self.darout):
                self.log("incoming DAR is greater that ougoing DAR. Adding top/bottom borders")
                # width, PAR stays the same as output
                # calculate newheight = (PAR * widthout) / DAR
                newheight = (par.num * self.widthout * dar.denom) / (par.denom * dar.num)
                self.log("newheight should be %d" % newheight)
                extra = self.heightout - newheight
                top = extra / 2
                bottom = extra - top # compensate for odd extra
                left = right = 0
                # calculate filter caps
                astr = "width=%d,height=%d" % (self.widthout, newheight)
            else:
                self.log("incoming DAR is smaller than outgoing DAR. Adding left/right borders")
                # height, PAR stays the same as output
                # calculate newwidth = (DAR * heightout) / PAR
                newwidth = (dar.num * self.heightout * par.denom) / (dar.denom * par.num)
                self.log("newwidth should be %d" % newwidth)
                extra = self.widthout - newwidth
                left = extra / 2
                right = extra - left # compensate for odd extra
                top = bottom = 0
                # calculate filter caps
                astr = "width=%d,height=%d" % (newwidth, self.heightout)
            caps = gst.caps_from_string("video/x-raw-yuv,%s;video/x-raw-rgb,%s" % (astr, astr))

        # set properties on elements
        self.debug("About to set left/right/top/bottom : %d/%d/%d/%d" % (-left, -right, -top, -bottom))
        self.videobox.props.left = -left
        self.videobox.props.right = -right
        self.videobox.props.top = -top
        self.videobox.props.bottom = -bottom
        self.debug("Settings filter caps %s" % caps.to_string())
        self.capsfilter.props.caps = caps
        self.debug("done")



gobject.type_register(SmartVideoScale)
