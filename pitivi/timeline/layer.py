# -- coding: utf-8 --
# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/layercontrols.py
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
from pitivi.utils.ui import LAYER_SPACING


# TODO add tooltips
# TODO GTK3 port to GtkGrid
class BaseLayerControl(gtk.Table, Loggable):
    """
    Base Layer control classes
    """

    __gtype_name__ = 'LayerControl'

    def __init__(self, app, layer, layer_type):
        gtk.Table.__init__(self, rows=2, columns=2)
        Loggable.__init__(self)

        self._app = app
        self._layer = layer

        self.set_row_spacings(3)
        self.set_col_spacings(3)

        icon_mapping = {ges.TRACK_TYPE_AUDIO: "audio-x-generic",
                        ges.TRACK_TYPE_VIDEO: "video-x-generic"}

        # Folding button
        # TODO use images
        fold_button = TwoStateButton("▼", "▶")
        fold_button.set_relief(gtk.RELIEF_NONE)
        fold_button.set_focus_on_click(False)
        fold_button.connect("changed-state", self._foldingChangedCb)
        self.attach(fold_button, 0, 1, 0, 1)

        # Name entry
        name_entry = gtk.Entry()
        name_entry.set_tooltip_text(_("Set or change this layers name"))
        name_entry.set_property("primary-icon-name", icon_mapping[layer_type])
        name_entry.connect("focus-in-event", self._focusChangeCb, False)
        name_entry.connect("focus-out-event", self._focusChangeCb, True)
        name_entry.props.sensitive = False

        # 'Solo' toggle button
        self.solo_button = gtk.ToggleButton()
        self.solo_button.set_tooltip_text(_("Only show this layer\n\nOther layers won't" +
                                            "be visible as long a this is enabled"))
        solo_image = gtk.Image()
        solo_image.set_from_icon_name("avatar-default-symbolic", gtk.ICON_SIZE_MENU)
        self.solo_button.add(solo_image)
        self.solo_button.connect("toggled", self._soloToggledCb)
        self.solo_button.props.sensitive = False

        # CheckButton
        visible_option = gtk.CheckButton()
        visible_option.connect("toggled", self._visibilityChangedCb)
        visible_option.set_active(True)
        visible_option.props.sensitive = False

        # Temporary delete button
        del_button = gtk.Button()
        del_button.set_tooltip_text(_("Delete this layer"))
        del_button.connect("clicked", self._deleteLayerCb)

        del_image = gtk.Image()
        del_image.set_from_icon_name("edit-delete", gtk.ICON_SIZE_MENU)
        del_button.add(del_image)

        # Upper bar
        upper = gtk.HBox()
        upper.pack_start(name_entry, True, True)
        upper.pack_start(self.solo_button, False, False)
        upper.pack_start(visible_option, False, False)
        upper.pack_start(del_button, False, False)

        # Lower bar
        self.lower_hbox = gtk.HBox()
        self.lower_hbox.props.sensitive = False

        self.attach(upper, 1, 2, 0, 1)
        self.attach(self.lower_hbox, 1, 2, 1, 2)

        self.show_all()

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

    def _deleteLayerCb(self, widget):
        timeline = self._layer.get_timeline()
        timeline.remove_layer(self._layer)

    def _soloToggledCb(self, button):
        if button.get_active():
            # Disable all other layers
            self._app.gui.timeline_ui.controls.soloLayer(self._layer)
        else:
            # Enable all layers
            self._app.gui.timeline_ui.controls.soloLayer(None)

    def getHeight(self):
        return self.get_allocation().height

    def setSoloState(self, state):
        self.solo_button.set_active(state)


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
