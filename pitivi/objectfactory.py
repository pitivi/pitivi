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
from settings import ExportSettings

from gettext import gettext as _

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
        self.audio_info_stream = None
        self.video_info = None
        self.video_info_stream = None
        self.mediaTags = {}
        self.title = None
        self.artist = None

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
            self.video_info_stream = get_stream_for_caps(value)
        elif property.name == "audio-info":
            self.audio_info = value
            self.audio_info_stream = get_stream_for_caps(value)
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

    def addMediaTags(self, tags=[]):
        """ Add the given gst.Tag or gst.TagList to the factory """
        gst.debug("tags:%s" % tags)
        for tag in tags:
            self.mediaTags.update(tag)
        for tag in self.mediaTags.keys():
            if isinstance(self.mediaTags[tag], str):
                self.mediaTags[tag] = self.mediaTags[tag].replace('&', '&amp;').strip()
            if isinstance(self.mediaTags[tag], gst.Date):
                d = self.mediaTags[tag]
                self.mediaTags[tag] = "%s/%s/%s" % (d.day, d.month, d.year)
        gst.debug("tags:%s" % self.mediaTags)
        if self.video_info_stream:
            self.video_info_stream.set_codec(self.mediaTags.get(gst.TAG_VIDEO_CODEC))
        if self.audio_info_stream:
            self.audio_info_stream.set_codec(self.mediaTags.get(gst.TAG_AUDIO_CODEC))
        self.artist = self.mediaTags.get(gst.TAG_ARTIST)
        if self.artist:
            self.artist.strip()
        self.title = self.mediaTags.get(gst.TAG_TITLE)
        if self.title:
            self.title.strip()

    def getPrettyInfo(self):
        """ Returns a prettyfied information string """
        if self.is_effect:
            if self.is_audio:
                return "Video Effect"
            elif self.is_video:
                return "Audio Effect"
            return "Effect"
        if not self.is_video and not self.is_audio:
            "Unknown"
        stl = []
        filename = os.path.basename(unquote(self.name))
        if not self.title:
            stl.append(_("<b>%s</b><small>") % gobject.markup_escape_text(filename))
        else:
            # either 'Title' or 'Title (Artist)'
            if self.artist:
                stl.append(_("<b>%s</b> (%s)") % (gobject.markup_escape_text(self.title),
                                               gobject.markup_escape_text(self.artist)))
            else:
                stl.append(_("<b>%s</b>") % gobject.markup_escape_text(self.title))
            stl.append(_("<small><b>File:</b> %s") % filename)
##         if self.title:
##             stl.append("<b>Title:</b> %s" % self.title)
##         if self.artist:
##             stl.append("<b>Artist:</b> %s" % self.artist)
        if self.is_video and self.video_info_stream:
            stl.append(self.video_info_stream.getMarkup())
        if self.is_audio and self.audio_info_stream:
            stl.append(self.audio_info_stream.getMarkup())
        return string.join(stl, "\n") + "</small>"

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
                     (2**63) - 1, # should be (1<<64)-1 but #335854
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
            if self.length and self.length != value:
                gst.warning("%s : Trying to set a new length (%s) different from previous one (%s)" % (gst.TIME_ARGS(self.length),
                                                                                                       gst.TIME_ARGS(value)))
            self.length = value
        elif property.name == "thumbnail":
            if os.path.isfile(value):
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

    def _binNewDecodedPadCb(self, unused_dbin, pad, unused_is_last, bin):
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

    def _binRemovedDecodedPadCb(self, unused_dbin, pad, bin):
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

    def getExportSettings(self):
        """ Returns the ExportSettings corresponding to this source """
        settings = ExportSettings()
        if self.video_info_stream:
            # Fill video properties
            vs = self.video_info_stream
            settings.videowidth = vs.width
            settings.videoheight = vs.height
            settings.videorate = vs.framerate
            settings.videopar = vs.par

        if self.audio_info_stream:
            # Fill audio properties
            as = self.audio_info_stream
            settings.audiochannels = as.channels
            settings.audiorate = as.rate
            settings.audiodepth = as.depth
            
        return settings

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

class MultimediaStream:

    def __init__(self, caps):
        gst.log("new with caps %s" % caps.to_string())
        self.caps = caps
        self.raw = False
        self.fixed = True
        self.codec = None
        self._analyzeCaps()

    def set_codec(self, codecstring=None):
        if codecstring and codecstring.strip():
            self.codec = codecstring.strip()

    def _analyzeCaps(self):
        raise NotImplementedError

class VideoStream(MultimediaStream):

    def _analyzeCaps(self):
        if len(self.caps) > 1:
            self.fixed = False
            
        struct = self.caps[0]
        self.videotype = struct.get_name()
        if self.videotype.startswith("video/x-raw-"):
            self.raw=True
        else:
            self.raw=False

        try:
            self.format = struct["format"]
        except:
            self.format = None
        try:
            self.width = struct["width"]
        except:
            self.width = None
        try:
            self.height = struct["height"]
        except:
            self.height = None
        try:
            self.framerate = struct["framerate"]
        except:
            self.framerate = None
        try:
            self.par = struct["pixel-aspect-ratio"]
        except:
            self.par = None

        if self.width and self.height and self.par:
            self.dar = gst.Fraction(self.width * self.par.num, self.height * self.par.denom)
        else:
            if self.width and self.height:
                self.dar = gst.Fraction(self.width, self.height)
            else:
                self.dar = gst.Fraction(4, 3)

    def getMarkup(self):
        if self.raw:
            if self.framerate.num:
                templ = _("<b>Video:</b> %d x %d <i>pixels</i> at %.2f<i>fps</i>")
                templ = templ % (self.dar * self.height , self.height, float(self.framerate))
            else:
                templ = _("<b>Image:</b> %d x %d <i>pixels</i>")
                templ = templ % (self.dar * self.height, self.height)
            if self.codec:
                templ = templ + _(" <i>(%s)</i>") % self.codec
            return templ
        return _("<b>Unknown Video format:</b> %s") % self.videotype
            
class AudioStream(MultimediaStream):

    def _analyzeCaps(self):
        if len(self.caps) > 1:
            self.fixed = False

        struct = self.caps[0]
        self.audiotype = struct.get_name()
        if self.audiotype.startswith("audio/x-raw-"):
            self.raw = True
        else:
            self.raw = False

        if self.audiotype == "audio/x-raw-float":
            self.float = True
        else:
            self.float = False

        try:
            self.channels = struct["channels"]
        except:
            self.channels = None
        try:
            self.rate = struct["rate"]
        except:
            self.rate = None
        try:
            self.width = struct["width"]
        except:
            self.width = None
        try:
            self.depth = struct["depth"]
        except:
            self.depth = None

    def getMarkup(self):
        if self.raw:
            templ = _("<b>Audio:</b> %d channels at %d <i>Hz</i> (%d <i>bits</i>)")
            templ = templ % (self.channels, self.rate, self.width)
            if self.codec:
                templ = templ + _(" <i>(%s)</i>") % self.codec
            return templ
        return _("<b>Unknown Audio format:</b> %s") % self.audiotype

class TextStream(MultimediaStream):

    def _analyzeCaps(self):
        if len(self.caps) > 1:
            self.fixed = False

        self.texttype = self.caps[0].get_name()

    def getMarkup(self):
        return _("<b>Text:</b> %s") % self.texttype

def get_stream_for_caps(caps):
    val = caps.to_string()
    if val.startswith("video/"):
        return VideoStream(caps)
    if val.startswith("audio/"):
        return AudioStream(caps)
    if val.startswith("text/"):
        return TextStream(caps)
    return None
                     
