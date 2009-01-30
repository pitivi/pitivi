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
import stream

(MEDIA_TYPE_NONE,
 MEDIA_TYPE_AUDIO,
 MEDIA_TYPE_VIDEO) = range(3)

# Previewer                      -- abstract base class with public interface for UI
# |_DefaultPreviewer             -- draws a default thumbnail for UI
# |_LivePreviewer                -- draws a continuously updated preview
# | |_LiveAudioPreviwer          -- a continously updating level meter
# | |_LiveVideoPreviewer         -- a continously updating video monitor
# |_RandomAccessPreviewer        -- asynchronous fetching and caching
#   |_RandomAccessAudioPreviewer -- audio-specific pipeline and rendering code
#   |_RandomAccessVideoPreviewer -- video-specific pipeline and rendering

previewers = {}

def get_preview_for_object(trackobject):
    factory = trackobject.factory
    stream_ = trackobject.stream
    stream_type = type(stream_)
    key = factory, stream_
    if not key in previewers:
        # TODO: handle still images
        # TODO: handle non-random access factories
        # TODO: handle non-source factories
        # note that we switch on the stream_type, but we hash on the stream
        # itself. 
        if stream_type == stream.AudioStream:
            previewers[key] = RandomAccessAudioPreviewer(factory, stream_)
        elif stream_type == stream.VideoStream:
            previewers[key] = RandomAccessVideoPreviewer(factory, stream_)
        else:
            previewers[key] = DefaultPreviewer(factory, stream_)
    return previewers[key]

class Previewer(object, Signallable):

    __signals__ = {
        "update" : ("segment",),
    }

    # TODO: parameterize height, instead of assuming self.theight pixels.
    # NOTE: dymamically changing thumbnail height would involve flushing the
    # thumbnail cache.

    __DEFAULT_THUMB__ = "pitivi-video.png"

    def __init__(self, factory, stream_):
        # create default thumbnail
        path = os.path.join(get_pixmap_dir(), self.__DEFAULT_THUMB__)
        self.default_thumb = cairo.ImageSurface.create_from_png(path) 

    def render_cairo(self, cr, bounds, element, y1):
        """Render a preview of element onto a cairo context within the current
        bounds, which may or may not be the entire object and which may or may
        not intersect the visible portion of the object"""
        raise NotImplementedError

class DefaultPreviewer(Previewer):

    def render_cairo(self, cr, bounds, element, y1):
        # TODO: draw a single thumbnail
        pass

class RandomAccessPreviewer(Previewer):

    """ Handles loading, caching, and drawing preview data for segments of
    random-access streams.  There is one Previewer per stream per
    ObjectFactory.  Preview data is read from an instance of an
    ObjectFactory's Object, and when requested, drawn into a given cairo
    context. If the requested data is not cached, an appropriate filler will
    be substituted, and an asyncrhonous request for the data will be issued.
    When the data becomes available, the update signal is emitted, along with
    the stream, and time segments. This allows the UI to re-draw the affected
    portion of a thumbnail sequence or audio waveform."""

    def __init__(self, factory, stream_):
        Previewer.__init__(self, factory, stream_)
        self._queue = []
        self._cache = {}

        # FIXME:
        # why doesn't this work?
        # bin = factory.makeBin(stream_)
        uri = factory.uri
        caps = stream_.caps
        bin = SingleDecodeBin(uri=uri, caps=caps)

        # assume 4:3 default aspect ratio, 50 pixel height
        self.theight = 50
        self.aspect = 4.0 / 3.0
        self.twidth = int(self.aspect * self.theight)

        self._pipelineInit(factory, bin)

    def _pipelineInit(self, factory, bin):
        """Create the pipeline for the preview process. Subclasses should
        override this method and create a pipeline, connecting to callbacks to
        the appropriate signals, and prerolling the pipeline if necessary."""
        raise NotImplementedError

## public interface

    def render_cairo(self, cr, bounds, element, y1):
        # The idea is to conceptually divide the clip into a sequence of
        # rectangles beginning at the start of the file, and
        # pixelsToNs(twidth) nanoseconds long. The thumbnail within the
        # rectangle is the frame produced from the timestamp corresponding to
        # rectangle's left edge. We speed things up by only drawing the
        # rectangles which intersect the given bounds.  FIXME: how would we
        # handle timestretch?
        height = bounds.y2 - bounds.y1
        width = bounds.x2 - bounds.x1

        # we actually draw the rectangles just to the left of the clip's in
        # point and just to the right of the clip's out-point, so we need to
        # mask off the actual bounds.
        cr.rectangle(bounds.x1, bounds.y1, width, height)
        cr.clip()

        # tdur = duration in ns of thumbnail
        # sof  = start of file in pixel coordinates
        tdur = Zoomable.pixelToNs(self.twidth)
        x1 = bounds.x1;
        sof = Zoomable.nsToPixel(element.start - element.in_point)

        # i = left edge of thumbnail to be drawn. We start with x1 and
        # subtract the distance to the nearest leftward rectangle.
        # Justification of the following: 
        #                i = sof + k * twidth
        #                i = x1 - delta
        # sof + k * twidth = x1 - delta 
        #           i * tw = (x1 - sof) - delta
        #    <=>     delta = x1 - sof (mod twidth).
        # Fortunately for us, % works on floats in python. 

        i = x1 - ((x1 - sof) % self.twidth)

        # j = timestamp *within the element* of thumbnail to be drawn. we want
        # timestamps to be numerically stable, but in practice this seems to
        # give good enough results. It might be possible to improve this
        # further, which would result in fewer thumbnails needing to be
        # generated.
        j = Zoomable.pixelToNs(i - sof)

        while i < bounds.x2:
            cr.set_source_surface(self._thumbForTime(j), i, y1)
            cr.rectangle(i - 1, y1, self.twidth + 2, self.theight)
            i += self.twidth
            j += tdur
            cr.fill()

    def _segmentForTime(self, time):
        """Return the segment for the specified time stamp. For some stream
        types, the segment duration will depend on the current zoom ratio,
        while others may only care about the timestamp. The value returned
        here will be used as the key which identifies the thumbnail in the
        thumbnail cache""" 
        
        raise NotImplementedError

    def _thumbForTime(self, time):
        segment = self._segment_for_time(time)
        if segment in self._cache:
            return self._cache[segment]
        self._requestThumbnail(segment)
        return self.default_thumb

    def _finishThumbnail(self, surface, segment):
        """Notifies the preview object that the a new thumbnail is ready to be
        cached. This should be called by subclasses when they have finished
        processing the thumbnail for the current segment. This function should
        always be called from the main thread of the application."""

        self._cache[segment] = surface 
        self.emit("update", segment)
        self._nextThumbnail()

        if segment in self._queue:
            self._queue.remove(segment)
        self._nextThumbnail()
        return False

    def _nextThumbnail(self):
        """Notifies the preview object that the pipeline is ready to process
        the next thumbnail in the queue. This should always be called from the
        main application thread."""
        print "next thumbnail"
        if self._queue:
            self._startThumbnail(self._queue.pop(0))
        return False

    def _requestThumbnail(self, segment):
        """Queue a thumbnail request for the given segment"""

        # TODO: need some sort of timeout so the queue doesn't fill up if the
        # thumbnail never arrives.

        if segment not in self._queue:
            if self._queue:
                self._queue.append(segment)
            else:
                self._queue.append(segment)
                self._nextThumbnail()

    def _startThumbnail(self, segment):
        """Start processing segment. Subclasses should override
        this method to perform whatever action on the pipeline is necessary.
        Typically this will be a flushing seek(). When the
        current segment has finished processing, subclasses should call
        _nextThumbnail() with the resulting cairo surface. Since seeking and
        playback are asyncrhonous, you may have to call _nextThumbnail() in a
        message handler or other callback.""" 
    
        raise NotImplementedError

class RandomAccessVideoPreviewer(RandomAccessPreviewer):

    def __init__(self, factory, stream_):
        RandomAccessPreviewer.__init__(self, factory, stream_)
        # use aspect ratio from stream
        self.aspect = stream_.width / stream_.height

    def _pipelineInit(self, factory, sbin):
        csp = gst.element_factory_make("ffmpegcolorspace")
        sink = CairoSurfaceThumbnailSink()
        scale = gst.element_factory_make("videoscale")
        caps = ("video/x-raw-rgb,height=(int) %d,width=(int) %d" % 
            (self.theight, self.twidth + 2))
        filter = utils.filter(caps)
        self.videopipeline = utils.pipeline({
            sbin : csp,
            csp : scale,
            scale : filter,
            filter : sink,
            sink : None
        })
        sink.connect('thumbnail', self._thumbnailCb)
        self.videopipeline.set_state(gst.STATE_PAUSED)

    def _segment_for_time(self, time):
        # for video thumbnails, the duration doesn't matter
        return time

    def _thumbnailCb(self, unused_thsink, pixbuf, timestamp):
        gobject.idle_add(self._finishThumbnail, pixbuf, timestamp)

    def _startThumbnail(self, timestamp):
        gst.log("timestamp : %s" % gst.TIME_ARGS(timestamp))
        self.videopipeline.seek(1.0, 
            gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
            gst.SEEK_TYPE_SET, timestamp,
            gst.SEEK_TYPE_NONE, -1)

class RandomAccessAudioPreviewer(RandomAccessPreviewer):

    def _pipelineInit(self, factory, sbin):
        self.audioSink = ArraySink()
        conv = gst.element_factory_make("audioconvert")
        self.audioPipeline = utils.pipeline({ 
            sbin : conv, 
            conv : self.audioSink,
            self.audioSink : None})
        self.bus = self.audioPipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.__bus_message)
        self.__audio_cur = None
        self.audioPipeline.set_state(gst.STATE_PAUSED)

    def _segment_for_time(self, time):
        # for audio files, we need to know the duration the segment spans
        return time, Zoomable.pixelToNs(self.twidth)

    def __bus_message(self, bus, message):	
        if message.type == gst.MESSAGE_SEGMENT_DONE:
            self.__finishWaveform()

        elif message.type == gst.MESSAGE_ERROR:
            error, debug = message.parse_error()
            print "Event bus error:", str(error), str(debug)

    def _startThumbnail(self, (timestamp, duration)):
        self.__audio_cur = timestamp, duration
        self.audioPipeline.seek(1.0, 
            gst.FORMAT_TIME, 
            gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE | gst.SEEK_FLAG_SEGMENT,
            gst.SEEK_TYPE_SET, timestamp,
            gst.SEEK_TYPE_SET, timestamp + duration)
        self.audioPipeline.set_state(gst.STATE_PLAYING)

    def __finishWaveform(self):
        surface = cairo.ImageSurface(cairo.FORMAT_A8, 
            int(self.twidth) + 2, self.theight)
        cr = cairo.Context(surface)
        self.__plotWaveform(cr, self.audioSink.samples)
        self.audioSink.reset()
        self._finishThumbnail(surface, self.__audio_cur)

    def __plotWaveform(self, cr, levels):
        hscale = 25
        if not levels:
            cr.move_to(0, hscale)
            cr.line_to(self.twidth, hscale)
            cr.stroke()
            return
        scale = float(self.twidth) / len(levels)
        cr.set_source_rgba(1, 1, 1, 0.0)
        cr.rectangle(0, 0, self.twidth, self.theight)
        cr.fill()
        cr.set_source_rgba(0, 0, 0, 1.0)
        points = ((x * scale, hscale - (y * hscale)) for x, y in enumerate(levels))
        self.__plot_points(cr, 0, hscale, points)
        cr.stroke()

    def __plot_points(self, cr, x0, y0, points):
        cr.move_to(x0, y0)
        for x, y in points:
            cr.line_to(x, y)

