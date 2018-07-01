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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
# pylint: disable=missing-docstring,invalid-name
"""GstValidateLauncher testsuite to run out unit tests."""
import os
import sys
import unittest

TEST_MANAGER = "base"
CDIR = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(CDIR, '..'))

# pylint: disable=wrong-import-position
# pylint: disable=unused-import
# Import tests so that the module is initialized
import tests  # noqa
# pylint: disable=import-error
from launcher.baseclasses import Test  # noqa
from launcher.config import GST_VALIDATE_TESTSUITE_VERSION  # noqa


# pylint: disable=too-few-public-methods
class PitiviTest(Test):
    """A launcher.Test subclass for our unit tests."""
    def build_arguments(self):
        """Builds subprocess arguments."""
        if GST_VALIDATE_TESTSUITE_VERSION == "1.12":
            self.add_arguments('-m', 'unittest', self.classname)
        else:
            self.add_arguments('-m', 'unittest', '.'.join(self.classname.split('.')[1:]))


def setup_tests(test_manager, options):
    """Sets up Pitivi unit testsuite."""
    loader = unittest.TestLoader()
    testsuites = loader.discover(CDIR)
    for testsuite in testsuites:
        for _tests in testsuite:

            if isinstance(_tests, unittest.loader._FailedTest):  # pylint: disable=protected-access
                print(_tests._exception)  # pylint: disable=protected-access
                continue
            for test in _tests:
                test_manager.add_test(PitiviTest(
                    sys.executable,
                    'tests.' + test.id(),
                    options, test_manager.reporter,
                    extra_env_variables={'PYTHONPATH': os.path.join(CDIR, '..')}))

    return True
