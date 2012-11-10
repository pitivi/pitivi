# PiTiVi , Non-linear video editor
#
#       tests/test_projectsettings.py
#
# Copyright (c) 2011, Alex Balut <alexandru.balut@gmail.com>
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

from unittest import TestCase

from pitivi.preset import PresetManager
from pitivi.project import ProjectSettingsDialog


class TestProjectSettingsDialog(TestCase):

    def testGetUniquePresetName(self):
        preset_manager = PresetManager()
        name = ProjectSettingsDialog._getUniquePresetName(preset_manager)
        self.assertEqual('New preset', name)

        preset_manager.addPreset(name, {})
        new_preset1 = ProjectSettingsDialog._getUniquePresetName(preset_manager)
        self.assertEqual('New preset 1', new_preset1)

        # Intentionally add 'New preset 2' before 'New preset 1'.
        preset_manager.addPreset('New preset 2', {})
        preset_manager.addPreset('New preset 1', {})
        new_preset3 = ProjectSettingsDialog._getUniquePresetName(preset_manager)
        self.assertEqual('New preset 3', new_preset3)
