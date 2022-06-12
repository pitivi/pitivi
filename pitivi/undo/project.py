# -*- coding: utf-8 -*-
# Pitivi video editor
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Logic for undo/redo project actions."""
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst

from pitivi.undo.base import Action
from pitivi.undo.base import UndoableAction
from pitivi.undo.markers import MetaContainerObserver
from pitivi.undo.timeline import TimelineObserver


class AssetAddedIntention(UndoableAction):
    """The intention of adding an asset to a project.

    This should be created when the async operation starts.
    See also AssetAddedAction.
    """

    def __init__(self, project, uri):
        UndoableAction.__init__(self)
        self.project = project
        self.uri = uri
        self.asset = None
        self.project.connect("asset-added", self._asset_added_cb)

    def _asset_added_cb(self, project, asset):
        if asset.get_id() == self.uri:
            self.asset = asset
            self.project.disconnect_by_func(self._asset_added_cb)

    def undo(self):
        # The asset might be missing if removed before it's added
        if self.asset:
            self.project.remove_asset(self.asset)

    def do(self):
        if self.asset:
            self.project.add_asset(self.asset)


class AssetAddedAction(Action):
    """The adding of an asset to a project.

    This should be created when the asset has been added.
    See also AssetAddedIntention.
    """

    def __init__(self, asset):
        Action.__init__(self)
        self.asset = asset

    def as_scenario_action(self):
        st = Gst.Structure.new_empty("add-asset")
        st.set_value("id", self.asset.get_id())
        type_string = GObject.type_name(self.asset.get_extractable_type())
        st.set_value("type", type_string)
        return st


class AssetRemovedAction(UndoableAction):
    """The removal of an asset from a project."""

    def __init__(self, project, asset):
        UndoableAction.__init__(self)
        self.project = project
        self.asset = asset

    def undo(self):
        self.project.add_asset(self.asset)

    def do(self):
        self.project.remove_asset(self.asset)

    def as_scenario_action(self):
        st = Gst.Structure.new_empty("remove-asset")
        st.set_value("id", self.asset.get_id())
        type_string = GObject.type_name(self.asset.get_extractable_type())
        st.set_value("type", type_string)
        return st


class AssetProxiedIntention(UndoableAction):
    """The intention of proxying an asset.

    Attributes:
        asset (GES.Asset): The original asset to be proxied.
        proxy_manager (pitivi.utils.proxy.ProxyManager): The manager
            controlling the proxy generation.
    """

    def __init__(self, asset, project, proxy_manager):
        UndoableAction.__init__(self)
        self.asset = asset
        self.project = project
        self.proxy_manager = proxy_manager

    def do(self):
        self.asset.force_proxying = True
        self.proxy_manager.add_job(self.asset)

    def undo(self):
        self.proxy_manager.cancel_job(self.asset)
        proxy = self.asset.props.proxy
        self.asset.set_proxy(None)
        if proxy:
            self.project.remove_asset(proxy)


class ProjectObserver(MetaContainerObserver):
    """Monitors a project instance and reports UndoableActions.

    Args:
        project (Project): The project to be monitored.
    """

    def __init__(self, project, action_log):
        MetaContainerObserver.__init__(self, project, action_log)
        project.connect("asset-added", self._asset_added_cb)
        project.connect("asset-removed", self._asset_removed_cb)
        assets = project.list_assets(GES.Extractable)
        for asset in assets:
            MetaContainerObserver.__init__(self, asset, action_log)
        self.timeline_observer = TimelineObserver(project.ges_timeline,
                                                  action_log)

    def _asset_added_cb(self, unused_project, asset):
        if not isinstance(asset, GES.UriClipAsset):
            return
        MetaContainerObserver.__init__(self, asset, self.action_log)
        action = AssetAddedAction(asset)
        self.action_log.push(action)

    def _asset_removed_cb(self, project, asset):
        if not isinstance(asset, GES.UriClipAsset):
            return
        action = AssetRemovedAction(project, asset)
        self.action_log.push(action)
