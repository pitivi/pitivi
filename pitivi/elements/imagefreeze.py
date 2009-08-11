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
    """
    'Image to Video' element
    """

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
        self.debug("resetting ourselves")
        self._outputrate = None
        self._srccaps = None
        # number of outputted buffers
        self._offset = 0
        self._segment = gst.Segment()
        self._segment.init(gst.FORMAT_TIME)
        self._needsegment = True
        self._bufferduration = 0
        self._outputrate = gst.Fraction(25, 1)
        # this is the buffer we store and repeatedly output
        self._buffer = None
        # this will be set by our task
        self.last_return = gst.FLOW_OK

    def _sink_setcaps(self, unused_pad, caps):
        self.debug("caps %s" % caps.to_string())
        downcaps = self.srcpad.peer_get_caps().copy()
        self.debug("downcaps %s" % downcaps.to_string())

        # methodology
        # 1. We override any incoming framerate
        ccaps = gst.Caps(caps)
        for struct in ccaps:
            if struct.has_key("framerate"):
                try:
                    del struct["framerate"]
                except:
                    self.warning("Couldn't remove 'framerate' from %s" % struct.to_string())

        # 2. we do the intersection of our incoming stripped caps
        #    and the downstream caps
        intersect = ccaps.intersect(downcaps)
        if intersect.is_empty():
            self.warning("no negotiation possible !")
            return False

        # 3. for each candidate in the intersection, we try to set that
        #    candidate downstream
        for candidate in intersect:
            self.debug("Trying %s" % candidate.to_string())
            if self.srcpad.peer_accept_caps(candidate):
                self.debug("accepted ! %s" % candidate.to_string())
                # 4. When we have an accepted caps downstream, we store the negotiated
                #    framerate and return
                if not candidate.has_key("framerate") or \
                        not isinstance(candidate["framerate"], gst.Fraction):
                    candidate["framerate"] = gst.Fraction(25, 1)
                self._outputrate = candidate["framerate"]
                self._bufferduration = gst.SECOND * self._outputrate.denom / self._outputrate.num
                self._srccaps = candidate.copy()
                res = self.srcpad.set_caps(self._srccaps)
                return res

        # 5. If we can't find an accepted candidate, we return False
        return False

    def _src_event(self, unused_pad, event):
        # for the moment we just push it upstream
        self.debug("event %r" % event)
        if event.type == gst.EVENT_SEEK:
            flags = event.parse_seek()[2]
            self.debug("Handling seek event %r" % flags)
            if flags & gst.SEEK_FLAG_FLUSH:
                self.debug("sending flush_start event")
                self.srcpad.push_event(gst.event_new_flush_start())
            self._segment.set_seek(*event.parse_seek())
            self.debug("_segment start:%s stop:%s" % (gst.TIME_ARGS(self._segment.start),
                                                     gst.TIME_ARGS(self._segment.stop)))
            # create a new initial seek
            self.debug("pausing task")
            self.srcpad.pause_task()
            self.debug("task paused")

            self._needsegment = True
            self.debug("Sending FLUS_STOP event")
            if flags & gst.SEEK_FLAG_FLUSH:
                self.srcpad.push_event(gst.event_new_flush_stop())
            self.debug("Restarting our task")
            self.srcpad.start_task(self._our_task)
            self.debug("Returning True")
            return True

        return self.sinkpad.push_event(event)

    def _sink_event(self, unused_pad, event):
        self.debug("event %r" % event)
        if event.type == gst.EVENT_NEWSEGMENT:
            self.debug("dropping new segment !")
            return True
        elif event.type == gst.EVENT_FLUSH_START:
            self._reset()
        return self.srcpad.push_event(event)

    def _sink_chain(self, unused_pad, buf):
        self.debug("buffer %s %s" % (gst.TIME_ARGS(buf.timestamp),
                                    gst.TIME_ARGS(buf.duration)))
        if self._buffer != None:
            self.debug("already have a buffer ! Returning GST_FLOW_WRONG_STATE")
            return gst.FLOW_WRONG_STATE

        self._buffer = buf
        self.srcpad.start_task(self._our_task)
        return gst.FLOW_WRONG_STATE

    def _our_task(self, something):
        if self._buffer == None:
            self.warning("We were started without a buffer, exiting")
            self.srcpad.pause_task()
            return

        #this is where we repeatedly output our buffer
        self.debug("self:%r, something:%r" % (self, something))

        self.debug("needsegment: %r" % self._needsegment)
        if self._needsegment:
            self.debug("Need to output a new segment")
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
            self.debug("Newsegment event pushed")

        # new position
        position = self._offset * gst.SECOND * self._outputrate.denom / self._outputrate.num
        if self._segment.stop != -1 and position > self._segment.stop:
            self.debug("end of configured segment (position:%s / segment_stop:%s)" % (gst.TIME_ARGS(position),
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
            self.debug("Pushing out buffer %s" % gst.TIME_ARGS(obuf.timestamp))
            self.last_return = self.srcpad.push(obuf)
        self._offset += 1

        if self.last_return != gst.FLOW_OK:
            self.debug("Pausing ourself, last_return : %s" % gst.flow_get_name(self.last_return))
            self.srcpad.pause_task()

    def do_change_state(self, transition):
        if transition in [gst.STATE_CHANGE_READY_TO_PAUSED, gst.STATE_CHANGE_PAUSED_TO_READY]:
            self._reset()
        return gst.Element.do_change_state(self, transition)

gobject.type_register(ImageFreeze)

def _dataprobe(unused_pad, data):
    if isinstance(data, gst.Buffer):
        print "Buffer", gst.TIME_ARGS(data.timestamp), gst.TIME_ARGS(data.duration), data.caps.to_string()
    else:
        print "Event", data.type
        if data.type == gst.EVENT_NEWSEGMENT:
            print data.parse_new_segment()
    return True

def _make_image_video_bin(location):
    bin = gst.Bin("image-video-bin-"+location)
    src = gst.element_factory_make("filesrc")
    src.props.location = location
    src.props.blocksize = 1024 * 1024
    dec = gst.element_factory_make("jpegdec")
    vscale = gst.element_factory_make("videoscale")
    freeze = ImageFreeze()
    cfil = gst.element_factory_make("capsfilter")
    cfil.props.caps = gst.Caps("video/x-raw-yuv,framerate=25/1")
    bin.add(src, dec, vscale, freeze, cfil)
    gst.element_link_many(src, dec, vscale)
    vscale.link(freeze, gst.Caps("video/x-raw-yuv,width=640,height=480"))
    gst.element_link_many(freeze, cfil)

    bin.add_pad(gst.GhostPad("src", cfil.get_pad("src")))

    return bin

def _post_link(source, unused_pad, queue):
    source.link(queue)

# filesrc ! jpegdec ! imagefreeze ! xvimagesink
if __name__ == "__main__":
    import sys
    pipe = gst.Pipeline()

    b = _make_image_video_bin(sys.argv[1])
    gnls = gst.element_factory_make("gnlsource")
    gnls.add(b)

    gnls.props.media_start = 5 * gst.SECOND
    gnls.props.media_duration = 5 * gst.SECOND
    gnls.props.duration = 5 * gst.SECOND

    toverl = gst.element_factory_make("timeoverlay")
    sink = gst.element_factory_make("xvimagesink")
    sink.get_pad("sink").add_data_probe(_dataprobe)

    queue = gst.element_factory_make("queue")

    pipe.add(gnls, toverl, queue, sink)

    gst.element_link_many(queue, toverl, sink)
    #q.link(sink)

    gnls.connect("pad-added", _post_link, queue)

    ml = gobject.MainLoop()

    pipe.set_state(gst.STATE_PLAYING)

    ml.run()
