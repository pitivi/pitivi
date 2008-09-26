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
import pango
import gobject
import pygst
import time
pygst.require("0.10")
import gst
import tempfile
from gettext import gettext as _

from sourcefactories import SourceFactoriesWidget


class NetstreamManagerDialog(object):

	def __init__(self):
		
		self.sourcefactories = SourceFactoriesWidget()
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


		self.http_radiobtn = self.objectpool_ui.get_widget("protocol")
		self.udp_radiobtn = self.objectpool_ui.get_widget("udp")
		self.rtsp_radiobtn = self.objectpool_ui.get_widget("rtsp")

		self.http_radiobtn.connect("toggled",self.on_protocol_toggled,"http")
		self.udp_radiobtn.connect("toggled",self.on_protocol_toggled,"udp")
		self.rtsp_radiobtn.connect("toggled",self.on_protocol_toggled,"rtsp")
		self.address.connect("changed",self.on_address_port_changed,"address")
		self.port.connect("changed",self.on_address_port_changed,"port")


		self.close_btn.connect("clicked",self.close)
		self.stream_window.connect("destroy",self.close)

	
		dic = { "on_close_clicked" : self.close, "on_preview_btn_clicked":self.live_pipeline,"on_capture_btn_clicked":self.capture}

		self.objectpool_ui.signal_autoconnect(dic)



		self.capture_btn = self.capture_btn.get_children()[0]
		self.capture_btn = self.capture_btn.get_children()[0].get_children()[1]
		self.capture_btn.set_label("Capture")
	
		
	# Create live display pipeline
	def live_pipeline(self,w=None):

		if self.player:
			self.player.set_state(gst.STATE_NULL)

		if self.uri.get_text() != None :
			self.player =  gst.parse_launch( self.uri.get_text() + " ! decodebin name=dbin dbin. ! queue ! ffmpegcolorspace ! autovideosink  dbin. ! queue ! audioconvert ! alsasink ")
		
			bus = self.player.get_bus()
			bus.add_signal_watch()
			bus.enable_sync_message_emission()
			bus.connect('message',self.on_message)
			bus.connect('sync-message::element',self.on_sync_message)
			self.player.set_state(gst.STATE_PLAYING)



	# Stream capture pipeline
	def capture_pipeline(self):

		self.filepath = tempfile.mktemp()
		self.file_uri = 'file://' + self.filepath + '.ogg'


		if self.uri.get_text() != None and len(self.uri.get_text().split('://')[1]) > 0 :
			if self.player:
				self.player.set_state(gst.STATE_NULL)
			self.capture_pipe = gst.parse_launch(self.uri.get_text() + " ! tee name=tee ! decodebin name=dbin ! queue !  ffmpegcolorspace ! autovideosink dbin. ! queue ! audioconvert ! queue ! alsasink tee. ! queue ! filesink location="+self.filepath+".ogg")		

			bus = self.capture_pipe.get_bus()
			bus.add_signal_watch()
			bus.enable_sync_message_emission()
			bus.connect('message',self.on_message)
			bus.connect('sync-message::element',self.on_sync_message)
			self.capture_pipe.set_state(gst.STATE_PLAYING)

			return True
		else:
			return False


	def capture(self,w):
			
		

		self.uri_stream = self.uri.get_text()

		if self.capture_btn.get_label() == "Capture" :
			
			if self.capture_pipeline():
				self.capture_btn.set_label("Stop")
		else:
			self.capture_btn.set_label("Capture")
			self.capture_pipe.set_state(gst.STATE_NULL)
			self.live_pipeline()
			self.sourcefactories.sourcelist.addFiles([self.file_uri])


	def on_message(self,bus,message):
		t = message.type
		if t == gst.MESSAGE_EOS:
			if self.player:
				self.player.set_state(gst.gst.STATE_NULL)
			self.capture_btn.set_label("Capture")

		elif t == gst.MESSAGE_ERROR:
			err,debug = message.parse_error()
			print "Error: %s" %err, debug
			if self.player:
				self.player.set_state(gst.STATE_NULL)
			self.capture_btn.set_label("Capture")


	def on_sync_message(self,bus,message):
		if message.structure is None :
			return
		message_name = message.structure.get_name()
		if message_name == 'prepare-xwindow-id':
			imagesink = message.src
			imagesink.set_property('force-aspect-ratio',True)
			imagesink.set_xwindow_id(self.screen.window.xid)
			
			
	# radio buttons address set callback
	def on_protocol_toggled(self,widget,data=None):
		self.uri.set_text(data+"://"+self.uri.get_text().split('://')[1])
			
	def on_address_port_changed(self,widget,data=None):
		self.uri.set_text(self.uri.get_text().split('://')[0] + '://' + self.address.get_text() + ['',':'][self.port.get_text().isdigit()] + self.port.get_text())



	def close(self,w):
		self.stream_window.destroy()
		if self.player:
			self.player.set_state(gst.STATE_NULL)
		if self.capture_pipe:
			self.capture_pipe.set_state(gst.STATE_NULL)

	
