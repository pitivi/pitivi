# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2012, Matas Brazdeikis <matas@brazdeikis.lt>
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
from gi.repository import GES
from gi.repository import Gtk

from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable


class Position:
    """Object for configuring the values for alignment. Each Variable should contain a tuple after being set: x, y."""

    TOP_LEFT_CORNER_OUT = None  # Top Left corner, out of the viewer
    LEFT_TOP_OUT = None  # Left, Top out of viewer
    LEFT_CENTER_OUT = None  # Left, Center out of viewer
    LEFT_BOTTOM_OUT = None  # Left, Bottom out of viewer
    BOTTOM_LEFT_CORNER_OUT = None  # Bottom, Left out of viewer

    TOP_RIGHT_CORNER_OUT = None  # Top Right corner, out of the viewer
    RIGHT_TOP_OUT = None  # Right, Top out of viewer
    RIGHT_CENTER_OUT = None  # Right, Center out of viewer
    RIGHT_BOTTOM_OUT = None  # Right, Bottom out of viwer
    BOTTOM_RIGHT_CORNER_OUT = None  # Bottom Right corner

    TOP_LEFT_OUT = None  # Top Center Left, out of viewer
    TOP_CENTER_OUT = None  # Top Center, out of viewer
    TOP_RIGHT_OUT = None  # Top Center Right, out of viewer

    BOTTOM_LEFT_OUT = None  # Bottom Center Left, out of viewer
    BOTTOM_CENTER_OUT = None  # Bottom Center, out of viewer
    BOTTOM_RIGHT_OUT = None  # Bottom Center Right, out of viewer

    TOP_LEFT = None  # Top Left, inside the viewer
    TOP_CENTER = None  # Top Center, inside the viewer
    TOP_RIGHT = None  # Top right, inside the viewer
    LEFT_CENTER = None  # Left Center, inside the viewer
    CENTER = None  # Center, inside the viewer
    RIGHT_CENTER = None  # Right Center, inside the viewer
    BOTTOM_LEFT = None  # Bottom Left, inside the viewer
    BOTTOM_CENTER = None  # Bottom Center, inside the viewer
    BOTTOM_RIGHT = None  # Bottom Right, inside the viewer


class AlignmentEditor(Gtk.EventBox, Loggable):
    """Widget for configuring a title.

    Attributes:
        app (Pitivi): The app.
        _project (Project): The project.
    """

    __gtype_name__ = "AlignmentEditor"

    def __init__(self, app):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)
        self.app = app
        self.source = None
        self._project = None
        self._selection = None
        self._selected_clip = None
        self._mouse_x = 0
        self._mouse_y = 0

        self.connect('button-release-event', self._button_release_event_cb)
        self.connect('motion-notify-event', self._motion_notify_event_cb)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)

        self.app.project_manager.connect_after(
            "new-project-loaded", self._new_project_loaded_cb)

    def _new_project_loaded_cb(self, unused_project_manager, project):
        if self._selection is not None:
            self._selection.disconnect_by_func(self._selection_changed_cb)
            self._selection = None
        if project:
            self._selection = project.ges_timeline.ui.selection
            self._selection.connect('selection-changed', self._selection_changed_cb)
        self._project = project

    def _get_clip_position(self):
        x = self.source.get_child_property("posx").value
        y = self.source.get_child_property("posy").value
        return x, y

    def _get_clip_width_height(self):
        width = self.source.get_child_property("width").value
        height = self.source.get_child_property("height").value
        return width, height

    def _set_clip_position(self, new_x, new_y):
        # Set the posx of the clip
        self.source.set_child_property("posx", new_x)
        # Set the posy of the clip
        self.source.set_child_property("posy", new_y)

    def _set_clip_width_height(self, new_width, new_height):
        # Set the new width of the clip
        self.source.set_child_property("width", new_width)
        # Set the new height of the clip
        self.source.set_child_property("height", new_height)

    def __draw_rectangle(self, cr, x, y, w, h):
        cr.rectangle(x, y, w, h)

    def _button_release_event_cb(self, widget, event):
        selected_box, _, _ = self.get_cursor_positons()
        pipeline = self._project.pipeline
        if selected_box is not None:
            with self.app.action_log.started("update alignment",
                                             finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                             toplevel=True):
                self._set_clip_position(selected_box[0], selected_box[1])
                self._project.pipeline.commit_timeline()

    def _motion_notify_event_cb(self, widget, event):
        self._mouse_x = event.x
        self._mouse_y = event.y
        self.queue_draw()

    def do_draw(self, cr):
        # Determine what color to draw widget depending on Pitivi theme
        if self.app.settings.useDarkTheme:
            cr.set_source_rgb(1, 1, 1)
        else:
            cr.set_source_rgb(0, 0, 0)
        self._draw_frame(cr)
        cr.stroke()

        # Highlight the box that the cursor is hovering over
        current_box, x, y = self.get_cursor_positons()
        if current_box is not None:
            self.__draw_rectangle(cr, x, y, 80, 60)
            cr.set_source_rgb(1, 0.1, 0)
            cr.fill()
            cr.stroke()

    def _draw_frame(self, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        self.set_margin_start(width * 0.1)
        self.set_margin_end(width * 0.1)
        self.set_margin_top(height * 0.1)
        self.set_margin_bottom(height * 0.1)
        # How far the line should be displaced from the edge of the widget
        line_offset = width * (1 / 7)

        cr.move_to(0, line_offset)
        cr.line_to(width - 0, line_offset)

        cr.move_to(0, height - line_offset)
        cr.line_to(width - 0, height - line_offset)

        cr.move_to(line_offset, 0)
        cr.line_to(line_offset, height - 0)

        cr.move_to(width - line_offset, 0)
        cr.line_to(width - line_offset, height - 0)

        cr.stroke()

    def get_cursor_positons(self):
        """Returns position of mouse and which box it is located in.

        Format:
        1) [x,y] - which box it cursor is in in x,y format
        2) x - x axis point for top left of rectangle to be drawn.
        3) y - y axis point for top left of rectangle to be drawn.
        """
        if 20 < self._mouse_x <= 100 and 60 < self._mouse_y <= 99:
            return Position.TOP_LEFT_CORNER_OUT, 20, 40
        if 20 < self._mouse_x <= 100 < self._mouse_y <= 140:
            return Position.LEFT_TOP_OUT, 20, 100
        if 20 < self._mouse_x <= 100 and 141 < self._mouse_y <= 181:
            return Position.LEFT_CENTER_OUT, 20, 130
        if 20 < self._mouse_x <= 100 and 182 < self._mouse_y <= 221:
            return Position.LEFT_BOTTOM_OUT, 20, 160
        if 20 < self._mouse_x <= 100 and 221 < self._mouse_y <= 280:
            return Position.BOTTOM_LEFT_CORNER_OUT, 20, 220

        if 100 < self._mouse_x <= 153 and 60 < self._mouse_y <= 99:
            return Position.TOP_LEFT_OUT, 100, 40
        if 100 < self._mouse_x <= 153 and 100 < self._mouse_y <= 140:
            return Position.TOP_LEFT, 100, 100
        if 100 < self._mouse_x <= 153 and 141 < self._mouse_y <= 181:
            return Position.LEFT_CENTER, 100, 130
        if 100 < self._mouse_x <= 153 and 182 < self._mouse_y <= 221:
            return Position.BOTTOM_LEFT, 100, 160
        if 100 < self._mouse_x <= 153 and 221 < self._mouse_y <= 280:
            return Position.BOTTOM_LEFT_OUT, 100, 220

        if 154 < self._mouse_x <= 204 and 60 < self._mouse_y <= 99:
            return Position.TOP_CENTER_OUT, 140, 40
        if 154 < self._mouse_x <= 204 and 100 < self._mouse_y <= 140:
            return Position.TOP_CENTER, 140, 100
        if 154 < self._mouse_x <= 204 and 141 < self._mouse_y <= 181:
            return Position.CENTER, 140, 130
        if 154 < self._mouse_x <= 204 and 182 < self._mouse_y <= 221:
            return Position.BOTTOM_CENTER, 140, 160
        if 154 < self._mouse_x <= 204 and 221 < self._mouse_y <= 280:
            return Position.BOTTOM_CENTER_OUT, 140, 220

        if 205 < self._mouse_x <= 260 and 60 < self._mouse_y <= 99:
            return Position.TOP_RIGHT_OUT, 180, 40
        if 205 < self._mouse_x <= 260 and 100 < self._mouse_y <= 140:
            return Position.TOP_RIGHT, 180, 100
        if 205 < self._mouse_x <= 260 and 141 < self._mouse_y <= 181:
            return Position.RIGHT_CENTER, 180, 130
        if 205 < self._mouse_x <= 260 and 182 < self._mouse_y <= 221:
            return Position.BOTTOM_RIGHT, 180, 160
        if 205 < self._mouse_x <= 260 and 221 < self._mouse_y <= 280:
            return Position.BOTTOM_RIGHT_OUT, 180, 220

        if 261 < self._mouse_x <= 320 and 60 < self._mouse_y <= 99:
            return Position.TOP_RIGHT_CORNER_OUT, 261, 40
        if 261 < self._mouse_x <= 320 and 100 < self._mouse_y <= 140:
            return Position.RIGHT_TOP_OUT, 261, 100
        if 261 < self._mouse_x <= 320 and 141 < self._mouse_y <= 181:
            return Position.RIGHT_CENTER_OUT, 261, 130
        if 261 < self._mouse_x <= 320 and 182 < self._mouse_y <= 221:
            return Position.RIGHT_BOTTOM_OUT, 261, 160
        if 261 < self._mouse_x <= 320 and 221 < self._mouse_y <= 280:
            return Position.BOTTOM_RIGHT_CORNER_OUT, 261, 220

        return None, 0, 0

    def __set_source(self, source):
        self.source = source
        if self.source:
            self.source.connect("deep-notify", self.__source_property_changed_cb)

    def __source_property_changed_cb(self, unused_source, unused_element, param):
        self._set_object_values()

    def _selection_changed_cb(self, unused_timeline):
        if len(self._selection) == 1:
            clip = list(self._selection)[0]
            source = clip.find_track_element(None, GES.VideoSource)
            if source:
                self._selected_clip = clip
                self.__set_source(source)
                self.app.gui.editor.viewer.overlay_stack.select(source)
                self._set_object_values()
                return

        # Deselect
        if self._selected_clip:
            self._selected_clip = None
            self._project.pipeline.commit_timeline()
        self.__set_source(None)

    def _set_object_values(self):
        # Get all the necessary information
        project_height = self._project.videoheight
        project_width = self._project.videowidth
        video_width, video_height = self._get_clip_size()
        middle_x = video_width / 2
        middle_y = video_height / 2
        # Set all the values for the left, outside the viewer
        Position.TOP_LEFT_CORNER_OUT = (-video_width, -video_height)
        Position.LEFT_TOP_OUT = (-video_width, 0)
        Position.LEFT_CENTER_OUT = (-video_width, project_height / 2 - middle_y)
        Position.LEFT_BOTTOM_OUT = (-video_width, project_height - video_height)
        Position.BOTTOM_LEFT_CORNER_OUT = (-video_width, project_height)
        # Set all the values for the right, outside the viewer
        Position.TOP_RIGHT_CORNER_OUT = (project_width, -video_height)
        Position.RIGHT_TOP_OUT = (project_width, 0)
        Position.RIGHT_CENTER_OUT = (project_width, project_height / 2 - middle_y)
        Position.RIGHT_BOTTOM_OUT = (project_width, project_height - video_height)
        Position.BOTTOM_RIGHT_CORNER_OUT = (project_width, project_height)
        # Set all the values for the top section, outside of the viewer
        Position.TOP_LEFT_OUT = (0, -video_height)
        Position.TOP_CENTER_OUT = (project_width / 2 - middle_x, -video_height)
        Position.TOP_RIGHT_OUT = (project_width - video_width, -video_height)
        # Set all the values for the bottom section, outside of the viewer
        Position.BOTTOM_LEFT_OUT = (0, project_height)
        Position.BOTTOM_CENTER_OUT = (project_width / 2 - middle_x, project_height)
        Position.BOTTOM_RIGHT_OUT = (project_width - video_width, project_height)
        # Set all the values for inside the viewer
        Position.TOP_LEFT = (0, 0)
        Position.TOP_CENTER = (project_width / 2 - middle_x, 0)
        Position.TOP_RIGHT = (project_width - video_width, 0)
        Position.LEFT_CENTER = (0, project_height / 2 - middle_y)
        Position.CENTER = (project_width / 2 - middle_x, project_height / 2 - middle_y)
        Position.RIGHT_CENTER = (project_width - video_width, project_height / 2 - middle_y)
        Position.BOTTOM_LEFT = (0, project_height - video_height)
        Position.BOTTOM_CENTER = (project_width / 2 - middle_x, project_height - middle_y * 2)
        Position.BOTTOM_RIGHT = (project_width - video_width, project_height - video_height)
