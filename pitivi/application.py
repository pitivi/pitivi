# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005-2009 Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2008-2009 Alessandro Decina <alessandro.d@gmail.com>
# Copyright (c) 2014 Alexandru Băluț<alexandru.balut@gmail.com>
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
import time
from gettext import gettext as _

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.configure import RELEASES_URL
from pitivi.configure import VERSION
from pitivi.dialogs.startupwizard import StartUpWizard
from pitivi.effects import EffectsManager
from pitivi.mainwindow import MainWindow
from pitivi.project import ProjectManager
from pitivi.settings import get_dir
from pitivi.settings import GlobalSettings
from pitivi.settings import xdg_cache_home
from pitivi.shortcuts import ShortcutsManager
from pitivi.shortcuts import show_shortcuts
from pitivi.undo.project import ProjectObserver
from pitivi.undo.undo import UndoableActionLog
from pitivi.utils import loggable
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import quote_uri
from pitivi.utils.proxy import ProxyManager
from pitivi.utils.system import get_system
from pitivi.utils.threads import ThreadMaster
from pitivi.utils.timeline import Zoomable


class Pitivi(Gtk.Application, Loggable):
    """Hello world.

    Attributes:
        action_log (UndoableActionLog): The undo/redo log for the current project.
        effects (EffectsManager): The effects which can be applied to a clip.
        gui (MainWindow): The main window of the app.
        project_manager (ProjectManager): The holder of the current project.
        settings (GlobalSettings): The application-wide settings.
        system (pitivi.utils.system.System): The system running the app.
    """

    __gsignals__ = {
        "version-info-received": (GObject.SIGNAL_RUN_LAST, None, (object,))
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
        self.project_observer = None
        self._last_action_time = Gst.util_get_timestamp()

        self.gui = None
        self.__welcome_wizard = None

        self._version_information = {}

        self._scenario_file = None
        self._first_action = True

        Zoomable.app = self
        self.shortcuts = ShortcutsManager(self)

    def write_action(self, action, properties={}):
        if self._scenario_file is None:
            return

        if self._first_action:
            self._scenario_file.write(
                "description, seek=true, handles-states=true\n")
            self._first_action = False

        now = Gst.util_get_timestamp()
        if now - self._last_action_time > 0.05 * Gst.SECOND:
            # We need to make sure that the waiting time was more than 50 ms.
            st = Gst.Structure.new_empty("wait")
            st["duration"] = float((now - self._last_action_time) / Gst.SECOND)
            self._scenario_file.write(st.to_string() + "\n")
            self._last_action_time = now

        if not isinstance(action, Gst.Structure):
            structure = Gst.Structure.new_empty(action)

            for key, value in properties.items():
                structure[key] = value

            action = structure

        self._scenario_file.write(action.to_string() + "\n")
        self._scenario_file.flush()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Init logging as early as possible so we can log startup code
        enable_color = not os.environ.get(
            'PITIVI_DEBUG_NO_COLOR', '0') in ('', '1')
        # Let's show a human-readable Pitivi debug output by default, and only
        # show a crazy unreadable mess when surrounded by gst debug statements.
        enable_crack_output = "GST_DEBUG" in os.environ
        loggable.init('PITIVI_DEBUG', enable_color, enable_crack_output)

        self.info('starting up')
        self._setup()
        self._checkVersion()

    def _setup(self):
        self.settings = GlobalSettings()
        self.threads = ThreadMaster()
        self.effects = EffectsManager()
        self.proxy_manager = ProxyManager(self)
        self.system = get_system()

        self.project_manager.connect(
            "new-project-loading", self._newProjectLoadingCb)
        self.project_manager.connect(
            "new-project-loaded", self._newProjectLoaded)
        self.project_manager.connect("project-closed", self._projectClosed)

        self._createActions()
        self._syncDoUndo()

    def _createActions(self):
        self.shortcuts.register_group("app", _("General"))
        self.undo_action = Gio.SimpleAction.new("undo", None)
        self.undo_action.connect("activate", self._undoCb)
        self.add_action(self.undo_action)
        self.shortcuts.add("app.undo", ["<Primary>z"],
                           _("Undo the most recent action"))

        self.redo_action = Gio.SimpleAction.new("redo", None)
        self.redo_action.connect("activate", self._redoCb)
        self.add_action(self.redo_action)
        self.shortcuts.add("app.redo", ["<Primary><Shift>z"],
                           _("Redo the most recent action"))

        self.quit_action = Gio.SimpleAction.new("quit", None)
        self.quit_action.connect("activate", self._quitCb)
        self.add_action(self.quit_action)
        self.shortcuts.add("app.quit", ["<Primary>q"], _("Quit"))

        self.show_shortcuts_action = Gio.SimpleAction.new("shortcuts_window", None)
        self.show_shortcuts_action.connect("activate", self._show_shortcuts_cb)
        self.add_action(self.show_shortcuts_action)
        self.shortcuts.add("app.shortcuts_window",
                           ["<Primary>F1", "<Primary>question"],
                           _("Show the Shortcuts Window"))

    def do_activate(self):
        if self.gui:
            # The app is already started and the window already created.
            # Present the already existing window.
            if self.system.has_x11():
                # TODO: Use present() instead of present_with_time() when
                # https://bugzilla.gnome.org/show_bug.cgi?id=688830 is fixed.
                from gi.repository import GdkX11
                x11_server_time = GdkX11.x11_get_server_time(self.gui.get_window())
                self.gui.present_with_time(x11_server_time)
            else:
                # On Wayland or Quartz (Mac OS X) backend there is no GdkX11,
                # so just use present() directly here.
                self.gui.present()
            # No need to show the welcome wizard.
            return
        self.createMainWindow()
        self.welcome_wizard.show()

    @property
    def welcome_wizard(self):
        if not self.__welcome_wizard:
            self.__welcome_wizard = StartUpWizard(self)
        return self.__welcome_wizard

    def createMainWindow(self):
        if self.gui:
            return
        self.gui = MainWindow(self)
        self.add_window(self.gui)
        self.gui.checkScreenConstraints()
        # We might as well show it.
        self.gui.show()

    def do_open(self, giofiles, unused_count, unused_hint):
        assert giofiles
        self.createMainWindow()
        if len(giofiles) > 1:
            self.warning(
                "Can open only one project file at a time. Ignoring the rest!")
        project_file = giofiles[0]
        self.project_manager.loadProject(quote_uri(project_file.get_uri()))
        return True

    def shutdown(self):
        """Closes the app.

        Returns:
            bool: True if successful, False otherwise.
        """
        self.debug("shutting down")
        # Refuse to close if we are not done with the current project.
        if not self.project_manager.closeRunningProject():
            self.warning(
                "Not closing since running project doesn't want to close")
            return False
        if self.welcome_wizard:
            self.welcome_wizard.hide()
        if self.gui:
            self.gui.destroy()
        self.threads.stopAllThreads()
        self.settings.storeSettings()
        self.quit()
        return True

    def _setScenarioFile(self, uri):
        if uri:
            project_path = path_from_uri(uri)
        else:
            # New project.
            project_path = None
        if 'PITIVI_SCENARIO_FILE' in os.environ:
            scenario_path = os.environ['PITIVI_SCENARIO_FILE']
        else:
            cache_dir = get_dir(os.path.join(xdg_cache_home(), "scenarios"))
            scenario_name = str(time.strftime("%Y%m%d-%H%M%S"))
            if project_path:
                scenario_name += os.path.splitext(project_path.replace(os.sep, "_"))[0]
            scenario_path = os.path.join(cache_dir, scenario_name + ".scenario")

        scenario_path = path_from_uri(quote_uri(scenario_path))
        self._scenario_file = open(scenario_path, "w")

        if project_path and not project_path.endswith(".scenario"):
            # It's an xges file probably.
            with open(project_path) as project:
                content = project.read().replace("\n", "")
                self.write_action("load-project",
                                  {"serialized-content": content})

    def _newProjectLoadingCb(self, unused_project_manager, project):
        self._setScenarioFile(project.get_uri())

    def _newProjectLoaded(self, unused_project_manager, project):
        self.action_log = UndoableActionLog()
        self.action_log.connect("pre-push", self._action_log_pre_push_cb)
        self.action_log.connect("commit", self._actionLogCommit)
        self.action_log.connect("move", self._action_log_move_cb)

        self.project_observer = ProjectObserver(project, self.action_log)

    def _projectClosed(self, unused_project_manager, project):
        if project.loaded:
            self.action_log = None
            self._syncDoUndo()

        if self._scenario_file:
            self.write_action("stop")
            self._scenario_file.close()
            self._scenario_file = None

    def _checkVersion(self):
        """Checks online for new versions of the app."""
        self.info("Requesting version information async")
        giofile = Gio.File.new_for_uri(RELEASES_URL)
        giofile.load_contents_async(None, self._versionInfoReceivedCb, None)

    def _versionInfoReceivedCb(self, giofile, result, user_data):
        try:
            raw = giofile.load_contents_finish(result)[1]
            if not isinstance(raw, str):
                raw = raw.decode()
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

            VERSION_split = [int(i) for i in VERSION.split(".")]
            current_version_split = [int(i)
                                     for i in current_version.split(".")]
            if VERSION_split > current_version_split:
                status = "CURRENT"
                self.info(
                    "Running version %s, which is newer than the latest known version. Considering it as the latest current version.", VERSION)
            elif status is "UNSUPPORTED":
                self.warning(
                    "Using an outdated version of Pitivi (%s)", VERSION)

            self._version_information["current"] = current_version
            self._version_information["status"] = status
            self.emit("version-info-received", self._version_information)
        except Exception as e:
            self.warning("Version info could not be read: %s", e)

    def isLatest(self):
        """Whether the app's version is the latest as far as we know."""
        status = self._version_information.get("status")
        return status is None or status.upper() == "CURRENT"

    def getLatest(self):
        """Get the latest version of the app or None."""
        return self._version_information.get("current")

    def _quitCb(self, unused_action, unused_param):
        self.shutdown()

    def _undoCb(self, unused_action, unused_param):
        self.action_log.undo()

    def _redoCb(self, unused_action, unused_param):
        self.action_log.redo()

    def _show_shortcuts_cb(self, unused_action, unused_param):
        show_shortcuts(self)

    def _action_log_pre_push_cb(self, unused_action_log, action):
        try:
            st = action.asScenarioAction()
        except NotImplementedError:
            self.warning("No serialization method for action %s", action)
            return
        if st:
            self.write_action(st)

    def _actionLogCommit(self, action_log, unused_stack):
        if action_log.is_in_transaction():
            return
        self._syncDoUndo()

    def _action_log_move_cb(self, action_log, unused_stack):
        self._syncDoUndo()

    def _syncDoUndo(self):
        can_undo = self.action_log and bool(self.action_log.undo_stacks)
        self.undo_action.set_enabled(bool(can_undo))

        can_redo = self.action_log and bool(self.action_log.redo_stacks)
        self.redo_action.set_enabled(bool(can_redo))

        if not self.project_manager.current_project:
            return

        dirty = self.action_log and self.action_log.dirty()
        self.project_manager.current_project.setModificationState(dirty)
        # In the tests we do not want to create any gui
        if self.gui is not None:
            self.gui.showProjectStatus()
