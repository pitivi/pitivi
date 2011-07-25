# PiTiVi , Non-linear video editor
#
#       pitivi/elements/extractionsink.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2011, Benjamin M. Schwartz <bens@alum.mit.edu>
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Extract audio samples without storing the whole waveform in memory
"""

import array
import gobject
gobject.threads_init()
import gst
from pitivi.utils import native_endianness, call_false


class ExtractionSink(gst.BaseSink):

    """
    Passes audio data directly to a provided L{Extractee}
    """

    caps = gst.Caps(
        "audio/x-raw-float, width=(int) 32, "
        "endianness = (int) %s, "
        "channels = (int) 1,"
        "rate = (int) [1, 96000]"
        % native_endianness)

    __gsttemplates__ = (
        gst.PadTemplate(
            "sink",
            gst.PAD_SINK,
            gst.PAD_ALWAYS,
            caps),)

    def __init__(self):
        gst.BaseSink.__init__(self)
        self.props.sync = False
        self.rate = 0
        self.channels = 0
        self.reset()
        self._cb = None

    def set_extractee(self, extractee):
        self.extractee = extractee

    def set_stopped_cb(self, cb):
        self._cb = cb

    def reset(self):
        self.samples = array.array('f')
        self.extractee = None

    def do_set_caps(self, caps):
        if not caps[0].get_name() == "audio/x-raw-float":
            return False
        self.rate = caps[0]["rate"]
        self.channels = caps[0]["channels"]
        return True

    def do_render(self, buf):
        if self.extractee is not None:
            self.extractee.receive(array.array('f', buf.data))
        return gst.FLOW_OK

    def do_preroll(self, buf):
        return gst.FLOW_OK

    def do_event(self, ev):
        self.info("Got event of type %s" % ev.type)
        if ev.type == gst.EVENT_EOS:
            if self._cb:
                gobject.idle_add(call_false, self._cb)
        return gst.FLOW_OK

gobject.type_register(ExtractionSink)
