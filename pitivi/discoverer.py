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

from gettext import gettext as _
import os.path
import gobject
import gst
import tempfile

from pitivi.factories.base import ObjectFactoryStreamError
from pitivi.factories.file import FileSourceFactory, PictureFileSourceFactory
from pitivi.stream import get_stream_for_caps
from pitivi.signalinterface import Signallable

# FIXME: We need to store more information regarding streams
# i.e. remember the path took to get to a raw stream, and figure out
# what encoded format it is
# We will need that in order to create proper Stream objects.

class Discoverer(object, Signallable):
    """
    Queues requests to discover information about given files.
    The discovery is done in a very fragmented way, so that it appears to be
    running in a separate thread.

    The "new_sourcefilefactory" signal is emitted when a file is established
    to be a media_file and the FileSourceFactory() is included in the signal.

    The "not_media_file" signal is emitted if a file is not a media_file.

    The "finished-analyzing" signal is emitted a file is finished being analyzed

    The "starting" signal is emitted when the discoverer starts analyzing some
    files.

    The "ready" signal is emitted when the discoverer has no more files to
    analyze.
    """

    __signals__ = {
        "new_sourcefilefactory" : ["factory"],
        "not_media_file" : ["a", "b", "c" ],
        "finished_analyzing" : ["factory"],
        "ready" : None,
        "starting" : None,
        }

    def __init__(self):
        self.queue = []
        self.working = False
        self.timeout_id = 0
        self._resetState()

    def _resetState(self):
        self.current_uri = None
        self.current_tags = []
        self.current_streams = []
        self.current_duration = gst.CLOCK_TIME_NONE
        self.pipeline = None
        self.bus = None
        self.error = None
        self.error_debug = None
        
    def _resetPipeline(self):
        # finish current, cleanup
        if self.bus is not None:
            self.bus.remove_signal_watch()
            self.bus = None
        
        if self.pipeline is not None:
            gst.info("before setting to NULL")
            res = self.pipeline.set_state(gst.STATE_NULL)
            gst.info("after setting to NULL : %s" % res)

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
        if self.queue and not self.working:
            self._startAnalysis()

    def _startAnalysis(self):
        """
        Call this method to start analyzing the uris
        """
        self.working = True
        self.emit("starting")
        
        self._scheduleAnalysis()

    def _scheduleAnalysis(self):
        gobject.idle_add(self._analyze)

    def _removeTimeout(self):
        gobject.source_remove(self.timeout_id)
        self.timeout_id = 0
    
    def _finishAnalysis(self):
        """
        Call this method when the current file is analyzed
        This method will wrap-up the analyzis and call the next analysis if needed
        """
        if self.timeout_id:
            self._removeTimeout()
        
        self._resetPipeline()
        
        if not self.current_streams and self.error is None:
            # EOS and no decodable streams?
            self.error = 'FIXME: no output streams'
            self.error_debug = 'see above'

        if self.error:
            self.emit('not_media_file', self.current_uri, self.error, self.error_debug)
        elif self.current_duration == gst.CLOCK_TIME_NONE:
            self.emit('not_media_file', self.current_uri,
                      _("Could not establish the duration of the file."),
                      _("This clip seems to be in a format which cannot"
                            " be accessed in a random fashion."))
        else:
            have_video, have_audio, have_image = self._getCurrentStreamTypes()
            if have_video or have_audio:
                factory = FileSourceFactory(self.current_uri)
            elif have_image:
                factory = PictureFileSourceFactory(self.current_uri)
            else:
                # woot, nothing decodable
                self.error = 'FIXME: make me translatable: can not decode file'
                self.error_debug = 'see above'
                factory = None
            
            if factory is not None:
                factory.duration = self.current_duration
                
                for stream in self.current_streams:
                    factory.addOutputStream(stream)

                self.emit('new_sourcefilefactory', factory)

            self.emit('finished_analyzing', factory)

        gst.info("Cleaning up after finished analyzing %s" % self.current_uri)
        self._resetState()

        self.queue.pop(0)
        # restart an analysis if there's more...
        if self.queue:
            self._scheduleAnalysis()
        else:
            self.working = False
            gst.info("discoverer is now ready again")
            self.emit("ready")

    def _timeoutCb(self):
        gst.debug("timeout")
        self.timeout_id = 0
        self._finishAnalysis()

        return False

    def _getCurrentStreamTypes(self):
        have_video = False
        have_image = False
        have_audio = False
        for stream in self.current_streams:
            caps_str = str(stream.caps)
            if caps_str.startswith('video'):
                if stream.is_image:
                    have_image = True
                else:
                    have_video = True

                if stream.thumbnail is not None and \
                        not os.path.exists(stream.thumbnail):
                    stream.thumbnail = None
            elif caps_str.startswith('audio'):
                have_audio = True

        return have_video, have_audio, have_image

    def _scheduleTimeout(self):
        self.timeout_id = gobject.timeout_add(1000000, self._timeoutCb)

    def _createSource(self):
        source = gst.element_make_from_uri(gst.URI_SRC,
                self.current_uri, "src-%s" % self.current_uri)

        return source

    def _useDecodeBinTwo(self):
        return os.getenv('USE_DECODEBIN2')

    def _analyze(self):
        """
        Sets up a pipeline to analyze the given uri
        """
        self.current_uri = self.queue[0]
        gst.info("Analyzing %s" % self.current_uri)

        # setup graph and start analyzing
        self.pipeline = gst.Pipeline("Discoverer-%s" % self.current_uri)
       
        source = self._createSource()
        if not source:
            gst.warning("This is not a media file : %s" % self.current_uri)
            self.error = _("Couldn't construct pipeline.")
            self.error_debug = _("GStreamer does not have an element to "
                    "handle files coming from this type of file system.")
            self._finishAnalysis()

            return False

        if self._useDecodeBinTwo():
            dbin = gst.element_factory_make("decodebin2", "dbin")
        else:
            dbin = gst.element_factory_make("decodebin", "dbin")
        
        dbin.connect("new-decoded-pad", self._newDecodedPadCb)
        
        self.pipeline.add(source, dbin)
        source.link(dbin)
        gst.info("analysis pipeline created")

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", self._busMessageEosCb)
        self.bus.connect("message::error", self._busMessageErrorCb)
        self.bus.connect("message::element", self._busMessageElementCb)
        self.bus.connect("message::state-changed",
                self._busMessageStateChangedCb)

        gst.info("setting pipeline to PAUSED")
        if self.pipeline.set_state(gst.STATE_PAUSED) == gst.STATE_CHANGE_FAILURE:
            if not self.error:
                self.error = _("Pipeline didn't want to go to PAUSED.")
            gst.info("pipeline didn't want to go to PAUSED")
            self._finishAnalysis()
            
            return False

        self._scheduleTimeout()

        # return False so we don't get called again
        return False

    def _busMessageEosCb(self, unused_bus, message):
        gst.log("got EOS")

        self._finishAnalysis()

    def _busMessageErrorCb(self, unused_bus, message):
        gerror, detail = message.parse_error()

        if self.error is not None:
            # don't clobber existing errors
            return

        self.error = _("An internal error occured while analyzing "
                "this file : %s") % gerror.message
        self.error_debug = detail

    def _busMessageElementCb(self, unused_bus, message):
        gst.debug("Element message %s" % message.structure.to_string())
        if message.structure.get_name() == "redirect":
            gst.warning("We don't implement redirections currently, ignoring file")
            if self.error is None:
                self.error = _("File contains a redirection to another clip.")
                self.error_debug = _("PiTiVi currently does not handle "
                        "redirection files.")
            
            self._finishAnalysis()
    
    def _busMessageStateChangedCb(self, unused_bus, message):
        if message.src != self.pipeline:
            return

        state_change = message.parse_state_changed()
        gst.log("%s:%s" % ( message.src, state_change))
        prev, new, pending = state_change

        if prev == gst.STATE_READY and new == gst.STATE_PAUSED and \
                pending == gst.STATE_VOID_PENDING:
            have_video, have_audio, have_image = self._getCurrentStreamTypes()
            if have_video or have_image:
                # go to PLAYING to generate the thumbnails
                self.pipeline.set_state(gst.STATE_PLAYING)
            else:
                self._finishAnalysis()

    def _busMessageTagCb(Self, unused_bus, message):
        gst.debug("Got tags %s" % message.structure.to_string())
        self.current_tags.append(message.parse_tag())

    def _maybeQueryDuration(self, pad):
        if self.current_duration == gst.CLOCK_TIME_NONE:
            result = pad.query_duration(gst.FORMAT_TIME)
            if result is not None:
                duration, format = result
                if format == gst.FORMAT_TIME:
                    self.current_duration = duration

    def _getThumbnailFilenameFromPad(self, pad):
        tmp = tempfile.gettempdir()
        name = '%s.%s' % (self.current_uri, pad.get_name())
        name = name.encode('base64').replace('\n', '') + '.png'
        filename = os.path.join(tmp, name)

        return filename

    def _newVideoPadCb(self, pad, stream):
        """ a new video pad was found """
        gst.debug("pad %s" % pad)

        queue = gst.element_factory_make("queue")
        queue.props.max_size_bytes = 5 * 1024 * 1024
        queue.props.max_size_time = 5 * gst.SECOND
        csp = gst.element_factory_make("ffmpegcolorspace")
        pngenc = gst.element_factory_make("pngenc")
        pngsink = gst.element_factory_make("filesink")
        stream.thumbnail = self._getThumbnailFilenameFromPad(pad)
        pngsink.props.location = stream.thumbnail

        self.pipeline.add(queue, csp, pngenc, pngsink)
        gst.element_link_many(queue, csp, pngenc, pngsink)
        pad.link(queue.get_pad("sink"))

        for element in [queue, csp, pngenc, pngsink]:
            element.set_state(gst.STATE_PAUSED)

    def _capsNotifyCb(self, pad, unused_property):
        gst.info("pad:%s , caps:%s" % (pad, pad.get_caps().to_string()))
        caps = pad.props.caps
        if caps is None or not caps.is_fixed():
            return

        stream = self._addStreamFromPad(pad)
        caps_str = str(pad.get_caps())
        if caps_str.startswith("video/x-raw"):
            self._newVideoPadCb(pad, stream)

    def _newDecodedPadCb(self, unused_element, pad, is_last):
        gst.info("pad:%s caps:%s is_last:%s" % (pad, pad.get_caps(), is_last))

        # try to get the duration
        # NOTE: this gets the duration only once, usually for the first stream.
        # Demuxers don't seem to implement per stream duration queries anyway.
        self._maybeQueryDuration(pad)
        
        if pad.get_caps().is_fixed():
            stream = self._addStreamFromPad(pad)
        
            caps_str = str(pad.get_caps())
            if caps_str.startswith("video/x-raw"):
                self._newVideoPadCb(pad, stream)
        else:
            # add the stream once the caps are fixed
            pad.connect("notify::caps", self._capsNotifyCb)

    def _addStreamFromPad(self, pad):
        stream = get_stream_for_caps(pad.get_caps(), pad)
        self.current_streams.append(stream)

        return stream
