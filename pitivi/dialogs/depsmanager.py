# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
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

from gi.repository import Gtk
import os

from pitivi.configure import get_ui_dir
from pitivi.check import soft_deps


class DepsManager(object):
    """Display a dialog listing missing soft dependencies.
    The sane way to query and install is by using PackageKit's InstallResource()
    """

    def __init__(self, app):
        self.app = app
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(), "depsmanager.ui"))
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("window1")

        # FIXME: autodetect if we can actually use PackageKit's "InstallResource" dbus
        # method, and if yes, show this button.
        self.builder.get_object("install_btn").hide()
        self.show()

    def _onCloseButtonClickedCb(self, unused_button):
        self.hide()

    def _onInstallButtonClickedCb(self, unused_button):
        self.hide()
        """
        # FIXME: this is not implemented properly. Here is some partially working code:

        self.session_bus = dbus.SessionBus()
        self.dbus_path = "/org/freedesktop/PackageKit"
        self.dbus_name = "org.freedesktop.PackageKit"
        self.dbus_interface = "org.freedesktop.PackageKit.Modify"
        self.obj = self.session_bus.get_object(self.dbus_name, self.dbus_path)
        self.iface = dbus.Interface(self.obj, self.dbus_interface)

        soft_deps_list = []
        for dep in soft_deps:
            soft_deps_list.append(dep)

        # This line works for testing, but InstallProvideFiles is not really what we want:
        #self.iface.InstallProvideFiles(self.window.window_xid, soft_deps_list, "show-progress,show-finished")

        # Instead, we should be using InstallResources(xid, type, resources)
        self.iface.InstallResources(self.window.window_xid, None, soft_deps_list)
        """
        # TODO: catch exceptions/create callbacks to _installFailedCb

    def _setDepsLabel(self):
        """Set the contents of the label containing the list of missing dependencies"""
        label_contents = ""
        for dep in soft_deps:
            label_contents += u"• " + dep + " (" + soft_deps[dep] + ")\n"
        self.builder.get_object("pkg_list").set_text(label_contents)

    def show(self):
        self.window.set_transient_for(self.app.gui)
        self.window.set_modal(True)
        self._setDepsLabel()
        self.window.show()
        self.window.grab_focus()

    def hide(self):
        self.window.hide()

    def _installFailedCb(self, unused_exception):
        """Handle the failure of installing packages."""
        self.show()
