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

    def __init__(self, **kw):
        TimelineObject.__init__(self, **kw)


class TimelineFileSource(TimelineSource):
    """
    Seekable sources (mostly files)
    """
    __gsignals__ = {
        "media-start-duration-changed" : ( gobject.SIGNAL_RUN_LAST,
                                       gobject.TYPE_NONE,
                                       (gobject.TYPE_UINT64, gobject.TYPE_UINT64))
        }

    media_start = -1
    media_duration = -1

    def __init__(self, media_start=-1, media_duration=-1, **kw):
        TimelineSource.__init__(self, **kw)
        self.gnlobject.connect("notify::media-start", self._mediaStartDurationChangedCb)
        self.gnlobject.connect("notify::media-duration", self._mediaStartDurationChangedCb)
        if media_start == -1:
            media_start = 0
        if media_duration == -1:
            media_duration = self.factory.length
        self.setMediaStartDurationTime(media_start, media_duration)

    def _makeGnlObject(self):
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
        decodebin = SingleDecodeBin(caps=caps, uri=self.factory.name)
        gnlobject.add(decodebin)
##         gnlobject.set_property("location", self.factory.name)
        gnlobject.set_property("caps", caps)
        gnlobject.set_property("start", long(0))
        gnlobject.set_property("duration", long(self.factory.length))
        return gnlobject

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
                                         media_type=MEDIA_TYPE_AUDIO, name=self.name)
        elif self.media_type == MEDIA_TYPE_AUDIO:
            if not self.factory.is_video:
                return None
            brother = TimelineFileSource(media_start=self.media_start, media_duration=self.media_duration,
                                         factory=self.factory, start=self.start, duration=self.duration,
                                         media_type=MEDIA_TYPE_VIDEO, name=self.name)
        else:
            brother = None
        return brother

    def _setMediaStartDurationTime(self, start=-1, duration=-1):
        gst.info("TimelineFileSource start:%d , duration:%d" % (start, duration))
        if not duration == -1 and not self.media_duration == duration:
            self.media_duration = duration
            self.gnlobject.set_property("media-duration", long(duration))
        if not start == -1 and not self.media_start == start:
            self.media_start = start
            self.gnlobject.set_property("media-start", long(start))

    def setMediaStartDurationTime(self, start=-1, duration=-1):
        """ sets the media start/duration time """
        self._setMediaStartDurationTime(start, duration)
        if self.linked and isinstance(self.linked, TimelineFileSource):
            self.linked._setMediaStartDurationTime(start, duration)

    def _mediaStartDurationChangedCb(self, gnlobject, property):
        mstart = None
        mduration = None
        if property.name == "media-start":
            mstart = gnlobject.get_property("media-start")
            if mstart == self.media_start:
                mstart = None
            else:
                self.media_start = mstart
        elif property.name == "media-duration":
            mduration = gnlobject.get_property("media-duration")
            if mduration == self.media_duration:
                mduration = None
            else:
                self.media_duration = mduration
        if mstart or mduration:
            self.emit("media-start-duration-changed",
                      self.media_start, self.media_duration)

    def getExportSettings(self):
        return self.factory.getExportSettings()


class TimelineLiveSource(TimelineSource):
    """
    Non-seekable sources (like cameras)
    """

    def __init__(self, **kw):
        TimelineSource.__init__(self, **kw)
