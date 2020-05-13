# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Michael Westburg <michael.westberg@huskers.unl.edu>
# Copyright (c) 2020, Matt Lowe <mattlowe13@huskers.unl.edu>
# Copyright (c) 2020, Aaron Byington <aabyington4@gmail.com>
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
import cairo
from gi.repository import Gtk

from pitivi.utils.ui import gtk_style_context_get_color
from pitivi.utils.ui import NORMAL_FONT
from pitivi.utils.ui import set_cairo_color
from pitivi.utils.ui import SPACING

# The width for the peak meter
PEAK_METER_WIDTH = 8
# The maximum height for the peak meter
PEAK_METER_MAX_HEIGHT = 200
# The minimum height for the peak meter
PEAK_METER_MIN_HEIGHT = 80
# The number of cells on the peak meter bar
CELL_COUNT = 20
# The minimum peak value represented by the peak meter
MIN_PEAK = -60
# The font size for the scale
FONT_SIZE = 13
# The number of values shown on the scale
SCALE_COUNT = 5


class PeakMeterWidget(Gtk.DrawingArea):
    """Base class for peak meter components."""

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.pixel_buffer = None

        style_context = self.get_style_context()
        style_context.add_class("background")
        self.connect("size-allocate", self.__size_allocate_cb)

    def __size_allocate_cb(self, unused_event, allocation):
        if self.pixel_buffer is not None:
            self.pixel_buffer.finish()
            self.pixel_buffer = None

        self.pixel_buffer = cairo.ImageSurface(cairo.FORMAT_ARGB32, allocation.width, allocation.height)

    def draw_background(self, context, width, height):
        style_context = self.get_style_context()
        Gtk.render_background(style_context, context, 0, 0, width, height)


class PeakMeter(PeakMeterWidget):
    """A meter that shows peak values."""

    def __init__(self):
        PeakMeterWidget.__init__(self)
        self.peak = MIN_PEAK
        self.background_gradient = None
        self.peak_gradient = None
        width = PEAK_METER_WIDTH
        self.set_property("width_request", width)

        style_context = self.get_style_context()
        style_context.add_class("frame")

        self.connect("size-allocate", self.__size_allocate_cb)

    def do_draw(self, context):
        if self.pixel_buffer is None:
            return

        width = self.get_allocated_width()
        height = self.get_allocated_height()
        pixel_buffer = self.pixel_buffer

        drawing_context = cairo.Context(pixel_buffer)
        self.draw_background(drawing_context, width, height)
        self.__draw_bar(drawing_context, width, height)
        self.__draw_cells(drawing_context, width, height)
        self.__draw_frame(drawing_context, width, height)
        pixel_buffer.flush()

        context.set_source_surface(pixel_buffer, 0.0, 0.0)
        context.paint()

    def __size_allocate_cb(self, unused_event, allocation):
        self.__set_gradients(allocation.width, allocation.height)

    def __draw_bar(self, context, width, height):
        peak_height = self.__normalize_peak(height)

        context.set_source(self.background_gradient)
        context.rectangle(0, 0, width, height)
        context.fill()

        context.set_source(self.peak_gradient)
        context.rectangle(0, height - peak_height + 0, width, peak_height)
        context.fill()

    def __draw_cells(self, context, width, height):
        context.set_source_rgba(0.0, 0.0, 0.0, 0.5)
        context.set_line_width(2.0)

        cell_size = height / CELL_COUNT
        for i in range(1, CELL_COUNT):
            context.move_to(0, cell_size * i)
            context.line_to(width, cell_size * i)

        context.stroke()

    def __draw_frame(self, context, width, height):
        style_context = self.get_style_context()
        Gtk.render_frame(style_context, context, 0, 0, width, height)

    def __set_gradients(self, width, height):
        self.background_gradient = cairo.LinearGradient(0, 0, width, height)
        self.background_gradient.add_color_stop_rgb(1.0, 0.0, 0.3, 0.0)
        self.background_gradient.add_color_stop_rgb(0.7, 0.3, 0.3, 0.0)
        self.background_gradient.add_color_stop_rgb(0.0, 0.3, 0.0, 0.0)

        self.peak_gradient = cairo.LinearGradient(0, 0, width, height)
        self.peak_gradient.add_color_stop_rgb(1.0, 0.0, 1.0, 0.0)
        self.peak_gradient.add_color_stop_rgb(0.7, 1.0, 1.0, 0.0)
        self.peak_gradient.add_color_stop_rgb(0.0, 1.0, 0.0, 0.0)

    def __normalize_peak(self, height):
        return height / (-MIN_PEAK) * (max(self.peak, MIN_PEAK) - MIN_PEAK)

    def update_peakmeter(self, peak):
        self.peak = peak
        self.queue_draw()


class PeakMeterScale(PeakMeterWidget):
    """A scale for the peak meter."""

    def __init__(self):
        PeakMeterWidget.__init__(self)
        width = FONT_SIZE * 2
        self.set_property("width_request", width)

    def do_draw(self, context):
        if self.pixel_buffer is None:
            return

        width = self.get_allocated_width()
        height = self.get_allocated_height()
        pixel_buffer = self.pixel_buffer

        drawing_context = cairo.Context(pixel_buffer)
        self.draw_background(drawing_context, width, height)
        self.__draw_scale(drawing_context)
        pixel_buffer.flush()

        context.set_source_surface(pixel_buffer, 0.0, 0.0)
        context.paint()

    def __draw_scale(self, context):
        bar_height = self.get_bar_height()
        section_height = bar_height / (SCALE_COUNT - 1)

        style_context = self.get_style_context()
        color = gtk_style_context_get_color(style_context, Gtk.StateFlags.NORMAL)

        set_cairo_color(context, color)
        context.set_font_size(FONT_SIZE)
        context.set_font_face(NORMAL_FONT)
        text_extent = context.text_extents("0")

        for i in range(SCALE_COUNT):
            context.move_to(0, section_height * i + SPACING + text_extent.height / 2)
            context.show_text(str((MIN_PEAK // (SCALE_COUNT - 1)) * i))

    def get_bar_height(self):
        return self.get_allocated_height() - SPACING * 2
