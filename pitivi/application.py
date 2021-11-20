# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005-2009 Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2008-2009 Alessandro Decina <alessandro.d@gmail.com>
# Copyright (c) 2014 Alex Băluț <alexandru.balut@gmail.com>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
import os
import time
from gettext import gettext as _
from typing import Optional

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.configure import RELEASES_URL
from pitivi.configure import VERSION
from pitivi.effects import EffectsManager
from pitivi.mainwindow import MainWindow
from pitivi.pluginmanager import PluginManager
from pitivi.project import ProjectManager
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
from pitivi.utils.system import System
from pitivi.utils.threads import ThreadMaster
from pitivi.utils.timeline import Zoomable


class Pitivi(Gtk.Application, Loggable):
    """Hello world.

    Attributes:
        action_log (UndoableActionLog): The undo/redo log for the current project.
        effects (EffectsManager): The effects which can be applied to a clip.
        gui (MainWindow): The main window of the app.
        recent_manager (Gtk.RecentManager): Manages recently used projects.
        project_manager (ProjectManager): The holder of the current project.
        settings (GlobalSettings): The application-wide settings.
        system (System): The system running the app.
    """

    __gsignals__ = {
        "version-info-received": (GObject.SignalFlags.RUN_LAST, None, (object,))
    }

    def __init__(self):
        Gtk.Application.__init__(self,
                                 application_id="org.pitivi.Pitivi",
                                 flags=Gio.ApplicationFlags.NON_UNIQUE | Gio.ApplicationFlags.HANDLES_OPEN)
        Loggable.__init__(self)

        self.settings: Optional[GlobalSettings] = None
        self.threads: Optional[ThreadMaster] = None
        self.effects: Optional[EffectsManager] = None
        self.system: Optional[System] = None
        self.project_manager = ProjectManager(self)

        self.action_log: Optional[UndoableActionLog] = None
        self.project_observer: Optional[ProjectObserver] = None
        self._last_action_time: int = Gst.util_get_timestamp()

        self.gui: Optional[MainWindow] = None
        self.recent_manager = Gtk.RecentManager.get_default()
        self.__inhibit_cookies = {}

        self._version_information = {}

        self._scenario_file = None
        self._first_action = True

        Zoomable.app = self
        self.shortcuts = ShortcutsManager(self)

    def write_action(self, action, **kwargs):
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
            self._scenario_file.write(st.to_string())
            self._scenario_file.write("\n")
            self._last_action_time = now

        if not isinstance(action, Gst.Structure):
            structure = Gst.Structure.new_empty(action)

            for key, value in kwargs.items():
                key = key.replace("_", "-")
                structure[key] = value

            action = structure

        self._scenario_file.write(action.to_string())
        self._scenario_file.write("\n")
        self._scenario_file.flush()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Init logging as early as possible so we can log startup code
        enable_color = os.environ.get('PITIVI_DEBUG_NO_COLOR', '0') not in ('', '1')
        # Let's show a human-readable Pitivi debug output by default, and only
        # show a crazy unreadable mess when surrounded by gst debug statements.
        enable_crack_output = "GST_DEBUG" in os.environ
        loggable.init('PITIVI_DEBUG', enable_color, enable_crack_output)

        self.info('starting up')
        self._setup()
        self._check_version()

    def _setup(self):
        # pylint: disable=attribute-defined-outside-init
        self.settings = GlobalSettings()
        self.threads = ThreadMaster()
        self.effects = EffectsManager()
        self.proxy_manager = ProxyManager(self)
        self.system = get_system()
        self.plugin_manager = PluginManager(self)

        self.project_manager.connect("new-project-loaded", self._new_project_loaded_cb)
        self.project_manager.connect_after("project-closed", self._project_closed_cb)
        self.project_manager.connect("project-saved", self.__project_saved_cb)

        self._create_actions()
        self._sync_do_undo()

    def _create_actions(self):
        self.shortcuts.register_group("app", _("General"), position=10)

        # pylint: disable=attribute-defined-outside-init
        self.undo_action = Gio.SimpleAction.new("undo", None)
        self.undo_action.connect("activate", self._undo_cb)
        self.add_action(self.undo_action)
        self.shortcuts.add("app.undo", ["<Primary>z"], self.undo_action,
                           _("Undo the most recent action"))

        self.redo_action = Gio.SimpleAction.new("redo", None)
        self.redo_action.connect("activate", self._redo_cb)
        self.add_action(self.redo_action)
        self.shortcuts.add("app.redo", ["<Primary><Shift>z"], self.redo_action,
                           _("Redo the most recent action"))

        self.quit_action = Gio.SimpleAction.new("quit", None)
        self.quit_action.connect("activate", self._quit_cb)
        self.add_action(self.quit_action)
        self.shortcuts.add("app.quit", ["<Primary>q"], self.quit_action, _("Quit"))

        self.show_shortcuts_action = Gio.SimpleAction.new("shortcuts_window", None)
        self.show_shortcuts_action.connect("activate", self._show_shortcuts_cb)
        self.add_action(self.show_shortcuts_action)
        self.shortcuts.add("app.shortcuts_window",
                           ["<Primary>F1", "<Primary>question"],
                           self.show_shortcuts_action,
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

        self.create_main_window()
        self.gui.show_perspective(self.gui.greeter)

    def create_main_window(self):
        if self.gui:
            return
        self.gui = MainWindow(self)
        self.gui.setup_ui()
        self.add_window(self.gui)

    def do_open(self, giofiles, unused_count, unused_hint):
        assert giofiles
        self.create_main_window()
        if len(giofiles) > 1:
            self.warning("Opening only one project at a time. Ignoring the rest!")
        project_file = giofiles[0]
        self.project_manager.load_project(quote_uri(project_file.get_uri()))
        return True

    def shutdown(self):
        """Closes the app.

        Returns:
            bool: True if successful, False otherwise.
        """
        self.debug("shutting down")
        # Refuse to close if we are not done with the current project.
        if not self.project_manager.close_running_project():
            self.warning(
                "Not closing since running project doesn't want to close")
            return False
        if self.gui:
            self.gui.destroy()
        self.threads.wait_all_threads()
        self.settings.store_settings()
        self.quit()
        return True

    def _set_scenario_file(self, uri):
        if uri:
            project_path = path_from_uri(uri)
        else:
            # New project.
            project_path = None
        if 'PITIVI_SCENARIO_FILE' in os.environ:
            scenario_path = os.environ['PITIVI_SCENARIO_FILE']
        else:
            cache_dir = xdg_cache_home("scenarios")
            scenario_name = str(time.strftime("%Y%m%d-%H%M%S"))
            if project_path:
                scenario_name += os.path.splitext(project_path.replace(os.sep, "_"))[0]
            scenario_path = os.path.join(cache_dir, scenario_name + ".scenario")

        scenario_path = path_from_uri(quote_uri(scenario_path))
        # pylint: disable=consider-using-with
        self._scenario_file = open(scenario_path, "w", encoding="UTF-8")

        if project_path and not project_path.endswith(".scenario"):
            # It's an xges file probably.
            with open(project_path, encoding="UTF-8") as project:
                content = project.read().replace("\n", "")
                self.write_action("load-project", serialized_content=content)

    def _new_project_loaded_cb(self, unused_project_manager, project):
        uri = project.get_uri()
        if uri:
            # We remove the project from recent projects list
            # and then re-add it to this list to make sure it
            # gets positioned at the top of the recent projects list.
            try:
                self.recent_manager.remove_item(uri)
            except GLib.Error as e:
                if e.domain != "gtk-recent-manager-error-quark":
                    raise e
            self.recent_manager.add_item(uri)

        self.action_log = UndoableActionLog()
        self.action_log.connect("pre-push", self._action_log_pre_push_cb)
        self.action_log.connect("commit", self._action_log_commit)
        self.action_log.connect("move", self._action_log_move_cb)
        self.project_observer = ProjectObserver(project, self.action_log)

        self._set_scenario_file(project.get_uri())

    def __project_saved_cb(self, unused_project_manager, unused_project, uri):
        if uri:
            self.recent_manager.add_item(uri)

    def _project_closed_cb(self, unused_project_manager, project):
        if project.loaded:
            self.action_log = None
            self._sync_do_undo()

        if self._scenario_file:
            self.write_action("stop")
            self._scenario_file.close()
            self._scenario_file = None

    def _check_version(self):
        """Checks online for new versions of the app."""
        self.info("Requesting version information async")
        giofile = Gio.File.new_for_uri(RELEASES_URL)
        giofile.load_contents_async(None, self._version_info_received_cb, None)

    def _version_info_received_cb(self, giofile, result, user_data):
        # pylint: disable=broad-except
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

            version_split = [int(i) for i in VERSION.split(".")]
            current_version_split = [int(i)
                                     for i in current_version.split(".")]
            if version_split > current_version_split:
                status = "CURRENT"
                self.info(
                    "Running version %s, which is newer than the latest known version. Considering it as the latest current version.", VERSION)
            elif status == "UNSUPPORTED":
                self.warning(
                    "Using an outdated version of Pitivi (%s)", VERSION)

            self._version_information["current"] = current_version
            self._version_information["status"] = status
            self.emit("version-info-received", self._version_information)
        except Exception as e:
            self.warning("Version info could not be read: %s", e)

    def is_latest(self):
        """Whether the app's version is the latest as far as we know."""
        status = self._version_information.get("status")
        return status is None or status.upper() == "CURRENT"

    def get_latest(self):
        """Get the latest version of the app or None."""
        return self._version_information.get("current")

    def _quit_cb(self, unused_action, unused_param):
        self.shutdown()

    def _undo_cb(self, unused_action, unused_param):
        self.action_log.undo()

    def _redo_cb(self, unused_action, unused_param):
        self.action_log.redo()

    def _show_shortcuts_cb(self, unused_action, unused_param):
        show_shortcuts(self)

    def _action_log_pre_push_cb(self, unused_action_log, action):
        scenario_action = action.as_scenario_action()
        if scenario_action:
            self.write_action(scenario_action)

    def _action_log_commit(self, action_log, unused_stack):
        if action_log.is_in_transaction():
            return
        self._sync_do_undo()

    def _action_log_move_cb(self, action_log, unused_stack):
        self._sync_do_undo()

    def _sync_do_undo(self):
        can_undo = self.action_log and bool(self.action_log.undo_stacks)
        self.undo_action.set_enabled(bool(can_undo))

        can_redo = self.action_log and bool(self.action_log.redo_stacks)
        self.redo_action.set_enabled(bool(can_redo))

        if not self.project_manager.current_project:
            return

        dirty = self.action_log and self.action_log.dirty()
        self.project_manager.current_project.set_modification_state(dirty)
        # In the tests we do not want to create any gui
        if self.gui is not None:
            self.gui.editor.show_project_status()

    def simple_inhibit(self, reason, flags):
        """Informs the session manager about actions to be inhibited.

        Keeps track of the reasons received. A specific reason should always
        be accompanied by the same flags. Calling the method a second time
        with the same reason has no effect unless `simple_uninhibit` has been
        called in the meanwhile.

        Args:
            reason (str): The reason for which to perform the inhibition.
            flags (Gtk.ApplicationInhibitFlags): What should be inhibited.
        """
        if reason in self.__inhibit_cookies:
            self.debug("Inhibit reason already active: %s", reason)
            return
        self.debug("Inhibiting %s for %s", flags, reason)
        cookie = self.inhibit(self.gui, flags, reason)
        self.__inhibit_cookies[reason] = cookie

    def simple_uninhibit(self, reason):
        """Informs the session manager that an inhibition is not needed anymore.

        Args:
            reason (str): The reason which is not valid anymore.
        """
        try:
            cookie = self.__inhibit_cookies.pop(reason)
        except KeyError:
            self.debug("Inhibit reason not active: %s", reason)
            return
        self.debug("Uninhibiting %s", reason)
        self.uninhibit(cookie)
