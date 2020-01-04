# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019 Pitivi project
# Author Jean-Paul Favier
# Tested with Pitivi 0.98-827-gdd262c24
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
# Boston, MA 02110-1301, USA.from gi.repository import GObject
import os

from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

from pitivi.configure import get_pixmap_dir
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.timeline import SELECT
from pitivi.utils.user_utils import Alert


class AdjustClipSVolume(GObject.Object, Peas.Activatable):
    """You can  adjust the volume of all selected clips at the same value.

    Print is used for debugging goal
    """

    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=unused-argument
    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        self.app = self.object.app
        dir_img = os.path.join(get_pixmap_dir(), "one_volume.svg")
        image = Gtk.Image.new_from_file(dir_img)
        self.button = Gtk.ToolButton.new(icon_widget=image)
        print("im", self.button.get_icon_widget())
        self.button.set_tooltip_text("Adjust the volume of the selected clips\nto the same value")
        self.button.show_all()
#        self.button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_INDENT)
#        self.button.set_tooltip_text("Adjust the volume of the selected clips\nto the same value")
#        self.button.show()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.button)
        self.button.connect("clicked", self._window_volume)

    def _window_volume(self, widget):
        """Select several clips.

        adjust the volume with the scale cursor
        """
        self.timeline = self.app.gui.editor.timeline_ui.timeline
        self.clips = sorted(self.timeline.selection, key=lambda x: x.get_start())
        # We deselect the selection to select later clips one by one
        # else the selection cannot find the keyframe curve of each clip
        self.timeline.selection.set_selection([], SELECT)
        self.no_audio = False
        self.test_audio()
        if self.no_audio is False:
#        if self.no_audio == True:
#            print("SELECT)", self.timeline.selection.setSelection([], SELECT))
#        else:
            if len(self.clips) > 0:  #if self.clips != None:
                print("len = ", len(self.clips))
                self.win = Gtk.Window()
                self.win.set_default_size(200, 100)
                self. win.set_title("Volume setting on selected clips")

                self.box = Gtk.VBox()
                box_h = Gtk.HBox()

                self.scale = Gtk.Scale.new_with_range(0, 0, 300, 10)  # first argument HORIZONTAL
                # scale = Gtk.HScale()    scale.set_range(0, 200)    scale.set_increments(1, 10)
                self.scale.set_digits(0)
                self.scale.set_size_request(300, 100)
                self.scale.connect("value-changed", self.volume_value)

                button = Gtk.Button("OK")
                button.connect("clicked", self.on_clicked_ok)
                button.set_size_request(20, 10)
                button_cancel = Gtk.Button("Cancel")
                button_cancel.connect("clicked", self.on_cancel)
                button_cancel.set_size_request(20, 10)
                self.mute_audio_button = Gtk.ToggleButton()
                unmute_image = Gtk.Image.new_from_icon_name(
                    "audio-volume-high-symbolic", Gtk.IconSize.BUTTON)
                self.mute_audio_button.set_image(unmute_image)
                self.mute_audio_button.connect("clicked", self._mute)

                self.win.add(self.box)
                box_h.add(self.mute_audio_button)
                box_h.add(self.scale)
                self.box.add(box_h)
                self.box.add(button)
                self.box.add(button_cancel)
                self.win.show_all()
            else:
                print("No selection")
                title = "No selection"
                message = "You have to select at least one clip."
                Alert(title, message, "service-logout.oga")

    def volume_value(self, widget):
        self.vol_setting = widget.get_value()
        print("vol_setting", self.vol_setting, widget.get_value())

    def _mute(self, widget):
        if widget.get_active():
            print("mute audio")
            mute_image = Gtk.Image.new_from_icon_name(
                "audio-volume-muted-symbolic", Gtk.IconSize.BUTTON)
            self.mute_audio_button.set_image(mute_image)
            self.vol_setting = 0.0
            self.scale.set_value(0.0)
            print("vol_setting mute", self.vol_setting)
        else:
            print("unmute audio")
            unmute_image = Gtk.Image.new_from_icon_name(
                "audio-volume-high-symbolic", Gtk.IconSize.BUTTON)
            self.mute_audio_button.set_image(unmute_image)
            self.vol_setting = self.scale.get_value()
            print("vol_setting unmute", self.vol_setting)

    def on_clicked_ok(self, widget):
        print("clicked")
        self.vol_setting *= 0.001
        print("vol_setting", self.vol_setting)
        self.___volume_cb()
        self.win.destroy()

    def on_cancel(self, widget):
        print("cancel")
        self.win.destroy()

    def ___volume_cb(self):
        # Undoing action :
        # http://developer.pitivi.org/Advanced_plugin.html#making-it-shine
        print("Select = ", self.timeline.selection)
        with self.app.action_log.started("Volume keyframe",\
            finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline), \
             toplevel=True):
            print("Clips = ", self.clips)
            for clip in self.clips:
                self.timeline.selection.set_selection([clip], SELECT)
                print("Clip = ", clip, self.timeline.selection)
                inpoint = clip.get_inpoint()
                end = clip.get_start() + clip.get_duration()
                ges_track_elements = clip.find_track_elements(None, GES.TrackType.AUDIO, GES.Source)
                print("gtels = ", ges_track_elements)
                # No audio in at least one clip
                if ges_track_elements == []:
                    Alert("Error", "A clip has no audio", "service-logout.oga")
                    break
                for ges_track_element in ges_track_elements:
                    print("gtel = ", ges_track_element)
                    # Move the keyframes inpoint and end to the value
                    keyframe_curve = ges_track_element.ui.keyframe_curve
                    print("keyframe_curve = ", keyframe_curve)
                    #pylint: disable=protected-access
                    offsets = keyframe_curve._keyframes.get_offsets()
                    print("kf", keyframe_curve.props)
                    print("offsets 4 = ", offsets)
                    # Setting the value of the volume inside 0 to 2
                    offset = offsets[0][0]
                    offsets[0][1] = self.vol_setting
                    print("svs = ", self.vol_setting)
                    #pylint: disable=protected-access
                    keyframe_curve._move_keyframe(int(offset), inpoint, self.vol_setting)
                    offset = offsets[len(offsets) - 1][0]
                    offsets[len(offsets) - 1][1] = self.vol_setting
                    #pylint: disable=protected-access
                    keyframe_curve._move_keyframe(end, int(offset), self.vol_setting)
                    print("offsets 0 end = ", offsets)
                    #  We remove the ghost point and other points
                    for off in offsets:
                        print("off[0] = ", off[0])
                        if off[0] > 0 and off[0] < offsets[len(offsets) - 1][0]:
                            keyframe_curve.toggle_keyframe(off[0])
                            print("toggle_keyframe", off[0])
                    keyframe_curve = ges_track_element.ui.keyframe_curve
                    #pylint: disable=protected-access
                    offsets = keyframe_curve._keyframes.get_offsets()
                    print("offsets in the end = ", offsets)
                print("Fin track --------")
            self.timeline.selection.set_selection([], SELECT)
            self.app.gui.editor.focus_timeline()

    def test_audio(self):
        """Alert if the track is not an audio track."""
        print("Clips a = ", self.clips)
        for clip in self.clips:  #self.clips:
            print("Clip a = ", clip)
            ges_track_elements = clip.find_track_elements(None, GES.TrackType.AUDIO, GES.Source)
            print("gtels a= ", ges_track_elements)
            # No audio in at least one clip
            if ges_track_elements == []:
                self.no_audio = True
                Alert("Error", "A clip has no audio", "service-logout.oga")
                break

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
