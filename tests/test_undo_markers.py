# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Millan Castro <m.castrovilarino@gmail.com>
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
"""Tests for the undo.markers module."""
import tempfile

from gi.repository import Gst

from tests import common
from tests.test_undo_timeline import BaseTestUndoTimeline


class TestMarkers(BaseTestUndoTimeline):
    """Tests for the various classes."""

    def test_marker_added(self):
        """Checks marker addition."""
        self.setup_timeline_container()
        markers = self.timeline.get_marker_list("markers")

        with self.action_log.started("Added marker"):
            marker1 = markers.add(10)
        self.assert_markers(markers, [(10, None)])

        with self.action_log.started("new comment"):
            marker1.set_string("comment", "comment 1")
        self.assert_markers(markers, [(10, "comment 1")])

        for _ in range(4):
            self.action_log.undo()
            self.assert_markers(markers, [(10, None)])

            self.action_log.undo()
            self.assert_markers(markers, [])

            self.action_log.redo()
            self.assert_markers(markers, [(10, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(10, "comment 1")])

        with self.action_log.started("Added marker"):
            marker2 = markers.add(20)
        self.assert_markers(markers, [(10, "comment 1"), (20, None)])

        with self.action_log.started("new comment"):
            marker2.set_string("comment", "comment 2")
        self.assert_markers(markers, [(10, "comment 1"), (20, "comment 2")])

        for _ in range(4):
            self.action_log.undo()
            self.action_log.undo()
            self.action_log.undo()
            self.action_log.undo()
            self.assert_markers(markers, [])

            self.action_log.redo()
            self.assert_markers(markers, [(10, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(10, "comment 1")])

            self.action_log.redo()
            self.assert_markers(markers, [(10, "comment 1"), (20, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(10, "comment 1"), (20, "comment 2")])

    def test_marker_removed(self):
        """Checks marker removal."""
        self.setup_timeline_container()
        markers = self.timeline.get_marker_list("markers")
        marker1 = markers.add(10)
        marker2 = markers.add(20)

        with self.action_log.started("Removed marker"):
            markers.remove(marker1)
        self.assert_markers(markers, [(20, None)])

        with self.action_log.started("Removed marker"):
            markers.remove(marker2)
        self.assert_markers(markers, [])

        for _ in range(4):
            self.action_log.undo()
            self.assert_markers(markers, [(20, None)])

            self.action_log.undo()
            self.assert_markers(markers, [(10, None), (20, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(20, None)])

            self.action_log.redo()
            self.assert_markers(markers, [])

    def test_marker_moved(self):
        """Checks marker moving."""
        self.setup_timeline_container()
        markers = self.timeline.get_marker_list("markers")
        marker1 = markers.add(10)
        markers.add(20)

        with self.action_log.started("Move marker"):
            markers.move(marker1, 40)
            markers.move(marker1, 30)

        stack, = self.action_log.undo_stacks
        self.assertEqual(len(stack.done_actions), 1, stack.done_actions)

        self.assert_markers(markers, [(20, None), (30, None)])

        for _ in range(4):
            self.action_log.undo()
            self.assert_markers(markers, [(10, None), (20, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(20, None), (30, None)])

    def test_marker_comment(self):
        """Checks marker comment."""
        self.setup_timeline_container()

        markers = self.timeline.get_marker_list("markers")

        with self.action_log.started("Added marker"):
            marker1 = markers.add(10)
        with self.action_log.started("Added marker"):
            marker2 = markers.add(20)

        self.assert_markers(markers, [(10, None), (20, None)])

        with self.action_log.started("new comment"):
            marker1.set_string("comment", "comment 1")
        with self.action_log.started("new comment"):
            marker2.set_string("comment", "comment 2")

        self.assert_markers(markers, [(10, "comment 1"), (20, "comment 2")])

        for _ in range(4):
            self.action_log.undo()
            self.assert_markers(markers, [(10, "comment 1"), (20, None)])

            self.action_log.undo()
            self.assert_markers(markers, [(10, None), (20, None)])

            self.action_log.undo()
            self.assert_markers(markers, [(10, None)])

            self.action_log.undo()
            self.assert_markers(markers, [])

            self.action_log.redo()
            self.assert_markers(markers, [(10, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(10, None), (20, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(10, "comment 1"), (20, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(10, "comment 1"), (20, "comment 2")])

    def test_marker_load_project(self):
        """Checks marker addition."""
        # TODO: When there is nothing connected to closing-project,
        # the default reply is "False", which means "abort saving". It should mean
        # "OK" to get rid off the handler.  The meaning of the default (False)
        # must be changed
        def closing(unused_manager, unused_project):
            return True

        def loaded_cb(project, timeline):
            mainloop.quit()

        markers = self.timeline.get_marker_list("markers")
        markers.add(10)
        markers.add(20)
        self.assert_markers(markers, [(10, None), (20, None)])

        project_uri = Gst.filename_to_uri(tempfile.NamedTemporaryFile().name)
        self.app.project_manager.saveProject(project_uri)
        self.app.project_manager.connect("closing-project", closing)

        self.app.project_manager.closeRunningProject()
        project = self.app.project_manager.new_blank_project()
        markers = project.ges_timeline.get_marker_list("markers")
        self.assert_markers(markers, [])

        self.app.project_manager.closeRunningProject()
        project = self.app.project_manager.load_project(project_uri)
        project.connect("loaded", loaded_cb)
        mainloop = common.create_main_loop()
        mainloop.run()
        self.action_log = self.app.action_log

        markers = project.ges_timeline.get_marker_list("markers")
        self.assert_markers(markers, [(10, None), (20, None)])

        ges_markers = markers.get_markers()
        marker1, marker2 = ges_markers

        with self.action_log.started("new comment"):
            marker1.set_string("comment", "comment 1")
        self.assert_markers(markers, [(10, "comment 1"), (20, None)])

        with self.action_log.started("new comment"):
            marker2.set_string("comment", "comment 2")
        self.assert_markers(markers, [(10, "comment 1"), (20, "comment 2")])

        for _ in range(4):
            self.action_log.undo()
            self.assert_markers(markers, [(10, "comment 1"), (20, None)])

            self.action_log.undo()
            self.assert_markers(markers, [(10, None), (20, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(10, "comment 1"), (20, None)])

            self.action_log.redo()
            self.assert_markers(markers, [(10, "comment 1"), (20, "comment 2")])
