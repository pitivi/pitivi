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
from pitivi.bin import SmartTimelineBin, SmartDefaultBin
from pitivi.objectfactory import FileSourceFactory
import pitivi.dnd as dnd
from pitivi.settings import ExportSettings
from exportsettingswidget import ExportSettingsDialog

def time_to_string(value):
    ms = value / gst.MSECOND
    sec = ms / 1000
    ms = ms % 1000
    min = sec / 60
    sec = sec % 60
    return "%02dm%02ds%03d" % (min, sec, ms)

class PitiviViewer(gtk.VBox):
    """ Pitivi's graphical viewer """

    def __init__(self, pitivi):
        gst.info("New PitiviViewer")
        self.pitivi = pitivi
        gtk.VBox.__init__(self)
        self.current_time = long(0)
        self.current_frame = -1
        self.valuechangedid = 0
        self._create_gui()

        # connect to the sourcelist for temp factories
        # TODO remove/replace the signal when closing/opening projects
        self.pitivi.current.sources.connect("tmp_is_ready", self._tmp_is_ready)

        # Only set the check time timeout in certain cases...
        self.checktimeoutid = 0
        self.pitivi.connect("new-project", self._new_project_cb)
        self.pitivi.playground.connect("current-state", self._current_state_cb)
        self.pitivi.playground.connect("bin-added", self._bin_added_cb)
        self.pitivi.playground.connect("bin-removed", self._bin_removed_cb)

        self.pitivi.current.settings.connect("settings-changed",
                                             self._settings_changed_cb)
        # FIXME : uncomment when gnonlin is ported
        self._add_timeline_to_playground()

    def _create_gui(self):
        """ Creates the Viewer GUI """
        self.set_border_width(5)
        self.set_spacing(5)
        
        # drawing area
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=0.0, ratio=4.0/3.0, obey_child=False)
        self.pack_start(self.aframe, expand=True)
        self.drawingarea = ViewerWidget()
        self.drawingarea.connect_after("realize", self._drawingarea_realize_cb)
        self.aframe.add(self.drawingarea)
        
        # horizontal line
        self.pack_start(gtk.HSeparator(), expand=False)

        # Slider
        self.posadjust = gtk.Adjustment()
        self.slider = gtk.HScale(self.posadjust)
        self.slider.set_draw_value(False)
        self.slider.connect("button-press-event", self._slider_button_press_cb)
        self.slider.connect("button-release-event", self._slider_button_release_cb)
        self.slider.connect("scroll-event", self._slider_scroll_cb)
        self.pack_start(self.slider, expand=False)
        self.moving_slider = False
        
        # Buttons/Controls
        bbox = gtk.HBox()
        boxalign = gtk.Alignment(xalign=0.5, yalign=0.5)
        boxalign.add(bbox)
        self.pack_start(boxalign, expand=False)

        self.record_button = gtk.ToolButton(gtk.STOCK_MEDIA_RECORD)
        self.record_button.connect("clicked", self.record_cb)
        self.record_button.set_sensitive(False)
        bbox.pack_start(self.record_button, expand=False)
        
        self.rewind_button = gtk.ToolButton(gtk.STOCK_MEDIA_REWIND)
        self.rewind_button.connect("clicked", self.rewind_cb)
        self.rewind_button.set_sensitive(False)
        bbox.pack_start(self.rewind_button, expand=False)
        
        self.back_button = gtk.ToolButton(gtk.STOCK_MEDIA_PREVIOUS)
        self.back_button.connect("clicked", self.back_cb)
        self.back_button.set_sensitive(False)
        bbox.pack_start(self.back_button, expand=False)

        self.playpause_button = PlayPauseButton()
        self.playpause_button.connect("play", self._play_button_cb)
        bbox.pack_start(self.playpause_button, expand=False)
        
        self.next_button = gtk.ToolButton(gtk.STOCK_MEDIA_NEXT)
        self.next_button.connect("clicked", self.next_cb)
        self.next_button.set_sensitive(False)
        bbox.pack_start(self.next_button, expand=False)
        
        self.forward_button = gtk.ToolButton(gtk.STOCK_MEDIA_FORWARD)
        self.forward_button.connect("clicked", self.forward_cb)
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
        self.sourcecombobox.connect("changed", self._combobox_changed_cb)
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
                           [dnd.DND_FILESOURCE_TUPLE, dnd.DND_URI_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag_data_received", self._dnd_data_received)

    def _create_sinkthreads(self):
        """ Creates the sink threads for the playground """
        # video elements
        gst.info("Creating video sink")
        self.videosink = plumber.get_video_sink(self.pitivi)
        vsinkthread = gst.Bin('vsinkthread')
        vqueue = gst.element_factory_make('queue')
        vsinkthread.add(self.videosink, vqueue)
        vqueue.link(self.videosink)
        vsinkthread.add_pad(gst.GhostPad("sink", vqueue.get_pad('sink')))

        self.drawingarea.videosink = self.videosink
        self.videosink.set_xwindow_id(self.drawingarea.window.xid)

        # audio elements
        gst.info("Creating audio sink")
        self.audiosink = plumber.get_audio_sink(self.pitivi)
        asinkthread = gst.Bin('asinkthread')
        aqueue = gst.element_factory_make('queue')
        asinkthread.add(self.audiosink, aqueue)
        aqueue.link(self.audiosink)
        asinkthread.add_pad(gst.GhostPad("sink", aqueue.get_pad('sink')))

        # setting sinkthreads on playground
        self.pitivi.playground.set_video_sink_thread(vsinkthread)
        self.pitivi.playground.set_audio_sink_thread(asinkthread)
        self.pitivi.playground.connect("current-changed", self._current_playground_changed)

    def _settings_changed_cb(self, settings):
        gst.info("current project settings changed")
        # modify the ratio if it's the timeline that's playing
        self.aframe.set_property("ratio", float(settings.videowidth) / float(settings.videoheight))

    def _drawingarea_realize_cb(self, drawingarea):
        drawingarea.modify_bg(gtk.STATE_NORMAL, drawingarea.style.black)
        self._create_sinkthreads()
        drawingarea.do_expose_event("hello")
        self.pitivi.playground.play()

    def _slider_button_press_cb(self, slider, event):
        gst.info("button pressed")
        self.moving_slider = True
        if self.checktimeoutid:
            gobject.source_remove(self.checktimeoutid)
            self.checktimeoutid = 0
        self.valuechangedid = slider.connect("value-changed", self._slider_value_changed_cb)
        self.pitivi.playground.current.set_state(gst.STATE_PAUSED)
        return False

    def _slider_button_release_cb(self, slider, event):
        gst.info("slider button release at %s" % time_to_string(long(slider.get_value())))
        self.moving_slider = False
        if self.valuechangedid:
            slider.disconnect(self.valuechangedid)
            self.valuechangedid = 0
        if not self.checktimeoutid:
            gst.debug("adding checktime again")
            self.checktimeoutid = gobject.timeout_add(300, self._check_time)
        self.pitivi.playground.current.set_state(gst.STATE_PLAYING)
        return False

    def _slider_value_changed_cb(self, slider):
        """ seeks when the value of the slider has changed """
        value = long(slider.get_value())
        gst.info(time_to_string(value))
        self._new_time(value)
        self.pitivi.playground.seek_in_current(value)

    def _slider_scroll_cb(self, slider, event):
        # calculate new seek position
        if self.current_frame == -1:
            # time scrolling, 0.5s forward/backward
            if event.direction in [gtk.gdk.SCROLL_LEFT, gtk.gdk.SCROLL_DOWN]:
                seekvalue = max(self.current_time - gst.SECOND / 2, 0)
            else:
                seekvalue = min(self.current_time + gst.SECOND / 2, self.pitivi.playground.current.length)
            self.pitivi.playground.seek_in_current(seekvalue)
        else:
            # frame scrolling, frame by frame
            gst.info("scroll direction:%s" % event.direction)
            if event.direction in [gtk.gdk.SCROLL_LEFT, gtk.gdk.SCROLL_DOWN]:
                gst.info("scrolling backward")
                seekvalue = max(self.current_frame - 1, 0)
            else:
                gst.info("scrolling forward")
                seekvalue = min(self.current_frame + 1, self.pitivi.playground.current.length)
            self.pitivi.playground.seek_in_current(seekvalue, gst.FORMAT_DEFAULT)

    def _check_time(self):
        # check time callback
        gst.log("checking time")
        if self.pitivi.playground.current == self.pitivi.playground.default:
            return True
        # don't check time if the timeline is not playing
        cur = self.current_time
        currentframe = self.current_frame
        if True: #not isinstance(self.pitivi.playground.current, SmartTimelineBin):
            pending, state, result = self.pitivi.playground.current.get_state(10)
            if not state in [gst.STATE_PAUSED, gst.STATE_PLAYING]:
                return
            try:
                cur, format = self.pitivi.playground.current.query_position(gst.FORMAT_TIME)
            except:
                self.pitivi.playground.current.warning("couldn't get position")
                cur = 0

            gst.info("about to conver %s to GST_FORMAT_DEFAULT" % cur)
            try:
                format, currentframe = self.videosink.query_convert(gst.FORMAT_TIME, cur, gst.FORMAT_DEFAULT)
            except:
                gst.info("convert query failed")

        # if the current_time or the length has changed, update time
        if not float(self.pitivi.playground.current.length) == self.posadjust.upper or not cur == self.current_time or not currentframe == self.current_frame:
            self.posadjust.upper = float(self.pitivi.playground.current.length)
            self._new_time(cur, currentframe)
        return True

    def _new_time(self, value, frame=-1):
        gst.info("value:%d, frame:%d" % (value, frame))
        self.current_time = value
        self.current_frame = frame
        self.timelabel.set_text(time_to_string(value) + " / " + time_to_string(self.pitivi.playground.current.length))
        if not self.moving_slider:
            self.posadjust.set_value(float(value))
        return False

    def _combobox_changed_cb(self, cbox):
        # selected another source
        idx = cbox.get_active()
        # get the corresponding smartbin
        smartbin = self.sourcelist[idx][1]
        if not self.pitivi.playground.current == smartbin:
            self.pitivi.playground.switch_to_pipeline(smartbin)

    def _get_smartbin_index(self, smartbin):
        # find the index of a smartbin
        # return -1 if it's not in there
        for pos in range(len(self.sourcelist)):
            if self.sourcelist[pos][1] == smartbin:
                return pos
        return -1

    def _bin_added_cb(self, playground, smartbin):
        # a smartbin was added
        self.sourcelist.append([smartbin.displayname, smartbin])
        self.sourcecombobox.set_sensitive(True)

    def _bin_removed_cb(self, playground, smartbin):
        # a smartbin was removed
        idx = self._get_smartbin_index(smartbin)
        if idx < 0:
            return
        del self.sourcelist[idx]
        if len(self.sourcelist) == 0:
            self.sourcecombobox.set_sensitive(False)

    def _current_playground_changed(self, playground, smartbin):
        if smartbin.width and smartbin.height:
            self.aframe.set_property("ratio", float(smartbin.width) / float(smartbin.height))
        else:
            self.aframe.set_property("ratio", 4.0/3.0)
        if not smartbin == playground.default:
            if isinstance(smartbin, SmartTimelineBin):
##                 start = smartbin.project.timeline.videocomp.start
##                 stop = smartbin.project.timeline.videocomp.stop
                gst.info("switching to Timeline, setting duration to %s" % (gst.TIME_ARGS(smartbin.project.timeline.videocomp.duration)))
                self.posadjust.upper = float(smartbin.project.timeline.videocomp.duration)
                self.record_button.set_sensitive(True)
            else:
                self.posadjust.upper = float(smartbin.factory.length)
                self.record_button.set_sensitive(False)
            self._new_time(0)
        self.sourcecombobox.set_active(self._get_smartbin_index(smartbin))

    def _dnd_data_received(self, widget, context, x, y, selection, targetType, time):
        gst.info("context:%s, targetType:%s" % (context, targetType))
        if targetType == dnd.DND_TYPE_URI_LIST:
            uri = selection.data.strip().split("\n")[0].strip()
        elif targetType == dnd.DND_TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            return
        gst.info("got file:%s" % uri)
        if uri in self.pitivi.current.sources:
            self.pitivi.playground.play_temporary_filesourcefactory(self.pitivi.current.sources[uri])
        else:
            self.pitivi.current.sources.add_tmp_uri(uri)

    def _tmp_is_ready(self, sourcelist, factory):
        """ the temporary factory is ready, we can know set it to play """
        gst.info("%s" % factory)
        self.pitivi.playground.play_temporary_filesourcefactory(factory)

    def _new_project_cb(self, pitivi, project):
        """ the current project has changed """
        self.pitivi.current.sources.connect("tmp_is_ready", self._tmp_is_ready)
        self.pitivi.current.settings.connect("settings-changed", self._settings_changed_cb)
        
    def _add_timeline_to_playground(self):
        gst.info("")
        self.pitivi.playground.add_pipeline(self.pitivi.current.get_bin())

    def record_cb(self, button):
        win = EncodingDialog(self.pitivi.current)
        win.show()

    def rewind_cb(self, button):
        pass

    def back_cb(self, button):
        pass


    def _play_button_cb(self, button, isplaying):
        if isplaying:
            self.pitivi.playground.play()
        else:
            self.pitivi.playground.pause()

    def next_cb(self, button):
        pass

    def forward_cb(self, button):
        pass

    def _current_state_cb(self, playground, state):
        gst.info("current state changed : %s" % state)
        if state == int(gst.STATE_PLAYING):
            if not isinstance(playground.current, SmartDefaultBin) and not self.checktimeoutid:
                gst.info("adding checktime")
                self.checktimeoutid = gobject.timeout_add(300, self._check_time)
            self.playpause_button.set_pause()
        elif state == int(gst.STATE_PAUSED):
            if not isinstance(playground.current, SmartDefaultBin) and not self.checktimeoutid:
                gst.info("adding checktime")
                self.checktimeoutid = gobject.timeout_add(300, self._check_time)
            self.playpause_button.set_play()

gobject.type_register(PitiviViewer)

class ViewerWidget(gtk.DrawingArea):

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.videosink = None
        self.have_set_xid = False
        self.unset_flags(gtk.DOUBLE_BUFFERED)

    def do_expose_event(self, event):
        if self.videosink:
            if not self.have_set_xid:
                self.videosink.set_xwindow_id(self.window.xid)
                self.have_set_xid = True
            self.videosink.expose()
        return False

gobject.type_register(ViewerWidget)

class PlayPauseButton(gtk.Button):

    __gsignals__ = {
        "play" : ( gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_BOOLEAN, ))
        }

    def __init__(self):
        gtk.Button.__init__(self, label="")
        self.set_play()
        self.connect('clicked', self._clicked)        

    def _clicked(self, whatever):
        print "clicked"
        if not self.playing:
            self.set_pause()
        else:
            self.set_play()
        self.emit("play", self.playing)

    def set_play(self):
        """ display the play image """
        self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON))
        self.playing = False

    def set_pause(self):
        """ display the pause image """
        self.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON))
        self.playing = True

gobject.type_register(PlayPauseButton)

class EncodingDialog(GladeWindow):
    glade_file = "encodingdialog.glade"

    def __init__(self, project):
        GladeWindow.__init__(self)
        self.project = project
        self.bin = project.get_bin()
        self.bin.connect("eos", self._eos_cb)
        self.outfile = None
        self.progressbar = self.widgets["progressbar"]
        self.timeoutid = None
        self.rendering = False
        self.settings = project.settings

    def filebutton_clicked(self, button):
        
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

    def recordbutton_clicked(self, button):
        if self.outfile and not self.rendering:
            self.bin.record(self.outfile, self.settings)
            self.timeoutid = gobject.timeout_add(400, self._timeout_cb)
            self.rendering = True

    def settingsbutton_clicked(self, button):
        dialog = ExportSettingsDialog(self.settings)
        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.settings = dialog.get_settings()
        dialog.destroy()

    def _timeout_cb(self):
        result, state, pending = self.bin.get_state(0)
        if state == gst.STATE_PLAYING and self.rendering:
            # check time
            value = self.bin.source.query(gst.QUERY_POSITION,
                                          gst.FORMAT_TIME)
            # set progresbar to percentage
            self.progressbar.set_fraction(float(value) / float(self.bin.length))
            
            # display current time in progressbar
            self.progressbar.set_text(time_to_string(value))
            return True
        self.timeoutid = False
        return False

    def _eos_cb(self, bin):
        self.rendering = False
        self.progressbar.set_text("Rendering Finished")
        self.progressbar.set_fraction(1.0)
        gobject.source_remove(self.timeoutid)
        
    def cancelbutton_clicked(self, button):
        self.bin.stop_recording()
        if self.timeoutid:
            gobject.source_remove(self.timeoutid)
            self.timeoutid = None
        self.destroy()
        
gobject.type_register(EncodingDialog)
