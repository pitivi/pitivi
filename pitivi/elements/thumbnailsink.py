# PiTiVi , Non-linear video editor
#
#       pitivi/elements/thumbnailsink.py
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
GdkPixbuf thumbnail sink
"""

import gobject
import gst
import cairo
import array

class CairoSurfaceThumbnailSink(gst.BaseSink):
    """
    GStreamer thumbnailing sink element.

    Can be used in pipelines to generates gtk.gdk.Pixbuf automatically.
    """

    __gsignals__ = {
        "thumbnail" : (gobject.SIGNAL_RUN_LAST,
                       gobject.TYPE_NONE,
                       ( gobject.TYPE_PYOBJECT, gobject.TYPE_UINT64 ))
        }

    __gsttemplates__ = (
        gst.PadTemplate ("sink",
                         gst.PAD_SINK,
                         gst.PAD_ALWAYS,
                         gst.Caps("video/x-raw-rgb,"
                                  "bpp = (int) 32, depth = (int) 32,"
                                  "endianness = (int) BIG_ENDIAN,"
                                  "blue_mask = (int)  0xFF000000, "
                                  "green_mask = (int) 0x00FF0000, "
                                  "red_mask = (int)   0x0000FF00, "
                                  "width = (int) [ 1, max ], "
                                  "height = (int) [ 1, max ], "
                                  "framerate = (fraction) [ 0, max ]"))
        )

    def __init__(self):
        gst.BaseSink.__init__(self)
        self._width = 1
        self._height = 1
        self.set_sync(False)

    def do_set_caps(self, caps):
        self.log("caps %s" % caps.to_string())
        self.log("padcaps %s" % self.get_pad("sink").get_caps().to_string())
        self.width = caps[0]["width"]
        self.height = caps[0]["height"]
        if not caps[0].get_name() == "video/x-raw-rgb":
            return False
        return True

    def do_render(self, buf):
        self.log("buffer %s %d" % (gst.TIME_ARGS(buf.timestamp),
                                   len(buf.data)))
        b = array.array("B")
        b.fromstring(buf)
        pixb = cairo.ImageSurface.create_for_data(b,
            cairo.FORMAT_ARGB32,
            self.width,
            self.height,
            self.width * 4)

        self.emit('thumbnail', pixb, buf.timestamp)
        return gst.FLOW_OK

    def do_preroll(self, buf):
        return self.do_render(buf)

gobject.type_register(CairoSurfaceThumbnailSink)
