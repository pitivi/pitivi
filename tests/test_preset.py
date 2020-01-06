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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Tests for the pitivi.preset module."""
# pylint: disable=protected-access
import os.path
import shutil
import tempfile

from pitivi.preset import AudioPresetManager
from pitivi.preset import PresetManager
from pitivi.utils.system import System
from tests import common


def clear_preset_manager_paths(preset_manager):
    try:
        shutil.rmtree(preset_manager.user_path)
    except FileNotFoundError:
        pass


def count_json_files_in(dir_path):
    return len([filename
                for filename in os.listdir(dir_path)
                if filename.endswith(".json")])


def count_default_presets(preset_manager):
    return count_json_files_in(preset_manager.default_path)


def count_user_presets(preset_manager):
    return count_json_files_in(preset_manager.user_path)


class TestPresetBasics(common.TestCase):

    def setUp(self):
        self.manager = PresetManager(None, tempfile.mkdtemp(), System())
        self.manager._serialize_preset = lambda preset: dict(preset.items())

    def tearDown(self):
        clear_preset_manager_paths(self.manager)

    def test_add_preset(self):
        self.manager.create_preset('preseT onE', {'name1': '1A'})
        self.manager.create_preset('Preset One', {'name1': '2A'})
        self.assertEqual(2, len(self.manager.presets))

    def test_add_preset_with_non_ascii_name(self):
        unicode_name = "ソリッド・スネーク"
        self.manager.create_preset(unicode_name, {})
        self.assertTrue(unicode_name in self.manager.get_preset_names())

    def test_rename_preset(self):
        self.manager.create_preset('preseT onE', {'name1': '1A'})
        self.manager.create_preset('Preset Two', {'name1': '2A'})
        self.assertEqual(2, len(self.manager.presets))

        self.manager.restore_preset('preseT onE')
        self.manager.save_current_preset('Preset One')
        self.assertEqual(2, len(self.manager.presets))
        self.manager.save_current_preset('Preset TWO')
        self.assertEqual(2, len(self.manager.presets))
        self.manager.save_current_preset('Preset two')
        self.assertEqual(2, len(self.manager.presets))

        self.manager.save_current_preset('Preset Two')
        self.assertEqual(1, len(self.manager.presets))
        self.manager.save_current_preset('Preset Two')
        self.assertEqual(1, len(self.manager.presets))
        self.manager.save_current_preset('preseT onE')
        self.assertEqual(1, len(self.manager.presets))

    def test_load_handles_missing_directory(self):
        self.manager.default_path = '/pitivi/non/existing/directory/1'
        self.manager.user_path = '/pitivi/non/existing/directory/2'
        self.manager.load_all()

    def test_get_unique_preset_name(self):
        name = self.manager.get_new_preset_name()
        self.assertEqual('New preset', name)

        self.manager.create_preset(name, {})
        new_preset1 = self.manager.get_new_preset_name()
        self.assertEqual('New preset 1', new_preset1)

        # Intentionally add 'New preset 2' before 'New preset 1'.
        self.manager.create_preset('New preset 2', {})
        self.manager.create_preset('New preset 1', {})
        new_preset3 = self.manager.get_new_preset_name()
        self.assertEqual('New preset 3', new_preset3)


class TestAudioPresetsIO(common.TestCase):

    def setUp(self):
        self.manager = AudioPresetManager(System())
        self.manager.user_path = tempfile.mkdtemp()

    def tearDown(self):
        clear_preset_manager_paths(self.manager)

    def create_other_manager(self):
        other_manager = AudioPresetManager(System())
        other_manager.user_path = self.manager.user_path
        return other_manager

    def test_save_and_load(self):
        self.manager.create_preset("Vegeta",
                                   {"channels": 6000,
                                    "sample-rate": 44100})
        self.manager.save_all()
        self.assertEqual(1, count_user_presets(self.manager))

        self.manager.create_preset("Nappa",
                                   {"channels": 4000,
                                    "sample-rate": 44100})
        self.manager.save_all()
        self.assertEqual(2, count_user_presets(self.manager))

        other_manager = self.create_other_manager()
        other_manager.load_all()
        total_presets = count_default_presets(
            self.manager) + count_user_presets(self.manager)
        self.assertEqual(total_presets, len(other_manager.presets))

    def test_non_ascii_filenames_save_and_load(self):
        non_ascii_preset_name = "Solid Snake (ソリッド・スネーク) \\#!\"'$%?&*"
        self.manager.create_preset(non_ascii_preset_name,
                                   {"channels": 2,
                                    "sample-rate": 44100})
        snake = self.manager.presets[non_ascii_preset_name]
        self.assertEqual(2, len(snake))
        self.manager.save_all()

        other_manager = self.create_other_manager()
        other_manager.load_all()
        self.assertEqual(1 + count_default_presets(
            other_manager), len(other_manager.presets))
        snaaaake = other_manager.presets[non_ascii_preset_name]
        self.assertEqual(snake, snaaaake)

    def test_invalid_filenames_save_and_load(self):
        # This would be an invalid file name as is.
        preset_name = " / % "
        self.manager.create_preset(preset_name,
                                   {"channels": 2,
                                    "sample-rate": 44100})
        values = self.manager.presets[preset_name]
        self.assertEqual(2, len(values))
        self.manager.save_all()

        other_manager = self.create_other_manager()
        other_manager.load_all()
        self.assertEqual(1 + count_default_presets(
            other_manager), len(other_manager.presets))
        other_values = other_manager.presets[preset_name]
        self.assertEqual(values, other_values)

    def test_removing_system_presets(self):
        self.manager.load_all()
        system_presets = list(self.manager.presets.keys())
        for preset_name in system_presets:
            self.manager.restore_preset(preset_name)
            self.manager.remove_current_preset()

        # Check that the files have not been deleted or changed.
        other_manager = AudioPresetManager(System())
        other_manager.user_path = "/pitivi/non/existing/directory"
        other_manager.load_all()
        for preset_name in system_presets:
            self.assertTrue(other_manager.has_preset(preset_name))

        # Check that overwrite files have been created and
        # they mark the system presets as deleted.
        other_manager = self.create_other_manager()
        other_manager.load_all()
        for preset_name in system_presets:
            self.assertFalse(other_manager.has_preset(preset_name))

    def test_renaming_system_presets(self):
        self.manager.load_all()
        system_presets = list(self.manager.presets.keys())
        new_name_template = "%s new"
        for preset_name in system_presets:
            self.manager.restore_preset(preset_name)
            new_name = new_name_template % preset_name
            self.manager.save_current_preset(new_name)

        # Check that the files have not been deleted or changed.
        other_manager = AudioPresetManager(System())
        other_manager.user_path = "/pitivi/non/existing/directory"
        other_manager.load_all()
        for preset_name in system_presets:
            self.assertTrue(other_manager.has_preset(preset_name), preset_name)

        other_manager = self.create_other_manager()
        other_manager.load_all()
        for preset_name in system_presets:
            self.assertFalse(other_manager.has_preset(preset_name), preset_name)
            new_name = new_name_template % preset_name
            self.assertTrue(other_manager.has_preset(new_name), new_name)
