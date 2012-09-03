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

import cairo
import os.path

from gi.repository import GooCanvas
from gi.repository import GES
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Pango

from gettext import gettext as _

import pitivi.configure as configure
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import Point, info_name
from pitivi.settings import GlobalSettings
from pitivi.utils.signal import Signallable
from pitivi.utils.timeline import SELECT, SELECT_ADD, UNSELECT, \
    SELECT_BETWEEN, EditingContext, Controller, View, Zoomable
from thumbnailer import Preview


#--------------------------------------------------------------#
#                       Private stuff                          #
LEFT_SIDE = Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE)
RIGHT_SIDE = Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE)
ARROW = Gdk.Cursor.new(Gdk.CursorType.ARROW)
TRIMBAR_PIXBUF = GdkPixbuf.Pixbuf.new_from_file(
    os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
TRIMBAR_PIXBUF_FOCUS = GdkPixbuf.Pixbuf.new_from_file(
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

GlobalSettings.addConfigOption('titleClipBg',
    section='user-interface',
    key='titleclip-background',
    default=996806336,
    notify=True)

PreferencesDialog.addColorPreference('titleClipBg',
    section=_("Appearance"),
    label=_("Color for title clips"),
    description=_("The background color for clips in title tracks."))


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
    logical = Pango.Rectangle()
    tmp = Pango.Rectangle()
    text.get_natural_extents(tmp, logical)
    Pango.extents_to_pixels(logical, tmp)
    return tmp.width, tmp.height


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
        tx = self._view.props.parent.get_simple_transform()

        # store y offset for later priority calculation
        self._y_offset = tx[4]
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
        priority = self.app.gui.timeline_ui.controls.getPriorityForY(
                        y - self._y_offset + self._vadj.get_value())

        self._context.setMode(self._getMode())
        self.debug("Setting position")
        self._context.editTo(position, priority)

    def _getMode(self):
        if self._shift_down:
            return GES.EditMode.EDIT_RIPPLE
        elif self._control_down:
            return GES.EditMode.EDIT_ROLL
        return self.default_mode

    def key_press(self, keyval):
        if self._context:
            self._context.setMode(self._getMode())

    def key_release(self, keyval):
        if self._context:
            self._context.setMode(self._getMode())


class TrimHandle(View, GooCanvas.CanvasImage, Loggable, Zoomable):

    """A component of a TrackObject which manage's the source's edit
    points"""

    def __init__(self, instance, element, timeline, **kwargs):
        self.app = instance
        self.element = element
        self.timeline = timeline
        self.movable = True
        self.current_pixbuf = TRIMBAR_PIXBUF
        GooCanvas.CanvasImage.__init__(self,
            pixbuf=self.current_pixbuf,
            line_width=0,
            pointer_events=GooCanvas.CanvasPointerEvents.FILL,
            **kwargs)
        View.__init__(self, instance, GES.EditMode.EDIT_TRIM)
        Zoomable.__init__(self)
        Loggable.__init__(self)

    def focus(self):
        self.current_pixbuf = TRIMBAR_PIXBUF_FOCUS
        self._scalePixbuf()

    def unfocus(self):
        self.current_pixbuf = TRIMBAR_PIXBUF
        self._scalePixbuf()

    _height = 0

    def setHeight(self, height):
        self._height = height
        self.props.height = height
        self._scalePixbuf()

    def getHeight(self):
        return self._height

    height = property(getHeight, setHeight)

    def _scalePixbuf(self):
        self.props.pixbuf = self.current_pixbuf.scale_simple(
                                                self.current_pixbuf.get_width(),
                                                self.height,
                                                GdkPixbuf.InterpType.BILINEAR)


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
                GES.EditMode.EDIT_TRIM, GES.Edge.EDGE_START, set([]),
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
                GES.EditMode.EDIT_TRIM, GES.Edge.EDGE_END, set([]),
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


#FIXME PyGI Missing anotation in GooItem(bug 677013), reimplement
def raise_new(self, above):
    parent = self.get_parent()
    if parent is None or above == self:
        return
    n_children = parent.get_n_children()
    for i in range(n_children):
        child = parent.get_child(i)
        if (child == self):
            item_pos = i
        if (child == above):
            above_pos = i
    if above is None:
        above_pos = n_children - 1
    if (above_pos > item_pos):
        parent.move_child(item_pos, above_pos)


setattr(GooCanvas.CanvasItem, "raise_", raise_new)


class TrackObject(View, GooCanvas.CanvasGroup, Zoomable, Loggable):

    class Controller(TrackObjectController):

        _handle_enter_leave = True

        def drag_start(self, item, target, event):
            if not self._view.movable:
                return

            TrackObjectController.drag_start(self, item, target, event)

            self._context = EditingContext(self._view.element,
                self._view.timeline, GES.EditMode.EDIT_NORMAL, GES.Edge.EDGE_NONE,
                self._view.timeline.selection.getSelectedTrackObjs(),
                self.app.settings)

            self._view.app.action_log.begin("move object")

        def _getMode(self):
            if self._shift_down:
                return GES.EditMode.EDIT_RIPPLE
            return GES.EditMode.EDIT_NORMAL

        def click(self, pos):
            timeline = self._view.timeline
            element = self._view.element
            if self._last_event.get_state()[1] & Gdk.ModifierType.SHIFT_MASK:
                timeline.selection.setToObj(element, SELECT_BETWEEN)
            elif self._last_event.get_state()[1] & Gdk.ModifierType.CONTROL_MASK:
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
        GooCanvas.CanvasGroup.__init__(self)
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

        self.bg = GooCanvas.CanvasRect(height=self.height, line_width=1)

        self.name = GooCanvas.CanvasText(
            x=NAME_HOFFSET + NAME_PADDING,
            y=NAME_VOFFSET + NAME_PADDING,
            operator=cairo.OPERATOR_ADD,
            alignment=Pango.Alignment.LEFT)
        self.namebg = GooCanvas.CanvasRect(
            radius_x=2,
            radius_y=2,
            x=NAME_HOFFSET,
            y=NAME_VOFFSET,
            line_width=0)

        self.start_handle = StartHandle(self.app, element, timeline, height=self.height)
        self.end_handle = EndHandle(self.app, element, timeline, height=self.height)

        self._selec_indic = GooCanvas.CanvasRect(
            visibility=GooCanvas.CanvasItemVisibility.INVISIBLE,
            line_width=0.0,
            height=self.height)

        self.element = element
        element.selected = Selected()
        element.selected.connect("selected-changed", self.selectedChangedCb)

        self.settings = instance.settings
        self.unfocus()

## Properties

    _height = 0

    def setHeight(self, height):
        self._height = height
        self.bg.props.height = height
        self.start_handle.height = height
        self.end_handle.height = height
        self._selec_indic.props.height = height
        if hasattr(self, "preview"):
            self.preview.height = height
        self._update()

    def getHeight(self):
        return self._height

    height = property(getHeight, setHeight)

    _expanded = True

    def setExpanded(self, expanded):
        self._expanded = expanded
        if not self._expanded:
            self.preview.props.visibility = GooCanvas.CanvasItemVisibility.INVISIBLE
            self.namebg.props.visibility = GooCanvas.CanvasItemVisibility.INVISIBLE
            self.name.props.y = 0
        else:
            self.preview.props.visibility = GooCanvas.CanvasItemVisibility.VISIBLE
            self.namebg.props.visibility = GooCanvas.CanvasItemVisibility.VISIBLE
            self.name.props.y = NAME_VOFFSET + NAME_PADDING

    def getExpanded(self):
        return self._expanded

    expanded = property(getExpanded, setExpanded)

    def _getColor(self):
        raise NotImplementedError

## Public API

    def focus(self):
        self.start_handle.props.visibility = GooCanvas.CanvasItemVisibility.VISIBLE
        self.end_handle.props.visibility = GooCanvas.CanvasItemVisibility.VISIBLE
        self.raise_(None)
        for transition in self.utrack.transitions:
            # This is required to ensure that transitions always show on top
            # of the clips on the canvas.
            transition.raise_(None)

    def unfocus(self):
        self.start_handle.props.visibility = GooCanvas.CanvasItemVisibility.INVISIBLE
        self.end_handle.props.visibility = GooCanvas.CanvasItemVisibility.INVISIBLE

    def zoomChanged(self):
        self._update()

## settings signals

    def setSettings(self, settings):
        target = self._clipAppearanceSettingsChangedCb
        if settings is not None:
            settings.connect("audioClipBgChanged", target)
            settings.connect("videoClipBgChanged", target)
            settings.connect("titleClipBgChanged", target)
            settings.connect("selectedColorChanged", target)
            settings.connect("clipFontDescChanged", target)
        else:
            self._settings.disconnect_by_func("audioClipBgChanged", target)
            self._settings.disconnect_by_func("videoClipBgChanged", target)
            self._settings.disconnect_by_func("titleClipBgChanged", target)
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
            self._settings.disconnect_by_func("titleClipBgChanged", target)
            self._settings.disconnect_by_func("selectedColorChanged", target)
            self._settings.disconnect_by_func("clipFontDescChanged", target)
        self._settings = None

    settings = property(getSettings, setSettings, delSettings)

    def _clipAppearanceSettingsChangedCb(self, *args):
        color = self._getColor()
        self.bg.props.fill_color_rgba = color
        self.namebg.props.fill_color_rgba = color
        self._selec_indic.props.fill_color_rgba = self.settings.selectedColor
        self.name.props.font = self.settings.clipFontDesc
        self.name.props.fill_color_rgba = self.settings.clipFontColor
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
            if isinstance(self.element, GES.TrackTransition):
                if isinstance(self.element, GES.TrackVideoTransition):
                    self.app.gui.trans_list.activate(self.element)
            elif isinstance(self.element, GES.TrackTitleSource):
                self.app.gui.switchContextTab("title editor")
                self.app.gui.title_editor.set_source(self.element.get_timeline_object())
            else:
                if self.element.get_track().get_property("track_type") == GES.TrackType.VIDEO:
                    has_text_overlay = False
                    tlobj = self.element.get_timeline_object()
                    trackobjs = tlobj.get_track_objects()
                    for trackobj in trackobjs:
                        if isinstance(trackobj, GES.TrackTextOverlay):
                            has_text_overlay = True
                            title = trackobj
                    if not has_text_overlay:
                        title = GES.TrackTextOverlay()
                        title.set_text("")
                        title.set_start(self.element.get_start())
                        title.set_duration(self.element.get_duration())
                        # FIXME: Creating a text overlay everytime we select a video track object is madness
                        self.element.get_timeline_object().add_track_object(title)
                        self.element.get_track().add_object(title)
                    self.app.gui.title_editor.set_source(title)
                self.app.gui.trans_list.deactivate()
                self.app.gui.switchContextTab()
            self._selec_indic.props.visibility = GooCanvas.CanvasItemVisibility.VISIBLE
        else:
            self.app.gui.title_editor.set_source(None)
            self._selec_indic.props.visibility = GooCanvas.CanvasItemVisibility.INVISIBLE

    def _update(self):
        # Calculating the new position
        try:
            x = self.nsToPixel(self.element.get_start())
        except Exception, e:
            raise Exception(e)

        # get layer and track_type
        layer = self.element.get_timeline_object().get_layer()
        track_type = self.element.get_track().get_property("track-type")

        # update height, compare with current height to not run into recursion
        new_height = self.app.gui.timeline_ui.controls.getHeightOfLayer(track_type, layer)
        if self.height != new_height:
            self.height = new_height

        # get y position for layer
        y = self.app.gui.timeline_ui.controls.getYOfLayer(track_type, layer)
        # get relative y for audio
        if track_type == GES.TrackType.AUDIO:
            y -= self.app.gui.timeline_ui.controls.getHeightOfTrack(GES.TrackType.VIDEO)

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
                self.namebg.props.visibility = GooCanvas.CanvasItemVisibility.VISIBLE
            else:
                self.namebg.props.visibility = GooCanvas.CanvasItemVisibility.INVISIBLE

        self.app.gui.timeline_ui._canvas.regroupTracks()
        self.app.gui.timeline_ui.unsureVadjHeight()


class TrackTransition(TrackObject):
    """
    Subclass of TrackObject to account for the differences of transition objects
    """
    def __init__(self, instance, element, track, timeline, utrack):
        TrackObject.__init__(self, instance, element, track, timeline, utrack)
        for thing in (self.bg, self._selec_indic, self.namebg, self.name):
            self.add_child(thing, -1)
        if isinstance(element, GES.TrackVideoTransition):
            element.connect("notify::transition-type", self._changeVideoTransitionCb)
        self.movable = False

    def _setElement(self, element):
        if isinstance(element, GES.TrackVideoTransition):
            self.name.props.text = element.props.transition_type.value_nick

    def _getColor(self):
        # Transitions are bright blue, independent of the user color settings
        return 0x0089CFF0

    def _changeVideoTransitionCb(self, transition, unused_transition_type):
        self.name.props.text = transition.props.transition_type.value_nick


class TrackTitleSource(TrackObject):
    """
    Subclass of TrackObject for titles
    """
    def __init__(self, instance, element, track, timeline, utrack):
        TrackObject.__init__(self, instance, element, track, timeline, utrack)
        #self.preview = Preview(self.app, element)
        for thing in (self.bg, self._selec_indic,
            self.start_handle, self.end_handle, self.namebg, self.name):
            self.add_child(thing, -1)

    def _getColor(self):
        return self.settings.titleClipBg

    def _setElement(self, element):
        if self.element:
            text = self.element.get_text()
            _, _, t, _ = Pango.parse_markup(text, -1, u'\x00')
            #TODO trim text, first line etc
            self.name.props.text = t
            twidth, theight = text_size(self.name)
            self.namewidth = twidth
            self.nameheight = theight
            self._update()


class TrackFileSource(TrackObject):
    """
    Subclass of TrackObject to allow thumbnailing of objects with URIs
    """
    def __init__(self, instance, element, track, timeline, utrack):
        TrackObject.__init__(self, instance, element, track, timeline, utrack)
        self.preview = Preview(self.app, element, self.height)
        for thing in (self.bg, self.preview, self._selec_indic,
            self.start_handle, self.end_handle, self.namebg, self.name):
            self.add_child(thing, -1)

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
        if self.element.get_track().get_property("track-type") == GES.TrackType.AUDIO:
            return self.settings.audioClipBg
        else:
            return self.settings.videoClipBg


class Track(GooCanvas.CanvasGroup, Zoomable, Loggable):
    """
    Groups all TrackObjects of one Track
    """
    __gtype_name__ = 'Track'

    def __init__(self, instance, track, timeline=None):
        GooCanvas.CanvasGroup.__init__(self)
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
        track_type = self.track.get_property("track-type")
        return self.app.gui.timeline_ui.controls.getHeightOfTrack(track_type)

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
        if isinstance(track_object, GES.TrackTransition):
            self._transitionAdded(track_object)
        elif isinstance(track_object, GES.TrackTitleSource):
            w = TrackTitleSource(self.app, track_object, self.track, self.timeline, self)
            self.widgets[track_object] = w
            self.add_child(w, -1)
        elif isinstance(track_object, GES.TrackFileSource):
            w = TrackFileSource(self.app, track_object, self.track, self.timeline, self)
            self.widgets[track_object] = w
            self.add_child(w, -1)

    def _objectRemovedCb(self, unused_timeline, track_object):
        if not isinstance(track_object, GES.TrackEffect) and track_object in self.widgets:
            w = self.widgets[track_object]
            del self.widgets[track_object]
            self.remove_child(self.find_child(w))
            Zoomable.removeInstance(w)

    def _transitionAdded(self, transition):
        w = TrackTransition(self.app, transition, self.track, self.timeline, self)
        self.widgets[transition] = w
        self.add_child(w, -1)
        self.transitions.append(w)
        w.raise_(None)

    def updateTrackObjects(self):
        for track_object in self.widgets.itervalues():
            track_object._update()
