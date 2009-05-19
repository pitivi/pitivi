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

from pitivi.pitivigstutils import patch_gst_python
patch_gst_python()

from gettext import gettext as _

import pitivi.instance as instance

from pitivi.check import initial_checks
from pitivi.device import get_probe
from pitivi.effects import Magician
from pitivi.configure import APPNAME
from pitivi.settings import GlobalSettings
from pitivi.threads import ThreadMaster
from pitivi.pluginmanager import PluginManager
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.log import log
from pitivi.project import Project
from pitivi.formatters.format import get_formatter_for_uri
from pitivi.formatters.base import FormatterError

# FIXME : Speedup loading time
# Currently we load everything in one go
# It would be better if a minimalistic UI could start up ASAP, without loading
# anything gst-related or that could slow down startup.
# AND THEN load up the required parts.
# This will result in a much better end-user experience

# FIXME : maybe we should have subclasses for UI and CLI

class Pitivi(Loggable, Signallable):
    """
    Pitivi's main application class.

    Signals:
     - C{new-project} : A new C{Project} is loaded and ready to use.

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
        "new-project" : ["project"],

        "new-project-loading" : ["project"],
        "new-project-loaded" : ["project"],
        "closing-project" : ["project"],
        "project-closed" : ["project"],
        "new-project-failed" : ["reason", "uri"],
        "missing-uri" : ["formatter", "uri"],
        "shutdown" : None
        }

    def __init__(self):
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
                _("There is already a %s instance, please inform developers by filing a bug at http://bugzilla.gnome.org/")
                % APPNAME)
        instance.PiTiVi = self

        self.projects = []
        self.current = None

        # get settings
        self.settings = GlobalSettings()
        self.threads = ThreadMaster()
        #self.screencast = False

        self.plugin_manager = PluginManager(
            self.settings.get_local_plugin_path(),
            self.settings.get_plugin_settings_path())
        self.effects = Magician()
        self.deviceprobe = get_probe()
        self.newBlankProject()

    #{ Project-related methods

    def addProject(self, project=None, uri=None):
        """ Add the given L{Project} to the list of projects controlled
        by the application.

        If no project is given, then the application will attempt to load
        the project contained at the given C{URI}.

        The 'C{new-project}' signal will be emitted if the project is properly
        added.

        @arg project: The project to add.
        @type project: L{Project}
        @arg uri: The location of the project to load.
        @type uri: C{URI}
        """
        if project == None and uri == None:
            raise Exception("No project or URI given")
        if uri != None:
            if project != None:
                raise Exception("Only provide either a project OR a URI")
            project = load_project(uri)

        if project in self.projects:
            raise Exception("Project already controlled")
        self.projects.append(project)
        self.emit("new-project", project)

    ## old implementations

    def loadProject(self, uri=None, filepath=None):
        """ Load the given file through it's uri or filepath """
        self.info("uri:%s, filepath:%s", uri, filepath)
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
        formatter = get_formatter_for_uri(uri)
        if not formatter:
            self.emit("new-project-failed", _("Not a valid project file."),
                uri)
            return
        # if current project, try to close it
        if self._closeRunningProject():
            project = formatter.newProject()
            formatter.connect("missing-uri", self._missingURICb)
            self.emit("new-project-loading", project)
            self.info("Got a new project %r, calling loadProject", project)
            try:
                formatter.loadProject(uri, project)
                self.current = project
                self.emit("new-project-loaded", self.current)
            except FormatterError, e:
                self.handleException(e)
                self.warning("error loading the project")
                self.current = None
                self.emit("new-project-failed",
                    _("There was an error loading the file."), uri)
            finally:
                formatter.disconnect_by_function(self._missingURICb)

    def _missingURICb(self, formatter, uri):
        self.emit("missing-uri", formatter, uri)

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

            from pitivi.stream import AudioStream, VideoStream
            import gst
            from pitivi.timeline.track import Track

            # FIXME: this should not be hard-coded
            # add default tracks for a new project
            video = VideoStream(gst.Caps('video/x-raw-rgb; video/x-raw-yuv'))
            track = Track(video)
            project.timeline.addTrack(track)
            audio = AudioStream(gst.Caps('audio/x-raw-int; audio/x-raw-float'))
            track = Track(audio)
            project.timeline.addTrack(track)

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

    def __init__(self, project=None, sources=[], add_to_timeline=False,
        mainloop=None, *args, **kwargs):
        from pitivi.ui.mainwindow import PitiviMainWindow
        from urllib import quote
        Pitivi.__init__(self, *args, **kwargs)
        self._mainloop = None
        self.mainloop = mainloop

        self._gui = PitiviMainWindow(self)
        self._gui.show()

        if project:
            self.loadProject(filepath=project)

        uris = ["file://" + os.path.abspath(path) for path in sources]
        if add_to_timeline:
            self._uris = uris
            self._duration = self.current.timeline.duration
            self.current.sources.connect("file_added", self._addSourceCb)
            self.current.sources.connect("discovery-error", self._discoveryErrorCb)
        self.current.sources.addUris(uris)

    def _addSourceCb(self, unused_sourcelist, factory):
        if factory.name in self._uris:
            self._uris.remove(factory.name)
            if not self._uris:
                self.current.sources.disconnect_by_function(self._addSourceCb)

            t = self.current.timeline.addSourceFactory(factory)
            t.start = self._duration
            self._duration += t.duration

    def _discoveryErrorCb(self, sourcelist, uri, error, debug):
        if uri in self._uris:
            self._uris.remove(uri)
            if not self._uris:
                self.current.sources.disconnect_by_function(self._discoveryErrorCb)

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

usage = _("%prog [-p PROJECT_FILE] [-a] [MEDIA_FILE]...")

description = _("""Starts the video editor, optionally loading PROJECT_FILE. If no
project is given, %prog creates a new project. Remaining arguments are treated
as clips to be imported into the project. If -a is specified, these clips will
also be added to the end of the project timeline.""")

project_help = _("""Open project file specified by PROJECT instead of creating a
new project.""")

add_help = _("""Add each MEDIA_FILE to timeline after importing.""")

def main(argv):
    """ Start PiTiVi ! """
    from optparse import OptionParser
    initial_checks()
    parser = OptionParser(usage, description=description)
    parser.add_option("-p", "--project", help=project_help)
    parser.add_option("-a", "--add-to-timeline", help=add_help, 
        action="store_true")
    options, args = parser.parse_args(argv)
    ptv = InteractivePitivi(project=options.project, sources=args[1:],
        add_to_timeline=options.add_to_timeline)
    ptv.run()
