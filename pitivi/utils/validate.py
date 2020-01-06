# -*- coding: utf-8 -*-
# Pitivi video editor
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
# pylint: disable=protected-access
import locale
import subprocess
from unittest import mock

import gi
from gi.repository import Gdk
from gi.repository import GES
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.utils.timeline import Zoomable


CAT = "validate"


try:
    gi.require_version("GstValidate", "1.0")
    from gi.repository import GstValidate
except ImportError:
    GstValidate = None
except ValueError:
    # pylint: disable=invalid-name
    GstValidate = None

monitor = None
has_validate = False


def create_event(event_type, **kwargs):
    event_types_constructors = {
        Gdk.EventType.BUTTON_PRESS: Gdk.EventButton,
        Gdk.EventType.BUTTON_RELEASE: Gdk.EventButton,
        Gdk.EventType.KEY_PRESS: Gdk.EventKey,
        Gdk.EventType.KEY_RELEASE: Gdk.EventKey,
        Gdk.EventType.MOTION_NOTIFY: Gdk.EventMotion
    }

    constructor = event_types_constructors[event_type]
    event = constructor()
    event.type = event_type
    for arg, value in kwargs.items():
        setattr(event, arg, value)

    return event


if GstValidate:
    class PitiviMonitor(GstValidate.Monitor):
        def __init__(self, runner, obj):
            GstValidate.Monitor.__init__(self, object=obj, validate_runner=runner)

            if GstValidate:
                try:
                    gi.require_version('Wnck', '3.0')
                    from gi.repository import Wnck
                    Wnck.Screen.get_default().connect("window-opened", self._window_opened_cb)
                except (ImportError, ValueError):
                    print("Wnck not present on the system,"
                          " not checking the sink does not open a new window")
                except AttributeError:
                    print("Wnck can not be used on the system")

        def _window_opened_cb(self, screen, window):
            global monitor

            if window.get_name() == 'renderer' and monitor:
                monitor.report_simple(GLib.quark_from_string("pitivi::wrong-window-creation"),
                                      "New window created by the sink,"
                                      " that should not happen")

        def check_wrong_window(self):
            try:
                windows = subprocess.check_output(["xwininfo", "-tree", "-root"]).decode(locale.getdefaultlocale()[1])
                for w in windows.split('\n'):
                    if "OpenGL renderer" in w and w.startswith("     0x"):
                        monitor.report_simple(GLib.quark_from_string("pitivi::wrong-window-creation"),
                                              "New window created by the sink,"
                                              " that should not happen, (current windows: %s)"
                                              % windows)
                        break
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass


def create_monitor(runner, app):
    global monitor
    global has_validate

    if not monitor and has_validate:
        monitor = PitiviMonitor(runner, app)
        GstValidate.Reporter.set_name(monitor, "Pitivi")


def stop_func(scenario, action):
    global monitor

    if monitor:
        monitor.check_wrong_window()

    if action.structure.get_boolean("force")[0]:
        GstValidate.execute_action(GstValidate.get_action_type(action.type).overriden_type,
                                   action)

        timeline = scenario.get_pipeline().props.timeline
        project = timeline.get_asset()

        if project:
            project.set_modification_state(False)
            GstValidate.print_action(action, "Force quitting, ignoring any"

                                     " changes in the project\n")
        timeline.ui.app.shutdown()

        return 1

    GstValidate.print_action(action, "STOP: not doing anything in pitivi\n")

    return 1


def position_changed_cb(pipeline, position, scenario, action,
                        wanted_position):
    if pipeline._busy_async:
        return

    if pipeline._next_seek:
        return

    print(str(wanted_position), str(position))
    if wanted_position != position:
        scenario.report_simple(
            GLib.quark_from_string("scenario::execution-error"),
            "Position after seek (%s) does not match wanted one %s" % (
                Gst.TIME_ARGS(position), Gst.TIME_ARGS(wanted_position)))

    pipeline.disconnect_by_func(position_changed_cb)
    action.set_done()


def seek_func(scenario, action):
    res, wanted_position = GstValidate.utils_get_clocktime(action.structure,
                                                           "start")
    assert res
    scenario.get_pipeline().simple_seek(wanted_position)
    scenario.get_pipeline().connect("position", position_changed_cb, scenario,
                                    action, wanted_position)

    return GstValidate.ActionReturn.ASYNC


def set_state_func(scenario, action):
    wanted_state = action.structure["state"]
    if wanted_state is None:
        wanted_state = action.structure.get_name()
        if wanted_state == "play":
            wanted_state = "playing"
        elif wanted_state == "pause":
            wanted_state = "paused"

    if wanted_state == "paused":
        if scenario.__dict__.get("started", None) is None:
            return 1

    return GstValidate.execute_action(GstValidate.get_action_type(action.type).overriden_type,
                                      action)


def get_edge(structure):
    try:
        res, edge = GstValidate.utils_enum_from_str(GES.Edge, structure["edge"])
        if not res:
            edge = GES.Edge.EDGE_NONE
        else:
            edge = GES.Edge(edge)

    except KeyError:
        edge = GES.Edge.EDGE_NONE

    return edge


def _release_button_if_needed(scenario, timeline, container, layer_prio,
                              position, y):
    next_actions = scenario.get_actions()
    if len(next_actions) == 1:
        return
    next_action = None
    for next_action in next_actions[1:]:
        if next_action.type not in ["wait", "add-layer"]:
            break
    if not next_action:
        return

    need_release = True
    if next_action and next_action.type == "edit-container":
        edge = get_edge(next_action.structure)

        if edge == scenario.last_edge:
            need_release = False

    if next_action is None or need_release:
        scenario.dragging = False
        x = Zoomable.ns_to_pixel_accurate(position)
        event = create_event(Gdk.EventType.BUTTON_RELEASE, button=1, x=x, y=y)
        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = container.ui
            container.ui._button_release_event_cb(None, event)

        if layer_prio > 0 and container.get_layer().get_priority() != layer_prio:
            scenario.report_simple(GLib.quark_from_string("scenario::execution-error"),
                                   "Resulting clip priority: %s"
                                   " is not the same as the wanted one: %s"
                                   % (container.get_layer().get_priority(),
                                      layer_prio))

        clean_edit_modes(timeline, scenario)


def clean_edit_modes(timeline, scenario):
    if scenario.last_mode == GES.EditMode.EDIT_RIPPLE:
        event = create_event(Gdk.EventType.KEY_RELEASE, keyval=Gdk.KEY_Shift_L)
        timeline.ui.get_parent().do_key_release_event(event)
    elif scenario.last_mode == GES.EditMode.EDIT_ROLL:
        event = create_event(Gdk.EventType.KEY_RELEASE, keyval=Gdk.KEY_Control_L)
        timeline.ui.get_parent().do_key_release_event(event)

    scenario.last_mode = None


def set_editing_mode(timeline, scenario, action):
    if not hasattr(scenario, "last_mode"):
        scenario.last_mode = None

    try:
        res, mode = GstValidate.utils_enum_from_str(GES.EditMode, action.structure["edit-mode"])
        if not res:
            mode = GES.EditMode.EDIT_NORMAL
        else:
            mode = GES.EditMode(mode)
    except KeyError:
        mode = GES.EditMode.EDIT_NORMAL

    if mode == GES.EditMode.EDIT_RIPPLE:
        timeline.ui.get_parent().do_key_press_event(create_event(Gdk.EventType.KEY_PRESS, keyval=Gdk.KEY_Shift_L))

        if scenario.last_mode == GES.EditMode.EDIT_ROLL:
            timeline.ui.get_parent().do_key_release_event(create_event(Gdk.EventType.KEY_RELEASE, keyval=Gdk.KEY_Control_L))

    elif mode == GES.EditMode.EDIT_ROLL:
        timeline.ui.do_key_press_event(create_event(Gdk.EventType.KEY_PRESS, keyval=Gdk.KEY_Control_L))

        if scenario.last_mode == GES.EditMode.EDIT_RIPPLE:
            timeline.ui.do_key_release_event(create_event(Gdk.EventType.KEY_RELEASE, keyval=Gdk.KEY_Shift_L))
    else:
        clean_edit_modes(timeline, scenario)

    scenario.last_mode = mode


def edit_container_func(scenario, action):
    timeline = scenario.get_pipeline().props.timeline
    container = timeline.get_element(action.structure["container-name"])

    if container is None:
        for layer in timeline.get_layers():
            for clip in layer.get_clips():
                Gst.info("Existing clip: %s" % clip.get_name())

        scenario.report_simple(GLib.quark_from_string("scenario::execution-error"),
                               "Could not find container: %s"
                               % action.structure["container-name"])

        return 1

    res, position = GstValidate.action_get_clocktime(scenario, action, "position")
    layer_prio = action.structure["new-layer-priority"]

    if res is False:
        return 0

    edge = get_edge(action.structure)
    container_ui = container.ui

    set_editing_mode(timeline, scenario, action)

    y = 21 - container_ui.translate_coordinates(timeline.ui, 0, 0)[1]

    if container.get_layer().get_priority() != layer_prio and layer_prio != -1:
        try:
            layer = timeline.get_layers()[layer_prio]
            Gst.info("Y is: %s Realized?? %s Priori: %s layer prio: %s"
                     % (layer.ui.get_allocation().y,
                        container_ui.get_realized(),
                        container.get_layer().get_priority(),
                        layer_prio))
            y = layer.ui.get_allocation().y - container_ui.translate_coordinates(timeline.ui, 0, 0)[1]
            if y < 0:
                y += 21
            elif y > 0:
                y -= 21
        except IndexError:
            if layer_prio == -1:
                y = -5
            else:
                layer = timeline.get_layers()[-1]
                alloc = layer.ui.get_allocation()
                y = alloc.y + alloc.height + 10 - container_ui.translate_coordinates(timeline.ui, 0, 0)[1]

    if not hasattr(scenario, "last_edge"):
        scenario.last_edge = edge

    if not hasattr(scenario, "dragging") or scenario.dragging is False \
            or scenario.last_edge != edge:
        event_widget = container.ui
        if isinstance(container, GES.SourceClip):
            if edge == GES.Edge.EDGE_START:
                event_widget = container.ui.left_handle
            elif edge == GES.Edge.EDGE_END:
                event_widget = container.ui.right_handle

        scenario.dragging = True
        event = create_event(Gdk.EventType.BUTTON_PRESS, button=1, y=y)
        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = event_widget
            timeline.ui._button_press_event_cb(event_widget, event)

    x = Zoomable.ns_to_pixel_accurate(position) - container_ui.translate_coordinates(timeline.ui.layout.layers_vbox, 0, 0)[0]
    event = create_event(Gdk.EventType.MOTION_NOTIFY, button=1,
                         x=x, y=y, state=Gdk.ModifierType.BUTTON1_MASK)
    with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
        get_event_widget.return_value = container.ui
        timeline.ui._motion_notify_event_cb(None, event)

    GstValidate.print_action(action,
                             "Editing %s to %s in %s mode, edge: %s "
                             "with new layer prio: %d\n" % (action.structure["container-name"],
                                                            Gst.TIME_ARGS(position),
                                                            scenario.last_mode,
                                                            edge,
                                                            layer_prio))

    _release_button_if_needed(scenario, timeline, container, layer_prio,
                              position, y)
    scenario.last_edge = edge

    return 1


def split_clip_func(scenario, action):
    timeline = scenario.get_pipeline().props.timeline.ui
    timeline.get_parent()._split_cb(None, None)

    return True


def zoom_func(scenario, action):
    timeline = scenario.get_pipeline().props.timeline

    GstValidate.print_action(action, action.type.replace('-', ' ') + "\n")

    {"zoom-fit": timeline.ui.set_best_zoom_ratio,
     "zoom-out": Zoomable.zoom_out,
     "zoom-in": Zoomable.zoom_in}[action.type]()

    return True


def set_zoom_level_func(scenario, action):
    Zoomable.set_zoom_level(action.structure["level"])

    return True


def add_layer_func(scenario, action):
    timeline = scenario.get_pipeline().props.timeline
    if len(timeline.get_layers()) == 0:
        GstValidate.print_action(action, "Adding first layer\n")
        timeline.append_layer()
    else:
        GstValidate.print_action(action, "Not adding layer, should be done by pitivi itself\n")

    return True


def remove_clip_func(scenario, action):
    try:
        next_action = scenario.get_actions()[1]
    except KeyError:
        next_action = None

    if next_action and next_action.type == "add-clip":
        if next_action.structure["element-name"] == action.structure["element-name"]:
            scenario.no_next_add_element = True
            GstValidate.print_action(action,
                                     "Just moving %s between layers, not removing it\n"
                                     % action.structure["element-name"])
            return True

    action_type = GstValidate.get_action_type(action.type)

    return GstValidate.execute_action(action_type.overriden_type, action)


def select_clips_func(scenario, action):
    should_select = True
    timeline = scenario.get_pipeline().props.timeline
    clip = timeline.get_element(action.structure["clip-name"])

    if clip is None:
        scenario.report_simple(GLib.quark_from_string("scenario::execution-error"),
                               "Could not find container: %s"
                               % action.structure["container-name"])

        return 1

    mode = action.structure["mode"]
    if mode:
        mode = mode.lower()

    if mode == "ctrl":
        if clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED:
            should_select = False

        event = create_event(Gdk.EventType.KEY_PRESS, keyval=Gdk.KEY_Control_L)
        timeline.ui.get_parent().do_key_press_event(event)

    event = create_event(Gdk.EventType.BUTTON_RELEASE, button=1)
    with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
        get_event_widget.return_value = clip.ui
        clip.ui._button_release_event_cb(None, event)

    selection = action.structure["selection"]
    if not selection:
        if should_select:
            if not clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED:
                scenario.report_simple(GLib.quark_from_string("scenario::execution-error"),
                                       "Clip %s should be selected but is not"
                                       % clip.get_name())
        elif clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED:
            scenario.report_simple(GLib.quark_from_string("scenario::execution-error"),
                                   "Clip %s should be UNselected but is not"
                                   % clip.get_name())
    else:
        for layer in timeline.get_layers():
            for clip in layer.get_clips():
                if clip.get_name() in selection:
                    if not clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED:
                        scenario.report_simple(GLib.quark_from_string("scenario::execution-error"),
                                               "Clip %s should be selected (as defined in selection %s)"
                                               " but is not" % (selection, clip.get_name()))
                else:
                    if clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED:
                        scenario.report_simple(GLib.quark_from_string("scenario::execution-error"),
                                               "Clip %s should NOT be selected (as defined in selection %s)"
                                               " but it is" % (selection, clip.get_name()))

    if mode == "ctrl":
        event = create_event(Gdk.EventType.KEY_RELEASE, keyval=Gdk.KEY_Control_L)
        timeline.ui.get_parent().do_key_release_event(event)

    return 1


def create_action_parameter(name, desc, mandatory=False, possible_variables=None, types=None):
    parameter = GstValidate.ActionParameter()
    parameter.description = desc
    parameter.mandatory = mandatory
    parameter.name = name
    parameter.possible_variables = possible_variables
    parameter.types = types

    return parameter


def init():
    global has_validate
    try:
        GstValidate.init()
        has_validate = GES.validate_register_action_types()
        GstValidate.register_action_type("stop", "pitivi",
                                         stop_func, None,
                                         "Pitivi override for the stop action",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("seek", "pitivi",
                                         seek_func, None,
                                         "Pitivi override for the seek action",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("pause", "pitivi",
                                         set_state_func, None,
                                         "Pitivi override for the pause action",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("play", "pitivi",
                                         set_state_func, None,
                                         "Pitivi override for the pause action",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("set-state", "pitivi",
                                         set_state_func, None,
                                         "Pitivi override for the set-state action",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("edit-container", "pitivi",
                                         edit_container_func, None,
                                         "Start dragging a clip in the timeline",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("split-clip", "pitivi",
                                         split_clip_func, None,
                                         "Split a clip",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("add-layer", "pitivi",
                                         add_layer_func, None,
                                         "Add layer",
                                         GstValidate.ActionTypeFlags.NONE)

        GstValidate.register_action_type("remove-clip", "pitivi",
                                         remove_clip_func, None,
                                         "Remove clip",
                                         GstValidate.ActionTypeFlags.NONE)
        GstValidate.register_action_type("select-clips", "pitivi",
                                         select_clips_func,
                                         [create_action_parameter("clip-name",
                                                                  "The name of the clip to select",
                                                                  True, None, "str")],
                                         "Select clips",
                                         GstValidate.ActionTypeFlags.NONE)

        for action_type in ["zoom-fit", "zoom-out", "zoom-in"]:
            GstValidate.register_action_type(action_type, "pitivi",
                                             zoom_func, None, action_type,
                                             GstValidate.ActionTypeFlags.NO_EXECUTION_NOT_FATAL)
        GstValidate.register_action_type('set-zoom-level', "pitivi", set_zoom_level_func, None, action_type,
                                         GstValidate.ActionTypeFlags.NO_EXECUTION_NOT_FATAL)

        Gst.info("Adding pitivi::wrong-window-creation")
        GstValidate.Issue.register(GstValidate.Issue.new(
            GLib.quark_from_string("pitivi::wrong-window-creation"),
            "A new window for the sink has wrongly been created",
            "All sink should display their images in an embedded "
            "widget and thus not create a new window",
            GstValidate.ReportLevel.CRITICAL))
        return True
    except ImportError:
        has_validate = False
        return False
