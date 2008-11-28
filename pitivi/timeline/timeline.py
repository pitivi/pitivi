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

import gst

from pitivi.settings import ExportSettings
from composition import TimelineComposition
from objects import MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
from source import TimelineBlankSource, TimelineFileSource
from pitivi.serializable import Serializable

class Timeline(Serializable):
    """
    Fully fledged timeline
    """

    __data_type__ = "timeline"

    # TODO make the compositions more versatile
    # for the time being we hardcode an audio and a video composition

    def __init__(self, project=None, **unused_kw):
        gst.log("new Timeline for project %s" % project)
        self.project = project

        if self.project:
            name = project.name
        else:
            name = "XXX"
        self.timeline = gst.Bin("timeline-" + name)
        self.audiocomp = None
        self.videocomp = None
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

    def addFactory(self, factory, time=gst.CLOCK_TIME_NONE, shift=False):
        """Add a factory to the timeline using the the specified time as the
        start time. If shift is true, then move overlapping sources out of the
        way."""

        if not factory:
            return

        #FIXME: need simple, generic, createFromFactory() type thing so we
        # have to care about all of this...
        if factory.is_video:
            video_source = TimelineFileSource(factory=factory,
                media_type=MEDIA_TYPE_VIDEO,
                name=factory.name)
            # WARNING: this won't actually catch the linked source, so if the
            # source is ever unlinked its edges will not be seen. On the other
            # hand, this won't matter once we switch to the parent-child
            # model.
            #self.register_instance(video_source)
            # TODO: insert source in proper location
            self.videocomp.appendSource(video_source)
        # must be elif because of auto-linking, this just catches case where
        # factory is only audio
        elif factory.is_audio:
            audio_source = TimelineFileSource(factory=factory,
                media_type=MEDIA_TYPE_VIDEO,
                name=factory.name)
            #self.register_instance(audio_source)
            # TODO: insert source in proper location
            self.audiocomp.appendSource(audio_source)

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
        vs = self.videocomp._getAutoSettings()
        as = self.audiocomp._getAutoSettings()
        if not vs and not as:
            return None
        # return an ExportSettings containing the combination of
        # the autosettings from the audio and video composition.
        settings = ExportSettings()
        if vs:
            settings.videowidth = vs.videowidth
            settings.videoheight = vs.videoheight
            settings.videorate = vs.videorate
            settings.videopar = vs.videopar
        if as:
            settings.audiochannels = as.audiochannels
            settings.audiorate = as.audiorate
            settings.audiodepth = as.audiodepth
        return settings

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

