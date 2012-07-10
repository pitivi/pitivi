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

import gtk
import ges
import gobject

from gettext import gettext as _

from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import LAYER_SPACING, LAYER_CONTROL_TUPLE, \
    TYPE_PITIVI_LAYER_CONTROL


# TODO add tooltips
# TODO GTK3 port to GtkGrid
class BaseLayerControl(gtk.VBox, Loggable):
    """
    Base Layer control classes
    """

    __gtype_name__ = 'LayerControl'

    def __init__(self, app, layer, layer_type):
        gtk.VBox.__init__(self, spacing=0)
        Loggable.__init__(self)

        self._app = app
        self._layer = layer
        self._selected = False

        # get the default colour for the current theme
        self.UNSELECTED_COLOR = self.rc_get_style().bg[gtk.STATE_NORMAL]
        # use base instead of bg colours so that we get the lighter colour
        # that is used for list items in TreeView.
        self.SELECTED_COLOR = self.rc_get_style().base[gtk.STATE_SELECTED]

        table = gtk.Table(rows=2, columns=2)
        table.props.border_width = 2
        table.set_row_spacings(3)
        table.set_col_spacings(3)

        self.eventbox = gtk.EventBox()
        self.eventbox.add(table)
        self.eventbox.connect("button_press_event", self._buttonPressCb)
        self.pack_start(self.eventbox)

        self.sep = SpacedSeparator()
        self.pack_start(self.sep)

        icon_mapping = {ges.TRACK_TYPE_AUDIO: "audio-x-generic",
                        ges.TRACK_TYPE_VIDEO: "video-x-generic"}

        # Folding button
        # TODO use images
        fold_button = TwoStateButton("▼", "▶")
        fold_button.set_relief(gtk.RELIEF_NONE)
        fold_button.set_focus_on_click(False)
        fold_button.connect("changed-state", self._foldingChangedCb)
        table.attach(fold_button, 0, 1, 0, 1)

        # Name entry
        self.name_entry = gtk.Entry()
        self.name_entry.set_tooltip_text(_("Set or change this layers name"))
        self.name_entry.set_property("primary-icon-name", icon_mapping[layer_type])
        self.name_entry.connect("focus-in-event", self._focusChangeCb, False)
        self.name_entry.connect("focus-out-event", self._focusChangeCb, True)
        self.name_entry.connect("button_press_event", self._buttonPressCb)
        self.name_entry.props.sensitive = False

        # 'Solo' toggle button
        self.solo_button = gtk.ToggleButton()
        self.solo_button.set_tooltip_text(_("Only show this layer\n\nOther layers won't" +
                                            "be visible as long a this is enabled"))
        solo_image = gtk.Image()
        solo_image.set_from_icon_name("avatar-default-symbolic", gtk.ICON_SIZE_MENU)
        self.solo_button.add(solo_image)
        self.solo_button.connect("toggled", self._soloToggledCb)
        self.solo_button.set_relief(gtk.RELIEF_NONE)
        self.solo_button.props.sensitive = False

        # CheckButton
        visible_option = gtk.CheckButton()
        visible_option.connect("toggled", self._visibilityChangedCb)
        visible_option.set_active(True)
        visible_option.props.sensitive = False

        # Upper bar
        upper = gtk.HBox()
        upper.pack_start(self.name_entry, True, True)
        upper.pack_start(self.solo_button, False, False)
        upper.pack_start(visible_option, False, False)

        # Lower bar
        self.lower_hbox = gtk.HBox()
        self.lower_hbox.props.sensitive = False

        table.attach(upper, 1, 2, 0, 1)
        table.attach(self.lower_hbox, 1, 2, 1, 2)

        self.show_all()

        # Popup Menu
        self.popup = gtk.Menu()
        menu_dellayer = gtk.ImageMenuItem(_("_Delete layer"))
        menu_dellayer.connect("activate", self._deleteLayerCb)
        self.popup.append(menu_dellayer)
        self.popup.show_all()

        # Drag and drop
        self.connect("drag_data_get", self._dragDataGetCb)
        self.drag_source_set(gtk.gdk.BUTTON1_MASK,
                             [LAYER_CONTROL_TUPLE],
                             gtk.gdk.ACTION_MOVE)

    def _dragDataGetCb(self, widget, context, selection, targetType, eventTime):
        if targetType == TYPE_PITIVI_LAYER_CONTROL:
            selection.set(selection.target, 8,
                          str(self._app.gui.timeline_ui.controls.getControlIdString(self)))

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
            self._app.gui.timeline_ui.controls.soloLayer(self._layer)
        else:
            # Enable all layers
            self._app.gui.timeline_ui.controls.soloLayer(None)

    def _buttonPressCb(self, widget, event):
        """
        Look if user selected layer or wants popup menu
        """
        if event.button == 1:
            self._app.gui.timeline_ui.controls.selectLayerControl(self)
        elif event.button == 3:
            self.popup.popup(None, None, None, event.button, event.time)

    def _selectionChangedCb(self):
        """
        Called when the selection state changes
        """
        if self.selected:
            self.eventbox.modify_bg(gtk.STATE_NORMAL, self.SELECTED_COLOR)
            self.name_entry.modify_bg(gtk.STATE_NORMAL, self.SELECTED_COLOR)
        else:
            self.eventbox.modify_bg(gtk.STATE_NORMAL, self.UNSELECTED_COLOR)
            self.name_entry.modify_bg(gtk.STATE_NORMAL, self.UNSELECTED_COLOR)

        # continue GTK signal propagation
        return True

    def _deleteLayerCb(self, widget):
        timeline = self._layer.get_timeline()
        timeline.remove_layer(self._layer)

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


class VideoLayerControl(BaseLayerControl):
    """
    Layer control class for video layers
    """

    __gtype_name__ = 'VideoLayerControl'

    def __init__(self, app, layer):
        BaseLayerControl.__init__(self, app, layer, ges.TRACK_TYPE_VIDEO)

        opacity = gtk.Label(_("Opacity:"))

        # Opacity scale
        opacity_adjust = gtk.Adjustment(value=100, upper=100, step_incr=5, page_incr=10)
        opacity_scale = gtk.HScale(opacity_adjust)
        opacity_scale.set_value_pos(gtk.POS_LEFT)
        opacity_scale.set_digits(0)
        opacity_scale.set_tooltip_text(_("Change video opacity"))

        self.lower_hbox.pack_start(opacity, False, False)
        self.lower_hbox.pack_start(opacity_scale, True, True)
        self.lower_hbox.show_all()


class AudioLayerControl(BaseLayerControl):
    """
    Layer control class for audio layers
    """

    __gtype_name__ = 'AudioLayerControl'

    def __init__(self, app, layer):
        BaseLayerControl.__init__(self, app, layer, ges.TRACK_TYPE_AUDIO)

        volume = gtk.Label(_("Vol:"))
        volume_button = gtk.VolumeButton()
        volume_button.props.size = gtk.ICON_SIZE_MENU

        panning = gtk.Label(_("Pan:"))
        # Volume scale
        panning_adjust = gtk.Adjustment(value=0, lower=-100, upper=100, step_incr=5, page_incr=10)
        panning_scale = gtk.HScale(panning_adjust)
        panning_scale.set_value_pos(gtk.POS_LEFT)
        panning_scale.set_digits(0)
        panning_scale.set_tooltip_text(_("Change audio panning"))

        self.lower_hbox.pack_start(volume, False, False)
        self.lower_hbox.pack_start(volume_button, False, False)
        self.lower_hbox.pack_start(panning, False, False)
        self.lower_hbox.pack_start(panning_scale, True, True)
        self.lower_hbox.show_all()


class TwoStateButton(gtk.Button):
    """
    Button with two states and according labels/images
    """

    __gsignals__ = {
       "changed-state": (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT,),)
       }

    def __init__(self, state1="", state2=""):
        gtk.Button.__init__(self)
        self.set_relief(gtk.RELIEF_NONE)
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


class SpacedSeparator(gtk.VBox):

    def __init__(self):
        gtk.VBox.__init__(self)

        self.add(gtk.HSeparator())
        self.props.border_width = 6
