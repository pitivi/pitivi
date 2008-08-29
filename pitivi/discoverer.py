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

"""
Discover file multimedia information.
"""

import gobject
import gst
import objectfactory

from gettext import gettext as _
import os.path

class Discoverer(gobject.GObject):
    """
    Queues requests to discover information about given files.
    The discovery is done in a very fragmented way, so that it appears to be
    running in a separate thread.

    The "new_sourcefilefactory" signal is emitted when a file is established
    to be a media_file and the FileSourceFactory() is included in the signal.

    The "not_media_file" signal is emitted if a file is not a media_file.

    The "finished-analyzing" signal is emitted a file is finished being analyzed

    The "starting" signal isemitted when the discoverer starts analyzing some
    files.

    The "ready" signal is emitted when the discoverer has no more files to
    analyze.
    """

    __gsignals__ = {
        "new_sourcefilefactory" : (gobject.SIGNAL_RUN_LAST,
                                   gobject.TYPE_NONE,
                                   (gobject.TYPE_PYOBJECT, )),
        "not_media_file" : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)),
        "finished_analyzing" : ( gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject.TYPE_PYOBJECT, )),
        "ready" : ( gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    ( )),
        "starting" : ( gobject.SIGNAL_RUN_LAST,
                       gobject.TYPE_NONE,
                       ( ))
        }

    def __init__(self, project):
        gst.log("new discoverer for project %s" % project)
        gobject.GObject.__init__(self)
        self.project = project
        self.queue = []
        self.working = False
        self.analyzing = False
        self.currentfactory = None
        self.current = None
        self.currentTags = []
        self.pipeline = None
        self.thisdone = False
        self.prerolled = False
        self.nomorepads = False
        self.timeoutid = 0
        self.signalsid = []
        self.error = None # reason for error
        self.extrainfo = None # extra information about the error
        self.fakesink = None
        self.isimage = False # Used to know if the file is an image

    def addFile(self, filename):
        """ queue a filename to be discovered """
        gst.info("filename: %s" % filename)
        self.queue.append(filename)
        if not self.working:
            self._startAnalysis()

    def addFiles(self, filenames):
        """ queue a list of filenames to be discovered """
        gst.info("filenames : %s" % filenames)
        self.queue.extend(filenames)
        if not self.working:
            self._startAnalysis()

    def _startAnalysis(self):
        """
        Call this method to start analyzing the uris
        """
        if self.working:
            gst.warning("called when still working!")
            return False

        if not self.queue:
            gst.warning("Nothing to analyze!!")
            return False

        self.working = True
        self.emit("starting")
        gobject.idle_add(self._analyze)
        return False

    def _finishAnalysis(self):
        """
        Call this method when the current file is analyzed
        This method will wrap-up the analyzis and call the next analysis if needed
        """
        if not self.analyzing:
            gst.warning("called when not analyzing!!")
            return False

        if self.timeoutid:
            gobject.source_remove(self.timeoutid)
            self.timeoutid = 0

        self.thisdone = True

        gst.info("Cleaning up after finished analyzing %s" % self.current)
        # finish current, cleanup
        self.bus.remove_signal_watch()
        self.bus = None
        gst.log("disconnecting all signal handlers")
        for sobject, sigid in self.signalsid:
            sobject.disconnect(sigid)
        self.signalsid = []
        gst.info("before setting to NULL")
        res = self.pipeline.set_state(gst.STATE_NULL)
        gst.info("after setting to NULL : %s" % res)
        if self.fakesink:
            self.fakesink.set_state(gst.STATE_NULL)
        if self.error:
            self.emit('not_media_file', self.current, self.error, self.extrainfo)
        elif self.currentfactory:
            self.currentfactory.addMediaTags(self.currentTags)
            if self.isimage:
                self.currentfactory.setThumbnail(gst.uri_get_location(self.current))
            if not self.currentfactory.getDuration() and not self.isimage:
                self.emit('not_media_file', self.current,
                          _("Could not establish the duration of the file."),
                          _("This clip seems to be in a format which cannot be accessed in a random fashion."))
            else:
                self.emit('finished-analyzing', self.currentfactory)
        self.currentTags = []
        self.analyzing = False
        self.current = None
        self.currentfactory = None
        self.pipeline = None
        self.fakesink = None
        self.prerolled = False
        self.nomorepads = False
        self.error = None
        self.extrainfo = None
        self.isimage = False

        # restart an analysis if there's more...
        if self.queue:
            gobject.idle_add(self._analyze)
        else:
            self.working = False
            gst.info("discoverer is now ready again")
            self.emit("ready")
        return False

    def _timeoutCb(self):
        gst.debug("timeout")
        gobject.idle_add(self._finishAnalysis)
        return False

    def _analyze(self):
        """
        Sets up a pipeline to analyze the given uri
        """
        self.analyzing = True
        self.thisdone = False
        self.current = self.queue.pop(0)
        gst.info("Analyzing %s" % self.current)
        self.currentfactory = None

        # setup graph and start analyzing
        self.pipeline = gst.Pipeline("Discoverer-%s" % self.current)
        source = gst.element_make_from_uri(gst.URI_SRC, self.current, "src-%s" % self.current)
        if not source:
            gst.warning("This is not a media file : %s" % self.current)
            if not self.error:
                self.error = _("Couldn't construct pipeline.")
                self.extrainfo = _("GStreamer does not have an element to handle files coming from this type of file system.")
            gobject.idle_add(self._finishAnalysis)
            return False
        if os.getenv("USE_DECODEBIN2"):
            dbin = gst.element_factory_make("decodebin2", "dbin")
        else:
            dbin = gst.element_factory_make("decodebin", "dbin")
        self.signalsid.append((dbin, dbin.connect("new-decoded-pad", self._newDecodedPadCb)))
        self.signalsid.append((dbin, dbin.connect("unknown-type", self._unknownTypeCb)))
        self.signalsid.append((dbin, dbin.connect("no-more-pads", self._noMorePadsCb)))
        tfind = dbin.get_by_name("typefind")
        self.signalsid.append((tfind, tfind.connect("have-type", self._typefindHaveTypeCb)))
        self.pipeline.add(source, dbin)
        source.link(dbin)
        gst.info("analysis pipeline created")

        # adding fakesink to make pipeline not terminate state before receiving no-more-pads
        self.fakesink = gst.element_factory_make("fakesink")
        self.pipeline.add(self.fakesink)

        self.bus = self.pipeline.get_bus()
        self.signalsid.append((self.bus, self.bus.connect("message", self._busMessageCb)))
        self.bus.add_signal_watch()

        gst.info("setting pipeline to PAUSED")
        if self.pipeline.set_state(gst.STATE_PAUSED) == gst.STATE_CHANGE_FAILURE:
            if not self.error:
                self.error = _("Pipeline didn't want to go to PAUSED.")
            gst.info("pipeline didn't want to go to PAUSED")
            gobject.idle_add(self._finishAnalysis)
            return False

        # timeout callback for 10s
        self.timeoutid = gobject.timeout_add(10000, self._timeoutCb)

        # return False so we don't get called again
        return False

    def _typefindHaveTypeCb(self, typefind, perc, caps):
        if caps.to_string().startswith("image/"):
            self.isimage = True

    def _busMessageCb(self, unused_bus, message):
        if self.thisdone:
            return
        gst.log("%s:%s" % (message.src.get_name(), message.type))
        if message.type == gst.MESSAGE_STATE_CHANGED:
            gst.log("%s:%s" % ( message.src, message.parse_state_changed()))
            if message.src == self.pipeline:
                prev, new, pending = message.parse_state_changed()
                if prev == gst.STATE_READY and new == gst.STATE_PAUSED and pending == gst.STATE_VOID_PENDING:
                    self.prerolled = True
                    # Let's get the information from all the pads
                    self._getPadsInfo()
                    # Only go to PLAYING if we have an video stream to thumbnail
                    if self.currentfactory and self.currentfactory.is_video and not self.isimage:
                        gst.log("pipeline has gone to PAUSED, now pushing to PLAYING")
                        if self.pipeline.set_state(gst.STATE_PLAYING) == gst.STATE_CHANGE_FAILURE:
                            if not self.error:
                                self.error = _("Pipeline didn't want to go to PLAYING.")
                            gst.info("Pipeline didn't want to go to playing")
                            gobject.idle_add(self._finishAnalysis)
                    elif self.nomorepads:
                        gst.info("finished analyzing")
                        gobject.idle_add(self._finishAnalysis)
                    else:
                        gst.warning("got prerolled but haven't got all pads yet")
        elif message.type == gst.MESSAGE_EOS:
            gst.log("got EOS")
            self.thisdone = True
            filename = "/tmp/" + self.currentfactory.name.encode('base64').replace('\n','') + ".png"
            if os.path.isfile(filename):
                self.currentfactory.setThumbnail(filename)
            gobject.idle_add(self._finishAnalysis)
        elif message.type == gst.MESSAGE_ERROR:
            error, detail = message.parse_error()
            self._handleError(error, detail, message.src)
        elif message.type == gst.MESSAGE_WARNING:
            gst.warning("got a WARNING")
        elif message.type == gst.MESSAGE_ELEMENT:
            gst.debug("Element message %s" % message.structure.to_string())
            if message.structure.get_name() == "redirect":
                gst.warning("We don't implement redirections currently, ignoring file")
                if not self.error:
                    self.error = _("File contains a redirection to another clip.")
                    self.extrainfo = _("PiTiVi does not currently does not handle redirection files.")
                gobject.idle_add(self._finishAnalysis)
        elif message.type == gst.MESSAGE_TAG:
            gst.debug("Got tags %s" % message.structure.to_string())
            self.currentTags.append(message.parse_tag())
        else:
            gst.log("%s:%s" % ( message.type, message.src))

    def _handleError(self, gerror, detail, unused_source):
        gst.warning("got an ERROR")

        if not self.error:
            self.error = _("An internal error occured while analyzing this file : %s") % gerror.message
            self.extrainfo = detail

        self.thisdone = True
        self.currentfactory = None
        gobject.idle_add(self._finishAnalysis)

    def _getPadsInfo(self):
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
                if not self.currentfactory:
                    self.currentfactory = objectfactory.FileSourceFactory(self.current, self.project)
                    self.emit("new_sourcefilefactory", self.currentfactory)
                if caps.to_string().startswith("audio/x-raw") and not self.currentfactory.audio_info:
                    self.currentfactory.setAudioInfo(caps)
                elif caps.to_string().startswith("video/x-raw") and not self.currentfactory.video_info:
                    self.currentfactory.setVideoInfo(caps)
            if not self.currentfactory.getDuration():
                try:
                    length, format = pad.query_duration(gst.FORMAT_TIME)
                except:
                    pad.warning("duration query failed")
                else:
                    if format == gst.FORMAT_TIME:
                        self.currentfactory.set_property("length", length)

    def _vcapsNotifyCb(self, pad, unused_property):
        gst.info("pad:%s , caps:%s" % (pad, pad.get_caps().to_string()))
        if pad.get_caps().is_fixed() and (not self.currentfactory.video_info_stream or not self.currentfactory.video_info_stream.fixed):
            self.currentfactory.setVideoInfo(pad.get_caps())

    def _newVideoPadCb(self, element, pad):
        """ a new video pad was found """
        gst.debug("pad %s" % pad)

        self.currentfactory.setVideo(True)

        if pad.get_caps().is_fixed():
            self.currentfactory.setVideoInfo(pad.get_caps())

        q = gst.element_factory_make("queue")
        q.props.max_size_bytes = 5 * 1024 * 1024
        q.props.max_size_time = 5 * gst.SECOND
        csp = gst.element_factory_make("ffmpegcolorspace")
        pngenc = gst.element_factory_make("pngenc")
        pngsink = gst.element_factory_make("filesink")
        pngsink.set_property("location", "/tmp/" + self.currentfactory.name.encode('base64').replace('\n','') + ".png")

        self.pipeline.add(q, csp, pngenc, pngsink)
        gst.element_link_many(q, csp, pngenc, pngsink)
        pad.link(q.get_pad("sink"))

        if not self.currentfactory.video_info:
            self.signalsid.append((pad, pad.connect("notify::caps", self._vcapsNotifyCb)))

        for element in [q, csp, pngenc, pngsink]:
            element.set_state(gst.STATE_PAUSED)

        if self.currentfactory.is_audio:
            gst.debug("already have audio, calling no_more_pads")
            self._noMorePadsCb(None)

    def _newAudioPadCb(self, unused_element, pad):
        """ a new audio pad was found """
        gst.debug("pad %s" % pad)

        self.currentfactory.setAudio(True)

        # if we already saw another pad, remove no-more-pads hack
        if self.currentfactory.is_video:
            gst.debug("already have video, calling no_more_pads")
            self._noMorePadsCb(None)

        if pad.get_caps().is_fixed():
            gst.debug("fixed caps, setting info on factory")
            self.currentfactory.setAudioInfo(pad.get_caps())
            # if we already have fixed caps, we don't need to take this stream.
        else:
            gst.debug("non-fixed caps, adding queue and fakesink")
            ##         if not self.currentfactory.is_video:
            # we need to add a fakesink
            q = gst.element_factory_make("queue")
            fakesink = gst.element_factory_make("fakesink")
            self.pipeline.add(fakesink, q)
            pad.link(q.get_pad("sink"))
            q.link(fakesink)
            q.set_state(gst.STATE_PAUSED)
            fakesink.set_state(gst.STATE_PAUSED)

    def _unknownTypeCb(self, unused_dbin, unused_pad, caps):
        gst.info(caps.to_string())
        if not self.currentfactory or (not self.currentfactory.is_audio and not self.currentfactory.is_video):
            gst.warning("got unknown pad without anything else")
            if not self.error:
                self.error = _("Got unknown stream type : %s") % caps.to_string()
                self.extrainfo = _("You are missing an element to handle this media type.")
            gobject.idle_add(self._finishAnalysis)

    def _newDecodedPadCb(self, element, pad, is_last):
        # check out the type (audio/video)
        # if we don't already have self.currentfactory
        #   create one, emit "new_sourcefile_factory"
        capsstr = pad.get_caps().to_string()
        gst.info("pad:%s caps:%s is_last:%s" % (pad, capsstr, is_last))
        if capsstr.startswith("video/x-raw"):
            if not self.currentfactory:
                self.currentfactory = objectfactory.FileSourceFactory(self.current, self.project)
                self.emit("new_sourcefilefactory", self.currentfactory)
            self._newVideoPadCb(element, pad)
        elif capsstr.startswith("audio/x-raw"):
            if not self.currentfactory:
                self.currentfactory = objectfactory.FileSourceFactory(self.current, self.project)
                self.emit("new_sourcefilefactory", self.currentfactory)
            self._newAudioPadCb(element, pad)
        else:
            if is_last:
                if not self.currentfactory or not self.currentfactory.is_audio or not self.currentfactory.is_video:
                    gst.warning("couldn't find a usable pad")
                    if not self.error:
                        self.error = "Got unknown stream type : %s" % capsstr
                        self.extrainfo = _("You are missing an element to handle this media type.")
                    gobject.idle_add(self._finishAnalysis)

    def _noMorePadsCb(self, unused_element):
        gst.debug("no more pads on decodebin !")
        self.nomorepads = True

        # remove fakesink
        gst.debug("removing fakesink")
        if self.fakesink:
            self.fakesink.set_state(gst.STATE_NULL)
            self.pipeline.remove(self.fakesink)
            self.fakesink = None
        # normally state changes should end the discovery
