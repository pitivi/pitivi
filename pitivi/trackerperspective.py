# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Vivek R <123vivekr@gmail.com>
# Copyright (c) 2022, Alex Băluț <alexandru.balut@gmail.com>
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
"""Pitivi's Tracker perspective."""
import json
import os
import uuid
from gettext import gettext as _
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import cairo
import numpy
from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import GstVideo
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.perspective import Perspective
from pitivi.utils.loggable import Loggable
from pitivi.utils.pipeline import AssetPipeline
from pitivi.utils.pipeline import SimplePipeline
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import NORMAL_CURSOR
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SPACING

# The meta of an Asset holding all the tracked objects data version 1.
ASSET_TRACKED_OBJECTS_META = "pitivi::tracker_data::1"

# The meta of an Effect holding the object_id of the tracked object.
EFFECT_TRACKED_OBJECT_ID_META = "pitivi:tracked_object_id"
# The meta of an Effect holding the name of the tracked object.
EFFECT_TRACKED_OBJECT_NAME_META = "pitivi:tracked_object_name"


# TODO: Replace with bisect.bisect_left when we use Python 3.10.
def bisect_left(values, val, key):
    low = 0
    high = len(values)
    while low < high:
        mid = (low + high) // 2
        if key(values[mid]) < val:
            low = mid + 1
        else:
            high = mid
    return low


class ObjectManager():
    """Manager of an Asset's tracked objects.

    Attributes:
        asset (GES.Asset): The Asset in which the objects are being tracked.
        objects (List[Tuple[int, str, str]]): The objects stored as
            (index, object_id, name) tuples.
        values (Dict[str, List[Tuple[int, Tuple[float, float, float, float]]]]):
            The tracking data for each object is kept as a list of
            (timestamp, rectangle) tuples, always ordered.
    """

    def __init__(self, asset: GES.Asset):
        self.asset: GES.Asset = asset
        # The list of objects kept in a persistent order.
        # (index, object_id, name)
        self.objects: List[Tuple[int, str, str]] = []
        # object_id -> [(timestamp, (x, y, w, h)), ...]
        self.values: Dict[str, List[Tuple[int, Tuple[float, float, float, float]]]] = {}

        dump_str = self.asset.get_string(ASSET_TRACKED_OBJECTS_META)
        if dump_str:
            data = json.loads(dump_str)
            objects, values = data
            # Convert lists back to tuples.
            self.objects = [tuple(o) for o in objects]
            self.values = {object_id: [(position, tuple(area)) for (position, area) in values_list]
                           for object_id, values_list in values.items()}

    def save(self):
        data = [self.objects, self.values]
        dump_str = json.dumps(data)
        if self.asset.check_meta_registered(ASSET_TRACKED_OBJECTS_META):
            self.asset.set_string(ASSET_TRACKED_OBJECTS_META, dump_str)
        else:
            self.asset.register_meta_string(GES.MetaFlag.READWRITE, ASSET_TRACKED_OBJECTS_META, dump_str)

    def update_object(self, object_id: str, start_pos: int, roi_data: Dict[int, Tuple[float, float, float, float]]):
        """Updates the values from the specified position to the end."""
        object_values: List[Tuple[int, Tuple[float, float, float, float]]] = self.values[object_id]
        index: int = bisect_left(object_values, start_pos, key=lambda x: x[0])
        object_values = object_values[:index]
        object_values.extend(sorted(roi_data.items()))
        self.values[object_id] = object_values

    def update_object_position(self, object_id: str, position: int, area: Tuple[float, float, float, float]):
        object_values: List[Tuple[int, Tuple[float, float, float, float]]] = self.values[object_id]
        index: int = bisect_left(object_values, position, key=lambda x: x[0])
        if index < len(object_values) and object_values[index][0] == position:
            # There is already an area for this position; replace it.
            object_values[index] = (position, area)
        else:
            object_values.insert(index, (position, area))

    def add_object(self, index: int, object_id: str, name: str):
        self.objects.append((index, object_id, name))
        self.values[object_id] = []

    def remove_object(self, object_id: str):
        del self.values[object_id]
        for i, (_index, some_object_id, _name) in enumerate(self.objects):
            if object_id == some_object_id:
                del self.objects[i]
                break

    def interpolate(self, object_id: str, position: int) -> Optional[Tuple[float, float, float, float]]:
        object_values: List[Tuple[int, Tuple[float, float, float, float]]] = self.values[object_id]
        if not object_values:
            return None

        index: int = bisect_left(object_values, position, key=lambda x: x[0])
        if index == 0:
            # Return the first area.
            return object_values[0][1]
        elif index < len(object_values):
            # Return the interpolated area.
            xp = (object_values[index - 1][0], object_values[index][0])
            yps = zip(object_values[index - 1][1], object_values[index][1])
            return tuple(numpy.interp(position, xp, yp) for yp in yps)
        else:
            # Return the last area.
            return object_values[-1][1]

    def greatest_index(self) -> int:
        if self.objects:
            return max(index for index, _object_id, _name in self.objects)
        else:
            return 0


class TrackedObjectItem(GObject.GObject):
    """Data for displaying a Tracked Object in the list.

    Attributes:
        object_id (str): Identifier to be passed externally where the data
            might have to be reused.
        name (str): The name for display.
        index (int): Internal identifier for sorting the objects in the
            order they have been created.
    """

    def __init__(self, object_id: str, index: int, name: str):
        GObject.GObject.__init__(self)
        self.object_id: str = object_id
        self.index: int = index
        self.name: str = name


class TrackedObjectRow(Gtk.ListBoxRow):
    """Represents a tracked object to be selected in a list."""

    def __init__(self, object_id: str, name: str):
        Gtk.ListBoxRow.__init__(self)
        self.object_id: str = object_id
        self.name: str = name

        label = Gtk.Label(name)
        label.props.margin = SPACING
        label.props.margin_end = PADDING
        label.props.margin_start = PADDING
        label.props.halign = Gtk.Align.START
        label.show()
        self.add(label)


@Gtk.Template(filename=os.path.join(get_ui_dir(), "trackerperspective.ui"))
class ToplevelWidget(Gtk.Box, Loggable):
    """Toplevel widget of the Tracker perspective."""

    __gtype_name__ = "ToplevelWidget"

    add_object_button = Gtk.Template.Child()
    algorithm_combo_box = Gtk.Template.Child()
    aspect_frame = Gtk.Template.Child()
    drawing_area = Gtk.Template.Child()
    howto_add_infobar = Gtk.Template.Child()
    next_frame_button = Gtk.Template.Child()
    object_listbox = Gtk.Template.Child()
    object_manager_box = Gtk.Template.Child()
    pause_icon = Gtk.Template.Child()
    play_icon = Gtk.Template.Child()
    play_pause_button = Gtk.Template.Child()
    pos_adj = Gtk.Template.Child()
    prev_frame_button = Gtk.Template.Child()
    remove_object_button = Gtk.Template.Child()
    seeker = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    track_button = Gtk.Template.Child()
    viewer_buttons = Gtk.Template.Child()
    viewer_overlay = Gtk.Template.Child()

    def __init__(self, app, asset: GES.Asset):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self.asset: GES.Asset = asset
        self.object_manager: ObjectManager = ObjectManager(self.asset)

        info = asset.get_info()
        video_streams = info.get_video_streams()
        stream = video_streams[0]
        self.source_width = stream.get_natural_width()
        self.source_height = stream.get_natural_height()
        self.videorate = self.app.project_manager.current_project.videorate

        self.pipeline = AssetPipeline(self.asset.props.id)
        self.pipeline.connect("error", self._pipeline_error_cb)
        self.pipeline.activate_position_listener(50)
        self.pipeline.connect("position", self._pipeline_position_cb)
        self.pipeline.connect("eos", self._pipeline_eos_cb)
        self.pipeline.connect("state-change", self._pipeline_state_change_cb)
        self.step = (self.videorate.denom / self.videorate.num) * Gst.SECOND

        # The area selected by the user with drag&drop.
        # The coordinates are in screen pixels.
        self.x1: Optional[float] = None  # pylint: disable=invalid-name
        self.y1: Optional[float] = None  # pylint: disable=invalid-name
        self.x2: Optional[float] = None  # pylint: disable=invalid-name
        self.y2: Optional[float] = None  # pylint: disable=invalid-name
        # The size of the viewer when the user selected the area.
        self.drawing_area_width: Optional[int] = None
        self.drawing_area_height: Optional[int] = None

        self.current_object: Optional[str] = None

        self.sink_widget = None
        self.tracker_pipeline: Optional[SimplePipeline] = None
        self.tracker_sink_widget = None
        # Data gathered during the current tracking operation.
        self.roi_data: Optional[Dict[int, Tuple[float, float, float, float]]] = None
        # Position where the last tracking has been started.
        self.start_pos: Optional[int] = None

        # Setup ListBox with the tracked objects
        self.tracked_objects_store = Gio.ListStore()
        for index, object_id, name in self.object_manager.objects:
            self.tracked_objects_store.append(TrackedObjectItem(object_id, index, name))
        self.object_listbox.bind_model(self.tracked_objects_store, self.create_tracked_object_row_func)

        fix_infobar(self.howto_add_infobar)

        # Setup Viewer
        _, self.sink_widget = self.pipeline.create_sink()
        self.aspect_frame.set(
            xalign=0.5, yalign=0.5, ratio=self.source_width / self.source_height, obey_child=False)
        self.viewer_overlay.add(self.sink_widget)
        self.viewer_overlay.add_overlay(self.drawing_area)
        self.viewer_overlay.show_all()

        # Setup Seeker
        self.seeker.props.adjustment.set_upper(self.asset.props.duration)
        self.seeker.props.adjustment.set_step_increment(self.step)

        # Setup algorithm ComboBox
        cell = Gtk.CellRendererText()
        self.algorithm_combo_box.set_model(self.__get_tracking_algorithms())
        self.algorithm_combo_box.pack_start(cell, False)
        self.algorithm_combo_box.add_attribute(cell, "text", 0)

        self._setup(None)

    @Gtk.Template.Callback()
    def _viewer_overlay_realize_cb(self, widget):
        self.pipeline.pause()

    # Playback methods

    def _pipeline_error_cb(self, pipeline, message, detail):
        self.warning("pipeline error: %s (%s)", message, detail)
        self.pipeline.set_simple_state(Gst.State.NULL)

    def __update_adjustment(self, position: int):
        """Updates the UI without triggering callbacks."""
        self.pos_adj.handler_block_by_func(self._adjustment_value_changed_cb)
        try:
            self.pos_adj.set_value(position)
        finally:
            self.pos_adj.handler_unblock_by_func(self._adjustment_value_changed_cb)

    def _pipeline_position_cb(self, pipline, position):
        self.__update_adjustment(position)

    def _pipeline_eos_cb(self, pipeline):
        pipeline.simple_seek(0)

    def _pipeline_state_change_cb(self, pipeline, state, prev_state):
        self.log("Pipeline state %s -> %s", prev_state, state)
        if pipeline.playing():
            icon = self.pause_icon
        else:
            icon = self.play_icon

        self.play_pause_button.set_image(icon)
        self.track_button.props.sensitive = False

    @Gtk.Template.Callback()
    def _play_pause_button_clicked_cb(self, button):
        self.pipeline.toggle_playback()
        self.__reset_selected_area()

    @Gtk.Template.Callback()
    def _next_frame_button_clicked_cb(self, button):
        self._seek(1)

    @Gtk.Template.Callback()
    def _prev_frame_button_clicked_cb(self, button):
        self._seek(-1)

    def _seek(self, direction: int):
        state = self.pipeline.get_simple_state()
        if state == Gst.State.PLAYING:
            self.pipeline.pause()
        elif state == Gst.State.PAUSED:
            self.pipeline.seek_relative(self.step * direction)

    @Gtk.Template.Callback()
    def _adjustment_value_changed_cb(self, adjustment):
        """Handle a seek performed by the user interacting with the UI."""
        if self.pipeline.get_simple_state() != Gst.State.PAUSED:
            self.pipeline.pause()

        # Block the pipeline's "position" signal to prevent a callback loop.
        self.pipeline.handler_block_by_func(self._pipeline_position_cb)
        try:
            self.pipeline.simple_seek(adjustment.props.value)
        finally:
            self.pipeline.handler_unblock_by_func(self._pipeline_position_cb)

    # Bounding box callbacks

    @Gtk.Template.Callback()
    def _drawing_area_button_event_cb(self, widget, event):
        res, button = event.get_button()
        if not res or button != 1:
            return

        if self.pipeline.get_simple_state() != Gst.State.PAUSED:
            return

        if event.get_event_type() == Gdk.EventType.BUTTON_PRESS:
            self.x1 = event.x
            self.y1 = event.y
            self.drawing_area_width = self.drawing_area.get_allocated_width
            self.drawing_area_height = self.drawing_area.get_allocated_height
        elif event.get_event_type() == Gdk.EventType.BUTTON_RELEASE:
            self.x2 = event.x
            self.y2 = event.y

            # Convert the viewer coordinates to video coordinates.
            factor: float = 1 / self.video_to_viewer_factor()
            x = min(self.x1, self.x2) * factor
            y = min(self.y1, self.y2) * factor
            w = abs(self.x2 - self.x1) * factor
            h = abs(self.y2 - self.y1) * factor
            if w and h:
                # Apply the selected area to the object.
                if not self.current_object:
                    self._create_empty_object()
                position = self.pipeline.get_position()
                self.object_manager.update_object_position(
                    self.current_object, position, (x, y, w, h))

                # Allow tracking.
                self.track_button.props.sensitive = True

            self.__reset_selected_area()

    def _create_empty_object(self):
        """Generates a new object and adds it to the object_manager."""
        index = 1 + self.object_manager.greatest_index()
        object_id = uuid.uuid4().hex
        name = _("Object {}").format(index)

        self.current_object = object_id
        self.object_manager.add_object(index, object_id, name)

        self.tracked_objects_store.append(TrackedObjectItem(object_id, index, name))
        last_row_index = self.tracked_objects_store.get_n_items() - 1
        last_row = self.object_listbox.get_row_at_index(last_row_index)
        self.object_listbox.select_row(last_row)

    def __reset_selected_area(self):
        self.x1, self.y1 = None, None
        self.x2, self.y2 = None, None
        self.drawing_area_width, self.drawing_area_height = None, None

    @Gtk.Template.Callback()
    def _drawing_area_enter_notify_event_cb(self, widget, event):
        self.app.gui.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.CROSSHAIR))

    @Gtk.Template.Callback()
    def _drawing_area_leave_notify_event_cb(self, widget, event):
        self.app.gui.get_window().set_cursor(NORMAL_CURSOR)

    @Gtk.Template.Callback()
    def _drawing_area_motion_notify_event_cb(self, widget, event):
        if self.x1 is not None:
            self.x2 = event.x
            self.y2 = event.y
            self.drawing_area.queue_draw()

    @Gtk.Template.Callback()
    def _drawing_area_draw_cb(self, drawing_area, cr):
        """Handler responsible for drawing the selection rectangle."""
        if self.x2 is not None:
            # Draw the area being delimited by the user on the viewer.
            x, y = self.x1, self.y1
            w, h = self.x2 - self.x1, self.y2 - self.y1
        elif self.current_object:
            # Draw the area tracked previously for the current position.
            position = self.pipeline.get_position(fails=False)
            video_coords = self.object_manager.interpolate(self.current_object, position)
            if not video_coords:
                return

            x, y, w, h = video_coords

            # Translate from video coordinates to viewer coordinates.
            factor: float = self.video_to_viewer_factor()
            cr.scale(factor, factor)
        else:
            # Nothing to draw.
            return

        cr.set_operator(cairo.OPERATOR_OVER)

        cr.set_source_rgba(1, 1, 0.6, 0.8)  # Yellow
        cr.rectangle(x, y, w, h)
        cr.stroke()

        cr.set_source_rgba(0.6, 0.6, 0.6, 0.5)  # Light gray
        cr.rectangle(x, y, w, h)
        cr.fill()

    def video_to_viewer_factor(self) -> float:
        if self.source_width > self.source_height:
            viewer_width = self.drawing_area.get_allocated_width()
            return viewer_width / self.source_width
        else:
            viewer_height = self.drawing_area.get_allocated_height()
            return viewer_height / self.source_height

    @Gtk.Template.Callback()
    def _add_object_button_clicked_cb(self, button):
        # If no object is selected then the user will be able to
        # delimit an area to create an object.
        self.object_listbox.unselect_all()

    @Gtk.Template.Callback()
    def _remove_object_button_clicked_cb(self, button):
        row = self.object_listbox.get_selected_row()
        index = row.get_index()
        tracked_object: TrackedObjectItem = self.tracked_objects_store.get_item(index)
        self.tracked_objects_store.remove(index)

        self.remove_object_button.props.sensitive = False
        self.current_object = None

        self.object_manager.remove_object(tracked_object.object_id)
        self.seeker.clear_marks()

    @Gtk.Template.Callback()
    def _stop_track_button_clicked_cb(self, button):
        self.tracker_pipeline.pause()
        self.__stop_tracker()

    def _setup(self, object_id: Optional[str]):
        """Sets up the UI for creating or updating a tracked object."""
        self.seeker.clear_marks()

        self._setup_tracking_ui(started=False)

        self.__reset_selected_area()

        self.current_object = object_id
        has_object = bool(object_id)
        if has_object:
            timed_data = self.object_manager.values[object_id]
            if timed_data:
                seek_pos, _area = timed_data[0]
                self.seeker.add_mark(seek_pos, Gtk.PositionType.BOTTOM, None)
                self.pipeline.simple_seek(seek_pos)

        self.add_object_button.props.sensitive = has_object
        self.remove_object_button.props.sensitive = has_object
        # Hide the infobar by making it transparent. This way the left column
        # of widgets has a stable width, as the infobar is the widest widget.
        self.howto_add_infobar.props.opacity = 1 if not has_object else 0

    # Object list box methods

    def create_tracked_object_row_func(self, item: TrackedObjectItem) -> TrackedObjectRow:
        return TrackedObjectRow(item.object_id, item.name)

    @Gtk.Template.Callback()
    def _listbox_selected_rows_changed_cb(self, listbox: Gtk.ListBox):
        row: TrackedObjectRow = listbox.get_selected_row()
        self._setup(row.object_id if row else None)

    # Tracker methods

    @Gtk.Template.Callback()
    def _track_button_clicked_cb(self, button):
        self._setup_tracking_ui(started=True)

        # Build the object tracking pipeline.
        algorithm = self.algorithm_combo_box.get_active()
        self.start_pos = self.pipeline.get_position()
        x, y, w, h = self.object_manager.interpolate(self.current_object, self.start_pos)
        self.roi_data = {}
        _pipeline = Gst.parse_launch(
            "uridecodebin uri={} ! videoconvert ! \
            cvtracker object-initial-x={} object-initial-y={} object-initial-width={} \
            object-initial-height={} algorithm={} draw-rect=true ! tee name=t ! \
            queue ! videoconvert ! gtksink name=gtksink t. \
            ! fakesink name=sink signal-handoffs=TRUE"
            .format(self.asset.props.id, int(x), int(y), int(w), int(h), algorithm))

        self.seeker.add_mark(self.start_pos, Gtk.PositionType.BOTTOM, None)

        # Connect to fakesink to get the tracking data.
        fakesink = _pipeline.get_by_name("sink")
        fakesink.connect("handoff", self.__tracker_handoff_cb, self.roi_data)

        # Set up a widget to show the video as the object is being tracked.
        video_sink = _pipeline.get_by_name("gtksink")
        self.tracker_sink_widget = video_sink.props.widget
        self.viewer_overlay.add_overlay(self.tracker_sink_widget)

        # Create a high-level pipeline to get position updates.
        self.tracker_pipeline = SimplePipeline(_pipeline)
        self.tracker_pipeline.activate_position_listener(50)
        self.tracker_pipeline.connect("position", self.__tracker_position_cb)

        # Connect to the bus of the pipeline to find out when the stream ends.
        bus = _pipeline.get_bus()
        bus.connect("message", self.__tracker_bus_message_cb)
        bus.add_signal_watch()

        # Start the tracking pipeline.
        self.tracker_pipeline.simple_seek(self.start_pos)
        self.tracker_pipeline.play()

    def _setup_tracking_ui(self, started: bool):
        """Sets up the widgets depending on the specified tracking status."""
        self.drawing_area.props.visible = not started
        self.object_manager_box.props.sensitive = not started
        self.algorithm_combo_box.props.sensitive = not started
        self.viewer_buttons.props.sensitive = not started

        self.track_button.props.visible = not started
        self.track_button.props.sensitive = False
        self.stop_button.props.visible = started

    def __get_tracking_algorithms(self) -> Gtk.ListStore:
        listmodel = Gtk.ListStore(str)
        element = Gst.ElementFactory.make("cvtracker", "tracker")
        properties = element.list_properties()
        for prop in properties:
            if prop.name == "algorithm":
                for unused_key, algorithm in prop.enum_class.__enum_values__.items():
                    listmodel.append([algorithm.value_nick])
                break

        return listmodel

    def __stop_tracker(self):
        position = self.tracker_pipeline.get_position(fails=False)
        self.pipeline.simple_seek(position)

        self.log("Waiting for the tracker_pipeline to stop")
        self.tracker_pipeline.connect("state-change", self.__pipeline_state_change_cb)
        self.tracker_pipeline.stop()

        self.object_manager.update_object(self.current_object, self.start_pos, self.roi_data)
        self.start_pos = None
        self.roi_data = None

    def __pipeline_state_change_cb(self, pipeline, state, prev_state):
        if state != Gst.State.READY:
            return

        self.log("Tracker_pipeline stopped")
        self.tracker_pipeline.disconnect_by_func(self.__pipeline_state_change_cb)
        self.tracker_pipeline.release()
        self.tracker_pipeline = None

        self.viewer_overlay.remove(self.tracker_sink_widget)

        self._setup_tracking_ui(started=False)

    def __tracker_position_cb(self, pipeline, position):
        if position >= self.start_pos:
            if not self.tracker_sink_widget.props.visible:
                self.tracker_sink_widget.show()

            self.__update_adjustment(position)

    def __tracker_bus_message_cb(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self.__stop_tracker()

    def __tracker_handoff_cb(self, element, buffer, pad, roi_data: Dict[int, Tuple[float, float, float, float]]):
        video_roi = GstVideo.buffer_get_video_region_of_interest_meta_id(buffer, 0)
        if video_roi:
            roi_data[buffer.pts] = (video_roi.x, video_roi.y, video_roi.w, video_roi.h)
        else:
            self.log("lost tracker at: %s", buffer.pts / Gst.SECOND)


class TrackerPerspective(Perspective):
    """Pitivi's Tracker Perspective.

    Allows the user to track multiple objects
    and manually correct the obtained track data.

    Attributes:
        app (Pitivi): The app.
        asset (GES.UriClipAsset): Asset to be used.
    """

    def __init__(self, app, asset):
        super().__init__()
        self.app = app
        self.asset = asset

    def __create_headerbar(self):
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(False)

        back_button = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        back_button.set_always_show_image(True)
        back_button.set_tooltip_text(_("Go back"))
        back_button.connect("clicked", self.__back_button_clicked_cb)
        back_button.set_margin_end(4 * PADDING)
        headerbar.pack_start(back_button)
        headerbar.props.title = os.path.basename(self.asset.props.id)
        headerbar.show_all()

        return headerbar

    def setup_ui(self):
        self.toplevel_widget = ToplevelWidget(self.app, self.asset)
        self.headerbar = self.__create_headerbar()

    def __back_button_clicked_cb(self, button):
        self.toplevel_widget.object_manager.save()
        self.toplevel_widget.pipeline.release()
        self.app.gui.show_perspective(self.app.gui.editor)

    def refresh(self):
        """Refreshes the perspective."""
        self.toplevel_widget.play_pause_button.grab_focus()


class CoverObjectPopover(Gtk.Popover, Loggable):
    """Popover for selecting an object to cover."""

    # The representation of the effect providing the cover.
    _EFFECT_PIPELINE = "video videotestsrc pattern=solid-color foreground-color=0xff000000 ! framepositioner name=positioner ! gescompositor"

    def __init__(self, app, clip: GES.Clip):
        Gtk.Popover.__init__(self)
        Loggable.__init__(self)

        self.app = app

        self.clip: GES.Clip = clip
        self.object_manager: Optional[ObjectManager] = None

        self.listbox = Gtk.ListBox()
        self.listbox.connect("row-activated", self.__row_activated_cb)

        self.scroll_window = Gtk.ScrolledWindow()
        self.scroll_window.add(self.listbox)
        self.scroll_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll_window.props.max_content_height = 350
        self.scroll_window.props.propagate_natural_height = True

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=PADDING)
        vbox.pack_start(self.scroll_window, True, True, 0)
        vbox.show_all()

        self.add(vbox)

    def update_object_list(self):
        """Updates the list of not yet covered objects."""
        self.object_manager = ObjectManager(self.clip.asset)

        for row in self.listbox.get_children():
            self.listbox.remove(row)

        # Check which tracked objects have already been covered.
        covered_objects = []
        for effect in self.clip.get_top_effects():
            tracked_object_id = effect.get_string(EFFECT_TRACKED_OBJECT_ID_META)
            if tracked_object_id:
                covered_objects.append(tracked_object_id)

        # Allow selecting the not-yet-covered objects.
        for _index, object_id, name in self.object_manager.objects:
            if object_id not in covered_objects:
                self.listbox.add(TrackedObjectRow(object_id, name))

        # Allow tracking new objects.
        button_row = Gtk.ListBoxRow(selectable=False)
        track_objects_button = Gtk.Button(_("Track objects"))
        track_objects_button.connect("clicked", self.__track_objects_button_clicked_cb)
        button_row.add(track_objects_button)
        self.listbox.add(button_row)

        self.listbox.show_all()

    def __row_activated_cb(self, listbox: Gtk.ListBox, row: TrackedObjectRow):
        self._create_effect(row.object_id, row.name)

        self.popdown()

    def __effect_control_binding_added_cb(self, track_element, binding, object_id):
        control_source = binding.props.control_source
        timed_data = self.object_manager.values[object_id]
        for timestamp, (x, y, w, h) in timed_data:
            if binding.name == "posx":
                value = x
            elif binding.name == "posy":
                value = y
            elif binding.name == "width":
                value = w
            elif binding.name == "height":
                value = h
            else:
                break

            control_source.set(timestamp, value)

    def __clip_child_added_cb(self, clip, track_element, object_id):
        if not isinstance(track_element, GES.Effect):
            return

        clip.disconnect_by_func(self.__clip_child_added_cb)

        track_element.connect("control-binding-added",
                              self.__effect_control_binding_added_cb,
                              object_id)
        try:
            for prop in ("posx", "posy", "width", "height"):
                control_source = GstController.InterpolationControlSource()
                control_source.props.mode = GstController.InterpolationMode.NONE
                track_element.set_control_source(control_source, prop, "direct-absolute")
        finally:
            track_element.disconnect_by_func(self.__effect_control_binding_added_cb)

    def _create_effect(self, object_id: str, name: str):
        effect = GES.Effect.new(self._EFFECT_PIPELINE)
        effect.register_meta_string(GES.MetaFlag.READABLE, EFFECT_TRACKED_OBJECT_ID_META, object_id)
        effect.register_meta_string(GES.MetaFlag.READABLE, EFFECT_TRACKED_OBJECT_NAME_META, name)

        self.log("Waiting for effect to be added to the clip")
        self.clip.connect("child-added", self.__clip_child_added_cb, object_id)
        self.clip.add_top_effect(effect, 0)

        self.app.project_manager.current_project.pipeline.commit_timeline()

    def __track_objects_button_clicked_cb(self, button):
        tracker = TrackerPerspective(self.app, self.clip.asset)
        self.app.project_manager.current_project.pipeline.pause()
        tracker.setup_ui()
        self.app.gui.show_perspective(tracker)
