"""Dialog box to quickstart Pitivi"""

import os
import gtk
import webbrowser

from pitivi.configure import get_ui_dir
from pitivi.configure import APPMANUALURL

from urllib import unquote


class StartUpWizard(object):
    """A Wizard displaying recent projects and allowing the user to either:

    load one, skip,see the quick start manual or

    configure a new project with the settings dialog.

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
        self.hide()
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
