# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Caleb Marcoux <caleb.marcoux@gmail.com> (primary contact),
# Copyright (c) 2020, Abby Brooks <abigail.brooks@huskers.unl.edu>,
# Copyright (c) 2020, Won Choi <won.choi@huskers.unl.edu>
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
"""Tests for the pitivi.editorstate module."""
# pylint: disable=consider-using-with,protected-access
import tempfile
from unittest import mock

from pitivi.editorstate import EditorState
from tests import common


class TestEditorState(common.TestCase):
    """Tests the EditorState class."""

    def test_save_load(self):
        values = {
            "playhead-position": 5000000000,
            "zoom-level": 50,
            "scroll": 50.0,
            "selection": []
        }
        saved = EditorState(mock.Mock())
        saved.conf_file_path = tempfile.NamedTemporaryFile().name
        for key, value in values.items():
            saved.set_value(key, value)
        saved.save_editor_state()

        loaded = EditorState(mock.Mock())
        loaded.conf_file_path = saved.conf_file_path
        loaded.load_editor_state()
        for key, value in values.items():
            self.assertEqual(loaded.get_value(key), value)
