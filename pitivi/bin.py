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

import gobject
import gst

class SmartBin(gst.Pipeline):
    """
    Self-contained Bin with playing/encoding ready places
    It also has length information
    """
    length = 0
    has_video = False
    has_audio = False
    width = 0
    height = 0

    def __init__(self, name, displayname=""):
        gst.log('name : %s, displayname : %s' % (name, displayname))
        gobject.GObject.__init__(self)
        self.name = name
        self.displayname = displayname
        self.set_name(name)
        if self.has_video:
            self.vtee = gst.element_factory_make("tee", "vtee")
            self.add(self.vtee)
        if self.has_audio:
            self.atee = gst.element_factory_make("tee", "atee")
            self.add(self.atee)
        self.addSource()
        self.connectSource()
        self.asinkthread = None
        self.vsinkthread = None

    def addSource(self):
        """ add the source to self, implement in subclasses """
        pass

    def connectSource(self):
        """ connect the source to the tee, implement in subclasses """
        pass

    def setAudioSinkThread(self, asinkthread):
        """ set the audio sink thread """
        self.debug("asinkthread : %s" % asinkthread)
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
            self.atee.get_pad("src%d").link(self.asinkthread.get_pad("sink"))
        return True

    def setVideoSinkThread(self, vsinkthread):
        """ set the video sink thread """
        self.debug("vsinkthread : %s" % vsinkthread)
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
            if self.width and self.height:
                #filtcaps = gst.caps_from_string("video/x-raw-yuv,width=%d,height=%d;video/x-raw-rgb,width=%d,height=%d" % (self.width, self.height, self.width, self.height))
                #self.vtee.get_pad("src%d").link_filtered(self.vsinkthread.get_pad("sink"), filtcaps)
                self.vtee.get_pad("src%d").link(self.vsinkthread.get_pad("sink"))
            else:
                self.vtee.get_pad("src%d").link(self.vsinkthread.get_pad("sink"))
        return True

    def removeAudioSinkThread(self):
        """ remove the audio sink thread """
        self.debug("asinkthread : %s" % self.asinkthread)
        result, state, pending = self.get_state(0)
        if state in [gst.STATE_PAUSED, gst.STATE_PLAYING]:
            self.warning("is in PAUSED or higher : %s" % state)
            return False
        if not self.asinkthread:
            self.warning("doesn't have an asinkthread??")
            return False
        self.asinkthread.get_pad("sink").get_peer().unlink(self.asinkthread.get_pad("sink"))
        self.remove(self.asinkthread)
        self.asinkthread = None
        return True

    def removeVideoSinkThread(self):
        """ remove the videos sink thread """
        self.debug("vsinkthread : %s" % self.vsinkthread)
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
        return True


class SmartFileBin(SmartBin):
    """
    SmartBin for file sources from FileSourceFactory
    """

    def __init__(self, factory):
        gst.log("new SmartFileBin for factory:%s, audio:%s, video:%s" % (factory, factory.is_audio, factory.is_video))
        self.factory = factory
        self.has_video = factory.is_video
        self.has_audio = factory.is_audio
        self.length = factory.length
        if self.factory.video_info:
            struct = self.factory.video_info[0]
            self.height = struct["height"]
            self.width = struct["width"]
        self.source = self.factory.makeBin()
        SmartBin.__init__(self, "smartfilebin-" + factory.name,
                          displayname=factory.displayname)

    def addSource(self):
        self.add(self.source)

    def connectSource(self):
        self.source.connect("pad-added", self._binNewDecodedPadCb)
        self.source.connect("pad-removed", self._binRemovedDecodedPadCb)

    def _binNewDecodedPadCb(self, bin, pad):
        # connect to good tee
        self.debug("SmartFileBin's source has a new pad: %s %s" % (pad , pad.get_caps().to_string()))
        if pad.get_caps().to_string().startswith("audio"):
            pad.link(self.atee.get_pad("sink"))
        elif pad.get_caps().to_string().startswith("video"):
            pad.link(self.vtee.get_pad("sink"))

    def _binRemovedDecodedPadCb(self, bin, pad):
        if pad.get_caps().to_string().startswith("audio"):
            pad.unlink(self.atee.get_pad("sink"))
        elif pad.get_caps().to_string().startswith("video"):
            pad.unlink(self.vtee.get_pad("sink"))

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
        
        # TODO : change this to use the project settings
        self.has_video = True
        self.has_audio = True

        self.width = project.settings.videowidth
        self.height = project.settings.videoheight
        self.log("source is %s" % project.timeline.timeline)
        self.source = project.timeline.timeline
        self.project.settings.connect("settings-changed", self._settingsChangedCb)
        project.timeline.videocomp.connect("start-duration-changed", self._startDurationChangedCb)
        self.length = project.timeline.videocomp.duration
        self.encthread = None
        self.tmpasink = None
        SmartBin.__init__(self, "project-" + project.name,
                          displayname = "Project: " + project.name)

    def addSource(self):
        self.add(self.source)

    def _settingsChangedCb(self, settings):
        self.width = settings.videowidth
        self.height = settings.videoheight

    def _newPadCb(self, source, pad):
        if pad.get_name() == "asrc":
            pad.link(self.atee.get_pad("sink"))
        elif pad.get_name() == "vsrc":
            pad.link(self.vtee.get_pad("sink"))

    def connectSource(self):
        self.source.connect("pad-added", self._newPadCb)

    def record(self, uri, settings=None):
        """ render the timeline to the given uri """
        self.encthread = self._makeEncThread(settings)
        self.add(self.encthread)
        self.encthread.filesink.set_uri(uri)

        # temporarily remove the audiosinkthread
        self.tmpasink = self.asinkthread
        self.removeAudioSinkThread()

        # set sync=false on the videosink
        self.getRealVideoSink().set_property("sync", False)
        
        self.debug("linking vtee to ecnthread:vsink")
        self.vtee.get_pad("src%d").link(self.encthread.get_pad("vsink"))
        self.debug("linking atee to encthread:asink")
        self.atee.get_pad("src%d").link(self.encthread.get_pad("asink"))

        self.set_state(gst.STATE_PAUSED)
        self.debug("About to seek to beginning for encoding")
        if not self.seek(1.0, gst.FORMAT_TIME,
                         gst.SEEK_FLAG_FLUSH,
                         gst.SEEK_TYPE_CUR, 0,
                         gst.SEEK_TYPE_NONE, -1):
            self.warning("Couldn't seek to beginning before encoding")
        self.set_state(gst.STATE_PLAYING)

    def stopRecording(self):
        """ stop the recording, removing the encoding thread """
        self.set_state(gst.STATE_PAUSED)
        
        if self.encthread:
            apad = self.encthread.get_pad("vsink")
            apad.unlink(apad.get_peer())
            apad = self.encthread.get_pad("asink")
            apad.unlink(apad.get_peer())
            #self.vtee.unlink(self.encthread)
            #self.atee.unlink(self.encthread)
            self.remove(self.encthread)
            del self.encthread
            self.encthread= None
            self.setAudioSinkThread(self.tmpasink)
            self.tmpasink = None

        self.getRealVideoSink().set_property("sync", True)

    def getRealVideoSink(self):
        """ returns the real video sink element or None """
        if not self.vsinkthread:
            return None
        return self.vsinkthread.videosink.realsink

    def _makeEncThread(self, settings=None):
        # TODO : verify if encoders take video/x-raw-yuv and audio/x-raw-int
        if not settings:
            settings = self.project.settings
        ainq = gst.element_factory_make("queue", "ainq")
        aoutq = gst.element_factory_make("queue", "aoutq")
        vinq = gst.element_factory_make("queue", "vinq")
        voutq = gst.element_factory_make("queue", "voutq")
        aenc = gst.element_factory_make(settings.aencoder ,"aenc")
        for prop, value in settings.acodecsettings.iteritems():
            aenc.set_property(prop, value)
        venc = gst.element_factory_make(settings.vencoder, "venc")
        for prop, value in settings.vcodecsettings.iteritems():
            venc.set_property(prop, value)
        mux = gst.element_factory_make(settings.muxer, "mux")
        for prop, value in settings.containersettings.iteritems():
            mux.set_property(prop, value)
        try:
            fsink = gst.element_factory_make("gnomevfssink", "fsink")
        except:
            fsink = gst.element_factory_make("filesink", "fsink")


        thread = gst.Bin("encthread")
        thread.add(mux, fsink, aoutq, voutq)

        thread.add(ainq, aenc)
       
        aconv = gst.element_factory_make("audioconvert", "aconv")
        thread.add(aconv)
        ainq.link(aconv)
        aconv.link(aenc)
        aenc.link(aoutq)

        thread.add(vinq, venc)
        csp = gst.element_factory_make("ffmpegcolorspace", "csp")
        thread.add(csp)
        vinq.link(csp)
        csp.link(venc)
        venc.link(voutq)

        thread.add_pad(gst.GhostPad("vsink", vinq.get_pad("sink")))
        thread.add_pad(gst.GhostPad("asink", ainq.get_pad("sink")))

        thread.filesink = fsink

        aoutq.link(mux)
        voutq.link(mux)
        mux.link(fsink)

        return thread

    def _startDurationChangedCb(self, videocomp, start, duration):
        self.info("smart timeline bin: start duration changed %d %d" %( start, duration ))
        self.length = duration


class SmartDefaultBin(SmartBin):
    """
    SmartBin with videotestsrc and silenc output
    Can be used as a default source
    """

    def __init__(self):
        gst.log("Creating new smartdefaultbin")
        self.videotestsrc = gst.element_factory_make("videotestsrc", "vtestsrc")
        self.silence = gst.element_factory_make("audiotestsrc", "silence")
        self.silence.set_property("wave", 4)
        self.has_audio = True
        self.has_video = True
        self.width = 720
        self.height = 576
        SmartBin.__init__(self, "smartdefaultbin")

    def addSource(self):
        self.add(self.videotestsrc, self.silence)

    def connectSource(self):
        self.debug("connecting sources")
        #vcaps = gst.caps_from_string("video/x-raw-yuv,width=320,height=240,framerate=25.0")
        self.videotestsrc.get_pad("src").link(self.vtee.get_pad("sink"))
        self.silence.get_pad("src").link(self.atee.get_pad("sink"))
        self.debug("finished connecting sources")

