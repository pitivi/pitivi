# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       tests/test_preset.py
#
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

from pitivi.preset import DuplicatePresetNameException, \
    PresetManager, \
    AudioPresetManager


class FakePresetManager(PresetManager):

    def __init__(self, default_path):
        PresetManager.__init__(self, default_path, tempfile.mkdtemp())

    def _saveSection(self, fout, section):
        pass


def clearPresetManagerPaths(preset_manager):
    shutil.rmtree(preset_manager.user_path)


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
        self.manager = FakePresetManager(None)

    def tearDown(self):
        clearPresetManagerPaths(self.manager)

    def testConvertPresetNameToSectionName(self):
        self.presetToSection = self.manager._convertPresetNameToSectionName
        self.assertEqual("my preset", self.presetToSection('my preset'))
        self.assertEqual("my preset_", self.presetToSection('my preset_'))
        self.assertEqual("default_x_", self.presetToSection('default_x_'))

        # Test that default_* preset names get a _ character at the end.
        self.assertEqual("Default_", self.presetToSection('Default'))
        self.assertEqual("defaulT__", self.presetToSection('defaulT_'))

    def testConvertSectionNameToPresetName(self):
        self.sectionToPreset = self.manager._convertSectionNameToPresetName
        self.assertEqual("my preset", self.sectionToPreset('my preset'))
        self.assertEqual("my preset_", self.sectionToPreset('my preset_'))
        self.assertEqual("default_x_", self.sectionToPreset('default_x_'))

        # Test that default_+ section names lose the last character.
        self.assertEqual("Default", self.sectionToPreset('Default_'))
        self.assertEqual("defaulT_", self.sectionToPreset('defaulT__'))

    def testAddPreset(self):
        self.manager.addPreset('preseT onE', {'name1': '1A'})
        self.assertRaises(DuplicatePresetNameException,
                          self.manager.addPreset, 'Preset One', {'name1': '2A'})

    def testAddDuplicatePreset(self):
        self.manager.addPreset('x', {})
        self.assertRaises(
            DuplicatePresetNameException, self.manager.addPreset, 'x', {})

    def testAddPresetWithNonAsciiName(self):
        unicode_name = "ソリッド・スネーク"
        self.manager.addPreset(unicode_name, {})
        self.assertTrue(unicode_name in self.manager.getPresetNames())

    def testRenamePreset(self):
        self.manager.addPreset('preseT onE', {'name1': '1A'})
        self.manager.addPreset('Preset Two', {'name1': '2A'})

        # Renaming 'preseT onE' to 'Preset One'.
        self.manager.renamePreset('0', 'Preset One')

        # Renaming 'Preset One' to 'Preset TWO'.
        self.assertRaises(DuplicatePresetNameException,
                          self.manager.renamePreset, '0', 'Preset TWO')
        # Renaming 'Preset One' to 'Preset two'.
        self.assertRaises(DuplicatePresetNameException,
                          self.manager.renamePreset, '0', 'Preset two')


class TestAudioPresetsIO(TestCase):

    def setUp(self):
        self.manager = AudioPresetManager()
        self.manager.user_path = tempfile.mkdtemp()

    def tearDown(self):
        clearPresetManagerPaths(self.manager)

    def createOtherManager(self):
        other_manager = AudioPresetManager()
        other_manager.user_path = self.manager.user_path
        return other_manager

    def testSaveAndLoad(self):
        self.manager.addPreset("Vegeta",
                               {"channels": 6000,
                                "sample-rate": 44100})
        self.manager.saveAll()
        self.assertEqual(1, countUserPresets(self.manager))

        self.manager.addPreset("Nappa",
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
        self.manager.addPreset(non_ascii_preset_name,
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
        self.manager.addPreset(preset_name,
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
