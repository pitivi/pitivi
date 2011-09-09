# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
#
#       tests/test_preset.py
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

import os.path
import shutil
import tempfile
from unittest import TestCase

from pitivi.ui.preset import DuplicatePresetNameException, PresetManager


class SimplePresetManager(PresetManager):
    """A preset manager that stores any (str: str) dict."""

    def __init__(self, empty_dir):
        PresetManager.__init__(self)
        self.user_path = self.dir = empty_dir

    def _getFilename(self):
        return os.path.join(self.dir, 'simple')

    def _loadPreset(self, parser, section):
        return dict(parser.items(section))

    def _savePreset(self, parser, section, values):
        parser.add_section(section)
        for name, value in values.iteritems():
            parser.set(section, name, value)


class TestProjectManager(TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.manager = SimplePresetManager(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def testConvertPresetNameToSectionName(self):
        self.assertEqual(
                'my preset',
                self.manager._convertPresetNameToSectionName('my preset'))
        self.assertEqual(
                'my preset_',
                self.manager._convertPresetNameToSectionName('my preset_'))
        self.assertEqual(
                'default_x_',
                self.manager._convertPresetNameToSectionName('default_x_'))

        # Test that default_* preset names get a _ character at the end.
        self.assertEqual(
                'Default_',
                self.manager._convertPresetNameToSectionName('Default'))
        self.assertEqual(
                'defaulT__',
                self.manager._convertPresetNameToSectionName('defaulT_'))

    def testConvertSectionNameToPresetName(self):
        self.assertEqual(
                'my preset',
                self.manager._convertSectionNameToPresetName('my preset'))
        self.assertEqual(
                'my preset_',
                self.manager._convertSectionNameToPresetName('my preset_'))
        self.assertEqual(
                'default_x_',
                self.manager._convertSectionNameToPresetName('default_x_'))

        # Test that default_+ section names lose the last character.
        self.assertEqual(
                'Default',
                self.manager._convertSectionNameToPresetName('Default_'))
        self.assertEqual(
                'defaulT_',
                self.manager._convertSectionNameToPresetName('defaulT__'))

    def testSaveAndLoad(self):
        self.manager.addPreset('preset one', {'name1': '1A'})
        self.manager.addPreset('default_', {'name2': '2A'})
        self.manager.addPreset('Default', {'name1': '1B', 'name2': '2B'})
        self.manager.saveAll()
        self.manager.addPreset('Solid Snake (ソリッド・スネーク) \#!"/$%?&*',
            {'name': 'デイビッド'})
        self.manager.saveAll()

        other_manager = SimplePresetManager(self.tempdir)
        other_manager.loadAll()
        
        snaaaake = other_manager.presets['Solid Snake (ソリッド・スネーク) \#!"/$%?&*']
        self.assertEqual(1, len(snaaaake))

        default = other_manager.presets['Default']
        self.assertEqual(2, len(default))
        self.assertEqual('1B', default['name1'])
        self.assertEqual('2B', default['name2'])

        default_ = other_manager.presets['default_']
        self.assertEqual(1, len(default_))
        self.assertEqual('2A', default_['name2'])

        preset_one = other_manager.presets['preset one']
        self.assertEqual(1, len(preset_one))
        self.assertEqual('1A', preset_one['name1'])

    def testAddPreset(self):
        self.manager.addPreset('preseT onE', {'name1': '1A'})
        self.assertRaises(DuplicatePresetNameException,
                self.manager.addPreset, 'Preset One', {'name1': '2A'})

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
