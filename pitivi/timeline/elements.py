# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, Mathieu Duponchelle <mduponchelle1@gmail.com>
# Copyright (c) 2016, Thibault Saunier <tsaunier@gnome.org>
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
import os
from gettext import gettext as _
from typing import Optional

import numpy
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import Gtk
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from pitivi.configure import get_pixmap_dir
from pitivi.effects import ALLOWED_ONLY_ONCE_EFFECTS
from pitivi.timeline.markers import ClipMarkersBox
from pitivi.timeline.markers import Marker
from pitivi.timeline.previewers import AudioPreviewer
from pitivi.timeline.previewers import ImagePreviewer
from pitivi.timeline.previewers import MiniPreview
from pitivi.timeline.previewers import TitlePreviewer
from pitivi.timeline.previewers import VideoPreviewer
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable
from pitivi.utils.markers import MarkerListManager
from pitivi.utils.misc import disconnect_all_by_func
from pitivi.utils.misc import filename_from_uri
from pitivi.utils.pipeline import PipelineError
from pitivi.utils.timeline import SELECT
from pitivi.utils.timeline import SELECT_ADD
from pitivi.utils.timeline import Selected
from pitivi.utils.timeline import UNSELECT
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import CURSORS
from pitivi.utils.ui import DRAG_CURSOR
from pitivi.utils.ui import EFFECT_TARGET_ENTRY
from pitivi.utils.ui import NORMAL_CURSOR
from pitivi.utils.ui import set_state_flags_recurse

KEYFRAME_LINE_HEIGHT = 2
KEYFRAME_LINE_ALPHA = 0.5
KEYFRAME_LINE_COLOR = "#EDD400"  # "Tango" medium yellow
KEYFRAME_NODE_COLOR = "#F57900"  # "Tango" medium orange
SELECTED_KEYFRAME_NODE_COLOR = "#204A87"  # "Tango" dark sky blue
HOVERED_KEYFRAME_NODE_COLOR = "#3465A4"  # "Tango" medium sky blue


def get_pspec(element_factory_name, propname):
    element = Gst.ElementFactory.make(element_factory_name)
    if not element:
        return None

    return [prop for prop in element.list_properties() if prop.name == propname][0]


class KeyframeCurve(FigureCanvasGTK3Cairo, Loggable):
    YLIM_OVERRIDES = {}

    __YLIM_OVERRIDES_VALUES = [("volume", "volume", (0.0, 0.2))]

    for factory_name, propname, values in __YLIM_OVERRIDES_VALUES:
        pspec = get_pspec(factory_name, propname)
        if pspec:
            YLIM_OVERRIDES[pspec] = values

    __gsignals__ = {
        # Signal the keyframes or the curve are being hovered
        "enter": (GObject.SignalFlags.RUN_LAST, None, ()),
        # Signal the keyframes or the curve are not being hovered anymore
        "leave": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, timeline, binding, ges_elem):
        figure = Figure()
        FigureCanvasGTK3Cairo.__init__(self, figure)
        Loggable.__init__(self)

        # Remove the "matplotlib-canvas" class which forces a white background.
        # https://github.com/matplotlib/matplotlib/commit/3c832377fb4c4b32fcbdbc60fdfedb57296bc8c0
        style_ctx = self.get_style_context()
        for css_class in style_ctx.list_classes():
            style_ctx.remove_class(css_class)

        style_ctx.add_class("KeyframeCurve")

        self._ges_elem = ges_elem
        self._timeline = timeline
        self.__source = binding.props.control_source
        self._connect_sources()
        self.__property_name = binding.props.name
        self.__paramspec = binding.pspec

        self.__ylim_min, self.__ylim_max = KeyframeCurve.YLIM_OVERRIDES.get(
            binding.pspec, (0.0, 1.0))
        self.__ydata_drag_start = self.__ylim_min

        # Curve values, basically separating source.get_values() timestamps
        # and values.
        self._line_xs = []
        self._line_ys = []

        transparent = (0, 0, 0, 0)
        self._ax: Axes = figure.add_axes([0, 0, 1, 1], facecolor=transparent)
        # Clear the Axes object.
        self._ax.cla()
        self._ax.grid(False)
        self._ax.tick_params(axis='both',
                             which='both',
                             bottom=False,
                             top=False,
                             right=False,
                             left=False)

        # This seems to also be necessary for transparency ..
        figure.patch.set_visible(False)

        # The PathCollection object holding the keyframes dots.
        sizes = [50]
        self._keyframes: PathCollection = self._ax.scatter([], [], marker='D', s=sizes,
                                                           c=KEYFRAME_NODE_COLOR, zorder=2)

        # matplotlib weirdness, simply here to avoid a warning ..
        self._keyframes.set_picker(True)

        # The Line2D object holding the lines between keyframes.
        self.__line: Line2D = self._ax.plot([], [],
                                            alpha=KEYFRAME_LINE_ALPHA,
                                            c=KEYFRAME_LINE_COLOR,
                                            linewidth=KEYFRAME_LINE_HEIGHT, zorder=1)[0]
        self._update_plots()

        # Drag and drop logic
        # Whether the clicked keyframe or line has been dragged.
        self._dragged = False
        # The inpoint of the clicked keyframe.
        self._offset = None
        # The initial keyframe value when a keyframe is being moved.
        self._initial_value = 0
        # The initial keyframe timestamp when a keyframe is being moved.
        self._initial_timestamp = 0
        # The initial event.x when a keyframe is being moved.
        self._initial_x = 0
        # The initial event.y when a keyframe is being moved.
        self._initial_y = 0
        # The (offset, value) of both keyframes of the clicked keyframe line.
        self.__clicked_line = ()
        # Whether the mouse events go to the keyframes logic.
        self.handling_motion = False

        self.__hovered = False

        self.connect("motion-notify-event", self.__motion_notify_event_cb)
        self.connect("event", self._event_cb)
        self.connect("notify::height-request", self.__height_request_cb)
        self.connect("button_release_event", self._button_release_event_cb)

        self.mpl_connect('button_press_event', self._mpl_button_press_event_cb)
        self.mpl_connect('button_release_event', self._mpl_button_release_event_cb)
        self.mpl_connect('motion_notify_event', self._mpl_motion_event_cb)

    def release(self):
        disconnect_all_by_func(self, self.__height_request_cb)
        disconnect_all_by_func(self, self.__motion_notify_event_cb)
        disconnect_all_by_func(self, self._button_release_event_cb)
        disconnect_all_by_func(self, self._control_source_changed_cb)

    def _connect_sources(self):
        self.__source.connect("value-added", self._control_source_changed_cb)
        self.__source.connect("value-removed", self._control_source_changed_cb)
        self.__source.connect("value-changed", self._control_source_changed_cb)

    def _update_plots(self):
        values = self.__source.get_all()
        if len(values) < 2:
            # No plot for less than two points.
            return

        self._line_xs = []
        self._line_ys = []
        for value in values:
            self._line_xs.append(value.timestamp)
            self._line_ys.append(value.value)

        self._populate_lines()

    def _populate_lines(self):
        self._ax.set_xlim(self._line_xs[0], self._line_xs[-1])
        self.__compute_ylim()

        arr = numpy.array((self._line_xs, self._line_ys)).transpose()
        self._keyframes.set_offsets(arr)
        self.__line.set_xdata(self._line_xs)
        self.__line.set_ydata(self._line_ys)
        self.queue_draw()

    def __compute_ylim(self):
        height = self.props.height_request
        if height <= 0:
            return

        ylim_min = -(KEYFRAME_LINE_HEIGHT / height)
        ylim_max = (self.__ylim_max * height) / (height - KEYFRAME_LINE_HEIGHT)
        self._ax.set_ylim(ylim_min, ylim_max)

    def __height_request_cb(self, unused_self, unused_pspec):
        self.__compute_ylim()

    def __maybe_create_keyframe(self, event):
        line_contains = self.__line.contains(event)[0]
        keyframe_existed = self._keyframes.contains(event)[0]
        if line_contains and not keyframe_existed:
            self._create_keyframe(event.xdata)

    def _create_keyframe(self, timestamp):
        res, value = self.__source.control_source_get_value(timestamp)
        assert res
        self.debug("Create keyframe at (%lf, %lf)", timestamp, value)
        with self._timeline.app.action_log.started("Keyframe added",
                                                   toplevel=True):
            self.__source.set(timestamp, value)

    def _remove_keyframe(self, timestamp):
        self.debug("Removing keyframe at timestamp %lf", timestamp)
        with self._timeline.app.action_log.started("Remove keyframe",
                                                   toplevel=True):
            self.__source.unset(timestamp)

    def _move_keyframe(self, source_timestamp, dest_timestamp, dest_value):
        self.__source.unset(source_timestamp)
        self.__source.set(dest_timestamp, dest_value)

    def _move_keyframe_line(self, line, y_dest_value, y_start_value):
        delta = y_dest_value - y_start_value
        for offset, value in line:
            value = max(self.__ylim_min, min(value + delta, self.__ylim_max))
            self.__source.set(offset, value)

    def toggle_keyframe(self, offset):
        """Sets or unsets the keyframe at the specified offset."""
        items = self.__source.get_all()
        if offset in (items[0].timestamp, items[-1].timestamp):
            return

        if offset in [item.timestamp for item in items]:
            self.__source.unset(offset)
        else:
            res, value = self.__source.control_source_get_value(offset)
            assert res
            self.__source.set(offset, value)

    def _control_source_changed_cb(self, unused_control_source, unused_timed_value):
        self._update_plots()
        self._timeline.ges_timeline.get_parent().commit_timeline()

    def __motion_notify_event_cb(self, unused_widget, unused_event):
        # We need to do this here, because Matplotlib's callbacks can't stop
        # signal propagation.
        if self.handling_motion:
            return True
        return False

    def _event_cb(self, unused_element, event):
        if event.type == Gdk.EventType.LEAVE_NOTIFY:
            cursor = NORMAL_CURSOR
            self._timeline.get_window().set_cursor(cursor)
        return False

    def _mpl_button_press_event_cb(self, event):
        if event.button != MouseButton.LEFT:
            return

        result = self._keyframes.contains(event)
        if result[0]:
            # A keyframe has been clicked.
            keyframe_index = result[1]['ind'][0]
            offsets = self._keyframes.get_offsets()
            offset, value = offsets[keyframe_index]

            # pylint: disable=protected-access
            if event.guiEvent.type == Gdk.EventType._2BUTTON_PRESS:
                index = result[1]['ind'][0]
                # pylint: disable=consider-using-in
                if index == 0 or index == len(offsets) - 1:
                    # It's an edge keyframe. These should not be removed.
                    return

                # Rollback the last operation if it is "Move keyframe".
                # This is needed because a double-click also triggers a
                # BUTTON_PRESS event which starts a "Move keyframe" operation
                self._timeline.app.action_log.try_rollback("Move keyframe")
                self._offset = None

                # A keyframe has been double-clicked, remove it.
                self._remove_keyframe(offset)
            else:
                # Remember the clicked frame for drag&drop.
                self._timeline.app.action_log.begin("Move keyframe",
                                                    toplevel=True)
                self._initial_x = event.x
                self._initial_y = event.y
                self._offset = offset
                self._initial_timestamp = offset
                self._initial_value = value
                self.handling_motion = True
            return

        if event.guiEvent.type != Gdk.EventType.BUTTON_PRESS:
            return

        result = self.__line.contains(event)
        if result[0]:
            # The line has been clicked.
            self.debug("The keyframe curve has been clicked")
            self._timeline.app.action_log.begin("Move keyframe curve segment",
                                                toplevel=True)
            x = event.xdata
            offsets = self._keyframes.get_offsets()
            keyframes = offsets[:, 0]
            right = numpy.searchsorted(keyframes, x)
            # Remember the clicked line for drag&drop.
            self.__clicked_line = (offsets[right - 1], offsets[right])
            self.__ydata_drag_start = max(self.__ylim_min, min(event.ydata, self.__ylim_max))
            self.handling_motion = True

    def _mpl_motion_event_cb(self, event):
        if event.ydata is not None and event.xdata is not None:
            # The mouse event is in the figure boundaries.
            if self._offset is not None:
                self._dragged = True
                keyframe_ts, ydata = self.__compute_keyframe_position(event)
                self._move_keyframe(int(self._offset), keyframe_ts, ydata)
                self._offset = keyframe_ts
                self._update_tooltip(event)
                hovering = True
            elif self.__clicked_line:
                self._dragged = True
                ydata = max(self.__ylim_min, min(event.ydata, self.__ylim_max))
                self._move_keyframe_line(self.__clicked_line, ydata, self.__ydata_drag_start)
                hovering = True
            else:
                hovering = self.__line.contains(event)[0]
        else:
            hovering = False

        if hovering:
            cursor = DRAG_CURSOR
            self._update_tooltip(event)
            if not self.__hovered:
                self.emit("enter")
                self.__hovered = True
        else:
            cursor = NORMAL_CURSOR
            if self.__hovered:
                self.emit("leave")
                self._update_tooltip(None)
                self.__hovered = False

        self._timeline.get_window().set_cursor(cursor)

    def _mpl_button_release_event_cb(self, event):
        if event.button != MouseButton.LEFT:
            return

        # In order to make sure we seek to the exact position where we added a
        # new keyframe, we don't use matplotlib's event.xdata, but rather
        # compute it the same way we do for the seek logic.
        event_widget = Gtk.get_event_widget(event.guiEvent)
        x, unused_y = event_widget.translate_coordinates(self._timeline.layout.layers_vbox,
                                                         event.x, event.y)
        event.xdata = Zoomable.pixel_to_ns(x) - self._ges_elem.props.start + self._ges_elem.props.in_point

        if self._offset is not None:
            # If dragging a keyframe, make sure the keyframe ends up exactly
            # where the mouse was released. Otherwise, the playhead will not
            # seek exactly on the keyframe.
            if self._dragged:
                if event.ydata is not None:
                    keyframe_ts, ydata = self.__compute_keyframe_position(event)
                    self._move_keyframe(int(self._offset), keyframe_ts, ydata)
            self.debug("Keyframe released")
            self._timeline.app.action_log.commit("Move keyframe")
        elif self.__clicked_line:
            self.debug("Line released")
            self._timeline.app.action_log.commit("Move keyframe curve segment")

            if not self._dragged:
                # The keyframe line was clicked, but not dragged
                assert event.guiEvent.type == Gdk.EventType.BUTTON_RELEASE
                self.__maybe_create_keyframe(event)

        self.handling_motion = False
        self._offset = None
        self.__clicked_line = ()

    def _button_release_event_cb(self, unused_widget, event):
        if not event.get_button() == (True, 1):
            return False

        dragged = self._dragged
        self._dragged = False

        # Return True to stop signal propagation, otherwise the clip will be
        # unselected.
        return dragged

    def _update_tooltip(self, event):
        """Sets or clears the tooltip showing info about the hovered line."""
        markup = None
        if event:
            if not event.xdata:
                return
            if self._offset is not None:
                xdata = self._offset
            else:
                xdata = max(self._line_xs[0], min(event.xdata, self._line_xs[-1]))
            res, value = self.__source.control_source_get_value(xdata)
            assert res
            pmin = self.__paramspec.minimum
            pmax = self.__paramspec.maximum
            value = value * (pmax - pmin) + pmin
            # Translators: This is a tooltip for a clip's keyframe curve,
            # showing what the keyframe curve affects, the timestamp at
            # the mouse cursor location, and the value at that timestamp.
            markup = _("Property: %s\nTimestamp: %s\nValue: %s") % (
                self.__property_name,
                Gst.TIME_ARGS(xdata),
                "{:.3f}".format(value))
        self.set_tooltip_markup(markup)

    def __compute_keyframe_position(self, event):
        keyframe_ts = self.__compute_keyframe_new_timestamp(event)
        ydata = max(self.__ylim_min, min(event.ydata, self.__ylim_max))
        if self._timeline.get_parent().control_mask:
            delta_x = abs(event.x - self._initial_x)
            delta_y = abs(event.y - self._initial_y)
            if delta_x > delta_y:
                ydata = self._initial_value
            else:
                keyframe_ts = self._initial_timestamp

        return keyframe_ts, ydata

    def __compute_keyframe_new_timestamp(self, event):
        # The user can not change the timestamp of the first
        # and last keyframes.
        values = self.__source.get_all()
        if self._offset in (values[0].timestamp, values[-1].timestamp):
            return self._offset

        if event.xdata != self._offset:
            try:
                kf = next(kf for kf in values if kf.timestamp == int(self._offset))
            except StopIteration:
                return event.xdata

            i = values.index(kf)
            keyframe_timestamp = int(event.xdata)
            if keyframe_timestamp <= values[i - 1].timestamp:
                keyframe_timestamp = values[i - 1].timestamp + 1
            if keyframe_timestamp >= values[i + 1].timestamp:
                keyframe_timestamp = values[i + 1].timestamp - 1
            return keyframe_timestamp

        return event.xdata


class MultipleKeyframeCurve(KeyframeCurve):
    """Keyframe curve which controls multiple properties at once."""

    def __init__(self, timeline, bindings, ges_elem):
        self.__bindings = bindings
        super().__init__(timeline, bindings[0], ges_elem)

        self._timeline = timeline
        self._project = timeline.app.project_manager.current_project
        self._project.pipeline.connect("position", self._position_cb)

        sizes = [80]
        self.__selected_keyframe = self._ax.scatter([0], [0.5], marker='D', s=sizes,
                                                    c=SELECTED_KEYFRAME_NODE_COLOR, zorder=3)
        self.__hovered_keyframe = self._ax.scatter([0], [0.5], marker='D', s=sizes,
                                                   c=HOVERED_KEYFRAME_NODE_COLOR, zorder=3)
        self.__update_selected_keyframe()
        self.__hovered_keyframe.set_visible(False)

    def release(self):
        super().release()
        self._project.pipeline.disconnect_by_func(self._position_cb)

    def _connect_sources(self):
        for binding in self.__bindings:
            source = binding.props.control_source
            source.connect("value-added", self._control_source_changed_cb)
            source.connect("value-removed", self._control_source_changed_cb)
            source.connect("value-changed", self._control_source_changed_cb)

    def _update_plots(self):
        timestamps = []
        for binding in self.__bindings:
            ts = [value.timestamp for value in binding.props.control_source.get_all()]
            timestamps.extend(ts)
        timestamps = sorted(list(set(timestamps)))

        if len(timestamps) < 2:
            # No plot for less than two points.
            return

        self._line_xs = []
        self._line_ys = []
        for timestamp in timestamps:
            self._line_xs.append(timestamp)
            self._line_ys.append(0.5)

        self._populate_lines()

    def _create_keyframe(self, timestamp):
        with self._timeline.app.action_log.started("Add keyframe",
                                                   toplevel=True):
            for binding in self.__bindings:
                binding.props.control_source.set(timestamp, binding.get_value(timestamp))

    def _remove_keyframe(self, timestamp):
        with self._timeline.app.action_log.started("Remove keyframe",
                                                   toplevel=True):
            for binding in self.__bindings:
                binding.props.control_source.unset(timestamp)

    def _move_keyframe(self, source_timestamp, dest_timestamp, unused_dest_value):
        if source_timestamp == dest_timestamp:
            return

        for binding in self.__bindings:
            dest_value = binding.get_value(source_timestamp)
            binding.props.control_source.set(dest_timestamp, dest_value)
            binding.props.control_source.unset(source_timestamp)

    def _move_keyframe_line(self, line, y_dest_value, y_start_value):
        pass

    def _mpl_button_release_event_cb(self, event):
        if event.button == MouseButton.LEFT:
            if self._offset is not None and not self._dragged:
                # A keyframe was clicked but not dragged, so we
                # should select it by seeking to its position.
                source = self._timeline.selection.get_single_clip()
                assert source
                position = int(self._offset) - source.props.in_point + source.props.start

                if self._timeline.app.settings.leftClickAlsoSeeks:
                    self._timeline.set_next_seek_position(position)
                else:
                    self._project.pipeline.simple_seek(position)

        super()._mpl_button_release_event_cb(event)

    def _mpl_motion_event_cb(self, event):
        super()._mpl_motion_event_cb(event)

        result = self._keyframes.contains(event)
        if result[0]:
            # A keyframe is hovered
            keyframe_index = result[1]['ind'][0]
            offset = self._keyframes.get_offsets()[keyframe_index][0]
            self.__show_special_keyframe(self.__hovered_keyframe, offset)
        else:
            self.__hide_special_keyframe(self.__hovered_keyframe)

    def __show_special_keyframe(self, keyframe, offset):
        offsets = numpy.array([[offset, 0.5]])
        keyframe.set_offsets(offsets)
        keyframe.set_visible(True)
        self.queue_draw()

    def __hide_special_keyframe(self, keyframe):
        keyframe.set_visible(False)
        self.queue_draw()

    def _control_source_changed_cb(self, control_source, timed_value):
        super()._control_source_changed_cb(control_source, timed_value)
        self.__update_selected_keyframe()
        self.__hide_special_keyframe(self.__hovered_keyframe)

    def _position_cb(self, unused_pipeline, unused_position):
        self.__update_selected_keyframe()

    def __update_selected_keyframe(self):
        try:
            position = self._project.pipeline.get_position()
        except PipelineError:
            self.warning("Could not get pipeline position")
            return

        source = self._timeline.selection.get_single_clip()
        if source is None:
            return
        source_position = position - source.props.start + source.props.in_point

        offsets = self._keyframes.get_offsets()
        keyframes = offsets[:, 0]

        index = numpy.searchsorted(keyframes, source_position)
        if 0 <= index < len(keyframes) and keyframes[index] == source_position:
            self.__show_special_keyframe(self.__selected_keyframe, source_position)
        else:
            self.__hide_special_keyframe(self.__selected_keyframe)

    def _update_tooltip(self, event):
        markup = None
        if event:
            if not event.xdata:
                return
            markup = _("Timestamp: %s") % Gst.TIME_ARGS(event.xdata)
        self.set_tooltip_markup(markup)


class TimelineElement(Gtk.Layout, Zoomable, Loggable):
    __gsignals__ = {
        # Signal the keyframes curve are being hovered
        "curve-enter": (GObject.SignalFlags.RUN_LAST, None, ()),
        # Signal the keyframes curve are not being hovered anymore
        "curve-leave": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, element, timeline):
        Gtk.Layout.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.set_name(element.get_name())

        self.timeline = timeline
        self._ges_elem = element
        self._ges_elem.selected = Selected()
        self._ges_elem.selected.connect(
            "selected-changed", self.__selected_changed_cb)

        self.__width = 0
        self.__height = 0

        self.props.vexpand = True

        self.previewer = self._get_previewer()
        if self.previewer:
            self.add(self.previewer)

        self.__background = self._get_background()
        if self.__background:
            self.add(self.__background)

        self.markers = ClipMarkersBox(self.app, self._ges_elem)
        self._ges_elem.markers_manager.set_markers_box(self.markers)

        self.add(self.markers)

        self.keyframe_curve = None
        self.__controlled_property = None
        self.show_all()

        # We set up the default mixing property right here, if a binding was
        # already set (when loading a project), it will be added later
        # and override that one.
        self.show_default_keyframes(lazy_render=True)

    def update_previewer(self):
        """Refreshes the previewer widget."""
        if self.previewer:
            self.previewer.refresh()

    def release(self):
        if self.previewer:
            self.previewer.release()

        if self.markers:
            self._ges_elem.markers_manager.set_markers_box(None)
            self.markers.release()

    # Public API
    def set_size(self, width, height):
        width = max(0, width)
        self.set_size_request(width, height)

        if self.__width != width or self.__height != height:
            self.__width = width
            self.__height = height
            self.update_sizes_and_positions()

    def show_keyframes(self, ges_elem, prop):
        self.__set_keyframes(ges_elem, prop)
        binding = ges_elem.get_control_binding(prop.name)
        self.__create_keyframe_curve([binding])

    def show_default_keyframes(self, lazy_render=False):
        self.__set_keyframes(self._ges_elem, self._get_default_mixing_property())
        if not lazy_render:
            self.__create_keyframe_curve()

    def show_multiple_keyframes(self, bindings):
        self.__controlled_property = None
        self.__create_keyframe_curve(bindings)

    def __set_keyframes(self, ges_elem, prop):
        self.__remove_keyframes()
        self.__controlled_property = prop
        if self.__controlled_property:
            self.__create_control_binding(ges_elem)

    def __curve_enter_cb(self, unused_keyframe_curve):
        self.emit("curve-enter")

    def __curve_leave_cb(self, unused_keyframe_curve):
        self.emit("curve-leave")

    def __remove_keyframes(self):
        if not self.keyframe_curve:
            # Nothing to remove.
            return

        self.keyframe_curve.disconnect_by_func(self.__curve_enter_cb)
        self.keyframe_curve.disconnect_by_func(self.__curve_leave_cb)
        self.remove(self.keyframe_curve)

        self.keyframe_curve.release()
        self.keyframe_curve = None

    # Private methods
    def __ensure_keyframes(self, binding):
        """Ensures that we have at least 2 keyframes (at inpoint and end)."""
        source = binding.props.control_source
        values = source.get_all()

        if len(values) < 2:
            source.unset_all()
            values_range = self.__controlled_property.maximum - self.__controlled_property.minimum
            val = float(self.__controlled_property.default_value) / values_range
            inpoint = self._ges_elem.props.in_point
            res = source.set(inpoint, val)
            assert res
            res = source.set(inpoint + self._ges_elem.props.duration, val)
            assert res

    def __create_keyframe_curve(self, bindings=None):
        """Creates required keyframe curve."""
        self.__remove_keyframes()
        if not bindings:
            bindings = [self._ges_elem.get_control_binding(self.__controlled_property.name)]

        if len(bindings) == 1:
            self.keyframe_curve = KeyframeCurve(self.timeline, bindings[0], self._ges_elem)
        else:
            self.keyframe_curve = MultipleKeyframeCurve(self.timeline, bindings, self._ges_elem)

        self.keyframe_curve.connect("enter", self.__curve_enter_cb)
        self.keyframe_curve.connect("leave", self.__curve_leave_cb)
        self.keyframe_curve.set_size_request(self.__width, self.__height)
        self.keyframe_curve.show()
        self.__update_keyframe_curve()

    def __create_control_binding(self, element):
        """Creates the required ControlBinding and keyframes."""
        if self.__controlled_property:
            element.connect("control-binding-added",
                            self.__control_binding_added_cb)
            binding = \
                element.get_control_binding(self.__controlled_property.name)

            if binding:
                self.__ensure_keyframes(binding)

                return

            source = GstController.InterpolationControlSource()
            source.props.mode = GstController.InterpolationMode.LINEAR
            element.set_control_source(source,
                                       self.__controlled_property.name, "direct")

    def __control_binding_added_cb(self, unused_ges_elem, binding):
        if binding.props.name == self.__controlled_property.name:
            self.__ensure_keyframes(binding)

    def do_draw(self, cr):
        self.propagate_draw(self.__background, cr)

        if self.previewer:
            self.propagate_draw(self.previewer, cr)

        if self.keyframe_curve and self.keyframe_curve.is_drawable():
            project = self.timeline.app.project_manager.current_project
            if project.pipeline.get_simple_state() != Gst.State.PLAYING:
                self.propagate_draw(self.keyframe_curve, cr)

        if self.markers and self.markers.is_drawable():
            self.propagate_draw(self.markers, cr)

    # Callbacks
    def __selected_changed_cb(self, unused_selected, selected):
        if not self.keyframe_curve and self.__controlled_property and \
                selected and len(self.timeline.selection) == 1:
            self.__create_keyframe_curve()

        if self.previewer:
            self.previewer.set_selected(selected)

        self.update_sizes_and_positions()

    def update_sizes_and_positions(self):
        markers_height = self.markers.props.height_request
        width = self.__width
        height = self.__height

        if self.__background:
            self.__background.set_size_request(width, height)

        if self.previewer:
            self.previewer.set_size_request(width, height)

        if self.markers:
            self.markers.set_size_request(width, markers_height)

        # Prevent keyframe curve from overlapping onto markers.
        if self.keyframe_curve:
            self.keyframe_curve.set_size_request(self.__width, self.__height - markers_height)
            self.__update_keyframe_curve()

    def __update_keyframe_curve(self):
        """Updates the keyframes widget visibility by adding or removing it."""
        if self._ges_elem.selected and len(self.timeline.selection) == 1:
            markers_height = self.markers.props.height_request
            if not self.keyframe_curve.get_parent():
                self.put(self.keyframe_curve, 0, markers_height)
            else:
                self.move(self.keyframe_curve, 0, markers_height)
        else:
            self.remove(self.keyframe_curve)

    # Virtual methods
    def _get_previewer(self):
        """Gets a Gtk.Widget to be used as previewer.

        This previewer will be automatically scaled to the width and
        height of the TimelineElement.

        Returns:
            Gtk.Widget: The widget showing thumbnails, waveforms, etc.
        """
        return None

    def _get_background(self):
        """Gets a Gtk.Widget to be used as background.

        Returns:
            Gtk.Widget: The widget identifying the clip type.
        """
        return None

    def _get_default_mixing_property(self):
        """Gets the property controlled by default by the keyframes.

        Returns:
            GObject.ParamSpec: The param spec of the default property.
        """
        return None


class VideoBackground(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self)
        self.get_style_context().add_class("VideoBackground")


class VideoSource(TimelineElement):
    """Widget representing a GES.VideoSource.

    Attributes:
        default_position (dict): The default position (x, y, width, height)
                                 of the VideoSource.
    """

    __gtype_name__ = "PitiviVideoSource"

    def __init__(self, element, timeline):
        super().__init__(element, timeline)

        project = self.timeline.app.project_manager.current_project
        project.connect("video-size-changed",
                        self._project_video_size_changed_cb)

        self.__videoflip = None
        self.__retrieve_project_size()
        self.default_position = self._get_default_position()

        if project.loaded:
            self.__apply_default_position()

        parent = element.get_parent()
        parent.connect("child-added", self.__parent_child_added_cb)
        parent.connect("child-removed", self.__parent_child_removed_cb)

    def __parent_child_added_cb(self, unused_parent, unused_child):
        self.__reset_position()

    def __parent_child_removed_cb(self, unused_parent, child):
        if child == self.__videoflip:
            self.__videoflip = None
            self.__reset_position()
            disconnect_all_by_func(child, self.__track_element_deep_notify_cb)
            disconnect_all_by_func(child, self.__track_element_notify_active_cb)

    def __retrieve_project_size(self):
        project = self.timeline.app.project_manager.current_project

        self._project_width = project.videowidth
        self._project_height = project.videoheight

    def _project_video_size_changed_cb(self, unused_project):
        # GES handles repositionning clips on project size change, make sure to
        # take that into account.
        self.__retrieve_project_size()
        self.default_position = self._get_default_position()

    def __has_default_position(self):
        for name, default_value in self.default_position.items():
            res, value = self._ges_elem.get_child_property(name)
            assert res
            if value != default_value:
                return False

        return True

    def __reset_position(self):
        using_defaults = self.__has_default_position()
        self.__retrieve_project_size()
        self.default_position = self._get_default_position()
        if using_defaults:
            self.debug("Applying default position")
            self.__apply_default_position()
        else:
            self.debug("Not using defaults")

    def __apply_default_position(self):
        video_source = self._ges_elem
        for name, value in self.default_position.items():
            video_source.set_child_property(name, value)

    def _get_default_position(self):
        video_source = self._ges_elem
        sinfo = video_source.get_asset().get_stream_info()

        asset_width = sinfo.get_natural_width()
        asset_height = sinfo.get_natural_height()
        parent = video_source.get_parent()
        if parent and not self.__videoflip:
            for track_element in parent.find_track_elements(
                    None, GES.TrackType.VIDEO, GES.BaseEffect):

                res, unused_videoflip, unused_pspec = track_element.lookup_child(
                    "GstVideoFlip::method")
                if res:
                    self.__videoflip = track_element
                    track_element.connect("deep-notify",
                                          self.__track_element_deep_notify_cb)
                    track_element.connect("notify::active",
                                          self.__track_element_notify_active_cb)

        if self.__videoflip:
            res, method = self.__videoflip.get_child_property("method")
            assert res
            if "clockwise" in method.value_nick and self.__videoflip.props.active:
                asset_width = sinfo.get_natural_height()
                asset_height = sinfo.get_natural_width()

        # Find the biggest size of the video inside the
        # final view (project size) keeping the aspect ratio
        scale = max(self._project_width / asset_width,
                    self._project_height / asset_height)
        if asset_width * scale > self._project_width or \
                asset_height * scale > self._project_height:
            # But make sure it is never bigger than the project!
            scale = min(self._project_width / asset_width,
                        self._project_height / asset_height)

        width = asset_width * scale
        height = asset_height * scale
        x = max(0, (self._project_width - width) / 2)
        y = max(0, (self._project_height - height) / 2)

        self.debug("video scale is %f -> %dx%d", scale, width, height)

        return {"posx": round(x),
                "posy": round(y),
                "width": round(width),
                "height": round(height)}

    def __track_element_deep_notify_cb(self, unused_source, unused_gstelement,
                                       unused_pspec):
        self.__reset_position()

    def __track_element_notify_active_cb(self, unused_track_element,
                                         unused_pspec):
        self.__reset_position()

    def _get_background(self):
        return VideoBackground()


class TitleSource(VideoSource):

    __gtype_name__ = "PitiviTitleSource"

    def _get_default_mixing_property(self):
        for spec in self._ges_elem.list_children_properties():
            if spec.name == "alpha":
                return spec
        return None

    def _get_previewer(self):
        previewer = TitlePreviewer(self._ges_elem)
        previewer.get_style_context().add_class("TitleSource")
        return previewer

    def _get_default_position(self):
        return {"posx": 0,
                "posy": 0,
                "width": self._project_width,
                "height": self._project_height}


class VideoTestSource(VideoSource):

    __gtype_name__ = "PitiviVideoTestSource"

    def _get_default_mixing_property(self):
        for spec in self._ges_elem.list_children_properties():
            if spec.name == "alpha":
                return spec
        return None

    def _get_previewer(self):
        previewer = ImagePreviewer(self._ges_elem, self.timeline.app.settings.previewers_max_cpu)
        return previewer

    def _get_default_position(self):
        return {"posx": 0,
                "posy": 0,
                "width": self._project_width,
                "height": self._project_height}


class VideoUriSource(VideoSource):

    __gtype_name__ = "PitiviUriVideoSource"

    def __init__(self, element, timeline):
        VideoSource.__init__(self, element, timeline)
        self.get_style_context().add_class("VideoUriSource")

    def _get_previewer(self):
        if isinstance(self._ges_elem, GES.ImageSource):
            previewer = ImagePreviewer(self._ges_elem, self.timeline.app.settings.previewers_max_cpu)
        else:
            previewer = VideoPreviewer(self._ges_elem, self.timeline.app.settings.previewers_max_cpu)
        return previewer

    def _get_default_mixing_property(self):
        for spec in self._ges_elem.list_children_properties():
            if spec.name == "alpha":
                return spec
        return None


class AudioBackground(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self)
        self.get_style_context().add_class("AudioBackground")


class AudioUriSource(TimelineElement):

    __gtype_name__ = "PitiviAudioUriSource"

    def __init__(self, element, timeline):
        TimelineElement.__init__(self, element, timeline)
        self.get_style_context().add_class("AudioUriSource")

    def _get_previewer(self):
        previewer = AudioPreviewer(self._ges_elem, self.timeline.app.settings.previewers_max_cpu)
        return previewer

    def _get_background(self):
        return AudioBackground()

    def _get_default_mixing_property(self):
        for spec in self._ges_elem.list_children_properties():
            if spec.name == "volume":
                return spec
        return None


class TrimHandle(Gtk.EventBox, Loggable):

    __gtype_name__ = "PitiviTrimHandle"

    SELECTED_WIDTH = 5
    DEFAULT_WIDTH = 1
    PIXBUF = None

    def __init__(self, clip, edge):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.clip = clip
        self.edge = edge

        self.get_style_context().add_class("Trimbar")
        if edge == GES.Edge.EDGE_END:
            css_class = "right"
        else:
            css_class = "left"
        self.get_style_context().add_class(css_class)

        self.props.valign = Gtk.Align.FILL
        self.shrink()
        if edge == GES.Edge.EDGE_END:
            self.props.halign = Gtk.Align.END
        else:
            self.props.halign = Gtk.Align.START

    def do_draw(self, cr):
        Gtk.EventBox.do_draw(self, cr)
        if TrimHandle.PIXBUF is None:
            TrimHandle.PIXBUF = GdkPixbuf.Pixbuf.new_from_file(
                os.path.join(get_pixmap_dir(), "trimbar-focused.png"))
        Gdk.cairo_set_source_pixbuf(cr, TrimHandle.PIXBUF, 10, 10)

    def enlarge(self):
        self.props.width_request = TrimHandle.SELECTED_WIDTH
        if self.props.window:
            self.props.window.set_cursor(CURSORS[self.edge])

    def shrink(self):
        self.props.width_request = TrimHandle.DEFAULT_WIDTH
        if self.props.window:
            self.props.window.set_cursor(NORMAL_CURSOR)


class Clip(Gtk.EventBox, Loggable):

    __gtype_name__ = "PitiviClip"

    def __init__(self, layer: GES.Layer, ges_clip: GES.Clip):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        name = ges_clip.get_name()
        self.set_name(name)
        self.get_accessible().set_name(name)

        self._elements_container = None
        self.left_handle = None
        self.right_handle = None
        self.handles = []
        self.z_order = -1
        self.timeline = layer.timeline
        self.app = layer.app

        self.ges_clip = ges_clip
        self.ges_clip.selected = Selected()
        self.ges_clip.selected.selected = self.ges_clip in self.timeline.selection

        self.audio_widget = None
        self.video_widget = None

        self._setup_widget()
        self._force_position_update = True

        for ges_timeline_element in self.ges_clip.get_children(False):
            self._add_child(ges_timeline_element)

        set_state_flags_recurse(self, Gtk.StateFlags.SELECTED, are_set=self.ges_clip.selected)

        # Connect to Widget signals.
        self.connect("button-release-event", self._button_release_event_cb)
        self.connect("event", self._event_cb)

        # Connect to GES signals.
        self.ges_clip.connect("notify::start", self._start_changed_cb)
        self.ges_clip.connect("notify::inpoint", self._start_changed_cb)
        self.ges_clip.connect("notify::duration", self._duration_changed_cb)
        self.ges_clip.connect("notify::layer", self._layer_changed_cb)

        self.ges_clip.connect_after("child-added", self._child_added_cb)
        self.ges_clip.connect_after("child-removed", self._child_removed_cb)

        # To be able to receive effects dragged on clips.
        self.drag_dest_set(0, [EFFECT_TARGET_ENTRY], Gdk.DragAction.COPY)
        self.connect("drag-drop", self.__drag_drop_cb)

    def __drag_drop_cb(self, widget, context, x, y, timestamp):
        success = False

        target = self.drag_dest_find_target(context, None)
        if not target:
            return False

        if target.name() == EFFECT_TARGET_ENTRY.target:
            self.info("Adding effect %s", self.timeline.drop_data)
            self.timeline.selection.set_selection([self.ges_clip], SELECT)
            self.app.gui.editor.switch_context_tab(self.ges_clip)

            effect_info = self.app.effects.get_info(self.timeline.drop_data)
            pipeline = self.timeline.ges_timeline.get_parent()
            with self.app.action_log.started("add effect",
                                             finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                             toplevel=True):
                self.add_effect(effect_info)
            self.timeline.clean_drop_data()
            success = True

        Gtk.drag_finish(context, success, False, timestamp)

        return success

    def add_effect(self, effect_info):
        """Adds the specified effect if it can be applied to the clip.

        Args:
            effect_info (EffectInfo): The effect to add.
        """
        factory_name = effect_info.effect_name
        if factory_name in ALLOWED_ONLY_ONCE_EFFECTS:
            for effect in self.ges_clip.find_track_elements(None, GES.TrackType.VIDEO,
                                                            GES.BaseEffect):
                for elem in effect.get_nleobject().iterate_recurse():
                    if elem.get_factory().get_name() == factory_name:
                        self.error("Not adding %s as it would be duplicate"
                                   " and this is not allowed.", factory_name)
                        # TODO Let the user know about why it did not work.
                        return effect

        for track_element in self.ges_clip.get_children(False):
            if effect_info.good_for_track_element(track_element):
                # Actually add the effect
                effect = GES.Effect.new(effect_info.bin_description)
                self.ges_clip.add(effect)
                return effect
        return None

    def _add_child(self, ges_timeline_element):
        """Initializes added Clip's ges_timeline_element."""

    def update_position(self):
        """Updates the UI of the clip."""

    def _setup_widget(self):
        pass

    def _add_trim_handles(self):
        overlay = Gtk.Overlay()
        self.add(overlay)

        self._elements_container = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        overlay.add_overlay(self._elements_container)

        self.left_handle = TrimHandle(self, GES.Edge.EDGE_START)
        overlay.add_overlay(self.left_handle)

        self.right_handle = TrimHandle(self, GES.Edge.EDGE_END)
        overlay.add_overlay(self.right_handle)

        self.handles.append(self.left_handle)
        self.handles.append(self.right_handle)

    def shrink_trim_handles(self):
        for handle in self.handles:
            handle.shrink()

    def do_map(self):
        Gtk.EventBox.do_map(self)
        self.update_position()

    def _button_release_event_cb(self, unused_widget, event):
        self.debug("Button release event")

        if self.timeline.got_dragged:
            # This means a drag & drop operation just finished and
            # this button-release-event should be ignored.
            self.timeline.got_dragged = False
            return False

        res, button = event.get_button()
        if res and not button == 1:
            # Only the left mouse button selects.
            return False

        mode = SELECT
        if self.timeline.get_parent().control_mask:
            if not self.ges_clip.selected:
                mode = SELECT_ADD
            else:
                mode = UNSELECT
            clicked_layer, click_pos = self.timeline.get_clicked_layer_and_pos(event)
            self.timeline.set_selection_meta_info(clicked_layer, click_pos, mode)
        else:
            self.app.gui.editor.switch_context_tab(self.ges_clip)

        parent = self.ges_clip.get_toplevel_parent()
        if parent is self.ges_clip:
            selection = [self.ges_clip]
        else:
            selection = [elem for elem in parent.get_children(True)
                         if isinstance(elem, (GES.SourceClip, GES.TransitionClip))]
        self.timeline.selection.set_selection(selection, mode)

        return False

    def release(self):

        disconnect_all_by_func(self.ges_clip, self._start_changed_cb)
        disconnect_all_by_func(self.ges_clip, self._duration_changed_cb)
        disconnect_all_by_func(self.ges_clip, self._layer_changed_cb)
        disconnect_all_by_func(self.ges_clip, self._child_added_cb)
        disconnect_all_by_func(self.ges_clip, self._child_removed_cb)

    def _event_cb(self, element, event):
        prelight = None
        if (event.type == Gdk.EventType.ENTER_NOTIFY and
                event.mode == Gdk.CrossingMode.NORMAL and
                not self.timeline.scrubbing):
            prelight = True
            for handle in self.handles:
                handle.enlarge()
        elif (event.type == Gdk.EventType.LEAVE_NOTIFY and
              event.mode == Gdk.CrossingMode.NORMAL):
            prelight = False
            for handle in self.handles:
                handle.shrink()

        if prelight is not None:
            set_state_flags_recurse(self, Gtk.StateFlags.PRELIGHT, are_set=prelight, ignored_classes=(Marker,))

        return False

    def _start_changed_cb(self, clip, pspec):
        self.update_position()

    def _duration_changed_cb(self, clip, pspec):
        self.update_position()

    def _layer_changed_cb(self, ges_clip, pspec):
        self.update_position()

    def _child_added_cb(self, ges_clip, ges_timeline_element: GES.TimelineElement):
        self._force_position_update = True
        self._add_child(ges_timeline_element)
        self.update_position()

    def _remove_child(self, ges_timeline_element):
        pass

    def _child_removed_cb(self, unused_ges_clip, ges_timeline_element: GES.TimelineElement):
        self._force_position_update = True
        self._remove_child(ges_timeline_element)
        self.update_position()


class FullClip(Clip, Zoomable):
    """Full version of Clip(ui)."""

    def __init__(self, layer: GES.Layer, ges_clip: GES.Clip):
        Zoomable.__init__(self)
        Clip.__init__(self, layer, ges_clip)

        self.ges_clip.ui = self

    def _add_child(self, ges_timeline_element):
        ges_timeline_element.selected = Selected()
        ges_timeline_element.selected.selected = self.ges_clip.selected.selected
        ges_timeline_element.ui = None

    def update_position(self):
        ges_layer = self.ges_clip.props.layer
        layer = ges_layer.ui
        if not layer or layer != self.get_parent():
            # Things are not settled yet.
            return

        start = self.ges_clip.props.start
        duration = self.ges_clip.props.duration
        x = self.ns_to_pixel(start)
        # The calculation of the width assumes that the start is always
        # int(pixels_float). In that case, the rounding can add up and a pixel
        # might be lost if we ignore the start of the clip.
        width = self.ns_to_pixel(start + duration) - x

        parent_height = layer.props.height_request
        y = 0
        height = parent_height
        has_video = self.ges_clip.find_track_elements(None, GES.TrackType.VIDEO, GObject.TYPE_NONE)
        has_audio = self.ges_clip.find_track_elements(None, GES.TrackType.AUDIO, GObject.TYPE_NONE)
        if not has_video or not has_audio:
            if layer.media_types == (GES.TrackType.AUDIO | GES.TrackType.VIDEO):
                height = parent_height / 2
                if not has_video:
                    y = height

        if self._force_position_update or \
                x != self._current_x or \
                y != self._current_y or \
                width != self._current_width or \
                parent_height != self._current_parent_height or \
                layer != self._current_parent:

            offset_px = self.ns_to_pixel(self.ges_clip.props.in_point)

            for ges_timeline_element in self.ges_clip.get_children(False):
                if not ges_timeline_element.ui:
                    continue

                if ges_timeline_element.ui.markers:
                    ges_timeline_element.ui.markers.offset = offset_px

            layer.move(self, x, y)
            self.set_size_request(width, height)

            elements = self._elements_container.get_children()
            for child in elements:
                child.set_size(width, height / len(elements))

            self._force_position_update = False
            # pylint: disable=attribute-defined-outside-init
            self._current_x = x
            self._current_y = y
            self._current_width = width
            self._current_parent_height = parent_height
            self._current_parent = layer


class MiniClip(Clip):
    """Mini version of Clip(mini_ui)."""

    __gtype_name__ = "PitiviMiniClip"

    def __init__(self, layer, ges_clip):
        Clip.__init__(self, layer, ges_clip)

        self.ges_clip.mini_ui = self

    def _add_child(self, ges_timeline_element):
        ges_timeline_element.mini_ui = None

    def update_position(self):
        ges_layer = self.ges_clip.props.layer
        layer = ges_layer.mini_ui
        if not layer or layer != self.get_parent():
            # Things are not settled yet.
            return

        start = self.ges_clip.props.start
        duration = self.ges_clip.props.duration
        ratio = self.timeline.calc_best_zoom_ratio()
        x = Zoomable.ns_to_pixel(start, zoomratio=ratio)
        # The calculation of the width assumes that the start is always
        # int(pixels_float). In that case, the rounding can add up and a pixel
        # might be lost if we ignore the start of the clip.
        width = Zoomable.ns_to_pixel(start + duration, zoomratio=ratio) - x

        parent_height = layer.props.height_request
        y = 0

        if self._force_position_update or \
                x != self._current_x or \
                y != self._current_y or \
                width != self._current_width or \
                parent_height != self._current_parent_height or \
                layer != self._current_parent:

            layer.move(self, x, y)
            self.set_size_request(width, parent_height)

            self._force_position_update = False
            # pylint: disable=attribute-defined-outside-init
            self._current_x = x
            self._current_y = y
            self._current_width = width
            self._current_parent_height = parent_height
            self._current_parent = layer


class SourceClip():
    __gtype_name__ = "PitiviSourceClip"

    def _setup_widget(self):
        self._add_trim_handles()

        self.get_style_context().add_class("Clip")

    def _remove_child(self, ges_timeline_element):
        if ges_timeline_element.ui:
            ges_timeline_element.ui.release()
            self._elements_container.remove(ges_timeline_element.ui)
            ges_timeline_element.ui = None

        if ges_timeline_element.mini_ui:
            self._elements_container.remove(ges_timeline_element.mini_ui)
            ges_timeline_element.mini_ui = None

    def _create_child_widget(self, ges_source: GES.Source) -> Optional[Gtk.Widget]:
        raise NotImplementedError()


class FullSourceClip(SourceClip, FullClip):
    __gtype_name__ = "PitiviFullSourceClip"

    def __init__(self, layer, ges_clip):
        FullClip.__init__(self, layer, ges_clip)

    def __show_handles(self):
        for handle in self.handles:
            handle.show()

    def __hide_handles(self):
        for handle in self.handles:
            handle.hide()

    def __curve_enter_cb(self, unused_keyframe_curve):
        self.__hide_handles()

    def __curve_leave_cb(self, unused_keyframe_curve):
        self.__show_handles()

    def _connect_to_child_ui(self, ges_timeline_element: GES.TimelineElement):
        ges_timeline_element.ui.connect("curve-enter", self.__curve_enter_cb)
        ges_timeline_element.ui.connect("curve-leave", self.__curve_leave_cb)

    def _disconnect_from_child_ui(self, ges_timeline_element: GES.TimelineElement):
        ges_timeline_element.ui.release()

    def _add_child(self, ges_timeline_element: GES.TimelineElement):
        FullClip._add_child(self, ges_timeline_element)

        # In some cases a GESEffect is added here,
        # so we have to limit the markers initialization to GESSources.
        if not isinstance(ges_timeline_element, GES.Source):
            return

        ges_source: GES.Source = ges_timeline_element

        if not hasattr(ges_source, "markers_manager"):
            ges_source.markers_manager = MarkerListManager(self.app.settings, ges_source)

        widget = self._create_child_widget(ges_source)
        if not widget:
            return

        ges_source.ui = widget

        self._connect_to_child_ui(ges_source)

        if ges_source.get_track_type() == GES.TrackType.VIDEO:
            self._elements_container.pack_start(widget, expand=True, fill=False, padding=0)
        else:
            self._elements_container.pack_end(widget, expand=True, fill=False, padding=0)
        widget.set_visible(True)

    def release(self):
        for child in self.ges_clip.get_children(True):
            if child.ui:
                self._disconnect_from_child_ui(child)
        super().release()

    def _create_child_widget(self, ges_source: GES.Source) -> Optional[Gtk.Widget]:
        raise NotImplementedError()


class MiniSourceClip(SourceClip, MiniClip):
    __gtype_name__ = "PitiviMiniSourceClip"

    def __init__(self, layer, ges_clip):
        MiniClip.__init__(self, layer, ges_clip)

    def _add_child(self, ges_timeline_element):
        MiniClip._add_child(self, ges_timeline_element)

        ges_source: GES.Source = ges_timeline_element

        widget = self._create_child_widget(ges_source)
        if not widget:
            return

        ges_source.mini_ui = widget
        self._elements_container.pack_start(widget, expand=True, fill=False, padding=0)
        widget.set_visible(True)

    def _create_child_widget(self, ges_source: GES.Source) -> Optional[Gtk.Widget]:
        raise NotImplementedError()


class SimpleClip(MiniSourceClip):
    __gtype_name__ = "PitiviSimpleClip"

    def __init__(self, layer, ges_clip):
        MiniSourceClip.__init__(self, layer, ges_clip)
        self.get_style_context().add_class("SimpleClip")

    def do_query_tooltip(self, x, y, keyboard_mode, tooltip):
        tooltip.set_markup(filename_from_uri(
            self.ges_clip.get_asset().props.id))

        return True

    def _create_child_widget(self, ges_source: GES.Source) -> Optional[Gtk.Widget]:
        color, tooltip = GES_TYPE_COLOR_TOOLTIP.get(self.ges_clip.__gtype__, None)
        self.props.has_tooltip = tooltip
        return MiniPreview(color)


class UriClip(FullSourceClip):
    __gtype_name__ = "PitiviUriClip"

    def __init__(self, layer: GES.Layer, ges_clip: GES.Clip):
        FullSourceClip.__init__(self, layer, ges_clip)
        self.get_style_context().add_class("UriClip")
        self.props.has_tooltip = True

    def do_query_tooltip(self, x, y, keyboard_mode, tooltip):
        tooltip.set_markup(filename_from_uri(
            self.ges_clip.get_asset().props.id))

        return True

    def _create_child_widget(self, ges_source: GES.Source) -> Optional[Gtk.Widget]:
        if ges_source.get_track_type() == GES.TrackType.AUDIO:
            self.audio_widget = AudioUriSource(ges_source, self.timeline)
            return self.audio_widget
        elif ges_source.get_track_type() == GES.TrackType.VIDEO:
            self.video_widget = VideoUriSource(ges_source, self.timeline)
            return self.video_widget

        return None


class TestClip(FullSourceClip):
    __gtype_name__ = "PitiviTestClip"

    def __init__(self, layer: GES.Layer, ges_clip: GES.Clip):
        FullSourceClip.__init__(self, layer, ges_clip)
        self.get_style_context().add_class("TestClip")

    def _create_child_widget(self, ges_source: GES.Source) -> Optional[Gtk.Widget]:
        if ges_source.get_track_type() == GES.TrackType.VIDEO:
            self.video_widget = VideoTestSource(ges_source, self.timeline)
            return self.video_widget

        return None


class TitleClip(FullSourceClip):
    __gtype_name__ = "PitiviTitleClip"

    def __init__(self, layer: GES.Layer, ges_clip: GES.Clip):
        FullSourceClip.__init__(self, layer, ges_clip)
        self.get_style_context().add_class("TitleClip")

    def _create_child_widget(self, ges_source: GES.Source) -> Optional[Gtk.Widget]:
        if ges_source.get_track_type() == GES.TrackType.VIDEO:
            self.video_widget = TitleSource(ges_source, self.timeline)
            return self.video_widget

        return None


class TransitionClip():

    __gtype_name__ = "PitiviTransitionClip"

    def __init__(self):
        self.__has_video = False

        if self.__has_video:
            self.z_order = 1
        else:
            self.z_order = 0

        self.get_style_context().add_class("TransitionClip")

        # In the case of TransitionClips, we are the only container
        self._add_trim_handles()

        self.props.has_tooltip = True

    def do_query_tooltip(self, x, y, keyboard_mode, tooltip):
        if self.__has_video:
            markup = str(self.ges_clip.props.vtype.value_nick)
        else:
            markup = _("Audio crossfade")
        tooltip.set_text(markup)

        return True

    def _add_child(self, ges_timeline_element):
        if not isinstance(ges_timeline_element, GES.VideoTransition):
            return

        self.z_order = 1
        self.set_sensitive(True)
        self.__has_video = True
        ges_timeline_element.selected.connect("selected-changed", self._selected_changed_cb, ges_timeline_element)

    def _selected_changed_cb(self, unused_selected, selected, ges_timeline_element):
        if selected:
            self.app.gui.editor.trans_list.activate(ges_timeline_element)
        else:
            self.app.gui.editor.trans_list.deactivate()


class FullTransitionClip(TransitionClip, FullClip):

    __gtype_name__ = "PitiviFullTransitionClip"

    def __init__(self, layer: GES.Layer, ges_clip: GES.Clip):
        FullClip.__init__(self, layer, ges_clip)
        TransitionClip.__init__(self)

    def _add_child(self, ges_timeline_element):
        FullClip._add_child(self, ges_timeline_element)
        TransitionClip._add_child(self, ges_timeline_element)


class MiniTransitionClip(TransitionClip, MiniClip):

    __gtype_name__ = "PitiviMiniTransitionClip"

    def __init__(self, layer: GES.Layer, ges_clip: GES.Clip):
        MiniClip.__init__(self, layer, ges_clip)
        TransitionClip.__init__(self)

    def _add_child(self, ges_timeline_element):
        MiniClip._add_child(self, ges_timeline_element)
        TransitionClip._add_child(self, ges_timeline_element)


GES_TYPE_UI_TYPE = {
    GES.UriClip.__gtype__: UriClip,
    GES.TitleClip.__gtype__: TitleClip,
    GES.TransitionClip.__gtype__: FullTransitionClip,
    GES.TestClip.__gtype__: TestClip
}

GES_TYPE_COLOR_TOOLTIP = {
    GES.UriClip.__gtype__: ((0.214, 0.50, 0.39), True),
    GES.TitleClip.__gtype__: ((0.819, 0.20, 0.267), False),
    GES.TestClip.__gtype__: ((0.619, 0.670, 0.067), False)
}

GES_TYPE_MINI_UI_TYPE = {
    GES.UriClip.__gtype__: SimpleClip,
    GES.TitleClip.__gtype__: SimpleClip,
    GES.TransitionClip.__gtype__: MiniTransitionClip,
    GES.TestClip.__gtype__: SimpleClip
}
