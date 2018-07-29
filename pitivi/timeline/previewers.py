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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
"""Previewers for the timeline."""
import contextlib
import os
import random
import sqlite3

import cairo
import numpy
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.settings import get_dir
from pitivi.settings import GlobalSettings
from pitivi.settings import xdg_cache_home
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import hash_file
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import quantize
from pitivi.utils.misc import quote_uri
from pitivi.utils.pipeline import MAX_BRINGING_TO_PAUSED_DURATION
from pitivi.utils.proxy import get_proxy_target
from pitivi.utils.system import CPUUsageTracker
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import EXPANDED_SIZE

# Our C module optimizing waveforms rendering
try:
    from . import renderer
except ImportError:
    # Running uninstalled?
    import renderer


SAMPLE_DURATION = Gst.SECOND / 100

THUMB_MARGIN_PX = 3
THUMB_HEIGHT = EXPANDED_SIZE - 2 * THUMB_MARGIN_PX
THUMB_PERIOD = int(Gst.SECOND / 2)
assert Gst.SECOND % THUMB_PERIOD == 0
# For the waveforms, ensures we always have a little extra surface when
# scrolling while playing.
MARGIN = 500

PREVIEW_GENERATOR_SIGNALS = {
    "done": (GObject.SIGNAL_RUN_LAST, None, ()),
    "error": (GObject.SIGNAL_RUN_LAST, None, ()),
}

GlobalSettings.addConfigSection("previewers")

GlobalSettings.addConfigOption("previewers_max_cpu",
                               section="previewers",
                               key="max-cpu-usage",
                               default=90)


class PreviewerBin(Gst.Bin, Loggable):
    """Baseclass for elements gathering datas to create previews."""
    def __init__(self, bin_desc):
        Gst.Bin.__init__(self)
        Loggable.__init__(self)

        self.internal_bin = Gst.parse_bin_from_description(bin_desc, True)
        self.add(self.internal_bin)
        self.add_pad(Gst.GhostPad.new(None, self.internal_bin.sinkpads[0]))
        self.add_pad(Gst.GhostPad.new(None, self.internal_bin.srcpads[0]))

    def finalize(self, proxy=None):
        """Finalizes the previewer, saving data to the disk if needed."""
        pass


class ThumbnailBin(PreviewerBin):
    """Bin to generate and save thumbnails to an SQLite database."""

    __gproperties__ = {
        "uri": (str,
                "uri of the media file",
                "A URI",
                "",
                GObject.PARAM_READWRITE),
    }

    def __init__(self, bin_desc="videoconvert ! videorate ! "
                 "videoscale method=lanczos ! "
                 "capsfilter caps=video/x-raw,format=(string)RGBA,"
                 "height=(int)%d,pixel-aspect-ratio=(fraction)1/1,"
                 "framerate=2/1 ! gdkpixbufsink name=gdkpixbufsink " %
                 THUMB_HEIGHT):
        PreviewerBin.__init__(self, bin_desc)

        self.uri = None
        self.thumb_cache = None
        self.gdkpixbufsink = self.internal_bin.get_by_name("gdkpixbufsink")

    def __addThumbnail(self, message):
        struct = message.get_structure()
        struct_name = struct.get_name()
        if struct_name == "pixbuf":
            stream_time = struct.get_value("stream-time")
            self.log("%s new thumbnail %s", self.uri, stream_time)
            pixbuf = struct.get_value("pixbuf")
            self.thumb_cache[stream_time] = pixbuf

        return False

    # pylint: disable=arguments-differ
    def do_post_message(self, message):
        if message.type == Gst.MessageType.ELEMENT and \
                message.src == self.gdkpixbufsink:
            GLib.idle_add(self.__addThumbnail, message)

        return Gst.Bin.do_post_message(self, message)

    def finalize(self, proxy=None):
        """Finalizes the previewer, saving data to file if needed."""
        self.thumb_cache.commit()
        if proxy:
            self.thumb_cache.copy(proxy.get_id())

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


class TeedThumbnailBin(ThumbnailBin):
    """Bin to generate and save thumbnails to an SQLite database."""

    def __init__(self):
        ThumbnailBin.__init__(
            self, bin_desc="tee name=t ! queue  "
            "max-size-buffers=0 max-size-bytes=0 max-size-time=0  ! "
            "videoconvert ! videorate ! videoscale method=lanczos ! "
            "capsfilter caps=video/x-raw,format=(string)RGBA,height=(int)%d,"
            "pixel-aspect-ratio=(fraction)1/1,"
            "framerate=2/1 ! gdkpixbufsink name=gdkpixbufsink "
            "t. ! queue " % THUMB_HEIGHT)


# pylint: disable=too-many-instance-attributes
class WaveformPreviewer(PreviewerBin):
    """Bin to generate and save waveforms as a .npy file."""

    __gproperties__ = {
        "uri": (str,
                "uri of the media file",
                "A URI",
                "",
                GObject.PARAM_READWRITE),
        "duration": (GObject.TYPE_UINT64,
                     "Duration",
                     "Duration",
                     0, GLib.MAXUINT64 - 1, 0, GObject.PARAM_READWRITE)
    }

    def __init__(self):
        PreviewerBin.__init__(self,
                              "audioconvert ! audioresample ! "
                              "audio/x-raw,channels=1 ! level name=level"
                              " ! audioconvert ! audioresample")
        self.level = self.internal_bin.get_by_name("level")
        self.debug("Creating waveforms!!")
        self.peaks = None

        self.uri = None
        self.wavefile = None
        self.passthrough = False
        self.samples = []
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

    # pylint: disable=arguments-differ
    def do_post_message(self, message):
        if not self.passthrough and \
                message.type == Gst.MessageType.ELEMENT and \
                message.src == self.level:
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

    def finalize(self, proxy=None):
        """Finalizes the previewer, saving data to file if needed."""
        if not self.passthrough and self.peaks:
            # Let's go mono.
            if len(self.peaks) > 1:
                samples = (numpy.array(self.peaks[0]) + numpy.array(self.peaks[1])) / 2
            else:
                samples = numpy.array(self.peaks[0])

            self.samples = list(samples)
            with open(self.wavefile, 'wb') as wavefile:
                numpy.save(wavefile, samples)

        if proxy and not proxy.get_error():
            proxy_wavefile = get_wavefile_location_for_uri(proxy.get_id())
            self.debug("symlinking %s and %s", self.wavefile, proxy_wavefile)
            try:
                os.remove(proxy_wavefile)
            except FileNotFoundError:
                pass
            os.symlink(self.wavefile, proxy_wavefile)


Gst.Element.register(None, "waveformbin", Gst.Rank.NONE,
                     WaveformPreviewer)
Gst.Element.register(None, "thumbnailbin", Gst.Rank.NONE,
                     ThumbnailBin)
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


class Previewer(Gtk.Layout):
    """Base class for previewers.

    Attributes:
        track_type (GES.TrackType): The type of content.
    """

    # We only need one PreviewGeneratorManager to manage all previewers.
    manager = PreviewGeneratorManager()

    def __init__(self, track_type, max_cpu_usage):
        Gtk.Layout.__init__(self)

        self.track_type = track_type
        self._max_cpu_usage = max_cpu_usage

    def start_generation(self):
        """Starts preview generation."""
        raise NotImplementedError

    def stop_generation(self):
        """Stops preview generation."""
        raise NotImplementedError

    def become_controlled(self):
        """Lets the PreviewGeneratorManager control our execution."""
        Previewer.manager.add_previewer(self)

    def set_selected(self, selected):
        """Marks this instance as being selected."""
        pass

    def pause_generation(self):
        """Pauses preview generation"""
        pass


class VideoPreviewer(Previewer, Zoomable, Loggable):
    """A video previewer widget, drawing thumbnails.

    Attributes:
        ges_elem (GES.TrackElement): The previewed element.
        thumbs (dict): Maps (quantized) times to Thumbnail widgets.
        thumb_cache (ThumbnailCache): The pixmaps persistent cache.
    """

    # We could define them in Previewer, but for some reason they are ignored.
    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, ges_elem, max_cpu_usage):
        Previewer.__init__(self, GES.TrackType.VIDEO, max_cpu_usage)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.ges_elem = ges_elem

        # Guard against malformed URIs
        self.uri = quote_uri(get_proxy_target(ges_elem).props.id)

        self.__start_id = 0
        self.__preroll_timeout_id = 0
        self._thumb_cb_id = 0

        # The thumbs to be generated.
        self.queue = []
        # The position for which a thumbnail is currently being generated.
        self.position = -1
        # The positions for which we failed to get a pixbuf.
        self.failures = set()
        self._thumb_cb_id = None

        self.thumbs = {}
        self.thumb_height = THUMB_HEIGHT
        self.thumb_width = 0

        self.__image_pixbuf = None
        if not isinstance(ges_elem, GES.ImageSource):
            self.thumb_cache = ThumbnailCache.get(self.uri)
            self._ensure_proxy_thumbnails_cache()
            self.thumb_width, unused_height = self.thumb_cache.image_size
        self.pipeline = None
        self.gdkpixbufsink = None

        self.cpu_usage_tracker = CPUUsageTracker()
        # Initial delay before generating the next thumbnail, in millis.
        self.interval = 500

        # Connect signals and fire things up
        self.ges_elem.connect("notify::in-point", self._inpoint_changed_cb)
        self.ges_elem.connect("notify::duration", self._duration_changed_cb)

        self.become_controlled()

        self.connect("notify::height-request", self._height_changed_cb)

    def pause_generation(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.READY)

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
        if self._thumb_cb_id is not None:
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
        self._thumb_cb_id = GLib.timeout_add(self.interval,
                                             self._create_next_thumb_cb,
                                             priority=GLib.PRIORITY_LOW)

    def _start_thumbnailing_cb(self):
        if not self.__start_id:
            # Can happen if stopGeneration is called because the clip has been
            # removed from the timeline after the PreviewGeneratorManager
            # started this job.
            return False

        self.__start_id = None

        if isinstance(self.ges_elem, GES.ImageSource):
            self.debug("Generating thumbnail for image: %s", path_from_uri(self.uri))
            self.__image_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                Gst.uri_get_location(self.uri), -1, self.thumb_height, True)
            self.thumb_width = self.__image_pixbuf.props.width
            self._update_thumbnails()
            self.emit("done")
        else:
            if not self.thumb_width:
                self.debug("Finding thumb width")
                self._setup_pipeline()
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
        self._thumb_cb_id = None

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

    @property
    def thumb_interval(self):
        """Gets the interval for which a thumbnail is displayed.

        Returns:
            int: a duration in nanos, multiple of THUMB_PERIOD.
        """
        interval = Zoomable.pixelToNs(self.thumb_width + THUMB_MARGIN_PX)
        # Make sure the thumb interval is a multiple of THUMB_PERIOD.
        quantized = quantize(interval, THUMB_PERIOD)
        # Make sure the quantized thumb interval fits
        # the thumb and the margin.
        if quantized < interval:
            quantized += THUMB_PERIOD
        # Make sure we don't show thumbs more often than THUMB_PERIOD.
        return max(THUMB_PERIOD, quantized)

    def _update_thumbnails(self):
        """Updates the thumbnail widgets for the clip at the current zoom."""
        if not self.thumb_width:
            # The thumb_width will be available when pipeline has been started
            # or the __image_pixbuf is ready.
            return

        thumbs = {}
        queue = []
        interval = self.thumb_interval
        element_left = quantize(self.ges_elem.props.in_point, interval)
        element_right = self.ges_elem.props.in_point + self.ges_elem.props.duration
        y = (self.props.height_request - self.thumb_height) / 2
        for position in range(element_left, element_right, interval):
            x = Zoomable.nsToPixel(position) - self.nsToPixel(self.ges_elem.props.in_point)
            try:
                thumb = self.thumbs.pop(position)
                self.move(thumb, x, y)
            except KeyError:
                thumb = Thumbnail(self.thumb_width, self.thumb_height)
                self.put(thumb, x, y)

            thumbs[position] = thumb
            if isinstance(self.ges_elem, GES.ImageSource):
                thumb.set_from_pixbuf(self.__image_pixbuf)
                thumb.set_visible(True)
            elif position in self.thumb_cache:
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

    def _set_pixbuf(self, pixbuf):
        """Sets the pixbuf for the thumbnail at the expected position."""
        position = self.position
        self.position = -1

        try:
            thumb = self.thumbs[position]
        except KeyError:
            # Can happen because we don't stop the pipeline before
            # updating the thumbnails in _update_thumbnails.
            return
        thumb.set_from_pixbuf(pixbuf)
        self.thumb_cache[position] = pixbuf
        self.queue_draw()

    def zoomChanged(self):
        self._update_thumbnails()

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
                self._set_pixbuf(pixbuf)
        elif message.src == self.pipeline and \
                message.type == Gst.MessageType.ASYNC_DONE:
            if self.position >= 0:
                self.warning("Thumbnail generation failed at %s", self.position)
                self.failures.add(self.position)
                self.position = -1
            self._schedule_next_thumb_generation()
        return Gst.BusSyncReply.PASS

    def __preroll_timed_out_cb(self):
        self.stop_generation()

    # pylint: disable=no-self-use
    def _autoplug_select_cb(self, unused_decode, unused_pad, unused_caps, factory):
        # Don't plug audio decoders / parsers.
        if "Audio" in factory.get_klass():
            return True
        return False

    def _height_changed_cb(self, unused_widget, unused_param_spec):
        self._update_thumbnails()

    def _inpoint_changed_cb(self, unused_ges_timeline_element, unused_param_spec):
        """Handles the changing of the in-point of the clip."""
        self._update_thumbnails()

    def _duration_changed_cb(self, unused_ges_timeline_element, unused_param_spec):
        """Handles the changing of the duration of the clip."""
        self._update_thumbnails()

    def set_selected(self, selected):
        if selected:
            opacity = 0.5
        else:
            opacity = 1.0

        for thumb in self.get_children():
            thumb.props.opacity = opacity

    def start_generation(self):
        self.debug("Waiting for UI to become idle for: %s",
                   path_from_uri(self.uri))
        self.__start_id = GLib.idle_add(self._start_thumbnailing_cb,
                                        priority=GLib.PRIORITY_LOW)

    def _ensure_proxy_thumbnails_cache(self):
        """Ensures that both the target asset and the proxy assets have caches."""
        uri = quote_uri(self.ges_elem.props.uri)
        if self.uri != uri:
            self.thumb_cache.copy(uri)

    def stop_generation(self):
        if self.__start_id:
            # Cancel the starting.
            GLib.source_remove(self.__start_id)
            self.__start_id = None

        if self.__preroll_timeout_id:
            # Stop waiting for the pipeline to be ready.
            GLib.source_remove(self.__preroll_timeout_id)
            self.__preroll_timeout_id = None

        if self._thumb_cb_id:
            # Cancel the thumbnailing.
            GLib.source_remove(self._thumb_cb_id)
            self._thumb_cb_id = None

        if self.pipeline:
            self.pipeline.get_bus().remove_signal_watch()
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
            self.pipeline = None

        self._ensure_proxy_thumbnails_cache()
        self.emit("done")

    def release(self):
        """Stops preview generation and cleans the object."""
        self.stop_generation()
        Zoomable.__del__(self)


class Thumbnail(Gtk.Image):
    """Simple widget representing a Thumbnail."""

    def __init__(self, width, height):
        Gtk.Image.__init__(self)
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
        self._filehash = hash_file(Gst.uri_get_location(uri))
        thumbs_cache_dir = get_dir(os.path.join(xdg_cache_home(), "thumbs"))
        self._dbfile = os.path.join(thumbs_cache_dir, self._filehash)
        self._db = sqlite3.connect(self._dbfile)
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

        if uri not in cls.caches_by_uri:
            cls.caches_by_uri[uri] = ThumbnailCache(uri)
        return cls.caches_by_uri[uri]

    def copy(self, uri):
        """Copies `self` to the specified `uri`.

        Args:
            uri (str): The place where to copy/save the ThumbnailCache
        """
        filehash = hash_file(Gst.uri_get_location(uri))
        thumbs_cache_dir = get_dir(os.path.join(xdg_cache_home(), "thumbs"))
        dbfile = os.path.join(thumbs_cache_dir, filehash)

        try:
            os.remove(dbfile)
        except FileNotFoundError:
            pass
        os.symlink(self._dbfile, dbfile)

    @property
    def image_size(self):
        """Gets the image size.

        Returns:
            List[int]: The width and height of the images in the cache.
        """
        if self._image_size[0] is 0:
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
        self.log("Saved thumbnail cache file: %s", self._filehash)


def get_wavefile_location_for_uri(uri):
    """Computes the URI where the wave.npy file should be stored."""
    filename = hash_file(Gst.uri_get_location(uri)) + ".wave.npy"
    cache_dir = get_dir(os.path.join(xdg_cache_home(), "waves"))

    return os.path.join(cache_dir, filename)


class AudioPreviewer(Previewer, Zoomable, Loggable):
    """Audio previewer using the results from the "level" GStreamer element."""

    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, ges_elem, max_cpu_usage):
        Previewer.__init__(self, GES.TrackType.AUDIO, max_cpu_usage)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.pipeline = None
        self._wavebin = None

        self.discovered = False
        self.ges_elem = ges_elem

        asset = self.ges_elem.get_parent().get_asset()
        self.n_samples = asset.get_duration() / SAMPLE_DURATION
        self.samples = None
        self.peaks = None
        self._start = 0
        self._end = 0
        self._surface_x = 0

        # Guard against malformed URIs
        self.wavefile = None
        self._uri = quote_uri(get_proxy_target(ges_elem).props.id)

        self._num_failures = 0
        self.adapter = None
        self.surface = None

        self._force_redraw = True

        self.ges_elem.connect("notify::in-point", self._inpoint_changed_cb)
        self.connect("notify::height-request", self._height_changed_cb)
        self.become_controlled()

    def _inpoint_changed_cb(self, unused_b_element, unused_value):
        self._force_redraw = True

    def _height_changed_cb(self, unused_widget, unused_param_spec):
        self._force_redraw = True

    def _startLevelsDiscovery(self):
        filename = get_wavefile_location_for_uri(self._uri)

        if os.path.exists(filename):
            with open(filename, "rb") as samples:
                self.samples = list(numpy.load(samples))
            self._startRendering()
        else:
            self.wavefile = filename
            self._launchPipeline()

    def _launchPipeline(self):
        self.debug(
            'Now generating waveforms for: %s', path_from_uri(self._uri))
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

        self.n_samples = asset.get_duration() / SAMPLE_DURATION
        bus.connect("message", self._busMessageCb)

    def zoomChanged(self):
        self._force_redraw = True

    def _prepareSamples(self):
        proxy = self.ges_elem.get_parent().get_asset().get_proxy_target()
        self._wavebin.finalize(proxy=proxy)
        self.samples = self._wavebin.samples

    def _startRendering(self):
        self.n_samples = len(self.samples)
        self.discovered = True
        if self.adapter:
            self.adapter.stop()
        self.queue_draw()

    def _busMessageCb(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self._prepareSamples()
            self._startRendering()
            self.stop_generation()

        elif message.type == Gst.MessageType.ERROR:
            if self.adapter:
                self.adapter.stop()
                self.adapter = None
            # Something went wrong TODO : recover
            self.stop_generation()
            self._num_failures += 1
            if self._num_failures < 2:
                self.warning("Issue during waveforms generation: %s"
                             " for the %ith time, trying again with no rate "
                             " modulation", message.parse_error(),
                             self._num_failures)
                bus.disconnect_by_func(self._busMessageCb)
                self._launchPipeline()
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

    def _get_num_inpoint_samples(self):
        if self.ges_elem.props.in_point:
            asset_duration = self.ges_elem.get_asset().get_filesource_asset().get_duration()
            return int(self.n_samples / (float(asset_duration) / float(self.ges_elem.props.in_point)))

        return 0

    # pylint: disable=arguments-differ
    def do_draw(self, context):
        if not self.discovered:
            return

        clipped_rect = Gdk.cairo_get_clip_rectangle(context)[1]

        num_inpoint_samples = self._get_num_inpoint_samples()
        drawn_start = self.pixelToNs(clipped_rect.x)
        drawn_duration = self.pixelToNs(clipped_rect.width)
        start = int(drawn_start / SAMPLE_DURATION) + num_inpoint_samples
        end = int((drawn_start + drawn_duration) / SAMPLE_DURATION) + num_inpoint_samples

        if self._force_redraw or self._surface_x > clipped_rect.x or self._end < end:
            self._start = start
            end = int(min(self.n_samples, end + (self.pixelToNs(MARGIN) /
                                                 SAMPLE_DURATION)))
            self._end = end
            self._surface_x = clipped_rect.x
            surface_width = min(self.props.width_request - clipped_rect.x,
                                clipped_rect.width + MARGIN)
            surface_height = int(self.get_parent().get_allocation().height)
            self.surface = renderer.fill_surface(self.samples[start:end],
                                                 surface_width,
                                                 surface_height)

            self._force_redraw = False

        context.set_operator(cairo.OPERATOR_OVER)
        context.set_source_surface(self.surface, self._surface_x, 0)
        context.paint()

    def _emit_done_on_idle(self):
        self.emit("done")

    def pause_generation(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.PAUSED)

    def start_generation(self):
        if not self.pipeline:
            self._startLevelsDiscovery()
        else:
            self.pipeline.set_state(Gst.State.PLAYING)

        if not self.pipeline:
            # No need to generate as we loaded pre-generated .wave file.
            GLib.idle_add(self._emit_done_on_idle, priority=GLib.PRIORITY_LOW)
            return

        self.pipeline.set_state(Gst.State.PLAYING)
        if self.adapter is not None:
            self.adapter.start()

    def stop_generation(self):
        if self.adapter is not None:
            self.adapter.stop()
            self.adapter = None

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_bus().disconnect_by_func(self._busMessageCb)
            self.pipeline = None

        self.emit("done")

    def release(self):
        """Stops preview generation and cleans the object."""
        self.stop_generation()
        Zoomable.__del__(self)
