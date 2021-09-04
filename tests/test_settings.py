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
import os
import tempfile
from unittest import mock

from gi.repository import Gdk

from pitivi.settings import ConfigError
from pitivi.settings import GlobalSettings
from tests import common


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
            with open(os.path.join(temp_dir, "pitivi.conf"), "w", encoding="UTF-8") as tmp_file:
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
