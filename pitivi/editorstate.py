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
import json
import os

from gi.repository import GLib

from pitivi.settings import xdg_config_home
from pitivi.utils.loggable import Loggable


class EditorState(Loggable):
    """Pitivi editor state.

    Loads the editor state for the current project from the editor state folder.

    Widgets call get_value when they are ready to restore their state.
    """

    def __init__(self, project_manager):
        Loggable.__init__(self)

        self.project_manager = project_manager
        self.conf_folder_path = xdg_config_home("editor_state")

        self.project = None
        self.conf_file_path = None
        self._editor_state = {}
        self.__state_saving_handle = 0

    def get_value(self, key):
        """Get a value from the loaded editor state."""
        return self._editor_state.get(key)

    def set_value(self, key, value):
        """Sets the given value in the EditorState."""
        self._editor_state[key] = value
        self.prepare_to_save()

    def prepare_to_save(self):
        if self.__state_saving_handle:
            GLib.source_remove(self.__state_saving_handle)
        self.__state_saving_handle = GLib.timeout_add(500, self._state_not_changing_anymore_cb, priority=GLib.PRIORITY_LOW)

    def _state_not_changing_anymore_cb(self):
        self.__state_saving_handle = 0
        self.save_editor_state()

    def set_project(self, project):
        self.project = project
        self.conf_file_path = os.path.join(self.conf_folder_path, self.project.get_project_id() + ".conf")
        self.load_editor_state()

    def save_editor_state(self):
        """Save the current editor state to the editor state file."""
        self.log("Editor state saving.")

        if self.conf_file_path:
            with open(self.conf_file_path, "w", encoding="UTF-8") as file:
                json.dump(self._editor_state, file)

    def load_editor_state(self):
        """Load an editor state file into the current editor state."""
        self.log("Loading state from file: %s", self.conf_file_path)
        try:
            with open(self.conf_file_path, "r", encoding="UTF-8") as file:
                try:
                    self._editor_state = json.load(file)
                except (json.decoder.JSONDecodeError, ValueError) as e:
                    self.warning("Editor state could not be read: %s", e)
        except FileNotFoundError:
            return
