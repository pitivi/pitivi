# PiTiVi , Non-linear video editor
#
#       pitivi/elements/singledecodebin.py
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
Image-to-video element
"""

# Goal:
#
# We want to take a raw image source and output a continuous
# video feed (by default [0,GST_CLOCK_TIME_NONE]) according to
# the srcpad negotiated caps (i.e. proper timestamps)
#
# In the event of seeks, this is the element that will handle the seeks
# and output the proper segments.
#
# for a given negotiated framerate R (in frames/second):
# The outputted buffer timestamps will be X * 1/R
# where X is an integer.
# EXCEPT for accurate segment seeks where the first/last buffers will be
# adjusted to the requested start/stop values

import gobject
import gst


class ImageFreeze(gst.Element):

    __gstdetails__ = (
        "ImageFreeze plugin",
        "imagefreeze.py",
        "Outputs a video feed out an incoming frame",
        "Edward Hervey <bilboed@bilboed.com>")

    _srctemplate = gst.PadTemplate("src",
                                   gst.PAD_SRC,
                                   gst.PAD_ALWAYS,
                                   gst.caps_new_any())
    _sinktemplate = gst.PadTemplate("sink",
                                   gst.PAD_SINK,
                                   gst.PAD_ALWAYS,
                                   gst.caps_new_any())
    __gsttemplates__ = (_srctemplate, _sinktemplate)

    def __init__(self, *args, **kwargs):
        gst.Element.__init__(self, *args, **kwargs)
        self.srcpad = gst.Pad(self._srctemplate)
        self.srcpad.set_event_function(self._src_event)

        self.sinkpad = gst.Pad(self._sinktemplate)
        self.sinkpad.set_chain_function(self._sink_chain)
        self.sinkpad.set_event_function(self._sink_event)
        self.sinkpad.set_setcaps_function(self._sink_setcaps)

        self.add_pad(self.srcpad)
        self.add_pad(self.sinkpad)

        self._reset()

    def _reset(self):
        gst.debug("resetting ourselves")
        self._outputrate = None
        self._srccaps = None
        # number of outputted buffers
        self._offset = 0
        self._segment = gst.Segment()
        self._segment.init(gst.FORMAT_TIME)
        self._needsegment = True
        self._bufferduration = 0
        # this is the buffer we store and repeatedly output
        self._buffer = None
        # this will be set by our task
        self.last_return = gst.FLOW_OK

    def _sink_setcaps(self, pad, caps):
        gst.debug("caps %s" % caps.to_string())
        downcaps = self.srcpad.peer_get_caps().copy()
        gst.debug("downcaps %s" % downcaps.to_string())

        # methodology
        # 1. We override any incoming framerate
        ccaps = caps.make_writable()
        for struct in ccaps:
            if struct.has_key("framerate"):
                try:
                    del struct["framerate"]
                except:
                    gst.warning("Couldn't remove 'framerate' from %s" % struct.to_string())

        # 2. we do the intersection of our incoming stripped caps
        #    and the downstream caps
        intersect = ccaps.intersect(downcaps)
        if intersect.is_empty():
            gst.warning("no negotiation possible !")
            return False

        # 3. for each candidate in the intersection, we try to set that
        #    candidate downstream
        for candidate in intersect:
            gst.debug("Trying %s" % candidate.to_string())
            if self.srcpad.peer_accept_caps(candidate):
                gst.debug("accepted !")
                # 4. When we have an accepted caps downstream, we store the negotiated
                #    framerate and return
                self._outputrate = candidate["framerate"]
                self._bufferduration = gst.SECOND * self._outputrate.denom / self._outputrate.num
                self._srccaps = candidate
                return self.srcpad.set_caps(candidate)

        # 5. If we can't find an accepted candidate, we return False
        return False

    def _src_event(self, pad, event):
        # for the moment we just push it upstream
        gst.debug("event %r" % event)
        if event.type == gst.EVENT_SEEK:
            rate,fmt,flags,startt,start,stopt,stop = event.parse_seek()
            gst.debug("Handling seek event %r" % flags)
            if flags & gst.SEEK_FLAG_FLUSH:
                gst.debug("sending flush_start event")
                self.srcpad.push_event(gst.event_new_flush_start())
            self._segment.set_seek(*event.parse_seek())
            gst.debug("_segment start:%s stop:%s" % (gst.TIME_ARGS(self._segment.start),
                                                     gst.TIME_ARGS(self._segment.stop)))
            # create a new initial seek
            gst.debug("pausing task")
            self.srcpad.pause_task()
            gst.debug("task paused")
            seek = gst.event_new_seek(1.0, gst.FORMAT_TIME, flags,
                                      gst.SEEK_TYPE_NONE, 0,
                                      gst.SEEK_TYPE_NONE, 0)
            #return self.sinkpad.push_event(seek)
            self._needsegment = True
            if flags & gst.SEEK_FLAG_FLUSH:
                self.srcpad.push_event(gst.event_new_flush_stop())
            self.srcpad.start_task(self.our_task)
            return True

        return self.sinkpad.push_event(event)

    def _sink_event(self, pad, event):
        gst.debug("event %r" % event)
        if event.type == gst.EVENT_NEWSEGMENT:
            gst.debug("dropping new segment !")
            return True
        elif event.type == gst.EVENT_FLUSH_START:
            self._reset()
        return self.srcpad.push_event(event)

    def _sink_chain(self, pad, buffer):
        gst.debug("buffer %s %s" % (gst.TIME_ARGS(buffer.timestamp),
                                    gst.TIME_ARGS(buffer.duration)))
        if self._buffer != None:
            gst.debug("already have a buffer ! Returning GST_FLOW_WRONG_STATE")
            return gst.FLOW_WRONG_STATE

        self._buffer = buffer
        self.srcpad.start_task(self.our_task)
        return gst.FLOW_WRONG_STATE

    def our_task(self, something):
        #this is where we repeatedly output our buffer
        gst.debug("self:%r, something:%r" % (self, something))

        gst.debug("needsegment: %r" % self._needsegment)
        if self._needsegment:
            gst.debug("Need to output a new segment")
            segment = gst.event_new_new_segment(False,
                                                self._segment.rate,
                                                self._segment.format,
                                                self._segment.start,
                                                self._segment.stop,
                                                self._segment.start)
            self.srcpad.push_event(segment)
            # calculate offset
            # offset is int(segment.start / outputrate)
            self._offset = int(self._segment.start * self._outputrate.num / self._outputrate.denom / gst.SECOND)
            self._needsegment = False
            gst.debug("Newsegment event pushed")

        # new position
        position = self._offset * gst.SECOND * self._outputrate.denom / self._outputrate.num
        if self._segment.stop != -1 and position > self._segment.stop:
            gst.debug("end of configured segment (position:%s / segment_stop:%s)" % (gst.TIME_ARGS(position),
                                                                                     gst.TIME_ARGS(self._segment.stop)))
            # end of stream/segment handling
            if self._segment.flags & gst.SEEK_FLAG_SEGMENT:
                # emit a gst.MESSAGE_SEGMENT_DONE
                self.post_message(gst.message_new_segment_done(self, gst.FORMAT_TIME, self._segment.stop))
            else:
                self.srcpad.push_event(gst.event_new_eos())
            self.last_return = gst.FLOW_WRONG_STATE
            self.srcpad.pause_task()

        # we need to update the caps here !
        obuf = self._buffer.make_metadata_writable()
        ok, nstart, nstop = self._segment.clip(gst.FORMAT_TIME,
                                               position, position + self._bufferduration)
        if ok:
            obuf.timestamp = nstart
            obuf.duration = nstop - nstart
            obuf.caps = self._srccaps
            gst.debug("Pushing out buffer %s" % gst.TIME_ARGS(obuf.timestamp))
            self.last_return = self.srcpad.push(obuf)
        self._offset += 1

        if self.last_return != gst.FLOW_OK:
            gst.debug("Pausing ourself, last_return : %s" % gst.flow_get_name(self.last_return))
            self.srcpad.pause_task()

    def do_change_state(self, transition):
        if transition in [gst.STATE_CHANGE_READY_TO_PAUSED, gst.STATE_CHANGE_PAUSED_TO_READY]:
            self._reset()
        return gst.Element.do_change_state(self, transition)

gobject.type_register(ImageFreeze)

def dataprobe(pad, data):
    if isinstance(data, gst.Buffer):
        print "Buffer", gst.TIME_ARGS(data.timestamp), gst.TIME_ARGS(data.duration), data.caps.to_string()
    else:
        print "Event", data.type
        if data.type == gst.EVENT_NEWSEGMENT:
            print data.parse_new_segment()
    return True

def make_image_video_bin(location):
    b = gst.Bin("image-video-bin-"+location)
    src = gst.element_factory_make("filesrc")
    src.props.location = location
    src.props.blocksize = 1024 * 1024
    dec = gst.element_factory_make("jpegdec")
    vscale = gst.element_factory_make("videoscale")
    freeze = ImageFreeze()
    cfil = gst.element_factory_make("capsfilter")
    cfil.props.caps = gst.Caps("video/x-raw-yuv,framerate=25/1")
    p.add(src, dec, vscale, freeze, cfil)
    gst.element_link_many(src, dec, vscale)
    vscale.link(freeze, gst.Caps("video/x-raw-yuv,width=640,height=480"))
    gst.element_link_many(freeze, cfil)

    b.add_pad(gst.GhostPad("src", cfil.get_pad("src")))

    return b

def post_link(gnls, pad, q):
    gnls.link(q)

# filesrc ! jpegdec ! imagefreeze ! xvimagesink
if __name__ == "__main__":
    import sys
    p = gst.Pipeline()

    b = make_image_video_bin(sys.argv[1])
    gnls = gst.element_factory_make("gnlsource")
    gnls.add(b)

    gnls.props.media_start = 5 * gst.SECOND
    gnls.props.media_duration = 5 * gst.SECOND
    gnls.props.duration = 5 * gst.SECOND

    toverl = gst.element_factory_make("timeoverlay")
    sink = gst.element_factory_make("xvimagesink")
    sink.get_pad("sink").add_data_probe(dataprobe)

    q = gst.element_factory_make("queue")

    p.add(gnls, toverl, q, sink)

    gst.element_link_many(q, toverl, sink)
    #q.link(sink)

    gnls.connect("pad-added", post_link, q)

    ml = gobject.MainLoop()

    p.set_state(gst.STATE_PLAYING)

    ml.run()

