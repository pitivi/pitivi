# -*- coding: utf-8 -*-
import enum

import cairo
from gi.repository import Gtk

from pitivi.utils.ui import gtk_style_context_get_color
from pitivi.utils.ui import NORMAL_FONT
from pitivi.utils.ui import set_cairo_color

WIDTH = 6
HEIGHT = 200
PADDING = 1
CELL_COUNT = 20
MIN_PEAK = -60
FONT_SIZE = 13
SCALE_COUNT = 2


class Channel(enum.Enum):
    LEFT_PEAK = 0
    RIGHT_PEAK = 1


class PeakMeter(Gtk.DrawingArea):
    """A meter that shows peak values."""

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.peak = 0
        self.full_height = HEIGHT + PADDING * 2
        self.full_width = WIDTH + PADDING * 2
        self.set_size_request(self.full_width, self.full_height)
        self.set_gradients()
        style_context = self.get_style_context()
        style_context.add_class("frame")
        style_context.add_class("trough")

        self.show()

    def do_draw(self, context):
        pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.full_width, self.full_height)

        drawing_context = cairo.Context(pixbuf)
        self.draw_frame(drawing_context)
        self.draw_bar(drawing_context)
        self.draw_cells(drawing_context)
        pixbuf.flush()

        context.set_source_surface(pixbuf, 0.0, 0.0)
        context.paint()

        return False

    def set_gradients(self):
        self.background_gradient = cairo.LinearGradient(1, 1, WIDTH, HEIGHT)
        self.background_gradient.add_color_stop_rgb(1.0, 0.0, 0.3, 0.0)
        self.background_gradient.add_color_stop_rgb(0.7, 0.3, 0.3, 0.0)
        self.background_gradient.add_color_stop_rgb(0.0, 0.3, 0.0, 0.0)

        self.peak_gradient = cairo.LinearGradient(1, 1, WIDTH, HEIGHT)
        self.peak_gradient.add_color_stop_rgb(1.0, 0.0, 1.0, 0.0)
        self.peak_gradient.add_color_stop_rgb(0.7, 1.0, 1.0, 0.0)
        self.peak_gradient.add_color_stop_rgb(0.0, 1.0, 0.0, 0.0)

    def draw_bar(self, context):
        context.set_source(self.background_gradient)
        context.rectangle(PADDING, PADDING, WIDTH, HEIGHT)
        context.fill()

        context.set_source(self.peak_gradient)
        context.rectangle(PADDING, HEIGHT - self.peak + PADDING, WIDTH, self.peak)
        context.fill()

    def draw_cells(self, context):
        context.set_source_rgba(0, 0, 0, 0.5)
        context.set_line_width(2.0)

        cell_size = HEIGHT / CELL_COUNT
        for i in range(1, CELL_COUNT):
            context.move_to(PADDING, cell_size * i + PADDING)
            context.line_to(WIDTH + PADDING, cell_size * i + PADDING)

        context.stroke()

    def draw_frame(self, context):
        style_context = self.get_style_context()
        Gtk.render_frame(style_context, context, 0, 0, self.full_width, self.full_height)

    def normalize_peak(self, peak):
        return HEIGHT / (-MIN_PEAK) * (max(peak, MIN_PEAK) - MIN_PEAK)

    def update_peakmeter(self, peak):
        self.peak = self.normalize_peak(peak)
        self.queue_draw()


class PeakMeterScale(Gtk.DrawingArea):
    """A scale for the peak meter."""

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.full_height = HEIGHT + FONT_SIZE * 2
        self.full_width = WIDTH + FONT_SIZE * 2
        self.set_size_request(self.full_width, self.full_height)

        self.show()

    def do_draw(self, context):
        pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.full_width, self.full_height)

        drawing_context = cairo.Context(pixbuf)
        self.draw_scale(drawing_context)
        pixbuf.flush()

        context.set_source_surface(pixbuf, 0.0, 0.0)
        context.paint()

        return False

    def draw_scale(self, context):
        section_height = HEIGHT / SCALE_COUNT

        style_context = self.get_style_context()
        color = gtk_style_context_get_color(style_context, Gtk.StateFlags.NORMAL)

        set_cairo_color(context, color)
        context.set_font_size(FONT_SIZE)
        context.set_font_face(NORMAL_FONT)
        text_extent = context.text_extents('0')

        for i in range(SCALE_COUNT + 1):
            context.move_to(0, section_height * i + FONT_SIZE + text_extent.height / 2)
            context.show_text(str((MIN_PEAK // SCALE_COUNT) * i))
