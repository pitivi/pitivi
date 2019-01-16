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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import time
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.pipeline import AssetPipeline
from pitivi.utils.ui import SPACING
from pitivi.utils.widgets import TimeWidget
from pitivi.viewer.overlay_stack import OverlayStack

GlobalSettings.addConfigSection("viewer")
GlobalSettings.addConfigOption("viewerDocked", section="viewer",
                               key="docked",
                               default=True)
GlobalSettings.addConfigOption("viewerWidth", section="viewer",
                               key="width",
                               default=320)
GlobalSettings.addConfigOption("viewerHeight", section="viewer",
                               key="height",
                               default=240)
GlobalSettings.addConfigOption("viewerX", section="viewer",
                               key="x-pos",
                               default=0)
GlobalSettings.addConfigOption("viewerY", section="viewer",
                               key="y-pos",
                               default=0)
GlobalSettings.addConfigOption("pointSize", section="viewer",
                               key="point-size",
                               default=25)
GlobalSettings.addConfigOption("clickedPointColor", section="viewer",
                               key="clicked-point-color",
                               default='ffa854')
GlobalSettings.addConfigOption("pointColor", section="viewer",
                               key="point-color",
                               default='49a0e0')


# The trim preview is updated at most once per this interval.
TRIM_PREVIEW_UPDATE_INTERVAL_MS = 200


class ViewerContainer(Gtk.Box, Loggable):
    """Wiget holding a viewer and the controls.

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
        self.docked = True
        self.target = None
        self._compactMode = False

        # When was the last seek performed while previewing a clip trim.
        self._last_trim_ns = 0
        # The delayed seek timeout ID, in case the last seek is too recent.
        self.__trim_seek_id = 0

        self._haveUI = False

        self._createUi()

        if not self.settings.viewerDocked:
            self.undock()

        self.__cursor = None
        self.__translation = None

        pm = self.app.project_manager
        pm.connect("new-project-loaded", self._project_manager_new_project_loaded_cb)
        pm.connect("project-closed", self._projectManagerProjectClosedCb)

    def _project_manager_new_project_loaded_cb(self, unused_project_manager, project):
        project.connect("rendering-settings-changed",
                        self._project_rendering_settings_changed_cb)
        self.set_project(project)

    def _projectManagerProjectClosedCb(self, unused_project_manager, project):
        self.project = None
        project.disconnect_by_func(self._project_rendering_settings_changed_cb)

    def _project_rendering_settings_changed_cb(self, project, unused_item):
        """Handles Project metadata changes."""
        self._reset_viewer_aspect_ratio(project)

    def _reset_viewer_aspect_ratio(self, project):
        """Resets the viewer aspect ratio."""
        self.target.update_aspect_ratio(project)
        self.timecode_entry.setFramerate(project.videorate)

    def set_project(self, project):
        """Sets the displayed project.

        Args:
            project (Project): The Project to switch to.
        """
        self.debug("Setting project: %r", project)
        self._disconnectFromPipeline()

        if self.target:
            parent = self.target.get_parent()
            if parent:
                parent.remove(self.target)

        project.pipeline.connect("state-change", self._pipelineStateChangedCb)
        project.pipeline.connect("position", self._positionCb)
        project.pipeline.connect("duration-changed", self._durationChangedCb)
        self.project = project

        self.__createNewViewer()
        self._setUiActive()

        # This must be done at the end, otherwise the created sink widget
        # appears in a separate window.
        project.pipeline.pause()

    def __createNewViewer(self):
        _, sink_widget = self.project.pipeline.create_sink()

        self.overlay_stack = OverlayStack(self.app, sink_widget)
        self.target = ViewerWidget(self.overlay_stack)
        self._reset_viewer_aspect_ratio(self.project)

        if self.docked:
            self.pack_start(self.target, expand=True, fill=True, padding=0)
        else:
            self.external_vbox.pack_start(self.target, expand=True, fill=False, padding=0)
            self.external_vbox.child_set(self.target, fill=True)

        self.target.show_all()

        # Wait for 1s to make sure that the viewer has completely realized
        # and then we can mark the resize status as showable.
        GLib.timeout_add(1000, self.__viewer_realization_done_cb, None)

    def _disconnectFromPipeline(self):
        if self.project is None:
            return

        pipeline = self.project.pipeline
        self.debug("Disconnecting from: %r", pipeline)
        pipeline.disconnect_by_func(self._pipelineStateChangedCb)
        pipeline.disconnect_by_func(self._positionCb)
        pipeline.disconnect_by_func(self._durationChangedCb)

    def _setUiActive(self, active=True):
        self.debug("active %r", active)
        if self._haveUI:
            for item in [self.goToStart_button, self.back_button,
                         self.playpause_button, self.forward_button,
                         self.goToEnd_button, self.timecode_entry]:
                item.set_sensitive(active)
        if active:
            self.emit("activate-playback-controls", True)

    def _externalWindowDeleteCb(self, unused_window, unused_event):
        self.dock()
        return True

    def _externalWindowConfigureCb(self, unused_window, event):
        self.settings.viewerWidth = event.width
        self.settings.viewerHeight = event.height
        self.settings.viewerX = event.x
        self.settings.viewerY = event.y

    def _createUi(self):
        """Creates the Viewer GUI."""
        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.external_window = Gtk.Window()
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        vbox.set_spacing(SPACING)
        self.external_window.add(vbox)
        self.external_window.connect(
            "delete-event", self._externalWindowDeleteCb)
        self.external_window.connect(
            "configure-event", self._externalWindowConfigureCb)
        self.external_vbox = vbox

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

        # Buttons/Controls
        bbox = Gtk.Box()
        bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        bbox.set_property("valign", Gtk.Align.CENTER)
        bbox.set_property("halign", Gtk.Align.CENTER)
        bbox.set_margin_left(SPACING)
        bbox.set_margin_right(SPACING)
        self.pack_end(bbox, False, False, 0)

        self.goToStart_button = Gtk.ToolButton()
        self.goToStart_button.set_icon_name("media-skip-backward")
        self.goToStart_button.connect("clicked", self._goToStartCb)
        self.goToStart_button.set_tooltip_text(
            _("Go to the beginning of the timeline"))
        self.goToStart_button.set_sensitive(False)
        bbox.pack_start(self.goToStart_button, False, False, 0)

        self.back_button = Gtk.ToolButton()
        self.back_button.set_icon_name("media-seek-backward")
        self.back_button.connect("clicked", self._backCb)
        self.back_button.set_tooltip_text(_("Go back one second"))
        self.back_button.set_sensitive(False)
        bbox.pack_start(self.back_button, False, False, 0)

        self.playpause_button = PlayPauseButton()
        self.playpause_button.connect("play", self._playButtonCb)
        bbox.pack_start(self.playpause_button, False, False, 0)
        self.playpause_button.set_sensitive(False)

        self.forward_button = Gtk.ToolButton()
        self.forward_button.set_icon_name("media-seek-forward")
        self.forward_button.connect("clicked", self._forwardCb)
        self.forward_button.set_tooltip_text(_("Go forward one second"))
        self.forward_button.set_sensitive(False)
        bbox.pack_start(self.forward_button, False, False, 0)

        self.goToEnd_button = Gtk.ToolButton()
        self.goToEnd_button.set_icon_name("media-skip-forward")
        self.goToEnd_button.connect("clicked", self._goToEndCb)
        self.goToEnd_button.set_tooltip_text(
            _("Go to the end of the timeline"))
        self.goToEnd_button.set_sensitive(False)
        bbox.pack_start(self.goToEnd_button, False, False, 0)

        self.timecode_entry = TimeWidget()
        self.timecode_entry.setWidgetValue(0)
        self.timecode_entry.set_tooltip_text(
            _('Enter a timecode or frame number\nand press "Enter" to go to that position'))
        self.timecode_entry.connectActivateEvent(self._entryActivateCb)
        self.timecode_entry.connect("key_press_event", self._entry_key_press_event_cb)
        bbox.pack_start(self.timecode_entry, False, 10, 0)

        self.undock_button = Gtk.ToolButton()
        self.undock_button.set_icon_name("view-restore")
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

        self._haveUI = True

        # Identify widgets for AT-SPI, making our test suite easier to develop
        # These will show up in sniff, accerciser, etc.
        self.goToStart_button.get_accessible().set_name("goToStart_button")
        self.back_button.get_accessible().set_name("back_button")
        self.playpause_button.get_accessible().set_name("playpause_button")
        self.forward_button.get_accessible().set_name("forward_button")
        self.goToEnd_button.get_accessible().set_name("goToEnd_button")
        self.timecode_entry.get_accessible().set_name("timecode_entry")
        self.undock_button.get_accessible().set_name("undock_button")

        self.buttons_container = bbox
        self.external_vbox.show_all()

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

    def activateCompactMode(self):
        self.back_button.hide()
        self.forward_button.hide()
        self._compactMode = True  # Prevent set_size_request later

    def _entryActivateCb(self, unused_entry):
        nanoseconds = self.timecode_entry.getWidgetValue()
        self.app.project_manager.current_project.pipeline.simple_seek(nanoseconds)
        self.app.gui.editor.timeline_ui.timeline.scrollToPlayhead(
            align=Gtk.Align.CENTER, when_not_in_view=True)

    def _entry_key_press_event_cb(self, widget, event):
        """Handles the key press events in the timecode_entry widget."""
        if event.keyval == Gdk.KEY_Escape:
            self.app.gui.editor.focusTimeline()

    # Active Timeline calllbacks
    def _durationChangedCb(self, unused_pipeline, duration):
        self._setUiActive(duration > 0)

    def _playButtonCb(self, unused_button, unused_playing):
        self.app.project_manager.current_project.pipeline.togglePlayback()
        self.app.gui.editor.focusTimeline()

    def _goToStartCb(self, unused_button):
        self.app.project_manager.current_project.pipeline.simple_seek(0)
        self.app.gui.editor.focusTimeline()
        self.app.gui.editor.timeline_ui.timeline.scrollToPlayhead(
            align=Gtk.Align.START, when_not_in_view=True)

    def _backCb(self, unused_button):
        # Seek backwards one second
        self.app.project_manager.current_project.pipeline.seekRelative(0 - Gst.SECOND)
        self.app.gui.editor.focusTimeline()
        self.app.gui.editor.timeline_ui.timeline.scrollToPlayhead(
            align=Gtk.Align.END, when_not_in_view=True)

    def _forwardCb(self, unused_button):
        # Seek forward one second
        self.app.project_manager.current_project.pipeline.seekRelative(Gst.SECOND)
        self.app.gui.editor.focusTimeline()
        self.app.gui.editor.timeline_ui.timeline.scrollToPlayhead(
            align=Gtk.Align.START, when_not_in_view=True)

    def _goToEndCb(self, unused_button):
        end = self.app.project_manager.current_project.pipeline.getDuration()
        self.app.project_manager.current_project.pipeline.simple_seek(end)
        self.app.gui.editor.focusTimeline()
        self.app.gui.editor.timeline_ui.timeline.scrollToPlayhead(
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
            position = self.project.pipeline.getPosition()
            self.project.pipeline.setState(Gst.State.NULL)
            self.remove(self.target)
            self.__createNewViewer()
        self.buttons_container.set_margin_bottom(SPACING)
        self.external_vbox.pack_end(self.buttons_container, False, False, 0)

        self.undock_button.hide()
        self.fullscreen_button = Gtk.ToggleToolButton()
        self.fullscreen_button.set_icon_name("view-fullscreen")
        self.fullscreen_button.set_tooltip_text(
            _("Show this window in fullscreen"))
        self.buttons_container.pack_end(
            self.fullscreen_button, expand=False, fill=False, padding=6)
        self.fullscreen_button.show()
        self.fullscreen_button.connect("toggled", self._toggleFullscreen)

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
            position = self.project.pipeline.getPosition()
            self.project.pipeline.setState(Gst.State.NULL)
            self.external_vbox.remove(self.target)
            self.__createNewViewer()

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

    def _toggleFullscreen(self, widget):
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

    def _positionCb(self, unused_pipeline, position):
        """Updates the viewer UI widgets if the timeline position changed.

        This is meant to be called either by the gobject timer when playing,
        or by mainwindow's _timelineSeekCb when the timer is disabled.
        """
        self.timecode_entry.setWidgetValue(position, False)

    def clipTrimPreview(self, clip, position):
        """Shows a live preview of a clip being trimmed."""
        if not hasattr(clip, "get_uri") or isinstance(clip, GES.TitleClip) or clip.props.is_image:
            self.log("Not previewing trim for image or title clip: %s", clip)
            return False

        if self.project.pipeline.getState() == Gst.State.PLAYING:
            self.project.pipeline.setState(Gst.State.PAUSED)

        if self.trim_pipeline and clip is not self.trim_pipeline.clip:
            # Seems to be the trim preview pipeline for a different clip.
            self.trim_pipeline.release()
            self.trim_pipeline = None

        if not self.trim_pipeline:
            self.debug("Creating temporary pipeline for clip %s", clip.props.uri)
            self.trim_pipeline = AssetPipeline(clip)
            unused_video_sink, sink_widget = self.trim_pipeline.create_sink()
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
            self.trim_pipeline.setState(Gst.State.PAUSED)
            self._last_trim_ns = 0

        if self.__trim_seek_id:
            # A seek is scheduled. Update the position where it will be done.
            self.__trim_seek_position = position
        else:
            # Avoid seeking too often, for performance.
            time_ns = time.monotonic_ns()
            delta_ns = time_ns - self._last_trim_ns
            if delta_ns > TRIM_PREVIEW_UPDATE_INTERVAL_MS * 1000 * 1000:
                # The last seek is not recent, we can seek right away.
                self.trim_pipeline.simple_seek(position)
                self._last_trim_ns = time_ns
            else:
                # The previous seek was too recent. Schedule a seek at this position.
                self.__trim_seek_position = position
                self.__trim_seek_id = GLib.timeout_add(delta_ns / 1000 / 1000,
                                                       self.__trim_seek_timeout_cb, None)

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

    def __trim_seek_timeout_cb(self, unused_data):
        self.__trim_seek_id = 0
        self.trim_pipeline.simple_seek(self.__trim_seek_position)
        self._last_trim_ns = time.monotonic_ns()
        return False

    def clipTrimPreviewFinished(self):
        """Switches back to the project pipeline following a clip trimming."""
        if self.__trim_seek_id:
            GLib.source_remove(self.__trim_seek_id)
            self.__trim_seek_id = 0
        if not self.trim_pipeline:
            return
        self.target.switch_widget(self.overlay_stack)
        self.trim_pipeline.release()
        self.trim_pipeline = None

    def _pipelineStateChangedCb(self, pipeline, state, old_state):
        """Updates the widgets when the playback starts or stops."""
        if state == Gst.State.PLAYING:
            st = Gst.Structure.new_empty("play")
            self.app.write_action(st)
            self.playpause_button.setPause()
            self.app.simple_inhibit(ViewerContainer.INHIBIT_REASON,
                                    Gtk.ApplicationInhibitFlags.IDLE)
            self.overlay_stack.hide_overlays()
        else:
            if state == Gst.State.PAUSED:
                if old_state != Gst.State.PAUSED:
                    st = Gst.Structure.new_empty("pause")
                    if old_state == Gst.State.PLAYING:
                        position_seconds = pipeline.getPosition() / Gst.SECOND
                        st.set_value("playback_time", position_seconds)
                    self.app.write_action(st)

                self.playpause_button.setPlay()
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
        ratio_fraction = project.getDAR()
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
        self.playing = False
        self.setPlay()

    def set_sensitive(self, value):
        Gtk.Button.set_sensitive(self, value)

    def do_clicked(self):
        """Handles the click events to toggle playback."""
        self.playing = not self.playing
        self.emit("play", self.playing)

    def setPlay(self):
        self.log("Displaying the play image")
        self.playing = True
        self.set_image(Gtk.Image.new_from_icon_name(
            "media-playback-start", Gtk.IconSize.BUTTON))
        self.set_tooltip_text(_("Play"))
        self.playing = False

    def setPause(self):
        self.log("Displaying the pause image")
        self.playing = False
        self.set_image(Gtk.Image.new_from_icon_name(
            "media-playback-pause", Gtk.IconSize.BUTTON))
        self.set_tooltip_text(_("Pause"))
        self.playing = True
