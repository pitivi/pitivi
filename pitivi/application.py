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
gobject.threads_init()

from pitivigstutils import patch_gst_python
patch_gst_python()

from gettext import gettext as _

import pitivi.instance as instance

from pitivi.check import initial_checks
from pitivi.device import get_probe
from pitivi.project import Project, file_is_project
from pitivi.effects import Magician
from pitivi.configure import APPNAME
from pitivi.settings import GlobalSettings
from pitivi.threads import ThreadMaster
from pitivi.pluginmanager import PluginManager
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.log import log

# FIXME : Speedup loading time
# Currently we load everything in one go
# It would be better if a minimalistic UI could start up ASAP, without loading
# anything gst-related or that could slow down startup.
# AND THEN load up the required parts.
# This will result in a much better end-user experience

# FIXME : maybe we should have subclasses for UI and CLI

class Pitivi(object, Loggable, Signallable):
    """
    Pitivi's main application class.

    Signals:
     - C{new-project-loading} : Pitivi is attempting to load a new project.
     - C{new-project-loaded} : A new L{Project} has been loaded, and the UI should refresh it's view.
     - C{new-project-failed} : A new L{Project} failed to load.
     - C{closing-project} :  pitivi would like to close a project. handlers should return false
     if they do not want this project to close. by default, assumes
     true. This signal should only be used by classes that might want to abort
     the closing of a project.
     - C{project-closed} : The project is closed, it will be freed when the callback returns.
     Classes should connect to this instance when they want to know that
     data related to that project is no longer going to be used.
     - C{shutdown} : Used internally, do not use this signal.`

    @ivar settings: Application-wide settings.
    @type settings: L{GlobalSettings}.
    @ivar projects: List of used projects
    @type projects: List of L{Project}.
    @ivar current: Currently used project.
    @type current: L{Project}.
    """

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
        Loggable.__init__(self)

        # init logging as early as possible so we can log startup code
        enable_color = os.environ.get('PITIVI_DEBUG_NO_COLOR', '0') in ('', '0')
        log.init('PITIVI_DEBUG', enable_color)

        self.info('starting up')

        # store ourself in the instance global
        if instance.PiTiVi:
            raise RuntimeWarning(
                _("There is already a %s instance, inform developers")
                % APPNAME)
        instance.PiTiVi = self

        self.projects = []

        # get settings
        self.settings = GlobalSettings()
        self.threads = ThreadMaster()
        #self.screencast = False

        self.plugin_manager = PluginManager(
            self.settings.get_local_plugin_path(),
            self.settings.get_plugin_settings_path())

        self.current = Project(_("New Project"))
        self.effects = Magician()

        self.deviceprobe = get_probe()

    #{ Project-related methods






    ## old implementations

    def loadProject(self, uri=None, filepath=None):
        """ Load the given file through it's uri or filepath """
        self.info("uri:%s, filepath:%s" % (uri, filepath))
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
        self.info("closing running project")
        if self.current:
            if self.current.hasUnsavedModifications():
                if not self.current.save():
                    return False
            if self.emit("closing-project", self.current) == False:
                return False
            self.emit("project-closed", self.current)
            self.current.release()
            self.current = None
        return True

    def newBlankProject(self):
        """ start up a new blank project """
        # if there's a running project we must close it
        if self._closeRunningProject():
            project = Project(_("New Project"))
            self.emit("new-project-loading", project)
            self.current = project
            self.emit("new-project-loaded", self.current)

    #{ Shutdown methods

    def shutdown(self):
        """
        Close PiTiVi.

        @return: C{True} if PiTiVi was successfully closed, else C{False}.
        @rtype: C{bool}
        """
        self.debug("shutting down")
        # we refuse to close if we're running a user interface and the user
        # doesn't want us to close the current project.
        if not self._closeRunningProject():
            self.warning("Not closing since running project doesn't want to close")
            return False
        self.threads.stopAllThreads()
        self.settings.storeSettings()
        self.deviceprobe.release()
        self.deviceprobe = None
        self.current = None
        instance.PiTiVi = None
        self.emit("shutdown")
        return True

    #}


class InteractivePitivi(Pitivi):
    """ Class for PiTiVi instances that provide user interaction """

    def __init__(self, filepath=None, mainloop=None, *args, **kwargs):
        from ui.mainwindow import PitiviMainWindow
        Pitivi.__init__(self, filepath=None,
                        *args, **kwargs)
        self._mainloop = None
        self.mainloop = mainloop

        self._gui = PitiviMainWindow(self)
        self._gui.load()
        self._gui.show()

        if filepath:
            self.loadProject(filepath=filepath)

    # properties

    def _get_mainloop(self):
        return self._mainloop

    def _set_mainloop(self, mainloop):
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
    initial_checks()
    parser = OptionParser()
    (unused_options, args) = parser.parse_args(argv[1:])
    if len(args) > 0:
        ptv = InteractivePitivi(filepath=args[0])
    else:
        ptv = InteractivePitivi()
    ptv.run()
