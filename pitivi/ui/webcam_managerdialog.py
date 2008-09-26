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
from pitivi import instance
pygst.require("0.10")
import gst
import tempfile
from gettext import gettext as _
import plumber
from pitivi.settings import ExportSettings
from sourcefactories import SourceFactoriesWidget
from pitivi.bin import SmartCaptureBin
from pitivi.playground import PlayGround



class WebcamManagerDialog(object):

	def __init__(self):
	

		# Create gtk widget using glade model 
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
	
		self.sourcefactories = SourceFactoriesWidget()

		self.player = SmartCaptureBin()		


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
		self.player.setVideoSinkThread(vsinkthread)

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
		self.player.setAudioSinkThread(asinkthread)
	
		bus = self.player.get_bus()
		bus.add_signal_watch()
		bus.enable_sync_message_emission()
		bus.connect('sync-message::element', self.on_sync_message)

		self.player.set_state(gst.STATE_PLAYING)



	def do_recording(self, w):
	
		if self.record_btn.get_label() == "Start Recording":
			self.player.record("file:///home/slynux/cool.ogg",ExportSettings())
			self.record_btn.set_label("Stop Recording")
			self.player.set_state(gst.STATE_PLAYING)



		else:
			self.player.stopRecording()
			self.sourcefactories.sourcelist.addFiles(["file:///home/slynux/cool.ogg"])


			self.record_btn.set_label("Start Recording")


	def close(self,w):
		self.cam_window.destroy()
		self.player.set_state(gst.STATE_NULL)
		

	def on_sync_message(self, bus, message):
		if message.structure is None:
			return
		message_name = message.structure.get_name()
		if message_name == 'prepare-xwindow-id':
			# Assign the viewport
			imagesink = message.src
			imagesink.set_property('force-aspect-ratio', True)
			imagesink.set_xwindow_id(self.draw_window.window.xid)

