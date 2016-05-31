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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
from pitivi import check
from tests import common


class FakeDependency(check.Dependency):
    import_result = None

    def _try_importing_component(self):
        return self.import_result


class TestDependency(common.TestCase):

    def testBoolEvaluation(self):
        dependency = FakeDependency(
            modulename="module1", version_required_string=None)
        self.assertFalse(dependency)
        self.assertFalse(dependency.satisfied)

        dependency.check()
        self.assertFalse(dependency)
        self.assertFalse(dependency.satisfied)

        dependency.import_result = "something"
        dependency.check()
        self.assertTrue(dependency)
        self.assertTrue(dependency.satisfied)
