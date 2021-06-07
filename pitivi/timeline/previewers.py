# -*- coding: utf-8 -*-
# Pitivi video editor
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Previewers for the timeline."""
import contextlib
import hashlib
import os
import random
import sqlite3
from gettext import gettext as _

import cairo
import numpy
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import PangoCairo

from pitivi.settings import GlobalSettings
from pitivi.settings import xdg_cache_home
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import quantize
from pitivi.utils.misc import quote_uri
from pitivi.utils.pipeline import MAX_BRINGING_TO_PAUSED_DURATION
from pitivi.utils.proxy import get_proxy_target
from pitivi.utils.proxy import ProxyManager
from pitivi.utils.system import CPUUsageTracker
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import CLIP_BORDER_WIDTH
from pitivi.utils.ui import EXPANDED_SIZE
from pitivi.utils.ui import MINI_LAYER_HEIGHT

# Our C module optimizing waveforms rendering
try:
    from . import renderer
except ImportError:
    # Running uninstalled?
    import renderer


# This decides how much data we are collecting for AudioPreviewer.
# We divide the clip into multiple samples of length SAMPLE_DURATION
# and then fetch average peak data for each sample using 'level'
# element. Lowering the value results in more detailed waveform
# but also increases the time it takes to collect all data.
SAMPLE_DURATION = Gst.SECOND // 50

# Horizontal space between thumbs.
THUMB_MARGIN_PX = 3
THUMB_HEIGHT = EXPANDED_SIZE - 2 * CLIP_BORDER_WIDTH
THUMB_PERIOD = int(Gst.SECOND / 2)
assert Gst.SECOND % THUMB_PERIOD == 0
# For the waveforms, ensures we always have a little extra surface when
# scrolling while playing, in pixels.
WAVEFORM_SURFACE_EXTRA_PX = 500

PREVIEW_GENERATOR_SIGNALS = {
    "done": (GObject.SignalFlags.RUN_LAST, None, ()),
    "error": (GObject.SignalFlags.RUN_LAST, None, ()),
}

GlobalSettings.add_config_section("previewers")

GlobalSettings.add_config_option("previewers_max_cpu",
                                 section="previewers",
                                 key="max-cpu-usage",
                                 default=90)


class PreviewerBin(Gst.Bin, Loggable):
    """Baseclass for elements gathering data to create previews."""

    def __init__(self, bin_desc):
        Gst.Bin.__init__(self)
        Loggable.__init__(self)

        self.internal_bin = Gst.parse_bin_from_description(bin_desc, True)
        self.add(self.internal_bin)
        sinkpad, = list(self.internal_bin.iterate_sink_pads())
        self.add_pad(Gst.GhostPad.new(None, sinkpad))
        srcpad, = list(self.internal_bin.iterate_src_pads())
        self.add_pad(Gst.GhostPad.new(None, srcpad))

    def finalize(self):
        """Finalizes the previewer, saving data to the disk if needed."""


class TeedThumbnailBin(PreviewerBin):
    """Bin to generate and save thumbnails to an SQLite database."""

    __gproperties__ = {
        "uri": (str,
                "uri of the media file",
                "A URI",
                "",
                GObject.ParamFlags.READWRITE),
    }

    def __init__(self, bin_desc="videoconvert ! videoflip method=automatic ! tee name=t ! queue  "
                 "max-size-buffers=0 max-size-bytes=0 max-size-time=0  ! "
                 "videoconvert ! videorate ! videoscale method=lanczos ! "
                 "capsfilter caps=video/x-raw,format=(string)RGBA,height=(int)%d,"
                 "pixel-aspect-ratio=(fraction)1/1,"
                 "framerate=2/1 ! gdkpixbufsink name=gdkpixbufsink "
                 "t. ! queue " % THUMB_HEIGHT):
        PreviewerBin.__init__(self, bin_desc)

        self.uri = None
        self.thumb_cache = None
        self.gdkpixbufsink = self.internal_bin.get_by_name("gdkpixbufsink")

    def __add_thumbnail(self, message):
        struct = message.get_structure()
        struct_name = struct.get_name()
        if struct_name == "pixbuf":
            stream_time = struct.get_value("stream-time")
            self.log("%s new thumbnail %s", self.uri, stream_time)
            pixbuf = struct.get_value("pixbuf")
            self.thumb_cache[stream_time] = pixbuf

        return False

    def do_post_message(self, message):
        if message.type == Gst.MessageType.ELEMENT and \
                message.src == self.gdkpixbufsink:
            GLib.idle_add(self.__add_thumbnail, message)

        return Gst.Bin.do_post_message(self, message)

    def finalize(self):
        """Finalizes the previewer, saving data to file if needed."""
        self.thumb_cache.commit()

    def do_get_property(self, prop):
        if prop.name == 'uri':
            return self.uri

        raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop, value):
        if prop.name == 'uri':
            self.uri = value
            self.thumb_cache = ThumbnailCache.get(self.uri)
        else:
            raise AttributeError('unknown property %s' % prop.name)


class WaveformPreviewer(PreviewerBin):
    """Bin to generate and save waveforms as a .npy file."""

    __gproperties__ = {
        "uri": (str,
                "uri of the media file",
                "A URI",
                "",
                GObject.ParamFlags.READWRITE),
        "duration": (GObject.TYPE_UINT64,
                     "Duration",
                     "Duration",
                     0, GLib.MAXUINT64 - 1, 0, GObject.ParamFlags.READWRITE)
    }

    def __init__(self):
        PreviewerBin.__init__(self,
                              "tee name=at ! queue ! audioconvert ! audioresample ! "
                              "audio/x-raw,channels=1 ! level name=level "
                              f"interval={SAMPLE_DURATION}"
                              " ! fakesink at. ! queue")
        self.level = self.internal_bin.get_by_name("level")
        self.debug("Creating waveforms!!")
        self.peaks = None

        self.uri = None
        self.wavefile = None
        self.passthrough = False
        self.samples = None
        self.n_samples = 0
        self.duration = 0
        self.prev_pos = 0

    def do_get_property(self, prop):
        if prop.name == 'uri':
            return self.uri

        if prop.name == 'duration':
            return self.duration

        raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop, value):
        if prop.name == 'uri':
            self.uri = value
            self.wavefile = get_wavefile_location_for_uri(self.uri)
            self.passthrough = os.path.exists(self.wavefile)
        elif prop.name == 'duration':
            self.duration = value
            self.n_samples = self.duration / SAMPLE_DURATION
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_post_message(self, message):
        if message.type == Gst.MessageType.ELEMENT and \
                message.src == self.level and \
                not self.passthrough:
            struct = message.get_structure()
            peaks = None
            if struct:
                peaks = struct.get_value("rms")

            if peaks:
                stream_time = struct.get_value("stream-time")

                if self.peaks is None:
                    self.peaks = []
                    for unused_channel in peaks:
                        self.peaks.append([0] * int(self.n_samples))

                pos = int(stream_time / SAMPLE_DURATION)
                if pos >= len(self.peaks[0]):
                    return False

                for i, val in enumerate(peaks):
                    if val < 0:
                        val = 10 ** (val / 20) * 100
                    else:
                        val = self.peaks[i][pos - 1]

                    # Linearly joins values between to known samples values.
                    unknowns = range(self.prev_pos + 1, pos)
                    if unknowns:
                        prev_val = self.peaks[i][self.prev_pos]
                        linear_const = (val - prev_val) / len(unknowns)
                        for temppos in unknowns:
                            self.peaks[i][temppos] = self.peaks[i][temppos - 1] + linear_const

                    self.peaks[i][pos] = val

                self.prev_pos = pos

        return Gst.Bin.do_post_message(self, message)

    def finalize(self):
        """Finalizes the previewer, saving data to file if needed."""
        if not self.passthrough and self.peaks:
            # Let's go mono.
            if len(self.peaks) > 1:
                samples = (numpy.array(self.peaks[0]) + numpy.array(self.peaks[1])) / 2
            else:
                samples = numpy.array(self.peaks[0])

            with open(self.wavefile, 'wb') as wavefile:
                numpy.save(wavefile, samples)

            self.samples = samples


Gst.Element.register(None, "waveformbin", Gst.Rank.NONE,
                     WaveformPreviewer)
Gst.Element.register(None, "teedthumbnailbin", Gst.Rank.NONE,
                     TeedThumbnailBin)


class PreviewGeneratorManager(Loggable):
    """Manager for running the previewers."""

    def __init__(self):
        Loggable.__init__(self)

        # The current Previewer per GES.TrackType.
        self._current_previewers = {}
        # The queue of Previewers.
        self._previewers = {
            GES.TrackType.AUDIO: [],
            GES.TrackType.VIDEO: []
        }
        self._running = True

    def add_previewer(self, previewer):
        """Adds the specified previewer to the queue.

        Args:
            previewer (Previewer): The previewer to control.
        """
        track_type = previewer.track_type

        current = self._current_previewers.get(track_type)
        if previewer in self._previewers[track_type] or previewer is current:
            # Already in the queue or already processing.
            return

        if not self._previewers[track_type] and current is None:
            self._start_previewer(previewer)
        else:
            self._previewers[track_type].insert(0, previewer)

    def _start_previewer(self, previewer):
        self._current_previewers[previewer.track_type] = previewer
        previewer.connect("done", self.__previewer_done_cb)
        previewer.start_generation()

    @contextlib.contextmanager
    def paused(self, interrupt=False):
        """Pauses (and flushes if interrupt=True) managed previewers."""
        if interrupt:
            for previewer in list(self._current_previewers.values()):
                previewer.stop_generation()

            for previewers in self._previewers.values():
                for previewer in previewers:
                    previewer.stop_generation()
        else:
            for previewer in list(self._current_previewers.values()):
                previewer.pause_generation()

            for previewers in self._previewers.values():
                for previewer in previewers:
                    previewer.pause_generation()

        try:
            self._running = False
            yield
        except:
            self.warning("An exception occurred while the previewer was paused")
            raise
        finally:
            self._running = True
            for track_type in self._previewers:
                self.__start_next_previewer(track_type)

    def __previewer_done_cb(self, previewer):
        self.__start_next_previewer(previewer.track_type)

    def __start_next_previewer(self, track_type):
        next_previewer = self._current_previewers.pop(track_type, None)
        if next_previewer:
            next_previewer.disconnect_by_func(self.__previewer_done_cb)

        if not self._running:
            return

        if self._previewers[track_type]:
            self._start_previewer(self._previewers[track_type].pop())


class Previewer(GObject.Object):
    """Base class for previewers.

    Attributes:
        track_type (GES.TrackType): The type of content.
    """

    # We only need one PreviewGeneratorManager to manage all previewers.
    manager = PreviewGeneratorManager()

    def __init__(self, track_type, max_cpu_usage):
        GObject.Object.__init__(self)
        self.track_type = track_type
        self._max_cpu_usage = max_cpu_usage

    def start_generation(self):
        """Starts preview generation."""

    def stop_generation(self):
        """Stops preview generation."""

    def become_controlled(self):
        """Lets the PreviewGeneratorManager control our execution."""
        Previewer.manager.add_previewer(self)

    def set_selected(self, selected):
        """Marks this instance as being selected."""

    def pause_generation(self):
        """Pauses preview generation."""

    @staticmethod
    def thumb_interval(thumb_width):
        """Gets the interval for which a thumbnail is displayed.

        Returns:
            int: a duration in nanos, multiple of THUMB_PERIOD.
        """
        interval = Zoomable.pixel_to_ns(thumb_width + THUMB_MARGIN_PX)
        # Make sure the thumb interval is a multiple of THUMB_PERIOD.
        quantized = quantize(interval, THUMB_PERIOD)
        # Make sure the quantized thumb interval fits
        # the thumb and the margin.
        if quantized < interval:
            quantized += THUMB_PERIOD
        # Make sure we don't show thumbs more often than THUMB_PERIOD.
        return max(THUMB_PERIOD, quantized)


class ImagePreviewer(Gtk.Layout, Previewer, Zoomable, Loggable):
    """A previewer widget drawing the same thumbnail repeatedly.

    Can be used for Image clips or Color clips.
    """

    # We could define them in Previewer, but for some reason they are ignored.
    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, ges_elem, max_cpu_usage):
        Gtk.Layout.__init__(self)
        Previewer.__init__(self, GES.TrackType.VIDEO, max_cpu_usage)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.get_style_context().add_class("VideoPreviewer")

        self.ges_elem = ges_elem
        self.uri = get_proxy_target(ges_elem).props.id

        self.__start_id = 0

        self.__image_pixbuf = None

        self.thumbs = {}
        self.thumb_height = THUMB_HEIGHT
        self.thumb_width = 0

        self.ges_elem.connect("notify::duration", self._duration_changed_cb)

        if isinstance(self.ges_elem, GES.VideoTestSource):
            self.ges_elem.connect("deep-notify", self._source_deep_notify_cb)

        self.become_controlled()

        self.connect("notify::height-request", self._height_changed_cb)

    def _start_thumbnailing_cb(self):
        if not self.__start_id:
            # Can happen if stopGeneration is called because the clip has been
            # removed from the timeline after the PreviewGeneratorManager
            # started this job.
            return False

        self.__start_id = None

        self.__image_pixbuf = self._generate_thumbnail()
        self.thumb_width = self.__image_pixbuf.props.width

        self._update_thumbnails()
        self.emit("done")

        # Stop calling me, I started already.
        return False

    def _generate_thumbnail(self):
        if isinstance(self.ges_elem, GES.ImageSource):
            self.debug("Generating thumbnail for image: %s", path_from_uri(self.uri))
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(
                Gst.uri_get_location(self.uri), -1, self.thumb_height, True)

        if isinstance(self.ges_elem, GES.VideoTestSource):
            self.debug("Generating thumbnail for color")
            pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, THUMB_HEIGHT, THUMB_HEIGHT)
            res, argb = self.ges_elem.get_child_property("foreground-color")
            assert res
            rgba = ((argb & 0xffffff) << 8) | ((argb & 0xff000000) >> 24)
            pixbuf.fill(rgba)
            return pixbuf

        raise Exception("Unsupported ges_source type: %s" % type(self.ges_elem))

    def _update_thumbnails(self):
        """Updates the thumbnail widgets for the clip at the current zoom."""
        if not self.thumb_width:
            # The __image_pixbuf is not ready yet.
            return

        thumbs = {}
        interval = self.thumb_interval(self.thumb_width)
        element_left = quantize(self.ges_elem.props.in_point, interval)
        element_right = self.ges_elem.props.in_point + self.ges_elem.props.duration
        y = (self.props.height_request - self.thumb_height) / 2
        for position in range(element_left, element_right, interval):
            x = Zoomable.ns_to_pixel(position) - self.ns_to_pixel(self.ges_elem.props.in_point)
            try:
                thumb = self.thumbs.pop(position)
                self.move(thumb, x, y)
            except KeyError:
                thumb = Thumbnail(self.thumb_width, self.thumb_height)
                self.put(thumb, x, y)

            thumbs[position] = thumb
            thumb.set_from_pixbuf(self.__image_pixbuf)
            thumb.set_visible(True)

        for thumb in self.thumbs.values():
            self.remove(thumb)
        self.thumbs = thumbs

    def zoom_changed(self):
        self._update_thumbnails()

    def _height_changed_cb(self, unused_widget, unused_param_spec):
        self._update_thumbnails()

    def _duration_changed_cb(self, unused_ges_timeline_element, unused_param_spec):
        """Handles the changing of the duration of the clip."""
        self._update_thumbnails()

    def _source_deep_notify_cb(self, source, unused_gstelement, pspec):
        """Handles updates in the VideoTestSource."""
        if pspec.name == "foreground-color":
            self.become_controlled()

    def set_selected(self, selected):
        if selected:
            opacity = 0.5
        else:
            opacity = 1.0

        for thumb in self.get_children():
            thumb.props.opacity = opacity

    def start_generation(self):
        self.debug("Waiting for UI to become idle for: %s", self.uri)
        self.__start_id = GLib.idle_add(self._start_thumbnailing_cb,
                                        priority=GLib.PRIORITY_LOW)

    def stop_generation(self):
        if self.__start_id:
            # Cancel the starting.
            GLib.source_remove(self.__start_id)
            self.__start_id = None

        self.emit("done")

    def release(self):
        """Stops preview generation and cleans the object."""
        self.stop_generation()
        Zoomable.__del__(self)


class AssetPreviewer(Previewer, Loggable):
    """Previewer for creating thumbnails for a video asset.

    Attributes:
        thumb_cache (ThumbnailCache): The pixmaps persistent cache.
    """

    # We could define them in Previewer, but for some reason they are ignored.
    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, asset, max_cpu_usage):
        Previewer.__init__(self, GES.TrackType.VIDEO, max_cpu_usage)
        Loggable.__init__(self)

        # Guard against malformed URIs
        self.asset = asset
        self.uri = quote_uri(asset.props.id)

        self.__start_id = 0
        self.__preroll_timeout_id = 0
        self.__thumb_cb_id = 0

        # The thumbs to be generated.
        self.queue = []
        # The position for which a thumbnail is currently being generated.
        self.position = -1
        # The positions for which we failed to get a pixbuf.
        self.failures = set()

        self.thumb_height = THUMB_HEIGHT
        self.thumb_width = 0

        self.thumb_cache = ThumbnailCache.get(self.asset)

        self.thumb_width, unused_height = self.thumb_cache.image_size
        self.pipeline = None
        self.gdkpixbufsink = None

        self.cpu_usage_tracker = CPUUsageTracker()
        # Initial delay before generating the next thumbnail, in millis.
        self.interval = 500

        self.become_controlled()

    def _update_thumbnails(self):
        """Updates the queue of thumbnails to be produced.

        Subclasses can also update the managed UI, if any.

        The contract is that if the method sets a queue,
        it also calls become_controlled().
        """
        position = int(self.asset.get_duration() / 2)
        if position in self.thumb_cache:
            return
        if position not in self.failures and position != self.position:
            self.queue = [position]
            self.become_controlled()

    def _setup_pipeline(self):
        """Creates the pipeline.

        It has the form "playbin ! thumbnailsink" where thumbnailsink
        is a Bin made out of "videorate ! capsfilter ! gdkpixbufsink"
        """
        if self.pipeline:
            # Generation was just PAUSED... keep going
            # bringing the pipeline back to PAUSED.
            self.pipeline.set_state(Gst.State.PAUSED)
            return

        pipeline = Gst.parse_launch(
            "uridecodebin uri={uri} name=decode ! "
            "videoconvert ! "
            "videorate ! "
            "videoflip method=automatic ! "
            "videoscale method=lanczos ! "
            "capsfilter caps=video/x-raw,format=(string)RGBA,height=(int){height},"
            "pixel-aspect-ratio=(fraction)1/1,framerate={thumbs_per_second}/1 ! "
            "gdkpixbufsink name=gdkpixbufsink".format(
                uri=self.uri,
                height=self.thumb_height,
                thumbs_per_second=int(Gst.SECOND / THUMB_PERIOD)))

        # Get the gdkpixbufsink which contains the the sinkpad.
        self.gdkpixbufsink = pipeline.get_by_name("gdkpixbufsink")

        decode = pipeline.get_by_name("decode")
        decode.connect("autoplug-select", self._autoplug_select_cb)

        self.__preroll_timeout_id = GLib.timeout_add_seconds(MAX_BRINGING_TO_PAUSED_DURATION,
                                                             self.__preroll_timed_out_cb)
        pipeline.get_bus().add_signal_watch()
        pipeline.get_bus().connect("message", self.__bus_message_cb)
        pipeline.set_state(Gst.State.PAUSED)
        self.pipeline = pipeline

    def _schedule_next_thumb_generation(self):
        """Schedules the generation of the next thumbnail, or stop.

        Checks the CPU usage and adjusts the waiting time at which the next
        thumbnail will be generated +/- 10%. Even then, it will only
        happen when the gobject loop is idle to avoid blocking the UI.
        """
        if self.__thumb_cb_id:
            # A thumb has already been scheduled.
            return

        if not self.queue:
            # Nothing left to do.
            self.debug("Thumbnails generation complete")
            self.stop_generation()
            return

        usage_percent = self.cpu_usage_tracker.usage()
        if usage_percent < self._max_cpu_usage:
            self.interval *= 0.9
            self.log("Thumbnailing sped up to a %.1f ms interval for `%s`",
                     self.interval, path_from_uri(self.uri))
        else:
            self.interval *= 1.1
            self.log("Thumbnailing slowed down to a %.1f ms interval for `%s`",
                     self.interval, path_from_uri(self.uri))
        self.cpu_usage_tracker.reset()
        self.__thumb_cb_id = GLib.timeout_add(self.interval,
                                              self._create_next_thumb_cb,
                                              priority=GLib.PRIORITY_LOW)

    def _start_thumbnailing_cb(self):
        if not self.__start_id:
            # Can happen if stopGeneration is called because the clip has been
            # removed from the timeline after the PreviewGeneratorManager
            # started this job.
            return False

        self.__start_id = None

        if not self.thumb_width:
            self.debug("Finding thumb width")
            # The pipeline will call `_update_thumbnails` after it sets
            # the missing `thumb_width`.
            self._setup_pipeline()
            # There is nothing else we can do now without `thummb_width`.
            return False

        # Update the thumbnails with what we already have, if anything.
        self._update_thumbnails()
        if self.queue:
            self.debug("Generating thumbnails for video: %s, %s", path_from_uri(self.uri), self.queue)
            # When the pipeline status is set to PAUSED,
            # the first thumbnail generation will be scheduled.
            self._setup_pipeline()
        else:
            self.emit("done")

        # Stop calling me, I started already.
        return False

    def _create_next_thumb_cb(self):
        """Creates a missing thumbnail."""
        self.__thumb_cb_id = 0

        try:
            self.position = self.queue.pop(0)
        except IndexError:
            # The queue is empty. Can happen if _update_thumbnails
            # has been called in the meanwhile.
            self.stop_generation()
            return False

        self.log("Creating thumb at %s", self.position)
        self.pipeline.seek(1.0,
                           Gst.Format.TIME,
                           Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                           Gst.SeekType.SET, self.position,
                           Gst.SeekType.NONE, -1)

        # Stop calling me.
        # The seek operation will generate an ASYNC_DONE message on the bus,
        # and then the next thumbnail generation operation will be scheduled.
        return False

    def _set_pixbuf(self, pixbuf, position):
        """Updates the managed UI when a new pixbuf becomes available.

        Args:
            pixbuf (GdkPixbuf.Pixbuf): The pixbuf produced by self.pipeline.
            position (int): The position for which the thumb has been created,
                in nanoseconds.
        """

    def __bus_message_cb(self, unused_bus, message):
        if message.src == self.pipeline and \
                message.type == Gst.MessageType.STATE_CHANGED:
            if message.parse_state_changed()[1] == Gst.State.PAUSED:
                # The pipeline is ready to be used.
                if self.__preroll_timeout_id:
                    GLib.source_remove(self.__preroll_timeout_id)
                    self.__preroll_timeout_id = 0
                    sinkpad = self.gdkpixbufsink.get_static_pad("sink")
                    neg_caps = sinkpad.get_current_caps()[0]
                    self.thumb_width = neg_caps["width"]

                self._update_thumbnails()
        elif message.src == self.gdkpixbufsink and \
                message.type == Gst.MessageType.ELEMENT and \
                self.__preroll_timeout_id == 0:
            # We got a thumbnail pixbuf.
            struct = message.get_structure()
            struct_name = struct.get_name()
            if struct_name == "preroll-pixbuf":
                pixbuf = struct.get_value("pixbuf")
                self.thumb_cache[self.position] = pixbuf
                self._set_pixbuf(pixbuf, self.position)
                self.position = -1
        elif message.src == self.pipeline and \
                message.type == Gst.MessageType.ASYNC_DONE:
            if self.position >= 0:
                self.warning("Thumbnail generation failed at %s", self.position)
                self.failures.add(self.position)
                self.position = -1
            self._schedule_next_thumb_generation()
        elif message.type == Gst.MessageType.STREAM_COLLECTION and isinstance(message.src, GES.Timeline):
            # Make sure we only work with the video track when thumbnailing
            # nested timelines.
            collection = message.parse_stream_collection()
            for i in range(collection.get_size()):
                stream = collection.get_stream(i)
                if stream.get_stream_type() == Gst.StreamType.VIDEO:
                    message.src.send_event(Gst.Event.new_select_streams([stream.get_stream_id()]))
                    break

        return Gst.BusSyncReply.PASS

    def __preroll_timed_out_cb(self):
        self.stop_generation()

    # pylint: disable=no-self-use
    def _autoplug_select_cb(self, unused_decode, unused_pad, unused_caps, factory):
        # Don't plug audio decoders / parsers.
        if "Audio" in factory.get_klass():
            return True
        return False

    def start_generation(self):
        self.debug("Waiting for UI to become idle for: %s",
                   path_from_uri(self.uri))
        self.__start_id = GLib.idle_add(self._start_thumbnailing_cb,
                                        priority=GLib.PRIORITY_DEFAULT_IDLE + 50)

    def stop_generation(self):
        if self.__start_id:
            # Cancel the starting.
            GLib.source_remove(self.__start_id)
            self.__start_id = None

        if self.__preroll_timeout_id:
            # Stop waiting for the pipeline to be ready.
            GLib.source_remove(self.__preroll_timeout_id)
            self.__preroll_timeout_id = None

        if self.__thumb_cb_id:
            # Cancel the thumbnailing.
            GLib.source_remove(self.__thumb_cb_id)
            self.__thumb_cb_id = 0

        if self.pipeline:
            self.pipeline.get_bus().remove_signal_watch()
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
            self.pipeline = None

        self.emit("done")

    def pause_generation(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.READY)


class VideoPreviewer(Gtk.Layout, AssetPreviewer, Zoomable):
    """A video previewer widget, drawing thumbnails.

    Attributes:
        ges_elem (GES.VideoSource): The previewed element.
        thumbs (dict): Maps (quantized) times to the managed Thumbnail widgets.
    """

    # We could define them in Previewer, but for some reason they are ignored.
    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, ges_elem, max_cpu_usage):
        Gtk.Layout.__init__(self)
        Zoomable.__init__(self)
        AssetPreviewer.__init__(self, get_proxy_target(ges_elem), max_cpu_usage)

        self.get_style_context().add_class("VideoPreviewer")

        self.ges_elem: GES.VideoUriSource = ges_elem
        self.thumbs = {}

        # Connect signals and fire things up
        self.ges_elem.connect("notify::in-point", self._inpoint_changed_cb)
        self.ges_elem.connect("notify::duration", self._duration_changed_cb)

        self.connect("notify::height-request", self._height_changed_cb)

    def set_selected(self, selected):
        if selected:
            opacity = 0.5
        else:
            opacity = 1.0

        for thumb in self.get_children():
            thumb.props.opacity = opacity

    def refresh(self):
        """Recreates the thumbnails cache."""
        self.stop_generation()
        self.thumb_cache = ThumbnailCache.get(self.uri)
        self._update_thumbnails()

    def _update_thumbnails(self):
        """Updates the thumbnail widgets for the clip at the current zoom."""
        # The thumb_width is available after the pipeline has been started.
        if not self.thumb_width or not self.ges_elem.get_track() or not self.ges_elem.props.active:
            return

        thumbs = {}
        queue = []

        interval = self.thumb_interval(self.thumb_width)
        y = (self.props.height_request - self.thumb_height) // 2
        clip = self.ges_elem.get_parent()
        for element_position in range(0, self.ges_elem.props.duration, interval):
            x = Zoomable.ns_to_pixel(element_position)

            # Convert position in the timeline to the internal position in the source element
            internal_position = clip.get_internal_time_from_timeline_time(self.ges_elem, self.ges_elem.props.start + element_position)
            position = quantize(internal_position, interval)
            try:
                thumb = self.thumbs.pop(position)
                self.move(thumb, x, y)
            except KeyError:
                thumb = Thumbnail(self.thumb_width, self.thumb_height)
                self.put(thumb, x, y)

            thumbs[position] = thumb
            if position in self.thumb_cache:
                pixbuf = self.thumb_cache[position]
                thumb.set_from_pixbuf(pixbuf)
                thumb.set_visible(True)
            else:
                if position not in self.failures and position != self.position:
                    queue.append(position)

        for thumb in self.thumbs.values():
            self.remove(thumb)
        self.thumbs = thumbs

        self.queue = queue
        if queue:
            self.become_controlled()

    def _set_pixbuf(self, pixbuf, position):
        """Sets the pixbuf for the thumbnail at the expected position."""
        try:
            thumb = self.thumbs[position]
        except KeyError:
            # Can happen because we don't stop the pipeline before
            # updating the thumbnails in _update_thumbnails.
            return
        thumb.set_from_pixbuf(pixbuf)

    def release(self):
        """Stops preview generation and cleans the object."""
        self.stop_generation()
        Zoomable.__del__(self)

    def _height_changed_cb(self, unused_widget, unused_param_spec):
        self._update_thumbnails()

    def _inpoint_changed_cb(self, unused_ges_timeline_element, unused_param_spec):
        """Handles the changing of the in-point of the clip."""
        # Whenever the inpoint changes, the duration also changes, as we never
        # "roll". We rely on the handler for the duration change event to update
        # the thumbnails.
        self.debug("Inpoint change ignored, expecting following duration change")

    def _duration_changed_cb(self, unused_ges_timeline_element, unused_param_spec):
        """Handles the changing of the duration of the clip."""
        self._update_thumbnails()

    def zoom_changed(self):
        self._update_thumbnails()


class Thumbnail(Gtk.Image):
    """Simple widget representing a Thumbnail."""

    def __init__(self, width, height):
        Gtk.Image.__init__(self)

        self.get_style_context().add_class("Thumbnail")

        self.props.width_request = width
        self.props.height_request = height


class ThumbnailCache(Loggable):
    """Cache for the thumbnails of an asset.

    Uses a separate sqlite3 database for each asset.
    """

    # The cache of caches.
    caches_by_uri = {}

    def __init__(self, uri):
        Loggable.__init__(self)
        self.uri = uri
        self.dbfile = self.dbfile_name(uri)
        self.log("Caching thumbs for %s in %s", uri, self.dbfile)
        self._db = sqlite3.connect(self.dbfile)
        self._cur = self._db.cursor()
        self._cur.execute("CREATE TABLE IF NOT EXISTS Thumbs "
                          "(Time INTEGER NOT NULL PRIMARY KEY, "
                          " Jpeg BLOB NOT NULL)")
        # The cached (width, height) of the images.
        self._image_size = (0, 0)
        # The cached positions available in the database.
        self.positions = self.__existing_positions()
        # The ID of the autosave event.
        self.__autosave_id = None

    def __existing_positions(self):
        self._cur.execute("SELECT Time FROM Thumbs")
        return {row[0] for row in self._cur.fetchall()}

    @staticmethod
    def dbfile_name(uri):
        """Returns the cache file path for the specified URI."""
        filename = gen_filename(Gst.uri_get_location(uri), "db")
        thumbs_dir = xdg_cache_home("thumbs")
        thumbs_cache_dir = os.path.join(thumbs_dir, "v1")

        if not os.path.exists(thumbs_cache_dir):
            os.makedirs(thumbs_cache_dir)
            GLib.idle_add(delete_all_files_in_dir, thumbs_dir)

        return os.path.join(thumbs_cache_dir, filename)

    @classmethod
    def update_caches(cls):
        """Trashes the obsolete caches, for assets which changed.

        Returns:
            list[str]: The URIs of the assets which changed.
        """
        changed_files_uris = []
        for uri, cache in cls.caches_by_uri.items():
            dbfile = cls.dbfile_name(uri)
            if cache.dbfile != dbfile:
                changed_files_uris.append(uri)
        for uri in changed_files_uris:
            del cls.caches_by_uri[uri]
        return changed_files_uris

    @classmethod
    def get(cls, obj):
        """Gets a ThumbnailCache for the specified object.

        Args:
            obj (str or GES.UriClipAsset): The object for which to get a cache,
                it can be a string representing a URI, or a GES.UriClipAsset.

        Returns:
            ThumbnailCache: The cache for the object.
        """
        if isinstance(obj, str):
            uri = obj
        elif isinstance(obj, GES.UriClipAsset):
            uri = get_proxy_target(obj).props.id
        else:
            raise ValueError("Unhandled type: %s" % type(obj))

        if ProxyManager.is_proxy_asset(uri):
            uri = ProxyManager.get_target_uri(uri)

        if uri not in cls.caches_by_uri:
            cls.caches_by_uri[uri] = ThumbnailCache(uri)
        return cls.caches_by_uri[uri]

    @property
    def image_size(self):
        """Gets the image size.

        Returns:
            List[int]: The width and height of the images in the cache.
        """
        if self._image_size[0] == 0:
            self._cur.execute("SELECT * FROM Thumbs LIMIT 1")
            row = self._cur.fetchone()
            if row:
                pixbuf = self.__pixbuf_from_row(row)
                self._image_size = (pixbuf.get_width(), pixbuf.get_height())
        return self._image_size

    def get_preview_thumbnail(self):
        """Gets a thumbnail contained 'at the middle' of the cache."""
        if not self.positions:
            return None

        middle = int(len(self.positions) / 2)
        position = sorted(list(self.positions))[middle]
        return self[position]

    @staticmethod
    def __pixbuf_from_row(row):
        """Returns the GdkPixbuf.Pixbuf from the specified row."""
        jpeg = row[1]
        loader = GdkPixbuf.PixbufLoader.new()
        loader.write(jpeg)
        loader.close()
        pixbuf = loader.get_pixbuf()
        return pixbuf

    def __contains__(self, position):
        """Returns whether a row for the specified position exists in the DB."""
        return position in self.positions

    def __getitem__(self, position):
        """Gets the GdkPixbuf.Pixbuf for the specified position."""
        self._cur.execute("SELECT * FROM Thumbs WHERE Time = ?", (position,))
        row = self._cur.fetchone()
        if not row:
            raise KeyError(position)
        return self.__pixbuf_from_row(row)

    def __setitem__(self, position, pixbuf):
        """Sets a GdkPixbuf.Pixbuf for the specified position."""
        success, jpeg = pixbuf.save_to_bufferv(
            "jpeg", ["quality", None], ["90"])
        if not success:
            self.warning("JPEG compression failed")
            return
        blob = sqlite3.Binary(jpeg)
        # Replace if a row with the same time already exists.
        self._cur.execute("DELETE FROM Thumbs WHERE  time=?", (position,))
        self._cur.execute("INSERT INTO Thumbs VALUES (?,?)", (position, blob,))
        self.positions.add(position)
        self._schedule_commit()

    def _schedule_commit(self):
        """Schedules an autosave at a random later time."""
        if self.__autosave_id is not None:
            # A commit is already scheduled.
            return
        # Save after some time, to avoid saving too often.
        # Randomize to avoid concurrent disk writes.
        random_time = random.randrange(10, 20)
        self.__autosave_id = GLib.timeout_add_seconds(random_time, self._autosave_cb)

    def _autosave_cb(self):
        """Handles the autosave event."""
        try:
            self.commit()
        finally:
            self.__autosave_id = None
        # Stop calling me.
        return False

    def commit(self):
        """Saves the cache on disk (in the database)."""
        self._db.commit()
        self.log("Saved thumbnail cache file")


def delete_all_files_in_dir(path):
    """Deletes the files in path without descending into subdirectories."""
    try:
        for dir_entry in os.scandir(path):
            if dir_entry.is_file() or dir_entry.is_symlink():
                os.unlink(dir_entry.path)
    except FileNotFoundError:
        pass


def gen_filename(uri, extension):
    """Generates the cache filename for the specified URI."""
    uri_hash = hashlib.sha256(uri.encode("UTF-8")).hexdigest()
    return "{}_{}_{}.{}".format(os.path.basename(uri), uri_hash, os.path.getmtime(uri), extension)


def get_wavefile_location_for_uri(uri):
    """Computes the URI where the wave.npy file should be stored."""
    if ProxyManager.is_proxy_asset(uri):
        uri = ProxyManager.get_target_uri(uri)
    filename = gen_filename(Gst.uri_get_location(uri), "wave.npy")
    waves_dir = xdg_cache_home("waves")
    cache_dir = os.path.join(waves_dir, "v2")

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        for old_cache_dir in (waves_dir, os.path.join(waves_dir, "v1")):
            GLib.idle_add(delete_all_files_in_dir, old_cache_dir)

    return os.path.join(cache_dir, filename)


class AudioPreviewer(Gtk.Layout, Previewer, Zoomable, Loggable):
    """Audio previewer using the results from the "level" GStreamer element."""

    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, ges_elem, max_cpu_usage):
        Gtk.Layout.__init__(self)
        Previewer.__init__(self, GES.TrackType.AUDIO, max_cpu_usage)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.get_style_context().add_class("AudioPreviewer")

        self.pipeline = None
        self._wavebin = None

        self.ges_elem = ges_elem

        self.samples = None
        self.peaks = None
        self.surface = None
        # The zoom level when self.surface has been created.
        self._surface_zoom_level = 0
        # The pixels range self.surface corresponds to.
        self._surface_start_px = 0
        self._surface_end_px = 0
        # The playback rate from last time the surface was updated.
        self._rate = 1.0

        # Guard against malformed URIs
        self.wavefile = None
        self._uri = quote_uri(get_proxy_target(ges_elem).props.id)

        self._num_failures = 0
        self.become_controlled()

    def refresh(self):
        """Discards the audio samples so they are recreated."""
        self.stop_generation()

        self.samples = None
        self.surface = None
        self.queue_draw()

        self.become_controlled()

    def _start_levels_discovery(self):
        filename = get_wavefile_location_for_uri(self._uri)
        if os.path.exists(filename):
            with open(filename, "rb") as samples:
                self.samples = self._scale_samples(numpy.load(samples))
            self.queue_draw()
        else:
            self.wavefile = filename
            self._launch_pipeline()

    @staticmethod
    def _scale_samples(samples):
        max_value = max(samples)
        has_sound = max_value > 0.0001
        if has_sound:
            # TODO: The 65 value comes from the height of the widget.
            #   It should not be hardcoded though. We can fix this
            #   when we implement a waveform samples cache, because it's
            #   wasteful if multiple clips backed by the same asset
            #   keep their own samples copy.
            factor = 65 / max_value
            samples = samples * factor

        return list(samples)

    def _launch_pipeline(self):
        self.debug(
            "Now generating waveforms for: %s", path_from_uri(self._uri))
        self.pipeline = Gst.parse_launch("uridecodebin name=decode uri=" +
                                         self._uri + " ! waveformbin name=wave"
                                         " ! fakesink qos=false name=faked")
        # This line is necessary so we can instantiate GstTranscoder's
        # GstCpuThrottlingClock below.
        Gst.ElementFactory.make("uritranscodebin", None)
        clock = GObject.new(GObject.type_from_name("GstCpuThrottlingClock"))
        clock.props.cpu_usage = self._max_cpu_usage
        self.pipeline.use_clock(clock)
        faked = self.pipeline.get_by_name("faked")
        faked.props.sync = True
        self._wavebin = self.pipeline.get_by_name("wave")
        asset = self.ges_elem.get_asset().get_filesource_asset()
        self._wavebin.props.uri = asset.get_id()
        self._wavebin.props.duration = asset.get_duration()
        decode = self.pipeline.get_by_name("decode")
        decode.connect("autoplug-select", self._autoplug_select_cb)
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._bus_message_cb)

    def _prepare_samples(self):
        self._wavebin.finalize()
        self.samples = self._scale_samples(self._wavebin.samples)

    def _bus_message_cb(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self._prepare_samples()
            self.queue_draw()
            self.stop_generation()

        elif message.type == Gst.MessageType.ERROR:
            # Something went wrong.
            self.stop_generation()
            self._num_failures += 1
            if self._num_failures < 2:
                self.warning("Issue during waveforms generation: %s"
                             " for the %ith time, trying again with no rate "
                             " modulation", message.parse_error(),
                             self._num_failures)
                bus.disconnect_by_func(self._bus_message_cb)
                self._launch_pipeline()
                self.become_controlled()
            else:
                if self.pipeline:
                    Gst.debug_bin_to_dot_file_with_ts(self.pipeline,
                                                      Gst.DebugGraphDetails.ALL,
                                                      "error-generating-waveforms")
                self.error("Aborting due to waveforms generation issue: %s",
                           message.parse_error())

    # pylint: disable=no-self-use
    def _autoplug_select_cb(self, unused_decode, unused_pad, unused_caps, factory):
        # Don't plug video decoders / parsers.
        if "Video" in factory.get_klass():
            return True
        return False

    def do_draw(self, context):
        if not self.samples or not self.ges_elem.get_track() or not self.ges_elem.props.active:
            # Nothing to draw.
            return

        # The area we have to refresh is this rect inside the clip.
        # For example rect.x is > 0 when the start of the clip is out of view.
        # rect.width = how many pixels of the clip are in view horizontally.
        res, rect = Gdk.cairo_get_clip_rectangle(context)
        assert res

        start = self.ges_elem.props.start
        inpoint = self.ges_elem.props.in_point
        duration = self.ges_elem.props.duration

        # Get the overall rate of the clip in the current area the clip is used
        clip = self.ges_elem.get_parent()
        internal_end = clip.get_internal_time_from_timeline_time(self.ges_elem, start + duration)
        internal_duration = internal_end - inpoint
        rate = internal_duration / duration

        inpoint_px = self.ns_to_pixel(start) - self.ns_to_pixel(start - inpoint / rate)
        max_duration_px = self.ns_to_pixel(clip.maxduration / rate)

        start_px = min(max(0, inpoint_px + rect.x), max_duration_px)
        end_px = min(max(0, inpoint_px + rect.x + rect.width), max_duration_px)

        zoom = self.get_current_zoom_level()
        height = self.get_allocation().height - 2 * CLIP_BORDER_WIDTH

        if not self.surface or \
                height != self.surface.get_height() or \
                zoom != self._surface_zoom_level or \
                start_px < self._surface_start_px or \
                rate != self._rate or \
                end_px > self._surface_end_px:
            # Generate a new surface since the previously generated one, if any,
            # cannot be reused.
            if self.surface:
                self.surface.finish()
                self.surface = None
            self._surface_zoom_level = zoom
            # The generated waveform is for an extended range if possible,
            # so if the user scrolls we don't rebuild the waveform every time.
            self._surface_start_px = max(0, start_px - WAVEFORM_SURFACE_EXTRA_PX)
            self._rate = rate
            self._surface_end_px = min(end_px + WAVEFORM_SURFACE_EXTRA_PX, max_duration_px)

            sample_duration = SAMPLE_DURATION / rate
            range_start = min(max(0, int(self.pixel_to_ns(self._surface_start_px) / sample_duration)), len(self.samples))
            range_end = min(max(0, int(self.pixel_to_ns(self._surface_end_px) / sample_duration)), len(self.samples))
            samples = self.samples[range_start:range_end]
            surface_width = self._surface_end_px - self._surface_start_px
            self.surface = renderer.fill_surface(samples, surface_width, height)

        # Paint the surface, ignoring the clipped rect.
        # We only have to make sure the offset is correct:
        # 1. + self._start_surface_ns, because that's the position of
        # the surface in context, if the entire asset would be drawn.
        # 2. - inpoint, because we're drawing a clip, not the entire asset.
        context.set_operator(cairo.OPERATOR_OVER)
        offset_px = self._surface_start_px - inpoint_px
        context.set_source_surface(self.surface, offset_px, CLIP_BORDER_WIDTH)
        context.paint()

    def _emit_done_on_idle(self):
        self.emit("done")

    def pause_generation(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.PAUSED)

    def start_generation(self):
        if not self.pipeline:
            self._start_levels_discovery()
        else:
            self.pipeline.set_state(Gst.State.PLAYING)

        if not self.pipeline:
            # No need to generate as we loaded pre-generated .wave file.
            GLib.idle_add(self._emit_done_on_idle, priority=GLib.PRIORITY_LOW)
            return

        self.pipeline.set_state(Gst.State.PLAYING)

    def stop_generation(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_bus().disconnect_by_func(self._bus_message_cb)
            self.pipeline = None

        self.emit("done")

    def release(self):
        """Stops preview generation and cleans the object."""
        self.stop_generation()
        Zoomable.__del__(self)


class TitlePreviewer(Gtk.Layout, Previewer, Zoomable, Loggable):
    """Title Clip previewer using Pango to draw text on the clip."""

    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, ges_elem):
        Gtk.Layout.__init__(self)
        Previewer.__init__(self, GES.TrackType.VIDEO, None)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.get_style_context().add_class("TitlePreviewer")

        self.ges_elem = ges_elem
        font = Gtk.Settings.get_default().get_property("gtk-font-name")
        self._font_desc = Pango.font_description_from_string(font)
        self._selected = False

        self.ges_elem.connect("deep-notify", self._ges_elem_deep_notify_cb)

    def _ges_elem_deep_notify_cb(self, ges_element, gst_element, pspec):
        """Forces a redraw when the clip's text is changed."""
        if pspec.name == "text":
            self.queue_draw()

    def do_draw(self, context):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        # The rect that needs to be drawn
        exists, rect = Gdk.cairo_get_clip_rectangle(context)
        if not exists:
            return

        # Text color white
        context.set_source_rgb(1, 1, 1)

        # Get text
        res, escaped_text = self.ges_elem.get_child_property("text")
        if res:
            escaped_text = escaped_text.strip().split("\n", 1)[0]
        if not res or not escaped_text:
            escaped_text = _("Title Clip")

        # Adapt to RTL/LTR direction
        direction = Pango.unichar_direction(escaped_text[0])
        ltr = direction in (Pango.Direction.LTR, Pango.Direction.NEUTRAL)

        x_pos = 10 if ltr else -10
        y_pos = int((height / 2) - 11)
        # Draw the text only if it intersects the rectangle to be drawn.
        if rect.y + rect.height > y_pos:
            # Setup Pango layout for drawing the text.
            layout = PangoCairo.create_layout(context)
            layout.set_markup(escaped_text, -1)

            layout.set_auto_dir(True)
            layout.set_font_description(self._font_desc)
            layout.set_width(width * Pango.SCALE)

            # Prevent lines from being wrapped
            layout.set_ellipsize(Pango.EllipsizeMode.END)

            # Draw text
            context.move_to(x_pos, y_pos)
            PangoCairo.show_layout(context, layout)

        # Draw gradient on top of text to make the text "fade out".
        # The gradient is mostly transparent and turning opaque at the very end.
        if ltr:
            x0 = width * 0.66
            x1 = width * 0.91
        else:
            x0 = width * 0.09
            x1 = width * 0.34
        # Control vector of the gradient is x0 -> x1.
        grad = cairo.LinearGradient(x0, 0, x1, 0)
        if self._selected:
            color = (0.14, 0.133, 0.15)
        else:
            color = (0.368, 0.305, 0.4)
        # Set the start offset of the control vector to transparent (if ltr).
        grad.add_color_stop_rgba(0.0, color[0], color[1], color[2], 0 if ltr else 1)
        # Set the end offset of the control vector to opaque (if ltr).
        grad.add_color_stop_rgba(1.0, color[0], color[1], color[2], 1 if ltr else 0)
        # The rectangle to be filled represents the entire surface.
        context.rectangle(0, 0, rect.width, rect.height)
        context.set_source(grad)
        context.fill()

    def set_selected(self, selected):
        self._selected = selected

    def release(self):
        # Nothing to release
        pass


class MiniPreview(Gtk.Layout):
    """Mini Clip previewer to draw color filled mini clips."""

    def __init__(self, color):
        Gtk.Layout.__init__(self)
        self.get_style_context().add_class("MiniPreviewer")
        self.color = color
        self.props.height_request = MINI_LAYER_HEIGHT

    def do_draw(self, context):
        rect = Gdk.cairo_get_clip_rectangle(context)[1]
        context.set_source_rgb(*self.color)
        context.rectangle(0, 0, rect.width, rect.height)
        context.fill()
