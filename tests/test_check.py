# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2014, Alex Băluț <alexandru.balut@gmail.com>
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
from unittest import mock

from pitivi.check import Dependency
from tests import common


class TestDependency(common.TestCase):

    def test_bool_evaluation(self):
        dependency = Dependency(
            modulename="module1", version_required=None)
        self.assertFalse(dependency)
        self.assertFalse(dependency.satisfied)

        with mock.patch.object(dependency, "_try_importing_component") as func:
            func.return_value = None
            dependency.check()
            self.assertFalse(dependency)
            self.assertFalse(dependency.satisfied)

        with mock.patch.object(dependency, "_try_importing_component") as func:
            func.return_value = "something"
            dependency.check()
            self.assertTrue(dependency)
            self.assertTrue(dependency.satisfied)
