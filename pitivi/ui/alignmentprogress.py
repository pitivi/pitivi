# PiTiVi , Non-linear video editor
#
#       ui/alignmentprogress.py
#
# Copyright (c) 2010, Brandon Lewis <brandon.lewis@collabora.co.uk>
# Copyright (c) 2011, Benjamin M. Schwartz <bens@alum.mit.edu>
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
Basic auto-alignment progress dialog, based on the EncodingProgressDialog
"""

import os
from gettext import gettext as _

import gobject
import gtk
import gst

import pitivi.configure as configure
from pitivi.utils.signal import Signallable


class AlignmentProgressDialog:
    """ Dialog indicating the progress of the auto-alignment process.
        Code derived from L{EncodingProgressDialog}, but greatly simplified
        (read-only, no buttons)."""

    def __init__(self, app):
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(configure.get_ui_dir(),
                                   "alignmentprogress.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("align-progress")
        self.progressbar = self.builder.get_object("progressbar")
        # Parent this dialog with mainwindow
        # set_transient_for allows this dialog to properly
        # minimize together with the mainwindow.  This method is
        # taken from EncodingProgressDialog.  In both cases, it appears
        # to work correctly, although there is a known bug for Gnome 3 in
        # EncodingProgressDialog (bug #652917)
        self.window.set_transient_for(app.gui)

        # UI widgets
        # We currently reuse the render icon for this dialog.
        icon_path = os.path.join(configure.get_pixmap_dir(),
                                 "pitivi-render-16.png")
        self.window.set_icon_from_file(icon_path)

        # FIXME: Add a cancel button

    def updatePosition(self, fraction, estimated):
        self.progressbar.set_fraction(fraction)
        self.window.set_title(_("%d%% Analyzed") % int(100 * fraction))
        if estimated:
            # Translators: This string indicates the estimated time
            # remaining until the action completes.  The "%s" is an
            # already-localized human-readable duration description like
            # "31 seconds".
            self.progressbar.set_text(_("About %s left") % estimated)
