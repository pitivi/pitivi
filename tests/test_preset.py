# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2011, Alex Băluț <alexandru.balut@gmail.com>
# Copyright (c) 2011, Jean-François Fortin Tam <nekohayo@gmail.com>
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
# TODO: add a specific testcase for audio, video, render presets
import os.path
import shutil
import tempfile
from unittest import TestCase

from pitivi.preset import AudioPresetManager
from pitivi.preset import PresetManager
from pitivi.utils.system import System


def clearPresetManagerPaths(preset_manager):
    try:
        shutil.rmtree(preset_manager.user_path)
    except FileNotFoundError:
        pass


def countJsonFilesIn(dir_path):
    return len([filename
                for filename in os.listdir(dir_path)
                if filename.endswith(".json")])


def countDefaultPresets(preset_manager):
    return countJsonFilesIn(preset_manager.default_path)


def countUserPresets(preset_manager):
    return countJsonFilesIn(preset_manager.user_path)


class TestPresetBasics(TestCase):

    def setUp(self):
        self.manager = PresetManager(None, tempfile.mkdtemp(), System())
        self.manager._serializePreset = lambda preset: dict(preset.items())

    def tearDown(self):
        clearPresetManagerPaths(self.manager)

    def testAddPreset(self):
        self.manager.createPreset('preseT onE', {'name1': '1A'})
        self.manager.createPreset('Preset One', {'name1': '2A'})
        self.assertEqual(2, len(self.manager.presets))

    def testAddPresetWithNonAsciiName(self):
        unicode_name = "ソリッド・スネーク"
        self.manager.createPreset(unicode_name, {})
        self.assertTrue(unicode_name in self.manager.getPresetNames())

    def testRenamePreset(self):
        self.manager.createPreset('preseT onE', {'name1': '1A'})
        self.manager.createPreset('Preset Two', {'name1': '2A'})
        self.assertEqual(2, len(self.manager.presets))

        self.manager.restorePreset('preseT onE')
        self.manager.saveCurrentPreset('Preset One')
        self.assertEqual(2, len(self.manager.presets))
        self.manager.saveCurrentPreset('Preset TWO')
        self.assertEqual(2, len(self.manager.presets))
        self.manager.saveCurrentPreset('Preset two')
        self.assertEqual(2, len(self.manager.presets))

        self.manager.saveCurrentPreset('Preset Two')
        self.assertEqual(1, len(self.manager.presets))
        self.manager.saveCurrentPreset('Preset Two')
        self.assertEqual(1, len(self.manager.presets))
        self.manager.saveCurrentPreset('preseT onE')
        self.assertEqual(1, len(self.manager.presets))

    def testLoadHandlesMissingDirectory(self):
        self.manager.default_path = '/pitivi/non/existing/directory/1'
        self.manager.user_path = '/pitivi/non/existing/directory/2'
        self.manager.loadAll()

    def testGetUniquePresetName(self):
        name = self.manager.getNewPresetName()
        self.assertEqual('New preset', name)

        self.manager.createPreset(name, {})
        new_preset1 = self.manager.getNewPresetName()
        self.assertEqual('New preset 1', new_preset1)

        # Intentionally add 'New preset 2' before 'New preset 1'.
        self.manager.createPreset('New preset 2', {})
        self.manager.createPreset('New preset 1', {})
        new_preset3 = self.manager.getNewPresetName()
        self.assertEqual('New preset 3', new_preset3)


class TestAudioPresetsIO(TestCase):

    def setUp(self):
        self.manager = AudioPresetManager(System())
        self.manager.user_path = tempfile.mkdtemp()

    def tearDown(self):
        clearPresetManagerPaths(self.manager)

    def createOtherManager(self):
        other_manager = AudioPresetManager(System())
        other_manager.user_path = self.manager.user_path
        return other_manager

    def testSaveAndLoad(self):
        self.manager.createPreset("Vegeta",
                                  {"channels": 6000,
                                   "sample-rate": 44100})
        self.manager.saveAll()
        self.assertEqual(1, countUserPresets(self.manager))

        self.manager.createPreset("Nappa",
                                  {"channels": 4000,
                                   "sample-rate": 44100})
        self.manager.saveAll()
        self.assertEqual(2, countUserPresets(self.manager))

        other_manager = self.createOtherManager()
        other_manager.loadAll()
        total_presets = countDefaultPresets(
            self.manager) + countUserPresets(self.manager)
        self.assertEqual(total_presets, len(other_manager.presets))

    def testNonAsciiFilenamesSaveAndLoad(self):
        non_ascii_preset_name = "Solid Snake (ソリッド・スネーク) \\#!\"'$%?&*"
        self.manager.createPreset(non_ascii_preset_name,
                                  {"channels": 2,
                                   "sample-rate": 44100})
        snake = self.manager.presets[non_ascii_preset_name]
        self.assertEqual(2, len(snake))
        self.manager.saveAll()

        other_manager = self.createOtherManager()
        other_manager.loadAll()
        self.assertEqual(1 + countDefaultPresets(
            other_manager), len(other_manager.presets))
        snaaaake = other_manager.presets[non_ascii_preset_name]
        self.assertEqual(snake, snaaaake)

    def testInvalidFilenamesSaveAndLoad(self):
        # This would be an invalid file name as is.
        preset_name = " / % "
        self.manager.createPreset(preset_name,
                                  {"channels": 2,
                                   "sample-rate": 44100})
        values = self.manager.presets[preset_name]
        self.assertEqual(2, len(values))
        self.manager.saveAll()

        other_manager = self.createOtherManager()
        other_manager.loadAll()
        self.assertEqual(1 + countDefaultPresets(
            other_manager), len(other_manager.presets))
        other_values = other_manager.presets[preset_name]
        self.assertEqual(values, other_values)

    def testRemovingSystemPresets(self):
        self.manager.loadAll()
        system_presets = list(self.manager.presets.keys())
        for preset_name in system_presets:
            self.manager.restorePreset(preset_name)
            self.manager.removeCurrentPreset()

        # Check that the files have not been deleted or changed.
        other_manager = AudioPresetManager(System())
        other_manager.user_path = "/pitivi/non/existing/directory"
        other_manager.loadAll()
        for preset_name in system_presets:
            self.assertTrue(other_manager.hasPreset(preset_name))

        # Check that overwrite files have been created and
        # they mark the system presets as deleted.
        other_manager = self.createOtherManager()
        other_manager.loadAll()
        for preset_name in system_presets:
            self.assertFalse(other_manager.hasPreset(preset_name))

    def testRenamingSystemPresets(self):
        self.manager.loadAll()
        system_presets = list(self.manager.presets.keys())
        new_name_template = "%s new"
        for preset_name in system_presets:
            self.manager.restorePreset(preset_name)
            new_name = new_name_template % preset_name
            self.manager.saveCurrentPreset(new_name)

        # Check that the files have not been deleted or changed.
        other_manager = AudioPresetManager(System())
        other_manager.user_path = "/pitivi/non/existing/directory"
        other_manager.loadAll()
        for preset_name in system_presets:
            self.assertTrue(other_manager.hasPreset(preset_name), preset_name)

        other_manager = self.createOtherManager()
        other_manager.loadAll()
        for preset_name in system_presets:
            self.assertFalse(other_manager.hasPreset(preset_name), preset_name)
            new_name = new_name_template % preset_name
            self.assertTrue(other_manager.hasPreset(new_name), new_name)
