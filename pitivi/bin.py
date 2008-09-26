# PiTiVi , Non-linear video editor
#
#       pitivi/bin.py
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
High-level Pipelines with plugable back-ends
"""

import gobject
import gst
from elements.smartscale import SmartVideoScale

class SmartBin(gst.Pipeline):
    """
    High-level pipeline with playing/encoding ready places
    It also has length information
    """

    def __init__(self, name, displayname="", has_video=False, has_audio=False,
                 length=0, width=0, height=0):
        """
        @type name: string
        @param name: The name of the SmartBin (for internal use)
        @type displayname: string
        @param displayname: The user-friendly name of the SmartBin
        """
        gst.log('name : %s, displayname : %s' % (name, displayname))
        gobject.GObject.__init__(self)
        self.length = length
        self.has_video = has_video
        self.has_audio = has_audio
        self.width = width
        self.height = height
        self.name = name
        self.displayname = displayname

        self.vtee = None
        self.atee = None

        self.set_name(name)
        # Until  basetransform issues are fixed, we use an identity instead
        # of a tee
        if self.has_video:
            #self.vtee = gst.element_factory_make("tee", "vtee")
            self.vtee = gst.element_factory_make("identity", "vtee")
            self.add(self.vtee)
        if self.has_audio:
            #self.atee = gst.element_factory_make("tee", "atee")
            self.atee = gst.element_factory_make("identity", "atee")
            self.add(self.atee)
        self._addSource()
        self._connectSource()
        self.asinkthread = None
        self.vsinkthread = None
        self.encthread = None
        self.tmpasink = None
        self.tmpvsink = None
        self.recording = False

    def _addSource(self):
        """ add the source to self """
        raise NotImplementedError

    def _connectSource(self):
        """ connect the source to the tee """
        raise NotImplementedError

    def setAudioSinkThread(self, asinkthread):
        """
        Set the audio sink thread.
        Returns False if there was a problem.
        """
        self.debug("asinkthread : %r" % asinkthread)
        res, state, pending = self.get_state(0)
        if state == gst.STATE_PLAYING:
            self.warning("is in PAUSED or higher : %s" % state)
            return False
        if self.asinkthread:
            self.warning("already has an asinkthread??")
            return False
        if self.has_audio:
            self.asinkthread = asinkthread
            self.add(self.asinkthread)
            # identity vs tee issue
            self.atee.get_pad("src").link(self.asinkthread.get_pad("sink"))
        return True

    def setVideoSinkThread(self, vsinkthread):
        """
        Set the video sink thread.
        Returns False if there was a problem.
        """
        self.debug("vsinkthread : %r" % vsinkthread)
        res , state , pending = self.get_state(0)
        if state == gst.STATE_PLAYING:
            self.warning("is in PAUSED or higher : %s" % state)
            return False
        if self.vsinkthread:
            self.warning("already has an vsinkthread??")
            return False
        if self.has_video:
            self.vsinkthread = vsinkthread
            self.add(self.vsinkthread)
            # identity vs tee issue
            if self.width and self.height:
                self.vtee.get_pad("src").link(self.vsinkthread.get_pad("sink"))
            else:
                self.vtee.get_pad("src").link(self.vsinkthread.get_pad("sink"))
        return True

    def removeAudioSinkThread(self):
        """
        Remove the audio sink thread.
        Returns False if there was a problem.
        """
        self.debug("asinkthread : %r" % self.asinkthread)
        result, state, pending = self.get_state(0)
        if state in [gst.STATE_PAUSED, gst.STATE_PLAYING]:
            self.warning("is in PAUSED, not removing audiosink")
            return False
        if not self.asinkthread:
            self.warning("doesn't have an asinkthread??")
            return False
        self.asinkthread.get_pad("sink").get_peer().unlink(self.asinkthread.get_pad("sink"))
        self.remove(self.asinkthread)
        self.asinkthread = None
        self.log("asinkthread removed succesfully")
        return True

    def removeVideoSinkThread(self):
        """
        Remove the videos sink thread.
        Returns False if there was a problem.
        """
        self.debug("vsinkthread : %r" % self.vsinkthread)
        result, state, pending = self.get_state(0)
        if state in [gst.STATE_PAUSED, gst.STATE_PLAYING]:
            self.warning("is in PAUSED or higher : %s" % state)
            return False
        if not self.vsinkthread:
            self.warning("doesn't have a vsinkthread??")
            return False
        self.vsinkthread.get_pad("sink").get_peer().unlink(self.vsinkthread.get_pad("sink"))
        self.remove(self.vsinkthread)
        self.vsinkthread = None
        self.log("vsinkthread removed succesfully")
        return True

    def getRealVideoSink(self):
        """ returns the real video sink element or None """
        if not self.vsinkthread:
            return None
        return self.vsinkthread.videosink.realsink

    def record(self, uri, settings=None):
        """
        Render the SmartBin to the given uri.
        Returns : True if the encoding process could be started properly, False otherwise."""
        self.debug("setting to READY")
        if self.set_state(gst.STATE_READY) == gst.STATE_CHANGE_FAILURE:
            self.warning("Couldn't switch to READY !")
            return False

        if self.recording:
            self.error("This bin is already in in recording mode !")
            return

        # temporarily remove the audiosinkthread
        self.debug("disconnecting audio sink thread")
        self.tmpasink = self.asinkthread
        if not self.removeAudioSinkThread():
            return False

        # FIXME : remove this once BaseTransform is fixed
        # Also temporarily remove the videosinkthread
        self.tmpvsink = self.vsinkthread
        if not self.removeVideoSinkThread():
            return False

        self.debug("creating and adding encoding thread")
        self.encthread = self._makeEncThread(uri, settings)
        if not self.encthread:
            gst.warning("Couldn't create encoding thread")
            return False
        self.add(self.encthread)
        self.debug("encoding thread added")

        # set sync=false on the videosink
        #self.getRealVideoSink().set_property("sync", False)

        self.debug("linking vtee to ecnthread:vsink")
        try:
            self.vtee.get_pad("src").link(self.encthread.get_pad("vsink"))
        except:
            return False

        self.debug("linking atee to encthread:asink")
        try:
            self.atee.get_pad("src").link(self.encthread.get_pad("asink"))
        except:
            return False

        self.debug("going back to PLAYING")
        changeret = self.set_state(gst.STATE_PLAYING)
        self.debug("now in PLAYING, set_state() returned %r" % changeret)
        if changeret == gst.STATE_CHANGE_FAILURE:
            return False

        self.recording = True
        return True

    def stopRecording(self):
        """ stop the recording, removing the encoding thread """
        if self.recording == False:
            self.warning("This bin is not in recording mode !")
            return False

        self.set_state(gst.STATE_PAUSED)

        if self.encthread:
            apad = self.encthread.get_pad("vsink")
            apad.get_peer().unlink(apad)
            apad = self.encthread.get_pad("asink")
            apad.get_peer().unlink(apad)
            self.remove(self.encthread)
            self.encthread.set_state(gst.STATE_NULL)
            del self.encthread
            self.encthread = None
            self.setAudioSinkThread(self.tmpasink)
            self.setVideoSinkThread(self.tmpvsink)
            self.tmpasink = None
            self.tmpvsink = None

        self.getRealVideoSink().set_property("sync", True)

        self.recording = False
        return True

    def getSettings(self):
        """ Return the ExportSettings for the bin """
        return None

    def _debugProbe(self, unused_pad, data, categoryname):
        if isinstance(data, gst.Buffer):
            self.log("%s\tBUFFER timestamp:%s duration:%s size:%d" % (categoryname,
                                                                      gst.TIME_ARGS(data.timestamp),
                                                                      gst.TIME_ARGS(data.duration),
                                                                      data.size))
            if not data.flag_is_set(gst.BUFFER_FLAG_DELTA_UNIT):
                self.log("%s\tKEYFRAME" % categoryname)
        else:
            self.log("%s\tEVENT %s" % (categoryname, data))
        return True

    def _makeEncThread(self, uri, settings=None):
        """ Construct the encoding bin according to the given setting. """
        # TODO : verify if encoders take video/x-raw-yuv and audio/x-raw-int
        # TODO : use video/audio settings !
        # TODO : Check if we really do both audio and video !

        if not settings:
            settings = self.getSettings()
            if not settings:
                self.error("No settings available to create the Encoding Thread")
                return None

        thread = gst.Bin("encthread")

        ##
        ## Muxer/FileSink part
        ##

        mux = gst.element_factory_make(settings.muxer, "mux")
        # set properties on the muxer
        for prop, value in settings.containersettings.iteritems():
            mux.set_property(prop, value)
        fsink = gst.element_make_from_uri(gst.URI_SINK, uri, "fsink")
        thread.add(mux, fsink)
        mux.link(fsink)

        ##
        ## Audio part
        ##

        ainq = gst.element_factory_make("queue", "ainq")
        aident = gst.element_factory_make("identity", "aident")
        aident.props.single_segment = True
        aconv = gst.element_factory_make("audioconvert", "aconv")
        ares = gst.element_factory_make("audioresample", "ares")
        arate = gst.element_factory_make("audiorate", "arate")
        if settings.aencoder:
            aenc = gst.element_factory_make(settings.aencoder ,"aenc")
            # set properties on the encoder
            for prop, value in settings.acodecsettings.iteritems():
                aenc.set_property(prop, value)
        else:
            aenc = gst.element_factory_make("identity", "aenc")
        aoutq = gst.element_factory_make("queue", "aoutq")

        # add and link all required audio elements
        thread.add(ainq, aident, aconv, ares, arate, aenc, aoutq)
        gst.element_link_many(ainq, aident, aconv, ares, arate)

        # link to encoder using the settings caps
        self.log("About to link encoder with settings pads")
        try:
            arate.link(aenc, settings.getAudioCaps())
        except:
            self.error("The audio encoder doesn't accept the audio settings")
            return None
        gst.element_link_many(aenc, aoutq, mux)

        # ghost sinkpad
        aghost = gst.GhostPad("asink", ainq.get_pad("sink"))
        aghost.set_active(True)
        thread.add_pad(aghost)

##         aenc.get_pad("sink").add_data_probe(self._debugProbe, "aenc-sink")
##         aenc.get_pad("src").add_data_probe(self._debugProbe, "aenc-src")

        ##
        ## Video part
        ##

        vinq = gst.element_factory_make("queue", "vinq")
        vident = gst.element_factory_make("identity", "vident")
        vident.props.single_segment = True
        csp = gst.element_factory_make("ffmpegcolorspace", "csp")
        vrate = gst.element_factory_make("videorate", "vrate")
        vscale = SmartVideoScale()
        if settings.vencoder:
            venc = gst.element_factory_make(settings.vencoder, "venc")
            # set properties on the encoder
            for prop, value in settings.vcodecsettings.iteritems():
                venc.set_property(prop, value)
        else:
            venc = gst.element_factory_make("identity", "venc")
        voutq = gst.element_factory_make("queue", "voutq")

        # add and link all required video elements
        thread.add(vinq, vident, csp, vrate, vscale, venc, voutq)
        caps = settings.getVideoCaps()
        vscale.set_caps(caps)
        gst.element_link_many(vinq, vident, csp, vscale, vrate)

        # link to encoder using the settings caps
        self.log("About to link encoder with settings pads")
        try:
            vrate.link(venc, caps)
        except:
            self.error("The video encoder doesn't accept the video settings")
            return None
        gst.element_link_many(venc, voutq, mux)

        # ghost sinkpad
        vghost = gst.GhostPad("vsink", vinq.get_pad("sink"))
        vghost.set_active(True)
        thread.add_pad(vghost)

##         vrate.get_pad("sink").add_data_probe(self._debugProbe, "before-vrate")
##         vrate.get_pad("src").add_data_probe(self._debugProbe, "after-vrate")

        thread.filesink = fsink

        return thread

class SmartFileBin(SmartBin):
    """
    SmartBin for file sources from FileSourceFactory
    """

    def __init__(self, factory):
        gst.log("new SmartFileBin for factory:%s, audio:%s, video:%s" % (factory, factory.is_audio, factory.is_video))
        self.factory = factory
        if self.factory.video_info:
            struct = self.factory.video_info[0]
            height = struct["height"]
            width = struct["width"]
        else:
            height = 0
            width = 0
        self.source = self.factory.makeBin()
        SmartBin.__init__(self, "smartfilebin-" + factory.name,
                          displayname=factory.displayname,
                          has_video = factory.is_video,
                          has_audio = factory.is_audio,
                          width = width, height = height,
                          length = factory.getDuration())

    def _addSource(self):
        self.add(self.source)

    def _connectSource(self):
        self.source.connect("pad-added", self._binNewDecodedPadCb)
        self.source.connect("pad-removed", self._binRemovedDecodedPadCb)

    def _binNewDecodedPadCb(self, unused_bin, pad):
        # connect to good tee
        self.debug("SmartFileBin's source has a new pad: %s %s" % (pad , pad.get_caps().to_string()))
        if pad.get_caps().to_string().startswith("audio"):
            if not self.atee:
                self.warning("Got new audio pad, but we didn't discover one previously !")
            else:
                pad.link(self.atee.get_pad("sink"))
        elif pad.get_caps().to_string().startswith("video"):
            if not self.vtee:
                self.warning("Got new video pad, but we didn't discover one previously !")
            else:
                pad.link(self.vtee.get_pad("sink"))

    def _binRemovedDecodedPadCb(self, unused_bin, pad):
        if pad.get_caps().to_string().startswith("audio") and self.atee:
            pad.unlink(self.atee.get_pad("sink"))
        elif pad.get_caps().to_string().startswith("video") and self.vtee:
            pad.unlink(self.vtee.get_pad("sink"))

    def getSettings(self):
        return self.factory.getExportSettings()

    def do_destroy(self):
        self.info("destroyed")
        self.factory.binIsDestroyed(self.source)


class SmartTimelineBin(SmartBin):
    """
    SmartBin for GnlTimeline
    """

    def __init__(self, project):
        gst.log("new SmartTimelineBin for project %s" % project)
        self.project = project

        settings = project.getSettings()
        self.log("source is %r" % project.timeline.timeline)
        self.source = project.timeline.timeline
        self.project.connect("settings-changed", self._settingsChangedCb)
        project.timeline.videocomp.connect("start-duration-changed", self._startDurationChangedCb)

        # TODO : change has_audio/has_video to project settings value
        SmartBin.__init__(self, "project-" + project.name,
                          displayname = "Project: " + project.name,
                          has_video=True, has_audio=True,
                          width=settings.videowidth,
                          height=settings.videoheight,
                          length=project.timeline.videocomp.duration)

    def _addSource(self):
        self.add(self.source)

    def _connectSource(self):
        self.source.connect("pad-added", self._newPadCb)
        self.source.connect("pad-removed", self._removedPadCb)

    def _settingsChangedCb(self, project):
        settings = project.getSettings()
        self.width = settings.videowidth
        self.height = settings.videoheight

    def _newPadCb(self, unused_source, pad):
        if pad.get_name() == "asrc":
            pad.link(self.atee.get_pad("sink"))
        elif pad.get_name() == "vsrc":
            pad.link(self.vtee.get_pad("sink"))

    def _removedPadCb(self, unused_source, pad):
        self.debug("pad %r went away" % pad)
        if pad.get_name() == "asrc":
            pad.unlink(self.atee.get_pad("sink"))
        elif pad.get_name() == "vsrc":
            pad.unlink(self.vtee.get_pad("sink"))


    def _startDurationChangedCb(self, unused_videocomp, start, duration):
        self.info("smart timeline bin: start duration changed %d %d" %( start, duration ))
        self.length = duration

    def getSettings(self):
        return self.project.getSettings()

class SmartDefaultBin(SmartBin):
    """
    SmartBin with videotestsrc and silenc output
    Can be used as a default source
    """

    def __init__(self):
        gst.log("Creating new smartdefaultbin")
        self.videotestsrc = gst.element_factory_make("videotestsrc", "vtestsrc")
        self.silence = gst.element_factory_make("audiotestsrc", "silence")
        self.videotestsrc.set_property("pattern", 2)
        self.silence.set_property("wave", 4)
        SmartBin.__init__(self, "smartdefaultbin", has_video=True, has_audio=True,
                          width=720, height=576)

    def _addSource(self):
        self.add(self.videotestsrc, self.silence)

    def _connectSource(self):
        self.debug("connecting sources")
        #vcaps = gst.caps_from_string("video/x-raw-yuv,width=320,height=240,framerate=25.0")
        self.videotestsrc.get_pad("src").link(self.vtee.get_pad("sink"))
        self.silence.get_pad("src").link(self.atee.get_pad("sink"))
        self.debug("finished connecting sources")


class SmartCaptureBin(SmartBin):
    """
    SmartBin derivative for capturing streams.
    """

    def __init__(self):
        gst.log("Creating new smartcapturebin")
        self.videosrc = gst.element_factory_make("videotestsrc", "vsrc")
        self.audiosrc = gst.element_factory_make("audiotestsrc", "asrc")

        SmartBin.__init__(self, "smartcapturebin", has_video=True, has_audio=True,
                          width=720, height=576)

    def _addSource(self):
        self.add(self.videosrc,self.audiosrc)

    def _connectSource(self):
        self.debug("connecting sources")
        #vcaps = gst.caps_from_string("video/x-raw-yuv,width=320,height=240,framerate=25.0")
        self.videosrc.get_pad("src").link(self.vtee.get_pad("sink"))
	self.audiosrc.get_pad("src").link(self.atee.get_pad("sink"))

        self.debug("finished connecting sources")

