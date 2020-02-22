# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2011 Jean-François Fortin Tam <nekohayo@gmail.com>
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
"""Missing dependencies logic."""
import os

from gi.repository import Gtk

from pitivi.check import MISSING_SOFT_DEPS
from pitivi.configure import get_ui_dir


class DepsManager:
    """Manages a dialog listing missing soft dependencies."""

    def __init__(self, app, parent_window=None):
        self.app = app
        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "depsmanager.ui"))
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("window1")
        self.window.set_modal(True)
        if parent_window:
            self.window.set_transient_for(parent_window)
        else:
            self.window.set_transient_for(self.app.gui)
        # Same hack as in the rendering progress dialog,
        # to prevent GTK3 from eating a crazy amount of vertical space:
        self.window.set_resizable(False)

        # FIXME: autodetect if we can actually use PackageKit's
        # "InstallResource" dbus method, and if yes, show this button.
        self.builder.get_object("install_btn").hide()
        self._set_deps_label()
        self.show()

    def _on_close_button_clicked_cb(self, unused_button):
        """Hides the dialog."""
        self.hide()

    def _on_install_button_clicked_cb(self, unused_button):
        """Hides on install and tries to install dependencies."""
        self.hide()
        # FIXME: this is not implemented properly.
        # Here is some partially working code:

        # self.session_bus = dbus.SessionBus()
        # self.dbus_path = "/org/freedesktop/PackageKit"
        # self.dbus_name = "org.freedesktop.PackageKit"
        # self.dbus_interface = "org.freedesktop.PackageKit.Modify"
        # self.obj = self.session_bus.get_object(self.dbus_name, self.dbus_path)
        # self.iface = dbus.Interface(self.obj, self.dbus_interface)

        # soft_deps_list = MISSING_SOFT_DEPS.keys()

        # This line works for testing, but InstallProvideFiles
        # is not really what we want:
        # self.iface.InstallProvideFiles(self.window.window_xid,
        # soft_deps_list, "show-progress,show-finished")

        # Instead, we should be using InstallResources(xid, type, resources)
        # self.iface.InstallResources(self.window.window_xid,
        # None, soft_deps_list)

        # TODO: catch exceptions/create callbacks to _install_failed_cb

    def _set_deps_label(self):
        """Updates the UI to display the list of missing dependencies."""
        label_contents = ""
        for dep in MISSING_SOFT_DEPS.items():
            label_contents += "• %s (%s)\n" % (
                dep.modulename, dep.additional_message)
        self.builder.get_object("pkg_list").set_text(label_contents)

    def show(self):
        """Shows the dialog."""
        self.window.show()

    def hide(self):
        """Hides the dialog."""
        self.window.hide()

    def _install_failed_cb(self, unused_exception):
        """Handles the failure of installing packages."""
        self.show()
