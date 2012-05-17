# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/track.py
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
import gtk
import os.path
import pango
import cairo

import pitivi.configure as configure

from gettext import gettext as _

from pitivi.dialogs.prefs import PreferencesDialog

from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import Point, info_name
from pitivi.settings import GlobalSettings
from pitivi.utils.signal import Signallable
from pitivi.utils.timeline import SELECT, SELECT_ADD, UNSELECT, \
    SELECT_BETWEEN, EditingContext, Controller, View, Zoomable
from pitivi.utils.ui import LAYER_HEIGHT_EXPANDED,\
        LAYER_HEIGHT_COLLAPSED, LAYER_SPACING, \
        unpack_cairo_pattern, unpack_cairo_gradient
from thumbnailer import Preview


#--------------------------------------------------------------#
#                       Private stuff                          #
LEFT_SIDE = gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE)
RIGHT_SIDE = gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE)
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
TRIMBAR_PIXBUF = gtk.gdk.pixbuf_new_from_file(
    os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
TRIMBAR_PIXBUF_FOCUS = gtk.gdk.pixbuf_new_from_file(
    os.path.join(configure.get_pixmap_dir(), "trimbar-focused.png"))
NAME_HOFFSET = 10
NAME_VOFFSET = 5
NAME_PADDING = 2
NAME_PADDING2X = 2 * NAME_PADDING

GlobalSettings.addConfigOption('videoClipBg',
    section='user-interface',
    key='videoclip-background',
    default=993737707,
    notify=True)

PreferencesDialog.addColorPreference('videoClipBg',
    section=_("Appearance"),
    label=_("Color for video clips"),
    description=_("The background color for clips in video tracks."))

GlobalSettings.addConfigOption('audioClipBg',
    section='user-interface',
    key='audioclip-background',
    default=996806336,
    notify=True)

PreferencesDialog.addColorPreference('audioClipBg',
    section=_("Appearance"),
    label=_("Color for audio clips"),
    description=_("The background color for clips in audio tracks."))

GlobalSettings.addConfigOption('selectedColor',
    section='user-interface',
    key='selected-color',
    default=0x00000077,
    notify=True)

PreferencesDialog.addColorPreference('selectedColor',
    section=_("Appearance"),
    label=_("Selection color"),
    description=_("Selected clips will be tinted with this color."))

GlobalSettings.addConfigOption('clipFontDesc',
    section='user-interface',
    key='clip-font-name',
    default="Sans 9",
    notify=True)

PreferencesDialog.addFontPreference('clipFontDesc',
    section=_('Appearance'),
    label=_("Clip font"),
    description=_("The font to use for clip titles"))

GlobalSettings.addConfigOption('clipFontColor',
    section='user-interface',
    key='clip-font-color',
    default=0xFFFFFFAA,
    notify=True)


def text_size(text):
    ink, logical = text.get_natural_extents()
    x1, y1, x2, y2 = [pango.PIXELS(x) for x in logical]
    return x2 - x1, y2 - y1


#--------------------------------------------------------------#
#                            Main Classes                      #
class Selected(Signallable):
    """
    A simple class that let us emit a selected-changed signal
    when needed, and that can be check directly to know if the
    object is selected or not.

    This is meant only for individual elements, do not confuse this with
    utils.timeline's "Selection" class.
    """

    __signals__ = {
        "selected-changed": []}

    def __init__(self):
        self._selected = False
        self.movable = True

    def __nonzero__(self):
        """
        checking a Selected object is the same as checking its _selected
        property
        """
        return self._selected

    def getSelected(self):
        return self._selected

    def setSelected(self, selected):
        self._selected = selected
        self.emit("selected-changed", selected)

    selected = property(getSelected, setSelected)


class TrackObjectController(Controller):

    _cursor = ARROW
    _context = None
    _handle_enter_leave = False
    previous_x = None
    next_previous_x = None
    ref = None

    def __init__(self, instance, default_mode, view=None):
        # Used to force the editing mode in use
        Controller.__init__(self, instance, view)

        self.default_mode = default_mode

    def enter(self, unused, unused2):
        self._view.focus()

    def leave(self, unused, unused2):
        self._view.unfocus()

    def drag_start(self, item, target, event):
        """
            Start draging an element in the Track
        """
        self.debug("Drag started")

        if not self._view.element.selected:
            self._view.timeline.selection.setToObj(self._view.element, SELECT)

        if self.previous_x != None:
            ratio = float(self.ref / Zoomable.pixelToNs(10000000000))
            self.previous_x = self.previous_x * ratio

        self.ref = Zoomable.pixelToNs(10000000000)
        tx = self._view.props.parent.get_transform()

        # store y offset for later priority calculation
        self._y_offset = tx[5]
        # zero y component of mousdown coordiante
        self._mousedown = Point(self._mousedown[0], 0)

    def drag_end(self, item, target, event):
        if not self._view.movable:
            return
        self.debug("Drag end")
        self._context.finish()
        self._context = None
        self._view.app.action_log.commit()

    def set_pos(self, item, pos):
        if not self._view.movable:
            return
        x, y = pos
        x = x + self._hadj.get_value()

        position = Zoomable.pixelToNs(x)
        priority = int((y - self._y_offset + self._vadj.get_value()) //
            (LAYER_HEIGHT_EXPANDED + LAYER_SPACING))

        self._context.setMode(self._getMode())
        self.debug("Setting position")
        self._context.editTo(position, priority)

    def _getMode(self):
        if self._shift_down:
            return ges.EDIT_MODE_RIPPLE
        elif self._control_down:
            return ges.EDIT_MODE_ROLL
        return self.default_mode

    def key_press(self, keyval):
        if self._context:
            self._context.setMode(self._getMode())

    def key_release(self, keyval):
        if self._context:
            self._context.setMode(self._getMode())


class TrimHandle(View, goocanvas.Image, Loggable, Zoomable):

    """A component of a TrackObject which manage's the source's edit
    points"""

    def __init__(self, instance, element, timeline, **kwargs):
        self.app = instance
        self.element = element
        self.timeline = timeline
        self.movable = True
        goocanvas.Image.__init__(self,
            pixbuf=TRIMBAR_PIXBUF,
            line_width=0,
            pointer_events=goocanvas.EVENTS_FILL,
            **kwargs)
        View.__init__(self, instance, ges.EDIT_MODE_TRIM)
        Zoomable.__init__(self)
        Loggable.__init__(self)

    def focus(self):
        self.props.pixbuf = TRIMBAR_PIXBUF_FOCUS

    def unfocus(self):
        self.props.pixbuf = TRIMBAR_PIXBUF


class StartHandle(TrimHandle):

    """Subclass of TrimHandle wich sets the object's start time"""

    class Controller(TrackObjectController):

        _cursor = LEFT_SIDE

        def drag_start(self, item, target, event):
            self.debug("Trim start %s" % target)
            TrackObjectController.drag_start(self, item, target, event)

            if self._view.element.is_locked():
                elem = self._view.element.get_timeline_object()
            else:
                elem = self._view.element

            self._context = EditingContext(elem, self._view.timeline,
                ges.EDIT_MODE_TRIM, ges.EDGE_START, set([]),
                self.app.settings)
            self._context.connect("clip-trim", self.clipTrimCb)
            self._context.connect("clip-trim-finished", self.clipTrimFinishedCb)

            self._view.app.action_log.begin("trim object")

        def clipTrimCb(self, unused_TrimStartContext, tl_obj, position):
            # While a clip is being trimmed, ask the viewer to preview it
            self._view.app.gui.viewer.clipTrimPreview(tl_obj, position)

        def clipTrimFinishedCb(self, unused_TrimStartContext):
            # When a clip has finished trimming, tell the viewer to reset itself
            self._view.app.gui.viewer.clipTrimPreviewFinished()


class EndHandle(TrimHandle):

    """Subclass of TrimHandle which sets the objects's end time"""

    class Controller(TrackObjectController):

        _cursor = RIGHT_SIDE

        def drag_start(self, item, target, event):
            self.debug("Trim end %s" % target)
            TrackObjectController.drag_start(self, item, target, event)

            if self._view.element.is_locked():
                elem = self._view.element.get_timeline_object()
            else:
                elem = self._view.element
            self._context = EditingContext(elem, self._view.timeline,
                ges.EDIT_MODE_TRIM, ges.EDGE_END, set([]),
                self.app.settings)
            self._context.connect("clip-trim", self.clipTrimCb)
            self._context.connect("clip-trim-finished", self.clipTrimFinishedCb)
            self._view.app.action_log.begin("trim object")

        def clipTrimCb(self, unused_TrimStartContext, tl_obj, position):
            # While a clip is being trimmed, ask the viewer to preview it
            self._view.app.gui.viewer.clipTrimPreview(tl_obj, position)

        def clipTrimFinishedCb(self, unused_TrimStartContext):
            # When a clip has finished trimming, tell the viewer to reset itself
            self._view.app.gui.viewer.clipTrimPreviewFinished()


class TrackObject(View, goocanvas.Group, Zoomable, Loggable):

    class Controller(TrackObjectController):

        _handle_enter_leave = True

        def drag_start(self, item, target, event):
            if not self._view.movable:
                return
            point = self.from_item_event(item, event)
            TrackObjectController.drag_start(self, item, target, event)

            self._context = EditingContext(self._view.element,
                self._view.timeline, ges.EDIT_MODE_NORMAL, ges.EDGE_NONE,
                self._view.timeline.selection.getSelectedTrackObjs(),
                self.app.settings)

            self._view.app.action_log.begin("move object")

        def _getMode(self):
            if self._shift_down:
                return ges.EDIT_MODE_RIPPLE
            return ges.EDIT_MODE_NORMAL

        def click(self, pos):
            timeline = self._view.timeline
            element = self._view.element
            if self._last_event.get_state() & gtk.gdk.SHIFT_MASK:
                timeline.selection.setToObj(element, SELECT_BETWEEN)
            elif self._last_event.get_state() & gtk.gdk.CONTROL_MASK:
                if element.selected:
                    mode = UNSELECT
                else:
                    mode = SELECT_ADD
                timeline.selection.setToObj(element, mode)
            else:
                x, y = pos
                x += self._hadj.get_value()
                self._view.app.current.seeker.seek(Zoomable.pixelToNs(x))
                timeline.selection.setToObj(element, SELECT)

    def __init__(self, instance, element, track, timeline, utrack):
        goocanvas.Group.__init__(self)
        View.__init__(self, instance)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.ref = Zoomable.nsToPixel(10000000000)
        self.app = instance
        self.track = track
        self.utrack = utrack
        self.timeline = timeline
        self.namewidth = 0
        self.nameheight = 0
        self._element = None
        self._settings = None
        self.movable = True

        self.bg = goocanvas.Rect(height=self.height, line_width=1)

        self.name = goocanvas.Text(
            x=NAME_HOFFSET + NAME_PADDING,
            y=NAME_VOFFSET + NAME_PADDING,
            operator=cairo.OPERATOR_ADD,
            alignment=pango.ALIGN_LEFT)
        self.namebg = goocanvas.Rect(
            radius_x=2,
            radius_y=2,
            x=NAME_HOFFSET,
            y=NAME_VOFFSET,
            line_width=0)

        self.start_handle = StartHandle(self.app, element, timeline, height=self.height)
        self.end_handle = EndHandle(self.app, element, timeline, height=self.height)

        self._selec_indic = goocanvas.Rect(
            visibility=goocanvas.ITEM_INVISIBLE,
            line_width=0.0,
            height=self.height)

        self.element = element
        element.selected = Selected()
        element.selected.connect("selected-changed", self.selectedChangedCb)
        obj = self.element.get_timeline_object()

        self.settings = instance.settings
        self.unfocus()

## Properties

    _height = LAYER_HEIGHT_EXPANDED

    def setHeight(self, height):
        self._height = height
        self.start_handle.props.height = height
        self.end_handle.props.height = height
        self._update()

    def getHeight(self):
        return self._height

    height = property(getHeight, setHeight)

    _expanded = True

    def setExpanded(self, expanded):
        self._expanded = expanded
        if not self._expanded:
            self.height = LAYER_HEIGHT_COLLAPSED
            self.preview.props.visibility = goocanvas.ITEM_INVISIBLE
            self.namebg.props.visibility = goocanvas.ITEM_INVISIBLE
            self.bg.props.height = LAYER_HEIGHT_COLLAPSED
            self.name.props.y = 0
        else:
            self.height = LAYER_HEIGHT_EXPANDED
            self.preview.props.visibility = goocanvas.ITEM_VISIBLE
            self.namebg.props.visibility = goocanvas.ITEM_VISIBLE
            self.bg.props.height = LAYER_HEIGHT_EXPANDED
            self.height = LAYER_HEIGHT_EXPANDED
            self.name.props.y = NAME_VOFFSET + NAME_PADDING

    def getExpanded(self):
        return self._expanded

    expanded = property(getExpanded, setExpanded)

    def _getColor(self):
        raise NotImplementedError

## Public API

    def focus(self):
        self.start_handle.props.visibility = goocanvas.ITEM_VISIBLE
        self.end_handle.props.visibility = goocanvas.ITEM_VISIBLE
        self.raise_(None)
        for transition in self.utrack.transitions:
            # This is required to ensure that transitions always show on top
            # of the clips on the canvas.
            transition.raise_(None)

    def unfocus(self):
        self.start_handle.props.visibility = goocanvas.ITEM_INVISIBLE
        self.end_handle.props.visibility = goocanvas.ITEM_INVISIBLE

    def zoomChanged(self):
        self._update()

## settings signals

    def setSettings(self, settings):
        target = self._clipAppearanceSettingsChangedCb
        if settings is not None:
            settings.connect("audioClipBgChanged", target)
            settings.connect("videoClipBgChanged", target)
            settings.connect("selectedColorChanged", target)
            settings.connect("clipFontDescChanged", target)
        else:
            self._settings.disconnect_by_func("audioClipBgChanged", target)
            self._settings.disconnect_by_func("videoClipBgChanged", target)
            self._settings.disconnect_by_func("selectedColorChanged", target)
            self._settings.disconnect_by_func("clipFontDescChanged", target)
        self._settings = settings
        # Don't forget to actually create the UI now, or you'll get a segfault
        self._clipAppearanceSettingsChangedCb()

    def getSettings(self):
        return self._settings

    def delSettings(self):
        target = self._clipAppearanceSettingsChangedCb
        if self._settings is not None:
            self._settings.disconnect_by_func("audioClipBgChanged", target)
            self._settings.disconnect_by_func("videoClipBgChanged", target)
            self._settings.disconnect_by_func("selectedColorChanged", target)
            self._settings.disconnect_by_func("clipFontDescChanged", target)
        self._settings = None

    settings = property(getSettings, setSettings, delSettings)

    def _clipAppearanceSettingsChangedCb(self, *args):
        color = self._getColor()
        pattern = unpack_cairo_gradient(color)
        self.bg.props.fill_pattern = pattern
        self.namebg.props.fill_pattern = pattern
        self._selec_indic.props.fill_pattern = unpack_cairo_pattern(self.settings.selectedColor)
        self.name.props.font = self.settings.clipFontDesc
        self.name.props.fill_pattern = unpack_cairo_pattern(self.settings.clipFontColor)
        twidth, theight = text_size(self.name)
        self.namewidth = twidth
        self.nameheight = theight
        self._update()

## element signals

    def _setElement(self, element):
        """
        Virtual method to allow subclasses to override the "setElement" method
        """
        pass

    def setElement(self, element):
        if element is not None:
            element.connect("notify::start", self._updateCb)
            element.connect("notify::duration", self._updateCb)
            element.connect("notify::in-point", self._updateCb)
        else:
            self._element.disconnect_by_func("notify::start", self._updateCb)
            self._element.disconnect_by_func("notify::duration", self._updateCb)
            self._element.disconnect_by_func("notify::in-point", self._updateCb)

        self._element = element
        self._setElement(element)

    def getElement(self):
        return self._element

    def delElement(self):
        if self._element is not None:
            self._element.disconnect_by_func("notify::start", self._updateCb)
            self._element.disconnect_by_func("notify::duration", self._updateCb)
            self._element.disconnect_by_func("notify::in-point", self._updateCb)

        self._element = None

    element = property(getElement, setElement, delElement)

    def _updateCb(self, track_object, start):
        self._update()

    def selectedChangedCb(self, element, unused_selection):
        # Do not confuse this method with _selectionChangedCb in Timeline
        # unused_selection is True only when no clip was selected before
        # Note that element is a track.Selected object,
        # whereas self.element is a GES object (ex: TrackVideoTransition)
        if element.selected:
            if isinstance(self.element, ges.TrackTransition):
                if isinstance(self.element, ges.TrackVideoTransition):
                    self.app.gui.trans_list.activate(self.element)
            else:
                self.app.gui.trans_list.deactivate()
                self.app.gui.switchContextTab()
            self._selec_indic.props.visibility = goocanvas.ITEM_VISIBLE
        else:
            self._selec_indic.props.visibility = goocanvas.ITEM_INVISIBLE

    def _update(self):
        # Calculating the new position
        try:
            x = self.nsToPixel(self.element.get_start())
        except Exception, e:
            raise Exception(e)

        layer = self.element.get_timeline_object().get_layer()
        track_type = self.element.get_track().props.track_type

        # calculate correct y-position, highest priority on top
        y = self.app.gui.timeline_ui._controls.getYOfLayer(track_type, layer)
        #priority = self.element.get_timeline_object().get_layer().get_priority()
        #y = (self.height + LAYER_SPACING) * priority
        print y

        # Setting new position
        self.set_simple_transform(x, y, 1, 0)
        width = self.nsToPixel(self.element.get_duration())

        # Handle a duration of 0
        handles_width = self.start_handle.props.width
        min_width = handles_width * 2
        if width < min_width:
            width = min_width
        w = width - handles_width
        self.name.props.clip_path = "M%g,%g h%g v%g h-%g z" % (0, 0, w, self.height, w)
        self.bg.props.width = width

        self._selec_indic.props.width = width
        self.end_handle.props.x = w

        if self.expanded:
            if w - NAME_HOFFSET > 0:
                self.namebg.props.height = self.nameheight + NAME_PADDING2X
                self.namebg.props.width = min(w - NAME_HOFFSET,
                    self.namewidth + NAME_PADDING2X)
                self.namebg.props.visibility = goocanvas.ITEM_VISIBLE
            else:
                self.namebg.props.visibility = goocanvas.ITEM_INVISIBLE

        self.app.gui.timeline_ui._canvas.regroupTracks()
        self.app.gui.timeline_ui.unsureVadjHeight()


class TrackTransition(TrackObject):
    """
    Subclass of TrackObject to account for the differences of transition objects
    """
    def __init__(self, instance, element, track, timeline, utrack):
        TrackObject.__init__(self, instance, element, track, timeline, utrack)
        for thing in (self.bg, self._selec_indic, self.namebg, self.name):
            self.add_child(thing)
        if isinstance(element, ges.TrackVideoTransition):
            element.connect("notify::transition-type", self._changeVideoTransitionCb)
        self.movable = False

    def _setElement(self, element):
        if isinstance(element, ges.TrackVideoTransition):
            self.name.props.text = element.props.transition_type.value_nick

    def _getColor(self):
        # Transitions are bright blue, independent of the user color settings
        return 0x0089CFF0

    def _changeVideoTransitionCb(self, transition, unused_transition_type):
        self.name.props.text = transition.props.transition_type.value_nick


class TrackFileSource(TrackObject):
    """
    Subclass of TrackObject to allow thumbnailing of objects with URIs
    """
    def __init__(self, instance, element, track, timeline, utrack):
        TrackObject.__init__(self, instance, element, track, timeline, utrack)
        self.preview = Preview(self.app, element)
        for thing in (self.bg, self.preview, self._selec_indic,
            self.start_handle, self.end_handle, self.namebg, self.name):
            self.add_child(thing)

    def _setElement(self, element):
        """
        Set the human-readable file name as the clip's text label
        """
        if self.element:
            uri = self.element.props.uri
            info = self.app.current.medialibrary.getInfoFromUri(uri)
            self.name.props.text = info_name(info)
            twidth, theight = text_size(self.name)
            self.namewidth = twidth
            self.nameheight = theight
            self._update()

    def _getColor(self):
        if self.element.get_track().props.track_type == ges.TRACK_TYPE_AUDIO:
            return self.settings.audioClipBg
        else:
            return self.settings.videoClipBg


class Track(goocanvas.Group, Zoomable, Loggable):
    """
    Groups all TrackObjects of one Track
    """
    __gtype_name__ = 'Track'

    def __init__(self, instance, track, timeline=None):
        goocanvas.Group.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)
        self.app = instance
        self.widgets = {}
        self.transitions = []
        self.timeline = timeline
        self._track = None
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

    def getTrack(self):
        return self._track

    def setTrack(self, track):
        if self._track:
            self._track.disconnect_by_func(self._objectAddedCb)
            self._track.disconnect_by_func(self._objectRemovedCb)
            for trackobj in self._track.get_objects():
                self._objectRemovedCb(None, trackobj)

        self._track = track
        if track:
            for trackobj in self.track.get_objects():
                self._objectAddedCb(None, trackobj)
            self._track.connect("track-object-added", self._objectAddedCb)
            self._track.connect("track-object-removed", self._objectRemovedCb)

    track = property(getTrack, setTrack, None, "The timeline property")

    def _objectAddedCb(self, unused_timeline, track_object):
        if isinstance(track_object, ges.TrackTransition):
            self._transitionAdded(track_object)
        elif isinstance(track_object, ges.TrackSource):
            w = TrackFileSource(self.app, track_object, self.track, self.timeline, self)
            self.widgets[track_object] = w
            self.add_child(w)

    def _objectRemovedCb(self, unused_timeline, track_object):
        if not isinstance(track_object, ges.TrackEffect) and track_object in self.widgets:
            w = self.widgets[track_object]
            del self.widgets[track_object]
            self.remove_child(w)
            Zoomable.removeInstance(w)

    def _transitionAdded(self, transition):
        w = TrackTransition(self.app, transition, self.track, self.timeline, self)
        self.widgets[transition] = w
        self.add_child(w)
        self.transitions.append(w)
        w.raise_(None)
