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

import gobject
import gtk
import gst

from pitivi.action import ViewAction

from pitivi.utils import time_to_string, Seeker
from pitivi.log.loggable import Loggable
from pitivi.pipeline import PipelineError

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

    def __init__(self, action=None, pipeline=None):
        """
        @param action: Specific action to use instead of auto-created one
        @type action: L{ViewAction}
        """
        gtk.VBox.__init__(self)
        Loggable.__init__(self)
        self.log("New PitiviViewer")

        self.seeker = Seeker(80)
        self.seeker.connect('seek', self._seekerSeekCb)
        self.action = action
        self.pipeline = pipeline
        self.producer = None

        self.current_time = long(0)
        self._initial_seek = None
        self.current_frame = -1

        self.currentState = gst.STATE_PAUSED
        self._haveUI = False

        self._createUi()
        self.setAction(action)
        self.setPipeline(pipeline)

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
        self.pipeline.disconnect_by_function(self._elementMessageCb)
        #self.deactivatePositionListener()
        self.pipeline.stop()

        self.pipeline = None

    def _connectToAction(self, action):
        self.debug("action: %r", action)
        # not sure what we need to do ...
        self.action = action
        # FIXME: fix this properly?
        self.drawingarea.action = action
        self.drawingarea.have_set_xid = False
        self.showControls()

    def _disconnectFromAction(self):
        self.action = None

    def _setUiActive(self, active=True):
        self.debug("active %r", active)
        self.set_sensitive(active)
        if self._haveUI:
            for item in [self.slider, self.rewind_button, self.back_button,
                         self.playpause_button, self.next_button,
                         self.forward_button, self.timelabel]:
                item.set_sensitive(active)
        if active:
            self.emit("activate-playback-controls", True)

    def _getDefaultAction(self):
        return ViewAction()

    def _createUi(self):
        """ Creates the Viewer GUI """
        self.set_border_width(5)
        self.set_spacing(5)

        # drawing area
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=0.5, ratio=4.0/3.0,
                                      obey_child=False)
        self.pack_start(self.aframe, expand=True)
        self.drawingarea = ViewerWidget(self.action)
        self.drawingarea.connect_after("expose-event", self._drawingAreaExposeCb)
        self.aframe.add(self.drawingarea)

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

        self.rewind_button = gtk.ToolButton(gtk.STOCK_MEDIA_REWIND)
        self.rewind_button.connect("clicked", self._rewindCb)
        self.rewind_button.set_sensitive(False)
        bbox.pack_start(self.rewind_button, expand=False)

        self.back_button = gtk.ToolButton(gtk.STOCK_MEDIA_PREVIOUS)
        self.back_button.connect("clicked", self._backCb)
        self.back_button.set_sensitive(False)
        bbox.pack_start(self.back_button, expand=False)

        self.playpause_button = PlayPauseButton()
        self.playpause_button.connect("play", self._playButtonCb)
        bbox.pack_start(self.playpause_button, expand=False)
        self.playpause_button.set_sensitive(False)

        self.next_button = gtk.ToolButton(gtk.STOCK_MEDIA_NEXT)
        self.next_button.connect("clicked", self._nextCb)
        self.next_button.set_sensitive(False)
        bbox.pack_start(self.next_button, expand=False)

        self.forward_button = gtk.ToolButton(gtk.STOCK_MEDIA_FORWARD)
        self.forward_button.connect("clicked", self._forwardCb)
        self.forward_button.set_sensitive(False)
        bbox.pack_start(self.forward_button, expand=False)

        # current time
        self.timelabel = gtk.Label()
        self.timelabel.set_markup("<tt>00:00:00.000 / --:--:--.---</tt>")
        self.timelabel.set_alignment(1.0, 0.5)
        self.timelabel.set_padding(5, 5)
        bbox.pack_start(self.timelabel, expand=False, padding=10)
        self._haveUI = True

    def showControls(self):
        if not self.action:
            return
        if True:
            self.rewind_button.show()
            self.back_button.show()
            self.playpause_button.show()
            self.next_button.show()
            self.forward_button.show()
            self.slider.show()
        else:
            self.rewind_button.hide()
            self.back_button.hide()
            self.playpause_button.hide()
            self.next_button.hide()
            self.forward_button.hide()
            self.slider.hide()

    def setDisplayAspectRatio(self, ratio):
        """ Sets the DAR of the Viewer to the given ratio """
        self.debug("Setting ratio of %f [%r]", float(ratio), ratio)
        try:
            self.aframe.set_property("ratio", float(ratio))
        except:
            self.warning("could not set ratio !")

    def _settingsChangedCb(self, unused_project):
        self.info("current project settings changed")
        # modify the ratio if it's the timeline that's playing
        # FIXME : do we really need to modify the ratio ??
        pass

    def _drawingAreaExposeCb(self, drawingarea, event):
        drawingarea.disconnect_by_func(self._drawingAreaExposeCb)
        for state in range(gtk.STATE_INSENSITIVE + 1):
            drawingarea.modify_bg(state, drawingarea.style.black)
        self.debug("yay, we are exposed !")
        if self.pipeline:
            try:
                self.pipeline.paused()
            except:
                self.currentState = gst.STATE_NULL
            else:
                self.currentState = gst.STATE_PAUSED
        return False

    ## gtk.HScale callbacks for self.slider

    def _sliderButtonPressCb(self, slider, unused_event):
        self.info("button pressed")
        self.moving_slider = True
        self.valuechangedid = slider.connect("value-changed", self._sliderValueChangedCb)
        self.pipeline.pause()
        return False

    def _sliderButtonReleaseCb(self, slider, unused_event):
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
            self._doSeek(value)

    def _sliderScrollCb(self, unused_slider, event):
        # calculate new seek position
        if self.current_frame == -1:
            # time scrolling, 0.5s forward/backward
            if event.direction in [gtk.gdk.SCROLL_LEFT, gtk.gdk.SCROLL_DOWN]:
                seekvalue = max(self.current_time - gst.SECOND / 2, 0)
            else:
                seekvalue = min(self.current_time + gst.SECOND / 2, self.pipeline.getDuration())
            self._doSeek(seekvalue)
        else:
            # frame scrolling, frame by frame
            self.info("scroll direction:%s", event.direction)
            if event.direction in [gtk.gdk.SCROLL_LEFT, gtk.gdk.SCROLL_DOWN]:
                self.info("scrolling backward")
                seekvalue = max(self.current_frame - 1, 0)
            else:
                self.info("scrolling forward")
                seekvalue = min(self.current_frame + 1, self.pipeline.getDuration())
            self._doSeek(seekvalue, gst.FORMAT_DEFAULT)

    def _doSeek(self, position, format=gst.FORMAT_TIME):
        self.seeker.seek(position, format)

    def _seekerSeekCb(self, seeker, position, format):
        try:
            self.pipeline.seek(position, format)
        except PipelineError:
            self.error("seek failed %s %s", gst.TIME_ARGS(position), format)

    def _newTime(self, value, frame=-1):
        self.info("value:%s, frame:%d", gst.TIME_ARGS(value), frame)
        self.current_time = value
        self.current_frame = frame
        try:
            duration = self.pipeline.getDuration()
        except:
            duration = gst.CLOCK_TIME_NONE
        self.timelabel.set_markup("<tt>%s / %s</tt>" % (time_to_string(value),
                                                        time_to_string(duration)))
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

        self.timelabel.set_markup("<tt>%s / %s</tt>" % (time_to_string(self.current_time),
                                                        time_to_string(duration)))

        if duration == 0:
            self._setUiActive(False)
        else:
            self._setUiActive(True)

        if self._initial_seek is not None:
            seek, self._initial_seek = self._initial_seek, None
            self.pipeline.seek(seek)

    ## Control gtk.Button callbacks

    def _rewindCb(self, unused_button):
        self.rewind()

    def _backCb(self, unused_button):
        self.back()

    def _playButtonCb(self, unused_button, isplaying):
        self.togglePlayback()

    def _nextCb(self, unused_button):
        self.next()

    def _forwardCb(self, unused_button):
        self.forward()

    ## public methods for controlling playback

    def play(self):
        if not self.pipeline.play() == gst.STATE_CHANGE_FAILURE:
            self.currentState = gst.STATE_PLAYING
            self.playpause_button.setPause()

    def pause(self):
        if not self.pipeline.pause() == gst.STATE_CHANGE_FAILURE:
            self.currentState = gst.STATE_PAUSED
            self.playpause_button.setPlay()

    def togglePlayback(self):
        if self.pipeline is None:
            return

        if self.currentState == gst.STATE_PLAYING:
            self.pause()
        else:
            self.play()

    def rewind(self):
        raise NotImplementedError

    def back(self):
        raise NotImplementedError

    def next(self):
        raise NotImplementedError

    def forward(self):
        raise NotImplementedError

    def _posCb(self, unused_pipeline, pos):
        self._newTime(pos)

    def _currentStateCb(self, unused_pipeline, state):
        self.info("current state changed : %s", state)
        if state == int(gst.STATE_PLAYING):
            self.playpause_button.setPause()
        elif state == int(gst.STATE_PAUSED):
            self.playpause_button.setPlay()

    def _eosCb(self, unused_pipeline):
        self.playpause_button.setPlay()

    def _elementMessageCb(self, unused_pipeline, message):
        name = message.structure.get_name()
        self.log('message:%s / %s', message, name)
        if name == 'prepare-xwindow-id':
            self.drawingarea.set_xwindow_id()


class ViewerWidget(gtk.DrawingArea, Loggable):
    """
    Widget for displaying properly GStreamer video sink
    """

    __gsignals__ = {}

    def __init__(self, action):
        gtk.DrawingArea.__init__(self)
        Loggable.__init__(self)
        self.action = action # FIXME : Check if it's a view action
        self.have_set_xid = False
        self.unset_flags(gtk.SENSITIVE)

    def set_xwindow_id(self):
        """ set the widget's XID on the configured videosink. """
        self.log("...")
        if self.have_set_xid:
            return
        self.action.set_window_xid(self.window.xid)
        self.unset_flags(gtk.DOUBLE_BUFFERED)
        self.have_set_xid = True


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
            self.playing = False

    def setPause(self):
        self.log("setPause")
        """ display the pause image """
        if not self.playing:
            self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON))
            self.playing = True
