# -*- coding: utf-8 -*-
# Pitivi video editor
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
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.utils.loggable import Loggable


# Selection modes
# Set the selection to the given set.
SELECT = 0
# Remove the given set from the selection.
UNSELECT = 1
# Extend the selection with the given set.
SELECT_ADD = 2


class TimelineError(Exception):
    """Base Exception for errors happening in `Timeline`s or `Clip`s."""
    pass


class Selected(GObject.Object):
    """Allows keeping track of the selection status for individual elements.

    Signals:
        selected-changed: Emitted when the selection is specified.
    """

    __gsignals__ = {
        "selected-changed": (GObject.SignalFlags.RUN_LAST, None, (bool,)),
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self._selected = False

    def __bool__(self):
        """Checks whether it's selected."""
        return self._selected

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, selected):
        differs = self._selected != selected
        self._selected = selected
        if differs:
            self.emit("selected-changed", selected)


class Selection(GObject.Object, Loggable):
    """Manages a set of clips representing a selection.

    Attributes:
        selected (List[GES.TrackElement]): Set of selected elements.

    Signals:
        selection-changed: The contents of the selection changed.
    """

    __gsignals__ = {
        "selection-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        GObject.Object.__init__(self)
        Loggable.__init__(self)
        self.selected = set()
        self.can_group = False
        self.can_ungroup = False

    def setSelection(self, objs, mode):
        """Updates the current selection.

        Args:
            objs (List[GES.TrackElement]): Timeline objects to update the
                selection with.
            mode (SELECT or UNSELECT or SELECT_ADD): The type of update to
                apply. The selection will be:
                - `SELECT` : set to the provided selection.
                - `UNSELECT` : the same minus the provided selection.
                - `SELECT_ADD` : extended with the provided selection.
        """
        selection = set()
        for obj in objs:
            # FIXME GES break, handle the fact that we have unlinked objects in
            # GES
            if isinstance(obj, GES.TrackElement):
                selection.add(obj.get_parent())
            else:
                selection.add(obj)
        if mode == SELECT_ADD:
            selection = self.selected | selection
        elif mode == UNSELECT:
            selection = self.selected - selection

        old_selection = self.selected
        if selection == old_selection:
            # Nothing changed. This can happen for example when the user clicks
            # the selected clip, then the clip remains selected.
            return
        self.selected = selection

        for obj, selected in self.__get_selection_changes(old_selection):
            obj.selected.selected = selected
            if obj.ui:
                if selected:
                    from pitivi.utils.ui import set_children_state_recurse
                    set_children_state_recurse(obj.ui, Gtk.StateFlags.SELECTED)
                else:
                    from pitivi.utils.ui import unset_children_state_recurse
                    unset_children_state_recurse(obj.ui, Gtk.StateFlags.SELECTED)
            for element in obj.get_children(False):
                if isinstance(obj, GES.BaseEffect) or\
                        isinstance(obj, GES.TextOverlay):
                    continue
                element.selected.selected = selected
        self.set_can_group_ungroup()
        self.emit("selection-changed")

    def set_can_group_ungroup(self):
        can_ungroup = False
        toplevels = self.toplevels
        self.can_group = len(toplevels) > 1
        # If we allow grouping, we disallow ungrouping.
        if not self.can_group:
            for toplevel in toplevels:
                if (isinstance(toplevel, GES.Group) or
                        (isinstance(toplevel, GES.Container) and len(toplevel.get_children(False)) > 1)):
                    can_ungroup = True
                    break
        self.can_ungroup = can_ungroup and not self.can_group

    def __get_selection_changes(self, old_selection):
        for obj in old_selection - self.selected:
            yield obj, False

        # Announce all selected objects that they are selected, even if
        # they were already selected. This allows them to update based on
        # the current selection.
        for obj in self.selected:
            yield obj, True

    def select(self, objs):
        self.setSelection(objs, SELECT)

    def unselect(self, objs):
        self.setSelection(objs, UNSELECT)

    def getSelectedTrackElements(self):
        """Returns the list of elements contained in this selection.

        Returns:
            List[GES.TrackElement]
        """
        objects = []
        for clip in self.selected:
            objects.extend(clip.get_children(False))

        return set(objects)

    def getSingleClip(self, clip_type=GES.SourceClip):
        """Returns the single-selected clip, if any.

        Args:
            clip_type (type): The class the clip must be an instance of.
        """
        if len(self.selected) == 1:
            clip = tuple(self.selected)[0]
            if isinstance(clip, clip_type):
                return clip
        return None

    @property
    def toplevels(self):
        """Returns the toplevel elements of the selection."""
        toplevels = set()
        for obj in self.selected:
            if not obj.timeline:
                # The element has been removed from the timeline. Ignore it.
                continue
            toplevel = obj.get_toplevel_parent()
            toplevels.update(self.__serializable_toplevels(toplevel))

        return toplevels

    def __serializable_toplevels(self, toplevel):
        """Generates the specified element if serializable, or its children."""
        if toplevel.props.serialize:
            yield toplevel
        else:
            for element in toplevel.get_children(False):
                for child in self.__serializable_toplevels(element):
                    yield child

    def group(self):
        """Groups the serializable toplevel elements into a new GES.Group.

        Returns:
            GES.Group: The serializable elements which have no parent or
            have only non-serializable ancestors.
        """
        toplevels = set()
        for obj in self.selected:
            if not obj.timeline:
                # The element has been removed from the timeline. Ignore it.
                continue
            toplevel = obj.get_toplevel_parent()
            toplevels.add(toplevel)

        group = GES.Group()
        group.props.serialize = False
        for toplevel in toplevels:
            group.add(toplevel)
        return group

    def __len__(self):
        return len(self.selected)

    def __iter__(self):
        return iter(self.selected)


class EditingContext(GObject.Object, Loggable):
    """Encapsulates interactive editing.

    This is the main class for interactive editing.
    Handles various timeline editing modes.

    Attributes:
        focus (GES.Clip or GES.TrackElement): The Clip or TrackElement which is
            to be the main target of interactive editing, such as the object
            directly under the mouse pointer.
        timeline (GES.Timeline): The timeline to edit.
        edge (GES.Edge): The edge on which the editing will happen, this
            parameter can be changed while still using the same context.
        mode (GES.EditMode): The mode in which the editing will happen, this
            parameter can be changed while still using the same context.
        app (Pitivi): The app.
    """

    def __init__(self, focus, timeline, mode, edge, app, log_actions):
        GObject.Object.__init__(self)
        Loggable.__init__(self)
        if isinstance(focus, GES.TrackElement):
            self.focus = focus.get_parent()
        else:
            self.focus = focus

        self.with_video = GES.TrackType.VIDEO & self.focus.get_track_types()

        self.old_position = self.focus.get_start()
        if edge == GES.Edge.EDGE_END and mode == GES.EditMode.EDIT_TRIM:
            self.old_position += self.focus.get_duration()

        self.old_priority = self.focus.get_priority()
        self.new_position = None

        self.timeline = timeline
        self.app = app

        self.edge = edge
        self.mode = mode

        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        self.__log_actions = log_actions
        if log_actions:
            self.app.action_log.begin("move-clip",
                                      finalizing_action=CommitTimelineFinalizingAction(
                                          self.timeline.get_asset().pipeline),
                                      toplevel=True)

    def finish(self):
        if self.__log_actions:
            self.app.action_log.commit("move-clip")
        self.timeline.get_asset().pipeline.commit_timeline()
        self.timeline.ui.app.gui.editor.viewer.clipTrimPreviewFinished()

    def setMode(self, mode):
        """Sets the current editing mode.

        Args:
            mode (GES.EditMode): The editing mode.
        """
        self.mode = mode

    def edit_to(self, position, layer):
        """Updates the position and priority of the edited clip or element.

        Args:
            position (int): The time in nanoseconds.
            layer (GES.Layer): The layer on which it should be placed.
        """
        position = max(0, position)
        priority = layer.props.priority
        if self.edge in [GES.Edge.EDGE_START, GES.Edge.EDGE_END]:
            priority = -1
        else:
            priority = max(0, priority)

        self.new_position = position
        self.new_priority = priority

        res = self.focus.edit([], priority, self.mode, self.edge, int(position))
        self.app.write_action("edit-container",
                              container_name=self.focus.get_name(),
                              position=float(position / Gst.SECOND),
                              edit_mode=self.mode.value_nick,
                              edge=self.edge.value_nick,
                              new_layer_priority=int(priority))

        if res and self.mode == GES.EditMode.EDIT_TRIM and self.with_video:
            if self.edge == GES.Edge.EDGE_START:
                self.timeline.ui.app.gui.editor.viewer.clipTrimPreview(
                    self.focus, self.focus.props.in_point)
            elif self.edge == GES.Edge.EDGE_END:
                self.timeline.ui.app.gui.editor.viewer.clipTrimPreview(
                    self.focus, self.focus.props.duration + self.focus.props.in_point)


# -------------------------- Interfaces ----------------------------------------#


class Zoomable:
    """Base class for conversions between timeline timestamps and UI pixels.

    Complex Timeline interfaces v2 (01 Jul 2008)

    Zoomable
    -----------------------
    Interface for the Complex Timeline widgets for setting, getting,
    distributing and modifying the zoom ratio and the size of the widget.

    A zoomratio is the number of pixels per second
    ex : 10.0 = 10 pixels for a second
    ex : 0.1 = 1 pixel for 10 seconds
    ex : 1.0 = 1 pixel for a second
     Class Methods
    . pixelToNs(pixels)
    . nsToPixels(time)
    . setZoomRatio
    Instance Methods
    . zoomChanged()
    """

    sigid = None
    _instances = []
    max_zoom = 1000.0
    min_zoom = 0.25
    zoom_steps = 100
    zoom_range = max_zoom - min_zoom
    _cur_zoom = 20
    zoomratio = None

    app = None

    def __init__(self):
        # FIXME: ideally we should deprecate this
        Zoomable.addInstance(self)
        if Zoomable.zoomratio is None:
            Zoomable.zoomratio = self.computeZoomRatio(self._cur_zoom)

    def __del__(self):
        if self in Zoomable._instances:
            # FIXME: ideally we should deprecate this and spit a warning here
            self._instances.remove(self)

    @classmethod
    def addInstance(cls, instance):
        cls._instances.append(instance)

    @classmethod
    def removeInstance(cls, instance):
        cls._instances.remove(instance)

    @classmethod
    def setZoomRatio(cls, ratio):
        ratio = min(max(cls.min_zoom, ratio), cls.max_zoom)
        if cls.zoomratio != ratio:
            cls.zoomratio = ratio
            for inst in cls._instances:
                inst.zoomChanged()

    @classmethod
    def setZoomLevel(cls, level):
        level = int(max(0, min(level, cls.zoom_steps)))
        if level != cls._cur_zoom:
            cls._cur_zoom = level
            cls.setZoomRatio(cls.computeZoomRatio(level))

    @classmethod
    def getCurrentZoomLevel(cls):
        return cls._cur_zoom

    @classmethod
    def zoomIn(cls):
        cls.setZoomLevel(cls._cur_zoom + 1)
        cls.app.write_action("zoom-in", optional_action_type=True)

    @classmethod
    def zoomOut(cls):
        cls.setZoomLevel(cls._cur_zoom - 1)
        cls.app.write_action("zoom-out", optional_action_type=True)

    @classmethod
    def computeZoomRatio(cls, x):
        return ((((float(x) / cls.zoom_steps) ** 3) * cls.zoom_range) +
                cls.min_zoom)

    @classmethod
    def computeZoomLevel(cls, ratio):
        return int((
            (max(0, ratio - cls.min_zoom) /
                cls.zoom_range) ** (1.0 / 3.0)) * cls.zoom_steps)

    @classmethod
    def pixelToNs(cls, pixel):
        """Returns the duration equivalent of the specified pixel."""
        return int(pixel * Gst.SECOND / cls.zoomratio)

    @classmethod
    def pixelToNsAt(cls, pixel, ratio):
        """Returns the duration equivalent of the specified pixel."""
        return int(pixel * Gst.SECOND / ratio)

    @classmethod
    def nsToPixel(cls, duration):
        """Returns the pixel equivalent of the specified duration"""
        # Here, a long time ago (206f3a05), a pissed programmer said:
        # DIE YOU CUNTMUNCH CLOCK_TIME_NONE UBER STUPIDITY OF CRACK BINDINGS !!
        if duration == Gst.CLOCK_TIME_NONE:
            return 0
        return int((float(duration) / Gst.SECOND) * cls.zoomratio)

    @classmethod
    def nsToPixelAccurate(cls, duration):
        """Returns the pixel equivalent of the specified duration."""
        # Here, a long time ago (206f3a05), a pissed programmer said:
        # DIE YOU CUNTMUNCH CLOCK_TIME_NONE UBER STUPIDITY OF CRACK BINDINGS !!
        if duration == Gst.CLOCK_TIME_NONE:
            return 0
        return (float(duration) / Gst.SECOND) * cls.zoomratio

    def zoomChanged(self):
        pass
