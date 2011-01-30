"""Dialog box to quickstart Pitivi"""

import os
import gtk
import webbrowser

from pitivi.configure import LIBDIR
from projectsettings import ProjectSettingsDialog
from pitivi.configure import APPMANUALURL

from urllib import unquote

class StartUpWizard(object):
    """A Wizard displaying recent projects and allowing the user to either:

    load one, skip,see the quick start manual or

    configure a new project with the settings dialog.

    """

    def __init__(self, app):
        if 'pitivi.exe' in __file__.lower():
            glade_dir = LIBDIR
        else:
            glade_dir = os.path.dirname(os.path.abspath(__file__))
        self.app = app
        self.builder = gtk.Builder()
        gladefile = os.path.join(glade_dir, "startupwizard.glade")
        self.builder.add_from_file(gladefile)
        self.builder.connect_signals(self)

        chooser = self.builder.get_object("recentchooser2")
        # FIXME: gtk creates a combo box with only one item, but there is no
        # simple way to hide it.
        filtre = gtk.RecentFilter()
        filtre.set_name("Projects")
        filtre.add_pattern("*.xptv")
        chooser.add_filter(filtre)

    def _newProjectCb(self, unused_button4):
        self.quit()
        self.app.gui.showProjectSettingsDialog()

    def _loadCb(self, unused_button3):
        self.data = unquote(self.data)
        self.app.projectManager.loadProject(self.data)

    def _onBrowseButtonClickedCb(self, unused_button6):
        self.app.gui.openProject()

    def _getFileNameCb(self, chooser):
        self.data = chooser.get_current_uri()
        return self.data

    def _quick_start_manual(self, unused_button5):
        webbrowser.open(APPMANUALURL)

    def _quitWizardCb(self,unused_button2):
        self.quit()

    def quit(self):
        self.builder.get_object("window1").destroy()
