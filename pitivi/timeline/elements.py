# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/timeline/elements.py
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

"""
Convention throughout this file:
Every GES element which name could be mistaken with a UI element
is prefixed with a little b, example : bTimeline
"""
import os

from gi.repository import GES
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GstController
from gi.repository import GObject

from pitivi.utils import ui
from pitivi.utils import misc
from pitivi import configure
from pitivi.timeline import previewers
from pitivi.utils.loggable import Loggable
from pitivi.utils import timeline as timelineUtils

from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
import numpy

KEYFRAME_LINE_COLOR = (237, 212, 0)  # "Tango" yellow

CURSORS = {
    GES.Edge.EDGE_START: Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE),
    GES.Edge.EDGE_END: Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE)
}

NORMAL_CURSOR = Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)
DRAG_CURSOR = Gdk.Cursor.new(Gdk.CursorType.HAND1)


class KeyframeCurve(FigureCanvas, Loggable):

    __gsignals__ = {
        # Signal our values changed, and a redraw will be needed
        "plot-changed": (GObject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self, timeline, source):
        figure = Figure()
        FigureCanvas.__init__(self, figure)
        Loggable.__init__(self)

        self.__timeline = timeline
        self.__source = source

        # Curve values, basically separating source.get_values() timestamps
        # and values.
        self.__line_xs = []
        self.__line_ys = []

        # axisbg to None for transparency
        self.__ax = figure.add_axes([0, 0, 1, 1], axisbg='None')
        self.__ax.cla()

        # FIXME: drawing a grid and ticks would be nice, but
        # matplotlib is too slow for now.
        self.__ax.grid(False)

        self.__ax.tick_params(axis='both',
                              which='both',
                              bottom='off',
                              top='off',
                              right='off',
                              left='off')

        # This seems to also be necessary for transparency ..
        figure.patch.set_visible(False)

        # The actual Line2D object
        self.__line = None

        # The PathCollection as returned by scatter
        self.__keyframes = None

        sizes = [50]
        colors = ['r']

        self.__keyframes = self.__ax.scatter([], [], marker='D', s=sizes,
                                             c=colors, zorder=2)
        self.__line = self.__ax.plot([], [],
                                     linewidth=1.0, zorder=1)[0]
        self.__updatePlots()

        # Drag and drop logic
        self.__dragged = False
        self.__offset = None
        self.__handling_motion = False

        self.connect("motion-notify-event", self.__gtkMotionEventCb)
        self.connect("event", self._eventCb)

        self.mpl_connect('button_press_event', self.__mplButtonPressEventCb)
        self.mpl_connect(
            'button_release_event', self.__mplButtonReleaseEventCb)
        self.mpl_connect('motion_notify_event', self.__mplMotionEventCb)

    # Private methods
    def __updatePlots(self):
        values = self.__source.get_all()

        self.__line_xs = []
        self.__line_ys = []
        for value in values:
            self.__line_xs.append(value.timestamp)
            self.__line_ys.append(value.value)
            self.__ax.set_xlim(self.__line_xs[0], self.__line_xs[-1])
            self.__ax.set_ylim(0.0, 1.0)

        arr = numpy.array((self.__line_xs, self.__line_ys))
        arr = arr.transpose()
        self.__keyframes.set_offsets(arr)
        self.__line.set_xdata(self.__line_xs)
        self.__line.set_ydata(self.__line_ys)
        self.emit("plot-changed")

    def __maybeCreateKeyframe(self, event):
        result = self.__line.contains(event)
        if result[0]:
            self.__source.set(event.xdata, event.ydata)
            self.__updatePlots()

    # Callbacks

    def __gtkMotionEventCb(self, widget, event):
        """
        We need to do that here, because mpl's callbacks can't stop
        signal propagation.
        """
        if self.__handling_motion:
            return True
        return False

    def _eventCb(self, element, event):
        if event.type == Gdk.EventType.LEAVE_NOTIFY:
            cursor = NORMAL_CURSOR
            self.__timeline.get_window().set_cursor(cursor)
        return False

    def __mplButtonPressEventCb(self, event):
        result = self.__keyframes.contains(event)
        if result[0]:
            self.__handling_motion = True
            self.__offset = \
                self.__keyframes.get_offsets()[result[1]['ind'][0]][0]

    def __mplMotionEventCb(self, event):
        if not self.props.visible:
            return

        if self.__offset is not None:
            self.__dragged = True
            # Check that the mouse event still is in the figure boundaries
            if event.ydata is not None and event.xdata is not None:
                self.__source.unset(int(self.__offset))
                self.__source.set(event.xdata, event.ydata)
                self.__offset = event.xdata
                self.__updatePlots()

        cursor = NORMAL_CURSOR
        result = self.__line.contains(event)
        if result[0]:
            cursor = DRAG_CURSOR

        self.__timeline.get_window().set_cursor(
            cursor)

    def __mplButtonReleaseEventCb(self, event):
        self.__offset = None
        self.__handling_motion = False

        if not self.__dragged:
            self.__maybeCreateKeyframe(event)
        self.__dragged = False


class TimelineElement(Gtk.Layout, timelineUtils.Zoomable, Loggable):

    def __init__(self, element, timeline):
        super(TimelineElement, self).__init__()
        timelineUtils.Zoomable.__init__(self)
        Loggable.__init__(self)

        self.set_name(element.get_name())

        self.timeline = timeline
        self._bElement = element
        self._bElement.selected = timelineUtils.Selected()
        self._bElement.selected.connect(
            "selected-changed", self.__selectedChangedCb)

        self.__width = self.__height = 0

        # Needed for effect's keyframe toggling
        self._bElement.ui_element = self

        self.props.vexpand = True

        self.__previewer = self._getPreviewer()
        if self.__previewer:
            self.add(self.__previewer)

        self.__background = self._getBackground()
        if self.__background:
            self.add(self.__background)

        self.__keyframeCurve = None
        self.show_all()

        # We set up the default mixing property right here, if a binding was
        # already set (when loading a project), it will be added later
        # and override that one.
        self.__controlledProperty = self._getDefaultMixingProperty()
        if self.__controlledProperty:
            self.__createControlBinding(self._bElement)

    # Public API
    def setSize(self, width, height):
        width = max(0, width)
        self.set_size_request(width, height)

        if self.__previewer:
            self.__previewer.set_size_request(width, height)

        if self.__background:
            self.__background.set_size_request(width, height)

        if self.__keyframeCurve:
            self.__keyframeCurve.set_size_request(width, height)

        self.__width = width
        self.__height = height

    def showKeyframes(self, effect, prop):
        self.__controlledProperty = prop
        self.__createControlBinding(effect)

    # Private methods
    def __createKeyframeCurve(self, binding):
        source = binding.props.control_source
        values = source.get_all()

        if len(values) < 2:
            source.unset_all()
            val = float(self.__controlledProperty.default_value) / \
                (self.__controlledProperty.maximum -
                 self.__controlledProperty.minimum)
            source.set(self._bElement.props.in_point, val)
            source.set(
                self._bElement.props.duration + self._bElement.props.in_point,
                val)

        if self.__keyframeCurve:
            self.__keyframeCurve.disconnect_by_func(
                self.__keyframePlotChangedCb)
            self.remove(self.__keyframeCurve)

        self.__keyframeCurve = KeyframeCurve(self.timeline, source)
        self.__keyframeCurve.connect("plot-changed",
                                     self.__keyframePlotChangedCb)
        self.add(self.__keyframeCurve)
        self.__keyframeCurve.set_size_request(self.__width, self.__height)
        self.__keyframeCurve.props.visible = bool(self._bElement.selected)
        self.queue_draw()

    def __createControlBinding(self, element):
        if self.__controlledProperty:
            element.connect("control-binding-added",
                            self.__controlBindingAddedCb)
            binding = \
                element.get_control_binding(self.__controlledProperty.name)

            if binding:
                self.__createKeyframeCurve(binding)

            source = GstController.InterpolationControlSource()
            source.props.mode = GstController.InterpolationMode.LINEAR
            element.set_control_source(source,
                                       self.__controlledProperty.name, "direct")

    def __controlBindingAddedCb(self, unused_bElement, binding):
        if binding.props.name == self.__controlledProperty.name:
            self.__createKeyframeCurve(binding)

    # Gtk implementation
    def do_set_property(self, property_id, value, pspec):
        Gtk.Layout.do_set_property(self, property_id, value, pspec)

    def do_get_preferred_width(self):
        wanted_width = max(
            0, self.nsToPixel(self._bElement.props.duration) - TrimHandle.DEFAULT_WIDTH * 2)

        return wanted_width, wanted_width

    def do_draw(self, cr):
        self.propagate_draw(self.__background, cr)

        if self.__previewer:
            self.propagate_draw(self.__previewer, cr)

        if self.__keyframeCurve and self._bElement.selected:
            self.__keyframeCurve.draw()
            self.propagate_draw(self.__keyframeCurve, cr)

    def do_show_all(self):
        for child in self.get_children():
            if bool(self._bElement.selected) or child != self.__keyframeCurve:
                child.show_all()

        self.show()

    # Callbacks
    def __selectedChangedCb(self, unused_bElement, selected):
        if self.__keyframeCurve:
            self.__keyframeCurve.props.visible = selected

    def __keyframePlotChangedCb(self, unused_curve):
        self.queue_draw()

    # Virtual methods
    def _getPreviewer(self):
        """
        Should return a GtkWidget offering a representation of the
        medium (waveforms for audio, thumbnails for video ..).
        This previewer will be automatically scaled to the width and
        height of the TimelineElement.
        """
        return None

    def _getBackground(self):
        """
        Should return a GtkWidget with a unique background color.
        """
        return None

    def _getDefaultMixingProperty(self):
        """
        Should return a controllable GObject.ParamSpec allowing to mix
        media on different layers.
        """
        return None


class TitleSource(TimelineElement):

    __gtype_name__ = "PitiviTitleSource"

    def __init__(self, element, timeline):
        super(TitleSource, self).__init__(element, timeline)
        self.get_style_context().add_class("VideoUriSource")

    def _getBackground(self):
        return VideoBackground()

    def do_get_preferred_height(self):
        return ui.LAYER_HEIGHT / 2, ui.LAYER_HEIGHT


class VideoBackground (Gtk.Box):

    def __init__(self):
        super(VideoBackground, self).__init__(self)
        self.get_style_context().add_class("VideoBackground")


class VideoSource(TimelineElement):

    __gtype_name__ = "PitiviVideoSource"

    def _getBackground(self):
        return VideoBackground()

    def do_get_preferred_height(self):
        return ui.LAYER_HEIGHT / 2, ui.LAYER_HEIGHT


class VideoUriSource(VideoSource):

    __gtype_name__ = "PitiviUriVideoSource"

    def __init__(self, element, timeline):
        super(VideoUriSource, self).__init__(element, timeline)
        self.get_style_context().add_class("VideoUriSource")

    def _getPreviewer(self):
        previewer = previewers.VideoPreviewer(self._bElement)
        previewer.get_style_context().add_class("VideoUriSource")

        return previewer

    def _getDefaultMixingProperty(self):
        for spec in self._bElement.list_children_properties():
            if spec.name == "alpha":
                return spec


class AudioBackground (Gtk.Box):

    def __init__(self):
        super(AudioBackground, self).__init__(self)
        self.get_style_context().add_class("AudioBackground")


class AudioUriSource(TimelineElement):

    __gtype_name__ = "PitiviAudioUriSource"

    def __init__(self, element, timeline):
        super(AudioUriSource, self).__init__(element, timeline)
        self.get_style_context().add_class("AudioUriSource")

    def do_get_preferred_height(self):
        return ui.LAYER_HEIGHT / 2, ui.LAYER_HEIGHT

    def _getPreviewer(self):
        previewer = previewers.AudioPreviewer(self._bElement)
        previewer.get_style_context().add_class("AudioUriSource")
        previewer.startLevelsDiscoveryWhenIdle()

        return previewer

    def _getBackground(self):
        return AudioBackground()

    def _getDefaultMixingProperty(self):
        for spec in self._bElement.list_children_properties():
            if spec.name == "volume":
                return spec


class TrimHandle(Gtk.EventBox, Loggable):

    __gtype_name__ = "PitiviTrimHandle"

    DEFAULT_WIDTH = 5

    def __init__(self, clip, edge):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.clip = clip
        self.get_style_context().add_class("Trimbar")
        self.edge = edge

        self.connect("event", self._eventCb)
        self.connect("notify::window", self._windowSetCb)

    def _windowSetCb(self, window, pspec):
        self.props.window.set_cursor(CURSORS[self.edge])

    def do_show_all(self):
        self.info("DO not do anythin on .show_all")

    def _eventCb(self, element, event):
        if event.type == Gdk.EventType.ENTER_NOTIFY:
            self.clip.edit_mode = GES.EditMode.EDIT_TRIM
            self.clip.dragging_edge = self.edge
        elif event.type == Gdk.EventType.LEAVE_NOTIFY:
            self.clip.dragging_edge = GES.Edge.EDGE_NONE
            self.clip.edit_mode = None

        return False

    def do_get_preferred_width(self):
        return TrimHandle.DEFAULT_WIDTH, TrimHandle.DEFAULT_WIDTH

    def do_draw(self, cr):
        Gtk.EventBox.do_draw(self, cr)
        Gdk.cairo_set_source_pixbuf(cr, GdkPixbuf.Pixbuf.new_from_file(os.path.join(
                                    configure.get_pixmap_dir(), "trimbar-focused.png")), 10, 10)


class Clip(Gtk.EventBox, timelineUtils.Zoomable, Loggable):

    __gtype_name__ = "PitiviClip"

    def __init__(self, layer, bClip):
        super(Clip, self).__init__()
        timelineUtils.Zoomable.__init__(self)
        Loggable.__init__(self)

        self.set_name(bClip.get_name())

        self.handles = []
        self.z_order = -1
        self.layer = layer
        self.timeline = layer.timeline
        self.app = layer.app

        self.bClip = bClip
        self.bClip.ui = self
        self.bClip.selected = timelineUtils.Selected()

        self._audioSource = None
        self._videoSource = None

        self._setupWidget()

        for child in self.bClip.get_children(False):
            self._childAdded(self.bClip, child)

        self._savePositionState()
        self._connectWidgetSignals()

        self.edit_mode = None
        self.dragging_edge = GES.Edge.EDGE_NONE

        self._connectGES()
        self.get_accessible().set_name(self.bClip.get_name())

    def do_get_preferred_width(self):
        return self.nsToPixel(self.bClip.props.duration), self.nsToPixel(self.bClip.props.duration)

    def do_get_preferred_height(self):
        parent = self.get_parent()
        return parent.get_allocated_height(), parent.get_allocated_height()

    def _savePositionState(self):
        self._current_x = self.nsToPixel(self.bClip.props.start)
        self._curent_width = self.nsToPixel(self.bClip.props.duration)
        parent = self.get_parent()
        if parent:
            self._current_parent_height = self.get_parent(
            ).get_allocated_height()
        else:
            self._current_parent_height = 0
        self._current_parent = parent

    def updatePosition(self):
        parent = self.get_parent()
        x = self.nsToPixel(self.bClip.props.start)
        width = self.nsToPixel(self.bClip.props.duration)
        parent_height = parent.get_allocated_height()

        if x != self._current_x or \
                width != self._curent_width \
                or parent_height != self._current_parent_height or \
                parent != self._current_parent:

            self.layer.move(self, x, 0)
            self.set_size_request(width, parent_height)

            elements = self._elements_container.get_children()
            for child in elements:
                child.setSize(width, parent_height / len(elements))

            self._savePositionState()

    def _setupWidget(self):
        pass

    def sendFakeEvent(self, event, event_widget):
        follow_up = True
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            follow_up = self._clickedCb(event_widget, event)

        if follow_up:
            self.timeline.sendFakeEvent(event, event_widget)

    def do_draw(self, cr):
        self.updatePosition()
        Gtk.EventBox.do_draw(self, cr)

    def _clickedCb(self, unused_action, unused_actor):
        if self.timeline.got_dragged:
            # If the timeline just got dragged and @self
            # is the element initiating the mode,
            # do not do anything when the button is
            # released
            self.timeline.got_dragged = False

            return False

        # TODO : Let's be more specific, masks etc ..
        mode = timelineUtils.SELECT
        if self.timeline.parent._controlMask:
            if not self.get_state_flags() & Gtk.StateFlags.SELECTED:
                mode = timelineUtils.SELECT_ADD
                self.timeline.current_group.add(
                    self.bClip.get_toplevel_parent())
            else:
                self.timeline.current_group.remove(
                    self.bClip.get_toplevel_parent())
                mode = timelineUtils.UNSELECT
        elif not self.get_state_flags() & Gtk.StateFlags.SELECTED:
            GES.Container.ungroup(self.timeline.current_group, False)
            self.timeline.createSelectionGroup()
            self.timeline.current_group.add(
                self.bClip.get_toplevel_parent())
            self.timeline.parent.gui.switchContextTab(self.bClip)

        parent = self.bClip.get_parent()
        if parent == self.timeline.current_group or parent is None:
            selection = [self.bClip]
        else:
            while parent:
                if parent.get_parent() == self.timeline.current_group:
                    break
                parent = parent.get_parent()

            children = parent.get_children(True)
            selection = [elem for elem in children if isinstance(elem, GES.SourceClip) or
                         isinstance(elem, GES.TransitionClip)]

        self.timeline.selection.setSelection(selection, mode)

        # if self.keyframedElement:
        #    self.showKeyframes(self.keyframedElement, self.prop)

        return False

    def _connectWidgetSignals(self):
        self.connect("button-release-event", self._clickedCb)
        self.connect("event", self._eventCb)

    def _eventCb(self, element, event):
        if event.type == Gdk.EventType.ENTER_NOTIFY:
            ui.set_children_state_recurse(self, Gtk.StateFlags.PRELIGHT)
            for handle in self.handles:
                handle.show()
        elif event.type == Gdk.EventType.LEAVE_NOTIFY:
            ui.unset_children_state_recurse(self, Gtk.StateFlags.PRELIGHT)
            for handle in self.handles:
                handle.hide()

        return False

    def _startChangedCb(self, unused_clip, unused_pspec):
        if self.get_parent() is None:
            # FIXME Check why that happens at all (looks like a GTK bug)
            return

        self.layer.move(self, self.nsToPixel(self.bClip.props.start), 0)

    def _durationChangedCb(self, unused_clip, unused_pspec):
        parent = self.get_parent()
        if parent:
            duration = self.nsToPixel(self.bClip.props.duration)
            parent_height = parent.get_allocated_height()
            self.set_size_request(duration, parent_height)

    def _layerChangedCb(self, bClip, unused_pspec):
        bLayer = bClip.props.layer
        if bLayer:
            self.layer = bLayer.ui

    def _childAdded(self, clip, child):
        child.selected = timelineUtils.Selected()

    def _childAddedCb(self, clip, child):
        self._childAdded(clip, child)

    def _childRemoved(self, clip, child):
        pass

    def _childRemovedCb(self, clip, child):
        self._childRemoved(clip, child)

    def _connectGES(self):
        self.bClip.connect("notify::start", self._startChangedCb)
        self.bClip.connect("notify::inpoint", self._startChangedCb)
        self.bClip.connect("notify::duration", self._durationChangedCb)
        self.bClip.connect("notify::layer", self._layerChangedCb)

        self.bClip.connect_after("child-added", self._childAddedCb)
        self.bClip.connect_after("child-removed", self._childRemovedCb)


class SourceClip(Clip):
    __gtype_name__ = "PitiviSourceClip"

    def __init__(self, layer, bClip):
        super(SourceClip, self).__init__(layer, bClip)

    def _setupWidget(self):
        self._vbox = Gtk.Box()
        self._vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.add(self._vbox)

        self.leftHandle = TrimHandle(self, GES.Edge.EDGE_START)
        self._vbox.pack_start(self.leftHandle, False, False, 0)

        self._elements_container = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        self._vbox.pack_start(self._elements_container, True, True, 0)

        self.rightHandle = TrimHandle(self, GES.Edge.EDGE_END)
        self._vbox.pack_end(self.rightHandle, False, False, 0)\

        self.handles.append(self.leftHandle)
        self.handles.append(self.rightHandle)

        self.get_style_context().add_class("Clip")

    def _childRemoved(self, clip, child):
        if child.ui is not None:
            self._elements_container.remove(child.ui)
            child.ui = None


class UriClip(SourceClip):
    __gtype_name__ = "PitiviuriClip"

    def __init__(self, layer, bClip):
        super(UriClip, self).__init__(layer, bClip)

        self.set_tooltip_markup(misc.filename_from_uri(bClip.get_uri()))

    def _childAdded(self, clip, child):
        if isinstance(child, GES.Source):
            if child.get_track_type() == GES.TrackType.AUDIO:
                self._audioSource = AudioUriSource(child, self.timeline)
                child.ui = self._audioSource
                self._elements_container.pack2(self._audioSource, True, False)
                self._audioSource.set_visible(True)
            elif child.get_track_type() == GES.TrackType.VIDEO:
                self._videoSource = VideoUriSource(child, self.timeline)
                child.ui = self._videoSource
                self._elements_container.pack1(self._videoSource, True, False)
                self._videoSource.set_visible(True)
        else:
            child.ui = None


class TitleClip(SourceClip):
    __gtype_name__ = "PitiviTitleClip"

    def _childAdded(self, clip, child):
        if isinstance(child, GES.Source):
            if child.get_track_type() == GES.TrackType.VIDEO:
                self._videoSource = VideoSource(child, self.timeline)
                child.ui = self._videoSource
                self._elements_container.pack1(self._videoSource, True, False)
                self._videoSource.set_visible(True)
        else:
            child.ui = None


class TransitionClip(Clip):

    __gtype_name__ = "PitiviTransitionClip"

    def __init__(self, layer, bClip):
        super(TransitionClip, self).__init__(layer, bClip)
        self.get_style_context().add_class("TransitionClip")
        self.z_order = 0

        for child in bClip.get_children(True):
            child.selected = timelineUtils.Selected()
        self.bClip.connect("child-added", self._childAddedCb)
        self.selected = False
        self.connect("state-flags-changed", self._selectedChangedCb)
        self.connect("button-press-event", self._pressEventCb)

        # In the case of TransitionClips, we are the only container
        self._elements_container = self
        self.set_tooltip_markup("<span foreground='blue'>%s</span>" %
                                str(bClip.props.vtype.value_nick))

    def _childAdded(self, clip, child):
        child.selected = timelineUtils.Selected()

        if isinstance(child, GES.VideoTransition):
            self.z_order += 1

    def do_draw(self, cr):
        Clip.do_draw(self, cr)

    def _selectedChangedCb(self, unused_widget, flags):
        if not [c for c in self.bClip.get_children(True) if isinstance(c, GES.VideoTransition)]:
            return

        if flags & Gtk.StateFlags.SELECTED:
            self.timeline.parent.app.gui.trans_list.activate(self.bClip)
            self.selected = True
        elif self.selected:
            self.selected = False
            self.timeline.parent.app.gui.trans_list.deactivate()

    def _pressEventCb(self, unused_action, unused_widget):
        selection = {self.bClip}
        self.timeline.selection.setSelection(selection, timelineUtils.SELECT)
        return True

GES_TYPE_UI_TYPE = {
    GES.UriClip.__gtype__: UriClip,
    GES.TitleClip.__gtype__: TitleClip,
    GES.TransitionClip.__gtype__: TransitionClip
}
