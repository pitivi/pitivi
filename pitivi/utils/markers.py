# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2021, Piotr Brzeziński <thewildtreee@gmail.com>
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
from gettext import gettext as _
from typing import List
from typing import Optional
from typing import Tuple

from gi.repository import GES
from gi.repository import GObject

from pitivi.settings import GlobalSettings
from pitivi.timeline.markers import MarkersBox

# FIXME: Remove this once we depend on GES 1.20
GES_MARKERS_SNAPPABLE = hasattr(GES.MarkerList.new().props, "flags")

DEFAULT_LIST_KEY = "user_markers"
NAMES_DICT = {
    # Translators: The list of markers created by the user.
    DEFAULT_LIST_KEY: _("User markers"),
    # Translators: The list of markers representing detected audio beats.
    "beat_markers": _("Beats"),
}


class MarkerListManager(GObject.Object):
    """An abstraction layer between UI components and individual GESSources's marker lists.

    Attaches to a single GESSource, initialising a default marker list and tracking the
    addition / removal of any other ones. Keeps track of the currently active list, which
    is shown to the user if a MarkersBox has been attached via set_markers_box().
    """

    __gsignals__ = {
        # Emitted when a list is added or removed.
        "lists-modified": (GObject.SignalFlags.RUN_LAST, None, ()),
        # Emitted when the current list changes, along with its metadata key.
        "current-list-changed": (GObject.SignalFlags.RUN_LAST, None, (str,))
    }

    def __init__(self, settings: GlobalSettings, ges_source: GES.Source):
        GObject.Object.__init__(self)
        self._ges_source: Optional[GES.Source] = ges_source
        self._settings: GlobalSettings = settings
        self._box: Optional[MarkersBox] = None
        self._current_key: Optional[str] = None
        self.__ensure_default_list_exists()
        self._load_previous_or_default()
        self._set_default_snappability()

    def set_markers_box(self, markers_box: Optional[MarkersBox]):
        """Sets the MarkersBox used to display contents of the current marker list."""
        if self._box == markers_box:
            return

        if markers_box and self._ges_source != markers_box.ges_elem:
            raise ValueError("Marker box has to be attached to the same GESSource.")

        self._box = markers_box
        if not self._box:
            return

        self._box.markers_container = self.current_list

    def get_all_keys(self) -> List[str]:
        """Returns a list of metadata keys under which a marker list can be found."""
        list_keys = []
        self._ges_source.foreach(MarkerListManager.__clip_meta_foreach_func, list_keys)
        return list_keys

    def get_all_keys_with_names(self) -> List[Tuple[str, str]]:
        """Returns a list of list keys along with their human-readable names.

        This exists for ease of use with the MarkerProperties component.
        """
        list_keys = self.get_all_keys()
        # If no name is found just display the key directly.
        return [(key, NAMES_DICT.get(key, key)) for key in list_keys]

    def get_all_lists(self) -> List[GES.MarkerList]:
        """Returns a list of all existing marker lists."""
        list_keys = self.get_all_keys()
        return [self._ges_source.get_marker_list(key) for key in list_keys]

    def list_exists(self, list_key: str) -> bool:
        """Returns whether a list under the given metadata key exists."""
        return list_key in self.get_all_keys()

    def add_list(self, key: str, marker_timestamps: Optional[List[int]] = None) -> GES.MarkerList:
        """Creates an empty marker list and saves it under the given key.

        The key cannot be empty, can't contain spaces, and another list cannot
        already exist under the given key.
        A list of timestamps can be provided to automatically add corresponding
        markers to the newly created list.

        Emits the "lists-modified" signal after the list is successfully added.
        """
        if not key:
            raise ValueError("You must provide a key for the list.")
        if self._ges_source.get_marker_list(key):
            raise ValueError("A list already exists under the given key.")
        if " " in key:
            raise ValueError("List key cannot contain a space character.")

        marker_list = GES.MarkerList.new()

        if GES_MARKERS_SNAPPABLE and self._settings.markersSnappableByDefault:
            marker_list.props.flags |= GES.MarkerFlags.SNAPPABLE

        if marker_timestamps:
            for timestamp in marker_timestamps:
                marker_list.add(timestamp)

        self._ges_source.set_marker_list(key, marker_list)
        self.emit("lists-modified")
        return marker_list

    def remove_list(self, key: str):
        """Removes the marker list found under the given key.

        If the list being removed is currently active, the default list
        will be set as active instead.

        Note: the default "user_markers" cannot be removed.
        """
        if not key:
            raise ValueError("You must provide a key for the list.")

        if key == DEFAULT_LIST_KEY:
            raise ValueError("Cannot remove the default marker list.")

        if key == self.current_list_key:
            self._load_default()

        self._ges_source.set_meta(key, None)
        self.emit("lists-modified")

    @property
    def current_list_key(self) -> Optional[str]:
        """Returns the metadata key under which the current list can be found."""
        return self._current_key

    @current_list_key.setter
    def current_list_key(self, list_key: str):
        """Sets the marker list found under the given key as the currently active one.

        If no list should be active, an empty string needs to be given as the key.
        """
        if list_key is None:
            raise ValueError("No metadata key has been provided.")

        if self.current_list_key == list_key:
            return

        # Don't retrieve the list if the key is an empty string.
        new_list = None
        if list_key:
            new_list = self._ges_source.get_marker_list(list_key)
            if not new_list:
                raise ValueError("Invalid metadata key has been provided.")

        # Turn snappability off for lists going inactive.
        # The was_snappable value is not being serialized, thus
        # after reloading it will be set to the default user-preferred value.
        if self.current_list:
            self.current_list.was_snappable = self.snappable
            self.snappable = False

        # Set the new list as active and restore its snappable state if it's not None.
        self._current_key = list_key

        if new_list and hasattr(new_list, "was_snappable"):
            self.snappable = new_list.was_snappable
        if self._box:
            self._box.markers_container = new_list

        # This lets us preserve the current list between sessions.
        self._ges_source.set_string("last_chosen_list", list_key)
        self.emit("current-list-changed", self.current_list_key)

    @property
    def current_list(self) -> Optional[GES.MarkerList]:
        """Returns the currently active marker list."""
        if self.current_list_key is None:
            return None

        return self._ges_source.get_marker_list(self.current_list_key)

    @property
    def snappable(self) -> bool:
        """Returns whether the current list is considered a snapping target."""
        if not GES_MARKERS_SNAPPABLE:
            return False

        if not self.current_list:
            return False

        return self.current_list.props.flags & GES.MarkerFlags.SNAPPABLE

    @snappable.setter
    def snappable(self, snappable: bool):
        """Sets the snappable flag of the current list to a given value."""
        if not GES_MARKERS_SNAPPABLE:
            return

        if not self.current_list:
            return

        if self.snappable == snappable:
            return

        if snappable:
            self.current_list.props.flags |= GES.MarkerFlags.SNAPPABLE
        else:
            self.current_list.props.flags &= ~GES.MarkerFlags.SNAPPABLE

    def _load_previous_or_default(self):
        last_list_key = self._ges_source.get_string("last_chosen_list")

        # The default list is guaranteed to exist at this point.
        list_key = DEFAULT_LIST_KEY if last_list_key is None else last_list_key
        self.current_list_key = list_key

    def _load_default(self):
        self.current_list_key = DEFAULT_LIST_KEY

    def _set_default_snappability(self):
        """Sets user-chosen snappability state for all lists except for the active one.

        This is assumed to be only called once, after the default / previously chosen
        list has been loaded up.
        """
        snappable_by_default = self._settings.markersSnappableByDefault
        all_lists = self.get_all_lists()

        for marker_list in all_lists:
            # Ignore the active list - its flags were loaded from the project file.
            if marker_list == self.current_list:
                continue

            marker_list.was_snappable = snappable_by_default

    def __ensure_default_list_exists(self):
        if self._ges_source.get_marker_list(DEFAULT_LIST_KEY):
            return

        self.add_list(DEFAULT_LIST_KEY)

    @staticmethod
    def __clip_meta_foreach_func(container, key, value, keys):
        if isinstance(value, GES.MarkerList):
            keys.append(key)
