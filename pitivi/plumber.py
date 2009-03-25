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

import gst
from gst import interfaces
from pitivi.factories.base import SinkFactory

class DefaultVideoSink(SinkFactory):

    def __init__(self, *args, **kwargs):
        SinkFactory.__init__(self, *args, **kwargs)
        self.max_bins = 1
        self._xid = 0
        self._cachedsink = None
        self._realsink = None
        self.sync = True

    def _makeBin(self, input_stream=None):
        """ Returns a video sink bin"""
        if self._cachedsink != None:
            self.debug("Returning cached sink")
            return self._cachedsink

        autovideosink = gst.element_factory_make("autovideosink")
        autovideosink.set_state(gst.STATE_READY)

        if not autovideosink.implements_interface(interfaces.XOverlay):
            autovideosink.info("doesn't implement XOverlay interface")
            self._realsink = autovideosink.get_by_interface(interfaces.XOverlay)
            if not self._realsink:
                self.info("%s", list(autovideosink.elements()))
                autovideosink.warning("couldn't even find an XOverlay within!!!")
            else:
                self._realsink.info("implements XOverlay interface")
                autovideosink.set_xwindow_id = self._realsink.set_xwindow_id
                autovideosink.expose = self._realsink.expose
        else:
            self._realsink = autovideosink
        # FIXME : YUCK, I'm guessing most of these issues (qos/max-lateness)
        # have been solved since
        if self._realsink:
            props = list(self._realsink.props)
            if "force-aspect-ratio"in [prop.name for prop in props]:
                self._realsink.set_property("force-aspect-ratio", True)

            self._realsink.props.sync = self.sync

        if self._xid != 0:
            self._realsink.set_xwindow_id(self._xid)

        self._cachedsink = autovideosink
        return autovideosink

    def _releaseBin(self, bin, *args):
        if bin == self._cachedsink:
            self._realsink = None
            self._cachedsink = None
            self._xid = 0

    def set_window_xid(self, xid):
        if self._xid != 0:
            return
        self._xid = xid
        if self._cachedsink:
            self._cachedsink.set_xwindow_id(self._xid)

    def setSync(self, sync=True):
        self.debug("sync:%r", sync)
        if self.sync == sync:
            return
        self.sync = sync
        self.debug("_realsink:%r", self._realsink)
        if self._realsink:
            self._realsink.props.sync = self.sync

class DefaultAudioSink(SinkFactory):

    def __init__(self, *args, **kwargs):
        SinkFactory.__init__(self, *args, **kwargs)
        self.max_bins = 1
        self._cachedsink = None
        self._realsink = None
        self.sync = True

    def _makeBin(self, input_stream=None):
        """ Returns an audio sink bin that can be used in the Discoverer """
        if self._cachedsink != None:
            self.debug("Returning cached sink")
            return self._cachedsink
        autoaudiosink = gst.element_factory_make("autoaudiosink")

        autoaudiosink.set_state(gst.STATE_READY)
        self._realsink = find_recursive_element(autoaudiosink, gst.BaseSink)
        self._realsink.props.sync = self.sync

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

        self._cachedsink = audiosink
        return audiosink

    def _releaseBin(self, bin, *args):
        if bin == self._cachedsink:
            self._realsink = None
            self._cachedsink = None

    def setSync(self, sync=True):
        self.debug("sync:%r", sync)
        if self.sync == sync:
            return
        self.sync = sync
        self.debug("_realsink:%r", self._realsink)
        if self._realsink:
            self._realsink.props.sync = self.sync

def find_recursive_element(bin, typ):
    if not isinstance(bin, gst.Bin):
        if isinstance(bin, typ):
            return bin
        return None
    for elt in bin.elements():
        if isinstance(elt, typ):
            return elt
        if isinstance(elt, gst.Bin):
            r = find_recursive_element(elt, typ)
            if r:
                return r
    return None
