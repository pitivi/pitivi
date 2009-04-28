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
from preview import Preview
import gst
from common import LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED
from common import LAYER_SPACING
from pitivi.ui.point import Point

LEFT_SIDE = gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE)
RIGHT_SIDE = gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE)
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
TRIMBAR_PIXBUF = gtk.gdk.pixbuf_new_from_file(
    os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
TRIMBAR_PIXBUF_FOCUS = gtk.gdk.pixbuf_new_from_file(
    os.path.join(configure.get_pixmap_dir(), "trimbar-focused.png"))

import gst

def text_size(text):
    ink, logical = text.get_natural_extents()
    x1, y1, x2, y2 = [pango.PIXELS(x) for x in logical]
    return x2 - x1, y2 - y1

class TimelineController(controller.Controller):

    _cursor = ARROW

    def enter(self, unused, unused2):
        self._view.focus()

    def leave(self, unused, unused2):
        self._view.unfocus()

    def drag_start(self):
        pass

    def drag_end(self):
        self._view.timeline.rebuildEdges()

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

    def focus(self):
        self.props.pixbuf = TRIMBAR_PIXBUF_FOCUS

    def unfocus(self):
        self.props.pixbuf = TRIMBAR_PIXBUF

class StartHandle(TrimHandle):

    """Subclass of TrimHandle wich sets the object's start time"""

    class Controller(TimelineController):

        _cursor = LEFT_SIDE

        def set_pos(self, obj, pos):
            new_start = max(self._view.pixelToNs(pos[0]), 0)
            self._view.element.trimStart(new_start, snap=True)

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

    __BACKGROUND__ = 0x3182bdC0
    __BORDER__ = 0xffea00FF

    class Controller(TimelineController):

        def drag_start(self):
            TimelineController.drag_start(self)
            self._view.raise_(None)
            tx = self._view.props.parent.get_transform()
            self._y_offset = tx[5]
            self._mousedown = Point(self._mousedown[0], 0)

        def click(self, pos):
            mode = 0
            if self._last_event.get_state() & gtk.gdk.SHIFT_MASK:
                mode = 1
            elif self._last_event.get_state() & gtk.gdk.CONTROL_MASK:
                mode = 2
            self._view.timeline.setSelectionToObj(
                self._view.element, mode)

        def set_pos(self, item, pos):
            x, y = pos
            self._view.element.setStart(max(self._view.pixelToNs(x), 0),
                    snap=True)
            priority = int(max(0, (y - self._y_offset) // (LAYER_HEIGHT_EXPANDED +
                LAYER_SPACING)))
            self._view.element.setObjectPriority(priority)

    def __init__(self, element, track, timeline):
        goocanvas.Group.__init__(self)
        View.__init__(self)
        Zoomable.__init__(self)

        self.element = element
        self.track = track
        self.timeline = timeline

        self.bg = goocanvas.Rect(
            height=self.height, 
            fill_color_rgba=self.__BACKGROUND__,
            stroke_color_rgba=self.__BORDER__,
            line_width=0)

        self.content = Preview(self.element)

        self.name = goocanvas.Text(
            x=10,
            y=5,
            text=os.path.basename(unquote(element.factory.name)),
            font="Sans 9",
            fill_color_rgba=0xFFFFFFAA,
            operator = cairo.OPERATOR_ADD,
            alignment=pango.ALIGN_LEFT)
        twidth, theight = text_size(self.name)
        self.namebg = goocanvas.Rect(
            radius_x = 2,
            radius_y = 2,
            x = 8,
            y = 3,
            width = twidth + 4,
            height = theight + 4,
            line_width = 0,
            fill_color_rgba = self.__BACKGROUND__)
        self.namewidth = twidth

        self.start_handle = StartHandle(element, timeline,
            height=self.height)
        self.end_handle = EndHandle(element, timeline,
            height=self.height)

        for thing in (self.bg, self.content, self.start_handle,
            self.end_handle, self.namebg, self.name):
            self.add_child(thing)

        if element:
            self.zoomChanged()
        self.normal()

## Properties

    _height = LAYER_HEIGHT_EXPANDED

    def setHeight(self, height):
        self._height = height
        self.start_handle.props.height = height
        self.end_handle.props.height = height
        self._update()

    def getHeight(self):
        return self._height

    height = property(getHeight, setHeight)

    _expanded = True

    def setExpanded(self, expanded):
        self._expanded = expanded
        if not self._expanded:
            self.height = LAYER_HEIGHT_COLLAPSED
            self.content.props.visibility = goocanvas.ITEM_INVISIBLE
            self.namebg.props.visibility = goocanvas.ITEM_INVISIBLE
            self.bg.props.height = LAYER_HEIGHT_COLLAPSED
            self.name.props.y = 0
        else:
            self.height = LAYER_HEIGHT_EXPANDED
            self.content.props.visibility = goocanvas.ITEM_VISIBLE
            self.namebg.props.visibility = goocanvas.ITEM_VISIBLE
            self.bg.props.height = LAYER_HEIGHT_EXPANDED
            self.height = LAYER_HEIGHT_EXPANDED
            self.name.props.y = 5

    def getExpanded(self):
        return self._expanded

    expanded = property(getExpanded, setExpanded)

## Public API

    def focus(self):
        self.start_handle.focus()
        self.end_handle.focus()

    def unfocus(self):
        self.start_handle.unfocus()
        self.end_handle.unfocus()

    def zoomChanged(self):
        self._update()

## element signals

    element = receiver()

    @handler(element, "start-changed")
    @handler(element, "duration-changed")
    def startChangedCb(self, track_object, start):
        self._update()

    @handler(element, "selected-changed")
    def selected_changed(self, element, state):
        if element.selected:
            self.bg.props.line_width = 2.0
        else:
            self.bg.props.line_width = 0

    @handler(element, "priority-changed")
    def priority_changed(self, element, priority):
        self._update()

    def _update(self):
        x = self.nsToPixel(self.element.start)
        y = (self.height + LAYER_SPACING) * self.element.priority
        self.set_simple_transform(x, y, 1, 0)
        width = self.nsToPixel(self.element.duration)
        w = width - self.end_handle.props.width
        self.name.props.clip_path = "M%g,%g h%g v%g h-%g z" % (
            0, 0, w, self.height, w)
        self.bg.props.width = width
        self.end_handle.props.x = w
        if self.expanded:
            if w - 10 > 0:
                self.namebg.props.width = min(w - 8, self.namewidth)
                self.namebg.props.visibility = goocanvas.ITEM_VISIBLE
            else:
                self.namebg.props.visibility = goocanvas.ITEM_INVISIBLE

