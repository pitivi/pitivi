# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2017, Fabian Orccon <cfoch.fabian@gmail.com>
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
"""Tests for the pitivi.settings module."""
# pylint: disable=no-self-use
import configparser
import datetime
import os
import tempfile
import uuid
from unittest import mock

from gi.repository import Gdk

from pitivi.project import ProjectManager
from pitivi.settings import ConfigError
from pitivi.settings import EditorState
from pitivi.settings import GlobalSettings
from tests import common


class TestEditorState(common.TestCase):
    """Tests the EditorState class."""

    def setUp(self):
        self.app = common.create_pitivi_mock()
        self.app.project_manager = ProjectManager(self.app)
        self.project = self.app.project_manager.new_blank_project()
        self.editor_state = EditorState(self.app)

    def tearDown(self):
        pass

    def __load_editor_state(self, editor_state, timestamp):
        """Loads the given editor state into self.editor_state.

        This way it can be used with editor_state.get_value.
        """
        path = self.editor_state.get_file_path()
        contents = {
            'metadata': {
                'timestamp': timestamp
            },
            'timeline': {
                'playhead-position': editor_state['playhead-position'],
                'zoom-level': editor_state['zoom-level'],
                'hadjustment': editor_state['hadjustment'],
                'selection': editor_state['selection']
            }
        }
        self.__write_editor_state_file(path, contents)
        self.editor_state.load_editor_state(self.project)

    def __write_editor_state_file(self, file_path, contents):
        config = configparser.ConfigParser()
        for section in contents:
            config.add_section(section)
            for option in contents[section]:
                config.set(section, option, str(contents[section][option]))
        with open(file_path, 'w') as file:
            config.write(file)

    def test_save_load_editor_state_file(self):
        editor_state = {
            'playhead-position': 5000000000,
            'zoom-level': 50,
            'hadjustment': 50.0,
            'selection': []
        }
        timestamp = datetime.datetime.now().timestamp()
        self.editor_state.save_editor_state(editor_state, timestamp)
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)
        self.assertEqual(self.editor_state.get_timestamp(), timestamp)

    def test_editor_state_file_already_exists_on_load(self):
        editor_state = {
            'playhead-position': 5000000000,
            'zoom-level': 50,
            'hadjustment': 50.0,
            'selection': []
        }
        timestamp = datetime.datetime.now().timestamp()
        self.__load_editor_state(editor_state, timestamp)
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)
        self.assertEqual(self.editor_state.get_timestamp(), timestamp)

    def test_editor_state_file_already_exists_on_save(self):
        editor_state = {
            'playhead-position': 5000000000,
            'zoom-level': 50,
            'hadjustment': 50.0,
            'selection': []
        }
        timestamp = datetime.datetime.now().timestamp()
        self.__load_editor_state(editor_state, timestamp)
        timestamp = datetime.datetime.now().timestamp()
        self.editor_state.save_editor_state(editor_state, timestamp)
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)
        self.assertEqual(self.editor_state.get_timestamp(), timestamp)

    def test_editor_state_file_missing(self):
        """Associated editor state file is missing."""
        editor_state = EditorState.get_default()
        project_id = uuid.uuid4().hex
        self.project.set_string('project-id', project_id)
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)

    def test_no_editor_state_file(self):
        """No associated editor state file."""
        editor_state = EditorState.get_default()
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)

    def test_missing_section_on_save(self):
        """Existing editor state file with missing section."""
        timestamp = datetime.datetime.now().timestamp()
        path = self.editor_state.get_file_path()
        contents = {
            'metadata': {
                'timestamp': timestamp
            }
        }
        self.__write_editor_state_file(path, contents)
        editor_state = {
            'playhead-position': 5000000000,
            'zoom-level': 50,
            'hadjustment': 50.0,
            'selection': []
        }
        self.editor_state.save_editor_state(editor_state, timestamp)
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)
        self.assertEqual(self.editor_state.get_timestamp(), timestamp)

    def test_missing_section_on_load(self):
        """Existing editor state file with missing section."""
        timestamp = datetime.datetime.now().timestamp()
        path = self.editor_state.get_file_path()
        contents = {
            'metadata': {
                'timestamp': timestamp
            }
        }
        self.__write_editor_state_file(path, contents)
        editor_state = EditorState.get_default()
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)
        self.assertEqual(self.editor_state.get_timestamp(), timestamp)

    def test_missing_values(self):
        """Existing editor state file with missing values."""
        path = self.editor_state.get_file_path()
        contents = {
            'metadata': {
                'timestamp': ""
            },
            'timeline': {
                'playhead-position': "",
                'zoom-level': "",
                'hadjustment': "",
                'selection': ""
            }
        }
        self.__write_editor_state_file(path, contents)
        editor_state = EditorState.get_default()
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)

    def test_editor_state_full_cycle(self):
        common.create_timeline_container()
        editor_state = {
            'playhead-position': 5000000000,
            'zoom-level': 50,
            'hadjustment': 50.0,
            'selection': []
        }
        timestamp = datetime.datetime.now().timestamp()
        self.__load_editor_state(editor_state, timestamp)
        timestamp = datetime.datetime.now().timestamp()
        self.editor_state.load_editor_state(self.project)
        self.editor_state.save_editor_state(None, timestamp)
        self.assertEqual(self.editor_state.load_editor_state(self.project), editor_state)
        self.assertEqual(self.editor_state.get_timestamp(), timestamp)


class TestGlobalSettings(common.TestCase):
    """Tests the GlobalSettings class."""

    def setUp(self):
        self.__attributes = []
        self.__options = GlobalSettings.options
        self.__environment = GlobalSettings.environment
        self.__defaults = GlobalSettings.defaults
        self.__add_config_option_real = GlobalSettings.add_config_option
        GlobalSettings.options = {}
        GlobalSettings.environment = set()
        GlobalSettings.defaults = {}
        GlobalSettings.add_config_option = self.__add_config_option

    def __add_config_option(self, attrname, *args, **kwargs):
        """Calls GlobalSettings.add_config_option but remembers attributes.

        It receives the same arguments as GlobalSettings.add_config_option but
        remembers attributes so they can be cleaned later.
        """
        self.__add_config_option_real(attrname, *args, **kwargs)
        if hasattr(GlobalSettings, attrname):
            self.__attributes.append(attrname)

    def tearDown(self):
        GlobalSettings.options = self.__options
        GlobalSettings.environment = self.__environment
        GlobalSettings.defaults = self.__defaults
        GlobalSettings.add_config_option = self.__add_config_option_real
        self.__clean_settings_attributes()

    def __clean_settings_attributes(self):
        """Cleans new attributes set to GlobalSettings."""
        for attribute in self.__attributes:
            delattr(GlobalSettings, attribute)
        self.__attributes = []

    def test_add_section(self):
        GlobalSettings.add_config_section("section-a")
        GlobalSettings.add_config_section("section-a")

    def test_add_config_option(self):
        def add_option():
            GlobalSettings.add_config_option("optionA1", section="section-a",
                                             key="option-a-1", default=False)
        # "section-a" does not exist.
        with self.assertRaises(ConfigError):
            add_option()

        GlobalSettings.add_config_section("section-a")
        add_option()
        self.assertFalse(GlobalSettings.optionA1)
        with self.assertRaises(ConfigError):
            add_option()

    def test_read_config_file(self):
        GlobalSettings.add_config_section("section-1")
        GlobalSettings.add_config_option("section1OptionA", section="section-1",
                                         key="option-a", default=50)
        GlobalSettings.add_config_option("section1OptionB", section="section-1",
                                         key="option-b", default=False)
        GlobalSettings.add_config_option("section1OptionC", section="section-1",
                                         key="option-c", default="")
        GlobalSettings.add_config_option("section1OptionD", section="section-1",
                                         key="option-d", default=[])
        GlobalSettings.add_config_option("section1OptionE", section="section-1",
                                         key="option-e", default=["foo"])
        GlobalSettings.add_config_option("section1OptionF", section="section-1",
                                         key="option-f", default=Gdk.RGBA())

        self.assertEqual(GlobalSettings.section1OptionA, 50)
        self.assertEqual(GlobalSettings.section1OptionB, False)
        self.assertEqual(GlobalSettings.section1OptionC, "")
        self.assertEqual(GlobalSettings.section1OptionD, [])
        self.assertEqual(GlobalSettings.section1OptionE, ["foo"])
        self.assertEqual(GlobalSettings.section1OptionF, Gdk.RGBA())

        self.assertIs(GlobalSettings.options["section-1"]["section1OptionA"][0], int)
        self.assertIs(GlobalSettings.options["section-1"]["section1OptionB"][0], bool)
        self.assertIs(GlobalSettings.options["section-1"]["section1OptionC"][0], str)
        self.assertIs(GlobalSettings.options["section-1"]["section1OptionD"][0], list)
        self.assertIs(GlobalSettings.options["section-1"]["section1OptionE"][0], list)
        self.assertIs(GlobalSettings.options["section-1"]["section1OptionF"][0], Gdk.RGBA)

        conf_file_content = ("[section-1]\n"
                             "option-a = 10\n"
                             "option-b = True\n"
                             "option-c = Pigs fly\n"
                             "option-d=\n"
                             "option-e=\n"
                             "     elmo\n"
                             "          knows\n"
                             "     where you live\n"
                             "option-f=rgba(51,102,255,0.4)")

        with mock.patch("pitivi.settings.xdg_config_home") as xdg_config_home,\
                tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "pitivi.conf"), "w") as tmp_file:
                tmp_file.write(conf_file_content)
            xdg_config_home.return_value = temp_dir
            settings = GlobalSettings()

        self.assertEqual(settings.section1OptionA, 10)
        self.assertEqual(settings.section1OptionB, True)
        self.assertEqual(settings.section1OptionC, "Pigs fly")
        self.assertEqual(settings.section1OptionD, [])
        expected_e_value = [
            "elmo",
            "knows",
            "where you live"
        ]
        self.assertEqual(settings.section1OptionE, expected_e_value)
        self.assertEqual(settings.section1OptionF, Gdk.RGBA(0.2, 0.4, 1.0, 0.4))

    def test_write_config_file(self):
        GlobalSettings.add_config_section("section-new")
        GlobalSettings.add_config_option("sectionNewOptionA",
                                         section="section-new", key="option-a",
                                         default="elmo")
        GlobalSettings.add_config_option("sectionNewOptionB",
                                         section="section-new", key="option-b",
                                         default=["foo"])

        with mock.patch("pitivi.settings.xdg_config_home") as xdg_config_home,\
                tempfile.TemporaryDirectory() as temp_dir:
            xdg_config_home.return_value = temp_dir
            settings1 = GlobalSettings()

            settings1.sectionNewOptionA = "kermit"
            settings1.sectionNewOptionB = []
            settings1.store_settings()

            settings2 = GlobalSettings()
            self.assertEqual(settings2.sectionNewOptionA, "kermit")
            self.assertEqual(settings2.sectionNewOptionB, [])
