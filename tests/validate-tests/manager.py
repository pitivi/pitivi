#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, Thibault Saunier <thibault.saunier@collabora.com>
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
"""The Pitivi GstValidate tests manager and friends."""
import os
import urllib.parse
from urllib.parse import unquote

from launcher import utils
from launcher.baseclasses import GstValidateTest
from launcher.baseclasses import ScenarioManager
from launcher.baseclasses import TestsManager


def quote_uri(uri):
    """Encodes a URI/path according to RFC 2396."""
    # Split off the "file:///" part, if present.
    parts = urllib.parse.urlsplit(uri, allow_fragments=False)
    # Make absolutely sure the string is unquoted before quoting again!
    raw_path = unquote(parts.path)
    return utils.path2url(raw_path)


class PitiviTest(GstValidateTest):
    """A scenario to be run as a test."""

    def __init__(self, executable, classname, options, reporter, scenario):
        super(PitiviTest, self).__init__(executable, classname, options, reporter,
                                         scenario=None)
        self._scenario = scenario

    def set_sample_paths(self):
        """Passes the media paths as optional flags."""
        paths = self.options.paths

        if not isinstance(paths, list):
            paths = [paths]

        for path in paths:
            # We always want paths separator to be cut with '/' for ges-launch
            path = path.replace("\\", "/")
            self.add_arguments("--ges-sample-path-recurse", quote_uri(path))

    def build_arguments(self):
        """Prepares the arguments for the executable used to run the test."""
        GstValidateTest.build_arguments(self)

        self.set_sample_paths()
        # Pass the path to the scenario file as a positional argument.
        self.add_arguments(self._scenario.path)


class PitiviTestsManager(TestsManager):

    name = "pitivi"
    """The name identifying this test manager class."""

    _scenarios = ScenarioManager()

    def init(self):
        """Initializes the manager."""
        self.fixme("Implement init checking")

        return True

    def add_options(self, parser):
        """Adds options to the specified ArgumentParser."""
        group = parser.add_argument_group("Pitivi specific option group"
                                          " and behaviours",
                                          description="")
        group.add_argument("--pitivi-executable", dest="pitivi_executable",
                           default=os.path.join("..", "..", "bin", "pitivi"),
                           help="Path to the pitivi executable")
        group.add_argument("--pitivi-scenarios-paths", dest="pitivi_scenario_paths",
                           help="Paths in which to look for scenario files")

    def set_settings(self, options, args, reporter):
        """Configures the manager based on the specified options."""
        TestsManager.set_settings(self, options, args, reporter)
        PitiviTestsManager._scenarios.config = self.options

        try:
            os.makedirs(utils.url2path(options.dest)[0])
        except OSError:
            pass

    def list_tests(self):
        """Lists the tests in the order they have been added."""
        return self.tests

    def find_scenarios(self):
        """Yields paths to the found scenario files."""
        for path in self.options.pitivi_scenario_paths:
            for root, unused_dirs, files in os.walk(path):
                for file in files:
                    if not file.endswith(".scenario"):
                        continue
                    yield os.path.join(path, root, file)

    def register_defaults(self):
        """Adds the available scenario files as tests."""
        for scenario_name in self.find_scenarios():
            scenario = PitiviTestsManager._scenarios.get_scenario(scenario_name)
            if scenario is None:
                continue

            classname = "pitivi.%s" % scenario.name
            self.add_test(PitiviTest(self.options.pitivi_executable,
                                     classname,
                                     self.options,
                                     self.reporter,
                                     scenario=scenario))
