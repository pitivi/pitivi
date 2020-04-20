# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Lubosz Sarnecki <lubosz.sarnecki@collabora.co.uk>
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
import numpy
from gi.repository import Gtk


class SafeAreasOverlay(Gtk.DrawingArea):
    """Viewer for a video's safe area."""

    def __init__(self, stack):
        Gtk.DrawingArea.__init__(self)

        self.__stack = stack
        self.__project = stack.app.project_manager.current_project
        self.__title_safe_area_size = numpy.array([0, 0])
        self.__action_safe_area_size = numpy.array([0, 0])
        self.__title_safe_area_position = numpy.array([0, 0])
        self.__action_safe_area_position = numpy.array([0, 0])
        self.safe_areas_enabled = False  # Set the default state as off

        self.__update_safe_areas()

        self.__project.connect("safe-area-size-changed", self.__safe_areas_size_changed_cb)

    def __safe_areas_size_changed_cb(self):
        self.__update_safe_areas()

    def __update_safe_areas(self):
        self.__resize_safe_areas_display()
        self.queue_draw()

    def toggle_safe_areas(self):
        self.safe_areas_enabled = not self.safe_areas_enabled
        self.__update_safe_areas()

        self.set_visible(self.safe_areas_enabled)

    def __resize_safe_areas_display(self):
        window_width, window_height = [int(window_size_value) for window_size_value in self.__stack.window_size]

        self.__title_safe_area_size = self.compute_new_safe_area_size(window_width, window_height,
                                                                      self.__project.title_safe_area_horizontal, self.__project.title_safe_area_vertical)
        self.__action_safe_area_size = self.compute_new_safe_area_size(window_width, window_height,
                                                                       self.__project.action_safe_area_horizontal, self.__project.action_safe_area_vertical)
        self.__title_safe_area_position = self.compute_new_safe_area_position(window_width, window_height,
                                                                              self.__title_safe_area_size[numpy.array([0])], self.__title_safe_area_size[numpy.array([1])])
        self.__action_safe_area_position = self.compute_new_safe_area_position(window_width, window_height,
                                                                               self.__action_safe_area_size[numpy.array([0])], self.__action_safe_area_size[numpy.array([1])])

    def compute_new_safe_area_position(self, window_width, window_height, safe_area_width, safe_area_height):
        x_position = (window_width - safe_area_width) / 2
        y_position = (window_height - safe_area_height) / 2

        return numpy.array([x_position, y_position])

    def compute_new_safe_area_size(self, window_width, window_height, new_width_percentage, new_height_percentage):
        safe_area_width = window_width * new_width_percentage
        safe_area_height = window_height * new_height_percentage

        return numpy.array([safe_area_width, safe_area_height])

    def __draw_safe_area(self, cr, safe_area_position, safe_area_size):
        if not self.safe_areas_enabled:
            return

        x_position, y_position = [int(position_value) for position_value in safe_area_position]
        width, height = [int(size_value) for size_value in safe_area_size]
        cr.rectangle(x_position, y_position, width, height)

    def do_draw(self, cr):
        cr.save()

        #  Transparent Background
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()

        #  Resize the safe areas on drawing
        self.__resize_safe_areas_display()

        #  Black safe area line border color
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(3)
        self.__draw_safe_area(cr, self.__title_safe_area_position, self.__title_safe_area_size)
        self.__draw_safe_area(cr, self.__action_safe_area_position, self.__action_safe_area_size)
        cr.stroke()

        #  White safe area line inner color
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(1)
        self.__draw_safe_area(cr, self.__title_safe_area_position, self.__title_safe_area_size)
        self.__draw_safe_area(cr, self.__action_safe_area_position, self.__action_safe_area_size)
        cr.stroke()

        cr.restore()
