# PiTiVi , Non-linear video editor
#
#       pitivi/pitivi.py
#
# Copyright (c) 2005-2009 Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2008-2009 Alessandro Decina <alessandro.d@gmail.com>
# Copyright (c) 2010      Google <aleb@google.com>
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Main application
"""
import gobject
import gtk
import os
import sys
import urllib
import ges

from gettext import gettext as _
from optparse import OptionParser

import pitivi.instance as instance

from pitivi.check import initial_checks
from pitivi.effects import EffectsHandler
from pitivi.configure import APPNAME
from pitivi.settings import GlobalSettings
from pitivi.utils.threads import ThreadMaster
from pitivi.mainwindow import PitiviMainWindow
from pitivi.project import ProjectManager, ProjectLogObserver
from pitivi.undo.medialibrary import MediaLibraryLogObserver
from pitivi.undo.undo import UndoableActionLog, DebugActionLogObserver
from pitivi.dialogs.startupwizard import StartUpWizard

from pitivi.utils.signal import Signallable
from pitivi.utils.system import getSystem
from pitivi.utils.loggable import Loggable
import pitivi.utils.loggable as log
#FIXME GES port disabled it
#from pitivi.undo.timeline import TimelineLogObserver

# FIXME : Speedup loading time
# Currently we load everything in one go
# It would be better if a minimalistic UI could start up ASAP, without loading
# anything gst-related or that could slow down startup.
# AND THEN load up the required parts.
# This will result in a much better end-user experience


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
    @ivar current: Currently used project.
    @type current: L{Project}.
    """

    __signals__ = {
        "new-project": ["project"],
        "new-project-loading": ["uri"],
        "new-project-created": ["project"],
        "new-project-loaded": ["project"],
        "new-project-failed": ["uri", "exception"],
        "closing-project": ["project"],
        "project-closed": ["project"],
        "missing-uri": ["formatter", "uri"],
        "shutdown": None}

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
            raise RuntimeWarning(_("There is already a %s instance, please inform "
                "the developers by filing a bug at "
                "http://bugzilla.gnome.org/enter_bug.cgi?product=pitivi")
                % APPNAME)
        instance.PiTiVi = self

        self.current = None

        # get settings
        self.settings = GlobalSettings()
        self.threads = ThreadMaster()
        #self.screencast = False

        self.effects = EffectsHandler()
        self.system = getSystem()

        self.projectManager = ProjectManager(self.effects)
        self._connectToProjectManager(self.projectManager)

        self.action_log = UndoableActionLog()
        self.debug_action_log_observer = DebugActionLogObserver()
        self.debug_action_log_observer.startObserving(self.action_log)
        # TODO reimplement the observing after GES port
        #self.timelineLogObserver = TimelineLogObserver(self.action_log)
        self.projectLogObserver = ProjectLogObserver(self.action_log)
        self.medialibrary_log_observer = MediaLibraryLogObserver(self.action_log)

    def shutdown(self):
        """
        Close PiTiVi.

        @return: C{True} if PiTiVi was successfully closed, else C{False}.
        @rtype: C{bool}
        """
        self.debug("shutting down")
        # we refuse to close if we're running a user interface and the user
        # doesn't want us to close the current project.
        if self.current and not self.projectManager.closeRunningProject():
            self.warning("Not closing since running project doesn't want to close")
            return False
        self.threads.stopAllThreads()
        self.settings.storeSettings()
        self.current = None
        instance.PiTiVi = None
        self.emit("shutdown")
        return True

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
        #self.timelineLogObserver.startObserving(project.timeline)
        self.projectLogObserver.startObserving(project)
        self.medialibrary_log_observer.startObserving(project.medialibrary)
        self._newProjectLoaded(project)
        self.emit("new-project-loaded", project)

    def _projectManagerNewProjectFailed(self, projectManager, uri, exception):
        self.emit("new-project-failed", uri, exception)

    def _projectManagerClosingProject(self, projectManager, project):
        return self.emit("closing-project", project)

    def _projectManagerProjectClosed(self, projectManager, project):
        #self.timelineLogObserver.stopObserving(project.timeline)
        self.projectLogObserver.stopObserving(project)
        self.current = None
        self.emit("project-closed", project)


class InteractivePitivi(Pitivi):
    """
    Base class to launch interactive PiTiVi
    """

    def __init__(self, debug=False):
        Pitivi.__init__(self)
        self.mainloop = gobject.MainLoop()
        self.actioner = None
        self.gui = None

        # Check the dependencies.
        missing_deps = initial_checks()
        if missing_deps:
            message, detail = missing_deps
            self._showStartupError(message, detail)
            sys.exit(2)

        if debug:
            sys.excepthook = self._excepthook

    def _showStartupError(self, message, detail):
        self.error("%s %s" % (message, detail))

    def _excepthook(self, exc_type, value, tback):
        import traceback
        import pdb
        traceback.print_tb(tback)
        pdb.post_mortem(tback)

    def _setActioner(self, actioner):
        self.actioner = actioner
        if self.actioner:
            self.actioner.connect("eos", self._eosCb)
            # On error, all we need to do is shutdown which
            # is the same as we do for EOS
            self.actioner.connect("error", self._eosCb)
            # Configure the actioner and start acting!
            self.actioner.startAction()

    def _eosCb(self, unused_obj):
        raise NotImplementedError()

    def _loadProject(self, project_filename):
        project = "file://%s" % os.path.abspath(project_filename)
        self.projectManager.loadProject(project)

    def run(self):
        """Runs the main loop."""
        self.mainloop.run()


class GuiPitivi(InteractivePitivi):
    """
    Base class to launch PiTiVi with UI
    """

    def __init__(self, debug=False):
        InteractivePitivi.__init__(self, debug)
        self._showGui()

    def _showStartupError(self, message, detail):
        dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                                   buttons=gtk.BUTTONS_OK)
        dialog.set_icon_name("pitivi")
        dialog.set_markup("<b>" + message + "</b>")
        dialog.format_secondary_text(detail)
        dialog.run()

    def _eosCb(self, unused_obj):
        self.shutdown()

    def _createGui(self):
        """Returns a gtk.Widget which represents the UI."""
        raise NotImplementedError()

    def _showGui(self):
        """Creates and shows the UI."""
        self.gui = self._createGui()
        self.gui.show()

    def shutdown(self):
        if Pitivi.shutdown(self):
            self.gui.destroy()
            self.mainloop.quit()
            return True
        return False


class FullGuiPitivi(GuiPitivi):
    """
    Creates an instance of PiTiVi with the UI

    This is called when we start the UI with a project passed as a parameter.
    It is also called by StartupWizardGuiPitivi.
    """

    def _createGui(self, **kargs):
        return PitiviMainWindow(self, **kargs)


#FIXME the GES port screwed the import to the timeline
class ProjectCreatorGuiPitivi(FullGuiPitivi):
    """
    Creates an instance of PiTiVi with the UI and loading a list
    of clips, adding them to the timeline or not
    """

    def __init__(self, media_filenames, add_to_timeline=False, debug=False):
        FullGuiPitivi.__init__(self, debug)
        # load the passed filenames, optionally adding them to the timeline
        # (useful during development)
        self.projectManager.newBlankProject(False)
        uris = ["file://" + urllib.quote(os.path.abspath(media_filename))
                for media_filename in media_filenames]
        self.current.medialibrary.connect("source-added",
                self._sourceAddedCb, uris, add_to_timeline)
        self.current.medialibrary.connect("discovery-error",
                self._discoveryErrorCb, uris)
        self.current.medialibrary.addUris(uris)

    def _sourceAddedCb(self, medialibrary, info,
            startup_uris, add_to_timeline):
        if self._maybePopStartupUri(startup_uris, info.get_uri()) \
                and add_to_timeline:
            self.action_log.begin("add clip")
            src = ges.TimelineFileSource(info.get_uri())
            src.set_property("priority", 1)
            self.current.timeline.get_layers()[0].add_object(src)
            self.action_log.commit()

    def _discoveryErrorCb(self, medialibrary, uri, error, debug, startup_uris):
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
            self.current.medialibrary.disconnect_by_function(self._sourceAddedCb)
            self.current.medialibrary.disconnect_by_function(self._discoveryErrorCb)

        return True


class ProjectLoaderGuiPitivi(FullGuiPitivi):
    """
    Creates an instance of the UI and loads @project_filename
    """

    def __init__(self, project_filename, debug=False):
        FullGuiPitivi.__init__(self, debug)
        self._loadProject(project_filename)


class StartupWizardGuiPitivi(FullGuiPitivi):
    """
    Creates an instance of the PiTiVi UI with the welcome dialog

    This is not called when a project is passed as a parameter.
    """

    def __init__(self, debug=False):
        FullGuiPitivi.__init__(self, debug)
        self.projectManager.newBlankProject(False)

    def _createGui(self):
        self.wizard = StartUpWizard(self)
        # Prevent the main window to go fullscreen because at least
        # the Metacity window manager will refuse to bring
        # the startup wizard window in front of the main window.
        return FullGuiPitivi._createGui(self, allow_full_screen=False)

    def _showGui(self):
        FullGuiPitivi._showGui(self)
        self.wizard.show()


def _parse_options(argv):
    parser = OptionParser(
            usage=_("""
    %prog [PROJECT_FILE]               # Start the video editor.
    %prog -i [-a] [MEDIA_FILE1 ...]    # Start the editor and create a project."""))

    parser.add_option("-i", "--import", dest="import_sources",
            action="store_true", default=False,
            help=_("Import each MEDIA_FILE into a new project."))
    parser.add_option("-a", "--add-to-timeline",
            action="store_true", default=False,
            help=_("Add each imported MEDIA_FILE to the timeline."))
    parser.add_option("-d", "--debug",
            action="store_true", default=False,
            help=_("Run Pitivi in the Python Debugger."))
    options, args = parser.parse_args(argv[1:])

    # Validate options.
    if options.add_to_timeline and not options.import_sources:
        parser.error(_("-a requires -i"))

    # Validate args.
    if options.import_sources:
        # When no MEDIA_FILE is specified, we just create a new project.
        pass
    else:
        if len(args) > 1:
            parser.error(_("Cannot open more than one PROJECT_FILE"))

    return options, args


def main(argv):
    options, args = _parse_options(argv)
    if options.import_sources:
        ptv = ProjectCreatorGuiPitivi(media_filenames=args,
                                      add_to_timeline=options.add_to_timeline,
                                      debug=options.debug)
    else:
        if args:
            ptv = ProjectLoaderGuiPitivi(project_filename=args[0],
                                         debug=options.debug)
        else:
            ptv = StartupWizardGuiPitivi(debug=options.debug)
    ptv.run()
