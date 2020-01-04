# -*- coding: utf-8 -*-
# Pitivi video editor
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
import re
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import Gtk

from pitivi.timeline import elements
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import LAYER_HEIGHT
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SEPARATOR_HEIGHT
from pitivi.utils.user_utils import Alert


class SpacedSeparator(Gtk.EventBox):
    """A Separator with vertical spacing.

    Inherits from EventBox since we want to change background color.
    """

    def __init__(self):
        Gtk.EventBox.__init__(self)

        self.get_style_context().add_class("SpacedSeparator")
        self.props.height_request = SEPARATOR_HEIGHT


class LayerControls(Gtk.EventBox, Loggable):
    """Container with widgets for controlling a layer."""

    __gtype_name__ = 'PitiviLayerControls'

    def __init__(self, ges_layer, app):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.ges_layer = ges_layer
        self.ges_timeline = self.ges_layer.get_timeline()
        self.app = app
        self.__icon = None

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(hbox)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox.pack_start(vbox, True, True, 0)

        rightside_separator = Gtk.Separator.new(Gtk.Orientation.VERTICAL)
        hbox.pack_start(rightside_separator, False, False, 0)

        name_row = Gtk.Box()
        name_row.set_orientation(Gtk.Orientation.HORIZONTAL)
        name_row.props.spacing = PADDING
        name_row.props.margin_top = PADDING
        name_row.props.margin_left = PADDING
        name_row.props.margin_right = PADDING
        vbox.pack_start(name_row, False, False, 0)

        self.name_entry = Gtk.Entry()
        self.name_entry.get_style_context().add_class("LayerControlEntry")
        self.name_entry.props.valign = Gtk.Align.CENTER
        self.name_entry.connect("focus-out-event", self.__name_focus_out_cb)
        self.ges_layer.connect("notify-meta", self.__layer_rename_cb)
        self.__update_name()
        name_row.pack_start(self.name_entry, True, True, 0)

        #entry_provider = Gtk.CssProvider()
        #entry_css = ("entry:not(:focus) { border: 1px solid transparent;"
#                     "background: transparent; }").encode("UTF-8")
        #entry_provider.load_from_data(entry_css)
        #Gtk.StyleContext.add_provider(self.name_entry.get_style_context(),
#                                      entry_provider,
#                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Mute audio button 2019 06  jep_f
        self.mute_audio_button = Gtk.ToggleButton()
        mute_image = Gtk.Image.new_from_icon_name(
            "audio-volume-high-symbolic", Gtk.IconSize.BUTTON)
        self.mute_audio_button.set_image(mute_image)
        self.mute_audio_button.props.valign = Gtk.Align.CENTER
        self.mute_audio_button.props.relief = Gtk.ReliefStyle.NORMAL
        self.mute_audio_button.set_tooltip_text("Mute audio")
        self.mute_audio_button.connect("clicked", self.__mute_audio_cb)
        name_row.pack_start(self.mute_audio_button, False, False, 0)
        # End of Mute audio button 2019 06 jep_f

        # Mute video button 2019 06 jep_f
        # TODO
#        self.mute_video_button = Gtk.ToggleButton()
#        mute_image = Gtk.Image.new_from_icon_name(
#            "camera-photo-symbolic", Gtk.IconSize.BUTTON)
#        self.mute_video_button.set_image(mute_image)
#        self.mute_video_button.props.valign = Gtk.Align.CENTER
#        self.mute_video_button.props.relief = Gtk.ReliefStyle.NORMAL
#        self.mute_video_button.set_tooltip_text("Mute video")
#        self.mute_video_button.connect("clicked", self.__mute_video_cb)
#        name_row.pack_start(self.mute_video_button, False, False, 0)
        # End of  Mute video button 2019 06  jep_f

        self.menubutton = Gtk.MenuButton.new()
        self.menubutton.props.valign = Gtk.Align.CENTER
        self.menubutton.props.relief = Gtk.ReliefStyle.NONE
        model, action_group = self.__create_menu_model()
        popover = Gtk.Popover.new_from_model(self.menubutton, model)
        popover.insert_action_group("layer", action_group)
        popover.props.position = Gtk.PositionType.LEFT
        self.menubutton.set_popover(popover)
        name_row.pack_start(self.menubutton, False, False, 0)

        space = Gtk.Label()
        space.props.vexpand = True
        vbox.pack_start(space, False, False, 0)

        self.ges_layer.connect("notify::priority", self.__layer_priority_changed_cb)
        self.ges_timeline.connect("layer-added", self.__timeline_layer_added_cb)
        self.ges_timeline.connect("layer-removed", self.__timeline_layer_removed_cb)
        self.__update_actions()

        # When the window property is set, specify the mouse cursor.
        self.connect("notify::window", self.__window_set_cb)

    def __window_set_cb(self, unused_window, unused_pspec):
        self.props.window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND1))

    def __del__(self):
        self.name_entry.disconnect_by_func(self.__name_focus_out_cb)
        self.ges_layer.disconnect_by_func(self.__layer_rename_cb)
        self.ges_layer.disconnect_by_func(self.__layer_priority_changed_cb)
        self.ges_timeline.disconnect_by_func(self.__timeline_layer_added_cb)
        self.ges_timeline.disconnect_by_func(self.__timeline_layer_removed_cb)
        super().__del__()

    def __layer_rename_cb(self, unused_ges_layer, item, value):
        if not item == "video::name":
            return
        self.__update_name()

    def __name_focus_out_cb(self, unused_widget, unused_event):
        current_name = self.ges_layer.ui.get_name()
        name = self.name_entry.get_text()
        if name == current_name:
            return

        with self.app.action_log.started("change layer name",
                                         toplevel=True):
            self.ges_layer.ui.set_name(name)

    def __layer_priority_changed_cb(self, unused_ges_layer, unused_pspec):
        self.__update_actions()
        self.__update_name()

    def __timeline_layer_added_cb(self, unused_timeline, unused_ges_layer):
        self.__update_actions()

    def __timeline_layer_removed_cb(self, unused_timeline, unused_ges_layer):
        self.__update_actions()

    def __update_actions(self):
        priority = self.ges_layer.get_priority()
        first = priority == 0
        self.__move_layer_up_action.props.enabled = not first
        self.__move_layer_top_action.props.enabled = not first
        layers_count = len(self.ges_timeline.get_layers())
        last = priority == layers_count - 1
        self.__move_layer_down_action.props.enabled = not last
        self.__move_layer_bottom_action.props.enabled = not last
        self.delete_layer_action.props.enabled = layers_count > 1

    def __update_name(self):
        self.name_entry.set_text(self.ges_layer.ui.get_name())

    def __create_menu_model(self):
        action_group = Gio.SimpleActionGroup()
        menu_model = Gio.Menu()

        self.__move_layer_top_action = Gio.SimpleAction.new("move-layer-to-top", None)
        action = self.__move_layer_top_action
        action.connect("activate", self.__move_layer_cb, -2)
        action_group.add_action(action)
        menu_model.append(_("Move layer to top"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_up_action = Gio.SimpleAction.new("move-layer-up", None)
        action = self.__move_layer_up_action
        action.connect("activate", self.__move_layer_cb, -1)
        action_group.add_action(action)
        menu_model.append(_("Move layer up"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_down_action = Gio.SimpleAction.new("move-layer-down", None)
        action = self.__move_layer_down_action
        action.connect("activate", self.__move_layer_cb, 1)
        action_group.add_action(action)
        menu_model.append(_("Move layer down"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_bottom_action = Gio.SimpleAction.new("move-layer-to-bottom", None)
        action = self.__move_layer_bottom_action
        action.connect("activate", self.__move_layer_cb, 2)
        action_group.add_action(action)
        menu_model.append(_("Move layer to bottom"), "layer.%s" % action.get_name().replace(" ", "."))

        self.delete_layer_action = Gio.SimpleAction.new("delete-layer", None)
        action = self.delete_layer_action
        action.connect("activate", self.__delete_layer_cb)
        action_group.add_action(action)
        menu_model.append(_("Delete layer"), "layer.%s" % action.get_name())

        return menu_model, action_group

    def __delete_layer_cb(self, unused_action, unused_parameter):
        pipeline = self.ges_timeline.get_asset().pipeline
        with self.app.action_log.started("delete layer",
                                         finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                         toplevel=True):
            self.ges_timeline.remove_layer(self.ges_layer)
            removed_priority = self.ges_layer.props.priority
            for ges_layer in self.ges_timeline.get_layers():
                if ges_layer.props.priority > removed_priority:
                    ges_layer.props.priority -= 1

    def __move_layer_cb(self, unused_simple_action, unused_parameter, step):
        index = self.ges_layer.get_priority()
        if abs(step) == 1:
            index += step
        elif step == -2:
            index = 0
        else:
            index = len(self.ges_timeline.get_layers()) - 1
        self.ges_timeline.ui.move_layer(self.ges_layer, index)
        self.app.project_manager.current_project.pipeline.commit_timeline()

    # Mute buttons 2019 06 jep_f
    # Audio
    def __mute_audio_cb(self, widget):
        if widget.get_active():
            print("mute audio")
            mute_image = Gtk.Image.new_from_icon_name(
                "audio-volume-muted-symbolic", Gtk.IconSize.BUTTON)
            self.mute_audio_button.set_image(mute_image)
            self.__mute_audio_action_cb(True)
        else:
            print("unmute audio")
            mute_image = Gtk.Image.new_from_icon_name(
                "audio-volume-high-symbolic", Gtk.IconSize.BUTTON)
            self.mute_audio_button.set_image(mute_image)
            self.__mute_audio_action_cb(False)

    def __mute_audio_action_cb(self, mute_b):
        alert = True
        ges_clips = self.ges_layer.get_clips()
        for ges_clip in ges_clips:
            for child in ges_clip.get_children(False):
                track = child.get_track()
                print("track = ", track)
                if not track:
                    continue
                media_type = track.props.track_type
                if media_type == GES.TrackType.AUDIO:
                    alert = False
#                        print("bef mute audio = ", child.get_child_property("mute"))
                    # On transition, there is not child.get_child_property("mute")
                    try:
                        ges_clip.get_child_property("mute")
                    # pylint: disable=bare-except
                    except:
                        break
                    else:
                        ges_clip.set_child_property("mute", mute_b)
                        print("mute audio = ", child.get_child_property("mute"))
                    # Cannot find more types than these.
                    break
#                    alert = False
#                    print("bef mute audio = ", child.get_child_property("mute"))
#                    ges_clip.set_child_property("mute", mute_b)
#                    print("mute audio = ", child.get_child_property("mute"))
#                    # Cannot find more types than these.
#                    break
        if alert is True and mute_b is True:  # No alert when we unmute
            Alert("Warning", "No audio in this layer", "service-logout.oga")
        self.app.gui.editor.focus_timeline()

    # End of Audio

    # Video
    # TODO
    def __mute_video_cb(self, widget):
        if widget.get_active():
            print("mute video")
            self.__mute_video_action_cb(True)
        else:
            print("unmute video")
            self.__mute_video_action_cb(False)

    def __mute_video_action_cb(self, mute_v):
        alert = True
        ges_clips = self.ges_layer.get_clips()  # GES.Layer : Get the clips this layer contains.
        for ges_clip in ges_clips:
            ges_track_elements = ges_clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
            print("gtes = ", ges_track_elements)
            for ges_track_element in ges_track_elements:
                print("gte track = ", ges_track_element, ges_track_element.get_track())
                print("gte track active= ", ges_track_element.is_active())
                if ges_track_element.get_track_type() == GES.TrackType.VIDEO:
                    alert = False
                    if mute_v is True:
                        print("Black = ", ges_track_element, ges_track_element.get_track())
                        gt = ges_track_element.set_active(False)  # GES.TrackElement
                        print("Active", ges_track_element.props.active)  # GES.TrackElement
                        print("gtt = ", gt, ges_track_element.is_active())
                        mute_image = Gtk.Image.new_from_icon_name("weather-clear-night", Gtk.IconSize.BUTTON)
                        self.mute_video_button.set_image(mute_image)
                    if mute_v is False:
                        print("Normal = ", ges_track_element)
                        gt = ges_track_element.set_active(True)  # GES.TrackElement
                        print("gtf = ", gt)
                        mute_image = Gtk.Image.new_from_icon_name("camera-photo-symbolic", Gtk.IconSize.BUTTON)
                        self.mute_video_button.set_image(mute_image)
        if alert is True and mute_v is True:  # No alert when we unmute
            Alert("Warning", "No video in this layer", "service-logout.oga")
            mute_image = Gtk.Image.new_from_icon_name("camera-photo-symbolic", Gtk.IconSize.BUTTON)
            self.mute_video_button.set_image(mute_image)

        self.app.gui.editor.focus_timeline()

    # End of Video
    # End of Mute buttons 2019 06  jep_f

    def update(self, media_types):
        self.props.height_request = self.ges_layer.ui.props.height_request

        if media_types & GES.TrackType.VIDEO or not media_types:
            # The layer has video or is empty.
            icon = "video-x-generic-symbolic"
#        # Hide the audio mute button
#        elif not (media_types & GES.TrackType.AUDIO) and media_types & GES.TrackType.VIDEO:
#            icon = "video-x-generic-symbolic"
#            self.mute_audio_button.hide()
#            # End of Hide the audio mute button
        else:
            # The layer has audio and nothing else.
            icon = "audio-x-generic-symbolic"
            # Hide the video mute button
#            self.mute_video_button.hide()
            # End of Hide the video mute button

        if icon != self.__icon:
            image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            self.menubutton.props.image = image
            self.__icon = icon


class Layer(Gtk.Layout, Zoomable, Loggable):
    """Container for the clips widgets of a layer."""

    __gtype_name__ = "PitiviLayer"

    def __init__(self, ges_layer, timeline):
        Gtk.Layout.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.ges_layer = ges_layer
        self.ges_layer.ui = self
        self.timeline = timeline
        self.app = timeline.app

        self._children = []
        self._changed = False

        self.ges_layer.connect("clip-added", self._clip_added_cb)
        self.ges_layer.connect("clip-removed", self._clip_removed_cb)

        # The layer is always the width of the Timeline which contains it.
        self.props.hexpand = True
        self.props.valign = Gtk.Align.START

        self.media_types = GES.TrackType(0)
        for ges_clip in ges_layer.get_clips():
            self._add_clip(ges_clip)
        self.check_media_types()

    def set_name(self, name):
        self.ges_layer.set_meta("video::name", name)

    def _name_if_set(self):
        name = self.ges_layer.get_meta("video::name")
        if not name:
            name = self.ges_layer.get_meta("audio::name")
        return name

    def __name_if_meaningful(self):
        name = self._name_if_set()
        if name:
            for pattern in ("video [0-9]+$", "audio [0-9]+$", "Layer [0-9]+$"):
                if re.match(pattern, name):
                    return None
        return name

    def get_name(self):
        name = self.__name_if_meaningful()
        if not name:
            name = _('Layer %d') % self.ges_layer.get_priority()
        return name

    def release(self):
        for ges_clip in self.ges_layer.get_clips():
            self._remove_clip(ges_clip)
        self.ges_layer.disconnect_by_func(self._clip_added_cb)
        self.ges_layer.disconnect_by_func(self._clip_removed_cb)

    def check_media_types(self):
        if self.timeline.editing_context:
            self.info("Not updating media types as"
                      " we are editing the timeline")
            return
        old_media_types = self.media_types
        self.media_types = GES.TrackType(0)
        ges_clips = self.ges_layer.get_clips()
        for ges_clip in ges_clips:
            for child in ges_clip.get_children(False):
                track = child.get_track()
                if not track:
                    continue
                self.media_types |= track.props.track_type
                if self.media_types == GES.TrackType.AUDIO | GES.TrackType.VIDEO:
                    # Cannot find more types than these.
                    break

        if (self.media_types & GES.TrackType.AUDIO) and (self.media_types & GES.TrackType.VIDEO):
            self.props.height_request = LAYER_HEIGHT
        else:
            # If the layer is empty, set layer's height to default height.
            self.props.height_request = LAYER_HEIGHT / 2

        if hasattr(self.ges_layer, "control_ui") and self.ges_layer.control_ui:
            self.ges_layer.control_ui.update(self.media_types)

        if old_media_types != self.media_types:
            self.update_position()

    def _clip_child_added_cb(self, ges_clip, child):
        self.check_media_types()

    def _clip_child_removed_cb(self, ges_clip, child):
        self.check_media_types()

    def _clip_added_cb(self, unused_ges_layer, ges_clip):
        self._add_clip(ges_clip)
        self.check_media_types()

    def _add_clip(self, ges_clip):
        ui_type = elements.GES_TYPE_UI_TYPE.get(ges_clip.__gtype__, None)
        if ui_type is None:
            self.error("Implement UI for type %s?", ges_clip.__gtype__)
            return

        widget = ui_type(self, ges_clip)
        self._children.append(widget)
        self._children.sort(key=lambda clip: clip.z_order)
        self.put(widget, self.ns_to_pixel(ges_clip.props.start), 0)
        widget.update_position()
        self._changed = True
        widget.show_all()

        ges_clip.connect_after("child-added", self._clip_child_added_cb)
        ges_clip.connect_after("child-removed", self._clip_child_removed_cb)

    def _clip_removed_cb(self, unused_ges_layer, ges_clip):
        self._remove_clip(ges_clip)
        self.check_media_types()

    def _remove_clip(self, ges_clip):
        if not ges_clip.ui:
            return

        ui_type = elements.GES_TYPE_UI_TYPE.get(ges_clip.__gtype__, None)
        if ui_type is None:
            self.error("Implement UI for type %s?", ges_clip.__gtype__)
            return

        self.remove(ges_clip.ui)
        self._children.remove(ges_clip.ui)
        self._changed = True
        ges_clip.ui.release()
        ges_clip.ui = None

        ges_clip.disconnect_by_func(self._clip_child_added_cb)
        ges_clip.disconnect_by_func(self._clip_child_removed_cb)

    def update_position(self):
        for ges_clip in self.ges_layer.get_clips():
            if hasattr(ges_clip, "ui"):
                ges_clip.ui.update_position()

    def do_draw(self, cr):
        if self._changed:
            self._children.sort(key=lambda clip: clip.z_order)
            for child in self._children:
                if isinstance(child, elements.TransitionClip):
                    window = child.get_window()
                    window.raise_()
            self._changed = False

        for child in self._children:
            self.propagate_draw(child, cr)
