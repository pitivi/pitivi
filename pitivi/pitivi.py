# PiTiVi , Non-linear video editor
#
#       pitivi/pitivi.py
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
Main application
"""
import os
import gtk
import gst
import check
import instance
import device
from ui import mainwindow
from pitivigstutils import patch_gst_python
from playground import PlayGround
from project import Project, file_is_project
from effects import Magician
from configure import APPNAME
from settings import GlobalSettings
from threads import ThreadMaster
from pluginmanager import PluginManager
from signalinterface import Signallable
import instance

from gettext import gettext as _

# FIXME : Speedup loading time
# Currently we load everything in one go
# It would be better if a minimalistic UI could start up ASAP, without loading
# anything gst-related or that could slow down startup.
# AND THEN load up the required parts.
# This will result in a much better end-user experience

class Pitivi(object, Signallable):
    """
    Pitivi's main class

    Signals
        void new-project-loading()
            Pitivi is attempting to load a new project
        void new-project-loaded (project)
            a new project has been loaded, and the UI should refresh it's views
            * project - the project which has been loaded
        void new-project-failed(reason, uri)
            a new project could not be created
            * reason - the reason for failure
            * uri - the uri which failed to load (or None)
        boolean closing-project(project)
            pitivi would like to close a project. handlers should return false
            if they do not want this project to close. by default, assumes
            true.
            This signal should only be used by classes that might want to abort
            the closing of a project.
            * project - the project Pitivi would like to close
        void project-closed(project)
            The project is closed, it will be freed when the callback returns.
            Classes should connect to this instance when they want to know that
            data related to that project is no longer going to be used.
            * project - the project closed
        shutdown
            used internally, do not catch this signals"""

    __signals__ = {
        "new-project-loading" : ["project"],
        "new-project-loaded" : ["project"],
        "closing-project" : ["project"],
        "project-closed" : ["project"],
        "new-project-failed" : ["reason", "uri"],
        "shutdown" : None
        }

    def __init__(self, args=[], use_ui=True):
        """
        initialize pitivi with the command line arguments
        """
        gst.log("starting up pitivi...")
        self.project = None
        self._use_ui = use_ui

        # patch gst-python for new behaviours
        patch_gst_python()

        # store ourself in the instance global
        if instance.PiTiVi:
            raise RuntimeWarning(
                _("There is already a %s instance, inform developers")
                % APPNAME)
        instance.PiTiVi = self

        # FIXME: use gnu getopt or somethign of the sort
        project_file = None
        if len(args) > 1:
            if os.path.exists(args[1]):
                project_file = args[1]

        # get settings
        self.settings = GlobalSettings()
        self.threads = ThreadMaster()
        #self.screencast = False

        self.plugin_manager = PluginManager(
            self.settings.get_local_plugin_path(),
            self.settings.get_plugin_settings_path())

        self.playground = PlayGround()
        self.current = Project(_("New Project"))
        self.effects = Magician()

        self.deviceprobe = device.get_probe()

        if self._use_ui:
            self.uimanager = gtk.UIManager()
            # we're starting a GUI for the time being
            self.gui = mainwindow.PitiviMainWindow()
            self.gui.show()
            if project_file:
                self.loadProject(filepath=project_file)

    def do_closing_project(self, project):
        return True

    def loadProject(self, uri=None, filepath=None):
        """ Load the given file through it's uri or filepath """
        gst.info("uri:%s, filepath:%s" % (uri, filepath))
        if not uri and not filepath:
            self.emit("new-project-failed", _("Not a valid project file."),
                uri)
            return
        if filepath:
            uri = "file://" + filepath
        # is the given filepath a valid pitivi project
        if not file_is_project(uri):
            self.emit("new-project-failed", _("Not a valid project file."),
                uri)
            return
        # if current project, try to close it
        if self._closeRunningProject():
            project = Project(uri=uri)
            self.emit("new-project-loading", project)
            try:
                project.load()
                self.current = project
                self.emit("new-project-loaded", self.current)
            except:
                self.current = None
                self.emit("new-project-failed",
                    _("There was an error loading the file."), uri)

    def _closeRunningProject(self):
        """ close the current project """
        gst.info("closing running project")
        if self.current:
            if self.current.hasUnsavedModifications():
                if not self.current.save():
                    return False
            if not self.emit("closing-project", self.current):
                return False
            self.playground.pause()
            self.emit("project-closed", self.current)
            self.current = None
        return True

    def newBlankProject(self):
        """ start up a new blank project """
        # if there's a running project we must close it
        if self._closeRunningProject():
            project = Project(_("New Project"))
            self.playground.pause()
            self.emit("new-project-loading", project)
            self.current = project
            self.emit("new-project-loaded", self.current)

    def shutdown(self):
        """ close PiTiVi """
        gst.debug("shutting down")
        # we refuse to close if we're running a user interface and the user
        # doesn't want us to close the current project.
        if not self._closeRunningProject():
            gst.warning("Not closing since running project doesn't want to close")
            return
        self.threads.stopAllThreads()
        self.playground.shutdown()
        instance.PiTiVi = None
        self.emit("shutdown")

def shutdownCb(pitivi):
    """ shutdown callback used by main()"""
    gst.debug("Exiting main loop")
    gtk.main_quit()

def main(argv):
    """ Start PiTiVi ! """
    check.initial_checks()
    ptv = Pitivi(argv)
    ptv.connect('shutdown', shutdownCb)
    gtk.main()
