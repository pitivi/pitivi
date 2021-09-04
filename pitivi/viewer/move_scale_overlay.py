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
from collections import OrderedDict

import cairo
import numpy

from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.misc import disconnect_all_by_func
from pitivi.utils.pipeline import PipelineError
from pitivi.viewer.overlay import Overlay


class Edge:
    top = 1
    bottom = 2
    left = 3
    right = 4


class Handle:
    INITIAL_SIZE = 30
    MINIMAL_SIZE = 10
    CURSORS = {
        (Edge.top, Edge.left): "nw-resize",
        (Edge.bottom, Edge.left): "sw-resize",
        (Edge.bottom, Edge.right): "se-resize",
        (Edge.top, Edge.right): "ne-resize",
        (Edge.top,): "n-resize",
        (Edge.bottom,): "s-resize",
        (Edge.left,): "w-resize",
        (Edge.right,): "e-resize"
    }

    def __init__(self, overlay):
        self.__size = Handle.INITIAL_SIZE
        self.__window_position = numpy.array([0, 0])
        self.__translation = numpy.array([0, 0])
        self.__click_position = numpy.array([0, 0])
        self._opposite_position = numpy.array([0, 0])
        self._opposite_to_handle = numpy.array([0, 0])
        self._overlay = overlay
        self.placement = ()
        self.position = numpy.array([0, 0])
        self.hovered = False
        self.neighbours = []

    def _get_minimal_box_size(self):
        raise NotImplementedError

    def _needs_size_restriction(self, handle_position_compare, cursor_position_compare):
        pass

    def _update_neighbours(self):
        pass

    def _restrict(self, handle_to_cursor):
        raise NotImplementedError

    def __update_window_position(self):
        self.__window_position = (self.position + self.__translation) * self._overlay.stack.window_size

    def __update_opposite(self):
        self._opposite_to_handle = 2 * (self.position - self._overlay.get_center())
        self._opposite_position = self.position - self._opposite_to_handle

    def __init_neighbours(self):
        for corner in self._overlay.corner_handles:
            for edge in self.placement:
                if edge in corner and corner != self.placement:
                    self.neighbours.append(self._overlay.corner_handles[corner])

    def _restrict_to_minimal_size(self, cursor_position):
        minimal_size = self._get_minimal_box_size()
        handle_to_opposite_sign = numpy.sign(self._opposite_to_handle)
        minimal_size_handle_position = self._opposite_position + minimal_size * handle_to_opposite_sign
        cursor_position_compare = cursor_position >= minimal_size_handle_position
        handle_position_compare = handle_to_opposite_sign >= numpy.array([0, 0])

        if self._needs_size_restriction(handle_position_compare, cursor_position_compare):
            cursor_position = minimal_size_handle_position
        return cursor_position

    def _get_normalized_minimal_size(self):
        return 2 * Handle.MINIMAL_SIZE / self._overlay.stack.window_size

    def get_window_position(self):
        x, y = [int(v) + 0.5 for v in self.__window_position]
        if Edge.right in self.placement:
            x -= 1
        if Edge.bottom in self.placement:
            y -= 1
        return x, y

    def get_source_position(self):
        """Returns a source translation when handles at TOP or LEFT are dragged.

        The user is not translating here, but scaling.
        This is needed to move the pivot point of the scale operation
        from the TOP LEFT corner to the CENTER.
        Returns None for handles where this is not needed
        """
        source_position = None
        if Edge.top in self.placement or Edge.left in self.placement:
            position_stream_size = self.position * self._overlay.project_size
            # only x source translation changes
            if self.placement in [(Edge.bottom, Edge.left), (Edge.left,)]:
                position_stream_size[1] = 0
            # only y source translation changes
            elif self.placement in [(Edge.top, Edge.right), (Edge.top,)]:
                position_stream_size[0] = 0
            source_position = position_stream_size + self._overlay.click_source_position

        return source_position

    def set_placement(self, placement):
        self.placement = placement
        self.__init_neighbours()

    def set_position(self, position):
        self.position = position
        self.__update_window_position()

    def set_translation(self, translation):
        self.__translation = translation
        self.__update_window_position()

    def set_x(self, x):
        self.position = numpy.array([x, self.position[1]])
        self.__update_window_position()

    def set_y(self, y):
        self.position = numpy.array([self.position[0], y])
        self.__update_window_position()

    def on_hover(self, cursor_pos):
        if cursor_pos is None:
            # The cursor is out of the widget.
            self.hovered = False
            return

        distance = numpy.linalg.norm(self.__window_position - cursor_pos)
        if distance < self.__size / 2:
            self.hovered = True
            self._overlay.stack.set_cursor(Handle.CURSORS[self.placement])
        else:
            self.hovered = False

    def on_click(self):
        self.__click_position = self.position
        self.__update_opposite()

    def on_drag(self, click_to_cursor):
        handle_to_cursor = click_to_cursor + self.__click_position
        restricted_handle_to_cursor = self._restrict(handle_to_cursor)

        # Update box from motion event coordinates
        self.set_position(restricted_handle_to_cursor)
        self._update_neighbours()

    def on_release(self):
        self._opposite_position = None
        self._opposite_to_handle = None

    def restrict_size(self, size):
        if size < Handle.INITIAL_SIZE * 5:
            self.__size = max(Handle.MINIMAL_SIZE, size / 5)
        else:
            self.__size = Handle.INITIAL_SIZE

    def reset_size(self):
        self.__size = Handle.INITIAL_SIZE

    def draw(self, cr):
        src_x, src_y = self.get_window_position()
        x = src_x - (self.__size / 2)
        y = src_y - (self.__size / 2)

        if self.hovered:
            cr.set_source_rgba(1, 1, 1, 0.25)
            cr.rectangle(x, y, self.__size, self.__size)
            cr.fill()

        # Black outline around the box
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(3)
        cr.rectangle(x, y, self.__size + 1, self.__size + 1)
        cr.stroke()

        # Inner white line
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(1)
        cr.rectangle(x, y, self.__size + 1, self.__size + 1)
        cr.stroke()


class CornerHandle(Handle):
    def __init__(self, overlay):
        Handle.__init__(self, overlay)

    def __restrict_to_aspect_ratio(self, cursor_position):
        opposite_to_cursor = cursor_position - self._opposite_position
        opposite_to_cursor_ratio = opposite_to_cursor[0] / opposite_to_cursor[1]
        opposite_to_handle_ratio = self._opposite_to_handle[0] / self._opposite_to_handle[1]
        restricted_cursor_position = cursor_position

        if abs(opposite_to_cursor_ratio) > abs(opposite_to_handle_ratio):
            # adjust width
            restricted_cursor_position[0] =\
                self._opposite_position[0] + opposite_to_cursor[1] * opposite_to_handle_ratio
        else:
            # adjust height
            restricted_cursor_position[1] =\
                self._opposite_position[1] + opposite_to_cursor[0] / opposite_to_handle_ratio
        return restricted_cursor_position

    def _get_minimal_box_size(self):
        # keep aspect when making a minimal box when corner is dragged
        minimal_size = self._get_normalized_minimal_size()
        if self._overlay.get_aspect_ratio() < 1.0:
            minimal_size[1] = minimal_size[0] / self._overlay.get_aspect_ratio()
        else:
            minimal_size[0] = minimal_size[1] * self._overlay.get_aspect_ratio()
        return minimal_size

    def _needs_size_restriction(self, handle_position_compare, cursor_position_compare):
        if (handle_position_compare != cursor_position_compare).any():
            return True
        return False

    def _update_neighbours(self):
        for neighbour in self.neighbours:
            if neighbour.placement[0] == self.placement[0]:
                neighbour.set_y(self.position[1])
            elif neighbour.placement[1] == self.placement[1]:
                neighbour.set_x(self.position[0])

    def _restrict(self, handle_to_cursor):
        return self._restrict_to_minimal_size(
            self.__restrict_to_aspect_ratio(handle_to_cursor))


class EdgeHandle(Handle):
    def __init__(self, overlay):
        Handle.__init__(self, overlay)

    def _get_minimal_box_size(self):
        # nullify x / y in minimal box for edge handles
        # required in minimal handle position calculation
        minimal_size = self._get_normalized_minimal_size()
        if self._opposite_to_handle[0] == 0:
            # top bottom
            minimal_size[0] = 0
        else:
            # left right
            minimal_size[1] = 0
        return minimal_size

    def _needs_size_restriction(self, handle_position_compare, cursor_position_compare):
        if self._opposite_to_handle[0] == 0:
            # top bottom
            if handle_position_compare[1] != cursor_position_compare[1]:
                return True
        else:
            # left right
            if handle_position_compare[0] != cursor_position_compare[0]:
                return True
        return False

    def _update_neighbours(self):
        if self.placement[0] in (Edge.left, Edge.right):
            for neighbour in self.neighbours:
                neighbour.set_x(self.position[0])
        elif self.placement[0] in (Edge.top, Edge.bottom):
            for neighbour in self.neighbours:
                neighbour.set_y(self.position[1])

    def _restrict(self, handle_to_cursor):
        return self._restrict_to_minimal_size(handle_to_cursor)


class MoveScaleOverlay(Overlay):
    """Viewer overlays for GES.VideoSource transformations."""

    def __init__(self, stack, action_log, source):
        Overlay.__init__(self, stack, source)

        self.__clicked_handle = None

        self.__action_log = action_log
        self.hovered_handle = None

        # Corner handles need to be ordered for drawing.
        self.corner_handles = OrderedDict([
            ((Edge.top, Edge.left), CornerHandle(self)),
            ((Edge.bottom, Edge.left), CornerHandle(self)),
            ((Edge.bottom, Edge.right), CornerHandle(self)),
            ((Edge.top, Edge.right), CornerHandle(self))])

        self.handles = self.corner_handles.copy()
        for edge in range(1, 5):
            self.handles[(edge,)] = EdgeHandle(self)

        for key in self.handles:
            self.handles[key].set_placement(key)

        self._source.connect("deep-notify", self.__source_property_changed_cb)
        self.update_from_source()

    def __get_source_property(self, prop):
        if self.__source_property_keyframed(prop):
            binding = self._source.get_control_binding(prop)
            res, position = self.__get_pipeline_position()
            if res:
                start = self._source.props.start
                in_point = self._source.props.in_point
                duration = self._source.props.duration
                # If the position is outside of the clip, take the property
                # value at the start/end (whichever is closer) of the clip.
                source_position = max(0, min(position - start, duration - 1)) + in_point
                value = binding.get_value(source_position)
                res = value is not None
                return res, value

        return self._source.get_child_property(prop)

    def __set_source_property(self, prop, value):
        if self.__source_property_keyframed(prop):
            control_source = self._source.get_control_binding(prop).props.control_source
            res, timestamp = self.__get_pipeline_position()
            if not res:
                return
            source_timestamp = timestamp - self._source.props.start + self._source.props.in_point
            control_source.set(source_timestamp, value)
        else:
            self._source.set_child_property(prop, value)

    def __source_property_keyframed(self, prop):
        binding = self._source.get_control_binding(prop)
        return binding is not None

    def __get_pipeline_position(self):
        project = self.stack.app.project_manager.current_project
        if project:
            pipeline = project.pipeline
            try:
                position = pipeline.get_position()
                return True, position
            except PipelineError:
                pass
        return False, None

    def __get_source_position(self):
        res_x, x = self.__get_source_property("posx")
        res_y, y = self.__get_source_property("posy")
        assert res_x and res_y
        return numpy.array([x, y])

    def __get_source_size(self):
        res_x, x = self.__get_source_property("width")
        res_y, y = self.__get_source_property("height")
        assert res_x and res_y
        return numpy.array([x, y])

    def __get_normalized_source_position(self):
        return self.__get_source_position() / self.project_size

    def __set_source_position(self, position):
        self.__set_source_property("posx", int(position[0]))
        self.__set_source_property("posy", int(position[1]))

    def __set_source_size(self, size):
        self.__set_source_property("width", int(size[0]))
        self.__set_source_property("height", int(size[1]))

    def __get_size(self):
        return numpy.array([self.__get_width(), self.__get_height()])

    def __get_size_stream(self):
        return self.__get_size() * self.project_size

    def __get_height(self):
        return self.handles[(Edge.bottom, Edge.left)].position[1] - self.handles[(Edge.top, Edge.left)].position[1]

    def __get_width(self):
        return self.handles[(Edge.bottom, Edge.right)].position[0] - self.handles[(Edge.bottom, Edge.left)].position[0]

    def __set_size(self, size):
        self.handles[(Edge.top, Edge.left)].position = numpy.array([0, 0])
        self.handles[(Edge.bottom, Edge.left)].position = numpy.array([0, size[1]])
        self.handles[(Edge.bottom, Edge.right)].position = numpy.array([size[0], size[1]])
        self.handles[(Edge.top, Edge.right)].position = numpy.array([size[0], 0])
        self.__update_edges_from_corners()

    def __set_position(self, position):
        for handle in self.handles.values():
            handle.set_translation(position)

    def __reset_handle_sizes(self):
        for handle in self.handles.values():
            handle.reset_size()
        self.__update_handle_sizes()

    def __update_handle_sizes(self):
        size = self.__get_size() * self.stack.window_size
        smaller_size = numpy.amin(size)

        for handle in self.handles.values():
            handle.restrict_size(smaller_size)

    def __update_edges_from_corners(self):
        half_w = numpy.array([self.__get_width() * 0.5, 0])
        half_h = numpy.array([0, self.__get_height() * 0.5])

        self.handles[(Edge.left,)].set_position(self.handles[(Edge.top, Edge.left)].position + half_h)
        self.handles[(Edge.right,)].set_position(self.handles[(Edge.top, Edge.right)].position + half_h)
        self.handles[(Edge.bottom,)].set_position(self.handles[(Edge.bottom, Edge.left)].position + half_w)
        self.handles[(Edge.top,)].set_position(self.handles[(Edge.top, Edge.right)].position - half_w)

    def __draw_rectangle(self, cr):
        cr.move_to(*self.handles[(Edge.top, Edge.right)].get_window_position())
        for handle in self.corner_handles.values():
            cr.line_to(*handle.get_window_position())

    def get_center(self):
        diagonal = self.handles[(Edge.bottom, Edge.right)].position - self.handles[(Edge.top, Edge.left)].position
        return self.handles[(Edge.top, Edge.left)].position + (diagonal / 2)

    def get_aspect_ratio(self):
        size = self.__get_size()
        return size[0] / size[1]

    def on_button_press(self):
        disconnect_all_by_func(self._source, self.__source_property_changed_cb)
        self.click_source_position = self.__get_source_position()
        self.__clicked_handle = None

        hovered = self._is_hovered()
        if self.hovered_handle or hovered:
            self.__action_log.begin("Video position change",
                                    finalizing_action=CommitTimelineFinalizingAction(
                                        self._source.get_timeline().get_parent()),
                                    toplevel=True)

        if self.hovered_handle:
            self.hovered_handle.on_click()
            self.__clicked_handle = self.hovered_handle
        elif hovered:
            self._select()
            self.stack.set_cursor("grabbing")
            self.stack.selected_overlay = self
        elif self._is_selected():
            self._deselect()
            self.hovered_handle = None

    def on_button_release(self, cursor_position):
        self.click_source_position = None
        self.update_from_source()
        self.on_hover(cursor_position)

        self.__action_log.commit("Video position change")
        if self.__clicked_handle:
            if not self.__clicked_handle.hovered:
                self.stack.reset_cursor()
            self.__clicked_handle.on_release()
            self.__clicked_handle = None
        elif self._is_hovered():
            self.stack.set_cursor("grab")

        self._source.connect("deep-notify", self.__source_property_changed_cb)
        self.queue_draw()

    def __source_property_changed_cb(self, unused_source, unused_gstelement,
                                     unused_pspec):
        self.update_from_source()

    def on_motion_notify(self, cursor_pos):
        click_to_cursor = self.stack.get_normalized_drag_distance(cursor_pos)
        if self.__clicked_handle:
            # Resize Box / Use Handle
            self.__clicked_handle.on_drag(click_to_cursor)
            self.__update_edges_from_corners()

            # We only need to change translation coordinates in the source for resizing
            # when handle does not return NULL for get_source_position
            source_position = self.__clicked_handle.get_source_position()
            if isinstance(source_position, numpy.ndarray):
                self.__set_source_position(source_position)

            self.__set_source_size(self.__get_size_stream())
            self.__update_handle_sizes()
        else:
            # Move Box
            stream_position = self.click_source_position + click_to_cursor * self.project_size
            self.__set_position(stream_position / self.project_size)
            self.__set_source_position(stream_position)
        self.queue_draw()
        self._commit()

    def on_hover(self, cursor_pos):
        if not self.is_visible():
            return False

        # Check if one of the handles is hovered.
        self.hovered_handle = None
        if self._is_selected():
            for handle in self.handles.values():
                handle.on_hover(cursor_pos)
                if handle.hovered:
                    self.hovered_handle = handle
            if self.hovered_handle:
                self._hover()
                self.queue_draw()
                return True

        # Check if self is hovered
        source = self.__get_normalized_source_position()
        cursor = self.stack.get_normalized_cursor_position(cursor_pos)
        if (source < cursor).all() and (cursor < source + self.__get_size()).all():
            self.stack.set_cursor("grab")
            self._hover()
        else:
            self.unhover()

        self.queue_draw()
        return self._is_hovered()

    def unhover(self):
        if self.hovered_handle:
            self.hovered_handle.on_hover(None)
        Overlay.unhover(self)

    def update_from_source(self):
        self.__set_size(self.__get_source_size() / self.project_size)
        self.__set_position(self.__get_source_position() / self.project_size)
        self.__reset_handle_sizes()
        self.queue_draw()

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

        if selected:
            for handle in self.handles.values():
                handle.draw(cr)
