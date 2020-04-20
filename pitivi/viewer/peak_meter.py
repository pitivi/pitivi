# -*- coding: utf-8 -*-
import enum

import cairo
from gi.repository import GObject
from gi.repository import Gtk

from pitivi.utils.ui import gtk_style_context_get_color
from pitivi.utils.ui import NORMAL_FONT
from pitivi.utils.ui import set_cairo_color

# The width for the peak meter
WIDTH = 6
# The maximum height for the peak meter
HEIGHT = 200
# The minimum height for the peak meter
MIN_HEIGHT = 60
# The padding for the peak meter
PADDING = 1
# The number of cells on the peak meter bar
CELL_COUNT = 20
# The minimum peak value represented by the peak meter
MIN_PEAK = -60

# The font size for the scale
FONT_SIZE = 13
# The number of values shown on the scale
SCALE_COUNT = 5


class Channel(enum.Enum):
    LEFT_PEAK = 0
    RIGHT_PEAK = 1


class PeakMeter(Gtk.DrawingArea):
    # A meter that shows peak values.

    # Signal for the peak meter being resized
    __gsignals__ = {
        "peak-meter-resized": (GObject.SignalFlags.RUN_LAST,
                               None, (GObject.TYPE_INT,))
    }

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.peak = MIN_PEAK
        height = HEIGHT + PADDING * 2
        width = WIDTH + PADDING * 2
        self.set_size_request(width, height)
        self.set_gradients()
        style_context = self.get_style_context()
        style_context.add_class("frame")
        style_context.add_class("trough")

        self.show()

    def set_gradients(self):
        bar_height = self._get_bar_height()
        bar_width = self._get_bar_width()

        self.background_gradient = cairo.LinearGradient(1, 1, bar_width, bar_height)
        self.background_gradient.add_color_stop_rgb(1.0, 0.0, 0.3, 0.0)
        self.background_gradient.add_color_stop_rgb(0.7, 0.3, 0.3, 0.0)
        self.background_gradient.add_color_stop_rgb(0.0, 0.3, 0.0, 0.0)

        self.peak_gradient = cairo.LinearGradient(1, 1, bar_width, bar_height)
        self.peak_gradient.add_color_stop_rgb(1.0, 0.0, 1.0, 0.0)
        self.peak_gradient.add_color_stop_rgb(0.7, 1.0, 1.0, 0.0)
        self.peak_gradient.add_color_stop_rgb(0.0, 1.0, 0.0, 0.0)

    def do_draw(self, context):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        bar_height = self._get_bar_height()
        bar_width = self._get_bar_width()

        pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        drawing_context = cairo.Context(pixbuf)
        self.draw_frame(drawing_context, width, height)
        self.draw_bar(drawing_context, bar_width, bar_height)
        self.draw_cells(drawing_context, bar_width, bar_height)
        pixbuf.flush()

        context.set_source_surface(pixbuf, 0.0, 0.0)
        context.paint()

        return False

    def draw_bar(self, context, bar_width, bar_height):
        peak_height = self.normalize_peak(self.peak)

        context.set_source(self.background_gradient)
        context.rectangle(PADDING, PADDING, bar_width, bar_height)
        context.fill()

        context.set_source(self.peak_gradient)
        context.rectangle(PADDING, bar_height - peak_height + PADDING, bar_width, peak_height)
        context.fill()

    def draw_cells(self, context, bar_width, bar_height):
        context.set_source_rgba(0, 0, 0, 0.5)
        context.set_line_width(2.0)

        cell_size = bar_height / CELL_COUNT
        for i in range(1, CELL_COUNT):
            context.move_to(PADDING, cell_size * i + PADDING)
            context.line_to(bar_width + PADDING, cell_size * i + PADDING)

        context.stroke()

    def draw_frame(self, context, width, height):
        style_context = self.get_style_context()
        Gtk.render_frame(style_context, context, 0, 0, width, height)

    def normalize_peak(self, peak):
        bar_height = self._get_bar_height()
        return bar_height / (-MIN_PEAK) * (max(peak, MIN_PEAK) - MIN_PEAK)

    def update_peakmeter(self, peak):
        self.peak = peak
        self.queue_draw()

    def _get_bar_height(self):
        return self.get_allocated_height() - PADDING * 2

    def _get_bar_width(self):
        return self.get_allocated_width() - PADDING * 2

    def do_configure_event(self, unused_event):
        padding = FONT_SIZE * 3
        difference = HEIGHT + padding - self.get_parent().get_allocated_height()
        bar_height = max(HEIGHT - max(difference, 0), MIN_HEIGHT)
        height = bar_height + PADDING * 2
        width = WIDTH + PADDING * 2

        self.set_size_request(width, height)
        self.set_gradients()
        self.emit("peak-meter-resized", bar_height)

        return False


class PeakMeterScale(Gtk.DrawingArea):
    """A scale for the peak meter.

    Args:
        peak_meter (PeakMeter): The peak meter the scale corresponds to
    """

    def __init__(self, peak_meter):
        Gtk.DrawingArea.__init__(self)
        height = HEIGHT + FONT_SIZE * 2
        width = FONT_SIZE * 2
        self.set_size_request(width, height)
        self.peak_meter = peak_meter
        self.peak_meter.connect("peak-meter-resized", self._peak_meter_resized_cb)

        self.show()

    def do_draw(self, context):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        drawing_context = cairo.Context(pixbuf)
        self.draw_scale(drawing_context)
        pixbuf.flush()

        context.set_source_surface(pixbuf, 0.0, 0.0)
        context.paint()

        return False

    def draw_scale(self, context):
        bar_height = self._get_bar_height()
        section_height = bar_height / (SCALE_COUNT - 1)

        style_context = self.get_style_context()
        color = gtk_style_context_get_color(style_context, Gtk.StateFlags.NORMAL)

        set_cairo_color(context, color)
        context.set_font_size(FONT_SIZE)
        context.set_font_face(NORMAL_FONT)
        text_extent = context.text_extents('0')

        for i in range(SCALE_COUNT):
            context.move_to(0, section_height * i + FONT_SIZE + text_extent.height / 2)
            context.show_text(str((MIN_PEAK // (SCALE_COUNT - 1)) * i))

    def _get_bar_height(self):
        return self.get_allocated_height() - FONT_SIZE * 2

    def _peak_meter_resized_cb(self, unused_event, bar_height):
        height = bar_height + FONT_SIZE * 2
        width = FONT_SIZE * 2

        self.set_size_request(width, height)
