# PiTiVi , Non-linear video editor
#
#       pitivi/ui/timeline.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
Timeline widgets for the complex view
"""

import gtk

from pitivi.log.loggable import Loggable
import ruler
import dnd
import gst
import gobject
import ges

from gettext import gettext as _
from timelinecanvas import TimelineCanvas
from timelinecontrols import TimelineControls
from pitivi.receiver import receiver, handler
from zoominterface import Zoomable
from pitivi.ui.common import LAYER_HEIGHT_EXPANDED, LAYER_SPACING, TRACK_SPACING
from pitivi.timeline.timeline import MoveContext, SELECT
from pitivi.ui.filelisterrordialog import FileListErrorDialog
from pitivi.ui.common import SPACING
from pitivi.ui.alignmentprogress import AlignmentProgressDialog
from pitivi.ui.depsmanager import DepsManager
#from pitivi.timeline.align import AutoAligner
from pitivi.check import soft_deps

DND_EFFECT_LIST = [[dnd.VIDEO_EFFECT_TUPLE[0], dnd.EFFECT_TUPLE[0]],\
                  [dnd.AUDIO_EFFECT_TUPLE[0], dnd.EFFECT_TUPLE[0]]]
VIDEO_EFFECT_LIST = [dnd.VIDEO_EFFECT_TUPLE[0], dnd.EFFECT_TUPLE[0]],
AUDIO_EFFECT_LIST = [dnd.AUDIO_EFFECT_TUPLE[0], dnd.EFFECT_TUPLE[0]],

# tooltip text for toolbar
DELETE = _("Delete Selected")
SPLIT = _("Split clip at playhead position")
KEYFRAME = _("Add a keyframe")
PREVFRAME = _("Move to the previous keyframe")
NEXTFRAME = _("Move to the next keyframe")
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
                <menuitem action="Keyframe" />
                <separator />
                <menuitem action="DeleteObj" />
                <menuitem action="LinkObj" />
                <menuitem action="UnlinkObj" />
                <menuitem action="GroupObj" />
                <menuitem action="UngroupObj" />
                <menuitem action="AlignObj" />
                <separator />
                <menuitem action="Prevframe" />
                <menuitem action="Nextframe" />
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
    <accelerator action="DeleteObj" />
    <accelerator action="ControlEqualAccel" />
    <accelerator action="ControlKPAddAccel" />
    <accelerator action="ControlKPSubtractAccel" />
</ui>
'''


class InfoStub(gtk.HBox, Loggable):
    """
    Box used to display information on the current state of the timeline
    """

    def __init__(self):
        gtk.HBox.__init__(self)
        Loggable.__init__(self)
        self.errors = []
        self._scroll_pos_ns = 0
        self._errorsmessage = _("One or more GStreamer errors occured!")
        self._makeUI()

    def _makeUI(self):
        self.set_spacing(SPACING)
        self.erroricon = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING,
                                                  gtk.ICON_SIZE_SMALL_TOOLBAR)

        self.pack_start(self.erroricon, expand=False)

        self.infolabel = gtk.Label(self._errorsmessage)
        self.infolabel.set_alignment(0, 0.5)

        self.questionbutton = gtk.Button()
        self.infoicon = gtk.Image()
        self.infoicon.set_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.questionbutton.add(self.infoicon)
        self.questionbutton.connect("clicked", self._questionButtonClickedCb)

        self.pack_start(self.infolabel, expand=True, fill=True)
        self.pack_start(self.questionbutton, expand=False)

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


class Timeline(gtk.Table, Loggable, Zoomable):

    def __init__(self, instance, ui_manager):
        gtk.Table.__init__(self, rows=2, columns=1, homogeneous=False)
        Loggable.__init__(self)
        Zoomable.__init__(self)
        self.log("Creating Timeline")

        self._updateZoom = True
        self.project = None
        self.ui_manager = ui_manager
        self.app = instance
        self._temp_objects = None
        self._factories = None
        self._finish_drag = False
        self._position = 0
        self._state = gst.STATE_NULL
        self._createUI()
        self._prev_duration = 0
        self.rate = gst.Fraction(1, 1)

        self._temp_objects = []

    def _createUI(self):
        self.leftSizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        self.props.row_spacing = 2
        self.props.column_spacing = 2
        self.hadj = gtk.Adjustment()
        self.vadj = gtk.Adjustment()

        # zooming slider's "zoom fit" button
        zoom_controls_hbox = gtk.HBox()
        zoom_fit_btn = gtk.Button()
        zoom_fit_btn.set_relief(gtk.RELIEF_NONE)
        zoom_fit_btn.set_tooltip_text(ZOOM_FIT)
        zoom_fit_icon = gtk.Image()
        zoom_fit_icon.set_from_stock(gtk.STOCK_ZOOM_FIT, gtk.ICON_SIZE_BUTTON)
        zoom_fit_btn_hbox = gtk.HBox()
        zoom_fit_btn_hbox.pack_start(zoom_fit_icon)
        zoom_fit_btn_hbox.pack_start(gtk.Label(_("Zoom")))
        zoom_fit_btn.add(zoom_fit_btn_hbox)
        zoom_fit_btn.connect("clicked", self._zoomFitCb)
        zoom_controls_hbox.pack_start(zoom_fit_btn)
        # zooming slider
        self._zoomAdjustment = gtk.Adjustment()
        self._zoomAdjustment.set_value(Zoomable.getCurrentZoomLevel())
        self._zoomAdjustment.connect("value-changed",
            self._zoomAdjustmentChangedCb)
        self._zoomAdjustment.props.lower = 0
        self._zoomAdjustment.props.upper = Zoomable.zoom_steps
        zoomslider = gtk.HScale(self._zoomAdjustment)
        zoomslider.props.draw_value = False
        zoomslider.set_tooltip_text(_("Zoom Timeline"))
        zoomslider.connect("scroll-event", self._zoomSliderScrollCb)
        zoomslider.set_size_request(100, 0)  # At least 100px wide for precision
        zoom_controls_hbox.pack_start(zoomslider)
        self.attach(zoom_controls_hbox, 0, 1, 0, 1, yoptions=0, xoptions=gtk.FILL)

        # controls for tracks and layers
        self._controls = TimelineControls()
        controlwindow = gtk.Viewport(None, self.vadj)
        controlwindow.add(self._controls)
        controlwindow.set_size_request(-1, 1)
        controlwindow.set_shadow_type(gtk.SHADOW_OUT)
        self.attach(controlwindow, 0, 1, 1, 2, xoptions=gtk.FILL)

        # timeline ruler
        self.ruler = ruler.ScaleRuler(self.app, self.hadj)
        self.ruler.set_size_request(0, 25)
        #self.ruler.set_border_width(2)
        self.ruler.connect("key-press-event", self._keyPressEventCb)
        self.ruler.connect("size-allocate", self._rulerSizeAllocateCb)
        rulerframe = gtk.Frame()
        rulerframe.set_shadow_type(gtk.SHADOW_OUT)
        rulerframe.add(self.ruler)
        self.attach(rulerframe, 1, 2, 0, 1, yoptions=0)

        # proportional timeline
        self._canvas = TimelineCanvas(self.app)
        self._root_item = self._canvas.get_root_item()
        self.attach(self._canvas, 1, 2, 1, 2)
        self.vadj.connect("changed", self._unsureVadjHeightCb)

        # scrollbar
        self._hscrollbar = gtk.HScrollbar(self.hadj)
        self._vscrollbar = gtk.VScrollbar(self.vadj)
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
            ("ZoomIn", gtk.STOCK_ZOOM_IN, None, "<Control>plus", ZOOM_IN,
                self._zoomInCb),
            ("ZoomOut", gtk.STOCK_ZOOM_OUT, None, "<Control>minus", ZOOM_OUT,
                self._zoomOutCb),
            ("ZoomFit", gtk.STOCK_ZOOM_FIT, None, None, ZOOM_FIT,
                self._zoomFitCb),

            # actions for adding additional accelerators
            ("ControlEqualAccel", gtk.STOCK_ZOOM_IN, None, "<Control>equal", ZOOM_IN,
                self._zoomInCb),
            ("ControlKPAddAccel", gtk.STOCK_ZOOM_IN, None, "<Control>KP_Add", ZOOM_IN,
                self._zoomInCb),
            ("ControlKPSubtractAccel", gtk.STOCK_ZOOM_OUT, None, "<Control>KP_Subtract", ZOOM_OUT,
                self._zoomOutCb),
        )

        selection_actions = (
            ("DeleteObj", gtk.STOCK_DELETE, None, "Delete", DELETE,
                self.deleteSelected),
            ("UnlinkObj", "pitivi-unlink", None, "<Shift><Control>L", UNLINK,
                self.unlinkSelected),
            ("LinkObj", "pitivi-link", None, "<Control>L", LINK,
                self.linkSelected),
            ("UngroupObj", "pitivi-ungroup", None, "<Shift><Control>G", UNGROUP,
                self.ungroupSelected),
            ("GroupObj", "pitivi-group", None, "<Control>G", GROUP,
                self.groupSelected),
            ("AlignObj", "pitivi-align", None, "<Shift><Control>A", ALIGN,
                self.alignSelected),
        )

        self.playhead_actions = (
            ("Split", "pitivi-split", _("Split"), "S", SPLIT,
                self.split),
            ("Keyframe", "pitivi-keyframe", _("Add a Keyframe"), "K", KEYFRAME,
                self.keyframe),
            ("Prevframe", "pitivi-prevframe", _("_Previous Keyframe"), "E", PREVFRAME,
                self.prevframe),
            ("Nextframe", "pitivi-nextframe", _("_Next Keyframe"), "R", NEXTFRAME,
                self.nextframe),
        )

        actiongroup = gtk.ActionGroup("timelinepermanent")
        actiongroup.add_actions(actions)
        self.ui_manager.insert_action_group(actiongroup, 0)

        actiongroup = gtk.ActionGroup("timelineselection")
        actiongroup.add_actions(selection_actions)
        actiongroup.add_actions(self.playhead_actions)
        self.link_action = actiongroup.get_action("LinkObj")
        self.unlink_action = actiongroup.get_action("UnlinkObj")
        self.group_action = actiongroup.get_action("GroupObj")
        self.ungroup_action = actiongroup.get_action("UngroupObj")
        self.align_action = actiongroup.get_action("AlignObj")
        self.delete_action = actiongroup.get_action("DeleteObj")
        self.split_action = actiongroup.get_action("Split")
        self.keyframe_action = actiongroup.get_action("Keyframe")
        self.prevframe_action = actiongroup.get_action("Prevframe")
        self.nextframe_action = actiongroup.get_action("Nextframe")

        self.ui_manager.insert_action_group(actiongroup, -1)

        self.ui_manager.add_ui_from_string(ui)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_MOTION,
            [dnd.FILESOURCE_TUPLE, dnd.EFFECT_TUPLE],
            gtk.gdk.ACTION_COPY)

        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.connect("drag-leave", self._dragLeaveCb)
        self.connect("drag-drop", self._dragDropCb)
        self.connect("drag-motion", self._dragMotionCb)
        self._canvas.connect("key-press-event", self._keyPressEventCb)
        self._canvas.connect("scroll-event", self._scrollEventCb)

## Event callbacks
    def _keyPressEventCb(self, unused_widget, event):
        kv = event.keyval
        self.debug("kv:%r", kv)
        if kv not in [gtk.keysyms.Left, gtk.keysyms.Right]:
            return False
        mod = event.get_state()
        try:
            if mod & gtk.gdk.CONTROL_MASK:
                now = self.project.pipeline.getPosition()
                ltime, rtime = self.project.timeline.edges.closest(now)

            if kv == gtk.keysyms.Left:
                if mod & gtk.gdk.SHIFT_MASK:
                    self._seekRelative(0 - gst.SECOND)
                elif mod & gtk.gdk.CONTROL_MASK:
                    self._seeker.seek(ltime + 1)
                else:
                    self._seekRelative(0 - long(self.rate * gst.SECOND))
            elif kv == gtk.keysyms.Right:
                if mod & gtk.gdk.SHIFT_MASK:
                    self._seekRelative(gst.SECOND)
                elif mod & gtk.gdk.CONTROL_MASK:
                    self._seeker.seek(rtime + 1)
                else:
                    self._seekRelative(long(self.rate * gst.SECOND))
        finally:
            return True

    def _seekRelative(self, time):
        pipeline = self.project.pipeline
        seekvalue = max(0, min(pipeline.getPosition() + time,
            pipeline.getDuration()))
        self._seeker.seek(seekvalue)

## Drag and Drop callbacks

    def _dragMotionCb(self, unused, context, x, y, timestamp):

        atom = gtk.gdk.atom_intern(dnd.FILESOURCE_TUPLE[0])

        self.drag_get_data(context, atom, timestamp)
        self.drag_highlight()
        if  context.targets not in DND_EFFECT_LIST:
            if not self._temp_objects:
                self._add_temp_source()
                focus = self._temp_objects[0]
                self._move_context = MoveContext(self.timeline,
                        focus, set(self._temp_objects[1:]))
            self._move_temp_source(self.hadj.props.value + x, y)
        return True

    def _dragLeaveCb(self, unused_layout, context, unused_tstamp):
        if self._temp_objects:
            self._temp_objects = []

        self.drag_unhighlight()
        self.app.projectManager.current.timeline.enable_update(True)

    def _dragDropCb(self, widget, context, x, y, timestamp):
            #FIXME GES break, reimplement me
        if  context.targets not in DND_EFFECT_LIST:
            self.app.action_log.begin("add clip")
            self.app.action_log.commit()

            return True
        elif context.targets in DND_EFFECT_LIST:
            if not self.timeline.timeline_objects:
                return False
            factory = self._factories[0]
            timeline_objs = self._getTimelineObjectUnderMouse(x, y, factory.getInputStreams()[0])
            if timeline_objs:
                self.app.action_log.begin("add effect")
                self.timeline.addEffectFactoryOnObject(factory,
                                               timeline_objects=timeline_objs)
                self.app.action_log.commit()
                self._factories = None
                self.app.current.seeker.seek(self._position)
                context.drop_finish(True, timestamp)

                self.timeline.selection.setSelection(timeline_objs, SELECT)

            return True

        return False

    def _dragDataReceivedCb(self, unused_layout, context, x, y,
        selection, targetType, timestamp):
        self.app.projectManager.current.timeline.enable_update(False)
        self.log("SimpleTimeline, targetType:%d, selection.data:%s" %
            (targetType, selection.data))
        # FIXME: let's have just one target type, call it
        # TYPE_PITIVI_OBJECTFACTORY.
        # TODO: handle uri targets by doign an import-add. This would look
        # something like this:
        # tell current project to import the uri
        # wait for source-added signal, meanwhile ignore dragMotion signals
        # when ready, add factories to the timeline.
        self.selection_data = selection.data

        if targetType not in [dnd.TYPE_PITIVI_FILESOURCE, dnd.TYPE_PITIVI_EFFECT]:
            context.finish(False, False, timestamp)
            return

        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uris = selection.data.split("\n")
            self._factories = [self.project.sources.getUri(uri) for uri in uris]
        else:
            if not self.timeline.timeline_objects:
                return False
            self._factories = [self.app.effects.getFactoryFromName(selection.data)]

        context.drag_status(gtk.gdk.ACTION_COPY, timestamp)
        return True

    def _getTimelineObjectUnderMouse(self, x, y, stream):
        timeline_objs = []
        items_in_area = self._canvas.getItemsInArea(x, y - 15, x + 1, y - 30)
        tracks = [obj for obj in items_in_area[0]]
        track_objects = [obj for obj in items_in_area[1]]
        for track_object in track_objects:
            if (type(stream) == type(track_object.stream)):
                timeline_objs.append(track_object.timeline_object)

        return timeline_objs

    def _add_temp_source(self):
        uris = self.selection_data.split("\n")
        for layer in self.app.projectManager.current.timeline.get_layers():
            if layer.get_priority() != 99:
                break
        for uri in uris:
            src = ges.TimelineFileSource(uri)
            src.set_property("priority", 1)
            layer.add_object(src)
            self._temp_objects.insert(0, src)

    def _move_temp_source(self, x, y):
        x1, y1, x2, y2 = self._controls.get_allocation()
        offset = 10 + (x2 - x1)
        x, y = self._canvas.convert_from_pixels(x - offset, y)
        priority = int((y // (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)))
        delta = Zoomable.pixelToNs(x)
        obj = self._temp_objects[0]
        obj.starting_start = obj.get_property("start")
        self._move_context.editTo(delta, priority)

## Zooming and Scrolling

    def _scrollEventCb(self, canvas, event):
        if event.state & gtk.gdk.SHIFT_MASK:
            # shift + scroll => vertical (up/down) scroll
            if event.direction == gtk.gdk.SCROLL_UP:
                self.scroll_up()
            elif event.direction == gtk.gdk.SCROLL_DOWN:
                self.scroll_down()
            event.state &= ~gtk.gdk.SHIFT_MASK
        elif event.state & gtk.gdk.CONTROL_MASK:
            # zoom + scroll => zooming (up: zoom in)
            if event.direction == gtk.gdk.SCROLL_UP:
                Zoomable.zoomIn()
                return True
            elif event.direction == gtk.gdk.SCROLL_DOWN:
                Zoomable.zoomOut()
                return True
            return False
        else:
            if event.direction == gtk.gdk.SCROLL_UP:
                self.scroll_left()
            elif event.direction == gtk.gdk.SCROLL_DOWN:
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
        self._updateZoom = False
        Zoomable.setZoomLevel(int(adjustment.get_value()))
        self._updateZoom = True

    def _unsureVadjHeightCb(self, adj):
        # GTK crack, without that, at loading a project, the vadj upper
        # property is reset to be equal as the lower, right after the
        # trackobjects are added to the timeline (bug: #648714)
        if self.vadj.props.upper < self._canvas.height:
            self.vadj.props.upper = self._canvas.height

    _scroll_pos_ns = 0

    def _zoomSliderScrollCb(self, unused_widget, event):
        value = self._zoomAdjustment.get_value()
        if event.direction in [gtk.gdk.SCROLL_UP, gtk.gdk.SCROLL_RIGHT]:
            self._zoomAdjustment.set_value(value + 1)
        elif event.direction in [gtk.gdk.SCROLL_DOWN, gtk.gdk.SCROLL_LEFT]:
            self._zoomAdjustment.set_value(value - 1)

    def zoomChanged(self):
        if self._updateZoom:
            self._zoomAdjustment.set_value(self.getCurrentZoomLevel())

        # the new scroll position should preserve the current horizontal
        # position of the playhead in the window
        cur_playhead_offset = self._canvas._playhead.props.x -\
            self.hadj.props.value
        new_pos = Zoomable.nsToPixel(self._position) - cur_playhead_offset

        self._updateScrollAdjustments()
        self._scrollToPosition(new_pos)
        self.ruler.queue_resize()
        self.ruler.queue_draw()

    def timelinePositionChanged(self, position):
        self._position = position
        self.ruler.timelinePositionChanged(position)
        self._canvas.timelinePositionChanged(position)
        if self._state == gst.STATE_PLAYING:
            self.scrollToPlayhead()

    def stateChanged(self, state):
        self._state = state

    def scrollToPlayhead(self):
        """
        If the current position is out of the view bouds, then scroll
        as close to the center of the view as possible or as close as the
        timeline canvas allows.
        """
        page_size = self.hadj.get_page_size()

        new_pos = Zoomable.nsToPixel(self._position)
        scroll_pos = self.hadj.get_value()
        if (new_pos > scroll_pos + page_size) or (new_pos < scroll_pos):
            self.scrollToPosition(min(new_pos - page_size / 2, self.hadj.upper - page_size - 1))
        return False

    def scrollToPosition(self, position):
        if position > self.hadj.upper:
            # we can't perform the scroll because the canvas needs to be
            # updated
            gobject.idle_add(self._scrollToPosition, position)
        else:
            self._scrollToPosition(position)

    def _scrollToPosition(self, position):
        self._hscrollbar.set_value(position)
        return False

    def _rulerSizeAllocateCb(self, ruler, allocation):
        self._canvas.props.redraw_when_scrolled = False

## Project callbacks

    def _setProject(self):
        if self.project:
            self.timeline = self.project.timeline
            self._controls.timeline = self.timeline
            self._canvas.timeline = self.timeline
            self._canvas.set_timeline()
            self._canvas.zoomChanged()
            self.ruler.setProjectFrameRate(self.project.getSettings().videorate)
            self.ruler.zoomChanged()
            self._settingsChangedCb(self.project, None, self.project.getSettings())
            self._seeker = self.project.seeker

    #FIXME GES port
    project = receiver(_setProject)

    @handler(project, "settings-changed")
    def _settingsChangedCb(self, project, old, new):
        rate = new.videorate
        self.rate = float(1 / rate)
        self.ruler.setProjectFrameRate(rate)

## Timeline callbacks

    def _setTimeline(self):
        if self.timeline:
            self._timelineSelectionChanged(self.timeline)
            self._timelineStartDurationChanged(self.timeline,
                self.timeline.duration)

        self._controls.timeline = self.timeline

    def _updateScrollAdjustments(self):
        a = self.get_allocation()
        size = Zoomable.nsToPixel(self.timeline.duration)
        self.hadj.props.lower = 0
        self.hadj.props.upper = size + 200  # why is this necessary???
        self.hadj.props.page_size = a.width
        self.hadj.props.page_increment = size * 0.9
        self.hadj.props.step_increment = size * 0.1

## ToolBar callbacks
    def _zoomFitCb(self, unused_action):
        self.app.gui.setBestZoomRatio()

    def _zoomInCb(self, unused_action):
        Zoomable.zoomIn()

    def _zoomOutCb(self, unused_action):
        Zoomable.zoomOut()

    def deleteSelected(self, unused_action):
        self.app.projectManager.current.pipeline.set_state(gst.STATE_NULL)
        if self.timeline:
            self.app.action_log.begin("delete clip")
            for track_object in self.timeline.selected:
                obj = track_object.get_timeline_object()
                obj.release_track_object(track_object)
                track = track_object.get_track()
                track.remove_object(track_object)
                remove = True
                for tck_obj in obj.get_track_objects():
                    if isinstance(tck_obj, ges.TrackSource):
                        remove = False
                if remove:
                    lyr = obj.get_layer()
                    lyr.remove_object(obj)
                    print "removed"
            self.app.action_log.commit()
        self.app.projectManager.current.pipeline.set_state(gst.STATE_PAUSED)

    def unlinkSelected(self, unused_action):
        if self.timeline:
            self.timeline.unlinkSelection()

    def linkSelected(self, unused_action):
        if self.timeline:
            self.timeline.linkSelection()

    def ungroupSelected(self, unused_action):
        if self.timeline:
            self.app.action_log.begin("ungroup")
            for track_object in self.timeline.selected:
                track_object.set_locked(False)
            self.app.action_log.commit()

    def groupSelected(self, unused_action):
        if self.timeline:
            for track_object in self.timeline.selected:
                track_object.set_locked(True)

    def alignSelected(self, unused_action):
        if "NumPy" in soft_deps:
            DepsManager(self.app)

        elif self.timeline:
            progress_dialog = AlignmentProgressDialog(self.app)
            progress_dialog.window.show()
            self.app.action_log.begin("align")
            self.timeline.disableUpdates()

            def alignedCb():  # Called when alignment is complete
                self.timeline.enableUpdates()
                self.app.action_log.commit()
                progress_dialog.window.destroy()

            pmeter = self.timeline.alignSelection(alignedCb)
            pmeter.addWatcher(progress_dialog.updatePosition)

    def split(self, action):
        self.timeline.enable_update(False)
        tl_objs_dict = {}
        for track in self.timeline.get_tracks():
            tck_objects = track.get_track_objects_at_position(long(self._position))
            for tck_obj in tck_objects:
                if isinstance(tck_obj, ges.TrackAudioTestSource) or isinstance(tck_obj, ges.TrackVideoTestSource):
                    continue
                obj = tck_obj.get_timeline_object()
                if obj in tl_objs_dict.keys():
                    tl_objs_dict[obj] = "both"
                elif tck_obj.get_track().get_caps().to_string() == "audio/x-raw-int; audio/x-raw-float":
                    tl_objs_dict[obj] = "audio"
                else:
                    tl_objs_dict[obj] = "video"
        for src in tl_objs_dict:
            src.split(self._position)
        self.timeline.enable_update(True)
        # work-around for 603149

    def keyframe(self, action):
        timeline_position = self._position
        selected = self.timeline.selection.getSelectedTrackObjs()

        for obj in selected:
            keyframe_exists = False

            position_in_obj = (timeline_position - obj.start) + obj.in_point
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

    def prevframe(self, action):
        timeline_position = self._position

        prev_kf = self.timeline.getPrevKeyframe(timeline_position)
        if prev_kf != None:
            self._seeker.seek(prev_kf)
            self.scrollToPlayhead()

    def nextframe(self, action):
        timeline_position = self._position

        next_kf = self.timeline.getNextKeyframe(timeline_position)
        if next_kf:
            self._seeker.seek(next_kf)
            self.scrollToPlayhead()
