# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, Mathieu Duponchelle <mduponchelle1@gmail.com>
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
from typing import Any
from typing import List
from typing import Optional

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.action_search_bar import ActionSearchBar
from pitivi.autoaligner import AutoAligner
from pitivi.configure import get_ui_dir
from pitivi.configure import in_devel
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.effects import EffectsPopover
from pitivi.settings import GlobalSettings
from pitivi.timeline.elements import Clip
from pitivi.timeline.elements import TransitionClip
from pitivi.timeline.elements import TrimHandle
from pitivi.timeline.layer import FullLayer
from pitivi.timeline.layer import LayerControls
from pitivi.timeline.layer import MiniLayer
from pitivi.timeline.layer import SpacedSeparator
from pitivi.timeline.markers import MarkersBox
from pitivi.timeline.previewers import Previewer
from pitivi.timeline.ruler import TimelineScaleRuler
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable
from pitivi.utils.markers import GES_MARKERS_SNAPPABLE
from pitivi.utils.misc import asset_get_duration
from pitivi.utils.pipeline import PipelineError
from pitivi.utils.timeline import EditingContext
from pitivi.utils.timeline import SELECT
from pitivi.utils.timeline import Selection
from pitivi.utils.timeline import TimelineError
from pitivi.utils.timeline import UNSELECT
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import EFFECT_TARGET_ENTRY
from pitivi.utils.ui import LAYER_HEIGHT
from pitivi.utils.ui import MINI_LAYER_HEIGHT
from pitivi.utils.ui import PLAYHEAD_COLOR
from pitivi.utils.ui import PLAYHEAD_WIDTH
from pitivi.utils.ui import SEPARATOR_HEIGHT
from pitivi.utils.ui import set_cairo_color
from pitivi.utils.ui import set_state_flags_recurse
from pitivi.utils.ui import SNAPBAR_COLOR
from pitivi.utils.ui import SNAPBAR_WIDTH
from pitivi.utils.ui import SPACING
from pitivi.utils.ui import TOUCH_INPUT_SOURCES
from pitivi.utils.ui import URI_TARGET_ENTRY
from pitivi.utils.widgets import ZoomBox


# Creates new layer if a clip is held at layers separator after this time interval
SEPARATOR_ACCEPTING_DROP_INTERVAL_MS = 1000


GlobalSettings.add_config_option('markersSnappableByDefault',
                                 section="user-interface",
                                 key="markers-snappable-default",
                                 default=False,
                                 notify=False)

if GES_MARKERS_SNAPPABLE:
    PreferencesDialog.add_toggle_preference('markersSnappableByDefault',
                                            section="timeline",
                                            label=_("Markers magnetic by default"),
                                            description=_(
                                                "Whether markers created on new clips will be snapping targets by default."))

GlobalSettings.add_config_option('edgeSnapDeadband',
                                 section="user-interface",
                                 key="edge-snap-deadband",
                                 default=5,
                                 notify=True)

PreferencesDialog.add_numeric_preference('edgeSnapDeadband',
                                         section="timeline",
                                         label=_("Snap distance"),
                                         description=_("Threshold (in pixels) at which two clips will snap together "
                                                       "when dragging or trimming."),
                                         lower=0)

GlobalSettings.add_config_option('imageClipLength',
                                 section="user-interface",
                                 key="image-clip-length",
                                 default=1000,
                                 notify=True)

PreferencesDialog.add_numeric_preference('imageClipLength',
                                         section="timeline",
                                         label=_("Image clip duration"),
                                         description=_(
                                             "Default clip length (in milliseconds) of images when inserting on the timeline."),
                                         lower=1)

GlobalSettings.add_config_option('leftClickAlsoSeeks',
                                 section="user-interface",
                                 key="left-click-to-select",
                                 default=False,
                                 notify=True)

PreferencesDialog.add_toggle_preference('leftClickAlsoSeeks',
                                        section="timeline",
                                        label=_("Left click also seeks"),
                                        description=_(
                                            "Whether left-clicking also seeks besides selecting and editing clips."))

GlobalSettings.add_config_option("timelineAutoRipple",
                                 section="user-interface",
                                 key="timeline-autoripple",
                                 default=False)


class Marquee(Gtk.Box, Loggable):
    """Widget representing a selection area inside the timeline.

    Args:
        timeline (Timeline): The timeline indirectly containing the marquee.
        layout (LayersLayout): Layout containing the layers on which the marquee would be drawn.
    """

    __gtype_name__ = "PitiviMarquee"

    def __init__(self, timeline, layout):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)

        self._timeline = timeline
        self.layout = layout
        self.start_x, self.start_y = 0, 0
        self.end_x, self.end_y = self.start_x, self.start_y

        self.props.no_show_all = True
        self.hide()

        self.get_style_context().add_class("Marquee")

    def hide(self):
        """Hides and resets the widget."""
        self.start_x, self.start_y = 0, 0
        self.props.height_request = -1
        self.props.width_request = -1
        self.set_visible(False)

    def set_start_position(self, event):
        """Sets the first corner of the marquee.

        Args:
            event (Gdk.EventButton): The button pressed event which might
                start a select operation.
        """
        event_widget = Gtk.get_event_widget(event)
        self.start_x, self.start_y = event_widget.translate_coordinates(
            self.layout.layers_vbox, event.x, event.y)
        self.end_x, self.end_y = self.start_x, self.start_y
        self.get_parent().move(self, self.start_x, self.start_y)

        self.props.width_request = 0
        self.props.height_request = 0
        self.set_visible(True)

    def move(self, event):
        """Sets the second corner of the marquee.

        Args:
            event (Gdk.EventMotion): The motion event which contains
                the coordinates of the second corner.
        """
        event_widget = Gtk.get_event_widget(event)
        self.end_x, self.end_y = event_widget.translate_coordinates(
            self.layout.layers_vbox, event.x, event.y)

        x = min(self.start_x, self.end_x)
        y = min(self.start_y, self.end_y)
        self.get_parent().move(self, x, y)

        self.props.width_request = abs(self.start_x - self.end_x)
        self.props.height_request = abs(self.start_y - self.end_y)

    def find_clips(self, mini=False):
        """Finds the clips which intersect the marquee.

        Args:
            mini (bool): Layers layout or Mini Layers layout.

        Returns:
            List[GES.Clip]: The clips under the marquee.
        """
        if self.props.width_request == 0:
            return []

        start_layer = self._timeline.get_layer_at(self.start_y, mini=mini)[0]
        end_layer = self._timeline.get_layer_at(self.end_y, mini=mini)[0]

        ratio = self._timeline.calc_best_zoom_ratio() if mini else None
        start_pos = max(0, self._timeline.pixel_to_ns(self.start_x, zoomratio=ratio))
        end_pos = max(0, self._timeline.pixel_to_ns(self.end_x, zoomratio=ratio))

        return self._timeline.get_clips_in_between(start_layer, end_layer,
                                                   start_pos, end_pos)


class LayersLayout(Gtk.Layout, Loggable):
    """Layout for displaying scrollable layers, the playhead, snap indicator.

    The layers are actual widgets in a vertical Gtk.Box.
    The playhead and the snap indicator are drawn on top in do_draw().

    Args:
        timeline (Timeline): The timeline indirectly containing the layout.

    Attributes:
        snap_position (int): The time where the snapbar should appear.
        playhead_position (int): The time where the playhead should appear.
    """

    def __init__(self, timeline):
        Gtk.Layout.__init__(self)
        Loggable.__init__(self)

        self._timeline = timeline

        self.snap_position = 0
        self.playhead_position = 0

        self.layers_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.layers_vbox.get_style_context().add_class("LayersBox")
        self.put(self.layers_vbox, 0, 0)

        self.marquee = Marquee(timeline, self)
        self.put(self.marquee, 0, 0)

        self.layers_vbox.connect("size-allocate", self.__size_allocate_cb)

    def do_draw(self, cr):
        """Draws the children and indicators."""
        Gtk.Layout.do_draw(self, cr)

        self._draw_playhead(cr)
        self._draw_snap_indicator(cr)

    def update_width(self, width):
        """Updates the width of the area and the width of the layers_vbox."""
        view_width = self.get_allocated_width()
        space_at_the_end = view_width * 2 / 3
        width = width + space_at_the_end
        width = max(view_width, width)

        self.log("Updating the width_request of the layers_vbox: %s", width)
        # This triggers a renegotiation of the size, meaning
        # layers_vbox's "size-allocate" will be emitted, see __size_allocate_cb.
        self.layers_vbox.props.width_request = width

    def _draw_vertical_bar(self, cr, xpos, width, color):
        if xpos < 0:
            return

        # Add 0.5 so the line is sharp, xpos represents the center of the line.
        xpos += 0.5
        height = self.get_allocated_height()
        cr.set_line_width(width)
        cr.move_to(xpos, 0)
        set_cairo_color(cr, color)
        cr.line_to(xpos, height)
        cr.stroke()

    def __size_allocate_cb(self, unused_widget, allocation):
        """Sets the size of the scrollable area to fit the layers_vbox."""
        self.log("The size of the layers_vbox changed: %sx%s", allocation.width, allocation.height)
        self.props.width = allocation.width
        # The additional space is for the 'Add layer' button.
        self.props.height = allocation.height + LAYER_HEIGHT / 2


class FullLayersLayout(LayersLayout, Zoomable):

    def __init__(self, timeline):
        Zoomable.__init__(self)
        LayersLayout.__init__(self, timeline)

    def _draw_playhead(self, cr):
        """Draws the playhead line."""
        offset = self.get_hadjustment().get_value()
        position = max(0, self.playhead_position)

        x = self.ns_to_pixel(position) - offset
        self._draw_vertical_bar(cr, x, PLAYHEAD_WIDTH, PLAYHEAD_COLOR)

    def _draw_snap_indicator(self, cr):
        """Draws a snapping indicator line."""
        offset = self.get_hadjustment().get_value()
        x = self.ns_to_pixel(self.snap_position) - offset
        if x <= 0:
            return

        self._draw_vertical_bar(cr, x, SNAPBAR_WIDTH, SNAPBAR_COLOR)

    def update_width(self):
        ges_timeline = self._timeline.ges_timeline
        duration = 0 if not ges_timeline else ges_timeline.props.duration
        width = self.ns_to_pixel(duration)

        LayersLayout.update_width(self, width)

    def zoom_changed(self):
        # The width of the area/workspace changes when the zoom level changes.
        self.update_width()
        # Required so the playhead is redrawn.
        self.queue_draw()


class MiniLayersLayout(LayersLayout):

    def __init__(self, timeline):
        LayersLayout.__init__(self, timeline)

    def _draw_playhead(self, cr):
        """Draws the playhead line."""
        offset = self.get_hadjustment().get_value()
        position = max(0, self.playhead_position)

        ratio = self._timeline.calc_best_zoom_ratio()
        x = Zoomable.ns_to_pixel(position, zoomratio=ratio) - offset
        self._draw_vertical_bar(cr, x, PLAYHEAD_WIDTH, PLAYHEAD_COLOR)

    def _draw_snap_indicator(self, cr):
        """Draws a snapping indicator line."""
        offset = self.get_hadjustment().get_value()
        ratio = self._timeline.calc_best_zoom_ratio()
        x = Zoomable.ns_to_pixel(self.snap_position, zoomratio=ratio) - offset
        if x <= 0:
            return

        self._draw_vertical_bar(cr, x, SNAPBAR_WIDTH, SNAPBAR_COLOR)

    def update_width(self):
        ges_timeline = self._timeline.ges_timeline
        duration = 0 if not ges_timeline else ges_timeline.props.duration
        ratio = self._timeline.calc_best_zoom_ratio()
        width = Zoomable.ns_to_pixel(duration, zoomratio=ratio)

        LayersLayout.update_width(self, width)


class Timeline(Gtk.EventBox, Zoomable, Loggable):
    """Container for the layers controls and representation.

    Attributes:
        _project (Project): The project.
    """

    __gtype_name__ = "PitiviTimeline"

    def __init__(self, app, size_group, editor_state):
        Gtk.EventBox.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.app: Any = app
        self._project = None
        self.ges_timeline = None
        self.editor_state = editor_state

        self.props.can_focus = False

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(hbox)

        self.layout = FullLayersLayout(self)
        self.layout.props.can_focus = True
        self.layout.props.can_default = True
        self.hadj = self.layout.get_hadjustment()
        self.vadj = self.layout.get_vadjustment()
        hbox.pack_end(self.layout, True, True, 0)

        self.mini_layout = MiniLayersLayout(self)

        self.mini_layout_container = Gtk.EventBox.new()
        self.mini_layout_container.add(self.mini_layout)
        self.mini_layout_container.add_events(Gdk.EventType.BUTTON_PRESS | Gdk.EventType.BUTTON_RELEASE)
        self.mini_layout_container.props.no_show_all = True
        self.mini_layout_container.props.height_request = MINI_LAYER_HEIGHT
        self.mini_layout_container.hide()

        self._layers_controls_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._layers_controls_vbox.props.hexpand = False
        self._layers_controls_vbox.props.valign = Gtk.Align.START
        size_group.add_widget(self._layers_controls_vbox)

        # Stuff the layers controls in a ScrolledWindow so they can be scrolled.
        # Use self.layout's hadj to scroll the controls in sync with the layers.
        scrolled_window = Gtk.ScrolledWindow(vadjustment=self.vadj)
        scrolled_window.props.propagate_natural_width = True
        scrolled_window.props.vscrollbar_policy = Gtk.PolicyType.EXTERNAL
        scrolled_window.add(self._layers_controls_vbox)
        hbox.pack_start(scrolled_window, False, False, 0)

        self.add_layer_button = Gtk.Button.new_with_label(_("Add layer"))
        self.add_layer_button.props.margin = SPACING
        self.add_layer_button.set_halign(Gtk.Align.CENTER)
        self.add_layer_button.show()
        self.add_layer_button.set_action_name("timeline.add-layer")
        self._layers_controls_vbox.pack_end(self.add_layer_button, False, False, 0)

        self.get_style_context().add_class("Timeline")
        self.props.expand = True
        self.get_accessible().set_name("timeline canvas")

        # A window is needed to receive BUTTON_* events. This is the reason why
        # Timeline is a Gtk.EventBox subclass and not directly a Gtk.Box,
        # see `hbox` above.
        assert self.get_has_window()
        # A lot of operations go through the handlers of these events.
        self.add_events(Gdk.EventType.BUTTON_PRESS | Gdk.EventType.BUTTON_RELEASE)

        # Whether the entire timeline content is in view and
        # it should be kept that way if it makes sense.
        self.zoomed_fitted = True

        # A list of (controls separator, layers separator) tuples.
        self._separators = []
        # Whether the user is dragging a layer.
        self.__moving_layer = None

        self._separator_accepting_drop = False
        self._separator_accepting_drop_id = 0
        self.__last_position = 0
        self.scrubbing = False
        self._scrolling = False
        # The parameters for the delayed scroll to be performed after
        # the layers box is allocated a size.
        self.delayed_scroll = {}
        self.__next_seek_position = None

        # Whether the playhead is in Locked mode
        # If this is true, Playhead will center itself.
        self.playhead_locked = False

        # Clip selection.
        self.selection = Selection()
        # The last layer where the user clicked.
        self.last_clicked_layer = None
        # Position where the user last clicked.
        self.last_click_pos = 0

        # Clip editing.
        # Which clip widget is being edited.
        self.dragging_element = None
        # The GES.Group in case there are one or more clips being dragged.
        self.dragging_group = None
        # Which handle of the dragging_element has been clicked, if any.
        # If set, it means we are in a trim operation.
        self.__clicked_handle = None
        # The object keeping track of the current operation being performed.
        self.editing_context = None
        # Whether dragging_element really got dragged.
        self.__got_dragged = False
        # The x of the event which starts the drag operation.
        self.__drag_start_x = 0
        # The current layer on which the operation is performed.
        self._on_layer = None
        # The separators immediately above or below _on_layer
        # on which the operation will be performed.
        # Implies a new layer will be created.
        self.__on_separators = []

        # Drag & dropping assets from outside.

        # Set to True when a clip has been dragged because the first
        # button-release-event on the clip should be ignored.
        self.got_dragged = False
        # Whether the drop data has been received. See self.drop_data below.
        self.drop_data_ready = False
        # What's being dropped, for example asset URIs.
        self.drop_data = None
        # Whether clips have been created in the current drag & drop.
        self.dropping_clips = False
        # The list of (Layer, Clip) tuples dragged into the timeline.
        self.__last_clips_on_leave = None

        # To be able to receive effects dragged on clips.
        self.drag_dest_set(0, [EFFECT_TARGET_ENTRY], Gdk.DragAction.COPY)
        self.mini_layout_container.drag_dest_set(0, [EFFECT_TARGET_ENTRY], Gdk.DragAction.COPY)
        # To be able to receive assets dragged from the media library.
        self.drag_dest_add_uri_targets()
        self.mini_layout_container.drag_dest_add_uri_targets()

        self.connect("drag-motion", self._drag_motion_cb)
        self.connect("drag-leave", self._drag_leave_cb)
        self.connect("drag-drop", self._drag_drop_cb)
        self.connect("drag-data-received", self._drag_data_received_cb)

        mini = True
        self.mini_layout_container.connect("drag-motion", self._drag_motion_cb, mini)
        self.mini_layout_container.connect("drag-leave", self._drag_leave_cb)
        self.mini_layout_container.connect("drag-drop", self._drag_drop_cb)
        self.mini_layout_container.connect("drag-data-received", self._drag_data_received_cb)

        self.app.settings.connect("edgeSnapDeadbandChanged",
                                  self.__snap_distance_changed_cb)

        self.layout.layers_vbox.connect_after("size-allocate", self.__size_allocate_cb)

        self.hadj.connect("value-changed", self.__hadj_value_changed_cb)

    def __size_allocate_cb(self, unused_widget, unused_allocation):
        """Handles the layers vbox size allocations."""
        if self.delayed_scroll:
            self.scroll_to_playhead(**self.delayed_scroll)

    @property
    def media_types(self):
        """Gets the media types present in the layers.

        Returns:
            GES.TrackType: The type of media available in the timeline.
        """
        media_types = GES.TrackType(0)

        for ges_layer in self.ges_timeline.get_layers():
            media_types |= ges_layer.ui.media_types

            if ((media_types & GES.TrackType.AUDIO) and
                    (media_types & GES.TrackType.VIDEO)):
                break

        return media_types

    def set_project(self, project):
        """Connects to the GES.Timeline holding the project."""
        if self.ges_timeline is not None:
            self.disconnect_by_func(self._button_press_event_cb)
            self.disconnect_by_func(self._button_release_event_cb)
            self.disconnect_by_func(self._motion_notify_event_cb)

            self.mini_layout_container.disconnect_by_func(self._button_press_event_cb)
            self.mini_layout_container.disconnect_by_func(self._button_release_event_cb)
            self.mini_layout_container.disconnect_by_func(self._motion_notify_event_cb)

            self.ges_timeline.disconnect_by_func(self._duration_changed_cb)
            self.ges_timeline.disconnect_by_func(self._layer_added_cb)
            self.ges_timeline.disconnect_by_func(self._layer_removed_cb)
            self.ges_timeline.disconnect_by_func(self.__snapping_started_cb)
            self.ges_timeline.disconnect_by_func(self.__snapping_ended_cb)
            for ges_layer in self.ges_timeline.get_layers():
                self._remove_layer(ges_layer)

            self.ges_timeline.ui = None
            self.ges_timeline = None

        if self._project and self._project.pipeline:
            self._project.pipeline.disconnect_by_func(self._position_cb)

        self._project = project
        if self._project:
            self._project.pipeline.connect('position', self._position_cb)
            self.ges_timeline = self._project.ges_timeline

        if self.ges_timeline is None:
            return

        self.ges_timeline.ui = self

        for ges_layer in self.ges_timeline.get_layers():
            self._add_layer(ges_layer)
        self.__update_layers()
        self.__update_mini_timeline_height()

        self.ges_timeline.connect("notify::duration", self._duration_changed_cb)
        self.ges_timeline.connect("layer-added", self._layer_added_cb)
        self.ges_timeline.connect("layer-removed", self._layer_removed_cb)
        self.ges_timeline.connect("snapping-started", self.__snapping_started_cb)
        self.ges_timeline.connect("snapping-ended", self.__snapping_ended_cb)

        self.connect("button-press-event", self._button_press_event_cb)
        self.connect("button-release-event", self._button_release_event_cb)
        self.connect("motion-notify-event", self._motion_notify_event_cb)

        mini = True
        self.mini_layout_container.connect("button-press-event", self._button_press_event_cb, mini)
        self.mini_layout_container.connect("button-release-event", self._button_release_event_cb, mini)
        self.mini_layout_container.connect("motion-notify-event", self._motion_notify_event_cb, mini)

        self.layout.update_width()
        self.mini_layout.update_width()

    def _duration_changed_cb(self, ges_timeline, pspec):
        self.layout.update_width()
        self.mini_layout.update_width()

    def scroll_to_playhead(self, align=None, when_not_in_view=False, delayed=False):
        """Scrolls so that the playhead is in view.

        Args:
            align (Optional[Gtk.Align]): Where the playhead should be
                post-scroll.
            when_not_in_view (Optional[bool]): When True, scrolls only if
                the playhead is not in view.
            delayed (Optional[bool]): When True, the scroll will be done only
                after the layers box size allocation is updated.
        """
        self.debug("Scrolling to playhead, delayed=%s", delayed)
        if delayed:
            self.delayed_scroll = {"align": align, "when_not_in_view": when_not_in_view}
            return

        # If a scroll is forced, forget about the delayed scroll, if any.
        self.delayed_scroll = {}

        layout_width = self.layout.get_allocation().width
        if when_not_in_view:
            x = self.ns_to_pixel(self.__last_position) - self.hadj.get_value()
            if 0 <= x <= layout_width:
                return

        # Deciding the new position of the playhead in the timeline's view.
        if align == Gtk.Align.START:
            delta = 100
        elif align == Gtk.Align.END:
            delta = layout_width - 100
        else:
            # Center.
            delta = layout_width / 2
        self.hadj.set_value(self.ns_to_pixel(self.__last_position) - delta)

    def _position_cb(self, pipeline, position):
        if self.__last_position == position:
            return

        self.__last_position = position
        self.layout.playhead_position = position
        self.layout.queue_draw()

        self.mini_layout.playhead_position = position
        self.mini_layout.queue_draw()

        layout_width = self.layout.get_allocation().width
        x = self.ns_to_pixel(self.__last_position) - self.hadj.get_value()
        if self.playhead_locked:
            self.scroll_to_playhead()
        elif pipeline.playing() and x > layout_width - 100:
            self.scroll_to_playhead(Gtk.Align.START)
        if not pipeline.playing():
            self.update_visible_overlays()
            self.editor_state.set_value("playhead-position", position)

    def __snapping_started_cb(self, unused_timeline, unused_obj1, unused_obj2, position):
        """Handles a clip snap update operation."""
        self.layout.snap_position = position
        self.layout.queue_draw()

        self.mini_layout.snap_position = position
        self.mini_layout.queue_draw()

    def __snapping_ended_cb(self, *unused_args):
        self.__end_snap()

    def __end_snap(self):
        """Updates the UI to reflect the snap has ended."""
        self.layout.snap_position = 0
        self.layout.queue_draw()

        self.mini_layout.snap_position = 0
        self.mini_layout.queue_draw()

    def update_snapping_distance(self):
        """Updates the snapping distance of self.ges_timeline."""
        self.ges_timeline.set_snapping_distance(
            Zoomable.pixel_to_ns(self.app.settings.edgeSnapDeadband))

    def __snap_distance_changed_cb(self, unused_settings):
        """Handles the change of the snapping distance by the user."""
        self.update_snapping_distance()

    # Gtk.Widget virtual methods implementation

    def do_get_preferred_height(self):
        minimum = SEPARATOR_HEIGHT + LAYER_HEIGHT + SEPARATOR_HEIGHT
        if not self.ges_timeline:
            count = 0
        else:
            count = len(self.ges_timeline.get_layers())
        count = max(1, count)
        natural = SEPARATOR_HEIGHT + count * (LAYER_HEIGHT + SEPARATOR_HEIGHT)
        return minimum, natural

    # ------------- #
    # util methods  #
    # ------------- #

    def _get_parent_of_type(self, widget, _type):
        """Gets a clip from a child widget.

        Args:
            widget (Gtk.Widget): A child of the clip.
            _type (type): The type the clip should be.
        """
        if isinstance(widget, _type):
            return widget

        parent = widget.get_parent()
        while parent is not None and parent != self:
            if isinstance(parent, _type):
                return parent

            parent = parent.get_parent()
        return None

    # Gtk events management

    def do_scroll_event(self, event):
        res, delta_x, delta_y = event.get_scroll_deltas()
        if not res:
            res, direction = event.get_scroll_direction()
            if not res:
                self.error("Could not get scroll delta")
                return False

            if direction == Gdk.ScrollDirection.UP:
                delta_y = -1.0
            elif direction == Gdk.ScrollDirection.DOWN:
                delta_y = 1.0
            else:
                self.error("Could not handle %s scroll event", direction)
                return False

        event_widget = Gtk.get_event_widget(event)
        if event.get_state() & (Gdk.ModifierType.CONTROL_MASK |
                                Gdk.ModifierType.MOD1_MASK):
            # Zoom.
            x, unused_y = event_widget.translate_coordinates(self.layout.layers_vbox, event.x, event.y)
            # Figure out first where to scroll at the end.
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                # The time at the mouse cursor.
                position = self.pixel_to_ns(x)
            else:
                # The time at the playhead.
                position = self.__last_position
            if delta_y > 0:
                Zoomable.zoom_out()
            else:
                Zoomable.zoom_in()
            # Scroll so position remains in place.
            x, unused_y = event_widget.translate_coordinates(self.layout, event.x, event.y)
            self.hadj.set_value(self.ns_to_pixel(position) - x)
            return False

        device = event.get_source_device() or event.device
        if device and device.get_source() in TOUCH_INPUT_SOURCES:
            scroll_x = delta_x
            scroll_y = delta_y
        else:
            scroll_x = delta_y
            scroll_y = 0
            if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                scroll_x, scroll_y = scroll_y, scroll_x

        self.__scroll_adjustment(self.hadj, scroll_x)
        self.__scroll_adjustment(self.vadj, scroll_y)

        return False

    def __scroll_adjustment(self, adj, factor):
        """Changes the adjustment's value depending on the page size.

        The delta is the page_size of adj to the power of 2/3, for example:
        f(200) = 34, f(600) = 71, f(1000) = 100.

        Args:
            adj (Gtk.Adjustment): The adjustment to be changed.
            factor (int): Factor applied to the delta. -1 to scroll up/left,
                1 to scroll down/right.
        """
        adj.set_value(adj.get_value() + factor * adj.props.page_size ** (2 / 3))

    def get_sources_at_position(self, position):
        """Gets video sources at the current position on all layers.

        Returns:
            List[GES.VideoSource]: The found video sources.
        """
        sources = []
        for layer in self.ges_timeline.layers:
            clips = layer.get_clips()
            for clip in clips:
                start = clip.get_start()
                duration = clip.get_duration()
                if start <= position <= duration + start:
                    source = clip.find_track_element(None, GES.VideoSource)
                    if source:
                        sources.append(source)
                    continue
        return sources

    def update_visible_overlays(self):
        sources = self.get_sources_at_position(self.__last_position)
        self.app.gui.editor.viewer.overlay_stack.set_current_sources(sources)

    def set_next_seek_position(self, next_seek_position):
        """Sets the position the playhead seeks to on the next button-release.

        Args:
            next_seek_position (int): the position to seek to
        """
        self.__next_seek_position = next_seek_position

    def _button_press_event_cb(self, unused_widget, event, mini=False):
        """Handles a mouse button press event."""
        self.debug("PRESSED %s", event)
        self.app.gui.editor.focus_timeline()

        event_widget = Gtk.get_event_widget(event)

        res, button = event.get_button()
        if res and button == 1:
            self.dragging_element = self._get_parent_of_type(event_widget, Clip)
            if isinstance(event_widget, TrimHandle):
                self.__clicked_handle = event_widget
            self.debug("Dragging element is %s", self.dragging_element)

            if self.dragging_element:
                self.__drag_start_x = event.x
                self._on_layer = self.dragging_element.ges_clip.props.layer
            else:
                layer_controls = self._get_parent_of_type(event_widget, LayerControls)
                if layer_controls:
                    self.__moving_layer = layer_controls.ges_layer
                    self.app.action_log.begin("move layer",
                                              finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                              toplevel=True)
                else:
                    if not mini:
                        self.layout.marquee.set_start_position(event)
                    else:
                        self.mini_layout.marquee.set_start_position(event)

        self.scrubbing = res and button == 3
        if self.scrubbing:
            self._seek(event, mini)
            clip = self._get_parent_of_type(event_widget, Clip)
            if clip:
                clip.shrink_trim_handles()

        self._scrolling = res and button == 2
        if self._scrolling:
            # pylint: disable=attribute-defined-outside-init
            self._scroll_start_x = event.x
            self._scroll_start_y = event.y

    def _button_release_event_cb(self, unused_widget, event, mini=False):
        self.debug("RELEASED %s", event)
        allow_seek = not self.__got_dragged

        res, button = event.get_button()
        if self.dragging_element:
            self.drag_end()
        elif self.__moving_layer:
            self.__end_moving_layer()
            return False
        elif self.layout.marquee.is_visible() and res and button == 1:
            if not mini:
                clips = self.layout.marquee.find_clips(mini=mini)
                self.selection.set_selection(clips, SELECT)
                self.layout.marquee.hide()
            else:
                clips = self.mini_layout.marquee.find_clips(mini=mini)
                self.selection.set_selection(clips, SELECT)
                self.mini_layout.marquee.hide()

        self.scrubbing = False

        self._scrolling = False

        if allow_seek and res and button == 1:
            if self.app.settings.leftClickAlsoSeeks:
                if self.__next_seek_position is not None:
                    self._project.pipeline.simple_seek(self.__next_seek_position)
                    self.__next_seek_position = None
                else:
                    event_widget = Gtk.get_event_widget(event)
                    if event_widget and self._get_parent_of_type(event_widget, LayerControls) is None:
                        self._seek(event, mini)

            # Allowing group clips selection by shift+clicking anywhere on the timeline.
            if self.get_parent().shift_mask:
                last_clicked_layer = self.last_clicked_layer
                if not last_clicked_layer:
                    clicked_layer, click_pos = self.get_clicked_layer_and_pos(event, mini=mini)
                    self.set_selection_meta_info(clicked_layer, click_pos, SELECT)
                else:
                    last_click_pos = self.last_click_pos
                    cur_clicked_layer, cur_click_pos = self.get_clicked_layer_and_pos(event, mini=mini)
                    clips = self.get_clips_in_between(
                        last_clicked_layer, cur_clicked_layer, last_click_pos, cur_click_pos)
                    self.selection.set_selection(clips, SELECT)
            elif not self.get_parent().control_mask:
                clicked_layer, click_pos = self.get_clicked_layer_and_pos(event, mini=mini)
                self.set_selection_meta_info(clicked_layer, click_pos, SELECT)

        self.__end_snap()
        self.update_visible_overlays()

        return False

    def set_selection_meta_info(self, clicked_layer, click_pos, mode):
        if mode == UNSELECT:
            self.last_clicked_layer = None
            self.last_click_pos = 0
        else:
            self.last_clicked_layer = clicked_layer
            self.last_click_pos = click_pos

    def get_clicked_layer_and_pos(self, event, mini=False):
        """Gets layer and position in the timeline where user clicked."""
        event_widget = Gtk.get_event_widget(event)
        layers_box = self.layout.layers_vbox if not mini else self.mini_layout.layers_vbox
        x, y = event_widget.translate_coordinates(layers_box, event.x, event.y)
        clicked_layer = self.get_layer_at(y, mini=mini)[0]
        ratio = self.calc_best_zoom_ratio() if mini else None
        click_pos = max(0, self.pixel_to_ns(x, zoomratio=ratio))
        return clicked_layer, click_pos

    def get_clips_in_between(self, layer1, layer2, pos1, pos2):
        """Gets all clips between pos1 and pos2 within layer1 and layer2."""
        layers = self.ges_timeline.get_layers()
        layer1_pos = layer1.props.priority
        layer2_pos = layer2.props.priority

        if layer2_pos >= layer1_pos:
            layers_pos = range(layer1_pos, layer2_pos + 1)
        else:
            layers_pos = range(layer2_pos, layer1_pos + 1)

        # The interval in which the clips will be selected.
        start = min(pos1, pos2)
        end = max(pos1, pos2)

        clips = set()
        for layer_pos in layers_pos:
            layer = layers[layer_pos]
            clips.update(layer.get_clips_in_interval(start, end))

        grouped_clips = set()
        # Also include those clips which are grouped with currently selected clips.
        for clip in clips:
            toplevel = clip.get_toplevel_parent()
            if isinstance(toplevel, GES.Group):
                grouped_clips.update([c for c in toplevel.get_children(True)
                                      if isinstance(c, GES.Clip)])

        return clips.union(grouped_clips)

    def clips(self):
        for layer in self.ges_timeline.get_layers():
            for clip in layer.get_clips():
                yield clip

    def _motion_notify_event_cb(self, unused_widget, event, mini=False):
        if self.dragging_element:
            if self.dragging_group is None:
                self.dragging_group = self.selection.group()
            if isinstance(self.dragging_element, TransitionClip) and \
                    not self.__clicked_handle:
                # Don't allow dragging a transition.
                return False

            state = event.get_state()
            if isinstance(state, tuple):
                state = state[1]
            if not state & Gdk.ModifierType.BUTTON1_MASK:
                self.drag_end()
                return False

            if self.got_dragged or self.__past_threshold(event):
                event_widget = Gtk.get_event_widget(event)
                layers_box = self.layout.layers_vbox if not mini else self.mini_layout.layers_vbox
                x, y = event_widget.translate_coordinates(layers_box, event.x, event.y)
                self.__drag_update(x, y, mini)
                self.got_dragged = True
        elif self.__moving_layer:
            event_widget = Gtk.get_event_widget(event)
            unused_x, y = event_widget.translate_coordinates(self, event.x, event.y)
            layer, unused_on_sep = self.get_layer_at(
                y, prefer_ges_layer=self.__moving_layer,
                past_middle_when_adjacent=True, mini=mini)
            if layer != self.__moving_layer:
                priority = layer.get_priority()
                self.move_layer(self.__moving_layer, priority)
        elif self.layout.marquee.is_visible():
            self.layout.marquee.move(event)
        elif self.mini_layout.marquee.is_visible():
            self.mini_layout.marquee.move(event)
        elif self.scrubbing:
            self._seek(event, mini)
        elif self._scrolling:
            self.__scroll(event)

        return False

    def __past_threshold(self, event):
        threshold = 0
        tool = event.get_device_tool()
        if tool:
            if tool.get_tool_type() in {Gdk.DeviceToolType.PEN,
                                        Gdk.DeviceToolType.ERASER}:
                # Wait for the user to drag at least 3 pixels in any direction
                # before dragging when using a stylus. This avoids issues
                # with digitizer tablets where there may be some movement in
                # the stylus while clicking.
                threshold = 3

        delta_x = abs(self.__drag_start_x - event.x)

        return delta_x > threshold

    def _seek(self, event, mini=False):
        event_widget = Gtk.get_event_widget(event)
        layers_box = self.layout.layers_vbox if not mini else self.mini_layout.layers_vbox
        x, unused_y = event_widget.translate_coordinates(layers_box, event.x, event.y)

        ratio = self.calc_best_zoom_ratio() if mini else None
        position = max(0, self.pixel_to_ns(x, zoomratio=ratio))
        self._project.pipeline.simple_seek(position)

    def __scroll(self, event):
        # determine how much to move the canvas
        x_diff = self._scroll_start_x - event.x
        self.hadj.set_value(self.hadj.get_value() + x_diff)
        y_diff = self._scroll_start_y - event.y
        self.vadj.set_value(self.vadj.get_value() + y_diff)

    def __hadj_value_changed_cb(self, hadj):
        self.editor_state.set_value("scroll", hadj.get_value())

    def update_position(self):
        for ges_layer in self.ges_timeline.get_layers():
            ges_layer.ui.update_position()

    def add_clip_to_layer(self, ges_layer: GES.Layer, asset: GES.Asset, start: int) -> Optional[GES.Clip]:
        """Creates a clip out of the asset on the specified layer.

        Shortens the duration so the clip covers an exact number of frames.
        """
        if asset.is_image():
            duration = self.app.settings.imageClipLength * Gst.SECOND / 1000.0
        else:
            duration = asset_get_duration(asset)

        duration = self.mod_duration(duration)

        track_types = asset.get_supported_formats()
        ges_clip = ges_layer.add_asset(asset, start, 0, duration, track_types)
        if not ges_clip:
            return None

        # Tell GES that the max duration is our newly compute max duration
        # so it has the proper information when doing timeline editing.
        if not asset.is_image():
            ges_clip.props.max_duration = min(ges_clip.props.max_duration, duration)

        return ges_clip

    def mod_duration(self, duration: int) -> int:
        """Shortens the duration so it represents an exact number of frames."""
        duration_frames = self.ges_timeline.get_frame_at(duration)
        return self.ges_timeline.get_frame_time(duration_frames)

    def __create_clips(self, x, y, mini=False):
        """Creates the clips for an asset drag operation.

        Args:
            x (int): The x coordinate relative to the layers box.
            y (int): The y coordinate relative to the layers box.
            mini (bool): Event from Mini Timeline or Simple Timeline
        """
        placement = 0
        self.dragging_element = None

        assets = self._project.assets_for_uris(self.drop_data)
        if not assets:
            self._project.add_uris(self.drop_data)
            return

        ges_clips = []
        self.app.action_log.begin("Add clips")
        for asset in assets:
            ges_layer, unused_on_sep = self.get_layer_at(y, mini=mini)
            if not placement:
                ratio = self.calc_best_zoom_ratio() if mini else None
                placement = max(0, self.pixel_to_ns(x, zoomratio=ratio))

            self.debug("Adding %s at %s on layer %s", asset.props.id, Gst.TIME_ARGS(placement), ges_layer)
            self.app.action_log.begin("Add one clip")
            ges_clip = self.add_clip_to_layer(ges_layer, asset, placement)
            if not ges_clip:
                # The clip cannot be placed.

                # Rollback the current "Add one asset" transaction without
                # doing anything, since nothing really changed but GES still
                # emitted signals as if it added AND removed the clip.
                self.app.action_log.rollback(undo=False)
                # Rollback the rest of the "Add assets" transaction.
                self.app.action_log.rollback()
                return

            self.app.action_log.commit("Add one clip")

            placement += ges_clip.props.duration
            ges_clip.first_placement = True
            self._project.pipeline.commit_timeline()

            ges_clips.append(ges_clip)

        self.app.action_log.commit("Add clips")

        if ges_clips:
            ges_clip = ges_clips[0]
            self.dragging_element = ges_clip.ui if not mini else ges_clip.mini_ui
            self._on_layer = ges_layer
            self.dropping_clips = True

            self.selection.set_selection(ges_clips, SELECT)

            self.dragging_group = self.selection.group()

    def _drag_motion_cb(self, widget, context, x, y, timestamp, mini=False):
        target = self.drag_dest_find_target(context, None)
        if not target:
            Gdk.drag_status(context, 0, timestamp)
            return True

        if not self.drop_data_ready:
            # We don't know yet the details of what's being dragged.
            # Ask for the details.
            self.drag_get_data(context, target, timestamp)
        elif target.name() == URI_TARGET_ENTRY.target:
            layers_box = self.layout.layers_vbox if not mini else self.mini_layout.layers_vbox
            x, y = widget.translate_coordinates(layers_box, x, y)
            if not self.dropping_clips:
                # The preview clips have not been created yet.
                self.__create_clips(x, y, mini)
            self.__drag_update(x, y, mini)
        Gdk.drag_status(context, Gdk.DragAction.COPY, timestamp)
        return True

    def _drag_leave_cb(self, unused_widget, context, unused_timestamp):
        # De-highlight the separators. We still need to remember them.
        # See how __on_separators is used in __dragDropCb for details
        self._set_separators_prelight(False)

        target = self.drag_dest_find_target(context, None)
        if self.dragging_element:
            self.__last_clips_on_leave = [(clip.get_layer(), clip)
                                          for clip in self.dragging_group.get_children(False)]
            self.drop_data_ready = False
            if self.dropping_clips:
                self.selection.set_selection([], SELECT)
                for clip in self.dragging_group.get_children(False):
                    clip.get_layer().remove_clip(clip)
                self._project.pipeline.commit_timeline()
                self.app.gui.editor.focus_timeline()

            self.dragging_element = None
            self.__got_dragged = False
            self.dropping_clips = False
            self.dragging_group.ungroup(recursive=False)
            self.dragging_group = None
        elif target == URI_TARGET_ENTRY.target:
            self.clean_drop_data()

    def clean_drop_data(self):
        self.drop_data_ready = False
        self.drop_data = None
        self.dropping_clips = False

    def _drag_drop_cb(self, unused_widget, context, x, y, timestamp):
        # Same as in insertEnd: this value changes during insertion, snapshot
        # it
        zoom_was_fitted = self.zoomed_fitted

        target = self.drag_dest_find_target(context, None).name()
        success = True
        self.clean_drop_data()
        if target == URI_TARGET_ENTRY.target:
            if self.__last_clips_on_leave:
                pipeline = self._project.pipeline
                with self.app.action_log.started("add clip",
                                                 finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                                 toplevel=True):
                    if self.__on_separators:
                        priority = self.separator_priority(self.__on_separators[1])
                        created_layer = self.create_layer(priority)
                    else:
                        created_layer = None
                    for layer, clip in self.__last_clips_on_leave:
                        if created_layer:
                            layer = created_layer
                        clip.first_placement = False
                        layer.add_clip(clip)

                if zoom_was_fitted:
                    self.set_best_zoom_ratio()

                self.drag_end()
        else:
            success = False

        Gtk.drag_finish(context, success, False, timestamp)
        return success

    def _drag_data_received_cb(self, unused_widget, unused_context, unused_x,
                               unused_y, selection_data, unused_info, timestamp):
        data_type = selection_data.get_data_type().name()
        if not self.drop_data_ready:
            self.__last_clips_on_leave = None
            if data_type == URI_TARGET_ENTRY.target:
                self.drop_data = selection_data.get_uris()
                self.drop_data_ready = True
            elif data_type == EFFECT_TARGET_ENTRY.target:
                # Dragging an effect from the Effect Library.
                factory_name = str(selection_data.get_data(), "UTF-8")
                self.drop_data = factory_name
                self.drop_data_ready = True

    # Handle layers
    def _layer_added_cb(self, unused_ges_timeline, ges_layer):
        self._add_layer(ges_layer)
        self.__update_layers()
        self.__update_mini_timeline_height()

    def move_layer(self, ges_layer, index):
        self.debug("Moving layer %s to %s", ges_layer.props.priority, index)
        ges_layers = self.ges_timeline.get_layers()
        ges_layers.remove(ges_layer)
        ges_layers.insert(index, ges_layer)
        for i, ges_layer2 in enumerate(ges_layers):
            if ges_layer2.props.priority != i:
                ges_layer2.props.priority = i

    def _add_layer(self, ges_layer):
        """Adds widgets for controlling and showing the specified layer."""
        layer = FullLayer(ges_layer, self)
        ges_layer.ui = layer

        mini_layer = MiniLayer(ges_layer, self)
        ges_layer.mini_ui = mini_layer

        if not self._separators:
            # Make sure the first layer has separators above it.
            self.__add_separators()

        control = LayerControls(ges_layer, self.app)
        control.show_all()
        self._layers_controls_vbox.pack_start(control, False, False, 0)
        ges_layer.control_ui = control
        # Check the media types so the controls are set up properly.
        layer.check_media_types()
        mini_layer.check_media_types()

        self.layout.layers_vbox.pack_start(layer, False, False, 0)
        layer.show()

        self.mini_layout.layers_vbox.pack_start(mini_layer, False, False, 0)
        mini_layer.show()

        self.__add_separators()

        ges_layer.connect("notify::priority", self.__layer_priority_changed_cb)

    def __add_separators(self):
        """Adds separators to separate layers."""
        controls_separator = SpacedSeparator()
        controls_separator.show()
        self._layers_controls_vbox.pack_start(controls_separator, False, False, 0)

        separator = SpacedSeparator()
        separator.show()
        self.layout.layers_vbox.pack_start(separator, False, False, 0)

        mini_separator = SpacedSeparator()
        mini_separator.show()
        self.mini_layout.layers_vbox.pack_start(mini_separator, False, False, 0)

        self._separators.append((controls_separator, separator, mini_separator))

    def __layer_priority_changed_cb(self, unused_ges_layer, unused_pspec):
        """Handles the changing of a layer's priority."""
        self.__update_layers()

    def __update_layers(self):
        """Updates the layer widgets if their priorities are in good order."""
        ges_layers = self.ges_timeline.get_layers()
        if not ges_layers:
            # Nothing to update.
            return

        priorities = [ges_layer.props.priority for ges_layer in ges_layers]
        if priorities != list(range(len(priorities))):
            self.debug("Layers still being shuffled, not updating widgets: %s", priorities)
            return
        self.debug("Updating layers widgets positions")
        self.__update_separator(0)
        for ges_layer in ges_layers:
            self.__update_layer(ges_layer)
            self.__update_separator(ges_layer.props.priority + 1)

    def __update_separator(self, priority):
        """Sets the position of the separators in their parent."""
        position = priority * 2
        controls_separator, layers_separator, mini_layers_separator = self._separators[priority]
        vbox = self._layers_controls_vbox
        vbox.child_set_property(controls_separator, "position", position)
        vbox = self.layout.layers_vbox
        vbox.child_set_property(layers_separator, "position", position)
        vbox = self.mini_layout.layers_vbox
        vbox.child_set_property(mini_layers_separator, "position", position)

    def __update_layer(self, ges_layer):
        """Sets the position of the layer and its controls in their parent."""
        position = ges_layer.props.priority * 2 + 1
        vbox = self._layers_controls_vbox
        vbox.child_set_property(ges_layer.control_ui, "position", position)
        vbox = self.layout.layers_vbox
        vbox.child_set_property(ges_layer.ui, "position", position)
        vbox = self.mini_layout.layers_vbox
        vbox.child_set_property(ges_layer.mini_ui, "position", position)

    def __update_mini_timeline_height(self):
        ges_layers = self.ges_timeline.get_layers()
        # extra space to allow drag over separators of last layer.
        height = (len(ges_layers) * MINI_LAYER_HEIGHT) + (2 * MINI_LAYER_HEIGHT)
        self.mini_layout_container.props.height_request = height

    def _remove_layer(self, ges_layer):
        self.info("Removing layer: %s", ges_layer.props.priority)
        self.layout.layers_vbox.remove(ges_layer.ui)
        self.mini_layout.layers_vbox.remove(ges_layer.mini_ui)
        self._layers_controls_vbox.remove(ges_layer.control_ui)
        ges_layer.disconnect_by_func(self.__layer_priority_changed_cb)

        # Remove extra separators.
        controls_separator, separator, mini_layers_separator = self._separators.pop()
        self.layout.layers_vbox.remove(separator)
        self.mini_layout.layers_vbox.remove(mini_layers_separator)
        self._layers_controls_vbox.remove(controls_separator)

        ges_layer.ui.release()
        ges_layer.ui = None
        ges_layer.mini_ui.release()
        ges_layer.mini_ui = None
        ges_layer.control_ui = None

    def _layer_removed_cb(self, unused_ges_timeline, ges_layer):
        self._remove_layer(ges_layer)
        self.__update_layers()
        self.__update_mini_timeline_height()

    def separator_priority(self, separator):
        position = self.layout.layers_vbox.child_get_property(separator, "position")
        assert position % 2 == 0
        return int(position / 2)

    # Interface Zoomable
    def zoom_changed(self):
        if not self.ges_timeline:
            # Probably the app starts and there is no project/timeline yet.
            return

        self.update_snapping_distance()
        self.zoomed_fitted = False

        self.update_position()
        self.editor_state.set_value("zoom-level", Zoomable.get_current_zoom_level())

    def calc_best_zoom_ratio(self, mini=True):
        """Returns the zoom ratio so that the entire timeline is in (mini)view."""
        duration = 0 if not self.ges_timeline else self.ges_timeline.get_duration()
        if not duration or (mini and not self.mini_layout_container.get_visible()):
            # Maximum available width, the parent is TimelineContainer
            return self.get_parent().get_allocated_width()

        # Add Gst.SECOND - 1 to the timeline duration to make sure the
        # last second of the timeline will be in view.
        timeline_duration = duration + Gst.SECOND - 1
        timeline_duration_s = int(timeline_duration / Gst.SECOND)
        self.debug("Adjusting zoom for a timeline duration of %s secs",
                   timeline_duration_s)

        layout = self.mini_layout if mini else self.layout
        zoom_ratio = layout.get_allocation().width / timeline_duration_s
        return zoom_ratio

    def set_best_zoom_ratio(self, allow_zoom_in=False):
        """Sets the zoom level so that the entire timeline is in view."""
        duration = 0 if not self.ges_timeline else self.ges_timeline.get_duration()
        if not duration:
            return

        zoom_ratio = self.calc_best_zoom_ratio(mini=False)
        nearest_zoom_level = Zoomable.compute_zoom_level(zoom_ratio)
        if nearest_zoom_level >= Zoomable.get_current_zoom_level() and not allow_zoom_in:
            # This means if we continue we'll zoom in.
            if not allow_zoom_in:
                # For example when the user zoomed out and is adding clips
                # to the timeline, zooming in would be confusing.
                self.log("The entire timeline is already visible")
                return

        Zoomable.set_zoom_level(nearest_zoom_level)
        self.update_snapping_distance()

        # Only do this at the very end, after updating the other widgets.
        self.log("Setting 'zoomed_fitted' to True")
        self.zoomed_fitted = True

        self.hadj.set_value(0)

    def __get_editing_mode(self) -> GES.EditMode:
        if not self.editing_context:
            is_handle = False
        else:
            is_handle = self.editing_context.edge != GES.Edge.EDGE_NONE

        parent = self.get_parent()
        autoripple_active = self.app.settings.timelineAutoRipple and in_devel()
        if parent.shift_mask or autoripple_active:
            return GES.EditMode.EDIT_RIPPLE
        if is_handle and parent.control_mask:
            return GES.EditMode.EDIT_ROLL
        elif is_handle:
            return GES.EditMode.EDIT_TRIM
        return GES.EditMode.EDIT_NORMAL

    def get_layer_at(self, y, prefer_ges_layer=None, past_middle_when_adjacent=False, mini=False):
        ges_layers = self.ges_timeline.get_layers()
        if y < SEPARATOR_HEIGHT:
            # The cursor is at the top, above the first layer.
            self.debug("Returning very first layer")
            ges_layer = ges_layers[0]
            separators = self._separators[0]
            return ges_layer, separators

        # This means if an asset is dragged directly on a separator,
        # it will prefer the layer below the separator, if any.
        # Otherwise, it helps choosing a layer as close to prefer_ges_layer
        # as possible when having an option (y is between two layers).
        prefer_after = True

        if past_middle_when_adjacent:
            index_preferred = prefer_ges_layer.get_priority()
            height_preferred = prefer_ges_layer.ui.get_allocation().height if not mini \
                else prefer_ges_layer.mini_ui.get_allocation().height

        for i, ges_layer in enumerate(ges_layers):
            layer_rect = ges_layer.ui.get_allocation() if not mini \
                else ges_layer.mini_ui.get_allocation()
            layer_y = layer_rect.y
            layer_height = layer_rect.height
            if layer_y <= y < layer_y + layer_height:
                # The cursor is exactly on ges_layer.
                if past_middle_when_adjacent:
                    # Check if far enough from prefer_ges_layer.
                    delta = index_preferred - ges_layer.get_priority()
                    if (delta == 1 and y >= layer_y + height_preferred) or \
                            (delta == -1 and y < layer_y + layer_height - height_preferred):
                        # ges_layer is adjacent to prefer_ges_layer, but the cursor
                        # is not far enough to warrant a change.
                        return prefer_ges_layer, []
                return ges_layer, []

            # Check if there are more layers.
            try:
                next_ges_layer = ges_layers[i + 1]
            except IndexError:
                # Nope, the cursor is below the last layer.
                self.debug("Returning very last layer")
                return ges_layer, self._separators[i + 1]

            if ges_layer == prefer_ges_layer:
                # Choose a layer as close to prefer_ges_layer as possible.
                prefer_after = False

            next_layer = next_ges_layer.ui if not mini \
                else next_ges_layer.mini_ui

            if layer_y + layer_height <= y < next_layer.get_allocation().y:
                # The cursor is between this layer and the one below.
                if prefer_after:
                    ges_layer = next_ges_layer
                separators = self._separators[i + 1]
                self.debug("Returning layer %s, separators: %s", ges_layer, separators)
                return ges_layer, separators

        return None

    def _set_separators_prelight(self, prelight):
        for sep in self.__on_separators:
            set_state_flags_recurse(sep, Gtk.StateFlags.PRELIGHT, are_set=prelight)

    def __drag_update(self, x, y, mini=False):
        """Updates a clip or asset drag operation.

        Args:
            x (int): The x coordinate relative to the layers box.
            y (int): The y coordinate relative to the layers box.
            mini (bool): Event from Mini Timeline or Simple Timeline
        """
        if not self.dragging_element:
            return

        if self.__got_dragged is False:
            self.__got_dragged = True
            if self.__clicked_handle:
                edit_mode = GES.EditMode.EDIT_TRIM
                dragging_edge = self.__clicked_handle.edge
            else:
                edit_mode = GES.EditMode.EDIT_NORMAL
                dragging_edge = GES.Edge.EDGE_NONE

            self.editing_context = EditingContext(self.dragging_element.ges_clip,
                                                  self.ges_timeline,
                                                  edit_mode,
                                                  dragging_edge,
                                                  self.app,
                                                  not self.dropping_clips)

        mode: GES.EditMode = self.__get_editing_mode()
        self.editing_context.set_mode(mode)

        ratio = self.calc_best_zoom_ratio() if mini else None
        x = x - int(self.__drag_start_x)

        if self.editing_context.edge is GES.Edge.EDGE_END:
            x = self.pixel_to_ns(x, zoomratio=ratio)
            position = x + self.__clicked_handle.get_allocated_width()
        else:
            x = self.pixel_to_ns(x, zoomratio=ratio)
            position = x

        self._set_separators_prelight(False)
        res = self.get_layer_at(y, prefer_ges_layer=self._on_layer, mini=mini)
        self._on_layer, self.__on_separators = res
        if (mode != GES.EditMode.EDIT_NORMAL or
                self.dragging_group.props.height > 1):
            # When dragging clips from more than one layer, do not allow
            # them to be dragged between layers to create a new layer.
            self.__on_separators = []

        self._separator_accepting_drop = False
        if self._separator_accepting_drop_id:
            GLib.source_remove(self._separator_accepting_drop_id)
            self._separator_accepting_drop_id = 0
        if self.__on_separators:
            self._separator_accepting_drop_id = GLib.timeout_add(SEPARATOR_ACCEPTING_DROP_INTERVAL_MS,
                                                                 self._separator_accepting_drop_timeout_cb)

        self.editing_context.edit_to(position, self._on_layer)

    def _separator_accepting_drop_timeout_cb(self):
        self._separator_accepting_drop_id = 0
        self._set_separators_prelight(True)
        self._separator_accepting_drop = True

    def create_layer(self, priority):
        """Adds a new layer to the GES timeline."""
        self.debug("Creating layer: priority = %s", priority)
        ges_layers = self.ges_timeline.get_layers()
        assert 0 <= priority <= len(ges_layers)
        new_ges_layer = GES.Layer.new()
        new_ges_layer.props.priority = priority

        for ges_layer in ges_layers:
            if priority <= ges_layer.get_priority():
                ges_layer.props.priority += 1

        self.ges_timeline.add_layer(new_ges_layer)

        return new_ges_layer

    def drag_end(self):
        self.debug("Ending dragging")
        if self.editing_context:
            self.__end_snap()

            if self._separator_accepting_drop and self.__on_separators and self.__got_dragged and not self.__clicked_handle:
                priority = self.separator_priority(self.__on_separators[1])
                ges_layer = self.create_layer(priority)
                position = self.editing_context.new_position
                self.editing_context.edit_to(position, ges_layer)

            self.editing_context.finish()

        self.dragging_element = None
        if self.dragging_group is not None:
            self.dragging_group.ungroup(recursive=False)
            self.dragging_group = None
        self.__clicked_handle = None
        self.__got_dragged = False
        self.editing_context = None

        for ges_layer in self.ges_timeline.get_layers():
            ges_layer.ui.check_media_types()
            ges_layer.mini_ui.check_media_types()

        self._set_separators_prelight(False)
        self.__on_separators = []

    def __end_moving_layer(self):
        self.app.action_log.commit("move layer")
        self.__moving_layer = None


class TimelineContainer(Gtk.Grid, Zoomable, Loggable):
    """Widget for zoom box, ruler, timeline, scrollbars and toolbar."""

    def __init__(self, app, editor_state):
        Zoomable.__init__(self)
        Gtk.Grid.__init__(self)
        Loggable.__init__(self)

        self.app: Gtk.Application = app
        self.editor_state = editor_state
        self._settings = self.app.settings
        self.shift_mask = False
        self.control_mask = False

        self._project = None
        self.state_restored = False
        self.ges_timeline = None
        self.__copied_group = None

        self._create_ui()
        self._create_actions()

        self.timeline.connect("size-allocate", self.__timeline_size_allocate_cb)

    # Public API

    def update_clips_asset(self, asset):
        """Updates the relevant clips to use the asset or the proxy.

        Args:
            asset (GES.Asset): Only the clips which contain this asset will be
                updated.
        """
        proxy = asset.props.proxy

        if not proxy:
            proxy_uris = (self.app.proxy_manager.get_proxy_uri(asset),
                          self.app.proxy_manager.get_proxy_uri(asset, scaled=True))

        for clip in self.timeline.clips():
            if not isinstance(clip, GES.UriClip):
                continue

            if not proxy:
                if clip.get_asset().props.id in proxy_uris:
                    clip.set_asset(asset)
            else:
                if clip.get_asset() == asset:
                    clip.set_asset(proxy)

        self._project.pipeline.commit_timeline()

    def insert_assets(self, assets, position=None):
        """Creates clips out of the specified assets on the longest layer."""
        layer = self._get_longest_layer()
        self._insert_clips_and_assets(assets, position, layer)

    def insert_clips_on_first_layer(self, clips, position=None):
        """Adds clips to the timeline on the first layer."""
        with self.app.action_log.started("insert on first layer",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline)):
            layers = self.ges_timeline.get_layers()
            first_layer = layers[0]
            start = self.__get_insert_position(position)
            end = start + sum([clip.get_duration() for clip in clips])
            intersecting_clips = first_layer.get_clips_in_interval(start, end)
            if intersecting_clips:
                first_layer = self.timeline.create_layer(0)
            self._insert_clips_and_assets(clips, start, first_layer)

    def _insert_clips_and_assets(self, objs, position, layer):
        if self.ges_timeline is None:
            raise TimelineError("No ges_timeline set, this is a bug")

        # We need to snapshot this value, because we only do the zoom fit at the
        # end of clip insertion, but inserting multiple clips eventually changes
        # the value of zoomed_fitted as clips get progressively inserted.
        zoom_was_fitted = self.timeline.zoomed_fitted

        initial_position = self.__get_insert_position(position)
        clip_position = initial_position

        with self.app.action_log.started("add asset",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline)):
            for obj in objs:
                if isinstance(obj, GES.Clip):
                    obj.set_start(clip_position)
                    layer.add_clip(obj)
                    original_duration = obj.get_duration()
                    duration = self.timeline.mod_duration(original_duration)
                    if duration != original_duration:
                        obj.set_duration(duration)
                        obj.props.max_duration = min(obj.props.max_duration, duration)
                elif isinstance(obj, GES.Asset):
                    ges_clip = self.timeline.add_clip_to_layer(layer, obj, clip_position)
                    duration = ges_clip.props.duration
                else:
                    raise TimelineError("Cannot insert: %s" % type(obj))
                clip_position += duration
        self.app.gui.editor.focus_timeline()

        if zoom_was_fitted:
            self.timeline.set_best_zoom_ratio()
        else:
            self.scroll_to_pixel(Zoomable.ns_to_pixel(initial_position))

    def __get_insert_position(self, position):
        if position is None:
            return self._project.pipeline.get_position()
        if position < 0:
            return self.ges_timeline.props.duration
        return position

    def purge_asset(self, asset_id):
        """Removes all instances of an asset from the timeline."""
        layers = self.ges_timeline.get_layers()
        for layer in layers:
            for clip in layer.get_clips():
                if asset_id == clip.get_id():
                    layer.remove_clip(clip)
        self._project.pipeline.commit_timeline()

    def scroll_to_pixel(self, x):
        if x > self.timeline.hadj.props.upper:
            # We can't scroll yet, because the canvas needs to be updated
            GLib.idle_add(self._scroll_to_pixel, x)
        else:
            self._scroll_to_pixel(x)

    def set_project(self, project):
        """Connects to the project's timeline and pipeline."""
        if self._project:
            self.markers.markers_container = None

        self._project = project

        if project:
            self.ges_timeline = project.ges_timeline
        else:
            self.ges_timeline = None

        self.timeline.set_project(project)

        if project:
            self.ruler.set_pipeline(project.pipeline)
            self.ruler.zoom_changed()

            self.timeline.update_snapping_distance()
            self.markers.markers_container = project.ges_timeline.get_marker_list("markers")
            self.editor_state.set_project(project)
            self.restore_state()

    def restore_state(self):
        if self.state_restored:
            return

        if not self._project or not self.get_realized():
            return

        # One attempt is enough.
        self.state_restored = True

        position = self.editor_state.get_value("playhead-position")
        if position:
            self._project.pipeline.simple_seek(position)

        clip_names = self.editor_state.get_value("selection")
        if clip_names:
            clips = [self.ges_timeline.get_element(clip_name)
                     for clip_name in clip_names]
            if all(clips):
                self.timeline.selection.set_selection(clips, SELECT)

        zoom_level = self.editor_state.get_value("zoom-level")
        if zoom_level:
            Zoomable.set_zoom_level(zoom_level)
        else:
            self.timeline.set_best_zoom_ratio(allow_zoom_in=True)

        scroll = self.editor_state.get_value("scroll")
        if scroll:
            # TODO: Figure out why self.scroll_to_pixel(scroll) which calls _scroll_to_pixel directly does not work.
            GLib.idle_add(self._scroll_to_pixel, scroll)

    def do_realize(self):
        Gtk.Widget.do_realize(self)
        self.restore_state()

    def update_actions(self):
        selection = self.timeline.selection
        selection_non_empty = bool(selection)
        self.delete_action.set_enabled(selection_non_empty)
        self.delete_and_shift_action.set_enabled(selection_non_empty)
        self.group_action.set_enabled(selection.can_group)
        self.ungroup_action.set_enabled(selection.can_ungroup)
        self.cut_action.set_enabled(selection_non_empty)
        self.copy_action.set_enabled(selection_non_empty)
        can_paste = bool(self.__copied_group)
        self.paste_action.set_enabled(can_paste)
        self.keyframe_action.set_enabled(selection_non_empty)
        project_loaded = bool(self._project)
        self.add_layer_action.set_enabled(project_loaded)
        self.backward_one_frame_action.set_enabled(project_loaded)
        self.forward_one_frame_action.set_enabled(project_loaded)
        self.backward_one_second_action.set_enabled(project_loaded)
        self.forward_one_second_action.set_enabled(project_loaded)
        self.align_clips_action.set_enabled(AutoAligner.can_align(selection))

    # Internal API

    def _create_ui(self):
        left_size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        self.zoom_box = ZoomBox(self)
        left_size_group.add_widget(self.zoom_box)

        self.timeline = Timeline(self.app, left_size_group, self.editor_state)
        self.effects_popover = EffectsPopover(self.app)

        # Vertical Scrollbar. It will be displayed only when needed.
        self.vscrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL,
                                        adjustment=self.timeline.vadj)
        self.vscrollbar.get_style_context().add_class("background")

        hscrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.HORIZONTAL,
                                   adjustment=self.timeline.hadj)
        hscrollbar.get_style_context().add_class("background")

        self.ruler = TimelineScaleRuler(self)
        self.ruler.props.hexpand = True

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "timelinetoolbar.ui"))
        self.toolbar = builder.get_object("timeline_toolbar")
        self.toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        self.toolbar.get_accessible().set_name("timeline toolbar")

        self.gapless_button = builder.get_object("gapless_button")
        self.gapless_button.set_active(self._settings.timelineAutoRipple)

        self.markers = MarkersBox(self.app, hadj=self.timeline.hadj)

        self.attach(self.markers, 1, 0, 1, 1)
        self.attach(self.zoom_box, 0, 1, 1, 1)
        self.attach(self.ruler, 1, 1, 1, 1)
        self.attach(self.timeline, 0, 2, 2, 1)
        self.attach(self.vscrollbar, 2, 2, 1, 1)
        self.attach(hscrollbar, 1, 3, 1, 1)
        self.attach(self.toolbar, 3, 2, 1, 1)

        self.set_margin_top(SPACING)

        self.show_all()
        if not in_devel():
            self.gapless_button.hide()

        self.timeline.selection.connect(
            "selection-changed", self.__selection_changed_cb)

    def _get_longest_layer(self):
        """Returns the longest layer."""
        layers = self.ges_timeline.get_layers()
        if len(layers) == 1:
            return layers[0]

        # Create a list of (layer_length, layer) tuples.
        layer_lengths = [(max([(clip.get_start() + clip.get_duration()) for clip in layer.get_clips()] or [0]), layer)
                         for layer in layers]
        # Easily get the longest.
        unused_longest_time, longest_layer = max(layer_lengths)
        return longest_layer

    def _create_actions(self):
        # The actions below are added to this action group and thus
        # are accessible only to the self.timeline.layout and self.toolbar
        # widgets (and their children) using the "timeline" prefix.
        # When the action for an accelerator is searched, due to the "timeline"
        # prefix, the accelerators work only when the focus is on one of these
        # two widgets: the layout with the layers representation (excluding the
        # controls) and the timeline toolbar.
        group = Gio.SimpleActionGroup()
        self.timeline.layout.insert_action_group("timeline", group)
        self.timeline.add_layer_button.insert_action_group("timeline", group)
        self.toolbar.insert_action_group("timeline", group)
        self.app.shortcuts.register_group("timeline", _("Timeline"), position=30)

        # Action Search Bar.
        self.action_search = Gio.SimpleAction.new("action-search", None)
        self.action_search.connect("activate", self.__action_search_cb)
        group.add_action(self.action_search)
        self.app.shortcuts.add("timeline.action-search", ["slash"],
                               self.action_search, _("Action Search"))

        # Cut Mode.
        self.action_cut_mode = Gio.SimpleAction.new("action-cut-mode", None)
        self.action_cut_mode.connect("activate", self.__action_cut_mode_cb)
        group.add_action(self.action_cut_mode)
        self.app.shortcuts.add("timeline.action-cut-mode", ["<Alt>c"],
                               self.action_cut_mode, _("Action Cut Mode"))

        # Locked playhead mode, playhead is centered automatically.
        self.action_locked_playhead_mode = Gio.SimpleAction.new("action-playhead-locked-mode", None)
        self.action_locked_playhead_mode.connect("activate", self.__action_locked_playhead_mode_cb)
        group.add_action(self.action_locked_playhead_mode)
        self.app.shortcuts.add("timeline.action-playhead-locked-mode", ["<Alt>p"],
                               self.action_locked_playhead_mode, _("Action Locked Playhead Mode"))

        # Clips actions.
        self.delete_action = Gio.SimpleAction.new("delete-selected-clips", None)
        self.delete_action.connect("activate", self._delete_selected_cb)
        group.add_action(self.delete_action)
        self.app.shortcuts.add("timeline.delete-selected-clips", ["Delete"],
                               self.delete_action,
                               _("Delete selected clips"))

        self.delete_and_shift_action = Gio.SimpleAction.new("delete-selected-clips-and-shift", None)
        self.delete_and_shift_action.connect("activate", self._delete_selected_and_shift_cb)
        group.add_action(self.delete_and_shift_action)
        self.app.shortcuts.add("timeline.delete-selected-clips-and-shift", ["<Shift>Delete"],
                               self.delete_and_shift_action,
                               _("Delete selected clips and shift following ones"))

        self.group_action = Gio.SimpleAction.new("group-selected-clips", None)
        self.group_action.connect("activate", self._group_selected_cb)
        group.add_action(self.group_action)
        self.app.shortcuts.add("timeline.group-selected-clips", ["<Primary>g"],
                               self.group_action,
                               _("Group selected clips together"))

        self.ungroup_action = Gio.SimpleAction.new("ungroup-selected-clips", None)
        self.ungroup_action.connect("activate", self._ungroup_selected_cb)
        group.add_action(self.ungroup_action)
        self.app.shortcuts.add("timeline.ungroup-selected-clips", ["<Primary><Shift>g"],
                               self.ungroup_action,
                               _("Ungroup selected clips"))

        self.cut_action = Gio.SimpleAction.new("cut-selected-clips", None)
        self.cut_action.connect("activate", self.__cut_clips_cb)
        group.add_action(self.cut_action)
        self.app.shortcuts.add("timeline.cut-selected-clips", ["<Primary>x"],
                               self.cut_action,
                               _("Cut selected clips"))

        self.copy_action = Gio.SimpleAction.new("copy-selected-clips", None)
        self.copy_action.connect("activate", self.__copy_clips_cb)
        group.add_action(self.copy_action)
        self.app.shortcuts.add("timeline.copy-selected-clips", ["<Primary>c"],
                               self.copy_action,
                               _("Copy selected clips"))

        self.paste_action = Gio.SimpleAction.new("paste-clips", None)
        self.paste_action.connect("activate", self.__paste_clips_cb)
        group.add_action(self.paste_action)
        self.app.shortcuts.add("timeline.paste-clips", ["<Primary>v"],
                               self.paste_action,
                               _("Paste selected clips"))

        self.add_layer_action = Gio.SimpleAction.new("add-layer", None)
        self.add_layer_action.connect("activate", self.__add_layer_cb)
        group.add_action(self.add_layer_action)
        self.app.shortcuts.add("timeline.add-layer", ["<Primary>n"],
                               self.add_layer_action,
                               _("Add layer"))

        self.seek_forward_clip_action = Gio.SimpleAction.new("seek-forward-clip", None)
        self.seek_forward_clip_action.connect("activate", self._seek_forward_clip_cb)
        group.add_action(self.seek_forward_clip_action)
        self.app.shortcuts.add("timeline.seek-forward-clip", ["<Primary>Right"],
                               self.seek_forward_clip_action,
                               _("Seek to the first clip edge after the playhead"))

        self.seek_backward_clip_action = Gio.SimpleAction.new("seek-backward-clip", None)
        self.seek_backward_clip_action.connect("activate", self._seek_backward_clip_cb)
        group.add_action(self.seek_backward_clip_action)
        self.app.shortcuts.add("timeline.seek-backward-clip", ["<Primary>Left"],
                               self.seek_backward_clip_action,
                               _("Seek to the first clip edge before the playhead"))

        self.shift_forward_action = Gio.SimpleAction.new("shift-forward", None)
        self.shift_forward_action.connect("activate", self._shift_forward_cb)
        group.add_action(self.shift_forward_action)
        self.app.shortcuts.add("timeline.shift-forward", ["<Primary><Shift>Right"],
                               self.shift_forward_action,
                               _("Shift selected clips one frame forward"))

        self.shift_backward_action = Gio.SimpleAction.new("shift-backward", None)
        self.shift_backward_action.connect("activate", self._shift_backward_cb)
        group.add_action(self.shift_backward_action)
        self.app.shortcuts.add("timeline.shift-backward", ["<Primary><Shift>Left"],
                               self.shift_backward_action,
                               _("Shift selected clips one frame backward"))

        self.snap_clips_forward_action = Gio.SimpleAction.new("snap-clips-forward", None)
        self.snap_clips_forward_action.connect("activate", self._snap_clips_forward_cb)
        group.add_action(self.snap_clips_forward_action)
        self.app.shortcuts.add("timeline.snap-clips-forward", ["<Alt>s"],
                               self.snap_clips_forward_action,
                               _("Snap selected clips to the next clip"))

        self.snap_clips_backward_action = Gio.SimpleAction.new("snap-clips-backward", None)
        self.snap_clips_backward_action.connect("activate", self._snap_clips_backward_cb)
        group.add_action(self.snap_clips_backward_action)
        self.app.shortcuts.add("timeline.snap-clips-backward", ["<Alt>a"],
                               self.snap_clips_backward_action,
                               _("Snap selected clips to the previous clip"))

        self.add_effect_action = Gio.SimpleAction.new("add-effect", None)
        self.add_effect_action.connect("activate", self.__add_effect_cb)
        group.add_action(self.add_effect_action)
        self.app.shortcuts.add("timeline.add-effect", ["<Primary>e"],
                               self.add_effect_action,
                               _("Add an effect to the selected clip"))

        self.align_clips_action = Gio.SimpleAction.new("align-clips", None)
        self.align_clips_action.connect("activate", self._align_selected_cb)
        group.add_action(self.align_clips_action)

        if in_devel():
            self.gapless_action = Gio.SimpleAction.new("toggle-gapless-mode", None)
            self.gapless_action.connect("activate", self._gaplessmode_toggled_cb)
            group.add_action(self.gapless_action)

        # Playhead actions.
        self.split_action = Gio.SimpleAction.new("split-clips", None)
        self.split_action.connect("activate", self._split_cb)
        group.add_action(self.split_action)
        self.split_action.set_enabled(True)
        self.app.shortcuts.add("timeline.split-clips", ["s"], self.split_action,
                               _("Split the clip at the position"))

        self.keyframe_action = Gio.SimpleAction.new("keyframe-selected-clips", None)
        self.keyframe_action.connect("activate", self._keyframe_cb)
        group.add_action(self.keyframe_action)
        self.app.shortcuts.add("timeline.keyframe-selected-clips", ["k"],
                               self.keyframe_action,
                               _("Add keyframe to the keyframe curve of selected clip"))

        navigation_group = Gio.SimpleActionGroup()
        self.timeline.layout.insert_action_group("navigation", navigation_group)
        self.toolbar.insert_action_group("navigation", navigation_group)
        self.app.shortcuts.register_group("navigation", _("Timeline Navigation"), position=40)

        self.zoom_in_action = Gio.SimpleAction.new("zoom-in", None)
        self.zoom_in_action.connect("activate", self._zoom_in_cb)
        navigation_group.add_action(self.zoom_in_action)
        self.app.shortcuts.add("navigation.zoom-in",
                               ["<Primary>plus", "<Primary>KP_Add", "<Primary>equal"],
                               self.zoom_in_action,
                               _("Zoom in"))

        self.zoom_out_action = Gio.SimpleAction.new("zoom-out", None)
        self.zoom_out_action.connect("activate", self._zoom_out_cb)
        navigation_group.add_action(self.zoom_out_action)
        self.app.shortcuts.add("navigation.zoom-out",
                               ["<Primary>minus", "<Primary>KP_Subtract"],
                               self.zoom_out_action,
                               _("Zoom out"))

        self.zoom_fit_action = Gio.SimpleAction.new("zoom-fit", None)
        self.zoom_fit_action.connect("activate", self._zoom_fit_cb)
        navigation_group.add_action(self.zoom_fit_action)
        self.app.shortcuts.add("navigation.zoom-fit",
                               ["<Primary>0", "<Primary>KP_0"],
                               self.zoom_fit_action,
                               _("Adjust zoom to fit the project to the window"))

        self.play_action = Gio.SimpleAction.new("play", None)
        self.play_action.connect("activate", self._play_pause_cb)
        navigation_group.add_action(self.play_action)
        self.app.shortcuts.add("navigation.play", ["space"],
                               self.play_action, _("Play"))

        self.backward_one_frame_action = Gio.SimpleAction.new("backward_one_frame", None)
        self.backward_one_frame_action.connect("activate", self._seek_backward_one_frame_cb)
        navigation_group.add_action(self.backward_one_frame_action)
        self.app.shortcuts.add("navigation.backward_one_frame", ["Left"],
                               self.backward_one_frame_action,
                               _("Seek backward one frame"))

        self.forward_one_frame_action = Gio.SimpleAction.new("forward_one_frame", None)
        self.forward_one_frame_action.connect("activate", self._seek_forward_one_frame_cb)
        navigation_group.add_action(self.forward_one_frame_action)
        self.app.shortcuts.add("navigation.forward_one_frame", ["Right"],
                               self.forward_one_frame_action,
                               _("Seek forward one frame"))

        self.backward_one_second_action = Gio.SimpleAction.new("backward_one_second", None)
        self.backward_one_second_action.connect("activate", self._seek_backward_one_second_cb)
        navigation_group.add_action(self.backward_one_second_action)
        self.app.shortcuts.add("navigation.backward_one_second",
                               ["<Shift>Left"],
                               self.backward_one_second_action,
                               _("Seek backward one second"))

        self.forward_one_second_action = Gio.SimpleAction.new("forward_one_second", None)
        self.forward_one_second_action.connect("activate", self._seek_forward_one_second_cb)
        navigation_group.add_action(self.forward_one_second_action)
        self.app.shortcuts.add("navigation.forward_one_second",
                               ["<Shift>Right"],
                               self.forward_one_second_action,
                               _("Seek forward one second"))

        # Markers actions.
        self.add_marker_action = Gio.SimpleAction.new("marker-add", None)
        self.add_marker_action.connect("activate", self._add_marker_cb)
        navigation_group.add_action(self.add_marker_action)
        self.app.shortcuts.add("navigation.marker-add", ["<Primary><Shift>m"],
                               self.add_marker_action,
                               _("Add a marker"))

        self.seek_backward_marker_action = Gio.SimpleAction.new("seek-backward-marker", None)
        self.seek_backward_marker_action.connect("activate", self._seek_backward_marker_cb)
        navigation_group.add_action(self.seek_backward_marker_action)
        self.app.shortcuts.add("navigation.seek-backward-marker", ["<Alt>Left"],
                               self.seek_backward_marker_action,
                               _("Seek to the first marker before the playhead"))

        self.seek_forward_marker_action = Gio.SimpleAction.new("seek-forward-marker", None)
        self.seek_forward_marker_action.connect("activate", self._seek_forward_marker_cb)
        navigation_group.add_action(self.seek_forward_marker_action)
        self.app.shortcuts.add("navigation.seek-forward-marker", ["<Alt>Right"],
                               self.seek_forward_marker_action,
                               _("Seek to the first marker after the playhead"))

        # Viewer actions.
        self.timeline.layout.insert_action_group("viewer", self.app.gui.editor.viewer.action_group)

        self.update_actions()

    def _scroll_to_pixel(self, x):
        hadj = self.timeline.hadj
        self.log("Scroll to: %s %s %s", x, hadj.props.lower, hadj.props.upper)
        if x > hadj.props.upper:
            self.warning(
                "Position %s is bigger than the hscrollbar's upper bound (%s) - is the position really in pixels?",
                x, hadj.props.upper)
        elif x < hadj.props.lower:
            self.warning(
                "Position %s is smaller than the hscrollbar's lower bound (%s)",
                x, hadj.props.lower)

        hadj.set_value(x)

        self.timeline.update_position()
        return False

    def _delete_selected_cb(self, unused_action, unused_parameter):
        if self.ges_timeline:
            with Previewer.manager.paused():
                with self.app.action_log.started("delete clip",
                                                 finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                                 toplevel=True):
                    for clip in self.timeline.selection:
                        if isinstance(clip, GES.TransitionClip):
                            continue
                        layer = clip.get_layer()
                        layer.remove_clip(clip)

            self.timeline.selection.set_selection([], SELECT)

    def _delete_selected_and_shift_cb(self, unused_action, unused_parameter):
        if self.ges_timeline:
            with self.app.action_log.started("delete clip and shift",
                                             finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                             toplevel=True):
                start = []
                end = []

                # remove the clips and store their start/end positions
                for clip in self.timeline.selection:
                    if isinstance(clip, GES.TransitionClip):
                        continue
                    layer = clip.get_layer()
                    start.append(clip.start)
                    end.append(clip.start + clip.duration)
                    layer.remove_clip(clip)

                if start:
                    start = min(start)
                    end = max(end)
                    found_overlapping = False

                    # check if any other clips occur during that period
                    for layer in self.ges_timeline.layers:
                        for clip in layer.get_clips():
                            clip_end = clip.start + clip.duration
                            if clip_end > start and clip.start < end:
                                found_overlapping = True
                                break
                        if found_overlapping:
                            break

                    if not found_overlapping:
                        # now shift everything following cut time
                        shift_by = end - start
                        for layer in self.ges_timeline.layers:
                            for clip in layer.get_clips():
                                if clip.start >= end:
                                    clip.set_start(clip.start - shift_by)

            self.timeline.selection.set_selection([], SELECT)

    def _ungroup_selected_cb(self, unused_action, unused_parameter):
        if not self.ges_timeline:
            return

        toplevels = self.timeline.selection.toplevels()
        containers = set()
        with self.app.action_log.started("ungroup",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            for toplevel in toplevels:
                # Normally we don't ungroup Clips unless they are
                # selected by themselves.
                if isinstance(toplevel, GES.Group) or len(toplevels) == 1:
                    containers |= set(toplevel.ungroup(recursive=False))

        clips = list(self.timeline.selection.get_clips_of(containers))
        self.timeline.selection.set_selection(clips, SELECT)

    def _group_selected_cb(self, unused_action, unused_parameter):
        if not self.ges_timeline:
            return

        toplevels = self.timeline.selection.toplevels()
        if not toplevels:
            return

        with self.app.action_log.started("group",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            container = GES.Container.group(list(toplevels))

        clips = self.timeline.selection.get_clips_of([container])
        self.timeline.selection.set_selection(clips, SELECT)

    def __cut_clips_cb(self, unused_action, unused_parameter):
        self.copy_action.activate(None)
        self.delete_action.activate(None)

    def __copy_clips_cb(self, unused_action, unused_parameter):
        group = self.timeline.selection.group()
        try:
            self.__copied_group = group.copy(deep=True)
            self.__copied_group.props.serialize = False
        finally:
            group.ungroup(recursive=False)
        self.update_actions()

    def __paste_clips_cb(self, unused_action, unused_parameter):
        if not self.__copied_group:
            self.info("Nothing to paste.")
            return

        position = self._project.pipeline.get_position()
        with self.app.action_log.started("paste",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            pasted_group = self.__copied_group.paste(position)
            if not pasted_group:
                self.info("The paste is not possible at position: %s", position)
                return

            # Need to save this as the .ungroup() below changes the duration.
            duration = pasted_group.duration
            self.timeline.selection.select(pasted_group.children)
            try:
                # We need to recreate the copied group as pasting destroys it.
                self.__copied_group = pasted_group.copy(True)
                self.__copied_group.props.serialize = False
            finally:
                pasted_group.ungroup(recursive=False)
        # Seek to the end of the pasted clip(s) for convenience.
        self._project.pipeline.simple_seek(position + duration)

    def __add_layer_cb(self, unused_action, unused_parameter):
        with self.app.action_log.started("add layer",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            priority = len(self.ges_timeline.get_layers())
            self.timeline.create_layer(priority)

    def first_clip_edge(self, layers: Optional[List[GES.Layer]] = None, before: Optional[int] = None, after: Optional[int] = None) -> Optional[int]:
        assert (after is not None) != (before is not None)

        if after is not None:
            start = after
            end = self.ges_timeline.props.duration
            edges = [end]
        else:
            start = 0
            end = before
            edges = [start]

        if start >= end:
            return None

        if not layers:
            layers = self.ges_timeline.layers
        for layer in layers:
            clips = layer.get_clips_in_interval(start, end)
            for clip in clips:
                if clip.start > start:
                    edges.append(clip.start)
                if clip.start + clip.duration < end:
                    edges.append(clip.start + clip.duration)

        if after is not None:
            return min(edges)
        else:
            return max(edges)

    def _seek_forward_clip_cb(self, unused_action, unused_parameter):
        """Seeks to the first clip edge at the right of the playhead."""
        position = self.first_clip_edge(after=self._project.pipeline.get_position())
        if position is None:
            return

        self._project.pipeline.simple_seek(position)
        self.timeline.scroll_to_playhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _seek_backward_clip_cb(self, unused_action, unused_parameter):
        """Seeks to the first clip edge at the left of the playhead."""
        position = self.first_clip_edge(before=self._project.pipeline.get_position())
        if position is None:
            return

        self._project.pipeline.simple_seek(position)
        self.timeline.scroll_to_playhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def __add_effect_cb(self, unused_action, unused_parameter):
        clip = self.timeline.selection.get_single_clip()
        if clip:
            self.effects_popover.set_relative_to(clip.ui)
            self.effects_popover.popup()

    def _align_selected_cb(self, unused_action, unused_parameter):
        if not self.ges_timeline:
            return

        with self.app.action_log.started("Align clips",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            auto_aligner = AutoAligner(self.timeline.selection)
            auto_aligner.run()

    def _split_cb(self, unused_action, unused_parameter):
        """Splits clips.

        If clips are selected, split them at the current playhead position.
        Otherwise, split all clips at the playhead position.
        """
        with self.app.action_log.started("split clip", toplevel=True,
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline)):
            self._split_elements(list(self.timeline.selection))

    def _split_elements(self, clips=None):
        splitting_selection = clips is not None
        if clips is None:
            clips = []
            for layer in self.timeline.ges_timeline.get_layers():
                clips.extend(layer.get_clips())

        position = self._project.pipeline.get_position()
        position = self.ges_timeline.get_frame_time(self.ges_timeline.get_frame_at(position))
        splitted = False
        with self._project.pipeline.commit_timeline_after():
            for clip in clips:
                start = clip.get_start()
                end = start + clip.get_duration()
                if start < position < end:
                    layer = clip.get_layer()
                    layer.splitting_object = True
                    try:
                        self.app.write_action("split-clip",
                                              clip_name=clip.get_name(),
                                              position=float(position / Gst.SECOND))

                        clip.split(position)
                        splitted = True
                    finally:
                        layer.splitting_object = False

        if not splitted and splitting_selection:
            self._split_elements()

    def _keyframe_cb(self, unused_action, unused_parameter):
        """Toggles a keyframe on the selected clip."""
        ges_clip = self.timeline.selection.get_single_clip(GES.Clip)
        if ges_clip is None:
            return

        ges_track_elements = ges_clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
        ges_track_elements += ges_clip.find_track_elements(None, GES.TrackType.AUDIO, GES.Source)

        offset = self._project.pipeline.get_position() - ges_clip.props.start
        if offset <= 0 or offset >= ges_clip.props.duration:
            return
        offset += ges_clip.props.in_point

        with self.app.action_log.started("Toggle keyframe", toplevel=True):
            for ges_track_element in ges_track_elements:
                keyframe_curve = ges_track_element.ui.keyframe_curve
                keyframe_curve.toggle_keyframe(offset)

    def _play_pause_cb(self, unused_action, unused_parameter):
        self._project.pipeline.toggle_playback()

    # Gtk widget virtual methods

    def do_key_press_event(self, event):
        # This is used both for changing the selection modes and for affecting
        # the seek keyboard shortcuts further below
        if event.keyval == Gdk.KEY_Shift_L:
            self.shift_mask = True
        elif event.keyval == Gdk.KEY_Control_L:
            self.control_mask = True

    def do_key_release_event(self, event):
        if event.keyval == Gdk.KEY_Shift_L:
            self.shift_mask = False
        elif event.keyval == Gdk.KEY_Control_L:
            self.control_mask = False

    def _seek_backward_one_second_cb(self, unused_action, unused_parameter):
        self._project.pipeline.seek_relative(0 - Gst.SECOND)
        self.timeline.scroll_to_playhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _seek_forward_one_second_cb(self, unused_action, unused_parameter):
        self._project.pipeline.seek_relative(Gst.SECOND)
        self.timeline.scroll_to_playhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _seek_backward_one_frame_cb(self, unused_action, unused_parameter):
        self._project.pipeline.step_frame(-1)
        self.timeline.scroll_to_playhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _seek_forward_one_frame_cb(self, unused_action, unused_parameter):

        self._project.pipeline.step_frame(1)
        self.timeline.scroll_to_playhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _shift_forward_cb(self, action: Gio.SimpleAction, parameter: Optional[GLib.Variant]) -> None:
        self._shift_clips(1)

    def _shift_backward_cb(self, action: Gio.SimpleAction, parameter: Optional[GLib.Variant]) -> None:
        self._shift_clips(-1)

    def _shift_clips(self, delta_frames):
        """Shifts the selected clips position with the specified number of frames."""
        if not self.ges_timeline:
            return

        previous_snapping_distance = self.ges_timeline.get_snapping_distance()
        self.ges_timeline.set_snapping_distance(0)
        try:
            clips = list(self.timeline.selection)
            clips.sort(key=lambda candidate_clip: candidate_clip.start, reverse=delta_frames > 0)
            # We must use delta * frame_time because getting negative frame time is not possible.
            clip_delta = delta_frames * self.ges_timeline.get_frame_time(1)
            self.app.action_log.begin("Shift clip delta frames")

            for clip in clips:
                if not clip.set_start(clip.start + clip_delta):
                    self.app.action_log.rollback()
                    return
        finally:
            self.ges_timeline.set_snapping_distance(previous_snapping_distance)
        self.app.action_log.commit("Shift clip delta frames")

    def _snap_clips_forward_cb(self, action, parameter):
        self.snap_clips(forward=True)

    def _snap_clips_backward_cb(self, action, parameter):
        self.snap_clips(forward=False)

    def snap_clips(self, forward: bool):
        """Snap clips to next or previous clip."""
        clips = list(self.timeline.selection)
        clips.sort(key=lambda clip: clip.start, reverse=forward)
        with self.app.action_log.started("Snaps to closest clip",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            for clip in clips:
                layer = clip.props.layer
                if not forward:
                    position = self.first_clip_edge(layers=[layer], before=clip.start)
                else:
                    position = self.first_clip_edge(layers=[layer], after=clip.start + clip.duration)
                    if position is not None:
                        position -= clip.duration
                if position is not None:
                    clip.set_start(position)

    def do_focus_in_event(self, unused_event):
        self.log("Timeline has grabbed focus")
        self.update_actions()

    def do_focus_out_event(self, unused_event):
        self.log("Timeline has lost focus")
        self.update_actions()

    def __timeline_size_allocate_cb(self, unused_widget, allocation):
        fits = self.timeline.layout.props.height <= allocation.height
        self.vscrollbar.set_opacity(0 if fits else 1)

    def _zoom_in_cb(self, unused_action, unused_parameter):
        Zoomable.zoom_in()

    def _zoom_out_cb(self, unused_action, unused_parameter):
        Zoomable.zoom_out()

    def _zoom_fit_cb(self, unused_action, unused_parameter):
        self.app.write_action("zoom-fit", optional_action_type=True)

        self.timeline.set_best_zoom_ratio(allow_zoom_in=True)

    def __selection_changed_cb(self, selection):
        """Handles selection changing."""
        self.update_actions()
        clip_names = [clip.props.name for clip in selection]
        self.editor_state.set_value("selection", clip_names)

    def _gaplessmode_toggled_cb(self, unused_action, unused_parameter):
        self._settings.timelineAutoRipple = self.gapless_button.get_active()
        self.info("Automatic ripple: %s", self._settings.timelineAutoRipple)

    def __action_search_cb(self, unused_action, unused_param):
        win = ActionSearchBar(self.app)
        win.set_transient_for(self.app.gui)

        win.show_all()

    def __get_current_marker_boxes(self):
        # Return a list of the selected elements' marker boxes
        sources = self.timeline.selection.get_selected_track_elements()
        if sources:
            return [source.ui.markers for source in sources]

        # Else focus on timeline markers
        return [self.markers]

    def __find_closest_marker(self, containers, before=None, after=None):
        if not containers:
            return None

        position = before if before else after
        timestamps = []
        for container in containers:
            timestamp = container.first_marker(before, after)
            if timestamp is not None:
                timestamps.append(timestamp)

        if not timestamps:
            return None

        closest_timestamp = min(timestamps, key=lambda timestamp: abs(position - timestamp))
        return closest_timestamp

    def _add_marker_cb(self, action, param):
        try:
            position = self.app.project_manager.current_project.pipeline.get_position(fails=False)
        except PipelineError:
            self.warning("Could not get pipeline position")
            return

        containers = self.__get_current_marker_boxes()

        with self.app.action_log.started("Added marker", toplevel=True):
            for marker_container in containers:
                marker_container.add_at_timeline_time(position)

    def _seek_backward_marker_cb(self, action, param):
        try:
            timeline_position = self.app.project_manager.current_project.pipeline.get_position(fails=False)
        except PipelineError:
            self.warning("Could not get pipeline position")
            return

        containers = self.__get_current_marker_boxes()
        position = self.__find_closest_marker(containers, before=timeline_position)
        if position is None:
            return

        self.app.project_manager.current_project.pipeline.simple_seek(position)
        self.app.gui.editor.timeline_ui.timeline.scroll_to_playhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _seek_forward_marker_cb(self, action, param):
        try:
            timeline_position = self.app.project_manager.current_project.pipeline.get_position(fails=False)
        except PipelineError:
            self.warning("Could not get pipeline position")
            return

        containers = self.__get_current_marker_boxes()
        position = self.__find_closest_marker(containers, after=timeline_position)
        if position is None:
            return

        self.app.project_manager.current_project.pipeline.simple_seek(position)
        self.app.gui.editor.timeline_ui.timeline.scroll_to_playhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def __action_cut_mode_cb(self, unused_action, unused_parameter):
        if self.timeline.mini_layout_container.is_visible():
            self.timeline.mini_layout_container.hide()
        else:
            self.timeline.mini_layout_container.props.no_show_all = False
            self.timeline.mini_layout_container.show_all()

    def __action_locked_playhead_mode_cb(self, unused_action, unused_parameter):
        if self.timeline.playhead_locked:
            self.timeline.playhead_locked = False
        else:
            self.timeline.playhead_locked = True
            self.timeline.scroll_to_playhead()
