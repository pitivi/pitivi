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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import json
import os.path
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import Gtk

from pitivi.configure import get_audiopresets_dir
from pitivi.configure import get_videopresets_dir
from pitivi.settings import xdg_config_home
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
        self.ordered.set_sort_column_id(0, Gtk.SortType.DESCENDING)
        self.cur_preset = None
        # Whether to ignore the updateValue calls.
        self.ignore_update_requests = False
        self.system = system

    def setupUi(self, combo, button):
        self.combo = combo
        self.button = button

        combo.set_model(self.ordered)
        combo.set_id_column(0)
        combo.set_entry_text_column(0)
        combo.connect("changed", self._presetChangedCb)

        entry = combo.get_child()
        alter_style_class("GtkEntry.unsaved", entry, "font-style:italic;")

        action_group = Gio.SimpleActionGroup()
        menu_model = Gio.Menu()

        action = Gio.SimpleAction.new("new", None)
        action.connect("activate", self._addPresetCb)
        action_group.add_action(action)
        menu_model.append(_("New"), "preset.%s" % action.get_name())
        self.action_new = action

        action = Gio.SimpleAction.new("remove", None)
        action.connect("activate", self._removePresetCb)
        action_group.add_action(action)
        menu_model.append(_("Remove"), "preset.%s" % action.get_name())
        self.action_remove = action

        action = Gio.SimpleAction.new("save", None)
        action.connect("activate", self._savePresetCb)
        action_group.add_action(action)
        menu_model.append(_("Save"), "preset.%s" % action.get_name())
        self.action_save = action

        menu = Gtk.Menu.new_from_model(menu_model)
        menu.insert_action_group("preset", action_group)
        button.set_popup(menu)

    def _presetChangedCb(self, combo):
        """Handles the selection of a preset."""
        # Check whether the user selected a preset or editing the preset name.
        self.select_preset(combo)
        self.updateMenuActions()

    def select_preset(self, combo):
        preset_name = combo.get_active_id()
        if preset_name:
            # The user selected a preset.
            self.restorePreset(preset_name)
            self.emit("preset-loaded")

    def _addPresetCb(self, unused_action, unused_param):
        preset_name = self.getNewPresetName()
        self.createPreset(preset_name)
        self.combo.set_active_id(preset_name)
        self.updateMenuActions()

    def _removePresetCb(self, unused_action, unused_param):
        self.removeCurrentPreset()
        self.updateMenuActions()

    def _savePresetCb(self, unused_action, unused_param):
        entry = self.combo.get_child()
        preset_name = entry.get_text()
        self.saveCurrentPreset(preset_name)
        self.updateMenuActions()

    def updateMenuActions(self):
        entry = self.combo.get_child()
        preset_name = entry.get_text()
        can_save = self.isSaveButtonSensitive(preset_name)
        self.action_save.set_enabled(can_save)
        if can_save:
            entry.get_style_context().add_class("unsaved")
        else:
            entry.get_style_context().remove_class("unsaved")

        can_remove = self.isRemoveButtonSensitive()
        self.action_remove.set_enabled(can_remove)

        can_create_new = self.isNewButtonSensitive()
        self.action_new.set_enabled(can_create_new)

    def loadAll(self):
        self._loadFromDir(self.default_path, extra={"readonly": True})
        if os.path.isfile(self.user_path):
            # We used to save presets as a single file instead of a directory
            os.rename(self.user_path, "%s.old" % self.user_path)
        self._loadFromDir(self.user_path)

    def _loadFromDir(self, presets_dir, extra={}):
        try:
            files = os.listdir(presets_dir)
        except FileNotFoundError:
            self.debug("Presets directory missing: %s", presets_dir)
            return
        for uri in files:
            filepath = os.path.join(presets_dir, uri)
            if filepath.endswith("json"):
                with open(filepath) as section:
                    parser = json.loads(section.read())
                name = parser["name"]
                if parser.get("removed"):
                    self._forgetPreset(name)
                    continue
                try:
                    preset = self._deserializePreset(parser)
                except DeserializeException as e:
                    self.debug("Failed to load preset %s: %s", filepath, e)
                    continue
                preset["filepath"] = filepath
                for key, value in extra.items():
                    preset[key] = value
                self._addPreset(name, preset)

    def saveAll(self):
        """Writes changes to disk for all presets."""
        for preset_name, values in self.ordered:
            self._savePreset(preset_name)

    def _savePreset(self, preset_name):
        if not os.path.exists(self.user_path):
            os.makedirs(self.user_path)
        try:
            file_path = self.presets[preset_name]["filepath"]
        except KeyError:
            file_path = self._buildFilePath(preset_name)
            self.presets[preset_name]["filepath"] = file_path
        with open(file_path, "w") as fout:
            values = self.presets[preset_name]
            raw = self._serializePreset(values)
            raw["name"] = preset_name
            serialized = json.dumps(raw, indent=4)
            fout.write(serialized)

    def _buildFilePath(self, preset_name):
        file_name = self.system.getUniqueFilename(preset_name + ".json")
        return os.path.join(self.user_path, file_name)

    def getNewPresetName(self):
        """Gets a unique name for a new preset."""
        name = _("New preset")
        i = 1
        while self.hasPreset(name):
            name = _("New preset %d") % i
            i += 1
        return name

    def createPreset(self, name, values=None):
        """Creates a preset, overwriting the preset with the same name if any.

        Args:
            name (str): The name of the new preset.
            values (dict): The values of the new preset.
        """
        if not values:
            values = {}
            self._updatePresetValues(values)
        self._addPreset(name, values)
        self.cur_preset = name

    def _addPreset(self, name, values):
        self._forgetPreset(name)
        self.presets[name] = values
        # Note: This generates a "row-inserted" signal in the model.
        self.ordered.append((name, values))

    def _renameCurrentPreset(self, new_name):
        """Changes the name of the current preset."""
        old_name = self.cur_preset
        if old_name == new_name:
            # Nothing to do.
            return
        # If there is one already with this name, make way for this one.
        self._forgetPreset(new_name)
        for i, row in enumerate(self.ordered):
            if row[0] == old_name:
                row[0] = new_name
                break
        self.presets[new_name] = self.presets[old_name]
        if "filepath" in self.presets[old_name]:
            # If the previous preset had already been saved,
            # delete the file and pop it from the list
            self.removeCurrentPreset()
        else:
            # We're renaming an unsaved preset, so just pop it from the list
            self.presets.pop(old_name)
        new_filepath = self._createUserPresetPath(new_name)
        self.presets[new_name]["filepath"] = new_filepath
        self.cur_preset = new_name

    def _createUserPresetPath(self, preset_name):
        return os.path.join(self.user_path, preset_name + ".json")

    def hasPreset(self, name):
        name = name.lower()
        return any(name == preset.lower() for preset in self.getPresetNames())

    def getPresetNames(self):
        return (row[0] for row in self.ordered)

    def getModel(self):
        """Gets the GtkModel used by the UI."""
        return self.ordered

    def updateValue(self, name, value):
        """Updates a value in the current preset, if any."""
        if self.ignore_update_requests:
            # This is caused by restorePreset, nothing to do.
            return
        if self.cur_preset:
            self.presets[self.cur_preset][name] = value

    def bindWidget(self, propname, setter_func, getter_func):
        """Links the specified functions to the specified preset property."""
        self.widget_map[propname] = (setter_func, getter_func)

    def restorePreset(self, preset):
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
            for field, (setter, getter) in self.widget_map.items():
                setter(values[field])
        finally:
            self.ignore_update_requests = False

    def saveCurrentPreset(self, new_name=None):
        """Updates the current preset values from the widgets and saves it."""

        if not self.cur_preset:
            self.createPreset(preset_name)
        if new_name:
            self._renameCurrentPreset(new_name)
        values = self.presets[self.cur_preset]
        self._updatePresetValues(values)
        self._savePreset(self.cur_preset)

    def _updatePresetValues(self, values):
        """Copies the values from the widgets to the specified values dict."""
        for field, (setter, getter) in self.widget_map.items():
            values[field] = getter()

    def _isCurrentPresetChanged(self, name):
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

    def removeCurrentPreset(self):
        name = self.cur_preset
        preset = self.presets[name]
        filepath = preset.get("filepath")
        if filepath:
            if "readonly" in preset:
                self._markRemoved(name)
            else:
                os.remove(filepath)

        self.cur_preset = None
        self._forgetPreset(name)

    def _forgetPreset(self, name):
        try:
            self.presets.pop(name)
        except KeyError:
            # Nothing to forget.
            return
        for i, row in enumerate(self.ordered):
            if row[0] == name:
                del self.ordered[i]
                break

    def _markRemoved(self, name):
        data = json.dumps({"name": name, "removed": True}, indent=4)
        filepath = self._createUserPresetPath(name)
        with open(filepath, "w") as fout:
            fout.write(data)

    def prependPreset(self, name, values):
        self.presets[name] = values
        # Note: This generates a "row-inserted" signal in the model.
        self.ordered.prepend((name, values))

    def isSaveButtonSensitive(self, name):
        """Checks whether the Save button should be enabled.

        Args:
            name (str): The new preset name.
        """
        if self.cur_preset:
            return self._isCurrentPresetChanged(name)

        if name:
            # Can be saved as new preset.
            return True

        return False

    def isRemoveButtonSensitive(self):
        """Checks whether the Remove button should be enabled."""
        if not self.cur_preset:
            return False
        return True

    def isNewButtonSensitive(self):
        """Checks whether the New button should be enabled."""
        return bool(self.cur_preset)

    def _projectToPreset(self, project):
        raise NotImplementedError()

    def matchingPreset(self, project):
        query = self._projectToPreset(project)
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
        user_path = os.path.join(xdg_data_home(), 'video_presets')
        PresetManager.__init__(self, default_path, user_path, system)

    def _deserializePreset(self, parser):
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

    def _serializePreset(self, preset):
        return {
            "width": int(preset["width"]),
            "height": int(preset["height"]),
            "framerate-num": preset["frame-rate"].num,
            "framerate-denom": preset["frame-rate"].denom,
        }

    def _projectToPreset(self, project):
        return {
            "width": project.videowidth,
            "height": project.videoheight,
            "frame-rate": project.videorate}


class AudioPresetManager(PresetManager):

    def __init__(self, system):
        default_path = get_audiopresets_dir()
        user_path = os.path.join(xdg_data_home(), 'audio_presets')
        PresetManager.__init__(self, default_path, user_path, system)

    def _deserializePreset(self, parser):
        channels = parser["channels"]
        sample_rate = parser["sample-rate"]

        return {
            "channels": channels,
            "sample-rate": sample_rate,
        }

    def _serializePreset(self, preset):
        return {
            "channels": preset["channels"],
            "sample-rate": int(preset["sample-rate"]),
        }

    def _projectToPreset(self, project):
        return {
            "channels": project.audiochannels,
            "sample-rate": project.audiorate}


class EncodingTargetManager(PresetManager):
    """Manager of EncodingTargets used as render presets.

    Uses the GstEncodingTarget API to discover and access the EncodingProfiles.

    Attributes:
        _project (Project): The project.
    """

    __gsignals__ = {
        "profile-selected": (GObject.SignalFlags.RUN_LAST, None, (GstPbutils.EncodingProfile,)),
    }

    def __init__(self, project):
        PresetManager.__init__(self)
        self._project = project
        self._removed_file_list = os.path.join(xdg_data_home(),
                                               'hidden_encoding_profiles.json')
        try:
            with open(self._removed_file_list) as f:
                self._removed_profiles = json.loads(f.read())
        except FileNotFoundError:
            self._removed_profiles = []

    def _add_target(self, target):
        profiles = target.get_profiles()
        for profile in profiles:
            name = target.get_name().split(';')[0]
            if len(profiles) != 1 and profile.get_name().lower() != 'default':
                name += '_' + profile.get_name()

            if name in self._removed_profiles:
                continue

            self.presets[name] = profile
            self._addPreset(name, profile)

    def loadAll(self):
        """Loads profiles from GstEncodingTarget and add them to self.combo.

        Override from PresetManager
        """
        for target in GstPbutils.encoding_list_all_targets():
            if target.get_category() != GstPbutils.ENCODING_CATEGORY_FILE_EXTENSION:
                self._add_target(target)

    def createPreset(self, name, values=None):
        self.saveCurrentPreset(name, validate_name=False)

    def getNewPresetName(self):
        """Gets a unique name for a new preset."""
        # Translators: This must contain exclusively low case alphanum and '-'
        name = _("new-profile")
        i = 1
        while self.hasPreset(name):
            # Translators: This must contain exclusively low case alphanum and '-'
            name = _("new-profile-%d") % i
            i += 1
        return name

    def saveCurrentPreset(self, new_name, validate_name=True):
        """PresetManager override, saves currently selected profile on disk.

        Override from PresetManager

        Args:
            new_name (str): The name to save current Gst.EncodingProfile as.
        """
        if validate_name and not self.combo.get_parent().valid:
            self.error("Current encoding target name is not valid")
            return

        if new_name in self._removed_profiles:
            self._removed_profiles.remove(new_name)
            self._save_removed_profiles()

        target = GstPbutils.EncodingTarget.new(new_name, "user-defined",
                                               new_name,
                                               [self._project.container_profile])
        target.save()

        self._add_target(target)
        self.combo.set_active(len(self.combo.props.model) - 1)

    def select_preset(self, combo):
        """Selects preset from currently active row in @combo.

        Override from PresetManager

        Args:
            combo (str): The Gtk.ComboBox to retrieve selected GstEncodingProfile from.
        """
        active_iter = combo.get_active_iter()
        name = None
        if active_iter:
            # The user selected a preset.
            name = combo.props.model.get_value(active_iter, 0)
            profile = combo.props.model.get_value(active_iter, 1)
            self.emit("profile-selected", profile)
        self.cur_preset = name

    def _save_removed_profiles(self):
        with open(self._removed_file_list, 'w') as f:
            json.dump(self._removed_profiles, f)

    def removeCurrentPreset(self):
        self._removed_profiles.append(self.cur_preset)
        self._save_removed_profiles()
        self._forgetPreset(self.cur_preset)
        self.combo.get_parent().setWidgetValue(self.getNewPresetName())
        self.cur_preset = None

    def restorePreset(self, values):
        """Raises NotImplemented as it does not make sense for that class.

        Override from PresetManager
        """
        raise NotImplementedError
