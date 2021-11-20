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

from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.viewer.overlay import Overlay


class TitleOverlay(Overlay):
    """Viewer overlays for GES.TitleSource."""

    def __init__(self, stack, source):
        Overlay.__init__(self, stack, source)
        self.__position = numpy.array([0, 0])
        self.__size = None
        self.__click_window_position = None
        self.update_from_source()

        stack.app.project_manager.current_project.pipeline.connect("async-done", self.on_async_done)

    def on_async_done(self, unused_pipeline):
        # Only update on_async when we are not dragging
        if isinstance(self.stack.click_position, numpy.ndarray):
            return
        self.update_from_source()

    def __draw_rectangle(self, cr):
        x, y = [int(v) + 0.5 for v in self.__position]
        w, h = [int(v) - 1 for v in self.__size]
        cr.rectangle(x, y, w, h)

    def __get_text_position(self):
        res_x, x = self._source.get_child_property("text-x")
        res_y, y = self._source.get_child_property("text-y")
        assert res_x and res_y
        return numpy.array([x, y])

    def __get_text_size(self):
        res_w, w = self._source.get_child_property("text-width")
        res_h, h = self._source.get_child_property("text-height")
        assert res_w and res_h
        return numpy.array([w, h])

    def __set_source_position(self, position):
        self._source.set_child_property("x-absolute", float(position[0]))
        self._source.set_child_property("y-absolute", float(position[1]))

    def __update_from_motion(self, title_position):
        self.__position = title_position

    def update_from_source(self):
        position = self.__get_text_position()
        size = self.__get_text_size()

        self.__position = position * self.stack.window_size / self.project_size
        self.__size = size * self.stack.window_size / self.project_size
        self.queue_draw()

    def on_hover(self, cursor_position):
        if (self.__position <= cursor_position).all() and (cursor_position < self.__position + self.__size).all():
            if self._is_selected():
                self.stack.set_cursor("grab")
            self._hover()
        else:
            self.unhover()
        self.queue_draw()
        return self._is_hovered()

    def on_button_press(self):
        self.__click_window_position = self.__position
        if self._is_hovered():
            self._select()
            self.stack.set_cursor("grabbing")
            self.stack.app.action_log.begin("Title drag",
                                            finalizing_action=CommitTimelineFinalizingAction(
                                                self.stack.app.project_manager.current_project.pipeline),
                                            toplevel=True)
        else:
            # We're not hovered anymore, make sure we're not selected.
            if self._is_selected():
                self._deselect()

    def on_button_release(self, cursor_position):
        if self._is_selected():
            self.stack.app.action_log.commit("Title drag")

        self.on_hover(cursor_position)
        if self._is_hovered():
            self.stack.set_cursor("grab")
        self.queue_draw()

    def on_motion_notify(self, cursor_position):
        if not isinstance(self.stack.click_position, numpy.ndarray):
            return

        self.__update_from_motion(self.__click_window_position + self.stack.get_drag_distance(cursor_position))
        self.queue_draw()

        title_position = self.__position / (self.stack.window_size * (1 - self.__get_text_size() / self.project_size))

        self.__set_source_position(title_position)
        self._commit()

    def do_draw(self, cr):
        selected = self._is_selected()
        hovered = self._is_hovered()
        if not selected and not hovered:
            return

        cr.save()

        # Clear background
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()

        if not selected:
            cr.set_dash((5, 5))

        # Black outline around the box
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(3)
        self.__draw_rectangle(cr)
        cr.stroke()

        # Inner white line
        color = (0.8, 0.8, 0.8) if not selected else (1, 1, 1)
        cr.set_source_rgb(*color)
        cr.set_line_width(1)
        self.__draw_rectangle(cr)
        cr.stroke()

        cr.restore()
