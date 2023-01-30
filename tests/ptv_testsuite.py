# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2017, Thibault Saunier <tsaunier@gnome.org>
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
"""GstValidateLauncher testsuite to run our unit tests."""
import os
import sys
import unittest

TEST_MANAGER = "base"
CDIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(CDIR, '..'))

# pylint: disable=wrong-import-position
# pylint: disable=unused-import
# Import tests so that the module is initialized
import tests
# pylint: disable=import-error
# pylint: disable=wrong-import-order
from launcher.baseclasses import Test

import launcher


class PitiviTest(Test):
    """A Test corresponding to a module in our unit tests suite."""

    def build_arguments(self):
        """Builds subprocess arguments."""
        self.add_arguments("-m", "unittest", ".".join(self.classname.split(".")[1:]))


def setup_tests(
        test_manager: launcher.baseclasses.GstValidateBaseTestManager,
        options: "launcher.baseclasses.LauncherConfig"):
    """Sets up Pitivi unit testsuite."""
    if os.environ.get("PITIVI_VSCODE_DEBUG", False):
        import debugpy
        debugpy.listen(("0.0.0.0", 5678))
        print("Waiting for the debugger to attach...")
        debugpy.wait_for_client()

    loader = unittest.TestLoader()
    testsuites: unittest.suite.TestSuite = loader.discover(CDIR)
    # A testsuite per each .py file.
    for testsuite in testsuites:
        # A testsuite per each unittest.TestCase subclass.
        for _tests in testsuite:
            if isinstance(_tests, unittest.loader._FailedTest):  # pylint: disable=protected-access
                print(_tests._exception)  # pylint: disable=protected-access
                continue

            # A test for each test_* method.
            for test in _tests:
                env = {"PYTHONPATH": os.path.join(CDIR, "..")}
                gitlab_ci = os.environ.get("GITLAB_CI")
                if gitlab_ci:
                    # The tests extend internal timeouts when they figure they
                    # are running in the CI.
                    env["GITLAB_CI"] = gitlab_ci
                    # Workaround a segfault when GStreamer deinitializes
                    # https://gitlab.freedesktop.org/gstreamer/gstreamer/-/issues/1964
                    env["GST_DEBUG"] = "*:5"
                test_manager.add_test(PitiviTest(
                    sys.executable,
                    "tests." + test.id(),
                    options,
                    test_manager.reporter,
                    extra_env_variables=env))

    return True
