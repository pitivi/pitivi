import hashlib
import os
import sqlite3
import sys
import xdg.BaseDirectory as xdg_dirs

from gi.repository import Clutter, Gst, GLib, GdkPixbuf, Cogl
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import EXPANDED_SIZE, SPACING

BORDER_WIDTH = 3  # For the timeline elements


"""
Convention throughout this file:
Every GES element which name could be mistaken with a UI element
is prefixed with a little b, example : bTimeline
"""


class VideoPreviewer(Clutter.ScrollActor, Zoomable):
    def __init__(self, bElement, timeline):
        """
        @param bElement : the backend GES.TrackElement
        @param track : the track to which the bElement belongs
        @param timeline : the containing graphic timeline.
        """
        Zoomable.__init__(self)
        Clutter.ScrollActor.__init__(self)

        self.uri = bElement.props.uri

        self.bElement = bElement
        self.timeline = timeline

        self.bElement.connect("notify::duration", self.duration_changed)
        self.bElement.connect("notify::in-point", self._inpoint_changed_cb)
        self.bElement.connect("notify::start", self.start_changed)

        self.timeline.connect("scrolled", self._scroll_changed)

        self.duration = self.bElement.props.duration

        self.thumb_margin = BORDER_WIDTH
        self.thumb_height = EXPANDED_SIZE - 2 * self.thumb_margin
        # self.thumb_width will be set by self._setupPipeline()

        # TODO: read this property from the settings
        self.thumb_period = long(0.5 * Gst.SECOND)

        # maps (quantized) times to Thumbnail objects
        self.thumbs = {}

        self.thumb_cache = get_cache_for_uri(self.uri)

        self.wishlist = []

        self._setupPipeline()

        self._startThumbnailing()

        self.callback_id = None

        self.counter = 0

        self._allAnimated = False

    # Internal API

    def _scroll_changed(self, unused):
        self._update()

    def start_changed(self, unused_bElement, unused_value):
        self._update()

    def _update(self, unused_msg_source=None):
        if self.callback_id:
            GLib.source_remove(self.callback_id)
        self.callback_id = GLib.idle_add(self._addVisibleThumbnails, priority=GLib.PRIORITY_LOW)

    def _setupPipeline(self):
        """
        Create the pipeline.

        It has the form "playbin ! thumbnailsink" where thumbnailsink
        is a Bin made out of "videorate ! capsfilter ! gdkpixbufsink"
        """
        # TODO: don't hardcode framerate
        self.pipeline = Gst.parse_launch(
            "uridecodebin uri={uri} ! "
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

        # pop all messages from the bus so we won't be flooded with messages
        # from the prerolling phase
        while self.pipeline.get_bus().pop():
            continue
        # add a message handler that listens for the created pixbufs
        self.pipeline.get_bus().add_signal_watch()
        self.pipeline.get_bus().connect("message", self.bus_message_handler)

    def _startThumbnailing(self):
        self.queue = []
        query_success, duration = self.pipeline.query_duration(Gst.Format.TIME)
        if not query_success:
            print("Could not determine the duration of the file {}".format(self.uri))
            duration = self.duration
        else:
            self.duration = duration

        current_time = 0
        while current_time < duration:
            self.queue.append(current_time)
            current_time += self.thumb_period

        self._create_next_thumb()

    def _create_next_thumb(self):
        if not self.queue:
            # nothing left to do
            self.thumb_cache.commit()
            return
        wish = self._get_wish()
        if wish:
            time = wish
            self.queue.remove(wish)
        else:
            time = self.queue.pop(0)
        # append the time to the end of the queue so that if this seek fails
        # another try will be started later
        self.queue.append(time)

        self.pipeline.seek(1.0,
            Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
            Gst.SeekType.SET, time,
            Gst.SeekType.NONE, -1)

    def _addVisibleThumbnails(self):
        self.remove_all_children()
        old_thumbs = self.thumbs.copy()
        self.thumbs = {}
        self.wishlist = []

        thumb_duration_tmp = Zoomable.pixelToNs(self.thumb_width + self.thumb_margin)

        # quantize thumb length to thumb_period
        # TODO: replace with a call to utils.misc.quantize:
        thumb_duration = (thumb_duration_tmp // self.thumb_period) * self.thumb_period
        # make sure that the thumb duration after the quantization isn't smaller than before
        if thumb_duration < thumb_duration_tmp:
            thumb_duration += self.thumb_period

        # make sure that we don't show thumbnails more often than thumb_period
        thumb_duration = max(thumb_duration, self.thumb_period)

        element_left, element_right = self._get_visible_range()
        # TODO: replace with a call to utils.misc.quantize:
        element_left = (element_left // thumb_duration) * thumb_duration

        current_time = element_left
        while current_time < element_right:
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
            current_time += thumb_duration
        self._allAnimated = False
        self.counter += 1
        print(self.counter)

    def _inpoint_changed_cb(self, unused_bElement, unused_value):
        position = Clutter.Point()
        position.x = Zoomable.nsToPixel(self.bElement.props.in_point)
        self.scroll_to_point(position)
        self._update()

    def _get_wish(self):
        """Returns a wish that is also in the queue or None
           if no such wish exists"""
        while True:
            if not self.wishlist:
                return None
            wish = self.wishlist.pop(0)
            if wish in self.queue:
                return wish

    def _setThumbnail(self, time, thumbnail):
        # TODO: is "time" guaranteed to be nanosecond precise?
        # => __tim says: "that's how it should be"
        # => also see gst-plugins-good/tests/icles/gdkpixbufsink-test
        # => Daniel: It is *not* nanosecond precise when we remove the videorate
        #            element from the pipeline
        if time in self.queue:
            self.queue.remove(time)

        self.thumb_cache[time] = thumbnail

        if time in self.thumbs:
            self.thumbs[time].set_from_gdkpixbuf_animated(thumbnail)

    # Interface (Zoomable)

    def zoomChanged(self):
        self.remove_all_children()
        self._allAnimated = True
        self._update()

    def _get_visible_range(self):
        timeline_left, timeline_right = self._get_visible_timeline_range()
        element_left = timeline_left - self.bElement.props.start + self.bElement.props.in_point
        element_left = max(element_left, self.bElement.props.in_point)

        element_right = timeline_right - self.bElement.props.start + self.bElement.props.in_point
        element_right = min(element_right, self.bElement.props.in_point + self.bElement.props.duration)

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
                self._setThumbnail(struct.get_value("stream-time"), struct.get_value("pixbuf"))
        elif message.type == Gst.MessageType.ASYNC_DONE:
            self._create_next_thumb()
        return Gst.BusSyncReply.PASS

    def duration_changed(self, unused_bElement, unused_value):
        new_duration = max(self.duration, self.bElement.props.duration)
        if new_duration > self.duration:
            self.duration = new_duration
            self._update()


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

    def set_from_gdkpixbuf(self, gdkpixbuf):
        row_stride = gdkpixbuf.get_rowstride()
        pixel_data = gdkpixbuf.get_pixels()
        alpha = gdkpixbuf.get_has_alpha()
        if alpha:
            self.props.content.set_data(pixel_data, Cogl.PixelFormat.RGBA_8888, self.width, self.height, row_stride)
        else:
            self.props.content.set_data(pixel_data, Cogl.PixelFormat.RGB_888, self.width, self.height, row_stride)
        self.set_opacity(255)

    def set_from_gdkpixbuf_animated(self, gdkpixbuf):
        self.save_easing_state()
        self.set_easing_duration(750)
        self.set_from_gdkpixbuf(gdkpixbuf)
        self.restore_easing_state()


# TODO: replace with utils.misc.hash_file
def hash_file(uri):
    """Hashes the first 256KB of the specified file"""
    sha256 = hashlib.sha256()
    with open(uri, "rb") as file:
        for _ in range(1024):
            chunk = file.read(256)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()

# TODO: remove eventually
autocreate = True


# TODO: replace with pitivi.settings.get_dir
def get_dir(path, autocreate=True):
    if autocreate and not os.path.exists(path):
        os.makedirs(path)
    return path


caches = {}


def get_cache_for_uri(uri):
    if uri in caches:
        return caches[uri]
    else:
        cache = ThumbnailCache(uri)
        caches[uri] = cache
        return cache


class ThumbnailCache(object):

    """Caches thumbnails by key using LRU policy, implemented with heapq.

    Uses a two stage caching mechanism. A limited number of elements are
    held in memory, the rest is being cached on disk using an sqlite db."""

    def __init__(self, uri):
        object.__init__(self)
        # TODO: replace with utils.misc.hash_file
        filehash = hash_file(Gst.uri_get_location(uri))
        # TODO: replace with pitivi.settings.xdg_cache_home()
        cache_dir = get_dir(os.path.join(xdg_dirs.xdg_cache_home, "pitivi"), autocreate)
        dbfile = os.path.join(get_dir(os.path.join(cache_dir, "thumbs")), filehash)
        self.conn = sqlite3.connect(dbfile)
        self.cur = self.conn.cursor()
        self.cur.execute("CREATE TABLE IF NOT EXISTS Thumbs\
                          (Time INTEGER NOT NULL PRIMARY KEY,\
                          Jpeg BLOB NOT NULL)")

    def __contains__(self, key):
        # check if item is present in on disk cache
        self.cur.execute("SELECT Time FROM Thumbs WHERE Time = ?", (key,))
        if self.cur.fetchone():
            return True
        return False

    def __getitem__(self, key):
        self.cur.execute("SELECT * FROM Thumbs WHERE Time = ?", (key,))
        row = self.cur.fetchone()
        if row:
            jpeg = row[1]
            loader = GdkPixbuf.PixbufLoader.new()
            # TODO: what do to if any of the following calls fails?
            loader.write(jpeg)
            loader.close()
            pixbuf = loader.get_pixbuf()
            return pixbuf
        raise KeyError(key)

    def __setitem__(self, key, value):
        success, jpeg = value.save_to_bufferv("jpeg", ["quality", None], ["90"])
        if not success:
            self.warning("JPEG compression failed")
            return
        blob = sqlite3.Binary(jpeg)
        #Replace if the key already existed
        self.cur.execute("DELETE FROM Thumbs WHERE  time=?", (key,))
        self.cur.execute("INSERT INTO Thumbs VALUES (?,?)", (key, blob,))
        #self.conn.commit()

    def commit(self):
        print("commit")
        self.conn.commit()
