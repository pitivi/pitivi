# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Jackson Eickhoff <jacksoneick@gmail.com>
# Copyright (c) 2020, Tanner Skelton <tskelton@huskers.unl.edu>
# Copyright (c) 2020, Cordell Rhoads <rhoadscordell7@gmail.com>
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
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

from pitivi.utils.loggable import Loggable


class AlignmentEditor(Gtk.EventBox, Loggable):
    """Widget for aligning a video clip.

    Attributes:
        app (Pitivi): The app.
        _project (Project): The project.
    """

    __gtype_name__ = "AlignmentEditor"

    __gsignals__ = {
        "align": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)
        self._hovered_box = None

        self.connect("button-release-event", self._button_release_event_cb)
        self.connect("motion-notify-event", self._motion_notify_event_cb)
        self.connect("leave-notify-event", self._leave_notify_event_cb)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)

    def _leave_notify_event_cb(self, unused_widget, _):
        self._hovered_box = None
        self.queue_draw()

    def _button_release_event_cb(self, widget, event):
        if not self._hovered_box:
            return
        self.emit("align")

    def get_clip_position(self, project, source):
        """Returns corresponding clip position in the viewer."""
        clip_width = source.get_child_property("width").value
        clip_height = source.get_child_property("height").value
        x = self.__calculate_clip_position(self._hovered_box[0], clip_width, project.videowidth)
        y = self.__calculate_clip_position(self._hovered_box[1], clip_height, project.videoheight)

        return x, y

    def __calculate_clip_position(self, index, clip_size, project_size):
        if index == 0:
            coordinate = -clip_size
        elif index == 1:
            coordinate = -clip_size / 2
        elif index == 2:
            coordinate = 0
        elif index == 3:
            coordinate = project_size / 2 - clip_size / 2
        elif index == 4:
            coordinate = project_size - clip_size
        elif index == 5:
            coordinate = project_size - clip_size / 2
        elif index == 6:
            coordinate = project_size
        else:
            coordinate = 0

        return int(coordinate)

    def _motion_notify_event_cb(self, widget, event):
        hovered_box = self._get_box(event.x, event.y)
        if hovered_box != self._hovered_box:
            self._hovered_box = hovered_box
            self.queue_draw()

    def get_used_size(self):
        """Returns the size used for drawing.

        For drawing pixel perfect lines, we need to be able to divide
        the width and height between four boxes and three 1px lines,
        such that the box size is an int value:

            box_size + 1 + box_size + 1 + box_size + 1 + box_size
        """
        box_width = ((self.get_allocated_width() - 3) // 4)
        box_height = ((self.get_allocated_height() - 3) // 4)
        width = box_width * 4 + 3
        height = box_height * 4 + 3
        return width, height, box_width, box_height

    def do_draw(self, cr):
        width, height, box_width, box_height = self.get_used_size()

        self._draw_frame(cr, width, height)

        # Highlight the box that the cursor is hovering over
        if self._hovered_box:
            x = width / 8 * self._hovered_box[0]
            y = height / 8 * self._hovered_box[1]
            cr.rectangle(x, y, box_width, box_height)

            color = self.get_style_context().get_color(Gtk.StateFlags.LINK)
            cr.set_source_rgba(color.red, color.green, color.blue, 0.7)
            cr.set_line_width(1)
            cr.fill()
            cr.stroke()

    def _draw_frame(self, cr, width, height):
        # How far the line should be displaced from the edge of the widget
        line_offset_x = (width - 3) / 4 + 0.5
        line_offset_y = (height - 3) / 4 + 0.5

        cr.move_to(0, line_offset_y)
        cr.line_to(width, line_offset_y)

        cr.move_to(0, height - line_offset_y)
        cr.line_to(width, height - line_offset_y)

        cr.move_to(line_offset_x, 0)
        cr.line_to(line_offset_x, height)

        cr.move_to(width - line_offset_x, 0)
        cr.line_to(width - line_offset_x, height)

        color = self.get_style_context().get_color(Gtk.StateFlags.ACTIVE)
        cr.set_source_rgba(color.red, color.green, color.blue, 0.6)
        cr.set_line_width(1)
        cr.stroke()

        # cr.rectangle(line_offset_x + 0.5, line_offset_y + 0.5, width - line_offset_x * 2 - 1, height - line_offset_y * 2 - 1)
        cr.rectangle(line_offset_x, line_offset_y, width - line_offset_x * 2, height - line_offset_y * 2)

        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        cr.set_line_width(2)
        cr.stroke()

    def _get_box(self, x, y):
        """Returns the box containing the specified pixel."""
        width, height, _, _ = self.get_used_size()

        box_x = int(x * 7 / width)
        box_y = int(y * 7 / height)

        if box_x < 0 or box_x > 6 or box_y < 0 or box_y > 6:
            return None

        return box_x, box_y
