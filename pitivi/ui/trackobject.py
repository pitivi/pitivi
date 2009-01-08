import goocanvas
import gobject
import gtk
import os.path
import pango
import cairo
import pitivi.configure as configure
from urllib import unquote
from pitivi.receiver import receiver, handler
from view import View
import controller
from zoominterface import Zoomable
from pitivi.timeline.track import TrackError

LEFT_SIDE = gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE)
RIGHT_SIDE = gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE)
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
TRIMBAR_PIXBUF = gtk.gdk.pixbuf_new_from_file(
    os.path.join(configure.get_pixmap_dir(), "trimbar.png"))

import gst

class TimelineController(controller.Controller):

    _cursor = ARROW

    def drag_start(self):
        pass

    def drag_end(self):
        self._view.timeline.rebuildEdges()

    def set_pos(self, item, pos):
        self._view.element.setStart(max(self._view.pixelToNs(pos[0]), 0),
                snap=True)

class TrimHandle(View, goocanvas.Image, Zoomable):

    """A component of a TrackObject which manage's the source's edit
    points"""

    element = receiver()

    def __init__(self, element, timeline, **kwargs):
        self.element = element
        self.timeline = timeline
        goocanvas.Image.__init__(self,
            pixbuf = TRIMBAR_PIXBUF,
            line_width=0,
            **kwargs
        )
        View.__init__(self)
        Zoomable.__init__(self)

class StartHandle(TrimHandle):

    """Subclass of TrimHandle wich sets the object's start time"""

    class Controller(TimelineController):

        _cursor = LEFT_SIDE

        def set_pos(self, obj, pos):
            new_start = max(self._view.pixelToNs(pos[0]), 0)
            self._view.element.trimStart(new_start)

class EndHandle(TrimHandle):

    """Subclass of TrimHandle which sets the objects's end time"""

    class Controller(TimelineController):

        _cursor = RIGHT_SIDE

        def set_pos(self, obj, pos):
            start = self._view.element.start
            abs_pos = self._view.pixelToNs(pos[0])
            duration = max(abs_pos - start, 0)
            self._view.element.setDuration(duration, snap=True)

class TrackObject(View, goocanvas.Group, Zoomable):

    element = receiver()

    __HEIGHT__ = 50
    __NORMAL__ = 0x709fb899
    __SELECTED__ = 0xa6cee3AA

    class Controller(TimelineController):

        def click(self, pos):
            mode = 0
            if self._last_event.get_state() & gtk.gdk.SHIFT_MASK:
                mode = 1
            elif self._last_event.get_state() & gtk.gdk.CONTROL_MASK:
                mode = 2
            self._view.timeline.setSelectionToObj(
                self._view.element, mode)

    def __init__(self, element, track, timeline):
        goocanvas.Group.__init__(self)
        View.__init__(self)
        Zoomable.__init__(self)

        self.element = element
        self.track = track
        self.timeline = timeline

        self.bg = goocanvas.Rect(
            height=self.__HEIGHT__, 
            fill_color_rgba=self.__NORMAL__,
            line_width=0)

        self.name = goocanvas.Text(
            x=10,
            y=10,
            text=os.path.basename(unquote(element.factory.name)),
            font="Sans 9",
            fill_color_rgba=0x000000FF,
            alignment=pango.ALIGN_LEFT)
 
        self.start_handle = StartHandle(element, timeline,
            height=self.__HEIGHT__)
        self.end_handle = EndHandle(element, timeline,
            height=self.__HEIGHT__)

        for thing in (self.bg, self.start_handle, self.end_handle, self.name):
            self.add_child(thing)

        if element:
            self.zoomChanged()
        self.normal()

    def zoomChanged(self):
        self._startDurationChangedCb(self.element, self.element.start,
            self.element.duration)

    @handler(element, "start-changed")
    def _startChangedCb(self, track_object, start):
        self._startDurationChangedCb(track_object,
                track_object.start, track_object.duration)

    @handler(element, "duration-changed")
    def _startChangedCb(self, track_object, start):
        self._startDurationChangedCb(track_object,
                track_object.start, track_object.duration)
    
    def _startDurationChangedCb(self, obj, start, duration):
        self.set_simple_transform(self.nsToPixel(start), 0, 1, 0)
        width = self.nsToPixel(duration)
        w = width - self.end_handle.props.width
        self.name.props.clip_path = "M%g,%g h%g v%g h-%g z" % (
            0, 0, w, self.__HEIGHT__, w)
        self.bg.props.width = width
        # place end handle at appropriate distance
        self.end_handle.props.x = w

    @handler(element, "selected-changed")
    def _selected_changed(self, element, state):
        if element.selected:
            self.bg.props.fill_color_rgba = self.__SELECTED__
        else:
            self.bg.props.fill_color_rgba = self.__NORMAL__
