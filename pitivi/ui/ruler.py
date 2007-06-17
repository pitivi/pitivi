# PiTiVi , Non-linear video editor
#
#       pitivi/ui/ruler.py
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
Widget for the complex view ruler
"""

import gobject
import gtk
import gst
import pitivi.instance as instance
from complexinterface import ZoomableWidgetInterface

class ScaleRuler(gtk.Layout, ZoomableWidgetInterface):

    __gsignals__ = {
        "expose-event":"override",
        "size-allocate":"override",
        "realize":"override",
        "button-press-event":"override",
        "button-release-event":"override",
        "motion-notify-event":"override",
        }

    border = 5

    def __init__(self, hadj):
        gst.log("Creating new ScaleRule")
        gtk.Layout.__init__(self)
        self.add_events(gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK)
        self.set_hadjustment(hadj)
        self.pixmap = None
        # position is in nanoseconds
        self.position = 0

        self.requested_time = long(0)
        self.currentlySeeking = False
        self.pressed = False

    ## ZoomableWidgetInterface methods are handled by the container (LayerStack)
    ## Except for ZoomChanged

    def zoomChanged(self):
        self.doPixmap()
        self.queue_draw()

    def getPixelWidth(self):
        return ZoomableWidgetInterface.getPixelWidth(self) + 2 * self.border


    ## timeline position changed method

    def timelinePositionChanged(self, value, unused_frame):
        previous = self.position
        self.position = value
        self.queue_draw_area(max(self.nsToPixel(min(value, previous)) - 5, 0),
                             0,
                             self.nsToPixel(max(value, previous)) + 5,
                             self.get_allocation().height)

    ## gtk.Widget overrides

    def do_size_allocate(self, allocation):
        gst.debug("ScaleRuler got %s" % list(allocation))
        gtk.Layout.do_size_allocate(self, allocation)
        width = max(self.getPixelWidth(), allocation.width)
        gst.debug("Setting layout size to %d x %d" % (width, allocation.height))
        self.set_size(width, allocation.height)
        # the size has changed, therefore we want to redo our pixmap
        self.doPixmap()

    def do_realize(self):
        gtk.Layout.do_realize(self)
        # we want to create our own pixmap here
        self.doPixmap()

    def do_expose_event(self, event):
        gst.debug("exposing ScaleRuler %s" % list(event.area))
        x, y, width, height = event.area
        # double buffering power !
        self.bin_window.draw_drawable(self.style.fg_gc[gtk.STATE_NORMAL],
                                      self.pixmap,
                                      x, y, x, y, width, height)
        # draw the position
        context = self.bin_window.cairo_create()
        self.drawPosition(context, self.get_allocation())
        return False

    def do_button_press_event(self, event):
        gst.debug("button pressed at x:%d" % event.x)
        instance.PiTiVi.playground.switchToTimeline()
        self.pressed = True
        # seek at position
        cur = self.pixelToNs(event.x)
        self._doSeek(cur)
        return True

    def do_button_release_event(self, event):
        gst.debug("button released at x:%d" % event.x)
        self.pressed = False
        return False

    def do_motion_notify_event(self, event):
        gst.debug("motion at event.x %d" % event.x)
        if self.pressed:
            # seek at position
            cur = self.pixelToNs(event.x)
            self._doSeek(cur)
        return False

    ## Seeking methods

    def _seekTimeoutCb(self):
        gst.debug("timeout")
        self.currentlySeeking = False
        if not self.position == self.requested_time:
            self._doSeek(self.requested_time)

    def _doSeek(self, value, format=gst.FORMAT_TIME):
        gst.debug("seeking to %s" % gst.TIME_ARGS (value))
        if not self.currentlySeeking:
            self.currentlySeeking = True
            self.requested_time = value
            gobject.timeout_add(80, self._seekTimeoutCb)
            instance.PiTiVi.playground.seekInCurrent(value, format=format)
        elif format == gst.FORMAT_TIME:
            self.requested_time = value

    ## Drawing methods

    def doPixmap(self):
        """ (re)create the buffered drawable for the Widget """
        # we can't create the pixmap if we're not realized
        if not self.flags() & gtk.REALIZED:
            return
        allocation = self.get_allocation()
        lwidth, lheight = self.get_size()
        allocation.width = max(allocation.width, lwidth)
        gst.debug("Creating pixmap(self.window, width:%d, height:%d)" % (allocation.width, allocation.height))
        if self.pixmap:
            del self.pixmap
        self.pixmap = gtk.gdk.Pixmap(self.bin_window, allocation.width, allocation.height)
        context = self.pixmap.cairo_create()
        self.drawBackground(context, allocation)
        self.drawRuler(context, allocation)

    def draw(self, context):
        rect = self.get_allocation()
        gst.debug("Ruler draw %s" % list(rect))
        self.drawBackground(context, rect)
        self.drawRuler(context, rect)

    def drawBackground(self, context, allocation):
        context.save()

        context.set_source_rgb(0.5, 0.5, 0.5)
        context.rectangle(0, 0,
                          allocation.width, allocation.height)
        context.fill()
        context.stroke()

        if self.getDuration() > 0:
            context.set_source_rgb(0.8, 0.8, 0.8)
            context.rectangle(0, 0,
                              self.getPixelWidth(), allocation.height)
            context.fill()
            context.stroke()

        context.restore()

    def drawRuler(self, context, allocation):
        context.save()

        zoomRatio = self.getZoomRatio()

        paintpos = float(self.border) + 0.5
        seconds = 0
        secspertic = 1

        timeprint = 0
        ticspertime = 1

        # FIXME : this should be beautified (instead of all the if/elif/else)
        if zoomRatio < 0.05:
            #Smallest tic is 10 minutes
            secspertic = 600
            if zoomRatio < 0.006:
                ticspertime = 24
            elif zoomRatio < 0.0125:
                ticspertime = 12
            elif zoomRatio < 0.025:
                ticspertime = 6
            else:
                ticspertime = 3
        elif zoomRatio < 0.5:
            #Smallest tic is 1 minute
            secspertic = 60
            if zoomRatio < 0.25:
                ticspertime = 10
            else:
                ticspertime = 5
        elif zoomRatio < 3:
            #Smallest tic is 10 seconds
            secspertic = 10
            if zoomRatio < 1:
                ticspertime = 12
            else:
                ticspertime = 6
        else:
            #Smallest tic is 1 second
            if zoomRatio < 5:
                ticspertime = 20
            elif zoomRatio < 10:
                ticspertime = 10
            elif zoomRatio < 20:
                ticspertime = 5
            elif zoomRatio < 40:
                ticspertime = 2

        while paintpos < allocation.width:
            context.move_to(paintpos, 0)

            if seconds % 600 == 0:
                context.line_to(paintpos, allocation.height)
            elif seconds % 60 == 0:
                context.line_to(paintpos, allocation.height * 3 / 4)
            elif seconds % 10 == 0:
                context.line_to(paintpos, allocation.height / 2)
            else:
                context.line_to(paintpos, allocation.height / 4)

            if timeprint == 0:
                # draw the text position
                hours = seconds / 3600
                mins = seconds % 3600 / 60
                secs = seconds % 60
                time = "%02d:%02d:%02d" % (hours, mins, secs)
                txtwidth, txtheight = context.text_extents(time)[2:4]
                context.move_to( paintpos - txtwidth / 2.0,
                                 allocation.height - 2 )
                context.show_text( time )
                timeprint = ticspertime
            timeprint -= 1

            paintpos += zoomRatio * secspertic
            seconds += secspertic

        #Since drawing is done in batch we can't use different styles
        context.set_line_width(1)
        context.set_source_rgb(0, 0, 0)

        context.stroke()
        context.restore()

    def drawPosition(self, context, allocation):
        if self.getDuration() <= 0:
            return
        # a simple RED line will do for now
        xpos = self.nsToPixel(self.position) + self.border + 0.5
        context.save()
        context.set_source_rgb(1.0, 0, 0)

        context.move_to(xpos, 0)
        context.line_to(xpos, allocation.height)
        context.stroke()

        context.restore()
