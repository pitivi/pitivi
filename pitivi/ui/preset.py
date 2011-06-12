# PiTiVi , Non-linear video editor
#
#       pitivi/ui/preset.py
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

import ConfigParser
import os.path

import gst
import gtk

from pitivi.settings import xdg_data_home



class PresetManager(object):
    """Abstract class for storing a list of presets.

    Subclasses must provide a filename attribute.

    @cvar filename: The name of the file where the presets will be stored.
    @type filename: str
    """

    def __init__(self):
        self.presets = {}
        self.widget_map = {}
        self.ordered = gtk.ListStore(str, object)
        self.cur_preset = None
        self.ignore = False

    def _getFilename(self):
        return os.path.join(xdg_data_home(), "pitivi", self.filename)

    def load(self):
        parser = ConfigParser.SafeConfigParser()
        if not parser.read(self._getFilename()):
            # The file probably does not exist yet.
            return
        self._loadPresetsFromParser(parser)

    def save(self):
        parser = ConfigParser.SafeConfigParser()
        self._savePresetsToParser(parser)
        fout = open(self._getFilename(), "w")
        parser.write(fout)
        fout.close()

    def _loadPresetsFromParser(self, parser):
        for section in sorted(parser.sections()):
            values = self._loadPreset(parser, section)
            preset = self._convertSectionNameToPresetName(section)
            self.addPreset(preset, values)

    def _savePresetsToParser(self, parser):
        for preset, properties in self.ordered:
            values = self.presets[preset]
            section = self._convertPresetNameToSectionName(preset)
            self._savePreset(parser, section, values)

    def _loadPreset(self, parser, section):
        """Load the specified section from the specified config parser.

        @param parser: The config parser from which the section will be loaded.
        @type parser: ConfigParser
        @param section: The name of the section to be loaded.
        @type section: str
        @return: A dict representing a preset.
        """
        raise NotImplemented

    def _savePreset(self, parser, section, values):
        """Create the specified section into the specified config parser.

        @param parser: The config parser in which the section will be created.
        @type parser: ConfigParser
        @param section: The name of the section to be created.
        @type section: str
        @param values: The values of a preset.
        @type values: dict
        """
        raise NotImplemented

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
        self.presets[name] = values
        self.ordered.append((name, values))

    def removePreset(self, name):
        self.presets.pop(name)
        for i, row in enumerate(self.ordered):
            if row[0] == name:
                del self.ordered[i]
                break
        if self.cur_preset == name:
            self.cur_preset = None

    def renamePreset(self, path, new_name):
        old_name = self.ordered[path][0]
        self.ordered[path][0] = new_name
        self.presets[new_name] = self.presets.pop(old_name)

    def getPresetNames(self):
        return (row[0] for row in self.ordered)

    def getModel(self):
        return self.ordered

    def updateValue(self, name, value):
        if self.cur_preset and not self.ignore:
            self.presets[self.cur_preset][name] = value

    def bindWidget(self, propname, setter_func, getter_func):
        self.widget_map[propname] = (setter_func, getter_func)

    def restorePreset(self, preset):
        self.ignore = True
        if preset is None:
            self.cur_preset = None
            return
        elif not preset in self.presets:
            return
        values = self.presets[preset]
        self.cur_preset = preset
        for field, (setter_func, getter_func) in self.widget_map.iteritems():
            setter_func(values[field])
        self.ignore = False

    def savePreset(self):
        values = self.presets[self.cur_preset]
        for field, (setter, getter) in self.widget_map.iteritems():
            values[field] = getter()

    def changed(self):
        if not self.cur_preset:
            return False

        values = self.presets[self.cur_preset]
        return any((values[field] != getter() for field, (setter, getter)
            in self.widget_map.iteritems()))


class VideoPresetManager(PresetManager):

    filename = "video_presets"

    def _loadPreset(self, parser, section):
        width = parser.getint(section, "width")
        height = parser.getint(section, "height")

        rate_num = parser.getint(section, "framerate-num")
        rate_denom = parser.getint(section, "framerate-denom")
        rate = gst.Fraction(rate_num, rate_denom)

        par_num = parser.getint(section, "par-num")
        par_denom = parser.getint(section, "par-denom")
        par = gst.Fraction(par_num, par_denom)

        return {
            "width": width,
            "height": height,
            "frame-rate": rate,
            "par": par}

    def _savePreset(self, parser, section, values):
        parser.add_section(section)
        parser.set(section, "width", str(values["width"]))
        parser.set(section, "height", str(values["height"]))
        parser.set(section, "framerate-num",
            str(int(values["frame-rate"].num)))
        parser.set(section, "framerate-denom",
            str(int(values["frame-rate"].denom)))
        parser.set(section, "par-num",
            str(int(values["par"].num)))
        parser.set(section, "par-denom",
            str(int(values["par"].denom)))


class AudioPresetManager(PresetManager):

    filename = "audio_presets"

    def _loadPreset(self, parser, section):
        channels = parser.getint(section, "channels")
        depth = parser.getint(section, "depth")
        rate = parser.getint(section, "sample-rate")

        return {
            "channels": channels,
            "depth": depth,
            "sample-rate": rate}

    def _savePreset(self, parser, section, values):
        parser.add_section(section)
        parser.set(section, "channels", str(values["channels"]))
        parser.set(section, "depth", str(values["depth"]))
        parser.set(section, "sample-rate", str(values["sample-rate"]))
