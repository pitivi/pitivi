# Pitivi video editor
#
#       pitivi/viewer.py
#
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

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import GObject
from gi.repository import GES

from gettext import gettext as _
from time import time

from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import format_ns
from pitivi.utils.pipeline import AssetPipeline, Seeker
from pitivi.utils.ui import SPACING
from pitivi.utils.widgets import TimeWidget

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


class ViewerContainer(Gtk.Box, Loggable):

    """
    A wiget holding a viewer and the controls.
    """
    __gtype_name__ = 'ViewerContainer'
    __gsignals__ = {
        "activate-playback-controls": (GObject.SignalFlags.RUN_LAST,
                                       None, (GObject.TYPE_BOOLEAN,)),
    }

    INHIBIT_REASON = _("Currently playing")

    def __init__(self, app):
        Gtk.Box.__init__(self)
        self.set_border_width(SPACING)
        self.app = app
        self.settings = app.settings
        self.system = app.system

        Loggable.__init__(self)
        self.log("New ViewerContainer")

        self.pipeline = None
        self.docked = True
        self.seeker = Seeker()
        self.target = None

        # Only used for restoring the pipeline position after a live clip trim
        # preview:
        self._oldTimelinePos = None

        self._haveUI = False

        self._createUi()

        self.__owning_pipeline = False
        if not self.settings.viewerDocked:
            self.undock()

    def setPipeline(self, pipeline, position=None):
        """
        Set the Viewer to the given Pipeline.

        Properly switches the currently set action to that new Pipeline.

        @param pipeline: The Pipeline to switch to.
        @type pipeline: L{Pipeline}.
        @param position: Optional position to seek to initially.
        """
        self._disconnectFromPipeline()

        if self.target:
            parent = self.target.get_parent()
            if parent:
                parent.remove(self.target)

        self.debug("New pipeline: %r", pipeline)
        self.pipeline = pipeline
        if position:
            self.seeker.seek(position)

        self.pipeline.connect("state-change", self._pipelineStateChangedCb)
        self.pipeline.connect("position", self._positionCb)
        self.pipeline.connect("duration-changed", self._durationChangedCb)

        self.__owning_pipeline = False
        self.__createNewViewer()
        self._setUiActive()

        self.pipeline.pause()

    def __createNewViewer(self):
        self.sink = Gst.ElementFactory.make("glsinkbin", None)
        self.sink.props.sink = Gst.ElementFactory.make("gtkglsink", None)
        self.pipeline.setSink(self.sink)

        self.target = ViewerWidget(self.sink, self.app)

        if self.docked:
            self.pack_start(self.target, True, True, 0)
            screen = Gdk.Screen.get_default()
            height = screen.get_height()
            if height >= 800:
                # show the controls and force the aspect frame to have at least the same
                # width (+110, which is a magic number to minimize dead padding).
                req = self.buttons.size_request()
                width = req.width
                height = req.height
                width += 110
                height = int(width / self.target.props.ratio)
                self.target.set_size_request(width, height)
        else:
            self.external_vbox.pack_start(self.target, False, False, 0)
            self.target.props.expand = True
            self.external_vbox.child_set(self.target, fill=True)

        self.setDisplayAspectRatio(self.app.project_manager.current_project.getDAR())
        self.target.show_all()

    def _disconnectFromPipeline(self):
        self.debug("Previous pipeline: %r", self.pipeline)
        if self.pipeline is None:
            # silently return, there's nothing to disconnect from
            return

        self.pipeline.disconnect_by_func(self._pipelineStateChangedCb)
        self.pipeline.disconnect_by_func(self._positionCb)
        self.pipeline.disconnect_by_func(self._durationChangedCb)

        if self.__owning_pipeline:
            self.pipeline.release()
        self.pipeline = None

    def _setUiActive(self, active=True):
        self.debug("active %r", active)
        self.set_sensitive(active)
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
        """ Creates the Viewer GUI """
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

        # Buttons/Controls
        bbox = Gtk.Box()
        bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        bbox.set_property("valign", Gtk.Align.CENTER)
        bbox.set_property("halign", Gtk.Align.CENTER)
        self.pack_end(bbox, False, False, SPACING)

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
        bbox.pack_start(self.timecode_entry, False, 10, 0)

        self.undock_button = Gtk.ToolButton()
        self.undock_button.set_icon_name("view-restore")
        self.undock_button.connect("clicked", self.undock)
        self.undock_button.set_tooltip_text(
            _("Detach the viewer\nYou can re-attach it by closing the newly created window."))
        bbox.pack_start(self.undock_button, False, False, 0)

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

        self.buttons = bbox
        self.buttons_container = bbox
        self.show_all()
        self.external_vbox.show_all()

    def setDisplayAspectRatio(self, ratio):
        self.debug("Setting aspect ratio to %f [%r]", float(ratio), ratio)
        self.target.setDisplayAspectRatio(ratio)

    def _entryActivateCb(self, unused_entry):
        self._seekFromTimecodeWidget()

    def _seekFromTimecodeWidget(self):
        nanoseconds = self.timecode_entry.getWidgetValue()
        self.seeker.seek(nanoseconds)

    # Active Timeline calllbacks
    def _durationChangedCb(self, unused_pipeline, duration):
        if duration == 0:
            self._setUiActive(False)
        else:
            self._setUiActive(True)

    def _playButtonCb(self, unused_button, unused_playing):
        self.app.project_manager.current_project.pipeline.togglePlayback()
        self.app.gui.focusTimeline()

    def _goToStartCb(self, unused_button):
        self.seeker.seek(0)
        self.app.gui.focusTimeline()

    def _backCb(self, unused_button):
        # Seek backwards one second
        self.seeker.seekRelative(0 - Gst.SECOND)
        self.app.gui.focusTimeline()

    def _forwardCb(self, unused_button):
        # Seek forward one second
        self.seeker.seekRelative(Gst.SECOND)
        self.app.gui.focusTimeline()

    def _goToEndCb(self, unused_button):
        end = self.app.project_manager.current_project.pipeline.getDuration()
        self.seeker.seek(end)
        self.app.gui.focusTimeline()

    # Public methods for controlling playback

    def undock(self, *unused_widget):
        if not self.docked:
            self.warning("The viewer is already undocked")
            return

        self.docked = False
        self.settings.viewerDocked = False

        self.remove(self.buttons_container)
        position = None
        if self.pipeline:
            position = self.pipeline.getPosition()
            self.pipeline.setState(Gst.State.NULL)
            self.remove(self.target)

        self.external_vbox.pack_end(self.buttons_container, False, False, 0)
        self.external_window.set_type_hint(Gdk.WindowTypeHint.UTILITY)

        self.undock_button.hide()
        self.fullscreen_button = Gtk.ToggleToolButton()
        self.fullscreen_button.set_icon_name("view-fullscreen")
        self.fullscreen_button.set_tooltip_text(
            _("Show this window in fullscreen"))
        self.buttons.pack_end(
            self.fullscreen_button, expand=False, fill=False, padding=6)
        self.fullscreen_button.show()
        self.fullscreen_button.connect("toggled", self._toggleFullscreen)

        self.external_window.show()
        self.hide()
        self.external_window.move(self.settings.viewerX, self.settings.viewerY)
        self.external_window.resize(
            self.settings.viewerWidth, self.settings.viewerHeight)
        if self.pipeline:
            self.pipeline.pause()
            self.seeker.seek(position)

    def dock(self):
        if self.docked:
            self.warning("The viewer is already docked")
            return

        self.docked = True
        self.settings.viewerDocked = True

        if self.pipeline:
            position = self.pipeline.getPosition()
            self.pipeline.setState(Gst.State.NULL)
            self.external_vbox.remove(self.target)
            self.__createNewViewer()

        self.undock_button.show()
        self.fullscreen_button.destroy()
        self.external_vbox.remove(self.buttons_container)
        self.pack_end(self.buttons_container, False, False, 0)
        self.show()

        self.external_window.hide()
        if position:
            self.pipeline.pause()
            self.seeker.seek(position)

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
        """
        If the timeline position changed, update the viewer UI widgets.

        This is meant to be called either by the gobject timer when playing,
        or by mainwindow's _timelineSeekCb when the timer is disabled.
        """
        self.timecode_entry.setWidgetValue(position, False)

    def clipTrimPreview(self, clip, position):
        """
        While a clip is being trimmed, show a live preview of it.
        """
        if not hasattr(clip, "get_uri") or isinstance(clip, GES.TitleClip) or clip.props.is_image:
            self.log(
                "%s is an image or has no URI, so not previewing trim" % clip)
            return False

        clip_uri = clip.props.uri
        cur_time = time()
        if self.pipeline == self.app.project_manager.current_project.pipeline:
            self.debug("Creating temporary pipeline for clip %s, position %s",
                       clip_uri, format_ns(position))
            self._oldTimelinePos = self.pipeline.getPosition(True)
            self.pipeline.set_state(Gst.State.NULL)
            self.setPipeline(AssetPipeline(clip))
            self.__owning_pipeline = True
            self._lastClipTrimTime = cur_time

        if (cur_time - self._lastClipTrimTime) > 0.2 and self.pipeline.getState() == Gst.State.PAUSED:
            # Do not seek more than once every 200 ms (for performance)
            self.pipeline.simple_seek(position)
            self._lastClipTrimTime = cur_time

    def clipTrimPreviewFinished(self):
        """
        After trimming a clip, reset the project pipeline into the viewer.
        """
        if self.pipeline is not self.app.project_manager.current_project.pipeline:
            self.pipeline.setState(Gst.State.NULL)
            # Using pipeline.getPosition() here does not work because for some
            # reason it's a bit off, that's why we need self._oldTimelinePos.
            self.setPipeline(
                self.app.project_manager.current_project.pipeline, self._oldTimelinePos)
            self._oldTimelinePos = None
            self.debug("Back to the project's pipeline")

    def _pipelineStateChangedCb(self, unused_pipeline, state, old_state):
        """
        When playback starts/stops, update the viewer widget,
        play/pause button and (un)inhibit the screensaver.

        This is meant to be called by mainwindow.
        """
        if int(state) == int(Gst.State.PLAYING):
            st = Gst.Structure.new_empty("play")
            self.app.write_action(st)
            self.playpause_button.setPause()
            self.system.inhibitScreensaver(self.INHIBIT_REASON)
        elif int(state) == int(Gst.State.PAUSED):
            if old_state != int(Gst.State.PAUSED):
                st = Gst.Structure.new_empty("pause")
                if old_state == int(Gst.State.PLAYING):
                    st.set_value("playback_time", float(self.pipeline.getPosition()) /
                                 Gst.SECOND)
                self.app.write_action(st)

            self.playpause_button.setPlay()
            self.system.uninhibitScreensaver(self.INHIBIT_REASON)
        else:
            self.system.uninhibitScreensaver(self.INHIBIT_REASON)


class TransformationBox(Gtk.EventBox, Loggable):
    def __init__(self, app):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self.__editSource = None
        self.__startDraggingPosition = None
        self.add_events(Gdk.EventMask.SCROLL_MASK)

    def __setupEditSource(self):
        if self.__editSource:
            return
        elif self.app.project_manager.current_project.pipeline.getState() != Gst.State.PAUSED:
            return

        try:
            position = self.app.project_manager.current_project.pipeline.getPosition()
        except:
            return False

        self.__editSource = None
        for clip in self.app.project_manager.current_project.timeline.ui.selection.selected:
            if clip.props.start <= position and position <= clip.props.start + clip.props.duration:
                video_source = clip.find_track_elements(None, GES.TrackType.VIDEO, GES.VideoSource)
                if video_source and self.__editSource:
                    video_source = None
                    break

                try:
                    self.__editSource = video_source[0]
                except IndexError:
                    continue

    def do_event(self, event):
        if event.type == Gdk.EventType.ENTER_NOTIFY and event.mode == Gdk.CrossingMode.NORMAL:
            self.__setupEditSource()
            if self.__editSource:
                self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND1))
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            self.__startDraggingPosition = None
        elif event.type == Gdk.EventType.LEAVE_NOTIFY and event.mode == Gdk.CrossingMode.NORMAL:
            self.get_window().set_cursor(None)
            self.__startDraggingPosition = None
            self.__editSource = None
            self.__startEditSourcePosition = None
        elif event.type == Gdk.EventType.BUTTON_PRESS:
            self.__setupEditSource()
            if self.__editSource:
                res_x, current_x = self.__editSource.get_child_property("posx")
                res_y, current_y = self.__editSource.get_child_property("posy")

                if res_x and res_y:
                    event_widget = Gtk.get_event_widget(event)
                    x, y = event_widget.translate_coordinates(self, event.x, event.y)
                    self.__startEditSourcePosition = (current_x, current_y)
                    self.__startDraggingPosition = (x, y)
        elif event.type == Gdk.EventType.MOTION_NOTIFY:
            if self.__startDraggingPosition and self.__editSource:
                event_widget = Gtk.get_event_widget(event)
                x, y = event_widget.translate_coordinates(self, event.x, event.y)
                self.__editSource.set_child_property("posx",
                                                     self.__startEditSourcePosition[0] +
                                                     (x - self.__startDraggingPosition[0]))

                self.__editSource.set_child_property("posy", self.__startEditSourcePosition[1] +
                                                     (y - self.__startDraggingPosition[1]))
                self.app.project_manager.current_project.pipeline.commit_timeline()
        elif event.type == Gdk.EventType.SCROLL:
            if self.__editSource:
                res, delta_x, delta_y = event.get_scroll_deltas()
                if not res:
                    res, direction = event.get_scroll_direction()
                    if not res:
                        self.error("Could not get scroll delta")
                        return True

                    if direction == Gdk.ScrollDirection.UP:
                        delta_y = -1.0
                    elif direction == Gdk.ScrollDirection.DOWN:
                        delta_y = 1.0
                    else:
                        self.error("Could not handle %s scroll event" % direction)
                        return True

                delta_y = delta_y * -1.0
                width = self.__editSource.get_child_property("width")[1]
                height = self.__editSource.get_child_property("height")[1]
                if event.get_state()[1] & Gdk.ModifierType.SHIFT_MASK:
                    height += delta_y
                elif event.get_state()[1] & Gdk.ModifierType.CONTROL_MASK:
                    width += delta_y
                else:
                    width += delta_y
                    height += delta_y

                self.__editSource.set_child_property("width", width)
                self.__editSource.set_child_property("height", height)
                self.app.project_manager.current_project.pipeline.commit_timeline()

        return True


class ViewerWidget(Gtk.AspectFrame, Loggable):

    """
    Widget for displaying a GStreamer video sink.

    @ivar settings: The settings of the application.
    @type settings: L{GlobalSettings}
    """

    __gsignals__ = {}

    def __init__(self, sink, app=None):
        # Prevent black frames and flickering while resizing or changing focus:
        # The aspect ratio gets overridden by setDisplayAspectRatio.
        Gtk.AspectFrame.__init__(self, xalign=0.5, yalign=0.5,
                                 ratio=4.0 / 3.0, obey_child=False)
        Loggable.__init__(self)
        self.__transformationBox = TransformationBox(app)

        # We only work with a gtkglsink inside a glsinkbin
        self.drawing_area = sink.props.sink.props.widget

        # We keep the ViewerWidget hidden initially, or the desktop wallpaper
        # would show through the non-double-buffered widget!
        self.add(self.__transformationBox)
        self.__transformationBox.add(self.drawing_area)

        self.drawing_area.show()

        self.seeker = Seeker()
        if app:
            self.settings = app.settings
        self.app = app
        self.box = None
        self.stored = False
        self.area = None
        self.zoom = 1.0
        self.sink = sink
        self.pixbuf = None
        self.pipeline = None
        self.transformation_properties = None
        self._setting_ratio = False
        self.__startDraggingPosition = None
        self.__startEditSourcePosition = None
        self.__editSource = None

    def setDisplayAspectRatio(self, ratio):
        self._setting_ratio = True
        self.set_property("ratio", float(ratio))

    def _sizeCb(self, unused_widget, unused_area):
        # The transformation box is cleared when using regular rendering
        # so we need to flush the pipeline
        self.seeker.flush()


class PlayPauseButton(Gtk.Button, Loggable):
    """
    Double state Gtk.Button which displays play/pause
    """
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
        self.connect('clicked', self._clickedCb)

    def set_sensitive(self, value):
        Gtk.Button.set_sensitive(self, value)

    def _clickedCb(self, unused):
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
