# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Millan Castro <m.castrovilarino@gmail.com>
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
'''MarkerBox and Markers '''
import os

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk

from pitivi.configure import get_pixmap_dir
from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import Zoomable

MARKER_WIDTH = 10
MARKER_SEMI_WIDTH = MARKER_WIDTH / 2


# pylint: disable=too-many-instance-attributes
class Marker(Gtk.EventBox, Loggable):
    """Widget representing a marker"""

    def __init__(self, ges_marker):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.ges_marker = ges_marker
        self.position_ns = self.ges_marker.props.position
        self._selected = False
        self._hover = False

        self.__unselect_pixbuf = None
        self.__select_pixbuf = None
        self.__hover_pixbuf = None

        self.image = Gtk.Image()
        self._update_image()
        self.add(self.image)

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("motion-notify-event", self._motion_notify_event_cb)
        self.connect("leave-notify-event", self._leave_notify_event_cb)

    @property
    def position(self):
        """Returns the position of the marker, in nanoseconds."""
        return self.ges_marker.props.position

    def _motion_notify_event_cb(self, widget, event):
        if not self.selected:
            self._hover = True
            self._update_image()

    def _leave_notify_event_cb(self, widget, event):
        if not self.selected:
            self._hover = False
            self._update_image()

    @property
    def selected(self):
        """Gets the selection status"""
        return self._selected

    @selected.setter
    def selected(self, selected):
        if self._selected != selected:
            self._selected = selected
            self._update_image()

    def _update_image(self):
        if not self.selected and self._hover:
            if self.__hover_pixbuf is None:
                self.__hover_pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                    os.path.join(get_pixmap_dir(), "marker-hover.png"))
            self.image.set_from_pixbuf(self.__hover_pixbuf)

        elif not self.selected:
            if self.__unselect_pixbuf is None:
                self.__unselect_pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                    os.path.join(get_pixmap_dir(), "marker-unselect.png"))
            self.image.set_from_pixbuf(self.__unselect_pixbuf)

        else:
            if self.__select_pixbuf is None:
                self.__select_pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                    os.path.join(get_pixmap_dir(), "marker-select.png"))
            self.image.set_from_pixbuf(self.__select_pixbuf)

    @property
    def comment(self):
        """Returns a comment from ges_marker"""
        return self.ges_marker.get_string("comment")

    @comment.setter
    def comment(self, text):
        if text == self.comment:
            return
        self.ges_marker.set_string("comment", text)


class MarkersBox(Gtk.Layout, Zoomable, Loggable):
    """Container for markers"""

    def __init__(self, timeline):
        Gtk.Layout.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.timeline = timeline
        self.hadj = timeline.timeline.hadj
        self.hadj.connect("value-changed", self._hadj_value_changed_cb)
        self.props.hexpand = True
        self.props.valign = Gtk.Align.START

        self.offset = 0
        self.props.height_request = 10

        self.__markers_container = None
        self.marker_selected = None
        self.marker_pressed = None

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)

        self.connect("button-press-event", self._select_marker_cb)
        self.connect("button-release-event", self._unselect_marker_cb)
        self.connect("motion-notify-event", self._move_marker_cb)

        self.text_view = Gtk.TextView()
        self._init_popover()

        self.marker_box = Gtk.EventBox()
        self.marker_box.add(self)
        self.marker_box.get_style_context().add_class("MarkersContainer")

    @property
    def markers_container(self):
        """Gets the GESMarkerContainer"""
        return self.__markers_container

    @markers_container.setter
    def markers_container(self, ges_markers_container):
        if self.__markers_container:
            for marker in self.get_children():
                self.remove(marker)
            self.__markers_container.disconnect_by_func(self._marker_added_cb)
        self.__markers_container = ges_markers_container
        self._create_marker_widgets()
        self.__markers_container.connect("marker-added", self._marker_added_cb)

    def _create_marker_widgets(self):
        start = self.pixelToNs(self.offset)
        end = self.pixelToNs(self.get_allocated_width() + MARKER_SEMI_WIDTH) + start
        range_markers = self.__markers_container.get_range(start, end)

        for ges_marker in range_markers:
            marker = Marker(ges_marker)
            position = self.nsToPixel(marker.position) - MARKER_SEMI_WIDTH
            self.put(marker, position, 0)
        self.show_all()

    def _hadj_value_changed_cb(self, hadj):
        """Handles the adjustment value change."""
        self.offset = hadj.get_value()
        self._update_position()

    def zoomChanged(self):
        self._update_position()

    def _update_position(self):
        for marker in self.get_children():
            position = self.nsToPixel(marker.position) - self.offset - MARKER_SEMI_WIDTH
            self.move(marker, position, 0)

    # pylint: disable=protected-access
    def _select_marker_cb(self, unused_widget, event):
        event_widget = Gtk.get_event_widget(event)
        button = event.button

        if button == Gdk.BUTTON_PRIMARY:
            if isinstance(event_widget, Marker):
                if event.type == Gdk.EventType.BUTTON_PRESS:
                    self._change_selected_marker(event_widget)
                    self.marker_pressed = self.marker_selected

                elif event.type == Gdk.EventType._2BUTTON_PRESS:

                    self.marker_pressed = None

                    text_buffer = self.text_view.get_buffer()
                    text = self.marker_selected.comment
                    if text is None:
                        text = "your comments"
                    text_buffer.set_text(text)

                    self.popover.set_relative_to(self.marker_selected)
                    self.popover.show_all()
                    self.popover.popup()

            else:

                position = self.pixelToNs(event.x + self.offset)
                self.__markers_container.add(position)
                self.marker_pressed = self.marker_selected

    def _unselect_marker_cb(self, unused_widget, event):
        button = event.button
        event_widget = Gtk.get_event_widget(event)

        if button == Gdk.BUTTON_PRIMARY and self.marker_pressed:
            self.marker_pressed = None

        elif button == Gdk.BUTTON_SECONDARY and isinstance(event_widget, Marker):
            self._remove_marker(event_widget)

    def _move_marker_cb(self, unused_widget, event):
        if self.marker_pressed:
            event_widget = Gtk.get_event_widget(event)
            event_x, unused_y = event_widget.translate_coordinates(self, event.x, event.y)
            if event_x >= 0:
                position_ns = self.pixelToNs(event_x + self.offset)
                self.__markers_container.move(self.marker_pressed.ges_marker, position_ns)
                x = int(event_x) - MARKER_SEMI_WIDTH
                self.move(self.marker_pressed, x, 0)

    def _marker_added_cb(self, unused_markers, position, ges_marker):
        marker = Marker(ges_marker)
        self._change_selected_marker(marker)
        x = self.nsToPixel(position) - self.offset - MARKER_SEMI_WIDTH
        self.put(marker, x, 0)
        self.show_all()

    def _change_selected_marker(self, marker):
        if self.marker_selected:
            self.marker_selected.selected = False

        marker.selected = True
        self.marker_selected = marker

    def _remove_marker(self, marker):
        self.__markers_container.remove(marker.ges_marker)
        self.remove(marker)

    def _init_popover(self):
        self.popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.text_view, False, True, 10)

        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.LEFT)
        self.popover.connect('closed', self._save_text_cb)

    def _save_text_cb(self, unused_element):
        buffer = self.text_view.get_buffer()
        text = buffer.props.text
        self.marker_selected.comment = text
