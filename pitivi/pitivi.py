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
import gobject
import gst
import check
import instance
import device
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

# FIXME : maybe we should have subclasses for UI and CLI

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

    def __init__(self, filepath=None):
        """
        initialize pitivi with the command line arguments
        """
        gst.log("starting up pitivi...")

        # patch gst-python for new behaviours
        # FIXME : this shouldn't be in this class
        patch_gst_python()

        # store ourself in the instance global
        if instance.PiTiVi:
            raise RuntimeWarning(
                _("There is already a %s instance, inform developers")
                % APPNAME)
        instance.PiTiVi = self

        # get settings
        self._settings = GlobalSettings()
        self.threads = ThreadMaster()
        #self.screencast = False

        self.plugin_manager = PluginManager(
            self.settings.get_local_plugin_path(),
            self.settings.get_plugin_settings_path())

        self.playground = PlayGround()
        self._current = Project(_("New Project"))
        self.effects = Magician()

        self.deviceprobe = device.get_probe()

    ## properties

    def _get_settings(self):
        return self._settings

    def _set_settings(self, settings):
        self._settings = settings
        # FIXME : we could notify this
    settings = property(_get_settings, _set_settings,
                        doc="The project-wide output settings")

    def _get_current(self):
        return self._current

    def _set_current(self, project):
        self._current = project
        # FIXME : we could notify this
    current = property(_get_current, _set_current,
                       doc="The currently used Project")

    ## public methods

    def loadProject(self, uri=None, filepath=None):
        """ Load the given file through it's uri or filepath """
        gst.info("uri:%s, filepath:%s" % (uri, filepath))
        if not uri and not filepath:
            self.emit("new-project-failed", _("No location given."),
                uri)
            return
        if filepath:
            if not os.path.exists(filepath):
                self.emit("new-project-failed",
                          _("File does not exist"), filepath)
                return
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
            if self.emit("closing-project", self.current) == False:
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
        """ Close PiTiVi
        Returns True if PiTiVi was successfully closed, else False
        """
        gst.debug("shutting down")
        # we refuse to close if we're running a user interface and the user
        # doesn't want us to close the current project.
        if not self._closeRunningProject():
            gst.warning("Not closing since running project doesn't want to close")
            return False
        self.threads.stopAllThreads()
        self.playground.shutdown()
        instance.PiTiVi = None
        self.emit("shutdown")
        return True



class InteractivePitivi(Pitivi):
    """ Class for PiTiVi instances that provide user interaction """

    def __init__(self, filepath=None, mainloop=None, *args, **kwargs):
        Pitivi.__init__(self, filepath=None,
                        *args, **kwargs)
        self.mainloop = mainloop

        from ui.mainwindow import PitiviMainWindow
        self._gui = PitiviMainWindow(self)
        self._gui.load()

        self._gui.show()

        if filepath:
            self.loadProject(filepath=filepath)

    # properties

    def _get_mainloop(self):
        return self._mainloop

    def _set_mainloop(self, mainloop):
        if hasattr(self, "_mainloop"):
            if self._mainloop != None:
                raise Exception("Mainloop already set !")
        if mainloop == None:
            mainloop = gobject.MainLoop()
        self._mainloop = mainloop
    mainloop = property(_get_mainloop, _set_mainloop,
                        doc="The MainLoop running the program")

    @property
    def gui(self):
        """The user interface"""
        return self._gui


    # PiTiVi method overrides
    def shutdown(self):
        if Pitivi.shutdown(self):
            if self.mainloop:
                self.mainloop.quit()
            return True
        return False

    def run(self):
        if self.mainloop:
            self.mainloop.run()

def main(argv):
    """ Start PiTiVi ! """
    from optparse import OptionParser
    check.initial_checks()
    parser = OptionParser()
    (unused_options, args) = parser.parse_args(argv[1:])
    if len(args) > 0:
        ptv = InteractivePitivi(filepath=args[0])
    else:
        ptv = InteractivePitivi()
    ptv.run()
