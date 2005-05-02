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
import gst.interfaces
from pitivi.objectfactory import FileSourceFactory
import pitivi.dnd as dnd

class PitiviViewer(gtk.VBox):
    """ Pitivi's graphical viewer """

    def __init__(self, pitivi):
        self.pitivi = pitivi
        gtk.VBox.__init__(self)
        self._create_gui()
        self._create_sinkthreads()

        # connect to the sourcelist for temp factories
        # TODO remove/replace the signal when closing/opening projects
        self.pitivi.current.sources.connect("tmp_is_ready", self._tmp_is_ready)

        self.pitivi.connect("new-project", self._new_project_cb)

    def _create_sinkthreads(self):
        """ Creates the sink threads for the playground """
        self.videosink = gst.element_factory_make("xvimagesink", "vsink")
        self.audiosink = gst.element_factory_make("alsasink", "asink")
        self.vqueue = gst.element_factory_make("queue", "vqueue")
        self.aqueue = gst.element_factory_make("queue", "aqueue")
        self.vsinkthread = gst.Thread("vsinkthread")
        self.asinkthread = gst.Thread("asinkthread")
        self.vsinkthread.add_many(self.videosink, self.vqueue)
        self.vqueue.link(self.videosink)
        self.vsinkthread.add_ghost_pad(self.vqueue.get_pad("sink"), "sink")
        self.asinkthread.add_many(self.audiosink, self.aqueue)
        self.aqueue.link(self.audiosink)
        self.asinkthread.add_ghost_pad(self.aqueue.get_pad("sink"), "sink")

        self.pitivi.playground.set_video_sink_thread(self.vsinkthread)
        self.pitivi.playground.set_audio_sink_thread(self.asinkthread)
        self.pitivi.playground.connect("current-changed", self._current_playground_changed)

    def _create_gui(self):
        """ Creates the Viewer GUI """
        # drawing area
        self.aframe = gtk.AspectFrame(xalign=0.5, yalign=0.0, ratio=4.0/3.0, obey_child=False)
        self.pack_start(self.aframe, expand=True)
        self.drawingarea = gtk.DrawingArea()
        self.drawingarea.connect_after("expose-event", self._drawingarea_expose_event)
        self.aframe.add(self.drawingarea)
        
        # Buttons/Controls
        bbox = gtk.HBox()
        boxalign = gtk.Alignment(xalign=0.5, yalign=0.5)
        boxalign.add(bbox)
        self.pack_start(boxalign, expand=False)

        self.record_button = gtk.ToolButton(gtk.STOCK_MEDIA_RECORD)
        self.record_button.connect("clicked", self.record_cb)
        bbox.pack_start(self.record_button, expand=False)
        self.rewind_button = gtk.ToolButton(gtk.STOCK_MEDIA_REWIND)
        self.rewind_button.connect("clicked", self.rewind_cb)
        bbox.pack_start(self.rewind_button, expand=False)
        self.back_button = gtk.ToolButton(gtk.STOCK_MEDIA_PREVIOUS)
        self.back_button.connect("clicked", self.back_cb)
        bbox.pack_start(self.back_button, expand=False)
        self.pause_button = gtk.ToolButton(gtk.STOCK_MEDIA_PAUSE)
        self.pause_button.connect("clicked", self.pause_cb)
        bbox.pack_start(self.pause_button, expand=False)
        self.play_button = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("clicked", self.play_cb)
        bbox.pack_start(self.play_button, expand=False)
        self.next_button = gtk.ToolButton(gtk.STOCK_MEDIA_NEXT)
        self.next_button.connect("clicked", self.next_cb)
        bbox.pack_start(self.next_button, expand=False)
        self.forward_button = gtk.ToolButton(gtk.STOCK_MEDIA_FORWARD)
        self.forward_button.connect("clicked", self.forward_cb)
        bbox.pack_start(self.forward_button, expand=False)
        
        # info / time
        infohbox = gtk.HBox()
        self.pack_start(infohbox, expand=False)
        self.infolabel = gtk.Label("info")
        self.timelabel = gtk.Label("time")
        self.timelabel.set_justify(gtk.JUSTIFY_RIGHT)
        infohbox.pack_start(self.infolabel)
        infohbox.pack_start(self.timelabel, expand=False)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.DND_FILESOURCE_TUPLE, dnd.DND_URI_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag_data_received", self._dnd_data_received)

    def play_filesourcefactory(self, factory):
        # TODO
        if not isinstance(factory, FileSourceFactory):
            return
        pass
    
    def _drawingarea_expose_event(self, window, event):
        self.videosink.set_xwindow_id(self.drawingarea.window.xid)
        self.pitivi.playground.play()
        return False

    def _current_playground_changed(self, playground, smartbin):
        if smartbin.width and smartbin.height:
            self.aframe.set_property("ratio", float(smartbin.width) / float(smartbin.height))
        else:
            self.aframe.set_property("ratio", 4.0/3.0)
        self.infolabel.set_text(smartbin.factory.name)

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
        self.pitivi.playground.play_temporary_filesourcefactory(factory)

    def _new_project_cb(self, pitivi, project):
        """ the current project has changed """
        self.pitivi.current.sources.connect("tmp_is_ready", self._tmp_is_ready)
        
    def record_cb(self, button):
        pass

    def rewind_cb(self, button):
        pass

    def back_cb(self, button):
        pass


    def pause_cb(self, button):
        pass

    def play_cb(self, button):
        pass

    def next_cb(self, button):
        pass

    def forward_cb(self, button):
        pass
