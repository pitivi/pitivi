# PiTiVi , Non-linear video editor
#
#       pitivi/elements/arraysink.py
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
Stores audio samples in an array for plotting waveforms
"""

import gobject
gobject.threads_init()
import gst
import gtk
import array

class ArraySink(gst.BaseSink):

    """
    Stores audio samples in a numeric array of floats.
    """
    caps = gst.Caps(
        "audio/x-raw-float, width=(int) 32, "
        "endianness = (int) LITTLE_ENDIAN, "
        "channels = (int) 1, "
        "rate = (int) [1, 96000]"
    )

    __gsttemplates__ = (
        gst.PadTemplate(
            "sink",
            gst.PAD_SINK,
            gst.PAD_ALWAYS,
            caps
       ),
    )

    def __init__(self):
        gst.BaseSink.__init__(self)
        self.props.sync = False
        self.rate = 0
        self.duration = 0L
        self.reset()

    def reset(self):
        self.samples = array.array('f')

    def do_set_caps(self, caps):
        if not caps[0].get_name() == "audio/x-raw-float":
            return False
        self.rate = caps[0]["rate"]
        return True

    def do_render(self, buf):
        self.samples.fromstring(buf)
        self.duration += buf.duration
        return gst.FLOW_OK

    def do_preroll(self, buf):
        return self.do_render(buf)

gobject.type_register(ArraySink)
