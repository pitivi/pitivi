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

import gobject
import gst

class SmartVideoScale(gst.Bin):

    def __init__(self):
        gst.Bin.__init__(self)
        self.videoscale = gst.element_factory_make("videoscale")
        self.videobox = gst.element_factory_make("videobox")
        self.capsfilter = gst.element_factory_make("capsfilter")
        self.add(self.videoscale, self.capsfilter, self.videobox)
        gst.element_link_many(self.videobox, self.capsfilter, self.videoscale)

        self._sinkPad = gst.GhostPad("sink", self.videobox.get_pad("sink"))
        self._srcPad = gst.GhostPad("src", self.videoscale.get_pad("src"))

        self.add_pad(self._sinkPad)
        self.add_pad(self._srcPad)

        self.videobox.get_pad("sink").connect("notify::caps", self._sinkPadCapsNotifyCb)
        self.videoscale.get_pad("src").connect("notify::caps", self._srcPadCapsNotifyCb)

        # input/output values
        self.widthin = -1
        self.heightin = -1
        self.parin = gst.Fraction(1,1)
        self.widthout = -1
        self.heightout = -1
        self.parout = gst.Fraction(1,1)

    def _sinkPadCapsNotifyCb(self, pad, unused_prop):
        caps = pad.get_negotiated_caps()
        if not caps:
            return
        self.log("caps:%s" % caps.to_string())
        if not caps.is_fixed():
            return
        # store values
        self.widthin = caps[0]["width"]
        self.heightin = caps[0]["height"]
        if caps[0].has_field('pixel-aspect-ratio'):
            self.parin = caps[0]["pixel-aspect-ratio"]
        else:
            self.parin = gst.Fraction(1,1)

    def _srcPadCapsNotifyCb(self, pad, unused_prop):
        caps = pad.get_negotiated_caps()
        if not caps:
            return
        self.log("caps:%s" % caps.to_string())
        if not caps.is_fixed():
            return
        # store values
        self.widthout = caps[0]["width"]
        self.heightout = caps[0]["height"]
        if caps[0].has_field('pixel-aspect-ratio'):
            self.parout = caps[0]['pixel-aspect-ratio']
        else:
            self.parout = gst.Fraction(1,1)

    def _computeAndSetValues(self):
        """ Calculate the new values to set on capsfilter and videobox. """

gobject.type_register(SmartVideoScale)
