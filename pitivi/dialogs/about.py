# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
"""Pitivi's about dialog."""
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.configure import APPNAME
from pitivi.configure import APPURL
from pitivi.configure import VERSION


class AboutDialog(Gtk.AboutDialog):
    """Pitivi's about dialog.

    Displays info regarding Pitivi's version, license,
    maintainers, contributors, etc.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Gtk.AboutDialog.__init__(self)
        self.set_program_name(APPNAME)
        self.set_website(APPURL)

        if app.is_latest():
            version_str = _("Version %s") % VERSION
        else:
            version_str = _("Version %(cur_ver)s — %(new_ver)s is available") % \
                {"cur_ver": VERSION,
                 "new_ver": app.get_latest()}
        self.set_version(version_str)

        comments = ["",
                    "GES %s" % ".".join(map(str, GES.version())),
                    "GTK+ %s" % ".".join(map(str, (Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION))),
                    "GStreamer %s" % ".".join(map(str, Gst.version()))]
        self.set_comments("\n".join(comments))

        authors = [_("Current maintainers:"),
                   "Thibault Saunier <tsaunier@gnome.org>",
                   "Mathieu Duponchelle <mduponchelle1@gmail.com>",
                   "Alexandru Băluț <alexandru.balut@gmail.com>",
                   "",
                   _("Past maintainers:"),
                   "Edward Hervey <bilboed@bilboed.com>",
                   "Alessandro Decina <alessandro.decina@collabora.co.uk>",
                   "Brandon Lewis <brandon_lewis@berkeley.edu>",
                   "Jean-François Fortin Tam <nekohayo@gmail.com>",
                   "",
                   _("Contributors:"),
                   "https://gitlab.gnome.org/GNOME/pitivi/-/graphs/master",
                   ""]
        self.set_authors(authors)
        # Translators: See
        # https://developer.gnome.org/gtk3/stable/GtkAboutDialog.html#gtk-about-dialog-set-translator-credits
        # for details on how this is used.
        translators = _("translator-credits")
        if translators != "translator-credits":
            self.set_translator_credits(translators)
        documenters = ["Jean-François Fortin Tam <nekohayo@gmail.com>", ]
        self.set_documenters(documenters)
        self.set_license_type(Gtk.License.LGPL_2_1)
        self.set_logo_icon_name("org.pitivi.Pitivi")
        self.connect("response", self.__about_response_cb)
        self.set_transient_for(app.gui)

    @staticmethod
    def __about_response_cb(dialog, unused_response):
        dialog.destroy()
