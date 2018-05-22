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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gtk


class BrowseProjectsDialog(object):
    """Displays the Gtk.FileChooserDialog for browsing projects.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        self.app = app
        self.__create_and_show_dialog()

    def __create_and_show_dialog(self):
        # Requesting project closure at this point in time prompts users about
        # unsaved changes (if any); much better than having ProjectManager
        # trigger this *after* the user already chose a new project to load...
        if not self.app.project_manager.closeRunningProject():
            return  # The user has not made a decision, don't do anything.

        chooser = Gtk.FileChooserDialog(title=_("Open File..."),
                                        transient_for=self.app.gui,
                                        action=Gtk.FileChooserAction.OPEN)
        chooser.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                            _("Open"), Gtk.ResponseType.OK)
        chooser.set_default_response(Gtk.ResponseType.OK)
        chooser.set_select_multiple(False)
        # TODO: Remove this set_current_folder call when GTK bug 683999 is
        # fixed
        chooser.set_current_folder(self.app.settings.lastProjectFolder)
        formatter_assets = GES.list_assets(GES.Formatter)
        formatter_assets.sort(
            key=lambda x: - x.get_meta(GES.META_FORMATTER_RANK))
        for format_ in formatter_assets:
            filt = Gtk.FileFilter()
            filt.set_name(format_.get_meta(GES.META_DESCRIPTION))
            filt.add_pattern("*%s" %
                             format_.get_meta(GES.META_FORMATTER_EXTENSION))
            chooser.add_filter(filt)
        default = Gtk.FileFilter()
        default.set_name(_("All supported formats"))
        default.add_custom(Gtk.FileFilterFlags.URI, self.__canLoadUri, None)
        chooser.add_filter(default)

        response = chooser.run()
        uri = chooser.get_uri()
        chooser.destroy()

        if response == Gtk.ResponseType.OK:
            self.app.gui.show_main_window()
            self.app.project_manager.loadProject(uri)
        else:
            self.app.gui.show_welcome_window()

    def __canLoadUri(self, filterinfo, unused_uri):
        try:
            return GES.Formatter.can_load_uri(filterinfo.uri)
        except:
            return False
