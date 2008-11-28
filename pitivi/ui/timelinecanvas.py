from track import Track
from timelineobject import TimelineObject
import controller
import view
from point import Point
import goocanvas
from zoominterface import Zoomable
from pitivi.receiver import receiver, handler
import gtk

# cursors to be used for resizing objects
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
# TODO: replace this with custom cursor
RAZOR_CURSOR = gtk.gdk.Cursor(gtk.gdk.XTERM)

# FIXME: do we want this expressed in pixels or miliseconds?
# If we express it in miliseconds, then we can have the core handle edge
# snapping (it's really best implemented in the core). On the other hand, if
# the dead-band is a constant unit of time, it will be too large at high zoom,
# and too small at low zoom. So we might want to be able to adjust the
# deadband from the UI.
# default number of pixels to use for edge snaping
DEADBAND = 5

class TimelineCanvas(goocanvas.Canvas, Zoomable):

    __tracks = None

    def __init__(self, timeline):
        goocanvas.Canvas.__init__(self)
        Zoomable.__init__(self)
        self._selected_sources = []
        self.__tracks = [] 

        self._block_size_request = False
        self.props.integer_layout = True
        self.props.automatic_bounds = False

        self._createUI()
        self.timeline = timeline
       
    def _createUI(self):
        self._cursor = ARROW
        root = self.get_root_item()

        self.tracks = goocanvas.Group()
        root.add_child(self.tracks)

        root.connect("enter_notify_event", self._mouseEnterCb)
        self._marquee = goocanvas.Rect(
            line_width=0,
            fill_color="orange",
            width=1)

        self._razor = goocanvas.Rect(
            stroke_color_rgba=0x33CCFF66,
            fill_color_rgba=0x33CCFF66)
        self._razor.props.visibility = goocanvas.ITEM_INVISIBLE
        root.add_child(self._razor)

## mouse callbacks

    def _mouseEnterCb(self, unused_item, unused_target, event):
        event.window.set_cursor(self._cursor)
        return True

## Razor Tool Implementation

    def activateRazor(self, unused_action):
        self._cursor = RAZOR_CURSOR
        self._razor_sigid = self.connect("button_press_event", 
            self._razorClickedCb)
        self._razor_release_sigid = self.connect("button_release_event",
            self._razorReleasedCb)
        self._razor_motion_sigid = self.connect("motion_notify_event",
            self._razorMovedCb)
        self._razor.props.visibility = goocanvas.ITEM_VISIBLE
        return True

    def _razorMovedCb(self, canvas, event):
        x, y = self.convert_from_pixels(event.x, event.y)
        self._razor.props.x = self.nsToPixel(self.pixelToNs(x))
        return True

    def _razorReleasedCb(self, unused_canvas, event):
        self._cursor = ARROW
        event.window.set_cursor(ARROW)
        self.disconnect(self._razor_sigid)
        self.disconnect(self._razor_motion_sigid)
        self.disconnect(self._razor_release_sigid)
        self._razor.props.visibility = goocanvas.ITEM_INVISIBLE

        x, y = self.convert_from_pixels(event.x, event.y)
        bounds = goocanvas.Bounds(x, y, x, y)
        items = self.get_items_in_area(bounds, True, True, True)
        if items:
            for item in items:
                if isinstance(item, TimelineObject):
                    self.timeline.splitObject(item.element, self.pixelToNs(x))
        return True

    def _razorClickedCb(self, unused_canvas, unused_event):
        return True

## Zoomable Override

    def zoomChanged(self):
        if self.timeline:
            self.timeline.setDeadband(self.pixelToNs(DEADBAND))

## Timeline callbacks

    def __set_timeline(self):
        while self.__tracks:
            self._trackRemoved(None, 0)
        if self.timeline:
            for track in self.timeline.tracks:
                self._trackAdded(None, track, -1)

    timeline = receiver(__set_timeline)

    @handler(timeline, "start-duration-changed")
    def _request_size(self, unused_item, start, duration):
        tl, br = Point.from_widget_bounds(self)
        pw, ph = br - tl
        tl, br = Point.from_item_bounds(self.tracks)
        w, h = br - tl
        if (w > pw) or (h > ph):
            self.set_bounds(0, 0, w + 200, h)
        self._razor.props.height = h

    @handler(timeline, "track-added")
    def _trackAdded(self, unused_timeline, comp, position):
        track = Track(comp=comp)
        self.__tracks.append(track)
        track.set_canvas(self)
        self.tracks.add_child(track)
        self._regroup_tracks()

    @handler(timeline, "track-removed")
    def _trackRemoved(self, unused_timeline, position):
        track = self.__tracks[position]
        del self.__tracks[position]
        track.remove()
        self._regroup_tracks()

    def _regroup_tracks(self):
        for i, track in enumerate(self.__tracks):
            # FIXME: hard-coding track height, because this won't be updated
            # later
            height = 50
            track.set_simple_transform(0, i * (height + 10), 1, 0)
