#!/usr/bin/python
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import platform
import gobject
import gtk
from gtk import gdk
import gst

from gettext import gettext as _

from pitivi.action import ViewAction

from pitivi.stream import VideoStream
from pitivi.utils import time_to_string, Seeker
from pitivi.log.loggable import Loggable
from pitivi.pipeline import PipelineError
from pitivi.ui.common import SPACING

class ViewerError(Exception):
    pass

# TODO : Switch to using Pipeline and Action

class PitiviViewer(gtk.VBox, Loggable):

    __gtype_name__ = 'PitiviViewer'
    __gsignals__ = {
        "activate-playback-controls" : (gobject.SIGNAL_RUN_LAST, 
            gobject.TYPE_NONE, (gobject.TYPE_BOOLEAN,)),
    }

    """
    A Widget to control and visualize a Pipeline

    @cvar pipeline: The current pipeline
    @type pipeline: L{Pipeline}
    @cvar action: The action controlled by this Pipeline
    @type action: L{ViewAction}
    """

    def __init__(self, app, undock_action, action=None, pipeline=None):
        """
        @param action: Specific action to use instead of auto-created one
        @type action: L{ViewAction}
        """
        gtk.VBox.__init__(self)
        self.set_border_width(SPACING)
        self.app = app
        self.settings = app.settings

        Loggable.__init__(self)
        self.log("New PitiviViewer")

        self.seeker = Seeker(80)
        self.seeker.connect('seek', self._seekerSeekCb)
        self.action = action
        self.pipeline = pipeline
        self.sink = None
        self.docked = True

        self.current_time = long(0)
        self._initial_seek = None
        self.current_frame = -1

        self.currentState = gst.STATE_PAUSED
        self._haveUI = False

        self._createUi()
        self.target = self.internal
        self.setAction(action)
        self.setPipeline(pipeline)
        self.undock_action = undock_action
        self.undock_action.connect("activate", self._toggleDocked)

    def setPipeline(self, pipeline):
        """
        Set the Viewer to the given Pipeline.

        Properly switches the currently set action to that new Pipeline.

        @param pipeline: The Pipeline to switch to.
        @type pipeline: L{Pipeline}.
        """
        self.debug("self.pipeline:%r, pipeline:%r", self.pipeline, pipeline)

        if pipeline is not None and pipeline == self.pipeline:
            return

        if self.pipeline != None:
            # remove previously set Pipeline
            self._disconnectFromPipeline()
            # make ui inactive
            self._setUiActive(False)
            # finally remove previous pipeline
            self.pipeline = None
            self.currentState = gst.STATE_PAUSED
            self.playpause_button.setPause()
        self._connectToPipeline(pipeline)
        self.pipeline = pipeline
        if self.pipeline is not None:
            self._setUiActive()

    def setAction(self, action):
        """
        Set the controlled action.

        @param action: The Action to set. If C{None}, a default L{ViewAction}
        will be used.
        @type action: L{ViewAction} or C{None}
        """
        self.debug("self.action:%r, action:%r", self.action, action)
        if action is not None and action == self.action:
            return

        if self.action != None:
            # if there was one previously, remove it
            self._disconnectFromAction()
        if action == None:
            # get the default action
            action = self._getDefaultAction()
        self._connectToAction(action)
        self.showControls()

    def _connectToPipeline(self, pipeline):
        self.debug("pipeline:%r", pipeline)
        if self.pipeline != None:
            raise ViewerError("previous pipeline wasn't disconnected")
        self.pipeline = pipeline
        if self.pipeline == None:
            return
        self.pipeline.connect('position', self._posCb)
        self.pipeline.activatePositionListener()
        self.pipeline.connect('state-changed', self._currentStateCb)
        self.pipeline.connect('element-message', self._elementMessageCb)
        self.pipeline.connect('duration-changed', self._durationChangedCb)
        self.pipeline.connect('eos', self._eosCb)
        # if we have an action set it to that new pipeline
        if self.action:
            self.pipeline.setAction(self.action)
            self.action.activate()

    def _disconnectFromPipeline(self):
        self.debug("pipeline:%r", self.pipeline)
        if self.pipeline == None:
            # silently return, there's nothing to disconnect from
            return
        if self.action and (self.action in self.pipeline.actions):
            # if we have an action, properly remove it from pipeline
            if self.action.isActive():
                self.pipeline.stop()
                self.action.deactivate()
            self.pipeline.removeAction(self.action)

        self.pipeline.disconnect_by_function(self._posCb)
        self.pipeline.disconnect_by_function(self._currentStateCb)
        self.pipeline.disconnect_by_function(self._elementMessageCb)
        self.pipeline.disconnect_by_function(self._durationChangedCb)
        self.pipeline.disconnect_by_function(self._eosCb)
        self.pipeline.stop()

        self.pipeline = None

    def _connectToAction(self, action):
        self.debug("action: %r", action)
        # not sure what we need to do ...
        self.action = action
        # FIXME: fix this properly?
        self.internal.action = action
        dar = float(4/3)
        try:
            producer = action.producers[0]
            self.debug("producer:%r", producer)
            for stream in producer.output_streams:
                self.warning("stream:%r", stream)
            for stream in producer.getOutputStreams(VideoStream):
                self.debug("stream:%r", stream)
                if stream.dar:
                    dar = stream.dar
                    continue
        except:
            dar = float(4/3)
        self.setDisplayAspectRatio(dar)
        self.showControls()

    def _disconnectFromAction(self):
        self.action = None

    def _setUiActive(self, active=True):
        self.debug("active %r", active)
        self.set_sensitive(active)
        if self._haveUI:
            for item in [self.slider, self.goToStart_button, self.back_button,
                         self.playpause_button, self.forward_button,
                         self.goToEnd_button, self.timelabel]:
                item.set_sensitive(active)
        if active:
            self.emit("activate-playback-controls", True)

    def _getDefaultAction(self):
        return ViewAction()

    def _externalWindowDeleteCb(self, window, event):
        self.dock()
        return True

    def _createUi(self):
        """ Creates the Viewer GUI """
        # drawing area
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=0.5, ratio=4.0/3.0,
                                      obey_child=False)
        self.pack_start(self.aframe, expand=True)
        self.internal = ViewerWidget(self.action)
        self.aframe.add(self.internal)

        self.external_window = gtk.Window()
        vbox = gtk.VBox()
        vbox.set_spacing(6)
        self.external_window.add(vbox)
        self.external = ViewerWidget(self.action)
        vbox.pack_start(self.external)
        self.external_window.connect("delete-event",
            self._externalWindowDeleteCb)
        self.external_vbox = vbox

        # Slider
        self.posadjust = gtk.Adjustment()
        self.slider = gtk.HScale(self.posadjust)
        self.slider.set_draw_value(False)
        self.slider.connect("button-press-event", self._sliderButtonPressCb)
        self.slider.connect("button-release-event", self._sliderButtonReleaseCb)
        self.slider.connect("scroll-event", self._sliderScrollCb)
        self.pack_start(self.slider, expand=False)
        self.moving_slider = False
        self.slider.set_sensitive(False)

        # Buttons/Controls
        bbox = gtk.HBox()
        boxalign = gtk.Alignment(xalign=0.5, yalign=0.5)
        boxalign.add(bbox)
        self.pack_start(boxalign, expand=False)

        self.goToStart_button = gtk.ToolButton(gtk.STOCK_MEDIA_PREVIOUS)
        self.goToStart_button.connect("clicked", self._goToStartCb)
        self.goToStart_button.set_tooltip_text(_("Go to the beginning of the timeline"))
        self.goToStart_button.set_sensitive(False)
        bbox.pack_start(self.goToStart_button, expand=False)

        self.back_button = gtk.ToolButton(gtk.STOCK_MEDIA_REWIND)
        self.back_button.connect("clicked", self._backCb)
        self.back_button.set_tooltip_text(_("Go back one second"))
        self.back_button.set_sensitive(False)
        bbox.pack_start(self.back_button, expand=False)

        self.playpause_button = PlayPauseButton()
        self.playpause_button.connect("play", self._playButtonCb)
        bbox.pack_start(self.playpause_button, expand=False)
        self.playpause_button.set_sensitive(False)

        self.forward_button = gtk.ToolButton(gtk.STOCK_MEDIA_FORWARD)
        self.forward_button.connect("clicked", self._forwardCb)
        self.forward_button.set_tooltip_text(_("Go forward one second"))
        self.forward_button.set_sensitive(False)
        bbox.pack_start(self.forward_button, expand=False)

        self.goToEnd_button = gtk.ToolButton(gtk.STOCK_MEDIA_NEXT)
        self.goToEnd_button.connect("clicked", self._goToEndCb)
        self.goToEnd_button.set_tooltip_text(_("Go to the end of the timeline"))
        self.goToEnd_button.set_sensitive(False)
        bbox.pack_start(self.goToEnd_button, expand=False)

        # current time
        self.timelabel = gtk.Label()
        self.timelabel.set_markup("<tt>00:00:00.000</tt>")
        self.timelabel.set_alignment(1.0, 0.5)
        bbox.pack_start(self.timelabel, expand=False, padding=10)
        self._haveUI = True

        screen = gdk.screen_get_default()
        height = screen.get_height()
        if height >= 800:
            # show the controls and force the aspect frame to have at least the same
            # width (+110, which is a magic number to minimize dead padding).
            bbox.show_all()
            width, height = bbox.size_request()
            width += 110
            height = int(width / self.aframe.props.ratio)
            self.aframe.set_size_request(width , height)
        self.show_all()
        self.buttons = boxalign

    _showingSlider = True

    def showSlider(self):
        self._showingSlider = True
        self.slider.show()

    def hideSlider(self):
        self._showingSlider = False
        self.slider.hide()

    def showControls(self):
        if not self.action:
            return
        if True:
            self.goToStart_button.show()
            self.back_button.show()
            self.playpause_button.show()
            self.forward_button.show()
            self.goToEnd_button.show()
            if self._showingSlider:
                self.slider.show()
        else:
            self.goToStart_button.hide()
            self.back_button.hide()
            self.playpause_button.hide()
            self.forward_button.hide()
            self.goToEnd_button.hide()
            self.slider.hide()

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

    ## gtk.HScale callbacks for self.slider

    def _sliderButtonPressCb(self, slider, event):
        # borrow totem hack for seek-on-click behavior
        event.button = 2
        self.info("button pressed")
        self.moving_slider = True
        self.valuechangedid = slider.connect("value-changed", self._sliderValueChangedCb)
        self.pipeline.pause()
        return False

    def _sliderButtonReleaseCb(self, slider, event):
        # borrow totem hack for seek-on-click behavior
        event.button = 2
        self.info("slider button release at %s", time_to_string(long(slider.get_value())))
        self.moving_slider = False
        if self.valuechangedid:
            slider.disconnect(self.valuechangedid)
            self.valuechangedid = 0
        # revert to previous state
        if self.currentState == gst.STATE_PAUSED:
            self.pipeline.pause()
        else:
            self.pipeline.play()
        return False

    def _sliderValueChangedCb(self, slider):
        """ seeks when the value of the slider has changed """
        value = long(slider.get_value())
        self.info(gst.TIME_ARGS(value))
        if self.moving_slider:
            self.seek(value)

    def _sliderScrollCb(self, unused_slider, event):
        if event.direction == gtk.gdk.SCROLL_LEFT:
            amount = -gst.SECOND
        else:
            amount = gst.SECOND
        self.seekRelative(amount)

    def seek(self, position, format=gst.FORMAT_TIME):
        try:
            self.seeker.seek(position, format)
        except:
            self.warning("seek failed")

    def _seekerSeekCb(self, seeker, position, format):
        try:
            self.pipeline.seek(position, format)
        except PipelineError:
            self.error("seek failed %s %s", gst.TIME_ARGS(position), format)

    def _newTime(self, value, frame=-1):
        self.info("value:%s, frame:%d", gst.TIME_ARGS(value), frame)
        self.current_time = value
        self.current_frame = frame
        self.timelabel.set_markup("<tt>%s</tt>" % time_to_string(value))
        if not self.moving_slider:
            self.posadjust.set_value(float(value))
        return False


    ## active Timeline calllbacks

    def _durationChangedCb(self, unused_pipeline, duration):
        self.debug("duration : %s", gst.TIME_ARGS(duration))
        position = self.posadjust.get_value()
        if duration < position:
            self.posadjust.set_value(float(duration))
        self.posadjust.upper = float(duration)

        if duration == 0:
            self._setUiActive(False)
        else:
            self._setUiActive(True)

        if self._initial_seek is not None:
            seek, self._initial_seek = self._initial_seek, None
            self.pipeline.seek(seek)

    ## Control gtk.Button callbacks

    def _goToStartCb(self, unused_button):
        self.seek(0)

    def _backCb(self, unused_button):
        self.seekRelative(-gst.SECOND)

    def _playButtonCb(self, unused_button, isplaying):
        self.togglePlayback()

    def _forwardCb(self, unused_button):
        self.seekRelative(gst.SECOND)

    def _goToEndCb(self, unused_button):
        try:
            dur = self.pipeline.getDuration()
            self.seek(dur - 1)
        except:
            self.warning("couldn't get duration")

    ## public methods for controlling playback

    def play(self):
        self.pipeline.play()

    def pause(self):
        self.pipeline.pause()

    def togglePlayback(self):
        if self.pipeline is None:
            return
        self.pipeline.togglePlayback()

    def undock(self):
        if not self.docked:
            return

        self.docked = False
        self.undock_action.set_label(_("Dock Viewer"))

        self.remove(self.buttons)
        self.remove(self.slider)
        self.external_vbox.pack_end(self.slider, False, False)
        self.external_vbox.pack_end(self.buttons, False, False)
        self.external_window.show_all()
        self.target = self.external
        # if we are playing, switch output immediately
        if self.sink:
            self._switch_output_window()
        self.hide()

    def dock(self):
        if self.docked:
            return
        self.docked = True
        self.undock_action.set_label(_("Undock Viewer"))

        self.target = self.internal
        self.external_vbox.remove(self.slider)
        self.external_vbox.remove(self.buttons)
        self.pack_end(self.slider, False, False)
        self.pack_end(self.buttons, False, False)
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

    def seekRelative(self, time):
        try:
            self.pipeline.seekRelative(time)
        except:
            self.warning("seek failed")

    def _posCb(self, unused_pipeline, pos):
        self._newTime(pos)

    def _currentStateCb(self, unused_pipeline, state):
        self.info("current state changed : %s", state)
        if state == int(gst.STATE_PLAYING):
            self.playpause_button.setPause()
        elif state == int(gst.STATE_PAUSED):
            self.playpause_button.setPlay()
        else:
            self.sink = None
        self.currentState = state

    def _eosCb(self, unused_pipeline):
        self.playpause_button.setPlay()

    def _elementMessageCb(self, unused_pipeline, message):
        name = message.structure.get_name()
        self.log('message:%s / %s', message, name)
        if name == 'prepare-xwindow-id':
            sink = message.src
            self.sink = sink
            self._switch_output_window()

    def _switch_output_window(self):
        gtk.gdk.threads_enter()
        self.sink.set_xwindow_id(self.target.window_xid)
        self.sink.expose()
        gtk.gdk.threads_leave()


class ViewerWidget(gtk.DrawingArea, Loggable):
    """
    Widget for displaying properly GStreamer video sink
    """

    __gsignals__ = {}

    def __init__(self, action):
        gtk.DrawingArea.__init__(self)
        Loggable.__init__(self)
        self.action = action # FIXME : Check if it's a view action
        self.unset_flags(gtk.SENSITIVE)
        for state in range(gtk.STATE_INSENSITIVE + 1):
            self.modify_bg(state, self.style.black)

    def do_realize(self):
        gtk.DrawingArea.do_realize(self)
        if platform.system() == 'Windows':
            self.window_xid = self.window.handle
        else:
            self.window_xid  = self.window.xid

class PlayPauseButton(gtk.Button, Loggable):
    """ Double state gtk.Button which displays play/pause """

    __gsignals__ = {
        "play" : ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_BOOLEAN, ))
        }

    def __init__(self):
        gtk.Button.__init__(self, label="")
        Loggable.__init__(self)
        self.get_settings().props.gtk_button_images = True
        self.playing = True
        self.setPlay()
        self.connect('clicked', self._clickedCb)

    def set_sensitive(self, value):
        gtk.Button.set_sensitive(self, value)

    def _clickedCb(self, unused):
        self.emit("play", self.playing)

    def setPlay(self):
        """ display the play image """
        self.log("setPlay")
        if self.playing:
            self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON))
            self.set_tooltip_text(_("Play"))
            self.playing = False

    def setPause(self):
        self.log("setPause")
        """ display the pause image """
        if not self.playing:
            self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON))
            self.set_tooltip_text(_("Pause"))
            self.playing = True
