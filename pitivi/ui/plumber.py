#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       ui/plumber.py
#
# Copyright (c) 2005, Edward Hervey <edward@fluendo.com>
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

#
# The plumber takes care of the sinks
#
# This is a required level of abstraction for the many different sinks that
# exist out there
#

import gst
import gst.interfaces
import gconf

gconfvideostring = "/system/gstreamer/0.9/default/videosink"
gconfaudiostring = "/system/gstreamer/0.9/default/audiosink"

def get_video_sink(pitivi):
    """ Returns a video sink bin that can be used in the Discoverer """
    gconf_client = gconf.client_get_default()
    gconfsink = gst.parse_launch(gconf_client.get(gconfvideostring).to_string())

    gconfsink.set_state(gst.STATE_READY)
    
    if not gconfsink.implements_interface(gst.interfaces.XOverlay):
        gconfsink.info("doesn't implement XOverlay interface")
        realsink = gconfsink.get_by_interface(gst.interfaces.XOverlay)
        if not realsink:
            gst.info("%s" % list(gconfsink.elements()))
            gconfsink.warning("couldn't even find an XOverlay within!!!")
        else:
            realsink.info("implements XOverlay interface")
            gconfsink.set_xwindow_id = realsink.set_xwindow_id
            gconfsink.expose = realsink.expose
            
    return gconfsink

def get_audio_sink(pitivi):
    """ Returns an audio sink bin that can be used in the Discoverer """
    gconf_client = gconf.client_get_default()
    gconfsink = gst.parse_launch(gconf_client.get(gconfaudiostring).to_string())
    return gconfsink
