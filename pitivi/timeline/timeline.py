# PiTiVi , Non-linear video editor
#
#       pitivi/timeline.py
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
Timeline and timeline objects
"""

import gobject
import gst

from pitivi.settings import ExportSettings
from composition import TimelineComposition
from objects import MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
from source import TimelineBlankSource
from pitivi.serializable import Serializable

class Timeline(gobject.GObject, Serializable):
    """
    Fully fledged timeline
    """

    __data_type__ = "timeline"

    # TODO make the compositions more versatile
    # for the time being we hardcode an audio and a video composition

    def __init__(self, project=None, **unused_kw):
        gst.log("new Timeline for project %s" % project)
        gobject.GObject.__init__(self)
        self.project = project

        if self.project:
            name = project.name
        else:
            name = "XXX"
        self.timeline = gst.Bin("timeline-" + name)
        self._fillContents()

    def _fillContents(self):
        # TODO create the initial timeline according to the project settings
        self.audiocomp = TimelineComposition(media_type = MEDIA_TYPE_AUDIO,
                                             name="audiocomp")
        self.videocomp = TimelineComposition(media_type = MEDIA_TYPE_VIDEO,
                                             name="videocomp")
        self.videocomp.linkObject(self.audiocomp)

        # add default audio/video sources
        defaultaudiosource = TimelineBlankSource(media_type=MEDIA_TYPE_AUDIO,
                                                 name="default-audio")
        self.audiocomp.setDefaultSource(defaultaudiosource)

        defaultvideosource = TimelineBlankSource(media_type=MEDIA_TYPE_VIDEO,
                                                 name="default-video")
        self.videocomp.setDefaultSource(defaultvideosource)

        self.timeline.add(self.audiocomp.gnlobject,
                          self.videocomp.gnlobject)
        self.audiocomp.gnlobject.connect("pad-added", self._newAudioPadCb)
        self.videocomp.gnlobject.connect("pad-added", self._newVideoPadCb)
        self.audiocomp.gnlobject.connect("pad-removed", self._removedAudioPadCb)
        self.videocomp.gnlobject.connect("pad-removed", self._removedVideoPadCb)

    def _newAudioPadCb(self, unused_audiocomp, pad):
        asrc = gst.GhostPad("asrc", pad)
        asrc.set_active(True)
        self.timeline.add_pad(asrc)

    def _newVideoPadCb(self, unused_videocomp, pad):
        vsrc = gst.GhostPad("vsrc", pad)
        vsrc.set_active(True)
        self.timeline.add_pad(vsrc)

    def _removedAudioPadCb(self, unused_audiocomp, unused_pad):
        self.timeline.remove_pad(self.timeline.get_pad("asrc"))

    def _removedVideoPadCb(self, unused_audiocomp, unused_pad):
        self.timeline.remove_pad(self.timeline.get_pad("vsrc"))

    def getAutoSettings(self):
        v = self.videocomp._getAutoSettings()
        a = self.audiocomp._getAutoSettings()
        if not v and not a:
            return None
        # return an ExportSettings containing the combination of
        # the autosettings from the audio and video composition.
        s = ExportSettings()
        if v:
            s.videowidth = v.videowidth
            s.videoheight = v.videoheight
            s.videorate = v.videorate
            s.videopar = v.videopar
        if a:
            s.audiochannels = a.audiochannels
            s.audiorate = a.audiorate
            s.audiodepth = a.audiodepth
        return s

    def getDuration(self):
        return max(self.audiocomp.duration, self.videocomp.duration)

    # Serializable methods

    def toDataFormat(self):
        ret = Serializable.toDataFormat(self)
        ret["compositions"] = dict((\
            (self.audiocomp.name, self.audiocomp.toDataFormat()),
            (self.videocomp.name, self.videocomp.toDataFormat())))
        return ret

    def fromDataFormat(self, obj):
        Serializable.fromDataFormat(self, obj)
        audio = obj["compositions"]["audiocomp"]
        video = obj["compositions"]["videocomp"]
        self.audiocomp.fromDataFormat(audio)
        self.videocomp.fromDataFormat(video)

