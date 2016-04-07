# Pitivi video editor
#
#       pitivi/undo/project.py
#
# Copyright (c) 2012, Thibault Saunier <tsaunier@gnome.org>
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
from gi.repository import GObject
from gi.repository import Gst

from pitivi.undo.undo import UndoableAction


class AssetAddedAction(UndoableAction):

    def __init__(self, project, asset):
        UndoableAction.__init__(self)
        self.project = project
        self.asset = asset

    def undo(self):
        self.project.remove_asset(self.asset)

    def do(self):
        self.project.add_asset(self.asset)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("add-asset")
        st.set_value("id", self.asset.get_id())
        type_string = GObject.type_name(self.asset.get_extractable_type())
        st.set_value("type", type_string)
        return st


class AssetRemovedAction(UndoableAction):

    def __init__(self, project, asset):
        UndoableAction.__init__(self)
        self.project = project
        self.asset = asset

    def undo(self):
        self.project.add_asset(self.asset)

    def do(self):
        self.project.remove_asset(self.asset)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("remove-asset")
        st.set_value("id", self.asset.get_id())
        type_string = GObject.type_name(self.asset.get_extractable_type())
        st.set_value("type", type_string)
        return st


class MetaChangedAction(UndoableAction):

    def __init__(self, meta_container, item, current_value, new_value):
        UndoableAction.__init__(self)
        self.meta_container = meta_container
        self.item = item
        self.old_value = current_value
        self.new_value = new_value

    def do(self):
        self.meta_container.set_meta(self.item, self.new_value)

    def undo(self):
        self.meta_container.set_meta(self.item, self.old_value)


class ProjectObserver():
    """Monitors a project instance and reports UndoableActions.

    Attributes:
        action_log (UndoableActionLog): The action log where to report actions.
    """

    def __init__(self, action_log):
        self.action_log = action_log

    def startObserving(self, project):
        """Starts monitoring the specified Project.

        Args:
            project (Project): The project to be monitored.
        """
        self.metas = {}
        def set_meta(project, item, value):
            self.metas[item] = value
        project.foreach(set_meta)

        project.connect("notify-meta", self._settingsChangedCb)
        project.connect("asset-added", self._assetAddedCb)
        project.connect("asset-removed", self._assetRemovedCb)

    def _settingsChangedCb(self, project, item, value):
        current_value = self.metas.get(item)
        action = MetaChangedAction(project, item, current_value, value)
        self.metas[item] = value
        self.action_log.push(action)

    def _assetAddedCb(self, project, asset):
        action = AssetAddedAction(project, asset)
        self.action_log.push(action)

    def _assetRemovedCb(self, project, asset):
        action = AssetRemovedAction(project, asset)
        self.action_log.push(action)
