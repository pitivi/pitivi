# Pitivi video editor
#
#       pitivi/utils/validate.py
#
# Copyright (c) 2014, Thibault Saunier <thibault.saunier@collabora.com>
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
import sys

from gi.repository import Gst
from gi.repository import GES
from gi.repository import Gdk
from gi.repository import GLib

from pitivi.utils import ui
from pitivi.utils import timeline as timelineUtils

try:
    from gi.repository import GstValidate
except ImportError:
    GstValidate = None

has_validate = False


def stop(scenario, action):
    if action.structure.get_boolean("force")[0]:
        timeline = scenario.pipeline.props.timeline
        project = timeline.get_asset()

        if project:
            project.setModificationState(False)
            GstValidate.print_action(action, "Force quiting, ignoring any"
                                     " changes in the project")
        timeline.ui.app.shutdown()

        return 1

    GstValidate.print_action(action, "not doing anything in pitivi")

    return 1


def editContainer(scenario, action):
    # edit-container, edge=(string)edge_end, position=(double)2.2340325289999998, edit-mode=(string)edit_trim, container-name=(string)uriclip0, new-layer-priority=(int)-1;
    timeline = scenario.pipeline.props.timeline
    container = timeline.get_element(action.structure["container-name"])

    try:
        res, edge = GstValidate.utils_enum_from_str(GES.Edge, action.structure["edge"])
        if not res:
            edge = GES.Edge.EDGE_NONE
        else:
            edge = GES.Edge(edge)
    except KeyError:
        edge = GES.Edge.EDGE_NONE

    res, position = GstValidate.action_get_clocktime(scenario, action, "position")
    layer_prio = action.structure["new-layer-priority"]

    if res is False:
        return 0

    container_ui = container.ui

    y = 21
    if container.get_layer().get_priority() != layer_prio:
        try:
            layer = timeline.get_layers()[layer_prio]
            y = layer.ui.get_allocation().y - container_ui.translate_coordinates(timeline.ui, 0, 0)[1]
            if y < 0:
                y += 21
            else:
                y -= 21
        except IndexError:
            if layer_prio == -1:
                y = -5
            else:
                layer = timeline.get_layers()[-1]
                alloc = layer.ui.get_allocation()
                y = alloc.y + alloc.height + 10 - container_ui.translate_coordinates(timeline.ui, 0, 0)[1]

    if not hasattr(scenario, "dragging") or scenario.dragging is False:
        if isinstance(container, GES.SourceClip):
            if edge == GES.Edge.EDGE_START:
                container.ui.leftHandle._eventCb(Gdk.Event.new(Gdk.Event.ENTER_NOTIFY))
            elif edge == GES.Edge.EDGE_END:
                container.ui.leftHandle._eventCb(Gdk.Event.new(Gdk.Event.ENTER_NOTIFY))

        scenario.dragging = True
        event = Gdk.EventButton.new(Gdk.EventType.BUTTON_PRESS)
        event.button = 1
        event.y = y
        container.ui.sendFakeEvent(event, container.ui)

    event = Gdk.EventMotion.new(Gdk.EventType.MOTION_NOTIFY)
    event.button = 1
    event.x = timelineUtils.Zoomable.nsToPixelAccurate(position) - container_ui.translate_coordinates(timeline.ui, 0, 0)[0] + ui.CONTROL_WIDTH
    event.y = y
    event.state = Gdk.ModifierType.BUTTON1_MASK
    container.ui.sendFakeEvent(event, container.ui)

    GstValidate.print_action(action, "Editing %s to %s in %s mode, edge: %s "
          "with new layer prio: %d\n" % (action.structure["container-name"],
                                         Gst.TIME_ARGS(position),
                                         timeline.ui.draggingElement.edit_mode,
                                         timeline.ui.draggingElement.dragging_edge,
                                         layer_prio))

    next_action = scenario.get_next_action()
    if next_action is None or next_action.type != "edit-container":
        scenario.dragging = False
        event = Gdk.EventButton.new(Gdk.EventType.BUTTON_RELEASE)
        event.button = 1
        event.x = timelineUtils.Zoomable.nsToPixelAccurate(position)
        event.y = y
        container.ui.sendFakeEvent(event, container.ui)

        if isinstance(container, GES.SourceClip):
            if edge == GES.Edge.EDGE_START:
                container.ui.leftHandle._eventCb(Gdk.Event.new(Gdk.Event.LEAVE_NOTIFY))
            if edge == GES.Edge.EDGE_END:
                container.ui.leftHandle._eventCb(Gdk.Event.new(Gdk.Event.LEAVE_NOTIFY))

        if container.get_layer().get_priority() != layer_prio:
            scenario.report_simple(GLib.quark_from_string("scenario::execution-error"),
                                   "Resulting clip priority: %s"
                                   " is not the same as the wanted one: %s"
                                   % (container.get_layer().get_priority(),
                                      layer_prio))

    return 1


def splitClip(scenario, action):
    timeline = scenario.pipeline.props.timeline.ui
    timeline.parent._splitCb(None)

    return True


def setZoomFit(scenario, action):
    timeline = scenario.pipeline.props.timeline.ui
    timeline.parent.zoomFit()

    return True


def init():
    global has_validate
    try:
        from gi.repository import GstValidate
        GstValidate.init()
        has_validate = GES.validate_register_action_types()
        GstValidate.register_action_type("stop", "pitivi",
                                         stop, None,
                                         "Pitivi override for the stop action",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("edit-container", "pitivi",
                                         editContainer, None,
                                         "Start dragging a clip in the timeline",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("split-clip", "pitivi",
                                         splitClip, None,
                                         "Split a clip",
                                         GstValidate.ActionTypeFlags.NONE)
        GstValidate.register_action_type("set-zoom-fit", "pitivi",
                                         setZoomFit, None,
                                         "Split a clip",
                                         GstValidate.ActionTypeFlags.NO_EXECUTION_NOT_FATAL)
    except ImportError:
        has_validate = False
