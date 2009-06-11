# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/timeline_undo.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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

from pitivi.utils import PropertyChangeTracker
from pitivi.undo import UndoableAction

class TimelineObjectPropertyChangeTracker(PropertyChangeTracker):
    # no out-point
    property_names = ["start", "duration", "in-point",
            "media-duration", "priority", "selected"]

    _disabled = False

    def connectToObject(self, obj):
        PropertyChangeTracker.connectToObject(self, obj)
        self.timeline = obj.timeline
        self.timeline.connect("disable-updates", self._timelineDisableUpdatesCb)

    def disconnectFromObject(self, obj):
        self.timeline.disconnect_by_func(self._timelineDisableUpdatesCb)
        PropertyChangeTracker.disconnectFromObject(self, obj)

    def _timelineDisableUpdatesCb(self, timeline, disabled):
        if self._disabled and not disabled:
            self._disabled = disabled
            properties = self._takeCurrentSnapshot(self.obj)
            for property_name, property_value in properties.iteritems():
                old_value = self.properties[property_name]
                if old_value != property_value:
                    self._propertyChangedCb(self.obj, property_value, property_name)
        else:
            self._disabled = disabled

    def _propertyChangedCb(self, timeline_object, value, property_name):
        if not self._disabled:
            PropertyChangeTracker._propertyChangedCb(self,
                    timeline_object, value, property_name)

class TimelineObjectPropertyChanged(UndoableAction):
    def __init__(self, timeline_object, property_name, old_value, new_value):
        self.timeline_object = timeline_object
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def do(self):
        setattr(self.timeline_object,
                self.property_name.replace("-", "_"), self.new_value)
        self._done()

    def undo(self):
        setattr(self.timeline_object,
                self.property_name.replace("-", "_"), self.old_value)
        self._undone()

class TimelineObjectAdded(UndoableAction):
    def __init__(self, timeline, timeline_object):
        self.timeline = timeline
        self.timeline_object = timeline_object
        self.timeline_object_copy = self._copyTimelineObject(timeline_object)

    def do(self):
        temporary_timeline_object = \
                self._copyTimelineObject(self.timeline_object_copy)
        self.timeline_object.track_objects = []
        for track_object in temporary_timeline_object.track_objects:
            track, track_object.track = track_object.track, None
            track.addTrackObject(track_object)
            self.timeline_object.addTrackObject(track_object)

        self.timeline.addTimelineObject(self.timeline_object)
        self._done()

    def undo(self):
        self.timeline.removeTimelineObject(self.timeline_object, deep=True)
        self._undone()

    def _copyTimelineObject(self, timeline_object):
        copy = timeline_object.copy()
        for (track_object_copy, track_object) in \
                    zip(copy.track_objects, timeline_object.track_objects):
            track_object_copy.track = track_object.track

        return copy

class TimelineObjectRemoved(UndoableAction):
    def __init__(self, timeline, timeline_object):
        self.timeline = timeline
        self.timeline_object = timeline_object
        self.timeline_object_copy = self._copyTimelineObject(timeline_object)

    def do(self):
        self.timeline.removeTimelineObject(self.timeline_object, deep=True)
        self._done()

    def undo(self):
        temporary_timeline_object = \
                self._copyTimelineObject(self.timeline_object_copy)
        for track_object in temporary_timeline_object.track_objects:
            track, track_object.track = track_object.track, None
            track.addTrackObject(track_object)

        self.timeline_object.track_objects = temporary_timeline_object.track_objects
        self.timeline.addTimelineObject(self.timeline_object)
        self._undone()

    def _copyTimelineObject(self, timeline_object):
        copy = timeline_object.copy()
        for (track_object_copy, track_object) in \
                    zip(copy.track_objects, timeline_object.track_objects):
            track_object_copy.track = track_object.track

        return copy

class TimelineLogObserver(object):
    propertyChangedAction = TimelineObjectPropertyChanged
    timelineObjectAddedAction = TimelineObjectAdded
    timelineObjectRemovedAction = TimelineObjectRemoved

    def __init__(self, log):
        self.log = log
        self.property_trackers = {}

    def startObserving(self, timeline):
        self._connectToTimeline(timeline)
        for timeline_object in timeline.timeline_objects:
            self._connectToTimelineObject(timeline_object)

    def stopObserving(self, timeline):
        self._disconnectFromTimeline(timeline)
        for timeline_object in timeline.timeline_objects:
            self._disconnectFromTimelineObject(timeline_object)

    def _connectToTimeline(self, timeline):
        timeline.connect("timeline-object-added", self._timelineObjectAddedCb)
        timeline.connect("timeline-object-removed", self._timelineObjectRemovedCb)

    def _disconnectFromTimeline(self, timeline):
        timeline.disconnect_by_func(self._timelineObjectAddedCb)
        timeline.disconnect_by_func(self._timelineObjectRemovedCb)

    def _connectToTimelineObject(self, timeline_object):
        tracker = TimelineObjectPropertyChangeTracker()
        tracker.connectToObject(timeline_object)
        for property_name in tracker.property_names:
            tracker.connect(property_name + "-changed",
                    self._timelineObjectPropertyChangedCb, property_name)
        self.property_trackers[timeline_object] = tracker

    def _disconnectFromTimelineObject(self, timeline_object):
        tracker = self.property_trackers.pop(timeline_object)
        tracker.disconnectFromObject(timeline_object)
        tracker.disconnect_by_func(self._timelineObjectPropertyChangedCb)

    def _timelineObjectAddedCb(self, timeline, timeline_object):
        self._connectToTimelineObject(timeline_object)
        action = self.timelineObjectAddedAction(timeline, timeline_object)
        self.log.push(action)

    def _timelineObjectRemovedCb(self, timeline, timeline_object):
        self._disconnectFromTimelineObject(timeline_object)
        action = self.timelineObjectRemovedAction(timeline, timeline_object)
        self.log.push(action)

    def _timelineObjectPropertyChangedCb(self, tracker, timeline_object,
            old_value, new_value, property_name):
        action = self.propertyChangedAction(timeline_object,
                property_name, old_value, new_value)
        self.log.push(action)
