# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
#
#       pitivi/ui/depsmanager.py
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

import gtk
import os
from gettext import gettext as _

from pitivi.configure import get_ui_dir
from pitivi.check import soft_deps


class DepsManager(object):
    """Display a dialog listing missing soft dependencies.
    The sane way to query and install is by using PackageKit's InstallResource()
    """

    def __init__(self, app):
        self.app = app
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(), "depsmanager.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("window1")
        self.show()

    def _onCloseButtonClickedCb(self, unused_button):
        self.hide()

    def _onInstallButtonClickedCb(self, unused_button):  # TODO: do stuff here
        self.hide()
        for foo in soft_deps:
            print foo
            print "\t", soft_deps[foo], "\n"

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
