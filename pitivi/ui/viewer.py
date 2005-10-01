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
import gconf
import pango
import gst.interfaces
from glade import GladeWindow
from pitivi.bin import SmartTimelineBin
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
        self.gconf_client = gconf.client_get_default()
        self._create_gui()

        # connect to the sourcelist for temp factories
        # TODO remove/replace the signal when closing/opening projects
        self.pitivi.current.sources.connect("tmp_is_ready", self._tmp_is_ready)

        gobject.timeout_add(500, self._check_time)
        self.pitivi.connect("new-project", self._new_project_cb)
        self.pitivi.playground.connect("current-state", self._current_state_cb)
        self.pitivi.playground.connect("bin-added", self._bin_added_cb)
        self.pitivi.playground.connect("bin-removed", self._bin_removed_cb)

        self.pitivi.current.settings.connect("settings-changed",
                                             self._settings_changed_cb)
        # FIXME : uncomment when gnonlin is ported
        # self._add_timeline_to_playground()

    def _create_gui(self):
        """ Creates the Viewer GUI """
        self.set_border_width(5)
        self.set_spacing(5)
        
        # drawing area
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=0.0, ratio=4.0/3.0, obey_child=False)
        self.pack_start(self.aframe, expand=True)
        self.drawingarea = ViewerWidget()
##         self.drawingarea = gtk.DrawingArea()
##         self.drawingarea.connect("expose-event", self._drawingarea_expose_event)
        self.drawingarea.connect_after("realize", self._drawingarea_realize_cb)
##         self.drawingarea.connect("configure-event", self._drawingarea_configure_event)
        self.aframe.add(self.drawingarea)
        
        # horizontal line
        self.pack_start(gtk.HSeparator(), expand=False)

        # Slider
        self.posadjust = gtk.Adjustment()
        self.slider = gtk.HScale(self.posadjust)
        self.slider.set_draw_value(False)
        self.slider.connect("button-press-event", self._slider_button_press_cb)
        self.slider.connect("button-release-event", self._slider_button_release_cb)
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
        
        self.pause_button = gtk.ToggleToolButton(gtk.STOCK_MEDIA_PAUSE)
        self.pause_button.connect("clicked", self.pause_cb)
        bbox.pack_start(self.pause_button, expand=False)
        
        self.play_button = gtk.ToggleToolButton(gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("clicked", self.play_cb)
        bbox.pack_start(self.play_button, expand=False)
        
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
        vsink = self.gconf_client.get("/system/gstreamer/0.9/default/videosink").to_string()
        self.videosink = gst.parse_launch(vsink)
        self.vqueue = gst.element_factory_make("queue", "vqueue")
        self.vqueue.set_property("max-size-time", long(10 * gst.SECOND))
        self.vqueue.set_property("max-size-bytes", 10000000)
        self.vsinkthread = gst.Bin("vsinkthread")
        self.vsinkthread.add(self.videosink, self.vqueue)

        # FIXME : hack for ximagesink
        if vsink == "ximagesink":
            gst.warning("Adding videoscale and ffmpegcolorspace for ximagesink")
            vscale = gst.element_factory_make("videoscale")
            csp = gst.element_factory_make("ffmpegcolorspace")
            print vscale, csp
            self.vsinkthread.add(vscale, csp)
            self.vqueue.link(vscale)
            vscale.link(csp)
            csp.link(self.videosink)
        else:
            gst.info("linking vqueue to videosink")
            self.vqueue.link(self.videosink)
        self.vsinkthread.add_pad(gst.GhostPad("sink", self.vqueue.get_pad("sink")))

        self.drawingarea.videosink = self.videosink
        self.videosink.set_xwindow_id(self.drawingarea.window.xid)

        # audio elements
        gst.info("Creating audio sink")
        aconv = gst.element_factory_make("audioconvert", "aconv")
        self.audiosink = gst.parse_launch(self.gconf_client.get("/system/gstreamer/0.9/default/audiosink").to_string())
        
        self.aqueue = gst.element_factory_make("queue", "aqueue")
        self.aqueue.set_property("max-size-time", long(10 * gst.SECOND))
        self.asinkthread = gst.Bin("asinkthread")
        
        self.asinkthread.add(self.audiosink, self.aqueue, aconv)
        gst.info("Linking aconv->aqueue->audiosink")
        aconv.link(self.aqueue)
        self.aqueue.link(self.audiosink)
        self.asinkthread.add_pad(gst.GhostPad("sink", aconv.get_pad("sink")))
##         gst.info("Linking aqueue->aconv->audiosink")
##         self.aqueue.link(aconv)
##         aconv.link(self.audiosink)
##         self.asinkthread.add_pad(gst.GhostPad("sink", self.aqueue.get_pad("sink")))

        # setting sinkthreads on playground
        self.pitivi.playground.set_video_sink_thread(self.vsinkthread)
        self.pitivi.playground.set_audio_sink_thread(self.asinkthread)
        self.pitivi.playground.connect("current-changed", self._current_playground_changed)

    def _settings_changed_cb(self, settings):
        print "current project settings changed"
        # modify the ratio if it's the timeline that's playing
        self.aframe.set_property("ratio", float(settings.videowidth) / float(settings.videoheight))

    def _drawingarea_realize_cb(self, drawingarea):
        drawingarea.modify_bg(gtk.STATE_NORMAL, drawingarea.style.black)
        self._create_sinkthreads()
        self.pitivi.playground.play()
        print drawingarea.flags()
        print drawingarea.window.get_events()

    def _slider_button_press_cb(self, slider, event):
        print "slider button_press"
        self.moving_slider = True
        return False

    def _slider_button_release_cb(self, slider, event):
        print "slider button release at", time_to_string(long(slider.get_value()))
        self.moving_slider = False

        self.pitivi.playground.seek_in_current(long(slider.get_value()))
        return False

    def _check_time(self):
        # check time callback
        gst.debug("checking time")
        if self.pitivi.playground.current == self.pitivi.playground.default:
            return True
        # don't check time if the timeline is not playing
        cur = self.current_time
        if not isinstance(self.pitivi.playground.current, SmartTimelineBin):
            #pending, state, result = self.pitivi.playground.current.get_state(0.1)
            if True:#state == gst.STATE_PLAYING:
                #        if not (isinstance(self.pitivi.playground.current, SmartTimelineBin) and not self.pitivi.playground.state == gst.STATE_PLAYING):
                res = self.pitivi.playground.current.query_position(gst.FORMAT_TIME)
                if not res:
                    return True
                cur, end, format = res
        # if the current_time or the length has changed, update time
        if not float(self.pitivi.playground.current.length) == self.posadjust.upper or not cur == self.current_time:
            self.posadjust.upper = float(self.pitivi.playground.current.length)
            self._new_time(cur)
        return True

    def _new_time(self, value):
        self.current_time = value
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
                start = smartbin.project.timeline.videocomp.start
                stop = smartbin.project.timeline.videocomp.stop
                self.posadjust.upper = float(stop - start)
                self.record_button.set_sensitive(True)
            else:
                self.posadjust.upper = float(smartbin.factory.length)
                self.record_button.set_sensitive(False)
            self._new_time(0)
        self.sourcecombobox.set_active(self._get_smartbin_index(smartbin))

    def _dnd_data_received(self, widget, context, x, y, selection, targetType, time):
        print "data received in viewer, type:", targetType
        if targetType == dnd.DND_TYPE_URI_LIST:
            uri = selection.data.strip().split("\n")[0].strip()
        elif targetType == dnd.DND_TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            return
        print "got file:", uri
        if uri in self.pitivi.current.sources:
            self.pitivi.playground.play_temporary_filesourcefactory(self.pitivi.current.sources[uri])
        else:
            self.pitivi.current.sources.add_tmp_uri(uri)

    def _tmp_is_ready(self, sourcelist, factory):
        """ the temporary factory is ready, we can know set it to play """
        print "tmp_is_ready", factory
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


    def pause_cb(self, button):
        print "pause_cb"
        if self.pause_button.get_active():
            #self.pause_button.set_active(False)
            self.pitivi.playground.pause()

    def play_cb(self, button):
        print "play_cb"
        if self.play_button.get_active():
            #self.play_button.set_active(False)
            self.pitivi.playground.play()

    def next_cb(self, button):
        pass

    def forward_cb(self, button):
        pass

    def _current_state_cb(self, playground, state):
        print "current state changed", state
        if state == int(gst.STATE_PLAYING):
            self.play_button.set_active(True)
            self.pause_button.set_active(False)
        elif state == int(gst.STATE_PAUSED):
            self.pause_button.set_active(True)
            self.play_button.set_active(False)
        elif state == int(gst.STATE_READY):
            self.play_button.set_active(False)
            self.pause_button.set_active(False)

gobject.type_register(PitiviViewer)

class ViewerWidget(gtk.DrawingArea):

    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.videosink = None
        self.have_set_xid = False

    def do_expose_event(self, event):
        if self.videosink:
            self.window.draw_rectangle(self.style.white_gc,
                                       True, 0, 0,
                                       self.allocation.width,
                                       self.allocation.height)
            if not self.have_set_xid:
                self.videosink.set_xwindow_id(self.window.xid)
                self.have_set_xid = True
            #self.videosink.expose()
        return True

gobject.type_register(ViewerWidget)

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
        result, state, pending = self.bin.get_state(0.0)
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
