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
import webbrowser

from pitivi.configure import get_ui_dir
from pitivi.configure import APPMANUALURL

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
        self.window.connect("key-press-event", self._keypressCb)

        self.recent_chooser = self.builder.get_object("recentchooser2")
        # FIXME: gtk creates a combo box with only one item, but there is no
        # simple way to hide it.
        filter = gtk.RecentFilter()
        filter.set_name("Projects")
        filter.add_pattern("*.xptv")
        self.recent_chooser.add_filter(filter)

    def _newProjectCb(self, unused_button):
        self.hide()
        # A new project has already been created, so only display
        # the Project Settings dialog.
        self.app.gui.showProjectSettingsDialog()

    def _loadCb(self, unused_recent_chooser):
        self.app.projectManager.loadProject(self._getFileName())

    def _getFileName(self):
        """Get the URI of the project selected in the recent chooser."""
        uri = self.recent_chooser.get_current_uri()
        return unquote(uri)

    def _keypressCb(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:  # If the user presses "Esc"
            self.hide()

    def _onBrowseButtonClickedCb(self, unused_button6):
        self.app.gui.openProject()

    def _quick_start_manual(self, unused_button5):
        webbrowser.open(APPMANUALURL)

    def _dialogCloseCb(self, unused_widget):
        self.hide()

    def show(self):
        self.window.set_transient_for(self.app.gui)
        self.window.show()
        self.window.grab_focus()

    def hide(self):
        self.window.hide()
