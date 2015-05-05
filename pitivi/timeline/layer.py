# -- coding: utf-8 --
# Pitivi video editor
#
#       pitivi/timeline/layer.py
#
# Copyright (c) 2012, Paul Lange <palango@gmx.de>
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

from gi.repository import Gtk
from gi.repository import GES
from gi.repository import GObject

from gettext import gettext as _

from pitivi.timeline import elements
from pitivi.utils.loggable import Loggable
from pitivi.utils import ui
from pitivi.utils import timeline as timelineUtils


class BaseLayerControl(Gtk.Box, Loggable):

    """
    Base Layer control classes
    """

    __gtype_name__ = 'LayerControl'

    def __init__(self, control_container, layer, layer_type, app):
        Gtk.Box.__init__(self, spacing=0)
        Loggable.__init__(self)

        self._app = app
        self._control_container = control_container
        self.layer = layer
        self._selected = False

        context = self.get_style_context()

        # get the default color for the current theme
        self.UNSELECTED_COLOR = context.get_background_color(
            Gtk.StateFlags.NORMAL)
        # use base instead of bg colors so that we get the lighter color
        # that is used for list items in TreeView.
        self.SELECTED_COLOR = context.get_background_color(
            Gtk.StateFlags.SELECTED)

        self.set_orientation(Gtk.Orientation.VERTICAL)

        table = Gtk.Table(n_rows=2, n_columns=2)
        table.set_border_width(2)
        table.set_row_spacings(3)
        table.set_col_spacings(3)

        self.eventbox = Gtk.EventBox()
        self.eventbox.add(table)
        self.eventbox.connect("button_press_event", self._buttonPressCb)
        self.pack_start(self.eventbox, True, True, 0)

        icon_mapping = {GES.TrackType.AUDIO: "audio-x-generic",
                        GES.TrackType.VIDEO: "video-x-generic"}

        # Folding button
        # TODO use images
        fold_button = TwoStateButton("▼", "▶")
        fold_button.set_relief(Gtk.ReliefStyle.NONE)
        fold_button.set_focus_on_click(False)
        fold_button.connect("changed-state", self._foldingChangedCb)
        table.attach(fold_button, 0, 1, 0, 1)

        # Name entry
        self.name_entry = Gtk.Entry()
        self.name_entry.set_tooltip_text(
            _("Set a personalized name for this layer"))
        self.name_entry.set_property(
            "primary-icon-name", icon_mapping[layer_type])
        self.name_entry.connect("button_press_event", self._buttonPressCb)
#        self.name_entry.drag_dest_unset()
        self.name_entry.set_sensitive(False)

        # 'Solo' toggle button
        self.solo_button = Gtk.ToggleButton()
        self.solo_button.set_tooltip_markup(_("<b>Solo mode</b>\n"
                                              "Other non-soloed layers will be disabled as long as "
                                              "this is enabled."))
        solo_image = Gtk.Image()
        solo_image.set_from_icon_name(
            "avatar-default-symbolic", Gtk.IconSize.MENU)
        self.solo_button.add(solo_image)
        self.solo_button.connect("toggled", self._soloToggledCb)
        self.solo_button.set_relief(Gtk.ReliefStyle.NONE)
        self.solo_button.set_sensitive(False)

        # CheckButton
        visible_option = Gtk.CheckButton()
        visible_option.connect("toggled", self._visibilityChangedCb)
        visible_option.set_active(True)
        visible_option.set_sensitive(False)
        visible_option.set_tooltip_markup(_("<b>Enable or disable this layer</b>\n"
                                            "Disabled layers will not play nor render."))

        # Upper bar
        upper = Gtk.Box()
        upper.set_orientation(Gtk.Orientation.HORIZONTAL)
        upper.pack_start(self.name_entry, True, True, 0)
        upper.pack_start(self.solo_button, False, False, 0)
        upper.pack_start(visible_option, False, False, 0)

        # Lower bar
        self.lower_hbox = Gtk.Box()
        self.lower_hbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.lower_hbox.set_sensitive(False)

        table.attach(upper, 1, 2, 0, 1)
        table.attach(self.lower_hbox, 1, 2, 1, 2)

        self.show_all()

        # Popup Menu
        self.popup = Gtk.Menu()
        layer_delete = Gtk.MenuItem.new_with_label(_("_Delete layer"))
        layer_delete.connect("activate", self._deleteLayerCb)
        self.layer_up = Gtk.MenuItem.new_with_label(_("Move layer up"))
        self.layer_up.connect("activate", self._moveLayerCb, -1)
        self.layer_down = Gtk.MenuItem.new_with_label(_("Move layer down"))
        self.layer_down.connect("activate", self._moveLayerCb, 1)
        self.layer_first = Gtk.MenuItem.new_with_label(_("Move layer to top"))
        self.layer_first.connect("activate", self._moveLayerCb, -2)
        self.layer_last = Gtk.MenuItem.new_with_label(
            _("Move layer to bottom"))
        self.layer_last.connect("activate", self._moveLayerCb, 2)

        self.popup.append(self.layer_first)
        self.popup.append(self.layer_up)
        self.popup.append(self.layer_down)
        self.popup.append(self.layer_last)
        self.popup.append(Gtk.SeparatorMenuItem())
        self.popup.append(layer_delete)
        for menu_item in self.popup:
            menu_item.set_use_underline(True)
        self.popup.show_all()

        # Drag and drop

    def getSelected(self):
        return self._selected

    def setSelected(self, selected):
        if selected != self._selected:
            self._selected = selected
            self._selectionChangedCb()

    selected = property(getSelected, setSelected, None, "Selection state")

    def _foldingChangedCb(self, unused_button, state):
        if state:
            self.lower_hbox.show()
        else:
            self.lower_hbox.hide()

    def _visibilityChangedCb(self, button):
        if button.get_active():
            button.set_tooltip_text(_("Make layer invisible"))
        else:
            button.set_tooltip_text(_("Make layer visible"))

    def _soloToggledCb(self, button):
        """
        Send TimelineControls the new solo-ed layer
        """
        if button.get_active():
            # Disable all other layers
            self._app.gui.timeline_ui.controls.soloLayer(self.layer)
        else:
            # Enable all layers
            self._app.gui.timeline_ui.controls.soloLayer(None)

    def _buttonPressCb(self, unused_widget, event):
        """
        Look if user selected layer or wants popup menu
        """
        # FIXME!! self._control_container.selectLayerControl(self)
        if event.button == 3:
            self.popup.popup(None, None, None, None, event.button, event.time)

    def _selectionChangedCb(self):
        """
        Called when the selection state changes
        """
        if self.selected:
            self.eventbox.override_background_color(
                Gtk.StateType.NORMAL, self.SELECTED_COLOR)
            self.name_entry.override_background_color(
                Gtk.StateType.NORMAL, self.SELECTED_COLOR)
        else:
            self.eventbox.override_background_color(
                Gtk.StateType.NORMAL, self.UNSELECTED_COLOR)
            self.name_entry.override_background_color(
                Gtk.StateType.NORMAL, self.UNSELECTED_COLOR)

        # continue GTK signal propagation
        return True

    def _deleteLayerCb(self, unused_widget):
        self._app.action_log.begin("delete layer")
        bLayer = self.layer.bLayer
        bTimeline = bLayer.get_timeline()
        bTimeline.remove_layer(bLayer)
        bTimeline.get_asset().pipeline.commit_timeline()
        self._app.action_log.commit()

    def _moveLayerCb(self, unused_widget, step):
        index = self.layer.bLayer.get_priority()
        if abs(step) == 1:
            index += step
        elif step == -2:
            index = 0
        else:
            index = len(self.layer.bLayer.get_timeline().get_layers()) - 1
            # if audio, set last position

        self._app.moveLayer(self, index)
        # self._app.timeline.parent.app.gui.timeline_ui.controls.moveControlWidget(self, index)

    def getHeight(self):
        return self.get_allocation().height

    def getSeparatorHeight(self):
        return self.sep.get_allocation().height

    def getControlHeight(self):
        return self.getHeight() - self.getSeparatorHeight()

    def setSoloState(self, state):
        self.solo_button.set_active(state)

    def setSeparatorVisibility(self, visible):
        if visible:
            self.sep.show()
        else:
            self.sep.hide()

    def updateMenuSensitivity(self, position):
        """
        Update Menu item sensitivity

        0 = first item -> disable "up" and "first"
        -1 = last item -> disable "down" and "last"
        -2 = first and last item -> all disabled
        """
        for menu_item in (self.layer_up, self.layer_first,
                          self.layer_down, self.layer_last):
            menu_item.set_sensitive(True)

        if position == -2 or position == 0:
            self.layer_first.set_sensitive(False)
            self.layer_up.set_sensitive(False)

        if position == -2 or position == -1:
            self.layer_down.set_sensitive(False)
            self.layer_last.set_sensitive(False)

    def setSeparatorHighlight(self, highlighted):
        """
        Sets if the Separator should be highlighted

        Used for visual drag'n'drop feedback
        """
        if highlighted:
            self.sep.override_background_color(
                Gtk.StateType.NORMAL, self.SELECTED_COLOR)
        else:
            self.sep.override_background_color(
                Gtk.StateType.NORMAL, self.UNSELECTED_COLOR)


class VideoLayerControl(BaseLayerControl):
    """
    Layer control class for video layers
    """

    __gtype_name__ = 'VideoLayerControl'

    def __init__(self, control_container, layer, app):
        BaseLayerControl.__init__(
            self, control_container, layer, GES.TrackType.VIDEO, app)

        opacity = Gtk.Label(label=_("Opacity:"))

        # Opacity scale
        opacity_adjust = Gtk.Adjustment(
            value=100, upper=100, step_increment=5, page_increment=10)
        opacity_scale = Gtk.Scale.new(
            Gtk.Orientation.HORIZONTAL, adjustment=opacity_adjust)
        opacity_scale.set_value_pos(Gtk.PositionType.LEFT)
        opacity_scale.set_digits(0)
        opacity_scale.set_tooltip_text(_("Change video opacity"))

        self.lower_hbox.pack_start(opacity, False, False, 0)
        self.lower_hbox.pack_start(opacity_scale, True, True, 0)
        self.lower_hbox.show_all()


class AudioLayerControl(BaseLayerControl):
    """
    Layer control class for audio layers
    """

    __gtype_name__ = 'AudioLayerControl'

    def __init__(self, control_container, layer, app):
        BaseLayerControl.__init__(
            self, control_container, layer, GES.TrackType.AUDIO, app)

        volume = Gtk.Label(label=_("Vol:"))
        volume_button = Gtk.VolumeButton(size=Gtk.IconSize.MENU)

        panning = Gtk.Label(label=_("Pan:"))
        # Volume scale
        panning_adjust = Gtk.Adjustment(
            value=0, lower=-100, upper=100, step_increment=5, page_increment=10)
        panning_scale = Gtk.Scale.new(
            Gtk.Orientation.HORIZONTAL, adjustment=panning_adjust)
        panning_scale.set_value_pos(Gtk.PositionType.LEFT)
        panning_scale.set_digits(0)
        panning_scale.set_tooltip_text(_("Change audio panning"))

        self.lower_hbox.pack_start(volume, False, False, 0)
        self.lower_hbox.pack_start(volume_button, False, False, 0)
        self.lower_hbox.pack_start(panning, False, False, 0)
        self.lower_hbox.pack_start(panning_scale, True, True, 0)
        self.lower_hbox.show_all()


class TwoStateButton(Gtk.Button):
    """
    Button with two states and according labels/images
    """

    __gsignals__ = {
        "changed-state": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,),)
    }

    def __init__(self, state1="", state2=""):
        Gtk.Button.__init__(self)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.connect("clicked", self._clickedCb)

        self.set_states(state1, state2)
        self._state = True

        self.set_label(self.states[self._state])

    def set_states(self, state1, state2):
        self.states = {True: state1, False: state2}

    def _clickedCb(self, unused_widget):
        self._state = not self._state

        self.set_label(self.states[self._state])
        self.emit("changed-state", self._state)


class SpacedSeparator(Gtk.EventBox):
    """
    A Separator with vertical spacing

    Inherits from EventBox since we want to change background color
    """

    def __init__(self):
        Gtk.EventBox.__init__(self)

        self.box = Gtk.Box()
        self.box.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(self.box)

        self.get_style_context().add_class("SpacedSeparator")
        self.box.get_style_context().add_class("SpacedSeparator")


class LayerControls(Gtk.Bin, Loggable):

    __gtype_name__ = 'PitiviLayerControls'

    def __init__(self, bLayer, app):
        super(LayerControls, self).__init__()
        Loggable.__init__(self)

        ebox = Gtk.EventBox()
        self.add(ebox)
        self._hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ebox.add(self._hbox)
        self.bLayer = bLayer
        self.app = app

        sep = SpacedSeparator()
        self._hbox.pack_start(sep, False, False, 5)

        self.video_control = VideoLayerControl(None, self, self.app)
        self.video_control.set_visible(True)
        self.video_control.props.width_request = ui.CONTROL_WIDTH
        self.video_control.props.height_request = ui.LAYER_HEIGHT / 2
        self._hbox.add(self.video_control)

        self.audio_control = AudioLayerControl(None, self, self.app)
        self.audio_control.set_visible(True)
        self.audio_control.props.height_request = ui.LAYER_HEIGHT / 2
        self.audio_control.props.width_request = ui.CONTROL_WIDTH
        self._hbox.add(self.audio_control)

        self._hbox.props.vexpand = False
        self._hbox.props.width_request = ui.CONTROL_WIDTH
        self.props.width_request = ui.CONTROL_WIDTH

        sep = SpacedSeparator()
        self._hbox.pack_start(sep, False, False, 5)


class LayerLayout(Gtk.Layout, Loggable):
    """
    A GtkLayout that exclusivly container Clips.
    This allows us to properly handle the z order of
    """
    __gtype_name__ = "PitiviLayerLayout"

    def __init__(self, timeline):
        super(LayerLayout, self).__init__()
        Loggable.__init__(self)

        self._children = []
        self._changed = False
        self.timeline = timeline

        self.props.hexpand = True
        self.get_style_context().add_class("LayerLayout")

    def do_add(self, widget):
        self._children.append(widget)
        self._children.sort(key=lambda clip: clip.z_order)
        Gtk.Layout.do_add(self, widget)
        self._changed = True

        for child in self._children:
            if isinstance(child, elements.TransitionClip):
                window = child.get_window()
                if window is not None:
                    window.raise_()

    def do_remove(self, widget):
        self._children.remove(widget)
        self._changed = True
        Gtk.Layout.do_remove(self, widget)

    def put(self, child, x, y):
        self._children.append(child)
        self._children.sort(key=lambda clip: clip.z_order)
        Gtk.Layout.put(self, child, x, y)
        self._changed = True

    def do_draw(self, cr):
        if self._changed:
            self._children.sort(key=lambda clip: clip.z_order)
            for child in self._children:

                if isinstance(child, elements.TransitionClip):
                    window = child.get_window()
                    window.raise_()
            self._changed = False

        self.props.width = max(self.timeline.layout.get_allocation().width,
                               timelineUtils.Zoomable.nsToPixel(self.timeline.bTimeline.props.duration))
        self.props.width_request = max(self.timeline.layout.get_allocation().width,
                                       timelineUtils.Zoomable.nsToPixel(self.timeline.bTimeline.props.duration))

        for child in self._children:
            self.propagate_draw(child, cr)


class Layer(Gtk.EventBox, timelineUtils.Zoomable, Loggable):

    __gtype_name__ = "PitiviLayer"

    __gsignals__ = {
        "remove-me": (GObject.SignalFlags.RUN_LAST, None, (),)
    }

    def __init__(self, bLayer, timeline):
        super(Layer, self).__init__()
        Loggable.__init__(self)

        self.bLayer = bLayer
        self.bLayer.ui = self
        self.timeline = timeline
        self.app = timeline.app

        self.bLayer.connect("clip-added", self._clipAddedCb)
        self.bLayer.connect("clip-removed", self._clipRemovedCb)

        # FIXME Make the layer height user setable with 'Paned'
        self.props.height_request = ui.LAYER_HEIGHT
        self.props.valign = Gtk.Align.START

        self._layout = LayerLayout(self.timeline)
        self.add(self._layout)

        self.media_types = GES.TrackType(0)
        for clip in bLayer.get_clips():
            self._addClip(clip)

        self.before_sep = None
        self.after_sep = None

    def checkMediaTypes(self, bClip=None):
        if self.timeline.editing_context:
            self.info("Not updating media types as"
                      " we are editing the timeline")
            return
        self.media_types = GES.TrackType(0)
        bClips = self.bLayer.get_clips()

        """
        FIXME: That produces segfault in GES/GSequence
        if not bClips:
            self.emit("remove-me")
            return
        """

        for bClip in bClips:
            for child in bClip.get_children(False):
                self.media_types |= child.get_track().props.track_type
                if self.media_types == (GES.TrackType.AUDIO | GES.TrackType.VIDEO):
                    break

        if not (self.media_types & GES.TrackType.AUDIO) and not (self.media_types & GES.TrackType.VIDEO):
            self.media_types = GES.TrackType.AUDIO | GES.TrackType.VIDEO

        height = 0
        if self.media_types & GES.TrackType.AUDIO:
            height += ui.LAYER_HEIGHT / 2
            self.bLayer.control_ui.audio_control.show()
        else:
            self.bLayer.control_ui.audio_control.hide()

        if self.media_types & GES.TrackType.VIDEO:
            self.bLayer.control_ui.video_control.show()
            height += ui.LAYER_HEIGHT / 2
        else:
            self.bLayer.control_ui.video_control.hide()

        self.props.height_request = height
        self.bLayer.control_ui.props.height_request = height

    def move(self, child, x, y):
        self._layout.move(child, x, y)

    def _childAddedCb(self, bClip, child):
        self.checkMediaTypes()

    def _childRemovedCb(self, bClip, child):
        self.checkMediaTypes()

    def _clipAddedCb(self, layer, bClip):
        self._addClip(bClip)

    def _addClip(self, bClip):
        ui_type = elements.GES_TYPE_UI_TYPE.get(bClip.__gtype__, None)
        if ui_type is None:
            self.error("Implement UI for type %s?" % bClip.__gtype__)
            return

        if not hasattr(bClip, "ui") or bClip.ui is None:
            clip = ui_type(self, bClip)
        else:
            clip = bClip.ui

        self._layout.put(clip, self.nsToPixel(bClip.props.start), 0)
        self.show_all()
        bClip.connect_after("child-added", self._childAddedCb)
        bClip.connect_after("child-removed", self._childRemovedCb)
        self.checkMediaTypes()

    def _clipRemovedCb(self, bLayer, bClip):
        self._removeClip(bClip)

    def _removeClip(self, bClip):
        ui_type = elements.GES_TYPE_UI_TYPE.get(bClip.__gtype__, None)
        if ui_type is None:
            self.error("Implement UI for type %s?" % bClip.__gtype__)
            return

        self._layout.remove(bClip.ui)
        if self.timeline.draggingElement is None:
            bClip.ui = None

        bClip.disconnect_by_func(self._childAddedCb)
        bClip.disconnect_by_func(self._childRemovedCb)
        self.checkMediaTypes(bClip)

    def updatePosition(self):
        for bClip in self.bLayer.get_clips():
            bClip.ui.updatePosition()

    def do_draw(self, cr):
        Gtk.Box.do_draw(self, cr)
