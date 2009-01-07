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

# TODO: refactor this mess into hierarchy of classes along these lines, to aid
# with refactoring effort. Individual factories can name the preview class
# they want to use for each stream they output, which leaves the door open for
# plugins which define new kinds of object factories.  

# Previewer                      -- abstract base class with public interface for UI
# |_DefaultPreviewer             -- draws a default thumbnail for UI
# |_LivePreviewer                -- draws a continuously updated preview
# | |_LiveAudioPreviwer          -- a continously updating level meter
# | |_LiveVideoPreviewer         -- a continously updating video monitor
# |_RandomAccessPreviewer        -- asynchronous fetching and caching
#   |_RandomAccessAudioPreviewer -- audio-specific pipeline and rendering code
#   |_RandomAccessVideoPreviewer -- video-specific caching and rendering

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

        # create default thumbnail
        path = os.path.join(get_pixmap_dir(), "pitivi-video.png")
        self.default_thumb = cairo.ImageSurface.create_from_png(path) 

        if factory.is_video:
            self.__init_video(factory)
        if factory.is_audio:
            self.__init_audio(factory)

## public interface

    def render_cairo(self, cr, bounds, element):
        if element.media_type == MEDIA_TYPE_AUDIO:
           self.__render_waveform(cr, bounds, element)
        elif element.media_type == MEDIA_TYPE_VIDEO:
           self.__render_thumbseq(cr, bounds, element)

## thumbmailsequence generator

    def __init_video(self, factory):
        self.__video_ready = False
        sbin = factory.makeVideoBin() 
        csp = gst.element_factory_make("ffmpegcolorspace")
        sink = CairoSurfaceThumbnailSink()
        scale = gst.element_factory_make("videoscale")
        filter = utils.filter("video/x-raw-rgb,height=(int) 50, width=(int) %d"
            % self.__TWIDTH__)
        self.videopipeline = utils.pipeline({
            sbin : csp,
            csp : scale,
            scale : filter,
            filter : sink,
            sink : None
        })
        sink.connect('thumbnail', self._thumbnailCb)
        self.thumbcache = {}
        self.videoqueue = []
        self.videopipeline.set_state(gst.STATE_PAUSED)

    def __render_thumbseq(self, cr, bounds, element):
        # The idea is to conceptually divide the clip into a sequence of
        # rectangles beginning at the start of the file, and
        # pixelsToNs(twidth) nanoseconds long. The thumbnail within the
        # rectangle is the frame produced from the timestamp of the
        # rectangle's left edge. This sequence of rectangles is anchored in
        # the timeline at the start of the file in timeline space. We speed
        # things up by only drawing the rectangles which intersect the given
        # bounds.
        # FIXME: how would we handle timestretch?

        height = bounds.y2 - bounds.y1
        width = bounds.x2 - bounds.x1

        # we actually draw the rectangles just to the left of the clip's in
        # point and just to the right of the clip's out-point, so we need to
        # mask off the actual bounds.
        cr.rectangle(bounds.x1, bounds.y1, width, height)
        cr.clip()

        # tdur = duration in ns of thumbnail
        tdur = Zoomable.pixelToNs(self.__TWIDTH__)
        x1 = bounds.x1; y1 = bounds.y1
        # start of file in pixel coordinates
        sof = Zoomable.nsToPixel(element.start - element.media_start)

        # i = left edge of thumbnail to be drawn. We start with x1 and
        # subtract the distance to the nearest leftward rectangle. v it's worth
        # noting that % is defined for floats in python, and works for our
        # purposes. justification of the following: 
        # since i = sof + k * twidth, and i = x1 - delta,
        # sof + k * twidth = x1 - delta => i * tw = (x1 - sof) - delta
        # therefore delta = x1 - sof (mod twidth)
        i = x1 - ((x1 - sof) % self.__TWIDTH__)

        # j = timestamp *within the element* of thumbnail to be drawn. we want
        # timestamps to be numerically stable, but in practice this seems to
        # give good enough results. It might be possible to improve this
        # further, which would result in fewer thumbnails needing to be
        # generated.
        j = Zoomable.pixelToNs(i - sof)

        while i < bounds.x2:
            cr.set_source_surface(self.video_thumb_for_time(j), i, y1)
            cr.rectangle(i, y1, self.__TWIDTH__, height)
            i += self.__TWIDTH__
            j += tdur
            cr.fill()

    def video_thumb_for_time(self, time):
        if time in self.thumbcache:
            return self.thumbcache[time]
        self.makeThumbnail(time)
        return self.default_thumb

    def _thumbnailCb(self, unused_thsink, pixbuf, timestamp):
        #self.log("pixbuf:%s, timestamp:%s" % (pixbuf, gst.TIME_ARGS(timestamp)))
        if not self.__video_ready:
            # we know we're prerolled when we get the initial thumbnail
            self.__video_ready = True

        # TODO: implement actual caching strategy, instead of slowly consuming all
        # available memory
        self.thumbcache[timestamp] = pixbuf
        self.emit("update", MEDIA_TYPE_VIDEO)
        if timestamp in self.videoqueue:
            self.videoqueue.remove(timestamp)

        if self.videoqueue:
            gobject.idle_add(self._makeThumbnail, self.videoqueue.pop(0))

    def makeThumbnail(self, timestamp):
        """ Queue a thumbnail request for the given timestamp """
        #self.log( "timestamp %s" % gst.TIME_ARGS(timestamp))
        assert timestamp >= 0
        # TODO: need some sort of timeout so the queue doesn't fill up if the
        # thumbnail never arrives.
        if timestamp not in self.videoqueue:
            if self.videoqueue or not self.__video_ready:
                self.videoqueue.append(timestamp)
            else:
                self.videoqueue.append(timestamp)
                self._makeThumbnail(timestamp)

    def _makeThumbnail(self, timestamp):
        if not self.__video_ready:
            return
        gst.log("timestamp : %s" % gst.TIME_ARGS(timestamp))
        self.videopipeline.seek(1.0, 
            gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
            gst.SEEK_TYPE_SET, timestamp,
            gst.SEEK_TYPE_NONE, -1)
        return False

 ## Waveform peaks generator 

    def __init_audio(self, factory):
        self.__audio_ready = False
        sbin = factory.makeAudioBin()
        conv = gst.element_factory_make("audioconvert")
        self.audioSink = ArraySink()
        self.audioPipeline = utils.pipeline({ 
            sbin : conv, 
            conv : self.audioSink,
            self.audioSink : None})
        self.bus = self.audioPipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.__bus_message)
        self.__audio_cur = None
        self.wavecache = {}
        self.audioqueue = []
        self.audioPipeline.set_state(gst.STATE_PAUSED)

    def __render_waveform(self, cr, bounds, element):
        height = bounds.y2 - bounds.y1
        width = bounds.x2 - bounds.x1
        cr.rectangle(bounds.x1, bounds.y1, width, height)
        cr.clip()

        tdur = Zoomable.pixelToNs(self.__TWIDTH__)
        x1 = bounds.x1; y1 = bounds.y1
        sof = Zoomable.nsToPixel(element.start - element.media_start)

        i = x1 - ((x1 - sof) % self.__TWIDTH__)
        j = Zoomable.pixelToNs(i - sof)

        while i < bounds.x2:
            cr.set_source_surface(self.audio_thumb_for_time_duration(j, tdur),
                i, y1)
            cr.rectangle(i, y1, self.__TWIDTH__, height)
            i += self.__TWIDTH__
            j += tdur
            cr.fill()

    def audio_thumb_for_time_duration(self, time, duration):
        if (time, duration) in self.wavecache:
            return self.wavecache[(time, duration)]
        self.__requestWaveform(time, duration)
        return self.default_thumb

    def __bus_message(self, bus, message):	
        if message.type == gst.MESSAGE_SEGMENT_DONE:
            self.__finishWaveform()

        elif message.type == gst.MESSAGE_STATE_CHANGED:
            self.__audio_ready = True

        # true only if we are prerolled
        elif message.type == gst.MESSAGE_ERROR:
            error, debug = message.parse_error()
            print "Event bus error:", str(error), str(debug)

    def __requestWaveform(self, timestamp, duration):
        """
        Queue a waveform request for the given timestamp and duration.
        """
        assert (timestamp >= 0) and (duration > 0)
        # TODO: need some sort of timeout so the queue doesn't fill up if the
        # thumbnail never arrives.
        if (timestamp, duration) not in self.audioqueue:
            if self.audioqueue or not self.__audio_ready:
                self.audioqueue.append((timestamp, duration))
            else:
                self.audioqueue.append((timestamp, duration))
                self.__makeWaveform((timestamp, duration))

    def __makeWaveform(self, (timestamp, duration)):
        if not self.__audio_ready:
            return
        # TODO: read up on segment seeks, which will do what we want as far as
        # playing over jsut a portion of a file.
        # 02:22 < bilboed-pi> so, preroll, wait for confirmed state change to PAUSED, 
        # send seek (flushing, start, stop), set to PLAYING
        # 02:22 < twi_> morning
        # 02:22 < bilboed-pi> you'll receive EOS when the pipeline
        # has reached the end 
        # position
        self.__audio_cur = timestamp, duration
        self.audioPipeline.seek(1.0, 
            gst.FORMAT_TIME, 
            gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE | gst.SEEK_FLAG_SEGMENT,
            gst.SEEK_TYPE_SET, timestamp,
            gst.SEEK_TYPE_SET, timestamp + duration)
        self.audioPipeline.set_state(gst.STATE_PLAYING)
        return False

    def __finishWaveform(self):
        surface = cairo.ImageSurface(cairo.FORMAT_A8, int(self.__TWIDTH__), 50)
        cr = cairo.Context(surface)
        self.__plotWaveform(cr, self.audioSink.samples)
        self.audioSink.reset()
        self.wavecache[self.__audio_cur] = surface
        surface.write_to_png("test.png")

        self.emit("update", MEDIA_TYPE_AUDIO)
        self.audioqueue.pop(0)

        if self.audioqueue:
            gobject.idle_add(self.__makeWaveform, self.audioqueue[0])

    def nsToSample(self, time):
        return (time * 3000) / gst.SECOND

    def __plotWaveform(self, cr, levels):
        hscale = 25
        if not levels:
            cr.move_to(0, hscale)
            cr.line_to(self.__TWIDTH__, hscale)
            cr.stroke()
            return
        scale = self.__TWIDTH__ / len(levels)
        cr.set_source_rgba(1, 1, 1, 0.0)
        cr.rectangle(0, 0, self.__TWIDTH__, 50)
        cr.fill()
        cr.set_source_rgba(0, 0, 0, 1.0)
        points = ((x * scale, hscale - (y * hscale)) for x, y in enumerate(levels))
        self.__plot_points(cr, 0, hscale, points)
        cr.stroke()

    def __plot_points(self, cr, x0, y0, points):
        cr.move_to(x0, y0)
        for x, y in points:
            cr.line_to(x, y)


