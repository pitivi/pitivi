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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Markers display and management."""
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pitivi.utils.loggable import Loggable
from pitivi.utils.pipeline import PipelineError
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import SPACING

MARKER_WIDTH = 10


class Marker(Gtk.EventBox, Loggable):
    """Widget representing a marker."""

    def __init__(self, ges_marker):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK)

        self.ges_marker = ges_marker
        self.ges_marker.ui = self
        self.position_ns = self.ges_marker.props.position

        self.get_style_context().add_class("Marker")
        self.ges_marker.connect("notify-meta", self._notify_meta_cb)

        self._selected = False

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_get_preferred_height(self):
        return MARKER_WIDTH, MARKER_WIDTH

    def do_get_preferred_width(self):
        return MARKER_WIDTH, MARKER_WIDTH

    def do_enter_notify_event(self, unused_event):
        self.set_state_flags(Gtk.StateFlags.PRELIGHT, clear=False)

    def do_leave_notify_event(self, unused_event):
        self.unset_state_flags(Gtk.StateFlags.PRELIGHT)

    def _notify_meta_cb(self, unused_ges_marker, item, value):
        self.set_tooltip_text(self.comment)

    @property
    def position(self):
        """Returns the position of the marker, in nanoseconds."""
        return self.ges_marker.props.position

    @property
    def comment(self):
        """Returns a comment from ges_marker."""
        return self.ges_marker.get_string("comment")

    @comment.setter
    def comment(self, text):
        if text == self.comment:
            return
        self.ges_marker.set_string("comment", text)

    @property
    def selected(self):
        """Returns whether the marker is selected."""
        return self._selected

    @selected.setter
    def selected(self, selected):
        self._selected = selected
        if self._selected:
            self.set_state_flags(Gtk.StateFlags.SELECTED, clear=False)
        else:
            self.unset_state_flags(Gtk.StateFlags.SELECTED)


class MarkersBox(Gtk.EventBox, Zoomable, Loggable):
    """Container for displaying and managing markers."""

    def __init__(self, app, hadj=None):
        Gtk.EventBox.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.layout = Gtk.Layout()
        self.add(self.layout)
        self.get_style_context().add_class("MarkersBox")

        self.app = app

        if hadj:
            hadj.connect("value-changed", self._hadj_value_changed_cb)
        self.props.hexpand = True
        self.props.valign = Gtk.Align.START

        self.offset = 0
        self.props.height_request = MARKER_WIDTH

        self.__markers_container = None
        self.marker_moving = None
        self.marker_new = None

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)

        self._create_actions()

    def _create_actions(self):
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("markers", self.action_group)
        self.app.shortcuts.register_group("markers", _("Markers"), position=70)

        self.add_marker_action = Gio.SimpleAction.new("marker-add", GLib.VariantType("mx"))
        self.add_marker_action.connect("activate", self._add_marker_cb)
        self.action_group.add_action(self.add_marker_action)
        self.app.shortcuts.add("markers.marker-add(@mx nothing)", ["<Primary><Shift>m"],
                               self.add_marker_action, _("Add a marker"))

    def _add_marker_cb(self, action, param):
        maybe = param.get_maybe()
        if maybe:
            position = maybe.get_int64()
        else:
            try:
                position = self.app.project_manager.current_project.pipeline.get_position(fails=False)
            except PipelineError:
                self.warning("Could not get pipeline position")
                return

        with self.app.action_log.started("Added marker", toplevel=True):
            self.__markers_container.add(position)

    @property
    def markers_container(self):
        """Gets the GESMarkerContainer."""
        return self.__markers_container

    @markers_container.setter
    def markers_container(self, ges_markers_container):
        if self.__markers_container:
            for marker in self.layout.get_children():
                self.layout.remove(marker)
            self.__markers_container.disconnect_by_func(self._marker_added_cb)

        self.__markers_container = ges_markers_container
        if self.__markers_container:
            self.__create_marker_widgets()
            self.__markers_container.connect("marker-added", self._marker_added_cb)
            self.__markers_container.connect("marker-removed", self._marker_removed_cb)
            self.__markers_container.connect("marker-moved", self._marker_moved_cb)

    def __create_marker_widgets(self):
        markers = self.__markers_container.get_markers()

        for ges_marker in markers:
            position = ges_marker.props.position
            self._add_marker(position, ges_marker)

    def _hadj_value_changed_cb(self, hadj):
        """Handles the adjustment value change."""
        self.offset = hadj.get_value()
        self._update_position()

    def zoom_changed(self):
        self._update_position()

    def _update_position(self):
        for marker in self.layout.get_children():
            position = self.ns_to_pixel(marker.position) - self.offset - MARKER_WIDTH / 2
            self.layout.move(marker, position, 0)

    def do_button_press_event(self, event):
        event_widget = Gtk.get_event_widget(event)
        button = event.button
        if button == Gdk.BUTTON_PRIMARY:
            if isinstance(event_widget, Marker):
                if event.type == Gdk.EventType.BUTTON_PRESS:
                    self.marker_moving = event_widget
                    self.marker_moving.selected = True
                    self.app.action_log.begin("Move marker", toplevel=True)

                elif event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
                    self.marker_moving = None
                    self.app.action_log.rollback()
                    marker_popover = MarkerPopover(self.app, event_widget)
                    marker_popover.popup()

            else:
                position = self.pixel_to_ns(event.x + self.offset)
                param = GLib.Variant.new_maybe(GLib.VariantType("x"), GLib.Variant.new_int64(position))
                self.add_marker_action.activate(param)
                self.marker_new.selected = True

    def do_button_release_event(self, event):
        button = event.button
        event_widget = Gtk.get_event_widget(event)
        if button == Gdk.BUTTON_PRIMARY:
            if self.marker_moving:
                self.marker_moving.selected = False
                self.marker_moving = None
                self.app.action_log.commit("Move marker")
            elif self.marker_new:
                self.marker_new.selected = False
                self.marker_new = None

        elif button == Gdk.BUTTON_SECONDARY and isinstance(event_widget, Marker):
            with self.app.action_log.started("Removed marker", toplevel=True):
                self.__markers_container.remove(event_widget.ges_marker)

    def do_motion_notify_event(self, event):
        event_widget = Gtk.get_event_widget(event)
        if event_widget is self.marker_moving:
            event_x, unused_y = event_widget.translate_coordinates(self, event.x, event.y)
            event_x = max(0, event_x)
            position_ns = self.pixel_to_ns(event_x + self.offset)
            self.__markers_container.move(self.marker_moving.ges_marker, position_ns)

    def _marker_added_cb(self, unused_markers, position, ges_marker):
        self._add_marker(position, ges_marker)

    def _add_marker(self, position, ges_marker):
        marker = Marker(ges_marker)
        x = self.ns_to_pixel(position) - self.offset - MARKER_WIDTH / 2
        self.layout.put(marker, x, 0)
        marker.show()
        self.marker_new = marker

    def _marker_removed_cb(self, unused_markers, ges_marker):
        self._remove_marker(ges_marker)

    def _remove_marker(self, ges_marker):
        if not ges_marker.ui:
            return

        self.layout.remove(ges_marker.ui)
        ges_marker.ui = None

    def _marker_moved_cb(
            self, unused_markers, unused_prev_position, position, ges_marker):
        self._move_marker(position, ges_marker)

    def _move_marker(self, position, ges_marker):
        x = self.ns_to_pixel(position) - self.offset - MARKER_WIDTH / 2
        self.layout.move(ges_marker.ui, x, 0)


class MarkerPopover(Gtk.Popover):
    """A popover to edit a marker's metadata."""

    def __init__(self, app, marker):
        Gtk.Popover.__init__(self)

        self.app = app

        self.text_view = Gtk.TextView()
        self.text_view.set_size_request(100, -1)

        self.marker = marker

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.props.margin = SPACING
        vbox.pack_start(self.text_view, False, True, 0)
        self.add(vbox)

        text = self.marker.comment
        if text:
            text_buffer = self.text_view.get_buffer()
            text_buffer.set_text(text)

        self.set_position(Gtk.PositionType.TOP)
        self.set_relative_to(self.marker)
        self.show_all()

    def do_closed(self):
        buffer = self.text_view.get_buffer()
        if buffer.props.text != self.marker.comment:
            with self.app.action_log.started("marker comment", toplevel=True):
                self.marker.comment = buffer.props.text
        self.marker.selected = False
