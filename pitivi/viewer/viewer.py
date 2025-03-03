# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
import collections
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.pipeline import AssetPipeline
from pitivi.utils.ui import SPACING
from pitivi.utils.widgets import TimeWidget
from pitivi.viewer.guidelines import GuidelinesPopover
from pitivi.viewer.overlay_stack import OverlayStack
from pitivi.viewer.peak_meter import PEAK_METER_MAX_HEIGHT
from pitivi.viewer.peak_meter import PEAK_METER_MIN_HEIGHT
from pitivi.viewer.peak_meter import PeakMeter
from pitivi.viewer.peak_meter import PeakMeterScale


GlobalSettings.add_config_section("viewer")
GlobalSettings.add_config_option("viewerDocked", section="viewer",
                                 key="docked",
                                 default=True)
GlobalSettings.add_config_option("viewerWidth", section="viewer",
                                 key="width",
                                 default=320)
GlobalSettings.add_config_option("viewerHeight", section="viewer",
                                 key="height",
                                 default=240)
GlobalSettings.add_config_option("viewerX", section="viewer",
                                 key="x-pos",
                                 default=0)
GlobalSettings.add_config_option("viewerY", section="viewer",
                                 key="y-pos",
                                 default=0)
GlobalSettings.add_config_option("pointSize", section="viewer",
                                 key="point-size",
                                 default=25)
GlobalSettings.add_config_option("clickedPointColor", section="viewer",
                                 key="clicked-point-color",
                                 default='ffa854')
GlobalSettings.add_config_option("pointColor", section="viewer",
                                 key="point-color",
                                 default='49a0e0')


class ViewerContainer(Gtk.Box, Loggable):
    """Widget holding a viewer, the controls, and a peak meter.

    Attributes:
        pipeline (SimplePipeline): The displayed pipeline.
    """

    __gtype_name__ = 'ViewerContainer'
    __gsignals__ = {
        "activate-playback-controls": (GObject.SignalFlags.RUN_LAST,
                                       None, (GObject.TYPE_BOOLEAN,)),
    }

    INHIBIT_REASON = _("Currently playing")

    def __init__(self, app):
        Gtk.Box.__init__(self)
        self.app = app
        self.settings = app.settings

        Loggable.__init__(self)
        self.log("New ViewerContainer")

        self.project = None
        self.trim_pipeline = None
        self.trim_pipelines_cache = collections.OrderedDict()
        self.docked = True
        self.target = None

        self.overlay_stack = None
        self.guidelines_popover = None
        self._create_ui()
        self._create_actions()

        if not self.settings.viewerDocked:
            self.undock()

        self.__cursor = None
        self.__translation = None

        pm = self.app.project_manager
        pm.connect("project-closed", self._project_manager_project_closed_cb)

    def _project_manager_project_closed_cb(self, unused_project_manager, project):
        if self.project == project:
            project.disconnect_by_func(self._project_video_size_changed_cb)
            project.disconnect_by_func(self._project_audio_channels_changed_cb)
        self.project = None

    def _project_video_size_changed_cb(self, project):
        """Handles Project metadata changes."""
        self._reset_viewer_aspect_ratio(project)

    def _reset_viewer_aspect_ratio(self, project):
        """Resets the viewer aspect ratio."""
        self.target.update_aspect_ratio(project)
        self.timecode_entry.set_framerate(project.videorate)

    def _project_audio_channels_changed_cb(self, project):
        """Handles Project audio channels changes."""
        self.__update_peak_meters(project)

    def __update_peak_meters(self, project):
        for peak_meter in self.peak_meters:
            self.peak_meter_box.remove(peak_meter)

        for i in range(project.audiochannels):
            if i > len(self.peak_meters) - 1:
                new_peak_meter = PeakMeter()
                new_peak_meter.set_property("valign", Gtk.Align.FILL)
                new_peak_meter.set_property("halign", Gtk.Align.CENTER)
                new_peak_meter.set_margin_bottom(SPACING)
                new_peak_meter.set_margin_top(SPACING)
                self.peak_meters.append(new_peak_meter)
            self.peak_meter_box.pack_start(self.peak_meters[i], False, False, 0)

        self.peak_meter_box.show_all()

    def set_project(self, project):
        """Sets the displayed project.

        Args:
            project (Project): The Project to switch to.
        """
        self.debug("Setting project: %r", project)
        self._disconnect_from_pipeline()

        if self.target:
            parent = self.target.get_parent()
            if parent:
                parent.remove(self.target)

        project.pipeline.connect("state-change", self._pipeline_state_changed_cb)
        project.pipeline.connect("position", self._position_cb)
        project.pipeline.connect("duration-changed", self._duration_changed_cb)
        project.pipeline.get_bus().connect("message::element", self._bus_level_message_cb)
        self.project = project

        self.__update_peak_meters(project)
        self.__create_new_viewer()
        self._set_ui_active()

        # This must be done at the end, otherwise the created sink widget
        # appears in a separate window.
        project.pipeline.pause()

        project.connect("video-size-changed", self._project_video_size_changed_cb)
        project.connect("audio-channels-changed", self._project_audio_channels_changed_cb)

    def __create_new_viewer(self):

        self.guidelines_popover = GuidelinesPopover()
        self.guidelines_button.set_popover(self.guidelines_popover)
        video_sink, sink_widget = self.project.pipeline.create_sink()
        self.overlay_stack = OverlayStack(self.app,
                                          sink_widget,
                                          self.guidelines_popover.overlay)
        self.target = ViewerWidget(self.overlay_stack)
        self._reset_viewer_aspect_ratio(self.project)
        self.viewer_row_box.pack_start(self.target, expand=True, fill=True, padding=0)

        if self.docked:
            self.pack_start(self.viewer_row_box, expand=True, fill=True, padding=0)
        else:
            self.external_vbox.pack_start(self.viewer_row_box, expand=True, fill=False, padding=0)
            self.external_vbox.child_set(self.viewer_row_box, fill=True)

        self.viewer_row_box.show_all()

        self.project.pipeline.preview_set_video_sink(video_sink)

        # Wait for 1s to make sure that the viewer has completely realized
        # and then we can mark the resize status as showable.
        GLib.timeout_add(1000, self.__viewer_realization_done_cb, None)

    def _disconnect_from_pipeline(self):
        if self.project is None:
            return

        pipeline = self.project.pipeline
        self.debug("Disconnecting from: %r", pipeline)
        pipeline.disconnect_by_func(self._pipeline_state_changed_cb)
        pipeline.disconnect_by_func(self._position_cb)
        pipeline.disconnect_by_func(self._duration_changed_cb)

    def _set_ui_active(self, active=True):
        self.debug("active %r", active)
        for item in [self.start_button, self.back_button,
                     self.playpause_button, self.forward_button,
                     self.end_button, self.timecode_entry]:
            item.set_sensitive(active)
        if active:
            self.emit("activate-playback-controls", True)

    def _external_window_delete_cb(self, unused_window, unused_event):
        self.dock()
        return True

    def _external_window_configure_cb(self, unused_window, event):
        self.settings.viewerWidth = event.width
        self.settings.viewerHeight = event.height
        self.settings.viewerX = event.x
        self.settings.viewerY = event.y

    def _create_ui(self):
        """Creates the Viewer GUI."""
        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.external_window = Gtk.Window()
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        vbox.set_spacing(SPACING)
        self.external_window.add(vbox)
        self.external_window.connect(
            "delete-event", self._external_window_delete_cb)
        self.external_window.connect(
            "configure-event", self._external_window_configure_cb)
        self.external_vbox = vbox

        # This holds the viewer and the peak meters box.
        self.viewer_row_box = Gtk.Box()
        self.viewer_row_box.set_orientation(Gtk.Orientation.HORIZONTAL)

        # Corner marker.
        corner = Gtk.DrawingArea()
        # Number of lines to draw in the corner marker.
        lines = 3
        # Space between each line.
        space = 5
        # Margin from left and bottom of viewer container.
        margin = 2
        corner_size = space * lines + margin
        corner.set_size_request(corner_size, corner_size)
        corner.set_halign(Gtk.Align.START)
        corner.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                          Gdk.EventMask.BUTTON_PRESS_MASK |
                          Gdk.EventMask.BUTTON_RELEASE_MASK |
                          Gdk.EventMask.POINTER_MOTION_MASK)
        hpane = self.app.gui.editor.mainhpaned
        vpane = self.app.gui.editor.toplevel_widget
        corner.connect("draw", self.__corner_draw_cb, lines, space, margin)
        corner.connect("enter-notify-event", self.__corner_enter_notify_cb)
        corner.connect("button-press-event", self.__corner_button_press_cb, hpane, vpane)
        corner.connect("button-release-event", self.__corner_button_release_cb)
        corner.connect("motion-notify-event", self.__corner_motion_notify_cb, hpane, vpane)
        self.pack_end(corner, False, False, 0)

        # Peak Meters
        self.peak_meter_box = Gtk.Box()
        self.peak_meter_box.set_margin_end(SPACING)
        self.peak_meter_box.set_margin_start(SPACING)
        self.peak_meter_box.set_margin_bottom(SPACING)
        self.peak_meter_box.set_margin_top(SPACING)
        self.peak_meter_box.set_property("valign", Gtk.Align.CENTER)

        self.peak_meters = []

        # Peak Meter Scale
        self.peak_meter_scale = PeakMeterScale()
        self.peak_meter_scale.set_property("valign", Gtk.Align.FILL)
        self.peak_meter_scale.set_property("halign", Gtk.Align.CENTER)
        self.peak_meter_scale.set_margin_start(SPACING)
        self.peak_meter_box.pack_end(self.peak_meter_scale, False, False, 0)
        self.viewer_row_box.pack_end(self.peak_meter_box, False, False, 0)
        self.peak_meter_scale.connect("configure-event", self.__peak_meter_scale_configure_event_cb)

        # Buttons/Controls
        bbox = Gtk.Box()
        bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        bbox.set_property("valign", Gtk.Align.CENTER)
        bbox.set_property("halign", Gtk.Align.CENTER)
        bbox.set_margin_start(SPACING)
        bbox.set_margin_end(SPACING)
        self.pack_end(bbox, False, False, 0)

        self.guidelines_button = Gtk.MenuButton.new()
        self.guidelines_button.props.image = Gtk.Image.new_from_icon_name("view-grid-symbolic", Gtk.IconSize.BUTTON)
        self.guidelines_button.set_relief(Gtk.ReliefStyle.NONE)
        self.guidelines_button.set_tooltip_text(_("Select composition guidelines"))
        bbox.pack_start(self.guidelines_button, False, False, 0)

        self.start_button = Gtk.Button.new_from_icon_name("media-skip-backward-symbolic",
                                                          Gtk.IconSize.BUTTON)
        self.start_button.connect("clicked", self._start_button_clicked_cb)
        self.start_button.set_relief(Gtk.ReliefStyle.NONE)
        self.start_button.set_tooltip_text(
            _("Go to the beginning of the timeline"))
        self.start_button.set_sensitive(False)
        bbox.pack_start(self.start_button, False, False, 0)

        self.back_button = Gtk.Button.new_from_icon_name("media-seek-backward-symbolic",
                                                         Gtk.IconSize.BUTTON)

        self.back_button.set_relief(Gtk.ReliefStyle.NONE)
        self.back_button.connect("clicked", self._back_cb)
        self.back_button.set_tooltip_text(_("Go back one second"))
        self.back_button.set_sensitive(False)
        bbox.pack_start(self.back_button, False, False, 0)

        self.playpause_button = PlayPauseButton()
        self.playpause_button.connect("play", self._play_button_cb)
        bbox.pack_start(self.playpause_button, False, False, 0)
        self.playpause_button.set_sensitive(False)

        self.forward_button = Gtk.Button.new_from_icon_name("media-seek-forward-symbolic",
                                                            Gtk.IconSize.BUTTON)
        self.forward_button.set_relief(Gtk.ReliefStyle.NONE)
        self.forward_button.connect("clicked", self._forward_cb)
        self.forward_button.set_tooltip_text(_("Go forward one second"))
        self.forward_button.set_sensitive(False)
        bbox.pack_start(self.forward_button, False, False, 0)

        self.end_button = Gtk.Button.new_from_icon_name("media-skip-forward-symbolic",
                                                        Gtk.IconSize.BUTTON)
        self.end_button.set_relief(Gtk.ReliefStyle.NONE)
        self.end_button.connect("clicked", self._end_button_clicked_cb)
        self.end_button.set_tooltip_text(
            _("Go to the end of the timeline"))
        self.end_button.set_sensitive(False)
        bbox.pack_start(self.end_button, False, False, 0)

        self.timecode_entry = TimeWidget()
        self.timecode_entry.set_widget_value(0)
        self.timecode_entry.set_tooltip_text(
            _('Enter a timecode or frame number\nand press "Enter" to go to that position'))
        self.timecode_entry.connect_activate_event(self._entry_activate_cb)
        self.timecode_entry.connect("key_press_event", self._entry_key_press_event_cb)
        bbox.pack_start(self.timecode_entry, False, False, 15)

        self.undock_button = Gtk.Button.new_from_icon_name("view-restore-symbolic",
                                                           Gtk.IconSize.BUTTON)

        self.undock_button.set_relief(Gtk.ReliefStyle.NONE)
        self.undock_button.connect("clicked", self.undock_cb)
        self.undock_button.set_tooltip_text(
            _("Detach the viewer\nYou can re-attach it by closing the newly created window."))
        bbox.pack_start(self.undock_button, False, False, 0)

        self.show_all()

        # Create a hidden container for the clip trim preview video widget.
        self.hidden_chest = Gtk.Frame()
        # It has to be added to the window, otherwise when we add
        # a video widget to it, it will create a new window!
        self.pack_end(self.hidden_chest, False, False, 0)

        # Identify widgets for AT-SPI, making our test suite easier to develop
        # These will show up in sniff, accerciser, etc.
        self.start_button.get_accessible().set_name("start_button")
        self.back_button.get_accessible().set_name("back_button")
        self.playpause_button.get_accessible().set_name("playpause_button")
        self.forward_button.get_accessible().set_name("forward_button")
        self.end_button.get_accessible().set_name("end_button")
        self.timecode_entry.get_accessible().set_name("timecode_entry")
        self.undock_button.get_accessible().set_name("undock_button")

        self.buttons_container = bbox
        self.external_vbox.show_all()

    def _create_actions(self):
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("viewer", self.action_group)
        self.app.shortcuts.register_group("viewer", _("Viewer"), position=60)

        self.toggle_guidelines_action = Gio.SimpleAction.new("toggle-composition-guidelines", None)
        self.toggle_guidelines_action.connect("activate", self.__toggle_guidelines_cb)
        self.action_group.add_action(self.toggle_guidelines_action)
        self.app.shortcuts.add("viewer.toggle-composition-guidelines",
                               ["<Primary><Shift>c"],
                               self.toggle_guidelines_action,
                               _("Toggle the currently selected composition guidelines"))

        self.toggle_safe_areas_action = Gio.SimpleAction.new("toggle-safe-areas", None)
        self.toggle_safe_areas_action.connect("activate", self.__toggle_safe_areas_cb)
        self.action_group.add_action(self.toggle_safe_areas_action)
        self.app.shortcuts.add("viewer.toggle-safe-areas",
                               ["apostrophe"],
                               self.toggle_safe_areas_action,
                               _("Toggle safe areas on viewer"))

    def __toggle_guidelines_cb(self, unused_action, unused_parameter):
        self.guidelines_popover.toggle()

    def __toggle_safe_areas_cb(self, unused_action, unused_parameter):
        overlay = self.overlay_stack.safe_areas_overlay
        overlay.set_visible(not overlay.get_visible())

    def _bus_level_message_cb(self, unused_bus, message):
        peak_values = message.get_structure().get_value("peak")
        if peak_values:
            for count, peak in enumerate(peak_values):
                self.peak_meters[count].update_peakmeter(peak)

    def __corner_draw_cb(self, unused_widget, cr, lines, space, margin):
        cr.set_line_width(1)

        marker_color = self.app.gui.get_style_context().lookup_color("borders")
        cr.set_source_rgb(marker_color.color.red,
                          marker_color.color.green,
                          marker_color.color.blue)

        cr.translate(margin, 0)
        for i in range(lines):
            cr.move_to(0, space * i)
            cr.line_to(space * (lines - i), space * lines)
            cr.stroke()

    def __corner_enter_notify_cb(self, widget, unused_event):
        if not self.__cursor:
            self.__cursor = Gdk.Cursor.new(Gdk.CursorType.BOTTOM_LEFT_CORNER)
        widget.get_window().set_cursor(self.__cursor)

    def __corner_button_press_cb(self, unused_widget, event, hpane, vpane):
        if event.button == 1:
            # The mouse pointer position is w.r.t the root of the screen
            # whereas the positions of panes is w.r.t the root of the
            # mainwindow. We need to find the translation that takes us
            # from screen coordinate system to mainwindow coordinate system.
            self.__translation = (event.x_root - hpane.get_position(),
                                  event.y_root - vpane.get_position())

    def __corner_button_release_cb(self, unused_widget, unused_event):
        self.__translation = None

    def __corner_motion_notify_cb(self, unused_widget, event, hpane, vpane):
        if self.__translation is None:
            return

        hpane.set_position(event.x_root - self.__translation[0])
        vpane.set_position(event.y_root - self.__translation[1])

    def __peak_meter_scale_configure_event_cb(self, unused_widget, unused_event):
        container_height = self.viewer_row_box.get_allocated_height()
        margins = self.peak_meter_box.get_allocated_height() - self.peak_meter_scale.get_bar_height() + SPACING * 4

        bar_height = max(min(PEAK_METER_MAX_HEIGHT, container_height - margins), PEAK_METER_MIN_HEIGHT)
        box_height = bar_height + SPACING * 2

        self.peak_meter_box.set_property("height_request", box_height)

    def activate_compact_mode(self):
        self.back_button.hide()
        self.forward_button.hide()

    def _entry_activate_cb(self, unused_entry):
        nanoseconds = self.timecode_entry.get_widget_value()
        self.app.project_manager.current_project.pipeline.simple_seek(nanoseconds)
        self.app.gui.editor.timeline_ui.timeline.scroll_to_playhead(
            align=Gtk.Align.CENTER, when_not_in_view=True)

    def _entry_key_press_event_cb(self, widget, event):
        """Handles the key press events in the timecode_entry widget."""
        if event.keyval == Gdk.KEY_Escape:
            self.app.gui.editor.focus_timeline()

    # Active Timeline calllbacks
    def _duration_changed_cb(self, unused_pipeline, duration):
        self._set_ui_active(duration > 0)

    def _play_button_cb(self, unused_button, unused_playing):
        self.app.project_manager.current_project.pipeline.toggle_playback()
        self.app.gui.editor.focus_timeline()

    def _start_button_clicked_cb(self, unused_button):
        self.app.project_manager.current_project.pipeline.simple_seek(0)
        self.app.gui.editor.focus_timeline()
        self.app.gui.editor.timeline_ui.timeline.scroll_to_playhead(
            align=Gtk.Align.START, when_not_in_view=True)

    def _back_cb(self, unused_button):
        # Seek backwards one second
        self.app.project_manager.current_project.pipeline.seek_relative(0 - Gst.SECOND)
        self.app.gui.editor.focus_timeline()
        self.app.gui.editor.timeline_ui.timeline.scroll_to_playhead(
            align=Gtk.Align.END, when_not_in_view=True)

    def _forward_cb(self, unused_button):
        # Seek forward one second
        self.app.project_manager.current_project.pipeline.seek_relative(Gst.SECOND)
        self.app.gui.editor.focus_timeline()
        self.app.gui.editor.timeline_ui.timeline.scroll_to_playhead(
            align=Gtk.Align.START, when_not_in_view=True)

    def _end_button_clicked_cb(self, unused_button):
        end = self.app.project_manager.current_project.pipeline.get_duration()
        self.app.project_manager.current_project.pipeline.simple_seek(end)
        self.app.gui.editor.focus_timeline()
        self.app.gui.editor.timeline_ui.timeline.scroll_to_playhead(
            align=Gtk.Align.CENTER, when_not_in_view=True)

    def undock_cb(self, unused_widget):
        self.undock()

    # Public methods for controlling playback

    def undock(self):
        if not self.docked:
            self.warning("The viewer is already undocked")
            return

        self.docked = False
        self.settings.viewerDocked = False
        self.remove(self.buttons_container)
        position = None
        if self.project:
            self.overlay_stack.enable_resize_status(False)
            position = self.project.pipeline.get_position()
            self.project.pipeline.set_simple_state(Gst.State.NULL)
            self.remove(self.viewer_row_box)
            self.viewer_row_box.remove(self.target)
            self.__create_new_viewer()
        self.buttons_container.set_margin_bottom(SPACING)
        self.external_vbox.pack_end(self.buttons_container, False, False, 0)

        self.undock_button.hide()
        self.fullscreen_button = Gtk.ToggleButton()
        fullscreen_image = Gtk.Image.new_from_icon_name(
            "view-fullscreen-symbolic", Gtk.IconSize.BUTTON)
        self.fullscreen_button.set_image(fullscreen_image)
        self.fullscreen_button.set_tooltip_text(
            _("Show this window in fullscreen"))
        self.fullscreen_button.set_relief(Gtk.ReliefStyle.NONE)
        self.buttons_container.pack_end(
            self.fullscreen_button, expand=False, fill=False, padding=6)
        self.fullscreen_button.show()
        self.fullscreen_button.connect("toggled", self._toggle_fullscreen_cb)

        self.external_window.show()
        self.hide()
        self.external_window.move(self.settings.viewerX, self.settings.viewerY)
        self.external_window.resize(
            self.settings.viewerWidth, self.settings.viewerHeight)
        if self.project:
            self.project.pipeline.pause()
            self.project.pipeline.simple_seek(position)

    def __viewer_realization_done_cb(self, unused_data):
        self.overlay_stack.enable_resize_status(True)
        return False

    def dock(self):
        if self.docked:
            self.warning("The viewer is already docked")
            return

        self.docked = True
        self.settings.viewerDocked = True

        position = None
        if self.project:
            self.overlay_stack.enable_resize_status(False)
            position = self.project.pipeline.get_position()
            self.project.pipeline.set_simple_state(Gst.State.NULL)
            self.external_vbox.remove(self.viewer_row_box)
            self.viewer_row_box.remove(self.target)
            self.__create_new_viewer()

        self.undock_button.show()
        self.fullscreen_button.destroy()
        self.external_vbox.remove(self.buttons_container)
        self.buttons_container.set_margin_bottom(0)
        self.pack_end(self.buttons_container, False, False, 0)
        self.show()

        self.external_window.hide()
        if self.project.pipeline:
            self.project.pipeline.pause()
            self.project.pipeline.simple_seek(position)

    def _toggle_fullscreen_cb(self, widget):
        if widget.get_active():
            self.external_window.hide()
            # GTK doesn't let us fullscreen utility windows
            self.external_window.set_type_hint(Gdk.WindowTypeHint.NORMAL)
            self.external_window.show()
            self.external_window.fullscreen()
            widget.set_tooltip_text(_("Exit fullscreen mode"))
        else:
            self.external_window.unfullscreen()
            widget.set_tooltip_text(_("Show this window in fullscreen"))
            self.external_window.hide()
            self.external_window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            self.external_window.show()

    def _position_cb(self, unused_pipeline, position):
        """Updates the viewer UI widgets if the timeline position changed.

        This is meant to be called either by the gobject timer when playing,
        or by mainwindow's _timelineSeekCb when the timer is disabled.
        """
        self.timecode_entry.set_widget_value(position, False)

    def clip_trim_preview(self, clip, position):
        """Shows a live preview of a clip being trimmed."""
        if not hasattr(clip, "get_uri") or isinstance(clip, GES.TitleClip) or clip.props.is_image:
            self.log("Not previewing trim for image or title clip: %s", clip)
            return

        if self.project.pipeline.get_simple_state() == Gst.State.PLAYING:
            self.project.pipeline.set_simple_state(Gst.State.PAUSED)

        uri = clip.props.uri
        if self.trim_pipeline and uri != self.trim_pipeline.uri:
            # Seems to be the trim preview pipeline for a different clip.
            self.trim_pipeline.release()
            self.trim_pipeline = None

        if not self.trim_pipeline:
            self.trim_pipeline, sink_widget = self.get_trim_preview_pipeline(uri)
            # Add the widget to a hidden container and make it appear later
            # when it's ready. If we show it before the initial seek completion,
            # there is a flicker when the first frame of the asset is shown for
            # a brief moment until the initial seek to the frame we actually
            # want to show is performed.
            # First make sure the container itself is ready.
            widget = self.hidden_chest.get_child()
            if widget:
                self.warning("The previous trim preview video widget should have been removed already")
                self.hidden_chest.remove(widget)
            self.hidden_chest.add(sink_widget)
            sink_widget.show()
            self.trim_pipeline.connect("state-change", self._state_change_cb)
            self.trim_pipeline.set_simple_state(Gst.State.PAUSED)

        self.trim_pipeline.simple_seek(position)

    def get_trim_preview_pipeline(self, uri):
        try:
            trim_pipeline, sink_widget = self.trim_pipelines_cache[uri]
            self.debug("Reusing temporary pipeline for clip %s", uri)
        except KeyError:
            self.debug("Creating temporary pipeline for clip %s", uri)
            trim_pipeline = AssetPipeline(uri)
            unused_video_sink, sink_widget = trim_pipeline.create_sink()
        self.trim_pipelines_cache[uri] = trim_pipeline, sink_widget
        if len(self.trim_pipelines_cache) > 4:
            # Pop the first inserted item.
            expired_uri, (expired_pipeline, unused_expired_widget) = self.trim_pipelines_cache.popitem(last=False)
            self.debug("Releasing temporary pipeline for clip %s", expired_uri)
            expired_pipeline.release()
        return trim_pipeline, sink_widget

    def _state_change_cb(self, trim_pipeline, state, prev_state):
        if self.trim_pipeline is not trim_pipeline:
            self.warning("State change reported for previous trim preview pipeline")
            trim_pipeline.disconnect_by_func(self._state_change_cb)
            return

        # First the pipeline goes from READY to PAUSED, and then it goes
        # from PAUSED to PAUSED, and this is a good moment.
        if prev_state == Gst.State.PAUSED and state == Gst.State.PAUSED:
            sink_widget = self.hidden_chest.get_child()
            if sink_widget:
                self.hidden_chest.remove(sink_widget)
                self.target.switch_widget(sink_widget)
            trim_pipeline.disconnect_by_func(self._state_change_cb)

    def clip_trim_preview_finished(self):
        """Switches back to the project pipeline following a clip trimming."""
        if not self.trim_pipeline:
            return
        self.target.switch_widget(self.overlay_stack)
        self.trim_pipeline = None

    def _pipeline_state_changed_cb(self, pipeline, state, old_state):
        """Updates the widgets when the playback starts or stops."""
        if state == Gst.State.PLAYING:
            st = Gst.Structure.new_empty("play")
            self.app.write_action(st)
            self.playpause_button.set_pause()
            self.app.simple_inhibit(ViewerContainer.INHIBIT_REASON,
                                    Gtk.ApplicationInhibitFlags.IDLE)
            self.overlay_stack.hide_overlays()
        else:
            if state == Gst.State.PAUSED:
                if old_state != Gst.State.PAUSED:
                    st = Gst.Structure.new_empty("pause")
                    if old_state == Gst.State.PLAYING:
                        position_seconds = pipeline.get_position() / Gst.SECOND
                        st.set_value("playback_time", position_seconds)
                    self.app.write_action(st)

                self.playpause_button.set_play()
            self.overlay_stack.show_overlays()
            self.app.simple_uninhibit(ViewerContainer.INHIBIT_REASON)


class ViewerWidget(Gtk.AspectFrame, Loggable):
    """Container responsible with enforcing the aspect ratio.

    Args:
        video_widget (Gtk.Widget): The child widget doing the real work.
            Can be an OverlayStack or a sink widget.
    """

    def __init__(self, video_widget):
        Gtk.AspectFrame.__init__(self, xalign=0.5, yalign=0.5, ratio=4 / 3,
                                 border_width=SPACING, obey_child=False)
        Loggable.__init__(self)

        # The width and height used when snapping the child widget size.
        self.videowidth = 0
        self.videoheight = 0
        # Sequence of floats representing sizes where the viewer size snaps.
        # The project natural video size is 1, double size is 2, etc.
        self.snaps = []

        # Set the shadow to None, otherwise it will take space and the
        # child widget size snapping will be a bit off.
        self.set_shadow_type(Gtk.ShadowType.NONE)

        self.add(video_widget)

        # We keep the ViewerWidget hidden initially, or the desktop wallpaper
        # would show through the non-double-buffered widget!
        self.hide()

    def switch_widget(self, widget):
        child = self.get_child()
        if child:
            self.remove(child)
        self.add(widget)

    def update_aspect_ratio(self, project):
        """Forces the DAR of the project on the child widget."""
        ratio_fraction = project.get_dar()
        self.debug("Updating aspect ratio to %r", ratio_fraction)
        self.props.ratio = float(ratio_fraction)

        self.videowidth = project.videowidth
        self.videoheight = project.videoheight

        self.snaps = []
        for divisor in (16, 8, 4, 2):
            if self.videowidth % divisor == 0 and self.videoheight % divisor == 0:
                self.snaps.append(1 / divisor)
        self.snaps += list(range(1, 10))

    def do_get_preferred_width(self):
        minimum, unused_natural = Gtk.AspectFrame.do_get_preferred_width(self)
        # Do not let a chance for Gtk to choose video natural size
        # as we want to have full control
        return minimum, minimum + 1

    def do_get_preferred_height(self):
        minimum, unused_natural = Gtk.AspectFrame.do_get_preferred_height(self)
        # Do not let a chance for Gtk to choose video natural size
        # as we want to have full control
        return minimum, minimum + 1

    def do_compute_child_allocation(self, allocation):
        """Snaps the size of the child depending on the project size."""
        # Start with the max possible allocation.
        Gtk.AspectFrame.do_compute_child_allocation(self, allocation)

        if not self.videowidth:
            return

        # Calculate the current scale of the displayed video
        # using width or height, whichever gives a higher precision.
        if self.videowidth > self.videoheight:
            current_scale = allocation.width / self.videowidth
        else:
            current_scale = allocation.height / self.videoheight

        # See if we want to snap the size of the child widget.
        snap = 0
        for scale in self.snaps:
            if scale < current_scale < scale + 0.05:
                snap = scale
                break
            if current_scale < scale:
                break
        if snap:
            allocation.width = self.videowidth * snap
            allocation.height = self.videoheight * snap
            full = self.get_allocation()
            allocation.x = full.x + self.props.xalign * (full.width - allocation.width)
            allocation.y = full.y + self.props.yalign * (full.height - allocation.height)


class PlayPauseButton(Gtk.Button, Loggable):
    """Double state Gtk.Button which displays play/pause."""

    __gsignals__ = {
        "play": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_BOOLEAN,))
    }

    def __init__(self):
        Gtk.Button.__init__(self)
        Loggable.__init__(self)
        self.image = Gtk.Image()
        self.add(self.image)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.playing = False
        self.set_play()

    def set_sensitive(self, value):
        Gtk.Button.set_sensitive(self, value)

    def do_clicked(self):
        """Handles the click events to toggle playback."""
        self.playing = not self.playing
        self.emit("play", self.playing)

    def set_play(self):
        self.log("Displaying the play image")
        self.playing = True
        self.set_image(Gtk.Image.new_from_icon_name(
            "media-playback-start-symbolic", Gtk.IconSize.BUTTON))
        self.set_tooltip_text(_("Play"))
        self.playing = False

    def set_pause(self):
        self.log("Displaying the pause image")
        self.playing = False
        self.set_image(Gtk.Image.new_from_icon_name(
            "media-playback-pause-symbolic", Gtk.IconSize.BUTTON))
        self.set_tooltip_text(_("Pause"))
        self.playing = True
