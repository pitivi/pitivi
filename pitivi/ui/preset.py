# PiTiVi , Non-linear video editor
#
#       pitivi/ui/controller.py
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from pitivi.settings import xdg_data_home
from ConfigParser import SafeConfigParser
from pitivi.ui.dynamic import DynamicWidget
from pitivi.ui.common import set_combo_value, get_combo_value
import os.path
import gtk
import gst

class PresetManager(object):

    def __init__(self):
        self.path = os.path.join(xdg_data_home(), "pitivi", self.filename)
        self.presets = {}
        self.widget_map = {}
        self.ordered = gtk.ListStore(str, object)
        self.cur_preset = None
        self.ignore = False

    def load(self):
        try:
            fin = open(self.path, "r")
            parser = SafeConfigParser()
            parser.readfp(fin)
            self._load(parser)
        except IOError:
            pass

    def save(self):
        fout = open(self.path, "w")
        parser = SafeConfigParser()
        self._save(parser)
        parser.write(fout)

    def _load(self, parser):
        for section in sorted(parser.sections()):
            self.loadSection(parser, section)

    def _save(self, parser):
        for name, properties in self.ordered:
            self.saveSection(parser, name)

    def loadSection(self, parser, section):
        raise NotImplemented

    def saveSection(self, parser, section):
        raise NotImplemented

    def addPreset(self, name, values):
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

    def loadSection(self, parser, section):
        width = parser.getint(section, "width")
        height = parser.getint(section, "height")

        rate_num = parser.getint(section, "framerate-num")
        rate_denom = parser.getint(section, "framerate-denom")
        rate = gst.Fraction(rate_num, rate_denom)

        par_num = parser.getint(section, "par-num")
        par_denom = parser.getint(section, "par-denom")
        par = gst.Fraction(par_num, par_denom)

        self.addPreset(section, {
            "width": width,
            "height": height,
            "frame-rate": rate,
            "par": par,
        })

    def saveSection(self, parser, section):
        values = self.presets[section]
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

    def loadSection(self, parser, section):
        channels = parser.getint(section, "channels")
        depth = parser.getint(section, "depth")
        rate = parser.getint(section, "sample-rate")

        self.addPreset(section, {
            "channels": channels,
            "depth": depth,
            "sample-rate": rate,
        })

    def saveSection(self, parser, section):
        values = self.presets[section]
        parser.add_section(section)
        parser.set(section, "channels", str(values["channels"]))
        parser.set(section, "depth", str(values["depth"]))
        parser.set(section, "sample-rate", str(values["sample-rate"]))
