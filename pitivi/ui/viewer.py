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

import os.path
import gobject
import gtk
import gst
import gst.interfaces
from glade import GladeWindow

import plumber
import pitivi.instance as instance
from pitivi.bin import SmartTimelineBin
import pitivi.dnd as dnd
from pitivi.signalgroup import SignalGroup

from gettext import gettext as _

def time_to_string(value):
    if value == -1:
        return "--:--:--.---"
    ms = value / gst.MSECOND
    sec = ms / 1000
    ms = ms % 1000
    mins = sec / 60
    sec = sec % 60
    hours = mins / 60
    return "%02d:%02d:%02d.%03d" % (hours, mins, sec, ms)

class PitiviViewer(gtk.VBox):
    """ Pitivi's viewer widget with controls """

    def __init__(self):
        gst.log("New PitiviViewer")
        gtk.VBox.__init__(self)
        self.current_time = long(0)
        self.requested_time = long(0)
        self.current_frame = -1
        self.valuechangedid = 0
        self.currentlySeeking = False
        self.currentState = gst.STATE_PAUSED
        self._createUi()

        # Connect to project.  We must remove and reset the callbacks when
        # changing project.
        self.project_signals = SignalGroup()
        self._connectToProject(instance.PiTiVi.current)
        instance.PiTiVi.connect("new-project-loaded", self._newProjectCb)
        instance.PiTiVi.playground.connect("current-state", self._currentStateCb)
        instance.PiTiVi.playground.connect("position", self._playgroundPositionCb)

        # callback to know when to set the XID on our viewer widget
        instance.PiTiVi.playground.connect("element-message", self._playgroundElementMessageCb)

        # signal for timeline duration changes : (composition, sigid)
        self._timelineDurationChangedSigId = (None, None)

        self._addTimelineToPlayground()

    def _connectToProject(self, project):
        """Connect signal handlers to a project.

        This first disconnects any handlers connected to an old project.
        If project is None, this just disconnects any connected handlers.

        """
        self.project_signals.connect(project.sources, "tmp_is_ready",
                                     None, self._tmpIsReadyCb)
        self.project_signals.connect(project, "settings-changed",
                                     None, self._settingsChangedCb)

    def _createUi(self):
        """ Creates the Viewer GUI """
        self.set_border_width(5)
        self.set_spacing(5)

        # drawing area
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=0.5, ratio=4.0/3.0, obey_child=False)
        self.pack_start(self.aframe, expand=True)
        self.drawingarea = ViewerWidget()
        self.drawingarea.connect_after("realize", self._drawingAreaRealizeCb)
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
        self.timelabel.set_markup("<tt>00m00s000 / --m--s---</tt>")
        self.timelabel.set_alignment(1.0, 0.5)
        self.timelabel.set_padding(5, 5)
        bbox.pack_start(self.timelabel, expand=False, padding=10)


        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.FILESOURCE_TUPLE, dnd.URI_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag_data_received", self._dndDataReceivedCb)

    def _asyncFrameRatioChange(self, ratio):
        gst.debug("ratio:%f" % ratio)
        self.aframe.set_property("ratio", ratio)

    def _videosinkCapsNotifyCb(self, sinkpad, unused_property):
        caps = sinkpad.get_negotiated_caps()
        if not caps:
            return
        gst.log("caps:%s" % caps.to_string())
        try:
            width = caps[0]["width"]
            height = caps[0]["height"]
        except:
            gst.warning("Something went wrong when getting the video sink aspect ratio")
        else:
            try:
                par = caps[0]["pixel-aspect-ratio"]
            except:
                # set aspect ratio
                gobject.idle_add(self._asyncFrameRatioChange, float(width) / float(height))
            else:
                gobject.idle_add(self._asyncFrameRatioChange, float(width * par.num) / float(par.denom * height))

    def _createSinkThreads(self):
        """ Creates the sink threads for the playground """
        # video elements
        gst.debug("Creating video sink")
        self.videosink = plumber.get_video_sink()
        vsinkthread = gst.Bin('vsinkthread')
        vqueue = gst.element_factory_make('queue')
        cspace = gst.element_factory_make('ffmpegcolorspace')
        vscale = gst.element_factory_make('videoscale')
        vscale.props.method = 1
        vsinkthread.add(self.videosink, vqueue, vscale, cspace)
        vqueue.link(self.videosink)
        cspace.link(vscale)
        vscale.link(vqueue)
        vsinkthread.videosink = self.videosink
        vsinkthread.add_pad(gst.GhostPad("sink", cspace.get_pad('sink')))

        self.videosink.get_pad("sink").connect("notify::caps", self._videosinkCapsNotifyCb)

        self.drawingarea.videosink = self.videosink

        # audio elements
        gst.debug("Creating audio sink")
        self.audiosink = plumber.get_audio_sink()
        asinkthread = gst.Bin('asinkthread')
        aqueue = gst.element_factory_make('queue')
        aconv = gst.element_factory_make('audioconvert')
        asinkthread.add(self.audiosink, aqueue, aconv)
        aconv.link(aqueue)
        aqueue.link(self.audiosink)
        asinkthread.audiosink = self.audiosink
        asinkthread.add_pad(gst.GhostPad("sink", aconv.get_pad('sink')))

        # setting sinkthreads on playground
        instance.PiTiVi.playground.setVideoSinkThread(vsinkthread)
        instance.PiTiVi.playground.setAudioSinkThread(asinkthread)
        instance.PiTiVi.playground.connect("current-changed", self._currentPlaygroundChangedCb)

    def _settingsChangedCb(self, unused_project):
        gst.info("current project settings changed")
        # modify the ratio if it's the timeline that's playing
        # FIXME : do we really need to modify the ratio ??
        pass

    def _drawingAreaRealizeCb(self, drawingarea):
        drawingarea.modify_bg(gtk.STATE_NORMAL, drawingarea.style.black)
        self._createSinkThreads()
        if not instance.PiTiVi.playground.play() == gst.STATE_CHANGE_FAILURE:
            self.currentState = gst.STATE_PLAYING

    ## gtk.HScale callbacks for self.slider

    def _sliderButtonPressCb(self, slider, unused_event):
        gst.info("button pressed")
        self.moving_slider = True
        self.valuechangedid = slider.connect("value-changed", self._sliderValueChangedCb)
        instance.PiTiVi.playground.pause()
        return False

    def _sliderButtonReleaseCb(self, slider, unused_event):
        gst.info("slider button release at %s" % time_to_string(long(slider.get_value())))
        self.moving_slider = False
        if self.valuechangedid:
            slider.disconnect(self.valuechangedid)
            self.valuechangedid = 0
        # revert to previous state
        if self.currentState == gst.STATE_PAUSED:
            instance.PiTiVi.playground.pause()
        else:
            instance.PiTiVi.playground.play()
        return False

    def _sliderValueChangedCb(self, slider):
        """ seeks when the value of the slider has changed """
        value = long(slider.get_value())
        gst.info(gst.TIME_ARGS(value))
        if self.moving_slider:
            self._doSeek(value)

    def _sliderScrollCb(self, unused_slider, event):
        # calculate new seek position
        if self.current_frame == -1:
            # time scrolling, 0.5s forward/backward
            if event.direction in [gtk.gdk.SCROLL_LEFT, gtk.gdk.SCROLL_DOWN]:
                seekvalue = max(self.current_time - gst.SECOND / 2, 0)
            else:
                seekvalue = min(self.current_time + gst.SECOND / 2, instance.PiTiVi.playground.current.length)
            self._doSeek(seekvalue)
        else:
            # frame scrolling, frame by frame
            gst.info("scroll direction:%s" % event.direction)
            if event.direction in [gtk.gdk.SCROLL_LEFT, gtk.gdk.SCROLL_DOWN]:
                gst.info("scrolling backward")
                seekvalue = max(self.current_frame - 1, 0)
            else:
                gst.info("scrolling forward")
                seekvalue = min(self.current_frame + 1, instance.PiTiVi.playground.current.length)
            self._doSeek(seekvalue, gst.FORMAT_DEFAULT)

    def _seekTimeoutCb(self):
        self.currentlySeeking = False
        if not self.current_time == self.requested_time:
            self._doSeek(self.requested_time)

    def _doSeek(self, value, format=gst.FORMAT_TIME):
        if not self.currentlySeeking:
            self.currentlySeeking = True
            gobject.timeout_add(80, self._seekTimeoutCb)
            instance.PiTiVi.playground.seekInCurrent(value, format=format)
            self._newTime(value)
        if format == gst.FORMAT_TIME:
            self.requested_time = value

    def _newTime(self, value, frame=-1):
        gst.info("value:%s, frame:%d" % (gst.TIME_ARGS(value), frame))
        self.current_time = value
        self.current_frame = frame
        self.timelabel.set_markup("<tt>%s / %s</tt>" % (time_to_string(value), time_to_string(instance.PiTiVi.playground.current.length)))
        if not self.moving_slider:
            self.posadjust.set_value(float(value))
        return False


    ## active Timeline calllbacks

    def _asyncTimelineDurationChanged(self, duration):
        gst.debug("duration : %s" % gst.TIME_ARGS(duration))
        gst.debug("playground.current.length : %s" % gst.TIME_ARGS(instance.PiTiVi.playground.current.length))
        self.posadjust.upper = float(duration)
        self.timelabel.set_markup("<tt>%s / %s</tt>" % (time_to_string(self.current_time), time_to_string(instance.PiTiVi.playground.current.length)))


    def _backToDefaultCb(self):
        instance.PiTiVi.playground.switchToDefault()
        instance.PiTiVi.playground.play()
        self._newTime(0)

    def _timelineDurationChangedCb(self, unused_composition, unused_start,
                                   duration):
        gst.debug("duration : %s" % gst.TIME_ARGS(duration))
        if duration == 0:
            gobject.idle_add(self._backToDefaultCb)
        gobject.idle_add(self._asyncTimelineDurationChanged, duration)

    def _dndDataReceivedCb(self, unused_widget, context, unused_x, unused_y,
                           selection, targetType, ctime):
        gst.info("context:%s, targetType:%s" % (context, targetType))
        if targetType == dnd.TYPE_URI_LIST:
            uri = selection.data.strip().split("\n")[0].strip()
        elif targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, ctime)
            return
        gst.info("got file:%s" % uri)
        if uri in instance.PiTiVi.current.sources:
            instance.PiTiVi.playground.playTemporaryFilesourcefactory(instance.PiTiVi.current.sources[uri])
        else:
            instance.PiTiVi.current.sources.addTmpUri(uri)
        context.finish(True, False, ctime)
        gst.info("end")

    def _tmpIsReadyCb(self, unused_sourcelist, factory):
        """ the temporary factory is ready, we can know set it to play """
        gst.info("%s" % factory)
        instance.PiTiVi.playground.playTemporaryFilesourcefactory(factory)

    def _newProjectCb(self, unused_pitivi, project):
        """ the current project has changed """
        assert(instance.PiTiVi.current == project)
        self._connectToProject(project)

    def _addTimelineToPlayground(self):
        instance.PiTiVi.playground.addPipeline(instance.PiTiVi.current.getBin())


    ## Control gtk.Button callbacks

    def _rewindCb(self, unused_button):
        pass

    def _backCb(self, unused_button):
        instance.PiTiVi.playground.backward_one()

    def _playButtonCb(self, unused_button, isplaying):
        if isplaying:
            if not instance.PiTiVi.playground.play() == gst.STATE_CHANGE_FAILURE:
                self.currentState = gst.STATE_PLAYING
        else:
            if not instance.PiTiVi.playground.pause() == gst.STATE_CHANGE_FAILURE:
                self.currentState = gst.STATE_PAUSED

    def _nextCb(self, unused_button):
        instance.PiTiVi.playground.forward_one()

    def _forwardCb(self, unused_button):
        pass


    ## Playground callbacks

    def _playgroundPositionCb(self, unused_playground, unused_smartbin, pos):
        self._newTime(pos)

    def _currentPlaygroundChangedCb(self, playground, smartbin):
        gst.log("smartbin:%s" % smartbin)
        if smartbin == playground.default:
            self.slider.set_sensitive(False)
            self.playpause_button.set_sensitive(False)
            self.next_button.set_sensitive(False)
            self.back_button.set_sensitive(False)
            if not self._timelineDurationChangedSigId == (None, None):
                obj, sigid = self._timelineDurationChangedSigId
                obj.disconnect(sigid)
                self._timelineDurationChangedSigId = (None, None)
        else:
            if isinstance(smartbin, SmartTimelineBin):
                gst.info("switching to Timeline, setting duration to %s" % (gst.TIME_ARGS(smartbin.project.timeline.videocomp.duration)))
                self.posadjust.upper = float(smartbin.project.timeline.videocomp.duration)
                # FIXME : we need to disconnect from this signal !
                sigid = smartbin.project.timeline.videocomp.connect("start-duration-changed",
                                                                    self._timelineDurationChangedCb)
                self._timelineDurationChangedSigId = (smartbin.project.timeline.videocomp,
                                                      sigid)
            else:
                self.posadjust.upper = float(smartbin.factory.length)
                if not self._timelineDurationChangedSigId == (None, None):
                    obj, sigid = self._timelineDurationChangedSigId
                    obj.disconnect(sigid)
                    self._timelineDurationChangedSigId = (None, None)
            self._newTime(0)
            self.slider.set_sensitive(True)
            self.playpause_button.set_sensitive(True)
            self.next_button.set_sensitive(True)
            self.back_button.set_sensitive(True)

    def _currentStateCb(self, unused_playground, state):
        gst.info("current state changed : %s" % state)
        if state == int(gst.STATE_PLAYING):
            self.playpause_button.setPause()
        elif state == int(gst.STATE_PAUSED):
            self.playpause_button.setPlay()

    def _playgroundElementMessageCb(self, unused_playground, message):
        name = message.structure.get_name()
        gst.log('message:%s / %s' % (message, name))
        if name == 'prepare-xwindow-id':
            dav = self.drawingarea.videosink
            gst.log('%s' % dav)
            if dav and dav.realsink and dav.realsink == message.src:
                self.drawingarea.can_set_xid = True
                if self.drawingarea.isexposed:
                    self.drawingarea.set_xwindow_id()


class ViewerWidget(gtk.DrawingArea):
    """
    Widget for displaying properly GStreamer video sink
    """

    __gsignals__ = {}

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.videosink = None
        self.have_set_xid = False
        self.can_set_xid = False
        self.unset_flags(gtk.DOUBLE_BUFFERED)
        self.unset_flags(gtk.SENSITIVE)
        self.isexposed = False

    def do_expose_event(self, unused_event):
        """ 'expose-event' override """
        gst.log("expose have_set_xid:%d can_set_xid:%d" % (self.have_set_xid, self.can_set_xid))
        self.isexposed = True
        if self.videosink:
            if not self.have_set_xid and self.can_set_xid:
                self.set_xwindow_id()
            elif self.have_set_xid:
                self.videosink.expose()
        return False

    def set_xwindow_id(self):
        """ set the widget's XID on the configured videosink. """
        gst.log("...")
        if not self.videosink:
            return
        if self.have_set_xid:
            return
        gst.log("About to set %s's xid to %d" % (self.videosink,
                                                 self.window.xid))
        self.videosink.set_xwindow_id(self.window.xid)
        self.have_set_xid = True
        #self.videosink.expose()


class PlayPauseButton(gtk.Button):
    """ Double state gtk.Button which displays play/pause """

    __gsignals__ = {
        "play" : ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_BOOLEAN, ))
        }

    def __init__(self):
        gtk.Button.__init__(self, label="")
        self.playing = True
        self.setPlay()
        self.connect('clicked', self._clickedCb)

    def _clickedCb(self, unused):
        if not self.playing:
            self.setPause()
        else:
            self.setPlay()
        self.emit("play", self.playing)

    def setPlay(self):
        """ display the play image """
        gst.log("setPlay")
        if self.playing:
            self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON))
            self.playing = False

    def setPause(self):
        gst.log("setPause")
        """ display the pause image """
        if not self.playing:
            self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON))
            self.playing = True



