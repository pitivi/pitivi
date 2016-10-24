#!/usr/bin/env python2
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import os
from urllib import unquote

import urlparse
import utils
from baseclasses import GstValidateTest
from baseclasses import ScenarioManager
from baseclasses import TestsManager

Pitivi_DURATION_TOLERANCE = utils.GST_SECOND / 2


def quote_uri(uri):
    """
    Encode a URI/path according to RFC 2396, without touching the file:/// part.
    """
    # Split off the "file:///" part, if present.
    parts = urlparse.urlsplit(uri, allow_fragments=False)
    # Make absolutely sure the string is unquoted before quoting again!
    raw_path = unquote(parts.path)
    return utils.path2url(raw_path)


class PitiviTest(GstValidateTest):

    def __init__(self, executable, classname, options, reporter, scenario):
        super(PitiviTest, self).__init__(executable, classname, options, reporter,
                                         scenario=None)
        self._scenario = scenario

    def set_sample_paths(self):
        paths = self.options.paths

        if not isinstance(paths, list):
            paths = [paths]

        for path in paths:
            # We always want paths separator to be cut with '/' for ges-launch
            path = path.replace("\\", "/")
            self.add_arguments("--ges-sample-path-recurse", quote_uri(path))

    def build_arguments(self):
        GstValidateTest.build_arguments(self)

        self.set_sample_paths()
        self.add_arguments(self._scenario.path)


class PitiviTestsManager(TestsManager):
    name = "pitivi"

    _scenarios = ScenarioManager()

    def __init__(self):
        super(PitiviTestsManager, self).__init__()

    def init(self):
        self.fixme("Implement init checking")

        return True

    def add_options(self, parser):
        group = parser.add_argument_group("Pitivi specific option group"
                                          " and behaviours",
                                          description="")
        group.add_argument("--pitivi-executable", dest="pitivi_executable",
                           default=os.path.join("..", "..", "bin", "pitivi"),
                           help="Path to the pitivi executable")
        group.add_argument("--pitivi-scenarios-paths", dest="pitivi_scenario_paths",
                           help="Paths in which to look for scenario files")

    def set_settings(self, options, args, reporter):
        TestsManager.set_settings(self, options, args, reporter)
        self._scenarios.config = self.options

        try:
            os.makedirs(utils.url2path(options.dest)[0])
        except OSError:
            pass

    def list_tests(self):
        return self.tests

    def find_scenarios(self):
        for path in self.options.pitivi_scenario_paths:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if not file.endswith(".scenario"):
                        continue
                    yield os.path.join(path, root, file)

    def register_defaults(self):
        for scenario_name in self.find_scenarios():
            scenario = self._scenarios.get_scenario(scenario_name)
            if scenario is None:
                continue

            classname = "pitivi.%s" % scenario.name
            self.add_test(PitiviTest(self.options.pitivi_executable,
                                     classname,
                                     self.options,
                                     self.reporter,
                                     scenario=scenario))
