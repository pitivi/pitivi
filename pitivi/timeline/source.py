# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/source.py
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
Timeline source objects
"""

import gst
from objects import TimelineObject, MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO, MEDIA_TYPE_NONE

class TimelineSource(TimelineObject):
    """
    Base class for all sources (O input)

    Save/Load properties:
    * 'media-start' (int) : start position of the media
    * 'media-duration' (int) : duration of the media
    """
    __signals__ = {
        "media-start-duration-changed" : ["media-start", "media-duration"]
        }

    __data_type__ = "timeline-source"


    def __init__(self, media_start=gst.CLOCK_TIME_NONE,
                 media_duration=0, **kwargs):
        self.media_start = media_start
        self.media_duration = media_duration
        TimelineObject.__init__(self, **kwargs)

    def _makeGnlObject(self):
        # FIXME : This should all be in *Factory.make*bin
        gst.debug("Making a source for %r" % self)
        if self.isaudio:
            caps = gst.caps_from_string("audio/x-raw-int;audio/x-raw-float")
            postfix = "audio"
        elif self.isvideo:
            caps = gst.caps_from_string("video/x-raw-yuv;video/x-raw-rgb")
            postfix = "video"
        else:
            raise NameError, "media type is NONE !"

        if self.factory:
            self.factory.lastbinid = self.factory.lastbinid + 1
            sourcename =  "source-" + self.name + "-" + postfix + str(self.factory.lastbinid)
        else:
            sourcename = "source-" + self.name + "-" + postfix
        gnl = gst.element_factory_make("gnlsource", sourcename)

        try:
            gst.debug("calling makeGnlSourceContents()")
            obj = self.makeGnlSourceContents()
        except:
            gst.debug("Failure in calling self.makeGnlSourceContents()")
            import sys
            sys.excepthook(*sys.exc_info())
            return None
        gnl.add(obj)

        # set properties
        gnl.set_property("media-duration", long(self.media_duration))
        gnl.set_property("media-start", long(self.media_start))
        gnl.set_property("caps", caps)
        gnl.connect("notify::media-start", self._mediaStartDurationChangedCb)
        gnl.connect("notify::media-duration", self._mediaStartDurationChangedCb)
        return gnl

    def makeGnlSourceContents(self):
        """
        Return the contents of the gnlsource.
        Should be a single element (or bin).

        Sub-classes not implementing this method will need to override
        the _makeGnlObject() method.
        """
        #FIXME : Maybe the default implementation should be to call
        # the factory's make*bin() method !
        raise NotImplementedError

    def _setMediaStartDurationTime(self, start=gst.CLOCK_TIME_NONE,
                                   duration=0):
        gst.info("TimelineFileSource %s start:%s , duration:%s" % (
            self,
            gst.TIME_ARGS(start),
            gst.TIME_ARGS(duration)))
        gst.info("TimelineFileSource %s EXISTING start:%s , duration:%s" % (
            self,
            gst.TIME_ARGS(self.media_start),
            gst.TIME_ARGS(self.media_duration)))
        if duration > 0 and not self.media_duration == duration:
            duration = max(0, min(duration, self.factory.getDuration()))
            self.gnlobject.set_property("media-duration", long(duration))
        if not start == gst.CLOCK_TIME_NONE and not self.media_start == start:
            start = max(0, start)
            self.gnlobject.set_property("media-start", long(start))

    # override setInTime and setOutTime methods to handle media-start/duration

    def setInTime(self, time):
        """Sets the [media-]{start,duration} properties such that the
        out-point and hypothetical beginning of the media remain constant."""
        # { .... [ ==|=======] .... }
        # A      B   t       C      D
        # or
        # { ..|. [ ==========] .... }
        # A   t  B           C      D
        # 
        # A = hypothetical start of media file
        # B = in-point in timeline
        # C = out-point in timeline
        # D = hypothetical end of media file
        # t = input time, where we want point B
        delta = time - self.start
        duration = self.duration - delta
        media_start = self.media_start + delta
        self.setStartDurationTime(time, duration)
        self.setMediaStartDurationTime(media_start, duration)

    def setOutTime(self, time):
        """Sets the [media-]{start,duration} properties such that the in-point
        of the source remain constant."""
        self.setStartDurationTime(gst.CLOCK_TIME_NONE, time - self.start)
        self.setMediaStartDurationTime(gst.CLOCK_TIME_NONE, time - self.start)

    def setMediaStartDurationTime(self, start=gst.CLOCK_TIME_NONE,
                                  duration=0):
        """ sets the media start/duration time """
        self._setMediaStartDurationTime(start, duration)
        if self.linked and isinstance(self.linked, TimelineFileSource):
            self.linked._setMediaStartDurationTime(start, duration)

    def _mediaStartDurationChangedCb(self, gnlobject, prop):
        gst.log("%r %s %s" % (gnlobject, prop, prop.name))
        mstart = None
        mduration = None
        if prop.name == "media-start":
            mstart = gnlobject.get_property("media-start")
            gst.log("start: %s => %s" % (gst.TIME_ARGS(self.media_start),
                                         gst.TIME_ARGS(mstart)))
            if self.media_start == gst.CLOCK_TIME_NONE:
                self.media_start = mstart
            elif mstart == self.media_start:
                mstart = None
            else:
                self.media_start = mstart
        elif prop.name == "media-duration":
            mduration = gnlobject.get_property("media-duration")
            gst.log("duration: %s => %s" % (gst.TIME_ARGS(self.media_duration),
                                         gst.TIME_ARGS(mduration)))
            if mduration == self.media_duration:
                mduration = None
            else:
                self.media_duration = mduration
        if not mstart == None or not mduration == None:
            self.emit("media-start-duration-changed",
                      self.media_start, self.media_duration)

class TimelineBlankSource(TimelineSource):
    """
    Blank source for testing purposes.
    """

    __data_type__ = "timeline-blank-source"
    __requires_factory__ = False

    def __init__(self, **kwargs):
        TimelineSource.__init__(self, **kwargs)

    def makeGnlSourceContents(self):
        if self.isaudio:
            # silent audiotestsrc
            src = gst.element_factory_make("audiotestsrc")
            src.set_property("volume", 0)
        elif self.isvideo:
            # black videotestsrc
            src = gst.element_factory_make("videotestsrc")
            src.props.pattern = 2
        else:
            gst.error("Can only handle Audio OR Video sources")
            return None
        return src

    def getExportSettings(self):
        return self.factory.getExportSettings()

class TimelineFileSource(TimelineSource):
    """
    Seekable sources (mostly files)

    Save/Load properties:
    * (optional) 'volume' (int) : volume of the audio
    """
    __data_type__ = "timeline-file-source"

    __editable_properties__ = (
        ("volume", float, (-1, 1), True),
    )

    def __init__(self, **kw):
        TimelineSource.__init__(self, **kw)

    def _makeGnlObject(self):
        if self.media_start == gst.CLOCK_TIME_NONE:
            self.media_start = 0
        if self.media_duration == 0:
            self.media_duration = self.factory.default_duration

        gnlobject = TimelineSource._makeGnlObject(self)
        if gnlobject == None:
            return None

        # we override start/duration
        gnlobject.set_property("duration", long(self.factory.default_duration))
        gnlobject.set_property("start", long(0))

        return gnlobject

    def makeGnlSourceContents(self):
        if self.isaudio:
            self.decodebin = self.factory.makeAudioBin()
        elif self.isvideo:
            self.decodebin = self.factory.makeVideoBin()
        else:
            raise NameError, "media type is NONE !"

        if self.isaudio:
            self.volume_element = gst.element_factory_make("volume", "internal-volume")
            self.audioconv = gst.element_factory_make("audioconvert", "audioconv")
            self.volumebin = gst.Bin("volumebin")
            self.volumebin.add(self.decodebin, self.audioconv, self.volume_element)
            self.audioconv.link(self.volume_element)
            self.decodebin.connect('pad-added', self._decodebinPadAddedCb)
            self.decodebin.connect('pad-removed', self._decodebinPadRemovedCb)
            bin = self.volumebin
        else:
            bin = self.decodebin

        return bin

    def _decodebinPadAddedCb(self, unused_dbin, pad):
        pad.link(self.audioconv.get_pad("sink"))
        ghost = gst.GhostPad("src", self.volume_element.get_pad("src"))
        ghost.set_active(True)
        self.volumebin.add_pad(ghost)

    def _decodebinPadRemovedCb(self, unused_dbin, pad):
        gst.log("pad:%s" % pad)
        # workaround for gstreamer bug ...
        gpad = self.volumebin.get_pad("src")
        target = gpad.get_target()
        peer = target.get_peer()
        target.unlink(peer)
        # ... to hereeeto here
        self.volumebin.remove_pad(self.volumebin.get_pad("src"))
        self.decodebin.unlink(self.audioconv)

    def getVolume(self):
        return self.volume_element.props.level

    def __setVolume(self, level):
        self.volume_element.props.volume = level

    def setVolume(self, level):
        """ Set the volume to the given level """
        if self.isaudio:
            self.__setVolume(level)
        elif self.linked:
            self.linked.__setVolume(level)

    volume = property(getVolume, setVolume)

    def _makeBrother(self):
        """ make the brother element """
        self.gnlobject.info("making filesource brother")
        # find out if the factory provides the other element type

        # FIXME : this is atrociously complicated code for such a simple
        # thing. We should just figure out the brother stream and then ask
        # To create the object for the same factory by the other stream

        # FIXME : The factory knows which stream is the brother of another !!!

        if self.media_type == MEDIA_TYPE_NONE:
            return None
        if not self.isaudio and not self.isvideo:
            return None
        # handle blank cases
        classtype = TimelineFileSource
        if self.isvideo and not self.factory.is_audio:
            classtype = TimelineBlankSource
        if self.isaudio and not self.factory.is_video:
            classtype = TimelineBlankSource
        if self.isaudio:
            mtype = MEDIA_TYPE_VIDEO
        else:
            mtype = MEDIA_TYPE_AUDIO
        return classtype(media_start=self.media_start,
                         media_duration=self.media_duration,
                         factory=self.factory, start=self.start,
                         duration=self.duration,
                         media_type=mtype,
                         name=self.name + "-brother")


    def getExportSettings(self):
        return self.factory.getExportSettings()

    # Serializable methods

    def toDataFormat(self):
        ret = TimelineSource.toDataFormat(self)
        ret["media-start"] = self.media_start
        ret["media-duration"] = self.media_duration
        if self.isaudio and hasattr(self, "volume_element"):
            ret["volume"] = self.volume_element.get_property("volume")
        return ret

    def fromDataFormat(self, obj):
        TimelineSource.fromDataFormat(self, obj)
        self.media_start = obj["media-start"]
        self.media_duration = obj["media-duration"]
        if "volume" in obj:
            volume = obj["volume"]
            self.setVolume(volume)

class TimelineLiveSource(TimelineSource):
    """
    Non-seekable sources (like cameras)
    """

    __data_type__ = "timeline-live-source"

    def __init__(self, **kwargs):
        TimelineSource.__init__(self, **kwargs)
