# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/dialogs/depsmanager.py
#
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

""" This module implements the notions of missing dependencies """

from gi.repository import Gtk
import os

from pitivi.configure import get_ui_dir
from pitivi.check import missing_soft_deps


class DepsManager(object):

    """Display a dialog listing missing soft dependencies.
    The sane way to query and install is by using PackageKit's InstallResource()
    """

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
        self._setDepsLabel()
        self.show()

    def _onCloseButtonClickedCb(self, unused_button):
        """ Hide on close """
        self.hide()

    def _onInstallButtonClickedCb(self, unused_button):
        """ Hide on install and try to install dependencies """
        self.hide()
        # FIXME: this is not implemented properly.
        # Here is some partially working code:

        # self.session_bus = dbus.SessionBus()
        # self.dbus_path = "/org/freedesktop/PackageKit"
        # self.dbus_name = "org.freedesktop.PackageKit"
        # self.dbus_interface = "org.freedesktop.PackageKit.Modify"
        # self.obj = self.session_bus.get_object(self.dbus_name, self.dbus_path)
        # self.iface = dbus.Interface(self.obj, self.dbus_interface)

        # soft_deps_list = missing_soft_deps.keys()

        # This line works for testing, but InstallProvideFiles
        # is not really what we want:
        # self.iface.InstallProvideFiles(self.window.window_xid,
        # soft_deps_list, "show-progress,show-finished")

        # Instead, we should be using InstallResources(xid, type, resources)
        # self.iface.InstallResources(self.window.window_xid,
        # None, soft_deps_list)

        # TODO: catch exceptions/create callbacks to _installFailedCb

    def _setDepsLabel(self):
        """
        Set the contents of the label containing the list of
        missing dependencies
        """
        label_contents = ""
        for depname, dep in missing_soft_deps.items():
            label_contents += "• %s (%s)\n" % (
                dep.modulename, dep.additional_message)
        self.builder.get_object("pkg_list").set_text(label_contents)

    def show(self):
        """Show internal window"""
        self.window.show()

    def hide(self):
        """Hide internal window"""
        self.window.hide()

    def _installFailedCb(self, unused_exception):
        """Handle the failure of installing packages."""
        self.show()
