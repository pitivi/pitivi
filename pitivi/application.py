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
import urllib

from pitivi.pitivigstutils import patch_gst_python
patch_gst_python()

from gettext import gettext as _

import pitivi.instance as instance

from pitivi.check import initial_checks
from pitivi.device import get_probe
from pitivi.effects import EffectsHandler
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
from pitivi.ui.viewer import PitiviViewer
from pitivi.actioner import Renderer, Previewer
from pitivi.ui.startupwizard import StartUpWizard

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
        self.effects = EffectsHandler()
        self.deviceprobe = get_probe()

        self.projectManager = ProjectManager(self.effects)
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

    def _newProjectLoaded(self, project):
        pass

    def _projectManagerNewProjectLoaded(self, projectManager, project):
        self.current = project
        self.action_log.clean()
        self.timelineLogObserver.startObserving(project.timeline)
        self.projectLogObserver.startObserving(project)
        self.sourcelist_log_observer.startObserving(project.sources)
        self._newProjectLoaded(project)
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

    def __init__(self):
        Pitivi.__init__(self)
        self.mainloop = gobject.MainLoop()
        self.actioner = None

    def _newProjectLoaded(self, project):
        if self.render_output:
            # create renderer and set output file
            self.actioner = Renderer(self.current, pipeline=None, outfile=self.output_file)
        elif self.preview:
            # create previewer and set ui
            self.actioner = Previewer(self.current, pipeline=None, ui=self.gui)
            # hack to make the gtk.HScale seek slider UI behave properly
            self.gui._durationChangedCb(None, project.timeline.duration)
        if self.actioner:
            self.actioner.connect("eos", self._eosCb)
            # on error, all we need to do is shutdown which is the same as we do for EOS
            self.actioner.connect("error", self._eosCb)
            # configure the actioner and start acting!
            self.actioner.startAction()

    def run(self, options, args):
        # check for dependencies
        if not self._checkDependencies():
            return

        if options.debug:
            sys.excepthook = self._excepthook

        # validate options
        self.render_output = options.render_output
        self.preview = options.preview
        if options.render_output:
            options.no_ui = True

        if options.no_ui:
            self.gui = None
        elif options.preview:
            # init ui for previewing
            self.gui = PitiviViewer(self.settings)
            self.window = gtk.Window()
            self.window.connect("delete-event", self._deleteCb)
            self.window.add(self.gui)
            self.window.show_all()
        else:
            # create the ui
            self.gui = PitiviMainWindow(self)
            self.gui.show()

        if not options.import_sources:
            if args:
                if options.render_output:
                    self.output_file = "file://%s" % os.path.abspath(options.render_output)
                # load a project file
                project = "file://%s" % os.path.abspath(args[0])
                self.projectManager.loadProject(project)
            else:
                self.projectManager.newBlankProject()
        
                self.projectManager.connect("new-project-loaded", self._quitWizardCb)
                self.wizard = StartUpWizard(self)
        else:
            # load the passed filenames, optionally adding them to the timeline
            # (useful during development)
            self.projectManager.newBlankProject()
            uris = ["file://" + urllib.quote(os.path.abspath(path)) for path in args]
            self.current.sources.connect("source-added",
                    self._sourceAddedCb, uris, options.add_to_timeline)
            self.current.sources.connect("discovery-error",
                    self._discoveryErrorCb, uris)
            self.current.sources.addUris(uris)

        # run the mainloop
        self.mainloop.run()

    def _quitWizardCb(self, unused_projectManager, uri):
        if uri.uri is not None:
            self.wizard.quit()

    def _deleteCb(self, unused_widget, unused_data):
        self.shutdown()

    def _eosCb(self, unused_obj):
        if self.gui is None:
            self.shutdown()
        elif self.window is not None:
            self.gui.seek(0)

    def shutdown(self):
        if Pitivi.shutdown(self):
            if self.gui:
                self.gui.destroy()
            self.mainloop.quit()
            return True

        return False

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

def _parse_options(argv):
    parser = OptionParser(
            usage=_("""
    %prog [PROJECT_FILE]               # Start the video editor.
    %prog -i [-a] MEDIA_FILE1 [...]    # Start the editor and create a project.
    %prog PROJECT_FILE -r OUTPUT_FILE  # Render a project.
    %prog PROJECT_FILE -p              # Preview a project."""))

    parser.add_option("-i", "--import", dest="import_sources",
            action="store_true", default=False,
            help=_("Import each MEDIA_FILE into a new project."))
    parser.add_option("-a", "--add-to-timeline",
            action="store_true", default=False,
            help=_("Add each imported MEDIA_FILE to the timeline."))
    parser.add_option("-d", "--debug",
            action="store_true", default=False,
            help=_("Run Pitivi in the Python Debugger."))
    parser.add_option("-r", "--render", dest="render_output",
            action="store", default=None,
            help=_("Render the specified project to OUTPUT_FILE with no GUI."))
    parser.add_option("-p", "--preview",
            action="store_true", default=False,
            help=_("Preview the specified project file without the full UI."))
    options, args = parser.parse_args(argv[1:])

    # Validate options.
    if options.render_output and options.preview:
        parser.error("-p and -r cannot be used simultaneously")

    if options.import_sources and (options.render_output or options.preview):
        parser.error("-r or -p and -i are incompatible")

    if options.add_to_timeline and not options.import_sources:
        parser.error("-a requires -i")

    # Validate args.
    if options.import_sources:
        if not args:
            parser.error("-i requires at least one MEDIA_FILE")
    elif options.render_output:
        if len(args) != 1:
            parser.error("-r requires exactly one PROJECT_FILE")
    elif options.preview:
        if len(args) != 1:
            parser.error("-p requires exactly one PROJECT_FILE")
    else:
        if len(args) > 1:
            parser.error("Cannot open more than one PROJECT_FILE")

    return options, args

def main(argv):
    options, args = _parse_options(argv)
    ptv = InteractivePitivi()
    ptv.run(options, args)
