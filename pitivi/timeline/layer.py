# -- coding: utf-8 --
# PiTiVi , Non-linear video editor
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
from gi.repository import Gdk
from gi.repository import GES
from gi.repository import GObject

from gettext import gettext as _

from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import LAYER_CONTROL_TARGET_ENTRY


# TODO GTK3 port to GtkGrid
class BaseLayerControl(Gtk.VBox, Loggable):
    """
    Base Layer control classes
    """

    __gtype_name__ = 'LayerControl'

    def __init__(self, app, layer, layer_type):
        Gtk.VBox.__init__(self, spacing=0)
        Loggable.__init__(self)

        self._app = app
        self.layer = layer
        self._selected = False

        context = self.get_style_context()

        # get the default color for the current theme
        self.UNSELECTED_COLOR = context.get_background_color(Gtk.StateFlags.NORMAL)
        # use base instead of bg colors so that we get the lighter color
        # that is used for list items in TreeView.
        self.SELECTED_COLOR = context.get_background_color(Gtk.StateFlags.SELECTED)

        table = Gtk.Table(rows=2, columns=2)
        table.set_border_width(2)
        table.set_row_spacings(3)
        table.set_col_spacings(3)

        self.eventbox = Gtk.EventBox()
        self.eventbox.add(table)
        self.eventbox.connect("button_press_event", self._buttonPressCb)
        self.pack_start(self.eventbox, True, True, 0)

        self.sep = SpacedSeparator()
        self.pack_start(self.sep, True, True, 0)

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
        self.name_entry.set_tooltip_text(_("Set a personalized name for this layer"))
        self.name_entry.set_property("primary-icon-name", icon_mapping[layer_type])
        self.name_entry.connect("focus-in-event", self._focusChangeCb, False)
        self.name_entry.connect("focus-out-event", self._focusChangeCb, True)
        self.name_entry.connect("button_press_event", self._buttonPressCb)
        self.name_entry.drag_dest_unset()
        self.name_entry.set_sensitive(False)

        # 'Solo' toggle button
        self.solo_button = Gtk.ToggleButton()
        self.solo_button.set_tooltip_markup(_("<b>Solo mode</b>\n"
                        "Other non-soloed layers will be disabled as long as "
                        "this is enabled."))
        solo_image = Gtk.Image()
        solo_image.set_from_icon_name("avatar-default-symbolic", Gtk.IconSize.MENU)
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
        upper = Gtk.HBox()
        upper.pack_start(self.name_entry, True, True, 0)
        upper.pack_start(self.solo_button, False, False, 0)
        upper.pack_start(visible_option, False, False, 0)

        # Lower bar
        self.lower_hbox = Gtk.HBox()
        self.lower_hbox.set_sensitive(False)

        table.attach(upper, 1, 2, 0, 1)
        table.attach(self.lower_hbox, 1, 2, 1, 2)

        self.show_all()

        # Popup Menu
        self.popup = Gtk.Menu()
        layer_delete = Gtk.ImageMenuItem(_("_Delete layer"))
        layer_delete.connect("activate", self._deleteLayerCb)
        layer_delete.set_image(Gtk.Image.new_from_icon_name("edit-delete", Gtk.IconSize.MENU))
        self.layer_up = Gtk.ImageMenuItem(_("Move layer up"))
        self.layer_up.connect("activate", self._moveLayerCb, -1)
        self.layer_up.set_image(Gtk.Image.new_from_icon_name("go-up", Gtk.IconSize.MENU))
        self.layer_down = Gtk.ImageMenuItem(_("Move layer down"))
        self.layer_down.connect("activate", self._moveLayerCb, 1)
        self.layer_down.set_image(Gtk.Image.new_from_icon_name("go-down", Gtk.IconSize.MENU))
        self.layer_first = Gtk.ImageMenuItem(_("Move layer to top"))
        self.layer_first.connect("activate", self._moveLayerCb, -2)
        self.layer_first.set_image(Gtk.Image.new_from_icon_name("go-top", Gtk.IconSize.MENU))
        self.layer_last = Gtk.ImageMenuItem(_("Move layer to bottom"))
        self.layer_last.connect("activate", self._moveLayerCb, 2)
        self.layer_last.set_image(Gtk.Image.new_from_icon_name("go-bottom", Gtk.IconSize.MENU))

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
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                             [LAYER_CONTROL_TARGET_ENTRY],
                             Gdk.DragAction.MOVE)

    def getSelected(self):
        return self._selected

    def setSelected(self, selected):
        if selected != self._selected:
            self._selected = selected
            self._selectionChangedCb()

    selected = property(getSelected, setSelected, None, "Selection state")

    def _foldingChangedCb(self, button, state):
        if state:
            self.lower_hbox.show()
        else:
            self.lower_hbox.hide()

    def _visibilityChangedCb(self, button):
        if button.get_active():
            button.set_tooltip_text(_("Make layer invisible"))
        else:
            button.set_tooltip_text(_("Make layer visible"))

    def _focusChangeCb(self, widget, direction, sensitive_actions):
        self._app.gui.setActionsSensitive(sensitive_actions)

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

    def _buttonPressCb(self, widget, event):
        """
        Look if user selected layer or wants popup menu
        """
        self._app.gui.timeline_ui.controls.selectLayerControl(self)
        if event.button == 3:
            self.popup.popup(None, None, None, None, event.button, event.time)

    def _selectionChangedCb(self):
        """
        Called when the selection state changes
        """
        if self.selected:
            self.eventbox.override_background_color(Gtk.StateType.NORMAL, self.SELECTED_COLOR)
            self.name_entry.override_background_color(Gtk.StateType.NORMAL, self.SELECTED_COLOR)
        else:
            self.eventbox.override_background_color(Gtk.StateType.NORMAL, self.UNSELECTED_COLOR)
            self.name_entry.override_background_color(Gtk.StateType.NORMAL, self.UNSELECTED_COLOR)

        # continue GTK signal propagation
        return True

    def _deleteLayerCb(self, widget):
        timeline = self.layer.get_timeline()
        timeline.remove_layer(self.layer)

    def _moveLayerCb(self, widget, step):
        index = self._app.gui.timeline_ui.controls.getControlIndex(self)
        if abs(step) == 1:
            index += step
        elif step == -2:
            index = 0
        else:
            index = len(self.layer.get_timeline().get_layers())
            # if audio, set last position
            if type(self) == AudioLayerControl:
                index *= 2

        self._app.gui.timeline_ui.controls.moveControlWidget(self, index)

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
            print "set normal highlight"
            self.sep.override_background_color(Gtk.StateType.NORMAL, self.SELECTED_COLOR)
        else:
            print "set highlight highlight"
            self.sep.override_background_color(Gtk.StateType.NORMAL, self.UNSELECTED_COLOR)


class VideoLayerControl(BaseLayerControl):
    """
    Layer control class for video layers
    """

    __gtype_name__ = 'VideoLayerControl'

    def __init__(self, app, layer):
        BaseLayerControl.__init__(self, app, layer, GES.TrackType.VIDEO)

        opacity = Gtk.Label(label=_("Opacity:"))

        # Opacity scale
        opacity_adjust = Gtk.Adjustment(value=100, upper=100, step_incr=5, page_incr=10)
        opacity_scale = Gtk.HScale(adjustment=opacity_adjust)
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

    def __init__(self, app, layer):
        BaseLayerControl.__init__(self, app, layer, GES.TrackType.AUDIO)

        volume = Gtk.Label(label=_("Vol:"))
        volume_button = Gtk.VolumeButton(size=Gtk.IconSize.MENU)

        panning = Gtk.Label(label=_("Pan:"))
        # Volume scale
        panning_adjust = Gtk.Adjustment(value=0, lower=-100, upper=100, step_incr=5, page_incr=10)
        panning_scale = Gtk.HScale(adjustment=panning_adjust)
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
       "changed-state": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (GObject.TYPE_PYOBJECT,),)
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

    def  _clickedCb(self, widget):
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

        self.box = Gtk.VBox()
        self.box.add(Gtk.HSeparator())
        self.box.set_border_width(6)

        self.add(self.box)
