# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/ruler.py
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Widget for the complex view ruler
"""

import gobject
import gtk
import gst
import cairo

from pitivi.utils.playback import Seeker
from pitivi.utils.timeline import Zoomable
from pitivi.utils.loggable import Loggable

from pitivi.utils.ui import time_to_string


def setCairoColor(cr, color):
    cr.set_source_rgb(color.red_float, color.green_float, color.blue_float)


class ScaleRuler(gtk.DrawingArea, Zoomable, Loggable):

    __gsignals__ = {
        "expose-event": "override",
        "button-press-event": "override",
        "button-release-event": "override",
        "motion-notify-event": "override",
        "scroll-event": "override",
        "seek": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                [gobject.TYPE_UINT64])
        }

    border = 0
    min_tick_spacing = 3
    scale = [0, 0, 0, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 3600]
    subdivide = ((1, 1.0), (2, 0.5), (10, .25))

    def __init__(self, instance, hadj):
        gtk.DrawingArea.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.log("Creating new ScaleRuler")
        self.app = instance
        self._seeker = Seeker()
        self.hadj = hadj
        hadj.connect("value-changed", self._hadjValueChangedCb)
        self.add_events(gtk.gdk.POINTER_MOTION_MASK |
            gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK)

        self.pixbuf = None
        # all values are in pixels
        self.pixbuf_offset = 0
        self.pixbuf_offset_painted = 0
        # This is the number of width we allocate for the pixbuf
        self.pixbuf_multiples = 4

        self.position = 0  # In nanoseconds
        self.pressed = False
        self.need_update = True
        self.min_frame_spacing = 5.0
        self.frame_height = 5.0
        self.frame_rate = gst.Fraction(1 / 1)

    def _hadjValueChangedCb(self, hadj):
        self.pixbuf_offset = self.hadj.get_value()
        self.queue_draw()

## Zoomable interface override

    def zoomChanged(self):
        self.need_update = True
        self.queue_draw()

## timeline position changed method

    def timelinePositionChanged(self, value, unused_frame=None):
        self.position = value
        self.queue_draw()

## gtk.Widget overrides

    def do_expose_event(self, event):
        self.log("exposing ScaleRuler %s", list(event.area))
        x, y, width, height = event.area

        self.repaintIfNeeded(width, height)
        # offset in pixbuf to paint
        offset_to_paint = self.pixbuf_offset - self.pixbuf_offset_painted

        self.window.draw_pixbuf(
            self.style.fg_gc[gtk.STATE_NORMAL],
            self.pixbuf,
            int(offset_to_paint), 0,
            x, y, width, height,
            gtk.gdk.RGB_DITHER_NONE)

        # draw the position
        context = self.window.cairo_create()
        self.drawPosition(context)
        return False

    def do_button_press_event(self, event):
        self.debug("button pressed at x:%d", event.x)
        self.pressed = True
        position = self.pixelToNs(event.x + self.pixbuf_offset)
        self._seeker.seek(position)
        return True

    def do_button_release_event(self, event):
        self.debug("button released at x:%d", event.x)
        self.pressed = False
        # The distinction between the ruler and timeline canvas is theoretical.
        # If the user interacts with the ruler, have the timeline steal focus
        # from other widgets. This reactivates keyboard shortcuts for playback.
        timeline = self.app.gui.timeline_ui
        timeline._canvas.grab_focus(timeline._root_item)
        return False

    def do_motion_notify_event(self, event):
        if self.pressed:
            self.debug("motion at event.x %d", event.x)
            position = self.pixelToNs(event.x + self.pixbuf_offset)
            self._seeker.seek(position)
        return False

    def do_scroll_event(self, event):
        if event.state & gtk.gdk.CONTROL_MASK:
            # Control + scroll = zoom
            if event.direction == gtk.gdk.SCROLL_UP:
                Zoomable.zoomIn()
                self.log("Setting 'zoomed_fitted' to False")
                self.app.gui.zoomed_fitted = False
            elif event.direction == gtk.gdk.SCROLL_DOWN:
                Zoomable.zoomOut()
                self.log("Setting 'zoomed_fitted' to False")
                self.app.gui.zoomed_fitted = False
        else:
            # No modifier key held down, just scroll
            if event.direction == gtk.gdk.SCROLL_UP or\
                event.direction == gtk.gdk.SCROLL_LEFT:
                self.app.gui.timeline_ui.scroll_left()
            elif event.direction == gtk.gdk.SCROLL_DOWN or\
                event.direction == gtk.gdk.SCROLL_RIGHT:
                self.app.gui.timeline_ui.scroll_right()

## Drawing methods

    def repaintIfNeeded(self, width, height):
        """ (re)create the buffered drawable for the Widget """
        # we can't create the pixbuf if we're not realized
        if self.pixbuf:
            # The new offset starts before painted in pixbuf
            if (self.pixbuf_offset < self.pixbuf_offset_painted):
                self.need_update = True
            # The new offsets end after pixbuf we have
            if (self.pixbuf_offset + width > self.pixbuf_offset_painted + self.pixbuf.get_width()):
                self.need_update = True
        else:
            self.need_update = True

        if self.need_update:
            self.debug("Ruller is repainted")
            # We create biger pixbuf to not repaint ruller every time
            if self.pixbuf:
                del self.pixbuf
            #Create image surface
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width * self.pixbuf_multiples, height)
            self.pixbuf_offset_painted = self.pixbuf_offset
            cr = cairo.Context(surface)
            self.drawBackground(cr)
            self.drawRuler(cr)
            cr = None
            self.pixbuf = gtk.gdk.pixbuf_new_from_data(surface.get_data(),
            gtk.gdk.COLORSPACE_RGB, True, 8, surface.get_width(),
            surface.get_height(), 4 * surface.get_width())
            surface = None
            self.need_update = False

    def setProjectFrameRate(self, rate):
        """
        Set the lowest scale based on project framerate
        """
        self.frame_rate = rate
        self.scale[0] = float(2 / rate)
        self.scale[1] = float(5 / rate)
        self.scale[2] = float(10 / rate)

    def drawBackground(self, cr):
        setCairoColor(cr, self.style.bg[gtk.STATE_NORMAL])
        cr.rectangle(0, 0, cr.get_target().get_width(), cr.get_target().get_height())
        cr.fill()
        offset = int(self.nsToPixel(gst.CLOCK_TIME_NONE)) - self.pixbuf_offset
        if offset > 0:
            setCairoColor(cr, self.style.bg[gtk.STATE_ACTIVE])
            cr.rectangle(0, 0, int(offset), cr.get_target().get_height())
            cr.fill()

    def drawRuler(self, cr):
        cr.set_font_face(cairo.ToyFontFace("Cantarell"))
        cr.set_font_size(15)
        textwidth = cr.text_extents(time_to_string(0))[2]

        for scale in self.scale:
            spacing = Zoomable.zoomratio * scale
            if spacing >= textwidth * 1.5:
                break

        offset = self.pixbuf_offset % spacing
        zoomRatio = self.zoomratio
        self.drawFrameBoundaries(cr)
        self.drawTicks(cr, offset, spacing, scale)
        self.drawTimes(cr, offset, spacing, scale)

    def drawTick(self, cr, paintpos, height):
        #Line in midle to get 1 pixel width
        paintpos = int(paintpos - 0.5) + 0.5
        height = int(cr.get_target().get_height() * (1 - height))
        setCairoColor(cr, self.style.fg[gtk.STATE_NORMAL])
        cr.set_line_width(1)
        cr.move_to(paintpos, height)
        cr.line_to(paintpos, cr.get_target().get_height())
        cr.close_path()
        cr.stroke()

    def drawTicks(self, cr, offset, spacing, scale):
        for subdivide, height in self.subdivide:
            spc = spacing / float(subdivide)
            if spc < self.min_tick_spacing:
                break
            paintpos = -spacing + 0.5
            paintpos += spacing - offset
            while paintpos < cr.get_target().get_width():
                self.drawTick(cr, paintpos, height)
                paintpos += spc

    def drawTimes(self, cr, offset, spacing, scale):
        # figure out what the optimal offset is
        interval = long(gst.SECOND * scale)
        seconds = self.pixelToNs(self.pixbuf_offset)
        paintpos = float(self.border) + 2
        if offset > 0:
            seconds = seconds - (seconds % interval) + interval
            paintpos += spacing - offset

        while paintpos < cr.get_target().get_width():
            if paintpos < self.nsToPixel(gst.CLOCK_TIME_NONE):
                state = gtk.STATE_ACTIVE
            else:
                state = gtk.STATE_NORMAL
            timevalue = time_to_string(long(seconds))
            setCairoColor(cr, self.style.fg[state])
            x_bearing, y_bearing = cr.text_extents("0")[:2]
            cr.move_to(int(paintpos), 1 - y_bearing)
            cr.show_text(timevalue)
            paintpos += spacing
            seconds += interval

    def drawFrameBoundaries(self, cr):
        ns_per_frame = float(1 / self.frame_rate) * gst.SECOND
        frame_width = self.nsToPixel(ns_per_frame)
        if frame_width >= self.min_frame_spacing:
            offset = self.pixbuf_offset % frame_width
            paintpos = -frame_width + 0.5
            height = cr.get_target().get_height()
            y = int(height - self.frame_height)
            states = [gtk.STATE_ACTIVE, gtk.STATE_PRELIGHT]
            paintpos += frame_width - offset
            frame_num = int(paintpos // frame_width) % 2
            while paintpos < cr.get_target().get_width():
                setCairoColor(cr, self.style.bg[states[frame_num]])
                cr.rectangle(paintpos, y, frame_width, height)
                cr.fill()
                frame_num = (frame_num + 1) % 2
                paintpos += frame_width

    def drawPosition(self, context):
        # a simple RED line will do for now
        xpos = self.nsToPixel(self.position) + self.border - self.pixbuf_offset
        context.save()
        context.set_line_width(1.5)
        context.set_source_rgb(1.0, 0, 0)
        context.move_to(xpos, 0)
        context.line_to(xpos, context.get_target().get_height())
        context.stroke()
        context.restore()
