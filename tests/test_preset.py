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

    def _serializePreset(self, preset):
        return dict(preset.items())


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
        self.manager = FakePresetManager(None)

    def tearDown(self):
        clearPresetManagerPaths(self.manager)

    def testAddPreset(self):
        self.manager.createPreset('preseT onE', {'name1': '1A'})
        self.assertRaises(DuplicatePresetNameException,
                          self.manager.createPreset, 'Preset One', {'name1': '2A'})

    def testAddPresetWithNonAsciiName(self):
        unicode_name = "ソリッド・スネーク"
        self.manager.createPreset(unicode_name, {})
        self.assertTrue(unicode_name in self.manager.getPresetNames())

    def testRenamePreset(self):
        self.manager.createPreset('preseT onE', {'name1': '1A'})
        self.manager.createPreset('Preset Two', {'name1': '2A'})

        # Renaming 'preseT onE' to 'Preset One'.
        self.manager.renamePreset('0', 'Preset One')

        # Renaming 'Preset One' to 'Preset TWO'.
        self.assertRaises(DuplicatePresetNameException,
                          self.manager.renamePreset, '0', 'Preset TWO')
        # Renaming 'Preset One' to 'Preset two'.
        self.assertRaises(DuplicatePresetNameException,
                          self.manager.renamePreset, '0', 'Preset two')

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
        self.manager = AudioPresetManager()
        self.manager.user_path = tempfile.mkdtemp()

    def tearDown(self):
        clearPresetManagerPaths(self.manager)

    def createOtherManager(self):
        other_manager = AudioPresetManager()
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
