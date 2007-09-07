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

# Default width / height ratio for simple elements
DEFAULT_SIMPLE_SIZE_RATIO = 1.50 # default height / width ratio

# Default simple elements size
DEFAULT_SIMPLE_ELEMENT_WIDTH = 150
DEFAULT_SIMPLE_ELEMENT_HEIGHT = DEFAULT_SIMPLE_ELEMENT_WIDTH * DEFAULT_SIMPLE_SIZE_RATIO

# Default spacing between/above elements in simple timeline
DEFAULT_SIMPLE_SPACING = 10

# Simple Timeline's default values
DEFAULT_HEIGHT = DEFAULT_SIMPLE_ELEMENT_HEIGHT + 2 * DEFAULT_SIMPLE_SPACING
DEFAULT_WIDTH = 3 * DEFAULT_SIMPLE_SPACING # borders (2) + one holding place
MINIMUM_HEIGHT = DEFAULT_HEIGHT
MINIMUM_WIDTH = 3 * MINIMUM_HEIGHT

def time_to_string(value):
    if value == -1:
        return "--:--:--.---"
    ms = value / gst.MSECOND
    sec = ms / 1000
    ms = ms % 1000
    mins = sec / 60
    sec = sec % 60
    hours = mins / 60
    return "%02d:%02d:%02d.%03d" % (hours, mins, sec, ms)

class SimpleTimeline(gtk.Layout):
    """ Simple Timeline representation """

    def __init__(self, **kw):
        gobject.GObject.__init__(self, **kw)

        self.hadjustment = self.get_property("hadjustment")

        # timeline and top level compositions
        self.timeline = instance.PiTiVi.current.timeline
        self.condensed = self.timeline.videocomp.condensed

        # TODO : connect signals for when the timeline changes

        # widgets correspondance dictionnary
        # MAPPING timelineobject => widget
        self.widgets = {}

        # edit-mode
        # True when in editing mode
        self._editingMode = False
        self.editingWidget = SimpleEditingWidget()
        self.editingWidget.connect("hide-me", self._editingWidgetHideMeCb)

        # Connect to timeline.  We must remove and reset the callbacks when
        # changing project.
        self.project_signals = SignalGroup()
        self._connectToTimeline(instance.PiTiVi.current.timeline)
        instance.PiTiVi.connect("new-project-loaded", self._newProjectCb)

        # size
        self.width = int(DEFAULT_WIDTH)
        self.height = int(DEFAULT_HEIGHT)
        self.realWidth = 0 # displayed width of the layout
        self.childheight = int(DEFAULT_SIMPLE_ELEMENT_HEIGHT)
        self.childwidth = int(DEFAULT_SIMPLE_ELEMENT_WIDTH)
        self.set_size_request(int(MINIMUM_WIDTH), int(MINIMUM_HEIGHT))
        self.set_property("width", int(DEFAULT_WIDTH))
        self.set_property("height", int(DEFAULT_HEIGHT))

        # event callbacks
        self.connect("expose-event", self._exposeEventCb)
        self.connect("notify::width", self._widthChangedCb)
        self.connect("size-allocate", self._sizeAllocateCb)
        self.connect("realize", self._realizeCb)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.FILESOURCE_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.connect("drag-leave", self._dragLeaveCb)
        self.connect("drag-motion", self._dragMotionCb)
        self.slotposition = -1

        self.draggedelement = None

        self.show_all()


    ## Project callbacks

    def _connectToTimeline(self, timeline):
        self.timeline = timeline
        self.condensed = self.timeline.videocomp.condensed

        self.project_signals.connect(self.timeline.videocomp,
                                     "condensed-list-changed",
                                     None, self._condensedListChangedCb)

    def _newProjectCb(self, unused_pitivi, project):
        assert(instance.PiTiVi.current == project)

        for widget in self.widgets.itervalues():
            self.remove(widget)
        self.widgets = {}

        self._connectToTimeline(instance.PiTiVi.current.timeline)


    ## Timeline callbacks

    def _condensedListChangedCb(self, unused_videocomp, clist):
        """ add/remove the widgets """
        gst.debug("condensed list changed in videocomp")

        current = self.widgets.keys()
        self.condensed = clist

        new = [x for x in clist if not x in current]
        removed = [x for x in current if not x in clist]

        # new elements
        for element in new:
            # add the widget to self.widget
            gst.debug("Adding new element to the layout")
            if isinstance(element, TimelineFileSource):
                widget = SimpleSourceWidget(element)
                widget.connect("delete-me", self._sourceDeleteMeCb, element)
                widget.connect("edit-me", self._sourceEditMeCb, element)
                widget.connect("drag-begin", self._sourceDragBeginCb, element)
                widget.connect("drag-end", self._sourceDragEndCb, element)
            else:
                widget = SimpleTransitionWidget(element)
            self.widgets[element] = widget
            self.put(widget, 0, 0)
            widget.show()

        # removed elements
        for element in removed:
            self.remove(self.widgets[element])
            del self.widgets[element]

        self._resizeChildrens()


    ## Utility methods

    def _getNearestSourceSlot(self, x):
        """
        returns the nearest file slot position available for the given position
        Returns the value in condensed list position
        Returns n , the element before which it should go
        Return -1 if it's meant to go last
        """
        if not self.condensed or x < 0:
            return 0
        if x > self.width - DEFAULT_SIMPLE_SPACING:
            return -1

        pos = DEFAULT_SIMPLE_SPACING
        order = 0
        # TODO Need to avoid getting position between source and transition
        for source in self.condensed:
            if isinstance(source, TimelineSource):
                spacing = self.childheight
            elif isinstance(source, TimelineTransition):
                spacing = self.childheight / 2
            else:
                # this shouldn't happen !! The condensed list only contains
                # sources and/or transitions
                pass
            if x <= pos + spacing / 2:
                return order
            pos = pos + spacing + DEFAULT_SIMPLE_SPACING
            order = order + 1
        return -1

    def _getNearestSourceSlotPixels(self, x):
        """
        returns the nearest file slot position available for the given position
        Returns the value in pixels
        """
        if not self.condensed or x < 0:
            return DEFAULT_SIMPLE_SPACING
        if x > self.width - DEFAULT_SIMPLE_SPACING:
            return self.width - 2 * DEFAULT_SIMPLE_SPACING

        pos = DEFAULT_SIMPLE_SPACING
        # TODO Need to avoid getting position between source and transition
        for source in self.condensed:
            if isinstance(source, TimelineSource):
                spacing = self.childheight
            elif isinstance(source, TimelineTransition):
                spacing = self.childheight / 2
            else:
                # this shouldn't happen !! The condensed list only contains
                # sources and/or transitions
                pass
            if x <= pos + spacing / 2:
                return pos
            pos = pos + spacing + DEFAULT_SIMPLE_SPACING
        return pos


    ## Drawing

    def _drawDragSlot(self):
        if self.slotposition == -1:
            return
        self.bin_window.draw_rectangle(self.style.black_gc, True,
                                       self.slotposition, DEFAULT_SIMPLE_SPACING,
                                       DEFAULT_SIMPLE_SPACING, self.childheight)

    def _eraseDragSlot(self):
        if self.slotposition == -1:
            return
        self.bin_window.draw_rectangle(self.style.white_gc, True,
                                       self.slotposition, DEFAULT_SIMPLE_SPACING,
                                       DEFAULT_SIMPLE_SPACING, self.childheight)

    def _gotFileFactory(self, filefactory, x, unused_y):
        """ got a filefactory at the given position """
        # remove the slot
        self._eraseDragSlot()
        self.slotposition = -1
        if not filefactory or not filefactory.is_video:
            return
        pos = self._getNearestSourceSlot(x)

        gst.debug("_got_filefactory pos : %d" % pos)

        # we just add it here, the drawing will be done in the condensed_list
        # callback
        source = TimelineFileSource(factory=filefactory,
                                    media_type=MEDIA_TYPE_VIDEO,
                                    name=filefactory.name)

        # ONLY FOR SIMPLE TIMELINE : if video-only, we link a blank audio object
        if not filefactory.is_audio:
            audiobrother = TimelineBlankSource(factory=filefactory,
                                               media_type=MEDIA_TYPE_AUDIO,
                                               name=filefactory.name)
            source.setBrother(audiobrother)

        if pos == -1:
            self.timeline.videocomp.appendSource(source)
        elif pos:
            self.timeline.videocomp.insertSourceAfter(source, self.condensed[pos - 1])
        else:
            self.timeline.videocomp.prependSource(source)

    def _moveElement(self, element, x):
        gst.debug("TimelineSource, move %s to x:%d" % (element, x))
        # remove the slot
        self._eraseDragSlot()
        self.slotposition = -1
        pos = self._getNearestSourceSlot(x)

        self.timeline.videocomp.moveSource(element, pos)

    def _widthChangedCb(self, unused_layout, property):
        if not property.name == "width":
            return
        self.width = self.get_property("width")

    def _motionNotifyEventCb(self, layout, event):
        pass


    ## Drag and Drop callbacks

    def _dragMotionCb(self, unused_layout, unused_context, x, unused_y,
                      unused_timestamp):
        # TODO show where the dragged item would go
        pos = self._getNearestSourceSlotPixels(x + (self.hadjustment.get_value()))
        rpos = self._getNearestSourceSlot(x + self.hadjustment.get_value())
        gst.log("SimpleTimeline x:%d , source would go at %d" % (x, rpos))
        if not pos == self.slotposition:
            if not self.slotposition == -1:
                # erase previous slot position
                self._eraseDragSlot()
            # draw new slot position
            self.slotposition = pos
            self._drawDragSlot()

    def _dragLeaveCb(self, unused_layout, unused_context, unused_timestamp):
        gst.log("SimpleTimeline")
        self._eraseDragSlot()
        self.slotposition = -1
        # TODO remove the drag emplacement

    def _dragDataReceivedCb(self, unused_layout, context, x, y, selection,
                            targetType, timestamp):
        gst.log("SimpleTimeline, targetType:%d, selection.data:%s" % (targetType, selection.data))
        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, timestamp)
        x = x + int(self.hadjustment.get_value())
        if self.draggedelement:
            self._moveElement(self.draggedelement, x)
        else:
            self._gotFileFactory(instance.PiTiVi.current.sources[uri], x, y)
        context.finish(True, False, timestamp)
        instance.PiTiVi.playground.switchToTimeline()


    ## Drawing

    def _realizeCb(self, unused_layout):
        self.modify_bg(gtk.STATE_NORMAL, self.style.white)

    def _areaIntersect(self, x, y, w, h, x2, y2, w2, h2):
        """ returns True if the area intersects, else False """
        # is zone to the left of zone2
        z1 = gtk.gdk.Rectangle(x, y, w, h)
        z2 = gtk.gdk.Rectangle(x2, y2, w2, h2)
        r = z1.intersect(z2)
        a, b, c, d = r
        if a or b or c or d:
            return True
        return False

    def _exposeEventCb(self, unused_layout, event):
        x, y, w, h = event.area
        # redraw the slot rectangle if there's one
        if not self.slotposition == -1:
            if self._areaIntersect(x, y, w, h,
                                   self.slotposition, DEFAULT_SIMPLE_SPACING,
                                   DEFAULT_SIMPLE_SPACING, self.childheight):
                self.bin_window.draw_rectangle(self.style.black_gc, True,
                                               self.slotposition, DEFAULT_SIMPLE_SPACING,
                                               DEFAULT_SIMPLE_SPACING, self.childheight)

        return False

    def _sizeAllocateCb(self, unused_layout, allocation):
        if not self.height == allocation.height:
            self.height = allocation.height
            self.childheight = self.height - 2 * DEFAULT_SIMPLE_SPACING
            self.childwidth = int(self.height / DEFAULT_SIMPLE_SIZE_RATIO)
            self._resizeChildrens()
        self.realWidth = allocation.width
        if self._editingMode:
            self.editingWidget.set_size_request(self.realWidth - 20,
                                                self.height - 20)

    def _resizeChildrens(self):
        # resize the childrens to self.height
        # also need to move them to their correct position
        # TODO : check if there already at the given position
        # TODO : check if they already have the good size
        if self._editingMode:
            return
        pos = 2 * DEFAULT_SIMPLE_SPACING
        for source in self.condensed:
            widget = self.widgets[source]
            if isinstance(source, TimelineFileSource):
                widget.set_size_request(self.childwidth, self.childheight)
                self.move(widget, pos, DEFAULT_SIMPLE_SPACING)
                pos = pos + self.childwidth + DEFAULT_SIMPLE_SPACING
            elif isinstance(source, SimpleTransitionWidget):
                widget.set_size_request(self.childheight / 2, self.childheight)
                self.move(widget, pos, DEFAULT_SIMPLE_SPACING)
                pos = pos + self.childwidth + DEFAULT_SIMPLE_SPACING
        newwidth = pos + DEFAULT_SIMPLE_SPACING
        self.set_property("width", newwidth)

    ## Child callbacks

    def _sourceDeleteMeCb(self, unused_widget, element):
        # remove this element from the timeline
        self.timeline.videocomp.removeSource(element, collapse_neighbours=True)

    def _sourceEditMeCb(self, unused_widget, element):
        self.switchToEditingMode(element)

    def _sourceDragBeginCb(self, unused_widget, unused_context, element):
        gst.log("Timeline drag beginning on %s" % element)
        if self.draggedelement:
            gst.error("We were already doing a DnD ???")
        self.draggedelement = element
        # this element is starting to be dragged

    def _sourceDragEndCb(self, unused_widget, unused_context, element):
        gst.log("Timeline drag ending on %s" % element)
        if not self.draggedelement == element:
            gst.error("The DnD that ended is not the one that started before ???")
        self.draggedelement = None
        # this element is no longer dragged

    def _editingWidgetHideMeCb(self, unused_widget):
        self.switchToNormalMode()
        # switch back to timeline in playground !
        instance.PiTiVi.playground.switchToTimeline()



    ## Editing mode

    def _switchEditingMode(self, source, mode=True):
        """ Switch editing mode for the given TimelineSource """
        gst.log("source:%s , mode:%s" % (source, mode))

        if self._editingMode == mode:
            gst.warning("We were already in the correct editing mode : %s" % mode)
            return

        if mode and not source:
            gst.warning("You need to specify a valid TimelineSource")
            return

        if mode:
            # switching TO editing mode
            gst.log("Switching TO editing mode")

            # 1. Hide all sources
            for widget in self.widgets.itervalues():
                widget.hide()
                self.remove(widget)

            self._editingMode = mode

            # 2. Show editing widget
            self.editingWidget.setSource(source)
            self.put(self.editingWidget, 10, 10)
            self.props.width = self.realWidth
            self.editingWidget.set_size_request(self.realWidth - 20, self.height - 20)
            self.editingWidget.show()

        else:
            gst.log("Switching back to normal mode")
            # switching FROM editing mode

            # 1. Hide editing widget
            self.editingWidget.hide()
            self.remove(self.editingWidget)

            self._editingMode = mode

            # 2. Show all sources
            for widget in self.widgets.itervalues():
                self.put(widget, 0, 0)
                widget.show()
            self._resizeChildrens()

    def switchToEditingMode(self, source):
        """ Switch to Editing mode for the given TimelineSource """
        self._switchEditingMode(source)

    def switchToNormalMode(self):
        """ Switch back to normal timeline mode """
        self._switchEditingMode(None, False)


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
        id = instance.PiTiVi.playground.connect("position",
            self._playgroundPositionCb)
        self._playgroundPositionSigId = id

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

    def _updateTextFields(self, start=-1, duration=-1):
        if not start == -1:
            self.startPos.props.label = time_to_string(start)
        if not start == -1 and not duration == -1:
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

        duration_max = self._source.factory.length - self._mediaStart
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
        print (time_to_string(self._mediaStart),
            time_to_string(self._mediaDuration))
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
        assert end <= self._source.factory.length 

        if (self._mediaStart + gst.SECOND) >= end:
            self.startAdvanceButton.set_sensitive(False)
        else:
            self.startAdvanceButton.set_sensitive(True)

        if (end - gst.SECOND) <= self._mediaStart:
            self.endRewindButton.set_sensitive(False)
        else:
            self.endRewindButton.set_sensitive(True)

        if end >= self._source.factory.length:
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

class SimpleSourceWidget(gtk.EventBox):
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
        gtk.EventBox.__init__(self)

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

        # drag and drop
        self.drag_source_set(gtk.gdk.BUTTON1_MASK,
                             [dnd.URI_TUPLE, dnd.FILESOURCE_TUPLE],
                             gtk.gdk.ACTION_COPY)
        self.connect("drag_data_get", self._dragDataGetCb)

    def _createUI(self):
        # basic widget properties
        # TODO: randomly assign this color
        #self.color = self.get_colormap().alloc_color("green")
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
                beautify_length(self.filesource.factory.length))
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
        self.drag_source_set_icon_pixbuf(smallthumb)

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
