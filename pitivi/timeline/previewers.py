# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/previewers
#
# Copyright (c) 2013, Daniel Thul <daniel.thul@gmail.com>
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

from datetime import datetime, timedelta
from gi.repository import Clutter, Gst, GLib, GdkPixbuf, Cogl, GES
from random import randrange
import cairo
import numpy
import os
import pickle
import sqlite3

# Our C module optimizing waveforms rendering
import renderer

from pitivi.settings import get_dir, xdg_cache_home
from pitivi.utils.signal import Signallable
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import binary_search, filename_from_uri, quantize, quote_uri, hash_file, format_ns
from pitivi.utils.system import CPUUsageTracker
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import CONTROL_WIDTH
from pitivi.utils.ui import EXPANDED_SIZE


WAVEFORMS_CPU_USAGE = 30

# A little lower as it's more fluctuating
THUMBNAILS_CPU_USAGE = 20

INTERVAL = 500000  # For the waveform update interval.
BORDER_WIDTH = 3  # For the timeline elements
MARGIN = 500  # For the waveforms, ensures we always have a little extra surface when scrolling while playing.

"""
Convention throughout this file:
Every GES element which name could be mistaken with a UI element
is prefixed with a little b, example : bTimeline
"""


class PreviewGeneratorManager():
    """
    Manage the execution of PreviewGenerators
    """
    def __init__(self):
        self._cpipeline = {
            GES.TrackType.AUDIO: None,
            GES.TrackType.VIDEO: None
        }
        self._pipelines = {
            GES.TrackType.AUDIO: [],
            GES.TrackType.VIDEO: []
        }

    def addPipeline(self, pipeline):
        track_type = pipeline.track_type

        if pipeline in self._pipelines[track_type] or \
                pipeline is self._cpipeline[track_type]:
            return

        if not self._pipelines[track_type] and self._cpipeline[track_type] is None:
            self._setPipeline(pipeline)
        else:
            self._pipelines[track_type].insert(0, pipeline)

    def _setPipeline(self, pipeline):
        self._cpipeline[pipeline.track_type] = pipeline
        PreviewGenerator.connect(pipeline, "done", self._nextPipeline)
        pipeline.startGeneration()

    def _nextPipeline(self, controlled):
        track_type = controlled.track_type
        if self._cpipeline[track_type]:
            PreviewGenerator.disconnect_by_function(self._cpipeline[track_type],
                                                    self._nextPipeline)
            self._cpipeline[track_type] = None

        if self._pipelines[track_type]:
            self._setPipeline(self._pipelines[track_type].pop())


class PreviewGenerator(Signallable):
    """
    Interface to be implemented by classes that generate previews
    It is need to implement it so PreviewGeneratorManager can manage
    those classes
    """

    # We only want one instance of PreviewGeneratorManager to be used for
    # all the generators.
    __manager = PreviewGeneratorManager()

    __signals__ = {
        "done": [],
        "error": [],
    }

    def __init__(self, track_type):
        """
        @param track_type : GES.TrackType.*
        """
        Signallable.__init__(self)
        self.track_type = track_type

    def startGeneration(self):
        raise NotImplemented

    def stopGeneration(self):
        raise NotImplemented

    def becomeControlled(self):
        """
        Let the PreviewGeneratorManager control our execution
        """
        PreviewGenerator.__manager.addPipeline(self)


class VideoPreviewer(Clutter.ScrollActor, PreviewGenerator, Zoomable, Loggable):
    def __init__(self, bElement, timeline):
        """
        @param bElement : the backend GES.TrackElement
        @param track : the track to which the bElement belongs
        @param timeline : the containing graphic timeline.
        """
        Zoomable.__init__(self)
        Clutter.ScrollActor.__init__(self)
        Loggable.__init__(self)
        PreviewGenerator.__init__(self, GES.TrackType.VIDEO)

        # Variables related to the timeline objects
        self.timeline = timeline
        self.bElement = bElement
        self.uri = quote_uri(bElement.props.uri)  # Guard against malformed URIs
        self.duration = bElement.props.duration

        # Variables related to thumbnailing
        self.wishlist = []
        self._callback_id = None
        self._thumb_cb_id = None
        self._allAnimated = False
        self._running = False
        # We should have one thumbnail per thumb_period.
        # TODO: get this from the user settings
        self.thumb_period = long(0.5 * Gst.SECOND)
        self.thumb_margin = BORDER_WIDTH
        self.thumb_height = EXPANDED_SIZE - 2 * self.thumb_margin
        self.thumb_width = None  # will be set by self._setupPipeline()

        # Maps (quantized) times to Thumbnail objects
        self.thumbs = {}
        self.thumb_cache = get_cache_for_uri(self.uri)

        self.cpu_usage_tracker = CPUUsageTracker()
        self.interval = 500  # Every 0.5 second, reevaluate the situation

        # Connect signals and fire things up
        self.timeline.connect("scrolled", self._scrollCb)
        self.bElement.connect("notify::duration", self._durationChangedCb)
        self.bElement.connect("notify::in-point", self._inpointChangedCb)
        self.bElement.connect("notify::start", self._startChangedCb)

        self.pipeline = None
        self.becomeControlled()

    # Internal API

    def _update(self, unused_msg_source=None):
        if self._callback_id:
            GLib.source_remove(self._callback_id)

        if self.thumb_width:
            self._addVisibleThumbnails()
            if self.wishlist:
                self.becomeControlled()

    def _setupPipeline(self):
        """
        Create the pipeline.

        It has the form "playbin ! thumbnailsink" where thumbnailsink
        is a Bin made out of "videorate ! capsfilter ! gdkpixbufsink"
        """
        # TODO: don't hardcode framerate
        self.pipeline = Gst.parse_launch(
            "uridecodebin uri={uri} name=decode ! "
            "videoconvert ! "
            "videorate ! "
            "videoscale method=lanczos ! "
            "capsfilter caps=video/x-raw,format=(string)RGBA,height=(int){height},"
            "pixel-aspect-ratio=(fraction)1/1,framerate=2/1 ! "
            "gdkpixbufsink name=gdkpixbufsink".format(uri=self.uri, height=self.thumb_height))

        # get the gdkpixbufsink and the sinkpad
        self.gdkpixbufsink = self.pipeline.get_by_name("gdkpixbufsink")
        sinkpad = self.gdkpixbufsink.get_static_pad("sink")

        self.pipeline.set_state(Gst.State.PAUSED)

        # Wait for the pipeline to be prerolled so we can check the width
        # that the thumbnails will have and set the aspect ratio accordingly
        # as well as getting the framerate of the video:
        change_return = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        if Gst.StateChangeReturn.SUCCESS == change_return[0]:
            neg_caps = sinkpad.get_current_caps()[0]
            self.thumb_width = neg_caps["width"]
        else:
            # the pipeline couldn't be prerolled so we can't determine the
            # correct values. Set sane defaults (this should never happen)
            self.warning("Couldn't preroll the pipeline")
            # assume 16:9 aspect ratio
            self.thumb_width = 16 * self.thumb_height / 9

        decode = self.pipeline.get_by_name("decode")
        decode.connect("autoplug-select", self._autoplugSelectCb)

        # pop all messages from the bus so we won't be flooded with messages
        # from the prerolling phase
        while self.pipeline.get_bus().pop():
            continue
        # add a message handler that listens for the created pixbufs
        self.pipeline.get_bus().add_signal_watch()
        self.pipeline.get_bus().connect("message", self.bus_message_handler)

    def _checkCPU(self):
        """
        Check the CPU usage and adjust the time interval (+10 or -10%) at
        which the next thumbnail will be generated. Even then, it will only
        happen when the gobject loop is idle to avoid blocking the UI.
        """
        usage_percent = self.cpu_usage_tracker.usage()
        if usage_percent < THUMBNAILS_CPU_USAGE:
            self.interval *= 0.9
            self.log('Thumbnailing sped up (+10%%) to a %.1f ms interval for "%s"' % (self.interval, filename_from_uri(self.uri)))
        else:
            self.interval *= 1.1
            self.log('Thumbnailing slowed down (-10%%) to a %.1f ms interval for "%s"' % (self.interval, filename_from_uri(self.uri)))
        self.cpu_usage_tracker.reset()
        self._thumb_cb_id = GLib.timeout_add(self.interval, self._create_next_thumb)

    def _startThumbnailingWhenIdle(self):
        self.debug('Waiting for UI to become idle for: %s', filename_from_uri(self.uri))
        GLib.idle_add(self._startThumbnailing, priority=GLib.PRIORITY_LOW)

    def _startThumbnailing(self):
        self.debug('Now generating thumbnails for: %s', filename_from_uri(self.uri))
        query_success, duration = self.pipeline.query_duration(Gst.Format.TIME)
        if not query_success or duration == -1:
            self.debug("Could not determine duration of: %s", self.uri)
            duration = self.duration
        else:
            self.duration = duration

        self.queue = range(0, duration, self.thumb_period)

        self._checkCPU()

        self._addVisibleThumbnails()
        # Save periodically to avoid the common situation where the user exits
        # the app before a long clip has been fully thumbnailed.
        # Spread timeouts between 30-80 secs to avoid concurrent disk writes.
        random_time = randrange(30, 80)
        GLib.timeout_add_seconds(random_time, self._autosave)

        # Remove the GSource
        return False

    def _create_next_thumb(self):
        if not self.wishlist or not self.queue:
            # nothing left to do
            self.debug("Thumbnails generation complete")
            self.stopGeneration()
            self.thumb_cache.commit()
            return
        else:
            self.debug("Missing %d thumbs", len(self.wishlist))

        wish = self._get_wish()
        if wish:
            time = wish
            self.queue.remove(wish)
        else:
            time = self.queue.pop(0)
        self.log('Creating thumb for "%s"' % filename_from_uri(self.uri))
        # append the time to the end of the queue so that if this seek fails
        # another try will be started later
        self.queue.append(time)
        self.pipeline.seek(1.0,
                           Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                           Gst.SeekType.SET, time,
                           Gst.SeekType.NONE, -1)

        # Remove the GSource
        return False

    def _autosave(self):
        if self.wishlist:
            self.log("Periodic thumbnail autosave")
            self.thumb_cache.commit()
            return True
        else:
            return False  # Stop the timer

    def _get_thumb_duration(self):
        thumb_duration_tmp = Zoomable.pixelToNs(self.thumb_width + self.thumb_margin)
        # quantize thumb length to thumb_period
        thumb_duration = quantize(thumb_duration_tmp, self.thumb_period)
        # make sure that the thumb duration after the quantization isn't smaller than before
        if thumb_duration < thumb_duration_tmp:
            thumb_duration += self.thumb_period
        # make sure that we don't show thumbnails more often than thumb_period
        return max(thumb_duration, self.thumb_period)

    def _addVisibleThumbnails(self):
        """
        Get the thumbnails to be displayed in the currently visible clip portion
        """
        self.remove_all_children()
        old_thumbs = self.thumbs
        self.thumbs = {}
        self.wishlist = []

        thumb_duration = self._get_thumb_duration()
        element_left, element_right = self._get_visible_range()
        element_left = quantize(element_left, thumb_duration)

        for current_time in range(element_left, element_right, thumb_duration):
            thumb = Thumbnail(self.thumb_width, self.thumb_height)
            thumb.set_position(Zoomable.nsToPixel(current_time), self.thumb_margin)
            self.add_child(thumb)
            self.thumbs[current_time] = thumb
            if current_time in self.thumb_cache:
                gdkpixbuf = self.thumb_cache[current_time]
                if self._allAnimated or current_time not in old_thumbs:
                    self.thumbs[current_time].set_from_gdkpixbuf_animated(gdkpixbuf)
                else:
                    self.thumbs[current_time].set_from_gdkpixbuf(gdkpixbuf)
            else:
                self.wishlist.append(current_time)
        self._allAnimated = False

    def _get_wish(self):
        """
        Returns a wish that is also in the queue, or None if no such wish exists
        """
        while True:
            if not self.wishlist:
                return None
            wish = self.wishlist.pop(0)
            if wish in self.queue:
                return wish

    def _setThumbnail(self, time, pixbuf):
        # Q: Is "time" guaranteed to be nanosecond precise?
        # A: Not always.
        # => __tim says: "that's how it should be"
        # => also see gst-plugins-good/tests/icles/gdkpixbufsink-test
        # => Daniel: It is *not* nanosecond precise when we remove the videorate
        #            element from the pipeline
        # => thiblahute: not the case with mpegts
        original_time = time
        if time in self.thumbs:
            thumb = self.thumbs[time]
        else:
            sorted_times = sorted(self.thumbs.keys())
            index = binary_search(sorted_times, time)
            time = sorted_times[index]
            thumb = self.thumbs[time]
            if thumb.has_pixel_data:
                # If this happens, it means the precision of the thumbnail
                # generator is not good enough for the current thumbnail
                # interval.
                # We could consider shifting the thumbnails, but seems like
                # too much trouble for something which does not happen in
                # practice. My last words..
                self.fixme("Thumbnail is already set for time: %s, %s",
                           format_ns(time), format_ns(original_time))
                return
        thumb.set_from_gdkpixbuf_animated(pixbuf)
        if time in self.queue:
            self.queue.remove(time)
        self.thumb_cache[time] = pixbuf

    # Interface (Zoomable)

    def zoomChanged(self):
        self.remove_all_children()
        self._allAnimated = True
        self._update()

    def _get_visible_range(self):
        # Shortcut/convenience variables:
        start = self.bElement.props.start
        in_point = self.bElement.props.in_point
        duration = self.bElement.props.duration
        timeline_left, timeline_right = self._get_visible_timeline_range()

        element_left = timeline_left - start + in_point
        element_left = max(element_left, in_point)
        element_right = timeline_right - start + in_point
        element_right = min(element_right, in_point + duration)

        return (element_left, element_right)

    # TODO: move to Timeline or to utils
    def _get_visible_timeline_range(self):
        # determine the visible left edge of the timeline
        # TODO: isn't there some easier way to get the scroll point of the ScrollActor?
        # timeline_left = -(self.timeline.get_transform().xw - self.timeline.props.x)
        timeline_left = self.timeline.get_scroll_point().x

        # determine the width of the pipeline
        # by intersecting the timeline's and the stage's allocation
        timeline_allocation = self.timeline.props.allocation
        stage_allocation = self.timeline.get_stage().props.allocation

        timeline_rect = Clutter.Rect()
        timeline_rect.init(timeline_allocation.x1,
                           timeline_allocation.y1,
                           timeline_allocation.x2 - timeline_allocation.x1,
                           timeline_allocation.y2 - timeline_allocation.y1)

        stage_rect = Clutter.Rect()
        stage_rect.init(stage_allocation.x1,
                        stage_allocation.y1,
                        stage_allocation.x2 - stage_allocation.x1,
                        stage_allocation.y2 - stage_allocation.y1)

        has_intersection, intersection = timeline_rect.intersection(stage_rect)

        if not has_intersection:
            return (0, 0)

        timeline_width = intersection.size.width

        # determine the visible right edge of the timeline
        timeline_right = timeline_left + timeline_width

        # convert to nanoseconds
        time_left = Zoomable.pixelToNs(timeline_left)
        time_right = Zoomable.pixelToNs(timeline_right)

        return (time_left, time_right)

    # Callbacks

    def bus_message_handler(self, unused_bus, message):
        if message.type == Gst.MessageType.ELEMENT and \
                message.src == self.gdkpixbufsink:
            struct = message.get_structure()
            struct_name = struct.get_name()
            if struct_name == "preroll-pixbuf":
                stream_time = struct.get_value("stream-time")
                pixbuf = struct.get_value("pixbuf")
                self._setThumbnail(stream_time, pixbuf)
        elif message.type == Gst.MessageType.ASYNC_DONE and \
                message.src == self.pipeline:
            self._checkCPU()
        return Gst.BusSyncReply.PASS

    def _autoplugSelectCb(self, decode, pad, caps, factory):
        # Don't plug audio decoders / parsers.
        if "Audio" in factory.get_klass():
            return True
        return False

    def _scrollCb(self, unused):
        self._update()

    def _startChangedCb(self, unused_bElement, unused_value):
        self._update()

    def _inpointChangedCb(self, unused_bElement, unused_value):
        position = Clutter.Point()
        position.x = Zoomable.nsToPixel(self.bElement.props.in_point)
        self.scroll_to_point(position)
        self._update()

    def _durationChangedCb(self, unused_bElement, unused_value):
        new_duration = max(self.duration, self.bElement.props.duration)
        if new_duration > self.duration:
            self.duration = new_duration
            self._update()

    def startGeneration(self):
        self._setupPipeline()
        self._startThumbnailingWhenIdle()

    def stopGeneration(self):
        if self._thumb_cb_id:
            GLib.source_remove(self._thumb_cb_id)
            self._thumb_cb_id = None

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
            self.pipeline = None
        PreviewGenerator.emit(self, "done")

    def cleanup(self):
        self.stopGeneration()
        Zoomable.__del__(self)


class Thumbnail(Clutter.Actor):
    def __init__(self, width, height):
        Clutter.Actor.__init__(self)
        image = Clutter.Image.new()
        self.props.content = image
        self.width = width
        self.height = height
        #self.set_background_color(Clutter.Color.new(0, 100, 150, 100))
        self.set_opacity(0)
        self.set_size(self.width, self.height)
        self.has_pixel_data = False

    def set_from_gdkpixbuf(self, gdkpixbuf):
        row_stride = gdkpixbuf.get_rowstride()
        pixel_data = gdkpixbuf.get_pixels()
        alpha = gdkpixbuf.get_has_alpha()
        self.has_pixel_data = True
        if alpha:
            self.props.content.set_data(pixel_data, Cogl.PixelFormat.RGBA_8888,
                                        self.width, self.height, row_stride)
        else:
            self.props.content.set_data(pixel_data, Cogl.PixelFormat.RGB_888,
                                        self.width, self.height, row_stride)
        self.set_opacity(255)

    def set_from_gdkpixbuf_animated(self, gdkpixbuf):
        self.save_easing_state()
        self.set_easing_duration(750)
        self.set_from_gdkpixbuf(gdkpixbuf)
        self.restore_easing_state()


caches = {}


def get_cache_for_uri(uri):
    if uri in caches:
        return caches[uri]
    else:
        cache = ThumbnailCache(uri)
        caches[uri] = cache
        return cache


class ThumbnailCache(Loggable):

    """Caches thumbnails by key using LRU policy, implemented with heapq.

    Uses a two stage caching mechanism. A limited number of elements are
    held in memory, the rest is being cached on disk using an sqlite db."""

    def __init__(self, uri):
        Loggable.__init__(self)
        self._filehash = hash_file(Gst.uri_get_location(uri))
        self._filename = filename_from_uri(uri)
        thumbs_cache_dir = get_dir(os.path.join(xdg_cache_home(), "thumbs"))
        dbfile = os.path.join(thumbs_cache_dir, self._filehash)
        self._db = sqlite3.connect(dbfile)
        self._cur = self._db.cursor()  # Use this for normal db operations
        self._cur.execute("CREATE TABLE IF NOT EXISTS Thumbs\
                          (Time INTEGER NOT NULL PRIMARY KEY,\
                          Jpeg BLOB NOT NULL)")

    def __contains__(self, key):
        # check if item is present in on disk cache
        self._cur.execute("SELECT Time FROM Thumbs WHERE Time = ?", (key,))
        if self._cur.fetchone():
            return True
        return False

    def __getitem__(self, key):
        self._cur.execute("SELECT * FROM Thumbs WHERE Time = ?", (key,))
        row = self._cur.fetchone()
        if not row:
            raise KeyError(key)
        jpeg = row[1]
        loader = GdkPixbuf.PixbufLoader.new()
        # TODO: what do to if any of the following calls fails?
        loader.write(jpeg)
        loader.close()
        pixbuf = loader.get_pixbuf()
        return pixbuf

    def __setitem__(self, key, value):
        success, jpeg = value.save_to_bufferv("jpeg", ["quality", None], ["90"])
        if not success:
            self.warning("JPEG compression failed")
            return
        blob = sqlite3.Binary(jpeg)
        #Replace if the key already existed
        self._cur.execute("DELETE FROM Thumbs WHERE  time=?", (key,))
        self._cur.execute("INSERT INTO Thumbs VALUES (?,?)", (key, blob,))

    def commit(self):
        self.debug('Saving thumbnail cache file to disk for: %s', self._filename)
        self._db.commit()
        self.log("Saved thumbnail cache file: %s" % self._filehash)


class PipelineCpuAdapter(Loggable):
    """
    This pipeline manager will modulate the rate of the provided pipeline.
    It is the responsibility of the caller to set the sync of the sink to True,
    disable QOS and provide a pipeline with a rate of 1.0.
    Doing otherwise would be cheating. Cheating is bad.
    """
    def __init__(self, pipeline):
        Loggable.__init__(self)
        self.pipeline = pipeline
        self.bus = self.pipeline.get_bus()

        self.cpu_usage_tracker = CPUUsageTracker()
        self.rate = 1.0
        self.done = False
        self.ready = False
        self.lastPos = 0
        self._bus_cb_id = None

    def start(self):
        GLib.timeout_add(200, self._modulateRate)
        self._bus_cb_id = self.bus.connect("message", self._messageCb)
        self.done = False

    def stop(self):
        if self._bus_cb_id is not None:
            self.bus.disconnect(self._bus_cb_id)
            self._bus_cb_id = None
        self.pipeline = None
        self.done = True

    def _modulateRate(self):
        """
        Adapt the rate of audio playback (analysis) depending on CPU usage.
        """
        if self.done:
            return False

        usage_percent = self.cpu_usage_tracker.usage()
        self.cpu_usage_tracker.reset()
        if usage_percent >= WAVEFORMS_CPU_USAGE:
            if self.rate < 0.1:
                if not self.ready:
                    self.ready = True
                    self.pipeline.set_state(Gst.State.READY)
                    res, self.lastPos = self.pipeline.query_position(Gst.Format.TIME)
                return True

            if self.rate > 0.0:
                self.rate *= 0.9
                self.log('Pipeline rate slowed down (-10%%) to %.3f' % self.rate)
        else:
            self.rate *= 1.1
            self.log('Pipeline rate sped up (+10%%) to %.3f' % self.rate)

        if not self.ready:
            res, position = self.pipeline.query_position(Gst.Format.TIME)
        else:
            if self.rate > 0.5:  # This to avoid going back and forth from READY to PAUSED
                self.pipeline.set_state(Gst.State.PAUSED)  # The message handler will unset ready and seek correctly.
            return True

        self.pipeline.set_state(Gst.State.PAUSED)
        self.pipeline.seek(self.rate,
                           Gst.Format.TIME,
                           Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                           Gst.SeekType.SET,
                           position,
                           Gst.SeekType.NONE,
                           -1)
        self.pipeline.set_state(Gst.State.PLAYING)
        self.ready = False
        # Keep the glib timer running:
        return True

    def _messageCb(self, bus, message):
        if not self.ready:
            return
        if message.type == Gst.MessageType.STATE_CHANGED:
            prev, new, pending = message.parse_state_changed()
            if message.src == self.pipeline:
                if prev == Gst.State.READY and new == Gst.State.PAUSED:
                    self.pipeline.seek(1.0,
                                       Gst.Format.TIME,
                                       Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                                       Gst.SeekType.SET,
                                       self.lastPos,
                                       Gst.SeekType.NONE,
                                       -1)
                    self.ready = False


class AudioPreviewer(Clutter.Actor, PreviewGenerator, Zoomable, Loggable):
    """
    Audio previewer based on the results from the "level" gstreamer element.
    """
    def __init__(self, bElement, timeline):
        Clutter.Actor.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        PreviewGenerator.__init__(self, GES.TrackType.AUDIO)
        self.discovered = False
        self.bElement = bElement
        self._uri = quote_uri(bElement.props.uri)  # Guard against malformed URIs
        self.timeline = timeline
        self.actors = []

        self.set_content_scaling_filters(Clutter.ScalingFilter.NEAREST, Clutter.ScalingFilter.NEAREST)
        self.canvas = Clutter.Canvas()
        self.set_content(self.canvas)
        self.width = 0
        self._num_failures = 0
        self.lastUpdate = datetime.now()

        self.interval = timedelta(microseconds=INTERVAL)

        self.current_geometry = (-1, -1)

        self.adapter = None
        self.surface = None
        self.timeline.connect("scrolled", self._scrolledCb)
        self.canvas.connect("draw", self._drawContentCb)
        self.canvas.invalidate()

        self._callback_id = 0

    def startLevelsDiscoveryWhenIdle(self):
        self.debug('Waiting for UI to become idle for: %s', filename_from_uri(self._uri))
        GLib.idle_add(self._startLevelsDiscovery, priority=GLib.PRIORITY_LOW)

    def _startLevelsDiscovery(self):
        self.log('Preparing waveforms for "%s"' % filename_from_uri(self._uri))
        filename = hash_file(Gst.uri_get_location(self._uri)) + ".wave"
        cache_dir = get_dir(os.path.join(xdg_cache_home(), "waves"))
        filename = cache_dir + "/" + filename

        if os.path.exists(filename):
            self.samples = pickle.load(open(filename, "rb"))
            self._startRendering()
        else:
            self.wavefile = filename
            self._launchPipeline()

    def _launchPipeline(self):
        self.debug('Now generating waveforms for: %s', filename_from_uri(self._uri))
        self.peaks = None
        self.pipeline = Gst.parse_launch("uridecodebin name=decode uri=" + self._uri + " ! audioconvert ! level name=wavelevel interval=10000000 post-messages=true ! fakesink qos=false name=faked")
        faked = self.pipeline.get_by_name("faked")
        faked.props.sync = True
        self._level = self.pipeline.get_by_name("wavelevel")
        decode = self.pipeline.get_by_name("decode")
        decode.connect("autoplug-select", self._autoplugSelectCb)
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()

        self.nSamples = self.bElement.get_parent().get_asset().get_duration() / 10000000
        bus.connect("message", self._messageCb)
        self.becomeControlled()

    def set_size(self, width, height):
        if self.discovered:
            self._maybeUpdate()

    def updateOffset(self):
        print self.timeline.get_scroll_point().x

    def zoomChanged(self):
        self._maybeUpdate()

    def _maybeUpdate(self):
        if self.discovered:
            self.log('Checking if the waveform for "%s" needs to be redrawn' % self._uri)
            if datetime.now() - self.lastUpdate > self.interval:
                self.lastUpdate = datetime.now()
                self._compute_geometry()
            else:
                if self._callback_id:
                    GLib.source_remove(self._callback_id)
                self._callback_id = GLib.timeout_add(500, self._compute_geometry)

    def _compute_geometry(self):
        self.log("Computing the clip's geometry for waveforms")
        start = self.timeline.get_scroll_point().x - self.nsToPixel(self.bElement.props.start)
        start = max(0, start)
        end = min(self.timeline.get_scroll_point().x + self.timeline._container.get_allocation().width - CONTROL_WIDTH + MARGIN,
                  self.nsToPixel(self.bElement.props.duration))

        pixelWidth = self.nsToPixel(self.bElement.props.duration)

        if pixelWidth <= 0:
            return

        real_duration = self.bElement.get_parent().get_asset().get_duration()

        # We need to take duration and inpoint into account.

        nbSamples = self.nbSamples
        startOffsetSamples = 0

        if self.bElement.props.duration != 0:
            nbSamples = self.nbSamples / (float(real_duration) / float(self.bElement.props.duration))
        if self.bElement.props.in_point != 0:
            startOffsetSamples = self.nbSamples / (float(real_duration) / float(self.bElement.props.in_point))

        self.start = int(start / pixelWidth * nbSamples + startOffsetSamples)
        self.end = int(end / pixelWidth * nbSamples + startOffsetSamples)

        self.width = int(end - start)

        if self.width < 0:  # We've been called at a moment where size was updated but not scroll_point.
            return

        self.canvas.set_size(self.width, 65)
        Clutter.Actor.set_size(self, self.width, EXPANDED_SIZE)
        self.set_position(start, self.props.y)
        self.canvas.invalidate()

    def _prepareSamples(self):
        # Let's go mono.
        if (len(self.peaks) > 1):
            samples = (numpy.array(self.peaks[0]) + numpy.array(self.peaks[1])) / 2
        else:
            samples = numpy.array(self.peaks[0])

        self.samples = samples.tolist()
        f = open(self.wavefile, 'w')
        pickle.dump(self.samples, f)

    def _startRendering(self):
        self.nbSamples = len(self.samples)
        self.discovered = True
        self.start = 0
        self.end = self.nbSamples
        self._compute_geometry()
        if self.adapter:
            self.adapter.stop()

    def _messageCb(self, bus, message):
        if message.src == self._level:
            s = message.get_structure()
            p = None
            if s:
                p = s.get_value("rms")

            if p:
                st = s.get_value("stream-time")

                if self.peaks is None:
                    self.peaks = []
                    for channel in p:
                        self.peaks.append([0] * self.nSamples)

                pos = int(st / 10000000)
                if pos >= len(self.peaks[0]):
                    return

                for i, val in enumerate(p):
                    if val < 0:
                        val = 10 ** (val / 20) * 100
                        self.peaks[i][pos] = val
                    else:
                        self.peaks[i][pos] = self.peaks[i][pos - 1]
            return

        if message.type == Gst.MessageType.EOS:
            self._prepareSamples()
            self._startRendering()
            self.stopGeneration()

        elif message.type == Gst.MessageType.ERROR:
            if self.adapter:
                self.adapter.stop()
                self.adapter = None
            # Something went wrong TODO : recover
            self.stopGeneration()
            self._num_failures += 1
            if self._num_failures < 2:
                self.warning("Issue during waveforms generation: %s"
                             " for the %ith time, trying again with no rate "
                             " modulation", message.parse_error(),
                             self._num_failures)
                bus.disconnect_by_func(self._messageCb)
                self._launchPipeline()
                self.becomeControlled()
            else:
                self.error("Issue during waveforms generation: %s"
                           "Abandonning", message.parse_error())

        elif message.type == Gst.MessageType.STATE_CHANGED:
            prev, new, pending = message.parse_state_changed()
            if message.src == self.pipeline:
                if prev == Gst.State.READY and new == Gst.State.PAUSED:
                    self.pipeline.seek(1.0,
                                       Gst.Format.TIME,
                                       Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                                       Gst.SeekType.SET,
                                       0,
                                       Gst.SeekType.NONE,
                                       -1)

                # In case we failed previously, we won't modulate next time
                elif not self.adapter and prev == Gst.State.PAUSED and \
                        new == Gst.State.PLAYING and self._num_failures == 0:
                    self.adapter = PipelineCpuAdapter(self.pipeline)
                    self.adapter.start()

    def _autoplugSelectCb(self, decode, pad, caps, factory):
        # Don't plug video decoders / parsers.
        if "Video" in factory.get_klass():
            return True
        return False

    def _drawContentCb(self, canvas, cr, surf_w, surf_h):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        if not self.discovered:
            return

        if self.surface:
            self.surface.finish()

        self.surface = renderer.fill_surface(self.samples[self.start:self.end], int(self.width), int(EXPANDED_SIZE))

        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_surface(self.surface, 0, 0)
        cr.paint()

    def _scrolledCb(self, unused):
        self._maybeUpdate()

    def startGeneration(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        if self.adapter is not None:
            self.adapter.start()

    def stopGeneration(self):
        if self.adapter is not None:
            self.adapter.stop()
            self.adapter = None
        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        PreviewGenerator.emit(self, "done")

    def cleanup(self):
        self.stopGeneration()
        self.canvas.disconnect_by_func(self._drawContentCb)
        self.timeline.disconnect_by_func(self._scrolledCb)
        Zoomable.__del__(self)
