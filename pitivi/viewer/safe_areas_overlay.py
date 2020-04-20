# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Guy Richard <guy.richard99@gmail.com>
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
from gi.repository import Gtk

from pitivi.utils.misc import round05


class SafeAreasOverlay(Gtk.DrawingArea):
    """Overlay showing the safe areas of a project."""

    def __init__(self, stack):
        Gtk.DrawingArea.__init__(self)

        self.__project = stack.app.project_manager.current_project

        self.__project.connect("safe-area-size-changed", self.__safe_areas_size_changed_cb)

        self.props.no_show_all = True

    def __safe_areas_size_changed_cb(self, project):
        self.queue_draw()

    @staticmethod
    def _compute_rect(widget_width, widget_height, horizontal_factor, vertical_factor):
        w = widget_width * horizontal_factor
        h = widget_height * vertical_factor
        x = (widget_width - w) / 2
        y = (widget_height - h) / 2
        return round05(x), round05(y), int(w), int(h)

    def do_draw(self, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        title_rect = self._compute_rect(width, height, self.__project.title_safe_area_horizontal, self.__project.title_safe_area_vertical)
        action_rect = self._compute_rect(width, height, self.__project.action_safe_area_horizontal, self.__project.action_safe_area_vertical)

        # Black line borders.
        cr.set_line_width(2)
        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(*action_rect)
        cr.rectangle(*title_rect)
        cr.stroke()

        # Lines inner color.
        cr.set_line_width(1)

        cr.set_source_rgb(1, 1, 0.75)
        cr.rectangle(*action_rect)
        cr.stroke()

        cr.set_source_rgb(0.8, 1, 0.85)
        cr.rectangle(*title_rect)
        cr.stroke()
