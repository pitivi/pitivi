# PiTiVi , Non-linear video editor
#
#       pitivi/ui/webcam_managerdialog.py
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

import gtk
import os
import gtk.glade
import pygst
from pitivi import instance
pygst.require("0.10")
import gst
import tempfile
from gettext import gettext as _
from pitivi.settings import ExportSettings
from sourcefactories import SourceFactoriesWidget
from pitivi.bin import SmartCaptureBin,SinkBin
from pitivi.threads import CallbackThread
from pitivi.playground import PlayGround


class WebcamManagerDialog(object):

	def __init__(self):
		gst.log("Creating new WebcamManager Dialog")

		# Create gtk widget using glade model 
		glade_dir = os.path.dirname(os.path.abspath(__file__))
		self.cam_ui = gtk.glade.XML(os.path.join(glade_dir, "cam_capture.glade"))
		self.cam_window = self.cam_ui.get_widget("cam_capture")
		self.draw_window = self.cam_ui.get_widget("draw_window")
		self.record_btn = self.cam_ui.get_widget("record_btn")
		self.close_btn = self.cam_ui.get_widget("close_btn")

		self.close_btn.connect("clicked",self.close)
		self.record_btn.connect("clicked", self.threaded_recording)
		self.cam_window.connect("destroy",self.close)
		
		self.record_btn = self.record_btn.get_children()[0]
		self.record_btn = self.record_btn.get_children()[0].get_children()[1]
		self.record_btn.set_label("Start Recording")
	
		self.sourcefactories = SourceFactoriesWidget()

		gst.debug("SmartCaptureBin player created")
		self.player = SmartCaptureBin()		
		self.setSinks()
	


		self.player.set_state(gst.STATE_PLAYING)

	# Perform record in a seperate thread
	def threaded_recording(self,w):
		
		CallbackThread(self.do_recording,w).start()


	# Record button action callback
	def do_recording(self, w):
	
		if self.record_btn.get_label() == "Start Recording":
			gst.debug("recording started")
			self.filepath = 'file://'+tempfile.mktemp()+'.ogg'
			self.player.record(self.filepath,ExportSettings())
			self.record_btn.set_label("Stop Recording")
			self.player.set_state(gst.STATE_PLAYING)



		else:
			gst.debug("recording stopped")
			self.player.stopRecording()
			self.sourcefactories.sourcelist.addFiles([self.filepath])
			self.player.set_state(gst.STATE_PLAYING)
			self.record_btn.set_label("Start Recording")
		

	# For Setting up audio,video sinks
	def setSinks(self):
		sink = SinkBin()
		sink.connectSink(self.player,True,True)
		bus = self.player.get_bus()
		bus.add_signal_watch()
		bus.enable_sync_message_emission()
		bus.connect('sync-message::element', self.on_sync_message)

	# Close the Webcamdialog
	def close(self,w):
		self.cam_window.destroy()
		self.player.set_state(gst.STATE_NULL)
		
	# For draw_window syncs
	def on_sync_message(self, bus, message):
		if message.structure is None:
			return
		message_name = message.structure.get_name()
		if message_name == 'prepare-xwindow-id':
			# Assign the viewport
			imagesink = message.src
			imagesink.set_property('force-aspect-ratio', True)
			imagesink.set_xwindow_id(self.draw_window.window.xid)

