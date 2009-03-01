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
from pitivi.ui.zoominterface import Zoomable
from pitivi.log.loggable import Loggable
from pitivi.utils import time_to_string

class ScaleRuler(gtk.Layout, Zoomable, Loggable):

    __gsignals__ = {
        "expose-event":"override",
        "size-allocate":"override",
        "realize":"override",
        "button-press-event":"override",
        "button-release-event":"override",
        "motion-notify-event":"override",
        "scroll-event" : "override",
        "seek": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                [gobject.TYPE_UINT64])
        }

    border = 0
    min_tick_spacing = 3

    def __init__(self, hadj):
        gtk.Layout.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.log("Creating new ScaleRule")
        self.add_events(gtk.gdk.POINTER_MOTION_MASK |
            gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK)
        self.set_hadjustment(hadj)

        # double-buffering properties
        self.pixmap = None
        # all values are in pixels
        self.pixmap_offset = 0
        self.pixmap_visible_width = 0
        self.pixmap_allocated_width = 0
        self.pixmap_old_allocated_width = -1
        # This is the number of visible_width we allocate for the pixmap
        self.pixmap_multiples = 2

        # position is in nanoseconds
        self.position = 0
        self.requested_time = gst.CLOCK_TIME_NONE
        self.currentlySeeking = False
        self.pressed = False
        self.pending_seek_id = None
        self.shaded_duration = gst.CLOCK_TIME_NONE
        self.max_duration = gst.CLOCK_TIME_NONE
        self.seek_delay = 80

## Zoomable interface override

    def zoomChanged(self):
        self.queue_resize()
        self.doPixmap()
        self.queue_draw()

## timeline position changed method

    def timelinePositionChanged(self, value, unused_frame=None):
        self.debug("value : %r" % value)
        ppos = max(self.nsToPixel(self.position) - 1, 0)
        self.position = value
        npos = max(self.nsToPixel(self.position) - 1, 0)
        height = self.get_allocation().height
        self.bin_window.invalidate_rect((ppos, 0, 2, height), True)
        self.bin_window.invalidate_rect((npos, 0, 2, height), True)

## gtk.Widget overrides

    def do_size_allocate(self, allocation):
        self.debug("ScaleRuler got %s", list(allocation))
        gtk.Layout.do_size_allocate(self, allocation)
        width = max(self.getMaxDurationWidth(), allocation.width)
        self.debug("Setting layout size to %d x %d",
                   width, allocation.height)
        self.set_size(width, allocation.height)
        # the size has changed, therefore we want to redo our pixmap
        self.doPixmap()

    def do_realize(self):
        gtk.Layout.do_realize(self)
        # we want to create our own pixmap here
        self.doPixmap()

    def do_expose_event(self, event):
        self.debug("exposing ScaleRuler %s", list(event.area))
        x, y, width, height = event.area
        if (x < self.pixmap_offset) or (x+width > self.pixmap_offset + self.pixmap_allocated_width):
            self.debug("exposing outside boundaries !")
            self.pixmap_offset = max(0, x + (width / 2) - (self.pixmap_allocated_width / 2))
            self.debug("offset is now %d", self.pixmap_offset)
            self.doPixmap()
            width = self.pixmap_allocated_width

        # double buffering power !
        self.bin_window.draw_drawable(
            self.style.fg_gc[gtk.STATE_NORMAL],
            self.pixmap,
            x - self.pixmap_offset, y,
            x, y, width, height)
        # draw the position
        context = self.bin_window.cairo_create()
        self.drawPosition(context, self.get_allocation())
        return False

    def do_button_press_event(self, event):
        self.debug("button pressed at x:%d", event.x)
        if self.getShadedDuration() <= 0:
            self.debug("no timeline to seek on, ignoring")
        self.pressed = True
        # seek at position
        cur = self.pixelToNs(event.x)
        self._doSeek(cur)
        return True

    def do_button_release_event(self, event):
        self.debug("button released at x:%d", event.x)
        self.pressed = False
        return False

    def do_motion_notify_event(self, event):
        self.debug("motion at event.x %d", event.x)
        if self.pressed:
            # seek at position
            cur = self.pixelToNs(event.x)
            self._doSeek(cur)
        return False

    def do_scroll_event(self, event):
        if event.direction == gtk.gdk.SCROLL_UP:
            Zoomable.zoomIn()
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            Zoomable.zoomOut()
        # TODO: seek timeline back/forward
        elif event.direction == gtk.gdk.SCROLL_LEFT:
            pass
        elif event.direction == gtk.gdk.SCROLL_RIGHT:
            pass

## Seeking methods

    def _seekTimeoutCb(self):
        self.pending_seek_id = None

        self.debug("delayed seek timeout %s %s",
                   gst.TIME_ARGS(self.seek_position), self.seek_format)

        # clamping values within acceptable range
        duration = self.getShadedDuration()
        if duration == gst.CLOCK_TIME_NONE:
            return
        if self.seek_position > duration:
            self.seek_position = duration - (1 * gst.MSECOND)
        elif self.seek_position < 0:
            self.seek_position = 0

        self.emit('seek', self.seek_position)

        return False

    def _doSeek(self, value, format=gst.FORMAT_TIME):
        if self.pending_seek_id is None:
            self.pending_seek_id = gobject.timeout_add(self.seek_delay,
                    self._seekTimeoutCb)

        self.seek_position = value
        self.seek_format = format

## Drawing methods

    def doPixmap(self):
        """ (re)create the buffered drawable for the Widget """
        # we can't create the pixmap if we're not realized
        if not self.flags() & gtk.REALIZED:
            return

        # We want to benefit from double-buffering (so as not to recreate the
        # ruler graphics all the time) yet we don't want to allocate insanely
        # big pixmaps (which would result in big memory usage, or even not being
        # able to allocate such a big pixmap).
        #
        # We therefore create a pixmap with a width of 2 times the maximum viewable
        # width (allocation.width)

        allocation = self.get_allocation()
        lwidth, lheight = self.get_size()

        self.pixmap_visible_width = allocation.width
        self.pixmap_allocated_width = self.pixmap_visible_width * self.pixmap_multiples
        allocation.width = self.pixmap_allocated_width


        if (allocation.width != self.pixmap_old_allocated_width):
            if self.pixmap:
                del self.pixmap
            self.pixmap = gtk.gdk.Pixmap(self.bin_window, allocation.width,
                                         allocation.height)
            self.pixmap_old_allocated_width = allocation.width

        context = self.pixmap.cairo_create()
        self.drawBackground(context, allocation)
        self.drawRuler(context, allocation)

    def draw(self, context):
        rect = self.get_allocation()
        self.debug("Ruler draw %s", list(rect))
        self.drawBackground(context, rect)
        self.drawRuler(context, rect)

    def setShadedDuration(self, duration):
        self.info("start/duration changed")
        self.queue_resize()

        self.shaded_duration = duration

        if duration < self.position:
            position = duration - gst.NSECOND
        else:
            position = self.position

        self._doSeek(position, gst.FORMAT_TIME)

    def getShadedDuration(self):
        return self.shaded_duration

    def getShadedDurationWidth(self):
        return self.nsToPixel(self.getShadedDuration())

    def setMaxDuration(self, duration):
        self.queue_resize()
        self.max_duration = duration

    def getMaxDuration(self):
        return self.max_duration

    def getMaxDurationWidth(self):
        return self.nsToPixel(self.getMaxDuration())

    def getPixelPosition(self):
        return 0

    def drawBackground(self, context, allocation):
        context.save()

        context.set_source_rgb(0.5, 0.5, 0.5)
        context.rectangle(0, 0, allocation.width, allocation.height)
        context.fill()
        context.stroke()

        if self.getShadedDuration() > 0:
            context.set_source_rgb(0.8, 0.8, 0.8)
            context.rectangle(0, 0, self.getShadedDurationWidth(), allocation.height)
            context.fill()
            context.stroke()

        context.restore()

    def drawRuler(self, context, allocation):
        # there are 4 lengths of tick mark:
        # full height: largest increments, 1 minute
        # 3/4 height: 10 seconds
        # 1/2 height: 1 second
        # 1/4 height: 1/10 second (might later be changed to 1 frame in
        #   project framerate)

        # At the highest level of magnification, all ticmarks are visible. At
        # the lowest, only the full height tic marks are visible. The
        # appearance of text is dependent on the spacing between tics: text
        # only appears when there is enough space between tics for it to be
        # readable.

        def textSize(text):
            return context.text_extents(text)[2:4]

        def drawTick(paintpos, height):
            context.move_to(paintpos, 0)
            context.line_to(paintpos, allocation.height * height)

        def drawText(paintpos, time, txtwidth, txtheight):
            # draw the text position
            time = time_to_string(time)
            context.move_to( paintpos - txtwidth / 2.0,
                             allocation.height - 2 )
            context.show_text( time )

        def drawTicks(interval, height):
            spacing = zoomRatio * interval
            offset = self.pixmap_offset % spacing
            paintpos = float(self.border) + 0.5
            if offset > 0:
                paintpos += spacing - offset
            if spacing >= self.min_tick_spacing:
                while paintpos < allocation.width:
                    drawTick(paintpos, height)
                    paintpos += zoomRatio * interval

        def drawTimes(interval):
            # figure out what the optimal offset is
            spacing = zoomRatio * interval
            offset = self.pixmap_offset % spacing
            seconds = self.pixelToNs(self.pixmap_offset)
            paintpos = float(self.border) + 0.5
            if offset > 0:
                seconds += self.pixelToNs(spacing - offset)
                paintpos += spacing - offset
            textwidth, textheight = textSize(time_to_string(0))
            if spacing > textwidth:
                while paintpos < allocation.width:
                    timevalue = long(seconds)
                    drawText(paintpos, timevalue, textwidth, textheight)
                    paintpos += spacing
                    seconds += long(interval * gst.SECOND)


        context.save()
        zoomRatio = self.zoomratio
        # looks better largest tick doesn't run into the text label
        interval_sizes = ((60, 0.80), (10, 0.75), (1, 0.5), (0.1, 0.25))
        for interval, height in interval_sizes:
            drawTicks(interval, height)
            drawTimes(interval)

        #set a slightly thicker line. This forces anti-aliasing, and gives the
        #a softer appearance
        context.set_line_width(1.1)
        context.set_source_rgb(0.4, 0.4, 0.4)
        context.stroke()
        context.restore()

    def drawPosition(self, context, allocation):
        if self.getShadedDuration() <= 0:
            return
        # a simple RED line will do for now
        xpos = self.nsToPixel(self.position) + self.border
        context.save()
        context.set_line_width(1.5)
        context.set_source_rgb(1.0, 0, 0)

        context.move_to(xpos, 0)
        context.line_to(xpos, allocation.height)
        context.stroke()

        context.restore()
