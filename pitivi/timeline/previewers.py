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
import os
import pickle
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
from pitivi.settings import xdg_cache_home
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import binary_search
from pitivi.utils.misc import get_proxy_target
from pitivi.utils.misc import hash_file
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import quantize
from pitivi.utils.misc import quote_uri
from pitivi.utils.system import CPUUsageTracker
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import EXPANDED_SIZE

# Our C module optimizing waveforms rendering
try:
    from . import renderer
except ImportError:
    # Running uninstalled?
    import renderer


WAVEFORMS_CPU_USAGE = 30
SAMPLE_DURATION = Gst.SECOND / 100

# A little lower as it's more fluctuating
THUMBNAILS_CPU_USAGE = 20

THUMB_MARGIN_PX = 3
# For the waveforms, ensures we always have a little extra surface when
# scrolling while playing.
MARGIN = 500

PREVIEW_GENERATOR_SIGNALS = {
    "done": (GObject.SIGNAL_RUN_LAST, None, ()),
    "error": (GObject.SIGNAL_RUN_LAST, None, ()),
}

THUMB_HEIGHT = EXPANDED_SIZE - 2 * THUMB_MARGIN_PX


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
        else:
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
    """Bin to generate and save waveforms as a pickle file."""

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
                              "audioconvert ! audioresample ! level name=level"
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
        elif prop.name == 'duration':
            return self.duration
        else:
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
                    return

                for i, val in enumerate(peaks):
                    if val < 0:
                        val = 10 ** (val / 20) * 100
                    else:
                        val = self.peaks[i][pos - 1]

                    # Linearly joins values between to known samples
                    # values
                    unknowns = range(self.prev_pos + 1, pos)
                    if len(unknowns):
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
                pickle.dump(list(samples), wavefile)

        if proxy:
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


# pylint: disable=too-few-public-methods
class PreviewGeneratorManager():
    """Manager for running the previewers."""

    def __init__(self):
        # The current Previewer per GES.TrackType.
        self._current_previewers = {}
        # The queue of Previewers.
        self._previewers = {
            GES.TrackType.AUDIO: [],
            GES.TrackType.VIDEO: []
        }

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
        previewer.startGeneration()

    def __previewer_done_cb(self, previewer):
        track_type = previewer.track_type
        next_previewer = self._current_previewers.pop(track_type, None)
        if next_previewer:
            next_previewer.disconnect_by_func(self.__previewer_done_cb)

        if self._previewers[track_type]:
            self._start_previewer(self._previewers[track_type].pop())


class Previewer(Gtk.Layout):
    """Base class for previewers.

    Attributes:
        track_type (GES.TrackType): The type of content.
    """

    # We only need one PreviewGeneratorManager to manage all previewers.
    __manager = PreviewGeneratorManager()

    def __init__(self, track_type):
        Gtk.Layout.__init__(self)

        self.track_type = track_type

    def startGeneration(self):
        """Starts preview generation."""
        raise NotImplementedError

    def stopGeneration(self):
        """Stops preview generation."""
        raise NotImplementedError

    def becomeControlled(self):
        """Lets the PreviewGeneratorManager control our execution."""
        Previewer.__manager.add_previewer(self)

    def setSelected(self, selected):
        """Marks this instance as being selected."""
        pass


class VideoPreviewer(Previewer, Zoomable, Loggable):
    """A video previewer widget, drawing thumbnails.

    Attributes:
        ges_elem (GES.TrackElement): The previewed element.
        thumbs (dict): Maps (quantized) times to Thumbnail objects.
        thumb_cache (ThumbnailCache): The pixmaps persistent cache.
    """

    # We could define them in Previewer, but for some reason they are ignored.
    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, ges_elem):
        Previewer.__init__(self, GES.TrackType.VIDEO)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        # Variables related to the timeline objects
        self.timeline = ges_elem.get_parent().get_timeline().ui
        self.ges_elem = ges_elem

        # Guard against malformed URIs
        self.uri = quote_uri(get_proxy_target(ges_elem).props.id)

        # Variables related to thumbnailing
        self.wishlist = []
        self.queue = []
        self._thumb_cb_id = None
        self._running = False

        # We should have one thumbnail per thumb_period.
        # TODO: get this from the user settings
        self.thumb_period = int(0.5 * Gst.SECOND)
        self.thumb_height = THUMB_HEIGHT

        self.__image_pixbuf = None
        if isinstance(ges_elem, GES.ImageSource):
            self.__image_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                Gst.uri_get_location(self.uri), -1, self.thumb_height, True)

        self.thumbs = {}
        self.thumb_cache = ThumbnailCache.get(self.uri)
        self._ensure_proxy_thumbnails_cache()
        self.thumb_width, unused_height = self.thumb_cache.getImagesSize()

        self.cpu_usage_tracker = CPUUsageTracker()
        self.interval = 500  # Every 0.5 second, reevaluate the situation

        # Connect signals and fire things up
        self.ges_elem.connect("notify::in-point", self._inpoint_changed_cb)

        self.pipeline = None
        self.gdkpixbufsink = None
        self.becomeControlled()

        self.connect("notify::height-request", self._heightChangedCb)

    # Internal API
    def _setupPipeline(self):
        """Creates the pipeline.

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
        self.pipeline.get_bus().connect("message", self.__bus_message_handler)

    def _checkCPU(self):
        """Adjusts when the next thumbnail is generated.

        Checks the CPU usage and adjusts the waiting time at which the next
        thumbnail will be generated +/- 10%. Even then, it will only
        happen when the gobject loop is idle to avoid blocking the UI.
        """
        usage_percent = self.cpu_usage_tracker.usage()
        if usage_percent < THUMBNAILS_CPU_USAGE:
            self.interval *= 0.9
            self.log(
                'Thumbnailing sped up (+10%%) to a %.1f ms interval for "%s"',
                self.interval, path_from_uri(self.uri))
        else:
            self.interval *= 1.1
            self.log(
                'Thumbnailing slowed down (-10%%) to a %.1f ms interval for "%s"',
                self.interval, path_from_uri(self.uri))
        self.cpu_usage_tracker.reset()
        self._thumb_cb_id = GLib.timeout_add(self.interval,
                                             self._create_next_thumb,
                                             priority=GLib.PRIORITY_LOW)

    def _startThumbnailingWhenIdle(self):
        self.debug(
            'Waiting for UI to become idle for: %s', path_from_uri(self.uri))
        GLib.idle_add(self._startThumbnailing, priority=GLib.PRIORITY_LOW)

    def _startThumbnailing(self):
        if not self.pipeline:
            # Can happen if stopGeneration is called because the clip has been
            # removed from the timeline after the PreviewGeneratorManager
            # started this job.
            return

        self.debug(
            'Now generating thumbnails for: %s', path_from_uri(self.uri))
        query_success, duration = self.pipeline.query_duration(Gst.Format.TIME)
        if not query_success or duration == -1:
            self.debug("Could not determine duration of: %s", self.uri)
            duration = self.ges_elem.props.duration

        self.queue = list(range(0, duration, self.thumb_period))

        self._checkCPU()

        # Save periodically to avoid the common situation where the user exits
        # the app before a long clip has been fully thumbnailed.
        # Spread timeouts between 30-80 secs to avoid concurrent disk writes.
        random_time = random.randrange(30, 80)
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
        self.log('Creating thumb for "%s"', path_from_uri(self.uri))
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
        thumb_duration_tmp = Zoomable.pixelToNs(self.thumb_width + THUMB_MARGIN_PX)
        # quantize thumb length to thumb_period
        thumb_duration = quantize(thumb_duration_tmp, self.thumb_period)
        # make sure that the thumb duration after the quantization isn't
        # smaller than before
        if thumb_duration < thumb_duration_tmp:
            thumb_duration += self.thumb_period
        # make sure that we don't show thumbnails more often than thumb_period
        return max(thumb_duration, self.thumb_period)

    def _update_thumbnails(self):
        """Updates the thumbnails for the currently visible clip portion."""
        if self.thumb_width is None:
            return False

        thumbs = {}
        self.wishlist = []
        thumb_duration = self._get_thumb_duration()
        element_left = quantize(self.ges_elem.props.in_point, thumb_duration)
        element_right = self.ges_elem.props.in_point + self.ges_elem.props.duration
        for position in range(element_left, element_right, thumb_duration):
            x = Zoomable.nsToPixel(position) - self.nsToPixel(self.ges_elem.props.in_point)
            y = (self.props.height_request - self.thumb_height) / 2
            try:
                thumb = self.thumbs.pop(position)
                self.move(thumb, x, y)
            except KeyError:
                thumb = Thumbnail(self.thumb_width, self.thumb_height)
                self.put(thumb, x, y)

            thumbs[position] = thumb
            if self.__image_pixbuf:
                # The thumbnail is fixed, probably it's an image clip.
                thumb.set_from_pixbuf(self.__image_pixbuf)
                thumb.set_visible(True)
            elif position in self.thumb_cache:
                pixbuf = self.thumb_cache[position]
                thumb.set_from_pixbuf(pixbuf)
                thumb.set_visible(True)
            else:
                self.wishlist.append(position)
        for thumb in self.thumbs.values():
            self.remove(thumb)
        self.thumbs = thumbs

        return True

    def _get_wish(self):
        """Returns a wish that is also in the queue, if any."""
        while True:
            if not self.wishlist:
                return None
            wish = self.wishlist.pop(0)
            if wish in self.queue:
                return wish

    def _set_pixbuf(self, position, pixbuf):
        """Sets the pixbuf for the thumbnail at the specified position."""
        if position in self.thumbs:
            thumb = self.thumbs[position]
        else:
            # The pixbufs we get from gdkpixbufsink are not always
            # exactly the ones requested, the reported position can differ.
            # Try to find the closest thumbnail for the specified position.
            sorted_times = sorted(self.thumbs.keys())
            index = binary_search(sorted_times, position)
            position = sorted_times[index]
            thumb = self.thumbs[position]

        thumb.set_from_pixbuf(pixbuf)
        if position in self.queue:
            self.queue.remove(position)
        self.thumb_cache[position] = pixbuf
        self.queue_draw()

    # Interface (Zoomable)

    def zoomChanged(self):
        self._update_thumbnails()

    # Callbacks

    def __bus_message_handler(self, unused_bus, message):
        if message.type == Gst.MessageType.ELEMENT and \
                message.src == self.gdkpixbufsink:
            struct = message.get_structure()
            struct_name = struct.get_name()
            if struct_name == "preroll-pixbuf":
                stream_time = struct.get_value("stream-time")
                pixbuf = struct.get_value("pixbuf")
                self._set_pixbuf(stream_time, pixbuf)
        elif message.type == Gst.MessageType.ASYNC_DONE and \
                message.src == self.pipeline:
            self._checkCPU()
        return Gst.BusSyncReply.PASS

    # pylint: disable=no-self-use
    def _autoplugSelectCb(self, unused_decode, unused_pad, unused_caps, factory):
        # Don't plug audio decoders / parsers.
        if "Audio" in factory.get_klass():
            return True
        return False

    def _heightChangedCb(self, unused_widget, unused_param_spec):
        self._update_thumbnails()

    def _inpoint_changed_cb(self, unused_ges_timeline_element, unused_param_spec):
        self._update_thumbnails()

    def setSelected(self, selected):
        if selected:
            opacity = 0.5
        else:
            opacity = 1.0

        for thumb in self.get_children():
            thumb.props.opacity = opacity

    def startGeneration(self):
        self._setupPipeline()
        self._startThumbnailingWhenIdle()

    def _ensure_proxy_thumbnails_cache(self):
        """Ensures that both the target asset and the proxy assets have caches."""
        uri = self.ges_elem.props.uri
        if self.uri != uri:
            self.thumb_cache.copy(uri)

    def stopGeneration(self):
        if self._thumb_cb_id:
            GLib.source_remove(self._thumb_cb_id)
            self._thumb_cb_id = None

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
            self.pipeline = None

        self._ensure_proxy_thumbnails_cache()
        self.emit("done")

    def release(self):
        """Stops preview generation and cleans the object."""
        self.stopGeneration()
        Zoomable.__del__(self)


class Thumbnail(Gtk.Image):
    """Simple widget representing a Thumbnail."""

    def __init__(self, width, height):
        Gtk.Image.__init__(self)
        self.props.width_request = width
        self.props.height_request = height


class ThumbnailCache(Loggable):
    """Caches an asset's thumbnails by key, using LRU policy.

    Uses a two stage caching mechanism. A limited number of elements are
    held in memory, the rest is being cached on disk in an SQLite db.
    """

    caches_by_uri = {}

    def __init__(self, uri):
        Loggable.__init__(self)
        self._filehash = hash_file(Gst.uri_get_location(uri))
        thumbs_cache_dir = get_dir(os.path.join(xdg_cache_home(), "thumbs"))
        self._dbfile = os.path.join(thumbs_cache_dir, self._filehash)
        self._db = sqlite3.connect(self._dbfile)
        self._cur = self._db.cursor()  # Use this for normal db operations
        self._cur.execute("CREATE TABLE IF NOT EXISTS Thumbs\
                          (Time INTEGER NOT NULL PRIMARY KEY,\
                          Jpeg BLOB NOT NULL)")

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

    def getImagesSize(self):
        """Gets the image size.

        Returns:
            List[int]: The width and height of the images in the cache.
        """
        self._cur.execute("SELECT * FROM Thumbs LIMIT 1")
        row = self._cur.fetchone()
        if not row:
            return None, None

        pixbuf = self.__getPixbufFromRow(row)
        return pixbuf.get_width(), pixbuf.get_height()

    def getPreviewThumbnail(self):
        """Gets a thumbnail contained 'at the middle' of the cache."""
        self._cur.execute("SELECT Time FROM Thumbs")
        timestamps = self._cur.fetchall()
        if not timestamps:
            return None

        return self[timestamps[int(len(timestamps) / 2)][0]]

    # pylint: disable=no-self-use
    def __getPixbufFromRow(self, row):
        jpeg = row[1]
        loader = GdkPixbuf.PixbufLoader.new()
        # TODO: what do to if any of the following calls fails?
        loader.write(jpeg)
        loader.close()
        pixbuf = loader.get_pixbuf()
        return pixbuf

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
        return self.__getPixbufFromRow(row)

    def __setitem__(self, key, value):
        success, jpeg = value.save_to_bufferv(
            "jpeg", ["quality", None], ["90"])
        if not success:
            self.warning("JPEG compression failed")
            return
        blob = sqlite3.Binary(jpeg)
        # Replace if a row with the same time already exists.
        self._cur.execute("DELETE FROM Thumbs WHERE  time=?", (key,))
        self._cur.execute("INSERT INTO Thumbs VALUES (?,?)", (key, blob,))

    def commit(self):
        """Saves the cache on disk (in the database)."""
        self._db.commit()
        self.log("Saved thumbnail cache file: %s" % self._filehash)

        return False


class PipelineCpuAdapter(Loggable):
    """Pipeline manager modulating the rate of the provided pipeline.

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
        self.last_pos = 0
        self._bus_cb_id = None

    def start(self):
        """Start modulating the rate on the controlled pipeline.

        This avoid using too much CPU.
        """
        GLib.timeout_add(200, self._modulateRate)
        self._bus_cb_id = self.bus.connect("message", self._messageCb)
        self.done = False

    def stop(self):
        """Stops modulating the rate on the controlled pipeline."""
        if self._bus_cb_id is not None:
            self.bus.disconnect(self._bus_cb_id)
            self._bus_cb_id = None
        self.pipeline = None
        self.done = True

    def _modulateRate(self):
        """Adapts the rate of audio analysis depending on CPU usage."""
        if self.done:
            return False

        usage_percent = self.cpu_usage_tracker.usage()
        self.cpu_usage_tracker.reset()
        if usage_percent >= WAVEFORMS_CPU_USAGE:
            if self.rate < 0.1:
                if not self.ready:
                    res, position = self.pipeline.query_position(
                        Gst.Format.TIME)
                    if res:
                        self.last_pos = position
                    self.pipeline.set_state(Gst.State.READY)
                    self.ready = True
                return True

            if self.rate > 0.0:
                self.rate *= 0.9
                self.log(
                    'Pipeline rate slowed down (-10%%) to %.3f' % self.rate)
        else:
            self.rate *= 1.1
            self.log('Pipeline rate sped up (+10%%) to %.3f' % self.rate)

        if not self.ready:
            res, position = self.pipeline.query_position(Gst.Format.TIME)
            assert res
        else:
            # This to avoid going back and forth from READY to PAUSED
            if self.rate > 0.5:
                # The message handler will unset ready and seek correctly.
                self.pipeline.set_state(Gst.State.PAUSED)
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

    def _messageCb(self, unused_bus, message):
        if not self.ready:
            return
        if message.type == Gst.MessageType.STATE_CHANGED:
            prev, new, unused_pending_state = message.parse_state_changed()
            if message.src == self.pipeline:
                if prev == Gst.State.READY and new == Gst.State.PAUSED:
                    self.pipeline.seek(1.0,
                                       Gst.Format.TIME,
                                       Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                                       Gst.SeekType.SET,
                                       self.last_pos,
                                       Gst.SeekType.NONE,
                                       -1)
                    self.ready = False


def get_wavefile_location_for_uri(uri):
    """Computes the URI where the pickled wave file should be stored."""
    filename = hash_file(Gst.uri_get_location(uri)) + ".wave"
    cache_dir = get_dir(os.path.join(xdg_cache_home(), "waves"))

    return os.path.join(cache_dir, filename)


class AudioPreviewer(Previewer, Zoomable, Loggable):
    """Audio previewer using the results from the "level" GStreamer element."""

    __gsignals__ = PREVIEW_GENERATOR_SIGNALS

    def __init__(self, ges_elem):
        Previewer.__init__(self, GES.TrackType.AUDIO)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.pipeline = None
        self._wavebin = None

        self.discovered = False
        self.ges_elem = ges_elem
        self.timeline = ges_elem.get_parent().get_timeline().ui

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

    def _inpoint_changed_cb(self, unused_b_element, unused_value):
        self._force_redraw = True

    def _height_changed_cb(self, unused_widget, unused_param_spec):
        self._force_redraw = True

    def startLevelsDiscoveryWhenIdle(self):
        """Starts processing waveform (whenever possible)."""
        self.debug('Waiting for UI to become idle for: %s',
                   path_from_uri(self._uri))
        GLib.idle_add(self._startLevelsDiscovery, priority=GLib.PRIORITY_LOW)

    def _startLevelsDiscovery(self):
        filename = get_wavefile_location_for_uri(self._uri)

        if os.path.exists(filename):
            with open(filename, "rb") as samples:
                self.samples = pickle.load(samples)
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
        faked = self.pipeline.get_by_name("faked")
        faked.props.sync = True
        self._wavebin = self.pipeline.get_by_name("wave")
        asset = self.ges_elem.get_parent().get_asset()
        self._wavebin.props.uri = asset.get_id()
        self._wavebin.props.duration = asset.get_duration()
        decode = self.pipeline.get_by_name("decode")
        decode.connect("autoplug-select", self._autoplugSelectCb)
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()

        asset = self.ges_elem.get_parent().get_asset()
        self.n_samples = asset.get_duration() / SAMPLE_DURATION
        bus.connect("message", self._busMessageCb)
        self.becomeControlled()

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

    def _busMessageCb(self, bus, message):
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
                bus.disconnect_by_func(self._busMessageCb)
                self._launchPipeline()
                self.becomeControlled()
            else:
                Gst.debug_bin_to_dot_file_with_ts(self.pipeline,
                                                  Gst.DebugGraphDetails.ALL,
                                                  "error-generating-waveforms")
                self.error("Aborting due to waveforms generation issue: %s",
                           message.parse_error())

        elif message.type == Gst.MessageType.STATE_CHANGED:
            prev, new, unused_pending_state = message.parse_state_changed()
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

    # pylint: disable=no-self-use
    def _autoplugSelectCb(self, unused_decode, unused_pad, unused_caps, factory):
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

    def startGeneration(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        if self.adapter is not None:
            self.adapter.start()

    def stopGeneration(self):
        if self.adapter is not None:
            self.adapter.stop()
            self.adapter = None

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)

        self.emit("done")

    def release(self):
        """Stops preview generation and cleans the object."""
        self.stopGeneration()
        Zoomable.__del__(self)
