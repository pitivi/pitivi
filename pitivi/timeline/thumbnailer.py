# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/thumbnailer.py
#
# Copyright (c) 2006, Edward Hervey <bilboed@bilboed.com>
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
Handle the creation, caching and display of thumbnails in the timeline.
"""

import ges
import gst
import os
import cairo
import gobject
import goocanvas
import collections
import array
import sqlite3

from gettext import gettext as _

import pitivi.settings as settings
from pitivi.settings import GlobalSettings
from pitivi.configure import get_pixmap_dir

import pitivi.utils as utils

from pitivi.utils.misc import big_to_cairo_alpha_mask, big_to_cairo_red_mask, big_to_cairo_green_mask, big_to_cairo_blue_mask
from pitivi.utils.receiver import receiver, handler
from pitivi.utils.timeline import Zoomable
from pitivi.utils.signal import Signallable
from pitivi.utils.loggable import Loggable

from pitivi.dialogs.prefs import PreferencesDialog

GlobalSettings.addConfigSection("thumbnailing")
GlobalSettings.addConfigOption("thumbnailSpacingHint",
    section="thumbnailing",
    key="spacing-hint",
    default=5,
    notify=True)

GlobalSettings.addConfigOption("thumbnailPeriod",
    section="thumbnailing",
    key="thumbnail-period",
    default=gst.SECOND,
    notify=True)

PreferencesDialog.addNumericPreference("thumbnailSpacingHint",
    section=_("Appearance"),
    label=_("Thumbnail gap"),
    lower=0,
    description=_("The spacing between thumbnails, in pixels"))

PreferencesDialog.addChoicePreference("thumbnailPeriod",
    section=_("Performance"),
    label=_("Thumbnail every"),
    choices=(
        # Note that we cannot use "%s second" or ngettext, because fractions
        # are not supported by ngettext and their plurality is ambiguous
        # in many languages.
        # See http://www.gnu.org/software/hello/manual/gettext/Plural-forms.html
        (_("1/100 second"), gst.SECOND / 100),
        (_("1/10 second"), gst.SECOND / 10),
        (_("1/4 second"), gst.SECOND / 4),
        (_("1/2 second"), gst.SECOND / 2),
        (_("1 second"), gst.SECOND),
        (_("5 seconds"), 5 * gst.SECOND),
        (_("10 seconds"), 10 * gst.SECOND),
        (_("minute"), 60 * gst.SECOND)),
    description=_("The interval, in seconds, between thumbnails."))

# this default works out to a maximum of ~ 1.78 MiB per factory, assuming:
# 4:3 aspect ratio
# 4 bytes per pixel
# 50 pixel height
GlobalSettings.addConfigOption("thumbnailCacheSize",
    section="thumbnailing",
    key="cache-size",
    default=250)

# the maximum number of thumbnails to enqueue at a given time. setting this to
# a larger value will increase latency after large operations, such as zooming
GlobalSettings.addConfigOption("thumbnailMaxRequests",
    section="thumbnailing",
    key="max-requests",
    default=10)

GlobalSettings.addConfigOption('showThumbnails',
    section='user-interface',
    key='show-thumbnails',
    default=True,
    notify=True)

PreferencesDialog.addTogglePreference('showThumbnails',
    section=_("Performance"),
    label=_("Enable video thumbnails"),
    description=_("Show thumbnails on video clips"))

GlobalSettings.addConfigOption('showWaveforms',
    section='user-interface',
    key='show-waveforms',
    default=True,
    notify=True)

PreferencesDialog.addTogglePreference('showWaveforms',
    section=_("Performance"),
    label=_("Enable audio waveforms"),
    description=_("Show waveforms on audio clips"))


class ThumbnailCache(object):

    """Caches thumbnails by key using LRU policy, implemented with heapq.

    Uses a two stage caching mechanism. A limited number of elements are
    held in memory, the rest is being cached on disk using an sqlite db."""

    def __init__(self, uri, size=100):
        object.__init__(self)
        self.hash = utils.misc.hash_file(gst.uri_get_location(uri))
        self.cache = {}
        self.queue = collections.deque()
        dbfile = os.path.join(settings.get_dir(os.path.join(settings.xdg_cache_home(), "thumbs")), self.hash)
        self.conn = sqlite3.connect(dbfile)
        self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS Thumbs (Time INTEGER NOT NULL PRIMARY KEY,\
            Data BLOB NOT NULL, Width INTEGER NOT NULL, Height INTEGER NOT NULL)")
        self.size = size

    def __contains__(self, key):
        # check if item is present in memory
        if key in self.cache:
            return True
        # check if item is present in on disk cache
        self.cur.execute("SELECT Time FROM Thumbs WHERE Time = ?", (key,))
        if self.cur.fetchone():
            return True
        return False

    def __getitem__(self, key):
        # check if item is present in memory
        if key in self.cache:
            # I guess this is why LRU is considered expensive
            self.queue.remove(key)
            self.queue.append(key)
            return self.cache[key]
        # check if item is present in on disk cache
        # if so load it into memory
        self.cur.execute("SELECT * FROM Thumbs WHERE Time = ?", (key,))
        row = self.cur.fetchone()
        if row:
            if len(self.cache) > self.size:
                self.ejectLRU()
            self.cache[key] = cairo.ImageSurface.create_for_data(row[1], cairo.FORMAT_RGB24, row[2], row[3], 4 * row[2])
            self.queue.append(key)
            return self.cache[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.cache[key] = value
        self.queue.append(key)
        blob = sqlite3.Binary(bytearray(value.get_data()))
        #Replace if the key already existed
        self.cur.execute("DELETE FROM Thumbs WHERE  time=?", (key,))
        self.cur.execute("INSERT INTO Thumbs VALUES (?,?,?,?)", (key, blob, value.get_width(), value.get_height()))
        self.conn.commit()
        if len(self.cache) > self.size:
            self.ejectLRU()

    def ejectLRU(self):
        key = self.queue.popleft()
        del self.cache[key]

# Previewer                      -- abstract base class with public interface for UI
# |_DefaultPreviewer             -- draws a default thumbnail for UI
# |_LivePreviewer                -- draws a continuously updated preview
# | |_LiveAudioPreviwer          -- a continously updating level meter
# | |_LiveVideoPreviewer         -- a continously updating video monitor
# |_RandomAccessPreviewer        -- asynchronous fetching and caching
#   |_RandomAccessAudioPreviewer -- audio-specific pipeline and rendering code
#   |_RandomAccessVideoPreviewer -- video-specific pipeline and rendering
#     |_StillImagePreviewer      -- only uses one segment


previewers = {}


def get_preview_for_object(instance, trackobject):
    uri = trackobject.props.uri
    track_type = trackobject.get_track().props.track_type
    key = uri, track_type
    if not key in previewers:
        # TODO: handle non-random access factories
        # TODO: handle non-source factories
        # Note that we switch on the track_type, but we hash on the uri
        # itself.
        if track_type == ges.TRACK_TYPE_AUDIO:
            # FIXME: RandomAccessAudioPreviewer doesn't work yet
            # previewers[key] = RandomAccessAudioPreviewer(instance, uri)
            previewers[key] = DefaultPreviewer(instance, uri)
        elif track_type == ges.TRACK_TYPE_VIDEO:
            if trackobject.get_timeline_object().is_image():
                previewers[key] = StillImagePreviewer(instance, uri)
            else:
                previewers[key] = RandomAccessVideoPreviewer(instance, uri)
        else:
            previewers[key] = DefaultPreviewer(instance, uri)
    return previewers[key]


class Previewer(Signallable, Loggable):
    """
    Utility for easy generation of previews
    """

    __signals__ = {
        "update": ("segment",),
    }

    # TODO: parameterize height, instead of assuming self.theight pixels.
    # NOTE: dymamically changing thumbnail height would involve flushing the
    # thumbnail cache.

    __DEFAULT_THUMB__ = "processing-clip.png"

    aspect = 4.0 / 3.0

    def __init__(self, instance, uri):
        Loggable.__init__(self)
        # create default thumbnail
        path = os.path.join(get_pixmap_dir(), self.__DEFAULT_THUMB__)
        self.default_thumb = cairo.ImageSurface.create_from_png(path)
        self._connectSettings(instance.settings)

    def render_cairo(self, cr, bounds, element, hscroll_pos, y1):
        """Render a preview of element onto a cairo context within the current
        bounds, which may or may not be the entire object and which may or may
        not intersect the visible portion of the object"""
        raise NotImplementedError

    def _connectSettings(self, settings):
        self._settings = settings


class DefaultPreviewer(Previewer):

    def render_cairo(self, cr, bounds, element, hscroll_pos, y1):
        # TODO: draw a single thumbnail
        pass


class RandomAccessPreviewer(Previewer):
    """ Handles loading, caching, and drawing preview data for segments of
    random-access streams.  There is one Previewer per track_type per
    TrackObject.  Preview data is read from a uri, and when requested, drawn
    into a given cairo context. If the requested data is not cached, an
    appropriate filler will be substituted, and an asyncrhonous request
    for the data will be issued. When the data becomes available, the update
    signal is emitted, along with the stream, and time segments. This allows
    the UI to re-draw the affected portion of a thumbnail sequence or audio waveform."""

    def __init__(self, instance, uri):
        self._view = True
        self.uri = uri
        Previewer.__init__(self, instance, uri)
        self._queue = []

        bin = gst.element_factory_make("playbin2")
        bin.props.uri = uri

        # assume 50 pixel height
        self.theight = 50
        self.waiting_timestamp = None

        self._pipelineInit(uri, bin)

    def _pipelineInit(self, uri, bin):
        """Create the pipeline for the preview process. Subclasses should
        override this method and create a pipeline, connecting to callbacks to
        the appropriate signals, and prerolling the pipeline if necessary."""
        raise NotImplementedError

## public interface

    def render_cairo(self, cr, bounds, element, hscroll_pos, y1):
        if not self._view:
            return
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
        x1 = bounds.x1
        sof = Zoomable.nsToPixel(element.get_start() - element.get_inpoint()) +\
            hscroll_pos

        # i = left edge of thumbnail to be drawn. We start with x1 and
        # subtract the distance to the nearest leftward rectangle.
        # Justification of the following:
        #                i = sof + k * twidth
        #                i = x1 - delta
        # sof + k * twidth = x1 - delta
        #           i * tw = (x1 - sof) - delta
        #    <=>     delta = x1 - sof (mod twidth).
        # Fortunately for us, % works on floats in python.

        i = x1 - ((x1 - sof) % (self.twidth + self._spacing()))

        # j = timestamp *within the element* of thumbnail to be drawn. we want
        # timestamps to be numerically stable, but in practice this seems to
        # give good enough results. It might be possible to improve this
        # further, which would result in fewer thumbnails needing to be
        # generated.
        j = Zoomable.pixelToNs(i - sof)
        istep = self.twidth + self._spacing()
        jstep = self.tdur + Zoomable.pixelToNs(self.spacing)

        while i < bounds.x2:
            self._thumbForTime(cr, j, i, y1)
            cr.rectangle(i - 1, y1, self.twidth + 2, self.theight)
            i += istep
            j += jstep
            cr.fill()

    def _spacing(self):
        return self.spacing

    def _segmentForTime(self, time):
        """Return the segment for the specified time stamp. For some stream
        types, the segment duration will depend on the current zoom ratio,
        while others may only care about the timestamp. The value returned
        here will be used as the key which identifies the thumbnail in the
        thumbnail cache"""

        raise NotImplementedError

    def _thumbForTime(self, cr, time, x, y):
        segment = self._segment_for_time(time)
        if segment in self._cache:
            surface = self._cache[segment]
        else:
            self._requestThumbnail(segment)
            surface = self.default_thumb
        cr.set_source_surface(surface, x, y)

    def _finishThumbnail(self, surface, segment):
        """Notifies the preview object that the a new thumbnail is ready to be
        cached. This should be called by subclasses when they have finished
        processing the thumbnail for the current segment. This function should
        always be called from the main thread of the application."""
        waiting = self.waiting_timestamp
        self.waiting_timestamp = None

        if segment != waiting:
            segment = waiting

        self._cache[segment] = surface
        self.emit("update", segment)

        if segment in self._queue:
            self._queue.remove(segment)
        self._nextThumbnail()
        return False

    def _nextThumbnail(self):
        """Notifies the preview object that the pipeline is ready to process
        the next thumbnail in the queue. This should always be called from the
        main application thread."""
        if self._queue:
            if not self._startThumbnail(self._queue[0]):
                self._queue.pop(0)
                self._nextThumbnail()
        return False

    def _requestThumbnail(self, segment):
        """Queue a thumbnail request for the given segment"""

        if (segment not in self._queue) and (len(self._queue) <=
            self.max_requests):
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
        playback are asynchronous, you may have to call _nextThumbnail() in a
        message handler or other callback."""
        self.waiting_timestamp = segment

    def _connectSettings(self, settings):
        Previewer._connectSettings(self, settings)
        self.spacing = settings.thumbnailSpacingHint
        self._cache = ThumbnailCache(uri=self.uri, size=settings.thumbnailCacheSize)
        self.max_requests = settings.thumbnailMaxRequests
        settings.connect("thumbnailSpacingHintChanged",
            self._thumbnailSpacingHintChanged)

    def _thumbnailSpacingHintChanged(self, settings):
        self.spacing = settings.thumbnailSpacingHint
        self.emit("update", None)


class RandomAccessVideoPreviewer(RandomAccessPreviewer):

    @property
    def twidth(self):
        return int(self.aspect * self.theight)

    @property
    def tdur(self):
        return Zoomable.pixelToNs(self.twidth)

    def __init__(self, instance, uri):
        RandomAccessPreviewer.__init__(self, instance, uri)
        self.tstep = Zoomable.pixelToNsAt(self.twidth, Zoomable.max_zoom)

        if self.framerate.num:
            frame_duration = (gst.SECOND * self.framerate.denom) / self.framerate.num
            self.tstep = max(frame_duration, self.tstep)

    def bus_handler(self, unused_bus, message):
        # set the scaling method of the videoscale element to Lanczos
        element = message.src
        if isinstance(element, gst.Element):
            factory = element.get_factory()
            if factory and "GstVideoScale" == factory.get_element_type().name:
                element.props.method = 3
        return gst.BUS_PASS

    def _pipelineInit(self, factory, sbin):
        """
        Create the pipeline.

        It has the form "sbin ! thumbnailsink" where thumbnailsink
        is a Bin made out of "capsfilter ! cairosink"
        """
        self.videopipeline = sbin
        self.videopipeline.props.flags = 1  # Only render video
        self.videopipeline.get_bus().connect("message", self.bus_handler)

        # Use a capsfilter to scale the video to the desired size
        # (fixed height and par, variable width)
        caps = gst.Caps("video/x-raw, height=(int)%d, pixel-aspect-ratio=(fraction)1/1" %
            self.theight)
        capsfilter = gst.element_factory_make("capsfilter", "thumbnailcapsfilter")
        capsfilter.props.caps = caps
        cairosink = CairoSurfaceThumbnailSink()
        cairosink.connect("thumbnail", self._thumbnailCb)

        # Set up the thumbnailsink and add a sink pad
        thumbnailsink = gst.Bin("thumbnailsink")
        thumbnailsink.add(capsfilter)
        thumbnailsink.add(cairosink)
        capsfilter.link(cairosink)
        sinkpad = gst.GhostPad("sink", thumbnailsink.find_unlinked_pad(gst.PAD_SINK))
        thumbnailsink.add_pad(sinkpad)

        # Connect sbin and thumbnailsink
        self.videopipeline.props.video_sink = thumbnailsink

        self.videopipeline.set_state(gst.STATE_PAUSED)
        # Wait for the pipeline to be prerolled so we can check the width
        # that the thumbnails will have and set the aspect ratio accordingly
        # as well as getting the framerate of the video:
        if gst.STATE_CHANGE_SUCCESS == self.videopipeline.get_state(gst.CLOCK_TIME_NONE)[0]:
            neg_caps = sinkpad.get_negotiated_caps()[0]
            self.aspect = neg_caps["width"] / float(self.theight)
            self.framerate = neg_caps["framerate"]
        else:
            # the pipeline couldn't be prerolled so we can't determine the
            # correct values. Set sane defaults (this should never happen)
            self.warning("Couldn't preroll the pipeline")
            self.aspect = 16.0 / 9
            self.framerate = gst.Fraction(24, 1)

    def _segment_for_time(self, time):
        # quantize thumbnail timestamps to maximum granularity
        return utils.misc.quantize(time, self.tperiod)

    def _thumbnailCb(self, unused_thsink, pixbuf, timestamp):
        gobject.idle_add(self._finishThumbnail, pixbuf, timestamp)

    def _startThumbnail(self, timestamp):
        RandomAccessPreviewer._startThumbnail(self, timestamp)
        return self.videopipeline.seek(1.0,
            gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
            gst.SEEK_TYPE_SET, timestamp,
            gst.SEEK_TYPE_NONE, -1)

    def _connectSettings(self, settings):
        RandomAccessPreviewer._connectSettings(self, settings)
        settings.connect("showThumbnailsChanged", self._showThumbsChanged)
        settings.connect("thumbnailPeriodChanged",
            self._thumbnailPeriodChanged)
        self._view = settings.showThumbnails
        self.tperiod = settings.thumbnailPeriod

    def _showThumbsChanged(self, settings):
        self._view = settings.showThumbnails
        self.emit("update", None)

    def _thumbnailPeriodChanged(self, settings):
        self.tperiod = settings.thumbnailPeriod
        self.emit("update", None)


class StillImagePreviewer(RandomAccessVideoPreviewer):
    def _thumbForTime(self, cr, time, x, y):
        return RandomAccessVideoPreviewer._thumbForTime(self, cr, 0L, x, y)


class RandomAccessAudioPreviewer(RandomAccessPreviewer):

    def __init__(self, instance, uri):
        self.tdur = 30 * gst.SECOND
        self.base_width = int(Zoomable.max_zoom)
        RandomAccessPreviewer.__init__(self, instance, uri)

    @property
    def twidth(self):
        return Zoomable.nsToPixel(self.tdur)

    def _pipelineInit(self, factory, sbin):
        self.spacing = 0

        self.audioSink = ArraySink()
        conv = gst.element_factory_make("audioconvert")
        self.audioPipeline = utils.pipeline({
            sbin: conv,
            conv: self.audioSink,
            self.audioSink: None})
        bus = self.audioPipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::segment-done", self._busMessageSegmentDoneCb)
        bus.connect("message::error", self._busMessageErrorCb)

        self._audio_cur = None
        self.audioPipeline.set_state(gst.STATE_PAUSED)

    def _spacing(self):
        return 0

    def _segment_for_time(self, time):
        # for audio files, we need to know the duration the segment spans
        return time - (time % self.tdur), self.tdur

    def _busMessageSegmentDoneCb(self, bus, message):
        self.debug("segment done")
        self._finishWaveform()

    def _busMessageErrorCb(self, bus, message):
        error, debug = message.parse_error()
        self.error("Event bus error: %s: %s", str(error), str(debug))

        return gst.BUS_PASS

    def _startThumbnail(self, (timestamp, duration)):
        RandomAccessPreviewer._startThumbnail(self, (timestamp, duration))
        self._audio_cur = timestamp, duration
        res = self.audioPipeline.seek(1.0,
            gst.FORMAT_TIME,
            gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE | gst.SEEK_FLAG_SEGMENT,
            gst.SEEK_TYPE_SET, timestamp,
            gst.SEEK_TYPE_SET, timestamp + duration)
        if not res:
            self.warning("seek failed %s", timestamp)
        self.audioPipeline.set_state(gst.STATE_PLAYING)

        return res

    def _finishWaveform(self):
        surfaces = []
        surface = cairo.ImageSurface(cairo.FORMAT_A8,
            self.base_width, self.theight)
        cr = cairo.Context(surface)
        self._plotWaveform(cr, self.base_width)
        self.audioSink.reset()

        for width in [25, 100, 200]:
            scaled = cairo.ImageSurface(cairo.FORMAT_A8,
               width, self.theight)
            cr = cairo.Context(scaled)
            matrix = cairo.Matrix()
            matrix.scale(self.base_width / width, 1.0)
            cr.set_source_surface(surface)
            cr.get_source().set_matrix(matrix)
            cr.rectangle(0, 0, width, self.theight)
            cr.fill()
            surfaces.append(scaled)
        surfaces.append(surface)
        gobject.idle_add(self._finishThumbnail, surfaces, self._audio_cur)

    def _plotWaveform(self, cr, base_width):
        # clear background
        cr.set_source_rgba(1, 1, 1, 0.0)
        cr.rectangle(0, 0, base_width, self.theight)
        cr.fill()

        samples = self.audioSink.samples

        if not samples:
            return

        # find the samples-per-pixel ratio
        spp = len(samples) / base_width
        if spp == 0:
            spp = 1
        channels = self.audioSink.channels
        stride = spp * channels
        hscale = self.theight / (2 * channels)

        # plot points from min to max over a given hunk
        chan = 0
        y = hscale
        while chan < channels:
            i = chan
            x = 0
            while i < len(samples):
                slice = samples[i:i + stride:channels]
                min_ = min(slice)
                max_ = max(slice)
                cr.move_to(x, y - (min_ * hscale))
                cr.line_to(x, y - (max_ * hscale))
                i += spp
                x += 1
            y += 2 * hscale
            chan += 1

        # Draw!
        cr.set_source_rgba(0, 0, 0, 1.0)
        cr.stroke()

    def _thumbForTime(self, cr, time, x, y):
        segment = self._segment_for_time(time)
        twidth = self.twidth
        if segment in self._cache:
            surfaces = self._cache[segment]
            if twidth > 200:
                surface = surfaces[3]
                base_width = self.base_width
            elif twidth <= 200:
                surface = surfaces[2]
                base_width = 200
            elif twidth <= 100:
                surface = surfaces[1]
                base_width = 100
            elif twidth <= 25:
                surface = surfaces[0]
                base_width = 25
            x_scale = float(base_width) / self.twidth
            cr.set_source_surface(surface)
            matrix = cairo.Matrix()
            matrix.scale(x_scale, 1.0)
            matrix.translate(-x, -y)
            cr.get_source().set_matrix(matrix)
        else:
            self._requestThumbnail(segment)
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.0)

    def _connectSettings(self, settings):
        RandomAccessPreviewer._connectSettings(self, settings)
        self._view = settings.showWaveforms
        settings.connect("showWaveformsChanged", self._showWaveformsChanged)

    def _showWaveformsChanged(self, settings):
        self._view = settings.showWaveforms
        self.emit("update", None)


class CairoSurfaceThumbnailSink(gst.BaseSink):
    """
    GStreamer thumbnailing sink element.

    Can be used in pipelines to generates gtk.gdk.Pixbuf automatically.
    """

    __gsignals__ = {
        "thumbnail": (gobject.SIGNAL_RUN_LAST,
                      gobject.TYPE_NONE,
                      (gobject.TYPE_PYOBJECT, gobject.TYPE_UINT64))
        }

    __gsttemplates__ = (
        gst.PadTemplate.new("sink",
                         gst.PAD_SINK,
                         gst.PAD_ALWAYS,
                         gst.caps_from_string("video/x-raw,"
                                  "bpp = (int) 32, depth = (int) 32,"
                                  "endianness = (int) BIG_ENDIAN,"
                                  "alpha_mask = (int) %i, "
                                  "red_mask = (int)   %i, "
                                  "green_mask = (int) %i, "
                                  "blue_mask = (int)  %i, "
                                  "width = (int) [ 1, max ], "
                                  "height = (int) [ 1, max ], "
                                  "framerate = (fraction) [ 0, max ]"
                                  % (big_to_cairo_alpha_mask,
                                     big_to_cairo_red_mask,
                                     big_to_cairo_green_mask,
                                     big_to_cairo_blue_mask)))
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
        if not caps[0].get_name() == "video/x-raw":
            return False
        return True

    def do_render(self, buf):
        self.log("buffer %s %d" % (gst.TIME_ARGS(buf.timestamp),
                                   len(buf.data)))
        b = array.array("b")
        b.fromstring(buf)
        pixb = cairo.ImageSurface.create_for_data(b,
            # We don't use FORMAT_ARGB32 because Cairo uses premultiplied
            # alpha, and gstreamer does not.  Discarding the alpha channel
            # is not ideal, but the alternative would be to compute the
            # conversion in python (slow!).
            cairo.FORMAT_RGB24,
            self.width,
            self.height,
            self.width * 4)

        self.emit("thumbnail", pixb, buf.timestamp)
        return gst.FLOW_OK

    def do_preroll(self, buf):
        return self.do_render(buf)

gobject.type_register(CairoSurfaceThumbnailSink)


def between(a, b, c):
    return (a <= b) and (b <= c)


def intersect(b1, b2):
    return goocanvas.Bounds(max(b1.x1, b2.x1), max(b1.y1, b2.y1),
        min(b1.x2, b2.x2), min(b1.y2, b2.y2))


class Preview(goocanvas.ItemSimple, goocanvas.Item, Zoomable):

    """
    Custom canvas item for timeline object previews. This code is just a thin
    canvas-item wrapper which ensures that the preview is updated appropriately.
    The actual drawing is done by the pitivi.previewer.Previewer class.
    """

    __gtype_name__ = 'Preview'

    def __init__(self, instance, element, height=46, **kwargs):
        super(Preview, self).__init__(**kwargs)
        Zoomable.__init__(self)
        self.app = instance
        self.height = float(height)
        self.element = element
        self.props.pointer_events = False
        # ghetto hack
        self.hadj = instance.gui.timeline_ui.hadj

## properties

    def _get_height(self):
        return self._height

    def _set_height(self, value):
        self._height = value
        self.changed(True)
    height = gobject.property(_get_height, _set_height, type=float)

## element callbacks

    def _set_element(self):
        self.previewer = get_preview_for_object(self.app,
            self.element)
    element = receiver(setter=_set_element)

    @handler(element, "notify::in-point")
    @handler(element, "notify::duration")
    def _media_props_changed(self, obj, unused_start_duration):
        self.changed(True)

## previewer callbacks

    previewer = receiver()

    @handler(previewer, "update")
    def _update_preview(self, previewer, segment):
        # if segment is none we are not just drawing a new thumbnail, so we
        # should update bounds
        if segment == None:
            self.changed(True)
        else:
            self.changed(False)

## Zoomable interface overries

    def zoomChanged(self):
        self.changed(True)

## goocanvas item methods

    def do_simple_update(self, cr):
        cr.identity_matrix()
        if issubclass(self.previewer.__class__, RandomAccessPreviewer):
            border_width = self.previewer._spacing()
            self.bounds = goocanvas.Bounds(border_width, 4,
            max(0, Zoomable.nsToPixel(self.element.get_duration()) -
                border_width), self.height)

    def do_simple_paint(self, cr, bounds):
        x1 = -self.hadj.get_value()
        cr.identity_matrix()
        if issubclass(self.previewer.__class__, RandomAccessPreviewer):
            self.previewer.render_cairo(cr, intersect(self.bounds, bounds),
            self.element, x1, self.bounds.y1)

    def do_simple_is_item_at(self, x, y, cr, pointer_event):
        return (between(0, x, self.nsToPixel(self.element.get_duration())) and
            between(0, y, self.height))
