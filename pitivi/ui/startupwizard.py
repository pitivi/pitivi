# PiTiVi , Non-linear video editor
#
#       pitivi/ui/startupwizard.py
#
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
import gtk

from gettext import gettext as _

from pitivi.configure import get_ui_dir
from pitivi.ui.depsmanager import DepsManager
from pitivi.check import soft_deps
from pitivi.utils.misc import show_user_manual

from urllib import unquote


class StartUpWizard(object):
    """A Wizard displaying recent projects.

    Allows the user to:
    - create a new project and open the settings dialog (Create button),
    - create a new project with the default settings (dialog close or ESC),
    - load a recently opened project (double click recent chooser),
    - load a project (Browse button),
    - see the quick start manual (User Manual button).
    """

    def __init__(self, app):
        self.app = app
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(), "startupwizard.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("window1")

        self.recent_chooser = self.builder.get_object("recentchooser2")
        # FIXME: gtk creates a combo box with only one item, but there is no
        # simple way to hide it.
        filter = gtk.RecentFilter()
        filter.set_name(_("Projects"))
        filter.add_pattern("*.xptv")
        self.recent_chooser.add_filter(filter)

        if not soft_deps:
            self.builder.get_object("missing_deps_button").hide()

        self.app.projectManager.connect("new-project-failed",
                self._projectFailedCb)
        self.app.projectManager.connect("new-project-loaded",
                self._projectLoadedCb)
        self.app.projectManager.connect("new-project-loading",
                self._projectLoadingCb)

    def _newProjectCb(self, unused_button):
        """Handle a click on the New (Project) button."""
        self.app.projectManager.newBlankProject()
        self.app.gui.showProjectSettingsDialog()

    def _loadCb(self, unused_recent_chooser):
        """Handle a double-click on the recent chooser."""
        self.app.projectManager.loadProject(self._getFileName())

    def _getFileName(self):
        """Get the URI of the project selected in the recent chooser."""
        uri = self.recent_chooser.get_current_uri()[7:]
        return unquote(uri)

    def _keyPressCb(self, widget, event):
        """Handle a key press event on the dialog."""
        if event.keyval == gtk.keysyms.Escape:
            # The user pressed "Esc".
            self.app.projectManager.newBlankProject()

    def _onBrowseButtonClickedCb(self, unused_button6):
        """Handle a click on the Browse button."""
        self.app.gui.openProject()

    def _onMissingDepsButtonClickedCb(self, unused_button):
        self.hide()
        self.dep_manager = DepsManager(self.app)

    def _userManualCb(self, unused_button):
        """Handle a click on the Help button."""
        show_user_manual()

    def _deleteCb(self, unused_widget, event):
        """Handle a click on the X button of the dialog."""
        self.app.projectManager.newBlankProject()

    def show(self):
        self.window.set_transient_for(self.app.gui)
        self.window.show()
        self.window.grab_focus()

    def hide(self):
        self.window.hide()

    def _projectFailedCb(self, unused_project_manager, unused_uri,
            unused_exception):
        """Handle the failure of a project open operation."""
        self.show()

    def _projectLoadedCb(self, unused_project_manager, project):
        """Handle the success of a project load operation.

        All the create or load project usage scenarios must generate
        a new-project-loaded signal from self.app.projectManager!
        """
        if project.disconnect:
            return
        self.app.projectManager.disconnect_by_function(self._projectFailedCb)
        self.app.projectManager.disconnect_by_function(self._projectLoadedCb)
        self.app.projectManager.disconnect_by_function(self._projectLoadingCb)

    def _projectLoadingCb(self, unused_project_manager, unused_project):
        """Handle the start of a project load operation."""
        self.hide()
