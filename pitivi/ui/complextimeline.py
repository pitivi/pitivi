# PiTiVi , Non-linear video editor
#
#       pitivi/ui/complextimeline.py
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Timeline widgets for the complex view
"""

import gtk
import gst
import pitivi.instance as instance

from pitivi.bin import SmartTimelineBin
from pitivi.timeline.source import TimelineFileSource
from complexlayer import LayerInfoList
import ruler
from complexinterface import Zoomable
import goocanvas
from util import *
import os.path
from urllib import unquote
from pitivi.timeline.objects import MEDIA_TYPE_VIDEO
from pitivi.utils import closest_item
from gettext import gettext as _


# default heights for composition layer objects
VIDEO_TRACK_HEIGHT = 50
AUDIO_TRACK_HEIGHT = 20

# visual styles for sources in the UI
VIDEO_SOURCE = (
    goocanvas.Rect,
    {
        "height" : VIDEO_TRACK_HEIGHT, 
        "fill_color_rgba" : 0x709fb899,
        "line_width" : 0
    },
    {
        "normal_color" : 0x709fb899,
        "selected_color" : 0xa6cee3AA, 
    }
)
AUDIO_SOURCE = (
    goocanvas.Rect,
    {
        "height" : AUDIO_TRACK_HEIGHT, 
        "fill_color_rgba" : 0x709fb899,
        "line_width" : 0
    },
    {
        "normal_color" : 0x709fb899,
        "selected_color" : 0xa6cee3AA, 
    }
)

# defines visual appearance for source resize handle
DRAG_HANDLE = (
    goocanvas.Rect,
    {
        "width" : 5,
        "fill_color_rgba" : 0x00000022,
        "line-width" : 0
    },
    {}
)

BACKGROUND = (
    goocanvas.Rect,
    {
        "stroke_color" : "gray",
        "fill_color" : "gray",
    },
    {}
)

RAZOR_LINE = (
    goocanvas.Rect,
    {
        "line_width" : 0,
        "fill_color" : "orange",
        "width" : 1,
    },
    {}
)

SPACER = (
    goocanvas.Polyline,
    {
        "stroke_color_rgba" : 0xFFFFFFFF,
        "line_width" : 1,
    },
    {}
)

LABEL = (
    goocanvas.Text,
    {
        "font" : "Sans 9",
        "text" : "will be replaced",
        "fill_color_rgba" : 0x000000FF,
        "alignment" : pango.ALIGN_LEFT
    },
    {}
)

# the vsiual appearance for the selection marquee
MARQUEE = (
    goocanvas.Rect,
    {
        "stroke_color_rgba" : 0x33CCFF66,
        "fill_color_rgba" : 0x33CCFF66,
    },
    {}
)

# cursors to be used for resizing objects
LEFT_SIDE = gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE)
RIGHT_SIDE = gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE)
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
# TODO: replace this with custom cursor
RAZOR_CURSOR = gtk.gdk.Cursor(gtk.gdk.XTERM)

# default number of pixels to use for edge snaping
DEADBAND = 5

# tooltip text for toolbar
DELETE = _("Delete Selected")
RAZOR = _("Cut clip at mouse position")
ZOOM_IN =  _("Zoom In")
ZOOM_OUT =  _("Zoom Out")
SELECT_BEFORE = ("Select all sources before selected")
SELECT_AFTER = ("Select all after selected")

# ui string for the complex timeline toolbar
ui = '''
<ui>
    <toolbar name="TimelineToolBar">
        <toolitem action="ZoomOut" />
        <toolitem action="ZoomIn" />
        <separator />
        <toolitem action="Razor" />
        <separator />
        <toolitem action="DeleteObj" />
        <toolitem action="SelectBefore" />
        <toolitem action="SelectAfter" />
    </toolbar>
</ui>
'''

class ComplexTrack(SmartGroup, Zoomable):
    __gtype_name__ = 'ComplexTrack'

    def __init__(self, *args, **kwargs):
        SmartGroup.__init__(self, *args, **kwargs)
        self.widgets = {}
        self.elements = {}
        self.sig_ids = None
        self.comp = None
        self.object_style = None

    def set_composition(self, comp):
        if self.sig_ids:
            for sig in self.sig_ids:
                comp.disconnect(sig)
        self.comp = comp
        self.object_style = VIDEO_SOURCE
        if comp:
            added = comp.connect("source-added", self._objectAdded)
            removed = comp.connect("source-removed", self._objectRemoved)
            self.sig_ids = (added, removed)
            if comp.media_type == MEDIA_TYPE_VIDEO:
                self.object_style = VIDEO_SOURCE
                self.height = VIDEO_TRACK_HEIGHT
            else:
                self.object_style = AUDIO_SOURCE
                self.height = AUDIO_TRACK_HEIGHT

    def _objectAdded(self, timeline, element):
        w = ComplexTimelineObject(element, self.comp, self.object_style)
        make_dragable(self.canvas, w, start=self._start_drag,
            end=self._end_drag, moved=self._move_source_cb)
        element.connect("start-duration-changed", self.start_duration_cb, w)
        self.widgets[element] = w
        self.elements[w] = element
        #element.set_data("widget", w)
        self.start_duration_cb(element, element.start, element.duration, w)
        self.add_child(w)
        make_selectable(self.canvas, w.bg)
        make_dragable(self.canvas, w.l_handle, 
            start=self._start_drag, moved=self._trim_source_start_cb,
            cursor=LEFT_SIDE)
        make_dragable(self.canvas, w.r_handle, start=self._start_drag,
            moved=self._trim_source_end_cb,
            cursor=RIGHT_SIDE)

    def _objectRemoved(self, timeline, element):
        w = self.widgets[element]
        self.remove_child(w)
        w.comp = None
        del self.widgets[element]
        del self.elements[w]

    def start_duration_cb(self, obj, start, duration, widget):
        widget.props.width =  self.nsToPixel(duration)
        self.set_child_pos(widget, (self.nsToPixel(start), 0))

    def _start_drag(self, item):
        item.raise_(None)
        self._draging = True
        #self.canvas.block_size_request(True)
        self.canvas.update_editpoints()

    def _end_drag(self, item):
        self.canvas.block_size_request(False)

    def _move_source_cb(self, item, pos):
        element = item.element
        element.setStartDurationTime(max(self.canvas.snap_obj_to_edit(element,
            self.pixelToNs(pos[0])), 0))

    def _trim_source_start_cb(self, item, pos):
        element = item.element
        cur_end = element.start + element.duration
        # Invariant:
        #  max(duration) = element.factory.duration
        #  start = end - duration
        # Therefore
        #  min(start) = end - element.factory.duration
        new_start =  max(0,
            cur_end - element.factory.duration,
            self.canvas.snap_time_to_edit(self.pixelToNs(pos[0])))
        new_duration = cur_end - new_start
        new_media_start = element.media_start + (new_start - element.media_start)
        element.setStartDurationTime(new_start, new_duration)
        #FIXME: only for sources
        element.setMediaStartDurationTime(new_media_start, new_duration)

    def _trim_source_end_cb(self, item, pos):
        element = item.element
        cur_start = element.start
        new_end = min(cur_start + element.factory.duration,
            max(cur_start,
                self.canvas.snap_time_to_edit(
                    self.pixelToNs(pos[0] + width(item)))))
        new_duration = new_end - element.start

        element.setStartDurationTime(gst.CLOCK_TIME_NONE, new_duration)
        #FIXME: only for sources
        element.setMediaStartDurationTime(gst.CLOCK_TIME_NONE, new_duration)

    def zoomChanged(self):
        """Force resize if zoom ratio changes"""
        for child in self.elements:
            element = self.elements[child]
            start = element.start
            duration = element.duration
            self.start_duration_cb(self, start, duration, child)

class ComplexTimelineObject(goocanvas.Group):

    __gtype_name__ = 'ComplexTimelineObject'

    x = gobject.property(type=float)
    y = gobject.property(type=float)
    height = gobject.property(type=float)
    width = gobject.property(type=float)

    def __init__(self, element, composition, style):
        goocanvas.Group.__init__(self)
        self.element = element
        self.comp = composition
        self.bg = make_item(style)
        self.bg.element = element
        self.bg.comp = composition
        self.name = make_item(LABEL)
        self.name.props.text = os.path.basename(unquote(
            element.factory.name))
        self.l_handle = self._make_handle(LEFT_SIDE)
        self.r_handle = self._make_handle(RIGHT_SIDE)
        self.spacer = make_item(SPACER)
        self.children = [self.bg, self.name, self.l_handle, self.r_handle,
            self.spacer]
        for thing in self.children:
            self.add_child(thing)
        self.connect("notify::x", self.do_set_x)
        self.connect("notify::y", self.do_set_y)
        self.connect("notify::width", self.do_set_width)
        self.connect("notify::height", self.do_set_height)
        self.width = self.bg.props.width
        self.height = self.bg.props.height

    def _set_cursor(self, item, target, event, cursor):
        window = event.window
        # wtf ? no get_cursor?
        #self._oldcursor = window.get_cursor()
        window.set_cursor(cursor)
        return True

    def _make_handle(self, cursor):
        ret = make_item(DRAG_HANDLE)
        ret.element = self.element
        ret.connect("enter-notify-event", self._set_cursor, cursor)
        #ret.connect("leave-notify-event", self._set_cursor, ARROW)
        return ret

    def _size_spacer(self):
        x = self.x + self.width
        y = self.y + self.height
        self.spacer.points = goocanvas.Points([(x, 0), (x, y)])
        # clip text to object width
        w = self.width - width(self.r_handle)
        self.name.props.clip_path = "M%g,%g h%g v%g h-%g z" % (
            self.x, self.y, w, self.height, w)

    def do_set_x(self, *args):
        x = self.x
        self.bg.props.x = x
        self.name.props.x = x + width(self.l_handle) + 2
        self.l_handle.props.x = x
        self.r_handle.props.x = x + self.width - width(self.r_handle)
        self._size_spacer()

    def do_set_y(self, *args):
        y = self.y
        self.bg.props.y = y
        self.name.props.y = y + 2
        self.l_handle.props.y = y
        self.r_handle.props.y = y
        self._size_spacer()

    def do_set_width(self, *args):
        self.bg.props.width = self.width
        self.r_handle.props.x = self.x + self.width - width(self.r_handle)
        self.name.props.width = self.width - (2 * width(self.l_handle) + 4)
        self._size_spacer()

    def do_set_height(self, *args):
        height = self.height
        self.bg.props.height = height
        self.l_handle.props.height = height
        self.r_handle.props.height = height
        self._size_spacer()

class CompositionLayers(goocanvas.Canvas, Zoomable):
    """ Souped-up VBox that contains the timeline's CompositionLayer """

    def __init__(self, layerinfolist):
        goocanvas.Canvas.__init__(self)
        self._selected_sources = []
        self._editpoints = []
        self._deadband = 0
        self._timeline_position = 0

        self._block_size_request = False
        self.props.integer_layout = True
        self.props.automatic_bounds = False

        self.layerInfoList = layerinfolist
        self.layerInfoList.connect('layer-added', self._layerAddedCb)
        self.layerInfoList.connect('layer-removed', self._layerRemovedCb)

        self._createUI()
        self.connect("size_allocate", self._size_allocate)
       
    def _createUI(self):
        self._cursor = ARROW

        self.layers = VList(canvas=self)
        self.layers.connect("notify::width", self._request_size)
        self.layers.connect("notify::height", self._request_size)

        root = self.get_root_item()
        root.add_child(self.layers)

        root.connect("enter_notify_event", self._mouseEnterCb)
        self._marquee = make_item(MARQUEE)
        manage_selection(self, self._marquee, True, self._selection_changed_cb)

        self._razor = make_item(RAZOR_LINE)
        self._razor.props.visibility = goocanvas.ITEM_INVISIBLE
        root.add_child(self._razor)

## methods for dealing with updating the canvas size

    def block_size_request(self, status):
        self._block_size_request = status

    def _size_allocate(self, unused_layout, allocation):
        self._razor.props.height = allocation.height

    def _request_size(self, unused_item, prop):
        #TODO: figure out why this doesn't work... (wtf?!?)
        if self._block_size_request:
            return True
        # we only update the bounds of the canvas by chunks of 100 pixels
        # in width, otherwise we would always be redrawing the whole canvas.
        # Make sure canvas is at least 800 pixels wide, and at least 100 pixels 
        # wider than it actually needs to be.
        w = max(800, ((int(self.layers.width + 100) / 100) + 1 ) * 100)
        h = int(self.layers.height)
        x1,y1,x2,y2 = self.get_bounds()
        pw = abs(x2 - x1)
        ph = abs(y2 - y1)
        if not (w == pw and h == ph):
            self.set_bounds(0, 0, w, h)
        return True

## code for keeping track of edit points, and snapping timestamps to the
## nearest edit point. We do this here so we can keep track of edit points
## for all layers/tracks.

    def update_editpoints(self):
        #FIXME: this might be more efficient if we used a binary sort tree,
        # updated only when the timeline actually changes instead of before
        # every drag operation. possibly concerned this could lead to a
        # noticible lag on large timelines

        # using a dictionary to silently filter out duplicate entries
        # this list: it will screw up the edge-snaping algorithm
        edges = {}
        for layer in self.layerInfoList:
            for obj in layer.composition.condensed:
                # start/end of object both considered "edit points"
                edges[obj.start] = None
                edges[obj.start + obj.duration] = None
        self._editpoints = edges.keys()
        self._editpoints.sort()

    def snap_time_to_edit(self, time):
        res, diff = closest_item(self._editpoints, time)
        if diff <= self._deadband:
            return res
        return time

    def snap_time_to_playhead(self, time):
        if abs(time - self._timeline_position)  <= self._deadband:
            return self._timeline_position
        return time

    def snap_obj_to_edit(self, obj, time):
        # need to find the closest edge to both the left and right sides of
        # the object we are draging.
        duration = obj.duration
        left_res, left_diff = closest_item(self._editpoints, time)
        right_res, right_diff = closest_item(self._editpoints, time + duration)
        if left_diff <= right_diff:
            res = left_res
            diff = left_diff
        else:
            res = right_res - duration
            diff = right_diff
        if diff <= self._deadband:
            return res
        return time

## mouse callbacks

    def _mouseEnterCb(self, item, target, event):
        event.window.set_cursor(self._cursor)
        return True

## Editing Operations

    def deleteSelected(self, unused_action):
        for obj in self._selected_sources:
            if obj.comp:
                obj.comp.removeSource(obj.element, remove_linked=True, 
                    collapse_neighbours=False)
        set_selection(self, set())
        return True

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
        self._razor.props.x = self.nsToPixel(self.snap_time_to_playhead(
            self.pixelToNs(x)))
        return True

    def _razorClickedCb(self, canvas, event):
        self._cursor = ARROW
        event.window.set_cursor(ARROW)
        self.disconnect(self._razor_sigid)
        self.disconnect(self._razor_motion_sigid)
        self._razor.props.visibility = goocanvas.ITEM_INVISIBLE

        # Find the topmost source under the mouse. This is tricky because not
        # all objects in the timeline are ComplexTimelineObjects. Some of them
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
                self._splitSource(parent, self.snap_time_to_playhead(
                    self.pixelToNs(x)))
        return True

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

    def selectBeforeCurrent(self, unused_action):
        pass

    def selectAfterCurrent(self, unused_action):
        ## helper function
        #def source_pos(ui_obj):
        #    return ui_obj.comp.getSimpleSourcePosition(ui_obj.element)

        ## mapping from composition -> (source1, ... sourceN)
        #comps = dict()
        #for source in self._selected_sources:
        #    if not source.comp in comps:
        #        comps[source.comp] = []
        #    comps[source.comp].append(source)

        ## find the latest source in each compostion, and all sources which
        ## occur after it. then select them.
        #to_select = set()
        #for comp, sources in comps.items():
        #    # source positions start at 1, not 0.
        #    latest = max((source_pos(source) for source in sources)) - 1
        #    # widget is available in "widget" data member of object.
        #    # we add the background of the widget, not the widget itself.
        #    objs = [obj.get_data("widget").bg for obj in comp.condensed[latest:]]
        #    to_select.update(set(objs))
        #set_selection(self, to_select)
        pass

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

    def timelinePositionChanged(self, value, frame):
        self._timeline_position = value

## Zoomable Override

    def zoomChanged(self):
        self._deadband = self.pixelToNs(DEADBAND)

    def setChildZoomAdjustment(self, adj):
        for layer in self.layers:
            layer.setZoomAdjustment(adj)

## LayerInfoList callbacks

    def _layerAddedCb(self, unused_infolist, layer, position):
        track = ComplexTrack()
        track.setZoomAdjustment(self.getZoomAdjustment())
        track.set_composition(layer.composition)
        track.set_canvas(self)
        self.layers.insert_child(track, position)
        self.set_bounds(0, 0, self.layers.width, self.layers.height)
        self.set_size_request(int(self.layers.width), int(self.layers.height))

    def _layerRemovedCb(self, unused_layerInfoList, position):
        child = self.layers.item_at(position)
        self.layers.remove_child(child)
#
# Complex Timeline Design v2 (08 Feb 2006)
#
#
# Tree of contents (ClassName(ParentClass))
# -----------------------------------------
#
# ComplexTimelineWidget(gtk.VBox)
# |  Top container
# |
# +--ScaleRuler(gtk.Layout)
# |
# +--gtk.ScrolledWindow
#    |
#    +--CompositionLayers(goocanas.Canvas)
#    |  |
#    |  +--ComplexTrack(SmartGroup)
#    |
#    +--Status Bar ??
#

class ComplexTimelineWidget(gtk.VBox):

    # the screen width of the current unit
    unit_width = 10 
    # specific levels of zoom, in (multiplier, unit) pairs which 
    # from zoomed out to zoomed in
    zoom_levels = (1, 5, 10, 20, 50, 100, 150) 

    def __init__(self):
        gst.log("Creating ComplexTimelineWidget")
        gtk.VBox.__init__(self)

        self._zoom_adj = gtk.Adjustment()
        self._zoom_adj.lower = self._computeZoomRatio(0)
        self._zoom_adj.upper = self._computeZoomRatio(-1)
        self._cur_zoom = 2
        self._zoom_adj.set_value(self._computeZoomRatio(self._cur_zoom))
 
        # common LayerInfoList
        self.layerInfoList = LayerInfoList()

        instance.PiTiVi.playground.connect('position',
           self._playgroundPositionCb)
        # project signals
        instance.PiTiVi.connect("new-project-loading",
            self._newProjectLoadingCb)
        instance.PiTiVi.connect("new-project-failed",
            self._newProjectFailedCb)
        self._createUI()

        # force update of UI
        self.layerInfoList.setTimeline(instance.PiTiVi.current.timeline)
        self.layerInfoList.connect("start-duration-changed",
            self._layerStartDurationChanged)

    def _createUI(self):
        self.leftSizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        self.hadj = gtk.Adjustment()
        self.ruler = ruler.ScaleRuler(self.hadj)
        self.ruler.setZoomAdjustment(self._zoom_adj)
        self.ruler.set_size_request(0, 35)
        self.ruler.set_border_width(2)
        self.pack_start(self.ruler, expand=False, fill=True)

        # List of CompositionLayers
        self.compositionLayers = CompositionLayers(self.layerInfoList)
        self.compositionLayers.setZoomAdjustment(self._zoom_adj)
        self.scrolledWindow = gtk.ScrolledWindow(self.hadj)
        self.scrolledWindow.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_AUTOMATIC)
        self.scrolledWindow.add(self.compositionLayers)
        #FIXME: remove padding between scrollbar and scrolled window
        self.pack_start(self.scrolledWindow, expand=True)

        # toolbar actions
        actions = (
            ("ZoomIn", gtk.STOCK_ZOOM_IN, None, None, ZOOM_IN,
                self._zoomInCb),
            ("ZoomOut", gtk.STOCK_ZOOM_OUT, None, None, ZOOM_OUT, 
                self._zoomOutCb),
            ("DeleteObj", gtk.STOCK_DELETE, None, None, DELETE, 
                self.compositionLayers.deleteSelected),
            ("SelectBefore", gtk.STOCK_GOTO_FIRST, None, None, SELECT_BEFORE, 
                self.compositionLayers.selectBeforeCurrent),
            ("SelectAfter", gtk.STOCK_GOTO_LAST, None, None, SELECT_AFTER,
                self.compositionLayers.selectAfterCurrent),
            ("Razor", gtk.STOCK_CUT, None, None, RAZOR,
                self.compositionLayers.activateRazor)
        )
        self.actiongroup = gtk.ActionGroup("complextimeline")
        self.actiongroup.add_actions(actions)
        self.actiongroup.set_visible(False)
        uiman = instance.PiTiVi.gui.uimanager
        uiman.insert_action_group(self.actiongroup, 0)
        uiman.add_ui_from_string(ui)

## Project callbacks

    def _newProjectLoadingCb(self, unused_inst, project):
        self.layerInfoList.setTimeline(project.timeline)

    def _newProjectFailedCb(self, unused_inst, unused_reason, unused_uri):
        self.layerInfoList.setTimeline(None)

## layer callbacks

    def _layerStartDurationChanged(self, layer):
        self.ruler.startDurationChanged()

## ToolBar callbacks

    ## override show()/hide() methods to take care of actions
    def show(self):
        super(ComplexTimelineWidget, self).show()
        self.actiongroup.set_visible(True)

    def show_all(self):
        super(ComplexTimelineWidget, self).show_all()
        self.actiongroup.set_visible(True)

    def hide(self):
        self.actiongroup.set_visible(False)
        super(ComplexTimelineWidget, self).hide()

    def _computeZoomRatio(self, index):
        return self.zoom_levels[index]

    def _zoomInCb(self, unused_action):
        self._cur_zoom = min(len(self.zoom_levels) - 1, self._cur_zoom + 1)
        self._zoom_adj.set_value(self._computeZoomRatio(self._cur_zoom))

    def _zoomOutCb(self, unused_action):
        self._cur_zoom = max(0, self._cur_zoom - 1)
        self._zoom_adj.set_value(self._computeZoomRatio(self._cur_zoom))

## PlayGround timeline position callback

    def _playgroundPositionCb(self, unused_playground, smartbin, value):
        if isinstance(smartbin, SmartTimelineBin):
            # for the time being we only inform the ruler
            self.ruler.timelinePositionChanged(value, 0)
            self.compositionLayers.timelinePositionChanged(value, 0)
