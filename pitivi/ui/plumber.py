#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       ui/plumber.py
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

"""
Convenience functions for creating the output media sinks
"""

#
# The plumber takes care of the sinks
#
# This is a required level of abstraction for the many different sinks that
# exist out there
#

import gobject
import gst
import gst.interfaces

def get_video_sink():
    """ Returns a video sink bin that can be used in the Discoverer """
    try:
        gconfsink = gst.element_factory_make("gconfvideosink")
    except:
        gconfsink = gst.element_factory_make("autovideosink")
    gconfsink.realsink = None

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
            gconfsink.realsink = realsink
    else:
        gconfsink.realsink = gconfsink
    if gconfsink.realsink:
        if "force-aspect-ratio"in [prop.name for prop in gobject.list_properties(gconfsink.realsink)]:
            gconfsink.realsink.set_property("force-aspect-ratio", True)
        if "qos"in [prop.name for prop in gobject.list_properties(gconfsink.realsink)]:
            gconfsink.realsink.set_property("qos", False)
        if "max-lateness"in [prop.name for prop in gobject.list_properties(gconfsink.realsink)]:
            gconfsink.realsink.set_property("max-lateness", -1)
    return gconfsink

def get_audio_sink():
    """ Returns an audio sink bin that can be used in the Discoverer """
    try:
        gconfsink = gst.element_factory_make("gconfaudiosink")
    except:
        gconfsink = gst.element_factory_make("autoaudiosink")
    return gconfsink
