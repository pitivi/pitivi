#!/usr/bin/env python2
#
# Copyright (c) 2013,Thibault Saunier <thibault.saunier@collabora.com>
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
import sys
import urlparse
import utils
from urllib import unquote
from baseclasses import GstValidateTest, TestsManager, ScenarioManager

Pitivi_DURATION_TOLERANCE = utils.GST_SECOND / 2

PITIVI_COMMAND = "pitivi"
if "win32" in sys.platform:
    PITIVI_COMMAND += ".exe"


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
    def __init__(self, classname, options, reporter, scenario,
                 combination=None):

        super(PitiviTest, self).__init__(PITIVI_COMMAND, classname, options, reporter,
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
        group.add_argument("--pitivi-scenarios-paths", dest="pitivi_scenario_paths",
                           default=os.path.join(os.path.basename(__file__),
                                                "pitivi",
                                                "pitivi scenarios"),
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

    def register_defaults(self):
        scenarios = list()
        for path in self.options.pitivi_scenario_paths:
            for root, dirs, files in os.walk(path):
                for f in files:
                    if not f.endswith(".scenario"):
                        continue
                    scenarios.append(os.path.join(path, root, f))

        for scenario_name in scenarios:
            scenario = self._scenarios.get_scenario(scenario_name)
            if scenario is None:
                continue

            classname = "pitivi.%s" % (scenario.name)
            self.add_test(PitiviTest(classname,
                                     self.options,
                                     self.reporter,
                                     scenario=scenario)
                          )
