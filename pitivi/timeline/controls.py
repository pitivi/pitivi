# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/timeline/controls.py
#
# Copyright (c) 2013, Mathieu Duponchelle <mduponchelle1@gmail.com>
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

from gi.repository import Clutter
from gi.repository import GObject
from gi.repository import GtkClutter

from pitivi.timeline.layer import VideoLayerControl, AudioLayerControl
from pitivi.utils.ui import EXPANDED_SIZE, SPACING, CONTROL_WIDTH


class ControlActor(GtkClutter.Actor):

    def __init__(self, container, widget, layer, is_audio):
        GtkClutter.Actor.__init__(self)

        self.layer = layer
        self.is_audio = is_audio
        self._container = container
        self.widget = widget

        self.get_widget().add(widget)
        self.set_reactive(True)
        self._setUpDragAndDrop()

    def _getLayerForY(self, y):
        if self.is_audio:
            y -= self.nbrLayers * (EXPANDED_SIZE + SPACING)
        priority = int(y / (EXPANDED_SIZE + SPACING))

        return priority

    def _setUpDragAndDrop(self):
        self.dragAction = Clutter.DragAction()
        self.add_action(self.dragAction)

        self.dragAction.connect("drag-begin", self._dragBeginCb)
        self.dragAction.connect("drag-progress", self._dragProgressCb)
        self.dragAction.connect("drag-end", self._dragEndCb)

    def _dragBeginCb(self, unused_action, unused_actor, event_x, unused_event_y, unused_modifiers):
        self.brother = self._container.getBrotherControl(self)

        self.brother.raise_top()
        self.raise_top()

        self.nbrLayers = len(self._container.timeline.bTimeline.get_layers())
        self._dragBeginStartX = event_x

    def _dragProgressCb(self, unused_action, actor, unused_delta_x, delta_y):
        y = self.dragAction.get_motion_coords()[1]
        priority = self._getLayerForY(y)
        lowerLimit = 0
        if self.is_audio:
            lowerLimit = self.nbrLayers * (EXPANDED_SIZE + SPACING)

        if actor.props.y + delta_y > lowerLimit and priority < self.nbrLayers:
            actor.move_by(0, delta_y)
            self.brother.move_by(0, delta_y)

        if self.layer.get_priority() != priority and priority >= 0 and priority < self.nbrLayers:
            self._container.moveLayer(self, priority)
        return False

    def _dragEndCb(self, unused_action, unused_actor, unused_event_x, event_y, unused_modifiers):
        priority = self._getLayerForY(event_y)

        if self.layer.get_priority() != priority and priority >= 0 and priority < self.nbrLayers:
            self._container.moveLayer(self, priority)
        self._container._reorderLayerActors()


class ControlContainer(Clutter.ScrollActor):
    __gsignals__ = {
        "selection-changed": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,),)
    }

    def __init__(self, app, timeline):
        Clutter.ScrollActor.__init__(self)

        self._app = app
        self.timeline = timeline
        self.controlActors = []
        self.trackControls = []

    def _setTrackControlPosition(self, control):
        y = control.layer.get_priority() * (EXPANDED_SIZE + SPACING) + SPACING
        if control.is_audio:
            y += len(self.timeline.bTimeline.get_layers()) * \
                (EXPANDED_SIZE + SPACING)

        control.set_position(0, y)

    def _reorderLayerActors(self):
        for control in self.controlActors:
            control.save_easing_state()
            control.set_easing_mode(Clutter.AnimationMode.EASE_OUT_BACK)
            self._setTrackControlPosition(control)
            control.restore_easing_state()

    def getBrotherControl(self, control):
        for cont in self.controlActors:
            if cont != control and cont.layer == control.layer:
                return cont

    def moveLayer(self, control, target):
        movedLayer = control.layer
        priority = movedLayer.get_priority()

        # Don't put 1000 layers or this breaks !
        movedLayer.props.priority = 999

        if priority > target:
            for layer in self.timeline.bTimeline.get_layers():
                prio = layer.get_priority()
                if target <= prio < priority:  # Python idiom, is that bad ?
                    layer.props.priority = prio + 1
        elif priority < target:
            for layer in self.timeline.bTimeline.get_layers():
                prio = layer.get_priority()
                if priority < prio <= target:
                    layer.props.priority = prio - 1

        movedLayer.props.priority = target

        self._reorderLayerActors()
        self.timeline.bTimeline.get_asset().pipeline.commit_timeline()

    def addTrackControl(self, layer, is_audio):
        if is_audio:
            control = AudioLayerControl(self, layer, self._app)
        else:
            control = VideoLayerControl(self, layer, self._app)

        controlActor = ControlActor(self, control, layer, is_audio)
        controlActor.set_size(CONTROL_WIDTH, EXPANDED_SIZE + SPACING)

        self.add_child(controlActor)
        self.trackControls.append(control)
        self.controlActors.append(controlActor)

    def selectLayerControl(self, layer_control):
        for control in self.trackControls:
            control.selected = False
        layer_control.selected = True
        self.props.height += (EXPANDED_SIZE + SPACING) * 2 + SPACING

    def addLayerControl(self, layer):
        self.addTrackControl(layer, False)
        self.addTrackControl(layer, True)
        self._reorderLayerActors()

    def removeLayerControl(self, layer):
        for control in self.controlActors:
            if control.layer == layer:
                self.remove_child(control)
                self.trackControls.remove(control.widget)

        self.controlActors = [
            elem for elem in self.controlActors if elem.layer != layer]
        self._reorderLayerActors()
