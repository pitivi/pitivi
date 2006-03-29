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
import pango
import gst.interfaces
from glade import GladeWindow

import plumber
import pitivi.instance as instance
from pitivi.bin import SmartTimelineBin, SmartDefaultBin
from pitivi.objectfactory import FileSourceFactory
import pitivi.dnd as dnd
from pitivi.settings import ExportSettings
from exportsettingswidget import ExportSettingsDialog

def time_to_string(value):
    if value == -1:
        return "--m--s---"
    ms = value / gst.MSECOND
    sec = ms / 1000
    ms = ms % 1000
    min = sec / 60
    sec = sec % 60
    return "%02dm%02ds%03d" % (min, sec, ms)

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
        self._createUi()

        # connect to the sourcelist for temp factories
        # TODO remove/replace the signal when closing/opening projects
        instance.PiTiVi.current.sources.connect("tmp_is_ready", self._tmpIsReadyCb)

        # Only set the check time timeout in certain cases...
        self.checktimeoutid = 0
        self.positionChangedCallbacks = []
        instance.PiTiVi.connect("new-project", self._newProjectCb)
        instance.PiTiVi.playground.connect("current-state", self._currentStateCb)
        instance.PiTiVi.playground.connect("bin-added", self._binAddedCb)
        instance.PiTiVi.playground.connect("bin-removed", self._binRemovedCb)

        instance.PiTiVi.current.settings.connect("settings-changed",
                                                 self._settingsChangedCb)
        self._addTimelineToPlayground()

    def _createUi(self):
        """ Creates the Viewer GUI """
        self.set_border_width(5)
        self.set_spacing(5)
        
        # drawing area
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=0.0, ratio=4.0/3.0, obey_child=False)
        self.pack_start(self.aframe, expand=True)
        self.drawingarea = ViewerWidget()
        self.drawingarea.connect_after("realize", self._drawingAreaRealizeCb)
        self.aframe.add(self.drawingarea)
        
        # horizontal line
        self.pack_start(gtk.HSeparator(), expand=False)

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

        self.record_button = gtk.ToolButton(gtk.STOCK_MEDIA_RECORD)
        self.record_button.connect("clicked", self._recordCb)
        self.record_button.set_sensitive(False)
        bbox.pack_start(self.record_button, expand=False)
        
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
        
        infohbox = gtk.HBox()
        infohbox.set_spacing(5)
        self.pack_start(infohbox, expand=False)

        # available sources combobox
        infoframe = gtk.Frame()
        self.sourcelist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_PYOBJECT)
        self.sourcecombobox = gtk.ComboBox(self.sourcelist)
        cell = gtk.CellRendererText()
        self.sourcecombobox.pack_start(cell, True)
        self.sourcecombobox.add_attribute(cell, "text", 0)
        self.sourcecombobox.set_sensitive(False)
        self.sourcecombobox.connect("changed", self._comboboxChangedCb)
        infoframe.add(self.sourcecombobox)
        
        # current time
        timeframe = gtk.Frame()
        self.timelabel = gtk.Label("00m00s000 / --m--s---")
        self.timelabel.set_alignment(1.0, 0.5)
        self.timelabel.set_padding(5, 5)
        timeframe.add(self.timelabel)
        infohbox.pack_start(infoframe, expand=True)
        infohbox.pack_end(timeframe, expand=False)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.FILESOURCE_TUPLE, dnd.URI_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag_data_received", self._dndDataReceivedCb)

    def _videosinkCapsNotifyCb(self, sinkpad, property):
        caps = sinkpad.get_negotiated_caps()
        if not caps:
            return
        gst.log("caps:%s" % caps.to_string())
        try:
            width = caps[0]["width"]
            height = caps[0]["height"]
            
            # set aspect ratio
            self.aframe.set_property("ratio", float(width) / float(height))
        except:
            gst.warning("Something went wrong when getting the video sink aspect ratio")

    def _createSinkThreads(self):
        """ Creates the sink threads for the playground """
        # video elements
        gst.debug("Creating video sink")
        self.videosink = plumber.get_video_sink()
        vsinkthread = gst.Bin('vsinkthread')
        vqueue = gst.element_factory_make('queue')
        cspace = gst.element_factory_make('ffmpegcolorspace')
        vsinkthread.add(self.videosink, vqueue, cspace)
        cspace.link(vqueue)
        vqueue.link(self.videosink)
        vsinkthread.videosink = self.videosink
        vsinkthread.add_pad(gst.GhostPad("sink", cspace.get_pad('sink')))

        if self.videosink.realsink:
            self.videosink.info("Setting callback on 'notify::caps'")
            self.videosink.realsink.get_pad("sink").connect("notify::caps", self._videosinkCapsNotifyCb)

        self.drawingarea.videosink = self.videosink
        self.videosink.set_xwindow_id(self.drawingarea.window.xid)

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

    def _settingsChangedCb(self, settings):
        gst.info("current project settings changed")
        # modify the ratio if it's the timeline that's playing
        raise NotImplementedError

    def _drawingAreaRealizeCb(self, drawingarea):
        drawingarea.modify_bg(gtk.STATE_NORMAL, drawingarea.style.black)
        self._createSinkThreads()
        instance.PiTiVi.playground.play()

    ## gtk.HScale callbacks for self.slider

    def _sliderButtonPressCb(self, slider, event):
        gst.info("button pressed")
        self.moving_slider = True
        if self.checktimeoutid:
            gobject.source_remove(self.checktimeoutid)
            self.checktimeoutid = 0
        self.valuechangedid = slider.connect("value-changed", self._sliderValueChangedCb)
        instance.PiTiVi.playground.current.set_state(gst.STATE_PAUSED)
        return False

    def _sliderButtonReleaseCb(self, slider, event):
        gst.info("slider button release at %s" % time_to_string(long(slider.get_value())))
        self.moving_slider = False
        if self.valuechangedid:
            slider.disconnect(self.valuechangedid)
            self.valuechangedid = 0
        if not self.checktimeoutid:
            gst.debug("adding checktime again")
            self.checktimeoutid = gobject.timeout_add(300, self._checkTimeCb)
        instance.PiTiVi.playground.current.set_state(gst.STATE_PLAYING)
        return False

    def _sliderValueChangedCb(self, slider):
        """ seeks when the value of the slider has changed """
        value = long(slider.get_value())
        gst.info(time_to_string(value))
        self._doSeek(value)
        #instance.PiTiVi.playground.seekInCurrent(value)

    def _sliderScrollCb(self, slider, event):
        # calculate new seek position
        if self.current_frame == -1:
            # time scrolling, 0.5s forward/backward
            if event.direction in [gtk.gdk.SCROLL_LEFT, gtk.gdk.SCROLL_DOWN]:
                seekvalue = max(self.current_time - gst.SECOND / 2, 0)
            else:
                seekvalue = min(self.current_time + gst.SECOND / 2, instance.PiTiVi.playground.current.length)
            self._doSeek(seekvalue)
            #instance.PiTiVi.playground.seekInCurrent(seekvalue)
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
            #instance.PiTiVi.playground.seekInCurrent(seekvalue, gst.FORMAT_DEFAULT)

    def _seekTimeoutCb(self):
        self.currentlySeeking = False
        if not self.current_time == self.requested_time:
            self._doSeek(self.requested_time)

    def _doSeek(self, value, format=gst.FORMAT_TIME):
        if not self.currentlySeeking:
            self.currentlySeeking = True
            gobject.timeout_add(80, self._seekTimeoutCb)
            instance.PiTiVi.playground.seekInCurrent(value, format)
            self._newTime(value)
        elif format == gst.FORMAT_TIME:
            self.requested_time = value

    ## timeout functions for checking current time

    ## TODO : check_time timeout should in fact be in the playground to be more generic
    def _checkTimeCb(self):
        # check time callback
        gst.log("checking time")
        if instance.PiTiVi.playground.current == instance.PiTiVi.playground.default:
            return True
        # don't check time if the timeline is not playing
        cur = self.current_time
        currentframe = self.current_frame
        if True: #not isinstance(instance.PiTiVi.playground.current, SmartTimelineBin):
            pending, state, result = instance.PiTiVi.playground.current.get_state(10)
            if not state in [gst.STATE_PAUSED, gst.STATE_PLAYING]:
                return
            try:
                cur, format = instance.PiTiVi.playground.current.query_position(gst.FORMAT_TIME)
            except:
                instance.PiTiVi.playground.current.warning("couldn't get position")
                cur = 0

        # if the current_time or the length has changed, update time
        if not float(instance.PiTiVi.playground.current.length) == self.posadjust.upper or not cur == self.current_time or not currentframe == self.current_frame:
            self.posadjust.upper = float(instance.PiTiVi.playground.current.length)
            self._newTime(cur, currentframe)
        return True

    def _newTime(self, value, frame=-1):
        gst.info("value:%s, frame:%d" % (gst.TIME_ARGS(value), frame))
        self.current_time = value
        self.current_frame = frame
        self.timelabel.set_text(time_to_string(value) + " / " + time_to_string(instance.PiTiVi.playground.current.length))
        if not self.moving_slider:
            self.posadjust.set_value(float(value))
        if isinstance(instance.PiTiVi.playground.current, SmartTimelineBin):
            self._triggerTimelinePositionCallbacks(value, frame)
        return False

    def _triggerTimelinePositionCallbacks(self, value, frame = -1):
        for callback in self.positionChangedCallbacks:
            callback(value, frame)

    def addTimelinePositionCallback(self, function):
        """ Set the function that will be called whenever the timeline position has changed """
        self.positionChangedCallbacks.append(function)


    ## gtk.ComboBox callbacks for sources

    def _comboboxChangedCb(self, cbox):
        # selected another source
        idx = cbox.get_active()
        # get the corresponding smartbin
        smartbin = self.sourcelist[idx][1]
        if not instance.PiTiVi.playground.current == smartbin:
            instance.PiTiVi.playground.switchToPipeline(smartbin)


    ## active Timeline calllbacks

    def _timelineDurationChangedCb(self, composition, start, duration):
        # deactivate record button is the duration is null
        self.record_button.set_sensitive((duration > 0) and True or False)
            
        self.posadjust.upper = float(duration)
        self.timelabel.set_text(time_to_string(self.current_time) + " / " + time_to_string(instance.PiTiVi.playground.current.length))

    def _dndDataReceivedCb(self, widget, context, x, y, selection, targetType, time):
        gst.info("context:%s, targetType:%s" % (context, targetType))
        if targetType == dnd.TYPE_URI_LIST:
            uri = selection.data.strip().split("\n")[0].strip()
        elif targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            return
        gst.info("got file:%s" % uri)
        if uri in instance.PiTiVi.current.sources:
            instance.PiTiVi.playground.playTemporaryFilesourcefactory(instance.PiTiVi.current.sources[uri])
        else:
            instance.PiTiVi.current.sources.addTmpUri(uri)

    def _tmpIsReadyCb(self, sourcelist, factory):
        """ the temporary factory is ready, we can know set it to play """
        gst.info("%s" % factory)
        instance.PiTiVi.playground.playTemporaryFilesourcefactory(factory)

    def _newProjectCb(self, pitivi, project):
        """ the current project has changed """
        instance.PiTiVi.current.sources.connect("tmp_is_ready", self._tmpIsReadyCb)
        instance.PiTiVi.current.settings.connect("settings-changed", self._settingsChangedCb)
        
    def _addTimelineToPlayground(self):
        instance.PiTiVi.playground.addPipeline(instance.PiTiVi.current.getBin())


    ## Control gtk.Button callbacks
        
    def _recordCb(self, button):
        win = EncodingDialog(instance.PiTiVi.current)
        win.show()

    def _rewindCb(self, button):
        pass

    def _backCb(self, button):
        pass

    def _playButtonCb(self, button, isplaying):
        if isplaying:
            instance.PiTiVi.playground.play()
        else:
            instance.PiTiVi.playground.pause()

    def _nextCb(self, button):
        pass

    def _forwardCb(self, button):
        pass


    ## Playground callbacks
    
    def _currentPlaygroundChangedCb(self, playground, smartbin):
        if smartbin.width and smartbin.height:
            self.aframe.set_property("ratio", float(smartbin.width) / float(smartbin.height))
        else:
            self.aframe.set_property("ratio", 4.0/3.0)
        if not smartbin == playground.default:
            if isinstance(smartbin, SmartTimelineBin):
                gst.info("switching to Timeline, setting duration to %s" % (gst.TIME_ARGS(smartbin.project.timeline.videocomp.duration)))
                self.posadjust.upper = float(smartbin.project.timeline.videocomp.duration)
                smartbin.project.timeline.videocomp.connect("start-duration-changed",
                                                            self._timelineDurationChangedCb)
                if smartbin.project.timeline.videocomp.duration > 0:
                    self.record_button.set_sensitive(True)
                else:
                    self.record_button.set_sensitive(False)
            else:
                self.posadjust.upper = float(smartbin.factory.length)
                self.record_button.set_sensitive(False)
            self._newTime(0)
            self.slider.set_sensitive(True)
            self.playpause_button.set_sensitive(True)
        self.sourcecombobox.set_active(self._getSmartbinIndex(smartbin))

    def _binAddedCb(self, playground, smartbin):
        # a smartbin was added
        self.sourcelist.append([smartbin.displayname, smartbin])
        self.sourcecombobox.set_sensitive(True)

    def _getSmartbinIndex(self, smartbin):
        # find the index of a smartbin
        # return -1 if it's not in there
        for pos in range(len(self.sourcelist)):
            if self.sourcelist[pos][1] == smartbin:
                return pos
        return -1

    def _binRemovedCb(self, playground, smartbin):
        # a smartbin was removed
        idx = self._getSmartbinIndex(smartbin)
        if idx < 0:
            return
        del self.sourcelist[idx]
        if not self.sourcelist:
            self.sourcecombobox.set_sensitive(False)

    def _currentStateCb(self, playground, state):
        gst.info("current state changed : %s" % state)
        if state == int(gst.STATE_PLAYING):
            if not isinstance(playground.current, SmartDefaultBin) and not self.checktimeoutid:
                gst.info("adding checktime")
                self.checktimeoutid = gobject.timeout_add(300, self._checkTimeCb)
            self.playpause_button.setPause()
        elif state == int(gst.STATE_PAUSED):
            if not isinstance(playground.current, SmartDefaultBin) and not self.checktimeoutid:
                gst.info("adding checktime")
                self.checktimeoutid = gobject.timeout_add(300, self._checkTimeCb)
            self.playpause_button.setPlay()


class ViewerWidget(gtk.DrawingArea):
    """
    Widget for displaying properly GStreamer video sink
    """

    __gsignals__ = {}

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.videosink = None
        self.have_set_xid = False
        self.unset_flags(gtk.DOUBLE_BUFFERED)

    def do_expose_event(self, event):
        """ 'expose-event' override """
        if self.videosink:
            if not self.have_set_xid:
                self.videosink.set_xwindow_id(self.window.xid)
                self.have_set_xid = True
            self.videosink.expose()
        return False


class PlayPauseButton(gtk.Button):
    """ Double state gtk.Button which displays play/pause """

    __gsignals__ = {
        "play" : ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_BOOLEAN, ))
        }

    def __init__(self):
        gtk.Button.__init__(self, label="")
        self.setPlay()
        self.connect('clicked', self._clickedCb)        

    def _clickedCb(self, whatever):
        if not self.playing:
            self.setPause()
        else:
            self.setPlay()
        self.emit("play", self.playing)

    def setPlay(self):
        """ display the play image """
        self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON))
        self.playing = False

    def setPause(self):
        """ display the pause image """
        self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON))
        self.playing = True


class EncodingDialog(GladeWindow):
    """ Encoding dialog box """
    glade_file = "encodingdialog.glade"

    def __init__(self, project):
        GladeWindow.__init__(self)
        self.project = project
        self.bin = project.getBin()
        self.bus = self.bin.get_bus()
        self.bus.add_signal_watch()
        self.eosid = self.bus.connect("message::eos", self._eosCb)
        self.outfile = None
        self.progressbar = self.widgets["progressbar"]
        self.timeoutid = None
        self.rendering = False
        self.settings = project.settings

    def _fileButtonClickedCb(self, button):
        
        dialog = gtk.FileChooserDialog(title="Choose file to render to",
                                       parent=self.window,
                                       buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                                gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT),
                                       action=gtk.FILE_CHOOSER_ACTION_SAVE)
        if self.outfile:
            dialog.set_current_name(self.outfile)
        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.outfile = dialog.get_uri()
            button.set_label(os.path.basename(self.outfile))
        dialog.destroy()

    def _recordButtonClickedCb(self, button):
        if self.outfile and not self.rendering:
            if self.bin.record(self.outfile, self.settings):
                self.timeoutid = gobject.timeout_add(400, self._timeoutCb)
                self.rendering = True
            else:
                self.progressbar.set_text("Couldn't start rendering")

    def _settingsButtonClickedCb(self, button):
        dialog = ExportSettingsDialog(self.settings)
        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.settings = dialog.getSettings()
        dialog.destroy()

    def _timeoutCb(self):
        result, state, pending = self.bin.get_state(0)
        if state == gst.STATE_PLAYING and self.rendering:
            # check time
            value, format = self.bin.query_position(gst.FORMAT_TIME)
            # set progresbar to percentage
            self.progressbar.set_fraction(float(value) / float(self.bin.length))
            
            # display current time in progressbar
            self.progressbar.set_text(time_to_string(value))
            return True
        self.timeoutid = False
        return False

    def do_destroy(self):
        gst.debug("cleaning up...")
        self.bus.remove_signal_watch()
        gobject.source_remove(self.eosid)

    def _eosCb(self, bus, message):
        self.rendering = False
        self.progressbar.set_text("Rendering Finished")
        self.progressbar.set_fraction(1.0)
        gobject.source_remove(self.timeoutid)
        
    def _cancelButtonClickedCb(self, button):
        self.bin.stopRecording()
        if self.timeoutid:
            gobject.source_remove(self.timeoutid)
            self.timeoutid = None
        self.destroy()

