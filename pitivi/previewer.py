#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       previewer.py
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
Utility tools and classes for easy generation of previews
"""

import gobject
import gst
import cairo
import goocanvas
import os
import utils
from configure import get_pixmap_dir
from elements.singledecodebin import SingleDecodeBin
from elements.thumbnailsink import CairoSurfaceThumbnailSink
from elements.arraysink import ArraySink
from signalinterface import Signallable
from ui.zoominterface import Zoomable

(MEDIA_TYPE_NONE,
 MEDIA_TYPE_AUDIO,
 MEDIA_TYPE_VIDEO) = range(3)

class Previewer(object, Signallable):

    __signals__ = {
        "update" : ("timestamp",),
    }

    # TODO: use actual aspect ratio of source
    # TODO: parameterize height, instead of assuming 50 pixels.
    # NOTE: dymamically changing thumbnail height would involve flushing the
    # thumbnail cache.

    __TWIDTH__ = 4.0 / 3.0 * 50

    """
    Handles loading, caching, and drawing preview data for segments of
    timeline object streams. There is one Previewer per ObjectFactory. 
    Preview data is read from an instance of an ObjectFactory's Object, and
    when requested, drawn into a given cairo context. If the requested data is
    not cached, an appropriate filler will be substituted, and an asyncrhonous
    request for the data will be issued. When the data becomes available, the
    update signal is emitted, along with the stream, and time segments. This
    allows the UI to re-draw the affected portion of a thumbnail sequence or
    audio waveform."""

    def __init__(self, factory):
        # queue of timestamps
        self.queue = []

        # true only if we are prerolled
        self._ready = False

        # create pipeline for thumbnail previews
        sbin = SingleDecodeBin(caps=gst.Caps("video/x-raw-rgb;video/x-raw-yuv"),
            uri=factory.name)
        csp = gst.element_factory_make("ffmpegcolorspace")
        sink = CairoSurfaceThumbnailSink()
        scale = gst.element_factory_make("videoscale")
        filter = utils.filter("video/x-raw-rgb,height=(int) 50, width=(int) %d"
            % self.__TWIDTH__)
        self.pipeline = utils.pipeline({
            sbin : csp,
            csp : scale,
            scale : filter,
            filter : sink,
            sink : None
        })
        sink.connect('thumbnail', self._thumbnailCb)
        self.pipeline.set_state(gst.STATE_PAUSED)

        # initialize thumbnail cache
        self.thumbcache = {}

        # create default thumbnail
        path = os.path.join(get_pixmap_dir(), "pitivi-video.png")
        self.default_thumb = cairo.ImageSurface.create_from_png(path)

        #self.samplecache = {}

## public interface

    def render_cairo(self, cr, bounds, element):
        if element.media_type == MEDIA_TYPE_AUDIO:
           # self.__render_waveform(cr, bounds, element)
           pass
        elif element.media_type == MEDIA_TYPE_VIDEO:
            self.__render_thumbseq(cr, bounds, element)

    def __render_waveform(self, cr, bounds, element):
        height = bounds.y2 - bounds.y1
        y1 = bounds.y1 + height / 4
        y2 = (3 * height) / 4
        cr.rectangle(bounds.x1 + 3, y1, bounds.x2 - bounds.x1 - 6, y2)
        cr.stroke()

    def __render_thumbseq(self, cr, bounds, element):
        height = bounds.y2 - bounds.y1
        width = bounds.x2 - bounds.x1
        cr.rectangle(bounds.x1, bounds.y1, width, height)
        cr.clip()

        tdur = Zoomable.pixelToNs(self.__TWIDTH__)
        x = Zoomable.nsToPixel(element.start)
        x1 = bounds.x1

        # i = offset of first thumbnail
        i = (-(Zoomable.nsToPixel(element.media_start) + x1 - x) %
            self.__TWIDTH__) + x1
        j = element.media_start - (element.media_start % tdur)
        cr.set_source_surface(self.thumb_for_time(j), i - self.__TWIDTH__, 0)
        cr.rectangle(x1, 0, i - x1 - 2, 50)
        cr.fill()
        while i < bounds.x2:
            cr.set_source_surface(self.thumb_for_time(j), i, 0)
            cr.rectangle(i, 0, self.__TWIDTH__, 50)
            i += self.__TWIDTH__
            j += tdur
            cr.fill()

    def thumb_for_time(self, time):
        if time in self.thumbcache:
            return self.thumbcache[time]
        self.makeThumbnail(time)
        return self.default_thumb

## thumbmailsequence generator

    def _thumbnailCb(self, unused_thsink, pixbuf, timestamp):
        #self.log("pixbuf:%s, timestamp:%s" % (pixbuf, gst.TIME_ARGS(timestamp)))
        if not self._ready:
            # we know we're prerolled when we get the initial thumbnail
            self._ready = True

        # TODO: store a pattern instead of a pixbuf
        # TODO: implement actual caching strategy, instead of slowly consuming all
        # available memory
        self.thumbcache[timestamp] = pixbuf
        self.emit("update", MEDIA_TYPE_VIDEO)
        if timestamp in self.queue:
            self.queue.remove(timestamp)

        if self.queue:
            # still some more thumbnails to process
            gobject.idle_add(self._makeThumbnail, self.queue.pop(0))

    def makeThumbnail(self, timestamp):
        """ Queue a thumbnail request for the given timestamp """
        #self.log( "timestamp %s" % gst.TIME_ARGS(timestamp))
        assert timestamp > 0
        # TODO: need some sort of timeout so the queue doesn't fill up if the
        # thumbnail never arrives.
        if timestamp not in self.queue:
            if self.queue or not self._ready:
                self.queue.append(timestamp)
            else:
                self.queue.append(timestamp)
                self._makeThumbnail(timestamp)

    def _makeThumbnail(self, timestamp):
        if not self._ready:
            return
        gst.log("timestamp : %s" % gst.TIME_ARGS(timestamp))
        self.pipeline.seek(1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
                  gst.SEEK_TYPE_SET, timestamp,
                  gst.SEEK_TYPE_NONE, -1)
        return False

 ## Waveform peaks generator 

    def bus_eos(self, bus, message):	
        """
        Handler for the GStreamer End Of Stream message. Currently
        used when the file is loading and is being rendered. This
        function is called at the end of the file loading process and
        finalises the rendering.

        @param bus: GStreamer bus sending the message.
        @param message: GStreamer message.

        @return: False therefore stops the signal propagation. *CHECK*
        """
        if message.type == gst.MESSAGE_EOS:

            # We're done with the bin so release it
            self.stopGenerateWaveform(True)

            # Signal to interested objects that we've changed
            self.emit("audiopeaks-eos")

            return False

    def bus_error(self, bus, message):
        """
        Handler for when things go completely wrong with GStreamer.

        @param bus: GStreamer bus sending the message.
        @param message: GStreamer message.
        """
        error, debug = message.parse_error()

        print "Event bus error:", str(error), str(debug)
        self.stopGenerateWaveform(False)

    isLoading = False      # True if the event is loading level data
    loadingLength = 0      # The length of the file in seconds as its being rendered
    loadingPipeline = None # The Gstreamer pipeline used to load the waveform
    loadingSink = None

    @property
    def levels(self):
        if self.loadingSink:
            return self.loadingSink.samples
        return []

    @property
    def waveformduration(self):
        if self.loadingSink:
            return self.loadingSink.duration
        return 0

    def generateWaveform(self):
        """
        Renders the level information for the GUI.
        """
        #TODO use core uri functions to convert uri to filename instead of [7:]
        sbin = SingleDecodeBin(caps=gst.Caps("audio/x-raw-float;"
            "audio/x-raw-int"), uri=self.name)
        conv = gst.element_factory_make("audioconvert")
        self.loadingSink = ArraySink()
        self.loadingPipeline = pipeline({ 
            sbin : conv, conv : self.loadingSink,
            self.loadingSink : None})

        self.bus = self.loadingPipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", self.bus_eos)
        self.bus.connect("message::error", self.bus_error)

        self.isLoading = True
        self.emit("audiopeaks-loading")

        self.loadingPipeline.set_state(gst.STATE_PLAYING)

    def stopGenerateWaveform(self, finishedLoading=True):
        """
        Stops the internal pipeline that loads the waveform from this event's file.

        Parameters:
            finishedLoading -- True if the event has finished loading the waveform,
                    False if the loading is being cancelled.
        """

        if self.bus:
            self.bus.remove_signal_watch()
            self.bus = None
        if self.loadingPipeline:
            self.loadingPipeline.set_state(gst.STATE_NULL)
            self.isLoading = not finishedLoading
            self.loadingPipeline = None
            self.loadingLength = 0

    def nsToSample(self, time):
        return (time * 3000) / gst.SECOND

    def __plotWaveform(self, cr, levels):
        # figure out our scaling
        hscale = self.height / 2
        scale = self.width / len(levels)

        # upper portion of waveform
        points = ((x * scale, hscale - (y * hscale)) for x, y in enumerate(levels))
        self.__plot_points(cr, 0, hscale, points)

    def __plot_points(self, cr, x0, y0, points):
        cr.move_to(x0, y0)
        for x, y in points:
            cr.line_to(x, y)


