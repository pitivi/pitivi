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

class SmartBin(gst.Bin):
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
        self.add_source()
        self.connect_source()
        self.set_state(gst.STATE_PAUSED)
        self.asinkthread = None
        self.vsinkthread = None

    def add_source(self):
        """ add the source to self, implement in subclasses """
        pass

    def connect_source(self):
        """ connect the source to the tee, implement in subclasses """
        pass

    def set_audio_sink_thread(self, asinkthread):
        """ set the audio sink thread """
        print "setting asinkthread in", self.name
        if self.get_state() > gst.STATE_PAUSED:
            print self.name, "is in PAUSED or higher"
            return False
        if self.asinkthread:
            print self.name, "already has an asinkthread??"
            return False
        if self.has_audio:
            self.asinkthread = asinkthread
            self.add(self.asinkthread)
            self.atee.get_pad("src%d").link(self.asinkthread.get_pad("sink"))
        print "atee has now #pads", self.atee.get_property("num_pads")
        return True

    def set_video_sink_thread(self, vsinkthread):
        """ set the video sink thread """
        print "setting vsinkthread in ", self.name
        if self.get_state() > gst.STATE_PAUSED:
            return False
        if self.vsinkthread:
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
            print "vtee has now #pads:", self.vtee.get_property("num_pads")
        return True

    def remove_audio_sink_thread(self):
        """ remove the audio sink thread """
        print "removing asinkthread in ", self.name
        if self.get_state() > gst.STATE_PAUSED:
            return False
        if not self.asinkthread:
            return False
        self.asinkthread.get_pad("sink").get_peer().unlink(self.asinkthread.get_pad("sink"))
        self.remove(self.asinkthread)
        self.asinkthread = None
        return True

    def remove_video_sink_thread(self):
        """ remove the videos sink thread """
        print "removing vsinkthread in ", self.name
        if self.get_state() > gst.STATE_PAUSED:
            return False
        if not self.vsinkthread:
            return False
        self.vsinkthread.get_pad("sink").get_peer().unlink(self.vsinkthread.get_pad("sink"))
        self.remove(self.vsinkthread)
        self.vsinkthread = None
        return True

gobject.type_register(SmartBin)

class SmartFileBin(SmartBin):
    """
    SmartBin for file sources from FileSourceFactory
    """

    def __init__(self, factory):
        print "new SmartFileBin for factory:%s, audio:%s, video:%s" % (factory, factory.is_audio, factory.is_video)
        self.factory = factory
        self.has_video = factory.is_video
        self.has_audio = factory.is_audio
        self.length = factory.length
        if self.factory.video_info:
            struct = self.factory.video_info[0]
            self.height = struct["height"]
            self.width = struct["width"]
        self.source = self.factory.make_bin()
        SmartBin.__init__(self, "smartfilebin-" + factory.name,
                          displayname=factory.displayname)

    def add_source(self):
        self.add(self.source)

    def connect_source(self):
        print "connect_source for ", self.source.get_pad_list()
        print "delayed to 'new-decoded-pad' signal"
        self.source.connect("new-pad", self._bin_new_decoded_pad)
        self.source.connect("pad-removed", self._bin_removed_decoded_pad)
##         if self.has_video:
##             if not self.source.get_pad("vsrc").link(self.vtee.get_pad("sink")):
##                 print "problem connecting source:vsrc to vtee:sink"
##         if self.has_audio:
##             if not self.source.get_pad("asrc").link(self.atee.get_pad("sink")):
##                 print "problem connection source:asrc to atee:sink"

    def _bin_new_decoded_pad(self, bin, pad):
        # connect to good tee
        print "SmartFileBin's source has a new pad:", pad , pad.get_caps().to_string()
        if "audio" in pad.get_caps().to_string():
            pad.link(self.atee.get_pad("sink"))
        elif "video" in pad.get_caps().to_string():
            pad.link(self.vtee.get_pad("sink"))

    def _bin_removed_decoded_pad(self, bin, pad):
        if "audio" in pad.get_caps().to_string():
            pad.unlink(self.atee)
        elif "video" in pad.get_caps().to_string():
            pad.unlink(self.vtee)

    def do_destroy(self):
        print "do_destroy"
        self.factory.bin_is_destroyed(self.source)

gobject.type_register(SmartFileBin)

class SmartTimelineBin(SmartBin):
    """
    SmartBin for GnlTimeline
    """

    def __init__(self, project):
        print "new SmartTimelineBin for project", project
        self.project = project
        
        # TODO : change this to use the project settings
        self.has_video = True
        self.has_audio = True

        self.width = project.settings.videowidth
        self.height = project.settings.videoheight
        self.source = project.timeline.timeline
        self.project.settings.connect("settings-changed", self._settings_changed_cb)
        project.timeline.videocomp.connect("start-stop-changed", self._start_stop_changed)
        self.length = project.timeline.videocomp.stop - project.timeline.videocomp.start
        self.encthread = None
        self.tmpasink = None
        SmartBin.__init__(self, "project-" + project.name,
                          displayname = "Project: " + project.name)

    def add_source(self):
        self.add(self.source)

    def _settings_changed_cb(self, settings):
        self.width = settings.videowidth
        self.height = settings.videoheight

    def connect_source(self):
        srcpad = self.source.get_pad("src_" + self.project.timeline.audiocomp.gnlobject.get_name())
        srcpad.link(self.atee.get_pad("sink"))
        srcpad = self.source.get_pad("src_" + self.project.timeline.videocomp.gnlobject.get_name())
        srcpad.link(self.vtee.get_pad("sink"))

    def record(self, uri, settings=None):
        """ render the timeline to the given uri """
        self.encthread = self._make_encthread(settings)
        if self.get_state() == gst.STATE_PLAYING:
            self.set_state(gst.STATE_PAUSED)
        self.encthread.filesink.set_property("location", uri)
        self.add(self.encthread)

        # temporarily remove the audiosinkthread
        self.tmpasink = self.asinkthread
        self.remove_audio_sink_thread()
        
        self.vtee.get_pad("src%d").link(self.encthread.get_pad("vsink"))
        self.atee.get_pad("src%d").link(self.encthread.get_pad("asink"))

        self.source.seek(gst.SEEK_METHOD_SET | gst.FORMAT_TIME | gst.SEEK_FLAG_FLUSH,
                         long(0))
        self.set_state(gst.STATE_PLAYING)

    def stop_recording(self):
        """ stop the recording, removing the encoding thread """
        self.set_state(gst.STATE_PAUSED)
        # safely seek back to 0 and flush everything
        self.source.seek(gst.SEEK_METHOD_SET | gst.FORMAT_TIME | gst.SEEK_FLAG_FLUSH,
                    long(0))
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
            self.set_audio_sink_thread(self.tmpasink)
            self.tmpasink = None

    def _make_encthread(self, settings=None):
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
            print "setting property", prop, "to value", value
            venc.set_property(prop, value)
        mux = gst.element_factory_make(settings.muxer, "mux")
        for prop, value in settings.containersettings.iteritems():
            mux.set_property(prop, value)
        fsink = gst.element_factory_make("gnomevfssink", "fsink")

        thread = gst.Thread("encthread")
        thread.add_many(mux, fsink, aoutq, voutq)

        # Audio encoding thread
        aencthread = gst.Thread("aencthread")
        aencthread.add_many(ainq, aenc)
        thread.add(aencthread)
        
        filtcaps = gst.caps_from_string("audio/x-raw-int")
        if not len(filtcaps.intersect(aenc.get_pad("sink").get_caps())):
            aconv = gst.element_factory_make("audioconvert", "aconv")
            aencthread.add(aconv)
            ainq.link(aconv)
            aconv.link(aenc)
        else:
            ainq.link(aenc)
        aenc.link(aoutq)

        # Video encoding thread
        vencthread = gst.Thread("vencthread")
        vencthread.add_many(vinq, venc)
        thread.add(vencthread)
        
        filtcaps = gst.caps_from_string("video/x-raw-yuv")
        if not len(filtcaps.intersect(venc.get_pad("sink").get_caps())):
            csp = gst.element_factory_make("ffmpegcolorspace", "csp")
            vencthread.add(csp)
            ainq.link(csp)
            csp.link(venc)
        else:
            vinq.link(venc)
        venc.link(voutq)

        thread.add_ghost_pad(vinq.get_pad("sink"), "vsink")
        thread.add_ghost_pad(ainq.get_pad("sink"), "asink")

        thread.filesink = fsink

        aoutq.link(mux)
        voutq.link(mux)
        mux.link(fsink)

        return thread

    def _start_stop_changed(self, videocomp, start, stop):
        print "smart timeline bin: start stop changed", start, stop
        self.length = stop - start

gobject.type_register(SmartTimelineBin)

class SmartDefaultBin(SmartBin):
    """
    SmartBin with videotestsrc and silenc output
    Can be used as a default source
    """

    def __init__(self):
        print "Creating new smartdefaultbin"
        self.videotestsrc = gst.element_factory_make("videotestsrc", "vtestsrc")
        self.silence = gst.element_factory_make("silence", "silence")
        self.has_audio = True
        self.has_video = True
        self.width = 720
        self.height = 576
        SmartBin.__init__(self, "smartdefaultbin")

    def add_source(self):
        self.add_many(self.videotestsrc, self.silence)

    def connect_source(self):
        print "connecting sources"
        vcaps = gst.caps_from_string("video/x-raw-yuv,width=320,height=240,framerate=25.0")
        self.videotestsrc.get_pad("src").link_filtered(self.vtee.get_pad("sink"), vcaps)
        self.silence.get_pad("src").link(self.atee.get_pad("sink"))
        print "finished connecting sources"

gobject.type_register(SmartDefaultBin)

## class SmartTempUriBin(SmartBin):
##     """
##     SmartBin for temporary uris
##     """

##     def __init__(self, uri):
##         self.uri = uri
##         self.has_audio = True
##         self.has_video = True
##         SmartBin.__init__(self, "temp-" + uri)

##     def add_source(self):
##         filesrc = gst.element_factory_make("gnomevfssrc", "src")
##         filesrc.set_property("location", self.uri)
##         self.dbin = gst.element_factory_make("decodebin", "dbin")
##         self.dbin.connect("new-decoded-pad", self._bin_new_decoded_pad)
##         self.aident = gst.element_factory_make("queue", "aident")
##         self.vident = gst.element_factory_make("queue", "vident")
##         self.add_many(filesrc, self.dbin, self.aident, self.vident)

##     def connect_source(self):
##         print "connecting ident to tee"
##         print self.aident.get_pad("src").link(self.atee.get_pad("sink"))
##         print self.vident.get_pad("src").link(self.vtee.get_pad("sink"))

##     def _bin_new_decoded_pad(self, dbin, pad, is_last):
##         if "audio" in pad.get_caps().to_string():
##             pad.link(self.aident.get_caps("sink"))
##         elif "video" in pad.get_caps().to_string():
##             pad.link(self.vident.get_caps("sink"))

## gobject.type_register(SmartTempUriBin)
