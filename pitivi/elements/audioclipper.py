# PiTiVi , Non-linear video editor
#
#       pitivi/elements/audioclipper.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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
Audio clipping element
"""

import gobject
import gst
import gst.interfaces
import gst.audio
from pitivi.utils import data_probe

class AudioClipper(gst.Element):

    __gstdetails__ = (
        "Audio clipper",
        "Generic/Audio",
        "Clip audio buffers according to segments",
        "Edward Hervey <bilboed@bilboed.com>"
        )

    _srctemplate = gst.PadTemplate("src", gst.PAD_SRC, gst.PAD_ALWAYS,
                                   gst.Caps("audio/x-raw-int;audio/x-raw-float"))
    _sinktemplate = gst.PadTemplate("sink", gst.PAD_SINK, gst.PAD_ALWAYS,
                        gst.Caps("audio/x-raw-int;audio/x-raw-float"))

    __gsttemplates__ = (_srctemplate, _sinktemplate)

    def __init__(self):
        gst.Element.__init__(self)
        # add the source/sink pads
        self.srcpad = gst.Pad(self._srctemplate)
        self.sinkpad = gst.Pad(self._sinktemplate)
        self.sinkpad.set_chain_function(self._chain)
        self.sinkpad.set_event_function(self._sinkevent)
        self.sinkpad.set_setcaps_function(self._setcaps)
        self.add_pad(self.sinkpad)
        self.add_pad(self.srcpad)
        self.segment = gst.Segment()
        self.segment.init(gst.FORMAT_UNDEFINED)

    def _setcaps(self, sinkpad, caps):
        self.debug("caps %s" % caps.to_string())
        res = self.srcpad.get_peer().set_caps(caps)
        self.debug("res %r" % res)
        if res is True:
            self.rate = caps[0]["rate"]
            self.bps = (caps[0]["width"] / 8) * caps[0]["channels"]
            self.bitrate = self.rate * self.bps
            self.debug("rate:%d, bps:%d" % (self.rate, self.bps))
        return res

    def _sinkevent(self, pad, event):
        self.debug("event:%r" % event)
        if event.type == gst.EVENT_NEWSEGMENT:
            self.debug("%r" % list(event.parse_new_segment()))
            self.segment.set_newsegment(*event.parse_new_segment())
        elif event.type == gst.EVENT_FLUSH_STOP:
            self.segment.init(gst.FORMAT_UNDEFINED)
        return self.srcpad.push_event(event)

    def _chain(self, pad, inbuf):
        pad.debug("inbuf %r %s %s" % (inbuf, gst.TIME_ARGS(inbuf.timestamp),
                                      gst.TIME_ARGS(inbuf.duration)))
        start = inbuf.timestamp
        if inbuf.duration == gst.CLOCK_TIME_NONE:
            stop = inbuf.timestamp + (inbuf.size * gst.SECOND) / self.bitrate
        else:
            stop = inbuf.timestamp + inbuf.duration
        clip, nstart, nstop = self.segment.clip(gst.FORMAT_TIME, start, stop)
        self.debug("clip:%r, nstart:%s, nstop:%s" % (clip, gst.TIME_ARGS(nstart),
                                                     gst.TIME_ARGS(nstop)))
        if clip is True:
            if nstart != start and nstop != stop:
                self.debug("clipping")
                nduration = nstop - nstart
                # clip the buffer
                offset = (nstart - start) * self.bitrate
                # size
                nsize = nduration * self.bitrate
                b2 = inbuf.create_sub(offset, nsize)
                b2.timestamp = nstart
                b2.duration = nstop - nstart
                self.debug("buffer clipped")
                return self.srcpad.push(b2)
            self.debug("buffer untouched, just pushing forward")
            return self.srcpad.push(inbuf)
        self.debug("buffer dropped")
        return gst.FLOW_OK

gobject.type_register(AudioClipper)
gst.element_register(AudioClipper, 'audio-clipper')

class ClipperProbe(object):

    def __init__(self, pad):
        self._pad = pad
        self._pad.add_buffer_probe(self._bufferprobe)
        self._pad.add_event_probe(self._eventprobe)
        self.segment = gst.Segment()
        self.segment.init(gst.FORMAT_UNDEFINED)
        self._pad.connect("notify::caps", self._capsChangedCb)

    def _capsChangedCb(self, pad, unk):
        c = pad.get_negotiated_caps()
        if c is None:
            return
        pad.debug("caps:%s" % c.to_string())
        if c.is_fixed():
            self.rate = c[0]["rate"]
            self.bps = (c[0]["width"] / 8) * c[0]["channels"]
            self.bitrate = self.rate * self.bps
            pad.debug("rate:%d, bps:%d" % (self.rate, self.bps))

    def _eventprobe(self, pad, event):
        pad.debug("event %r" % event)
        if event.type == gst.EVENT_NEWSEGMENT:
            pad.debug("%r" % list(event.parse_new_segment()))
            self.segment.set_newsegment(*event.parse_new_segment())
        elif event.type == gst.EVENT_FLUSH_STOP:
            self.segment.init(gst.FORMAT_UNDEFINED)
        return True

    def _bufferprobe(self, pad, inbuf):
        start = inbuf.timestamp
        if start == gst.CLOCK_TIME_NONE:
            pad.warning("Got buffer without timestamp ! Forwarding")
            return True
        if inbuf.duration == gst.CLOCK_TIME_NONE:
            stop = inbuf.timestamp + (inbuf.size * gst.SECOND) / self.bitrate
        else:
            stop = inbuf.timestamp + inbuf.duration
        pad.debug("inbuf %s %s" % (gst.TIME_ARGS(start),
                                   gst.TIME_ARGS(stop)))
        clip, nstart, nstop = self.segment.clip(gst.FORMAT_TIME, start, stop)
        pad.debug("clip:%r, nstart:%s, nstop:%s" % (clip, gst.TIME_ARGS(nstart),
                                                     gst.TIME_ARGS(nstop)))
        if clip is True:
            if nstart != start or nstop != stop:
                pad.debug("clipping")
                nduration = nstop - nstart
                # clip the buffer
                offset = (nstart - start) * self.bitrate
                # size
                nsize = nduration * self.bitrate
                pad.debug("changing data")
                #inbuf.data = inbuf.data[offset:offset+nsize]
                #inbuf = inbuf.create_sub(offset, nsize)
                inbuf.timestamp = nstart
                inbuf.duration = nstop - nstart
                pad.debug("buffer clipped")
                return False
        return clip
