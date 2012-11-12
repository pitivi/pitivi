# PiTiVi , Non-linear video editor
#
#       pitivi/preset.py
#
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

import os.path

from gi.repository import Gst
from gi.repository import Gtk
import json

from gettext import gettext as _

from pitivi.render import available_muxers, available_video_encoders, available_audio_encoders
from pitivi.settings import xdg_data_home
from pitivi.utils.misc import isWritable
from pitivi.configure import get_renderpresets_dir, get_audiopresets_dir, get_videopresets_dir


class DuplicatePresetNameException(Exception):
    """Raised when an operation would result in a duplicated preset name."""
    pass


class PresetManager(object):
    """Abstract class for storing a list of presets.

    Subclasses must provide a filename attribute.

    @cvar filename: The name of the file where the presets will be stored.
    @type filename: str

    @ivar cur_preset: The currently selected preset. Note that a preset has to
        be selected before it can be changed.
    @type cur_preset: str
    @ivar ordered: A list holding (name -> preset_dict) tuples.
    @type ordered: Gtk.ListStore
    @ivar presets: A (name -> preset_dict) map.
    @type presets: dict
    @ivar widget_map: A (propname -> (setter_func, getter_func)) map.
        These two functions are used when showing or saving a preset.
    @type widget_map: dict
    """

    def __init__(self):
        self.presets = {}
        self.widget_map = {}
        self.ordered = Gtk.ListStore(str, object)
        self.cur_preset = None
        # Whether to ignore the updateValue calls.
        self._ignore_update_requests = False

    def loadAll(self):
        filepaths = []
        try:
            for uri in os.listdir(self.default_path):
                filepaths.append(os.path.join(self.default_path, uri))
        except Exception:
            pass
        try:
            for uri in os.listdir(self.user_path):
                filepaths.append(os.path.join(self.user_path, uri))
        except Exception:
            pass

        for filepath in filepaths:
            if filepath.endswith("json"):
                self._loadSection(os.path.join(self.default_path, filepath))

    def saveAll(self):
        """Write changes to disk for all presets"""
        if os.path.isfile(self.user_path):
            # We used to save presets as a single file instead of a directory
            os.remove(self.user_path)
        if not os.path.exists(self.user_path):
            os.makedirs(self.user_path)
        for name, properties in self.ordered:
            if not name == _("No preset"):
                try:
                    filepath = self.presets[name]["filepath"]
                except KeyError:
                    filename = name + ".json"
                    filepath = os.path.join(self.user_path, filename)
                try:
                    fout = open(filepath, "w")
                    self._saveSection(fout, name)
                    self.presets[name]["filepath"] = filepath
                except IOError:
                    # FIXME: this can happen in two cases: a permissions error,
                    # or an invalid filename (ex: gibberish). In the latter case
                    # we should log an error message or show an infobar, and
                    # the test suite should verify this
                    pass

    def _convertSectionNameToPresetName(self, section):
        # A section name for a ConfigParser can have any name except "default"!
        assert section != "default"
        if section.rstrip("_").lower() == "default":
            return section[:-1]
        else:
            return section

    def _convertPresetNameToSectionName(self, preset):
        if preset.rstrip("_").lower() == "default":
            # We add an _ to allow the user to have a preset named "default".
            return "%s_" % preset
        else:
            return preset

    def addPreset(self, name, values):
        """Add a new preset.

        @param name: The name of the new preset.
        @type name: str
        @param values: The values of the new preset.
        @type values: dict
        """
        if type(name) == unicode:
            # We need utf-8 string objects, not unicode objects!
            name = name.encode("utf-8")
        if self.hasPreset(name):
            raise DuplicatePresetNameException(name)
        self.presets[name] = values
        # Note: This generates a "row-inserted" signal in the model.
        self.ordered.append((name, values))

    def renamePreset(self, path, new_name):
        """Change the name of a preset.

        @param path: The path in the model identifying the preset to be renamed.
        @type path: str
        @param new_name: The new name for the preset.
        @type new_name: str
        """
        old_name = self.ordered[path][0]
        assert old_name in self.presets
        if old_name == new_name:
            # Nothing to do.
            return
        if old_name.lower() != new_name.lower() and self.hasPreset(new_name):
            raise DuplicatePresetNameException()
        self.ordered[path][0] = new_name
        self.presets[new_name] = self.presets[old_name]
        if "filepath" in self.presets[old_name]:
            # If the previous preset had already been saved,
            # delete the file and pop it from the list
            self.removePreset(old_name)
        else:
            # We're renaming an unsaved preset, so just pop it from the list
            self.presets.pop(old_name)
        new_filepath = os.path.join(self.user_path, new_name + ".json")
        self.presets[new_name]["filepath"] = new_filepath
        self.cur_preset = new_name
        self.saveCurrentPreset()

    def hasPreset(self, name):
        name = name.lower()
        return any(name == preset.lower() for preset in self.getPresetNames())

    def getPresetNames(self):
        return (row[0] for row in self.ordered)

    def getModel(self):
        """Get the GtkModel used by the UI."""
        return self.ordered

    def updateValue(self, name, value):
        """Update a value in the current preset, if any."""
        if self._ignore_update_requests:
            # This is caused by restorePreset, nothing to do.
            return
        if self.cur_preset:
            self.presets[self.cur_preset][name] = value

    def bindWidget(self, propname, setter_func, getter_func):
        """Link the specified functions to the specified preset property."""
        self.widget_map[propname] = (setter_func, getter_func)

    def restorePreset(self, preset):
        """Select a preset and copy the values from the preset to the widgets.

        @param preset: The name of the preset to be selected.
        @type preset: str
        """
        self._ignore_update_requests = True
        if preset is None:
            self.cur_preset = None
            return
        elif not preset in self.presets:
            return
        values = self.presets[preset]
        self.cur_preset = preset
        for field, (setter, getter) in self.widget_map.iteritems():
            if values[field] != 0:
                setter(values[field])
            else:
                setter(self.presets[_("No preset")][field])
        self._ignore_update_requests = False

    def saveCurrentPreset(self):
        """Update the current preset values from the widgets and save it."""
        if self.cur_preset != _("No preset"):
            self._updatePreset()
            if os.path.isfile(self.user_path):
                # We used to save presets as a single file instead of a directory
                os.remove(self.user_path)
            if not os.path.exists(self.user_path):
                os.makedirs(self.user_path)
            try:
                filepath = self.presets[self.cur_preset]["filepath"]
            except KeyError:
                filepath = os.path.join(self.user_path, self.cur_preset + ".json")
            try:
                fout = open(filepath, "w")
                self._saveSection(fout, self.cur_preset)
                self.presets[self.cur_preset]["filepath"] = filepath
            except IOError:
                # TODO: show an error infobar... but this should never happen,
                # because the UI is supposed to disable the Save button
                # ...unless the user types an invalid filename (ex: gibberish)
                pass

    def _updatePreset(self):
        """Copy the values from the widgets to the preset."""
        values = self.presets[self.cur_preset]
        for field, (setter, getter) in self.widget_map.iteritems():
            values[field] = getter()

    def _isCurrentPresetChanged(self):
        """Return whether the widgets values differ from those of the preset."""
        if not self.cur_preset:
            # There is no preset selected, nothing to do.
            return False
        values = self.presets[self.cur_preset]
        return any((values[field] != getter()
                    for field, (setter, getter) in self.widget_map.iteritems()))

    def removePreset(self, name):
        try:
            os.remove(self.presets[name]["filepath"])  # Deletes json file if exists
        except KeyError:
            # Trying to remove a preset that has not actually been saved
            return
        except Exception:
            raise
        self.presets.pop(name)
        for i, row in enumerate(self.ordered):
            if row[0] == name:
                del self.ordered[i]
                break
        if self.cur_preset == name:
            self.cur_preset = None

    def prependPreset(self, name, values):
        self.presets[name] = values
        # Note: This generates a "row-inserted" signal in the model.
        self.ordered.prepend((name, values))

    def isSaveButtonSensitive(self):
        """Check if the Save button should be sensitive"""
        if not self.cur_preset or self.cur_preset == _("No preset"):
            return False
        try:
            full_path = self.presets[self.cur_preset]["filepath"]
            (dir, name) = os.path.split(full_path)
        except KeyError:
            # This is a newly created preset that has not yet been saved
            return True
        if dir == self.default_path or not isWritable(full_path):
            # default_path is the system-wide directory where the default
            # presets are installed; they are not expected to be editable.
            return False
        else:
            return self._isCurrentPresetChanged()

    def isRemoveButtonSensitive(self):
        """Check if Remove buttons should be sensitive"""
        if not self.cur_preset or self.cur_preset == _("No preset"):
            return False
        try:
            full_path = self.presets[self.cur_preset]["filepath"]
            (dir, name) = os.path.split(full_path)
        except KeyError:
            # This is a newly created preset that has not yet been saved
            # We cannot remove it since it does not exist
            return False
        if dir == self.default_path or not isWritable(full_path):
            # default_path is the system-wide directory where the default
            # presets are installed; they are not expected to be editable.
            return False
        else:
            return True
        return False

    def _saveSection(self, fout, section):
        """Save the specified section into the specified file.

        @param fout: The file where to save the section.
        @type parser: file
        @param section: The name of the section to be saved.
        @type section: string
        """
        raise NotImplementedError()


class VideoPresetManager(PresetManager):

    default_path = get_videopresets_dir()
    user_path = os.path.join(xdg_data_home(), 'video_presets')

    def _loadSection(self, filepath):
        parser = json.loads(open(filepath).read())

        name = parser["name"]
        width = parser["width"]
        height = parser["height"]

        framerate_num = parser["framerate-num"]
        framerate_denom = parser["framerate-denom"]
        framerate = Gst.Fraction(framerate_num, framerate_denom)

        par_num = parser["par-num"]
        par_denom = parser["par-denom"]
        par = Gst.Fraction(par_num, par_denom)

        self.addPreset(name, {
            "width": width,
            "height": height,
            "frame-rate": framerate,
            "par": par,
            "filepath": filepath,
        })

    def _saveSection(self, fout, section):
        values = self.presets[section]
        data = json.dumps({
            "name": section,
            "width": int(values["width"]),
            "height": int(values["height"]),
            "framerate-num": values["frame-rate"].num,
            "framerate-denom": values["frame-rate"].denom,
            "par-num": values["par"].num,
            "par-denom": values["par"].denom,
        }, indent=4)
        fout.write(data)


class AudioPresetManager(PresetManager):

    default_path = get_audiopresets_dir()
    user_path = os.path.join(xdg_data_home(), 'audio_presets')

    def _loadSection(self, filepath):
        parser = json.loads(open(filepath).read())

        name = parser["name"]

        channels = parser["channels"]
        depth = parser["depth"]
        sample_rate = parser["sample-rate"]

        self.addPreset(name, {
            "channels": channels,
            "depth": depth,
            "sample-rate": sample_rate,
            "filepath": filepath,
        })

    def _saveSection(self, fout, section):
        values = self.presets[section]
        data = json.dumps({
            "name": section,
            "channels": values["channels"],
            "depth": int(values["depth"]),
            "sample-rate": int(values["sample-rate"]),
        }, indent=4)
        fout.write(data)


class RenderPresetManager(PresetManager):

    default_path = get_renderpresets_dir()
    user_path = os.path.join(xdg_data_home(), 'render_presets')

    def _loadSection(self, filepath):
        parser = json.loads(open(filepath).read())

        name = parser["name"]
        container = parser["container"]
        acodec = parser["acodec"]
        vcodec = parser["vcodec"]

        if (acodec not in [fact.get_name() for fact in available_audio_encoders()]
        or vcodec not in [fact.get_name() for fact in available_video_encoders()]
        or container not in [fact.get_name() for fact in available_muxers()]):
            return

        try:
            width = parser["width"]
            height = parser["height"]
        except:
            width = 0
            height = 0

        framerate_num = parser["framerate-num"]
        framerate_denom = parser["framerate-denom"]
        framerate = Gst.Fraction(framerate_num, framerate_denom)

        channels = parser["channels"]
        depth = parser["depth"]
        sample_rate = parser["sample-rate"]

        self.addPreset(name, {
            "container": container,
            "acodec": acodec,
            "vcodec": vcodec,
            "width": width,
            "height": height,
            "frame-rate": framerate,
            "channels": channels,
            "depth": depth,
            "sample-rate": sample_rate,
            "filepath": filepath,
        })

    def _saveSection(self, fout, section):
        values = self.presets[section]
        data = json.dumps({
            "name": section,
            "container": str(values["container"]),
            "acodec": str(values["acodec"]),
            "vcodec": str(values["vcodec"]),
            "width": int(values["width"]),
            "height": int(values["height"]),
            "framerate-num": values["frame-rate"].num,
            "framerate-denom": values["frame-rate"].denom,
            "channels": values["channels"],
            "depth": int(values["depth"]),
            "sample-rate": int(values["sample-rate"]),
        }, indent=4)
        fout.write(data)
