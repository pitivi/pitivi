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
import weakref
from random import randint
import string
import gobject
import gst

from serializable import Serializable
from settings import ExportSettings

from gettext import gettext as _

class ObjectFactory(gobject.GObject, Serializable):
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

    __data_type__ = "object-factory"

    # UID (int) => object (BrotherObjects) mapping.
    __instances__ = weakref.WeakValueDictionary()

    # dictionnary of objects waiting for pending objects for completion
    # pending UID (int) => objects (list of BrotherObjects and extra field)
    __waiting_for_pending_objects__ = {}

    def __init__(self, **unused_kw):
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
        self.uid = -1

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


    # Serializable methods

    def toDataFormat(self):
        ret = Serializable.toDataFormat(self)
        ret["uid"] = self.getUniqueID()
        ret["name"] = self.name
        ret["displayname"] = self.displayname
        ret["is_audio"] = self.is_audio
        ret["is_video"] = self.is_video
        return ret

    def fromDataFormat(self, obj):
        Serializable.fromDataFormat(self, obj)
        self.name = obj["name"]
        self.displayname = obj["displayname"]
        self.is_audio = obj["is_audio"]
        self.is_video = obj["is_video"]
        self.setUniqueID(obj["uid"])

    # Unique ID methods

    def getUniqueID(self):
        if self.uid == -1:
            i = randint(0, 2**32)
            while i in ObjectFactory.__instances__:
                i = randint(0, 2 ** 32)
            self.uid = i
            ObjectFactory.__instances__[self.uid] = self
        return self.uid

    def setUniqueID(self, uid):
        if not self.uid == -1:
            gst.warning("Trying to set uid [%d] on an object that already has one [%d]" % (uid, self.uid))
            return

        if uid in ObjectFactory.__instances__:
            gst.warning("Uid [%d] is already in use by another object [%r]" % (uid, ObjectFactory.__instances__[uid]))
            return

        self.uid = uid
        gst.log("Recording __instances__[uid:%d] = %r" % (self.uid, self))
        ObjectFactory.__instances__[self.uid] = self

        # Check if an object needs to be informed of our creation
        self._haveNewID(self.uid)

    @classmethod
    def getObjectByUID(cls, uid):
        """
        Returns the object with the given uid if it exists.
        Returns None if no object with the given uid exist.
        """
        if uid in cls.__instances__:
            return cls.__instances__[uid]
        return None

    # Delayed object creation methods

    def _haveNewID(self, uid):
        """
        This method is called when an object gets a new ID.
        It will check to see if any object needs to be informed of the creation
        of this object.
        """
        if uid in ObjectFactory.__waiting_for_pending_objects__ and uid in ObjectFactory.__instances__:
            for obj, extra in ObjectFactory.__waiting_for_pending_objects__[uid]:
                obj.pendingObjectCreated(ObjectFactory.__instances__[uid], extra)
            del ObjectFactory.__waiting_for_pending_objects__[uid]


    @classmethod
    def addPendingObjectRequest(cls, obj, uid, extra=None):
        """
        Ask to be called when the object with the given uid is created.
        obj : calling object
        uid : uid of the object we need to be informed of creation
        extra : extradata with which obj's callback will be called

        The class will call the calling object's when the requested object
        is available using the following method call:
        obj.pendingObjectCreated(new_object, extra)
        """
        if not uid in cls.__waiting_for_pending_objects__:
            cls.__waiting_for_pending_objects__[uid] = []
        cls.__waiting_for_pending_objects__[uid].append((weakref.proxy(obj), extra))

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
                     (2**63) - 1, # should be (1<<64)-1 but #335854
                     0,
                     gobject.PARAM_READWRITE ),
        "thumbnail" :  ( gobject.TYPE_STRING,
                         "Thumbnail filename",
                         "Filename for the element's thumbnail",
                         "",
                         gobject.PARAM_READWRITE )
        }

    __data_type__ = "file-source-factory"

    def __init__(self, filename="", project=None, **kwargs):
        gst.info("filename:%s , project:%s" % (filename, project))
        ObjectFactory.__init__(self, **kwargs)
        self.project = project
        self.name = filename
        self.displayname = os.path.basename(unquote(self.name))
        self.lastbinid = 0
        self.length = 0
        self.thumbnail = ""
        self.thumbnails = []
        self.settings = None

    def do_set_property(self, property, value):
        if property.name == "length":
            if self.length and self.length != value:
                gst.warning("%s : Trying to set a new length (%s) different from previous one (%s)" % (self.name,
                                                                                                       gst.TIME_ARGS(self.length),
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
        try:
            dbin = gst.element_factory_make("decodebin2")
        except:
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
            asrc = gst.GhostPad("asrc", pad)
            asrc.set_active(True)
            bin.add_pad(asrc)
        elif "video" in pad.get_caps().to_string():
            mypad = bin.get_pad("vsrc")
            if mypad:
                gst.warning("Removing previous vsrc. WHY didn't decodebin remove it??")
                bin.remove_pad(mypad)
            vsrc = gst.GhostPad("vsrc", pad)
            vsrc.set_active(True)
            bin.add_pad(vsrc)
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
        if self.settings:
            return self.settings

        self.settings = ExportSettings()
        if self.video_info_stream:
            # Fill video properties
            vs = self.video_info_stream
            self.settings.videowidth = vs.width
            self.settings.videoheight = vs.height
            self.settings.videorate = vs.framerate
            self.settings.videopar = vs.par

        if self.audio_info_stream:
            # Fill audio properties
            as = self.audio_info_stream
            self.settings.audiochannels = as.channels
            self.settings.audiorate = as.rate
            self.settings.audiodepth = as.depth

        return self.settings

    # Serializable methods

    def toDataFormat(self):
        ret = ObjectFactory.toDataFormat(self)
        ret["filename"] = self.name
        ret["length"] = self.length
        return ret

    def fromDataFormat(self, obj):
        ObjectFactory.fromDataFormat(self, obj)
        self.name = obj["filename"]
        self.length = obj["length"]


class OperationFactory(ObjectFactory):
    """
    Provides operations useable in a timeline
    """

    __data_type__ = "operation-factory"

    def __init__(self, **kwargs):
        ObjectFactory.__init__(self, **kwargs)
        self.nbinput = 1
        self.nboutput = 1


class SimpleOperationFactory(OperationFactory):
    """
    Provides simple (audio OR video) operations useable in a timeline
    """

    __data_type__ = "simple-operation-factory"

    def __init__(self, elementfactory, **kwargs):
        """ elementfactory is the GstElementFactory """
        OperationFactory.__init__(self, **kwargs)
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

    __data_type__ = "transition-factory"

    def __init__(self, **kwargs):
        OperationFactory.__init__(self, **kwargs)


class SMPTETransitionFactory(TransitionFactory):
    """
    Provides SMPTE video transitions useable in a timeline
    """

    __data_type__ = "SMPTE-transition-factory"

    def __init__(self, **kwargs):
        TransitionFactory.__init__(self, **kwargs)

##
## Multimedia streams, used for definition of media streams
##


class MultimediaStream:
    """
    Defines a media stream

    Properties:
    * raw (boolean) : True if the stream is a raw media format
    * fixed (boolean) : True if the stream is entirely defined
    * codec (string) : User-friendly description of the codec used
    * caps (gst.Caps) : Caps corresponding to the stream
    """

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

    def getMarkup(self):
        """
        Returns a pango-markup string definition of the stream
        Subclasses need to implement this
        """
        raise NotImplementedError

class VideoStream(MultimediaStream):
    """
    Video Stream
    """

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
            # if no framerate was given, use 1fps
            self.framerate = gst.Fraction(1,1)
        try:
            self.par = struct["pixel-aspect-ratio"]
        except:
            # use a default setting, None is not valid !
            self.par = gst.Fraction(1,1)

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
    """
    Audio stream
    """

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
            self.depth = self.width

    def getMarkup(self):
        if self.raw:
            templ = _("<b>Audio:</b> %d channels at %d <i>Hz</i> (%d <i>bits</i>)")
            templ = templ % (self.channels, self.rate, self.width)
            if self.codec:
                templ = templ + _(" <i>(%s)</i>") % self.codec
            return templ
        return _("<b>Unknown Audio format:</b> %s") % self.audiotype

class TextStream(MultimediaStream):
    """
    Text media stream
    """

    def _analyzeCaps(self):
        if len(self.caps) > 1:
            self.fixed = False

        self.texttype = self.caps[0].get_name()

    def getMarkup(self):
        return _("<b>Text:</b> %s") % self.texttype

def get_stream_for_caps(caps):
    """
    Returns the appropriate MediaStream corresponding to the
    given caps.
    """
    val = caps.to_string()
    if val.startswith("video/"):
        return VideoStream(caps)
    elif val.startswith("audio/"):
        return AudioStream(caps)
    elif val.startswith("text/"):
        return TextStream(caps)
    else:
        # FIXME : we should have an 'unknow' data stream class
        return None
