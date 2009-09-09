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
import cairo
from pitivi.ui.zoominterface import Zoomable
from pitivi.log.loggable import Loggable
from pitivi.utils import time_to_string, Seeker

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
    scale = [0, 0, 0, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 3600]
    subdivide = ((1, 1.0), (2, 0.5), (10, .25))

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
        self.pressed = False
        self.shaded_duration = gst.CLOCK_TIME_NONE
        self.max_duration = gst.CLOCK_TIME_NONE
        self.seeker = Seeker(80)
        self.seeker.connect('seek', self._seekerSeekCb)
        self.min_frame_spacing = 5.0
        self.frame_height = 5.0
        self.frame_rate = gst.Fraction(1/1)

## Zoomable interface override

    def zoomChanged(self):
        self.queue_resize()
        self.doPixmap()
        self.queue_draw()

## timeline position changed method

    def timelinePositionChanged(self, value, unused_frame=None):
        self.debug("value : %r", value)
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

    def _seekerSeekCb(self, seeker, position, format):
        # clamping values within acceptable range
        duration = self.getShadedDuration()
        if duration in (0, gst.CLOCK_TIME_NONE):
            return
        if position > duration:
            position = duration - (1 * gst.MSECOND)
        elif position < 0:
            position = 0

        self.emit('seek', position)

        return False

    def _doSeek(self, value, format=gst.FORMAT_TIME, on_idle=False):
        self.seeker.seek(value, format, on_idle)

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

        self.drawBackground(allocation)
        self.drawRuler(allocation)

    def setProjectFrameRate(self, rate):
        self.frame_rate = rate

        # set the lowest scale based on project framerate
        self.scale[0] = float(2 / rate)
        self.scale[1] = float(5 / rate)
        self.scale[2] = float(10 / rate)
        self.queue_resize()

    def setShadedDuration(self, duration):
        self.info("start/duration changed")
        self.queue_resize()

        self.shaded_duration = duration

        if duration < self.position:
            position = duration - gst.NSECOND
        else:
            position = self.position

        self._doSeek(position, gst.FORMAT_TIME, on_idle=True)

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

    def drawBackground(self, allocation):
        self.pixmap.draw_rectangle(
            self.style.bg_gc[gtk.STATE_NORMAL],
            True,
            0, 0,
            allocation.width, allocation.height)

        offset = int(Zoomable.nsToPixel(self.getShadedDuration())) - self.pixmap_offset
        if offset > 0:
            self.pixmap.draw_rectangle(
                self.style.bg_gc[gtk.STATE_ACTIVE],
                True,
                0, 0,
                offset,
                allocation.height)

    def drawRuler(self, allocation):
        layout = self.create_pango_layout(time_to_string(0))
        textwidth, textheight = layout.get_pixel_size()

        for scale in self.scale:
            spacing = Zoomable.zoomratio * scale
            if spacing >= textwidth * 1.5:
                break

        offset = self.pixmap_offset % spacing

        zoomRatio = self.zoomratio
        self.drawFrameBoundaries(allocation)
        self.drawTicks(allocation, offset, spacing, scale)
        self.drawTimes(allocation, offset, spacing, scale, layout)

    def drawTick(self, allocation, paintpos, height):
        paintpos = int(paintpos)
        height = allocation.height - int(allocation.height * height)
        self.pixmap.draw_line(
            self.style.fg_gc[gtk.STATE_NORMAL],
            paintpos, height, paintpos,
            allocation.height)

    def drawTicks(self, allocation, offset, spacing, scale):
        for subdivide, height in self.subdivide:
            spc = spacing / float(subdivide)
            dur = scale / float(subdivide)
            if spc < self.min_tick_spacing:
                break
            paintpos = float(self.border) + 0.5
            if offset > 0:
                paintpos += spacing - offset
            while paintpos < allocation.width:
                self.drawTick(allocation, paintpos, height)
                paintpos += spc

    def drawTimes(self, allocation, offset, spacing, scale, layout):
        # figure out what the optimal offset is
        interval = long(gst.SECOND * scale)
        seconds = self.pixelToNs(self.pixmap_offset)
        paintpos = float(self.border) + 2
        if offset > 0:
            seconds = seconds - (seconds % interval) + interval
            paintpos += spacing - offset
        shaded = self.getShadedDurationWidth()

        while paintpos < allocation.width:
            timevalue = time_to_string(long(seconds))
            layout.set_text(timevalue)
            if paintpos < shaded:
                state = gtk.STATE_ACTIVE
            else:
                state = gtk.STATE_NORMAL
            self.pixmap.draw_layout(
                self.style.fg_gc[state],
                int(paintpos), 0, layout)
            paintpos += spacing
            seconds += interval

    def drawFrameBoundaries(self, allocation):
        ns_per_frame = float(1 / self.frame_rate) * gst.SECOND
        frame_width = self.nsToPixel(ns_per_frame)
        if frame_width >= self.min_frame_spacing:
            offset = self.pixmap_offset % frame_width
            paintpos = float(self.border) + 0.5
            height = allocation.height
            y = int(height - self.frame_height)
            states = [gtk.STATE_ACTIVE, gtk.STATE_PRELIGHT]
            paintpos += frame_width - offset
            frame_num = int(paintpos // frame_width) % 2
            while paintpos < allocation.width:
                self.pixmap.draw_rectangle(
                    self.style.bg_gc[states[frame_num]],
                    True,
                    int(paintpos), y, frame_width, height)
                frame_num = (frame_num + 1) % 2
                paintpos += frame_width

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
