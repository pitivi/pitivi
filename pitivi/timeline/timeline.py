# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/timeline.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

#(05:43:09 PM) twi_: a timeline object can span multiple tracks
#(05:43:14 PM) twi_: say you group a/v
#(05:43:22 PM) twi_: can you do that?
#(05:43:58 PM) twi_: or you can only group contiguous objects in the same track?
#(05:44:50 PM) bilboed-tp: since we don't have any 'duplicates' in the Timeline, when you group TimelineObjects, you end up in each track with groups containing the corresponding TrackObjects of the grouped TimelineObjects
#(05:45:27 PM) twi_: aha, right
#(05:45:59 PM) bilboed-tp: for ex : say you group 5 TimelineObjects, of which only 3 have both A/V and the others only A, then you would end up with the audio group containing 5 TrackObjects, and the video group containing only 3 TrackObjects
#(05:47:24 PM) twi_: but then how do you make the two groups be a single group?
#(05:48:13 PM) bilboed-tp: because you created a new TimelineObject for the group (at the Timeline level) and a TrackObject for the corresponding gorup in each Track
#(05:48:26 PM) bilboed-tp: ergo... you keep the TimelineObject => TrackObject(s) relationship
#(05:48:28 PM) twi_: right, so you're left with only one group (timelineobject) in the timeline
#(05:48:31 PM) bilboed-tp: it's a single group in the Timeline
#(05:48:32 PM) twi_: not two
#(05:48:38 PM) bilboed-tp: correct
#(05:48:59 PM) twi_: so it does span two tracks
#(05:49:03 PM) twi_: (or more)
#(05:49:06 PM) bilboed-tp: yes
#(05:49:24 PM) twi_: ok
#(05:49:38 PM) bilboed-tp: in the same way that a FileTimelineObject can have FileTrackObjects in many Tracks
#(05:50:11 PM) bilboed-tp: there's a lot of hierarchy similitude between ObjectFactory, TimelineObject and TrackObject
#(05:50:49 PM) bilboed-tp: damn, still haven't updated the wiki with the new stuff we talked about
#(05:51:30 PM) twi_: so for example timelineobject.tracks is a synthesized property, and is [trackObject.track for trackObject in self.track_objects]
#(05:51:44 PM) bilboed-tp: yep
#(05:52:01 PM) twi_: ok
#(05:53:53 PM) bilboed-tp: erf... I hate gstreamer
#(05:54:11 PM) bilboed-tp: I finally figured out what thomas's problem is with gnloperation
#(05:54:24 PM) bilboed-tp: hmm.. maybe not
#(05:54:48 PM) twi_: i see a principle of madness in your words
#(05:55:46 PM) twi_: gah there's always something left to define
#(05:55:47 PM) twi_: like
#(05:55:58 PM) twi_: what if you have three or more tracks in the timeline
#(05:56:12 PM) twi_: and you drop a factory with 1 audio and 1 video streams
#(05:56:20 PM) twi_: where do the streams go?
#(05:56:32 PM) twi_: one goes in the track you dragged onto
#(05:56:33 PM) twi_: the other?
#(05:56:43 PM) bilboed-tp: that requires user interactoin
#(05:57:09 PM) twi_: ok, so i'm going to leave this as something for the ui
#(05:57:11 PM) twi_: good
#(05:57:13 PM) bilboed-tp: or make a *smart* choice for him => stick it in the first Track compatible with the other stream
#(05:57:15 PM) bilboed-tp: yeah, definitely
#(05:58:36 PM) twi_: then the program flow to add an object t o the timeline can be summed up like this: you drag something (let's assume 1 stream only for now) in a track; a TrackObject is created; a TimelineObject is created that encapsulates the TrackObject; the TimelineObject is added to the timeline
#(05:58:43 PM) twi_: sounds ok?
#(06:00:04 PM) jdm [i=cf3dcfc4@gateway/web/ajax/mibbit.com/x-41c08c5025b40fe7] entered the room.
#(06:00:36 PM) bilboed-tp: that's if you know a specific track you want to target, but we mustn't forget the possibility that the ui might not care (for some reason or another) about which track it lands into and just asks the Timeline to add the given objectfactory
#(06:01:35 PM) bilboed-tp: in which case, it would be : add objectfactory to timeline, Timeline figures out compatible Streams/Tracks, creates relevant TrackObject, puts them in corresponding Tracks, Creates TimelineObject, links TrackObjects to TimelineObject, adds TimelineObject to Timeline
#(06:01:49 PM) twi_: alright
#(06:02:15 PM) bilboed-tp: that smartness (figuring out in which tracks to put which trackobjects) is definitely in core and not the UI
#(06:02:56 PM) twi_: i was looking at it from the other perspective, ie that that level of "sloppyness" is better left to higher layers
#(06:03:05 PM) twi_: but given that the common case is not to care
#(06:03:08 PM) twi_: at least for normal users
#(06:03:10 PM) twi_: you're probably right

import gst
import weakref

from pitivi.signalinterface import Signallable

class TimelineError(Exception):
    pass

class TimelineObject(Signallable):
    def __init__(self, factory, start=0,
            duration=gst.CLOCK_TIME_NONE, in_point=gst.CLOCK_TIME_NONE,
            out_point=gst.CLOCK_TIME_NONE, priority=0):
        self.factory = factory
        self.start = start
        self.duration = duration
        self.in_point = in_point
        self.out_point = out_point
        self.priority = priority
        self.track_objects = []

    def addTrackObject(self, obj):
        if obj.track is None or obj.timeline_object is not None:
            raise TimelineError()

        if obj in self.track_objects:
            raise TimelineError()

        obj.timeline_object = weakref.proxy(self)
        self.track_objects.append(obj)

    def removeTrackObject(self, obj):
        if obj.track is None:
            raise TimelineError()

        try:
            self.track_objects.remove(obj)
            obj.timeline_object = None
        except ValueError:
            raise TimelineError()


class Selection(object):
    def __init__(self):
        self.timeline_objects = set([])

    def addTimelineObject(self, timeline_object):
        if timeline_object in self.timeline_objects:
            raise TimelineError()

        self.timeline_objects.add(timeline_object)

    def removeTimelineObject(self, timeline_object):
        try:
            self.timeline_objects.remove(timeline_object)
        except KeyError:
            raise TimelineError()

class Link(Selection):
    def __init__(self):
        Selection.__init__(self)
        self.objects_start_duration = {}
        self.waiting_update = []

    def addTimelineObject(self, timeline_object):
        Selection.addTimelineObject(self, timeline_object)

        # get the initial start and duration
        self.objects_start_duration[timeline_object] = \
            {'start': timeline_object.start,
             'duration': timeline_object.duration}

        # keep start and duration up to date with signals
        timeline_object.connect('start-changed', self._startChangedCb)
        timeline_object.connect('duration-changed', self._durationChangedCb)

    def removeTimelineObject(self, timeline_object):
        Selection.removeTimelineObject(timeline_object)

        del self.objects_start_duration[timeline_object]

    def _startChangedCb(self, timeline_object, start):
        if not self.waiting_update:
            old_start = self.objects_start_duration[timeline_object]['start']
            delta = start - old_start

            self.waiting_update = self.timeline_objects
            for linked_object in self.waiting_update:
                linked_object.start += delta

            assert not self.waiting_notification

        self.waiting_notification.remove(timeline_object)
        self.objects_start_duration[timeline_object]['start'] = start

    def _durationChangedCb(self, timeline_object, duration):
        self.objects_start_duration[timeline_object]['duration'] = duration

class Timeline(Signallable):
    def __init__(self):
        self.tracks = []
        self.selections = []
        self.timeline_objects = []

    def addTrack(self, track):
        if track in self.tracks:
            raise TimelineError()

        self.tracks.append(track)

    def removeTrack(self, track):
        try:
            self.tracks.remove(track)
        except ValueError:
            raise TimelineError()

    def addTimelineObject(self, obj):
        if obj in self.timeline_objects:
            raise TimelineError()

        if not obj.track_objects:
            raise TimelineError()

        self.timeline_objects.append(obj)

    def removeTimelineObject(self, obj):
        try:
            self.timeline_objects.remove(obj)
        except ValueError:
            raise TimelineError()

    def linkObjects(self, *objects):
        pass

    def unlinkObjects(self, *objects):
        pass

    def groupObjects(self, *objects):
        pass

    def ungroupObjects(self, *objects):
        pass

    def addSelection(self, selection):
        pass

    def removeSelection(self, selection):
        pass


