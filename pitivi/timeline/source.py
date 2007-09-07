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

import gobject
import gst
from pitivi.elements.singledecodebin import SingleDecodeBin
from objects import TimelineObject, MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO, MEDIA_TYPE_NONE

class TimelineSource(TimelineObject):
    """
    Base class for all sources (O input)
    """

    __data_type__ = "timeline-source"

    # FIXME : media_start and media_duration should be in this class

    def __init__(self, **kw):
        TimelineObject.__init__(self, **kw)

class TimelineBlankSource(TimelineSource):
    """
    Blank source for testing purposes.
    """

    __data_type__ = "timeline-blank-source"
    __requires_factory__ = False

    def __init__(self, **kw):
        TimelineObject.__init__(self, **kw)

    def _makeGnlObject(self):
        if self.media_type == MEDIA_TYPE_AUDIO:
            src = gst.element_factory_make("audiotestsrc")
            src.set_property("volume", 0)
        elif self.media_type == MEDIA_TYPE_VIDEO:
            src = gst.element_factory_make("videotestsrc")
        else:
            gst.Error("Can only handle Audio OR Video sources")
            return
        gnl = gst.element_factory_make("gnlsource")
        gnl.add(src)
        return gnl

    def getExportSettings(self):
        return self.factory.getExportSettings()

class TimelineFileSource(TimelineSource):
    """
    Seekable sources (mostly files)

    Save/Load properties:
    * 'media-start' (int) : start position of the media
    * 'media-duration' (int) : duration of the media
    * (optional) 'volume' (int) : volume of the audio
    """
    __gsignals__ = {
        "media-start-duration-changed" : ( gobject.SIGNAL_RUN_LAST,
                                       gobject.TYPE_NONE,
                                       (gobject.TYPE_UINT64, gobject.TYPE_UINT64))
        }

    __data_type__ = "timeline-file-source"

    def __init__(self, media_start=-1, media_duration=-1, **kw):
        self.media_start = media_start
        self.media_duration = media_duration
        TimelineSource.__init__(self, **kw)

    def _makeGnlObject(self):
        gst.log("creating object")
        if self.media_type == MEDIA_TYPE_AUDIO:
            caps = gst.caps_from_string("audio/x-raw-int;audio/x-raw-float")
            postfix = "audio"
        elif self.media_type == MEDIA_TYPE_VIDEO:
            caps = gst.caps_from_string("video/x-raw-yuv;video/x-raw-rgb")
            postfix = "video"
        else:
            raise NameError, "media type is NONE !"
        self.factory.lastbinid = self.factory.lastbinid + 1

        gnlobject = gst.element_factory_make("gnlsource", "source-" + self.name + "-" + postfix + str(self.factory.lastbinid))
        self.decodebin = SingleDecodeBin(caps=caps, uri=self.factory.name)
        if self.media_type == MEDIA_TYPE_AUDIO:
            self.volumeElement = gst.element_factory_make("volume", "internal-volume")
            self.audioconv = gst.element_factory_make("audioconvert", "fdsjkljf")
            self.volumeBin = gst.Bin("volumebin")
            self.volumeBin.add(self.decodebin, self.audioconv, self.volumeElement)
            self.audioconv.link(self.volumeElement)
            self.decodebin.connect('pad-added', self._decodebinPadAddedCb)
            self.decodebin.connect('pad-removed', self._decodebinPadRemovedCb)
            gnlobject.add(self.volumeBin)
        else:
            gnlobject.add(self.decodebin)
        gnlobject.set_property("caps", caps)
        gnlobject.set_property("start", long(0))
        gnlobject.set_property("duration", long(self.factory.length))

        if self.media_start == -1:
            self.media_start = 0
        if self.media_duration == -1:
            self.media_duration = self.factory.length
        gnlobject.set_property("media-duration", long(self.media_duration))
        gnlobject.set_property("media-start", long(self.media_start))
        gnlobject.connect("notify::media-start", self._mediaStartDurationChangedCb)
        gnlobject.connect("notify::media-duration", self._mediaStartDurationChangedCb)

        return gnlobject

    def _decodebinPadAddedCb(self, dbin, pad):
        pad.link(self.audioconv.get_pad("sink"))
        ghost = gst.GhostPad("src", self.volumeElement.get_pad("src"))
        ghost.set_active(True)
        self.volumeBin.add_pad(ghost)

    def _decodebinPadRemovedCb(self, dbin, pad):
        gst.log("pad:%s" % pad)
        # workaround for gstreamer bug ...
        gpad = self.volumeBin.get_pad("src")
        target = gpad.get_target()
        peer = target.get_peer()
        target.unlink(peer)
        # ... to hereeeto here
        self.volumeBin.remove_pad(self.volumeBin.get_pad("src"))
        self.decodebin.unlink(self.audioconv)

    def _setVolume(self, level):
        self.volumeElement.set_property("volume", level)
        #FIXME: we need a volume-changed signal, so that UI updates

    def setVolume(self, level):
        if self.media_type == MEDIA_TYPE_AUDIO:
            self._setVolume(level)
        else:
            self.linked._setVolume(level)

    def _makeBrother(self):
        """ make the brother element """
        self.gnlobject.info("making filesource brother")
        # find out if the factory provides the other element type
        if self.media_type == MEDIA_TYPE_NONE:
            return None
        if self.media_type == MEDIA_TYPE_VIDEO:
            if not self.factory.is_audio:
                return None
            brother = TimelineFileSource(media_start=self.media_start, media_duration=self.media_duration,
                                         factory=self.factory, start=self.start, duration=self.duration,
                                         media_type=MEDIA_TYPE_AUDIO,
                                         name=self.name + "-brother")
        elif self.media_type == MEDIA_TYPE_AUDIO:
            if not self.factory.is_video:
                return None
            brother = TimelineFileSource(media_start=self.media_start, media_duration=self.media_duration,
                                         factory=self.factory, start=self.start, duration=self.duration,
                                         media_type=MEDIA_TYPE_VIDEO,
                                         name=self.name + "-brother")
        else:
            brother = None
        return brother

    def _setMediaStartDurationTime(self, start=-1, duration=-1):
        gst.info("TimelineFileSource start:%s , duration:%s" % (
                gst.TIME_ARGS(start),
                gst.TIME_ARGS(duration)))
        gst.info("TimelineFileSource EXISTING start:%s , duration:%s" % (
                gst.TIME_ARGS(self.media_start),
                gst.TIME_ARGS(self.media_duration)))
        if not duration == -1 and not self.media_duration == duration:
            self.gnlobject.set_property("media-duration", long(duration))
        if not start == -1 and not self.media_start == start:
            self.gnlobject.set_property("media-start", long(start))

    def setMediaStartDurationTime(self, start=-1, duration=-1):
        """ sets the media start/duration time """
        if not start == -1 and start < 0:
            gst.warning("Can't set start values < 0 !")
            return
        if not duration == -1 and duration <= 0:
            gst.warning("Can't set durations <= 0 !")
            return
        self._setMediaStartDurationTime(start, duration)
        if self.linked and isinstance(self.linked, TimelineFileSource):
            self.linked._setMediaStartDurationTime(start, duration)

    def _mediaStartDurationChangedCb(self, gnlobject, property):
        gst.log("%s %s" % (property, property.name))
        mstart = None
        mduration = None
        if property.name == "media-start":
            mstart = gnlobject.get_property("media-start")
            gst.log("%s %s" % (gst.TIME_ARGS(mstart),
                               gst.TIME_ARGS(self.media_start)))
            if self.media_start == -1:
                self.media_start = mstart
            elif mstart == self.media_start:
                mstart = None
            else:
                self.media_start = mstart
        elif property.name == "media-duration":
            mduration = gnlobject.get_property("media-duration")
            gst.log("%s %s" % (gst.TIME_ARGS(mduration),
                               gst.TIME_ARGS(self.media_duration)))
            if mduration == self.media_duration:
                mduration = None
            else:
                self.media_duration = mduration
        if not mstart == None or not mduration == None:
            self.emit("media-start-duration-changed",
                      self.media_start, self.media_duration)

    def getExportSettings(self):
        return self.factory.getExportSettings()

    # Serializable methods

    def toDataFormat(self):
        ret = TimelineSource.toDataFormat(self)
        ret["media-start"] = self.media_start
        ret["media-duration"] = self.media_duration
        if self.media_type == MEDIA_TYPE_AUDIO and hasattr(self, "volumeElement"):
            ret["volume"] = self.volumeElement.get_property("volume")
        return ret

    def fromDataFormat(self, obj):
        TimelineSource.fromDataFormat(self, obj)
        self.media_start = obj["media-start"]
        self.media_duration = obj["media-duration"]
        if "volume" in obj:
            volume = obj["volume"]
            self.setVolume(volume)

gobject.type_register(TimelineFileSource)


class TimelineLiveSource(TimelineSource):
    """
    Non-seekable sources (like cameras)
    """

    __data_type__ = "timeline-live-source"

    def __init__(self, **kw):
        TimelineSource.__init__(self, **kw)
