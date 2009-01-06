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
from pitivi.utils import UNKNOWN_DURATION

class TimelineError(Exception):
    pass

class TimelineObject(Signallable):
    __signals__ = {
        'start-changed': ['start'],
        'duration-changed': ['duration'],
        'in-point-changed': ['in-point'],
        'out-point-changed': ['out-point']
    }

    DEFAULT_START = 0
    DEFAULT_DURATION = UNKNOWN_DURATION
    DEFAULT_IN_POINT = 0
    DEFAULT_OUT_POINT = UNKNOWN_DURATION

    def __init__(self, factory):
        self.factory = factory
        self.track_objects = []
        self._master_track_object = None
        self._start_duration_changed_sig_id = None
        self._duration_changed_sig_id = None
    
    def _getStart(self):
        if self._master_track_object is None:
            return self.DEFAULT_START

        return self._master_track_object.start
    
    def _setStart(self, value):
        if self._master_track_object is None:
            raise TimelineError()

        self._master_track_object.start = value

    start = property(_getStart, _setStart)

    def _getDuration(self):
        if self._master_track_object is None:
            return self.DEFAULT_DURATION
        
        return self._master_track_object.duration
    
    def _setDuration(self, value):
        if self._master_track_object is None:
            raise TimelineError()
        
        self._master_track_object.duration = value
    
    duration = property(_getDuration, _setDuration)

    def _getInPoint(self):
        if self._master_track_object is None:
            return self.DEFAULT_IN_POINT
        
        return self._master_track_object.in_point
    
    def _setInPoint(self, value):
        if self._master_track_object is None:
            raise TimelineError()
        self._master_track_object.in_point = value
    
    in_point = property(_getInPoint, _setInPoint)

    def _getOutPoint(self):
        if self._master_track_object is None:
            return self.DEFAULT_OUT_POINT
        
        return self._master_track_object.out_point
    
    def _setOutPoint(self, value):
        if self._master_track_object is None:
            raise TimelineError()
        
        self._master_track_object.out_point = value

    out_point = property(_getOutPoint, _setOutPoint)

    def addTrackObject(self, obj):
        if obj.track is None or obj.timeline_object is not None:
            raise TimelineError()

        if obj in self.track_objects:
            raise TimelineError()

        if self.track_objects:
            # multiple track objects are used for groups.
            # For example if you have the timeline:
            #
            # |sourceA|gap|sourceB|
            # | sourceC |gap
            #
            # If you group A B and C the group will create two gnl compositions,
            # one [A, B] with start A.start and duration B.duration and another
            # [C] with start C.start and duration B.duration (with silence used
            # as padding).
            # The compositions will always be aligned with the same start and
            # duration.
            existing_track_object = self.track_objects[0]
            if obj.start != existing_track_object.start or \
                    obj.duration != existing_track_object.duration:
                raise TimelineError()

        obj.timeline_object = weakref.proxy(self)
        self.track_objects.append(obj)

        if self._master_track_object == None:
            self._setMasterTrackObject(obj)

    def removeTrackObject(self, obj):
        if obj.track is None:
            raise TimelineError()

        try:
            self.track_objects.remove(obj)
            obj.timeline_object = None
        except ValueError:
            raise TimelineError()

        if obj is self._master_track_object:
            self._unsetMasterTrackObject()
            
            if self.track_objects:
                self._setMasterTrackObject(self.track_objects[0])

    def _setMasterTrackObject(self, obj):
        self._master_track_object = obj
        self._start_changed_sig_id = \
                obj.connect('start-changed', self._startChangedCb)
        self._duration_changed_sig_id = \
                obj.connect('duration-changed', self._durationChangedCb)
        self._in_point_changed_sig_id = \
                obj.connect('in-point-changed', self._inPointChangedCb)
        self._out_point_changed_sig_id = \
                obj.connect('out-point-changed', self._outPointChangedCb)

    def _unsetMasterTrackObject(self):
        obj = self._master_track_object
        self._master_track_object = None

        obj.disconnect(self._start_changed_sig_id)
        obj.disconnect(self._duration_changed_sig_id)

    def _startChangedCb(self, track_object, start):
        self.emit('start-changed', start)

    def _durationChangedCb(self, track_object, duration):
        self.emit('duration-changed', duration)

    def _inPointChangedCb(self, track_object, in_point):
        self.emit('in-point-changed', in_point)
    
    def _outPointChangedCb(self, track_object, out_point):
        self.emit('out-point-changed', out_point)

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

class LinkEntry(object):
    def __init__(self, start, duration,
            start_changed_sig_id, duration_changed_sig_id):
        self.start = start
        self.duration = duration
        self.start_changed_sig_id = start_changed_sig_id
        self.duration_changed_sig_id = duration_changed_sig_id

class Link(Selection):
    def __init__(self):
        Selection.__init__(self)
        self.link_entries = {}
        self.waiting_update = []

    def addTimelineObject(self, timeline_object):
        Selection.addTimelineObject(self, timeline_object)

        # connect to signals to update link entries
        start_changed_sig_id = timeline_object.connect('start-changed',
                self._startChangedCb)
        duration_changed_sig_id = timeline_object.connect('duration-changed',
                self._durationChangedCb)

        # create a link entry, saving the initial start and duration
        link_entry = LinkEntry(timeline_object.start, timeline_object.duration,
                start_changed_sig_id, duration_changed_sig_id)

        self.link_entries[timeline_object] = link_entry

    def removeTimelineObject(self, timeline_object):
        Selection.removeTimelineObject(self, timeline_object)

        # remove link entry
        link_entry = self.link_entries[timeline_object]
        timeline_object.disconnect(link_entry.start_changed_sig_id)
        timeline_object.disconnect(link_entry.duration_changed_sig_id)

    def _startChangedCb(self, timeline_object, start):
        link_entry = self.link_entries[timeline_object]
        
        if not self.waiting_update:
            old_start = link_entry.start
            delta = start - old_start

            self.waiting_update = list(self.timeline_objects)
            # we aren't waiting
            self.waiting_update.remove(timeline_object)
            for linked_object in list(self.waiting_update):
                # this will trigger signals that modify self.waiting_update so
                # we iterate over a copy
                linked_object.start += delta

            assert not self.waiting_update
        else:
            self.waiting_update.remove(timeline_object)
        
        link_entry.start = start

    def _durationChangedCb(self, timeline_object, duration):
        link_entry = self.link_entries[timeline_object]
        link_entry.duration = duration

class Timeline(Signallable):
    def __init__(self):
        self.tracks = []
        self.selections = []
        self.timeline_objects = []

    def addTrack(self, track):
        if track in self.tracks:
            raise TimelineError()

        self.tracks.append(track)

    def removeTrack(self, track, removeTrackObjects=True):
        try:
            self.tracks.remove(track)
        except ValueError:
            raise TimelineError()

        if removeTrackObjects:
            track.removeAllTrackObjects()

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

    def groupObjects(self, *objects):
        pass

    def ungroupObjects(self, *objects):
        pass

    def addSelection(self, selection):
        pass

    def removeSelection(self, selection):
        pass


