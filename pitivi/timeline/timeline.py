# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/timeline/timeline.py
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

import sys
import os

import gi
from gi.repository import GtkClutter

GtkClutter.init([])

from gi.repository import Gst, GES, GObject, Clutter, Gtk, GLib, Gdk

from pitivi.autoaligner import AlignmentProgressDialog, AutoAligner
from pitivi.check import at_least_version
from pitivi.utils.timeline import Zoomable, Selection, SELECT, TimelineError
from pitivi.settings import GlobalSettings
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import EXPANDED_SIZE, SPACING, PLAYHEAD_WIDTH, CONTROL_WIDTH, TYPE_PITIVI_EFFECT
from pitivi.utils.widgets import ZoomBox

from ruler import ScaleRuler
from gettext import gettext as _
from pitivi.utils.pipeline import PipelineError
from elements import URISourceElement, TransitionElement, Ghostclip
from controls import ControlContainer

GlobalSettings.addConfigOption('edgeSnapDeadband',
    section="user-interface",
    key="edge-snap-deadband",
    default=5,
    notify=True)

PreferencesDialog.addNumericPreference('edgeSnapDeadband',
    section=_("Behavior"),
    label=_("Snap distance"),
    description=_("Threshold (in pixels) at which two clips will snap together "
        "when dragging or trimming."),
    lower=0)

GlobalSettings.addConfigOption('imageClipLength',
    section="user-interface",
    key="image-clip-length",
    default=1000,
    notify=True)

PreferencesDialog.addNumericPreference('imageClipLength',
    section=_("Behavior"),
    label=_("Image clip duration"),
    description=_("Default clip length (in miliseconds) of images when inserting on the timeline."),
    lower=1)

TARGET_TYPE_URI_LIST = 80

# tooltip text for toolbar
DELETE = _("Delete Selected")
SPLIT = _("Split clip at playhead position")
KEYFRAME = _("Add a keyframe")
PREVKEYFRAME = _("Move to the previous keyframe")
NEXTKEYFRAME = _("Move to the next keyframe")
ZOOM_IN = _("Zoom In")
ZOOM_OUT = _("Zoom Out")
ZOOM_FIT = _("Zoom Fit")
UNGROUP = _("Ungroup clips")
GROUP = _("Group clips")
ALIGN = _("Align clips based on their soundtracks")
SELECT_BEFORE = ("Select all sources before selected")
SELECT_AFTER = ("Select all after selected")

# Colors
TIMELINE_BACKGROUND_COLOR = Clutter.Color.new(31, 30, 33, 255)
SELECTION_MARQUEE_COLOR = Clutter.Color.new(100, 100, 100, 200)
PLAYHEAD_COLOR = Clutter.Color.new(200, 0, 0, 255)
SNAPPING_INDICATOR_COLOR = Clutter.Color.new(50, 150, 200, 200)

ui = '''
<ui>
    <menubar name="MainMenuBar">
        <menu action="View">
            <placeholder name="Timeline">
                <menuitem action="ZoomIn" />
                <menuitem action="ZoomOut" />
                <menuitem action="ZoomFit" />
            </placeholder>
        </menu>
        <menu action="Timeline">
            <placeholder name="Timeline">
                <menuitem action="Split" />
                <menuitem action="DeleteObj" />
                <separator />
                <menuitem action="GroupObj" />
                <menuitem action="UngroupObj" />
                <menuitem action="AlignObj" />
                <separator />
                <menuitem action="Keyframe" />
                <menuitem action="Prevkeyframe" />
                <menuitem action="Nextkeyframe" />
                <separator />
                <menuitem action="PlayPause" />
                <menuitem action="Screenshot" />
            </placeholder>
        </menu>
    </menubar>
    <toolbar name="TimelineToolBar">
        <placeholder name="Timeline">
            <separator />
            <toolitem action="Split" />
            <toolitem action="DeleteObj" />
            <toolitem action="GroupObj" />
            <toolitem action="UngroupObj" />
            <toolitem action="AlignObj" />
        </placeholder>
    </toolbar>
    <accelerator action="PlayPause" />
    <accelerator action="DeleteObj" />
    <accelerator action="ControlEqualAccel" />
    <accelerator action="ControlKPAddAccel" />
    <accelerator action="ControlKPSubtractAccel" />
    <accelerator action="Keyframe" />
</ui>
'''


"""
Convention throughout this file:
Every GES element which name could be mistaken with a UI element
is prefixed with a little b, example : bTimeline
"""


class TimelineStage(Clutter.ScrollActor, Zoomable):
    """
    The timeline view showing the clips.
    """

    __gsignals__ = {
        'scrolled': (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    def __init__(self, container):
        Clutter.ScrollActor.__init__(self)
        Zoomable.__init__(self)
        self.bTimeline = None
        self.current_group = GES.Group()

        self._container = container
        self.allowSeek = True
        self._settings = container._settings
        self.elements = []
        self.ghostClips = []
        self.selection = Selection()
        self._scroll_point = Clutter.Point()
        self.lastPosition = 0  # Saved for redrawing when paused
        self._createPlayhead()
        self._createSnapIndicator()
        self._peekMouse()
        self._setUpDragAndDrop()

    # Public API

    def setPipeline(self, pipeline):
        pipeline.connect('position', self._positionCb)

    def setTimeline(self, bTimeline):
        """
        @param bTimeline : the backend GES.Timeline which we interface.
        Does all the necessary connections.
        """
        if self.bTimeline is not None:
            self.bTimeline.disconnect_by_func(self._trackAddedCb)
            self.bTimeline.disconnect_by_func(self._trackRemovedCb)
            self.bTimeline.disconnect_by_func(self._layerAddedCb)
            self.bTimeline.disconnect_by_func(self._layerRemovedCb)
            self.bTimeline.disconnect_by_func(self._snapCb)
            self.bTimeline.disconnect_by_func(self._snapEndedCb)
            for track in self.bTimeline.get_tracks():
                self._trackRemovedCb(self.bTimeline, track)
            for layer in self.bTimeline.get_layers():
                self._layerRemovedCb(self.bTimeline, layer)

        self.bTimeline = bTimeline

        if bTimeline is None:
            return

        for track in bTimeline.get_tracks():
            self._connectTrack(track)
        for layer in bTimeline.get_layers():
            self._add_layer(layer)

        self.bTimeline.connect("track-added", self._trackAddedCb)
        self.bTimeline.connect("track-removed", self._trackRemovedCb)
        self.bTimeline.connect("layer-added", self._layerAddedCb)
        self.bTimeline.connect("layer-removed", self._layerRemovedCb)
        self.bTimeline.connect("snapping-started", self._snapCb)
        self.bTimeline.connect("snapping-ended", self._snapEndedCb)

        self.zoomChanged()

    def findBrother(self, element):
        """
        Iterate over ui_elements to get the URI source with the same parent clip
        @param element: the ui_element for which we want to find the sibling.
        """
        father = element.get_parent()
        for elem in self.elements:
            if elem.bElement.get_parent() == father and elem.bElement != element:
                return elem
        return None

    def insertLayer(self, ghostclip):
        """
        @param ghostclip: the ghostclip that was dropped, needing a new layer.
        Will move subsequent layers down, if any.
        """
        layer = None
        if ghostclip.priority < len(self.bTimeline.get_layers()):
            for layer in self.bTimeline.get_layers():
                if layer.get_priority() >= ghostclip.priority:
                    layer.props.priority += 1

            layer = self.bTimeline.append_layer()
            layer.props.priority = ghostclip.priority
            self.bTimeline.commit()
            self._container.controls._reorderLayerActors()
        return layer

    # Drag and drop from the medialibrary, handled by "ghost" (temporary) clips.
    # We create those when drag data is received, reset them after conversion.
    # This avoids bugs when dragging in and out of the timeline

    def resetGhostClips(self):
        for ghostCouple in self.ghostClips:
            for ghostclip in ghostCouple:
                del ghostclip
        self.ghostClips = []

    def addGhostClip(self, asset, x, y):
        ghostAudio = ghostVideo = None

        if asset.get_supported_formats() & GES.TrackType.VIDEO:
            ghostVideo = self._createGhostclip(GES.TrackType.VIDEO, asset)
        if asset.get_supported_formats() & GES.TrackType.AUDIO:
            ghostAudio = self._createGhostclip(GES.TrackType.AUDIO, asset)

        self.ghostClips.append([ghostVideo, ghostAudio])

    def updateGhostClips(self, x, y):
        """
        This is called for each drag-motion.
        """
        for ghostCouple in self.ghostClips:
            for ghostclip in ghostCouple:
                if ghostclip is not None:
                    priority = int(y / (EXPANDED_SIZE + SPACING))
                    ghostclip.update(priority, y, False)
                    if x >= 0:
                        ghostclip.props.x = x
                        self._updateSize(ghostclip)

    def convertGhostClips(self):
        """
        This is called at drag-drop
        """
        placement = 0
        layer = None
        for ghostCouple in self.ghostClips:
            ghostclip = ghostCouple[0]
            if not ghostclip:
                ghostclip = ghostCouple[1]

            if layer is None:
                target = None
                if ghostclip.shouldCreateLayer:
                    layer = self.insertLayer(ghostclip)
                    target = layer
                else:
                    for layer in self.bTimeline.get_layers():
                        if layer.get_priority() == ghostclip.priority:
                            target = layer
                            break
                if target is None:
                    layer = self.bTimeline.append_layer()

            if ghostclip.asset.is_image():
                clip_duration = self._settings.imageClipLength * Gst.SECOND / 1000.0
            else:
                clip_duration = ghostclip.asset.get_duration()

            if not placement:
                placement = Zoomable.pixelToNs(ghostclip.props.x)
            layer.add_asset(ghostclip.asset,
                            placement,
                            0,
                            clip_duration,
                            ghostclip.asset.get_supported_formats())
            placement += clip_duration
        self.bTimeline.commit()

    def removeGhostClips(self):
        """
        This is called at drag-leave. We don't empty the list on purpose.
        """
        for ghostCouple in self.ghostClips:
            for ghostclip in ghostCouple:
                if ghostclip is not None and ghostclip.get_parent():
                    self.remove_child(ghostclip)
        self.bTimeline.commit()

    def getActorUnderPointer(self):
        return self.mouse.get_pointer_actor()

    # Internal API

    def _elementIsInLasso(self, element, x1, y1, x2, y2):
        xE1 = element.props.x
        xE2 = element.props.x + element.props.width
        yE1 = element.props.y
        yE2 = element.props.y + element.props.height

        return self._segmentsOverlap((x1, x2), (xE1, xE2)) and self._segmentsOverlap((y1, y2), (yE1, yE2))

    def _segmentsOverlap(self, a, b):
        x = max(a[0], b[0])
        y = min(a[1], b[1])
        return x < y

    def _translateToTimelineContext(self, event):
        event.x -= CONTROL_WIDTH
        event.x += self._scroll_point.x
        event.y += self._scroll_point.y

        delta_x = event.x - self.dragBeginStartX
        delta_y = event.y - self.dragBeginStartY

        newX = self.dragBeginStartX
        newY = self.dragBeginStartY

        # This is needed when you start to click and go left or up.

        if delta_x < 0:
            newX = event.x
            delta_x = abs(delta_x)

        if delta_y < 0:
            newY = event.y
            delta_y = abs(delta_y)

        return (newX, newY, delta_x, delta_y)

    def _setUpDragAndDrop(self):
        self.set_reactive(True)

        self.marquee = Clutter.Actor()
        self.marquee.set_background_color(SELECTION_MARQUEE_COLOR)
        self.marquee.hide()
        self.add_child(self.marquee)

        self.drawMarquee = False
        self._container.stage.connect("button-press-event", self._dragBeginCb)
        self._container.stage.connect("motion-event", self._dragProgressCb)
        self._container.stage.connect("button-release-event", self._dragEndCb)
        self._container.gui.connect("button-release-event", self._dragEndCb)

    def _peekMouse(self):
        manager = Clutter.DeviceManager.get_default()

        for device in manager.peek_devices():
            if device.props.device_type == Clutter.InputDeviceType.POINTER_DEVICE and device.props.enabled is True:
                self.mouse = device
                break

    def _createGhostclip(self, trackType, asset):
        ghostclip = Ghostclip(trackType)
        ghostclip.asset = asset
        ghostclip.setNbrLayers(len(self.bTimeline.get_layers()))

        if asset.is_image():
            clip_duration = self._settings.imageClipLength * Gst.SECOND / 1000.0
        else:
            clip_duration = asset.get_duration()

        ghostclip.setWidth(Zoomable.nsToPixel(clip_duration))
        self.add_child(ghostclip)
        return ghostclip

    def _connectTrack(self, track):
        for trackelement in track.get_elements():
            self._trackElementAddedCb(track, trackelement)
        track.connect("track-element-added", self._trackElementAddedCb)
        track.connect("track-element-removed", self._trackElementRemovedCb)

    def _disconnectTrack(self, track):
        track.disconnect_by_func(self._trackElementAddedCb)
        track.disconnect_by_func(self._trackElementRemovedCb)

    def _positionCb(self, pipeline, position):
        self.playhead.props.x = self.nsToPixel(position)
        self._container._scrollToPlayhead()
        self.lastPosition = position

    def _updatePlayHead(self):
        if self._container.pipeline and self._container.pipeline.get_state() != Gst.State.PLAYING:
            self.playhead.save_easing_state()
            self.playhead.set_easing_duration(600)
        height = len(self.bTimeline.get_layers()) * (EXPANDED_SIZE + SPACING) * 2
        self.playhead.set_size(PLAYHEAD_WIDTH, height)
        self.playhead.props.x = self.nsToPixel(self.lastPosition)
        if self._container.pipeline and self._container.pipeline.get_state() != Gst.State.PLAYING:
            self.playhead.restore_easing_state()

    def _createPlayhead(self):
        self.playhead = Clutter.Actor()
        self.playhead.set_background_color(PLAYHEAD_COLOR)
        self.playhead.set_size(0, 0)
        self.playhead.set_position(0, 0)
        self.playhead.set_easing_duration(0)
        self.playhead.set_z_position(1)
        self.add_child(self.playhead)

    def _createSnapIndicator(self):
        self._snap_indicator = Clutter.Actor()
        self._snap_indicator.set_background_color(SNAPPING_INDICATOR_COLOR)
        self._snap_indicator.props.visible = False
        self._snap_indicator.props.width = 3
        self._snap_indicator.props.y = 0
        self.add_child(self._snap_indicator)

    def _addTimelineElement(self, track, bElement):
        if isinstance(bElement, GES.Effect):
            return
        if isinstance(bElement.get_parent(), GES.TransitionClip):
            element = TransitionElement(bElement, track, self)
            element.set_z_position(0)
        else:
            element = URISourceElement(bElement, track, self)
            element.set_z_position(-1)

        bElement.connect("notify::start", self._elementStartChangedCb, element)
        bElement.connect("notify::duration", self._elementDurationChangedCb, element)
        bElement.connect("notify::in-point", self._elementInPointChangedCb, element)
        bElement.connect("notify::priority", self._elementPriorityChangedCb, element)

        self.elements.append(element)

        self._setElementX(element)
        self._setElementY(element)

        self.add_child(element)

    def _removeTimelineElement(self, track, bElement):
        if isinstance(bElement, GES.Effect):
            return
        bElement.disconnect_by_func(self._elementStartChangedCb)
        bElement.disconnect_by_func(self._elementDurationChangedCb)
        bElement.disconnect_by_func(self._elementInPointChangedCb)
        bElement.disconnect_by_func(self._elementPriorityChangedCb)

        element = self._getElement(bElement)
        if not element:
            raise TimelineError("Missing element for: " + bElement)
        element.cleanup()
        self.elements.remove(element)
        self.remove_child(element)
        self.selection.setSelection(set([]), SELECT)

    def _getElement(self, bElement):
        for element in self.elements:
            if element.bElement == bElement:
                return element
        return None

    def _setElementX(self, element, ease=True):
        if ease:
            element.save_easing_state()
            element.set_easing_duration(600)
        element.props.x = self.nsToPixel(element.bElement.get_start())
        if ease:
            element.restore_easing_state()

    # FIXME, change that when we have retractable layers
    def _setElementY(self, element):
        bElement = element.bElement
        track_type = bElement.get_track_type()

        y = 0
        if track_type == GES.TrackType.AUDIO:
            y = len(self.bTimeline.get_layers()) * (EXPANDED_SIZE + SPACING)
        y += bElement.get_parent().get_layer().get_priority() * (EXPANDED_SIZE + SPACING) + SPACING

        element.save_easing_state()
        element.props.y = y
        element.restore_easing_state()

    def _updateSize(self, ghostclip=None):
        self.save_easing_state()
        self.set_easing_duration(0)
        self.props.width = self.nsToPixel(self.bTimeline.get_duration()) + 250
        if ghostclip is not None:
            ghostEnd = ghostclip.props.x + ghostclip.props.width + 250
            self.props.width = max(ghostEnd, self.props.width)
        self.props.height = (len(self.bTimeline.get_layers()) + 1) * (EXPANDED_SIZE + SPACING) * 2 + SPACING
        self.restore_easing_state()
        self._container.vadj.props.upper = self.props.height
        self._container.updateHScrollAdjustments()

    def _redraw(self):
        self._updateSize()

        self.save_easing_state()
        for element in self.elements:
            self._setElementX(element)
            self._setElementY(element)
        self.restore_easing_state()

        self._updatePlayHead()

    def _remove_layer(self, layer):
        self._container.controls.removeLayerControl(layer)
        self._redraw()

    def _add_layer(self, layer):
        self._redraw()
        self._container.controls.addLayerControl(layer)

    def _addTrackElement(self, track, bElement):
        self._updateSize()
        self._addTimelineElement(track, bElement)

    # Interface overrides

    # Zoomable Override

    def zoomChanged(self):
        self._redraw()

    # Clutter Override

    # TODO: remove self._scroll_point and get_scroll_point as soon as the Clutter API
    # offers a way to query a ScrollActor for its current scroll point
    def scroll_to_point(self, point):
        Clutter.ScrollActor.scroll_to_point(self, point)
        self._scroll_point = point.copy()
        self.emit("scrolled")

    def get_scroll_point(self):
        return self._scroll_point

    # Callbacks

    def _dragBeginCb(self, actor, event):
        self.drawMarquee = self.getActorUnderPointer() == self
        if not self.drawMarquee:
            return

        if self.current_group:
            GES.Container.ungroup(self.current_group, False)
            self.current_group = GES.Group()

        self.dragBeginStartX = event.x - CONTROL_WIDTH + self._scroll_point.x
        self.dragBeginStartY = event.y + self._scroll_point.y
        self.marquee.set_size(0, 0)
        self.marquee.set_position(event.x - CONTROL_WIDTH, event.y)
        self.marquee.show()

    def _dragProgressCb(self, actor, event):
        if not self.drawMarquee:
            return False

        x, y, width, height = self._translateToTimelineContext(event)

        self.marquee.set_position(x, y)
        self.marquee.set_size(width, height)

        return False

    def _dragEndCb(self, actor, event):
        if not self.drawMarquee:
            return
        self.drawMarquee = False

        x, y, width, height = self._translateToTimelineContext(event)
        elements = self._getElementsInRegion(x, y, width, height)
        self.current_group = GES.Group()
        for element in elements:
            self.current_group.add(element)
        selection = [child for child in self.current_group.get_children(True)
                     if isinstance(child, GES.Source)]
        self.selection.setSelection(selection, SELECT)
        self.marquee.hide()

    def _getElementsInRegion(self, x, y, width, height):
        elements = set()
        for element in self.elements:
            if self._elementIsInLasso(element, x, y, x + width, y + height):
                elements.add(element.bElement.get_toplevel_parent())
        return elements

    # snapping indicator
    def _snapCb(self, unused_timeline, obj1, obj2, position):
        """
        Display or hide a snapping indicator line
        """
        if position == 0:
            self._snapEndedCb()
        else:
            height = len(self.bTimeline.get_layers()) * (EXPANDED_SIZE + SPACING) * 2
            self._snap_indicator.props.height = height
            self._snap_indicator.props.x = Zoomable.nsToPixel(position)
            self._snap_indicator.props.visible = True

    def _snapEndedCb(self, *args):
        self._snap_indicator.props.visible = False

    def _layerAddedCb(self, timeline, layer):
        self._add_layer(layer)

    def _layerRemovedCb(self, timeline, layer):
        # FIXME : really remove layer ^^
        for lyr in self.bTimeline.get_layers():
            if lyr.props.priority > layer.props.priority:
                lyr.props.priority -= 1
        self._remove_layer(layer)
        self._updatePlayHead()

    def _trackAddedCb(self, timeline, track):
        self._connectTrack(track)
        self._container.app.current_project.update_restriction_caps()

    def _trackRemovedCb(self, timeline, track):
        self._disconnectTrack(track)
        for element in track.get_elements():
            self._trackElementRemovedCb(track, element)

    def _trackElementAddedCb(self, track, bElement):
        self._addTrackElement(track, bElement)

    def _trackElementRemovedCb(self, track, bElement):
        self._removeTimelineElement(track, bElement)

    def _elementPriorityChangedCb(self, bElement, priority, element):
        self._setElementY(element)

    def _elementStartChangedCb(self, bElement, start, element):
        self._updateSize()
        self.allowSeek = False

        if element.isDragged:
            self._setElementX(element, ease=False)
        else:
            self._setElementX(element)

    def _elementDurationChangedCb(self, bElement, duration, element):
        self._updateSize()
        self.allowSeek = False
        element.update(False)

    def _elementInPointChangedCb(self, bElement, inpoint, element):
        self.allowSeek = False
        self._setElementX(element, ease=False)

    def _layerPriorityChangedCb(self, layer, priority):
        self._redraw()


# This is for running standalone
def quit_(stage):
    Gtk.main_quit()


def quit2_(*args, **kwargs):
    Gtk.main_quit()


class Timeline(Gtk.Grid, Zoomable, Loggable):
    """
    Container for zoom box, ruler, the actual timeline layers and scrollbars.
    """
    def __init__(self, gui, instance, ui_manager):
        Zoomable.__init__(self)
        Gtk.Grid.__init__(self)
        Loggable.__init__(self)
        if not at_least_version(gi.version_info, (3, 11, 0)):
            GObject.threads_init()

        # Allows stealing focus from other GTK widgets, prevent accidents:
        self.props.can_focus = True
        self.connect("focus-in-event", self._focusInCb)
        self.connect("focus-out-event", self._focusOutCb)

        self.gui = gui
        self.ui_manager = ui_manager
        self.app = instance
        self._settings = None
        if self.app:
            self._settings = self.app.settings

        self._projectmanager = None
        self._project = None
        self.pipeline = None
        self.bTimeline = None

        self._createUi()
        self._createActions()

        self._setUpDragAndDrop()

        if self._settings:
            self._settings.connect("edgeSnapDeadbandChanged",
                                   self._snapDistanceChangedCb)

        # Standalone
        if not self._settings:
            gtksettings = Gtk.Settings.get_default()
            gtksettings.set_property("gtk-application-prefer-dark-theme", True)

        self.show_all()

    # Public API

    def insertEnd(self, assets):
        """
        Allows to add any asset at the end of the current timeline.
        """
        self.app.action_log.begin("add clip")
        if self.bTimeline is None:
            raise TimelineError("No bTimeline set, this is a bug")

        layer = self._getLongestLayer()

        # We need to snapshot this value, because we only do the zoom fit at the
        # end of clip insertion, but inserting multiple clips eventually changes
        # the value of self.zoomed_fitted as clips get progressively inserted...
        zoom_was_fitted = self.zoomed_fitted

        for asset in assets:
            if isinstance(asset, GES.TitleClip):
                clip_duration = asset.get_duration()
            elif asset.is_image():
                clip_duration = self._settings.imageClipLength * Gst.SECOND / 1000.0
            else:
                clip_duration = asset.get_duration()

            if not isinstance(asset, GES.TitleClip):
                layer.add_asset(asset, self.bTimeline.props.duration,
                                0, clip_duration, asset.get_supported_formats())
            else:
                asset.set_start(self.bTimeline.props.duration)
                layer.add_clip(asset)

        if zoom_was_fitted:
            self._setBestZoomRatio()
        else:
            self.scrollToPixel(Zoomable.nsToPixel(self.bTimeline.props.duration))

        self.app.action_log.commit()
        self.bTimeline.commit()

    def purgeObject(self, asset_id):
        """Remove all instances of an asset from the timeline."""
        layers = self.bTimeline.get_layers()
        for layer in layers:
            for tlobj in layer.get_clips():
                if asset_id == tlobj.get_id():
                    layer.remove_clip(tlobj)

    def setProjectManager(self, projectmanager):
        if self._projectmanager is not None:
            self._projectmanager.disconnect_by_func(self._projectChangedCb)

        self._projectmanager = projectmanager

        if projectmanager is not None:
            projectmanager.connect("new-project-created", self._projectCreatedCb)
            projectmanager.connect("new-project-loaded", self._projectChangedCb)

    def updateHScrollAdjustments(self):
        """
        Recalculate the horizontal scrollbar depending on the timeline duration.
        """
        timeline_ui_width = self.embed.get_allocation().width
        controls_width = 0
        scrollbar_width = 0
        if self.bTimeline is None:
            contents_size = 0
        else:
            contents_size = Zoomable.nsToPixel(self.bTimeline.props.duration)

        widgets_width = controls_width + scrollbar_width
        end_padding = CONTROL_WIDTH + 250  # Provide some space for clip insertion at the end

        self.hadj.props.lower = 0
        self.hadj.props.upper = contents_size + widgets_width + end_padding
        self.hadj.props.page_size = timeline_ui_width
        self.hadj.props.page_increment = contents_size * 0.9
        self.hadj.props.step_increment = contents_size * 0.1

        if contents_size + widgets_width <= timeline_ui_width:
            # We're zoomed out completely, re-enable automatic zoom fitting
            # when adding new clips.
            self.log("Setting 'zoomed_fitted' to True")
            self.zoomed_fitted = True
        else:
            self.log("Setting 'zoomed_fitted' to False")
            self.zoomed_fitted = False

    def zoomFit(self):
        self._hscrollBar.set_value(0)
        self._setBestZoomRatio(allow_zoom_in=True)

    def scrollToPixel(self, x):
        if x > self.hadj.props.upper:
            # We can't scroll yet, because the canvas needs to be updated
            GLib.idle_add(self._scrollToPixel, x)
        else:
            self._scrollToPixel(x)

    def seekInPosition(self, position):
        self.pressed = True
        self._seeker.seek(position)

    def setTimeline(self, bTimeline):
        self.bTimeline = bTimeline
        self.timeline.selection.connect("selection-changed", self._selectionChangedCb)
        self.timeline.setTimeline(bTimeline)

    def getEditionMode(self, isAHandle=False):
        if self._shiftMask or (self.gui and self.gui._autoripple_active):
            return GES.EditMode.EDIT_RIPPLE
        if isAHandle and self._controlMask:
            return GES.EditMode.EDIT_ROLL
        elif isAHandle:
            return GES.EditMode.EDIT_TRIM
        return GES.EditMode.EDIT_NORMAL

    def setActionsSensitivity(self, sensitive):
        """
        The timeline's "actions" have global keyboard shortcuts that are
        dangerous in any context other than the timeline. In a text entry widget
        for example, you don't want the "Delete" key to remove clips currently
        selected on the timeline, or "Spacebar" to toggle playback.

        This sets the sensitivity of all actiongroups that might interfere.
        """
        self.playhead_actions.set_sensitive(sensitive)
        self.debug("Playback shortcuts sensitivity set to %s", sensitive)
        selected = self.timeline.selection.getSelectedTrackElements()
        if not sensitive or (sensitive and selected):
            self.selection_actions.set_sensitive(sensitive)
            self.debug("Editing shortcuts sensitivity set to %s", sensitive)

    # Internal API

    def _createUi(self):
        self.embed = GtkClutter.Embed()
        self.embed.get_accessible().set_name("timeline canvas")  # for dogtail
        self.stage = self.embed.get_stage()
        perspective = self.stage.get_perspective()

        self.timeline = TimelineStage(self)
        self.controls = ControlContainer(self.app, self.timeline)
        self.zoomBox = ZoomBox(self)
        self._shiftMask = False
        self._controlMask = False

        perspective.fov_y = 90.
        self.stage.set_perspective(perspective)

        self.stage.set_background_color(TIMELINE_BACKGROUND_COLOR)
        self.timeline.set_position(CONTROL_WIDTH, 0)
        self.controls.set_position(0, 0)
        self.controls.set_z_position(2)

        self.stage.add_child(self.controls)
        self.stage.add_child(self.timeline)

        self.timeline.connect("button-press-event", self._timelineClickedCb)
        self.timeline.connect("button-release-event", self._timelineClickReleasedCb)
        self.embed.connect("scroll-event", self._scrollEventCb)

        if self.gui:
            self.gui.connect("key-press-event", self._keyPressEventCb)
            self.gui.connect("key-release-event", self._keyReleaseEventCb)

        self.point = Clutter.Point()
        self.point.x = 0
        self.point.y = 0

        self.scrolled = 0

        self.zoomed_fitted = True
        self.pressed = False

        self.hadj = Gtk.Adjustment()
        self.vadj = Gtk.Adjustment()
        self.hadj.connect("value-changed", self._updateScrollPosition)
        self.vadj.connect("value-changed", self._updateScrollPosition)
        self.vadj.props.lower = 0
        self.vadj.props.page_size = 250
        self._vscrollbar = Gtk.VScrollbar(adjustment=self.vadj)
        self._hscrollBar = Gtk.HScrollbar(adjustment=self.hadj)

        self.ruler = ScaleRuler(self, self.hadj)
        self.ruler.props.hexpand = True
        self.ruler.setProjectFrameRate(24.)
        self.ruler.hide()

        self.attach(self.zoomBox, 0, 0, 1, 1)
        self.attach(self.ruler, 1, 0, 1, 1)
        self.attach(self.embed, 0, 1, 2, 1)
        self.attach(self._vscrollbar, 2, 1, 1, 1)
        self.attach(self._hscrollBar, 1, 2, 1, 1)

        min_height = (self.ruler.get_size_request()[1] +
                      (EXPANDED_SIZE + SPACING) * 2 +
                      SPACING * 3)
        self.set_size_request(-1, min_height)

    def enableKeyboardAndMouseEvents(self):
        self.info("Unblocking timeline mouse and keyboard signals")
        self.stage.disconnect_by_func(self._ignoreAllEventsCb)

    def disableKeyboardAndMouseEvents(self):
        """
        A safety measure to prevent interacting with the Clutter timeline
        during render (no, setting GtkClutterEmbed as insensitive won't work,
        neither will using handler_block_by_func, nor connecting to the "event"
        signals because they won't block the children and other widgets).
        """
        self.info("Blocking timeline mouse and keyboard signals")
        self.stage.connect("captured-event", self._ignoreAllEventsCb)

    def _ignoreAllEventsCb(self, *args):
        return True

    def _setUpDragAndDrop(self):
        self.dropHighlight = False
        self.dropOccured = False
        self.dropDataReady = False
        self.dropData = None
        dnd_list = [Gtk.TargetEntry.new('text/uri-list', Gtk.TargetFlags.OTHER_APP, TARGET_TYPE_URI_LIST)]

        self.drag_dest_set(0, dnd_list, Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()

        self.connect('drag-motion', self._dragMotionCb)
        self.connect('drag-data-received', self._dragDataReceivedCb)
        self.connect('drag-drop', self._dragDropCb)
        self.connect('drag-leave', self._dragLeaveCb)

    def _getLayers(self):
        """
        Make sure we have at least one layer in our timeline.
        """
        layers = self.bTimeline.get_layers()
        if not layers:
            layer = GES.Layer()
            layer.props.auto_transition = True
            self.bTimeline.add_layer(layer)
            return [layer]
        return layers

    def _getLongestLayer(self):
        """
        Return the longest layer.
        """
        layers = self._getLayers()
        if len(layers) == 1:
            return layers[0]
        # Create a list of (layer_length, layer) tuples.
        layer_lengths = [(max([(clip.get_start() + clip.get_duration()) for clip in layer.get_clips()] or [0]), layer)
                         for layer in layers]
        # Easily get the longest.
        unused_longest_time, longest_layer = max(layer_lengths)
        return longest_layer

    def _createActions(self):
        if not self.gui:
            return
        actions = (
            ("ZoomIn", Gtk.STOCK_ZOOM_IN, None,
            "<Control>plus", ZOOM_IN, self._zoomInCb),

            ("ZoomOut", Gtk.STOCK_ZOOM_OUT, None,
            "<Control>minus", ZOOM_OUT, self._zoomOutCb),

            ("ZoomFit", Gtk.STOCK_ZOOM_FIT, None,
            "<Control>0", ZOOM_FIT, self._zoomFitCb),

            ("Screenshot", None, _("Export current frame..."),
            None, _("Export the frame at the current playhead "
                    "position as an image file."), self._screenshotCb),

            # Alternate keyboard shortcuts to the actions above
            ("ControlEqualAccel", Gtk.STOCK_ZOOM_IN, None,
            "<Control>equal", ZOOM_IN, self._zoomInCb),

            ("ControlKPAddAccel", Gtk.STOCK_ZOOM_IN, None,
            "<Control>KP_Add", ZOOM_IN, self._zoomInCb),

            ("ControlKPSubtractAccel", Gtk.STOCK_ZOOM_OUT, None,
            "<Control>KP_Subtract", ZOOM_OUT, self._zoomOutCb),
        )

        selection_actions = (
            ("DeleteObj", Gtk.STOCK_DELETE, None,
            "Delete", DELETE, self._deleteSelected),

            ("UngroupObj", "pitivi-ungroup", _("Ungroup"),
            "<Shift><Control>G", UNGROUP, self._ungroupSelected),

            # Translators: This is an action, the title of a button
            ("GroupObj", "pitivi-group", _("Group"),
            "<Control>G", GROUP, self._groupSelected),

            ("AlignObj", "pitivi-align", _("Align"),
            "<Shift><Control>A", ALIGN, self._alignSelected),
        )

        playhead_actions = (
            ("PlayPause", Gtk.STOCK_MEDIA_PLAY, None,
            "space", _("Start Playback"), self._playPause),

            ("Split", "pitivi-split", _("Split"),
            "S", SPLIT, self._split),

            ("Keyframe", "pitivi-keyframe", _("Add a Keyframe"),
            "K", KEYFRAME, self._keyframe),

            ("Prevkeyframe", None, _("_Previous Keyframe"),
            "comma", PREVKEYFRAME, self._previousKeyframeCb),

            ("Nextkeyframe", None, _("_Next Keyframe"),
            "period", NEXTKEYFRAME, self._nextKeyframeCb),
        )

        actiongroup = Gtk.ActionGroup(name="timelinepermanent")
        self.selection_actions = Gtk.ActionGroup(name="timelineselection")
        self.playhead_actions = Gtk.ActionGroup(name="timelineplayhead")

        actiongroup.add_actions(actions)

        self.ui_manager.insert_action_group(actiongroup, 0)
        self.selection_actions.add_actions(selection_actions)
        self.selection_actions.set_sensitive(False)
        self.ui_manager.insert_action_group(self.selection_actions, -1)
        self.playhead_actions.add_actions(playhead_actions)
        self.ui_manager.insert_action_group(self.playhead_actions, -1)

        self.ui_manager.add_ui_from_string(ui)

    def _updateScrollPosition(self, adjustment):
        self._scroll_pos_ns = Zoomable.pixelToNs(self.hadj.get_value())
        point = Clutter.Point()
        point.x = self.hadj.get_value()
        point.y = self.vadj.get_value()
        self.point = point

        self.timeline.scroll_to_point(point)
        point.x = 0
        self.controls.scroll_to_point(point)

    def _setBestZoomRatio(self, allow_zoom_in=False):
        """
        Set the zoom level so that the entire timeline is in view.
        """
        ruler_width = self.ruler.get_allocation().width
        duration = 0 if not self.bTimeline else self.bTimeline.get_duration()
        if not duration:
            return

        # Add Gst.SECOND - 1 to the timeline duration to make sure the
        # last second of the timeline will be in view.
        timeline_duration = duration + Gst.SECOND - 1
        timeline_duration_s = int(timeline_duration / Gst.SECOND)
        self.debug("Adjusting zoom for a timeline duration of %s secs", timeline_duration_s)

        ideal_zoom_ratio = float(ruler_width) / timeline_duration_s
        nearest_zoom_level = Zoomable.computeZoomLevel(ideal_zoom_ratio)
        if nearest_zoom_level >= Zoomable.getCurrentZoomLevel():
            # This means if we continue we'll zoom in.
            if not allow_zoom_in:
                # For example when the user zoomed out and is adding clips
                # to the timeline, zooming in would be confusing.
                self.log("Zoom not changed because the entire timeline is already visible")
                return

        Zoomable.setZoomLevel(nearest_zoom_level)
        self.bTimeline.set_snapping_distance(Zoomable.pixelToNs(self._settings.edgeSnapDeadband))

        # Only do this at the very end, after updating the other widgets.
        self.log("Setting 'zoomed_fitted' to True")
        self.zoomed_fitted = True

    def scroll_left(self):
        # This method can be a callback for our events, or called by ruler.py
        self._hscrollBar.set_value(self._hscrollBar.get_value() -
            self.hadj.props.page_size ** (2.0 / 3.0))

    def scroll_right(self):
        # This method can be a callback for our events, or called by ruler.py
        self._hscrollBar.set_value(self._hscrollBar.get_value() +
            self.hadj.props.page_size ** (2.0 / 3.0))

    def scroll_up(self):
        self._vscrollbar.set_value(self._vscrollbar.get_value() -
            self.vadj.props.page_size ** (2.0 / 3.0))

    def scroll_down(self):
        self._vscrollbar.set_value(self._vscrollbar.get_value() +
            self.vadj.props.page_size ** (2.0 / 3.0))

    def _scrollToPixel(self, x):
        if x > self.hadj.props.upper:
            self.warning("Position %s is bigger than the hscrollbar's upper bound (%s) - is the position really in pixels?" % (x, self.hadj.props.upper))
        elif x < self.hadj.props.lower:
            self.warning("Position %s is smaller than the hscrollbar's lower bound (%s)" % (x, self.hadj.props.lower))

        if self.pipeline and self.pipeline.get_state() != Gst.State.PLAYING:
            self.timeline.save_easing_state()
            self.timeline.set_easing_duration(600)

        self._hscrollBar.set_value(x)
        if self.pipeline and self.pipeline.get_state() != Gst.State.PLAYING:
            self.timeline.restore_easing_state()
        return False

    def _scrollToPlayhead(self):
        #self.ruler._maybeUpdate()
        if self.ruler.pressed or self.pressed:
            self.pressed = False
            return
        canvas_width = self.embed.get_allocation().width - CONTROL_WIDTH
        try:
            new_pos = Zoomable.nsToPixel(self.app.current_project.pipeline.getPosition())
        except PipelineError, e:
            self.info("Pipeline error: %s", e)
            return
        except AttributeError:  # Standalone, no pipeline.
            return
        playhead_pos_centered = new_pos - canvas_width / 2
        self.scrollToPixel(max(0, playhead_pos_centered))

    def _deleteSelected(self, unused_action):
        if self.bTimeline:
            self.app.action_log.begin("delete clip")

            #FIXME GES port: Handle unlocked TrackElement-s
            for clip in self.timeline.selection:
                layer = clip.get_layer()
                layer.remove_clip(clip)

            self.app.action_log.commit()

    def _ungroupSelected(self, unused_action):
        if self.bTimeline:
            self.app.action_log.begin("ungroup")

            containers = set({})

            for obj in self.timeline.selection:
                toplevel = obj.get_toplevel_parent()
                if toplevel == self.timeline.current_group:
                    for child in toplevel.get_children(False):
                        containers.add(child)
                    toplevel.ungroup(False)
                else:
                    containers.add(toplevel)

            for container in containers:
                GES.Container.ungroup(container, False)
                self.timeline.bTimeline.commit()

            self.timeline.current_group = GES.Group()

            self.app.action_log.commit()
            self.bTimeline.commit()

    def _groupSelected(self, unused_action):
        if self.bTimeline:
            self.app.action_log.begin("group")

            containers = set({})

            for obj in self.timeline.selection:
                toplevel = obj.get_toplevel_parent()
                if toplevel == self.timeline.current_group:
                    for child in toplevel.get_children(False):
                        containers.add(child)
                    toplevel.ungroup(False)
                else:
                    containers.add(toplevel)

            if containers:
                group = GES.Container.group(list(containers))

            self.timeline.current_group = GES.Group()

            self.bTimeline.commit()
            self.app.action_log.commit()

    def _alignSelected(self, unused_action):
        if not self.bTimeline:
            self.error("Trying to use the autoalign feature with an empty timeline")
            return

        progress_dialog = AlignmentProgressDialog(self.app)
        progress_dialog.window.show()
        self.app.action_log.begin("align")

        def alignedCb():  # Called when alignment is complete
            self.app.action_log.commit()
            self.bTimeline.commit()
            progress_dialog.window.destroy()

        auto_aligner = AutoAligner(self.timeline.selection, alignedCb)
        try:
            progress_meter = auto_aligner.start()
            progress_meter.addWatcher(progress_dialog.updatePosition)
        except Exception, e:
            self.error("Could not start the autoaligner: %s" % e)
            progress_dialog.window.destroy()

    def _split(self, action):
        """
        If clips are selected, split them at the current playhead position.
        Otherwise, split all clips at the playhead position.
        """
        selected = self.timeline.selection.getSelectedTrackElements()

        if selected:
            self._splitElements(selected)
        else:
            for track in self.bTimeline.get_tracks():
                self._splitElements(track.get_elements())

        self.bTimeline.commit()

    def _splitElements(self, elements):
        position = self.app.current_project.pipeline.getPosition()
        for element in elements:
            start = element.get_start()
            end = start + element.get_duration()
            if start < position and end > position:
                clip = element.get_parent()
                clip.split(position)

    def _keyframe(self, action):
        """
        Add or remove a keyframe at the current position of the selected clip.

        FIXME GES: this method is currently not used anywhere
        """
        selected = self.timeline.selection.getSelectedTrackElements()

        for obj in selected:
            keyframe_exists = False
            position = self.app.current_project.pipeline.getPosition()
            position_in_obj = (position - obj.start) + obj.in_point
            interpolators = obj.getInterpolators()
            for value in interpolators:
                interpolator = obj.getInterpolator(value)
                keyframes = interpolator.getInteriorKeyframes()
                for kf in keyframes:
                    if kf.getTime() == position_in_obj:
                        keyframe_exists = True
                        self.app.action_log.begin("remove volume point")
                        interpolator.removeKeyframe(kf)
                        self.app.action_log.commit()
                if keyframe_exists is False:
                    self.app.action_log.begin("add volume point")
                    interpolator.newKeyframe(position_in_obj)
                    self.app.action_log.commit()

    def _playPause(self, unused_action):
        self.app.current_project.pipeline.togglePlayback()

    def transposeXY(self, x, y):
        height = self.ruler.get_allocation().height
        x += self.timeline.get_scroll_point().x
        return x - CONTROL_WIDTH, y - height

    def _showSaveScreenshotDialog(self):
        """
        Show a filechooser dialog asking the user where to save the snapshot
        and what file type to use.

        Returns a list containing the full path and the mimetype if successful,
        returns none otherwise.
        """
        chooser = Gtk.FileChooserDialog(title=_("Save As..."), transient_for=self.app.gui,
            action=Gtk.FileChooserAction.SAVE)
        chooser.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        chooser.set_icon_name("pitivi")
        chooser.set_select_multiple(False)
        chooser.set_current_name(_("Untitled"))
        chooser.props.do_overwrite_confirmation = True
        formats = {_("PNG image"): ["image/png", ("png",)],
            _("JPEG image"): ["image/jpeg", ("jpg", "jpeg")]}
        for format in formats:
            filt = Gtk.FileFilter()
            filt.set_name(format)
            filt.add_mime_type(formats.get(format)[0])
            chooser.add_filter(filt)
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            chosen_format = formats.get(chooser.get_filter().get_name())
            chosen_ext = chosen_format[1][0]
            chosen_mime = chosen_format[0]
            uri = os.path.join(chooser.get_current_folder(), chooser.get_filename())
            ret = [uri + "." + chosen_ext, chosen_mime]
        else:
            ret = None
        chooser.destroy()
        return ret

    # Interface

    # Zoomable

    def zoomChanged(self):
        if self._settings and self.bTimeline:
            # zoomChanged might be called various times before the UI is ready
            self.bTimeline.set_snapping_distance(Zoomable.pixelToNs(self._settings.edgeSnapDeadband))

        self.updateHScrollAdjustments()

    # Callbacks

    def _keyPressEventCb(self, widget, event):
        # This is used both for changing the selection modes and for affecting
        # the seek keyboard shortcuts further below
        if event.keyval == Gdk.KEY_Shift_L:
            self._shiftMask = True
        elif event.keyval == Gdk.KEY_Control_L:
            self._controlMask = True

        # Now the second (independent) part: framestepping and seeking shortcuts
        if event.keyval == Gdk.KEY_Left:
            if self._shiftMask:
                self._seeker.seekRelative(0 - Gst.SECOND)
            else:
                self._project.pipeline.stepFrame(self._framerate, -1)
        elif event.keyval == Gdk.KEY_Right:
            if self._shiftMask:
                self._seeker.seekRelative(Gst.SECOND)
            else:
                self._project.pipeline.stepFrame(self._framerate, 1)

    def _keyReleaseEventCb(self, widget, event):
        if event.keyval == Gdk.KEY_Shift_L:
            self._shiftMask = False
        elif event.keyval == Gdk.KEY_Control_L:
            self._controlMask = False

    def _focusInCb(self, unused_widget, unused_arg):
        self.log("Timeline has grabbed focus")
        self.setActionsSensitivity(True)

    def _focusOutCb(self, unused_widget, unused_arg):
        self.log("Timeline has lost focus")
        self.setActionsSensitivity(False)

    def _timelineClickedCb(self, unused_timeline, event):
        self.pressed = True
        self.grab_focus()  # Prevent other widgets from being confused

    def _timelineClickReleasedCb(self, unused_timeline, event):
        if self.app and self.timeline.allowSeek is True:
            position = self.pixelToNs(event.x - CONTROL_WIDTH + self.timeline._scroll_point.x)
            self._seeker.seek(position)

        self.timeline.allowSeek = True
        self.timeline._snapEndedCb()

    def _renderingSettingsChangedCb(self, project, item, value):
        """
        Called when any Project metadata changes, we filter out the one
        we are interested in.

        if @item is None, it mean we called it ourself, and want to force
        getting the project videorate value
        """
        if item == "videorate" or item is None:
            if value is None:
                value = project.videorate
            self._framerate = value

            self.ruler.setProjectFrameRate(self._framerate)

        if item == "width" or item == "height" or item == "videorate":
            project.update_restriction_caps()

    def _snapDistanceChangedCb(self, settings):
        if self.bTimeline:
            self.bTimeline.set_snapping_distance(Zoomable.pixelToNs(self._settings.edgeSnapDeadband))

    def _projectChangedCb(self, app, project, unused_fully_loaded):
        """
        When a project is loaded, we connect to its pipeline
        """

        if project:
            self._seeker = self._project.seeker
            self.timeline.setPipeline(self._project.pipeline)

            self.ruler.setProjectFrameRate(self._project.videorate)
            self.ruler.zoomChanged()

            self._renderingSettingsChangedCb(self._project, None, None)
            self._setBestZoomRatio()

    def _projectCreatedCb(self, app, project):
        """
        When a project is created, we connect to it timeline
        """
        if self._project:
            self._project.disconnect_by_func(self._renderingSettingsChangedCb)
            try:
                self.timeline.pipeline.disconnect_by_func(self.timeline.positionCb)
            except AttributeError:
                pass
            except TypeError:
                pass  # We were not connected no problem

            self.timeline.pipeline = None
            self._seeker = None

        self._project = project
        if self._project:
            self._project.connect("rendering-settings-changed",
                                  self._renderingSettingsChangedCb)
            self.setTimeline(project.timeline)

    def _zoomInCb(self, unused_action):
        Zoomable.zoomIn()
        self.log("Setting 'zoomed_fitted' to False")
        self.zoomed_fitted = False

    def _zoomOutCb(self, unused_action):
        Zoomable.zoomOut()
        self.log("Setting 'zoomed_fitted' to False")
        self.zoomed_fitted = False

    def _zoomFitCb(self, unused, unsued2=None):
        self._setBestZoomRatio(allow_zoom_in=True)

    def _screenshotCb(self, unused_action):
        """
        Export a snapshot of the current frame as an image file.
        """
        foo = self._showSaveScreenshotDialog()
        if foo:
            path, mime = foo[0], foo[1]
            self._project.pipeline.save_thumbnail(-1, -1, mime, path)

    def _previousKeyframeCb(self, action):
        position = self.app.current_project.pipeline.getPosition()
        prev_kf = self.timeline.getPrevKeyframe(position)
        if prev_kf:
            self._seeker.seek(prev_kf)
            self.scrollToPlayhead()

    def _nextKeyframeCb(self, action):
        position = self.app.current_project.pipeline.getPosition()
        next_kf = self.timeline.getNextKeyframe(position)
        if next_kf:
            self._seeker.seek(next_kf)
            self.scrollToPlayhead()

    def _scrollEventCb(self, embed, event):
        # FIXME : see https://bugzilla.gnome.org/show_bug.cgi?id=697522
        deltas = event.get_scroll_deltas()
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if deltas[2] < 0:
                Zoomable.zoomIn()
            elif deltas[2] > 0:
                Zoomable.zoomOut()
            self._scrollToPlayhead()
        elif event.state & Gdk.ModifierType.SHIFT_MASK:
            if deltas[2] > 0:
                self.scroll_down()
            elif deltas[2] < 0:
                self.scroll_up()
        else:
            if deltas[2] > 0:
                self.scroll_right()
            elif deltas[2] < 0:
                self.scroll_left()
        self.scrolled += 1

    def _selectionChangedCb(self, selection):
        """
        The selected clips on the timeline canvas have changed with the
        "selection-changed" signal.

        This is where you apply global UI changes, unlike individual
        track elements' "selected-changed" signal from the Selected class.
        """
        if selection:
            self.selection_actions.set_sensitive(True)
        else:
            self.selection_actions.set_sensitive(False)

    # drag and drop

    def _dragDataReceivedCb(self, widget, context, x, y, data, info, time):
        if not self.dropDataReady:
            if data.get_length() > 0:
                if not self.dropOccured:
                    self.timeline.resetGhostClips()
                self.dropData = data.get_uris()
                self.dropDataReady = True

        if self.dropOccured:
            self.dropOccured = False
            Gtk.drag_finish(context, True, False, time)
            self._dragLeaveCb(widget, context, time)
        else:
            self.isDraggedClip = True

    def _dragDropCb(self, widget, context, x, y, time):
        # Same as in insertEnd: this value changes during insertion, snapshot it
        zoom_was_fitted = self.zoomed_fitted

        target = widget.drag_dest_find_target(context, None)
        y -= self.ruler.get_allocation().height
        if target.name() == "text/uri-list":
            self.dropOccured = True
            widget.drag_get_data(context, target, time)
            if self.isDraggedClip:
                self.timeline.convertGhostClips()
                self.timeline.resetGhostClips()
                if zoom_was_fitted:
                    self._setBestZoomRatio()
                else:
                    x, y = self.transposeXY(x, y)
                    # Add a margin (up to 50px) on the left, this prevents
                    # disorientation & clarifies to users where the clip starts
                    margin = min(x, 50)
                    self.scrollToPixel(x - margin)
            else:
                actor = self.stage.get_actor_at_pos(Clutter.PickMode.ALL, x, y)
                try:
                    bElement = actor.bElement
                    self.app.gui.clipconfig.effect_expander.addEffectToClip(bElement.get_parent(), self.dropData[0])
                except AttributeError:
                    return False
            return True
        else:
            return False

    def _dragMotionCb(self, widget, context, x, y, time):
        target = widget.drag_dest_find_target(context, None)
        if target.name() not in ["text/uri-list", "pitivi/effect"]:
            return False
        if not self.dropDataReady:
            widget.drag_get_data(context, target, time)
            Gdk.drag_status(context, 0, time)
        else:
            x, y = self.transposeXY(x, y)

            # dragged from the media library
            if not self.timeline.ghostClips and self.isDraggedClip:
                for uri in self.dropData:
                    asset = self.app.gui.medialibrary.getAssetForUri(uri)
                    if asset is None:
                        self.isDraggedClip = False
                        break
                    self.timeline.addGhostClip(asset, x, y)

            if self.isDraggedClip:
                self.timeline.updateGhostClips(x, y)

            Gdk.drag_status(context, Gdk.DragAction.COPY, time)
            if not self.dropHighlight:
                widget.drag_highlight()
                self.dropHighlight = True
        return True

    def _dragLeaveCb(self, widget, context, time):
        if self.dropDataReady:
            self.dropDataReady = False
        if self.dropHighlight:
            widget.drag_unhighlight()
            self.dropHighlight = False

        self.timeline.removeGhostClips()

    # Standalone

    # Standalone public API

    def run(self):
        self.testTimeline(self.timeline)
        GLib.io_add_watch(sys.stdin, GLib.IO_IN, quit2_)
        Gtk.main()

    def addClipToLayer(self, layer, asset, start, duration, inpoint):
        layer.add_asset(asset, start * Gst.SECOND, 0, duration * Gst.SECOND, asset.get_supported_formats())

    def togglePlayback(self, button):
        self.pipeline.togglePlayback()

    def testTimeline(self, timeline):
        timeline.set_easing_duration(600)

        Gst.init([])
        GES.init()

        self.project = GES.Project(uri=None, extractable_type=GES.Timeline)

        bTimeline = GES.Timeline()
        bTimeline.add_track(GES.AudioTrack.new())
        bTimeline.add_track(GES.VideoTrack.new())

        self.bTimeline = bTimeline
        timeline.setTimeline(bTimeline)

        self.stage.connect("destroy", quit_)

        layer = GES.Layer()
        bTimeline.add_layer(layer)

        self.bTimeline = bTimeline

        self.project.connect("asset-added", self._doAssetAddedCb, layer)
        self.project.create_asset("file://" + sys.argv[2], GES.UriClip)

    # Standalone callbacks

    def _doAssetAddedCb(self, project, asset, layer):
        self.addClipToLayer(layer, asset, 2, 10, 5)
        self.addClipToLayer(layer, asset, 15, 10, 5)

        Zoomable.setZoomLevel(50)


def main():
    # Basic argument handling, no need for getopt here
    if len(sys.argv) < 3:
        print "Supply a uri as argument"
        sys.exit()

    print "Starting stupid demo, using uri as a new clip, with start = 2, duration = 25 and inpoint = 5."
    print "Use ipython if you want to interact with the timeline in a more interesting way"
    print "ipython ; %gui gtk3 ; %run timeline.py ; help yourself"

    window = Gtk.Window()
    widget = Timeline(None, None, None)
    window.add(widget)
    window.maximize()
    window.show_all()
    widget.run()
