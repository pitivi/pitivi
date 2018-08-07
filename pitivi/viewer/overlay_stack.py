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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import numpy
from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gtk

from pitivi.utils.loggable import Loggable
from pitivi.viewer.move_scale_overlay import MoveScaleOverlay
from pitivi.viewer.title_overlay import TitleOverlay


class OverlayStack(Gtk.Overlay, Loggable):
    """Manager for the viewer overlays."""

    def __init__(self, app, sink_widget):
        Gtk.Overlay.__init__(self)
        Loggable.__init__(self)
        self.__overlays = {}
        self.__visible_overlays = []
        self.__hide_all_overlays = False
        self.app = app
        self.window_size = numpy.array([1, 1])
        self.click_position = None
        self.hovered_overlay = None
        self.selected_overlay = None
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.SCROLL_MASK |
                        Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK |
                        Gdk.EventMask.ALL_EVENTS_MASK)
        self.add(sink_widget)
        self.connect("size-allocate", self.__on_size_allocate)

        box = Gtk.Box()
        self.resize_status = Gtk.Label(name="resize_status")
        box.pack_start(self.resize_status, True, True, 0)
        self.add_overlay(box)

    def __on_size_allocate(self, widget, rectangle):
        self.window_size = numpy.array([rectangle.width,
                                        rectangle.height])
        for overlay in self.__overlays.values():
            overlay.update_from_source()

    def __overlay_for_source(self, source):
        if source in self.__overlays:
            return self.__overlays[source]

        if type(source) == GES.TitleSource:
            overlay = TitleOverlay(self, source)
        else:
            overlay = MoveScaleOverlay(self, self.app.action_log, source)
        self.add_overlay(overlay)
        self.__overlays[source] = overlay
        return overlay

    def do_event(self, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            cursor_position = numpy.array([event.x, event.y])
            self.click_position = None
            if self.selected_overlay:
                self.selected_overlay.on_button_release(cursor_position)
            # reset the cursor if we are outside of the viewer
            if (cursor_position < numpy.zeros(2)).any() or (cursor_position > self.window_size).any():
                self.reset_cursor()
        elif event.type == Gdk.EventType.LEAVE_NOTIFY and event.mode == Gdk.CrossingMode.NORMAL:
            # If we have a click position, the user is dragging, so we don't want to lose focus and return
            if isinstance(self.click_position, numpy.ndarray):
                return
            for overlay in self.__overlays.values():
                overlay.unhover()
            self.reset_cursor()
        elif event.type == Gdk.EventType.BUTTON_PRESS:
            self.click_position = numpy.array([event.x, event.y])
            if self.hovered_overlay:
                self.hovered_overlay.on_button_press()
            elif self.selected_overlay:
                self.selected_overlay.on_button_press()
        elif event.type == Gdk.EventType.MOTION_NOTIFY:
            cursor_position = numpy.array([event.x, event.y])

            if isinstance(self.click_position, numpy.ndarray):
                if self.selected_overlay:
                    self.selected_overlay.on_motion_notify(cursor_position)
            else:

                # Prioritize Handles
                if isinstance(self.selected_overlay, MoveScaleOverlay):
                    if self.selected_overlay.on_hover(cursor_position):
                        if self.selected_overlay.hovered_handle:
                            self.hovered_overlay = self.selected_overlay
                            return

                for overlay in self.__visible_overlays:
                    if overlay.on_hover(cursor_position):
                        self.hovered_overlay = overlay
                        break
                if not self.hovered_overlay:
                    self.reset_cursor()
        elif event.type == Gdk.EventType.SCROLL:
            # TODO: Viewer zoom
            pass
        return True

    def set_current_sources(self, sources):
        self.__visible_overlays = []
        # check if source has instanced viewer
        for source in sources:
            overlay = self.__overlay_for_source(source)
            self.__visible_overlays.append(overlay)
        # check if viewer should be visible
        if not self.__hide_all_overlays:
            for source, overlay in self.__overlays.items():
                if source in sources:
                    overlay.show()
                else:
                    overlay.hide()

    def update(self, source):
        self.__overlays[source].update_from_source()

    def select(self, source):
        self.selected_overlay = self.__overlay_for_source(source)
        self.selected_overlay.queue_draw()

    def hide_overlays(self):
        if not self.__hide_all_overlays:
            for overlay in self.__visible_overlays:
                overlay.hide()
            self.__hide_all_overlays = True

    def show_overlays(self):
        if self.__hide_all_overlays:
            for overlay in self.__visible_overlays:
                overlay.show()
            self.__hide_all_overlays = False

    def set_cursor(self, name):
        cursor = None
        display = Gdk.Display.get_default()
        try:
            cursor = Gdk.Cursor.new_from_name(display, name)
        except TypeError:
            self.warning("Cursor '%s' not found.", name)
        self.app.gui.get_window().set_cursor(cursor)

    def reset_cursor(self):
        self.app.gui.get_window().set_cursor(None)

    def get_drag_distance(self, cursor_position):
        return cursor_position - self.click_position

    def get_normalized_drag_distance(self, cursor_position):
        return self.get_drag_distance(cursor_position) / self.window_size

    def get_normalized_cursor_position(self, cursor_position):
        return cursor_position / self.window_size
