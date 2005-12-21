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

import os.path

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
        self.emit('finished-analyzing', self.currentfactory)
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
        gst.info("setting pipeline to PAUSED")
        if self.pipeline.set_state(gst.STATE_PAUSED) == gst.STATE_CHANGE_FAILURE:
            self.emit("not_media_file", self.current)
            gst.info("pipeline didn't want to go to PAUSED")
            gobject.idle_add(self._finish_analysis)

        # return False so we don't get called again
        return False
        
    def _bus_message_cb(self, bus, message):
        if message.type == gst.MESSAGE_STATE_CHANGED:
            gst.log("%s:%s" % ( message.src, message.parse_state_changed()))
            if message.src == self.pipeline:
                prev, new, pending = message.parse_state_changed()
                if prev == gst.STATE_READY and new == gst.STATE_PAUSED:
                    # Let's get the information from all the pads
                    self._get_pads_info()
                    gst.log("pipeline has gone to PAUSED, now pushing to PLAYING")
                    self.pipeline.set_state(gst.STATE_PLAYING)
        elif message.type == gst.MESSAGE_EOS:
            gst.log("got EOS")
            filename = "/tmp/" + self.currentfactory.name.encode('base64').replace('\n','') + ".png"
            if os.path.isfile(filename):
                self.currentfactory.set_thumbnail(filename)
            gobject.idle_add(self._finish_analysis)
        elif message.type == gst.MESSAGE_ERROR:
            gst.warning("got an ERROR")
            if not self.currentfactory:
                self.emit("not_media_file", self.current)
            gobject.idle_add(self._finish_analysis)
        else:
            gst.log("%s:%s" % ( message.type, message.src))

    def _get_pads_info(self):
        # iterate all src pads and check their informatiosn
        gst.info("Getting pads info on decodebin")
        for pad in list(self.pipeline.get_by_name("dbin").pads()):
            if pad.get_direction() == gst.PAD_SINK:
                continue
            caps = pad.get_caps()
            if not caps.is_fixed():
                caps = pad.get_negotiated_caps()
            gst.info("testing pad %s : %s" % (pad, caps))
            if caps and caps.is_fixed():
                if "audio/" == caps.to_string()[:6] and not self.currentfactory.audio_info:
                    self.currentfactory.set_audio_info(caps)
                elif "video/" == caps.to_string()[:6] and not self.currentfactory.video_info:
                    self.currentfactory.set_video_info(caps)
            if not self.currentfactory.length:
                try:
                    length, format = pad.query_duration(gst.FORMAT_TIME)
                except:
                    pad.warning("duration query failed")
                else:
                    if format == gst.FORMAT_TIME:
                        self.currentfactory.set_property("length", length)

    def _vcaps_notify(self, pad, property):
        if pad.get_caps().is_fixed():
            self.currentfactory.set_video_info(pad.get_caps())

    def _new_video_pad_cb(self, element, pad):
        """ a new video pad was found """
        self.currentfactory.set_video(True)
        if pad.get_caps().is_fixed():
            self.currentfactory.set_video_info(pad.get_caps())

        # replacing queue-fakesink by ffmpegcolorspace-queue-pngenc
        csp = gst.element_factory_make("ffmpegcolorspace")
        queue = gst.element_factory_make("queue")
        pngenc = gst.element_factory_make("pngenc")
        pngsink = gst.element_factory_make("filesink")
        pngsink.set_property("location", "/tmp/" + self.currentfactory.name.encode('base64').replace('\n','') + ".png")
        self.pipeline.add(csp, queue, pngenc, pngsink)
        pngenc.link(pngsink)
        queue.link(pngenc)
        csp.link(queue)
        pad.link(csp.get_pad("sink"))
        if not self.currentfactory.video_info:
            pad.connect("notify::caps", self._vcaps_notify)
        for element in [csp, queue, pngenc, pngsink]:
            element.set_state(gst.STATE_PAUSED)
        
    def _new_audio_pad_cb(self, element, pad):
        """ a new audio pad was found """
        self.currentfactory.set_audio(True)

        if pad.get_caps().is_fixed():
            self.currentfactory.set_audio_info(pad.get_caps())
            
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
        gst.info("pad:%s caps:%s" % (pad, pad.get_caps().to_string()))
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
