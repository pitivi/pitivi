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

from pitivi.utils.loggable import Loggable
# from pitivi.configure import get_ui_dir


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

    PIXBUF = None

    def __init__(self, app):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)
        self.app = app
        self.source = None
        self._project = None
        self._selection = None
        self._selected_clip = None
        self._cr = None
        self._mouse_x = 0
        self._mouse_y = 0

        self._setting_props = False
        self._children_props_handler = None

        self.builder = Gtk.Builder()

        self.connect('button-release-event', self._button_release_event_cb)
        self.connect('motion-notify-event', self._motion_notify_event_cb)

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
        self.source.connect("deep-notify", self.__source_property_changed_cb)

    def _set_clip_width_height(self, new_width, new_height):
        # Set the new width of the clip
        self.source.set_child_property("width", new_width)
        # Set the new height of the clip
        self.source.set_child_property("height", new_height)
        self.source.connect("deep-notify", self.__source_property_changed_cb)

    def _placeholder_cb(self, junk1, junk2, junk3):
        pass

    def __draw_rectangle(self, cr, x, y, w, h):
        cr.rectangle(x, y, w, h)

    def _button_release_event_cb(self, widget, event):
        self._mouse_x = event.x
        self._mouse_y = event.y
        print(event.x, event.y)

    def _motion_notify_event_cb(self, widget, event):
        self._mouse_x = event.x
        self._mouse_y = event.y
        self.queue_draw()

    def do_draw(self, cr):
        self._cr = cr
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        x = 100
        y = 100
        w = 160
        h = 120
        cr.set_source_rgb(1, 1, 1)
        cr.move_to(180, 90)
        cr.line_to(180, 110)

        cr.move_to(180, 210)
        cr.line_to(180, 230)

        cr.move_to(90, 160)
        cr.line_to(110, 160)

        cr.move_to(250, 160)
        cr.line_to(270, 160)

        cr.move_to(100, 100)
        cr.line_to(100, 60)

        cr.move_to(100, 100)
        cr.line_to(60, 100)

        cr.move_to(100, 220)
        cr.line_to(100, 260)

        cr.move_to(100, 220)
        cr.line_to(60, 220)

        cr.move_to(260, 100)
        cr.line_to(260, 60)

        cr.move_to(260, 100)
        cr.line_to(300, 100)

        cr.move_to(260, 220)
        cr.line_to(300, 220)

        cr.move_to(260, 220)
        cr.line_to(260, 260)

        self.__draw_rectangle(cr, x, y, w, h)
        cr.stroke()

        # highlight selected area
        # if 100 < self._mouse_x <= 153 and 60 < self._mouse_y <= 99:
        #     self.__draw_rectangle(cr, 100, 40, 80, 60)
        # if 100 < self._mouse_x <= 153 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 100, 130, 80, 60)
        # if 100 < self._mouse_x <= 153 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 100, 160, 80, 60)
        # if 100 < self._mouse_x <= 153 and 100 < self._mouse_y <= 140:
        #     self.__draw_rectangle(cr, 100, 100, 80, 60)
        # if 100 < self._mouse_x <= 153 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 100, 130, 80, 60)
        # if 100 < self._mouse_x <= 153 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 100, 160, 80, 60)
        # if 100 < self._mouse_x <= 153 and 221 < self._mouse_y <= 280:
        #     self.__draw_rectangle(cr, 100, 220, 80, 60)

        # if 20 < self._mouse_x <= 100 and 60 < self._mouse_y <= 99:
        #     self.__draw_rectangle(cr, 20, 40, 80, 60)
        # if 20 < self._mouse_x <= 100 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 20, 130, 80, 60)
        # if 20 < self._mouse_x <= 100 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 20, 160, 80, 60)
        # if 20 < self._mouse_x <= 100 < self._mouse_y <= 140:
        #     self.__draw_rectangle(cr, 20, 100, 80, 60)
        # if 20 < self._mouse_x <= 100 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 20, 130, 80, 60)
        # if 20 < self._mouse_x <= 100 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 20, 160, 80, 60)
        # if 20 < self._mouse_x <= 100 and 221 < self._mouse_y <= 280:
        #     self.__draw_rectangle(cr, 20, 220, 80, 60)

        # if 154 < self._mouse_x <= 204 and 60 < self._mouse_y <= 99:
        #     self.__draw_rectangle(cr, 140, 40, 80, 60)
        # if 154 < self._mouse_x <= 204 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 140, 130, 80, 60)
        # if 154 < self._mouse_x <= 204 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 140, 160, 80, 60)
        # if 154 < self._mouse_x <= 204 and 100 < self._mouse_y <= 140:
        #     self.__draw_rectangle(cr, 140, 100, 80, 60)
        # if 154 < self._mouse_x <= 204 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 140, 130, 80, 60)
        # if 154 < self._mouse_x <= 204 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 140, 160, 80, 60)
        # if 154 < self._mouse_x <= 204 and 221 < self._mouse_y <= 280:
        #     self.__draw_rectangle(cr, 140, 220, 80, 60)

        # if 205 < self._mouse_x <= 260 and 60 < self._mouse_y <= 99:
        #     self.__draw_rectangle(cr, 180, 40, 80, 60)
        # if 205 < self._mouse_x <= 260 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 180, 130, 80, 60)
        # if 205 < self._mouse_x <= 260 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 180, 160, 80, 60)
        # if 205 < self._mouse_x <= 260 and 100 < self._mouse_y <= 140:
        #     self.__draw_rectangle(cr, 180, 100, 80, 60)
        # if 205 < self._mouse_x <= 260 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 180, 130, 80, 60)
        # if 205 < self._mouse_x <= 260 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 180, 160, 80, 60)
        # if 205 < self._mouse_x <= 260 and 221 < self._mouse_y <= 280:
        #     self.__draw_rectangle(cr, 180, 220, 80, 60)

        # if 261 < self._mouse_x <= 320 and 60 < self._mouse_y <= 99:
        #     self.__draw_rectangle(cr, 261, 40, 80, 60)
        # if 261 < self._mouse_x <= 320 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 261, 130, 80, 60)
        # if 261 < self._mouse_x <= 320 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 261, 160, 80, 60)
        # if 261 < self._mouse_x <= 320 and 100 < self._mouse_y <= 140:
        #     self.__draw_rectangle(cr, 261, 100, 80, 60)
        # if 261 < self._mouse_x <= 320 and 141 < self._mouse_y <= 181:
        #     self.__draw_rectangle(cr, 261, 130, 80, 60)
        # if 261 < self._mouse_x <= 320 and 182 < self._mouse_y <= 221:
        #     self.__draw_rectangle(cr, 261, 160, 80, 60)
        # if 261 < self._mouse_x <= 320 and 221 < self._mouse_y <= 280:
        #     self.__draw_rectangle(cr, 261, 220, 80, 60)

        current_box, x, y = self.get_cursor_positons()
        if current_box is not None:
            self.__draw_rectangle(cr, x, y, 80, 60)

            cr.set_source_rgb(1, 0.1, 0)
            cr.fill()
            cr.stroke()

    def get_cursor_positons(self):
        """Returns position of mouse and which box it is located in.

        Format:
        1) [x,y] - which box it cursor is in in x,y format
        2) x - x axis point for top left of rectangle to be drawn.
        3) y - y axis point for top left of rectangle to be drawn.
        """
        if 20 < self._mouse_x <= 100 and 60 < self._mouse_y <= 99:
            return [1, 1], 20, 40
        if 20 < self._mouse_x <= 100 < self._mouse_y <= 140:
            return [1, 2], 20, 80
        if 20 < self._mouse_x <= 100 and 141 < self._mouse_y <= 181:
            return [1, 3], 20, 130
        if 20 < self._mouse_x <= 100 and 182 < self._mouse_y <= 221:
            return [1, 4], 20, 160
        if 20 < self._mouse_x <= 100 and 221 < self._mouse_y <= 280:
            return [1, 5], 20, 220

        if 100 < self._mouse_x <= 153 and 60 < self._mouse_y <= 99:
            return [2, 1], 100, 40
        if 100 < self._mouse_x <= 153 and 100 < self._mouse_y <= 140:
            return [2, 2], 100, 100
        if 100 < self._mouse_x <= 153 and 141 < self._mouse_y <= 181:
            return [2, 3], 100, 130
        if 100 < self._mouse_x <= 153 and 182 < self._mouse_y <= 221:
            return [2, 4], 100, 160
        if 100 < self._mouse_x <= 153 and 221 < self._mouse_y <= 280:
            return [2, 5], 100, 220

        if 154 < self._mouse_x <= 204 and 60 < self._mouse_y <= 99:
            return [3, 1], 140, 40
        if 154 < self._mouse_x <= 204 and 141 < self._mouse_y <= 181:
            return [3, 2], 140, 130
        if 154 < self._mouse_x <= 204 and 182 < self._mouse_y <= 221:
            return [3, 3], 140, 160
        if 154 < self._mouse_x <= 204 and 100 < self._mouse_y <= 140:
            return [3, 4], 140, 100
        if 154 < self._mouse_x <= 204 and 221 < self._mouse_y <= 280:
            return [3, 5], 140, 220

        if 205 < self._mouse_x <= 260 and 60 < self._mouse_y <= 99:
            return [4, 1], 180, 40
        if 205 < self._mouse_x <= 260 and 100 < self._mouse_y <= 140:
            return [4, 2], 180, 100
        if 205 < self._mouse_x <= 260 and 141 < self._mouse_y <= 181:
            return [4, 3], 180, 130
        if 205 < self._mouse_x <= 260 and 182 < self._mouse_y <= 221:
            return [4, 3], 180, 160
        if 205 < self._mouse_x <= 260 and 221 < self._mouse_y <= 280:
            return [4, 5], 180, 220

        if 261 < self._mouse_x <= 320 and 60 < self._mouse_y <= 99:
            return [5, 1], 261, 40
        if 261 < self._mouse_x <= 320 and 100 < self._mouse_y <= 140:
            return [5, 2], 261, 100
        if 261 < self._mouse_x <= 320 and 141 < self._mouse_y <= 181:
            return [5, 3], 261, 130
        if 261 < self._mouse_x <= 320 and 182 < self._mouse_y <= 221:
            return [5, 4], 261, 160
        if 261 < self._mouse_x <= 320 and 221 < self._mouse_y <= 280:
            return [5, 5], 261, 220

        return None, 0, 0

    def __set_source(self, source):
        self.source = source

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
        video_height = self._get_clip_width_height()[1] * .8
        video_width = self._get_clip_width_height()[0] * .8
        middle_x = video_width / 2
        middle_y = video_height / 2
        # Set all the values for the left, outside the viewer
        Position.TOP_LEFT_CORNER_OUT = (-video_width, -video_height)
        Position.LEFT_TOP_OUT = (-video_width, 0)
        Position.LEFT_CENTER_OUT = (-video_width, project_height / 2 - middle_y)
        Position.LEFT_BOTTOM_OUT = (-video_width, project_height - video_height)
        Position.BOTTOM_LEFT_CORNER_OUT = (-video_width, video_height)
        # Set all the values for the right, outside the viewer
        Position.TOP_RIGHT_CORNER_OUT = (project_width, -video_height)
        Position.RIGHT_TOP_OUT = (project_width, -video_height)
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
        Position.BOTTOM_CENTER = (middle_x, project_height - middle_y * 2)
        Position.BOTTOM_RIGHT = (project_width - video_width, project_height - video_height)
