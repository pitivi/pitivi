# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2009, Brandon Lewis <brandon_lewis@berkeley.edu>
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
"""Dialog for locating a missing asset."""
import os
from gettext import gettext as _

from gi.repository import Gtk

from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.medialibrary import AssetThumbnail
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import beautify_missing_asset
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SPACING


class MissingAssetDialog(Gtk.Dialog, Loggable):
    """Dialog for locating a missing asset using Gtk.FileChooserWidget.

    Attributes:
        app (Pitivi): The app.
        asset (GES.UriClipAsset): The missing asset.
        uri (str): Last known URI of the missing asset.
    """

    def __init__(self, app, asset, uri):
        Gtk.Dialog.__init__(self)
        Loggable.__init__(self)

        self.set_title(_("Locate missing file..."))
        self.set_modal(True)
        self.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                         _("Open"), Gtk.ResponseType.OK)
        self.set_border_width(SPACING * 2)
        self.get_content_area().set_spacing(SPACING)
        self.set_transient_for(app.gui)
        self.set_default_response(Gtk.ResponseType.OK)

        # This box will contain widgets with details about the missing file.
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)

        label_start = Gtk.Label()
        label_start.set_markup(_("The following file could not be found:"))
        label_start.set_xalign(0)
        vbox.pack_start(label_start, False, False, 0)

        hbox = Gtk.Box()
        hbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        hbox.set_margin_top(PADDING)
        hbox.set_spacing(PADDING * 2)

        label_asset_info = Gtk.Label()
        label_asset_info.set_markup(beautify_missing_asset(asset))
        label_asset_info.set_xalign(0)
        label_asset_info.set_yalign(0)
        hbox.pack_start(label_asset_info, False, False, 0)

        unused_small_thumb, large_thumb = AssetThumbnail.get_thumbnails_from_xdg_cache(uri)
        if large_thumb:
            self.debug("A thumbnail file was found for %s", uri)
            thumbnail = Gtk.Image.new_from_pixbuf(large_thumb)
            hbox.pack_end(thumbnail, False, False, 0)

        vbox.pack_start(hbox, False, False, 0)

        label_end = Gtk.Label()
        label_end.set_markup(_("Please specify its new location:"))
        label_end.set_xalign(0)
        label_end.set_margin_top(PADDING)
        vbox.pack_start(label_end, False, False, 0)

        self.get_content_area().pack_start(vbox, False, False, 0)
        vbox.show_all()

        self._chooser = self.__setup_file_chooser(uri, app.settings)
        self.get_content_area().pack_start(self._chooser, True, True, 0)
        self._chooser.show()

        # If the window is too big, the window manager will resize it so that
        # it fits on the screen.
        self.set_default_size(1024, 1000)

    @staticmethod
    def __setup_file_chooser(uri, settings):
        chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN)
        chooser.set_select_multiple(False)
        previewer = PreviewWidget(settings, discover_sync=True)
        chooser.set_preview_widget(previewer)
        chooser.set_use_preview_label(False)
        chooser.connect("update-preview", previewer.update_preview_cb)
        chooser.set_current_folder(settings.lastProjectFolder)
        # Use a Gtk FileFilter to only show files with the same extension
        # Note that splitext gives us the extension with the ".", no need to
        # add it inside the filter string.
        unused_filename, extension = os.path.splitext(uri)
        filter_ = Gtk.FileFilter()
        # Translators: this is a format filter in a filechooser. Ex: "AVI files"
        filter_.set_name(_("%s files") % extension)
        filter_.add_pattern("*%s" % extension.lower())
        filter_.add_pattern("*%s" % extension.upper())
        default = Gtk.FileFilter()
        default.set_name(_("All files"))
        default.add_pattern("*")
        chooser.add_filter(filter_)
        chooser.add_filter(default)
        return chooser

    def get_new_uri(self):
        """Returns new URI of the missing asset, if provided by the user."""
        response = self.run()
        if response == Gtk.ResponseType.OK:
            self.log("User chose a new URI for the missing file")
        return self._chooser.get_uri()
