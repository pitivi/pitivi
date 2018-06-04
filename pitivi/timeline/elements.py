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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import os
from gettext import gettext as _

import numpy
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import Gtk
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
from matplotlib.figure import Figure

from pitivi.configure import get_pixmap_dir
from pitivi.effects import ALLOWED_ONLY_ONCE_EFFECTS
from pitivi.effects import AUDIO_EFFECT
from pitivi.effects import VIDEO_EFFECT
from pitivi.timeline.previewers import AudioPreviewer
from pitivi.timeline.previewers import VideoPreviewer
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils import pipeline
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import disconnectAllByFunc
from pitivi.utils.misc import filename_from_uri
from pitivi.utils.timeline import SELECT
from pitivi.utils.timeline import SELECT_ADD
from pitivi.utils.timeline import Selected
from pitivi.utils.timeline import UNSELECT
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import EFFECT_TARGET_ENTRY
from pitivi.utils.ui import set_children_state_recurse
from pitivi.utils.ui import unset_children_state_recurse

KEYFRAME_LINE_HEIGHT = 2
KEYFRAME_LINE_ALPHA = 0.5
KEYFRAME_LINE_COLOR = "#EDD400"  # "Tango" medium yellow
KEYFRAME_NODE_COLOR = "#F57900"  # "Tango" medium orange
SELECTED_KEYFRAME_NODE_COLOR = "#204A87" # "Tango" dark sky blue
HOVERED_KEYFRAME_NODE_COLOR = "#3465A4" # "Tango" medium sky blue

CURSORS = {
    GES.Edge.EDGE_START: Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE),
    GES.Edge.EDGE_END: Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE)
}

NORMAL_CURSOR = Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)
DRAG_CURSOR = Gdk.Cursor.new(Gdk.CursorType.HAND1)


def get_pspec(element_factory_name, propname):
    element = Gst.ElementFactory.make(element_factory_name)
    if not element:
        return None

    return [prop for prop in element.list_properties() if prop.name == propname][0]


class KeyframeCurve(FigureCanvas, Loggable):
    YLIM_OVERRIDES = {}

    __YLIM_OVERRIDES_VALUES = [("volume", "volume", (0.0, 0.2))]

    for factory_name, propname, values in __YLIM_OVERRIDES_VALUES:
        pspec = get_pspec(factory_name, propname)
        if pspec:
            YLIM_OVERRIDES[pspec] = values

    __gsignals__ = {
        # Signal the keyframes or the curve are being hovered
        "enter": (GObject.SIGNAL_RUN_LAST, None, ()),
        # Signal the keyframes or the curve are not being hovered anymore
        "leave": (GObject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self, timeline, binding):
        figure = Figure()
        FigureCanvas.__init__(self, figure)
        Loggable.__init__(self)

        self._timeline = timeline
        self.__source = binding.props.control_source
        self._connect_sources()
        self.__propertyName = binding.props.name
        self.__paramspec = binding.pspec
        self.get_style_context().add_class("KeyframeCurve")

        self.__ylim_min, self.__ylim_max = KeyframeCurve.YLIM_OVERRIDES.get(
            binding.pspec, (0.0, 1.0))

        # Curve values, basically separating source.get_values() timestamps
        # and values.
        self._line_xs = []
        self._line_ys = []

        # facecolor to None for transparency
        self._ax = figure.add_axes([0, 0, 1, 1], facecolor='None')
        # Clear the Axes object.
        self._ax.cla()

        # FIXME: drawing a grid and ticks would be nice, but
        # matplotlib is too slow for now.
        self._ax.grid(False)

        self._ax.tick_params(axis='both',
                             which='both',
                             bottom='off',
                             top='off',
                             right='off',
                             left='off')

        # This seems to also be necessary for transparency ..
        figure.patch.set_visible(False)

        # The PathCollection object holding the keyframes dots.
        sizes = [50]
        self._keyframes = self._ax.scatter([], [], marker='D', s=sizes,
                                           c=KEYFRAME_NODE_COLOR, zorder=2)

        # matplotlib weirdness, simply here to avoid a warning ..
        self._keyframes.set_picker(True)

        # The Line2D object holding the lines between keyframes.
        self.__line = self._ax.plot([], [],
                                    alpha=KEYFRAME_LINE_ALPHA,
                                    c=KEYFRAME_LINE_COLOR,
                                    linewidth=KEYFRAME_LINE_HEIGHT, zorder=1)[0]
        self._update_plots()

        # Drag and drop logic
        # Whether the clicked keyframe or line has been dragged.
        self._dragged = False
        # The inpoint of the clicked keyframe.
        self._offset = None
        # The (offset, value) of both keyframes of the clicked keyframe line.
        self.__clicked_line = ()
        # Whether the mouse events go to the keyframes logic.
        self.handling_motion = False

        self.__hovered = False

        self.connect("motion-notify-event", self.__gtkMotionEventCb)
        self.connect("event", self._eventCb)
        self.connect("notify::height-request", self.__heightRequestCb)

        self.mpl_connect('button_press_event', self._mpl_button_press_event_cb)
        self.mpl_connect('button_release_event', self._mpl_button_release_event_cb)
        self.mpl_connect('motion_notify_event', self._mpl_motion_event_cb)

    def release(self):
        disconnectAllByFunc(self, self.__heightRequestCb)
        disconnectAllByFunc(self, self.__gtkMotionEventCb)
        disconnectAllByFunc(self, self._controlSourceChangedCb)

    def _connect_sources(self):
        self.__source.connect("value-added", self._controlSourceChangedCb)
        self.__source.connect("value-removed", self._controlSourceChangedCb)
        self.__source.connect("value-changed", self._controlSourceChangedCb)

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
        self.__computeYlim()

        arr = numpy.array((self._line_xs, self._line_ys))
        arr = arr.transpose()
        self._keyframes.set_offsets(arr)
        self.__line.set_xdata(self._line_xs)
        self.__line.set_ydata(self._line_ys)
        self.queue_draw()

    # Private methods
    def __computeYlim(self):
        height = self.props.height_request

        if height <= 0:
            return

        ylim_min = -(KEYFRAME_LINE_HEIGHT / height)
        ylim_max = (self.__ylim_max * height) / (height - KEYFRAME_LINE_HEIGHT)
        self._ax.set_ylim(ylim_min, ylim_max)

    def __heightRequestCb(self, unused_self, unused_pspec):
        self.__computeYlim()

    def __maybeCreateKeyframe(self, event):
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

    # Callbacks
    def _controlSourceChangedCb(self, unused_control_source, unused_timed_value):
        self._update_plots()
        self._timeline.ges_timeline.get_parent().commit_timeline()

    def __gtkMotionEventCb(self, unused_widget, unused_event):
        # We need to do this here, because Matplotlib's callbacks can't stop
        # signal propagation.
        if self.handling_motion:
            return True
        return False

    def _eventCb(self, unused_element, event):
        if event.type == Gdk.EventType.LEAVE_NOTIFY:
            cursor = NORMAL_CURSOR
            self._timeline.get_window().set_cursor(cursor)
        return False

    def _mpl_button_press_event_cb(self, event):
        if event.button != 1:
            return

        result = self._keyframes.contains(event)
        if result[0]:
            # A keyframe has been clicked.
            keyframe_index = result[1]['ind'][0]
            offsets = self._keyframes.get_offsets()
            offset = offsets[keyframe_index][0]

            if event.guiEvent.type == Gdk.EventType._2BUTTON_PRESS:
                index = result[1]['ind'][0]
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
                self._offset = offset
                self.handling_motion = True
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
                keyframe_ts = self.__computeKeyframeNewTimestamp(event)
                ydata = max(self.__ylim_min, min(event.ydata, self.__ylim_max))

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
        if event.button != 1:
            return

        # In order to make sure we seek to the exact position where we added a
        # new keyframe, we don't use matplotlib's event.xdata, but rather
        # compute it the same way we do for the seek logic.
        event_widget = Gtk.get_event_widget(event.guiEvent)
        x, unused_y = event_widget.translate_coordinates(self._timeline.layout.layers_vbox,
                                                         event.x, event.y)
        ges_clip = self._timeline.selection.getSingleClip(GES.Clip)
        event.xdata = Zoomable.pixelToNs(x) - ges_clip.props.start + ges_clip.props.in_point

        if self._offset is not None:
            # If dragging a keyframe, make sure the keyframe ends up exactly
            # where the mouse was released. Otherwise, the playhead will not
            # seek exactly on the keyframe.
            if self._dragged:
                if event.ydata is not None:
                    keyframe_ts = self.__computeKeyframeNewTimestamp(event)
                    ydata = max(self.__ylim_min, min(event.ydata, self.__ylim_max))
                    self._move_keyframe(int(self._offset), keyframe_ts, ydata)
            self.debug("Keyframe released")
            self._timeline.app.action_log.commit("Move keyframe")
        elif self.__clicked_line:
            self.debug("Line released")
            self._timeline.app.action_log.commit("Move keyframe curve segment")

            if not self._dragged:
                # The keyframe line was clicked, but not dragged
                assert event.guiEvent.type == Gdk.EventType.BUTTON_RELEASE
                self.__maybeCreateKeyframe(event)

        self.handling_motion = False
        self._offset = None
        self.__clicked_line = ()
        self._dragged = False

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
                self.__propertyName,
                Gst.TIME_ARGS(xdata),
                "{:.3f}".format(value))
        self.set_tooltip_markup(markup)

    def __computeKeyframeNewTimestamp(self, event):
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

    def __init__(self, timeline, bindings):
        self.__bindings = bindings
        super().__init__(timeline, bindings[0])

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
            source.connect("value-added", self._controlSourceChangedCb)
            source.connect("value-removed", self._controlSourceChangedCb)
            source.connect("value-changed", self._controlSourceChangedCb)

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
        if event.button == 1:
            if self._offset is not None and not self._dragged:
                # A keyframe was clicked but not dragged, so we
                # should select it by seeking to its position.
                source = self._timeline.selection.getSingleClip()
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

    def _controlSourceChangedCb(self, control_source, timed_value):
        super()._controlSourceChangedCb(control_source, timed_value)
        self.__update_selected_keyframe()
        self.__hide_special_keyframe(self.__hovered_keyframe)

    def _position_cb(self, unused_pipeline, unused_position):
        self.__update_selected_keyframe()

    def __update_selected_keyframe(self):
        try:
            position = self._project.pipeline.getPosition()
        except pipeline.PipelineError:
            self.warning("Could not get pipeline position")
            return

        source = self._timeline.selection.getSingleClip()
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
        "curve-enter": (GObject.SIGNAL_RUN_LAST, None, ()),
        # Signal the keyframes curve are not being hovered anymore
        "curve-leave": (GObject.SIGNAL_RUN_LAST, None, ()),
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
            "selected-changed", self.__selectedChangedCb)

        self.__width = 0
        self.__height = 0

        # Needed for effect's keyframe toggling
        self._ges_elem.ui_element = self

        self.props.vexpand = True

        self.__previewer = self._getPreviewer()
        if self.__previewer:
            self.add(self.__previewer)

        self.__background = self._getBackground()
        if self.__background:
            self.add(self.__background)

        self.keyframe_curve = None
        self.show_all()

        # We set up the default mixing property right here, if a binding was
        # already set (when loading a project), it will be added later
        # and override that one.
        self.showDefaultKeyframes(lazy_render=True)

    def release(self):
        if self.__previewer:
            self.__previewer.release()

    # Public API
    def setSize(self, width, height):
        width = max(0, width)
        self.set_size_request(width, height)

        if self.__previewer:
            self.__previewer.set_size_request(width, height)

        if self.__background:
            self.__background.set_size_request(width, height)

        if self.keyframe_curve:
            self.keyframe_curve.set_size_request(width, height)

        self.__width = width
        self.__height = height

    def showKeyframes(self, ges_elem, prop):
        self.__setKeyframes(ges_elem, prop)
        binding = ges_elem.get_control_binding(prop.name)
        self.__create_keyframe_curve([binding])

    def showDefaultKeyframes(self, lazy_render=False):
        self.__setKeyframes(self._ges_elem, self._getDefaultMixingProperty())
        if not lazy_render:
            self.__create_keyframe_curve()

    def showMultipleKeyframes(self, bindings):
        self.__controlledProperty = None
        self.__create_keyframe_curve(bindings)

    def __setKeyframes(self, ges_elem, prop):
        self.__removeKeyframes()
        self.__controlledProperty = prop
        if self.__controlledProperty:
            self.__createControlBinding(ges_elem)

    def __curveEnterCb(self, unused_keyframe_curve):
        self.emit("curve-enter")

    def __curveLeaveCb(self, unused_keyframe_curve):
        self.emit("curve-leave")

    def __removeKeyframes(self):
        if not self.keyframe_curve:
            # Nothing to remove.
            return

        self.keyframe_curve.disconnect_by_func(self.__curveEnterCb)
        self.keyframe_curve.disconnect_by_func(self.__curveLeaveCb)
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
            val = float(self.__controlledProperty.default_value) / \
                (self.__controlledProperty.maximum -
                 self.__controlledProperty.minimum)
            inpoint = self._ges_elem.props.in_point
            assert source.set(inpoint, val)
            assert source.set(inpoint + self._ges_elem.props.duration, val)

    def __create_keyframe_curve(self, bindings=[]):
        """Creates required keyframe curve."""
        self.__removeKeyframes()
        if not bindings:
            bindings = [self._ges_elem.get_control_binding(self.__controlledProperty.name)]

        if len(bindings) == 1:
            self.keyframe_curve = KeyframeCurve(self.timeline, bindings[0])
        else:
            self.keyframe_curve = MultipleKeyframeCurve(self.timeline, bindings)

        self.keyframe_curve.connect("enter", self.__curveEnterCb)
        self.keyframe_curve.connect("leave", self.__curveLeaveCb)
        self.keyframe_curve.set_size_request(self.__width, self.__height)
        self.keyframe_curve.show()
        self.__update_keyframe_curve_visibility()

    def __createControlBinding(self, element):
        """Creates the required ControlBinding and keyframes."""
        if self.__controlledProperty:
            element.connect("control-binding-added",
                            self.__controlBindingAddedCb)
            binding = \
                element.get_control_binding(self.__controlledProperty.name)

            if binding:
                self.__ensure_keyframes(binding)

                return

            source = GstController.InterpolationControlSource()
            source.props.mode = GstController.InterpolationMode.LINEAR
            element.set_control_source(source,
                                       self.__controlledProperty.name, "direct")

    def __controlBindingAddedCb(self, unused_ges_elem, binding):
        if binding.props.name == self.__controlledProperty.name:
            self.__ensure_keyframes(binding)

    def do_draw(self, cr):
        self.propagate_draw(self.__background, cr)

        if self.__previewer:
            self.propagate_draw(self.__previewer, cr)

        if self.keyframe_curve and self.keyframe_curve.is_drawable():
            project = self.timeline.app.project_manager.current_project
            if project.pipeline.getState() != Gst.State.PLAYING:
                self.propagate_draw(self.keyframe_curve, cr)

    # Callbacks
    def __selectedChangedCb(self, unused_selected, selected):
        if not self.keyframe_curve and self.__controlledProperty and \
                selected and len(self.timeline.selection) == 1:
            self.__create_keyframe_curve()

        if self.keyframe_curve:
            self.__update_keyframe_curve_visibility()

        if self.__previewer:
            self.__previewer.set_selected(selected)

    def __update_keyframe_curve_visibility(self):
        """Updates the keyframes widget visibility by adding or removing it."""
        if self._ges_elem.selected and len(self.timeline.selection) == 1:
            if not self.keyframe_curve.get_parent():
                self.add(self.keyframe_curve)
        else:
            self.remove(self.keyframe_curve)

    # Virtual methods
    def _getPreviewer(self):
        """Gets a Gtk.Widget to be used as previewer.

        This previewer will be automatically scaled to the width and
        height of the TimelineElement.

        Returns:
            Gtk.Widget: The widget showing thumbnails, waveforms, etc.
        """
        return None

    def _getBackground(self):
        """Gets a Gtk.Widget to be used as background.

        Returns:
            Gtk.Widget: The widget identifying the clip type.
        """
        return None

    def _getDefaultMixingProperty(self):
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

    def __parent_child_added_cb(self, parent, child):
        project = self.timeline.app.project_manager.current_project
        self.__apply_new_size_if_needed(project)

    def __parent_child_removed_cb(self, parent, child):
        project = self.timeline.app.project_manager.current_project
        if child == self.__videoflip:
            self.__videoflip = None
            self.__apply_new_size_if_needed(project)
            disconnectAllByFunc(child, self.__videoflip_changed_cb)

    def __videoflip_changed_cb(self, unused_child=None,
                               unused_element=None,
                               unused_pspec=None):
        project = self.timeline.app.project_manager.current_project
        self.__apply_new_size_if_needed(project)

    def __retrieve_project_size(self):
        project = self.timeline.app.project_manager.current_project

        self._project_width = project.videowidth
        self._project_height = project.videoheight

    def _project_video_size_changed_cb(self, project):
        self.__apply_new_size_if_needed(project)

    def __apply_new_size_if_needed(self, project):
        using_defaults = True
        for name, default_value in self.default_position.items():
            res, value = self._ges_elem.get_child_property(name)
            assert res
            if value != default_value:
                using_defaults = False
                break

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

        asset_width = sinfo.get_square_width()
        asset_height = sinfo.get_height()
        parent = video_source.get_parent()
        if parent and not self.__videoflip:
            for track_element in parent.find_track_elements(
                    None, GES.TrackType.VIDEO, GES.BaseEffect):

                res, videoflip, unused_pspec = track_element.lookup_child(
                    "GstVideoFlip::method")
                if res:
                    self.__videoflip = track_element
                    track_element.connect("deep-notify",
                                          self.__videoflip_changed_cb)
                    track_element.connect("notify::active",
                                          self.__videoflip_changed_cb)

        if self.__videoflip:
            res, method = self.__videoflip.get_child_property("method")
            assert res
            if "clockwise" in method.value_nick and self.__videoflip.props.active:
                asset_width = sinfo.get_height()
                asset_height = sinfo.get_square_width()

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

    def _getBackground(self):
        return VideoBackground()


class TitleSource(VideoSource):

    __gtype_name__ = "PitiviTitleSource"

    def _getDefaultMixingProperty(self):
        for spec in self._ges_elem.list_children_properties():
            if spec.name == "alpha":
                return spec

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

    def _getPreviewer(self):
        previewer = VideoPreviewer(self._ges_elem, self.timeline.app.settings.previewers_max_cpu)
        previewer.get_style_context().add_class("VideoUriSource")

        return previewer

    def _getDefaultMixingProperty(self):
        for spec in self._ges_elem.list_children_properties():
            if spec.name == "alpha":
                return spec


class AudioBackground(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self)
        self.get_style_context().add_class("AudioBackground")


class AudioUriSource(TimelineElement):

    __gtype_name__ = "PitiviAudioUriSource"

    def __init__(self, element, timeline):
        TimelineElement.__init__(self, element, timeline)
        self.get_style_context().add_class("AudioUriSource")

    def _getPreviewer(self):
        previewer = AudioPreviewer(self._ges_elem, self.timeline.app.settings.previewers_max_cpu)
        previewer.get_style_context().add_class("AudioUriSource")

        return previewer

    def _getBackground(self):
        return AudioBackground()

    def _getDefaultMixingProperty(self):
        for spec in self._ges_elem.list_children_properties():
            if spec.name == "volume":
                return spec


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


class Clip(Gtk.EventBox, Zoomable, Loggable):

    __gtype_name__ = "PitiviClip"

    def __init__(self, layer, ges_clip):
        Gtk.EventBox.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        name = ges_clip.get_name()
        self.set_name(name)
        self.get_accessible().set_name(name)

        self.handles = []
        self.z_order = -1
        self.timeline = layer.timeline
        self.app = layer.app

        self.ges_clip = ges_clip
        self.ges_clip.ui = self
        self.ges_clip.selected = Selected()

        self._audioSource = None
        self._videoSource = None

        self._setupWidget()
        self.__force_position_update = True

        for ges_timeline_element in self.ges_clip.get_children(False):
            self._add_child(ges_timeline_element)
            self.__connect_to_child(ges_timeline_element)

        # Connect to Widget signals.
        self.connect("button-release-event", self._button_release_event_cb)
        self.connect("event", self._eventCb)

        # Connect to GES signals.
        self.ges_clip.connect("notify::start", self._startChangedCb)
        self.ges_clip.connect("notify::inpoint", self._startChangedCb)
        self.ges_clip.connect("notify::duration", self._durationChangedCb)
        self.ges_clip.connect("notify::layer", self._layerChangedCb)

        self.ges_clip.connect_after("child-added", self._child_added_cb)
        self.ges_clip.connect_after("child-removed", self._child_removed_cb)

        # To be able to receive effects dragged on clips.
        self.drag_dest_set(0, [EFFECT_TARGET_ENTRY], Gdk.DragAction.COPY)
        self.connect("drag-drop", self.__dragDropCb)

    @property
    def layer(self):
        ges_layer = self.ges_clip.props.layer
        return ges_layer.ui if ges_layer else None

    def __dragDropCb(self, unused_widget, context, x, y, timestamp):
        success = False

        target = self.drag_dest_find_target(context, None)
        if not target:
            return False

        if target.name() == EFFECT_TARGET_ENTRY.target:
            self.info("Adding effect %s", self.timeline.dropData)
            self.timeline.resetSelectionGroup()
            self.timeline.current_group.add(self.ges_clip)
            self.timeline.selection.setSelection([self.ges_clip], SELECT)
            self.app.gui.editor.switchContextTab(self.ges_clip)

            effect_info = self.app.effects.getInfo(self.timeline.dropData)
            pipeline = self.timeline.ges_timeline.get_parent()
            with self.app.action_log.started("add effect",
                                             finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                             toplevel=True):
                self.add_effect(effect_info)
            self.timeline.cleanDropData()
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

    def updatePosition(self):
        layer = self.layer
        if not layer or layer != self.get_parent():
            # Things are not settled yet.
            return

        start = self.ges_clip.props.start
        duration = self.ges_clip.props.duration
        x = self.nsToPixel(start)
        # The calculation of the width assumes that the start is always
        # int(pixels_float). In that case, the rounding can add up and a pixel
        # might be lost if we ignore the start of the clip.
        width = self.nsToPixel(start + duration) - x

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

        if self.__force_position_update or \
                x != self._current_x or \
                y != self._current_y or \
                width != self._curent_width or \
                parent_height != self._current_parent_height or \
                layer != self._current_parent:

            layer.move(self, x, y)
            self.set_size_request(width, height)

            elements = self._elements_container.get_children()
            for child in elements:
                child.setSize(width, height / len(elements))

            self.__force_position_update = False
            self._current_x = x
            self._current_y = y
            self._curent_width = width
            self._current_parent_height = parent_height
            self._current_parent = layer

    def _setupWidget(self):
        pass

    def _addTrimHandles(self):
        overlay = Gtk.Overlay()
        self.add(overlay)

        self._elements_container = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        overlay.add_overlay(self._elements_container)

        self.leftHandle = TrimHandle(self, GES.Edge.EDGE_START)
        overlay.add_overlay(self.leftHandle)

        self.rightHandle = TrimHandle(self, GES.Edge.EDGE_END)
        overlay.add_overlay(self.rightHandle)

        self.handles.append(self.leftHandle)
        self.handles.append(self.rightHandle)

    def shrinkTrimHandles(self):
        for handle in self.handles:
            handle.shrink()

    def do_map(self):
        Gtk.EventBox.do_map(self)
        self.updatePosition()

    def _button_release_event_cb(self, unused_widget, event):
        if self.timeline.got_dragged:
            # This means a drag & drop operation just finished and
            # this button-release-event should be ignored.
            self.timeline.got_dragged = False
            return False

        res, button = event.get_button()
        if res and not button == 1:
            # Only the left mouse button selects.
            return False

        # TODO : Let's be more specific, masks etc ..
        mode = SELECT
        if self.timeline.get_parent()._controlMask:
            if not self.get_state_flags() & Gtk.StateFlags.SELECTED:
                mode = SELECT_ADD
                self.timeline.current_group.add(
                    self.ges_clip.get_toplevel_parent())
            else:
                self.timeline.current_group.remove(
                    self.ges_clip.get_toplevel_parent())
                mode = UNSELECT
            clicked_layer, click_pos = self.timeline.get_clicked_layer_and_pos(event)
            self.timeline.set_selection_meta_info(clicked_layer, click_pos, mode)
        else:
            self.timeline.resetSelectionGroup()
            self.timeline.current_group.add(self.ges_clip.get_toplevel_parent())
            self.app.gui.editor.switchContextTab(self.ges_clip)

        parent = self.ges_clip.get_parent()
        if parent == self.timeline.current_group or parent is None:
            selection = [self.ges_clip]
        else:
            while True:
                grandparent = parent.get_parent()
                if not grandparent or grandparent == self.timeline.current_group:
                    break

                parent = grandparent
            children = parent.get_children(True)
            selection = [elem for elem in children if isinstance(elem, GES.SourceClip) or
                         isinstance(elem, GES.TransitionClip)]

        self.timeline.selection.setSelection(selection, mode)

        return False

    def release(self):
        for child in self.ges_clip.get_children(True):
            self.__disconnectFromChild(child)

        disconnectAllByFunc(self.ges_clip, self._startChangedCb)
        disconnectAllByFunc(self.ges_clip, self._durationChangedCb)
        disconnectAllByFunc(self.ges_clip, self._layerChangedCb)
        disconnectAllByFunc(self.ges_clip, self._child_added_cb)
        disconnectAllByFunc(self.ges_clip, self._child_removed_cb)

    def __showHandles(self):
        for handle in self.handles:
            handle.show()

    def __hideHandles(self):
        for handle in self.handles:
            handle.hide()

    def _eventCb(self, element, event):
        if (event.type == Gdk.EventType.ENTER_NOTIFY and
                event.mode == Gdk.CrossingMode.NORMAL and
                not self.timeline._scrubbing):
            set_children_state_recurse(self, Gtk.StateFlags.PRELIGHT)
            for handle in self.handles:
                handle.enlarge()
        elif (event.type == Gdk.EventType.LEAVE_NOTIFY and
                event.mode == Gdk.CrossingMode.NORMAL):
            unset_children_state_recurse(self, Gtk.StateFlags.PRELIGHT)
            for handle in self.handles:
                handle.shrink()

        return False

    def _startChangedCb(self, unused_clip, unused_pspec):
        self.updatePosition()

    def _durationChangedCb(self, unused_clip, unused_pspec):
        self.updatePosition()

    def _layerChangedCb(self, ges_clip, unused_pspec):
        self.updatePosition()

    def __disconnectFromChild(self, child):
        if child.ui:
            child.ui.release()

    def __connect_to_child(self, child):
        if child.ui:
            child.ui.connect("curve-enter", self.__curveEnterCb)
            child.ui.connect("curve-leave", self.__curveLeaveCb)

    def __curveEnterCb(self, unused_keyframe_curve):
        self.__hideHandles()

    def __curveLeaveCb(self, unused_keyframe_curve):
        self.__showHandles()

    def _add_child(self, ges_timeline_element):
        ges_timeline_element.selected = Selected()
        ges_timeline_element.ui = None

    def _child_added_cb(self, unused_ges_clip, ges_timeline_element):
        self.__force_position_update = True
        self._add_child(ges_timeline_element)
        self.__connect_to_child(ges_timeline_element)
        self.updatePosition()

    def _remove_child(self, ges_timeline_element):
        pass

    def _child_removed_cb(self, unused_ges_clip, ges_timeline_element):
        self.__force_position_update = True
        self.__disconnectFromChild(ges_timeline_element)
        self._remove_child(ges_timeline_element)
        self.updatePosition()


class SourceClip(Clip):
    __gtype_name__ = "PitiviSourceClip"

    def __init__(self, layer, ges_clip):
        Clip.__init__(self, layer, ges_clip)

    def _setupWidget(self):
        self._addTrimHandles()

        self.get_style_context().add_class("Clip")

    def _remove_child(self, ges_timeline_element):
        if ges_timeline_element.ui:
            self._elements_container.remove(ges_timeline_element.ui)
            ges_timeline_element.ui = None


class UriClip(SourceClip):
    __gtype_name__ = "PitiviUriClip"

    def __init__(self, layer, ges_clip):
        SourceClip.__init__(self, layer, ges_clip)
        self.props.has_tooltip = True

    def do_query_tooltip(self, x, y, keyboard_mode, tooltip):
        tooltip.set_markup(filename_from_uri(
            self.ges_clip.get_asset().props.id))

        return True

    def _add_child(self, ges_timeline_element):
        SourceClip._add_child(self, ges_timeline_element)

        if not isinstance(ges_timeline_element, GES.Source):
            return

        if ges_timeline_element.get_track_type() == GES.TrackType.AUDIO:
            self._audioSource = AudioUriSource(ges_timeline_element, self.timeline)
            ges_timeline_element.ui = self._audioSource
            self._elements_container.pack_end(self._audioSource, True, False, 0)
            self._audioSource.set_visible(True)
        elif ges_timeline_element.get_track_type() == GES.TrackType.VIDEO:
            self._videoSource = VideoUriSource(ges_timeline_element, self.timeline)
            ges_timeline_element.ui = self._videoSource
            self._elements_container.pack_start(self._videoSource, True, False, 0)
            self._videoSource.set_visible(True)


class TitleClip(SourceClip):
    __gtype_name__ = "PitiviTitleClip"

    def _add_child(self, ges_timeline_element):
        SourceClip._add_child(self, ges_timeline_element)

        if not isinstance(ges_timeline_element, GES.Source):
            return

        if ges_timeline_element.get_track_type() == GES.TrackType.VIDEO:
            self._videoSource = TitleSource(ges_timeline_element, self.timeline)
            ges_timeline_element.ui = self._videoSource
            self._elements_container.pack_start(self._videoSource, True, False, 0)
            self._videoSource.set_visible(True)


class TransitionClip(Clip):

    __gtype_name__ = "PitiviTransitionClip"

    def __init__(self, layer, ges_clip):
        self.__has_video = False

        Clip.__init__(self, layer, ges_clip)

        if self.__has_video:
            self.z_order = 1
        else:
            self.z_order = 0

        self.get_style_context().add_class("TransitionClip")

        # In the case of TransitionClips, we are the only container
        self._addTrimHandles()

        self.props.has_tooltip = True

    def do_query_tooltip(self, x, y, keyboard_mode, tooltip):
        if self.__has_video:
            markup = str(self.ges_clip.props.vtype.value_nick)
        else:
            markup = _("Audio crossfade")
        tooltip.set_text(markup)

        return True

    def _add_child(self, ges_timeline_element):
        Clip._add_child(self, ges_timeline_element)

        if not isinstance(ges_timeline_element, GES.VideoTransition):
            return

        self.z_order = 1
        self.set_sensitive(True)
        self.__has_video = True
        ges_timeline_element.selected.connect("selected-changed", self._selectedChangedCb, ges_timeline_element)

    def _selectedChangedCb(self, unused_selected, selected, ges_timeline_element):
        if selected:
            self.app.gui.editor.trans_list.activate(ges_timeline_element)
        else:
            self.app.gui.editor.trans_list.deactivate()


GES_TYPE_UI_TYPE = {
    GES.UriClip.__gtype__: UriClip,
    GES.TitleClip.__gtype__: TitleClip,
    GES.TransitionClip.__gtype__: TransitionClip
}
