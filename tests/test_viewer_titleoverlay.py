# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2021, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.viewer.title_overlay module."""
# pylint: disable=protected-access,no-self-use,attribute-defined-outside-init
from unittest import mock

from gi.repository import Gdk
from gi.repository import GES

from pitivi.viewer.title_overlay import TitleOverlay
from tests import common


class TitleOverlayTest(common.TestCase):
    """Tests for the TitleOverlay class."""

    def assert_title_source_absolute_position(self, source: GES.TitleSource, expected_x: float, expected_y: float):
        res, val = source.get_child_property("x-absolute")
        self.assertTrue(res)
        self.assertAlmostEqual(val, expected_x)
        res, val = source.get_child_property("y-absolute")
        self.assertTrue(res)
        self.assertAlmostEqual(val, expected_y)

    def test_dragging_creates_an_undoable_operation(self):
        mainloop = common.create_main_loop()

        app = common.create_pitivi()
        app.gui = None
        app.create_main_window()
        app.project_manager.new_blank_project()
        mainloop.run(until_empty=True)
        self.assertDictEqual(app.gui.editor.viewer.overlay_stack._OverlayStack__overlays, {})

        app.gui.editor.clipconfig._title_button.clicked()
        mainloop.run(until_empty=True)

        self.assertEqual(len(app.gui.editor.viewer.overlay_stack._OverlayStack__overlays), 1)
        source = app.gui.editor.clipconfig.title_expander.source
        overlay = app.gui.editor.viewer.overlay_stack._OverlayStack__overlays[source]
        self.assertIsInstance(overlay, TitleOverlay)

        overlay_stack = app.gui.editor.viewer.overlay_stack
        # The overlay of the selected clip's video source should have been
        # selected.
        self.assertIs(overlay_stack.selected_overlay, overlay)

        # Simulate hover so it can be dragged.
        w, h = overlay_stack.window_size
        self.assertIs(overlay_stack.hovered_overlay, None)
        event = mock.Mock(type=Gdk.EventType.MOTION_NOTIFY, x=w / 2, y=h / 2)
        overlay_stack.do_event(event)
        self.assertIs(overlay_stack.hovered_overlay, overlay)

        # Simulate drag&drop.
        event = mock.Mock(type=Gdk.EventType.BUTTON_PRESS, x=w / 2, y=h / 2)
        overlay_stack.do_event(event)
        self.assert_title_source_absolute_position(source, 0.5, 0.5)

        event = mock.Mock(type=Gdk.EventType.MOTION_NOTIFY, x=0, y=0)
        overlay_stack.do_event(event)

        event = mock.Mock(type=Gdk.EventType.BUTTON_RELEASE, x=0, y=0)
        overlay_stack.do_event(event)
        mainloop.run(until_empty=True)
        # These values are weird.
        self.assert_title_source_absolute_position(source, -0.24980483996877437, -0.08686210640608036)

        # Undo movement.
        app.action_log.undo()
        self.assert_title_source_absolute_position(source, 0.5, 0.5)
        # Undo title creation.
        app.action_log.undo()

        app.action_log.redo()
        self.assert_title_source_absolute_position(source, 0.5, 0.5)
        app.action_log.redo()
        self.assert_title_source_absolute_position(source, -0.24980483996877437, -0.08686210640608036)
