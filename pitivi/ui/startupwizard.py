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

        chooser = self.builder.get_object("recentchooser2")
        # FIXME: gtk creates a combo box with only one item, but there is no
        # simple way to hide it.
        filtre = gtk.RecentFilter()
        filtre.set_name("Projects")
        filtre.add_pattern("*.xptv")
        chooser.add_filter(filtre)

    def _newProjectCb(self, unused_button4):
        self.hide()
        self.app.gui.showProjectSettingsDialog()

    def _loadCb(self, unused_button3):
        self.data = unquote(self.data)
        self.app.projectManager.loadProject(self.data)

    def _keypressCb(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:  # If the user presses "Esc"
            self.hide()

    def _onBrowseButtonClickedCb(self, unused_button6):
        self.app.gui.openProject()

    def _getFileNameCb(self, chooser):
        self.data = chooser.get_current_uri()
        return self.data

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
