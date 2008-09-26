# PiTiVi , Non-linear video editor
#
#       pitivi/ui/screencast_managerdialog.py
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
import plumber
from pitivi.settings import ExportSettings
from sourcefactories import SourceFactoriesWidget
import dbus
import dbus.service
import dbus.glib
import gobject


class ScreencastManagerDialog(object):

	def __init__(self):
		gst.log("Creating new ScreencastManager Dialog")

		# Create gtk widget using glade model 
		glade_dir = os.path.dirname(os.path.abspath(__file__))
		pool_ui = gtk.glade.XML(os.path.join(glade_dir, "screencast_manager.glade"))
	
		self.window = pool_ui.get_widget("screencast_window")
		self.close_btn = pool_ui.get_widget("btn_close")
		self.ok_btn = pool_ui.get_widget("btn_ok")
		self.screencast_btn = pool_ui.get_widget("btn_screencast")

		self.close_btn.connect("clicked",self.close)
		self.ok_btn.connect("clicked",self.ok)
		self.screencast_btn.connect("toggled",self.screencast)

		# Connect to istanbul dbus service
		try:
			bus = dbus.SessionBus()
            		remote_object = bus.get_object("org.gnome.istanbul", "/state")
            		self.iface = dbus.Interface(remote_object, "org.gnome.istanbul")
		except:
			self.screencast_btn.set_sensitive(False)

	def close(self,w):
		self.window.destroy()

	def ok(self,w):
		self.screencast(None)
		self.close(None)
		

	def screencast(self,w):


		if self.screencast_btn.get_active():
			self.iface.savemode(True)
		else:
			self.iface.savemode(False)

		
