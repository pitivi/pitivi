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

videoDevice="/dev/video0"
videoProperties="video/x-raw-yuv,width=640,height=480,framerate=30/1"
videoSink="ximagesink"



class WebcamManagerDialog(object):

	def __init__(self):
		
		global videoDevice, videoProperties, videoSink
		self.sourcefactories = SourceFactoriesWidget()

		glade_dir = os.path.dirname(os.path.abspath(__file__))
		self.cam_ui = gtk.glade.XML(os.path.join(glade_dir, "cam_capture.glade"))
		self.cam_window = self.cam_ui.get_widget("cam_capture")
		self.draw_window = self.cam_ui.get_widget("draw_window")
		self.record_btn = self.cam_ui.get_widget("record_btn")
		self.close_btn = self.cam_ui.get_widget("close_btn")

		self.close_btn.connect("clicked",self.close)
		self.record_btn.connect("clicked", self.do_recording)
		self.cam_window.connect("destroy",self.close)
		
		self.record_btn = self.record_btn.get_children()[0]
		self.record_btn = self.record_btn.get_children()[0].get_children()[1]
		self.record_btn.set_label("Start Recording")
	


		self.player = gst.parse_launch ("v4l2src ! videoscale ! " +videoProperties+" ! ffmpegcolorspace ! queue ! "+videoSink)

		bus = self.player.get_bus()
		bus.add_signal_watch()
		bus.enable_sync_message_emission()
		bus.connect('message', self.on_message)
		bus.connect('sync-message::element', self.on_sync_message)

		
		self.start()
		
		
		self.cam_window.show()

		self.recorder = None

	def close(self,w):
		self.cam_window.destroy()
		self.player.set_state(gst.STATE_NULL)
		if(self.recorder):
			self.recorder.set_state(gst.STATE_NULL)

	# Create live player pipeline
	def start(self):
		time.sleep(1)
		self.player.set_state(gst.STATE_PLAYING)


	# Create Recorder Pipeline callback

	def SetPipelines(self):
		global videoDevice, videoProperties, videoSink

		self.filepath = filename_cam = tempfile.mktemp()

		self.recorder = gst.parse_launch("v4l2src ! videoscale ! "  +videoProperties+ " ! tee name=tee tee. ! ffmpegcolorspace ! videorate  ! theoraenc ! queue ! oggmux name=mux mux. ! queue ! filesink location=" + self.filepath + ".ogg" + " alsasrc ! audiorate ! audioconvert ! vorbisenc ! queue ! mux. tee. ! ffmpegcolorspace ! queue ! "+videoSink)	

		bus = self.recorder.get_bus()
		bus.add_signal_watch()
		bus.enable_sync_message_emission()
		bus.connect('message', self.on_message)
		bus.connect('sync-message::element', self.on_sync_message)


	# Record button callback

	def do_recording(self, w):
		global timeElapsed
		


		if self.record_btn.get_label() == "Start Recording":
			self.SetPipelines()
			self.record_btn.set_label("Stop Recording")
			self.player.set_state(gst.STATE_NULL)
			time.sleep(0)
			self.recorder.set_state(gst.STATE_PLAYING)



		else:
			file_uri = 'file://' + self.filepath + '.ogg'
			
			self.recorder.set_state(gst.STATE_NULL)
			time.sleep(0)
			self.player.set_state(gst.STATE_PLAYING)
			self.sourcefactories.sourcelist.addFiles([file_uri])


			self.record_btn.set_label("Start Recording")


	def on_message(self, bus, message):
		t = message.type
		if t == gst.MESSAGE_EOS:
			self.player.set_state(gst.STATE_NULL)
			if self.recorder != None:
				self.recorder.set_state(gst.STATE_NULL)
			self.record_btn.set_label("Start Recording")
			self.record_btn.set_sensitive(True)
		elif t == gst.MESSAGE_ERROR:
			err, debug = message.parse_error()
			print "Error: %s" % err, debug
			'''gobject.timeout_add(1000, self.ET.set_label, "Error: %s" % err)'''
			self.player.set_state(gst.STATE_NULL)

			if self.recorder != None:
				self.recorder.set_state(gst.STATE_NULL)
			self.record_btn.set_label("Start Recording")
			self.record_btn.set_sensitive(True)


	def on_sync_message(self, bus, message):
		if message.structure is None:
			return
		message_name = message.structure.get_name()
		if message_name == 'prepare-xwindow-id':
			# Assign the viewport
			imagesink = message.src
			imagesink.set_property('force-aspect-ratio', True)
			imagesink.set_xwindow_id(self.draw_window.window.xid)


