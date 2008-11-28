from track import Track
from point import Point
import goocanvas
from zoominterface import Zoomable
import pitivi.instance as instance
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
        #manage_selection(self, self._marquee, True, self._selection_changed_cb)

        self._razor = goocanvas.Rect(
            stroke_color_rgba=0x33CCFF66,
            fill_color_rgba=0x33CCFF66)
        self._razor.props.visibility = goocanvas.ITEM_INVISIBLE
        root.add_child(self._razor)

## mouse callbacks

    def _mouseEnterCb(self, unused_item, unused_target, event):
        event.window.set_cursor(self._cursor)
        return True

## Editing Operations

    # FIXME: the razor is the one toolbar tool that violates the noun-verb
    # principle. Do I really want to make an exception for this? What about
    # just double-clicking on the source like jokosher?

    def activateRazor(self, unused_action):
        self._cursor = RAZOR_CURSOR
        # we don't want mouse events passing through to the canvas items
        # underneath, so we connect to the canvas's signals
        self._razor_sigid = self.connect("button_press_event", 
            self._razorClickedCb)
        self._razor_motion_sigid = self.connect("motion_notify_event",
            self._razorMovedCb)
        self._razor.props.visibility = goocanvas.ITEM_VISIBLE
        return True

    def _razorMovedCb(self, canvas, event):
        x, y = event_coords(self, event)
        self._razor.props.x = self.nsToPixel(self.pixelToNs(x))
        return True

    def _razorClickedCb(self, unused_canvas, event):
        self._cursor = ARROW
        event.window.set_cursor(ARROW)
        self.disconnect(self._razor_sigid)
        self.disconnect(self._razor_motion_sigid)
        self._razor.props.visibility = goocanvas.ITEM_INVISIBLE

        # Find the topmost source under the mouse. This is tricky because not
        # all objects in the timeline are TimelineObjects. Some of them
        # are drag handles, for example. For now, only objects marked as
        # selectable should be sources
        x, y = event_coords(self, event)
        items = self.get_items_at(x, y, True)
        if not items:
            return True
        for item in items:
            if item.get_data("selectable"):
                parent = item.get_parent()
                gst.log("attempting to split source at position %d" %  x)
                self._splitSource(parent, self.pixelToNs(x))
        return True

    # FIXME: this DEFINITELY needs to be in the core. Also, do we always want
    # to split linked sources? Should the user be forced to un-link linked
    # sources when they only wisth to split one of them? If not, 

    def _splitSource(self, obj, editpoint):
        comp = obj.comp
        element = obj.element

        # we want to divide element in elementA, elementB at the
        # edit point.
        a_start = element.start
        a_end = editpoint
        b_start = editpoint
        b_end = element.start + element.duration

        # so far so good, but we need this expressed in the form
        # start/duration.
        a_dur = a_end - a_start
        b_dur = b_end - b_start
        if not (a_dur and b_dur):
            gst.Log("cannot cut at existing edit point, aborting")
            return

        # and finally, we need the media-start/duration for both sources.
        # in this case, media-start = media-duration, but this would not be
        # true if timestretch were applied to either source. this is why I
        # really think we should not have to care about media-start /duratoin
        # here, and have a more abstract method for setting time stretch that
        # would keep media start/duration in sync for sources that have it.
        a_media_start = element.media_start
        b_media_start = a_media_start + a_dur

        # trim source a
        element.setMediaStartDurationTime(a_media_start, a_dur)
        element.setStartDurationTime(a_start, a_dur)

        # add source b
        # TODO: for linked sources, split linked and create brother
        # TODO: handle other kinds of sources
        new = TimelineFileSource(factory=element.factory,
            media_type=comp.media_type)
        new.setMediaStartDurationTime(b_media_start, b_dur)
        new.setStartDurationTime(b_start, b_dur)
        comp.addSource(new, 0, True)

    def _selection_changed_cb(self, selected, deselected):
        # TODO: filter this list for things other than sources, and put them
        # into appropriate lists
        for item in selected:
            item.props.fill_color_rgba = item.get_data("selected_color")
            parent = item.get_parent()
            self._selected_sources.append(parent)
        for item in deselected:
            item.props.fill_color_rgba = item.get_data("normal_color")
            parent = item.get_parent()
            self._selected_sources.remove(parent)

## Zoomable Override

    def zoomChanged(self):
        instance.PiTiVi.current.timeline.setDeadband(self.pixelToNs(DEADBAND))

    def setChildZoomAdjustment(self, adj):
        for track in self.__tracks:
            track.setZoomAdjustment(adj)

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

    @handler(timeline, "track-added")
    def _trackAdded(self, unused_timeline, comp, position):
        track = Track(comp=comp)
        self.__tracks.append(track)
        track.setZoomAdjustment(self.getZoomAdjustment())
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
