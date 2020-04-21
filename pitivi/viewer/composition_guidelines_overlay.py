# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Jaden Goter <jadengoter@huskers.unl.edu>
# Copyright (c) 2020, Jessie Guo <jessie.guo@huskers.unl.edu>,
# Copyright (c) 2020, Daniel Rudebusch <daniel.rudebusch@huskers.unl.edu>
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

from pitivi.utils.loggable import Loggable


class CompositionGuidelinesOverlay(Gtk.DrawingArea, Loggable):
    """Viewer overlays for composition guidelines."""

    def __init__(self, stack, action_log):
        Gtk.DrawingArea.__init__(self)
        Loggable.__init__(self)

        self.stack = stack
        self.__action_log = action_log

        project = stack.app.project_manager.current_project
        project.connect("video-size-changed", self._canvas_size_changed_cb)
        self.project_size = numpy.array([project.videowidth,
                                         project.videoheight])

        self.__guidelines_to_draw = set()
        self.update_from_source()

    def _canvas_size_changed_cb(self, project):
        project = self.stack.app.project_manager.current_project
        self.project_size = numpy.array([project.videowidth,
                                         project.videoheight])

    def get_aspect_ratio(self):
        size = self.__get_size()
        return size[0] / size[1]

    @property
    def guidelines_to_draw(self):
        return self.__guidelines_to_draw

    def three_by_three(self, cr):
        for x in range(1, 3):
            cr.move_to(x * self.stack.window_size[0] / 3, 0)
            cr.line_to(x * self.stack.window_size[0] / 3, self.stack.window_size[1])
            cr.move_to(0, x * self.stack.window_size[1] / 3)
            cr.line_to(self.stack.window_size[0], x * self.stack.window_size[1] / 3)

    def diagonals(self, cr):
        cr.move_to(0, 0)
        cr.line_to(self.stack.window_size[0], self.stack.window_size[1])
        cr.move_to(self.stack.window_size[0], 0)
        cr.line_to(0, self.stack.window_size[1])

    def vertical_horizontal_center(self, cr):
        cr.move_to(self.stack.window_size[0] / 2, 0)
        cr.line_to(self.stack.window_size[0] / 2, self.stack.window_size[1])
        cr.move_to(0, self.stack.window_size[1] / 2)
        cr.line_to(self.stack.window_size[0], self.stack.window_size[1] / 2)

    def add_guideline(self, guideline):
        self.__guidelines_to_draw.add(guideline)
        self.update_from_source()

    def remove_guideline(self, guideline):
        try:
            self.__guidelines_to_draw.remove(guideline)
            self.update_from_source()
        except ValueError:
            raise ValueError("The guideline %r not in guidelines to draw %r" % (guideline, self.__guidelines_to_draw))

    def update_from_source(self):
        self.queue_draw()

    def do_draw(self, cr):
        cr.save()

        # Clear background
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()

        # Draw black border
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(3)
        for guideline in self.__guidelines_to_draw:
            guideline(cr)
        cr.stroke()

        # Draw white line in middle
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(1)
        for guideline in self.__guidelines_to_draw:
            guideline(cr)
        cr.stroke()

        cr.restore()
