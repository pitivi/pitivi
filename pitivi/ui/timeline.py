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
from pitivi.timeline import objects
import ruler
from complexinterface import Zoomable
import dnd

from gettext import gettext as _
from timelinecanvas import TimelineCanvas
from pitivi.receiver import receiver, handler

# tooltip text for toolbar
DELETE = _("Delete Selected")
RAZOR = _("Cut clip at mouse position")
ZOOM_IN =  _("Zoom In")
ZOOM_OUT =  _("Zoom Out")
UNLINK = _("Unlink audio from video")
RELINK = _("Relink audio to original video")
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
        <toolitem action="UnlinkObj" />
        <toolitem action="RelinkObj" />
    </toolbar>
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
#

class Timeline(gtk.VBox):

    # the screen width of the current unit
    unit_width = 10 
    # specific levels of zoom, in (multiplier, unit) pairs which 
    # from zoomed out to zoomed in
    zoom_levels = (1, 5, 10, 20, 50, 100, 150) 

    def __init__(self):
        gst.log("Creating Timeline")
        gtk.VBox.__init__(self)

        self._zoom_adj = gtk.Adjustment()
        self._zoom_adj.lower = self._computeZoomRatio(0)
        self._zoom_adj.upper = self._computeZoomRatio(-1)
        self._cur_zoom = 2
        self._zoom_adj.set_value(self._computeZoomRatio(self._cur_zoom))

        self.timeline = instance.PiTiVi.current.timeline
        self.instance = instance.PiTiVi
        self.playground = instance.PiTiVi.playground
        self._createUI()

    def _createUI(self):
        self.leftSizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        self.hadj = gtk.Adjustment()
        self.ruler = ruler.ScaleRuler(self.hadj)
        self.ruler.setZoomAdjustment(self._zoom_adj)
        self.ruler.set_size_request(0, 35)
        self.ruler.set_border_width(2)
        self.pack_start(self.ruler, expand=False, fill=True)

        # List of TimelineCanvas
        self.__canvas = TimelineCanvas(self.timeline)
        self.__canvas.setZoomAdjustment(self._zoom_adj)

        self.scrolledWindow = gtk.ScrolledWindow(self.hadj)
        self.scrolledWindow.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_AUTOMATIC)
        self.scrolledWindow.add(self.__canvas)
        #FIXME: remove padding between scrollbar and scrolled window
        self.pack_start(self.scrolledWindow, expand=True)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION, 
            [dnd.FILESOURCE_TUPLE],
            gtk.gdk.ACTION_COPY)
        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.connect("drag-leave", self._dragLeaveCb)
        self.connect("drag-motion", self._dragMotionCb)

        # toolbar actions
        actions = (
            ("ZoomIn", gtk.STOCK_ZOOM_IN, None, None, ZOOM_IN,
                self._zoomInCb),
            ("ZoomOut", gtk.STOCK_ZOOM_OUT, None, None, ZOOM_OUT, 
                self._zoomOutCb),
            ("DeleteObj", gtk.STOCK_DELETE, None, None, DELETE, 
                self.deleteSelected),
            ("UnlinkObj", gtk.STOCK_DISCONNECT, None, None, UNLINK,
                self.unlinkSelected),
            ("RelinkObj", gtk.STOCK_CONNECT, None, None, RELINK,
                self.relinkSelected),
            ("Razor", gtk.STOCK_CUT, None, None, RAZOR,
                self.__canvas.activateRazor)
        )
        self.actiongroup = gtk.ActionGroup("complextimeline")
        self.actiongroup.add_actions(actions)
        #self.actiongroup.set_visible(False)
        uiman = instance.PiTiVi.gui.uimanager
        uiman.insert_action_group(self.actiongroup, 0)
        uiman.add_ui_from_string(ui)

## Drag and Drop callbacks

    def _dragMotionCb(self, unused_layout, unused_context, x, y, timestamp):

        # FIXME: temporarily add source to timeline, and put it in drag mode
        # so user can see where it will go
        gst.info("SimpleTimeline x:%d , source would go at %d" % (x, 0))

    def _dragLeaveCb(self, unused_layout, unused_context, unused_tstamp):
        gst.info("SimpleTimeline")
        #TODO: remove temp source from timeline

    def _dragDataReceivedCb(self, unused_layout, context, x, y, 
        selection, targetType, timestamp):
        gst.log("SimpleTimeline, targetType:%d, selection.data:%s" % 
            (targetType, selection.data))
        # FIXME: need to handle other types
        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, timestamp)
        # FIXME: access of instance, and playground
        factory = instance.PiTiVi.current.sources[uri]
        instance.PiTiVi.current.timeline.addFactory(factory)
        context.finish(True, False, timestamp)
        instance.PiTiVi.playground.switchToTimeline()

## Instance callbacks

    instance = receiver()

    @handler(instance, "new-project-loading")
    def _newProjectLoadingCb(self, unused_inst, project):
        self.timeline = project.timeline
        self.__canvas.timeline = self.timeline

    @handler(instance, "new-project-loaded")
    def _newProjectLoadedCb(self, unused_inst, unused_project):
        # force set deadband when new timeline loads
        self.__canvas.zoomChanged()

    @handler(instance, "new-project-failed")
    def _newProjectFailedCb(self, unused_inst, unused_reason, unused_uri):
        self.timeline = None
        self.__canvas.timeline = None

## Timeline callbacks

    timeline = receiver()

    @handler(timeline, "start-duration-changed")
    def _timelineStartDurationChanged(self, unused_timeline, start, duration):
        self.ruler.startDurationChanged()

## ToolBar callbacks

    ## override show()/hide() methods to take care of actions
    def show(self):
        gtk.VBox.show(self)
        self.actiongroup.set_visible(True)

    def show_all(self):
        gtk.VBox.show_all(self)
        self.actiongroup.set_visible(True)

    def hide(self):
        self.actiongroup.set_visible(False)
        gtk.Vbox.hide(self)

    def _computeZoomRatio(self, index):
        return self.zoom_levels[index]

    def _zoomInCb(self, unused_action):
        self._cur_zoom = min(len(self.zoom_levels) - 1, self._cur_zoom + 1)
        self._zoom_adj.set_value(self._computeZoomRatio(self._cur_zoom))

    def _zoomOutCb(self, unused_action):
        self._cur_zoom = max(0, self._cur_zoom - 1)
        self._zoom_adj.set_value(self._computeZoomRatio(self._cur_zoom))

    def deleteSelected(self, unused_action):
        instance.PiTiVi.current.timeline.deleteSelection()

    def unlinkSelected(self, unused_action):
        instance.PiTiVi.current.timeline.unlinkSelection()

    def relinkSelected(self, unused_action):
        instance.PiTiVi.current.timeline.relinkSelection()

## PlayGround timeline position callback

    playground = receiver()

    @handler(playground, "position")
    def _positionCb(self, unused_playground, smartbin, value):
        if isinstance(smartbin, SmartTimelineBin):
            # for the time being we only inform the ruler
            self.ruler.timelinePositionChanged(value, 0)
