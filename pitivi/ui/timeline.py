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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Timeline widgets for the complex view
"""

import gtk
import urllib

from pitivi.log.loggable import Loggable
import ruler
import dnd
import gst
import gobject

from gettext import gettext as _
from timelinecanvas import TimelineCanvas
from timelinecontrols import TimelineControls
from pitivi.receiver import receiver, handler
from zoominterface import Zoomable
from pitivi.ui.common import LAYER_HEIGHT_EXPANDED, LAYER_SPACING
from pitivi.timeline.timeline import MoveContext
from pitivi.utils import Seeker
from pitivi.ui.filelisterrordialog import FileListErrorDialog
from pitivi.ui.curve import Curve

# tooltip text for toolbar
DELETE = _("Delete Selected")
SPLIT = _("Split clip at playhead position")
KEYFRAME = _("Add a keyframe")
PREVFRAME = _("Move to the previous keyframe")
NEXTFRAME = _("Move to the next keyframe")
ZOOM_IN =  _("Zoom In")
ZOOM_OUT =  _("Zoom Out")
UNLINK = _("Break links between clips")
LINK = _("Link together arbitrary clips")
UNGROUP = _("Ungroup clips")
GROUP = _("Group clips")
SELECT_BEFORE = ("Select all sources before selected")
SELECT_AFTER = ("Select all after selected")

ui = '''
<ui>
    <menubar name="MainMenuBar">
        <menu action="View">
            <placeholder name="Timeline">
                <menuitem action="ZoomIn" />
                <menuitem action="ZoomOut" />
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
        </placeholder>
    </toolbar>
    <accelerator action="DeleteObj" />
    <accelerator action="ControlEqualAccel" />
    <accelerator action="ControlKPAddAccel" />
    <accelerator action="ControlKPSubtractAccel" />
</ui>
'''

# Complex Timeline Design v2 (08 Feb 2006)
#
#
# Tree of contents (ClassName(ParentClass))
# -----------------------------------------
#
# Timeline(gtk.VBox)
# |  Top container
# |
# +--ScaleRuler(gtk.Layout)
# |
# +--gtk.ScrolledWindow
#    |
#    +--TimelineCanvas(goocanas.Canvas)
#    |  |
#    |  +--Track(SmartGroup)
#    |
#    +--Status Bar ??

class InfoStub(gtk.HBox, Loggable):
    """
    Box used to display information on the current state of the timeline
    """

    def __init__(self):
        gtk.HBox.__init__(self)
        Loggable.__init__(self)
        self.errors = []
        self.showing = False
        self._errorsmessage = _("One or more GStreamer errors has occured!")
        self._makeUI()

    def _makeUI(self):
        self.set_spacing(6)
        self.erroricon = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING,
                                                  gtk.ICON_SIZE_SMALL_TOOLBAR)

        self.pack_start(self.erroricon, expand=False)


        self.infolabel = gtk.Label(self._errorsmessage)
        self.infolabel.set_alignment(0, 0.5)

        self.questionbutton = gtk.Button()
        self.questionbutton.set_image(gtk.image_new_from_stock(gtk.STOCK_INFO,
                                                               gtk.ICON_SIZE_SMALL_TOOLBAR))
        self.questionbutton.connect("clicked", self._questionButtonClickedCb)
        self._questionshowing = False

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
        self.showing = True

    def hide(self):
        self.log("hiding")
        gtk.VBox.hide(self)
        self.showing = False

class Timeline(gtk.Table, Loggable, Zoomable):

    # the screen width of the current unit
    unit_width = 10
    # specific levels of zoom, in (multiplier, unit) pairs which
    # from zoomed out to zoomed in


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
        self.shrink = True
        self.rate = gst.Fraction(1,1)

    def _createUI(self):
        self.leftSizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        self.props.row_spacing = 2
        self.props.column_spacing = 2
        self.hadj = gtk.Adjustment()
        self.vadj = gtk.Adjustment()

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
        self.attach(zoomslider, 0, 1, 0, 1, yoptions=0, xoptions=gtk.FILL)

        # controls for tracks and layers
        self._controls = TimelineControls()
        controlwindow = gtk.Viewport(None, self.vadj)
        controlwindow.add(self._controls)
        controlwindow.set_size_request(-1, 1)
        controlwindow.set_shadow_type(gtk.SHADOW_OUT)
        self.attach(controlwindow, 0, 1, 1, 2, xoptions=0)

        # timeline ruler
        self.ruler = ruler.ScaleRuler(self.app, self.hadj)
        self.ruler.set_size_request(0, 25)
        self.ruler.set_border_width(2)
        self.ruler.connect("key-press-event", self._keyPressEventCb)
        self.ruler.connect("size-allocate", self._rulerSizeAllocateCb)
        rulerframe = gtk.Frame()
        rulerframe.set_shadow_type(gtk.SHADOW_OUT)
        rulerframe.add(self.ruler)
        self.attach(rulerframe, 1, 2, 0, 1, yoptions=0)

        # proportional timeline
        self._canvas = TimelineCanvas(self.app)
        timelinewindow = gtk.ScrolledWindow(self.hadj, self.vadj)
        timelinewindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        timelinewindow.add(self._canvas)
        timelinewindow.set_shadow_type(gtk.SHADOW_IN)
        timelinewindow.set_name("timelinewindow")

        # temp fix for padding between scrollbar and scrolled window
        #FIXME: should be set at an global position for easy editing?
        gtk.rc_parse_string("""
            style 'timelinewindow'
            {
                GtkScrolledWindow::scrollbar-spacing = 0
            }
            widget '*.timelinewindow' style 'timelinewindow'
        """)

        self.attach(timelinewindow, 1, 2, 1, 2)

        # error infostub
        self.infostub = InfoStub()
        self.attach(self.infostub, 1, 2, 2, 3, yoptions=0)

        self.show_all()
        self.infostub.hide()

        # toolbar actions
        actions = (
            ("ZoomIn", gtk.STOCK_ZOOM_IN, None, "<Control>plus", ZOOM_IN,
                self._zoomInCb),
            ("ZoomOut", gtk.STOCK_ZOOM_OUT, None, "<Control>minus", ZOOM_OUT,
                self._zoomOutCb),

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
        )

        playhead_actions = (
            ("Split", "pitivi-split", _("Split"), "S", SPLIT,
                self.split),
            ("Keyframe", "pitivi-keyframe", _("Add a keyframe"), "K", KEYFRAME,
                self.keyframe),
            ("Prevframe", "pitivi-prevframe", _("_Prevframe"), "E", PREVFRAME,
                self.prevframe),
            ("Nextframe", "pitivi-nextframe", _("_Nextframe"), "R", NEXTFRAME,
                self.nextframe),
        )

        actiongroup = gtk.ActionGroup("timelinepermanent")
        actiongroup.add_actions(actions)
        self.ui_manager.insert_action_group(actiongroup, 0)

        actiongroup = gtk.ActionGroup("timelineselection")
        actiongroup.add_actions(selection_actions)
        actiongroup.add_actions(playhead_actions)
        self.link_action = actiongroup.get_action("LinkObj")
        self.unlink_action = actiongroup.get_action("UnlinkObj")
        self.group_action = actiongroup.get_action("GroupObj")
        self.ungroup_action = actiongroup.get_action("UngroupObj")
        self.delete_action = actiongroup.get_action("DeleteObj")
        self.split_action = actiongroup.get_action("Split")
        self.keyframe_action = actiongroup.get_action("Keyframe")
        self.prevframe_action = actiongroup.get_action("Prevframe")
        self.nextframe_action = actiongroup.get_action("Nextframe")

        self.ui_manager.insert_action_group(actiongroup, -1)

        self.ui_manager.add_ui_from_string(ui)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_MOTION, 
            [dnd.FILESOURCE_TUPLE],
            gtk.gdk.ACTION_COPY)

        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.connect("drag-leave", self._dragLeaveCb)
        self.connect("drag-drop", self._dragDropCb)
        self.connect("drag-motion", self._dragMotionCb)
        self._canvas.connect("button-press-event", self._buttonPress)
        self._canvas.connect("button-release-event", self._buttonRelease)
        self._canvas.connect("key-press-event", self._keyPressEventCb)


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
                    self._seekRelative(-gst.SECOND)
                elif mod & gtk.gdk.CONTROL_MASK:
                    self._seeker.seek(ltime+1)
                else:
                    self._seekRelative(-long(self.rate * gst.SECOND))
            elif kv == gtk.keysyms.Right:
                if mod & gtk.gdk.SHIFT_MASK:
                    self._seekRelative(gst.SECOND)
                elif mod & gtk.gdk.CONTROL_MASK:
                    self._seeker.seek(rtime+1)
                else:
                    self._seekRelative(long(self.rate * gst.SECOND))
        finally:
            return True

    def _seekRelative(self, time):
        pipeline = self.project.pipeline
        seekvalue = max(0, min(pipeline.getPosition() + time,
            pipeline.getDuration()))
        self._seeker.seek(seekvalue)

    def _buttonPress(self, window, event):
        self.shrink = False

    def _buttonRelease(self, window, event):
        self.shrink = True
        self._timelineStartDurationChanged(self.timeline,
            self.timeline.duration)

## Drag and Drop callbacks

    def _dragMotionCb(self, unused, context, x, y, timestamp):
        self.warning("self._factories:%r, self._temp_objects:%r",
                     not not self._factories,
                     not not self._temp_objects)
        if self._factories is None:
            atom = gtk.gdk.atom_intern(dnd.FILESOURCE_TUPLE[0])
            self.drag_get_data(context, atom, timestamp)
            self.drag_highlight()
        else:
            # actual drag-and-drop
            if not self._temp_objects:
                self.timeline.disableUpdates()
                self._add_temp_source()
                focus = self._temp_objects[0]
                self._move_context = MoveContext(self.timeline,
                        focus, set(self._temp_objects[1:]))
            self._move_temp_source(self.hadj.props.value + x, y)
        return True

    def _dragLeaveCb(self, unused_layout, unused_context, unused_tstamp):
        if self._temp_objects:
            try:
                for obj in self._temp_objects:
                    self.timeline.removeTimelineObject(obj, deep=True)
            finally:
                self._temp_objects = None
        self.drag_unhighlight()
        self.timeline.enableUpdates()

    def _dragDropCb(self, widget, context, x, y, timestamp):
        self.app.action_log.begin("add clip")
        self.timeline.disableUpdates()
        self._add_temp_source()
        focus = self._temp_objects[0]
        self._move_context = MoveContext(self.timeline,
                focus, set(self._temp_objects[1:]))
        self._move_temp_source(self.hadj.props.value + x, y)
        self._move_context.finish()
        self.timeline.enableUpdates()
        self.app.action_log.commit()
        context.drop_finish(True, timestamp)
        self._factories = None
        self._temp_objects = None
        self.app.current.seeker.seek(self._position)
        return True

    def _dragDataReceivedCb(self, unused_layout, context, x, y,
        selection, targetType, timestamp):
        self.log("SimpleTimeline, targetType:%d, selection.data:%s" %
            (targetType, selection.data))
        # FIXME: let's have just one target type, call it
        # TYPE_PITIVI_OBJECTFACTORY.
        # TODO: handle uri targets by doign an import-add. This would look
        # something like this:
        # tell current project to import the uri
        # wait for source-added signal, meanwhile ignore dragMotion signals
        # when ready, add factories to the timeline.
        if targetType != dnd.TYPE_PITIVI_FILESOURCE:
            context.finish(False, False, timestamp)
            return

        uris = selection.data.split("\n")
        self._factories = [self.project.sources.getUri(uri) for uri in uris]
        context.drag_status(gtk.gdk.ACTION_COPY, timestamp)
        return True

    def _add_temp_source(self):
        self._temp_objects = [self.timeline.addSourceFactory(factory)
            for factory in self._factories]

    def _move_temp_source(self, x, y):
        x1, y1, x2, y2 = self._controls.get_allocation()
        offset = 10 + (x2 - x1)
        x, y = self._canvas.convert_from_pixels(x - offset, y)
        priority = int((y // (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)))
        delta = Zoomable.pixelToNs(x)
        self._move_context.editTo(delta, priority)

## Zooming and Scrolling

    def _zoomAdjustmentChangedCb(self, adjustment):
        # GTK crack
        self._updateZoom = False
        Zoomable.setZoomLevel(int(adjustment.get_value()))
        self._updateZoom = True

    def zoomChanged(self):
        self._canvas.props.redraw_when_scrolled = True
        if self._updateZoom:
            self._zoomAdjustment.set_value(self.getCurrentZoomLevel())
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
        Scroll the current position as close to the center of the view
        as possible (as close as the timeline canvas allows).
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
        self.hadj.set_value(position)
        return False

    def _rulerSizeAllocateCb(self, ruler, allocation):
        self._canvas.props.redraw_when_scrolled = False

## Project callbacks

    def _setProject(self):
        if self.project:
            self.timeline = self.project.timeline
            self._controls.timeline = self.timeline
            self._canvas.timeline = self.timeline
            self._canvas.zoomChanged()
            self.ruler.setProjectFrameRate(self.project.getSettings().videorate)
            self.ruler.zoomChanged()
            self._settingsChangedCb(self.project, None, self.project.getSettings())
            self._seeker = self.project.seeker

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

    timeline = receiver(_setTimeline)

    @handler(timeline, "duration-changed")
    def _timelineStartDurationChanged(self, unused_timeline, duration):
        if self.shrink:
            self._prev_duration = duration
            self.ruler.setMaxDuration(duration + 60 * gst.SECOND)
            self._canvas.setMaxDuration(duration + 60 * gst.SECOND)
            self.ruler.setShadedDuration(duration)
        else:
            # only resize if new size is larger
            if duration > self._prev_duration:
                self._prev_duration = duration
                self.ruler.setMaxDuration(duration)
                self._canvas.setMaxDuration(duration)
                #self.ruler.setShadedDuration(duration)

    @handler(timeline, "selection-changed")
    def _timelineSelectionChanged(self, timeline):
        delete = False
        link = False
        unlink = False
        group = False
        ungroup = False
        split = False
        keyframe = False
        timeline_objects = {}
        if timeline.selection:
            delete = True
            if len(timeline.selection) > 1:
                link = True
                group = True

            start = None
            duration = None
            for obj in self.timeline.selection:
                if obj.link:
                    link = False
                    unlink = True

                if len(obj.track_objects) > 1:
                    ungroup = True

                if start is not None and duration is not None:
                    if obj.start != start or obj.duration != duration:
                        group = False
                else:
                    start = obj.start
                    duration = obj.duration

            split = True
            keyframe = True

        self.delete_action.set_sensitive(delete)
        self.link_action.set_sensitive(link)
        self.unlink_action.set_sensitive(unlink)
        self.group_action.set_sensitive(group)
        self.ungroup_action.set_sensitive(ungroup)
        self.split_action.set_sensitive(split)
        self.keyframe_action.set_sensitive(keyframe)


## ToolBar callbacks

    def hide(self):
        self.actiongroup.set_visible(False)
        gtk.Vbox.hide(self)

    def _zoomInCb(self, unused_action):
        Zoomable.zoomIn()

    def _zoomOutCb(self, unused_action):
        Zoomable.zoomOut()

    def deleteSelected(self, unused_action):
        if self.timeline:
            self.app.action_log.begin("delete clip")
            self.timeline.deleteSelection()
            self.app.action_log.commit()

    def unlinkSelected(self, unused_action):
        if self.timeline:
            self.timeline.unlinkSelection()

    def linkSelected(self, unused_action):
        if self.timeline:
            self.timeline.linkSelection()

    def ungroupSelected(self, unused_action):
        if self.timeline:
            self.app.action_log.begin("ungroup")
            self.timeline.ungroupSelection()
            self.app.action_log.commit()

    def groupSelected(self, unused_action):
        if self.timeline:
            self.timeline.groupSelection()

    def split(self, action):
        self.app.action_log.begin("split")
        self.timeline.disableUpdates()
        self.timeline.split(self._position)
        self.timeline.enableUpdates()
        self.app.action_log.commit()
        # work-around for 603149
        self.project.seeker.seek(self._position)

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
            self.timelinePositionChanged(prev_kf)

    def nextframe(self, action):
        timeline_position = self._position

        next_kf = self.timeline.getNextKeyframe(timeline_position)
        if next_kf:
                self._seeker.seek(next_kf)
                self.timelinePositionChanged(next_kf)
