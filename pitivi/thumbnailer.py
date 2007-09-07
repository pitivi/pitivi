#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       thumbnailer.py
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
Utility tools and classes for easy thumbnailing
"""

import gobject
import gst
from elements.singledecodebin import SingleDecodeBin
from elements.thumbnailsink import PixbufThumbnailSink

class Thumbnailer(gst.Pipeline):

    __gsignals__ = {
        "thumbnail" : (gobject.SIGNAL_RUN_LAST,
                       gobject.TYPE_NONE,
                       ( gobject.TYPE_PYOBJECT, gobject.TYPE_UINT64 ))
        }


    def __init__(self, uri):
        gst.Pipeline.__init__(self)
        # queue of timestamps
        self.queue = []

        # true only if we are prerolled
        self._ready = False

        self.log("uri : %s" % uri)

        self.uri = uri

        self.sbin = SingleDecodeBin(caps=gst.Caps("video/x-raw-rgb;video/x-raw-yuv"),
                                    uri=self.uri)
        self.csp = gst.element_factory_make("ffmpegcolorspace")
        self.sink = PixbufThumbnailSink()
        self.sink.connect('thumbnail', self._thumbnailCb)

        self.add(self.sbin, self.csp, self.sink)
        self.csp.link(self.sink)

        self.sbin.connect('pad-added', self._sbinPadAddedCb)
        self.set_state(gst.STATE_PAUSED)

    def _sbinPadAddedCb(self, sbin, pad):
        self.log("pad : %s" % pad)
        pad.link(self.csp.get_pad("sink"))

    def _thumbnailCb(self, thsink, pixbuf, timestamp):
        self.log("pixbuf:%s, timestamp:%s" % (pixbuf, gst.TIME_ARGS(timestamp)))
        if not self._ready:
            # we know we're prerolled when we get the initial thumbnail
            self._ready = True

        self.emit('thumbnail', pixbuf, timestamp)

        if timestamp in self.queue:
            self.queue.remove(timestamp)

        if self.queue:
            # still some more thumbnails to process
            gobject.idle_add(self._makeThumbnail, self.queue.pop(0))

    def makeThumbnail(self, timestamp):
        """ Queue a thumbnail request for the given timestamp """
        self.log("timestamp %s" % gst.TIME_ARGS(timestamp))
        if self.queue or not self._ready:
            self.queue.append(timestamp)
        else:
            self.queue.append(timestamp)
            self._makeThumbnail(timestamp)

    def _makeThumbnail(self, timestamp):
        if not self._ready:
            return
        gst.log("timestamp : %s" % gst.TIME_ARGS(timestamp))
        self.seek(1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
                  gst.SEEK_TYPE_SET, timestamp,
                  gst.SEEK_TYPE_NONE, -1)
        return False
