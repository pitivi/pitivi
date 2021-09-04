# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2010, Brandon Lewis <brandon_lewis@berkeley.edu>
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
import json
import os.path
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.configure import get_audiopresets_dir
from pitivi.configure import get_videopresets_dir
from pitivi.settings import xdg_data_home
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import alter_style_class


class DeserializeException(Exception):
    pass


class PresetManager(GObject.Object, Loggable):
    """Abstract class for storing a list of presets.

    Subclasses must provide a filename attribute.

    Attributes:
        filename (str): The name of the file where the presets will be stored.
        cur_preset (str): The currently selected preset. Note that a preset
            has to be selected before it can be changed.
        ordered (Gtk.ListStore): A list holding (name, preset_dict) tuples.
        presets (dict): A (name -> preset_dict) map.
        widget_map (dict): A (propname -> (setter_func, getter_func)) map.
            These two functions are used when showing or saving a preset.
    """

    __gsignals__ = {
        "preset-loaded": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, default_path=None, user_path=None, system=None):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self.default_path = default_path
        self.user_path = user_path

        self.presets = {}
        self.widget_map = {}
        self.ordered = Gtk.ListStore(str, object)

        def sortme(store, i1, i2, unused_udata):
            name1 = store[i1][0]
            name2 = store[i2][0]
            if name1 > name2:
                return 1

            return -1

        self.ordered.set_sort_func(0, sortme)
        self.ordered.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.cur_preset = None
        # Whether to ignore the update_value calls.
        self.ignore_update_requests = False
        self.system = system

    def setup_ui(self, combo, button):
        # pylint: disable=attribute-defined-outside-init
        self.combo = combo
        self.button = button

        combo.set_model(self.ordered)
        combo.set_id_column(0)
        combo.set_entry_text_column(0)
        combo.connect("changed", self._preset_changed_cb)

        entry = combo.get_child()
        alter_style_class("GtkEntry.unsaved", entry, "font-style:italic;")

        action_group = Gio.SimpleActionGroup()
        menu_model = Gio.Menu()

        action = Gio.SimpleAction.new("new", None)
        action.connect("activate", self._add_preset_cb)
        action_group.add_action(action)
        menu_model.append(_("New"), "preset.%s" % action.get_name())
        self.action_new = action

        action = Gio.SimpleAction.new("remove", None)
        action.connect("activate", self._remove_preset_cb)
        action_group.add_action(action)
        menu_model.append(_("Remove"), "preset.%s" % action.get_name())
        self.action_remove = action

        action = Gio.SimpleAction.new("save", None)
        action.connect("activate", self._save_preset_cb)
        action_group.add_action(action)
        menu_model.append(_("Save"), "preset.%s" % action.get_name())
        self.action_save = action

        menu = Gtk.Menu.new_from_model(menu_model)
        menu.insert_action_group("preset", action_group)
        button.set_popup(menu)

    def _preset_changed_cb(self, combo):
        """Handles the selection of a preset."""
        # Check whether the user selected a preset or editing the preset name.
        self.select_preset(combo)
        self.update_menu_actions()

    def select_preset(self, combo):
        preset_name = combo.get_active_id()
        if preset_name:
            # The user selected a preset.
            self.restore_preset(preset_name)
            self.emit("preset-loaded")

    def _add_preset_cb(self, unused_action, unused_param):
        preset_name = self.get_new_preset_name()
        self.create_preset(preset_name)
        self.combo.set_active_id(preset_name)
        self.update_menu_actions()

    def _remove_preset_cb(self, unused_action, unused_param):
        self.remove_current_preset()
        entry = self.combo.get_child()
        entry.set_text("")
        self.update_menu_actions()

    def _save_preset_cb(self, unused_action, unused_param):
        entry = self.combo.get_child()
        preset_name = entry.get_text()
        self.save_current_preset(preset_name)
        # Useful when a new preset has just been created.
        self.combo.set_active_id(preset_name)
        self.update_menu_actions()

    def update_menu_actions(self):
        entry = self.combo.get_child()
        preset_name = entry.get_text()
        can_save = self.is_save_button_sensitive(preset_name)
        self.action_save.set_enabled(can_save)
        if can_save:
            entry.get_style_context().add_class("unsaved")
        else:
            entry.get_style_context().remove_class("unsaved")

        can_remove = self.is_remove_button_sensitive()
        self.action_remove.set_enabled(can_remove)

        can_create_new = self.is_new_button_sensitive()
        self.action_new.set_enabled(can_create_new)

    def load_all(self):
        self._load_from_dir(self.default_path, extra={"readonly": True})
        if os.path.isfile(self.user_path):
            # We used to save presets as a single file instead of a directory
            os.rename(self.user_path, "%s.old" % self.user_path)
        self._load_from_dir(self.user_path)

    def _load_from_dir(self, presets_dir, extra=None):
        try:
            files = os.listdir(presets_dir)
        except FileNotFoundError:
            self.debug("Presets directory missing: %s", presets_dir)
            return
        for uri in files:
            filepath = os.path.join(presets_dir, uri)
            if filepath.endswith("json"):
                with open(filepath, encoding="UTF-8") as section:
                    parser = json.loads(section.read())
                name = parser["name"]
                if parser.get("removed"):
                    self._forget_preset(name)
                    continue
                try:
                    preset = self._deserialize_preset(parser)
                except DeserializeException as e:
                    self.debug("Failed to load preset %s: %s", filepath, e)
                    continue
                preset["filepath"] = filepath
                if extra:
                    for key, value in extra.items():
                        preset[key] = value
                self._add_preset(name, preset)

    def save_all(self):
        """Writes changes to disk for all presets."""
        for preset_name, unused_values in self.ordered:
            self._save_preset(preset_name)

    def _save_preset(self, preset_name):
        if not os.path.exists(self.user_path):
            os.makedirs(self.user_path)
        try:
            file_path = self.presets[preset_name]["filepath"]
        except KeyError:
            file_path = self._build_file_path(preset_name)
            self.presets[preset_name]["filepath"] = file_path
        with open(file_path, "w", encoding="UTF-8") as fout:
            values = self.presets[preset_name]
            raw = self._serialize_preset(values)
            raw["name"] = preset_name
            serialized = json.dumps(raw, indent=4)
            fout.write(serialized)

    def _build_file_path(self, preset_name):
        file_name = self.system.get_unique_filename(preset_name + ".json")
        return os.path.join(self.user_path, file_name)

    def get_new_preset_name(self):
        """Gets a unique name for a new preset."""
        name = _("New preset")
        i = 1
        while self.has_preset(name):
            name = _("New preset %d") % i
            i += 1
        return name

    def create_preset(self, name, values=None):
        """Creates a preset, overwriting the preset with the same name if any.

        Args:
            name (str): The name of the new preset.
            values (dict): The values of the new preset.
        """
        if not values:
            values = {}
            self._update_preset_values(values)
        self._add_preset(name, values)
        self.cur_preset = name

    def _add_preset(self, name, values):
        self._forget_preset(name)
        self.presets[name] = values
        # Note: This generates a "row-inserted" signal in the model.
        self.ordered.append((name, values))

    def _rename_current_preset(self, new_name):
        """Changes the name of the current preset."""
        old_name = self.cur_preset
        if old_name == new_name:
            # Nothing to do.
            return
        # If there is one already with this name, make way for this one.
        self._forget_preset(new_name)
        for row in self.ordered:
            if row[0] == old_name:
                row[0] = new_name
                break
        self.presets[new_name] = self.presets[old_name]
        if "filepath" in self.presets[old_name]:
            # If the previous preset had already been saved,
            # delete the file and pop it from the list
            self.remove_current_preset()
        else:
            # We're renaming an unsaved preset, so just pop it from the list
            self.presets.pop(old_name)
        new_filepath = self._create_user_preset_path(new_name)
        self.presets[new_name]["filepath"] = new_filepath
        self.cur_preset = new_name

    def _create_user_preset_path(self, preset_name):
        return os.path.join(self.user_path, preset_name + ".json")

    def has_preset(self, name):
        name = name.lower()
        return any(name == preset.lower() for preset in self.get_preset_names())

    def get_preset_names(self):
        return (row[0] for row in self.ordered)

    def update_value(self, name, value):
        """Updates a value in the current preset, if any."""
        if self.ignore_update_requests:
            # This is caused by restore_preset, nothing to do.
            return
        if self.cur_preset:
            self.presets[self.cur_preset][name] = value

    def bind_widget(self, propname, setter_func, getter_func):
        """Links the specified functions to the specified preset property."""
        self.widget_map[propname] = (setter_func, getter_func)

    def restore_preset(self, preset):
        """Selects a preset and copies its values to the widgets.

        Args:
            preset (str): The name of the preset to be selected.
        """
        if preset is None:
            self.cur_preset = None
            return
        if preset not in self.presets:
            return
        self.ignore_update_requests = True
        try:
            values = self.presets[preset]
            self.cur_preset = preset
            for field, (setter, unused_getter) in self.widget_map.items():
                setter(values[field])
        finally:
            self.ignore_update_requests = False

    def save_current_preset(self, new_name=None):
        """Updates the current preset values from the widgets and saves it."""
        if not self.cur_preset:
            self.create_preset(new_name)
        if new_name:
            self._rename_current_preset(new_name)
        values = self.presets[self.cur_preset]
        self._update_preset_values(values)
        self._save_preset(self.cur_preset)

    def _update_preset_values(self, values):
        """Copies the values from the widgets to the specified values dict."""
        for field, (unused_setter, getter) in self.widget_map.items():
            values[field] = getter()

    def _is_current_preset_changed(self, name):
        """Returns whether the widgets values differ from the preset values."""
        if not self.cur_preset:
            # There is no preset selected, nothing to do.
            return False
        if not name == self.cur_preset:
            # The preset can be renamed by saving.
            return True
        values = self.presets[self.cur_preset]
        return any((values[field] != getter()
                    for field, (setter, getter) in self.widget_map.items()))

    def remove_current_preset(self):
        name = self.cur_preset
        preset = self.presets[name]
        filepath = preset.get("filepath")
        if filepath:
            if "readonly" in preset:
                self._mark_removed(name)
            else:
                os.remove(filepath)

        self.cur_preset = None
        self._forget_preset(name)

    def _forget_preset(self, name):
        try:
            self.presets.pop(name)
        except KeyError:
            # Nothing to forget.
            return
        for i, row in enumerate(self.ordered):
            if row[0] == name:
                del self.ordered[i]
                break

    def _mark_removed(self, name):
        data = json.dumps({"name": name, "removed": True}, indent=4)
        filepath = self._create_user_preset_path(name)
        with open(filepath, "w", encoding="UTF-8") as fout:
            fout.write(data)

    def prepend_preset(self, name, values):
        self.presets[name] = values
        # Note: This generates a "row-inserted" signal in the model.
        self.ordered.prepend((name, values))

    def is_save_button_sensitive(self, name):
        """Checks whether the Save button should be enabled.

        Args:
            name (str): The new preset name.
        """
        if self.cur_preset:
            return self._is_current_preset_changed(name)

        if name:
            # Can be saved as new preset.
            return True

        return False

    def is_remove_button_sensitive(self):
        """Checks whether the Remove button should be enabled."""
        if not self.cur_preset:
            return False
        return True

    def is_new_button_sensitive(self):
        """Checks whether the New button should be enabled."""
        return bool(self.cur_preset)

    def _project_to_preset(self, project):
        raise NotImplementedError()

    def matching_preset(self, project):
        query = self._project_to_preset(project)
        for name, preset in self.presets.items():
            matches = True
            for key, value in query.items():
                if not value == preset.get(key):
                    matches = False
                    break
            if matches:
                return name
        return None


class VideoPresetManager(PresetManager):

    def __init__(self, system):
        default_path = get_videopresets_dir()
        user_path = xdg_data_home("video_presets")
        PresetManager.__init__(self, default_path, user_path, system)

    def _deserialize_preset(self, parser):
        width = parser["width"]
        height = parser["height"]

        framerate_num = parser["framerate-num"]
        framerate_denom = parser["framerate-denom"]
        framerate = Gst.Fraction(framerate_num, framerate_denom)

        return {
            "width": width,
            "height": height,
            "frame-rate": framerate,
        }

    def _serialize_preset(self, preset):
        return {
            "width": int(preset["width"]),
            "height": int(preset["height"]),
            "framerate-num": preset["frame-rate"].num,
            "framerate-denom": preset["frame-rate"].denom,
        }

    def _project_to_preset(self, project):
        return {
            "width": project.videowidth,
            "height": project.videoheight,
            "frame-rate": project.videorate}


class AudioPresetManager(PresetManager):

    def __init__(self, system):
        default_path = get_audiopresets_dir()
        user_path = xdg_data_home("audio_presets")
        PresetManager.__init__(self, default_path, user_path, system)

    def _deserialize_preset(self, parser):
        channels = parser["channels"]
        sample_rate = parser["sample-rate"]

        return {
            "channels": channels,
            "sample-rate": sample_rate,
        }

    def _serialize_preset(self, preset):
        return {
            "channels": preset["channels"],
            "sample-rate": int(preset["sample-rate"]),
        }

    def _project_to_preset(self, project):
        return {
            "channels": project.audiochannels,
            "sample-rate": project.audiorate}
