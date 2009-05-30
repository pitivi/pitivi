import goocanvas
import gobject
import gtk
import os.path
import pango
import cairo
import pitivi.configure as configure
from urllib import unquote
from gettext import gettext as _
from pitivi.receiver import receiver, handler
from view import View
import controller
from zoominterface import Zoomable
from pitivi.timeline.track import TrackError
from pitivi.timeline.timeline import SELECT, SELECT_ADD, UNSELECT
from preview import Preview
from pitivi.ui.curve import Curve
import gst
from common import LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED
from common import LAYER_SPACING, unpack_cairo_pattern, unpack_cairo_gradient
from pitivi.ui.point import Point
from pitivi.ui.prefs import PreferencesDialog
from pitivi.settings import GlobalSettings
from pitivi.stream import AudioStream, VideoStream

LEFT_SIDE = gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE)
RIGHT_SIDE = gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE)
ARROW = gtk.gdk.Cursor(gtk.gdk.ARROW)
TRIMBAR_PIXBUF = gtk.gdk.pixbuf_new_from_file(
    os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
TRIMBAR_PIXBUF_FOCUS = gtk.gdk.pixbuf_new_from_file(
    os.path.join(configure.get_pixmap_dir(), "trimbar-focused.png"))

import gst

GlobalSettings.addConfigOption('videoClipBg',
    section = 'user-interface',
    key = 'videoclip-background',
    default = 0x3182bdC0,
    notify = True)

PreferencesDialog.addColorPreference('videoClipBg',
    section = _("Appearance"),
    label = _("Clip Background (Video)"),
    description = _("The background color for clips in video tracks."))

GlobalSettings.addConfigOption('audioClipBg',
    section = 'user-interface',
    key = 'audioclip-background',
    default = 0x3182bdC0,
    notify = True)

PreferencesDialog.addColorPreference('audioClipBg',
    section = _("Appearance"),
    label = _("Clip Background (Audio)"),
    description = _("The background color for clips in audio tracks."))

GlobalSettings.addConfigOption('selectedColor',
    section = 'user-interface',
    key = 'selected-color',
    default = 0x00000077,
    notify = True)

PreferencesDialog.addColorPreference('selectedColor',
    section = _("Appearance"),
    label = _("Selection Color"),
    description = _("Selected clips will be tinted with this color."))

GlobalSettings.addConfigOption('clipFontDesc',
    section = 'user-interface',
    key = 'clip-font-name',
    default = "Sans 9",
    notify = True)

PreferencesDialog.addFontPreference('clipFontDesc',
    section = _('Appearance'),
    label = _("Clip Font"),
    description = _("The font to use for clip titles"))

GlobalSettings.addConfigOption('clipFontColor',
    section = 'user-interface',
    key = 'clip-font-color',
    default = 0xFFFFFFAA,
    notify = True)

def text_size(text):
    ink, logical = text.get_natural_extents()
    x1, y1, x2, y2 = [pango.PIXELS(x) for x in logical]
    return x2 - x1, y2 - y1

class TimelineController(controller.Controller):

    _cursor = ARROW

    def enter(self, unused, unused2):
        self._view.focus()

    def leave(self, unused, unused2):
        self._view.unfocus()

    def drag_start(self, item, target, event):
        pass

    def drag_end(self, item, target, event):
        self._view.timeline.rebuildEdges()

class TrimHandle(View, goocanvas.Image, Zoomable):

    """A component of a TrackObject which manage's the source's edit
    points"""

    element = receiver()

    def __init__(self, instance, element, timeline, **kwargs):
        self.app = instance
        self.element = element
        self.timeline = timeline
        goocanvas.Image.__init__(self,
            pixbuf = TRIMBAR_PIXBUF,
            line_width=0,
            **kwargs
        )
        View.__init__(self)
        Zoomable.__init__(self)

    def focus(self):
        self.props.pixbuf = TRIMBAR_PIXBUF_FOCUS

    def unfocus(self):
        self.props.pixbuf = TRIMBAR_PIXBUF

class StartHandle(TrimHandle):

    """Subclass of TrimHandle wich sets the object's start time"""

    class Controller(TimelineController):

        _cursor = LEFT_SIDE

        def drag_start(self, item, target, event):
            TimelineController.drag_start(self, item, target, event)
            self._view.app.action_log.begin("trim object")

        def drag_end(self, item, target, event):
            TimelineController.drag_end(self, item, target, event)
            self._view.app.action_log.commit()

        def set_pos(self, obj, pos):
            new_start = max(self._view.pixelToNs(pos[0]), 0)
            self._view.element.trimStart(new_start, snap=True)

class EndHandle(TrimHandle):

    """Subclass of TrimHandle which sets the objects's end time"""

    class Controller(TimelineController):

        _cursor = RIGHT_SIDE

        def drag_start(self, item, target, event):
            TimelineController.drag_start(self, item, target, event)
            self._view.app.action_log.begin("trim object")

        def drag_end(self, item, target, event):
            TimelineController.drag_end(self, item, target, event)
            self._view.app.action_log.commit()

        def set_pos(self, obj, pos):
            start = self._view.element.start
            abs_pos = self._view.pixelToNs(pos[0])
            duration = max(abs_pos - start, 0)
            self._view.element.setDuration(duration, snap=True)

class TrackObject(View, goocanvas.Group, Zoomable):


    class Controller(TimelineController):

        def drag_start(self, item, target, event):
            TimelineController.drag_start(self, item, target, event)
            self._view.app.action_log.begin("move clip")
            self._view.timeline.disableUpdates()
            self._view.raise_(None)
            tx = self._view.props.parent.get_transform()
            self._y_offset = tx[5]
            self._mousedown = Point(self._mousedown[0], 0)
            element = self._view.element
            timeline = self._view.timeline
            self._offsets = {}
            self._min_start = 0
            self._min_pri = 0

            if len(self._view.timeline.selection) <= 1:
                self._view.timeline.setSelectionToObj(self._view.element,
                        SELECT)

            # calculate offsets to selected clips
            if element.selected:
                for obj in timeline.selection.getSelectedTrackObjs():
                    start = obj.start - element.start
                    if start < 0:
                        self._min_start = max(self._min_start, -start)
                    priority = obj.priority - element.priority
                    if priority < 0:
                        self._min_pri = max(self._min_pri, -priority)
                    self._offsets[obj] = start, priority
                del self._offsets[element]

        def drag_end(self, item, target, event):
            TimelineController.drag_end(self, item, target, event)
            self._view.timeline.enableUpdates()
            self._view.app.action_log.commit()

        def click(self, pos):
            mode = SELECT
            if self._last_event.get_state() & gtk.gdk.SHIFT_MASK:
                mode = SELECT_ADD
            elif self._last_event.get_state() & gtk.gdk.CONTROL_MASK:
                mode = UNSELECT
            self._view.timeline.setSelectionToObj(
                self._view.element, mode)

        def set_pos(self, item, pos):
            x, y = pos
            self._view.element.setStart(max(self._view.pixelToNs(x),
                self._min_start), snap=True)
            start = self._view.element.start
            priority = int(max(self._min_pri, (y - self._y_offset) // 
                (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)))
            self._view.element.setObjectPriority(priority)
            for obj, (s, p) in self._offsets.iteritems():
                obj.setStart(start + s)
                obj.setPriority(priority + p)

    def __init__(self, instance, element, track, timeline):
        goocanvas.Group.__init__(self)
        View.__init__(self)
        Zoomable.__init__(self)
        self.app = instance
        self.track = track
        self.timeline = timeline
        self.namewidth = 0

        self.bg = goocanvas.Rect(
            height=self.height, 
            line_width=0)

        self.content = Preview(element)

        self.name = goocanvas.Text(
            x=10,
            y=5,
            
            operator = cairo.OPERATOR_ADD,
            alignment=pango.ALIGN_LEFT)
        self.namebg = goocanvas.Rect(
            radius_x = 2,
            radius_y = 2,
            x = 8,
            y = 3,
            line_width = 0)

        self.start_handle = StartHandle(self.app, element, timeline,
            height=self.height)
        self.end_handle = EndHandle(self.app, element, timeline,
            height=self.height)

        self.selection_indicator = goocanvas.Rect(
            visibility=goocanvas.ITEM_INVISIBLE,
            line_width = 0.0,
            height=self.height)

        for thing in (self.bg, self.content, self.selection_indicator, 
            self.start_handle, self.end_handle, self.namebg, self.name):
            self.add_child(thing)

        for prop, interpolator in element.getInterpolators().itervalues():
            self.add_child(Curve(instance, element, interpolator, 50))

        self.element = element
        self.settings = instance.settings
        self.normal()

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
            self.name.props.y = 5

    def getExpanded(self):
        return self._expanded

    expanded = property(getExpanded, setExpanded)

## Public API

    def focus(self):
        self.start_handle.focus()
        self.end_handle.focus()

    def unfocus(self):
        self.start_handle.unfocus()
        self.end_handle.unfocus()

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
        if isinstance(self.element.stream, VideoStream):
            color = self.settings.videoClipBg
        elif isinstance(self.element.stream, AudioStream):
            color = self.settings.audioClipBg
        pattern = unpack_cairo_gradient(color)
        self.bg.props.fill_pattern = pattern

        self.namebg.props.fill_pattern = pattern

        self.selection_indicator.props.fill_pattern = unpack_cairo_pattern(
            self.settings.selectedColor)

        self.name.props.font = self.settings.clipFontDesc
        self.name.props.fill_pattern = unpack_cairo_pattern(
            self.settings.clipFontColor)

## element signals

    def _setElement(self):
        if self.element:
            self.name.props.text = os.path.basename(unquote(
                self.element.factory.name))
            twidth, theight = text_size(self.name)
            self.namewidth = twidth
            self.namebg.props.width = twidth + 6.0
            self.namebg.props.height = theight + 4.0
            self._update()

    element = receiver(_setElement)

    @handler(element, "start-changed")
    @handler(element, "duration-changed")
    def startChangedCb(self, track_object, start):
        self._update()

    @handler(element, "selected-changed")
    def selected_changed(self, element, state):
        if element.selected:
            self.selection_indicator.props.visibility = goocanvas.ITEM_VISIBLE
        else:
            self.selection_indicator.props.visibility = \
                goocanvas.ITEM_INVISIBLE

    @handler(element, "priority-changed")
    def priority_changed(self, element, priority):
        self._update()

    def _update(self):
        try:
            x = self.nsToPixel(self.element.start)
        except Exception, e:
            print self.element.start
            raise Exception(e)
        y = (self.height + LAYER_SPACING) * self.element.priority
        self.set_simple_transform(x, y, 1, 0)
        width = self.nsToPixel(self.element.duration)
        w = width - self.end_handle.props.width
        self.name.props.clip_path = "M%g,%g h%g v%g h-%g z" % (
            0, 0, w, self.height, w)
        self.bg.props.width = width
        self.selection_indicator.props.width = width
        self.end_handle.props.x = w
        if self.expanded:
            if w - 10 > 0:
                self.namebg.props.width = min(w - 8, self.namewidth)
                self.namebg.props.visibility = goocanvas.ITEM_VISIBLE
            else:
                self.namebg.props.visibility = goocanvas.ITEM_INVISIBLE
