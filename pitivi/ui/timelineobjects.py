# PiTiVi , Non-linear video editor
#
#       pitivi/ui/timelineobjects.py
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
Simple view timeline widgets
"""

import os.path
from urllib import unquote
import gobject
import gtk
import gst
import pango
import pitivi.instance as instance
from pitivi.timeline.source import TimelineFileSource, TimelineSource, TimelineBlankSource
from pitivi.timeline.effects import TimelineTransition
from pitivi.timeline.objects import MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
from pitivi.configure import get_pixmap_dir
import pitivi.dnd as dnd
from pitivi.bin import SmartFileBin
from pitivi.signalgroup import SignalGroup
from pitivi.thumbnailer import Thumbnailer
from pitivi.ui.slider import PipelineSlider
from sourcefactories import beautify_length
from gettext import gettext as _

import goocanvas
from util import *
from pitivi.utils import time_to_string

# Default width / height ratio for simple elements
DEFAULT_SIMPLE_SIZE_RATIO = 1.50 # default height / width ratio

# Default simple elements size
DEFAULT_SIMPLE_ELEMENT_WIDTH = 100
DEFAULT_SIMPLE_ELEMENT_HEIGHT = DEFAULT_SIMPLE_ELEMENT_WIDTH * DEFAULT_SIMPLE_SIZE_RATIO

# Default spacing between/above elements in simple timeline
DEFAULT_SIMPLE_SPACING = 10

# Simple Timeline's default values
DEFAULT_HEIGHT = DEFAULT_SIMPLE_ELEMENT_HEIGHT + 2 * DEFAULT_SIMPLE_SPACING
DEFAULT_WIDTH = 3 * DEFAULT_SIMPLE_SPACING # borders (2) + one holding place
MINIMUM_HEIGHT = DEFAULT_HEIGHT
MINIMUM_WIDTH = 3 * MINIMUM_HEIGHT

class SimpleTimelineWidget(gtk.HBox):
    """Contains the editing widget as well as a gtk.ScrolledWindow containing
    the simple timeline canvas. Handles showing/hiding the editing widget and
    canvas."""

    __gtype_name__ = 'SimpleTimelineWidget'

    def __init__(self, *args, **kwargs):
        gtk.HBox.__init__(self, *args, **kwargs)
        timeline = SimpleTimelineCanvas()
        timeline.connect("edit-me", self._editMeCb)

        self.content = gtk.ScrolledWindow()
        self.content.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_NEVER)
        self.content.add(timeline)
        #add other objects here
        self.add(self.content)

        # edit-mode
        # True when in editing mode
        self._editingMode = False
        self.editingWidget = SimpleEditingWidget()
        self.editingWidget.connect("hide-me", self._editingWidgetHideMeCb)

        instance.PiTiVi.connect("project-closed", self._projectClosedCb)
        instance.PiTiVi.connect("new-project-failed",
            self._newProjectFailedCb)

    def _editMeCb(self, unused_timeline, element):
        self._switchEditingMode(element)

    def _editingWidgetHideMeCb(self, unused_widget):
        self.switchToNormalMode()
        # switch back to timeline in playground !
        instance.PiTiVi.playground.switchToTimeline()

    def _newProjectFailedCb(self, unused_inst, unused_reason, unused_uri):
        self.switchToNormalMode()

    def _projectClosedCb(self, unused_pitivi, unused_project):
        self.switchToNormalMode()

    def _switchEditingMode(self, source, mode=True):
        """ Switch editing mode for the given TimelineSource """
        gst.log("source:%s , mode:%s" % (source, mode))

        if self._editingMode == mode:
            gst.warning("We were already in correct editing mode : %s" % 
                mode)
            return

        if mode and not source:
            gst.warning("You need to specify a valid TimelineSource")
            return

        if mode:
            # switching TO editing mode
            gst.log("Switching TO editing mode")

            # 1. Hide all sources
            self.remove(self.content)
            self.content.hide()
            self._editingMode = mode

            # 2. Show editing widget
            self.editingWidget.setSource(source)
            self.add(self.editingWidget)
            self.editingWidget.show_all()

        else:
            gst.log("Switching back to normal mode")
            # switching FROM editing mode

            # 1. Hide editing widget
            self.remove(self.editingWidget)
            self.editingWidget.hide()
            self._editingMode = mode

            # 2. Show all sources
            self.add(self.content)
            self.content.show_all()

    def switchToEditingMode(self, source):
        """ Switch to Editing mode for the given TimelineSource """
        self._switchEditingMode(source)

    def switchToNormalMode(self):
        """ Switch back to normal timeline mode """
        self._switchEditingMode(None, False)


class TimelineList(HList):
    """A dynamically re-orderable group of items which knows about pitivi
    timeline objects. Connects only to the video composition of the
    timeline"""
    __gtype_name__ = 'TimelineList'

    __gsignals__ = {
        'edit-me' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,))
        }

    def __init__(self, timeline, *args, **kwargs):
        HList.__init__(self, *args, **kwargs)
        self.sig_ids = None
        self.timeline = None
        self.set_timeline(timeline)
        self.reorderable = True
        self.widgets = {}
        self.elements = {}

    def set_timeline(self, timeline):
        self.remove_all()
        if self.timeline:
            for sig in self.sig_ids:
                self.timeline.videocomp.disconnect(sig)
            self.sig_ids = None
        self.timeline = timeline
        if timeline:
            #TODO: connect transition callbacks here
            changed = timeline.videocomp.connect("condensed-list-changed", 
                self._condensedListChangedCb)
            added = timeline.videocomp.connect("source-added",
                self._sourceAddedCb)
            removed = timeline.videocomp.connect("source-removed",
                self._sourceRemovedCb)
            self.sig_ids = (changed, added, removed)
            self._condensedListChangedCb(None, timeline.videocomp.condensed)

    # overriding from parent
    def swap(self, a, b):
        #TODO: make this code handle transitions.
        element_a = self.elements[a]
        element_b = self.elements[b]
        index_a = self.index(a)
        index_b = self.index(b)

        #FIXME: are both of these calls necessary? or do we just need to be
        # smarter about figuring which source to move in front of the other.
        # in any case, it seems to work.
        self.timeline.videocomp.moveSource(element_a, index_b, True, True)
        self.timeline.videocomp.moveSource(element_b, index_a, True, True)

    def _condensedListChangedCb(self, unused_videocomp, clist):
        """ add/remove the widgets """
        gst.debug("condensed list changed in videocomp")
        order = [self.index(self.widgets[e]) for e in clist]
        self.reorder(order)

    def _sourceAddedCb(self, timeline, element):
        gst.debug("Adding new element to the layout")
        if isinstance(element, TimelineFileSource):
            widget = SimpleSourceWidget(element)
            widget.connect("delete-me", self._sourceDeleteMeCb, element)
            widget.connect("edit-me", self._sourceEditMeCb, element)
            item = goocanvas.Widget(widget=widget)
            item.props.width = DEFAULT_SIMPLE_ELEMENT_WIDTH
            item.props.height = DEFAULT_SIMPLE_ELEMENT_HEIGHT
            background = goocanvas.Rect(fill_color="gray",
                stroke_color="gray",
                width=DEFAULT_SIMPLE_ELEMENT_WIDTH,
                height=DEFAULT_SIMPLE_ELEMENT_HEIGHT)
            item = group(background, item)
        else:
            #TODO: implement this
            raise Exception("Not Implemented")
        self.widgets[element] = item
        self.elements[item] = element
        self.add_child(self.widgets[element])

    def _sourceRemovedCb(self, timeline, element):
        gst.debug("Removing element")
        self.remove_child(self.widgets[element])
        del self.elements[self.widgets[element]]
        del self.widgets[element]

    def remove_all(self):
        HList.remove_all(self)
        self.elements = {}
        self.widgets = {}

## Child callbacks

    def _sourceDeleteMeCb(self, unused_widget, element):
        # remove this element from the timeline
        self.timeline.videocomp.removeSource(element, 
            collapse_neighbours=True)
#
    def _sourceEditMeCb(self, unused_widget, element):
        self.emit("edit-me", element)

class SimpleTimelineCanvas(goocanvas.Canvas):
    """goocanvas.Canvas derivative which contains all the widgets used in the
    simple timeline that should be scrolled together. It handles application event
    like loading/saving, and external drag-and-drop events for adding objects 
    to the canvas"""

    __gtype_name__ = 'SimpleTimeline'

    __gsignals__ = {
        'edit-me' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,))
        }


    def __init__(self, *args, **kwargs):
        goocanvas.Canvas.__init__(self, *args, **kwargs)
        self.props.automatic_bounds = False

        # timeline and top level compositions
        self.timeline = instance.PiTiVi.current.timeline

        self.root = self.get_root_item()
        self.items = TimelineList(self.timeline, self, spacing=10)
        self.root.add_child(self.items)
        self.items.connect("edit-me", self._editMeCb)

        self.left = None
        self.l_thresh = None
        self.right = None
        self.r_thresh = None
        self.initial = None


        self.scale = 1.0
        self.set_size_request(int(MINIMUM_WIDTH), int(MINIMUM_HEIGHT))

        instance.PiTiVi.connect("new-project-loaded",
            self._newProjectLoadedCb)
        instance.PiTiVi.connect("project-closed", self._projectClosedCb)
        instance.PiTiVi.connect("new-project-loading",
            self._newProjectLoadingCb)
        instance.PiTiVi.connect("new-project-failed",
            self._newProjectFailedCb)

        # set a reasonable minimum size which will avoid grahics glitch
        self.set_bounds(0, 0, DEFAULT_SIMPLE_ELEMENT_WIDTH,
            DEFAULT_SIMPLE_ELEMENT_HEIGHT)

    def _request_size(self, item, prop):
        # no need to set size, just set the bounds
        self.set_bounds(0, 0, self.items.width, self.items.height)
        return True

    def _size_allocate(self, unused_layout, allocation):
        x1, y1, x2, y2 = self.get_bounds()
        height = y2 - y1

        if height > 0:
            self.scale = allocation.height / height
            self.set_scale(self.scale)
        return True

## Project callbacks

    def _newProjectLoadingCb(self, unused_inst, project):
        #now we connect to the new project, so we can receive any
        self.items.set_timeline(project.timeline)

    def _newProjectLoadedCb(self, unused_inst, project):
        assert(instance.PiTiVi.current == project)

    def _newProjectFailedCb(self, unused_inst, unused_reason, unused_uri):
        self.items.set_timeline(None)

    def _projectClosedCb(self, unused_pitivi, unused_project):
        self.items.set_timeline(None)

## Editing mode

    def _editMeCb(self, timeline, element):
        self.emit("edit-me", element)

class SimpleEditingWidget(gtk.EventBox):
    """
    Widget for editing a source in the SimpleTimeline
    """

    __gsignals__ = {
        "hide-me" : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     ( ))
        }

    def __init__(self):
        gtk.EventBox.__init__(self)

        #default pixbuf for when source pixbuf is unavailable
        pixpath = os.path.join(get_pixmap_dir(), "pitivi-video.png")
        self.default_pixbuf = gtk.gdk.pixbuf_new_from_file(pixpath)

        self._createUi()

        #signals
        self.add_events(gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.BUTTON_PRESS_MASK)
        self.connect("realize", self._realizeCb)
        self.connect("expose-event", self._exposeEventCb)
        self.connect("button-press-event", self._buttonPressEventCb)
        self._source = None
        self._curPosition = 0

        # true if we need to switch the playground source to editing pipeline
        self._switchSource = False
        self._movingSlider = False
        self._pipeline = None
        self._mediaStartDurationChangedSigId = None
        self._playgroundPositionSigId = None

        #popup menu
        self._popupMenu = gtk.Menu()
        closeitem = gtk.MenuItem(_("Close"))
        closeitem.connect("activate", self._closeMenuItemCb)
        closeitem.show()

        self._popupMenu.append(closeitem)

        self._thumbnailer = None
        self._thumbnailerSigId = None

        #value to remember
        self._start = 0
        self._duration = 0
        self._mediaStart = 0
        self._mediaDuration = 0

    def _createUi(self):
        #layout
        layout = gtk.VBox()
        self.add(layout)
        top = gtk.HBox()
        layout.pack_start(top)

        #done and cancel buttons
        self.doneButton = gtk.Button(_("Done"))
        self.doneButton.connect("clicked", self._closeMenuItemCb)
        self.cancelButton = gtk.Button(_("Cancel"), gtk.STOCK_CANCEL)
        self.cancelButton.connect("clicked", self._closeMenuItemCb)
        done_box = gtk.HBox()
        done_box.pack_end(self.doneButton, False, False)
        done_box.pack_end(self.cancelButton, False, False)
        layout.pack_end(done_box, False, False)

        #timeline slider
        self.position = PipelineSlider(display_endpoints=True)
        layout.pack_end(self.position, False, False)

        #start point control widgets
        self.startPos = gtk.Label(time_to_string(0))
        self.startThumb = ScaledThumbnailViewer(self.default_pixbuf)
        self.startAdvanceButton = gtk.ToolButton(gtk.STOCK_MEDIA_FORWARD)
        self.startAdvanceButton.connect("clicked", self._startTrimButtonClickedCb)
        self.startRewindButton = gtk.ToolButton(gtk.STOCK_MEDIA_REWIND)
        self.startRewindButton.connect("clicked", self._startTrimButtonClickedCb)
        self.startSeekButton = gtk.Button(_("Start"))
        self.startSeekButton.connect("clicked", self._startSeekButtonClickedCb)
        self.startTrimButton = gtk.Button(_("Trim"))
        self.startTrimButton.connect("clicked", self._startTrimButtonClickedCb)

        start_btns = gtk.HBox()
        start_btns.pack_start(self.startRewindButton, False, False)
        start_btns.pack_start(self.startAdvanceButton, False, False)
        start_btns.pack_end(self.startTrimButton, False, False)
        start_btns.pack_end(self.startSeekButton, False, False)
        start_group = gtk.VBox()
        start_group.pack_start(self.startPos, False, False)
        start_group.pack_start(self.startThumb)
        start_group.pack_start(start_btns, False, False)
        top.pack_start(start_group)

        #source position label
        self.curPos = gtk.Label(time_to_string(0))
        top.pack_start(self.curPos)

        #end point control widgets
        self.endPos = gtk.Label(time_to_string(0))
        self.endThumb = ScaledThumbnailViewer(self.default_pixbuf)
        self.endAdvanceButton = gtk.ToolButton(gtk.STOCK_MEDIA_FORWARD)
        self.endAdvanceButton.connect("clicked", self._endTrimButtonClickedCb)
        self.endRewindButton = gtk.ToolButton(gtk.STOCK_MEDIA_REWIND)
        self.endRewindButton.connect("clicked", self._endTrimButtonClickedCb)
        self.endSeekButton = gtk.Button(_("End"))
        self.endSeekButton.connect("clicked", self._endSeekButtonClickedCb)
        self.endTrimButton = gtk.Button(_("Trim"))
        self.endTrimButton.connect("clicked", self._endTrimButtonClickedCb)
        end_btns = gtk.HBox()
        end_btns.pack_start(self.endTrimButton, False, False)
        end_btns.pack_start(self.endSeekButton, False, False)
        end_btns.pack_end(self.endAdvanceButton, False, False)
        end_btns.pack_end(self.endRewindButton, False, False)
        end_group = gtk.VBox()
        end_group.pack_start(self.endPos, False, False)
        end_group.pack_start(self.endThumb)
        end_group.pack_start(end_btns, False, False)
        top.pack_start(end_group)

        self.show_all()

    def setSource(self, source):
        gst.log("source:%s" % source)
        gst.log("start:%s / duration:%s / media-start:%s / media-duration:%s" %
                (gst.TIME_ARGS(source.start),
                 gst.TIME_ARGS(source.duration),
                 gst.TIME_ARGS(source.media_start),
                 gst.TIME_ARGS(source.media_duration)))
        #TODO: disable triming of start point for non-seekable sources
        # disable viewing of start point for non-seekable sources

        # register media update callback
        #self._mediaStartDurationChangedSigId = source.connect(
        #        "media-start-duration-changed",
        #        self._mediaStartDurationChangedCb)
        self._source = source

        # remember initial values
        self._start = source.start
        self._duration = source.duration
        self._mediaStart = source.media_start
        self._mediaDuration = source.media_duration

        ## connect to playground position change
        sid = instance.PiTiVi.playground.connect("position",
            self._playgroundPositionCb)
        self._playgroundPositionSigId = sid

        # set viewer source
        self._pipeline = SmartFileBin(source.factory)
        if self._pipeline == None:
            gst.warning("did not get editing pipeline")
        instance.PiTiVi.playground.pause()
        instance.PiTiVi.playground.addPipeline(self._pipeline)

        #Set slider min, max, and current
        self.position.setPipeline(self._pipeline)
        self.position.setStartDuration(self._mediaStart, self._mediaDuration)
        self.position.set_value(self._mediaStart)
        self.startPos.props.label = time_to_string(self._source.media_start)
        self.endPos.props.label = time_to_string(self._source.media_start +
            self._source.media_duration)

        # create thumbnailer
        self._thumbnailer = Thumbnailer(uri=source.factory.name)
        self._thumbnailerSigId = self._thumbnailer.connect('thumbnail', 
            self._newThumbnailCb)
        self._updateThumbnails()
        self._adjustControls()

    def _newThumbnailCb(self, thumbnailer, pixbuf, timestamp):
        gst.log("pixbuf:%s, timestamp:%s" % (pixbuf, gst.TIME_ARGS(timestamp)))
        # figure out if that thumbnail is for media_start or media_stop
        if timestamp == self._mediaStart:
            gst.log("pixbuf is for media_start")
            self.startThumb.setPixbuf(pixbuf)
        elif timestamp == self._mediaDuration + self._mediaStart:
            gst.log("pixbuf is for media_stop")
            self.endThumb.setPixbuf(pixbuf)
        else:
            gst.warning("got pixbuf for a non-handled timestamp")

    def _updateTextFields(self, start=gst.CLOCK_TIME_NONE, duration=0):
        if not start == gst.CLOCK_TIME_NONE:
            self.startPos.props.label = time_to_string(start)
        if not start == gst.CLOCK_TIME_NONE and not duration == 0:
            self.endPos.props.label = time_to_string(start + duration)

    def _updateThumbnails(self):
        self._thumbnailer.makeThumbnail(self._mediaStart)
        self._thumbnailer.makeThumbnail(self._mediaDuration + self._mediaStart)

    def _playgroundPositionCb(self, playground, bin, position):
        self.curPos.props.label = time_to_string(position)
        self._curPosition = position
        if position >= self._mediaStart + self._mediaDuration:
            self.startTrimButton.set_sensitive(False)
        else:
            self.startTrimButton.set_sensitive(True)

        if position <= self._mediaStart:
            self.endTrimButton.set_sensitive(False)
        else:
            self.endTrimButton.set_sensitive(True)

    def _startTrimButtonClickedCb(self, widget):
        gst.log("current position %s"
            % gst.TIME_ARGS(self._curPosition))
        if widget == self.startTrimButton:
            # set media_start at the current position
            start = self._curPosition
            # adjust media_duration accordingly
            duration = self._mediaDuration + self._mediaStart - start
        elif widget == self.startAdvanceButton:
            #FIXME: use a better value for advance/rewind
            gst.log("start frame advance")
            start = self._mediaStart + gst.SECOND
            duration = self._mediaDuration - gst.SECOND
        elif widget == self.startRewindButton:
            gst.log("start frame rewind")
            start = self._mediaStart - gst.SECOND
            duration = self._mediaDuration + gst.SECOND

        start = max(0, start)

        self._mediaStart = start
        self._mediaDuration = duration
        self._duration = duration
        self._updateStartDuration()
        
    def _endTrimButtonClickedCb(self, widget):
        gst.log("current position %s" %
            gst.TIME_ARGS(self._curPosition))
        start = self._curPosition
        if widget == self.endTrimButton:
            # set media_duration at currentposition - media_start
            duration = self._curPosition - self._mediaStart 
        elif widget == self.endAdvanceButton:
            gst.log("end frame advance")
            duration = self._mediaDuration + gst.SECOND
        elif widget == self.endRewindButton:
            gst.log("end frame rewind")
            duration = self._mediaDuration - gst.SECOND

        duration_max = self._source.factory.getDuration() - self._mediaStart
        duration = min(duration, duration_max)

        self._mediaDuration = duration
        self._duration = duration
        self._updateStartDuration()

    def _startSeekButtonClickedCb(self, unused_widget):
        gst.log(" in startSeekButtonClickedCb")
        # HELP : I'm assuming this button is to jump to the start trim point
        instance.PiTiVi.playground.seekInCurrent(self._mediaStart,
            gst.FORMAT_TIME)

    def _endSeekButtonClickedCb(self, unused_widget):
        gst.log(" in startSeekButtonClickedCb")
        # HELP : I'm assuming this button is to jump to the stop trim point
        instance.PiTiVi.playground.seekInCurrent(self._mediaStart +
            self._mediaDuration, gst.FORMAT_TIME)

    def _updateStartDuration(self):
        self._updateThumbnails()
        self._updateTextFields(self._mediaStart, self._mediaDuration)
        self._adjustControls()
        self.position.setStartDuration(self._mediaStart, self._mediaDuration)

    def _adjustControls(self):
        #FIXME: this code assumes the trimming arrows always seek
        # by one second

        if self._mediaStart == 0:
            self.startRewindButton.set_sensitive(False)
        else:
            self.startRewindButton.set_sensitive(True)

        end = self._mediaDuration + self._mediaStart
        assert end <= self._source.factory.getDuration()

        if (self._mediaStart + gst.SECOND) >= end:
            self.startAdvanceButton.set_sensitive(False)
        else:
            self.startAdvanceButton.set_sensitive(True)

        if (end - gst.SECOND) <= self._mediaStart:
            self.endRewindButton.set_sensitive(False)
        else:
            self.endRewindButton.set_sensitive(True)

        if end >= self._source.factory.getDuration():
            self.endAdvanceButton.set_sensitive(False)
        else:
            self.endAdvanceButton.set_sensitive(True)


    def _realizeCb(self, unused_widget):
        self.gc = self.window.new_gc()
        self.gc.set_background(self.style.black)

    def _exposeEventCb(self, unused_widget, event):
        x, y, w, h = event.area

    def _closeMenuItemCb(self, widget):
        # FIXME : reset everything here

        # disconnect signal handler of previous source
        if self._source != None and self._mediaStartDurationChangedSigId:
            self._source.disconnect(self._mediaStartDurationChangedSigId)

        # disconnect playground signals
        if self._playgroundPositionSigId:
            instance.PiTiVi.playground.disconnect(self._playgroundPositionSigId)

        # remove source from playground
        gst.warning("disconnecting source from playground")
        instance.PiTiVi.playground.switchToDefault()
        #FIXME: removeing the pipeline causes error
        #instance.PiTiVi.playground.removePipeline(self._pipeline)
        self._pipeline = None

        # disconnect/delete thumbnailer
        self._thumbnailer.disconnect(self._thumbnailerSigId)
        self._thumbnailer = None
        self._thumbnailerSigId = None

        # reset thumbnails
        self.startThumb.setPixbuf(self.default_pixbuf)
        self.endThumb.setPixbuf(self.default_pixbuf)

        # apply modifications to the object only if user clicked "Done"
        if widget == self.doneButton:
            self._source.setMediaStartDurationTime(self._mediaStart, 
                self._mediaDuration)
            self._source.setStartDurationTime(duration=self._duration)

            # Shift the following sources (Only in simple timeline !)
            # calculate the offset (final duration - initial duration)
            offset = self._source.duration - self._duration
            startpos = instance.PiTiVi.current.timeline.videocomp.\
                getSimpleSourcePosition(self._source)
            instance.PiTiVi.current.timeline.videocomp.shiftSources(offset, 
                startpos)

            self._source = None

        self.emit("hide-me")

    def _buttonPressEventCb(self, unused_widget, event):
        if event.button == 3:
            self._popupMenu.popup(None, None, None, event.button,
                                  event.time)


class ScaledThumbnailViewer(gtk.DrawingArea):
    """
    Widget for viewing a gtk.gdk.pixbuf image at various sizes with
    constant aspect ratio"""

    def __init__(self, pixbuf, interpolation=gtk.gdk.INTERP_NEAREST):
        gobject.GObject.__init__(self)

        # initialization
        self._update = False
        self.gc = None
        self.width = 0
        self.height = 0
        self.pixmap = None
        self.par = gst.Fraction(1,1) # 1/1 PAR

        # get pixbuf aspect ratio
        self.pixbuf = pixbuf

        # There are three rectangles and their associated aspect ratios to
        # consider here: the thumbnail rectangle, the display rectangle, and
        # the scaled rectangle.

        # The first rectangle is defined by the dimensions of the thumbnail
        # itself. As this image is scaled to fit the widget, we don't care
        # about it's size, but rather it's aspect ratio.

        # The second rectangle to consider is the one defined by the size of
        # the widget. I am calling this the display rectangle, and the display
        # aspect ratio. As this is GTK, we have no control over these
        # dimensions.

        # The third rectangle is the area within the display rectangle that
        # the scaled thumbnail will occupy. I am calling this the scaled
        # rectangle. The job of this widget is to maximize the size of the
        # scaled rectangle within the constraints of the display rectangle,
        # while making sure that the scaled aspect ratio and thumbnail
        # aspect ratios match, regardless of the aspect ratio of the display
        # rectangle. This is done by letterboxing or pillarboxing the
        # thumbnail within the display rectangle as necessary.

        # Another rule of thumb is display_aspect_ratio = pixel_aspect_ratio *
        # (display_width / display_height), and displayed_width /
        # displayed_height. Some formats have non-square pixels.

        self.thratio = gst.Fraction(self.pixbuf.get_width(),
                self.pixbuf.get_height())

        #signals
        self.connect("realize", self._realizeCb)
        self.connect("configure-event", self._configureEventCb)
        self.connect("expose-event", self._exposeEventCb)
        self.interpolation=interpolation

    def _drawData(self):
        if self.gc:
            self.pixmap = gtk.gdk.Pixmap(self.window, self.width, self.height)
            self.pixmap.draw_rectangle(self.style.black_gc, True,
                0, 0, self.width, self.height)

            # calculate display aspect ratio. i'm using floats for ease of
            # comparison
            dar = float(self.width) / float(self.height)
            thratio = float(self.thratio.num) / float(self.thratio.denom)

            # invariant: scaled_width/scaled_height = self.thratio

            # the means of calculating the size of the viewing rectangle
            # depends comparing the thumbnail aspect ratio with the display
            # aspect ratio.

            # letterboxing is required if the thumbnail A.R. is wider than the
            # display aspect ratio. In this case the scaled width is assumed
            # to be the display width, and the height is calculated to
            # preserve the aspect ratio.

            # If the widget is wider than the thumbnail, pillarboxing is
            # necessary. In this case the scaled height is assumed to be the
            # display height, and the scaled width is calculated to preserve
            # the thumbnail aspect ratio.

            if thratio > dar:
                scaled_width = self.width
                scaled_height = ((scaled_width * self.thratio.denom *
                        self.par.num) / (self.par.denom * self.thratio.num))

            elif thratio < dar:
                scaled_height = self.height
                scaled_width = ((scaled_height * self.thratio.num *
                            self.par.num) / (self.par.denom *
                                self.thratio.denom))
            else:
                scaled_width = self.width
                scaled_height = self.height

            # bail out if following calculations would result in divide by zero
            # or some other nonsense
            if scaled_width < 1 or scaled_height < 1:
                return

            # we want the image centered in the viewing area
            x = (self.width - scaled_width) / 2
            y = (self.height - scaled_height) / 2

            # create a scaled version of the thumbnail
            subpixbuf = self.pixbuf.scale_simple(scaled_width, scaled_height,
                self.interpolation)

            # draw the thumbnail into the pixmap
            self.pixmap.draw_pixbuf(self.gc, subpixbuf, 0, 0, x, y)

    def _configureEventCb(self, unused_layout, event):
        self.width = event.width
        self.height = event.height
        self._drawData()
        return False

    def _realizeCb(self, unused_widget):
        self.gc = self.window.new_gc()
        self._drawData()
        return False

    def _exposeEventCb(self, unused_widget, event):
        if self._update:
            self._drawData()
        x, y, w, h = event.area
        self.window.draw_drawable(self.gc, self.pixmap, x, y, x, y, w, h)
        return True

    def setPixbuf(self, pixbuf):
        """ Change the current displayed pixbuf
        and force redraw of widget"""
        self.pixbuf = pixbuf
        # update the incoming thratio
        self.thratio = gst.Fraction(self.pixbuf.get_width(),
                self.pixbuf.get_height())
        self._update = True
        self.queue_draw()

    def setPixelAspectRatio(self, par):
        """ Change the current pixel aspect ratio
        and force redraw of widget"""
        self.par = par
        self._update = True
        self.queue_draw()

class SimpleSourceWidget(gtk.HBox):
    """
    Widget for representing a source in simple timeline view
    Takes a TimelineFileSource
    """

    __gsignals__ = {
        'delete-me' : (gobject.SIGNAL_RUN_LAST,
                       gobject.TYPE_NONE,
                       ( )),
        'edit-me' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     ( ))
        }

    border = 10

    def __init__(self, filesource):
        """Represents filesource in the simple timeline."""
        gtk.HBox.__init__(self)

        #TODO: create a separate thumbnailer for previewing effects
        self.filesource = filesource
        self._thumbnailer = Thumbnailer(uri=filesource.factory.name)
        self._thumbnailer.connect('thumbnail', self._thumbnailCb)

        # enter, leave, pointer-motion
        self.add_events(gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.ENTER_NOTIFY_MASK
                        | gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.BUTTON_PRESS_MASK
                        | gtk.gdk.BUTTON_RELEASE_MASK)
        self._createUI()

        # connect signals
        self.connect("button-press-event", self._buttonPressCb)
        filesource.connect("media-start-duration-changed",
                self._mediaStartDurationChangedCb)

        # popup menus
        self._popupMenu = gtk.Menu()
        deleteitem = gtk.MenuItem(_("Remove"))
        deleteitem.connect("activate", self._deleteMenuItemCb)
        deleteitem.show()

        # temporarily deactivate editing for 0.10.3 release !
        edititem = gtk.MenuItem(_("Edit"))
        edititem.connect("activate", self._editMenuItemCb)
        edititem.show()
        self._popupMenu.append(deleteitem)
        self._popupMenu.append(edititem)

        # Don't need this anymore

        # drag and drop
        #self.drag_source_set(gtk.gdk.BUTTON1_MASK,
        #                     [dnd.URI_TUPLE, dnd.FILESOURCE_TUPLE],
        #                     gtk.gdk.ACTION_COPY)
        #self.connect("drag_data_get", self._dragDataGetCb)

    def _createUI(self):
        # basic widget properties
        # TODO: randomly assign this color
        #self.csdf
        
        lor = self.get_colormap().alloc_color("green")
        #self.modify_bg(gtk.STATE_NORMAL, self.color)

        # control decorations
        decorations = gtk.HBox()
        name = gtk.Label()
        name.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        name.set_markup("<small><b>%s</b></small>" %
            os.path.basename(unquote(self.filesource.factory.name)))
        decorations.pack_start(name, True, True, 0)
        close = gtk.Image()
        close.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        close_btn = gtk.Button()
        close_btn.add(close)
        close_btn.connect("clicked", self._deleteMenuItemCb)
        close_btn.props.relief = gtk.RELIEF_NONE
        decorations.pack_end(close_btn, False, False, 0)

        # thumbnail
        thumbnail = gtk.gdk.pixbuf_new_from_file(
            os.path.join(get_pixmap_dir(), "pitivi-video.png"))
        self.thumb = ScaledThumbnailViewer(thumbnail)
        self._updateThumbnails()

        # editing
        editing = gtk.HBox()
        edit = gtk.Button()
        temp_label = gtk.Label()
        temp_label.set_markup("<small>%s</small>" % _("Edit"))
        edit.add(temp_label)
        edit.set_border_width(5)
        editing.pack_start(edit, False, True)
        self.duration = gtk.Label()
        self.duration.set_markup("<small>%s</small>" %
                beautify_length(self.filesource.factory.getDuration()))
        editing.pack_end(self.duration, False, False)
        edit.connect("clicked", self._editMenuItemCb)

        # effects
        effects = gtk.VBox()
        temp_label = gtk.Label()
        temp_label.set_markup("<small>%s</small>" % _("Effect"))
        effects.pack_start(temp_label, False, False)
        self.effect_preview = ScaledThumbnailViewer(thumbnail)
        effects.pack_start(self.effect_preview, True, True)

        # sound
        sound = gtk.VBox()
        temp_label = gtk.Label()
        temp_label.set_markup("<small>%s</small>" % _("Sound"))
        sound.pack_start(temp_label, False, False)

        self.volume_adjustment = gtk.Adjustment(1, 0, 2)
        self.volume_adjustment.connect("value-changed",
                self._volumeAdjustmentValueChangedCb)
        volume = gtk.VScale(self.volume_adjustment)
        volume.set_draw_value(False)
        volume.set_inverted(True)
        volume.set_size_request(0, 60)
        sound.pack_start(volume, True, True)

        # sound and effects
        s_and_e_align = gtk.Alignment(0, 1.0, 1.0, 1.00)
        s_and_e = gtk.HBox()
        s_and_e.pack_start(effects, True, True)
        s_and_e.pack_end(sound, False, True)
        s_and_e_align.add(s_and_e)

        #  lay out the widget
        layout = gtk.VBox()
        layout.set_border_width(5)
        layout.pack_start(decorations, False, False, 3)
        layout.pack_start(self.thumb, True, True)
        layout.pack_start(editing, False, False)
        layout.pack_end(s_and_e_align, False, False)
        self.add(layout)
        self.show_all()

    def _updateThumbnails(self):
        self._thumbnailer.makeThumbnail(self.filesource.media_start)

    def _thumbnailCb(self, thumbnailer, pixbuf, timestamp):
        self.thumb.setPixbuf(pixbuf)
        self.effect_preview.setPixbuf(pixbuf)
        if not self.filesource.factory.video_info_stream:
            height = 64 * pixbuf.get_height() / pixbuf.get_width()
        else:
            vi = self.filesource.factory.video_info_stream
            height = 64 * vi.dar.denom / vi.dar.num
        smallthumb = pixbuf.scale_simple(64, height, gtk.gdk.INTERP_BILINEAR)
        #self.drag_source_set_icon_pixbuf(smallthumb)

    def _mediaStartDurationChangedCb(self, unused_source, start, duration):
        self._updateThumbnails()
        self.duration.set_markup("<small>%s</small>" %
               beautify_length(duration))

    def _volumeAdjustmentValueChangedCb(self, adjustment):
        self.filesource.setVolume(adjustment.get_value())

    def _deleteMenuItemCb(self, unused_menuitem):
        self.emit('delete-me')

    def _editMenuItemCb(self, unused_menuitem):
        self.emit('edit-me')

    def _buttonPressCb(self, unused_widget, event):
        gst.debug("button %d" % event.button)
        if event.button == 3:
            self._popupMenu.popup(None,None,None,event.button,event.time)
        else:
            # FIXME: mark as being selected
            pass

    ## Drag and Drop

    def _dragDataGetCb(self, unused_widget, unused_context, selection,
                       targetType, unused_eventTime):
        gst.info("TimelineSource data get, type:%d" % targetType)
        if targetType in [dnd.TYPE_PITIVI_FILESOURCE, dnd.TYPE_URI_LIST]:
            selection.set(selection.target, 8, self.filesource.factory.name)


class SimpleTransitionWidget(gtk.DrawingArea):
    """ Widget for representing a transition in simple timeline view """

    # Change to use a TimelineTransitionEffect
    def __init__(self, transitionfactory):
        gobject.GObject.__init__(self)
        self.gc = None
        self.width = 0
        self.height = 0
        self.pixmap = None
        self.factory = transitionfactory
        self.connect("expose-event", self._exposeEventCb)
        self.connect("realize", self._realizeCb)
        self.connect("configure-event", self._configureEventCb)

    def _drawData(self):
        # actually do the drawing in the pixmap here
        if self.gc:
            self.pixmap = gtk.gdk.Pixmap(self.window, self.width, self.height)
            # background and border
            self.pixmap.draw_rectangle(self.style.white_gc, True,
                                       0, 0, self.width, self.height)
            self.pixmap.draw_rectangle(self.gc, False,
                                       1, 1, self.width - 2, self.height - 2)
            # draw name

    def _configureEventCb(self, unused_layout, event):
        self.width = event.width
        self.height = event.height
        # draw background pixmap
        if self.gc:
            self._drawData()
        return False

    def _realizeCb(self, unused_widget):
        self.gc = self.window.new_gc()
        self.gc.set_line_attributes(2, gtk.gdk.LINE_SOLID,
                                    gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
        self.gc.set_background(self.style.white)
        self._drawData()

    def _exposeEventCb(self, unused_widget, event):
        x, y, w, h = event.area
        self.window.draw_drawable(self.gc, self.pixmap,
                                  x, y, x, y, w, h)
        return True
