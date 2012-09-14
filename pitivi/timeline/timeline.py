# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/timeline.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2009, Brandon Lewis <brandon_lewis@berkeley.edu>
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

"""
    Main Timeline widgets
"""

import sys
import time

from gi.repository import Gtk
from gi.repository import Gst
from gi.repository import GES
from gi.repository import GObject
from gi.repository import GooCanvas

from gi.repository import Gdk

from gettext import gettext as _
from os.path import join

from pitivi.timeline import ruler
from pitivi.check import soft_deps
from pitivi.effects import AUDIO_EFFECT, VIDEO_EFFECT
from pitivi.autoaligner import AlignmentProgressDialog
from pitivi.utils.misc import quote_uri, print_ns
from pitivi.utils.pipeline import PipelineError
from pitivi.settings import GlobalSettings

from track import Track, TrackObject
from layer import VideoLayerControl, AudioLayerControl
from pitivi.utils.timeline import EditingContext, SELECT, Zoomable

from pitivi.dialogs.depsmanager import DepsManager
from pitivi.dialogs.filelisterrordialog import FileListErrorDialog
from pitivi.dialogs.prefs import PreferencesDialog

from pitivi.utils.receiver import receiver, handler
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import SPACING, CANVAS_SPACING, \
    TYPE_PITIVI_FILESOURCE, VIDEO_EFFECT_TARGET_ENTRY, Point, \
    AUDIO_EFFECT_TARGET_ENTRY, EFFECT_TARGET_ENTRY, FILESOURCE_TARGET_ENTRY, TYPE_PITIVI_EFFECT, \
    LAYER_CREATION_BLOCK_TIME, LAYER_CONTROL_TARGET_ENTRY

# FIXME GES Port regression
# from pitivi.utils.align import AutoAligner

GlobalSettings.addConfigOption('edgeSnapDeadband',
    section="user-interface",
    key="edge-snap-deadband",
    default=5,
    notify=True)

PreferencesDialog.addNumericPreference('edgeSnapDeadband',
    section=_("Behavior"),
    label=_("Snap distance"),
    description=_("Threshold (in pixels) at which two clips will snap together "
        "when dragging or trimming."),
    lower=0)

GlobalSettings.addConfigOption('imageClipLength',
    section="user-interface",
    key="image-clip-length",
    default=1000,
    notify=True)

PreferencesDialog.addNumericPreference('imageClipLength',
    section=_("Behavior"),
    label=_("Image clip duration"),
    description=_("Default clip length (in miliseconds) of images when inserting on the timeline."),
    lower=1)


# cursors to be used for resizing objects
ARROW = Gdk.Cursor.new(Gdk.CursorType.ARROW)
# TODO: replace this with custom cursor
PLAYHEAD_CURSOR = Gdk.Cursor.new(Gdk.CursorType.SB_H_DOUBLE_ARROW)

# Drag and drop constants/tuples
# FIXME, rethink the way we handle that as it is quite 'hacky'
DND_EFFECT_LIST = [[VIDEO_EFFECT_TARGET_ENTRY.target, EFFECT_TARGET_ENTRY.target],\
                  [AUDIO_EFFECT_TARGET_ENTRY.target, EFFECT_TARGET_ENTRY.target]]
VIDEO_EFFECT_LIST = [VIDEO_EFFECT_TARGET_ENTRY.target, EFFECT_TARGET_ENTRY.target],
AUDIO_EFFECT_LIST = [AUDIO_EFFECT_TARGET_ENTRY.target, EFFECT_TARGET_ENTRY.target],

# tooltip text for toolbar
DELETE = _("Delete Selected")
SPLIT = _("Split clip at playhead position")
KEYFRAME = _("Add a keyframe")
PREVKEYFRAME = _("Move to the previous keyframe")
NEXTKEYFRAME = _("Move to the next keyframe")
ZOOM_IN = _("Zoom In")
ZOOM_OUT = _("Zoom Out")
ZOOM_FIT = _("Zoom Fit")
UNLINK = _("Break links between clips")
LINK = _("Link together arbitrary clips")
UNGROUP = _("Ungroup clips")
GROUP = _("Group clips")
ALIGN = _("Align clips based on their soundtracks")
SELECT_BEFORE = ("Select all sources before selected")
SELECT_AFTER = ("Select all after selected")

ui = '''
<ui>
    <menubar name="MainMenuBar">
        <menu action="View">
            <placeholder name="Timeline">
                <menuitem action="ZoomIn" />
                <menuitem action="ZoomOut" />
                <menuitem action="ZoomFit" />
            </placeholder>
        </menu>
        <menu action="Timeline">
            <placeholder name="Timeline">
                <menuitem action="Split" />
                <menuitem action="DeleteObj" />
                <separator />
                <menuitem action="LinkObj" />
                <menuitem action="UnlinkObj" />
                <menuitem action="GroupObj" />
                <menuitem action="UngroupObj" />
                <menuitem action="AlignObj" />
                <separator />
                <menuitem action="Keyframe" />
                <menuitem action="Prevkeyframe" />
                <menuitem action="Nextkeyframe" />
                <separator />
                <menuitem action="PlayPause" />
                <menuitem action="Screenshot" />
            </placeholder>
        </menu>
    </menubar>
    <toolbar name="TimelineToolBar">
        <placeholder name="Timeline">
            <separator />
            <toolitem action="Split" />
            <toolitem action="Keyframe" />
            <separator />
            <toolitem action="DeleteObj" />
            <toolitem action="UnlinkObj" />
            <toolitem action="LinkObj" />
            <toolitem action="GroupObj" />
            <toolitem action="UngroupObj" />
            <toolitem action="AlignObj" />
        </placeholder>
    </toolbar>
    <accelerator action="PlayPause" />
    <accelerator action="DeleteObj" />
    <accelerator action="ControlEqualAccel" />
    <accelerator action="ControlKPAddAccel" />
    <accelerator action="ControlKPSubtractAccel" />
</ui>
'''


class TimelineCanvas(GooCanvas.Canvas, Zoomable, Loggable):
    """
        The GooCanvas widget representing the timeline
    """

    __gtype_name__ = 'TimelineCanvas'

    _tracks = None

    def __init__(self, instance, timeline=None):
        GooCanvas.Canvas.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.app = instance
        self._tracks = []
        self.height = CANVAS_SPACING

        self._block_size_request = False
        self.props.integer_layout = True
        self.props.automatic_bounds = False
        self.props.clear_background = False
        self.get_root_item().set_simple_transform(0, 2.0, 1.0, 0)

        self._createUI()
        self._timeline = timeline
        self.settings = instance.settings
        self.connect("draw", self.drawCb)

    def _createUI(self):
        self._cursor = ARROW
        root = self.get_root_item()
        self.tracks = GooCanvas.CanvasGroup()
        self.tracks.set_simple_transform(0, 0, 1.0, 0)
        root.add_child(self.tracks, -1)
        self._marquee = GooCanvas.CanvasRect(
            parent=root,
            stroke_color_rgba=0x33CCFF66,
            fill_color_rgba=0x33CCFF66,
            visibility=GooCanvas.CanvasItemVisibility.INVISIBLE)
        self._playhead = GooCanvas.CanvasRect(
            y=-10,
            parent=root,
            line_width=1,
            fill_color_rgba=0x000000FF,
            stroke_color_rgba=0xFFFFFFFF,
            width=3)
        self._snap_indicator = GooCanvas.CanvasRect(
            parent=root, x=0, y=0, width=3, line_width=0.5,
            fill_color_rgba=0x85c0e6FF,
            stroke_color_rgba=0x294f95FF)
        self.connect("size-allocate", self._size_allocate_cb)
        root.connect("motion-notify-event", self._selectionDrag)
        root.connect("button-press-event", self._selectionStart)
        root.connect("button-release-event", self._selectionEnd)
        self.connect("button-release-event", self._buttonReleasedCb)
        # add some padding for the horizontal scrollbar
        self.set_size_request(-1, self.height)

    def from_event(self, event):
        x, y = event.x, event.y
        x += self.app.gui.timeline_ui.hadj.get_value()
        return Point(*self.convert_from_pixels(x, y))

    def setExpanded(self, track_object, expanded):
        track_ui = None
        for track in self._tracks:
            if track.track == track_object:
                track_ui = track
                break

        track_ui.setExpanded(expanded)

## sets the cursor as appropriate

    def _mouseEnterCb(self, unused_item, unused_target, event):
        event.window.set_cursor(self._cursor)
        return True

    def drawCb(self, widget, cr):
        allocation = self.get_allocation()
        width = allocation.width
        height = allocation.height
        # draw the canvas background
        # we must have props.clear_background set to False

        # FIXME GObject Introspection -> move to Gtk.StyleContext
        #self.style.apply_default_background(event.window,
            #True,
            #Gtk.StateType.ACTIVE,
            #event.area,
            #event.area.x, event.area.y,
            #event.area.width, event.area.height)

        #GooCanvas.Canvas.do_expose_event(self, event)

## implements selection marquee

    _selecting = False
    _mousedown = None
    _marquee = None
    _got_motion_notify = False

    def getItemsInArea(self, x1, y1, x2, y2):
        '''
        Permits to get the Non UI L{Track}/L{TrackObject} in a list of set
        corresponding to the L{Track}/L{TrackObject} which are in the are

        @param x1: The horizontal coordinate of the up left corner of the area
        @type x1: An C{int}
        @param y1: The vertical coordinate of the up left corner of the area
        @type y1: An C{int}
        @param x2: The horizontal coordinate of the down right area corner
        @type x2: An C{int}
        @param x2: The vertical coordinate of the down right corner of the area
        @type x2: An C{int}

        @returns: A list of L{Track}, L{TrackObject} tuples
        '''
        bounds = GooCanvas.CanvasBounds()
        bounds.x1 = x1
        bounds.x2 = x2
        bounds.y1 = y1
        bounds.y2 = y2
        items = self.get_items_in_area(bounds, True, True, True)
        if not items:
            return [], []

        tracks = set()
        track_objects = set()

        for item in items:
            if isinstance(item, Track):
                tracks.add(item.track)
            elif isinstance(item, TrackObject):
                track_objects.add(item.element)

        return tracks, track_objects

    def _normalize(self, p1, p2):
        w, h = p1 - p2
        w = abs(w)
        h = abs(h)
        x = min(p1[0], p2[0])
        y = min(p1[1], p2[1])
        return (x, y), (w, h)

    def _get_adjustment(self, xadj=True, yadj=True):
        return Point(self.app.gui.timeline_ui.hadj.get_value() * xadj,
                     self.app.gui.timeline_ui.vadj.get_value() * yadj)

    def _selectionDrag(self, item, target, event):
        if self._selecting:
            self._got_motion_notify = True
            cur = self.from_event(event) - self._get_adjustment(True, False)
            pos, size = self._normalize(self._mousedown, cur)
            self._marquee.props.x, self._marquee.props.y = pos
            self._marquee.props.width, self._marquee.props.height = size
            return True
        return False

    def _selectionStart(self, item, target, event):
        self._selecting = True
        self._marquee.props.visibility = GooCanvas.CanvasItemVisibility.VISIBLE
        self._mousedown = self.from_event(event) + self._get_adjustment(False, True)
        self._marquee.props.width = 0
        self._marquee.props.height = 0
        self.pointer_grab(self.get_root_item(), Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK, self._cursor, event.time)
        return True

    def _selectionEnd(self, item, target, event):
        self.pointer_ungrab(self.get_root_item(), event.time)
        self._selecting = False
        self._marquee.props.visibility = GooCanvas.CanvasItemVisibility.INVISIBLE
        if not self._got_motion_notify:
            self._timeline.selection.setSelection([], 0)
            self.app.current.seeker.seek(Zoomable.pixelToNs(event.x))
        elif self._timeline is not None:
            self._got_motion_notify = False
            mode = 0
            if event.get_state()[1] & Gdk.ModifierType.SHIFT_MASK:
                mode = 1
            if event.get_state()[1] & Gdk.ModifierType.CONTROL_MASK:
                mode = 2
            selected = self._objectsUnderMarquee()
            self._timeline.selection.setSelection(self._objectsUnderMarquee(), mode)
        return True

    def _objectsUnderMarquee(self):
        items = self.get_items_in_area(self._marquee.get_bounds(), True, True, True)
        if items:
            return set((item.element for item in items if isinstance(item,
                TrackObject) and item.bg in items))
        return set()

## playhead implementation

    position = 0

    def timelinePositionChanged(self, position):
        self.position = position
        self._playhead.props.x = self.nsToPixel(position)

    max_duration = 0

    def setMaxDuration(self, duration):
        self.max_duration = duration
        self._request_size()

    def _request_size(self):
        alloc = self.get_allocation()
        self.set_bounds(0, 0, alloc.width, alloc.height)
        self._playhead.props.height = max(0, self.height + SPACING)

    def _size_allocate_cb(self, widget, allocation):
        self._request_size()

    def zoomChanged(self):
        self.queue_draw()

## snapping indicator
    def _snapCb(self, unused_timeline, obj1, obj2, position):
        """
        Display or hide a snapping indicator line
        """
        if position == 0:
            self._snapEndedCb()
        else:
            self.debug("Snapping indicator at %d" % position)
            self._snap_indicator.props.x = Zoomable.nsToPixel(position)
            self._snap_indicator.props.height = self.height
            self._snap_indicator.props.visibility = GooCanvas.CanvasItemVisibility.VISIBLE

    def _snapEndedCb(self, *args):
        self._snap_indicator.props.visibility = GooCanvas.CanvasItemVisibility.INVISIBLE

    def _buttonReleasedCb(self, canvas, event):
        # select clicked layer, if any
        x, y = self.from_event(event) + self._get_adjustment(True, True)
        self.app.gui.timeline_ui.controls.selectLayerControlForY(y)

        # also hide snap indicator
        self._snapEndedCb()

## settings callbacks
    def _setSettings(self):
        self.zoomChanged()

    settings = receiver(_setSettings)

    @handler(settings, "edgeSnapDeadbandChanged")
    def _edgeSnapDeadbandChangedCb(self, settings):
        self.zoomChanged()

## Timeline callbacks

    def setTimeline(self, timeline):
        while self._tracks:
            self._trackRemovedCb(None, 0)

        if self._timeline is not None:
            self._timeline.disconnect_by_func(self._trackAddedCb)
            self._timeline.disconnect_by_func(self._trackRemovedCb)
            self._timeline.disconnect_by_func(self._snapCb)
            self._timeline.disconnect_by_func(self._snapEndedCb)

        self._timeline = timeline
        if self._timeline is not None:
            for track in self._timeline.get_tracks():
                self._trackAddedCb(None, track)

            self._timeline.connect("track-added", self._trackAddedCb)
            self._timeline.connect("track-removed", self._trackRemovedCb)
            self._timeline.connect("snapping-started", self._snapCb)
            self._timeline.connect("snapping-ended", self._snapEndedCb)

        self.zoomChanged()

    def getTimeline(self):
        return self._timeline

    timeline = property(getTimeline, setTimeline, None, "The timeline property")

    def _trackAddedCb(self, timeline, track):
        track = Track(self.app, track, self._timeline)
        self._tracks.append(track)
        track.set_canvas(self)
        self.tracks.add_child(track, -1)
        self.regroupTracks()

    def _trackRemovedCb(self, unused_timeline, position):
        track = self._tracks[position]
        del self._tracks[position]
        track.remove()
        self.regroupTracks()

    def regroupTracks(self):
        """
        Make it so we have a real differentiation between the Audio tracks
        and video tracks
        This method should be called each time a change happen in the timeline
        """
        height = 0
        for i, track in enumerate(self._tracks):
            track.set_simple_transform(0, height, 1, 0)
            height += track.height
        self.height = height
        self._request_size()

    def updateTracks(self):
        self.debug("Updating all TrackObjects")
        for track in self._tracks:
            track.updateTrackObjects()


class TimelineControls(Gtk.VBox, Loggable):
    """
    Holds and manages the LayerControlWidgets
    """

    __gsignals__ = {
       "selection-changed": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (GObject.TYPE_PYOBJECT,),)
       }

    def __init__(self, instance):
        Gtk.VBox.__init__(self)
        Loggable.__init__(self)
        self.app = instance
        self._layer_controls = {}
        self._selected_layer = None
        self._timeline = None
        self.set_spacing(0)
        self.separator_height = 0
        self.type_map = {GES.TrackType.AUDIO: AudioLayerControl,
                         GES.TrackType.VIDEO: VideoLayerControl}
        self.connect("size-allocate", self._sizeAllocatedCb)
        self.priority_block = sys.maxint
        self.priority_block_time = time.time()

        # drag'n' drop
        self.connect("drag_drop", self._dragDropCb)
        self.connect("drag_motion", self._dragMotionCb)
        self.connect("drag_leave", self._dragLeaveCb)
        self.drag_dest_set(Gtk.DestDefaults.ALL,
                             [LAYER_CONTROL_TARGET_ENTRY], Gdk.DragAction.MOVE)

    def _sizeAllocatedCb(self, widget, alloc):
        if self.get_children():
            self.separator_height = self.get_children()[0].getSeparatorHeight()
        self.app.gui.timeline_ui._canvas.updateTracks()

## Timeline callbacks

    def getTimeline(self):
        return self._timeline

    def setTimeline(self, timeline):
        self.debug("Setting timeline %s", timeline)

        # remove old layer controls
        for layer in self._layer_controls.copy():
            self._layerRemovedCb(None, layer)

        if timeline:
            for layer in timeline.get_layers():
                self._layerAddedCb(None, layer)

            timeline.connect("layer-added", self._layerAddedCb)
            timeline.connect("layer-removed", self._layerRemovedCb)
            self.connect = True

        elif self._timeline:
            self._timeline.disconnect_by_func(self._layerAddedCb)
            self._timeline.disconnect_by_func(self._layerRemovedCb)

        self._timeline = timeline

    timeline = property(getTimeline, setTimeline, None, "The timeline property")

    def _layerAddedCb(self, timeline, layer):
        video_control = VideoLayerControl(self.app, layer)
        audio_control = AudioLayerControl(self.app, layer)

        map = {GES.TrackType.AUDIO: audio_control,
               GES.TrackType.VIDEO: video_control}
        self._layer_controls[layer] = map

        self.pack_start(video_control, False, False, 0)
        self.pack_start(audio_control, False, False, 0)

        audio_control.show()
        video_control.show()

        self._orderControls()
        self._hideLastSeparator()
        self._updatePopupMenus()

    def _layerRemovedCb(self, timeline, layer):
        audio_control = self._layer_controls[layer][GES.TrackType.AUDIO]
        video_control = self._layer_controls[layer][GES.TrackType.VIDEO]

        self.remove(audio_control)
        self.remove(video_control)

        del self._layer_controls[layer]
        self._hideLastSeparator()
        self._updatePopupMenus()

    def _orderControls(self):
        # this works since every layer has audio and video
        middle = len(self.get_children()) / 2
        for child in self.get_children():
            if isinstance(child, VideoLayerControl):
                self.reorder_child(child, child.layer.get_priority())
            elif isinstance(child, AudioLayerControl):
                self.reorder_child(child, middle + child.layer.get_priority())

    def _hideLastSeparator(self):
        if self.get_children():
            for child in self.get_children():
                child.setSeparatorVisibility(True)

            self.get_children()[-1].setSeparatorVisibility(False)

    def _updatePopupMenus(self):
        """
        Update sensitivity of menus

        Should be called after _orderControls as it expects the controls
        in ordered state
        """
        children = self.get_children()

        # handle no layer case
        if not children:
            return

        # handle one layer case
        if len(children) == 2:
            for child in children:
                child.updateMenuSensitivity(-2)
            return

        # all other cases
        last = None
        index = 0
        first = True
        for child in children:
            if type(child) == AudioLayerControl and first:
                index = 0
                last.updateMenuSensitivity(-1)
                first = False

            child.updateMenuSensitivity(index)
            index += 1
            last = child

        last.updateMenuSensitivity(-1)

    def getHeightOfLayer(self, track_type, layer):
        if track_type == GES.TrackType.VIDEO:
            return self._layer_controls[layer][GES.TrackType.VIDEO].getControlHeight()
        else:
            return self._layer_controls[layer][GES.TrackType.AUDIO].getControlHeight()

    def getYOfLayer(self, track_type, layer):
        y = 0
        for child in self.get_children():
            if layer == child.layer and \
                isinstance(child, self.type_map[track_type]):
                return y

            y += child.getHeight()
        return 0

    def getHeightOfTrack(self, track_type):
        y = 0
        for child in self.get_children():
            if isinstance(child, self.type_map[track_type]):
                y += child.getHeight()

        return y - self.separator_height

    def getPriorityForY(self, y):
        priority = -1
        current = 0

        # increment priority for each control we pass
        for child in self.get_children():
            if y <= current:
                return self._limitPriority(priority)

            current += child.getHeight()
            priority += 1

        # another check if priority has been incremented but not returned
        # because there were no more children
        if y <= current:
            return self._limitPriority(priority)

        return 0

    def _limitPriority(self, calculated):
        priority = min(self._getLayerBlock(), calculated)
        self._setLayerBlock(priority)
        return priority

    def _setLayerBlock(self, n):
        if self.priority_block != n:
            self.debug("Blocking UI layer creation")
            self.priority_block = n
            self.priority_block_time = time.time()

    def _getLayerBlock(self):
        if time.time() - self.priority_block_time >= LAYER_CREATION_BLOCK_TIME:
            return sys.maxint
        else:
            return self.priority_block

    def soloLayer(self, layer):
        """
        Enable this layer and disable all others
        """
        for key, controls in self._layer_controls.iteritems():
            controls[GES.TrackType.VIDEO].setSoloState(key == layer)
            controls[GES.TrackType.AUDIO].setSoloState(key == layer)

    def selectLayerControl(self, layer_control):
        """
        Select layer_control and unselect all other controls
        """
        layer = layer_control.layer
        # if selected layer changed
        if self._selected_layer != layer:
            self._selected_layer = layer
            self.emit("selection-changed", layer)

        for key, controls in self._layer_controls.iteritems():
            # selected widget not in this layer
            if key != layer:
                controls[GES.TrackType.VIDEO].selected = False
                controls[GES.TrackType.AUDIO].selected = False
            # selected widget in this layer
            else:
                if type(layer_control) is AudioLayerControl:
                    controls[GES.TrackType.VIDEO].selected = False
                    controls[GES.TrackType.AUDIO].selected = True
                else:  # video
                    controls[GES.TrackType.VIDEO].selected = True
                    controls[GES.TrackType.AUDIO].selected = False

    def getSelectedLayer(self):
        return self._selected_layer

    def selectLayerControlForY(self, y):
        """
        Check if y is in the bounds of a layer control
        """
        current_y = 0
        # count height
        for child in self.get_children():
            # calculate upper bound
            next_y = current_y + child.getControlHeight()

            # if y is in bounds, activate control and terminate
            if y >= current_y and y <= next_y:
                self.selectLayerControl(child)
                return
            # else check next control
            else:
                current_y += child.getHeight()

    def _dragDropCb(self, widget, context, x, y, time):
        """
        Handles received drag data to reorder layers
        """
        widget = Gtk.drag_get_source_widget(context)
        self._unhighlightSeparators()

        current = self.getControlIndex(widget)
        index = self._getIndexForPosition(y, widget)

        # if current control is before desired index move one place less
        if current < index:
            index -= 1

        self.moveControlWidget(widget, index)

    def _dragLeaveCb(self, widget, context, timestamp):
        self._unhighlightSeparators()

    def _dragMotionCb(self, widget, context, x, y, timestamp):
        """
        Highlight separator where control would go when dropping
        """
        index = self._getIndexForPosition(y, Gtk.drag_get_source_widget(context))

        self._unhighlightSeparators()

        # control would go in first position
        if index == 0:
            pass
        else:
            self.get_children()[index - 1].setSeparatorHighlight(True)

    def _unhighlightSeparators(self):
        for child in self.get_children():
            child.setSeparatorHighlight(False)

    def _getIndexForPosition(self, y, widget):
        """
        Calculates the new index for a dragged layer
        """
        counter = 0
        index = 0
        last = None

        # find new index
        for child in self.get_children():
            next = counter + child.getControlHeight()

            # add height of last separator
            if last:
                next += last.getSeparatorHeight()

            # check if current interval matches y
            if y >= counter and y < next:
                return self._limitPositionIndex(index, widget)

            # setup next iteration
            counter = next
            index += 1
            last = child

        # return a limited index
        return self._limitPositionIndex(index, widget)

    def _limitPositionIndex(self, index, widget):
        """
        Limit the index depending on the type of widget
        """
        limit = len(self.get_children()) / 2
        if type(widget) == AudioLayerControl:
            return max(index, limit)
        else:
            return min(index, limit)

    def moveControlWidget(self, control, index):
        """
        Moves control to the given index and cares for moving the linked layer
        as well as updating separators
        """
        self.reorder_child(control, index)

        # reorder linked audio/video layer
        widget_type = type(control)
        index = 0
        for child in self.get_children():
            # only set layer priority once
            if type(child) == widget_type:
                child.layer.set_priority(index)
                index += 1

        # order controls and update separators
        self._orderControls()
        self._hideLastSeparator()
        self._updatePopupMenus()

    def getControlIndex(self, control):
        """
        Returns an unique ID of a control

        Used for drag and drop
        """
        counter = 0
        for child in self.get_children():
            if child == control:
                return counter

            counter += 1

    def getControlFromId(self, id):
        """
        Returns the control for an ID

        Used for drag and drop
        """
        counter = 0
        for child in self.get_children():
            if counter == id:
                return child

            counter += 1


class InfoStub(Gtk.HBox, Loggable):
    """
    Box used to display information on the current state of the timeline
    """

    def __init__(self):
        Gtk.HBox.__init__(self)
        Loggable.__init__(self)
        self.errors = []
        self._scroll_pos_ns = 0
        self._errorsmessage = _("One or more GStreamer errors occured!")
        self._makeUI()

    def _makeUI(self):
        self.set_spacing(SPACING)
        self.erroricon = Gtk.Image.new_from_stock(Gtk.STOCK_DIALOG_WARNING,
                                                  Gtk.IconSize.SMALL_TOOLBAR)

        self.pack_start(self.erroricon, False, True, 0)

        self.infolabel = Gtk.Label(label=self._errorsmessage)
        self.infolabel.set_alignment(0, 0.5)

        self.questionbutton = Gtk.Button()
        self.infoicon = Gtk.Image()
        self.infoicon.set_from_stock(Gtk.STOCK_INFO, Gtk.IconSize.SMALL_TOOLBAR)
        self.questionbutton.add(self.infoicon)
        self.questionbutton.connect("clicked", self._questionButtonClickedCb)

        self.pack_start(self.infolabel, True, True, 0)
        self.pack_start(self.questionbutton, False, True, 0)

    def addErrors(self, *args):
        self.errors.append(args)
        self.show()

    def _errorDialogBoxCloseCb(self, dialog):
        dialog.destroy()

    def _errorDialogBoxResponseCb(self, dialog, unused_response):
        dialog.destroy()

    def _questionButtonClickedCb(self, unused_button):
        msgs = (_("Error List"),
            _("The following errors have been reported:"))
        # show error dialog
        dbox = FileListErrorDialog(*msgs)
        dbox.connect("close", self._errorDialogBoxCloseCb)
        dbox.connect("response", self._errorDialogBoxResponseCb)
        for reason, extra in self.errors:
            dbox.addFailedFile(None, reason, extra)
        dbox.show()
        # reset error list
        self.errors = []
        self.hide()

    def show(self):
        self.log("showing")
        self.show_all()


class Timeline(Gtk.Table, Loggable, Zoomable):
    """
    Initiate and manage the timeline's user interface components.

    This class is not to be confused with project.py's
    "timeline" instance of GESTimeline.
    """

    def __init__(self, instance, ui_manager):
        Gtk.Table.__init__(self, rows=2, columns=1, homogeneous=False)
        Loggable.__init__(self)
        Zoomable.__init__(self)
        self.log("Creating Timeline")

        self._updateZoomSlider = True
        self.ui_manager = ui_manager
        self.app = instance
        self._temp_objects = []
        self._drag_started = False
        self._factories = None
        self._finish_drag = False
        self._createUI()
        self._framerate = Gst.Fraction(1, 1)
        self._timeline = None

        # Used to insert sources at the end of the timeline
        self._sources_to_insert = []

        self.zoomed_fitted = True

        # Timeline edition related fields
        self._creating_tckobjs_sigid = {}
        self._move_context = None

        self._project = None
        self._projectmanager = None

        # The IDs of the various gobject signals we connect to
        self._signal_ids = []

        self._settings = self.app.settings
        self._settings.connect("edgeSnapDeadbandChanged",
                self._snapDistanceChangedCb)

    def _createUI(self):
        self.leftSizeGroup = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self.props.row_spacing = 2
        self.props.column_spacing = 2
        self.hadj = Gtk.Adjustment()
        self.vadj = Gtk.Adjustment()

        # zooming slider's "zoom fit" button
        zoom_controls_hbox = Gtk.HBox()
        zoom_fit_btn = Gtk.Button()
        zoom_fit_btn.set_relief(Gtk.ReliefStyle.NONE)
        zoom_fit_btn.set_tooltip_text(ZOOM_FIT)
        zoom_fit_icon = Gtk.Image()
        zoom_fit_icon.set_from_stock(Gtk.STOCK_ZOOM_FIT, Gtk.IconSize.BUTTON)
        zoom_fit_btn_hbox = Gtk.HBox()
        zoom_fit_btn_hbox.pack_start(zoom_fit_icon, False, True, 0)
        zoom_fit_btn_hbox.pack_start(Gtk.Label(_("Zoom")), False, True, 0)
        zoom_fit_btn.add(zoom_fit_btn_hbox)
        zoom_fit_btn.connect("clicked", self._zoomFitCb)
        zoom_controls_hbox.pack_start(zoom_fit_btn, False, True, 0)
        # zooming slider
        self._zoomAdjustment = Gtk.Adjustment()
        self._zoomAdjustment.set_value(Zoomable.getCurrentZoomLevel())
        self._zoomAdjustment.connect("value-changed", self._zoomAdjustmentChangedCb)
        self._zoomAdjustment.props.lower = 0
        self._zoomAdjustment.props.upper = Zoomable.zoom_steps
        zoomslider = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, adjustment=self._zoomAdjustment)
        zoomslider.props.draw_value = False
        zoomslider.set_tooltip_text(_("Zoom Timeline"))
        zoomslider.connect("scroll-event", self._zoomSliderScrollCb)
        zoomslider.set_size_request(100, 0)  # At least 100px wide for precision
        zoom_controls_hbox.pack_start(zoomslider, True, True, 0)
        self.attach(zoom_controls_hbox, 0, 1, 0, 1, yoptions=0, xoptions=Gtk.AttachOptions.FILL)

        # controls for tracks and layers
        self.controls = TimelineControls(self.app)
        controlwindow = Gtk.Viewport(None, None)
        controlwindow.add(self.controls)
        controlwindow.set_size_request(-1, 1)
        controlwindow.set_shadow_type(Gtk.ShadowType.OUT)
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.add(controlwindow)
        scrolledwindow.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        scrolledwindow.props.vscrollbar_policy = Gtk.PolicyType.ALWAYS
        scrolledwindow.props.vadjustment = self.vadj
        # We need ALWAYS policy for correct sizing, but we don't want the
        # scrollbar to be visible. Yay gtk3!
        scrollbar = scrolledwindow.get_vscrollbar()

        def scrollbar_show_cb(scrollbar):
            scrollbar.hide()

        scrollbar.connect("show", scrollbar_show_cb)
        scrollbar.hide()
        self.attach(scrolledwindow, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL)

        # timeline ruler
        self.ruler = ruler.ScaleRuler(self.app, self.hadj)
        self.ruler.set_size_request(0, 25)
        self.ruler.connect("key-press-event", self._keyPressEventCb)
        rulerframe = Gtk.Frame()
        rulerframe.set_shadow_type(Gtk.ShadowType.OUT)
        rulerframe.add(self.ruler)
        self.attach(rulerframe, 1, 2, 0, 1, yoptions=0)

        # proportional timeline
        self._canvas = TimelineCanvas(self.app)
        self._root_item = self._canvas.get_root_item()
        self.attach(self._canvas, 1, 2, 1, 2)

        # scrollbar
        self._hscrollbar = Gtk.HScrollbar(self.hadj)
        self._vscrollbar = Gtk.VScrollbar(self.vadj)
        self.attach(self._hscrollbar, 1, 2, 2, 3, yoptions=0)
        self.attach(self._vscrollbar, 2, 3, 1, 2, xoptions=0)
        self.hadj.connect("value-changed", self._updateScrollPosition)
        self.vadj.connect("value-changed", self._updateScrollPosition)

        # error infostub
        self.infostub = InfoStub()
        self.attach(self.infostub, 1, 2, 4, 5, yoptions=0)

        self.show_all()
        self.infostub.hide()

        # toolbar actions
        actions = (
            ("ZoomIn", Gtk.STOCK_ZOOM_IN, None,
            "<Control>plus", ZOOM_IN, self._zoomInCb),

            ("ZoomOut", Gtk.STOCK_ZOOM_OUT, None,
            "<Control>minus", ZOOM_OUT, self._zoomOutCb),

            ("ZoomFit", Gtk.STOCK_ZOOM_FIT, None,
            "<Control>0", ZOOM_FIT, self._zoomFitCb),

            ("Screenshot", None, _("Export current frame..."),
            None, _("Export the frame at the current playhead "
                    "position as an image file."), self._screenshotCb),

            # Alternate keyboard shortcuts to the actions above
            ("ControlEqualAccel", Gtk.STOCK_ZOOM_IN, None,
            "<Control>equal", ZOOM_IN, self._zoomInCb),

            ("ControlKPAddAccel", Gtk.STOCK_ZOOM_IN, None,
            "<Control>KP_Add", ZOOM_IN, self._zoomInCb),

            ("ControlKPSubtractAccel", Gtk.STOCK_ZOOM_OUT, None,
            "<Control>KP_Subtract", ZOOM_OUT, self._zoomOutCb),
        )

        selection_actions = (
            ("DeleteObj", Gtk.STOCK_DELETE, None,
            "Delete", DELETE, self.deleteSelected),

            ("UnlinkObj", "pitivi-unlink", None,
            "<Shift><Control>L", UNLINK, self.unlinkSelected),

            ("LinkObj", "pitivi-link", None,
            "<Control>L", LINK, self.linkSelected),

            ("UngroupObj", "pitivi-ungroup", None,
            "<Shift><Control>G", UNGROUP, self.ungroupSelected),

            ("GroupObj", "pitivi-group", None,
            "<Control>G", GROUP, self.groupSelected),

            ("AlignObj", "pitivi-align", None,
            "<Shift><Control>A", ALIGN, self.alignSelected),
        )

        playhead_actions = (
            ("PlayPause", Gtk.STOCK_MEDIA_PLAY, None,
            "space", _("Start Playback"), self.playPause),

            ("Split", "pitivi-split", _("Split"),
            "S", SPLIT, self.split),

            ("Keyframe", "pitivi-keyframe", _("Add a Keyframe"),
            "K", KEYFRAME, self.keyframe),

            ("Prevkeyframe", None, _("_Previous Keyframe"),
            "comma", PREVKEYFRAME, self._previousKeyframeCb),

            ("Nextkeyframe", None, _("_Next Keyframe"),
            "period", NEXTKEYFRAME, self._nextKeyframeCb),
        )

        actiongroup = Gtk.ActionGroup("timelinepermanent")
        actiongroup.add_actions(actions)
        self.ui_manager.insert_action_group(actiongroup, 0)

        self.selection_actions = Gtk.ActionGroup("timelineselection")
        self.selection_actions.add_actions(selection_actions)
        self.selection_actions.set_sensitive(False)
        self.ui_manager.insert_action_group(self.selection_actions, -1)
        self.playhead_actions = Gtk.ActionGroup("timelineplayhead")
        self.playhead_actions.add_actions(playhead_actions)
        self.ui_manager.insert_action_group(self.playhead_actions, -1)

        self.ui_manager.add_ui_from_string(ui)

        # drag and drop

        self._canvas.drag_dest_set(Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT,
                                   [FILESOURCE_TARGET_ENTRY, EFFECT_TARGET_ENTRY],
                                   Gdk.DragAction.COPY)

        self._canvas.drag_dest_add_text_targets()

        self._canvas.connect("drag-leave", self._dragLeaveCb)
        self._canvas.connect("drag-drop", self._dragDropCb)
        self._canvas.connect("drag-motion", self._dragMotionCb)
        self._canvas.connect("key-press-event", self._keyPressEventCb)
        self._canvas.connect("scroll-event", self._scrollEventCb)

## Event callbacks
    def _keyPressEventCb(self, unused_widget, event):
        kv = event.keyval
        self.debug("kv:%r", kv)
        if kv not in [Gdk.KEY_Left, Gdk.KEY_Right]:
            return False
        mod = event.get_state()
        try:
            if mod & Gdk.ModifierType.CONTROL_MASK:
                now = self._project.pipeline.getPosition()
                ltime, rtime = self._project.timeline.edges.closest(now)

            if kv == Gdk.KEY_Left:
                if mod & Gdk.ModifierType.SHIFT_MASK:
                    self._seeker.seekRelative(0 - Gst.SECOND)
                elif mod & Gdk.ModifierType.CONTROL_MASK:
                    self._seeker.seek(ltime + 1)
                else:
                    self.app.current.pipeline.stepFrame(self._framerate, -1)
            elif kv == Gdk.KEY_Right:
                if mod & Gdk.ModifierType.SHIFT_MASK:
                    self._seeker.seekRelative(Gst.SECOND)
                elif mod & Gdk.ModifierType.CONTROL_MASK:
                    self._seeker.seek(rtime + 1)
                else:
                    self.app.current.pipeline.stepFrame(self._framerate, 1)
        finally:
            return True

## Drag and Drop callbacks

    def _dragMotionCb(self, unused, context, x, y, timestamp):
        # Set up the initial data when we first initiate the drag operation
        if not self._drag_started:
            self._drag_started = True
        elif context.list_targets() not in DND_EFFECT_LIST and self.app.gui.medialibrary.dragged:
            if not self._temp_objects and not self._creating_tckobjs_sigid:
                self._create_temp_source(x, y)

            # Let some time for TrackObject-s to be created
            if self._temp_objects and not self._creating_tckobjs_sigid:
                focus = self._temp_objects[0]
                if self._move_context is  None:
                    self._move_context = EditingContext(focus,
                            self.timeline, GES.EditMode.EDIT_NORMAL, GES.Edge.EDGE_NONE,
                            set(self._temp_objects[1:]), self.app.settings)

                self._move_temp_source(x, y)
        return True

    def _dragLeaveCb(self, unused_layout, context, unused_tstamp):
        """
        This occurs when the user leaves the canvas area during a drag,
        or when the item being dragged has been dropped.

        Since we always get a "drag-dropped" signal right after "drag-leave",
        we wait 75 ms to see if a drop happens and if we need to cleanup or not.
        """
        self.debug("Drag leave")
        self._canvas.handler_block_by_func(self._dragMotionCb)
        GObject.timeout_add(75, self._dragCleanUp, context)

    def _dragCleanUp(self, context):
        """
        If the user drags outside the timeline,
        remove the temporary objects we had created during the drap operation.
        """
        # If TrackObject-s still being created, wait before deleting
        if self._creating_tckobjs_sigid:
            return True

        # Clean up only if clip was not dropped already
        if self._drag_started:
            self.debug("Drag cleanup")
            self._drag_started = False
            self._factories = []
            if context.list_targets() not in DND_EFFECT_LIST:
                self.timeline.enable_update(True)
                self.debug("Need to cleanup %d objects" % len(self._temp_objects))
                for obj in self._temp_objects:
                    layer = obj.get_layer()
                    layer.remove_object(obj)
                self._temp_objects = []
                self._move_context = None

            self.debug("Drag cleanup ended")
        self._canvas.handler_unblock_by_func(self._dragMotionCb)
        return False

    def _dragDropCb(self, widget, context, x, y, timestamp):
        # Resetting _drag_started will tell _dragCleanUp to not do anything
        self._drag_started = False
        self.debug("Drag drop")

        if self.app.gui.medialibrary.dragged:
            self._canvas.drag_unhighlight()
            self.app.action_log.begin("add clip")
            if self._move_context is not None:
                self._move_context.finish()
                self._move_context = None
            self.app.action_log.commit()
            # The temporary objects and factories that we had created
            # in _dragMotionCb are now kept for good.
            # Clear the temporary references to objects, as they are real now.
            self._temp_objects = []
            self._factories = []
            #context.drop_finish(True, timestamp)
        else:
            if self.app.current.timeline.props.duration == 0:
                return False
            timeline_objs = self._getTimelineObjectUnderMouse(x, y)
            if timeline_objs:
                # FIXME make a util function to add effects
                # instead of copy/pasting it from cliproperties
                bin_desc = self.app.gui.effectlist.getSelectedItems()
                media_type = self.app.effects.getFactoryFromName(bin_desc).media_type

                # Trying to apply effect only on the first object of the selection
                tlobj = timeline_objs[0]

                # Checking that this effect can be applied on this track object
                # Which means, it has the corresponding media_type
                for tckobj in tlobj.get_track_objects():
                    track = tckobj.get_track()
                    if track.get_property("track_type") == GES.TrackType.AUDIO and \
                            media_type == AUDIO_EFFECT or \
                            track.get_property("track_type") == GES.TrackType.VIDEO and \
                            media_type == VIDEO_EFFECT:
                        #Actually add the effect
                        self.app.action_log.begin("add effect")
                        effect = GES.TrackParseLaunchEffect(bin_description=bin_desc)
                        tlobj.add_track_object(effect)
                        track.add_object(effect)
                        self.app.gui.clipconfig.effect_expander.updateAll()
                        self.app.action_log.commit()
                        self._factories = None
                        self._seeker.flush()

                        self.timeline.selection.setSelection(timeline_objs, SELECT)
                        break
        Gtk.drag_finish(context, True, False, timestamp)
        return True

    def _getTimelineObjectUnderMouse(self, x, y):
        timeline_objs = []
        items_in_area = self._canvas.getItemsInArea(x, y, x + 1, y + 1)

        track_objects = [obj for obj in items_in_area[1]]
        for track_object in track_objects:
            timeline_objs.append(track_object.get_timeline_object())

        return timeline_objs

    def _showSaveScreenshotDialog(self):
        """
        Show a filechooser dialog asking the user where to save the snapshot
        and what file type to use.

        Returns a list containing the full path and the mimetype if successful,
        returns none otherwise.
        """
        chooser = Gtk.FileChooserDialog(_("Save As..."), self.app.gui,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        chooser.set_icon_name("pitivi")
        chooser.set_select_multiple(False)
        chooser.set_current_name(_("Untitled"))
        chooser.props.do_overwrite_confirmation = True
        formats = {_("PNG image"): ["image/png", ("png",)],
            _("JPEG image"): ["image/jpeg", ("jpg", "jpeg")]}
        for format in formats:
            filt = Gtk.FileFilter()
            filt.set_name(format)
            filt.add_mime_type(formats.get(format)[0])
            chooser.add_filter(filt)
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            chosen_format = formats.get(chooser.get_filter().get_name())
            chosen_ext = chosen_format[1][0]
            chosen_mime = chosen_format[0]
            uri = join(chooser.get_current_folder(), chooser.get_filename())
            ret = [uri + "." + chosen_ext, chosen_mime]
        else:
            ret = None
        chooser.destroy()
        return ret

    def _ensureLayer(self):
        """
        Make sure we have a layer in our timeline

        Returns: The number of layer present in self.timeline
        """
        layers = self.timeline.get_layers()

        if (len(layers) == 0):
            layer = GES.TimelineLayer()
            layer.props.auto_transition = True
            self.timeline.add_layer(layer)
            layers = [layer]

        return layers

    def purgeObject(self, uri):
        """Remove all instances of a clip from the timeline."""
        quoted_uri = quote_uri(uri)
        layers = self.timeline.get_layers()
        for layer in layers:
            for tlobj in layer.get_objects():
                if hasattr(tlobj, "get_uri"):
                    if quote_uri(tlobj.get_uri()) == quoted_uri:
                        layer.remove_object(tlobj)
                else:
                    # TimelineStandardTransition and the like don't have URIs
                    # GES will remove those transitions automatically.
                    self.debug("Not removing %s from timeline as it has no URI" % tlobj)

    def _create_temp_source(self, x, y):
        """
        Create temporary clips to be displayed on the timeline during a
        drag-and-drop operation.
        """
        layer = self._ensureLayer()[0]
        duration = 0

        for uri in self.app.gui.medialibrary.getSelectedItems():
            info = self._project.medialibrary.getInfoFromUri(uri)
            src = GES.TimelineFileSource(uri=uri)
            src.props.start = duration
            # Set image duration
            # FIXME: after GES Materials are merged, check if image instead
            if src.props.duration == 0:
                src.set_duration(long(self._settings.imageClipLength) * Gst.SECOND / 1000)
            duration += info.get_duration()
            layer.add_object(src)
            id = src.connect("track-object-added", self._trackObjectsCreatedCb, src, x, y)
            self._creating_tckobjs_sigid[src] = id

    def _trackObjectsCreatedCb(self, unused_tl, track_object, tlobj, x, y):
        # Make sure not to start the moving process before the TrackObject-s
        # are created. We concider that the time between the different
        # TrackObject-s creation is short enough so we are all good when the
        # first TrackObject is added to the TimelineObject
        if tlobj.is_image():
            tlobj.set_duration(long(self._settings.imageClipLength) * Gst.SECOND / 1000)
        self._temp_objects.insert(0, tlobj)
        tlobj.disconnect(self._creating_tckobjs_sigid[tlobj])
        del self._creating_tckobjs_sigid[tlobj]

    def _move_temp_source(self, x, y):
        x = self.hadj.props.value + x
        y = self.vadj.props.value + y

        priority = self.controls.getPriorityForY(y)

        delta = Zoomable.pixelToNs(x)
        self._move_context.editTo(delta, priority)

## Zooming and Scrolling

    def _scrollEventCb(self, canvas, event):
        if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            # shift + scroll => vertical (up/down) scroll
            if event.direction == Gdk.ScrollDirection.UP:
                self.scroll_up()
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.scroll_down()
            event.props.state &= ~Gdk.SHIFT_MASK
        elif event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            # zoom + scroll => zooming (up: zoom in)
            if event.direction == Gdk.ScrollDirection.UP:
                Zoomable.zoomIn()
                self.log("Setting 'zoomed_fitted' to False")
                self.zoomed_fitted = False
                return True
            elif event.direction == Gdk.ScrollDirection.DOWN:
                Zoomable.zoomOut()
                self.log("Setting 'zoomed_fitted' to False")
                self.zoomed_fitted = False
                return True
            return False
        else:
            if event.direction == Gdk.ScrollDirection.UP:
                self.scroll_left()
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.scroll_right()
        return True

    def scroll_left(self):
        self._hscrollbar.set_value(self._hscrollbar.get_value() -
            self.hadj.props.page_size ** (2.0 / 3.0))

    def scroll_right(self):
        self._hscrollbar.set_value(self._hscrollbar.get_value() +
            self.hadj.props.page_size ** (2.0 / 3.0))

    def scroll_up(self):
        self._vscrollbar.set_value(self._vscrollbar.get_value() -
            self.vadj.props.page_size ** (2.0 / 3.0))

    def scroll_down(self):
        self._vscrollbar.set_value(self._vscrollbar.get_value() +
            self.vadj.props.page_size ** (2.0 / 3.0))

    def unsureVadjHeight(self):
        self._scroll_pos_ns = Zoomable.pixelToNs(self.hadj.get_value())
        self._root_item.set_simple_transform(0 - self.hadj.get_value(),
            0 - self.vadj.get_value(), 1.0, 0)

    def _updateScrollPosition(self, adjustment):
        self.unsureVadjHeight()

    def _zoomAdjustmentChangedCb(self, adjustment):
        # GTK crack
        self._updateZoomSlider = False
        Zoomable.setZoomLevel(int(adjustment.get_value()))
        self.log("Setting 'zoomed_fitted' to False")
        self.zoomed_fitted = False
        self._updateZoomSlider = True

    def _zoomSliderScrollCb(self, unused_widget, event):
        value = self._zoomAdjustment.get_value()
        if event.direction in [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.RIGHT]:
            self._zoomAdjustment.set_value(value + 1)
        elif event.direction in [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.LEFT]:
            self._zoomAdjustment.set_value(value - 1)

    def zoomChanged(self):
        if self._updateZoomSlider:
            self._zoomAdjustment.set_value(self.getCurrentZoomLevel())

        if self._settings and self._timeline:
            # zoomChanged might be called various times before the UI is ready
            self._timeline.props.snapping_distance = \
                Zoomable.pixelToNs(self._settings.edgeSnapDeadband)

        # the new scroll position should preserve the current horizontal
        # position of the playhead in the window
        cur_playhead_offset = self._canvas._playhead.props.x - self.hadj.props.value
        try:
            position = self.app.current.pipeline.getPosition()
        except PipelineError:
            position = 0
        new_pos = Zoomable.nsToPixel(position) - cur_playhead_offset

        # Update the position of the playhead's line on the canvas
        # This does not actually change the timeline position
        self._canvas._playhead.props.x = Zoomable.nsToPixel(position)

        self.updateHScrollAdjustments()
        self.scrollToPosition(new_pos)
        self.ruler.queue_resize()
        self.ruler.queue_draw()

    def positionChangedCb(self, seeker, position):
        self.ruler.timelinePositionChanged(position)
        self._canvas.timelinePositionChanged(position)
        if self.app.current.pipeline.getState() == Gst.State.PLAYING:
            self.scrollToPlayhead()

    def scrollToPlayhead(self):
        """
        If the current position is out of the view bounds, then scroll
        as close to the center of the view as possible or as close as the
        timeline canvas allows.
        """
        canvas_size = self._canvas.get_allocation().width
        new_pos = Zoomable.nsToPixel(self.app.current.pipeline.getPosition())
        scroll_pos = self.hadj.get_value()
        if (new_pos > scroll_pos + canvas_size) or (new_pos < scroll_pos):
            self.scrollToPosition(min(new_pos - canvas_size / 6,
                                      self.hadj.props.upper - canvas_size - 1))
        return False

    def scrollToPosition(self, position):
        if position > self.hadj.props.upper:
            # we can't perform the scroll because the canvas needs to be
            # updated
            GObject.idle_add(self._scrollToPosition, position)
        else:
            self._scrollToPosition(position)

    def _scrollToPosition(self, position):
        self._hscrollbar.set_value(position)
        return False

    def _snapDistanceChangedCb(self, settings):
        if self._timeline:
            self._timeline.props.snapping_distance = \
                Zoomable.pixelToNs(settings.edgeSnapDeadband)

    def _setBestZoomRatio(self):
        """
        Set the zoom level so that the entire timeline is in view.
        """
        ruler_width = self.ruler.get_allocation().width
        # Add Gst.SECOND - 1 to the timeline duration to make sure the
        # last second of the timeline will be in view.
        duration = self.timeline.get_duration()
        if duration == 0:
            self.debug("The timeline duration is 0, impossible to calculate zoom")
            return

        timeline_duration = duration + Gst.SECOND - 1
        timeline_duration_s = int(timeline_duration / Gst.SECOND)

        self.debug("duration: %s, timeline duration: %s" % (duration,
           print_ns(timeline_duration)))

        ideal_zoom_ratio = float(ruler_width) / timeline_duration_s
        nearest_zoom_level = Zoomable.computeZoomLevel(ideal_zoom_ratio)
        Zoomable.setZoomLevel(nearest_zoom_level)
        self.timeline.props.snapping_distance = \
            Zoomable.pixelToNs(self.app.settings.edgeSnapDeadband)

        # Only do this at the very end, after updating the other widgets.
        self.log("Setting 'zoomed_fitted' to True")
        self.zoomed_fitted = True

## Project callbacks

    def _projectChangedCb(self, app, project):
        """
        When a new blank project is created, immediately clear the timeline.

        Otherwise, we would sit around until a clip gets imported to the
        media library, waiting for a "ready" signal.
        """
        self.debug("New blank project created, pre-emptively clearing the timeline")
        self.setProject(project)

    def setProject(self, project):
        self.debug("Setting project %s", project)
        if self._project:
            self._project.disconnect_by_function(self._settingsChangedCb)
            self._pipeline.disconnect_by_func(self.positionChangedCb)
            self.pipeline = None

        self._project = project
        if self._project:
            self.setTimeline(project.timeline)
            self.ruler.setProjectFrameRate(self._project.getSettings().videorate)
            self.ruler.zoomChanged()
            self._settingsChangedCb(self._project, None, self._project.getSettings())

            self._seeker = self._project.seeker
            self._pipeline = self._project.pipeline
            self._pipeline.connect("position", self.positionChangedCb)
            self._project.connect("settings-changed", self._settingsChangedCb)
            self._setBestZoomRatio()

    def setProjectManager(self, projectmanager):
        if self._projectmanager is not None:
            self._projectmanager.disconnect_by_func(self._projectChangedCb)

        self._projectmanager = projectmanager
        if projectmanager is not None:
            projectmanager.connect("new-project-loaded", self._projectChangedCb)

    def _settingsChangedCb(self, project, old, new):
        self._framerate = new.videorate
        self.ruler.setProjectFrameRate(self._framerate)

## Timeline callbacks

    def setTimeline(self, timeline):
        self.debug("Setting timeline %s", timeline)

        self.delTimeline()
        self.controls.timeline = timeline
        self._timeline = timeline

        if timeline:
            # Connecting to timeline gobject signals
            self._signal_ids.append(timeline.connect("layer-added",
                    self._layerAddedCb))
            self._signal_ids.append(timeline.connect("layer-removed",
                    self._layerRemovedCb))
            self._signal_ids.append(timeline.connect("notify::update",
                    self._timelineUpdateChangedCb))
            self._signal_ids.append(timeline.connect("notify::duration",
                    self._timelineDurationChangedCb))

            # The Selection object of _timeline inherits signallable
            # We will be able to disconnect it with disconnect_by_func
            self._timeline.selection.connect("selection-changed", self._selectionChangedCb)

            # Make sure to set the current layer in use
            self._layerAddedCb(None, None)
            self._timeline.props.snapping_distance = \
                Zoomable.pixelToNs(self._settings.edgeSnapDeadband)

        self._canvas.setTimeline(timeline)
        self._canvas.zoomChanged()

    def getTimeline(self):
        return self._timeline

    def delTimeline(self):
        # Disconnect signals
        for sigid in self._signal_ids:
            self._timeline.disconnect(sigid)
        self._signal_ids = []
        if hasattr(self._timeline, "selection"):
            self._timeline.selection.disconnect_by_func(self._selectionChangedCb)

        #Remove references to the ges timeline
        self._timeline = None
        self.controls.timeline = None

    timeline = property(getTimeline, setTimeline, delTimeline, "The GESTimeline")

    def _timelineDurationChangedCb(self, timeline, unused_duration):
        self.updateHScrollAdjustments()

    def _timelineUpdateChangedCb(self, unused, unsued2=None):
        if self.zoomed_fitted is True:
            self._setBestZoomRatio()

    def _layerAddedCb(self, unused_layer, unused_user_data):
        self.updateVScrollAdjustments()

    def _layerRemovedCb(self, unused_layer, unused_user_data):
        self.updateVScrollAdjustments()

    def updateVScrollAdjustments(self):
        """
        Recalculate the vertical scrollbar depending on the number of layer in
        the timeline.
        """
        self.vadj.props.upper = self.controls.get_allocation().height + 50

    def updateHScrollAdjustments(self):
        """
        Recalculate the horizontal scrollbar depending on the timeline duration.
        """
        timeline_ui_width = self.get_allocation().width
        controls_width = self.controls.get_allocation().width
        scrollbar_width = self._vscrollbar.get_allocation().width
        contents_size = Zoomable.nsToPixel(self.app.current.timeline.props.duration)

        widgets_width = controls_width + scrollbar_width
        end_padding = 250  # Provide some space for clip insertion at the end

        self.hadj.props.lower = 0
        self.hadj.props.upper = contents_size + widgets_width + end_padding
        self.hadj.props.page_size = timeline_ui_width
        self.hadj.props.page_increment = contents_size * 0.9
        self.hadj.props.step_increment = contents_size * 0.1

        if contents_size + widgets_width <= timeline_ui_width:
            # We're zoomed out completely, re-enable automatic zoom fitting
            # when adding new clips.
            self.log("Setting 'zoomed_fitted' to True")
            self.zoomed_fitted = True

    def _selectionChangedCb(self, selection):
        """
        The selected clips on the timeline canvas have changed with the
        "selection-changed" signal.

        This is where you apply global UI changes, unlike individual
        track elements' "selected-changed" signal from the Selected class.
        """
        if selection:
            self.selection_actions.set_sensitive(True)
        else:
            self.selection_actions.set_sensitive(False)

## ToolBar callbacks
    def _zoomFitCb(self, unused, unsued2=None):
        self._setBestZoomRatio()

    def _zoomInCb(self, unused_action):
        # This only handles the button callbacks (from the menus),
        # not keyboard shortcuts or the zoom slider!
        Zoomable.zoomIn()
        self.log("Setting 'zoomed_fitted' to False")
        self.zoomed_fitted = False

    def _zoomOutCb(self, unused_action):
        # This only handles the button callbacks (from the menus),
        # not keyboard shortcuts or the zoom slider!
        Zoomable.zoomOut()
        self.log("Setting 'zoomed_fitted' to False")
        self.zoomed_fitted = False

    def deleteSelected(self, unused_action):
        if self.timeline:
            self.app.action_log.begin("delete clip")
            #FIXME GES port: Handle unlocked TrackObject-s
            for obj in self.timeline.selection:
                layer = obj.get_layer()
                layer.remove_object(obj)
            self.app.action_log.commit()

    def unlinkSelected(self, unused_action):
        if self.timeline:
            self.timeline.unlinkSelection()

    def linkSelected(self, unused_action):
        if self.timeline:
            self.timeline.linkSelection()

    def ungroupSelected(self, unused_action):
        if self.timeline:
            self.debug("Ungouping selected clips %s" % self.timeline.selection)
            self.timeline.enable_update(False)
            self.app.action_log.begin("ungroup")
            for tlobj in self.timeline.selection:
                tlobj.objects_set_locked(False)
            self.timeline.enable_update(True)
            self.app.action_log.commit()

    def groupSelected(self, unused_action):
        if self.timeline:
            self.debug("Gouping selected clips %s" % self.timeline.selection)
            self.timeline.enable_update(False)
            self.app.action_log.begin("group")
            for tlobj in self.timeline.selection:
                tlobj.objects_set_locked(True)
            self.app.action_log.commit()
            self.timeline.enable_update(True)

    def alignSelected(self, unused_action):
        if "NumPy" in soft_deps:
            DepsManager(self.app)

        elif self.timeline:
            progress_dialog = AlignmentProgressDialog(self.app)
            progress_dialog.window.show()
            self.app.action_log.begin("align")
            self.timeline.enable_update(False)

            def alignedCb():  # Called when alignment is complete
                self.timeline.enable_update(True)
                self.app.action_log.commit()
                progress_dialog.window.destroy()

            pmeter = self.timeline.alignSelection(alignedCb)
            pmeter.addWatcher(progress_dialog.updatePosition)

    def split(self, action):
        """
        Split clips at the current playhead position, regardless of selections.
        """
        self.timeline.enable_update(False)
        position = self.app.current.pipeline.getPosition()
        for track in self.timeline.get_tracks():
            for tck_obj in track.get_objects():
                start = tck_obj.get_start()
                end = start + tck_obj.get_duration()
                if start < position and end > position:
                    obj = tck_obj.get_timeline_object()
                    obj.split(position)
        self.timeline.enable_update(True)

    def keyframe(self, action):
        """
        Add or remove a keyframe at the current position of the selected clip.

        FIXME GES: this method is currently not used anywhere
        """
        selected = self.timeline.selection.getSelectedTrackObjs()
        for obj in selected:
            keyframe_exists = False
            position = self.app.current.pipeline.getPosition()
            position_in_obj = (position - obj.start) + obj.in_point
            interpolators = obj.getInterpolators()
            for value in interpolators:
                interpolator = obj.getInterpolator(value)
                keyframes = interpolator.getInteriorKeyframes()
                for kf in keyframes:
                    if kf.getTime() == position_in_obj:
                        keyframe_exists = True
                        self.app.action_log.begin("remove volume point")
                        interpolator.removeKeyframe(kf)
                        self.app.action_log.commit()
                if keyframe_exists == False:
                    self.app.action_log.begin("add volume point")
                    interpolator.newKeyframe(position_in_obj)
                    self.app.action_log.commit()

    def playPause(self, unused_action):
        self.app.current.pipeline.togglePlayback()

    def _previousKeyframeCb(self, action):
        position = self.app.current.pipeline.getPosition()
        prev_kf = self.timeline.getPrevKeyframe(position)
        if prev_kf:
            self._seeker.seek(prev_kf)
            self.scrollToPlayhead()

    def _nextKeyframeCb(self, action):
        position = self.app.current.pipeline.getPosition()
        next_kf = self.timeline.getNextKeyframe(position)
        if next_kf:
            self._seeker.seek(next_kf)
            self.scrollToPlayhead()

    def _screenshotCb(self, unused_action):
        """
        Export a snapshot of the current frame as an image file.
        """
        foo = self._showSaveScreenshotDialog()
        if foo:
            path, mime = foo[0], foo[1]
            self._project.pipeline.save_thumbnail(-1, -1, mime, path)

    def insertEnd(self, sources):
        """
        Add source at the end of the timeline
        @type sources: An L{GES.TimelineSource}
        @param x2: A list of sources to add to the timeline
        """
        self.app.action_log.begin("add clip")
        # Handle the case of a blank project
        self._ensureLayer()
        self._sources_to_insert = sources

        # Start adding sources in the timeline
        self._insertNextSource()

    def _insertNextSource(self):
        """ Insert a source at the end of the timeline's first track """
        timeline = self.app.current.timeline

        if not self._sources_to_insert:
            # We need to wait (100ms is enoug for sure) for TrackObject-s to
            # be added to the Tracks
            # FIXME remove this "hack" when Materials are merged
            GObject.timeout_add(100, self._finalizeSourceAdded)
            self.app.action_log.commit()

            # Update zoom level if needed
            return
        source = self._sources_to_insert.pop()
        layer = timeline.get_layers()[0]  # FIXME Get the longest layer
        # Waiting for the TrackObject to be created because of a race
        # condition, and to know the real length of the timeline when
        # adding several sources at a time.
        # connecting before adding, as it signaled before connection
        source.connect("track-object-added", self._trackObjectAddedCb)
        layer.add_object(source)

    def _trackObjectAddedCb(self, source, trackobj):
        """ After an object has been added to the first track, position it
        correctly and request the next source to be processed. """
        timeline = self.app.current.timeline
        layer = timeline.get_layers()[0]  # FIXME Get the longest layer

        # Set the duration of the clip if it is an image
        if hasattr(source, "is_image") and source.is_image():
            source.set_duration(long(self._settings.imageClipLength) * Gst.SECOND / 1000)

        # Handle the case where we just inserted the first clip
        if len(layer.get_objects()) == 1:
            source.props.start = 0
        else:
            source.props.start = timeline.props.duration

        # We only need one TrackObject to estimate the new duration.
        # Process the next source.
        source.disconnect_by_func(self._trackObjectAddedCb)
        self._insertNextSource()

    def _finalizeSourceAdded(self):
        timeline = self.app.current.timeline
        self.app.current.seeker.seek(timeline.props.duration)
        if self.zoomed_fitted is True:
            self._setBestZoomRatio()
        return False
