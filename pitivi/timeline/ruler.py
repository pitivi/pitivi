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

from gettext import gettext as _

from pitivi.utils.pipeline import Seeker
from pitivi.utils.timeline import Zoomable
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import time_to_string, beautify_length


def setCairoColor(cr, color):
    cr.set_source_rgb(float(color.red), float(color.green), float(color.blue))


class ScaleRuler(gtk.DrawingArea, Zoomable, Loggable):

    __gsignals__ = {
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
        self.ns_per_frame = float(1 / self.frame_rate) * gst.SECOND
        self.connect('draw', self.drawCb)
        self.connect('configure-event', self.configureEventCb)

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
    def configureEventCb(self, widget, event, data=None):
        self.debug("Configuring, height %d, width %d",
            widget.get_allocated_width(), widget.get_allocated_height())

        # Destroy previous buffer
        if self.pixbuf is not None:
            self.pixbuf.finish()
            self.pixbuf = None

        # Create a new buffer
        self.pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                widget.get_allocated_width(), widget.get_allocated_height())

        return False

    def drawCb(self, widget, cr):
        if self.pixbuf is not None:
            db = self.pixbuf

            # Create cairo context with double buffer as is DESTINATION
            cc = cairo.Context(db)

            #draw everything
            self.drawBackground(cc)
            self.drawRuler(cc)
            self.drawPosition(cc)
            db.flush()

            cr.set_source_surface(self.pixbuf, 0.0, 0.0)
            cr.paint()
        else:
            self.info('No buffer to paint buffer')

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
        position = self.pixelToNs(event.x + self.pixbuf_offset)
        if self.pressed:
            self.debug("motion at event.x %d", event.x)
            self._seeker.seek(position)
        else:
            human_time = beautify_length(position)
            cur_frame = int(position / self.ns_per_frame) + 1
            self.set_tooltip_text(human_time + "\n" + _("Frame #%d" % cur_frame))
        return False

    def do_scroll_event(self, event):
        if event.state & gtk.gdk.CONTROL_MASK:
            # Control + scroll = zoom
            if event.direction == gtk.gdk.SCROLL_UP:
                Zoomable.zoomIn()
                self.app.gui.timeline_ui.zoomed_fitted = False
            elif event.direction == gtk.gdk.SCROLL_DOWN:
                Zoomable.zoomOut()
                self.app.gui.timeline_ui.zoomed_fitted = False
        else:
            # No modifier key held down, just scroll
            if event.direction == gtk.gdk.SCROLL_UP or\
                event.direction == gtk.gdk.SCROLL_LEFT:
                self.app.gui.timeline_ui.scroll_left()
            elif event.direction == gtk.gdk.SCROLL_DOWN or\
                event.direction == gtk.gdk.SCROLL_RIGHT:
                self.app.gui.timeline_ui.scroll_right()

    def setProjectFrameRate(self, rate):
        """
        Set the lowest scale based on project framerate
        """
        self.frame_rate = rate
        self.ns_per_frame = float(1 / self.frame_rate) * gst.SECOND
        self.scale[0] = float(2 / rate)
        self.scale[1] = float(5 / rate)
        self.scale[2] = float(10 / rate)

## Drawing methods

    def drawBackground(self, cr):
        style = self.get_style_context()
        setCairoColor(cr, style.get_background_color(gtk.StateFlags.NORMAL))
        cr.rectangle(0, 0, cr.get_target().get_width(), cr.get_target().get_height())
        cr.fill()
        offset = int(self.nsToPixel(gst.CLOCK_TIME_NONE)) - self.pixbuf_offset
        if offset > 0:
            setCairoColor(cr, style.get_background_color(gtk.StateFlags.ACTIVE))
            cr.rectangle(0, 0, int(offset), cr.get_target().get_height())
            cr.fill()

    def drawRuler(self, cr):
        # FIXME use system defaults
        cr.set_font_face(cairo.ToyFontFace("Cantarell"))
        cr.set_font_size(13)
        textwidth = cr.text_extents(time_to_string(0))[2]

        for scale in self.scale:
            spacing = Zoomable.zoomratio * scale
            if spacing >= textwidth * 1.5:
                break

        offset = self.pixbuf_offset % spacing
        self.drawFrameBoundaries(cr)
        self.drawTicks(cr, offset, spacing, scale)
        self.drawTimes(cr, offset, spacing, scale)

    def drawTick(self, cr, paintpos, height):
        # We need to use 0.5 pixel offsets to get a sharp 1 px line in cairo
        paintpos = int(paintpos - 0.5) + 0.5
        height = int(cr.get_target().get_height() * (1 - height))
        style = self.get_style_context()
        setCairoColor(cr, style.get_color(gtk.STATE_NORMAL))
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
            style = self.get_style_context()
            setCairoColor(cr, style.get_color(state))
            x_bearing, y_bearing = cr.text_extents("0")[:2]
            cr.move_to(int(paintpos), 1 - y_bearing)
            cr.show_text(timevalue)
            paintpos += spacing
            seconds += interval

    def drawFrameBoundaries(self, cr):
        frame_width = self.nsToPixel(self.ns_per_frame)
        if frame_width >= self.min_frame_spacing:
            offset = self.pixbuf_offset % frame_width
            paintpos = -frame_width + 0.5
            height = cr.get_target().get_height()
            y = int(height - self.frame_height)
            # INSENSITIVE is a dark shade of gray, but lacks contrast
            # SELECTED will be bright blue and more visible to represent frames
            states = [gtk.StateFlags.ACTIVE, gtk.StateFlags.SELECTED]
            paintpos += frame_width - offset
            frame_num = int(paintpos // frame_width) % 2
            style = self.get_style_context()
            while paintpos < cr.get_target().get_width():
                setCairoColor(cr, style.get_background_color(states[frame_num]))
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
