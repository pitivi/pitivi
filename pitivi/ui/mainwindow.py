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

"""
Main GTK+ window
"""

import os
import gobject
import gtk
import gst

import pitivi.instance as instance
import pitivi.configure as configure

from timeline import TimelineWidget
from sourcefactories import SourceFactoriesWidget
from viewer import PitiviViewer
from projectsettings import ProjectSettingsDialog
from pitivi.configure import pitivi_version

class PitiviMainWindow(gtk.Window):
    """
    Pitivi's main window
    """

    def __init__(self):
        """ initialize with the Pitivi object """
        gst.log("Creating MainWindow")
        gtk.Window.__init__(self)
        
        self._setActions()
        self._createUi()
        
        instance.PiTiVi.connect("new-project", self._newProjectCb)
        instance.PiTiVi.connect("closing-project", self._closingProjectCb)
        instance.PiTiVi.connect("not-project", self._notProjectCb)
        self.show_all()

    def _setActions(self):
        """ sets up the GtkActions """
        self.actions = [
            ("NewProject", gtk.STOCK_NEW, "_New Project", None, "Create a new project", self._newProjectCb),
            ("OpenProject", gtk.STOCK_OPEN, "_Open Project", None, "Opens an existing project", self._openProjectCb),
            ("SaveProject", gtk.STOCK_SAVE, "_Save Project", None, "Save the current project", self._saveProjectCb),
            ("SaveProjectAs", gtk.STOCK_SAVE_AS, "Save Project As...", None, "Save the current project", self._saveProjectAsCb),
            ("ProjectSettings", gtk.STOCK_PROPERTIES, "Project Settings", None, "Edit the project settings", self._projectSettingsCb),
            ("Quit", gtk.STOCK_QUIT, "_Quit PiTiVi", None, "Quit PiTiVi", self._quitCb),
            ("About", gtk.STOCK_ABOUT, "About PiTiVi", None, "Information about PiTiVi", self._aboutCb),
            ("File", None, "_File"),
            ("Help", None, "_Help")
            ]

        self.actiongroup = gtk.ActionGroup("mainwindow")
        self.actiongroup.add_actions(self.actions)
        
        # deactivating non-functional actions
        # FIXME : reactivate them
        for action in self.actiongroup.list_actions():
            if action.get_name() in ["ProjectSettings", "Quit", "File", "Help", "About"]:
                action.set_sensitive(True)
            else:
                action.set_sensitive(False)
                
        self.uimanager = gtk.UIManager()
        self.add_accel_group(self.uimanager.get_accel_group())
        self.uimanager.insert_action_group(self.actiongroup, 0)
        self.uimanager.add_ui_from_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "actions.xml"))

    def _createUi(self):
        """ Create the graphical interface """
        self.set_title("PiTiVi v%s" % pitivi_version)
        self.set_geometry_hints(min_width=800, min_height=600)

        self.connect("destroy", self._destroyCb)

        vbox = gtk.VBox(False, 5)
        self.add(vbox)

        self.menu = self.uimanager.get_widget("/MainMenuBar")
        vbox.pack_start(self.menu, expand=False)

        self.toolbar = self.uimanager.get_widget("/MainToolBar")
        self.toolbar.set_style(gtk.TOOLBAR_ICONS)
        vbox.pack_start(self.toolbar, expand=False)
        
        vpaned = gtk.VPaned()
        vbox.pack_start(vpaned)
        
        self.timeline = TimelineWidget()
        timelineframe = gtk.Frame()
        timelineframe.add(self.timeline)
        vpaned.pack2(timelineframe, resize=False, shrink=False)
        
        hpaned = gtk.HPaned()
        vpaned.pack1(hpaned, resize=True, shrink=False)

        # source-and-effects list
        self.sourcefactories = SourceFactoriesWidget()

        # Viewer
        self.viewer = PitiviViewer()
        viewerframe = gtk.Frame()
        viewerframe.add(self.viewer)

        # connect viewer's timeline position callback to the timeline widget
        self.viewer.addTimelinePositionCallback(self.timeline.timelinePositionChanged)

        hpaned.pack1(self.sourcefactories, resize=True, shrink=False)
        hpaned.pack2(viewerframe, resize=False, shrink=False)

        #application icon
        self.set_icon_from_file(configure.get_global_pixmap_dir() + "/application-pitivi.png")

    ## UI Callbacks

    def _destroyCb(self, widget, data=None):
        instance.PiTiVi.shutdown()


    ## Toolbar/Menu actions callback
        
    def _newProjectCb(self, action):
        instance.PiTiVi.new_blank_project()

    def _openProjectCb(self, action):
        raise NotImplementedError

    def _saveProjectCb(self, action):
        raise NotImplementedError

    def _saveProjectAsCb(self, action):
        raise NotImplementedError

    def _projectSettingsCb(self, action):
        l = ProjectSettingsDialog(self, instance.PiTiVi.current)
        l.show()

    def _quitCb(self, action):
        instance.PiTiVi.shutdown()

    def _aboutCb(self, action):
	abt = gtk.AboutDialog()
	abt.set_name("PiTiVi")
	abt.set_version("v%s" % pitivi_version)
	abt.set_website("http://www.pitivi.org/")
	authors = ["Edward Hervey <edward@fluendo.com>" ]
	abt.set_authors(authors)
	abt.set_license("GNU Lesser Public License\nSee http://www.gnu.org/copyleft/lesser.html for more details")
        abt.set_icon_from_file(configure.get_global_pixmap_dir() + "/application-pitivi.png")
	abt.show()


    ## PiTiVi main object callbacks

    def _newProjectCb(self, pitivi, project):
        raise NotImplementedError

    def _closingProjectCb(self, pitivi, project):
        # Return True if we accept the project being close
        # if we want to save it before it being closed, we must
        #   do so

        # For the time being we always accept it being closed
        return True

    def _notProjectCb(self, pitivi, uri):
        raise NotImplementedError
    
