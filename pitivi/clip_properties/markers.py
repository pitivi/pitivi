# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2021, Piotr Brzeziński <thewildtreee@gmail.com>
# Copyright (C) 2022, Alex Băluț <alexandru.balut@gmail.com>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Widgets to control clips properties."""
import os
from gettext import gettext as _
from typing import Optional

from gi.repository import GES
from gi.repository import Gtk

from pitivi.check import MISSING_SOFT_DEPS
from pitivi.configure import get_ui_dir
from pitivi.utils.beat_detection import BeatDetector
from pitivi.utils.loggable import Loggable
from pitivi.utils.markers import GES_MARKERS_SNAPPABLE
from pitivi.utils.misc import disconnect_all_by_func
from pitivi.utils.ui import disable_scroll
from pitivi.utils.ui import SPACING


class ClipMarkersProperties(Gtk.Expander, Loggable):
    """Widget for managing the marker lists of a clip.

    Attributes:
        app (Pitivi): The app.
        clip (GES.Clip): The clip being configured.
    """

    TRACK_TYPES = {
        GES.TrackType.VIDEO: _("Video"),
        GES.TrackType.AUDIO: _("Audio"),
        GES.TrackType.TEXT: _("Text"),
        GES.TrackType.CUSTOM: _("Custom"),
    }

    def __init__(self, app):
        Gtk.Expander.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self.clip: Optional[GES.Clip] = None
        self.beat_detector: Optional[BeatDetector] = None

        self._detect_button: Optional[Gtk.Button] = None
        self._clear_button: Optional[Gtk.Button] = None
        self._progress_bar: Optional[Gtk.ProgressBar] = None

        self.set_expanded(True)
        self.set_label(_("Clip markers"))

        self.expander_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.expander_box)

    def set_clip(self, clip):
        if self.clip:
            for child in self.clip.get_children(False):
                if not isinstance(child, GES.Source):
                    continue

                disconnect_all_by_func(child.markers_manager, self._lists_modified_cb)
                disconnect_all_by_func(child.markers_manager, self._current_list_changed_cb)

        for child in self.expander_box.get_children():
            self.expander_box.remove(child)

        self.clip = clip
        if not self.clip or not isinstance(self.clip, GES.SourceClip):
            self.hide()
            return

        self.show()

        audio_source: Optional[GES.AudioSource] = None
        labels_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        combos_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        for child in self.clip.get_children(False):
            # Ignore non-source children, e.g. effects
            if not isinstance(child, GES.Source):
                continue

            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=SPACING)
            row_box.set_border_width(SPACING)
            row_box.show()
            row_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)

            child_type = child.get_track_type()
            name = ClipMarkersProperties.TRACK_TYPES[child_type]
            label = Gtk.Label(label=name)
            row_box.pack_start(label, False, False, 0)
            label.show()
            labels_size_group.add_widget(label)
            row_size_group.add_widget(label)
            label.props.valign = Gtk.Align.START

            controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=SPACING)
            controls_box.show()

            selection_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=SPACING)
            list_store = Gtk.ListStore(str, str)
            list_combo = Gtk.ComboBox.new_with_model(list_store)
            renderer_text = Gtk.CellRendererText()
            list_combo.pack_start(renderer_text, True)
            list_combo.add_attribute(renderer_text, "text", 1)
            list_combo.set_id_column(0)
            selection_box.pack_start(list_combo, False, False, 0)
            list_combo.show()
            combos_size_group.add_widget(list_combo)
            row_size_group.add_widget(list_combo)

            snap_toggle = Gtk.CheckButton.new_with_label(_("Magnetic"))
            selection_box.pack_start(snap_toggle, False, False, 0)
            if GES_MARKERS_SNAPPABLE:
                snap_toggle.show()

            controls_box.pack_start(selection_box, False, False, 0)

            if isinstance(child, GES.AudioSource) and "librosa" not in MISSING_SOFT_DEPS:
                container = self._create_beat_detection_ui()
                controls_box.pack_start(container, False, False, 0)
                audio_source = child

            row_box.pack_start(controls_box, True, True, 0)

            manager = child.markers_manager
            list_combo.connect("changed", self._combo_changed_cb, child, snap_toggle)
            snap_toggle.connect("toggled", self._snappable_toggled_cb, manager)

            self._populate_list_combo(manager, list_combo)
            manager.connect("lists-modified", self._lists_modified_cb, list_combo)
            manager.connect("current-list-changed", self._current_list_changed_cb, list_combo)

            selection_box.show()

            # Display audio marker settings below the video ones,
            # matching how they're shown on the timeline.
            if child_type == GES.TrackType.AUDIO:
                self.expander_box.pack_end(row_box, False, False, 0)
            else:
                self.expander_box.pack_start(row_box, False, False, 0)

        self._set_audio_source(audio_source)

        self.expander_box.show()
        disable_scroll(self.expander_box)

    def _current_list_changed_cb(self, manager, list_key, list_combo):
        list_combo.set_active_id(list_key)

    def _lists_modified_cb(self, manager, list_combo):
        self._populate_list_combo(manager, list_combo)

    def _populate_list_combo(self, manager, list_combo):
        lists = manager.get_all_keys_with_names()
        list_store = list_combo.get_model()

        list_store.clear()
        for key, name in lists:
            list_store.append([key, name])

        list_key = manager.current_list_key
        list_combo.set_active_id(list_key)

    def _combo_changed_cb(self, combo, ges_source, snap_toggle):
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            return

        model = combo.get_model()
        list_key = model[tree_iter][0]

        manager = ges_source.markers_manager
        manager.current_list_key = list_key

        snap_toggle.set_active(manager.snappable)
        snap_toggle_interactable = bool(list_key != "")
        snap_toggle.set_sensitive(snap_toggle_interactable)

    def _snappable_toggled_cb(self, button, manager):
        active = button.get_active()
        manager.snappable = active

    def _create_beat_detection_ui(self) -> Gtk.Box:
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "beatdetection.ui"))
        builder.connect_signals(self)

        self._detect_button = builder.get_object("detect-button")
        self._clear_button = builder.get_object("clear-button")
        self._progress_bar = builder.get_object("detection-progress")

        return builder.get_object("container-box")

    def _set_audio_source(self, source: GES.AudioSource):
        if self.beat_detector:
            self.beat_detector.disconnect_by_func(self._detection_percentage_cb)
            self.beat_detector.disconnect_by_func(self._detection_failed_cb)
            self.beat_detector = None

        if source:
            self.beat_detector = BeatDetector(source)
            self.beat_detector.connect("detection-percentage", self._detection_percentage_cb)
            self.beat_detector.connect("detection-failed", self._detection_failed_cb)

            self._update_beat_detection_ui(self.beat_detector.progress)

        self.set_visible(bool(source))

    def _detection_percentage_cb(self, detector, percentage):
        self._update_beat_detection_ui(percentage)

    def _detection_failed_cb(self, detector, error):
        # TODO: Show an error in the UI.
        self.error("BeatDetector failed: %s", error)
        self._update_beat_detection_ui()

    def _update_beat_detection_ui(self, percentage=0):
        in_progress = self.beat_detector.in_progress
        has_beats = self.beat_detector.beat_list_exists
        self._detect_button.set_sensitive(not in_progress and not has_beats)
        self._clear_button.set_sensitive(not in_progress and has_beats)

        self._progress_bar.set_visible(in_progress)
        self._progress_bar.set_fraction(percentage / 100)

    def _detect_clicked_cb(self, button):
        self.beat_detector.detect_beats()
        self._update_beat_detection_ui()

    def _clear_clicked_cb(self, button):
        self.beat_detector.clear_beats()
        self._update_beat_detection_ui()
