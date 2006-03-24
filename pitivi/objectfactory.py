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

"""
Providers of elements to use in a timeline
"""

import os.path
from urllib import unquote
import string
import gobject
import gst

import utils

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
        """
        override for the "set_property" gobject virtual method
        """
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

    def setAudioInfo(self, caps):
        """ sets the audio caps of the element """
        self.set_property("audio-info", caps)

    def setVideoInfo(self, caps):
        """ set the video caps of the element """
        self.set_property("video-info", caps)

    def setAudio(self, is_audio):
        """ sets whether the element has audio stream """
        self.set_property("is-audio", is_audio)

    def setVideo(self, is_video):
        """ sets whether the element has video stream """
        self.set_property("is-video", is_video)

    def makeAudioBin(self):
        """ returns a audio only bin """
        raise NotImplementedError

    def makeVideoBin(self):
        """ returns a video only bin """
        raise NotImplementedError


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

    def makeBin(self):
        """ returns a source bin with all pads """
        bin = gst.Bin("%s-%d" % (self.name, self.lastbinid))
        self.lastbinid = self.lastbinid + 1
        src = gst.element_make_from_uri(gst.URI_SRC, self.name, "file source")
        dbin = gst.element_factory_make("decodebin")
        bin.add(src, dbin)
        src.link(dbin)

        dbin.connect("new-decoded-pad", self._binNewDecodedPadCb, bin )
        dbin.connect("removed-decoded-pad", self._binRemovedDecodedPadCb, bin)

        self.instances.append(bin)
        return bin

    def _binNewDecodedPadCb(self, dbin, pad, is_last, bin):
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

    def _binRemovedDecodedPadCb(self, dbin, pad, bin):
        gst.info("pad %s was removed" % pad)
        if "audio" in pad.get_caps().to_string():
            mypad = bin.get_pad("asrc")
        elif "video" in pad.get_caps().to_string():
            mypad = bin.get_pad("vsrc")
        else:
            return
        bin.remove_pad(mypad)
        
    def binIsDestroyed(self, bin):
        """ Remove the given bin from the list of instances """
        if bin in self.instances:
            self.instances.remove(bin)

    def setLength(self, length):
        """ sets the length of the element """
        self.set_property("length", length)

    def setThumbnail(self, thumbnail):
        """ Sets the thumbnail filename of the element """
        self.set_property("thumbnail", thumbnail)

    def getPrettyInfo(self):
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
                # FIXME : use DAR
                stl.append("Video: %d x %d @ %3f fps" % (self.video_info[0]["width"],
                                                        self.video_info[0]["height"],
                                                        utils.float_framerate(self.video_info[0]["framerate"])))
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

class OperationFactory(ObjectFactory):
    """
    Provides operations useable in a timeline
    """

    def __init__(self):
        ObjectFactory.__init__(self)
        self.nbinput = 1
        self.nboutput = 1


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


class TransitionFactory(OperationFactory):
    """
    Provides transitions useable in a timeline
    """

    def __init__(self):
        OperationFactory.__init__(self)


class SMPTETransitionFactory(TransitionFactory):
    """
    Provides SMPTE video transitions useable in a timeline
    """

    def __init__(self):
        TransitionFactory.__init__(self)
