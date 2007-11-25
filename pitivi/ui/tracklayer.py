#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       pitivi/ui/tracklayer.py
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
Complex timeline composition track widget
"""

import gobject
import gtk
import gst
import cairo

import pitivi.dnd as dnd
import pitivi.instance as instance

from pitivi.timeline.source import TimelineFileSource
from complexinterface import ZoomableWidgetInterface
from complexsource import ComplexTimelineSource
from gettext import gettext as _

#
# TrackLayer
#
# The TrackLayer is the graphical representation of a top-level composition.
#

class TrackLayer(gtk.Layout, ZoomableWidgetInterface):

    __gsignals__ = {
        "size-allocate":"override",
        "expose-event":"override",
        "realize":"override",
        "motion-notify-event":"override",
        }

    border = 5
    effectgutter = 5
    layergutter = 5

    def __init__(self, layerInfo, hadj):
        gst.log("new TrackLayer for composition %r" % layerInfo.composition)
        gtk.Layout.__init__(self)

        self.hadjustment = hadj
        self.set_hadjustment(hadj)
        self.sources = {}
        self.layerInfo = layerInfo
        self.layerInfo.composition.connect('start-duration-changed', self._compStartDurationChangedCb)
        self.layerInfo.composition.connect('source-added', self._compSourceAddedCb)
        self.layerInfo.composition.connect('source-removed', self._compSourceRemovedCb)

        self.position = 0

        self.pixmap = None

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.FILESOURCE_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect('drag-data-received', self._dragDataReceivedCb)
        self.connect('drag-leave', self._dragLeaveCb)
        self.connect('drag-motion', self._dragMotionCb)

        self.connect('button-press-event', self._buttonPressEventCb)
        self.connect('button-release-event', self._buttonReleaseEventCb)

        self._mouseDownPosition = [None, None]
        self._movingSource = None
        self._origSourcePosition = None
        self._requestedPosition = None
        self._currentlyMoving = False

        self._popupMenu = gtk.Menu()
        deleteitem = gtk.MenuItem(_("Remove"))
        deleteitem.connect("activate", self._deleteMenuItemCb)
        deleteitem.show()
        self._popupMenu.append(deleteitem)

        cutitem = gtk.MenuItem(_("Cut"))
        cutitem.connect("activate", self._cutMenuItemCb)
        cutitem.show()
        self._popupMenu.append(cutitem)

        # object being currently dragged
        self.dragObject = None

        self.add_events(gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK)

    def _deleteMenuItemCb(self, unused_menuitem):
        # remove currently selected source
        gst.log("removing source")
        self.layerInfo.composition.removeSource(self._movingSource)
        self._movingSource = None

    def _cutMenuItemCb(self, unused_menuitem):
        gst.log("cut at position %s" % gst.TIME_ARGS(self.position))
        # cut current source at current position
        source = self._findSourceAtPositionTime(self.position)

        gst.log("source:%s start:%s duration:%s" % (source,
                                                    gst.TIME_ARGS(source.start),
                                                    gst.TIME_ARGS(source.duration)))
        gst.log("media start:%s duration:%s" % (gst.TIME_ARGS(source.media_start),
                                                gst.TIME_ARGS(source.media_duration)))

        # 1 . change duration
        newfirstduration = self.position - source.start
        newfirstmediaduration = source.media_duration * (self.position - source.start) / source.duration

        newsecondduration = source.start + source.duration - self.position
        newsecondmediaduration = source.media_duration - newfirstmediaduration

        source.setStartDurationTime(duration = newfirstduration)
        source.setMediaStartDurationTime(duration = newfirstmediaduration)

        gst.log("source:%s start:%s duration:%s" % (source,
                                                    gst.TIME_ARGS(source.start),
                                                    gst.TIME_ARGS(source.duration)))
        gst.log("media start:%s duration:%s" % (gst.TIME_ARGS(source.media_start),
                                                gst.TIME_ARGS(source.media_duration)))

        # 2 . Add new item
        newsource = TimelineFileSource(factory = source.factory,
                                       media_type = self.layerInfo.composition.media_type,
                                       name = source.factory.name,
                                       start = self.position, duration = newsecondduration,
                                       media_start = source.media_start + newfirstmediaduration,
                                       media_duration = newsecondmediaduration)

        gst.log("source:%s start:%s duration:%s" % (newsource,
                                                    gst.TIME_ARGS(newsource.start),
                                                    gst.TIME_ARGS(newsource.duration)))
        gst.log("media start:%s duration:%s" % (gst.TIME_ARGS(newsource.media_start),
                                                gst.TIME_ARGS(newsource.media_duration)))

        self.layerInfo.composition.addSource(newsource, 1)

        # 3 . Change position/duration of new item

    ## composition signal callbacks

    def _compStartDurationChangedCb(self, unused_composition, unused_start,
                                    unused_duration):
        gst.info("setting width-request to %d" % self.getPixelWidth())
        self.set_property("width-request", self.getPixelWidth())
        self.set_size(self.getPixelWidth() + 2 * self.border, self.allocation.height)
        #self.set_property("height-request", self.layerInfo.currentHeight)
        self.startDurationChanged()

    def _compSourceAddedCb(self, unused_composition, source):
        gst.debug("Got a new source")
        # create new widget
        widget = ComplexTimelineSource(source, self.layerInfo)

        # add it to self at the correct position
        self.sources[source] = widget
        # TODO : set Y position depending on layer it's on
        self.put(widget, self.nsToPixel(widget.getStartTime()) + self.border,
                 self.effectgutter + self.layergutter)
        widget.show()
        # we need to keep track of the child's position
        source.connect_after('start-duration-changed', self._childStartDurationChangedCb)
        gst.debug("Finished adding source")

    def _compSourceRemovedCb(self, unused_composition, source):
        gst.debug("source removed")

        try:
            widget = self.sources[source]
        except:
            return

        widget.hide()
        self.remove(widget)
        del self.sources[source]

        gst.debug("finished removing source")

    ## ZoomableWidgetInterface methods

    def getDuration(self):
        return self.layerInfo.composition.duration

    def getStartTime(self):
        return self.layerInfo.composition.start

    def getPixelWidth(self):
        # Add borders
        pwidth = ZoomableWidgetInterface.getPixelWidth(self) + 2 * self.border
        return pwidth

    def zoomChanged(self):
        for source in self.sources.itervalues():
            self.move(source,
                      source.getPixelPosition() + self.border,
                      self.effectgutter + self.layergutter)

    ## gtk.Widget methods overrides

    def do_size_allocate(self, allocation):
        gst.debug("%r got allocation %s" % (self, list(allocation)))
        for source in self.sources:
            if self.layerInfo.expanded:
                height = 100
            else:
                height = allocation.height - self.effectgutter - 2 * self.layergutter
            self.sources[source].set_property("height-request", height)
        gtk.Layout.do_size_allocate(self, allocation)
        self.drawPixmap()

    def do_realize(self):
        gtk.Layout.do_realize(self)
        self.drawPixmap()

    def do_expose_event(self, event):
        gst.debug("TrackLayer %s" % list(event.area))
        x, y, width, height = event.area

        self.bin_window.draw_drawable(self.style.fg_gc[gtk.STATE_NORMAL],
                                      self.pixmap,
                                      x, y, x, y, width, height)
        return gtk.Layout.do_expose_event(self, event)

    def _moveTimeoutCb(self):
        self._currentlyMoving = False
        if self._requestedPosition and self._movingSource:
            self._movingSource.setStartDurationTime(start = self._requestedPosition)

    def do_motion_notify_event(self, event):
        gst.debug("motion x:%d y:%d" % (event.x , event.y))
        if not self._mouseDownPosition[0] == None:
            diffx = event.x - self._mouseDownPosition[0]
            diffy = event.y - self._mouseDownPosition[1]
            gst.debug("we moved by x:%d, y:%d" % (diffx, diffy))
            if self._movingSource:
                newstart = self._origSourcePosition + self.pixelToNs(diffx)
                # FIXME : implement blocking !!
                if newstart < 0:
                    newstart = 0
                gst.debug("we should move the source to %s" % gst.TIME_ARGS(newstart))
                if not self._currentlyMoving:
                    self._currentlyMoving = True
                    gobject.timeout_add(80, self._moveTimeoutCb)
                    self._movingSource.setStartDurationTime(start = newstart)
                self._requestedPosition = newstart

    ## Drawing methods

    def drawPixmap(self):
        # let's draw a nice gradient on the background
        if not self.flags() & gtk.REALIZED:
            return
        gst.debug("drawPixmap")
        alloc = self.get_allocation()
        if self.pixmap:
            del self.pixmap
        self.pixmap = gtk.gdk.Pixmap(self.bin_window, alloc.width, alloc.height)
        context = self.pixmap.cairo_create()

        pat = cairo.LinearGradient(0, 0, 0, alloc.height)
        pat.add_color_stop_rgb(0, 0.5, 0.5, 0.6)
        pat.add_color_stop_rgb(1, 0.6, 0.6, 0.7)

        context.rectangle(0, 0, alloc.width, alloc.height)
        context.set_source(pat)
        context.fill()
        context.stroke()


    ## Child callbacks

    def _childStartDurationChangedCb(self, source, start,
                                     duration):
        # move accordingly
        gst.debug("%r start:%s duration:%s" % (source, gst.TIME_ARGS(start),
                                               gst.TIME_ARGS(duration)))
        if start != -1:
            widget = self.sources[source]
            x = widget.getPixelPosition()
            if x != self.child_get_property(widget, "x"):
                self.move(widget, x + self.border,
                          self.effectgutter + self.layergutter)
            self.queue_resize()


    ## methods needed by the container (CompositionLayer)

    def getNeededHeight(self):
        """ return the needed height """
        if self.layerInfo.expanded:
            # TODO : update this formula
            # height = effectgutter + layergutter + n * (layerheight + layergutter)
            height = self.effectgutter + 2 * self.layergutter + 100
            return height
        return 0

    def timelinePositionChanged(self, value, unused_frame):
        self.position = value

    ## Drag and Drop

    def _dragDataReceivedCb(self, unused_layout, context, x, unused_y, selection,
                           targetType, timestamp):
        # something was dropped
        gst.debug("%s" % type(selection))
        self.dragObject = None
        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            # a source was dropped
            source = instance.PiTiVi.current.sources[selection.data]
        else:
            context.finish(False, False, timestamp)
            return
        x += int(self.hadjustment.get_value())
        gst.debug("got source %s x:%d" % (source, x))

        # do something with source
        # FIXME : CURRENTLY ONLY ADDED AT BEGINNING
        self.layerInfo.composition.prependSource(TimelineFileSource(factory=source,
                                                                    media_type=self.layerInfo.composition.media_type,
                                                                    name=source.name))

        context.finish(True, False, timestamp)
        instance.PiTiVi.playground.switchToTimeline()

    def _dragLeaveCb(self, unused_layout, unused_context, unused_timestamp):
        gst.debug("something left")
        self.dragObject = None

    def _dragMotionCb(self, unused_layout, context, x, y, unused_timestamp):
        gst.debug("something entered x:%d, y:%d" % (x,y))
        if not self.dragObject:
            source = context.get_source_widget().getSelectedItems()[0]
            self.dragObject = instance.PiTiVi.current.sources[source]
        gst.debug("we have %s" % self.dragObject)

    ## Mouse callbacks

    def _buttonPressEventCb(self, unused_layout, event):
        if event.button == 1:
            self._mouseDownPosition = [event.x, event.y]
            gst.log("Mouse down at %d / %d" % (event.x, event.y))
            source = self._findSourceAtPosition(event.x)
            if source:
                gst.log("we are moving %s" % source)
                self._movingSource = source
                self._origSourcePosition = source.start
        elif event.button == 3:
            source = self._findSourceAtPosition(event.x)
            if source:
                gst.log("we are moving %s" % source)
                self._movingSource = source
                self._origSourcePosition = source.start
                self._popupMenu.popup(None,None,None, event.button, event.time)

    def _buttonReleaseEventCb(self, unused_layout, unused_event):
        gst.log("Mouse up !")
        # reset values
        self._mouseDownPosition = [None,None]
        self._movingSource = None
        self._origSourcePosition = None

    def _findSourceAtPosition(self, position):
        """
        Find which source is at the given pixel position.
        Returns the source if there is one, or None if no source
        is at the given position
        """
        position -= self.border
        for source, widget in self.sources.iteritems():
            minv = widget.getPixelPosition()
            maxv = minv + widget.getPixelWidth()
            if position >= minv and position < maxv:
                return source

        return None

    def _findSourceAtPositionTime(self, position):
        """
        Find which source is at the given time.
        Returns the source if there is one, or None if no source is
        at the requested time.
        """
        for source, widget in self.sources.iteritems():
            start = source.start
            stop = start + source.duration
            if position >= start and position < stop:
                return source
        return None
