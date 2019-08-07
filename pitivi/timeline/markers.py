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
"""Markers display and management."""
from gi.repository import Gdk
from gi.repository import Gtk

from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import SPACING

MARKER_WIDTH = 10


# pylint: disable=too-many-instance-attributes
class Marker(Gtk.EventBox, Loggable):
    """Widget representing a marker"""

    def __init__(self, ges_marker):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK)

        self.ges_marker = ges_marker
        self.ges_marker.ui = self
        self.position_ns = self.ges_marker.props.position
        self.get_style_context().add_class("Marker")

    # pylint: disable=arguments-differ
    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_get_preferred_height(self):
        return (10, 10)

    def do_get_preferred_width(self):
        return (10, 10)

    def do_enter_notify_event(self, unused_event):
        self.set_state_flags(Gtk.StateFlags.PRELIGHT, clear=False)

    def do_leave_notify_event(self, unused_event):
        self.unset_state_flags(Gtk.StateFlags.PRELIGHT)

    @property
    def position(self):
        """Returns the position of the marker, in nanoseconds."""
        return self.ges_marker.props.position

    @property
    def comment(self):
        """Returns a comment from ges_marker"""
        return self.ges_marker.get_string("comment")

    @comment.setter
    def comment(self, text):
        if text == self.comment:
            return
        self.ges_marker.set_string("comment", text)


class MarkersBox(Gtk.EventBox, Zoomable, Loggable):
    """Container for markers"""

    def __init__(self, timeline):
        Gtk.EventBox.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.layout = Gtk.Layout()
        self.add(self.layout)
        self.get_style_context().add_class("MarkersBox")

        self.hadj = timeline.timeline.hadj
        self.hadj.connect("value-changed", self._hadj_value_changed_cb)
        self.props.hexpand = True
        self.props.valign = Gtk.Align.START

        self.offset = 0
        self.props.height_request = 10

        self.__markers_container = None
        self.current_marker = None
        self.marker_pressed = None

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)

    @property
    def markers_container(self):
        """Gets the GESMarkerContainer"""
        return self.__markers_container

    @markers_container.setter
    def markers_container(self, ges_markers_container):
        if self.__markers_container:
            for marker in self.layout.get_children():
                self.layout.remove(marker)
            self.__markers_container.disconnect_by_func(self._marker_added_cb)
        self.__markers_container = ges_markers_container
        self.__create_marker_widgets()
        self.__markers_container.connect("marker-added", self._marker_added_cb)
        self.__markers_container.connect("marker-removed", self._marker_removed_cb)
        self.__markers_container.connect("marker-moved", self._marker_moved_cb)

    def __create_marker_widgets(self):
        markers = self.__markers_container.get_markers()
        self.debug("markers %s", markers)
        for ges_marker in markers:
            position = ges_marker.props.position
            self._add_marker(position, ges_marker)
        self.marker_pressed = None

    def _hadj_value_changed_cb(self, hadj):
        """Handles the adjustment value change."""
        self.offset = hadj.get_value()
        self._update_position()

    def zoomChanged(self):
        self._update_position()

    def _update_position(self):
        for marker in self.layout.get_children():
            position = self.nsToPixel(marker.position) - self.offset - MARKER_WIDTH / 2
            self.layout.move(marker, position, 0)

    # pylint: disable=arguments-differ
    def do_button_press_event(self, event):
        event_widget = Gtk.get_event_widget(event)
        button = event.button

        if button == Gdk.BUTTON_PRIMARY:
            if isinstance(event_widget, Marker):
                if event.type == Gdk.EventType.BUTTON_PRESS:
                    self.marker_pressed = event_widget
                    self.app.action_log.begin("Move marker", toplevel=True)

                elif event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
                    self.marker_pressed = None
                    self.app.action_log.rollback("Move marker")
                    MarkerPopover(event_widget)

            else:
                position = self.pixelToNs(event.x + self.offset)
                with self.app.action_log.started("Added marker", toplevel=True):
                    self.__markers_container.add(position)

    def do_button_release_event(self, event):
        button = event.button
        event_widget = Gtk.get_event_widget(event)

        if button == Gdk.BUTTON_PRIMARY and self.marker_pressed:
            self.marker_pressed = None
            self.app.action_log.commit("Move marker")

        elif button == Gdk.BUTTON_SECONDARY and isinstance(event_widget, Marker):
            with self.app.action_log.started("Removed marker", toplevel=True):
                self.__markers_container.remove(event_widget.ges_marker)

    def do_motion_notify_event(self, event):
        if self.marker_pressed:
            event_widget = Gtk.get_event_widget(event)
            event_x, unused_y = event_widget.translate_coordinates(self, event.x, event.y)
            event_x = max(0, event_x)
            position_ns = self.pixelToNs(event_x + self.offset)
            self.__markers_container.move(self.marker_pressed.ges_marker, position_ns)

    def _marker_added_cb(self, unused_markers, position, ges_marker):
        self._add_marker(position, ges_marker)

    def _add_marker(self, position, ges_marker):
        marker = Marker(ges_marker)
        # self.marker_pressed = marker
        x = self.nsToPixel(position) - self.offset - MARKER_WIDTH / 2
        self.layout.put(marker, x, 0)
        marker.show()

    def _marker_removed_cb(self, unused_markers, ges_marker):
        self._remove_marker(ges_marker)

    def _remove_marker(self, ges_marker):
        if not ges_marker.ui:
            return

        self.layout.remove(ges_marker.ui)
        ges_marker.ui = None

    def _marker_moved_cb(self, unused_markers, position, ges_marker):
        self._move_marker(position, ges_marker)

    def _move_marker(self, position, ges_marker):
        x = self.nsToPixel(position) - self.offset - MARKER_WIDTH / 2
        self.layout.move(ges_marker.ui, x, 0)


class MarkerPopover(Gtk.Popover):
    """A popover menu to edit markers metadata"""

    def __init__(self, marker):
        Gtk.Popover.__init__(self)

        self.text_view = Gtk.TextView()

        self.marker = marker

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.text_view, False, True, SPACING * 2)

        self.add(vbox)
        self.set_position(Gtk.PositionType.LEFT)
        self.connect("closed", self._save_text_cb)

        text_buffer = self.text_view.get_buffer()
        text = self.marker.comment
        if text:
            text_buffer.set_text(text)

        self.set_relative_to(self.marker)
        self.show_all()
        self.popup()

    def _save_text_cb(self, unused_element):
        buffer = self.text_view.get_buffer()
        text = buffer.props.text
        self.marker.comment = text
