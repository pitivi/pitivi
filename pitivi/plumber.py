#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       plumber.py
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
# They should be provided by a generic sink provider

import gobject
import gst
from gst import interfaces

def get_video_sink():
    """ Returns a video sink bin that can be used in the Discoverer """
    autovideosink = gst.element_factory_make("autovideosink")
    autovideosink.realsink = None

    autovideosink.set_state(gst.STATE_READY)

    if not autovideosink.implements_interface(interfaces.XOverlay):
        autovideosink.info("doesn't implement XOverlay interface")
        realsink = autovideosink.get_by_interface(interfaces.XOverlay)
        if not realsink:
            gst.info("%s" % list(autovideosink.elements()))
            autovideosink.warning("couldn't even find an XOverlay within!!!")
        else:
            realsink.info("implements XOverlay interface")
            autovideosink.set_xwindow_id = realsink.set_xwindow_id
            autovideosink.expose = realsink.expose
            autovideosink.realsink = realsink
    else:
        autovideosink.realsink = autovideosink
    # FIXME : YUCK, I'm guessing most of these issues (qos/max-lateness)
    # have been solved since
    if autovideosink.realsink:
        if "force-aspect-ratio"in [prop.name for prop in gobject.list_properties(autovideosink.realsink)]:
            autovideosink.realsink.set_property("force-aspect-ratio", True)
        if "qos"in [prop.name for prop in gobject.list_properties(autovideosink.realsink)]:
            autovideosink.realsink.set_property("qos", False)
        if "max-lateness"in [prop.name for prop in gobject.list_properties(autovideosink.realsink)]:
            autovideosink.realsink.set_property("max-lateness", -1)
    return autovideosink

def get_audio_sink():
    """ Returns an audio sink bin that can be used in the Discoverer """
    autoaudiosink = gst.element_factory_make("autoaudiosink")

    audiosink = gst.Bin("pitivi-audiosink")
    aconv = gst.element_factory_make("audioconvert","audiobin-convert")
    ares = gst.element_factory_make("audioresample", "audiobin-resample")

    audiosink.add(aconv, ares, autoaudiosink)
    aconv.link(ares)
    # FIXME : This is really bad
    # For starters... it means we can't edit/preview multi-channel audio
    # Also, most hardware cards do internal resampling much better
    audiocaps = "audio/x-raw-int,channels=2,rate=44100,depth=16;audio/x-raw-float,channels=2,rate=44100"
    ares.link(autoaudiosink, gst.Caps(audiocaps))

    audiosink.add_pad(gst.GhostPad("sink", aconv.get_pad("sink")))

    return audiosink
