# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Lubosz Sarnecki <lubosz.sarnecki@collabora.co.uk>
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
"""Video viewer overlays."""
import numpy
from gi.repository import GES
from gi.repository import Gtk

from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import SELECT


class Overlay(Gtk.DrawingArea, Loggable):
    """Abstract class for viewer overlays."""

    def __init__(self, stack, source):
        Gtk.DrawingArea.__init__(self)
        Loggable.__init__(self)
        self._source = source
        self.click_source_position = None
        self.stack = stack

        project = stack.app.project_manager.current_project
        project.connect("video-size-changed", self._canvas_size_changed_cb)
        self.project_size = numpy.array([project.videowidth,
                                         project.videoheight])

        self._source.selected.connect("selected-changed", self.__source_selected_changed_cb)

    def _canvas_size_changed_cb(self, project):
        project = self.stack.app.project_manager.current_project
        self.project_size = numpy.array([project.videowidth,
                                         project.videoheight])

    def _is_hovered(self):
        return self.stack.hovered_overlay == self

    def _is_selected(self):
        return self.stack.selected_overlay == self

    def _select(self):
        self.stack.selected_overlay = self
        ges_clip = self._source.get_parent()
        self.stack.app.gui.editor.timeline_ui.timeline.selection.set_selection([ges_clip], SELECT)

        if not isinstance(self._source, (GES.TitleSource, GES.VideoUriSource, GES.VideoTestSource)):
            self.warning("Unknown clip type: %s", self._source)
            return

        self.stack.app.gui.editor.context_tabs.set_current_page(0)

    def __source_selected_changed_cb(self, unused_source, selected):
        if not selected and self._is_selected():
            self._deselect()

    def _deselect(self):
        self.stack.selected_overlay = None
        self.queue_draw()

    def _hover(self):
        self.stack.hovered_overlay = self

    def unhover(self):
        """Marks `self` as not over anymore."""
        self.stack.hovered_overlay = None
        self.queue_draw()

    def _commit(self):
        self.stack.app.project_manager.current_project.pipeline.commit_timeline()
