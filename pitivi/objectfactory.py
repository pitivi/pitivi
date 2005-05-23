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
                         gobject.PARAM_READWRITE ),
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
        self.nbinput = 0
        self.nboutput = 0
        self.thumbnail = ""
        self.thumbnails = []
        self.instances = []
        self.length = 0
        self.audio_info = None
        self.video_info = None

    def do_set_property(self, property, value):
        if property.name == "is-audio":
            self.is_audio = value
        elif property.name == "is-video":
            self.is_video = value
        elif property.name == "length":
            self.length = value
        elif property.name == "thumbnail":
            self.thumbnail = value
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
            

gobject.type_register(ObjectFactory)

class FileSourceFactory(ObjectFactory):
    """
    Provides File sources useable in a timeline
    """

    def __init__(self, filename):
        ObjectFactory.__init__(self)
        self.name = filename
        self.displayname = os.path.basename(unquote(self.name))
        self.lastbinid = 0

    def make_bin(self):
        """ returns a source bin with all pads """
        # pipeline = gst.Pipeline()
        bin = gst.Bin()
        src = gst.element_factory_make("gnomevfssrc")
        src.set_property("location", self.name)
        dbin = gst.element_factory_make("decodebin")
        bin.add_many(src, dbin)
        src.link(dbin)
##         if self.is_audio:
##             aident = gst.element_factory_make("identity")
##             bin.add(aident)
##             bin.add_ghost_pad(aident.get_pad("src"), "asrc")
##         else:
##             aident = None
##         if self.is_video:
##             vident = gst.element_factory_make("identity")
##             bin.add(vident)
##             bin.add_ghost_pad(vident.get_pad("src"), "vsrc")
##         else:
##             vident = None

        dbin.connect("new-decoded-pad", self._bin_new_decoded_pad, bin )
        dbin.connect("removed-decoded-pad", self._bin_removed_decoded_pad, bin)

##         pipeline.add(bin)
##         pipeline.set_state(gst.STATE_PLAYING)
        
##         for i in range(100):
##             if not pipeline.iterate():
##                 break

##         print bin.get_pad_list()
##         pipeline.set_state(gst.STATE_PAUSED)
##         bin.seek(gst.FORMAT_TIME, 0L) 
##         print bin.get_pad_list()
##         pipeline.remove(bin)
##         print bin.get_pad_list()
##         dbin.disconnect(sig)

        self.instances.append(bin)
        return bin

##     def _aprobe(self, probe, data):
##         print "aprobe", data
##         return True

##     def _vprobe(self, probe, data):
##         print "vprobe", data
##         return True

    def _bin_new_decoded_pad(self, dbin, pad, is_last, bin):
        print "decoded pad", pad.get_caps().to_string()
        # add it as ghost_pad to the bin
        if "audio" in pad.get_caps().to_string():
            bin.add_ghost_pad(pad, "asrc")
        elif "video" in pad.get_caps().to_string():
            bin.add_ghost_pad(pad, "vsrc")
        else:
            return
        #self.emit("new-decoded-pad", newpad)

    def _bin_removed_decoded_pad(self, dbin, pad, bin):
        print "pad", pad, "was removed"
        if "audio" in pad.get_caps().to_string():
            mypad = bin.get_pad("asrc")
        elif "video" in pad.get_caps().to_string():
            mypad = bin.get_pad("vsrc")
        else:
            return
        #self.emit("removed-decoded-pad", mypad)
        bin.remove_pad(mypad)
        
##         if "audio" in pad.get_caps().to_string():
##             probe = gst.Probe(False, self._aprobe)
##             pad.add_probe(probe)
##             bin.add_ghost_pad(pad, "asrc")
##             if not self.is_video or bin.get_pad("vsrc"):
##                 bin.set_eos()
##         elif "video" in pad.get_caps().to_string():
##             probe = gst.Probe(False, self._vprobe)
##             pad.add_probe(probe)
##             bin.add_ghost_pad(pad, "vsrc")
##             if not self.is_audio or bin.get_pad("asrc"):
##                 bin.set_eos()


    def bin_is_destroyed(self, bin):
        if bin in self.instances:
            self.instances.remove(bin)

    def _single_bin_new_decoded_pad(self, dbin, pad, is_last, data):
        # add safe de-activation of the other pad
        bin, mtype, identity = data
        if mtype in pad.get_caps().to_string():
            pad.link(identity.get_pad("sink"))
        if identity.get_pad("sink").get_peer():
            for pad in [x for x in dbin.get_pad_list() if x.get_direction == gst.PAD_SRC]:
                if not mtype in pad.get_caps().to_string():
                    pad.activate_recursive(False)
            
    def _single_bin_removed_decoded_pad(self, dbin, pad, data):
        bin, mtype, identity = data
        if mtype in pad.get_caps().to_string():
            pad.unlink(identity.get_pad("sink"))

    def _make_single_bin(self, type):
        # Use identity and ghost pad !
        bin = gst.Bin(self.name + str(self.lastbinid))
        self.lastbinid = self.lastbinid + 1
        src = gst.element_factory_make("gnomevfssrc")
        src.set_property("location", self.name)
        dbin = gst.element_factory_make("decodebin")
        ident = gst.element_factory_make("identity")
        bin.add_many(src, dbin, ident)
        src.link(dbin)
        bin.add_ghost_pad(ident.get_pad("src"), "src")
        
        dbin.connect("new-decoded-pad", self._single_bin_new_decoded_pad, (bin, type, ident))
        dbin.connect("removed-decoded-pad", self._single_bin_removed_decoded_pad, (bin, type, ident))

        self.instances.append(bin)
        return bin

    def make_audio_bin(self):
        return self._make_single_bin("audio")

    def make_video_bin(self):
        return self._make_single_bin("video")

    def make_audio_gnlsource(self):
        pass

    def make_video_gnlsource(self):
        pass

gobject.type_register(FileSourceFactory)

class OperationFactory(ObjectFactory):
    """
    Provides operations useable in a timeline
    """

    def __init__(self):
        ObjectFactory.__init__(self)

gobject.type_register(OperationFactory)

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
