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
import gobject
import gst

from serializable import Serializable
from settings import ExportSettings
from stream import get_stream_for_caps

from gettext import gettext as _

class ObjectFactory(Serializable):
    """
    base class for object factories which provide elements to use
    in the timeline
    """

    __data_type__ = "object-factory"

    # UID (int) => object (BrotherObjects) mapping.
    __instances__ = weakref.WeakValueDictionary()

    # dictionnary of objects waiting for pending objects for completion
    # pending UID (int) => objects (list of BrotherObjects and extra field)
    __waiting_for_pending_objects__ = {}

    # FIXME : Use Setter/Getter for internal values !

    def __init__(self, name="", displayname="", project=None,
                 **unused_kw):
        gst.info("name:%s , project:%r" % (name, project))
        self._project = project
        self._name = name
        self._displayname = displayname
        self._is_audio = False
        self._is_video = False
        self.is_effect = False
        self.instances = []
        self._audio_info = None
        self._audio_info_stream = None
        self._video_info = None
        self._video_info_stream = None
        self._mediaTags = {}
        self.title = None
        self.artist = None
        self.uid = -1

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self._displayname or self._name)

    ## properties

    def _get_is_audio(self):
        return self._is_audio

    def _set_is_audio(self, isaudio):
        self._is_audio = isaudio
    is_audio = property(_get_is_audio, _set_is_audio,
                        doc="True if the factory provides audio")

    def _get_is_video(self):
        return self._is_video

    def _set_is_video(self, isvideo):
        self._is_video = isvideo
    is_video = property(_get_is_video, _set_is_video,
                        doc="True if the factory provides video")

    def _get_audio_info(self):
        return self._audio_info

    def _set_audio_info(self, inf):
        self._audio_info = inf
        self._audio_info_stream = get_stream_for_caps(inf)
    audio_info = property(_get_audio_info, _set_audio_info,
                          doc="Audio information as gst.Caps")

    def _get_video_info(self):
        return self._video_info
    def _set_video_info(self, inf):
        self._video_info = inf
        self._video_info_stream = get_stream_for_caps(inf)
    video_info = property(_get_video_info, _set_video_info,
                          doc="Video information as gst.Caps")

    # read only properties
    @property
    def audio_info_stream(self):
        """Audio information of a Stream"""
        return self._audio_info_stream

    @property
    def video_info_stream(self):
        """Video information of a Stream"""
        return self._video_info_stream

    @property
    def name(self):
        """Name of the factory"""
        return self._name

    @property
    def displayname(self):
        """Name of the factory for display"""
        return self._displayname

    @property
    def project(self):
        """Project this factory is being used in"""
        return self._project

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.displayname or self.name)

    # FIXME : Media Tags are only Source specific (or not ?)
    # FIXME : if so, should be moved down
    def addMediaTags(self, tags=[]):
        """ Add the given gst.Tag or gst.TagList to the factory """
        gst.debug("tags:%s" % tags)
        for tag in tags:
            self._mediaTags.update(tag)
        for tag in self._mediaTags.keys():
            if isinstance(self._mediaTags[tag], str):
                self._mediaTags[tag] = self._mediaTags[tag].replace('&', '&amp;').strip()
            if isinstance(self._mediaTags[tag], gst.Date):
                d = self._mediaTags[tag]
                self._mediaTags[tag] = "%s/%s/%s" % (d.day, d.month, d.year)
        gst.debug("tags:%s" % self._mediaTags)
        if self.video_info_stream:
            self.video_info_stream.codec = self._mediaTags.get(gst.TAG_VIDEO_CODEC)
        if self.audio_info_stream:
            self.audio_info_stream.codec = self._mediaTags.get(gst.TAG_AUDIO_CODEC)
        self.artist = self._mediaTags.get(gst.TAG_ARTIST)
        if self.artist:
            self.artist.strip()
        self.title = self._mediaTags.get(gst.TAG_TITLE)
        if self.title:
            self.title.strip()

    # FIXME : Method can stay here, but implementation is wrong
    def getPrettyInfo(self):
        """ Returns a prettyfied information string """
        if self.is_effect:
            if self.is_audio:
                return "Video Effect"
            elif self.is_video:
                return "Audio Effect"
            return "Effect"
        if not self.is_video and not self.is_audio:
            return "Unknown"
        stl = []
        # FIXME : file is FileSourceFactory specific !
        # FIXME : and it might not be a file:// but maybe a http://
        # FIXME : we're only importing gobject for the markup ! Extract the code
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
            stl.append(self.video_info_stream.markup)
        if self.is_audio and self.audio_info_stream:
            stl.append(self.audio_info_stream.markup)
        return '\n'.join(stl) + "</small>"

    # FIXME : Too limited and ugly. What if we have non-AV streams ??
    def makeAudioBin(self):
        """ returns a audio only bin """
        raise NotImplementedError

    def makeVideoBin(self):
        """ returns a video only bin """
        raise NotImplementedError


    # FIXME : ALL the following methods will die once we switch to a saner
    # FIXME : and more flexible way of doing file save/load
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
        self._name = obj["name"]
        self._displayname = obj["displayname"]
        self._is_audio = obj["is_audio"]
        self._is_video = obj["is_video"]
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




# FIXME : Figure out everything which is Source specific and put it here
# FIXME : It might not just be files (network sources ?) !
# FIMXE : It might not even had a URI ! (audio/video generators for ex)




# FIXME : Figure out everything which is Source specific and put it here
# FIXME : It might not just be files (network sources ?) !
# FIMXE : It might not even had a URI ! (audio/video generators for ex)

class SourceFactory(ObjectFactory):
    """
    Provides sources usable in a timeline
    """

    __data_type__ = "source-factory"

    def _getDuration(self):
        """
        Returns the maximum duration of the source in nanoseconds

        If the source doesn't have a maximum duration (like an image), subclasses
        should implement this by returning 2**63 - 1 (MAX_LONG).
        """
        raise NotImplementedError

    def _getDefaultDuration(self):
        """
        Returns the default duration of a file in nanoseconds,
        this should be used when using sources initially.

        Most sources will return the same as getDuration(), but can be overriden
        for sources that have an infinite duration.
        """
        return self.duration

    ## read only properties

    @property
    def default_duration(self):
        """Default duration of the source in nanoseconds"""
        return self._getDefaultDuration()

    @property
    def duration(self):
        """Maximum duration of the source in nanoseconds"""
        return self._getDuration()



# FIXME : What about non-file sources ???




# FIXME : What about non-file sources ???

class FileSourceFactory(SourceFactory):
    """
    Provides File sources useable in a timeline
    """

    __data_type__ = "file-source-factory"

    # FIXME : filename is specific to this class and should be obvious
    def __init__(self, filename="", **kwargs):
        name = kwargs.pop("name", filename)
        displayname = kwargs.pop("displayname", os.path.basename(unquote(filename)))
        SourceFactory.__init__(self, name=name, displayname=displayname,
                               **kwargs)
        self.lastbinid = 0
        self._length = 0
        self._thumbnail = ""
        self._thumbnails = []
        self.settings = None

    def _get_length(self):
        return self._length

    def _set_length(self, length):
        gst.debug("length:%r" % length)
        self._length = length
    length = property(_get_length, _set_length,
                      doc="Length of the file in nanoseconds")

    def _get_thumbnail(self):
        return self._thumbnail

    def _set_thumbnail(self, thumbnail):
        self._thumbnail = thumbnail
    thumbnail = property(_get_thumbnail, _set_thumbnail,
                         doc="Thumbnail file location")

    ## SourceFactory implementation
    def _getDuration(self):
        return self._length

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

    # WTF, code used nowhere ???
    def binIsDestroyed(self, bin):
        """ Remove the given bin from the list of instances """
        if bin in self.instances:
            self.instances.remove(bin)


    # FIXME : Shouldn't this be in a parent class ???
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
        ret["length"] = self._length
        return ret

    def fromDataFormat(self, obj):
        ObjectFactory.fromDataFormat(self, obj)
        self._length = obj["length"]


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
        OperationFactory.__init__(self, name=elementfactory.get_name(),
                                  displayname=elementfactory.get_longname(),
                                  **kwargs)
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






