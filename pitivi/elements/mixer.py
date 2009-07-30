# PiTiVi , Non-linear video editor
#
#       pitivi/elements/mixer.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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
Audio and Video mixers
"""

import gobject
import gst

from pitivi.elements.audioclipper import ClipperProbe

class SmartAdderBin(gst.Bin):

    __gstdetails__ = (
        "Smart Adder",
        "Generic/Audio",
        "Convenience wrapper around adder, accepts anything",
        "Edward Hervey <bilboed@bilboed.com>"
        )

    __gsttemplates__ = (
        gst.PadTemplate("src", gst.PAD_SRC, gst.PAD_ALWAYS,
                        gst.Caps("audio/x-raw-int;audio/x-raw-float")),
        gst.PadTemplate("sink_%u", gst.PAD_SINK, gst.PAD_REQUEST,
                        gst.Caps("audio/x-raw-int;audio/x-raw-float"))

        )

    def __init__(self):
        gst.Bin.__init__(self)
        self.adder = gst.element_factory_make("adder", "real-adder")
        # FIXME : USE THE PROJECT SETTINGS FOR THESE CAPS !
        csp = gst.element_factory_make("capsfilter")
        csp.props.caps = gst.Caps("audio/x-raw-int,depth=32,width=32,signed=True,rate=44100,channels=2,endianness=1234")
        self.add(self.adder, csp)
        self.adder.link(csp)
        srcpad = gst.GhostPad("src", csp.get_pad("src"))
        srcpad.set_active(True)
        self.add_pad(srcpad)
        self.pad_count = 0
        self.inputs = {} # key:pad_name, value:(sinkpad, aconv, aresample, adderpad)

    def do_request_new_pad(self, template, name=None):
        self.debug("template:%r, name:%r" % (template, name))
        if name == None:
            name = "sink_%u" % self.pad_count
        if name in self.inputs.keys():
            return None

        aconv = gst.element_factory_make("audioconvert", "aconv-%d" % self.pad_count)
        aresample = gst.element_factory_make("audioresample", "aresample-%d" % self.pad_count)
        self.add(aconv, aresample)
        aconv.sync_state_with_parent()
        aresample.sync_state_with_parent()
        aconv.link(aresample)
        adderpad = self.adder.get_request_pad("sink%d")
        aresample.get_pad("src").link(adderpad)

        clipper = ClipperProbe(aresample.get_pad("src"))

        pad = gst.GhostPad(name, aconv.get_pad("sink"))
        pad.set_active(True)
        self.add_pad(pad)
        self.inputs[name] = (pad, aconv, aresample, clipper, adderpad)
        self.pad_count += 1
        return pad

    def do_release_pad(self, pad):
        self.debug("pad:%r" % pad)
        name = pad.get_name()
        if name in self.inputs.keys():
            sinkpad, aconv, aresample, clipper, adderpad = self.inputs.pop(name)
            # we deactivate this pad to make sure that if ever the streaming
            # thread was doing something downstream (like getting caps) it will
            # return with GST_FLOW_WRONG_STATE and not GST_FLOW_NOT_LINKED (which is
            # a fatal return flow).
            aresample.get_pad("src").set_active(False)

            self.adder.release_request_pad(adderpad)
            aresample.get_pad("src").unlink(adderpad)
            aconv.unlink(aresample)
            aconv.set_state(gst.STATE_NULL)
            aresample.set_state(gst.STATE_NULL)
            self.remove(aconv, aresample)
            self.remove_pad(sinkpad)
        self.debug("done")


gobject.type_register(SmartAdderBin)
gst.element_register(SmartAdderBin, 'smart-adder-bin')
