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
                            (gobject.TYPE_STRING, )),
        "finished_analyzing" : ( gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject.TYPE_PYOBJECT, )),
        "ready" : ( gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    ( ))
        }

    def __init__(self, project):
        gst.info("new discoverer for project %s" % project)
        gobject.GObject.__init__(self)
        self.project = project
        self.queue = []
        self.working = False
        self.analyzing = False
        self.currentfactory = None
        self.current = None
        self.pipeline = None
        self.thumbnailing = False
        # TODO create pipeline

    def add_file(self, filename):
        """ queue a filename to be discovered """
        gst.info("filename: %s" % filename)
        self.queue.append(filename)
        if not self.working:
            self._start_analysis()

    def add_files(self, filenames):
        """ queue a list of filenames to be discovered """
        gst.info("filenames : %s" % filenames)
        self.queue.extend(filenames)
        if not self.working:
            self._start_analysis()

    def _start_analysis(self):
        """
        Call this method to start analyzing the uris
        """
        if self.working:
            gst.warning("called when still working!")
            return False
        
        if not len(self.queue):
            gst.warning("Nothing to analyze!!")
            return False
        
        self.working = True
        gobject.idle_add(self._analyze)
        return False

    def _finish_analysis(self):
        """
        Call this method when the current file is analyzed
        This method will wrap-up the analyzis and call the next analysis if needed
        """
        if not self.analyzing:
            gst.warning("called when not analyzing!!")
            return False

        gst.info("Cleaning up after finished analyzing %s" % self.current)
        # finish current, cleanup
        self.bus.remove_signal_watch()
        self.bus = None
        gst.info("before setting to NULL")
        self.pipeline.set_state(gst.STATE_READY)
        gst.info("after setting to NULL")
        self.analyzing = False
        self.current = None
        self.currentfactory = None
        self.pipeline = None
        
        # restart an analysis if there's more...
        if len(self.queue):
            gobject.idle_add(self._analyze)
        else:
            self.working = False
            gst.info("discoverer is now ready again")
            self.emit("ready")
        return False


    def _analyze(self):
        """
        Sets up a pipeline to analyze the given uri
        """
        self.analyzing = True
        self.current = self.queue.pop(0)
        gst.info("Analyzing %s" % self.current)
        self.currentfactory = None
        
        # setup graph and start analyzing
        self.pipeline = gst.parse_launch("gnomevfssrc name=src location=\"%s\" ! decodebin name=dbin" % self.current)
        if not self.pipeline:
            gst.warning("This is not a media file : %s" % self.current)
            self.emit("not_media_file", self.current)
            gobject.idle_add(self._finish_analysis)
            return
        gst.info("analysis pipeline created")
        dbin = self.pipeline.get_by_name("dbin")
        dbin.connect("new-decoded-pad", self._new_decoded_pad_cb)
        dbin.connect("unknown-type", self._unknown_type_cb)
        self.bus = self.pipeline.get_bus()
        self.bus.connect("message", self._bus_message_cb)
        self.bus.add_signal_watch()
        gst.info("setting pipeline to play")
        self.pipeline.set_state(gst.STATE_PLAYING)

        # return False so we don't get called again
        return False
        
##         self.working = True
##         while len(self.queue) > 0:
##             self.current = self.queue.pop(0)
##             gst.info("Analyzing %s" % self.current)
##             self.currentfactory = None
##                 self._del_analyze_data()
##                 continue
##             dbin = self.pipeline.get_by_name("dbin")
##             dbin.connect("new-decoded-pad", self._new_decoded_pad_cb)
##             self.pipeline.set_state(gst.STATE_PLAYING)
##             for i in range(100):
##                 if not self.pipeline.iterate():
##                     break
##                 if not i % 2:
##                     while gtk.events_pending():
##                         gtk.main_iteration(False)
##             self.pipeline.set_state(gst.STATE_NULL)
##             if not self.currentfactory:
##                 gst.warning("This is not a media file : %s" % self.current)
##                 self.emit("not_media_file", self.current)
##             else:
##                 self.emit("finished_analyzing", self.currentfactory)
##             self._del_analyze_data()
##         self.working = False
##         self.emit("ready")

    def _bus_message_cb(self, bus, message):
        if message.type == gst.MESSAGE_STATE_CHANGED:
            print message.src, message.parse_state_changed()
        elif message.type in [gst.MESSAGE_EOS, gst.MESSAGE_ERROR]:
            gobject.idle_add(self._finish_analysis)
        else:
            print message.type, message.src

    def _vcaps_notify(self, pad, property):
        caps = pad.get_negotiated_caps()
        if caps and not self.currentfactory.video_info:
            self.currentfactory.set_video_info(caps)
            if not self.currentfactory.length:
                pad = pad.get_peer()
                gst.info("querying time on pad %s" % pad)
                value = pad.query_position(gst.FORMAT_TIME)
                gst.info("%s" % value)
                if value:
                    cur, length, format = value
                    if format == gst.FORMAT_TIME:
                        self.currentfactory.set_property("length", length)
            if not self.currentfactory.is_audio or self.currentfactory.audio_info:
                gobject.idle_add(self._finish_analysis)

    def _new_video_pad_cb(self, element, pad):
        """ a new video pad was found """
        self.currentfactory.set_video(True)
        if pad.get_caps().is_fixed():
            self.currentfactory.set_video_info(pad.get_caps())

        fakesink = gst.element_factory_make("fakesink")
        queue = gst.element_factory_make("queue")
        self.pipeline.add(fakesink, queue)
        queue.link(fakesink)
        pad.link(queue.get_pad("sink"))
        fakesink.get_pad("sink").connect("notify::caps", self._vcaps_notify)
        for element in [queue, fakesink]:
            element.set_state(gst.STATE_PAUSED)
        # Connect identity to fakesink at first
        # This allows to check when the desired buffer number arrives
        # When this happens we will connect the thumbnail-ing chain

##         self.thumbnailing = False

##         vident = gst.element_factory_make("identity")
##         fakesink = gst.element_factory_make("fakesink")

##         vcsp = gst.element_factory_make("ffmpegcolorspace")
##         #vscale = gst.element_factory_make("videoscale")
##         vpng = gst.element_factory_make("jpegenc")
##         #vpng.set_property("snapshot", False)
##         vpngfakesink = gst.element_factory_make("fakesink")
##         vpngfakesink.set_property("signal-handoffs", True)

##         vident.connect("handoff", self._vident_handoff_cb,
##                        (vident, fakesink, vcsp, vpng, vpngfakesink, pad))
##         vpngfakesink.connect("handoff", self._vpngsink_handoff_cb,
##                              (vident, fakesink, vcsp, vpng, vpngfakesink, pad))
        
##         self.pipeline.set_state(gst.STATE_PAUSED)
##         self.pipeline.add(vident, fakesink, vcsp, vpng, vpngfakesink)
##         pad.link(vident.get_pad("sink"))
##         vident.link(fakesink)
##         self.pipeline.set_state(gst.STATE_PLAYING)

    def _vident_handoff_cb(self, element, buffer, data):
        """ cb on handoff on identity """
        # If this is the first run,
        #   get video pad info
        #   if don't have length, get it
        # if this is the right buffer
        # disconnect fakesink and connect the correct pipeline
        if self.thumbnailing:
            return
        if not isinstance(buffer, gst.Event):
            vident, fakesink, vcsp, vpng, vpngfakesink, pad = data
            if not self.currentfactory.length:
                # Get the length
                length = pad.query(gst.QUERY_TOTAL, gst.FORMAT_TIME)
                if length:
                    self.currentfactory.set_length(length)
            # Get video info
            struct = pad.get_caps()[0]
            rw = struct["width"]
            he = struct["height"]
            if not self.currentfactory.video_info:
                self.currentfactory.set_video_info(pad.get_caps())
            height = 96 * he / rw #/ 16 * 16
            
            # Connect correct pipeline
            self.pipeline.set_state(gst.STATE_PAUSED)
            element.unlink(fakesink)
            element.link(vpng)
            #vscale.link_filtered(vpng, gst.caps_from_string("video/x-raw-yuv,width=(int)%d,height=(int)%d" % (96, height)))
            vpng.link(vpngfakesink)
            self.pipeline.set_state(gst.STATE_PLAYING)
            self.thumbnailing = True

    def _vpngsink_handoff_cb(self, element, buffer, sinkpad, data):
        """ cb on handoff on png fakesink """
        if not self.thumbnailing:
            gst.error("ERROR !!! the png fakesink shouldn't be called here !!!")
            return
        vident, fakesink, vcsp, vpng, vpngfakesink, pad = data
        # save the buffer to a file
        filename = "/tmp/" + self.currentfactory.name.encode('base64').replace('\n','') + ".jpg"
        pngfile = open(filename, "wb")
        pngfile.write(buffer.get_data())
        pngfile.close()
        self.currentfactory.set_thumbnail(filename)
        # disconnect this pipeline
        self.pipeline.set_state(gst.STATE_PAUSED)
        vident.unlink(vpng)
        # reconnect the fakesink
        vident.link(fakesink)
        self.pipeline.set_state(gst.STATE_PLAYING)
        # EVENTUALLY eos the pipeline
        if not self.currentfactory.is_audio or self.currentfactory.audio_info:
            self.pipeline.set_eos()
        
    def _acaps_notify(self, pad, property):
        caps = pad.get_negotiated_caps()
        if caps and not self.currentfactory.audio_info:
            self.currentfactory.set_audio_info(caps)
            if not self.currentfactory.length:
                pad = pad.get_peer()
                gst.info("querying time on pad %s" % pad)
                value = pad.query_position(gst.FORMAT_TIME)
                gst.info("%s" % value)
                if value:
                    cur, length, format = value
                    if format == gst.FORMAT_TIME:
                        self.currentfactory.set_property("length", length)
            if not self.currentfactory.is_video or self.currentfactory.video_info:
                gobject.idle_add(self._finish_analysis)

    def _new_audio_pad_cb(self, element, pad):
        """ a new audio pad was found """
        self.currentfactory.set_audio(True)

        if pad.get_caps().is_fixed():
            self.currentfactory.set_audio_info(pad.get_caps())
        
#        cb = self._audio_handoff_cb
        fakesink = gst.element_factory_make("fakesink")
        queue = gst.element_factory_make("queue")
#        fakesink.set_property("signal-handoffs", True)
#        fakesink.connect("handoff", cb, pad)
        #self.pipeline.set_state(gst.STATE_PAUSED)
        self.pipeline.add(fakesink, queue)
        queue.link(fakesink)
        pad.link(queue.get_pad("sink"))
        queue.get_pad("sink").connect("notify::caps", self._acaps_notify)
        for element in [queue, fakesink]:
            element.set_state(gst.STATE_PAUSED)
        #self.pipeline.set_state(gst.STATE_PLAYING)
        
    def _unknown_type_cb(self, dbin, pad, caps):
        gst.info(caps.to_string())
        if not self.currentfactory or not self.currentfactory.is_audio or not self.currentfactory.is_video:
            gst.warning("got unknown pad without anything else")
            self.emit("not_media_file", self.current)
            gobject.idle_add(self._finish_analysis)

    def _new_decoded_pad_cb(self, element, pad, is_last):
        # check out the type (audio/video)
        # if we don't already have self.currentfactory
        #   create one, emit "new_sourcefile_factory"
        gst.info(pad.get_caps().to_string())
        if "video" in pad.get_caps().to_string():
            if not self.currentfactory:
                self.currentfactory = objectfactory.FileSourceFactory(self.current, self.project)
                self.emit("new_sourcefilefactory", self.currentfactory)
            self._new_video_pad_cb(element, pad)
        elif "audio" in pad.get_caps().to_string():
            if not self.currentfactory:
                self.currentfactory = objectfactory.FileSourceFactory(self.current, self.project)
                self.emit("new_sourcefilefactory", self.currentfactory)
            self._new_audio_pad_cb(element, pad)
        if is_last:
            if not self.currentfactory or not self.currentfactory.is_audio or not self.currentfactory.is_video:
                gst.warning("couldn't find a usable pad")
                gobject.idle_add(self._finish_analysis)

    def _audio_handoff_cb(self, fakesink, data, sinkpad, pad):
        if not self.currentfactory.audio_info and pad.get_caps().is_fixed():
            self.currentfactory.set_audio_info(pad.get_caps())
        if not self.currentfactory.length:
            length = pad.query(gst.QUERY_TOTAL, gst.FORMAT_TIME)
            if length:
                self.currentfactory.set_length(length)
        # Stop pipeline if we have all info
        if self.currentfactory.audio_info and (not self.currentfactory.is_video or self.currentfactory.video_info):
            # Only stop pipeline if there isn't any video to thumbnail
            self.pipeline.set_eos()

    def _del_analyze_data(self):
        del self.pipeline
        self.pipeline = None
        self.currentfactory = None
        self.current = None
        
        
gobject.type_register(Discoverer)
