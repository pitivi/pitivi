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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import goocanvas
import ges
import gobject

from pitivi.log.loggable import Loggable
from pitivi.ui.zoominterface import Zoomable
from pitivi.receiver import receiver, handler
from pitivi.ui.trackobject import TrackObject
from pitivi.ui.common import LAYER_HEIGHT_EXPANDED,\
        LAYER_HEIGHT_COLLAPSED, LAYER_SPACING


class Transition(goocanvas.Rect, Zoomable):

    def __init__(self, transition):
        goocanvas.Rect.__init__(self)
        Zoomable.__init__(self)
        self.props.fill_color_rgba = 0xFFFFFF99
        self.props.stroke_color_rgba = 0x00000099
        self.set_simple_transform(0, - LAYER_SPACING + 3, 1.0, 0)
        self.props.height = LAYER_SPACING - 6
        self.props.pointer_events = goocanvas.EVENTS_NONE
        self.props.radius_x = 2
        self.props.radius_y = 2
        self.transition = transition

    def _setTransition(self):
        if self.transition:
            self._updateAll()

    def _updateAll(self):
        transition = self.transition
        start = transition.get_start()
        duration = transition.get_duration()
        priority = transition.get_priority()
        self._updateStart(transition, start)
        self._updateDuration(transition, duration)
        self._updatePriority(transition, priority)

    transition = receiver(_setTransition)

    @handler(transition, "notify::start")
    def _updateStart(self, transition, start):
        self.props.x = self.nsToPixel(start)

    @handler(transition, "notify::duration")
    def _updateDuration(self, transition, duration):
        width = max(0, self.nsToPixel(duration))
        if width == 0:
            self.props.visibility = goocanvas.ITEM_INVISIBLE
        else:
            self.props.visibility = goocanvas.ITEM_VISIBLE
        self.props.width = width

    @handler(transition, "notify::priority")
    def _updatePriority(self, transition, priority):
        self.props.y = (LAYER_HEIGHT_EXPANDED + LAYER_SPACING) * transition.get_priority()

    def zoomChanged(self):
        self._updateAll()


class Track(goocanvas.Group, Zoomable, Loggable):
    __gtype_name__ = 'Track'

    def __init__(self, instance, track, timeline=None):
        goocanvas.Group.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.app = instance
        self.widgets = {}
        self.transitions = []
        self.timeline = timeline
        self.track = track
        self._expanded = True

## Properties

    def setExpanded(self, expanded):
        if expanded != self._expanded:
            self._expanded = expanded

            for widget in self.widgets.itervalues():
                widget.expanded = expanded
            self.get_canvas().regroupTracks()

    def getHeight(self):
        # FIXME we have a refcount issue somewhere, the following makes sure
        # no to crash because of it
        #track_objects = self.track.get_objects()
        if self._expanded:
            nb_layers = len(self.timeline.get_layers())

            return  nb_layers * (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)
        else:
            return LAYER_HEIGHT_COLLAPSED + LAYER_SPACING

    height = property(getHeight)

## Public API

## track signals

    def _setTrack(self):
        self.debug("Setting track")
        if self.track:
            for trackobj in self.track.get_objects():
                self._objectAdded(None, trackobj)

    track = receiver(_setTrack)

    @handler(track, "track-object-added")
    def _objectAdded(self, unused_timeline, track_object):
        if isinstance(track_object, ges.TrackTransition):
            self._transitionAdded(track_object)
        elif not isinstance(track_object, ges.TrackEffect):
            #FIXME GES hack, waiting for the discoverer to do its job
            # so the duration properies are set properly
            gobject.timeout_add(1, self.check, track_object)

    def check(self, tr_obj):
        if tr_obj.get_timeline_object():
            w = TrackObject(self.app, tr_obj, self.track, self.timeline, self)
            self.widgets[tr_obj] = w
            self.add_child(w)
            self.app.gui.setBestZoomRatio()

    @handler(track, "track-object-removed")
    def _objectRemoved(self, unused_timeline, track_object):
        if isinstance(track_object, ges.TrackVideoTestSource) or \
            isinstance(track_object, ges.TrackAudioTestSource) or \
            isinstance(track_object, ges.TrackParseLaunchEffect):
            return
        w = self.widgets[track_object]
        self.remove_child(w)
        del self.widgets[track_object]
        Zoomable.removeInstance(w)

    def _transitionAdded(self, transition):
        w = TrackObject(self.app, transition, self.track, self.timeline, self, True)
        self.widgets[transition] = w
        self.add_child(w)
        self.transitions.append(w)
        w.raise_(None)
