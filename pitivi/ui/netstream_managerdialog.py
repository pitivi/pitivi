# PiTiVi , Non-linear video editor
#
#       pitivi/ui/netstream_managerdialog.py
#
# Copyright (c) 2008, Sarath Lakshman <sarathlakshman@slynux.org>
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

import os
import gtk
import gtk.glade
import gst
import tempfile
from pitivi.sourcelist import SourceList
from pitivi.bin import SmartStreamBin, SinkBin
from pitivi.settings import ExportSettings

class NetstreamManagerDialog(object):

    def __init__(self):
        self.sourcefactories = SourceList()
        self.capture_pipe = None
        self.player = None

        glade_dir = os.path.dirname(os.path.abspath(__file__))
        self.objectpool_ui = gtk.glade.XML(os.path.join(glade_dir, "net_capture.glade"))
        self.stream_window = self.objectpool_ui.get_widget("network_capture")
        self.screen = self.objectpool_ui.get_widget("screen")
        self.capture_btn = self.objectpool_ui.get_widget("capture_btn")
        self.preview_btn = self.objectpool_ui.get_widget("preview_btn")
        self.close_btn = self.objectpool_ui.get_widget("close_btn")
        self.port = self.objectpool_ui.get_widget("port")
        self.address = self.objectpool_ui.get_widget("address")
        self.uri = self.objectpool_ui.get_widget("url")
        self.status = self.objectpool_ui.get_widget("status")

        self.http_radiobtn = self.objectpool_ui.get_widget("protocol")
        self.udp_radiobtn = self.objectpool_ui.get_widget("udp")
        self.rtsp_radiobtn = self.objectpool_ui.get_widget("rtsp")

        self.http_radiobtn.connect("toggled", self.on_protocol_toggled, "http")
        self.udp_radiobtn.connect("toggled", self.on_protocol_toggled, "udp")
        self.rtsp_radiobtn.connect("toggled", self.on_protocol_toggled, "rtsp")
        self.address.connect("changed", self.on_address_port_changed, "address")
        self.port.connect("changed", self.on_address_port_changed, "port")


        self.close_btn.connect("clicked", self.close)
        self.stream_window.connect("destroy", self.close)


        dic = { "on_close_clicked" : self.close,
                "on_preview_btn_clicked" : self.live_pipeline,
                "on_capture_btn_clicked" : self.capture_pipeline }

        self.objectpool_ui.signal_autoconnect(dic)



        self.capture_btn = self.capture_btn.get_children()[0]
        self.capture_btn = self.capture_btn.get_children()[0].get_children()[1]
        self.capture_btn.set_label("Capture")


    # For Setting up audio,video sinks
    def setSinks(self, uri):
        gst.debug("SmartStreamBin player created")
        self.player = SmartStreamBin(uri)
        sink = SinkBin()
        sink.connectSink(self.player, self.player.is_video, self.player.is_audio)
        self.player.set_state(gst.STATE_PLAYING)


        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect('sync-message::element', self.on_sync_message)


    # Create live display pipeline
    def live_pipeline(self, w=None):

        if self.player:
            self.player.set_state(gst.STATE_NULL)

        uri = self.uri.get_text()

        if uri != None :

            if gst.uri_is_valid (uri) is False:
                self.status.set_label("Invalid URI. Please verify.")
                gst.debug("Invalid URI")
                return
            if gst.uri_protocol_is_supported(gst.URI_SRC,
                                             uri.split('://')[0]):
                self.setSinks(uri)
                self.player.set_state(gst.STATE_PLAYING)
                self.status.push(self.status_id, "")
            else:
                self.status.set_label("Unsupported Protocol. Please verify the URI.")
                gst.debug("Unsupported Protocol")



    # Stream capture pipeline
    def capture_pipeline(self, w=None):

        uri = self.uri.get_text()
        if self.capture_btn.get_label() == "Capture":
            if self.player is False and gst.uri_protocol_is_supported(gst.URI_SRC, uri.split('://')[0]) is False :
                self.status.set_label("Unsupported Protocol. Please verify the URI.")
                return
            elif self.player is False:
                self.player.set_state(gst.STATE_NULL)
                self.setSinks(uri)


            gst.debug("recording started")
            self.filepath = 'file://'+tempfile.mktemp()+'.ogg'
            self.player.record(self.filepath, ExportSettings())
            self.capture_btn.set_label("Stop")


        else:
            gst.debug("recording stopped")
            self.player.stopRecording()
            self.sourcefactories.sourcelist.addUris([self.filepath])
            self.capture_btn.set_label("Capture")

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            if self.player:
                self.player.set_state(gst.gst.STATE_NULL)
            self.capture_btn.set_label("Capture")

        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            if self.player:
                self.player.set_state(gst.STATE_NULL)
            self.capture_btn.set_label("Capture")


    def on_sync_message(self, bus, message):
        if message.structure is None :
            return
        message_name = message.structure.get_name()
        if message_name == 'prepare-xwindow-id':
            imagesink = message.src
            imagesink.set_property('force-aspect-ratio', True)
            imagesink.set_xwindow_id(self.screen.window.xid)

    # radio buttons address set callback
    def on_protocol_toggled(self, widget, data=None):
        self.uri.set_text(data+"://"+self.uri.get_text().split('://')[1])

    def on_address_port_changed(self, widget, data=None):
        self.uri.set_text(self.uri.get_text().split('://')[0] + '://' + self.address.get_text() + ['', ':'][self.port.get_text().isdigit()] + self.port.get_text())



    def close(self, w):
        self.stream_window.destroy()
        if self.player:
            self.player.set_state(gst.STATE_NULL)
        if self.capture_pipe:
            self.capture_pipe.set_state(gst.STATE_NULL)
