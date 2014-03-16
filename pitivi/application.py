# Pitivi video editor
#
#       pitivi/application.py
#
# Copyright (c) 2014 <alexandru.balut@gmail.com>
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

import os

from gi.repository import GObject
from gi.repository import GdkX11
from gi.repository import Gio
from gi.repository import Gtk

from pitivi.effects import EffectsHandler
from pitivi.configure import VERSION, RELEASES_URL
from pitivi.settings import GlobalSettings
from pitivi.utils.threads import ThreadMaster
from pitivi.mainwindow import PitiviMainWindow
from pitivi.project import ProjectManager, ProjectLogObserver
from pitivi.undo.undo import UndoableActionLog, DebugActionLogObserver
from pitivi.dialogs.startupwizard import StartUpWizard

from pitivi.utils.misc import quote_uri
from pitivi.utils.system import getSystem
from pitivi.utils.loggable import Loggable
import pitivi.utils.loggable as log


class Pitivi(Gtk.Application, Loggable):
    """
    Pitivi's application.

    @ivar gui: The main window of the app.
    @type gui: L{PitiviMainWindow}
    @type project_manager: L{ProjectManager}
    @ivar settings: Application-wide settings.
    @type settings: L{GlobalSettings}.
    """

    __gsignals__ = {
        'version-info-received': (GObject.SIGNAL_RUN_LAST, None, (object,))
    }

    def __init__(self):
        Gtk.Application.__init__(self,
                                 application_id="org.pitivi",
                                 flags=Gio.ApplicationFlags.HANDLES_OPEN)
        Loggable.__init__(self)

        self.settings = None
        self.threads = None
        self.effects = None
        self.system = None
        self.project_manager = ProjectManager(self)
        self.action_log = None
        self.debug_action_log_observer = None
        self.project_log_observer = None

        self.gui = None
        self.welcome_wizard = None

        self._version_information = {}

        self.connect("startup", self.startupCb)
        self.connect("activate", self.activateCb)
        self.connect("open", self.openCb)

    def startupCb(self, unused_app):
        # Init logging as early as possible so we can log startup code
        enable_color = not os.environ.get('PITIVI_DEBUG_NO_COLOR', '0') in ('', '1')
        # Let's show a human-readable Pitivi debug output by default, and only
        # show a crazy unreadable mess when surrounded by gst debug statements.
        enable_crack_output = "GST_DEBUG" in os.environ
        log.init('PITIVI_DEBUG', enable_color, enable_crack_output)

        self.info('starting up')
        self.settings = GlobalSettings()
        self.threads = ThreadMaster()
        self.effects = EffectsHandler()
        self.system = getSystem()

        self.action_log = UndoableActionLog()
        self.debug_action_log_observer = DebugActionLogObserver()
        self.debug_action_log_observer.startObserving(self.action_log)
        self.project_log_observer = ProjectLogObserver(self.action_log)

        self.project_manager.connect("new-project-loaded", self._newProjectLoaded)
        self.project_manager.connect("project-closed", self._projectClosed)

        self._checkVersion()

    def activateCb(self, unused_app):
        if self.gui:
            # The app is already started and the window already created.
            # Present the already existing window.
            # TODO: Use present() instead of present_with_time() when
            # https://bugzilla.gnome.org/show_bug.cgi?id=688830 is fixed.
            x11_server_time = GdkX11.x11_get_server_time(self.gui.get_window())
            self.gui.present_with_time(x11_server_time)
            # No need to show the welcome wizard.
            return
        self.createMainWindow()
        self.welcome_wizard = StartUpWizard(self)
        self.welcome_wizard.show()

    def createMainWindow(self):
        if self.gui:
            return
        self.gui = PitiviMainWindow(self)
        self.add_window(self.gui)
        # We might as well show it.
        self.gui.show()

    def openCb(self, unused_app, giofiles, unused_count, unused_hint):
        assert giofiles
        self.createMainWindow()
        if len(giofiles) > 1:
            self.warning("Can open only one project file at a time. Ignoring the rest!")
        project_file = giofiles[0]
        self.project_manager.loadProject(quote_uri(project_file.get_uri()))
        return True

    def shutdown(self):
        """
        Close Pitivi.

        @return: C{True} if Pitivi was successfully closed, else C{False}.
        @rtype: C{bool}
        """
        self.debug("shutting down")
        # Refuse to close if we are not done with the current project.
        if not self.project_manager.closeRunningProject():
            self.warning("Not closing since running project doesn't want to close")
            return False
        if self.welcome_wizard:
            self.welcome_wizard.hide()
        if self.gui:
            self.gui.destroy()
        self.threads.stopAllThreads()
        self.settings.storeSettings()
        self.quit()
        return True

    def _newProjectLoaded(self, unused_project_manager, project, unused_fully_loaded):
        self.action_log.clean()
        self.project_log_observer.startObserving(project)

    def _projectClosed(self, unused_project_manager, project):
        self.project_log_observer.stopObserving(project)

    def _checkVersion(self):
        """
        Check online for release versions information.
        """
        self.info("Requesting version information async")
        giofile = Gio.File.new_for_uri(RELEASES_URL)
        giofile.load_contents_async(None, self._versionInfoReceivedCb, None)

    def _versionInfoReceivedCb(self, giofile, result, user_data):
        try:
            raw = giofile.load_contents_finish(result)[1]
            raw = raw.split("\n")
            # Split line at '=' if the line is not empty or a comment line
            data = [element.split("=") for element in raw
                    if element and not element.startswith("#")]

            # search newest version and status
            status = "UNSUPPORTED"
            current_version = None
            for version, version_status in data:
                if VERSION == version:
                    status = version_status
                if version_status.upper() == "CURRENT":
                    # This is the latest.
                    current_version = version

            self.info("Latest software version is %s", current_version)
            # Python is magical... comparing version *strings* always works,
            # even with different major.minor.nano version number schemes!
            if VERSION > current_version:
                status = "CURRENT"
                self.info("Running version %s, which is newer than the latest known version. Considering it as the latest current version.", VERSION)
            elif status is "UNSUPPORTED":
                self.warning("Using an outdated version of Pitivi (%s)", VERSION)

            self._version_information["current"] = current_version
            self._version_information["status"] = status
            self.emit("version-info-received", self._version_information)
        except Exception as e:
            self.warning("Version info could not be read: %s", e)

    def isLatest(self):
        """
        Whether the app's version is the latest as far as we know.
        """
        status = self._version_information.get("status")
        return status is None or status.upper() == "CURRENT"

    def getLatest(self):
        """
        Get the latest version of the app or None.
        """
        return self._version_information.get("current")
