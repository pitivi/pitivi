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

    def _get_clip_size(self):
        width = self.source.get_child_property("width").value
        height = self.source.get_child_property("height").value
        return width, height

    def _set_clip_position(self, new_x, new_y):
        # Set the posx of the clip
        self.source.set_child_property("posx", new_x)
        # Set the posy of the clip
        self.source.set_child_property("posy", new_y)

    def _set_clip_size(self, width, height):
        self.source.set_child_property("width", width)
        self.source.set_child_property("height", height)

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
        # print(event.x, event.y)
        self.queue_draw()

    def do_draw(self, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        # Determine what color to draw widget depending on Pitivi theme
        if self.app.settings.useDarkTheme:
            cr.set_source_rgb(1, 1, 1)
        else:
            cr.set_source_rgb(0, 0, 0)
        self._draw_frame(cr, width, height)
        cr.stroke()

        # Highlight the box that the cursor is hovering over
        current_box, x, y = self.get_cursor_positons()
        if current_box is not None:
            self.__draw_rectangle(cr, x, y, width / 4, height / 4)
            cr.set_source_rgb(1, 0.1, 0)
            cr.fill()
            cr.stroke()

    def _draw_frame(self, cr, width, height):
        print('draw ', height)
        self.set_margin_start(width * 0.1)
        self.set_margin_end(width * 0.1)
        self.set_margin_top(height * 0.1)
        self.set_margin_bottom(height * 0.1)
        # How far the line should be displaced from the edge of the widget
        line_offset_x = width * 0.25
        line_offset_y = height * 0.25

        cr.move_to(0, line_offset_y)
        cr.line_to(width - 0, line_offset_y)

        cr.move_to(0, height - line_offset_y)
        cr.line_to(width - 0, height - line_offset_y)

        cr.move_to(line_offset_x, 0)
        cr.line_to(line_offset_x, height - 0)

        cr.move_to(width - line_offset_x, 0)
        cr.line_to(width - line_offset_x, height - 0)

        cr.stroke()

    def get_cursor_positons(self):
        """Returns position of mouse and which box it is located in.

        Format:
        1) [x,y] - which box it cursor is in in x,y format
        2) x - x axis point for top left of rectangle to be drawn.
        3) y - y axis point for top left of rectangle to be drawn.
        """
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        print(height)
        # Sizes of selection areas that the mouse will hover over
        selection_width = width / 7
        selection_height = height / 7
        box_size = (width / 4, height / 4)   # Size of box that will be drawn
        # Column 0
        if 0 < self._mouse_x <= selection_width and 0 < self._mouse_y <= selection_height:
            return (0, 0), 0, 0
        if 0 < self._mouse_x <= selection_width and selection_height < self._mouse_y <= selection_height * 2:
            return (0, 1), 0, box_size[1] / 2
        if 0 < self._mouse_x <= selection_width and selection_height * 2 < self._mouse_y <= selection_height * 3:
            return (0, 2), 0, box_size[1]
        if 0 < self._mouse_x <= selection_width and selection_height * 3 < self._mouse_y <= selection_height * 4:
            return (0, 3), 0, box_size[1] * 1.5
        if 0 < self._mouse_x <= selection_width and selection_height * 4 < self._mouse_y <= selection_height * 5:
            return (0, 4), 0, box_size[1] * 2
        if 0 < self._mouse_x <= selection_width and selection_height * 5 < self._mouse_y <= selection_height * 6:
            return (0, 5), 0, box_size[1] * 2.5
        if 0 < self._mouse_x <= selection_width and selection_height * 6 < self._mouse_y <= selection_height * 7:
            return (0, 6), 0, box_size[1] * 3
        # Column 1
        if selection_width < self._mouse_x <= selection_width * 2 and 0 < self._mouse_y <= selection_height:
            return (1, 0), box_size[0] / 2, 0
        if selection_width < self._mouse_x <= selection_width * 2 and selection_height < self._mouse_y <= selection_height * 2:
            return (1, 1), box_size[0] / 2, box_size[1] / 2
        if selection_width < self._mouse_x <= selection_width * 2 and selection_height * 2 < self._mouse_y <= selection_height * 3:
            return (1, 2), box_size[0] / 2, box_size[1]
        if selection_width < self._mouse_x <= selection_width * 2 and selection_height * 3 < self._mouse_y <= selection_height * 4:
            return (1, 3), box_size[0] / 2, box_size[1] * 1.5
        if selection_width < self._mouse_x <= selection_width * 2 and selection_height * 4 < self._mouse_y <= selection_height * 5:
            return (1, 4), box_size[0] / 2, box_size[1] * 2
        if selection_width < self._mouse_x <= selection_width * 2 and selection_height * 5 < self._mouse_y <= selection_height * 6:
            return (1, 5), box_size[0] / 2, box_size[1] * 2.5
        if selection_width < self._mouse_x <= selection_width * 2 and selection_height * 6 < self._mouse_y <= selection_height * 7:
            return (1, 6), box_size[0] / 2, box_size[1] * 3
        # Column 2
        if selection_width * 2 < self._mouse_x <= selection_width * 3 and 0 < self._mouse_y <= selection_height:
            return (2, 0), box_size[0], 0
        if selection_width * 2 < self._mouse_x <= selection_width * 3 and selection_height < self._mouse_y <= selection_height * 2:
            return (2, 1), box_size[0], box_size[1] / 2
        if selection_width * 2 < self._mouse_x <= selection_width * 3 and selection_height * 2 < self._mouse_y <= selection_height * 3:
            return (2, 2), box_size[0], box_size[1]
        if selection_width * 2 < self._mouse_x <= selection_width * 3 and selection_height * 3 < self._mouse_y <= selection_height * 4:
            return (2, 3), box_size[0], box_size[1] * 1.5
        if selection_width * 2 < self._mouse_x <= selection_width * 3 and selection_height * 4 < self._mouse_y <= selection_height * 5:
            return (2, 4), box_size[0], box_size[1] * 2
        if selection_width * 2 < self._mouse_x <= selection_width * 3 and selection_height * 5 < self._mouse_y <= selection_height * 6:
            return (2, 5), box_size[0], box_size[1] * 2.5
        if selection_width * 2 < self._mouse_x <= selection_width * 3 and selection_height * 6 < self._mouse_y <= selection_height * 7:
            return (2, 6), box_size[0], box_size[1] * 3
        # Column 3
        if selection_width * 3 < self._mouse_x <= selection_width * 4 and 0 < self._mouse_y <= selection_height:
            return (3, 0), box_size[0] * 1.5, 0
        if selection_width * 3 < self._mouse_x <= selection_width * 4 and selection_height < self._mouse_y <= selection_height * 2:
            return (3, 1), box_size[0] * 1.5, box_size[1] / 2
        if selection_width * 3 < self._mouse_x <= selection_width * 4 and selection_height * 2 < self._mouse_y <= selection_height * 3:
            return (3, 2), box_size[0] * 1.5, box_size[1]
        if selection_width * 3 < self._mouse_x <= selection_width * 4 and selection_height * 3 < self._mouse_y <= selection_height * 4:
            return (3, 3), box_size[0] * 1.5, box_size[1] * 1.5
        if selection_width * 3 < self._mouse_x <= selection_width * 4 and selection_height * 4 < self._mouse_y <= selection_height * 5:
            return (3, 4), box_size[0] * 1.5, box_size[1] * 2
        if selection_width * 3 < self._mouse_x <= selection_width * 4 and selection_height * 5 < self._mouse_y <= selection_height * 6:
            return (3, 5), box_size[0] * 1.5, box_size[1] * 2.5
        if selection_width * 3 < self._mouse_x <= selection_width * 4 and selection_height * 6 < self._mouse_y <= selection_height * 7:
            return (3, 6), box_size[0] * 1.5, box_size[1] * 3
        # Column 4
        if selection_width * 4 < self._mouse_x <= selection_width * 5 and 0 < self._mouse_y <= selection_height:
            return (4, 0), box_size[0] * 2, 0
        if selection_width * 4 < self._mouse_x <= selection_width * 5 and selection_height < self._mouse_y <= selection_height * 2:
            return (4, 1), box_size[0] * 2, box_size[1] / 2
        if selection_width * 4 < self._mouse_x <= selection_width * 5 and selection_height * 2 < self._mouse_y <= selection_height * 3:
            return (4, 2), box_size[0] * 2, box_size[1]
        if selection_width * 4 < self._mouse_x <= selection_width * 5 and selection_height * 3 < self._mouse_y <= selection_height * 4:
            return (4, 3), box_size[0] * 2, box_size[1] * 1.5
        if selection_width * 4 < self._mouse_x <= selection_width * 5 and selection_height * 4 < self._mouse_y <= selection_height * 5:
            return (4, 4), box_size[0] * 2, box_size[1] * 2
        if selection_width * 4 < self._mouse_x <= selection_width * 5 and selection_height * 5 < self._mouse_y <= selection_height * 6:
            return (4, 5), box_size[0] * 2, box_size[1] * 2.5
        if selection_width * 4 < self._mouse_x <= selection_width * 5 and selection_height * 6 < self._mouse_y <= selection_height * 7:
            return (4, 6), box_size[0] * 2, box_size[1] * 3
        # Column 5
        if selection_width * 5 < self._mouse_x <= selection_width * 6 and 0 < self._mouse_y <= selection_height:
            return (5, 0), box_size[0] * 2.5, 0
        if selection_width * 5 < self._mouse_x <= selection_width * 6 and selection_height < self._mouse_y <= selection_height * 2:
            return (5, 1), box_size[0] * 2.5, box_size[1] / 2
        if selection_width * 5 < self._mouse_x <= selection_width * 6 and selection_height * 2 < self._mouse_y <= selection_height * 3:
            return (5, 2), box_size[0] * 2.5, box_size[1]
        if selection_width * 5 < self._mouse_x <= selection_width * 6 and selection_height * 3 < self._mouse_y <= selection_height * 4:
            return (5, 3), box_size[0] * 2.5, box_size[1] * 1.5
        if selection_width * 5 < self._mouse_x <= selection_width * 6 and selection_height * 4 < self._mouse_y <= selection_height * 5:
            return (5, 4), box_size[0] * 2.5, box_size[1] * 2
        if selection_width * 5 < self._mouse_x <= selection_width * 6 and selection_height * 5 < self._mouse_y <= selection_height * 6:
            return (5, 5), box_size[0] * 2.5, box_size[1] * 2.5
        if selection_width * 5 < self._mouse_x <= selection_width * 6 and selection_height * 6 < self._mouse_y <= selection_height * 7:
            return (5, 6), box_size[0] * 2.5, box_size[1] * 3
        # Column 6
        if selection_width * 6 < self._mouse_x <= selection_width * 7 and 0 < self._mouse_y <= selection_height:
            return (6, 0), box_size[0] * 3, 0
        if selection_width * 6 < self._mouse_x <= selection_width * 7 and selection_height < self._mouse_y <= selection_height * 2:
            return (6, 1), box_size[0] * 3, box_size[1] / 2
        if selection_width * 6 < self._mouse_x <= selection_width * 7 and selection_height * 2 < self._mouse_y <= selection_height * 3:
            return (6, 2), box_size[0] * 3, box_size[1]
        if selection_width * 6 < self._mouse_x <= selection_width * 7 and selection_height * 3 < self._mouse_y <= selection_height * 4:
            return (6, 3), box_size[0] * 3, box_size[1] * 1.5
        if selection_width * 6 < self._mouse_x <= selection_width * 7 and selection_height * 4 < self._mouse_y <= selection_height * 5:
            return (6, 4), box_size[0] * 3, box_size[1] * 2
        if selection_width * 6 < self._mouse_x <= selection_width * 7 and selection_height * 5 < self._mouse_y <= selection_height * 6:
            return (6, 5), box_size[0] * 3, box_size[1] * 2.5
        if selection_width * 6 < self._mouse_x <= selection_width * 7 and selection_height * 6 < self._mouse_y <= selection_height * 7:
            return (6, 6), box_size[0] * 3, box_size[1] * 3

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
