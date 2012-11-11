# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
#
#       tests/test_preset.py
#
# Copyright (c) 2011, Alex Balut <alexandru.balut@gmail.com>
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

from pitivi.configure import get_audiopresets_dir
from pitivi.preset import DuplicatePresetNameException, \
    PresetManager, \
    AudioPresetManager


class FakePresetManager(PresetManager):

    def _saveSection(self, fout, section):
        pass


def setPresetManagerPaths(preset_manager, default_path):
    preset_manager.default_path = default_path
    preset_manager.user_path = tempfile.mkdtemp()


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
        self.manager = FakePresetManager()
        setPresetManagerPaths(self.manager, None)

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
        self.assertRaises(DuplicatePresetNameException, self.manager.addPreset, 'x', {})

    def testAddPresetWithNonAsciiName(self):
        unicode_name = u"ソリッド・スネーク"
        self.manager.addPreset(unicode_name, {})
        self.assertTrue(unicode_name.encode("utf-8") in self.manager.getPresetNames())

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
        setPresetManagerPaths(self.manager, get_audiopresets_dir())

    def tearDown(self):
        clearPresetManagerPaths(self.manager)

    def testSaveAndLoad(self):
        self.manager.addPreset("Vegeta",
            {"channels": 6000,
            "depth": 16,
            "sample-rate": 44100,
            "filepath": os.path.join(self.manager.user_path, "vegeta.json")})
        self.manager.saveAll()
        self.assertEqual(1, countUserPresets(self.manager))

        self.manager.addPreset("Nappa",
            {"channels": 4000,
            "depth": 16,
            "sample-rate": 44100,
            "filepath": os.path.join(self.manager.user_path, "nappa.json")})
        self.manager.saveAll()
        self.assertEqual(2, countUserPresets(self.manager))

        self.assertIn("vegeta.json", os.listdir(self.manager.user_path))
        self.assertIn("nappa.json", os.listdir(self.manager.user_path))

        other_manager = AudioPresetManager()
        other_manager.default_path = self.manager.default_path
        other_manager.user_path = self.manager.user_path
        other_manager.loadAll()

        total_presets = countDefaultPresets(self.manager) + countUserPresets(self.manager)
        self.assertEqual(total_presets, len(other_manager.presets))

    def testEsotericFilenames(self):
        self.manager.addPreset("Default",
            {"channels": 2,
            "depth": -9000,
            "sample-rate": 44100,
            "filepath": os.path.join(self.manager.user_path, "Default.json")})
        self.manager.saveAll()

        self.manager.addPreset('Solid Snake (ソリッド・スネーク) \#!"/$%?&*',
            {"channels": 2,
            "depth": 16,
            "sample-rate": 44100,
            "filepath": os.path.join(self.manager.user_path,
                'Solid Snake (ソリッド・スネーク) \#!"/$%?&*' + ".json")})
        snake = self.manager.presets['Solid Snake (ソリッド・スネーク) \#!"/$%?&*']
        self.assertEqual(4, len(snake))
        # The slash ("/") in the filename is supposed to make it choke
        #self.assertRaises(IOError, self.manager.saveAll)
        # Let's be slightly more gentle
        snake["filepath"] = os.path.join(self.manager.user_path,
                'Solid Snake (ソリッド・スネーク)' + ".json")
        self.manager.saveAll()

        # Create a second concurrent instance with the same paths,
        # to check that it can read and write from the first instance's data
        other_manager = AudioPresetManager()
        other_manager.default_path = self.manager.default_path
        other_manager.user_path = self.manager.user_path
        other_manager.loadAll()

        snaaaake = other_manager.presets['Solid Snake (ソリッド・スネーク)']
        self.assertEqual(2, snaaaake["channels"])

        foo = other_manager.presets['Default']
        self.assertEqual(4, len(foo))
        self.assertEqual(-9000, foo["depth"])

        self.assertEquals(2, len(other_manager.presets))
