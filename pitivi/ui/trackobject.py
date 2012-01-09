import goocanvas
import gtk
import os.path
import pango
import cairo

import pitivi.configure as configure
import controller

from view import View
from gettext import gettext as _
from zoominterface import Zoomable
from pitivi.utils.ui import LAYER_SPACING, unpack_cairo_pattern, \
    unpack_cairo_gradient, LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED

from pitivi.ui.point import Point
from pitivi.utils.loggable import Loggable
from pitivi.settings import GlobalSettings
from pitivi.receiver import receiver, handler
from pitivi.ui.prefs import PreferencesDialog
from pitivi.utils.signal import Signallable
from pitivi.utils.timeline import SELECT, SELECT_ADD, UNSELECT, \
    SELECT_BETWEEN, MoveContext, TrimStartContext, TrimEndContext


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
    default=0x000000A0,
    notify=True)

PreferencesDialog.addColorPreference('videoClipBg',
    section=_("Appearance"),
    label=_("Color for video clips"),
    description=_("The background color for clips in video tracks."))

GlobalSettings.addConfigOption('audioClipBg',
    section='user-interface',
    key='audioclip-background',
    default=0x4E9A06C0,
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
class Selected (Signallable):
    """
    A simple class that let us emit a selected-changed signal
    when needed, and that can be check directly to know if the
    object is selected or not.
    """

    __signals__ = {
        "selected-changed": []}

    def __init__(self):
        self._selected = False

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


class TimelineController(controller.Controller):

    _cursor = ARROW
    _context = None
    _handle_enter_leave = False
    previous_x = None
    next_previous_x = None
    ref = None

    def enter(self, unused, unused2):
        self._view.focus()

    def leave(self, unused, unused2):
        self._view.unfocus()

    def drag_start(self, item, target, event):
        self.debug("Drag started")
        if not self._view.element.selected:
            self._view.timeline.selection.setToObj(self._view.element, SELECT)
        if self.previous_x != None:
            ratio = float(self.ref / Zoomable.pixelToNs(10000000000))
            self.previous_x = self.previous_x * ratio
        self.ref = Zoomable.pixelToNs(10000000000)
        self._view.app.projectManager.current.timeline.enable_update(False)
        tx = self._view.props.parent.get_transform()
        # store y offset for later priority calculation
        self._y_offset = tx[5]
        # zero y component of mousdown coordiante
        self._mousedown = Point(self._mousedown[0], 0)

    def drag_end(self, item, target, event):
        self.debug("Drag end")
        self._context.finish()
        self._context = None
        self._view.app.projectManager.current.timeline.enable_update(True)
        self._view.app.action_log.commit()
        self._view.element.starting_start = self._view.element.props.start
        obj = self._view.element.get_timeline_object()
        obj.starting_start = obj.props.start
        self.previous_x = self.next_previous_x

    def set_pos(self, item, pos):
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
            return self._context.RIPPLE
        elif self._control_down:
            return self._context.ROLL
        return self._context.DEFAULT

    def key_press(self, keyval):
        if self._context:
            self._context.setMode(self._getMode())

    def key_release(self, keyval):
        if self._context:
            self._context.setMode(self._getMode())


class TrimHandle(View, goocanvas.Image, Loggable, Zoomable):

    """A component of a TrackObject which manage's the source's edit
    points"""

    element = receiver()

    def __init__(self, instance, element, timeline, **kwargs):
        self.app = instance
        self.element = element
        self.timeline = timeline
        goocanvas.Image.__init__(self,
            pixbuf=TRIMBAR_PIXBUF,
            line_width=0,
            pointer_events=goocanvas.EVENTS_FILL,
            **kwargs)
        View.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

    def focus(self):
        self.props.pixbuf = TRIMBAR_PIXBUF_FOCUS

    def unfocus(self):
        self.props.pixbuf = TRIMBAR_PIXBUF


class StartHandle(TrimHandle):

    """Subclass of TrimHandle wich sets the object's start time"""

    class Controller(TimelineController):

        _cursor = LEFT_SIDE

        def drag_start(self, item, target, event):
            self.debug("Trim start %s" % target)
            TimelineController.drag_start(self, item, target, event)
            if self._view.element.is_locked():
                elem = self._view.element.get_timeline_object()
            else:
                elem = self._view.element
            self._context = TrimStartContext(self._view.timeline,
                elem, set([]))
            self._view.app.action_log.begin("trim object")


class EndHandle(TrimHandle):

    """Subclass of TrimHandle which sets the objects's end time"""

    class Controller(TimelineController):

        _cursor = RIGHT_SIDE

        def drag_start(self, item, target, event):
            self.debug("Trim end %s" % target)
            TimelineController.drag_start(self, item, target, event)
            if self._view.element.is_locked():
                elem = self._view.element.get_timeline_object()
            else:
                elem = self._view.element
            self._context = TrimEndContext(self._view.timeline,
                elem, set([]))
            self._view.app.action_log.begin("trim object")


class TrackObject(View, goocanvas.Group, Zoomable):

    class Controller(TimelineController):

        _handle_enter_leave = True

        def drag_start(self, item, target, event):
            point = self.from_item_event(item, event)
            TimelineController.drag_start(self, item, target, event)
            self._context = MoveContext(self._view.timeline,
                self._view.element, self._view.timeline.selection.getSelectedTrackObjs())
            self._view.app.action_log.begin("move object")

        def _getMode(self):
            if self._shift_down:
                return self._context.RIPPLE
            return self._context.DEFAULT

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

    def __init__(self, instance, element, track, timeline, utrack, is_transition=False):
        goocanvas.Group.__init__(self)
        View.__init__(self)
        Zoomable.__init__(self)
        self.ref = Zoomable.nsToPixel(10000000000)
        self.app = instance
        self.track = track
        self.utrack = utrack
        self.timeline = timeline
        self.namewidth = 0
        self.nameheight = 0
        self.is_transition = is_transition

        self.snapped_before = False
        self.snapped_after = False

        self.bg = goocanvas.Rect(
            height=self.height,
            line_width=1)

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

        self.start_handle = StartHandle(self.app, element, timeline,
            height=self.height)
        self.end_handle = EndHandle(self.app, element, timeline,
            height=self.height)

        self._selec_indic = goocanvas.Rect(
            visibility=goocanvas.ITEM_INVISIBLE,
            line_width=0.0,
            height=self.height)

        if not self.is_transition:
            for thing in (self.bg, self._selec_indic,
                self.start_handle, self.end_handle, self.namebg, self.name):
                self.add_child(thing)
        else:
            for thing in (self.bg, self.name):
                self.add_child(thing)

        self.element = element
        element.max_duration = element.props.duration
        element.starting_start = element.props.start
        element.selected = Selected()
        element.selected.connect("selected-changed", self.selectedChangedCb)

        obj = self.element.get_timeline_object()
        obj.starting_start = obj.get_property("start")
        obj.max_duration = obj.props.duration

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
            self.content.props.visibility = goocanvas.ITEM_INVISIBLE
            self.namebg.props.visibility = goocanvas.ITEM_INVISIBLE
            self.bg.props.height = LAYER_HEIGHT_COLLAPSED
            self.name.props.y = 0
        else:
            self.height = LAYER_HEIGHT_EXPANDED
            self.content.props.visibility = goocanvas.ITEM_VISIBLE
            self.namebg.props.visibility = goocanvas.ITEM_VISIBLE
            self.bg.props.height = LAYER_HEIGHT_EXPANDED
            self.height = LAYER_HEIGHT_EXPANDED
            self.name.props.y = NAME_VOFFSET + NAME_PADDING

    def getExpanded(self):
        return self._expanded

    expanded = property(getExpanded, setExpanded)

## Public API

    def focus(self):
        self.start_handle.props.visibility = goocanvas.ITEM_VISIBLE
        self.end_handle.props.visibility = goocanvas.ITEM_VISIBLE
        self.raise_(None)
        for transition in self.utrack.transitions:
            transition.raise_(None)

    def unfocus(self):
        self.start_handle.props.visibility = goocanvas.ITEM_INVISIBLE
        self.end_handle.props.visibility = goocanvas.ITEM_INVISIBLE

    def zoomChanged(self):
        self._update()

## settings signals

    def _setSettings(self):
        if self.settings:
            self.clipAppearanceSettingsChanged()

    settings = receiver(_setSettings)

    @handler(settings, "audioClipBgChanged")
    @handler(settings, "videoClipBgChanged")
    @handler(settings, "selectedColorChanged")
    @handler(settings, "clipFontDescChanged")
    def clipAppearanceSettingsChanged(self, *args):
        if self.element.get_track().props.track_type.first_value_name == 'GES_TRACK_TYPE_AUDIO':
            color = self.settings.audioClipBg
        else:
            color = self.settings.videoClipBg
        if self.is_transition:
            color = 0x0089CFF0
        pattern = unpack_cairo_gradient(color)
        self.bg.props.fill_pattern = pattern

        self.namebg.props.fill_pattern = pattern

        self._selec_indic.props.fill_pattern = unpack_cairo_pattern(
            self.settings.selectedColor)

        self.name.props.font = self.settings.clipFontDesc
        self.name.props.fill_pattern = unpack_cairo_pattern(
            self.settings.clipFontColor)
        twidth, theight = text_size(self.name)
        self.namewidth = twidth
        self.nameheight = theight
        self._update()

## element signals

    def _setElement(self):
        if self.element and not self.is_transition:
            from pitivi.utils.ui import info_name

            sources = self.app.current.sources
            uri = self.element.props.uri
            info = sources.getInfoFromUri(uri)
            self.name.props.text = info_name(info)
            twidth, theight = text_size(self.name)
            self.namewidth = twidth
            self.nameheight = theight
            self._update()

    element = receiver(_setElement)

    @handler(element, "notify::start")
    @handler(element, "notify::duration")
    @handler(element, "notify::in-point")
    def startChangedCb(self, track_object, start):
        self._update()

    def selectedChangedCb(self, element, selected):
        if element.selected:
            self._selec_indic.props.visibility = goocanvas.ITEM_VISIBLE
        else:
            self._selec_indic.props.visibility = goocanvas.ITEM_INVISIBLE

    def _update(self):
        try:
            x = self.nsToPixel(self.element.get_start())
        except Exception, e:
            raise Exception(e)
        priority = (self.element.get_priority()) / 1000
        if priority < 0:
            priority = 0
        y = (self.height + LAYER_SPACING) * priority
        self.set_simple_transform(x, y, 1, 0)
        width = self.nsToPixel(self.element.get_duration())
        min_width = self.start_handle.props.width * 2
        if width < min_width:
            width = min_width
        w = width - self.end_handle.props.width
        self.name.props.clip_path = "M%g,%g h%g v%g h-%g z" % (
            0, 0, w, self.height, w)
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
        self.app.gui.timeline._canvas.regroupTracks()
        self.app.gui.timeline.unsureVadjHeight()
