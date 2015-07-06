# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/timeline/ruler.py
#
# Copyright (c) 2006, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2014, Alex Băluț <alexandru.balut@gmail.com>
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

import cairo

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import GLib
from gi.repository import GObject

from gettext import gettext as _

from pitivi.utils.pipeline import Seeker
from pitivi.utils.timeline import Zoomable
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import NORMAL_FONT, PLAYHEAD_WIDTH, set_cairo_color, time_to_string, beautify_length


HEIGHT = 25

# A series of valid interval lengths in seconds.
SCALES = (0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 3600)

# The minimum distance between adjacent ticks.
MIN_TICK_SPACING_PIXELS = 3
# (count per interval, height ratio) tuples determining how the ticks appear.
TICK_TYPES = ((1, 1.0), (2, 0.5), (10, .25))

# For displaying the times a bit to the right.
TIMES_LEFT_MARGIN_PIXELS = 3

# The minimum width for a frame to be displayed.
FRAME_MIN_WIDTH_PIXELS = 5
# How short it should be.
FRAME_HEIGHT_PIXELS = 5

NORMAL_FONT_SIZE = 13
SMALL_FONT_SIZE = 11


class ScaleRuler(Gtk.DrawingArea, Zoomable, Loggable):

    """
    Widget for displaying the ruler.

    Displays a series of consecutive intervals. For each interval its beginning
    time is shown. If zoomed in enough, shows the frames in alternate colors.
    """

    __gsignals__ = {
        "button-press-event": "override",
        "button-release-event": "override",
        "motion-notify-event": "override",
        "scroll-event": "override",
        "seek": (GObject.SignalFlags.RUN_LAST, None,
                 [GObject.TYPE_UINT64])
    }

    def __init__(self, timeline, hadj):
        Gtk.DrawingArea.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.log("Creating new ScaleRuler")

        # Allows stealing focus from other GTK widgets, prevent accidents:
        self.props.can_focus = True
        self.connect("focus-in-event", self._focusInCb)
        self.connect("focus-out-event", self._focusOutCb)

        self.timeline = timeline
        self._background_color = timeline.get_style_context().lookup_color(
            'theme_bg_color')[1]
        self._seeker = Seeker()
        self.hadj = hadj
        hadj.connect("value-changed", self._hadjValueChangedCb)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.SCROLL_MASK)

        self.pixbuf = None

        # all values are in pixels
        self.pixbuf_offset = 0
        self.pixbuf_offset_painted = 0
        # This is the number of width we allocate for the pixbuf
        self.pixbuf_multiples = 4

        self.position = 0  # In nanoseconds
        self.pressed = False
        self.frame_rate = Gst.Fraction(1 / 1)
        self.ns_per_frame = float(1 / self.frame_rate) * Gst.SECOND
        self.connect('draw', self.drawCb)
        self.connect('configure-event', self.configureEventCb)
        self.callback_id = None
        self.set_size_request(0, HEIGHT)

        style = self.get_style_context()
        color_normal = style.get_color(Gtk.StateFlags.NORMAL)
        color_insensitive = style.get_color(Gtk.StateFlags.INSENSITIVE)
        self._color_normal = color_normal
        self._color_dimmed = Gdk.RGBA(
            *[(x * 3 + y * 2) / 5
              for x, y in ((color_normal.red, color_insensitive.red),
                           (color_normal.green, color_insensitive.green),
                           (color_normal.blue, color_insensitive.blue))])

        self.scales = SCALES

    def _focusInCb(self, unused_widget, unused_arg):
        self.log("Ruler has grabbed focus")
        self.timeline.setActionsSensitivity(True)

    def _focusOutCb(self, unused_widget, unused_arg):
        self.log("Ruler has lost focus")
        self.timeline.setActionsSensitivity(False)

    def _hadjValueChangedCb(self, unused_arg):
        self.pixbuf_offset = self.hadj.get_value()
        self.queue_draw()

# Zoomable interface override

    def zoomChanged(self):
        self.queue_draw()

# Timeline position changed method

    def setPipeline(self, pipeline):
        pipeline.connect('position', self.timelinePositionCb)

    def timelinePositionCb(self, unused_pipeline, position):
        self.position = position
        self.queue_draw()

# Gtk.Widget overrides
    def configureEventCb(self, widget, unused_event, unused_data=None):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        self.debug("Configuring, height %d, width %d", width, height)

        # Destroy previous buffer
        if self.pixbuf is not None:
            self.pixbuf.finish()
            self.pixbuf = None

        # Create a new buffer
        self.pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        return False

    def drawCb(self, unused_widget, context):
        if self.pixbuf is None:
            self.info('No buffer to paint')
            return False

        pixbuf = self.pixbuf

        # Draw on a temporary context and then copy everything.
        drawing_context = cairo.Context(pixbuf)
        self.drawBackground(drawing_context)
        self.drawRuler(drawing_context)
        self.drawPosition(drawing_context)
        pixbuf.flush()

        context.set_source_surface(self.pixbuf, 0.0, 0.0)
        context.paint()

        return False

    def do_button_press_event(self, event):
        self.debug("button pressed at x:%d", event.x)
        self.pressed = True
        position = self.pixelToNs(event.x + self.pixbuf_offset)
        self._seeker.seek(position, on_idle=True)
        return True

    def do_button_release_event(self, event):
        self.debug("button released at x:%d", event.x)
        self.grab_focus()  # Prevent other widgets from being confused
        self.pressed = False
        return False

    def do_motion_notify_event(self, event):
        position = self.pixelToNs(event.x + self.pixbuf_offset)
        if self.pressed:
            self.debug("motion at event.x %d", event.x)
            self._seeker.seek(position, on_idle=True)

        human_time = beautify_length(position)
        cur_frame = int(position / self.ns_per_frame) + 1
        self.set_tooltip_text(human_time + "\n" + _("Frame #%d" % cur_frame))
        return False

    def do_scroll_event(self, event):
        if event.scroll.state & Gdk.ModifierType.CONTROL_MASK:
            # Control + scroll = zoom
            if event.scroll.direction == Gdk.ScrollDirection.UP:
                Zoomable.zoomIn()
            elif event.scroll.direction == Gdk.ScrollDirection.DOWN:
                Zoomable.zoomOut()
        else:
            # No modifier key held down, just scroll
            if event.scroll.direction in (Gdk.ScrollDirection.UP,
                                          Gdk.ScrollDirection.LEFT):
                self.timeline.scroll_left()
            elif event.scroll.direction in (Gdk.ScrollDirection.DOWN,
                                            Gdk.ScrollDirection.RIGHT):
                self.timeline.scroll_right()

    def setProjectFrameRate(self, rate):
        """
        Set the lowest scale based on project framerate
        """
        self.frame_rate = rate
        self.ns_per_frame = float(1 / self.frame_rate) * Gst.SECOND
        self.scales = (float(2 / rate), float(
            5 / rate), float(10 / rate)) + SCALES

# Drawing methods

    def drawBackground(self, context):
        style = self.get_style_context()
        set_cairo_color(context, self._background_color)
        width = context.get_target().get_width()
        height = context.get_target().get_height()
        context.rectangle(0, 0, width, height)
        context.fill()
        offset = int(self.nsToPixel(Gst.CLOCK_TIME_NONE)) - self.pixbuf_offset
        if offset > 0:
            set_cairo_color(
                context, style.get_background_color(Gtk.StateFlags.ACTIVE))
            context.rectangle(
                0, 0, int(offset), height)
            context.fill()

    def drawRuler(self, context):
        context.set_font_face(NORMAL_FONT)
        context.set_font_size(NORMAL_FONT_SIZE)

        spacing, scale = self._getSpacing(context)
        offset = self.pixbuf_offset % spacing
        self.drawFrameBoundaries(context)
        self.drawTicks(context, offset, spacing)
        self.drawTimes(context, offset, spacing, scale)

    def _getSpacing(self, context):
        textwidth = context.text_extents(time_to_string(0))[2]
        zoom = Zoomable.zoomratio
        for scale in self.scales:
            spacing = scale * zoom
            if spacing >= textwidth * 1.5:
                return spacing, scale
        raise Exception(
            "Failed to find an interval size for textwidth:%s, zoomratio:%s" %
            (textwidth, Zoomable.zoomratio))

    def drawTicks(self, context, offset, spacing):
        for count_per_interval, height_ratio in TICK_TYPES:
            space = float(spacing) / count_per_interval
            if space < MIN_TICK_SPACING_PIXELS:
                break
            paintpos = 0.5 - offset
            set_cairo_color(context, self._color_normal)
            while paintpos < context.get_target().get_width():
                self._drawTick(context, paintpos, height_ratio)
                paintpos += space

    def _drawTick(self, context, paintpos, height_ratio):
        # We need to use 0.5 pixel offsets to get a sharp 1 px line in cairo
        paintpos = int(paintpos - 0.5) + 0.5
        target_height = context.get_target().get_height()
        y = int(target_height * (1 - height_ratio))
        context.set_line_width(1)
        context.move_to(paintpos, y)
        context.line_to(paintpos, target_height)
        context.close_path()
        context.stroke()

    def drawTimes(self, context, offset, spacing, scale):
        # figure out what the optimal offset is
        interval = int(Gst.SECOND * scale)
        current_time = self.pixelToNs(self.pixbuf_offset)
        paintpos = TIMES_LEFT_MARGIN_PIXELS
        if offset > 0:
            current_time = current_time - (current_time % interval) + interval
            paintpos += spacing - offset

        state = Gtk.StateFlags.NORMAL
        style = self.get_style_context()
        set_cairo_color(context, style.get_color(state))
        y_bearing = context.text_extents("0")[1]
        millis = scale < 1

        def split(x):
            # Seven elements: h : mm : ss . mmm
            # Using negative indices because the first element (hour)
            # can have a variable length.
            return x[:-10], x[-10], x[-9:-7], x[-7], x[-6:-4], x[-4], x[-3:]

        previous = split(time_to_string(max(0, current_time - interval)))
        width = context.get_target().get_width()
        while paintpos < width:
            context.move_to(int(paintpos), 1 - y_bearing)
            current = split(time_to_string(int(current_time)))
            self._drawTime(context, current, previous, millis)
            previous = current
            paintpos += spacing
            current_time += interval

    def _drawTime(self, context, current, previous, millis):
        hour = int(current[0])
        for index, (element, previous_element) in enumerate(zip(current, previous)):
            if index <= 1 and not hour:
                continue
            if index >= 5 and not millis:
                break
            if element == previous_element:
                color = self._color_dimmed
            else:
                color = self._color_normal
            set_cairo_color(context, color)
            # Display the millis with a smaller font
            small = index >= 5
            if small:
                context.set_font_size(SMALL_FONT_SIZE)
            context.show_text(element)
            if small:
                context.set_font_size(NORMAL_FONT_SIZE)

    def drawFrameBoundaries(self, context):
        """
        Draw the alternating rectangles that represent the project frames at
        high zoom levels. These are based on the framerate set in the project
        settings, not the actual frames on a video codec level.
        """
        frame_width = self.nsToPixel(self.ns_per_frame)
        if not frame_width >= FRAME_MIN_WIDTH_PIXELS:
            return

        offset = self.pixbuf_offset % frame_width
        height = context.get_target().get_height()
        y = int(height - FRAME_HEIGHT_PIXELS)
        # INSENSITIVE is a dark shade of gray, but lacks contrast
        # SELECTED will be bright blue and more visible to represent frames
        style = self.get_style_context()
        states = [style.get_background_color(Gtk.StateFlags.ACTIVE),
                  style.get_background_color(Gtk.StateFlags.SELECTED)]

        frame_num = int(
            self.pixelToNs(self.pixbuf_offset) * float(self.frame_rate) / Gst.SECOND)
        paintpos = self.pixbuf_offset - offset
        max_pos = context.get_target().get_width() + self.pixbuf_offset
        while paintpos < max_pos:
            paintpos = self.nsToPixel(
                1 / float(self.frame_rate) * Gst.SECOND * frame_num)
            set_cairo_color(context, states[(frame_num + 1) % 2])
            context.rectangle(
                0.5 + paintpos - self.pixbuf_offset, y, frame_width, height)
            context.fill()
            frame_num += 1

    def drawPosition(self, context):
        # Add 0.5 so that the line center is at the middle of the pixel,
        # without this the line appears blurry.
        xpos = self.nsToPixel(self.position) - self.pixbuf_offset + 0.5
        context.set_line_width(PLAYHEAD_WIDTH + 2)
        set_cairo_color(context, (255, 0, 0))
        context.move_to(xpos, 0)
        context.line_to(xpos, context.get_target().get_height())
        context.stroke()
