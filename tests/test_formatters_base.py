#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       test_formatters_base.py
#
# Copyright (c) 2011, Alex Balut <alexandru.balut@gmail.com>
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

import shutil
import tempfile

from pitivi.formatters.base import Formatter

from common import TestCase


class TestFormatter(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.formatter = Formatter(avalaible_effects=None)

    def testSearchMissingFile(self):
        # The scenario is that a file has been moved from dir1 to dir2.
        dir0 = tempfile.mkdtemp()
        try:
            dir1 = tempfile.mkdtemp(dir=dir0)
            dir2 = tempfile.mkdtemp(dir=dir0)
            unused_file2, file2_path = tempfile.mkstemp(dir=dir2)
            uri2 = 'file://%s' % file2_path
            uri1 = uri2.replace(dir2, dir1)

            self.assertIsNone(self.formatter._searchMissingFile(uri1))

            self.formatter.addMapping('file://%s' % dir1, 'file://%s' % dir2)
            self.assertEqual(uri2, self.formatter._searchMissingFile(uri1))
        finally:
            shutil.rmtree(dir0)
