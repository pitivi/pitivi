# PiTiVi , Non-linear video editor
#
#       ui/mainwindow.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os
import gobject
import gtk

from timeline import TimelineWidget
from sourcefactories import SourceFactoriesWidget
from viewer import PitiviViewer
from projectsettings import ProjectSettingsDialog

PITIVI_VERSION = "0.1.9"

class PitiviMainWindow(gtk.Window):
    """
    Pitivi's main window
    """

    def __init__(self, pitivi):
        """ initialize with the Pitivi object """
        self.pitivi = pitivi
        gtk.Window.__init__(self)
        self.maximize()
        self._set_actions()
        self._create_gui()
        self.pitivi.connect("new-project", self._new_project_cb)
        self.pitivi.connect("closing-project", self._closing_project_cb)
        self.pitivi.connect("not-project", self._not_project_cb)
        self.show_all()

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def _set_actions(self):
        """ sets up the GtkActions """
        self.actions = [("NewProject", gtk.STOCK_NEW, "_New Project", None, "Create a new project", self.new_project_cb),
                        ("OpenProject", gtk.STOCK_OPEN, "_Open Project", None, "Opens an existing project", self.open_project_cb),
                        ("SaveProject", gtk.STOCK_SAVE, "_Save Project", None, "Save the current project", self.save_project_cb),
                        ("SaveProjectAs", gtk.STOCK_SAVE_AS, "Save Project As...", None, "Save the current project", self.save_project_as_cb),
                        ("ProjectSettings", gtk.STOCK_PROPERTIES, "Project Settings", None, "Edit the project settings", self.project_settings_cb),
                        ("Quit", gtk.STOCK_QUIT, "_Quit PiTiVi", None, "Quit PiTiVi", self.quit_cb),
                        ("About", gtk.STOCK_ABOUT, "About PiTiVi", None, "Information about PiTiVi", self.about_cb),
                        ("File", None, "_File"),
                        ("Help", None, "_Help")]
        self.actiongroup = gtk.ActionGroup("mainwindow")
        self.actiongroup.add_actions (self.actions)
        # deactivating non-functional actions
        for action in self.actiongroup.list_actions():
            if action.get_name() in ["ProjectSettings", "Quit", "File", "Help", "About"]:
                action.set_sensitive(True)
            else:
                action.set_sensitive(False)
        self.uimanager = gtk.UIManager()
        self.add_accel_group(self.uimanager.get_accel_group())
        self.uimanager.insert_action_group(self.actiongroup, 0)
        self.uimanager.add_ui_from_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "actions.xml"))

    def _create_gui(self):
        """ Create the graphical interface """
        self.set_title("PiTiVi v%s" % PITIVI_VERSION)
        self.set_geometry_hints(min_width=400, min_height=300)

        self.connect("destroy", self.destroy)

        vbox = gtk.VBox(False, 5)
        self.add(vbox)

        self.menu = self.uimanager.get_widget("/MainMenuBar")
        vbox.pack_start(self.menu, expand=False)

        self.toolbar = self.uimanager.get_widget("/MainToolBar")
        self.toolbar.set_style(gtk.TOOLBAR_ICONS)
        vbox.pack_start(self.toolbar, expand=False)
        
        vpaned = gtk.VPaned()
        vbox.pack_start(vpaned)
        
        self.timeline = TimelineWidget(self.pitivi)
        timelineframe = gtk.Frame()
        timelineframe.add(self.timeline)
        vpaned.pack2(timelineframe, resize=False, shrink=False)
        
        hpaned = gtk.HPaned()
        vpaned.pack1(hpaned, resize=True, shrink=False)

        # source-and-effects list
        self.sourcefactories = SourceFactoriesWidget(self.pitivi)

        # Viewer
        self.viewer = PitiviViewer(self.pitivi)
        viewerframe = gtk.Frame()
        viewerframe.add(self.viewer)

        hpaned.pack1(self.sourcefactories, resize=True, shrink=False)
        hpaned.pack2(viewerframe, resize=False, shrink=False)

    def new_project_cb(self, action):
        print "new project"
        self.pitivi.new_blank_project()

    def open_project_cb(self, action):
        print "open project"

    def save_project_cb(self, action):
        print "save project"

    def save_project_as_cb(self, action):
        print "save project as"

    def project_settings_cb(self, action):
        print "project settings"
        l = ProjectSettingsDialog(self, self.pitivi.current)
        l.show()

    def quit_cb(self, action):
        print "quit"
        gtk.main_quit()

    def about_cb(self, action):
        print "About..."
	abt = gtk.AboutDialog()
	abt.set_name("PiTiVi")
	abt.set_version("v%s" % PITIVI_VERSION)
	abt.set_website("http://www.pitivi.org/")
	authors = ["Edward Hervey" ]
	abt.set_authors(authors)
	abt.set_license("GNU Lesser Public License\nSee http://www.gnu.org/copyleft/lesser.html for more details")
	abt.show()

    def _new_project_cb(self, pitivi, project):
        print "Starting up a new project", project

    def _closing_project_cb(self, pitivi, project):
        print "Project", project, "is being closed"
        # Return True if we accept the project being close
        # if we want to save it before it being closed, we must
        #   do so

        # For the time being we always accept it being closed
        return True

    def _not_project_cb(self, pitivi, uri):
        print uri, "is not a project file !"

        
gobject.type_register(PitiviMainWindow)
