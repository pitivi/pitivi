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
from pitivi.configure import pitivi_version, APPNAME

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

        self.isFullScreen = False
        self.errorDialogBox = None
        
        instance.PiTiVi.connect("new-project", self._newProjectCb)
        instance.PiTiVi.connect("closing-project", self._closingProjectCb)
        instance.PiTiVi.connect("not-project", self._notProjectCb)
        instance.PiTiVi.playground.connect("error", self._playGroundErrorCb)
        self.show_all()

    def _setActions(self):
        """ sets up the GtkActions """
        self.actions = [
            ("NewProject", gtk.STOCK_NEW, None, None, "Create a new project", self._newProjectCb),
            ("OpenProject", gtk.STOCK_OPEN, None, None, "Opens an existing project", self._openProjectCb),
            ("SaveProject", gtk.STOCK_SAVE, None, None, "Save the current project", self._saveProjectCb),
            ("SaveProjectAs", gtk.STOCK_SAVE_AS, None, None, "Save the current project", self._saveProjectAsCb),
            ("ProjectSettings", gtk.STOCK_PROPERTIES, "Project Settings", None, "Edit the project settings", self._projectSettingsCb),
            ("ImportSources", gtk.STOCK_ADD, "_Import Sources...", None, "Import sources to use", self._importSourcesCb),
            ("Quit", gtk.STOCK_QUIT, None, None, None, self._quitCb),
            ("FullScreen", gtk.STOCK_FULLSCREEN, None, None, "View the main window on the whole screen", self._fullScreenCb),
            ("About", gtk.STOCK_ABOUT, None, None, "Information about %s" % APPNAME, self._aboutCb),
            ("File", None, "_File"),
            ("View", None, "_View"),
            ("Help", None, "_Help")
            ]
        self.toggleactions = [
            ("AdvancedView", None, "Advanced Vie_w", None, "Switch to advanced view", self._advancedViewCb)
            ]

        self.actiongroup = gtk.ActionGroup("mainwindow")
        self.actiongroup.add_actions(self.actions)
        self.actiongroup.add_toggle_actions(self.toggleactions)
        
        # deactivating non-functional actions
        # FIXME : reactivate them
        for action in self.actiongroup.list_actions():
            if action.get_name() in ["ProjectSettings", "Quit", "File", "Help",
                                     "About", "View", "FullScreen", "ImportSources",
                                     "AdvancedView"]:
                action.set_sensitive(True)
            else:
                action.set_sensitive(False)
                
        self.uimanager = gtk.UIManager()
        self.add_accel_group(self.uimanager.get_accel_group())
        self.uimanager.insert_action_group(self.actiongroup, 0)
        self.uimanager.add_ui_from_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "actions.xml"))

        self.connect("key-press-event", self._keyPressEventCb)

    def _createUi(self):
        """ Create the graphical interface """
        self.set_title("%s v%s" % (APPNAME, pitivi_version))
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
        self.timeline.showSimpleView()
        timelineframe = gtk.Frame()
        timelineframe.add(self.timeline)
        vpaned.pack2(timelineframe, resize=False, shrink=False)
        
        hpaned = gtk.HPaned()
        vpaned.pack1(hpaned, resize=True, shrink=False)

        # source-and-effects list
        self.sourcefactories = SourceFactoriesWidget()

        # Viewer
        self.viewer = PitiviViewer()

        # connect viewer's timeline position callback to the timeline widget
        self.viewer.addTimelinePositionCallback(self.timeline.timelinePositionChanged)

        hpaned.pack1(self.sourcefactories, resize=False, shrink=False)
        hpaned.pack2(self.viewer, resize=True, shrink=False)

        #application icon
        self.set_icon_from_file(configure.get_global_pixmap_dir() + "/pitivi.png")

    def toggleFullScreen(self):
        """ Toggle the fullscreen mode of the application """
        if not self.isFullScreen:
            self.viewer.window.fullscreen()
            self.isFullScreen = True
        else:
            self.viewer.window.unfullscreen()
            self.isFullScreen = False

    ## PlayGround callback

    def _errorMessageResponseCb(self, dialogbox, unused_response):
        dialogbox.hide()
        dialogbox.destroy()
        self.errorDialogBox = None

    def _playGroundErrorCb(self, unused_playground, error, detail):
        if self.errorDialogBox:
            return
        self.errorDialogBox = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                                                gtk.MESSAGE_ERROR,
                                                gtk.BUTTONS_OK,
                                                None)
        self.errorDialogBox.set_markup("<b>%s</b>" % error)
        self.errorDialogBox.connect("response", self._errorMessageResponseCb)
        if detail:
            self.errorDialogBox.format_secondary_text(detail)
        self.errorDialogBox.show()


    ## UI Callbacks

    def _destroyCb(self, unused_widget, data=None):
        instance.PiTiVi.shutdown()


    def _keyPressEventCb(self, unused_widget, event):
        if gtk.gdk.keyval_name(event.keyval) in ['f', 'F', 'F11']:
            self.toggleFullScreen()

    ## Toolbar/Menu actions callback
        
    def _newProjectCb(self, unused_action):
        instance.PiTiVi.new_blank_project()

    def _openProjectCb(self, unused_action):
        raise NotImplementedError

    def _saveProjectCb(self, unused_action):
        raise NotImplementedError

    def _saveProjectAsCb(self, unused_action):
        raise NotImplementedError

    def _projectSettingsCb(self, unused_action):
        l = ProjectSettingsDialog(self, instance.PiTiVi.current)
        l.show()

    def _quitCb(self, unused_action):
        instance.PiTiVi.shutdown()

    def _fullScreenCb(self, unused_action):
        self.toggleFullScreen()

    def _advancedViewCb(self, action):
        if action.get_active():
            self.timeline.showComplexView()
        else:
            self.timeline.showSimpleView()

    def _aboutCb(self, unused_action):
	abt = gtk.AboutDialog()
	abt.set_name(APPNAME)
	abt.set_version("v%s" % pitivi_version)
	abt.set_website("http://www.pitivi.org/")
	authors = ["Edward Hervey <edward@fluendo.com>" ]
	abt.set_authors(authors)
	abt.set_license("GNU Lesser Public License\nSee http://www.gnu.org/copyleft/lesser.html for more details")
        abt.set_icon_from_file(configure.get_global_pixmap_dir() + "/pitivi.png")
	abt.show()

    def _importSourcesCb(self, unused_action):
        self.sourcefactories.sourcelist.showImportSourcesDialog()

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
    
