# PiTiVi , Non-linear video editor
#
#       discoverer.py
#
# Copyright (c) 2005-2008, Edward Hervey <bilboed@bilboed.com>
#               2008, Alessandro Decina <alessandro.decina@collabora.co.uk>
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Discover file multimedia information.
"""

from gettext import gettext as _
import os
import gobject
gobject.threads_init()
import gst
from gst import pbutils
import tempfile
import hashlib

from pitivi.log.loggable import Loggable
from pitivi.factories.file import FileSourceFactory, PictureFileSourceFactory
from pitivi.stream import get_stream_for_pad
from pitivi.signalinterface import Signallable
from pitivi.stream import VideoStream, TextStream
from pitivi.settings import xdg_cache_home

# FIXME: We need to store more information regarding streams
# i.e. remember the path took to get to a raw stream, and figure out
# what encoded format it is
# We will need that in order to create proper Stream objects.


class EOSSir(gst.Element):
    __gstdetails__ = (
        "EOSSir",
        "Generic",
        "pushes EOS after the first buffer",
        "Alessandro Decina <alessandro.d@gmail.com>"
        )

    srctemplate = gst.PadTemplate("src", gst.PAD_SRC,
            gst.PAD_ALWAYS, gst.Caps("ANY"))
    sinktemplate = gst.PadTemplate("sink", gst.PAD_SINK,
            gst.PAD_ALWAYS, gst.Caps("ANY"))

    __gsttemplates__ = (srctemplate, sinktemplate)

    def __init__(self):
        gst.Element.__init__(self)

        self.sinkpad = gst.Pad(self.sinktemplate, "sink")
        self.sinkpad.set_chain_function(self.chain)
        self.add_pad(self.sinkpad)

        self.srcpad = gst.Pad(self.srctemplate, "src")
        self.add_pad(self.srcpad)

    def chain(self, pad, buf):
        ret = self.srcpad.push(buf)
        if ret == gst.FLOW_OK:
            self.info("pushed, doing EOS")
            self.srcpad.push_event(gst.event_new_eos())

        return ret
gobject.type_register(EOSSir)


class Discoverer(Signallable, Loggable):
    """
    Queues requests to discover information about given files.
    The discovery is done in a very fragmented way, so that it appears to be
    running in a separate thread.

    The "starting" signal is emitted when the discoverer starts analyzing some
    files.

    The "ready" signal is emitted when the discoverer has no more files to
    analyze.

    The "discovery-done" signal is emitted an uri is finished being analyzed.
    The "discovery-error" signal is emitted if an error is encountered while
    analyzing an uri.
    """

    __signals__ = {
        "discovery-error": ["a", "b", "c"],
        "discovery-done": ["uri", "factory"],
        "ready": None,
        "starting": None,
        "missing-plugins": ["uri", "detail", "description"]
        }

    def __init__(self):
        Loggable.__init__(self)
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
        self.error_detail = None
        self.unfixed_pads = 0
        self.unknown_pads = 0
        self.missing_plugin_messages = []
        self.dynamic_elements = []
        self.thumbnails = {}
        self.missing_plugin_details = []
        self.missing_plugin_descriptions = []

    def _resetPipeline(self):
        # finish current, cleanup
        if self.bus is not None:
            self.bus.remove_signal_watch()
            self.bus = None

        if self.pipeline is not None:
            self.debug("before setting to NULL")
            res = self.pipeline.set_state(gst.STATE_NULL)
            self.debug("after setting to NULL : %s", res)

        for element in self.dynamic_elements:
            self.pipeline.remove(element)

    def addUri(self, uri):
        """ queue a filename to be discovered """
        self.info("filename: %s", uri)
        self.queue.append(uri)
        if not self.working:
            self._startAnalysis()

    def addUris(self, uris):
        """ queue a list of filenames to be discovered """
        self.info("filenames : %s", uris)
        self.queue.extend(uris)
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

    def _checkMissingPlugins(self):
        if self.bus is not None:
            # This method is usually called when decodebin(2) reaches PAUSED and
            # we stop analyzing the current source.
            # decodebin2 commits its state change to PAUSED _before_ posting
            # missing-plugin messages, so we manually pop ELEMENT messages
            # looking for queued missing-plugin messages.
            while True:
                message = self.bus.pop_filtered(gst.MESSAGE_ELEMENT)
                if message is None:
                    break

                self._busMessageElementCb(self.bus, message)

        if not self.missing_plugin_messages:
            return False

        for message in self.missing_plugin_messages:
            detail = \
                    pbutils.missing_plugin_message_get_installer_detail(message)
            description = \
                    pbutils.missing_plugin_message_get_description(message)

            self.missing_plugin_details.append(detail)
            self.missing_plugin_descriptions.append(description)

        return True

    def _installMissingPluginsCallback(self, result, factory):
        rescan = False

        if result in (pbutils.INSTALL_PLUGINS_SUCCESS,
                pbutils.INSTALL_PLUGINS_PARTIAL_SUCCESS):
            gst.update_registry()
            rescan = True
        elif result == pbutils.INSTALL_PLUGINS_USER_ABORT \
                and factory.getOutputStreams():
            self._emitDone(factory)
        else:
            self._emitErrorMissingPlugins()

        self._finishAnalysisAfterResult(rescan=rescan)

    def _emitError(self):
        self.debug("emitting error %s, %s, %s",
                self.current_uri, self.error, self.error_detail)
        self.emit("discovery-error", self.current_uri, self.error, self.error_detail)

    def _emitErrorMissingPlugins(self):
        self.error = _("Missing plugins:\n%s") % \
                "\n".join(self.missing_plugin_descriptions)
        self.error_detail = ""
        self._emitError()

    def _emitDone(self, factory):
        self.emit("discovery-done", self.current_uri, factory)

    def _emitResult(self):
        missing_plugins = bool(self.missing_plugin_details)
        # we got a gst error, error out ASAP
        if not missing_plugins and self.error:
            self._emitError()
            return True

        have_video, have_audio, have_image = self._getCurrentStreamTypes()
        missing_plugins = bool(self.missing_plugin_details)

        if not self.current_streams and not missing_plugins:
            # woot, nothing decodable
            self.error = _('Cannot decode file.')
            self.error_detail = _("The given file does not contain audio, "
                    "video or picture streams.")
            self._emitError()
            return True

        # construct the factory with the streams we found
        if have_image and self.current_duration == gst.CLOCK_TIME_NONE:
            factory = PictureFileSourceFactory(self.current_uri)
        else:
            factory = FileSourceFactory(self.current_uri)

        factory.duration = self.current_duration
        for stream in self.current_streams:
            factory.addOutputStream(stream)

        if not missing_plugins:
            # make sure that we could query the duration (if it's an image, we
            # assume it's got infinite duration)
            is_image = have_image and len(self.current_streams) == 1
            if self.current_duration == gst.CLOCK_TIME_NONE and not is_image:
                self.error = _("Could not establish the duration of the file.")
                self.error_detail = _("This clip seems to be in a format "
                        "which cannot be accessed in a random fashion.")
                self._emitError()
                return True

            self._emitDone(factory)
            return True

        def callback(result):
            self._installMissingPluginsCallback(result, factory)

        res = self.emit("missing-plugins", self.current_uri, factory,
                self.missing_plugin_details,
                self.missing_plugin_descriptions,
                callback)
        if res is None or res != pbutils.INSTALL_PLUGINS_STARTED_OK:
            # no missing-plugins handlers
            if factory.getOutputStreams():
                self._emitDone(factory)
            else:
                self._emitErrorMissingPlugins()

            return True

        # plugins are being installed, processing will continue when
        # self._installMissingPluginsCallback is called by the application
        return False

    def _finishAnalysis(self, reason):
        """
        Call this method when the current file is analyzed
        This method will wrap-up the analyzis and call the next analysis if needed
        """
        if self.timeout_id:
            self._removeTimeout()

        self.info("analysys finished, reason %s", reason)

        # check if there are missing plugins before calling _resetPipeline as we
        # are going to pop messagess off the bus
        self._checkMissingPlugins()
        self._resetPipeline()

        # emit discovery-done, discovery-error or missing-plugins
        if self._emitResult():
            self._finishAnalysisAfterResult()

    def _finishAnalysisAfterResult(self, rescan=False):
        self.info("Cleaning up after finished analyzing %s", self.current_uri)
        self._resetState()

        if not rescan:
            self.queue.pop(0)
        # restart an analysis if there's more...
        if self.queue:
            self._scheduleAnalysis()
        else:
            self.working = False
            self.info("discoverer is now ready again")
            self.emit("ready")

    def _timeoutCb(self):
        self.debug("timeout")
        self.timeout_id = 0
        if not self.error:
            self.error = _('Timeout while analyzing file.')
            self.error_detail = _('Analyzing the file took too long.')
        self._finishAnalysis("timeout")

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
            elif caps_str.startswith('audio'):
                have_audio = True

        return have_video, have_audio, have_image

    def _scheduleTimeout(self):
        self.timeout_id = gobject.timeout_add_seconds(10, self._timeoutCb)

    def _createSource(self):
        source = gst.element_make_from_uri(gst.URI_SRC,
                self.current_uri, "src-%s" % self.current_uri)
        if not source:
            self.warning("This is not a media file: %s", self.current_uri)
            self.error = _("No available source handler.")
            self.error_detail = _('You do not have a GStreamer source element to handle the "%s" protocol') % gst.uri_get_protocol(self.current_uri)

            return None

        # increment source blocksize to 128kbytes, this should speed up
        # push-mode scenarios (like pictures).
        if hasattr(source.props, 'blocksize'):
            source.props.blocksize = 131072
        return source

    def _useDecodeBinTwo(self):
        ret = os.getenv('USE_DECODEBIN2', '1') == '1'
        return ret

    def _createDecodeBin(self):
        if self._useDecodeBinTwo():
            dbin = gst.element_factory_make("decodebin2", "dbin")
        else:
            dbin = gst.element_factory_make("decodebin", "dbin")

        dbin.connect("new-decoded-pad", self._newDecodedPadCb)
        dbin.connect("unknown-type", self._unknownType)

        return dbin

    def _connectToBus(self):
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", self._busMessageEosCb)
        self.bus.connect("message::error", self._busMessageErrorCb)
        self.bus.connect("message::element", self._busMessageElementCb)
        self.bus.connect("message::state-changed",
                         self._busMessageStateChangedCb)

    def _analyze(self):
        """
        Sets up a pipeline to analyze the given uri
        """
        self.current_uri = self.queue[0]
        self.info("Analyzing %s", self.current_uri)

        # check if file exists and is readable
        if gst.uri_get_protocol(self.current_uri) == "file":
            filename = gst.uri_get_location(self.current_uri)
            if not os.access(filename, os.R_OK):
                self.error = _("File not readable by current user")
                self.info("Error: %s", self.error)
                self._finishAnalysis("File does not exist or is not readable by the current user")
                return False

        # setup graph and start analyzing
        self.pipeline = gst.Pipeline("Discoverer-%s" % self.current_uri)

        # create the source element
        source = self._createSource()
        if source is None:
            self._finishAnalysis("no source")
            return False

        # create decodebin(2)
        dbin = self._createDecodeBin()

        self.pipeline.add(source, dbin)
        source.link(dbin)
        self.info("analysis pipeline created")

        # connect to bus messages
        self._connectToBus()

        self.info("setting pipeline to PAUSED")

        # go to PAUSED
        if self.pipeline.set_state(gst.STATE_PAUSED) == gst.STATE_CHANGE_FAILURE:
            if not self.error:
                self.error = _("Pipeline didn't want to go to PAUSED.")
            self.info("Pipeline didn't want to go to PAUSED")
            self._finishAnalysis("failure going to PAUSED")

            return False

        self._scheduleTimeout()

        # return False so we don't get called again
        return False

    def _busMessageEosCb(self, unused_bus, message):
        self.debug("got EOS")

        self._finishAnalysis("EOS")

    def _busMessageErrorCb(self, unused_bus, message):
        gerror, detail = message.parse_error()

        if self.error is not None:
            # don't clobber existing errors
            return

        self.error = _("An internal error occurred while analyzing this file: %s") % gerror.message
        self.error_detail = detail

        self._finishAnalysis("ERROR")

    def _busMessageElementCb(self, unused_bus, message):
        self.debug("Element message %s", message.structure.to_string())
        if message.structure.get_name() == "redirect":
            self.warning("We don't implement redirections currently, ignoring file")
            if self.error is None:
                self.error = _("File contains a redirection to another clip.")
                self.error_detail = _("PiTiVi currently does not handle redirection files.")

            self._finishAnalysis("redirect")
            return

        if pbutils.is_missing_plugin_message(message):
            self._busMessageMissingPlugins(message)

    def _busMessageMissingPlugins(self, message):
        self.missing_plugin_messages.append(message)

    def _busMessageStateChangedCb(self, unused_bus, message):
        if message.src != self.pipeline:
            return

        state_change = message.parse_state_changed()
        self.log("%s:%s", message.src, state_change)
        prev, new, pending = state_change

        if prev == gst.STATE_READY and new == gst.STATE_PAUSED and \
                pending == gst.STATE_VOID_PENDING:
            have_video, have_audio, have_image = self._getCurrentStreamTypes()
            if self.unfixed_pads or self.unknown_pads or have_video or have_image:
                # go to PLAYING to generate the thumbnails
                if self.pipeline.set_state(gst.STATE_PLAYING) == gst.STATE_CHANGE_FAILURE:
                    if not self.error:
                        self.error = _("Pipeline didn't want to go to PLAYING.")
                    self.info("Pipeline didn't want to go to PAUSED")
                    self._finishAnalysis("failure going to PAUSED")
            elif self.unfixed_pads == 0:
                # check for unfixed_pads until elements are fixed to do
                # negotiation before pushing in band data
                self._finishAnalysis("got to PAUSED and no unfixed pads")

    def _busMessageTagCb(self, unused_bus, message):
        self.debug("Got tags %s", message.structure.to_string())
        self.current_tags.append(message.parse_tag())

    def _maybeQueryDuration(self, pad):
        if self.current_duration == gst.CLOCK_TIME_NONE:
            result = pad.query_duration(gst.FORMAT_TIME)
            if result is not None:
                duration, format = result
                if format == gst.FORMAT_TIME:
                    self.current_duration = duration

    def _gettempdir(self):
        tmp = tempfile.gettempdir()
        tmp = os.path.join(tmp, 'pitivi-%s' % os.getenv('USER'))
        if not os.path.exists(tmp):
            os.mkdir(tmp)
        return tmp

    def _getThumbnailFilenameFromPad(self, pad):
        base = xdg_cache_home()
        name = self.current_uri
        md5sum = hashlib.md5()
        md5sum.update(self.current_uri)
        name = md5sum.hexdigest() + '.png'
        directory = os.path.join(base, "pitivi")
        try:
            os.makedirs(directory)
        except OSError, e:
            # 17 = file exists
            if e.errno != 17:
                raise
        filename = os.path.join(base, "pitivi", name)

        return filename

    def _videoPadSeekCb(self, pad):
        try:
            duration = self.pipeline.query_duration(gst.FORMAT_TIME)[0]
        except gst.QueryError:
            duration = 0

        self.debug("doing thumbnail seek at %s", gst.TIME_ARGS(duration))

        if duration:
            self.pipeline.seek_simple(gst.FORMAT_TIME,
                    gst.SEEK_FLAG_FLUSH, duration / 3)

        pad.set_blocked_async(False, self._videoPadBlockCb)

    def _videoPadBlockCb(self, pad, blocked):
        self.debug("video pad blocked: %s" % blocked)
        if blocked:
            gobject.timeout_add(0, self._videoPadSeekCb, pad)

    def _addVideoBufferProbe(self, pad):
        closure = {}
        closure['probe_id'] = pad.add_buffer_probe(self._videoBufferProbeCb,
                closure)

    def _removeVideoBufferProbe(self, pad, closure):
        pad.remove_buffer_probe(closure['probe_id'])

    def _videoBufferProbeCb(self, pad, buf, closure):
        self.log("video buffer probe for pad %s", pad)
        self._removeVideoBufferProbe(pad, closure)

        pad.set_blocked_async(True, self._videoPadBlockCb)

        return False

    def _padEventProbeCb(self, pad, event):
        self.log("got event %s from src %s on pad %s",
                event.type, event.src, pad)

        return True

    def _padBufferProbeCb(self, pad, buf):
        self.debug("got buffer on pad %s", pad)

        return True

    def _addPadProbes(self, pad):
        pad.add_event_probe(self._padEventProbeCb)
        pad.add_buffer_probe(self._padBufferProbeCb)

    def _newVideoPadCb(self, pad):
        """ a new video pad was found """
        self.debug("pad %r", pad)

        self._addPadProbes(pad)

        thumbnail = self._getThumbnailFilenameFromPad(pad)
        self.thumbnails[pad] = thumbnail
        have_thumbnail = os.path.exists(thumbnail)

        if have_thumbnail:
            self.debug("we already have a thumbnail %s for %s", thumbnail, pad)
            sink = gst.element_factory_make("fakesink")
            # use this and not fakesink.props.num_buffers = 1 to avoid some
            # not-expected errors when discovering pictures
            eossir = EOSSir()
            self.dynamic_elements.extend([eossir, sink])
            self.pipeline.add(eossir, sink)
            eossir.set_state(gst.STATE_PLAYING)
            sink.set_state(gst.STATE_PLAYING)

            pad.link(eossir.get_pad("sink"))
            eossir.link(sink)

            return

        stream = get_stream_for_pad(pad)
        if isinstance(stream, VideoStream) and not stream.is_image:
            self._addVideoBufferProbe(pad)

        queue = gst.element_factory_make("queue")
        queue.props.max_size_bytes = 5 * 1024 * 1024
        queue.props.max_size_time = 5 * gst.SECOND
        vscale = gst.element_factory_make("videoscale")
        vscale.props.method = 0
        csp = gst.element_factory_make("ffmpegcolorspace")
        pngenc = gst.element_factory_make("pngenc")
        pngenc.props.snapshot = True
        pngsink = gst.element_factory_make("filesink")
        pngsink.props.location = thumbnail

        self.dynamic_elements.extend([queue, vscale, csp, pngenc, pngsink])

        self.pipeline.add(queue, vscale, csp, pngenc, pngsink)
        gst.element_link_many(queue, csp, vscale)
        vscale.link(pngenc, gst.Caps("video/x-raw-rgb,width=[1,96],height=[1,96];video/x-raw-yuv,width=[1,96],height=[1,96]"))
        gst.element_link_many(pngenc, pngsink)
        pad.link(queue.get_pad("sink"))

        for element in [queue, vscale, csp, pngenc, pngsink]:
            element.sync_state_with_parent()

    def _newPadCb(self, pad):
        stream = get_stream_for_pad(pad)
        if isinstance(stream, TextStream):
            self.info("skipping subtitle pad")
            return

        self._addPadProbes(pad)

        queue = gst.element_factory_make('queue')
        fakesink = gst.element_factory_make('fakesink')
        fakesink.props.num_buffers = 1
        self.dynamic_elements.append(queue)
        self.dynamic_elements.append(fakesink)

        self.pipeline.add(queue, fakesink)
        pad.link(queue.get_pad('sink'))
        queue.link(fakesink)

        queue.sync_state_with_parent()
        fakesink.sync_state_with_parent()

    def _capsNotifyCb(self, pad, unused_property, ghost=None):
        if ghost is None:
            ghost = pad

        caps = pad.props.caps
        self.debug("pad caps notify %s", caps)
        if caps is None or not caps.is_fixed():
            return

        pad.disconnect_by_func(self._capsNotifyCb)

        self.info("got fixed caps for pad %s", pad)

        self.unfixed_pads -= 1
        self.debug("unfixed pads %d", self.unfixed_pads)
        stream = self._addStreamFromPad(ghost)
        if isinstance(stream, VideoStream):
            stream.thumbnail = self.thumbnails[ghost]

    def _newDecodedPadCb(self, unused_element, pad, is_last):
        self.info("pad:%s caps:%s is_last:%s", pad, pad.get_caps(), is_last)

        caps_str = str(pad.get_caps())
        if caps_str.startswith("video/x-raw"):
            self._newVideoPadCb(pad)
        else:
            self._newPadCb(pad)

        # try to get the duration
        self._maybeQueryDuration(pad)

        caps = pad.props.caps

        if caps is not None and caps.is_fixed():
            self.debug("got fixed caps for pad %s", pad)

            stream = self._addStreamFromPad(pad)
            if isinstance(stream, VideoStream):
                stream.thumbnail = self.thumbnails[pad]
        else:
            # add the stream once the caps are fixed
            if gst.version() < (0, 10, 21, 1) and \
                    isinstance(pad, gst.GhostPad):
                # see #564863 for the version check
                # the isinstance check is there so that we don't have to create
                # ghost pads in the tests
                pad.get_target().connect("notify::caps",
                        self._capsNotifyCb, pad)
            else:
                pad.connect("notify::caps", self._capsNotifyCb)
            self.unfixed_pads += 1
            self.debug("unfixed pads %d", self.unfixed_pads)

    def _unknownType(self, decodebin, pad, caps):
        # decodebin2 sends ASYNC_DONE when it finds an unknown type so we have
        # to deal with that...
        self.unknown_pads += 1

    def _addStreamFromPad(self, pad):
        self._maybeQueryDuration(pad)
        self.debug("adding stream from pad %s caps %s", pad, pad.props.caps)
        stream = get_stream_for_pad(pad)
        self.current_streams.append(stream)

        return stream

if __name__ == '__main__':
    import sys
    import gobject

    discoverer = Discoverer()
    discoverer.addUris(['file://%s' % i  for i in sys.argv[1:]])
    loop = gobject.MainLoop()
    loop.run()
