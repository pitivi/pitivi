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
from pitivi.utils import closest_item

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
        self.__selection = set()
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

        # we need to keep track of every object added to the timeline
        self.__instances = []
        self.videocomp.connect("source-added", self._sourceAddedCb)
        self.videocomp.connect("source-removed", self._sourceRemovedCb)

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
            self.videocomp.appendSource(video_source)
        # must be elif because of auto-linking, this just catches case where
        # factory is only audio
        elif factory.is_audio:
            audio_source = TimelineFileSource(factory=factory,
                media_type=MEDIA_TYPE_VIDEO,
                name=factory.name)
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

## code for managing the selection

    __selection = None

    def setSelectionTo(self, objs, mode=0):
        if mode == 1:
            objs |= self.__selection
        if mode == 2:
            objs ^= self.__selection

        for obj in self.__selection:
            obj.selected = False
        for obj in objs:
            obj.selected = True
        self.__selection = objs

    def setSelectionToObj(self, obj, mode=0):
        #TODO: range selection
        # sort all objects by increasing (start, end)
        # choose the slice from [last(selection) : obj]
        # or [obj: first(selection]
        self.setSelectionTo(set((obj,)), mode)

    def deleteSelection(self):
        for obj in self.__selection:
            if obj.isaudio:
                self.audiocomp.removeSource(obj, remove_linked=True,
                    collapse_neighbours=False)
            else:
                self.videocomp.removeSource(obj, remove_linked=True,
                    collapse_neighbours=False)
        self.__selection = set()

    def unlinkSelection(self):
        for obj in self.__selection:
            if obj.linked:
                obj.unlinkObject()

    def relinkSelection(self):
        for obj in self.__selection:
            if not obj.linked:
                obj.relinkBrother()

    def selectBefore(self):
        pass

    def selectAfter(self):
        pass

## code for keeping track of edit points, and snapping timestamps to the
## nearest edit point. We do this here so we can keep track of edit points
## for all layers/tracks.

    __instances = None
    __deadband = 0
    __do_updates = True
    __edges = None

    def _sourceAddedCb(self, composition, inst):
        self.__instances.append(inst)
        self.updateEdges()

    def _sourceRemovedCb(self, composition, inst):
        assert inst in self.__instances
        self.__instances.remove(inst)
        self.updateEdges()

    def setDeadband(self, db):
        self.__deadband = db

    def enableEdgeUpdates(self):
        self.__do_updates = True
        self.updateEdges()

    def disableEdgeUpdates(self):
        self.__do_updates = False

    def updateEdges(self):
        if not self.__do_updates:
            return
        #FIXME: this might be more efficient if we used a binary sort tree,
        # filter out duplicate edges in linear time
        edges = {}
        for obj in self.__instances:
            # start/end of object both considered "edit points"
            edges[obj.start] = None
            edges[obj.start + obj.duration] = None
            # TODO: add other critical object points when these are
            # implemented
            # TODO: filtering mechanism
        self.__edges = edges.keys()
        self.__edges.sort()

    def snapTimeToEdge(self, time):
        """Returns the input time or the nearest edge"""
        res, diff = closest_item(self.__edges, time)
        if diff <= self.__deadband:
            return res
        return time

    def snapObjToEdge(self, obj, time):
        """Returns the input time or the edge which is closest to either the
        start or finish time. The input time is interpreted as the start time
        of obj."""

        # need to find the closest edge to both the left and right sides of
        # the object we are draging.
        duration = obj.duration
        left_res, left_diff = closest_item(self.__edges, time)
        right_res, right_diff = closest_item(self.__edges, time + duration)
        if left_diff <= right_diff:
            res = left_res
            diff = left_diff
        else:
            res = right_res - duration
            diff = right_diff
        if diff <= self.__deadband:
            return res
        return time

## Serializable interfacemethods

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

