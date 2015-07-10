# -*- coding: utf-8 -*-
#
# Copyright (c) 2013, Alex Băluț <alexandru.balut@gmail.com>
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

import mock
from unittest import TestCase

from gi.repository import GES

from tests import common

from pitivi.utils.timeline import Selected, Selection, SELECT, SELECT_ADD, \
    UNSELECT


class TestSelected(TestCase):

    def testBoolEvaluation(self):
        selected = Selected()
        self.assertFalse(selected)

        selected.selected = True
        self.assertTrue(selected)

        selected.selected = False
        self.assertFalse(selected)


class TestSelection(TestCase):

    def testBoolEvaluation(self):
        clip1 = mock.MagicMock()
        selection = Selection()
        self.assertFalse(selection)
        selection.setSelection([clip1], SELECT)
        self.assertTrue(selection)
        selection.setSelection([clip1], SELECT_ADD)
        self.assertTrue(selection)
        selection.setSelection([clip1], UNSELECT)
        self.assertFalse(selection)

    def testGetSingleClip(self):
        selection = Selection()
        clip1 = common.createTestClip(GES.UriClip)
        clip2 = common.createTestClip(GES.TitleClip)

        # Selection empty.
        self.assertFalse(selection.getSingleClip(GES.TitleClip))

        # Selection contains only a non-requested-type clip.
        selection.setSelection([clip1], SELECT)
        self.assertFalse(selection.getSingleClip(GES.TitleClip))

        # Selection contains only requested-type clip.
        selection.setSelection([clip2], SELECT)
        self.assertEqual(clip2, selection.getSingleClip(GES.TitleClip))

        # Selection contains more than one clip.
        selection.setSelection([clip1, clip2], SELECT)
        self.assertFalse(selection.getSingleClip(GES.UriClip))
