#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2014, Thibault Saunier <thibault.saunier@collabora.com>
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
"""The Pitivi GstValidate testsuite."""
import os


# Instruct GstValidate to use the test manager with name == "pitivi".
TEST_MANAGER = "pitivi"


def setup_tests(test_manager, options):
    """Sets up the specified test manager."""
    path = os.path.abspath(os.path.dirname(__file__))
    print("Setting up Pitivi integration tests in %s" % path)
    options.pitivi_scenario_paths = [os.path.join(path, "scenarios")]
    options.add_paths(os.path.join(path, os.path.pardir, "samples"))
    options.pitivi_executable = os.path.join(path, "..", "..", "bin", "pitivi")
    test_manager.register_defaults()
    # Everything went fine.
    return True
