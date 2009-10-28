# PiTiVi , Non-linear video editor
#
#       pitivi/pitivi.py
#
# Copyright (c) 2005-2009 Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2008-2009 Alessandro Decina <alessandro.d@gmail.com>
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
import gobject
gobject.threads_init()
import gtk
from optparse import OptionParser
import os
import sys

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
from pitivi.ui.mainwindow import PitiviMainWindow
from pitivi.projectmanager import ProjectManager, ProjectLogObserver
from pitivi.undo import UndoableActionLog, DebugActionLogObserver
from pitivi.timeline.timeline_undo import TimelineLogObserver
from pitivi.sourcelist_undo import SourceListLogObserver
from pitivi.undo import UndoableAction

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

        "new-project-loading" : ["uri"],
        "new-project-created" : ["project"],
        "new-project-loaded" : ["project"],
        "new-project-failed" : ["uri", "exception"],
        "closing-project" : ["project"],
        "project-closed" : ["project"],
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
                _("There is already a %s instance, please inform the developers by filing a bug at http://bugzilla.gnome.org/enter_bug.cgi?product=pitivi")
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

        self.projectManager = ProjectManager()
        self._connectToProjectManager(self.projectManager)

        self.action_log = UndoableActionLog()
        self.debug_action_log_observer = DebugActionLogObserver()
        self.debug_action_log_observer.startObserving(self.action_log)
        self.timelineLogObserver = TimelineLogObserver(self.action_log)
        self.projectLogObserver = ProjectLogObserver(self.action_log)
        self.sourcelist_log_observer = SourceListLogObserver(self.action_log)

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
        if self.projectManager.current and not self.projectManager.closeRunningProject():
            self.warning("Not closing since running project doesn't want to close")
            return False
        self.threads.stopAllThreads()
        self.settings.storeSettings()
        if self.deviceprobe:
            self.deviceprobe.release()
        self.deviceprobe = None
        self.current = None
        instance.PiTiVi = None
        self.emit("shutdown")
        return True

    #}

    def _connectToProjectManager(self, projectManager):
        projectManager.connect("new-project-loading",
                self._projectManagerNewProjectLoading)
        projectManager.connect("new-project-created",
                self._projectManagerNewProjectCreated)
        projectManager.connect("new-project-loaded",
                self._projectManagerNewProjectLoaded)
        projectManager.connect("new-project-failed",
                self._projectManagerNewProjectFailed)
        projectManager.connect("closing-project",
                self._projectManagerClosingProject)
        projectManager.connect("project-closed",
                self._projectManagerProjectClosed)

    def _projectManagerNewProjectLoading(self, projectManager, uri):
        self.emit("new-project-loading", uri)

    def _projectManagerNewProjectCreated(self, projectManager, project):
        self.current = project
        self.emit("new-project-created", project)

    def _projectManagerNewProjectLoaded(self, projectManager, project):
        self.current = project
        self.action_log.clean()
        self.timelineLogObserver.startObserving(project.timeline)
        self.projectLogObserver.startObserving(project)
        self.sourcelist_log_observer.startObserving(project.sources)
        self.emit("new-project-loaded", project)

    def _projectManagerNewProjectFailed(self, projectManager, uri, exception):
        self.emit("new-project-failed", uri, exception)

    def _projectManagerClosingProject(self, projectManager, project):
        return self.emit("closing-project", project)

    def _projectManagerProjectClosed(self, projectManager, project):
        self.timelineLogObserver.stopObserving(project.timeline)
        self.projectLogObserver.stopObserving(project)
        self.current = None
        self.emit("project-closed", project)

class InteractivePitivi(Pitivi):
    usage = _("""
      %prog [PROJECT_FILE]
      %prog -i [-a] [MEDIA_FILE]...""")

    description = _("""Starts the video editor, optionally loading PROJECT_FILE. If
    no project is given, %prog creates a new project.
    Alternatively, when -i is specified, arguments are treated as clips to be
    imported into the project. If -a is specified, these clips will also be added to
    the end of the project timeline.""")

    import_help = _("""Import each MEDIA_FILE into the project.""")

    add_help = _("""Add each MEDIA_FILE to timeline after importing.""")
    debug_help = _("""Run pitivi in the Python Debugger""")

    no_ui_help = _("""Run pitivi with no gui""")

    def __init__(self):
        Pitivi.__init__(self)
        self.mainloop = gobject.MainLoop()

    def run(self, argv):
        # check for dependencies
        if not self._checkDependencies():
            return

        # parse cmdline options
        parser = self._createOptionParser()
        options, args = parser.parse_args(argv)

        if options.debug:
            sys.excepthook = self._excepthook

        # validate options

        if not options.no_ui:
            # create the ui
            self.gui = PitiviMainWindow(self)
            self.gui.show()

        if not options.import_sources and options.add_to_timeline:
            parser.error("-a requires -i")
            return

        if not options.import_sources and len(args) > 1:
            parser.error("invalid arguments")
            return

        if not options.import_sources and args:
            # load a project file
            project = "file://%s" % os.path.abspath(args[0])
            self.projectManager.loadProject(project)
        else:
            # load the passed filenames, optionally adding them to the timeline
            # (useful during development)
            self.projectManager.newBlankProject()
            uris = ["file://" + os.path.abspath(path) for path in args]
            self.current.sources.connect("source-added",
                    self._sourceAddedCb, uris, options.add_to_timeline)
            self.current.sources.connect("discovery-error",
                    self._discoveryErrorCb, uris)
            self.current.sources.addUris(uris)

        # run the mainloop
        self.mainloop.run()

    def shutdown(self):
        if Pitivi.shutdown(self):
            self.mainloop.quit()
            return True

        return False

    def _createOptionParser(self):
        parser = OptionParser(self.usage, description=self.description)
        parser.add_option("-i", "--import", help=self.import_help,
                dest="import_sources", action="store_true", default=False)
        parser.add_option("-a", "--add-to-timeline", help=self.add_help,
                action="store_true", default=False)
        parser.add_option("-d", "--debug", help=self.debug_help,
                action="store_true", default=False)
        parser.add_option("-n", "--no-ui", help=self.no_ui_help,
                action="store_true", default=False)

        return parser


    def _checkDependencies(self):
        missing_deps = initial_checks()
        if missing_deps:
            message, detail = missing_deps
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                                       buttons=gtk.BUTTONS_OK)
            dialog.set_icon_name("pitivi")
            dialog.set_markup("<b>"+message+"</b>")
            dialog.format_secondary_text(detail)
            dialog.run()

            return False

        return True

    def _sourceAddedCb(self, sourcelist, factory,
            startup_uris, add_to_timeline):
        if self._maybePopStartupUri(startup_uris, factory.uri) \
                and add_to_timeline:
            self.action_log.begin("add clip")
            self.current.timeline.addSourceFactory(factory)
            self.action_log.commit()

    def _discoveryErrorCb(self, sourcelist, uri, error, debug, startup_uris):
        self._maybePopStartupUri(startup_uris, uri)

    def _maybePopStartupUri(self, startup_uris, uri):
        try:
            startup_uris.remove(uri)
        except ValueError:
            # uri is not a startup uri. This can happen if the user starts
            # importing sources while sources specified at startup are still
            # being processed. In practice this will never happen.
            return False

        if not startup_uris:
            self.current.sources.disconnect_by_function(self._sourceAddedCb)
            self.current.sources.disconnect_by_function(self._discoveryErrorCb)

        return True

    def _excepthook(self, exc_type, value, tback):
        import traceback
        import pdb
        traceback.print_tb(tback)
        pdb.post_mortem(tback)

def main(argv):
    ptv = InteractivePitivi()
    ptv.run(sys.argv[1:])
