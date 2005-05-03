#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       discoverer.py
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

import gobject
import gst
import gtk
import objectfactory
import gc

class Discoverer(gobject.GObject):
    """
    Queues requests to discover information about given files.
    The discovery is done in a very fragmented way, so that it appears to be
    running in a separate thread.
    The "new_sourcefilefactory" signal is triggered when a file is established
    to be a media_file and the FileSourceFactory() is included in the signal.
    The "not_media_file" signal is triggered if a file is not a media_file.
    """

    __gsignals__ = {
        "new_sourcefilefactory" : (gobject.SIGNAL_RUN_LAST,
                                   gobject.TYPE_NONE,
                                   (gobject.TYPE_PYOBJECT, )),
        "not_media_file" : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_STRING, ))
        }

    def __init__(self):
        gobject.GObject.__init__(self)
        self.queue = []
        self.working = False
        self.currentfactory = None
        self.current = None
        self.videoprobe = None
        self.audioprobe = None
        self.pipeline = None
        self.probepads = []
        self.thumbnailing = False
        # TODO create pipeline

    def add_file(self, filename):
        """ queue a filename to be discovered """
        self.queue.append(filename)
        while gtk.events_pending():
            gtk.main_iteration(False)
        if not self.working:
            self._analyze()

    def add_files(self, filenames):
        """ queue a list of filenames to be discovered """
        self.queue.extend(filenames)
        while gtk.events_pending():
            gtk.main_iteration(False)
        if not self.working:
            self._analyze()

    def _analyze(self):
        """ segmented loop for analyzing queued filenames """
        self.working = True
        while len(self.queue) > 0:
            self.current = self.queue.pop(0)
            print "Analyzing ", self.current
            self.currentfactory = None
            # setup graph and start analyzing
            self.pipeline = gst.parse_launch("gnomevfssrc name=src location=\"%s\" ! decodebin name=dbin" % self.current)
            if not self.pipeline:
                self.emit("not_media_file", self.current)
                self._del_analyze_data()
                continue
            dbin = self.pipeline.get_by_name("dbin")
            dbin.connect("new-decoded-pad", self._new_decoded_pad_cb)
            self.pipeline.set_state(gst.STATE_PLAYING)
            for i in range(100):
                if not self.pipeline.iterate():
                    break
                if not i % 2:
                    while gtk.events_pending():
                        gtk.main_iteration(False)
            self.pipeline.set_state(gst.STATE_NULL)
            if not self.currentfactory:
                self.emit("not_media_file", self.current)
            self._del_analyze_data()
        self.working = False

    def _new_video_pad_cb(self, element, pad):
        """ a new video pad was found """
        print "video pad", pad.get_caps().to_string()
        if not self.currentfactory:
            self.currentfactory = objectfactory.FileSourceFactory(self.current)
            self.emit("new_sourcefilefactory", self.currentfactory)
        self.currentfactory.set_video(True)
        
        # Connect identity to fakesink at first
        # This allows to check when the desired buffer number arrives
        # When this happens we will connect the thumbnail-ing chain

        self.thumbnailing = False

        vident = gst.element_factory_make("identity")
        fakesink = gst.element_factory_make("fakesink")

        vcsp = gst.element_factory_make("ffmpegcolorspace")
        vscale = gst.element_factory_make("videoscale")
        vpng = gst.element_factory_make("jpegenc")
        #vpng.set_property("snapshot", False)
        vpngfakesink = gst.element_factory_make("fakesink")
        vpngfakesink.set_property("signal-handoffs", True)

        vident.connect("handoff", self._vident_handoff_cb,
                       (vident, fakesink, vcsp, vscale, vpng, vpngfakesink, pad))
        vpngfakesink.connect("handoff", self._vpngsink_handoff_cb,
                             (vident, fakesink, vcsp, vscale, vpng, vpngfakesink, pad))
        
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.pipeline.add_many(vident, fakesink, vcsp, vscale, vpng, vpngfakesink)
        pad.link(vident.get_pad("sink"))
        vident.link(fakesink)
        self.pipeline.set_state(gst.STATE_PLAYING)

    def _vident_handoff_cb(self, element, buffer, data):
        """ cb on handoff on identity """
        # If this is the first run,
        #   get video pad info
        #   if don't have length, get it
        # if this is the right buffer
        # disconnect fakesink and connect the correct pipeline
        print "vident_handoff_cb"
        if self.thumbnailing:
            return
        if not isinstance(buffer, gst.Event):
            vident, fakesink, vcsp, vscale, vpng, vpngfakesink, pad = data
            if not self.currentfactory.length:
                # Get the length
                length = pad.query(gst.QUERY_TOTAL, gst.FORMAT_TIME)
                if length:
                    self.currentfactory.set_length(length)
            # Get video info
            # TODO, we should check if we already have it or not
            caps = pad.get_caps()
            struct = caps[0]
            rw = struct["width"]
            he = struct["height"]
            if not self.currentfactory.video_info:
                self.currentfactory.set_video_info(caps)
            height = 96 * he / rw #/ 16 * 16
            
            # Connect correct pipeline
            self.pipeline.set_state(gst.STATE_PAUSED)
            element.unlink(fakesink)
            #element.link(vcsp)
            #vcsp.link(vscale)
            element.link(vscale)
            vscale.link_filtered(vpng, gst.caps_from_string("video/x-raw-yuv,width=(int)%d,height=(int)%d" % (96, height)))
            vpng.link(vpngfakesink)
            self.pipeline.set_state(gst.STATE_PLAYING)
            print "set up new pipeline"
            self.thumbnailing = True

    def _vpngsink_handoff_cb(self, element, buffer, sinkpad, data):
        """ cb on handoff on png fakesink """
        print "pngsink_handoff"
        if not self.thumbnailing:
            print "ERROR !!! the png fakesink shouldn't be called here !!!"
            return
        vident, fakesink, vcsp, vscale, vpng, vpngfakesink, pad = data
        # save the buffer to a file
        filename = "/tmp/" + self.currentfactory.name.encode('base64').replace('\n','') + ".jpg"
        pngfile = open(filename, "wb")
        pngfile.write(buffer.get_data())
        pngfile.close()
        self.currentfactory.set_thumbnail(filename)
        # disconnect this pipeline
        self.pipeline.set_state(gst.STATE_PAUSED)
        vident.unlink(vscale)
        # reconnect the fakesink
        vident.link(fakesink)
        self.pipeline.set_state(gst.STATE_PLAYING)
        # EVENTUALLY eos the pipeline
        self.pipeline.set_eos()
        self.thumbnailing = False
        
        
    def _new_audio_pad_cb(self, element, pad):
        """ a new audio pad was found """
        print "audio pad", pad.get_caps().to_string()
        if not self.currentfactory:
            self.currentfactory = objectfactory.FileSourceFactory(self.current)
            self.emit("new_sourcefilefactory", self.currentfactory)
        self.currentfactory.set_audio(True)
        cb = self._audio_handoff_cb
        #self.audioprobe = gst.Probe(False, self._audio_probe_cb, pad)
        #probe = self.audioprobe
        #probe = gst.Probe(False, self._audio_probe_cb, pad)
        #self.probepads.append((probe, pad))
        fakesink = gst.element_factory_make("fakesink")
        fakesink.set_property("signal-handoffs", True)
        fakesink.connect("handoff", cb, pad)
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.pipeline.add(fakesink)
        pad.link(fakesink.get_pad("sink"))
        #pad.add_probe(probe)
        self.pipeline.set_state(gst.STATE_PLAYING)
        

    def _new_decoded_pad_cb(self, element, pad, is_last):
        # check out the type (audio/video)
        # if we don't already have self.currentfactory
        #   create one, emit "new_sourcefile_factory"
        if "video" in pad.get_caps().to_string():
            self._new_video_pad_cb(element, pad)
        elif "audio" in pad.get_caps().to_string():
            self._new_audio_pad_cb(element, pad)

    def _filesink_handoff_cb(self, filesink):
        print "data outputted"
        self.currentfactory.set_thumbnail(filesink.get_property("location"))
        self.pipeline.set_eos()

    def _video_handoff_cb(self, identity, data, pad):
        print "video data"
        if not isinstance(data, gst.Event):
            if not self.currentfactory.length:
                length = pad.query(gst.QUERY_TOTAL, gst.FORMAT_TIME)
                if length:
                    self.currentfactory.set_length(length)
                    # link to vscale with the correct caps
                    width = 64
                    caps = pad.get_caps()
                    print "caps : ", caps
                    struct = caps[0]
                    print "struct : ", struct
                    rw = struct["width"]
                    he = struct["height"]
                    height = width * he / rw
                    print "width: %d, height: %d" % (width, height)
                    identity.link_filtered(self.pngenc, gst.caps_from_string("video/x-raw-rgb,width=(int)%d,height=(int)%d" % (width, height)))
                    #self.currentfactory.set_thumbnail("/tmp/" + self.currentfactory.name.encode('base64').replace('\n','') + ".png")
                    #self.pipeline.set_eos()

    def _audio_handoff_cb(self, fakesink, data, sinkpad, pad):
        print "audio data"
        if not isinstance(data, gst.Event):
            if not self.currentfactory.audio_info:
                self.currentfactory.set_audio_info(pad.get_caps())
            if not self.currentfactory.length:
                length = pad.query(gst.QUERY_TOTAL, gst.FORMAT_TIME)
                if length:
                    self.currentfactory.set_length(length)
                if not self.currentfactory.is_video:
                    # Only stop pipeline if there isn't any video to thumbnail
                    self.pipeline.set_eos()

    def _del_analyze_data(self):
        del self.pipeline
        self.pipeline = None
        self.currentfactory = None
        self.current = None
        
        
gobject.type_register(Discoverer)
