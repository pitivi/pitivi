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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.autoaligner import AlignmentProgressDialog
from pitivi.autoaligner import AutoAligner
from pitivi.configure import get_ui_dir
from pitivi.configure import in_devel
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.effects import EffectsPopover
from pitivi.settings import GlobalSettings
from pitivi.timeline.elements import Clip
from pitivi.timeline.elements import TransitionClip
from pitivi.timeline.elements import TrimHandle
from pitivi.timeline.layer import Layer
from pitivi.timeline.layer import LayerControls
from pitivi.timeline.layer import SpacedSeparator
from pitivi.timeline.markers import MarkersBox
from pitivi.timeline.previewers import Previewer
from pitivi.timeline.ruler import ScaleRuler
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable
from pitivi.utils.proxy import get_proxy_target
from pitivi.utils.timeline import EditingContext
from pitivi.utils.timeline import SELECT
from pitivi.utils.timeline import Selection
from pitivi.utils.timeline import TimelineError
from pitivi.utils.timeline import UNSELECT
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import EFFECT_TARGET_ENTRY
from pitivi.utils.ui import LAYER_HEIGHT
from pitivi.utils.ui import PLAYHEAD_COLOR
from pitivi.utils.ui import PLAYHEAD_WIDTH
from pitivi.utils.ui import SEPARATOR_HEIGHT
from pitivi.utils.ui import set_cairo_color
from pitivi.utils.ui import set_children_state_recurse
from pitivi.utils.ui import SNAPBAR_COLOR
from pitivi.utils.ui import SNAPBAR_WIDTH
from pitivi.utils.ui import SPACING
from pitivi.utils.ui import TOUCH_INPUT_SOURCES
from pitivi.utils.ui import unset_children_state_recurse
from pitivi.utils.ui import URI_TARGET_ENTRY
from pitivi.utils.widgets import ZoomBox


# Creates new layer if a clip is held at layers separator after this time interval
SEPARATOR_ACCEPTING_DROP_INTERVAL_MS = 1000


GlobalSettings.addConfigOption('edgeSnapDeadband',
                               section="user-interface",
                               key="edge-snap-deadband",
                               default=5,
                               notify=True)

PreferencesDialog.addNumericPreference('edgeSnapDeadband',
                                       section="timeline",
                                       label=_("Snap distance"),
                                       description=_("Threshold (in pixels) at which two clips will snap together "
                                                     "when dragging or trimming."),
                                       lower=0)

GlobalSettings.addConfigOption('imageClipLength',
                               section="user-interface",
                               key="image-clip-length",
                               default=1000,
                               notify=True)

PreferencesDialog.addNumericPreference('imageClipLength',
                                       section="timeline",
                                       label=_("Image clip duration"),
                                       description=_(
                                           "Default clip length (in milliseconds) of images when inserting on the timeline."),
                                       lower=1)

GlobalSettings.addConfigOption('leftClickAlsoSeeks',
                               section="user-interface",
                               key="left-click-to-select",
                               default=True,
                               notify=True)

PreferencesDialog.addTogglePreference('leftClickAlsoSeeks',
                                      section="timeline",
                                      label=_("Left click also seeks"),
                                      description=_(
                                          "Whether left-clicking also seeks besides selecting and editing clips."))

GlobalSettings.addConfigOption("timelineAutoRipple",
                               section="user-interface",
                               key="timeline-autoripple",
                               default=False)


class Marquee(Gtk.Box, Loggable):
    """Widget representing a selection area inside the timeline.

    Args:
        timeline (Timeline): The timeline indirectly containing the marquee.
    """

    __gtype_name__ = "PitiviMarquee"

    def __init__(self, timeline):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)

        self._timeline = timeline
        self.hide()

        self.get_style_context().add_class("Marquee")

    def hide(self):
        """Hides and resets the widget."""
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
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
            self._timeline.layout.layers_vbox, event.x, event.y)

    def move(self, event):
        """Sets the second corner of the marquee.

        Also makes the marquee visible.

        Args:
            event (Gdk.EventMotion): The motion event which contains
                the coordinates of the second corner.
        """
        event_widget = Gtk.get_event_widget(event)
        self.end_x, self.end_y = event_widget.translate_coordinates(
            self._timeline.layout.layers_vbox, event.x, event.y)

        x = min(self.start_x, self.end_x)
        y = min(self.start_y, self.end_y)

        self.get_parent().move(self, x, y)
        self.props.width_request = abs(self.start_x - self.end_x)
        self.props.height_request = abs(self.start_y - self.end_y)
        self.set_visible(True)

    def find_clips(self):
        """Finds the clips which intersect the marquee.

        Returns:
            List[GES.Clip]: The clips under the marquee.
        """
        start_layer = self._timeline._get_layer_at(self.start_y)[0]
        end_layer = self._timeline._get_layer_at(self.end_y)[0]
        start_pos = max(0, self._timeline.pixelToNs(self.start_x))
        end_pos = max(0, self._timeline.pixelToNs(self.end_x))

        return self._timeline.get_clips_in_between(start_layer,
            end_layer, start_pos, end_pos)


class LayersLayout(Gtk.Layout, Zoomable, Loggable):
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
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self._timeline = timeline

        self.snap_position = 0
        self.playhead_position = 0

        self.layers_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.layers_vbox.get_style_context().add_class("LayersBox")
        self.put(self.layers_vbox, 0, 0)

        self.marquee = Marquee(timeline)
        self.put(self.marquee, 0, 0)

        self.layers_vbox.connect("size-allocate", self.__size_allocate_cb)

    def zoomChanged(self):
        # The width of the area/workspace changes when the zoom level changes.
        self.update_width()
        # Required so the playhead is redrawn.
        self.queue_draw()

    def do_draw(self, cr):
        """Draws the children and indicators."""
        Gtk.Layout.do_draw(self, cr)

        self.__draw_playhead(cr)
        self.__draw_snap_indicator(cr)

    def __draw_playhead(self, cr):
        """Draws the playhead line."""
        offset = self.get_hadjustment().get_value()
        position = max(0, self.playhead_position)
        x = self.nsToPixel(position) - offset
        self.__draw_vertical_bar(cr, x, PLAYHEAD_WIDTH, PLAYHEAD_COLOR)

    def __draw_snap_indicator(self, cr):
        """Draws a snapping indicator line."""
        offset = self.get_hadjustment().get_value()
        x = self.nsToPixel(self.snap_position) - offset
        if x <= 0:
            return

        self.__draw_vertical_bar(cr, x, SNAPBAR_WIDTH, SNAPBAR_COLOR)

    def __draw_vertical_bar(self, cr, xpos, width, color):
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

    def update_width(self):
        """Updates the width of the area and the width of the layers_vbox."""
        ges_timeline = self._timeline.ges_timeline
        view_width = self.get_allocated_width()
        space_at_the_end = view_width * 2 / 3
        duration = 0 if not ges_timeline else ges_timeline.props.duration
        width = self.nsToPixel(duration) + space_at_the_end
        width = max(view_width, width)

        self.log("Updating the width_request of the layers_vbox: %s", width)
        # This triggers a renegotiation of the size, meaning
        # layers_vbox's "size-allocate" will be emitted, see __size_allocate_cb.
        self.layers_vbox.props.width_request = width

    def __size_allocate_cb(self, unused_widget, allocation):
        """Sets the size of the scrollable area to fit the layers_vbox."""
        self.log("The size of the layers_vbox changed: %sx%s", allocation.width, allocation.height)
        self.props.width = allocation.width
        # The additional space is for the 'Add layer' button.
        self.props.height = allocation.height + LAYER_HEIGHT / 2


class Timeline(Gtk.EventBox, Zoomable, Loggable):
    """Container for the the layers controls and representation.

    Attributes:
        _project (Project): The project.
    """

    __gtype_name__ = "PitiviTimeline"

    def __init__(self, app, size_group):
        Gtk.EventBox.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self._project = None
        self.ges_timeline = None

        self.props.can_focus = False

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(hbox)

        self.layout = LayersLayout(self)
        self.layout.props.can_focus = True
        self.layout.props.can_default = True
        self.hadj = self.layout.get_hadjustment()
        self.vadj = self.layout.get_vadjustment()
        hbox.pack_end(self.layout, True, True, 0)

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
        self._scrubbing = False
        self._scrolling = False
        # The parameters for the delayed scroll to be performed after
        # the layers box is allocated a size.
        self.delayed_scroll = {}
        self.__next_seek_position = None

        # Clip selection.
        self.selection = Selection()
        # The last layer where the user clicked.
        self.last_clicked_layer = None
        # Position where the user last clicked.
        self.last_click_pos = 0

        # Clip editing.
        # Which clip widget is being edited.
        self.draggingElement = None
        # The GES.Group in case there are one or more clips being dragged.
        self.dragging_group = None
        # Which handle of the draggingElement has been clicked, if any.
        # If set, it means we are in a trim operation.
        self.__clickedHandle = None
        # The GES object for controlling the operation.
        self.editing_context = None
        # Whether draggingElement really got dragged.
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
        # Whether the drop data has been received. See self.dropData below.
        self.dropDataReady = False
        # What's being dropped, for example asset URIs.
        self.dropData = None
        # Whether clips have been created in the current drag & drop.
        self.dropping_clips = False
        # The list of (Layer, Clip) tuples dragged into the timeline.
        self.__last_clips_on_leave = None

        # To be able to receive effects dragged on clips.
        self.drag_dest_set(0, [EFFECT_TARGET_ENTRY], Gdk.DragAction.COPY)
        # To be able to receive assets dragged from the media library.
        self.drag_dest_add_uri_targets()

        self.connect("drag-motion", self._drag_motion_cb)
        self.connect("drag-leave", self._drag_leave_cb)
        self.connect("drag-drop", self._drag_drop_cb)
        self.connect("drag-data-received", self._drag_data_received_cb)

        self.app.settings.connect("edgeSnapDeadbandChanged",
                                  self.__snap_distance_changed_cb)

        self.layout.layers_vbox.connect_after("size-allocate", self.__size_allocate_cb)

    def __size_allocate_cb(self, unused_widget, unused_allocation):
        """Handles the layers vbox size allocations."""
        if self.delayed_scroll:
            self.scrollToPlayhead(**self.delayed_scroll)

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

    def setProject(self, project):
        """Connects to the GES.Timeline holding the project."""
        if self.ges_timeline is not None:
            self.disconnect_by_func(self._button_press_event_cb)
            self.disconnect_by_func(self._button_release_event_cb)
            self.disconnect_by_func(self._motion_notify_event_cb)

            self.ges_timeline.disconnect_by_func(self._durationChangedCb)
            self.ges_timeline.disconnect_by_func(self._layer_added_cb)
            self.ges_timeline.disconnect_by_func(self._layer_removed_cb)
            self.ges_timeline.disconnect_by_func(self.__snapping_started_cb)
            self.ges_timeline.disconnect_by_func(self.__snapping_ended_cb)
            for ges_layer in self.ges_timeline.get_layers():
                self._remove_layer(ges_layer)

            self.ges_timeline.ui = None
            self.ges_timeline = None

        if self._project:
            self._project.pipeline.disconnect_by_func(self._positionCb)

        self._project = project
        if self._project:
            self._project.pipeline.connect('position', self._positionCb)
            self.ges_timeline = self._project.ges_timeline

        if self.ges_timeline is None:
            return

        self.ges_timeline.ui = self

        for ges_layer in self.ges_timeline.get_layers():
            self._add_layer(ges_layer)
        self.__update_layers()

        self.ges_timeline.connect("notify::duration", self._durationChangedCb)
        self.ges_timeline.connect("layer-added", self._layer_added_cb)
        self.ges_timeline.connect("layer-removed", self._layer_removed_cb)
        self.ges_timeline.connect("snapping-started", self.__snapping_started_cb)
        self.ges_timeline.connect("snapping-ended", self.__snapping_ended_cb)

        self.connect("button-press-event", self._button_press_event_cb)
        self.connect("button-release-event", self._button_release_event_cb)
        self.connect("motion-notify-event", self._motion_notify_event_cb)

        self.layout.update_width()

    def _durationChangedCb(self, ges_timeline, pspec):
        self.layout.update_width()

    def scrollToPlayhead(self, align=None, when_not_in_view=False, delayed=False):
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
            x = self.nsToPixel(self.__last_position) - self.hadj.get_value()
            if x >= 0 and x <= layout_width:
                return

        # Deciding the new position of the playhead in the timeline's view.
        if align == Gtk.Align.START:
            delta = 100
        elif align == Gtk.Align.END:
            delta = layout_width - 100
        else:
            # Center.
            delta = layout_width / 2
        self.hadj.set_value(self.nsToPixel(self.__last_position) - delta)

    def _positionCb(self, pipeline, position):
        if self.__last_position == position:
            return

        self.__last_position = position
        self.layout.playhead_position = position
        self.layout.queue_draw()
        layout_width = self.layout.get_allocation().width
        x = self.nsToPixel(self.__last_position) - self.hadj.get_value()
        if pipeline.playing() and x > layout_width - 100:
            self.scrollToPlayhead(Gtk.Align.START)
        if not pipeline.playing():
            self.update_visible_overlays()

    def __snapping_started_cb(self, unused_timeline, unused_obj1, unused_obj2, position):
        """Handles a clip snap update operation."""
        self.layout.snap_position = position
        self.layout.queue_draw()

    def __snapping_ended_cb(self, *unused_args):
        self.__end_snap()

    def __end_snap(self):
        """Updates the UI to reflect the snap has ended."""
        self.layout.snap_position = 0
        self.layout.queue_draw()

    def update_snapping_distance(self):
        """Updates the snapping distance of self.ges_timeline."""
        self.ges_timeline.set_snapping_distance(
            Zoomable.pixelToNs(self.app.settings.edgeSnapDeadband))

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

    def _getParentOfType(self, widget, _type):
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
                position = self.pixelToNs(x)
            else:
                # The time at the playhead.
                position = self.__last_position
            if delta_y > 0:
                Zoomable.zoomOut()
            else:
                Zoomable.zoomIn()
            # Scroll so position remains in place.
            x, unused_y = event_widget.translate_coordinates(self.layout, event.x, event.y)
            self.hadj.set_value(self.nsToPixel(position) - x)
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

    def _button_press_event_cb(self, unused_widget, event):
        """Handles a mouse button press event."""
        self.debug("PRESSED %s", event)
        self.app.gui.editor.focusTimeline()

        event_widget = Gtk.get_event_widget(event)

        res, button = event.get_button()
        if res and button == 1:
            self.draggingElement = self._getParentOfType(event_widget, Clip)
            if isinstance(event_widget, TrimHandle):
                self.__clickedHandle = event_widget
            self.debug("Dragging element is %s", self.draggingElement)

            if self.draggingElement:
                self.__drag_start_x = event.x
                self._on_layer = self.draggingElement.layer.ges_layer
                self.dragging_group = self.selection.group()
            else:
                layer_controls = self._getParentOfType(event_widget, LayerControls)
                if layer_controls:
                    self.__moving_layer = layer_controls.ges_layer
                    self.app.action_log.begin("move layer",
                                              finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                              toplevel=True)
                else:
                    self.layout.marquee.set_start_position(event)

        self._scrubbing = res and button == 3
        if self._scrubbing:
            self._seek(event)
            clip = self._getParentOfType(event_widget, Clip)
            if clip:
                clip.shrinkTrimHandles()

        self._scrolling = res and button == 2
        if self._scrolling:
            self._scroll_start_x = event.x
            self._scroll_start_y = event.y

    def _button_release_event_cb(self, unused_widget, event):
        allow_seek = not self.__got_dragged

        res, button = event.get_button()
        if self.draggingElement:
            self.dragEnd()
        elif self.__moving_layer:
            self.__endMovingLayer()
            return False
        elif res and button == 1:
            self._selectUnderMarquee()

        self._scrubbing = False

        self._scrolling = False

        if allow_seek and res and button == 1:
            if self.app.settings.leftClickAlsoSeeks:
                if self.__next_seek_position is not None:
                    self._project.pipeline.simple_seek(self.__next_seek_position)
                    self.__next_seek_position = None
                else:
                    event_widget = Gtk.get_event_widget(event)
                    if self._getParentOfType(event_widget, LayerControls) is None:
                        self._seek(event)

            # Allowing group clips selection by shift+clicking anywhere on the timeline.
            if self.get_parent()._shiftMask:
                last_clicked_layer = self.last_clicked_layer
                if not last_clicked_layer:
                    clicked_layer, click_pos = self.get_clicked_layer_and_pos(event)
                    self.set_selection_meta_info(clicked_layer, click_pos, SELECT)
                else:
                    last_click_pos = self.last_click_pos
                    cur_clicked_layer, cur_click_pos = self.get_clicked_layer_and_pos(event)
                    clips = self.get_clips_in_between(
                        last_clicked_layer, cur_clicked_layer, last_click_pos, cur_click_pos)
                    self.selection.setSelection(clips, SELECT)
            elif not self.get_parent()._controlMask:
                clicked_layer, click_pos = self.get_clicked_layer_and_pos(event)
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

    def get_clicked_layer_and_pos(self, event):
        """Gets layer and position in the timeline where user clicked."""
        event_widget = Gtk.get_event_widget(event)
        x, y = event_widget.translate_coordinates(self.layout.layers_vbox, event.x, event.y)
        clicked_layer = self._get_layer_at(y)[0]
        click_pos = max(0, self.pixelToNs(x))
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

    def _motion_notify_event_cb(self, unused_widget, event):
        if self.draggingElement:
            if type(self.draggingElement) == TransitionClip and \
                    not self.__clickedHandle:
                # Don't allow dragging a transition.
                return False

            state = event.get_state()
            if isinstance(state, tuple):
                state = state[1]
            if not state & Gdk.ModifierType.BUTTON1_MASK:
                self.dragEnd()
                return False

            if self.got_dragged or self.__past_threshold(event):
                event_widget = Gtk.get_event_widget(event)
                x, y = event_widget.translate_coordinates(self.layout.layers_vbox, event.x, event.y)
                self.__drag_update(x, y)
                self.got_dragged = True
        elif self.__moving_layer:
            event_widget = Gtk.get_event_widget(event)
            unused_x, y = event_widget.translate_coordinates(self, event.x, event.y)
            layer, unused_on_sep = self._get_layer_at(
                y, prefer_ges_layer=self.__moving_layer,
                past_middle_when_adjacent=True)
            if layer != self.__moving_layer:
                priority = layer.get_priority()
                self.moveLayer(self.__moving_layer, priority)
        elif self.layout.marquee.start_x:
            self.layout.marquee.move(event)
        elif self._scrubbing:
            self._seek(event)
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

    def _seek(self, event):
        event_widget = Gtk.get_event_widget(event)
        x, unused_y = event_widget.translate_coordinates(self.layout.layers_vbox, event.x, event.y)
        position = max(0, self.pixelToNs(x))
        self._project.pipeline.simple_seek(position)

    def __scroll(self, event):
        # determine how much to move the canvas
        x_diff = self._scroll_start_x - event.x
        self.hadj.set_value(self.hadj.get_value() + x_diff)
        y_diff = self._scroll_start_y - event.y
        self.vadj.set_value(self.vadj.get_value() + y_diff)

    def _selectUnderMarquee(self):
        if self.layout.marquee.props.width_request > 0:
            clips = self.layout.marquee.find_clips()
        else:
            clips = []
        self.selection.setSelection(clips, SELECT)

        self.layout.marquee.hide()

    def updatePosition(self):
        for ges_layer in self.ges_timeline.get_layers():
            ges_layer.ui.updatePosition()

    def __create_clips(self, x, y):
        """Creates the clips for an asset drag operation.

        Args:
            x (int): The x coordinate relative to the layers box.
            y (int): The y coordinate relative to the layers box.
        """
        placement = 0
        self.draggingElement = None

        assets = self._project.assetsForUris(self.dropData)
        if not assets:
            self._project.addUris(self.dropData)
            return False

        ges_clips = []
        for asset in assets:
            if asset.is_image():
                clip_duration = self.app.settings.imageClipLength * \
                    Gst.SECOND / 1000.0
            else:
                clip_duration = asset.get_duration()

            ges_layer, unused_on_sep = self._get_layer_at(y)
            if not placement:
                placement = self.pixelToNs(x)
            placement = max(0, placement)

            self.debug("Creating %s at %s", asset.props.id, Gst.TIME_ARGS(placement))

            ges_clip = ges_layer.add_asset(asset,
                                           placement,
                                           0,
                                           clip_duration,
                                           asset.get_supported_formats())
            placement += clip_duration
            ges_clip.first_placement = True
            self._project.pipeline.commit_timeline()

            ges_clips.append(ges_clip)

        if ges_clips:
            ges_clip = ges_clips[0]
            self.draggingElement = ges_clip.ui
            self._on_layer = ges_layer
            self.dropping_clips = True

            self.selection.setSelection(ges_clips, SELECT)

            self.dragging_group = self.selection.group()

        return True

    def _drag_motion_cb(self, widget, context, x, y, timestamp):
        target = self.drag_dest_find_target(context, None)
        if not target:
            Gdk.drag_status(context, 0, timestamp)
            return True

        if not self.dropDataReady:
            # We don't know yet the details of what's being dragged.
            # Ask for the details.
            self.drag_get_data(context, target, timestamp)
        elif target.name() == URI_TARGET_ENTRY.target:
            x, y = widget.translate_coordinates(self.layout.layers_vbox, x, y)
            if not self.dropping_clips:
                # The preview clips have not been created yet.
                self.__create_clips(x, y)
            self.__drag_update(x, y)
        Gdk.drag_status(context, Gdk.DragAction.COPY, timestamp)
        return True

    def _drag_leave_cb(self, unused_widget, context, unused_timestamp):
        # De-highlight the separators. We still need to remember them.
        # See how __on_separators is used in __dragDropCb for details
        self._setSeparatorsPrelight(False)

        target = self.drag_dest_find_target(context, None)
        if self.draggingElement:
            self.__last_clips_on_leave = [(clip.get_layer(), clip)
                                          for clip in self.dragging_group.get_children(False)]
            self.dropDataReady = False
            if self.dropping_clips:
                self.selection.setSelection([], SELECT)
                for clip in self.dragging_group.get_children(False):
                    clip.get_layer().remove_clip(clip)
                self._project.pipeline.commit_timeline()

            self.draggingElement = None
            self.__got_dragged = False
            self.dropping_clips = False
            self.dragging_group.ungroup(recursive=False)
            self.dragging_group = None
        elif target == URI_TARGET_ENTRY.target:
            self.cleanDropData()

    def cleanDropData(self):
        self.dropDataReady = False
        self.dropData = None
        self.dropping_clips = False

    def _drag_drop_cb(self, unused_widget, context, x, y, timestamp):
        # Same as in insertEnd: this value changes during insertion, snapshot
        # it
        zoom_was_fitted = self.zoomed_fitted

        target = self.drag_dest_find_target(context, None).name()
        success = True
        self.cleanDropData()
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

                self.dragEnd()
        else:
            success = False

        Gtk.drag_finish(context, success, False, timestamp)
        return success

    def _drag_data_received_cb(self, unused_widget, unused_context, unused_x,
                               unused_y, selection_data, unused_info, timestamp):
        data_type = selection_data.get_data_type().name()
        if not self.dropDataReady:
            self.__last_clips_on_leave = None
            if data_type == URI_TARGET_ENTRY.target:
                self.dropData = selection_data.get_uris()
                self.dropDataReady = True
            elif data_type == EFFECT_TARGET_ENTRY.target:
                # Dragging an effect from the Effect Library.
                factory_name = str(selection_data.get_data(), "UTF-8")
                self.dropData = factory_name
                self.dropDataReady = True

    # Handle layers
    def _layer_added_cb(self, unused_ges_timeline, ges_layer):
        self._add_layer(ges_layer)
        self.__update_layers()

    def moveLayer(self, ges_layer, index):
        self.debug("Moving layer %s to %s", ges_layer.props.priority, index)
        ges_layers = self.ges_timeline.get_layers()
        ges_layer = ges_layers.pop(ges_layer.props.priority)
        ges_layers.insert(index, ges_layer)
        for i, ges_layer in enumerate(ges_layers):
            if ges_layer.props.priority != i:
                ges_layer.props.priority = i

    def _add_layer(self, ges_layer):
        """Adds widgets for controlling and showing the specified layer."""
        layer = Layer(ges_layer, self)
        ges_layer.ui = layer

        if not self._separators:
            # Make sure the first layer has separators above it.
            self.__add_separators()

        control = LayerControls(ges_layer, self.app)
        control.show_all()
        self._layers_controls_vbox.pack_start(control, False, False, 0)
        ges_layer.control_ui = control
        # Check the media types so the controls are set up properly.
        layer.checkMediaTypes()

        self.layout.layers_vbox.pack_start(layer, False, False, 0)
        layer.show()

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

        self._separators.append((controls_separator, separator))

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
        controls_separator, layers_separator = self._separators[priority]
        vbox = self._layers_controls_vbox
        vbox.child_set_property(controls_separator, "position", position)
        vbox = self.layout.layers_vbox
        vbox.child_set_property(layers_separator, "position", position)

    def __update_layer(self, ges_layer):
        """Sets the position of the layer and its controls in their parent."""
        position = ges_layer.props.priority * 2 + 1
        vbox = self._layers_controls_vbox
        vbox.child_set_property(ges_layer.control_ui, "position", position)
        vbox = self.layout.layers_vbox
        vbox.child_set_property(ges_layer.ui, "position", position)

    def _remove_layer(self, ges_layer):
        self.info("Removing layer: %s", ges_layer.props.priority)
        self.layout.layers_vbox.remove(ges_layer.ui)
        self._layers_controls_vbox.remove(ges_layer.control_ui)
        ges_layer.disconnect_by_func(self.__layer_priority_changed_cb)

        # Remove extra separators.
        controls_separator, separator = self._separators.pop()
        self.layout.layers_vbox.remove(separator)
        self._layers_controls_vbox.remove(controls_separator)

        ges_layer.ui.release()
        ges_layer.ui = None
        ges_layer.control_ui = None

    def _layer_removed_cb(self, unused_ges_timeline, ges_layer):
        self._remove_layer(ges_layer)
        self.__update_layers()

    def separator_priority(self, separator):
        position = self.layout.layers_vbox.child_get_property(separator, "position")
        assert position % 2 == 0
        return int(position / 2)

    # Interface Zoomable
    def zoomChanged(self):
        if not self.ges_timeline:
            # Probably the app starts and there is no project/timeline yet.
            return

        self.update_snapping_distance()
        self.zoomed_fitted = False

        self.updatePosition()

    def set_best_zoom_ratio(self, allow_zoom_in=False):
        """Sets the zoom level so that the entire timeline is in view."""
        duration = 0 if not self.ges_timeline else self.ges_timeline.get_duration()
        if not duration:
            return

        # Add Gst.SECOND - 1 to the timeline duration to make sure the
        # last second of the timeline will be in view.
        timeline_duration = duration + Gst.SECOND - 1
        timeline_duration_s = int(timeline_duration / Gst.SECOND)
        self.debug("Adjusting zoom for a timeline duration of %s secs",
                   timeline_duration_s)

        zoom_ratio = self.layout.get_allocation().width / timeline_duration_s
        nearest_zoom_level = Zoomable.computeZoomLevel(zoom_ratio)
        if nearest_zoom_level >= Zoomable.getCurrentZoomLevel() and not allow_zoom_in:
            # This means if we continue we'll zoom in.
            if not allow_zoom_in:
                # For example when the user zoomed out and is adding clips
                # to the timeline, zooming in would be confusing.
                self.log("The entire timeline is already visible")
                return

        Zoomable.setZoomLevel(nearest_zoom_level)
        self.update_snapping_distance()

        # Only do this at the very end, after updating the other widgets.
        self.log("Setting 'zoomed_fitted' to True")
        self.zoomed_fitted = True

        self.hadj.set_value(0)

    def __getEditingMode(self):
        if not self.editing_context:
            is_handle = False
        else:
            is_handle = self.editing_context.edge != GES.Edge.EDGE_NONE

        parent = self.get_parent()
        autoripple_active = self.app.settings.timelineAutoRipple and in_devel()
        if parent._shiftMask or autoripple_active:
            return GES.EditMode.EDIT_RIPPLE
        if is_handle and parent._controlMask:
            return GES.EditMode.EDIT_ROLL
        elif is_handle:
            return GES.EditMode.EDIT_TRIM
        return GES.EditMode.EDIT_NORMAL

    def _get_layer_at(self, y, prefer_ges_layer=None, past_middle_when_adjacent=False):
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
            height_preferred = prefer_ges_layer.ui.get_allocation().height

        for i, ges_layer in enumerate(ges_layers):
            layer_rect = ges_layer.ui.get_allocation()
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

            if layer_y + layer_height <= y < next_ges_layer.ui.get_allocation().y:
                # The cursor is between this layer and the one below.
                if prefer_after:
                    ges_layer = next_ges_layer
                separators = self._separators[i + 1]
                self.debug("Returning layer %s, separators: %s", ges_layer, separators)
                return ges_layer, separators

    def _setSeparatorsPrelight(self, light):
        for sep in self.__on_separators:
            if light:
                set_children_state_recurse(sep, Gtk.StateFlags.PRELIGHT)
            else:
                unset_children_state_recurse(sep, Gtk.StateFlags.PRELIGHT)

    def __drag_update(self, x, y):
        """Updates a clip or asset drag operation.

        Args:
            x (int): The x coordinate relative to the layers box.
            y (int): The y coordinate relative to the layers box.
        """
        if not self.draggingElement:
            return

        if self.__got_dragged is False:
            self.__got_dragged = True
            if self.__clickedHandle:
                edit_mode = GES.EditMode.EDIT_TRIM
                dragging_edge = self.__clickedHandle.edge
            else:
                edit_mode = GES.EditMode.EDIT_NORMAL
                dragging_edge = GES.Edge.EDGE_NONE

            self.editing_context = EditingContext(self.draggingElement.ges_clip,
                                                  self.ges_timeline,
                                                  edit_mode,
                                                  dragging_edge,
                                                  self.app,
                                                  not self.dropping_clips)

        mode = self.__getEditingMode()
        self.editing_context.setMode(mode)

        if self.editing_context.edge is GES.Edge.EDGE_END:
            position = self.pixelToNs(x)
        else:
            position = self.pixelToNs(x - self.__drag_start_x)

        self._setSeparatorsPrelight(False)
        res = self._get_layer_at(y, prefer_ges_layer=self._on_layer)
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
        self._setSeparatorsPrelight(True)
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

    def dragEnd(self):
        if self.editing_context:
            self.__end_snap()

            if self._separator_accepting_drop and self.__on_separators and self.__got_dragged and not self.__clickedHandle:
                priority = self.separator_priority(self.__on_separators[1])
                ges_layer = self.create_layer(priority)
                position = self.editing_context.new_position
                self.editing_context.edit_to(position, ges_layer)

            self.editing_context.finish()

        self.draggingElement = None
        if self.dragging_group is not None:
            self.dragging_group.ungroup(recursive=False)
            self.dragging_group = None
        self.__clickedHandle = None
        self.__got_dragged = False
        self.editing_context = None

        for ges_layer in self.ges_timeline.get_layers():
            ges_layer.ui.checkMediaTypes()

        self._setSeparatorsPrelight(False)
        self.__on_separators = []

    def __endMovingLayer(self):
        self.app.action_log.commit("move layer")
        self.__moving_layer = None


class TimelineContainer(Gtk.Grid, Zoomable, Loggable):
    """Widget for zoom box, ruler, timeline, scrollbars and toolbar."""

    def __init__(self, app):
        Zoomable.__init__(self)
        Gtk.Grid.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self._settings = self.app.settings
        self._shiftMask = False
        self._controlMask = False

        self._project = None
        self.ges_timeline = None
        self.__copied_group = None

        self._createUi()
        self._createActions()

        self.timeline.connect("size-allocate", self.__timeline_size_allocate_cb)

    # Public API

    def update_clips_asset(self, asset, proxy):
        """Updates the relevant clips to use the asset or the proxy.

        Args:
            asset (GES.Asset): Only the clips who's current asset's target is
                this will be updated.
            proxy (Ges.Asset): The proxy to use, or None to use the asset itself.
        """
        original_asset = get_proxy_target(asset)
        replacement_asset = proxy or asset
        for clip in self.timeline.clips():
            if not isinstance(clip, GES.UriClip):
                continue
            if get_proxy_target(clip) == original_asset:
                clip.set_asset(replacement_asset)
        self._project.pipeline.commit_timeline()

    def insertAssets(self, assets, position=None):
        """Creates clips out of the specified assets on the longest layer."""
        layer = self._getLongestLayer()
        self._insertClipsAndAssets(assets, position, layer)

    def insert_clips_on_first_layer(self, clips, position=None):
        """Adds clips to the timeline on the first layer."""
        with self.app.action_log.started("insert on first layer",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline)):
            layers = self.ges_timeline.get_layers()
            first_layer = layers[0]
            start = self.__getInsertPosition(position)
            end = start + sum([clip.get_duration() for clip in clips])
            intersecting_clips = first_layer.get_clips_in_interval(start, end)
            if intersecting_clips:
                first_layer = self.timeline.create_layer(0)
            self._insertClipsAndAssets(clips, start, first_layer)

    def _insertClipsAndAssets(self, objs, position, layer):
        if self.ges_timeline is None:
            raise TimelineError("No ges_timeline set, this is a bug")

        # We need to snapshot this value, because we only do the zoom fit at the
        # end of clip insertion, but inserting multiple clips eventually changes
        # the value of zoomed_fitted as clips get progressively inserted.
        zoom_was_fitted = self.timeline.zoomed_fitted

        initial_position = self.__getInsertPosition(position)
        clip_position = initial_position

        with self.app.action_log.started("add asset",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline)):
            for obj in objs:
                if isinstance(obj, GES.Clip):
                    obj.set_start(clip_position)
                    layer.add_clip(obj)
                    duration = obj.get_duration()
                elif isinstance(obj, GES.Asset):
                    if obj.is_image():
                        duration = self.app.settings.imageClipLength * \
                            Gst.SECOND / 1000.0
                    else:
                        duration = obj.get_duration()

                    layer.add_asset(obj,
                                    start=clip_position,
                                    inpoint=0,
                                    duration=duration,
                                    track_types=obj.get_supported_formats())
                else:
                    raise TimelineError("Cannot insert: %s" % type(obj))
                clip_position += duration
        self.app.gui.editor.focusTimeline()

        if zoom_was_fitted:
            self.timeline.set_best_zoom_ratio()
        else:
            self.scrollToPixel(Zoomable.nsToPixel(initial_position))

    def __getInsertPosition(self, position):
        if position is None:
            return self._project.pipeline.getPosition()
        if position < 0:
            return self.ges_timeline.props.duration
        return position

    def purgeAsset(self, asset_id):
        """Removes all instances of an asset from the timeline."""
        layers = self.ges_timeline.get_layers()
        for layer in layers:
            for clip in layer.get_clips():
                if asset_id == clip.get_id():
                    layer.remove_clip(clip)
        self._project.pipeline.commit_timeline()

    def scrollToPixel(self, x):
        if x > self.timeline.hadj.props.upper:
            # We can't scroll yet, because the canvas needs to be updated
            GLib.idle_add(self._scrollToPixel, x)
        else:
            self._scrollToPixel(x)

    def setProject(self, project):
        """Connects to the project's timeline and pipeline."""
        if self._project:
            self._project.disconnect_by_func(self._rendering_settings_changed_cb)
            try:
                self.timeline._pipeline.disconnect_by_func(
                    self.timeline.positionCb)
            except AttributeError:
                pass
            except TypeError:
                pass  # We were not connected no problem

            self.timeline._pipeline = None
            self.markers.markers_container = None

        self._project = project

        if project:
            project.connect("rendering-settings-changed",
                            self._rendering_settings_changed_cb)
            self.ges_timeline = project.ges_timeline
        else:
            self.ges_timeline = None

        self.timeline.setProject(project)

        if project:
            self.ruler.setPipeline(project.pipeline)
            self.ruler.zoomChanged()
            self._update_ruler(project.videorate)

            self.timeline.set_best_zoom_ratio(allow_zoom_in=True)
            self.timeline.update_snapping_distance()
            self.markers.markers_container = project.ges_timeline.get_marker_list("markers")

    def updateActions(self):
        selection = self.timeline.selection
        selection_non_empty = bool(selection)
        self.delete_action.set_enabled(selection_non_empty)
        self.delete_and_shift_action.set_enabled(selection_non_empty)
        self.group_action.set_enabled(selection.can_group)
        self.ungroup_action.set_enabled(selection.can_ungroup)
        self.copy_action.set_enabled(selection_non_empty)
        can_paste = bool(self.__copied_group)
        self.paste_action.set_enabled(can_paste)
        self.keyframe_action.set_enabled(selection_non_empty)
        project_loaded = bool(self._project)
        self.backward_one_frame_action.set_enabled(project_loaded)
        self.forward_one_frame_action.set_enabled(project_loaded)
        self.backward_one_second_action.set_enabled(project_loaded)
        self.forward_one_second_action.set_enabled(project_loaded)

    # Internal API

    def _createUi(self):
        left_size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        zoom_box = ZoomBox(self)
        left_size_group.add_widget(zoom_box)

        self.timeline = Timeline(self.app, left_size_group)
        self.effects_popover = EffectsPopover(self.app)

        # Vertical Scrollbar. It will be displayed only when needed.
        self.vscrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL,
                                        adjustment=self.timeline.vadj)
        self.vscrollbar.get_style_context().add_class("background")

        hscrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.HORIZONTAL,
                                   adjustment=self.timeline.hadj)
        hscrollbar.get_style_context().add_class("background")

        self.ruler = ScaleRuler(self)
        self.ruler.props.hexpand = True
        self.ruler.setProjectFrameRate(24.)

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "timelinetoolbar.ui"))
        self.toolbar = builder.get_object("timeline_toolbar")
        self.toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        self.toolbar.get_accessible().set_name("timeline toolbar")

        self.gapless_button = builder.get_object("gapless_button")
        self.gapless_button.set_active(self._settings.timelineAutoRipple)

        self.markers = MarkersBox(self.app, hadj=self.timeline.hadj)

        self.attach(self.markers, 1, 0, 1, 1)
        self.attach(zoom_box, 0, 1, 1, 1)
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

    def _getLongestLayer(self):
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

    def _createActions(self):
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

        # Clips actions.
        self.delete_action = Gio.SimpleAction.new("delete-selected-clips", None)
        self.delete_action.connect("activate", self._deleteSelected)
        group.add_action(self.delete_action)
        self.app.shortcuts.add("timeline.delete-selected-clips", ["Delete"],
                               _("Delete selected clips"))

        self.delete_and_shift_action = Gio.SimpleAction.new("delete-selected-clips-and-shift", None)
        self.delete_and_shift_action.connect("activate", self._delete_selected_and_shift)
        group.add_action(self.delete_and_shift_action)
        self.app.shortcuts.add("timeline.delete-selected-clips-and-shift", ["<Shift>Delete"],
                               _("Delete selected clips and shift following ones"))

        self.group_action = Gio.SimpleAction.new("group-selected-clips", None)
        self.group_action.connect("activate", self._group_selected_cb)
        group.add_action(self.group_action)
        self.app.shortcuts.add("timeline.group-selected-clips", ["<Primary>g"],
                               _("Group selected clips together"))

        self.ungroup_action = Gio.SimpleAction.new("ungroup-selected-clips", None)
        self.ungroup_action.connect("activate", self._ungroup_selected_cb)
        group.add_action(self.ungroup_action)
        self.app.shortcuts.add("timeline.ungroup-selected-clips", ["<Primary><Shift>g"],
                               _("Ungroup selected clips"))

        self.copy_action = Gio.SimpleAction.new("copy-selected-clips", None)
        self.copy_action.connect("activate", self.__copyClipsCb)
        group.add_action(self.copy_action)
        self.app.shortcuts.add("timeline.copy-selected-clips", ["<Primary>c"],
                               _("Copy selected clips"))

        self.paste_action = Gio.SimpleAction.new("paste-clips", None)
        self.paste_action.connect("activate", self.__pasteClipsCb)
        group.add_action(self.paste_action)
        self.app.shortcuts.add("timeline.paste-clips", ["<Primary>v"],
                               _("Paste selected clips"))

        self.add_layer_action = Gio.SimpleAction.new("add-layer", None)
        self.add_layer_action.connect("activate", self.__add_layer_cb)
        group.add_action(self.add_layer_action)
        self.app.shortcuts.add("timeline.add-layer", ["<Primary>n"],
                               _("Add layer"))

        self.add_effect_action = Gio.SimpleAction.new("add-effect", None)
        self.add_effect_action.connect("activate", self.__add_effect_cb)
        group.add_action(self.add_effect_action)
        self.app.shortcuts.add("timeline.add-effect", ["<Primary>e"],
                               _("Add an effect to the selected clip"))

        if in_devel():
            self.gapless_action = Gio.SimpleAction.new("toggle-gapless-mode", None)
            self.gapless_action.connect("activate", self._gaplessmode_toggled_cb)
            group.add_action(self.gapless_action)

        # Playhead actions.
        self.split_action = Gio.SimpleAction.new("split-clips", None)
        self.split_action.connect("activate", self._splitCb)
        group.add_action(self.split_action)
        self.split_action.set_enabled(True)
        self.app.shortcuts.add("timeline.split-clips", ["s"],
                               _("Split the clip at the position"))

        self.keyframe_action = Gio.SimpleAction.new("keyframe-selected-clips", None)
        self.keyframe_action.connect("activate", self._keyframe_cb)
        group.add_action(self.keyframe_action)
        self.app.shortcuts.add("timeline.keyframe-selected-clips", ["k"],
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
                               _("Zoom in"))

        self.zoom_out_action = Gio.SimpleAction.new("zoom-out", None)
        self.zoom_out_action.connect("activate", self._zoom_out_cb)
        navigation_group.add_action(self.zoom_out_action)
        self.app.shortcuts.add("navigation.zoom-out", ["<Primary>minus", "<Primary>KP_Subtract"],
                               _("Zoom out"))

        self.zoom_fit_action = Gio.SimpleAction.new("zoom-fit", None)
        self.zoom_fit_action.connect("activate", self._zoom_fit_cb)
        navigation_group.add_action(self.zoom_fit_action)
        self.app.shortcuts.add("navigation.zoom-fit", ["<Primary>0", "<Primary>KP_0"],
                               _("Adjust zoom to fit the project to the window"))

        self.play_action = Gio.SimpleAction.new("play", None)
        self.play_action.connect("activate", self._playPauseCb)
        navigation_group.add_action(self.play_action)
        self.app.shortcuts.add("navigation.play", ["space"], _("Play"))

        self.backward_one_frame_action = Gio.SimpleAction.new("backward_one_frame", None)
        self.backward_one_frame_action.connect("activate", self._seek_backward_one_frame_cb)
        navigation_group.add_action(self.backward_one_frame_action)
        self.app.shortcuts.add("navigation.backward_one_frame", ["Left"],
                               _("Seek backward one frame"))

        self.forward_one_frame_action = Gio.SimpleAction.new("forward_one_frame", None)
        self.forward_one_frame_action.connect("activate", self._seek_forward_one_frame_cb)
        navigation_group.add_action(self.forward_one_frame_action)
        self.app.shortcuts.add("navigation.forward_one_frame", ["Right"],
                               _("Seek forward one frame"))

        self.backward_one_second_action = Gio.SimpleAction.new("backward_one_second", None)
        self.backward_one_second_action.connect("activate", self._seek_backward_one_second_cb)
        navigation_group.add_action(self.backward_one_second_action)
        self.app.shortcuts.add("navigation.backward_one_second",
                               ["<Shift>Left"],
                               _("Seek backward one second"))

        self.forward_one_second_action = Gio.SimpleAction.new("forward_one_second", None)
        self.forward_one_second_action.connect("activate", self._seek_forward_one_second_cb)
        navigation_group.add_action(self.forward_one_second_action)
        self.app.shortcuts.add("navigation.forward_one_second",
                               ["<Shift>Right"],
                               _("Seek forward one second"))

        self.updateActions()

    def _scrollToPixel(self, x):
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

        self.timeline.updatePosition()
        return False

    def _deleteSelected(self, unused_action, unused_parameter):
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

            self.timeline.selection.setSelection([], SELECT)

    def _delete_selected_and_shift(self, unused_action, unused_parameter):
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

            self.timeline.selection.setSelection([], SELECT)

    def _ungroup_selected_cb(self, unused_action, unused_parameter):
        if not self.ges_timeline:
            self.info("No ges_timeline set yet!")
            return

        with self.app.action_log.started("ungroup",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            toplevels = self.timeline.selection.toplevels
            for toplevel in toplevels:
                if isinstance(toplevel, GES.Group) or len(toplevels) == 1:
                    toplevel.ungroup(recursive=False)

        self.timeline.selection.setSelection([], SELECT)

    def _group_selected_cb(self, unused_action, unused_parameter):
        if not self.ges_timeline:
            self.info("No timeline set yet?")
            return

        with self.app.action_log.started("group",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            toplevels = self.timeline.selection.toplevels
            if toplevels:
                GES.Container.group(list(toplevels))

            # timeline.selection doesn't change during grouping,
            # we need to manually update group actions.
            self.timeline.selection.set_can_group_ungroup()
            self.updateActions()

    def __copyClipsCb(self, unused_action, unused_parameter):
        group = self.timeline.selection.group()
        try:
            self.__copied_group = group.copy(deep=True)
            self.__copied_group.props.serialize = False
        finally:
            group.ungroup(recursive=False)
        self.updateActions()

    def __pasteClipsCb(self, unused_action, unused_parameter):
        if not self.__copied_group:
            self.info("Nothing to paste.")
            return

        position = self._project.pipeline.getPosition()
        with self.app.action_log.started("paste",
                    finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                    toplevel=True):
            copied_group_shallow_copy = self.__copied_group.paste(position)
            if not copied_group_shallow_copy:
                self.info("The paste is not possible at position: %s", position)
                return

            try:
                self.__copied_group = copied_group_shallow_copy.copy(True)
                self.__copied_group.props.serialize = False
            finally:
                copied_group_shallow_copy.ungroup(recursive=False)

    def __add_layer_cb(self, unused_action, unused_parameter):
        with self.app.action_log.started("add layer",
                    finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                    toplevel=True):
            priority = len(self.ges_timeline.get_layers())
            self.timeline.create_layer(priority)

    def __add_effect_cb(self, unused_action, unused_parameter):
        clip = self.timeline.selection.getSingleClip()
        if clip:
            self.effects_popover.set_relative_to(clip.ui)
            self.effects_popover.popup()

    def _alignSelectedCb(self, unused_action, unused_parameter):
        if not self.ges_timeline:
            return

        progress_dialog = AlignmentProgressDialog(self.app)
        progress_dialog.window.show()
        self.app.action_log.begin("align", toplevel=True)

        def alignedCb():  # Called when alignment is complete
            self.app.action_log.commit()
            self._project.pipeline.commit_timeline()
            progress_dialog.window.destroy()

        auto_aligner = AutoAligner(self.timeline.selection, alignedCb)
        try:
            progress_meter = auto_aligner.start()
            progress_meter.addWatcher(progress_dialog.updatePosition)
        except Exception as e:
            self.error("Could not start the autoaligner: %s", e)
            progress_dialog.window.destroy()

    def _splitCb(self, unused_action, unused_parameter):
        """Splits clips.

        If clips are selected, split them at the current playhead position.
        Otherwise, split all clips at the playhead position.
        """
        with self.app.action_log.started("split clip", toplevel=True,
                    finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline)):
            self._splitElements(self.timeline.selection.selected)

    def _splitElements(self, clips=None):
        splitting_selection = clips is not None
        if clips is None:
            clips = []
            for layer in self.timeline.ges_timeline.get_layers():
                clips.extend(layer.get_clips())

        position = self._project.pipeline.getPosition()
        splitted = False

        with self._project.pipeline.commit_timeline_after():
            for clip in clips:
                start = clip.get_start()
                end = start + clip.get_duration()
                if start < position and end > position:
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
            self._splitElements()

    def _keyframe_cb(self, unused_action, unused_parameter):
        """Toggles a keyframe on the selected clip."""
        ges_clip = self.timeline.selection.getSingleClip(GES.Clip)
        if ges_clip is None:
            return

        ges_track_elements = ges_clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
        ges_track_elements += ges_clip.find_track_elements(None, GES.TrackType.AUDIO, GES.Source)

        offset = self._project.pipeline.getPosition() - ges_clip.props.start
        if offset <= 0 or offset >= ges_clip.props.duration:
            return
        offset += ges_clip.props.in_point

        with self.app.action_log.started("Toggle keyframe", toplevel=True):
            for ges_track_element in ges_track_elements:
                keyframe_curve = ges_track_element.ui.keyframe_curve
                keyframe_curve.toggle_keyframe(offset)

    def _playPauseCb(self, unused_action, unused_parameter):
        self._project.pipeline.togglePlayback()

    # Gtk widget virtual methods

    def do_key_press_event(self, event):
        # This is used both for changing the selection modes and for affecting
        # the seek keyboard shortcuts further below
        if event.keyval == Gdk.KEY_Shift_L:
            self._shiftMask = True
        elif event.keyval == Gdk.KEY_Control_L:
            self._controlMask = True

    def do_key_release_event(self, event):
        if event.keyval == Gdk.KEY_Shift_L:
            self._shiftMask = False
        elif event.keyval == Gdk.KEY_Control_L:
            self._controlMask = False

    def _seek_backward_one_second_cb(self, unused_action, unused_parameter):
        self._project.pipeline.seekRelative(0 - Gst.SECOND)
        self.timeline.scrollToPlayhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _seek_forward_one_second_cb(self, unused_action, unused_parameter):
        self._project.pipeline.seekRelative(Gst.SECOND)
        self.timeline.scrollToPlayhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _seek_backward_one_frame_cb(self, unused_action, unused_parameter):
        self._project.pipeline.stepFrame(self._framerate, -1)
        self.timeline.scrollToPlayhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def _seek_forward_one_frame_cb(self, unused_action, unused_parameter):
        self._project.pipeline.stepFrame(self._framerate, 1)
        self.timeline.scrollToPlayhead(align=Gtk.Align.CENTER, when_not_in_view=True)

    def do_focus_in_event(self, unused_event):
        self.log("Timeline has grabbed focus")
        self.updateActions()

    def do_focus_out_event(self, unused_event):
        self.log("Timeline has lost focus")
        self.updateActions()

    def _rendering_settings_changed_cb(self, project, item):
        """Handles Project metadata changes."""
        if item == "videorate" or item is None:
            self._update_ruler(project.videorate)

    def _update_ruler(self, videorate):
        self._framerate = videorate
        self.ruler.setProjectFrameRate(self._framerate)

    def __timeline_size_allocate_cb(self, unused_widget, allocation):
        fits = self.timeline.layout.props.height <= allocation.height
        self.vscrollbar.set_opacity(0 if fits else 1)

    def _zoom_in_cb(self, unused_action, unused_parameter):
        Zoomable.zoomIn()

    def _zoom_out_cb(self, unused_action, unused_parameter):
        Zoomable.zoomOut()

    def _zoom_fit_cb(self, unused_action, unused_parameter):
        self.app.write_action("zoom-fit", optional_action_type=True)

        self.timeline.set_best_zoom_ratio(allow_zoom_in=True)

    def __selection_changed_cb(self, unused_selection):
        """Handles selection changing."""
        self.updateActions()

    def _gaplessmode_toggled_cb(self, unused_action, unused_parameter):
        self._settings.timelineAutoRipple = self.gapless_button.get_active()
        self.info("Automatic ripple: %s", self._settings.timelineAutoRipple)
