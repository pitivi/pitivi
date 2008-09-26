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

from sourcefactories import SourceFactoriesWidget
from pitivi.bin import *
from pitivi.playground import PlayGround
import plumber



class WebcamManagerDialog(object):

	def __init__(self):
		
		player = SmartCaptureBin()		
		instance.PiTiVi.playground._playTemporaryBin(player)

	
