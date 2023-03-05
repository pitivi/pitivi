# -*- coding: utf-8 -*-
# Pitivi video editor
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
from gettext import gettext as _

import cairo
from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import beautify_length
from pitivi.utils.ui import FONT_SCALING_FACTOR
from pitivi.utils.ui import gtk_style_context_get_color
from pitivi.utils.ui import NORMAL_FONT
from pitivi.utils.ui import PLAYHEAD_COLOR
from pitivi.utils.ui import PLAYHEAD_WIDTH
from pitivi.utils.ui import set_cairo_color
from pitivi.utils.ui import time_to_string


# Tuples of:
# - an interval duration in seconds for which a timestamp will be displayed
# - how the ticks should be displayed for this interval:
#   (tick interval duration in seconds, height ratio) tuples.
SCALES = (
    (0.1, ((0.1, 1.0), (0.05, .5), (0.01, .25))),
    (0.2, ((0.2, 1.0), (0.1, .5), (0.05, .25))),
    (0.5, ((0.5, 1.0), (0.1, .25))),

    # 1 second.
    (1, ((1, 1.0), (0.5, .5), (0.1, .25))),
    (2, ((2, 1.0), (1, .5), (0.5, .25))),
    (5, ((5, 1.0), (1, .25))),
    (10, ((10, 1.0), (5, .5), (1, .25))),
    (20, ((20, 1.0), (10, .5), (1, .25))),
    (30, ((30, 1.0), (10, .5), (1, .25))),

    # 1 minute.
    (60, ((60, 1.0), (30, .5), (15, .25))),
    # 2 minutes.
    (120, ((120, 1.0), (60, .5), (30, .25))),
    # 5 minutes.
    (300, ((300, 1.0), (60, .25))),
    # 10 minutes.
    (600, ((600, 1.0), (300, .5), (60, .25))),
    # 30 minutes.
    (1800, ((1800, 1.0), (900, .5), (450, .25))),

    # 1 hour.
    (3600, ((3600, 1.0), (1800, .75), (900, .5))),
)

# The minimum distance between adjacent ticks.
MIN_TICK_SPACING_PIXELS = 6

# For displaying the times a bit to the right.
TIMES_LEFT_MARGIN_PIXELS = 3

# The minimum width for a frame to be displayed.
FRAME_MIN_WIDTH_PIXELS = 5
# How short it should be.
FRAME_HEIGHT_PIXELS = 5

NORMAL_FONT_SIZE = FONT_SCALING_FACTOR * 13
SMALL_FONT_SIZE = FONT_SCALING_FACTOR * 11


class ScaleRuler(Gtk.DrawingArea, Loggable):
    """Widget for displaying the ruler.

    Displays a series of consecutive intervals. For each interval its beginning
    time is shown. If zoomed in enough, shows the frames in alternate colors.

    Attributes:
        zoom (pitivi.utils.timeline.Zoomable): Zoom controller.
        settings (pitivi.settings.GlobalSettings): The settings of the app.
        style_context (Gtk.StyleContext): The style context for drawing.
        _pipeline (pitivi.utils.pipeline.Pipeline): The pipeline of the project.
    """

    def __init__(self, zoom, settings, style_context):
        Gtk.DrawingArea.__init__(self)
        Loggable.__init__(self)
        self.log("Creating new ScaleRuler")

        self.zoom = zoom
        self.settings = settings
        self.style_context = style_context
        self._pipeline = None
        self.ges_timeline = None

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.SCROLL_MASK)

        self.pixbuf = None

        # all values are in pixels
        self.pixbuf_offset = 0
        self.pixbuf_offset_painted = 0

        self.position = 0  # In nanoseconds

        self._scales = [(interval, list(reversed(ticks))) for interval, ticks in SCALES]

        # Update colors when theme or color preferences change.
        Gtk.Settings.get_default().connect("notify::gtk-theme-name", self._update_colors_cb)
        Gtk.Settings.get_default().connect("notify::gtk-application-prefer-dark-theme", self._update_colors_cb)

    def set_pipeline(self, pipeline):
        self._pipeline = pipeline
        self.ges_timeline = pipeline.props.timeline
        self._pipeline.connect("position", self._pipeline_position_cb)

    def _pipeline_position_cb(self, unused_pipeline, position):
        self.position = position
        self.queue_draw()

    def _set_colors(self):
        # pylint: disable=attribute-defined-outside-init
        context = self.get_style_context()
        color_normal = gtk_style_context_get_color(context, Gtk.StateFlags.NORMAL)
        color_insensitive = gtk_style_context_get_color(context, Gtk.StateFlags.BACKDROP)
        self._color_normal = color_normal
        self._color_dimmed = Gdk.RGBA(
            *[(x * 3 + y * 2) / 5
              for x, y in ((color_normal.red, color_insensitive.red),
                           (color_normal.green, color_insensitive.green),
                           (color_normal.blue, color_insensitive.blue))])

        self._color_subtle = Gdk.RGBA(
            *[(x * 3 + y * 2) / 10
              for x, y in ((color_normal.red, color_insensitive.red),
                           (color_normal.green, color_insensitive.green),
                           (color_normal.blue, color_insensitive.blue))])

        # Two colors with high contrast.
        self._color_frame = gtk_style_context_get_color(context, Gtk.StateFlags.LINK)

    def _update_colors_cb(self, settings, gparams):
        self._set_colors()

# Gtk.Widget overrides

    def do_configure_event(self, unused_event):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        self.debug("Configuring, height %d, width %d", width, height)

        # Destroy previous buffer
        if self.pixbuf is not None:
            self.pixbuf.finish()
            self.pixbuf = None

        # Create a new buffer
        self.pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        self._set_colors()
        return False

    def do_draw(self, context):
        if self.pixbuf is None:
            self.info("No buffer to paint")
            return False

        pixbuf = self.pixbuf

        # Draw on a temporary context and then copy everything.
        drawing_context = cairo.Context(pixbuf)
        self.draw_background(drawing_context)
        self.draw_ruler(drawing_context)
        self.draw_position(drawing_context)
        pixbuf.flush()

        context.set_source_surface(self.pixbuf, 0.0, 0.0)
        context.paint()

        return False

    def do_button_press_event(self, event):
        if not self._pipeline:
            return False

        button = event.button
        if button == 3 or (button == 1 and self.settings.leftClickAlsoSeeks):
            self.debug("button pressed at x:%d", event.x)
            position = self.pixel_to_ns(event.x + self.pixbuf_offset)
            self._pipeline.simple_seek(position)
            self.__set_tooltip_text(position, True)
        return False

    def do_button_release_event(self, event):
        button = event.button
        if button == 3 or (button == 1 and self.settings.leftClickAlsoSeeks):
            self.debug("button released at x:%d", event.x)
            position = self.pixel_to_ns(event.x + self.pixbuf_offset)
            self.__set_tooltip_text(position)
        return False

    def do_motion_notify_event(self, event):
        if not self._pipeline:
            return False

        position = self.pixel_to_ns(event.x + self.pixbuf_offset)

        seek_mask = Gdk.ModifierType.BUTTON3_MASK
        if self.settings.leftClickAlsoSeeks:
            seek_mask |= Gdk.ModifierType.BUTTON1_MASK

        seeking = event.state & seek_mask
        if seeking:
            self.debug("motion at event.x %d", event.x)
            self._pipeline.simple_seek(position)
        self.__set_tooltip_text(position, seeking)

        return False

    def __set_tooltip_text(self, position, seeking=False):
        """Updates the tooltip."""
        position = max(0, position)
        if seeking:
            timeline_duration = self.ges_timeline.props.duration
            position = min(position, timeline_duration)
        human_time = beautify_length(position)
        cur_frame = self.ges_timeline.get_frame_at(position) + 1
        self.set_tooltip_text(human_time + "\n" + _("Frame #%d") % cur_frame)

# Drawing methods

    def draw_background(self, context):
        width = context.get_target().get_width()
        height = context.get_target().get_height()
        Gtk.render_background(self.style_context, context, 0, 0, width, height)

    def draw_ruler(self, context):
        context.set_font_face(NORMAL_FONT)
        context.set_font_size(NORMAL_FONT_SIZE)

        spacing, interval_seconds, ticks = self._get_spacing(context)
        offset = self.pixbuf_offset % spacing
        self.draw_frame_boundaries(context)
        self.draw_ticks(context, offset, spacing, interval_seconds, ticks)
        self.draw_times(context, offset, spacing, interval_seconds)

    def _get_spacing(self, context):
        # The longest timestamp we display is 0:00:00 because
        # when we display millis, they are displayed by themselves.
        min_interval_width = context.text_extents("0:00:00")[2] * 1.3
        zoomratio = self.zoom.zoomratio
        for interval_seconds, ticks in self._scales:
            interval_width = interval_seconds * zoomratio
            if interval_width >= min_interval_width:
                return interval_width, interval_seconds, ticks
        raise Exception(
            "Failed to find an interval size for textwidth:%s, zoomratio:%s" %
            (min_interval_width, zoomratio))

    def draw_ticks(self, context, offset, spacing, interval_seconds, ticks):
        for tick_interval, height_ratio in ticks:
            count_per_interval = interval_seconds / tick_interval
            space = spacing / count_per_interval
            if space < MIN_TICK_SPACING_PIXELS:
                continue
            paintpos = 0.5 - offset

            color = (self._color_normal if height_ratio == 1
                     else self._color_subtle)

            set_cairo_color(context, color)
            while paintpos < context.get_target().get_width():
                self._draw_tick(context, paintpos, height_ratio)
                paintpos += space

    def _draw_tick(self, context, paintpos, height_ratio):
        # We need to use 0.5 pixel offsets to get a sharp 1 px line in cairo
        paintpos = int(paintpos - 0.5) + 0.5
        target_height = context.get_target().get_height()
        y = int(target_height * (1 - height_ratio))
        context.set_line_width(1)
        context.move_to(paintpos, y)
        context.line_to(paintpos, target_height)
        context.close_path()
        context.stroke()

    def draw_times(self, context, offset, spacing, interval_seconds):
        # figure out what the optimal offset is
        interval = int(Gst.SECOND * interval_seconds)
        current_time = self.zoom.pixel_to_ns(self.pixbuf_offset)
        paintpos = TIMES_LEFT_MARGIN_PIXELS
        if offset > 0:
            current_time = current_time - (current_time % interval) + interval
            paintpos += spacing - offset

        set_cairo_color(context, self._color_normal)
        y_bearing = context.text_extents("0")[1]

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
            millis = current_time % Gst.SECOND > 0
            self._draw_time(context, current, previous, millis)
            previous = current
            paintpos += spacing
            current_time += interval

    def _draw_time(self, context, current, previous, millis):
        hour = int(current[0])
        for index, (element, previous_element) in enumerate(zip(current, previous)):
            if index <= 1 and not hour:
                # Don't draw hour if 0.
                continue
            if millis:
                # Draw only the millis.
                if index < 5:
                    continue
            else:
                # Don't draw the millis.
                if index == 5:
                    break
            if element == previous_element:
                color = self._color_dimmed
            else:
                color = self._color_normal
            set_cairo_color(context, color)
            # Display the millis with a smaller font.
            small = index >= 5
            if small:
                context.set_font_size(SMALL_FONT_SIZE)
            context.show_text(element)
            if small:
                context.set_font_size(NORMAL_FONT_SIZE)

    def draw_frame_boundaries(self, context):
        """Draws the alternating rectangles that represent the project frames.

        These are drawn only at high zoom levels.

        These are based on the project's framerate settings, not the actual
        frames on the assets.
        """
        if not self.ges_timeline:
            # Timeline not set yet
            return

        frame_width = self.zoom.ns_to_pixel(self.ges_timeline.get_frame_time(1))
        if frame_width < FRAME_MIN_WIDTH_PIXELS:
            return

        offset = self.pixbuf_offset % frame_width
        height = context.get_target().get_height()
        y = int(height - FRAME_HEIGHT_PIXELS)

        frame_num = self.ges_timeline.get_frame_at(self.zoom.pixel_to_ns(self.pixbuf_offset))
        paintpos = self.pixbuf_offset - offset
        max_pos = context.get_target().get_width() + self.pixbuf_offset
        while paintpos < max_pos:
            paintpos = self.zoom.ns_to_pixel(self.ges_timeline.get_frame_time(frame_num))
            if frame_num % 2:
                set_cairo_color(context, self._color_frame)
                context.rectangle(
                    0.5 + paintpos - self.pixbuf_offset, y, frame_width, height)
                context.fill()
            frame_num += 1

    def draw_position(self, context):
        """Draws the top part of the playhead.

        This should be in sync with the playhead drawn by the timeline.
        See Timeline.__draw_playhead().
        """
        height = self.pixbuf.get_height()

        semi_width = 4
        semi_height = int(semi_width * 1.61803)
        y = int(3 * height / 4)

        # Add 0.5 so that the line center is at the middle of the pixel,
        # without this the line appears blurry.
        xpos = self.zoom.ns_to_pixel(self.position) - self.pixbuf_offset + 0.5
        set_cairo_color(context, PLAYHEAD_COLOR)

        context.set_line_width(PLAYHEAD_WIDTH)
        context.move_to(xpos, y)
        context.line_to(xpos, height)
        context.stroke()

        context.set_line_width(PLAYHEAD_WIDTH * 2)
        context.move_to(xpos, y)
        context.line_to(xpos + semi_width, y - semi_height)
        context.line_to(xpos, y - semi_height * 2)
        context.line_to(xpos - semi_width, y - semi_height)
        context.close_path()
        context.stroke()


class TimelineScaleRuler(ScaleRuler, Zoomable):
    """Widget for displaying a ruler which is connected to a timeline.

    Attributes:
        timeline_container (TimelineContainer): The timeline container for
            handling scroll events.
    """

    def __init__(self, timeline_container):
        Zoomable.__init__(self)
        ScaleRuler.__init__(self, self, self.app.settings, self.app.gui.get_style_context())
        self.log("Creating new TimelineScaleRuler")

        self.timeline_container = timeline_container

        timeline_container.timeline.hadj.connect("value-changed", self._hadj_value_changed_cb)

    def _hadj_value_changed_cb(self, hadj):
        """Handles the adjustment value change."""
        self.pixbuf_offset = hadj.get_value()
        self.queue_draw()

# Zoomable interface override

    def zoom_changed(self):
        self.queue_draw()

# Gtk.Widget overrides

    def do_scroll_event(self, event):
        self.timeline_container.timeline.do_scroll_event(event)
