#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       objectfactory.py
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

import os.path
from urllib import unquote
import string
import gobject
import gst

class ObjectFactory(gobject.GObject):
    """
    base class for object factories which provide elements to use
    in the timeline
    """
    __gproperties__ = {
        "is-audio" : ( gobject.TYPE_BOOLEAN,
                       "Contains audio stream",
                       "Does the element contain audio",
                       False, gobject.PARAM_READWRITE),
        
        "is-video" : ( gobject.TYPE_BOOLEAN,
                       "Contains video stream",
                       "Does the element contain video",
                       False, gobject.PARAM_READWRITE),
        "audio-info" : ( gobject.TYPE_PYOBJECT,
                         "Audio Information",
                         "GstCaps of the audio stream",
                         gobject.PARAM_READWRITE ),
        "video-info" : ( gobject.TYPE_PYOBJECT,
                         "Video Information",
                         "GstCaps of the video stream",
                         gobject.PARAM_READWRITE )
        }

    def __init__(self):
        gobject.GObject.__init__(self)
        self.name = ""
        self.displayname = ""
        self.is_audio = False
        self.is_video = False
        self.is_effect = False
        self.instances = []
        self.audio_info = None
        self.video_info = None

    def do_set_property(self, property, value):
        gst.info(property.name)
        if property.name == "is-audio":
            self.is_audio = value
        elif property.name == "is-video":
            self.is_video = value
        elif property.name == "video-info":
            self.video_info = value
        elif property.name == "audio-info":
            self.audio_info = value
        else:
            raise AttributeError, 'unknown property %s' % property.name

    def set_audio_info(self, caps):
        """ sets the audio caps of the element """
        self.set_property("audio-info", caps)

    def set_video_info(self, caps):
        """ set the video caps of the element """
        self.set_property("video-info", caps)

    def set_audio(self, is_audio):
        """ sets whether the element has audio stream """
        self.set_property("is-audio", is_audio)

    def set_video(self, is_video):
        """ sets whether the element has video stream """
        self.set_property("is-video", is_video)

    def make_audio_bin(self):
        """ returns a audio only bin """
        pass

    def make_video_bin(self):
        """ returns a video only bin """
        pass

gobject.type_register(ObjectFactory)

class FileSourceFactory(ObjectFactory):
    """
    Provides File sources useable in a timeline
    """

    __gproperties__ = {
        "length" : ( gobject.TYPE_UINT64,
                     "Length",
                     "Length of element",
                     0,
                     -1,
                     0,
                     gobject.PARAM_READWRITE ),
        "thumbnail" :  ( gobject.TYPE_STRING,
                         "Thumbnail filename",
                         "Filename for the element's thumbnail",
                         "",
                         gobject.PARAM_READWRITE )
        }

    def __init__(self, filename, project):
        gst.info("filename:%s , project:%s" % (filename, project))
        ObjectFactory.__init__(self)
        self.project = project
        self.name = filename
        self.displayname = os.path.basename(unquote(self.name))
        self.lastbinid = 0
        self.length = 0
        self.thumbnail = ""
        self.thumbnails = []

    def do_set_property(self, property, value):
        if property.name == "length":
            self.length = value
        elif property.name == "thumbnail":
            self.thumbnail = value
        else:
            ObjectFactory.do_set_property(self, property, value)

    def make_bin(self):
        """ returns a source bin with all pads """
        bin = gst.Bin("%s-%d" % (self.name, self.lastbinid))
        self.lastbinid = self.lastbinid + 1
        src = gst.element_factory_make("gnomevfssrc")
        src.set_property("location", self.name)
        dbin = gst.element_factory_make("decodebin")
        bin.add(src, dbin)
        src.link(dbin)

        dbin.connect("new-decoded-pad", self._bin_new_decoded_pad, bin )
        dbin.connect("removed-decoded-pad", self._bin_removed_decoded_pad, bin)

        self.instances.append(bin)
        return bin

    def _bin_new_decoded_pad(self, dbin, pad, is_last, bin):
        gst.info(pad.get_caps().to_string())
        # add it as ghost_pad to the bin
        if "audio" in pad.get_caps().to_string():
            mypad = bin.get_pad("asrc")
            if mypad:
                gst.warning("Removing previous asrc. WHY didn't decodebin remove it??")
                bin.remove_pad(mypad)
            bin.add_pad(gst.GhostPad("asrc", pad))
        elif "video" in pad.get_caps().to_string():
            mypad = bin.get_pad("vsrc")
            if mypad:
                gst.warning("Removing previous vsrc. WHY didn't decodebin remove it??")
                bin.remove_pad(mypad)
            bin.add_pad(gst.GhostPad("vsrc", pad))
        else:
            return

    def _bin_removed_decoded_pad(self, dbin, pad, bin):
        gst.info("pad %s was removed" % pad)
        if "audio" in pad.get_caps().to_string():
            mypad = bin.get_pad("asrc")
        elif "video" in pad.get_caps().to_string():
            mypad = bin.get_pad("vsrc")
        else:
            return
        bin.remove_pad(mypad)
        
    def bin_is_destroyed(self, bin):
        if bin in self.instances:
            self.instances.remove(bin)

    def _single_bin_new_decoded_pad(self, dbin, pad, is_last, data):
        # add safe de-activation of the other pad
        bin, mtype, identity = data
        goodpad = None
        badpads = []
        if mtype in pad.get_caps().to_string():
            pad.link(identity.get_pad("sink"))
        # only deactivate the other pad if we've already connected the good pad!
        if identity.get_pad("sink").get_peer():
            for pad in [x for x in dbin.get_pad_list() if x.get_direction == gst.PAD_SRC]:
                if not mtype in pad.get_caps().to_string():
                    badpads.append(pad)
                else:
                    goodpad = pad
        if goodpad:
            for pad in badpads:
                pad.activate_recursive(False)
                    
            
    def _single_bin_removed_decoded_pad(self, dbin, pad, data):
        bin, mtype, identity = data
        if mtype in pad.get_caps().to_string():
            pad.unlink(identity.get_pad("sink"))

    def _make_single_bin(self, type):
        # Use identity and ghost pad !
        # TODO : add the adapters
        bin = gst.Bin(self.name + str(self.lastbinid))
        self.lastbinid = self.lastbinid + 1
        src = gst.element_factory_make("gnomevfssrc")
        src.set_property("location", self.name)
        dbin = gst.element_factory_make("decodebin")
        #ident = gst.element_factory_make("identity")
        if type == "video":
            ident = self.make_video_adapter_bin()
        else:
            ident = self.make_audio_adapter_bin()
        bin.add(src, dbin, ident)
        src.link(dbin)
        bin.add_pad(gst.GhostPad("src", ident.get_pad("src")))
        
        dbin.connect("new-decoded-pad", self._single_bin_new_decoded_pad, (bin, type, ident))
        dbin.connect("removed-decoded-pad", self._single_bin_removed_decoded_pad, (bin, type, ident))

        self.instances.append(bin)
        return bin

    def make_audio_bin(self):
        return self._make_single_bin("audio")

    def make_video_bin(self):
        return self._make_single_bin("video")

    def set_length(self, length):
        """ sets the length of the element """
        self.set_property("length", length)

    def set_thumbnail(self, thumbnail):
        """ Sets the thumbnail filename of the element """
        self.set_property("thumbnail", thumbnail)

    def get_pretty_info(self):
        """ Returns a prettyfied information string """
        # Audio : [Mono|Stereo|<nbchanns>] @ <rate> Hz
        # Video : <width> x <Height> @ <rate> fps
        if self.is_effect:
            if self.is_audio:
                return "Video Effect"
            elif self.is_video:
                return "Audio Effect"
            return "Effect"
        if not self.is_video and not self.is_audio:
            "Unknown"
        stl = []
        if self.is_video:
            if self.video_info:
                stl.append("Video: %d x %d @ %3f fps" % (self.video_info[0]["width"],
                                                        self.video_info[0]["height"],
                                                        self.video_info[0]["framerate"]))
            else:
                stl.append("Video")
        if self.is_audio:
            if self.audio_info:
                nbchanns = self.audio_info[0]["channels"]
                rate = self.audio_info[0]["rate"]
                stl.append("Audio: %d channels @ %d Hz" % (nbchanns, rate))
            else:
                stl.append("Audio")
        return string.join(stl, "\n")

    def _update_video_adapter_bin(self, psettings, data):
        bin, vrate, vscale, vbox, ident = data
        srcwidth = self.video_info[0]["width"]
        srcheight = self.video_info[0]["height"]
        srcrate = self.video_info[0]["framerate"]
        src_ratio = float(srcwidth) / float(srcheight)
        dst_ratio = float(self.project.settings.videowidth) / float(self.project.settings.videoheight)

        result, pstate, pending = bin.get_state(0)
        if pstate > gst.STATE_READY:
            bin.set_state(gst.STATE_READY)

        vrate.unlink(vbox)
        filtcaps = gst.caps_from_string("video/x-raw-yuv,framerate=%f"
                                        % self.project.settings.videorate)
        vrate.link(vbox, filtcaps)

        if src_ratio < dst_ratio:
            # keep height, box on sides
            padding = int((srcheight * dst_ratio) / 2)
            vbox.set_property("top", 0)
            vbox.set_property("bottom", 0)
            vbox.set_property("left", -padding)
            vbox.set_property("right", -padding)
        elif src_ratio > dst_ratio:
            # keep width, box above/under
            padding = int(srcwidth / (dst_ratio * 2))
            vbox.set_property("top", -padding)
            vbox.set_property("bottom", -padding)
            vbox.set_property("left", 0)
            vbox.set_property("right", 0)
        else:
            # keep as such
            for side in ["top", "bottom", "left", "right"]:
                vbox.set_property(side, 0)


        filtcaps = gst.caps_from_string("video/x-raw-yuv,width=%d,height=%d,framerate=%f,pixel-aspect-ratio=(fraction)1/1"
                                        % (psettings.videowidth,
                                           psettings.videoheight,
                                           psettings.videorate))
        vscale.unlink(ident)
        vscale.link(ident, filtcaps)
        if pstate > gst.STATE_READY:
            bin.set_state(pstate)

    def _update_audio_adapter_bin(self, psettings, data):
        bin, ascale, ident = data
        result, pstate, pending = bin.get_state(0)
        if pstate > gst.STATE_READY:
            bin.set_state(gst.STATE_READY)
        filtcaps = gst.caps_from_string("audio/x-raw-int,channels=%d,rate=%d,depth=%d"
                                        % (psettings.audiochannels,
                                           psettings.audiorate,
                                           psettings.audiodepth))
        ascale.unlink(ident)
        ascale.link(ident, filtcaps)
        if pstate > gst.STATE_READY:
            bin.set_state(pstate)
    
    def make_video_adapter_bin(self):
        srcwidth = self.video_info[0]["width"]
        srcheight = self.video_info[0]["height"]
        srcrate = self.video_info[0]["framerate"]
        if self.video_info[0].has_key("pixel-aspect-ratio"):
            srcpar = self.video_info[0]["pixel-aspect-ratio"]
        else:
            srcpar = None
        
        bin = gst.Bin()
        vrate = gst.element_factory_make("videorate")
        vbox = gst.element_factory_make("videobox")
        ident = gst.element_factory_make("identity")

##         vscale = gst.element_factory_make("ffvideoscale")
##         if not vscale:
        vscale = gst.element_factory_make("videoscale")

        bin.add(vrate, vbox, vscale, ident)
        filtcaps = gst.caps_from_string("video/x-raw-yuv,framerate=%f"
                                        % self.project.settings.videorate)
        vrate.link(vbox, filtcaps)

        if srcpar:
            src_ratio = (float(srcwidth) * srcpar.num ) / (float(srcheight) * srcpar.denom)
        else:
            src_ratio = float(srcwidth) / float(srcheight)
        dst_ratio = float(self.project.settings.videowidth) / float(self.project.settings.videoheight)

        gst.info("src_ratio: %f dst_rate:%f" %( src_ratio, dst_ratio))
        gst.info("src wxh: %d x %d" % ( srcwidth, srcheight))
        gst.info("dst wxh: %d x %d" % ( self.project.settings.videowidth, self.project.settings.videoheight))

        if src_ratio < dst_ratio:
            # keep height, box on sides
            padding = int((srcheight * dst_ratio - srcwidth) / 2)
            gst.info("side padding: %d" % -padding)
            gst.info("results in %d x %d" % ( srcwidth + 2 * padding, srcheight))
            vbox.set_property("top", 0)
            vbox.set_property("bottom", 0)
            vbox.set_property("left", -padding)
            vbox.set_property("right", -padding)
        elif src_ratio > dst_ratio:
            # keep width, box above/under
            padding = int(((srcwidth / dst_ratio) - srcheight) / 2)
            print "top/bottom padding:", -padding
            print "results in", srcwidth, srcheight + 2 * padding
            vbox.set_property("top", -padding)
            vbox.set_property("bottom", -padding)
            vbox.set_property("left", 0)
            vbox.set_property("right", 0)
        else:
            # keep as such
            for side in ["top", "bottom", "left", "right"]:
                vbox.set_property(side, 0)

        filtcaps = gst.caps_from_string("video/x-raw-yuv,format=(fourcc)I420")
        vbox.link(vscale, filtcaps)
        filtcaps = gst.caps_from_string("video/x-raw-yuv,width=%d,height=%d,framerate=%f,pixel-aspect-ratio=(fraction)1/1"
                                        % (self.project.settings.videowidth,
                                           self.project.settings.videoheight,
                                           self.project.settings.videorate))
        vscale.link(ident, filtcaps)
        bin.add_pad(gst.GhostPad("sink", vrate.get_pad("sink")))
        bin.add_pad(gst.GhostPad("src", ident.get_pad("src")))
        self.project.settings.connect("settings-changed", self._update_video_adapter_bin,
                                 (bin, vrate, vscale, vbox, ident))
        return bin

    def make_audio_adapter_bin(self):
        bin = gst.Bin()
        aconv = gst.element_factory_make("audioconvert")
        ascale = gst.element_factory_make("audioscale")
        ident = gst.element_factory_make("identity")
        bin.add(aconv, ascale, ident)
        aconv.link(ascale)
        filtcaps = gst.caps_from_string("audio/x-raw-int,channels=%d,rate=%d,depth=%d"
                                        % (self.project.settings.audiochannels,
                                           self.project.settings.audiorate,
                                           self.project.settings.audiodepth))
        ascale.link(ident, filtcaps)
        bin.add_pad(gst.GhostPad("sink", aconv.get_pad("sink")))
        bin.add_pad(gst.GhostPad("src", ident.get_pad("src")))
        self.project.settings.connect("settings-changed", self._update_audio_adapter_bin,
                                 (bin, ascale, ident))
        return bin

gobject.type_register(FileSourceFactory)

class OperationFactory(ObjectFactory):
    """
    Provides operations useable in a timeline
    """

    def __init__(self):
        ObjectFactory.__init__(self)
        self.nbinput = 1
        self.nboutput = 1

gobject.type_register(OperationFactory)

class SimpleOperationFactory(OperationFactory):
    """
    Provides simple (audio OR video) operations useable in a timeline
    """

    def __init__(self, elementfactory):
        """ elementfactory is the GstElementFactory """
        OperationFactory.__init__(self)
        self.name = elementfactory.get_name()
        self.displayname = elementfactory.get_longname()
        # check what type the output pad is (AUDIO/VIDEO)
        for padt in elementfactory.get_pad_templates():
            if padt.direction == gst.PAD_SRC:
                if "audio" in padt.get_caps().to_string():
                    self.is_audio = True
                elif "video" in padt.get_caps().to_string():
                    self.is_video = True

    def _make_bin(self, mtype):
        # make a bin with adapters
        # TODO: add the adapters
        bin = gst.Bin()
        el = gst.element_factory_make(self.name)
        bin.add(el)
        return bin

    def make_audio_bin(self):
        if not self.is_audio:
            raise NameError, "this operation does not handle audio"

    def make_video_bin(self):
        if not self.is_video:
            raise NameError, "This operation does not handle video"
        

class TransitionFactory(OperationFactory):
    """
    Provides transitions useable in a timeline
    """

    def __init__(self):
        OperationFactory.__init__(self)

gobject.type_register(TransitionFactory)

class SMPTETransitionFactory(TransitionFactory):
    """
    Provides SMPTE video transitions useable in a timeline
    """

    def __init__(self):
        TransitionFactory.__init__(self)

gobject.type_register(TransitionFactory)

def _update_video_adapter_bin(settings, data):
    bin, vscale, ident = data
    result, pstate, pending = bin.get_state(0)
    if pstate > gst.STATE_READY:
        bin.set_state(gst.STATE_READY)
    filtcaps = gst.caps_from_string("video/x-raw-yuv,width=%d,height=%d,framerate=%f"
                                    % (settings.videowidth,
                                       settings.videoheight,
                                       settings.videorate))
    vscale.unlink(ident)
    vscale.link(ident, filtcaps)
    if pstate > gst.STATE_READY:
        bin.set_state(pstate)

def _update_audio_adapter_bin(settings, data):
    bin, ascale, ident = data
    result, pstate, pending = bin.get_state(0)
    if pstate > gst.STATE_READY:
        bin.set_state(gst.STATE_READY)
    filtcaps = gst.caps_from_string("audio/x-raw-int,channels=%d,rate=%d,depth=%d"
                                    % (settings.audiochannels,
                                       settings.audiorate,
                                       settings.audiodepth))
    ascale.unlink(ident)
    ascale.link(ident, filtcaps)
    if pstate > gst.STATE_READY:
        bin.set_state(pstate)

def make_video_adapter_bin(project):
    bin = gst.Bin()
    vrate = gst.element_factory_make("videorate")
    vscale = gst.element_factory_make("ffvideoscale")
    ident = gst.element_factory_make("identity")
    if not vscale:
        vscale = gst.element_factory_make("videoscale")
    bin.add(vrate, vscale, ident)
    vrate.link(vscale)
    filtcaps = gst.caps_from_string("video/x-raw-yuv,width=%d,height=%d,framerate=%f"
                                    % (project.settings.videowidth,
                                       project.settings.videoheight,
                                       project.settings.videorate))
    vscale.link(ident, filtcaps)
    bin.add_pad(gst.GhostPad("sink", vrate.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src", ident.get_pad("src")))
    project.settings.connect("settings-changed", _update_video_adapter_bin,
                             (bin, vscale, ident))
    return bin

def make_audio_adapter_bin(project):
    bin = gst.Bin()
    aconv = gst.element_factory_make("audioconvert")
    ascale = gst.element_factory_make("audioscale")
    ident = gst.element_factory_make("identity")
    bin.add(aconv, ascale, ident)
    aconv.link(ascale)
    filtcaps = gst.caps_from_string("audio/x-raw-int,channels=%d,rate=%d,depth=%d"
                                    % (project.settings.audiochannels,
                                       project.settings.audiorate,
                                       project.settings.audiodepth))
    ascale.link(ident, filtcaps)
    bin.add_pad(gst.GhostPad("sink", aconv.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src", ident.get_pad("src")))
    project.settings.connect("settings-changed", _update_audio_adapter_bin,
                             (bin, ascale, ident))
    return bin
