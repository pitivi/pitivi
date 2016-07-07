# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2010 Mathieu Duponchelle <seeed@laposte.net>
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
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gtk

from pitivi.check import missing_soft_deps
from pitivi.configure import get_ui_dir
from pitivi.dialogs.depsmanager import DepsManager
from pitivi.shortcuts import show_shortcuts
from pitivi.utils.misc import show_user_manual
from pitivi.utils.ui import fix_infobar


class StartUpWizard(object):
    """A Wizard displaying recent projects.

    Allows the user to:
    - create a new project and open the settings dialog (Create button),
    - create a new project with the default settings (dialog close or ESC),
    - load a recently opened project (double click recent chooser),
    - load a project (Browse button),
    - see the quick start manual (User Manual button).
    """

    @staticmethod
    def _userManualCb(unused_button):
        """Handles a click on the Help button."""
        show_user_manual()

    def _cheatsheetCb(self, unused_button):
        """Shows the shortcuts cheatsheet."""
        show_shortcuts(self.app)

    def __init__(self, app):
        self.app = app
        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "startupwizard.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("window1")
        # The line below is supremely important, it will NOT work if set
        # only by the GtkBuilder file. The DIALOG TypeHint allows proper
        # attachment (visually, behaviorally) to MainWindow, and
        # prevents other windows from showing on top too easily.
        self.window.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        self.recent_chooser = self.builder.get_object("recentchooser2")
        # FIXME: gtk creates a combo box with only one item, but there is no
        # simple way to hide it.
        _filter = Gtk.RecentFilter()
        _filter.set_name(_("Projects"))

        for asset in GES.list_assets(GES.Formatter):
            _filter.add_pattern(
                '*.' + asset.get_meta(GES.META_FORMATTER_EXTENSION))

        self.recent_chooser.add_filter(_filter)

        missing_button = self.builder.get_object("missing_deps_button")

        if not missing_soft_deps:
            missing_button.hide()

        vbox = self.builder.get_object("topvbox")
        self.infobar = Gtk.InfoBar()
        fix_infobar(self.infobar)
        vbox.pack_start(self.infobar, True, True, 0)
        if self.app.getLatest():
            self._appVersionInfoReceivedCb(self.app, None)
        else:
            self.app.connect(
                "version-info-received", self._appVersionInfoReceivedCb)

    def _newProjectCb(self, unused_button):
        """Handles a click on the New (Project) button."""
        self.app.project_manager.newBlankProject()

    def _loadCb(self, unused_recent_chooser):
        """Handles choosing a project on the recent chooser.

        This calls the project manager to load the associated URI.
        """
        uri = self.recent_chooser.get_current_uri()
        self.app.project_manager.loadProject(uri)

    def _keyPressCb(self, unused_widget, event):
        """Handles a key press event on the dialog."""
        if event.keyval == Gdk.KEY_Escape:
            # The user pressed "Esc".
            self.app.project_manager.newBlankProject()

    def _onBrowseButtonClickedCb(self, unused_button6):
        """Handles a click on the Browse button."""
        self.app.gui.openProject()

    def _onMissingDepsButtonClickedCb(self, unused_button):
        """Handles a click on the Missing Deps button."""
        DepsManager(self.app, parent_window=self.window)

    def _deleteCb(self, unused_widget, unused_event):
        """Handles a click on the X button of the dialog."""
        self.app.project_manager.newBlankProject()
        return True

    def show(self):
        if self.window.props.visible:
            return
        self.window.set_transient_for(self.app.gui)
        self.window.show()
        project_manager = self.app.project_manager
        project_manager.connect("new-project-loading", self._projectLoadingCb)

    def hide(self):
        if not self.window.props.visible:
            return
        self.window.hide()
        project_manager = self.app.project_manager
        project_manager.disconnect_by_func(self._projectLoadingCb)

    def _projectLoadingCb(self, unused_project_manager, unused_uri):
        """Handles the start of a project load operation."""
        self.hide()

    def _appVersionInfoReceivedCb(self, app, unused_version_information):
        """Handles new version info."""
        if app.isLatest():
            # current version, don't show message
            return

        latest_version = app.getLatest()
        if self.app.settings.lastCurrentVersion != latest_version:
            # new latest version, reset counter
            self.app.settings.lastCurrentVersion = latest_version
            self.app.settings.displayCounter = 0

        if self.app.settings.displayCounter >= 5:
            # current version info already showed 5 times, don't show again
            return

        # increment counter, create infobar and show info
        self.app.settings.displayCounter = self.app.settings.displayCounter + 1
        text = _("Pitivi %s is available." % latest_version)
        label = Gtk.Label(label=text)
        self.infobar.get_content_area().add(label)
        self.infobar.set_message_type(Gtk.MessageType.INFO)
        self.infobar.show_all()
