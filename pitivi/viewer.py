# PiTiVi , Non-linear video editor
#
#       ui/viewer.py
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

import platform
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import GdkX11
from gi.repository import GObject
from gi.repository import GES
GdkX11  # pyflakes
from gi.repository import GstVideo
GstVideo    # pyflakes
from gi.repository import GdkPixbuf
import cairo

from gettext import gettext as _
from time import time
from math import pi

from pitivi.settings import GlobalSettings
from pitivi.utils.pipeline import Seeker, SimplePipeline
from pitivi.utils.ui import SPACING, hex_to_rgb
from pitivi.utils.widgets import TimeWidget
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import print_ns

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


class PitiviViewer(Gtk.VBox, Loggable):
    """
    A Widget to control and visualize a Pipeline

    @ivar pipeline: The current pipeline
    @type pipeline: L{Pipeline}
    @ivar action: The action controlled by this Pipeline
    @type action: L{ViewAction}
    """
    __gtype_name__ = 'PitiviViewer'
    __gsignals__ = {
        "activate-playback-controls": (GObject.SignalFlags.RUN_LAST,
            None, (GObject.TYPE_BOOLEAN,)),
    }

    INHIBIT_REASON = _("Currently playing")

    def __init__(self, app, undock_action=None):
        Gtk.VBox.__init__(self)
        self.set_border_width(SPACING)
        self.app = app
        self.settings = app.settings
        self.system = app.system

        Loggable.__init__(self)
        self.log("New PitiviViewer")

        self.pipeline = None
        self._tmp_pipeline = None  # Used for displaying a preview when trimming

        self.sink = None
        self.docked = True

        # Only used for restoring the pipeline position after a live clip trim preview:
        self._oldTimelinePos = None

        self._haveUI = False

        self._createUi()
        self.target = self.internal
        self.undock_action = undock_action
        if undock_action:
            self.undock_action.connect("activate", self._toggleDocked)

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
        self.debug("self.pipeline:%r", self.pipeline)

        self.seeker = Seeker()
        self._disconnectFromPipeline()
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

        self.pipeline = pipeline
        if self.pipeline:
            self.pipeline.pause()
            self.seeker.seek(position)

            self.pipeline.connect("state-change", self._pipelineStateChangedCb)
            self.pipeline.connect("position", self._positionCb)
            self.pipeline.connect("window-handle-message", self._windowHandleMessageCb)
            self.pipeline.connect("duration-changed", self._durationChangedCb)

        self._setUiActive()

    def _disconnectFromPipeline(self):
        self.debug("pipeline:%r", self.pipeline)
        if self.pipeline is None:
            # silently return, there's nothing to disconnect from
            return

        self.pipeline.disconnect_by_func(self._pipelineStateChangedCb)
        self.pipeline.disconnect_by_func(self._windowHandleMessageCb)
        self.pipeline.disconnect_by_func(self._positionCb)
        self.pipeline.disconnect_by_func(self._durationChangedCb)

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

    def _externalWindowDeleteCb(self, window, event):
        self.dock()
        return True

    def _externalWindowConfigureCb(self, window, event):
        self.settings.viewerWidth = event.width
        self.settings.viewerHeight = event.height
        self.settings.viewerX = event.x
        self.settings.viewerY = event.y

    def _createUi(self):
        """ Creates the Viewer GUI """
        # Drawing area
        # The aspect ratio gets overridden on startup by setDisplayAspectRatio
        self.aframe = Gtk.AspectFrame(xalign=0.5, yalign=1.0, ratio=4.0 / 3.0,
                                      obey_child=False)

        self.internal = ViewerWidget(self.app.settings)
        self.internal.init_transformation_events()
        self.internal.show()
        self.aframe.add(self.internal)
        self.pack_start(self.aframe, True, True, 0)

        self.external_window = Gtk.Window()
        vbox = Gtk.VBox()
        vbox.set_spacing(SPACING)
        self.external_window.add(vbox)
        self.external = ViewerWidget(self.app.settings)
        vbox.pack_start(self.external, True, True, 0)
        self.external_window.connect("delete-event", self._externalWindowDeleteCb)
        self.external_window.connect("configure-event", self._externalWindowConfigureCb)
        self.external_vbox = vbox
        self.external_vbox.show_all()

        # Buttons/Controls
        bbox = Gtk.HBox()
        boxalign = Gtk.Alignment(xalign=0.5, yalign=0.5, xscale=0.0, yscale=0.0)
        boxalign.add(bbox)
        self.pack_start(boxalign, False, True, 0)

        self.goToStart_button = Gtk.ToolButton(Gtk.STOCK_MEDIA_PREVIOUS)
        self.goToStart_button.connect("clicked", self._goToStartCb)
        self.goToStart_button.set_tooltip_text(_("Go to the beginning of the timeline"))
        self.goToStart_button.set_sensitive(False)
        bbox.pack_start(self.goToStart_button, False, True, 0)

        self.back_button = Gtk.ToolButton(Gtk.STOCK_MEDIA_REWIND)
        self.back_button.connect("clicked", self._backCb)
        self.back_button.set_tooltip_text(_("Go back one second"))
        self.back_button.set_sensitive(False)
        bbox.pack_start(self.back_button, False, True, 0)

        self.playpause_button = PlayPauseButton()
        self.playpause_button.connect("play", self._playButtonCb)
        bbox.pack_start(self.playpause_button, False, True, 0)
        self.playpause_button.set_sensitive(False)

        self.forward_button = Gtk.ToolButton(Gtk.STOCK_MEDIA_FORWARD)
        self.forward_button.connect("clicked", self._forwardCb)
        self.forward_button.set_tooltip_text(_("Go forward one second"))
        self.forward_button.set_sensitive(False)
        bbox.pack_start(self.forward_button, False, True, 0)

        self.goToEnd_button = Gtk.ToolButton(Gtk.STOCK_MEDIA_NEXT)
        self.goToEnd_button.connect("clicked", self._goToEndCb)
        self.goToEnd_button.set_tooltip_text(_("Go to the end of the timeline"))
        self.goToEnd_button.set_sensitive(False)
        bbox.pack_start(self.goToEnd_button, False, True, 0)

        # current time
        self.timecode_entry = TimeWidget()
        self.timecode_entry.setWidgetValue(0)
        self.timecode_entry.connect("value-changed", self._jumpToTimecodeCb)
        self.timecode_entry.connectFocusEvents(self._entryFocusInCb, self._entryFocusOutCb)
        bbox.pack_start(self.timecode_entry, False, 10, 0)
        self._haveUI = True

        # Identify widgets for AT-SPI, making our test suite easier to develop
        # These will show up in sniff, accerciser, etc.
        self.goToStart_button.get_accessible().set_name("goToStart_button")
        self.back_button.get_accessible().set_name("back_button")
        self.playpause_button.get_accessible().set_name("playpause_button")
        self.forward_button.get_accessible().set_name("forward_button")
        self.goToEnd_button.get_accessible().set_name("goToEnd_button")
        self.timecode_entry.get_accessible().set_name("timecode_entry")

        screen = Gdk.Screen.get_default()
        height = screen.get_height()
        if height >= 800:
            # show the controls and force the aspect frame to have at least the same
            # width (+110, which is a magic number to minimize dead padding).
            bbox.show_all()
            req = bbox.size_request()
            width = req.width
            height = req.height
            width += 110
            height = int(width / self.aframe.props.ratio)
            self.aframe.set_size_request(width, height)
        self.show_all()
        self.buttons = boxalign

    def setDisplayAspectRatio(self, ratio):
        """
        Sets the DAR of the Viewer to the given ratio.

        @arg ratio: The aspect ratio to set on the viewer
        @type ratio: L{float}
        """
        self.debug("Setting ratio of %f [%r]", float(ratio), ratio)
        try:
            self.aframe.set_property("ratio", float(ratio))
        except:
            self.warning("could not set ratio !")

    def _entryFocusInCb(self, entry, event):
        self.app.gui.setActionsSensitive(False)

    def _entryFocusOutCb(self, entry, event):
        self.app.gui.setActionsSensitive(True)

    ## active Timeline calllbacks
    def _durationChangedCb(self, unused_pipeline, duration):
        if duration == 0:
            self._setUiActive(False)
        else:
            self._setUiActive(True)

    ## Control Gtk.Button callbacks

    def setZoom(self, zoom):
        """
        Zoom in or out of the transformation box canvas.
        This is called by clipproperties.
        """
        if self.target.box:
            maxSize = self.target.area
            width = int(float(maxSize.width) * zoom)
            height = int(float(maxSize.height) * zoom)
            area = ((maxSize.width - width) / 2,
                    (maxSize.height - height) / 2,
                    width, height)
            self.sink.set_render_rectangle(*area)
            self.target.box.update_size(area)
            self.target.zoom = zoom
            self.target.sink = self.sink
            self.target.renderbox()

    def _playButtonCb(self, unused_button, playing):
        self.app.current.pipeline.togglePlayback()

    def _goToStartCb(self, unused_button):
        self.seeker.seek(0)

    def _backCb(self, unused_button):
        # Seek backwards one second
        self.seeker.seekRelative(0 - Gst.SECOND)

    def _forwardCb(self, unused_button):
        # Seek forward one second
        self.seeker.seekRelative(Gst.SECOND)

    def _goToEndCb(self, unused_button):
        try:
            end = self.app.current.pipeline.getDuration()
        except:
            self.warning("Couldn't get timeline duration")
        try:
            self.seeker.seek(end)
        except:
            self.warning("Couldn't seek to the end of the timeline")

    ## Callback for jumping to a specific timecode

    def _jumpToTimecodeCb(self, widget):
        nanoseconds = widget.getWidgetValue()
        self.seeker.seek(nanoseconds)

    ## public methods for controlling playback

    def undock(self):
        if not self.undock_action:
            self.error("Cannot undock because undock_action is missing.")
            return
        if not self.docked:
            return

        self.docked = False
        self.settings.viewerDocked = False
        self.undock_action.set_label(_("Dock Viewer"))

        self.remove(self.buttons)
        self.external_vbox.pack_end(self.buttons, False, False, 0)
        self.external_window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.external_window.show()
        self.target = self.external
        # if we are playing, switch output immediately
        if self.sink:
            self._switch_output_window()
        self.hide()
        self.external_window.move(self.settings.viewerX, self.settings.viewerY)
        self.external_window.resize(self.settings.viewerWidth, self.settings.viewerHeight)

    def dock(self):
        if not self.undock_action:
            self.error("Cannot dock because undock_action is missing.")
            return
        if self.docked:
            return
        self.docked = True
        self.settings.viewerDocked = True
        self.undock_action.set_label(_("Undock Viewer"))

        self.target = self.internal
        self.external_vbox.remove(self.buttons)
        self.pack_end(self.buttons, False, False, 0)
        self.show()
        # if we are playing, switch output immediately
        if self.sink:
            self._switch_output_window()
        self.external_window.hide()

    def _toggleDocked(self, action):
        if self.docked:
            self.undock()
        else:
            self.dock()

    def _positionCb(self, unused_pipeline, position):
        """
        If the timeline position changed, update the viewer UI widgets.

        This is meant to be called either by the gobject timer when playing,
        or by mainwindow's _timelineSeekCb when the timer is disabled.
        """
        self.timecode_entry.setWidgetValue(position, False)

    def clipTrimPreview(self, tl_obj, position):
        """
        While a clip is being trimmed, show a live preview of it.
        """
        if isinstance(tl_obj, GES.TimelineTitleSource) or tl_obj.props.is_image or not hasattr(tl_obj, "get_uri"):
            self.log("%s is an image or has no URI, so not previewing trim" % tl_obj)
            return False

        clip_uri = tl_obj.props.uri
        cur_time = time()
        if not self._tmp_pipeline:
            self.debug("Creating temporary pipeline for clip %s, position %s",
                clip_uri, print_ns(position))

            self._oldTimelinePos = self.pipeline.getPosition()
            self._tmp_pipeline = Gst.ElementFactory.make("playbin", None)
            self._tmp_pipeline.set_property("uri", clip_uri)
            self.setPipeline(SimplePipeline(self._tmp_pipeline))
            self._lastClipTrimTime = cur_time
        if (cur_time - self._lastClipTrimTime) > 0.2:
            # Do not seek more than once every 200 ms (for performance)
            self._tmp_pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, position)
            self._lastClipTrimTime = cur_time

    def clipTrimPreviewFinished(self):
        """
        After trimming a clip, reset the project pipeline into the viewer.
        """
        if self._tmp_pipeline is not None:
            self._tmp_pipeline.set_state(Gst.State.NULL)
            self._tmp_pipeline = None  # Free the memory
            self.setPipeline(self.app.current.pipeline, self._oldTimelinePos)
            self.debug("Back to old pipeline")

    def _pipelineStateChangedCb(self, pipeline, state):
        """
        When playback starts/stops, update the viewer widget,
        play/pause button and (un)inhibit the screensaver.

        This is meant to be called by mainwindow.
        """
        self.info("current state changed : %s", state)
        if int(state) == int(Gst.State.PLAYING):
            self.playpause_button.setPause()
            self.system.inhibitScreensaver(self.INHIBIT_REASON)
        elif int(state) == int(Gst.State.PAUSED):
            self.playpause_button.setPlay()
            self.system.uninhibitScreensaver(self.INHIBIT_REASON)
        else:
            self.sink = None
            self.system.uninhibitScreensaver(self.INHIBIT_REASON)
        self.internal._currentStateCb(self.pipeline, state)

    def _windowHandleMessageCb(self, unused_pipeline, message):
        """
        When the pipeline sends us a message to prepare-xwindow-id,
        tell the viewer to switch its output window.
        """
        self.sink = message.src
        self._switch_output_window()

    def _switch_output_window(self):
        Gdk.threads_enter()
        self.sink.set_window_handle(self.target.window_xid)
        self.sink.expose()
        Gdk.threads_leave()


class Point():
    """
    Draw a point, used as a handle for the transformation box
    """

    def __init__(self, x, y, settings):
        self.x = x
        self.y = y
        self.color = hex_to_rgb(settings.pointColor)
        self.clickedColor = hex_to_rgb(settings.clickedPointColor)
        self.set_width(settings.pointSize)
        self.clicked = False

    def set_position(self, x, y):
        self.x = x
        self.y = y

    def set_width(self, width):
        self.width = width
        self.radius = width / 2

    def is_clicked(self, event):
        is_right_of_left = event.x > self.x - self.radius
        is_left_of_right = event.x < self.x + self.radius
        is_below_top = event.y > self.y - self.radius
        is_above_bottom = event.y < self.y + self.radius

        if is_right_of_left and is_left_of_right and is_below_top and is_above_bottom:
            self.clicked = True
            return True

    def draw(self, cr):
        linear = cairo.LinearGradient(self.x, self.y - self.radius,
                                    self.x, self.y + self.radius)
        linear.add_color_stop_rgba(0.00, .6, .6, .6, 1)
        linear.add_color_stop_rgba(0.50, .4, .4, .4, .1)
        linear.add_color_stop_rgba(0.60, .4, .4, .4, .1)
        linear.add_color_stop_rgba(1.00, .6, .6, .6, 1)

        radial = cairo.RadialGradient(self.x + self.radius / 2,
                                    self.y - self.radius / 2, 1,
                                    self.x, self.y,
                                    self.radius)
        if self.clicked:
            radial.add_color_stop_rgb(0, *self.clickedColor)
        else:
            radial.add_color_stop_rgb(0, *self.color)
        radial.add_color_stop_rgb(1, 0.1, 0.1, 0.1)
        radial_glow = cairo.RadialGradient(self.x, self.y,
                                        self.radius * .9,
                                        self.x, self.y,
                                        self.radius * 1.2)
        radial_glow.add_color_stop_rgba(0, 0.9, 0.9, 0.9, 1)
        radial_glow.add_color_stop_rgba(1, 0.9, 0.9, 0.9, 0)

        cr.set_source(radial_glow)
        cr.arc(self.x, self.y, self.radius * 1.2, 0, 2 * pi)
        cr.fill()
        cr.arc(self.x, self.y, self.radius * .9, 0, 2 * pi)
        cr.set_source(radial)
        cr.fill()
        cr.arc(self.x, self.y, self.radius * .9, 0, 2 * pi)
        cr.set_source(linear)
        cr.fill()

(NO_POINT,
 AREA,
 TOP_LEFT,
 BOTTOM_LEFT,
 TOP_RIGHT,
 BOTTOM_RIGHT,
 LEFT,
 RIGHT,
 TOP,
 BOTTOM) = range(10)


class TransformationBox():
    """
    Box for transforming the video on the ViewerWidget
    """

    def __init__(self, settings):
        self.clicked_point = NO_POINT
        self.left_factor = 0
        self.settings = settings
        self.right_factor = 1
        self.top_factor = 0
        self.bottom_factor = 1
        self.center_factor = Point(0.5, 0.5, settings)
        self.transformation_properties = None
        self.points = {}

    def is_clicked(self, event):
        is_right_of_left = event.x > self.left
        is_left_of_right = event.x < self.right
        is_below_top = event.y > self.top
        is_above_bottom = event.y < self.bottom

        if is_right_of_left and is_left_of_right and is_below_top and is_above_bottom:
            return True

    def update_scale(self):
        self.scale_x = (self.right_factor - self.left_factor) / 2.0
        self.scale_y = (self.bottom_factor - self.top_factor) / 2.0

    def update_center(self):
        self.center_factor.x = (self.left_factor + self.right_factor) / 2.0
        self.center_factor.y = (self.top_factor + self.bottom_factor) / 2.0

        self.center.x = self.area.width * self.center_factor.x
        self.center.y = self.area.height * self.center_factor.y

    def set_transformation_properties(self, transformation_properties):
        self.transformation_properties = transformation_properties
        self.update_from_effect(transformation_properties.effect)

    def update_from_effect(self, effect):
        self.scale_x = effect.get_property("scale-x")
        self.scale_y = effect.get_property("scale-y")
        self.center_factor.x = 2 * (effect.get_property("tilt-x") - 0.5) + self.scale_x
        self.center_factor.y = 2 * (effect.get_property("tilt-y") - 0.5) + self.scale_y
        self.left_factor = self.center_factor.x - self.scale_x
        self.right_factor = self.center_factor.x + self.scale_x
        self.top_factor = self.center_factor.y - self.scale_y
        self.bottom_factor = self.center_factor.y + self.scale_y
        self.update_absolute()
        self.update_factors()
        self.update_center()
        self.update_scale()
        self.update_points()

    def move(self, event):
        rel_x = self.last_x - event.x
        rel_y = self.last_y - event.y

        self.center.x -= rel_x
        self.center.y -= rel_y

        self.left -= rel_x
        self.right -= rel_x
        self.top -= rel_y
        self.bottom -= rel_y

        self.last_x = event.x
        self.last_y = event.y

    def init_points(self):
        #corner boxes
        self.points[TOP_LEFT] = Point(self.left, self.top, self.settings)
        self.points[TOP_RIGHT] = Point(self.right, self.top, self.settings)
        self.points[BOTTOM_LEFT] = Point(self.left, self.bottom, self.settings)
        self.points[BOTTOM_RIGHT] = Point(self.right, self.bottom, self.settings)
        #edge boxes
        self.points[TOP] = Point(self.center.x, self.top, self.settings)
        self.points[BOTTOM] = Point(self.center.x, self.bottom, self.settings)
        self.points[LEFT] = Point(self.left, self.center.y, self.settings)
        self.points[RIGHT] = Point(self.right, self.center.y, self.settings)

    def update_points(self):
        self._update_measure()

        #corner boxes
        self.points[TOP_LEFT].set_position(self.left, self.top)
        self.points[TOP_RIGHT].set_position(self.right, self.top)
        self.points[BOTTOM_LEFT].set_position(self.left, self.bottom)
        self.points[BOTTOM_RIGHT].set_position(self.right, self.bottom)
        #edge boxes
        self.points[TOP].set_position(self.center.x, self.top)
        self.points[BOTTOM].set_position(self.center.x, self.bottom)
        self.points[LEFT].set_position(self.left, self.center.y)
        self.points[RIGHT].set_position(self.right, self.center.y)

        if self.width < 100 or self.height < 100:
            if self.width < self.height:
                point_width = self.width / 4.0
            else:
                point_width = self.height / 4.0

            # gradient is not rendered below width 7
            if point_width < 7:
                point_width = 7
        else:
            point_width = self.settings.pointSize

        for point in self.points.values():
            point.set_width(point_width)

    def draw(self, cr):
        self.update_points()
        # main box
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.rectangle(self.left, self.top, self.right - self.left, self.bottom - self.top)
        cr.stroke()

        for point in self.points.values():
            point.draw(cr)

    def select_point(self, event):
        # translate when zoomed out
        event.x -= self.area.x
        event.y -= self.area.y
        for type, point in self.points.items():
            if point.is_clicked(event):
                self.clicked_point = type
                return

        if self.is_clicked(event):
            self.clicked_point = AREA
            self.last_x = event.x
            self.last_y = event.y
        else:
            self.clicked_point = NO_POINT

    def _update_measure(self):
        self.width = self.right - self.left
        self.height = self.bottom - self.top

    def transform(self, event):
        # translate when zoomed out
        event.x -= self.area.x
        event.y -= self.area.y
        aspect = float(self.area.width) / float(self.area.height)
        self._update_measure()

        if self.clicked_point == NO_POINT:
            return False
        elif self.clicked_point == AREA:
            self.move(event)
        elif self.clicked_point == TOP_LEFT:
            self.left = event.x
            self.top = self.bottom - self.width / aspect
        elif self.clicked_point == BOTTOM_LEFT:
            self.left = event.x
            self.bottom = self.top + self.width / aspect
        elif self.clicked_point == TOP_RIGHT:
            self.right = event.x
            self.top = self.bottom - self.width / aspect
        elif self.clicked_point == BOTTOM_RIGHT:
            self.right = event.x
            self.bottom = self.top + self.width / aspect
        elif self.clicked_point == LEFT:
            self.left = event.x
        elif self.clicked_point == RIGHT:
            self.right = event.x
        elif self.clicked_point == TOP:
            self.top = event.y
        elif self.clicked_point == BOTTOM:
            self.bottom = event.y
        self._check_negative_scale()
        self.update_factors()
        self.update_center()
        self.update_scale()
        return True

    def release_point(self):
        for point in self.points.values():
            point.clicked = False
        self.clicked_point = NO_POINT

    def _check_negative_scale(self):
        if self.right < self.left:
            if self.clicked_point in [RIGHT, BOTTOM_RIGHT, TOP_RIGHT]:
                self.right = self.left
            else:
                self.left = self.right
        if self.bottom < self.top:
            if self.clicked_point == [BOTTOM, BOTTOM_RIGHT, BOTTOM_LEFT]:
                self.bottom = self.top
            else:
                self.top = self.bottom

    def update_factors(self):
        self.bottom_factor = float(self.bottom) / float(self.area.height)
        self.top_factor = float(self.top) / float(self.area.height)
        self.left_factor = float(self.left) / float(self.area.width)
        self.right_factor = float(self.right) / float(self.area.width)

    def update_size(self, area):
        if area.width == 0 or area.height == 0:
            return
        self.area = area
        self.update_absolute()

    def init_size(self, area):
        self.area = area
        self.left = area.x
        self.right = area.x + area.width
        self.top = area.y
        self.bottom = area.y + area.height
        self.center = Point((self.left + self.right) / 2, (self.top + self.bottom) / 2, self.settings)
        self.init_points()
        self._update_measure()

    def update_absolute(self):
        self.top = self.top_factor * self.area.height
        self.left = self.left_factor * self.area.width
        self.bottom = self.bottom_factor * self.area.height
        self.right = self.right_factor * self.area.width
        self.update_center()

    def update_effect_properties(self):
        if self.transformation_properties:
            self.transformation_properties.disconnectSpinButtonsFromFlush()
            values = self.transformation_properties.spin_buttons
            values["tilt_x"].set_value((self.center_factor.x - self.scale_x) / 2.0 + 0.5)
            values["tilt_y"].set_value((self.center_factor.y - self.scale_y) / 2.0 + 0.5)

            values["scale_x"].set_value(self.scale_x)
            values["scale_y"].set_value(self.scale_y)
            self.transformation_properties.connectSpinButtonsToFlush()


class ViewerWidget(Gtk.DrawingArea, Loggable):
    """
    Widget for displaying properly GStreamer video sink

    @ivar settings: The settings of the application.
    @type settings: L{GlobalSettings}
    """

    __gsignals__ = {}

    def __init__(self, settings=None):
        Gtk.DrawingArea.__init__(self)
        Loggable.__init__(self)
        self.seeker = Seeker()
        self.settings = settings
        self.box = None
        self.stored = False
        self.area = None
        self.zoom = 1.0
        self.sink = None
        self.pixbuf = None
        self.pipeline = None
        self.transformation_properties = None
        # FIXME PyGi Styling with Gtk3
        #for state in range(Gtk.StateType.INSENSITIVE + 1):
            #self.modify_bg(state, self.style.black)

    def init_transformation_events(self):
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK
                        | Gdk.EventMask.POINTER_MOTION_HINT_MASK)

    def show_box(self):
        if not self.box:
            self.box = TransformationBox(self.settings)
            self.box.init_size(self.area)
            self._update_gradient()
            self.connect("button-press-event", self.button_press_event)
            self.connect("button-release-event", self.button_release_event)
            self.connect("motion-notify-event", self.motion_notify_event)
            self.connect("size-allocate", self._sizeCb)
            self.box.set_transformation_properties(self.transformation_properties)
            self.renderbox()

    def _sizeCb(self, widget, area):
        # The transformation box is cleared when using regular rendering
        # so we need to flush the pipeline
        self.seeker.flush()

    def hide_box(self):
        if self.box:
            self.box = None
            self.disconnect_by_func(self.button_press_event)
            self.disconnect_by_func(self.button_release_event)
            self.disconnect_by_func(self.motion_notify_event)
            self.seeker.flush()
            self.zoom = 1.0
            if self.sink:
                self.sink.set_render_rectangle(*self.area)

    def set_transformation_properties(self, transformation_properties):
            self.transformation_properties = transformation_properties

    def _store_pixbuf(self):
        """
        When not playing, store a pixbuf of the current viewer image.
        This will allow it to be restored for the transformation box.
        """

        if self.box and self.zoom != 1.0:
            # The transformation box is active and dezoomed
            # crop away 1 pixel border to avoid artefacts on the pixbuf

            self.pixbuf = Gdk.pixbuf_get_from_window(self.get_window(),
                self.box.area.x + 1, self.box.area.y + 1,
                self.box.area.width - 2, self.box.area.height - 2)
        else:
            self.pixbuf = Gdk.pixbuf_get_from_window(self.get_window(),
                0, 0,
                self.get_window().get_width(),
                self.get_window().get_height())

        self.stored = True

    def do_realize(self):
        """
        Redefine gtk DrawingArea's do_realize method to handle multiple OSes.
        This is called when creating the widget to get the window ID.
        """
        Gtk.DrawingArea.do_realize(self)
        if platform.system() == 'Windows':
            self.window_xid = self.props.window.handle
        else:
            self.window_xid = self.get_property('window').get_xid()

    def button_release_event(self, widget, event):
        if event.button == 1:
            self.box.update_effect_properties()
            self.box.release_point()
            self.seeker.flush()
            self.stored = False
        return True

    def button_press_event(self, widget, event):
        if event.button == 1:
            self.box.select_point(event)
        return True

    def _currentStateCb(self, pipeline, state):
        self.pipeline = pipeline
        if state == Gst.State.PAUSED:
            self._store_pixbuf()
        self.renderbox()

    def motion_notify_event(self, widget, event):
        if event.get_state() & Gdk.ModifierType.BUTTON1_MASK:
            if self.box.transform(event):
                if self.stored:
                    self.renderbox()
        return True

    def do_expose_event(self, event):
        self.area = event.area
        if self.box:
            self._update_gradient()
            if self.zoom != 1.0:
                width = int(float(self.area.width) * self.zoom)
                height = int(float(self.area.height) * self.zoom)
                area = ((self.area.width - width) / 2,
                        (self.area.height - height) / 2,
                        width, height)
                self.sink.set_render_rectangle(*area)
            else:
                area = self.area
            self.box.update_size(area)
            self.renderbox()

    def _update_gradient(self):
        self.gradient_background = cairo.LinearGradient(0, 0, 0, self.area.height)
        self.gradient_background.add_color_stop_rgb(0.00, .1, .1, .1)
        self.gradient_background.add_color_stop_rgb(0.50, .2, .2, .2)
        self.gradient_background.add_color_stop_rgb(1.00, .5, .5, .5)

    def renderbox(self):
        if self.box:
            cr = self.window.cairo_create()
            cr.push_group()

            if self.zoom != 1.0:
                # draw some nice background for zoom out
                cr.set_source(self.gradient_background)
                cr.rectangle(0, 0, self.area.width, self.area.height)
                cr.fill()

                # translate the drawing of the zoomed out box
                cr.translate(self.box.area.x, self.box.area.y)

            # clear the drawingarea with the last known clean video frame
            # translate when zoomed out
            if self.pixbuf:
                if self.box.area.width != self.pixbuf.get_width():
                    scale = float(self.box.area.width) / float(self.pixbuf.get_width())
                    cr.save()
                    cr.scale(scale, scale)
                cr.set_source_pixbuf(self.pixbuf, 0, 0)
                cr.paint()
                if self.box.area.width != self.pixbuf.get_width():
                    cr.restore()

            if self.pipeline and self.pipeline.get_state()[1] == Gst.State.PAUSED:
                self.box.draw(cr)
            cr.pop_group_to_source()
            cr.paint()


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
        """ display the play image """
        self.log("setPlay")
        self.playing = True
        self.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY, Gtk.IconSize.BUTTON))
        self.set_tooltip_text(_("Play"))
        self.playing = False

    def setPause(self):
        self.log("setPause")
        """ display the pause image """
        self.playing = False
        self.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PAUSE, Gtk.IconSize.BUTTON))
        self.set_tooltip_text(_("Pause"))
        self.playing = True
