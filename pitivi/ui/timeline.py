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

# tooltip text for toolbar
DELETE = _("Delete Selected")
RAZOR = _("Cut clip at mouse position")
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
                <menuitem action="Razor" />
                <separator />
                <menuitem action="DeleteObj" />
                <menuitem action="LinkObj" />
                <menuitem action="UnlinkObj" />
                <menuitem action="GroupObj" />
                <menuitem action="UngroupObj" />
            </placeholder>
        </menu>
    </menubar>
    <toolbar name="TimelineToolBar">
        <placeholder name="Timeline">
            <toolitem action="ZoomOut" />
            <toolitem action="ZoomIn" />
            <separator />
            <toolitem action="Razor" />
            <separator />
            <toolitem action="DeleteObj" />
            <toolitem action="UnlinkObj" />
            <toolitem action="LinkObj" />
            <toolitem action="GroupObj" />
            <toolitem action="UngroupObj" />
        </placeholder>
    </toolbar>
    <accelerator action="DeleteObj" />
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

        self.project = None
        self.ui_manager = ui_manager
        self.app = instance
        self._temp_objects = None
        self._factories = None
        self._finish_drag = False
        self._position = 0
        self._createUI()
        self._prev_duration = 0
        self.shrink = True

    def _createUI(self):
        self.leftSizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        self.hadj = gtk.Adjustment()
        self.vadj = gtk.Adjustment()

        # controls for tracks and layers
        self._controls = TimelineControls()
        self._controls.connect('track-expanded',
                self._timelineControlsTrackExpandedCb)
        controlwindow = gtk.ScrolledWindow(None, self.vadj)
        controlwindow.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        controlwindow.add_with_viewport(self._controls)
        self.attach(controlwindow, 0, 1, 1, 2, xoptions=0)

        # timeline ruler
        self.ruler = ruler.ScaleRuler(self.hadj)
        self.ruler.set_size_request(0, 35)
        self.ruler.set_border_width(2)
        self.attach(self.ruler, 1, 2, 0, 1, yoptions=0)

        # proportional timeline
        self._canvas = TimelineCanvas(self.app)
        timelinewindow = gtk.ScrolledWindow(self.hadj, self.vadj)
        timelinewindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        timelinewindow.add(self._canvas)
        #FIXME: remove padding between scrollbar and scrolled window
        self.attach(timelinewindow, 1, 2, 1, 2)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_MOTION,
            [dnd.FILESOURCE_TUPLE],
            gtk.gdk.ACTION_COPY)

        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.connect("drag-leave", self._dragLeaveCb)
        self.connect("drag-drop", self._dragDropCb)
        self.connect("drag-motion", self._dragMotionCb)

        # toolbar actions
        actions = (
            ("ZoomIn", gtk.STOCK_ZOOM_IN, None, None, ZOOM_IN,
                self._zoomInCb),
            ("ZoomOut", gtk.STOCK_ZOOM_OUT, None, None, ZOOM_OUT,
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

        toggle_actions = (
            ("Razor", "pitivi-split", _("Razor"), "<Ctrl>R", RAZOR,
                self.toggleRazor),
        )

        actiongroup = gtk.ActionGroup("timelinepermanent")
        actiongroup.add_actions(actions)
        actiongroup.add_toggle_actions(toggle_actions)
        self.ui_manager.insert_action_group(actiongroup, 0)

        actiongroup = gtk.ActionGroup("timelineselection")
        actiongroup.add_actions(selection_actions)
        self.link_action = actiongroup.get_action("LinkObj")
        self.unlink_action = actiongroup.get_action("UnlinkObj")
        self.delete_action = actiongroup.get_action("DeleteObj")

        self.ui_manager.insert_action_group(actiongroup)

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

    def _timelineControlsTrackExpandedCb(self, timeline_controls,
            track, expanded):
        self._canvas.setExpanded(track, expanded)


## Event callbacks

    def _buttonPress(self, window, event):
        self.shrink = False

    def _buttonRelease(self, window, event):
        self.shrink = True
        self._timelineStartDurationChanged(self.timeline,
            self.timeline.duration)

## Drag and Drop callbacks

    def _dragMotionCb(self, unused, context, x, y, timestamp):
        if not self._factories:
            atom = gtk.gdk.atom_intern(dnd.FILESOURCE_TUPLE[0])
            self.drag_get_data(context, atom, timestamp)
            self.drag_highlight()
        else:
            if not self._temp_objects:
                self._add_temp_source()
            self._move_temp_source(x, y)
        return True

    def _dragLeaveCb(self, unused_layout, unused_context, unused_tstamp):
        if self._temp_objects:
            try:
                for obj in self._temp_objects:
                    self.timeline.removeTimelineObject(obj, deep=True)
            finally:
                self._temp_objects = None
        self.drag_unhighlight()

    def _dragDropCb(self, widget, context, x, y, timestamp):
        self._add_temp_source()
        self._move_temp_source(x, y)
        context.drop_finish(True, timestamp)
        self._factories = None
        self._temp_objects = None
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
        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uris = selection.data.split("\n")
        else:
            context.finish(False, False, timestamp)
        self._factories = [self.project.sources[uri] for uri in uris]
        context.drag_status(gtk.gdk.ACTION_COPY, timestamp)
        return True

    def _add_temp_source(self):
        self._temp_objects = [self.timeline.addSourceFactory(factory)
            for factory in self._factories]

    def _move_temp_source(self, x, y):
        x1, y1, x2, y2 = self._controls.get_allocation()
        offset = 10 + (x2 - x1)
        x, y = self._canvas.convert_from_pixels(x - offset, y)
        delta = Zoomable.pixelToNs(x)
        for obj in self._temp_objects:
            obj.setStart(max(0, delta), snap=True)
            delta += obj.duration


## Zooming and Scrolling

    def zoomChanged(self):
        # this has to be in a timeout, because the resize hasn't actually
        # completed yet, and so the canvas can't actually complete the scroll
        gobject.idle_add(self.scrollToPlayhead)

    def timelinePositionChanged(self, position):
        self._position = position
        self.ruler.timelinePositionChanged(position)
        self._canvas._position = position
        self.scrollToPlayhead()

    def scrollToPlayhead(self):
        width = self.get_allocation().width
        new_pos = Zoomable.nsToPixel(self._position)
        scroll_pos = self.hadj.get_value()
        if (new_pos < scroll_pos) or (new_pos > scroll_pos + width):
            self.scrollToPosition(new_pos - width / 2)
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

## Project callbacks

    def _setProject(self):
        if self.project:
            self.timeline = self.project.timeline
            self._controls.timeline = self.timeline
            self._canvas.timeline = self.timeline
            self._canvas.zoomChanged()
            self.ruler.zoomChanged()

    project = receiver(_setProject)

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
            self.ruler.setMaxDuration(duration)
            self._canvas.setMaxDuration(duration)
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
        if timeline.selection:
            delete = True
            if len(timeline.selection) > 1:
                link = True
            for obj in self.timeline.selection:
                if obj.link:
                    unlink = True
                    break
        self.delete_action.set_sensitive(delete)
        self.link_action.set_sensitive(link)
        self.unlink_action.set_sensitive(unlink)

## ToolBar callbacks

    def hide(self):
        self.actiongroup.set_visible(False)
        gtk.Vbox.hide(self)

    def _computeZoomRatio(self, index):
        return self.zoom_levels[index]

    def _zoomInCb(self, unused_action):
        Zoomable.zoomIn()

    def _zoomOutCb(self, unused_action):
        Zoomable.zoomOut()

    def deleteSelected(self, unused_action):
        if self.timeline:
            self.timeline.deleteSelection()

    def unlinkSelected(self, unused_action):
        if self.timeline:
            self.timeline.unlinkSelection()

    def linkSelected(self, unused_action):
        if self.timeline:
            self.timeline.linkSelection()

    def ungroupSelected(self, unused_action):
        if self.timeline:
            self.timeline.ungroupSelection()

    def groupSelected(self, unused_action):
        if self.timeline:
            self.timeline.groupSelection()

    def toggleRazor(self, action):
        if action.props.active:
            self._canvas.activateRazor(action)
        else:
            self._canvas.deactivateRazor()
