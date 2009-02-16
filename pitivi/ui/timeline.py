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
import gst

from pitivi.bin import SmartTimelineBin
from pitivi.timeline.source import TimelineFileSource
from pitivi.timeline import objects
import ruler
import dnd

from gettext import gettext as _
from timelinecanvas import TimelineCanvas
from pitivi.receiver import receiver, handler
from zoominterface import Zoomable

# tooltip text for toolbar
DELETE = _("Delete Selected")
RAZOR = _("Cut clip at mouse position")
ZOOM_IN =  _("Zoom In")
ZOOM_OUT =  _("Zoom Out")
UNLINK = _("Break links between clips")
LINK = _("Link together arbitrary clips")
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
        <toolitem action="LinkObj" />
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
#

class Timeline(gtk.VBox):

    # the screen width of the current unit
    unit_width = 10 
    # specific levels of zoom, in (multiplier, unit) pairs which 
    # from zoomed out to zoomed in


    def __init__(self, project, ui_manager):
        gst.log("Creating Timeline")
        gtk.VBox.__init__(self)

        self.project = project
        self.timeline = project.timeline
        self.ui_manager = ui_manager

        self._createUI()

    def _createUI(self):
        self.leftSizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        self.hadj = gtk.Adjustment()
        self.ruler = ruler.ScaleRuler(self.hadj)
        self.ruler.set_size_request(0, 35)
        self.ruler.set_border_width(2)
        self.pack_start(self.ruler, expand=False, fill=True)

        # List of TimelineCanvas
        self.__canvas = TimelineCanvas(self.timeline)

        self.scrolledWindow = gtk.ScrolledWindow(self.hadj)
        self.scrolledWindow.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_AUTOMATIC)
        self.scrolledWindow.add(self.__canvas)
        #FIXME: remove padding between scrollbar and scrolled window
        self.pack_start(self.scrolledWindow, expand=True)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION, 
            [dnd.FILESOURCE_TUPLE],
            gtk.gdk.ACTION_COPY)

        # toolbar actions
        actions = (
            ("ZoomIn", gtk.STOCK_ZOOM_IN, None, None, ZOOM_IN,
                self._zoomInCb),
            ("ZoomOut", gtk.STOCK_ZOOM_OUT, None, None, ZOOM_OUT, 
                self._zoomOutCb),
            ("DeleteObj", gtk.STOCK_DELETE, None, "Delete", DELETE, 
                self.deleteSelected),
            ("UnlinkObj", "pitivi-unlink", None, None, UNLINK,
                self.unlinkSelected),
            ("LinkObj", "pitivi-link", None, None, LINK,
                self.linkSelected),
        )
        razor = gtk.ToggleAction("Razor", None, RAZOR, "pitivi-split")
        razor.connect("toggled", self.toggleRazor)
        self.actiongroup = gtk.ActionGroup("complextimeline")
        self.actiongroup.add_actions(actions)
        self.actiongroup.add_action(razor)
        #self.actiongroup.set_visible(False)
        self.ui_manager.insert_action_group(self.actiongroup, 0)
        self.ui_manager.add_ui_from_string(ui)

    def setTimeline(self, timeline):
        self.timeline = timeline
        self.__canvas.timeline = self.timeline
        self.__canvas.zoomChanged()

## Timeline callbacks

    timeline = receiver()

    @handler(timeline, "duration-changed")
    def _timelineStartDurationChanged(self, unused_timeline, duration):
        self.ruler.setDuration(duration)

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

    def toggleRazor(self, action):
        if action.props.active:
            self.__canvas.activateRazor(action)
        else:
            self.__canvas.deactivateRazor()

