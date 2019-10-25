# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
# Copyright (c) 2012, Jean-François Fortin Tam <nekohayo@gmail.com>
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
import subprocess
import sys
import time
from gettext import gettext as _
from gettext import ngettext
from hashlib import md5

import cairo
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_pixmap_dir
from pitivi.configure import get_ui_dir
from pitivi.dialogs.clipmediaprops import ClipMediaPropsDialog
from pitivi.dialogs.filelisterrordialog import FileListErrorDialog
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.settings import GlobalSettings
from pitivi.timeline.previewers import AssetPreviewer
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import disconnectAllByFunc
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import PathWalker
from pitivi.utils.misc import quote_uri
from pitivi.utils.misc import show_user_manual
from pitivi.utils.proxy import get_proxy_target
from pitivi.utils.proxy import ProxyingStrategy
from pitivi.utils.proxy import ProxyManager
from pitivi.utils.ui import beautify_asset
from pitivi.utils.ui import beautify_ETA
from pitivi.utils.ui import FILE_TARGET_ENTRY
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import info_name
from pitivi.utils.ui import LARGE_THUMB_WIDTH
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SMALL_THUMB_WIDTH
from pitivi.utils.ui import SPACING
from pitivi.utils.ui import URI_TARGET_ENTRY

# Values used in the settings file.
SHOW_TREEVIEW = 1
SHOW_ICONVIEW = 2

GlobalSettings.addConfigSection('clip-library')
GlobalSettings.addConfigOption('lastImportFolder',
                               section='clip-library',
                               key='last-folder',
                               environment='PITIVI_IMPORT_FOLDER',
                               default=os.path.expanduser("~"))
GlobalSettings.addConfigOption('closeImportDialog',
                               section='clip-library',
                               key='close-import-dialog-after-import',
                               default=True)
GlobalSettings.addConfigOption('lastClipView',
                               section='clip-library',
                               key='last-clip-view',
                               type_=int,
                               default=SHOW_ICONVIEW)

STORE_MODEL_STRUCTURE = (
    GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf,
    str, object, str, str, object)

(COL_ICON_64,
 COL_ICON_128,
 COL_INFOTEXT,
 COL_ASSET,
 COL_URI,
 COL_SEARCH_TEXT,
 COL_THUMB_DECORATOR) = list(range(len(STORE_MODEL_STRUCTURE)))

# This whitelist is made from personal knowledge of file extensions in the wild,
# from gst-inspect |grep demux,
# http://en.wikipedia.org/wiki/Comparison_of_container_formats and
# http://en.wikipedia.org/wiki/List_of_file_formats#Video
# ...and looking at the contents of /usr/share/mime
SUPPORTED_FILE_FORMATS = {
    "video": ("3gpp", "3gpp2", "dv", "mp2t", "mp2t", "mp4", "mpeg", "ogg",
              "quicktime", "webm", "x-flv", "x-matroska", "x-mng", "x-ms-asf",
              "x-ms-wmp", "x-ms-wmv", "x-msvideo", "x-ogm+ogg", "x-theora+ogg"),
    "application": ("mxf",),
    "audio": ("aac", "ac3", "basic", "flac", "mp2", "mp4", "mpeg", "ogg",
              "opus", "webm", "x-adpcm", "x-aifc", "x-aiff", "x-aiffc",
              "x-ape", "x-flac+ogg", "x-m4b", "x-matroska", "x-ms-asx",
              "x-ms-wma", "x-speex", "x-speex+ogg", "x-vorbis+ogg", "x-wav"),
    "image": ("jp2", "jpeg", "png", "svg+xml")}

SUPPORTED_MIMETYPES = []
for category, mime_types in SUPPORTED_FILE_FORMATS.items():
    for mime in mime_types:
        SUPPORTED_MIMETYPES.append(category + "/" + mime)


class FileChooserExtraWidget(Gtk.Box, Loggable):

    def __init__(self, app):
        Loggable.__init__(self)
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        self.app = app

        self.__keep_open_check = Gtk.CheckButton(label=_("Keep dialog open"))
        self.__keep_open_check.props.valign = Gtk.Align.START
        self.__keep_open_check.set_tooltip_text(_("When importing files keep the dialog open"))
        self.__keep_open_check.set_active(not self.app.settings.closeImportDialog)
        self.pack_start(self.__keep_open_check, expand=False, fill=False, padding=0)

        self.hq_proxy_check = Gtk.CheckButton.new()
        # Translators: Create optimized media for unsupported files.
        self.hq_proxy_check.set_label(_("Optimize:"))
        self.hq_proxy_check.connect("toggled", self._hq_proxy_check_cb)

        self.hq_combo = Gtk.ComboBoxText.new()
        self.hq_combo.insert_text(0, _("Unsupported assets"))
        self.hq_combo.insert_text(1, _("All"))
        self.hq_combo.props.active = 0
        self.hq_combo.set_sensitive(False)

        self.help_button = Gtk.Button()
        self.__update_help_button()
        self.help_button.props.relief = Gtk.ReliefStyle.NONE
        self.help_button.connect("clicked", self._help_button_clicked_cb)

        self.scaled_proxy_check = Gtk.CheckButton.new()
        self.__update_scaled_proxy_check()
        self.scaled_proxy_check.connect("toggled", self._scaled_proxy_check_cb)

        self.project_settings_label = Gtk.Label()
        self.project_settings_label.set_markup("<a href='#'>%s</a>" % _("Project Settings"))
        self.project_settings_label.connect("activate-link", self._target_res_cb)

        proxy_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        hq_proxy_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hq_proxy_row.pack_start(self.hq_proxy_check, expand=False, fill=False, padding=0)
        hq_proxy_row.pack_start(self.hq_combo, expand=False, fill=False, padding=PADDING)
        hq_proxy_row.pack_start(self.help_button, expand=False, fill=False, padding=SPACING)
        proxy_box.pack_start(hq_proxy_row, expand=False, fill=False, padding=0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row.pack_start(self.scaled_proxy_check, expand=False, fill=False, padding=0)
        row.pack_start(self.project_settings_label, expand=False, fill=False, padding=SPACING)
        proxy_box.pack_start(row, expand=False, fill=False, padding=0)

        self.pack_start(proxy_box, expand=False, fill=False, padding=SPACING * 2)

        self.show_all()

        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)
        size_group.add_widget(self.__keep_open_check)
        size_group.add_widget(hq_proxy_row)

        if self.app.settings.proxyingStrategy == ProxyingStrategy.AUTOMATIC:
            self.hq_proxy_check.set_active(True)
            self.hq_combo.set_sensitive(True)
            self.hq_combo.props.active = 0
        elif self.app.settings.proxyingStrategy == ProxyingStrategy.ALL:
            self.hq_proxy_check.set_active(True)
            self.hq_combo.set_sensitive(True)
            self.hq_combo.props.active = 1

        if self.app.settings.auto_scaling_enabled:
            self.scaled_proxy_check.set_active(True)

    def _hq_proxy_check_cb(self, check_button):
        active = check_button.get_active()
        self.hq_combo.set_sensitive(active)
        self.__update_help_button()

        if not active:
            self.scaled_proxy_check.set_active(False)

    def __update_help_button(self):
        if self.hq_proxy_check.get_active():
            icon = "question-round-symbolic"
        else:
            icon = "warning-symbolic"
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        self.help_button.set_image(image)

    def _help_button_clicked_cb(self, unused_button):
        show_user_manual("importing")

    def _scaled_proxy_check_cb(self, unused_button):
        if self.scaled_proxy_check.get_active():
            self.hq_proxy_check.set_active(True)

    def _target_res_cb(self, label_widget, unused_uri):
        self.app.gui.editor.showProjectSettingsDialog()
        self.__update_scaled_proxy_check()

    def __update_scaled_proxy_check(self):
        target_width = self.app.project_manager.current_project.scaled_proxy_width
        target_height = self.app.project_manager.current_project.scaled_proxy_height
        self.scaled_proxy_check.set_label(_("Scale assets larger than %s×%s px.") % (target_width, target_height))

    def saveValues(self):
        self.app.settings.closeImportDialog = not self.__keep_open_check.get_active()

        if self.hq_proxy_check.get_active():
            if self.hq_combo.props.active == 0:
                self.app.settings.proxyingStrategy = ProxyingStrategy.AUTOMATIC
            else:
                self.app.settings.proxyingStrategy = ProxyingStrategy.ALL
        else:
            assert not self.scaled_proxy_check.get_active()
            self.app.settings.proxyingStrategy = ProxyingStrategy.NOTHING

        self.app.settings.auto_scaling_enabled = self.scaled_proxy_check.get_active()


class AssetThumbnail(GObject.Object, Loggable):
    """Provider of decorated thumbnails for an asset.

    The small_thumb and large_thumb fields hold the thumbs decorated
    according to the status of the asset.
    """

    __gsignals__ = {
        # Emitted when small_thumb and large_thumb changed.
        "thumb-updated": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    EMBLEMS = {}
    PROXIED = "asset-proxied"
    SCALED = "asset-scaled"
    NO_PROXY = "no-proxy"
    IN_PROGRESS = "asset-proxy-in-progress"
    ASSET_PROXYING_ERROR = "asset-proxying-error"
    UNSUPPORTED = "asset-unsupported"

    DEFAULT_ALPHA = 255

    icons_by_name = {}

    for status in [PROXIED, SCALED, IN_PROGRESS, ASSET_PROXYING_ERROR, UNSUPPORTED]:
        EMBLEMS[status] = GdkPixbuf.Pixbuf.new_from_file_at_size(
            os.path.join(get_pixmap_dir(), "%s.svg" % status), 64, 64)

    def __init__(self, asset, proxy_manager):
        GObject.Object.__init__(self)
        Loggable.__init__(self)
        self.__asset = asset
        self.proxy_manager = proxy_manager
        self.__previewer = None
        self.refresh()

    def refresh(self):
        """Updates the shown icon. To be called when a new icon is available."""
        self.src_small, self.src_large = self.__get_thumbnails()
        self.decorate()

    def disregard_previewer(self):
        if self.__previewer:
            self.__previewer.disconnect_by_func(self.__done_cb)
            self.__previewer.stop_generation()
            self.__previewer = None

        self.refresh()
        self.emit("thumb-updated")

    def __get_thumbnails(self):
        """Gets the base source thumbnails.

        Returns:
            List[GdkPixbuf.Pixbuf]: The small thumbnail and the large thumbnail
            to be decorated.
        """
        video_streams = [
            stream_info
            for stream_info in self.__asset.get_info().get_stream_list()
            if isinstance(stream_info, GstPbutils.DiscovererVideoInfo)]
        if video_streams:
            # Check if the files have thumbnails in the user's cache directory.
            real_uri = get_proxy_target(self.__asset).props.id
            small_thumb, large_thumb = self.get_thumbnails_from_xdg_cache(real_uri)
            if not small_thumb:
                if self.__asset.is_image():
                    path = Gst.uri_get_location(real_uri)
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
                        width = pixbuf.props.width
                        height = pixbuf.props.height
                        small_thumb = pixbuf.scale_simple(
                            SMALL_THUMB_WIDTH,
                            SMALL_THUMB_WIDTH * height / width,
                            GdkPixbuf.InterpType.BILINEAR)
                        large_thumb = pixbuf.scale_simple(
                            LARGE_THUMB_WIDTH,
                            LARGE_THUMB_WIDTH * height / width,
                            GdkPixbuf.InterpType.BILINEAR)
                    except GLib.Error as error:
                        self.debug("Failed loading thumbnail because: %s", error)
                        small_thumb, large_thumb = self.__get_icons("image-x-generic")
                else:
                    # Build or reuse a ThumbnailCache.
                    if not self.__previewer:
                        self.__previewer = AssetPreviewer(self.__asset, 90)
                        self.__previewer.connect("done", self.__done_cb)
                    small_thumb = self.__previewer.thumb_cache.get_preview_thumbnail()
                    if not small_thumb:
                        # We'll be notified when the thumbnail is available.
                        small_thumb, large_thumb = self.__get_icons("video-x-generic")
                    else:
                        width = small_thumb.props.width
                        height = small_thumb.props.height
                        large_thumb = small_thumb.scale_simple(
                            LARGE_THUMB_WIDTH,
                            LARGE_THUMB_WIDTH * height / width,
                            GdkPixbuf.InterpType.BILINEAR)
                        if width > SMALL_THUMB_WIDTH:
                            small_thumb = small_thumb.scale_simple(
                                SMALL_THUMB_WIDTH,
                                SMALL_THUMB_WIDTH * height / width,
                                GdkPixbuf.InterpType.BILINEAR)
        else:
            small_thumb, large_thumb = self.__get_icons("audio-x-generic")
        return small_thumb, large_thumb

    def __done_cb(self, unused_asset_previewer):
        """Handles the done signal of our AssetPreviewer."""
        self.refresh()
        self.emit("thumb-updated")

    @staticmethod
    def get_asset_thumbnails_path(real_uri):
        """Gets normal & large thumbnail path for the asset in the XDG cache.

        Returns:
            List[str]: The path of normal thumbnail and large thumbnail.
        """
        quoted_uri = quote_uri(real_uri)
        thumbnail_hash = md5(quoted_uri.encode()).hexdigest()
        thumb_dir = os.path.join(GLib.get_user_cache_dir(), "thumbnails")
        return os.path.join(thumb_dir, "normal", thumbnail_hash + ".png"),\
            os.path.join(thumb_dir, "large", thumbnail_hash + ".png")

    @classmethod
    def get_thumbnails_from_xdg_cache(cls, real_uri):
        """Gets pixbufs for the specified thumbnail from the user's cache dir.

        Looks for thumbnails according to the [Thumbnail Managing Standard](https://specifications.freedesktop.org/thumbnail-spec/thumbnail-spec-latest.html#DIRECTORY).

        Args:
            real_uri (str): The URI of the asset.

        Returns:
            List[GdkPixbuf.Pixbuf]: The small thumbnail and the large thumbnail,
            if available in the user's cache directory, otherwise (None, None).
        """
        path_128, path_256 = cls.get_asset_thumbnails_path(real_uri)
        interpolation = GdkPixbuf.InterpType.BILINEAR

        # The cache dirs might have resolutions of 256 and/or 128,
        # while we need 128 (for iconview) and 64 (for listview).
        # First, try the 128 version since that's the native resolution we want.
        try:
            large_thumb = GdkPixbuf.Pixbuf.new_from_file(path_128)
            w, h = large_thumb.get_width(), large_thumb.get_height()
            small_thumb = large_thumb.scale_simple(w / 2, h / 2, interpolation)
            return small_thumb, large_thumb
        except GLib.GError:
            # path_128 doesn't exist, try the 256 version.
            try:
                thumb_256 = GdkPixbuf.Pixbuf.new_from_file(path_256)
                w, h = thumb_256.get_width(), thumb_256.get_height()
                large_thumb = thumb_256.scale_simple(w / 2, h / 2, interpolation)
                small_thumb = thumb_256.scale_simple(w / 4, h / 4, interpolation)
                return small_thumb, large_thumb
            except GLib.GError:
                return None, None

    @classmethod
    def __get_icons(cls, icon_name):
        if icon_name not in cls.icons_by_name:
            small_icon = cls.__get_icon(icon_name, SMALL_THUMB_WIDTH)
            large_icon = cls.__get_icon(icon_name, LARGE_THUMB_WIDTH)
            cls.icons_by_name[icon_name] = (small_icon, large_icon)
        return cls.icons_by_name[icon_name]

    @classmethod
    def __get_icon(cls, icon_name, size):
        icon_theme = Gtk.IconTheme.get_default()
        try:
            icon = icon_theme.load_icon(icon_name, size, Gtk.IconLookupFlags.FORCE_SIZE)
        except GLib.Error:
            icon = icon_theme.load_icon("dialog-question", size, 0)
        return icon

    def _set_state(self):
        asset = self.__asset
        target = asset.get_proxy_target()
        target_is_valid = target and not target.get_error()
        if self.proxy_manager.is_scaled_proxy(asset) and target_is_valid:
            # The asset is a scaled proxy.
            self.state = self.SCALED
        elif self.proxy_manager.is_hq_proxy(asset) and target_is_valid:
            # The asset is a HQ proxy.
            self.state = self.PROXIED
        elif not self.proxy_manager.is_proxy_asset(asset) and asset.proxying_error:
            self.state = self.ASSET_PROXYING_ERROR
        elif self.proxy_manager.is_asset_queued(asset):
            self.state = self.IN_PROGRESS
        elif not asset.is_image() and not self.proxy_manager.isAssetFormatWellSupported(asset):
            self.state = self.UNSUPPORTED
        else:
            self.state = self.NO_PROXY

    def decorate(self):
        self._set_state()
        if self.state == self.NO_PROXY:
            self.small_thumb = self.src_small
            self.large_thumb = self.src_large
            return

        self.small_thumb = self.src_small.copy()
        self.large_thumb = self.src_large.copy()

        for thumb in [self.small_thumb, self.large_thumb]:
            emblem = self.EMBLEMS[self.state]
            if thumb.get_height() < emblem.get_height() or \
                    thumb.get_width() < emblem.get_width():
                width = min(emblem.get_width(), thumb.get_width())
                height = min(emblem.get_height(), thumb.get_height())
                # Crop the emblem to fit the thumbnail.
                emblem = emblem.new_subpixbuf(0, emblem.get_height() - height,
                                              width, height)

            # The dest_* arguments define the area of thumb to change.
            # The offset_* arguments define the emblem offset so its
            # bottom-left corner matches the thumb's bottom-left corner.
            emblem.composite(thumb,
                             dest_x=0,
                             dest_y=thumb.get_height() - emblem.get_height(),
                             dest_width=emblem.get_width(),
                             dest_height=emblem.get_height(),
                             offset_x=0,
                             offset_y=thumb.get_height() - emblem.get_height(),
                             scale_x=1.0, scale_y=1.0,
                             interp_type=GdkPixbuf.InterpType.BILINEAR,
                             overall_alpha=self.DEFAULT_ALPHA)


class MediaLibraryWidget(Gtk.Box, Loggable):
    """Widget for managing assets.

    Attributes:
        app (Pitivi): The app.
    """

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_LAST, None,
                 (GObject.TYPE_PYOBJECT,))}

    def __init__(self, app):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)

        self._pending_assets = []

        self.app = app
        self._errors = []
        self._project = None
        self._draggedPaths = None
        self.dragged = False
        self.clip_view = self.app.settings.lastClipView
        if self.clip_view not in (SHOW_TREEVIEW, SHOW_ICONVIEW):
            self.clip_view = SHOW_ICONVIEW
        self.import_start_time = time.time()
        self._last_imported_uris = set()
        self.__last_proxying_estimate_time = _("Unknown")

        self.set_orientation(Gtk.Orientation.VERTICAL)
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "medialibrary.ui"))
        builder.connect_signals(self)
        self._welcome_infobar = builder.get_object("welcome_infobar")
        fix_infobar(self._welcome_infobar)
        self._project_settings_infobar = Gtk.InfoBar()
        self._project_settings_infobar.hide()
        self._project_settings_infobar.set_message_type(Gtk.MessageType.OTHER)
        self._project_settings_infobar.set_show_close_button(True)
        self._project_settings_infobar.add_button(_("Project Settings"), Gtk.ResponseType.OK)
        self._project_settings_infobar.connect("response", self.__projectSettingsSetInfobarCb)
        self._project_settings_label = Gtk.Label()
        self._project_settings_label.set_line_wrap(True)
        self._project_settings_label.show()
        content_area = self._project_settings_infobar.get_content_area()
        content_area.add(self._project_settings_label)

        fix_infobar(self._project_settings_infobar)
        self._import_warning_infobar = builder.get_object("warning_infobar")
        fix_infobar(self._import_warning_infobar)
        self._import_warning_infobar.hide()
        self._import_warning_infobar.connect("response", self.__warningInfobarCb)
        self._warning_label = builder.get_object("warning_label")
        self._view_error_button = builder.get_object("view_error_button")
        toolbar = builder.get_object("medialibrary_toolbar")
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        self._import_button = builder.get_object("media_import_button")
        self._clipprops_button = builder.get_object("media_props_button")
        self._listview_button = builder.get_object("media_listview_button")
        searchEntry = builder.get_object("media_search_entry")

        # Store
        self.storemodel = Gtk.ListStore(*STORE_MODEL_STRUCTURE)
        self.storemodel.set_sort_func(
            COL_URI, MediaLibraryWidget.compare_basename)
        # Prefer to sort the media library elements by URI
        # rather than show them randomly.
        self.storemodel.set_sort_column_id(COL_URI, Gtk.SortType.ASCENDING)
        self.storemodel.connect("row-deleted", self.__updateViewCb)
        self.storemodel.connect("row-inserted", self.__updateViewCb)

        # Scrolled Windows
        self.treeview_scrollwin = Gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.treeview_scrollwin.get_accessible().set_name(
            "media_listview_scrollwindow")

        self.iconview_scrollwin = Gtk.ScrolledWindow()
        self.iconview_scrollwin.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.iconview_scrollwin.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.iconview_scrollwin.get_accessible().set_name(
            "media_iconview_scrollwindow")

        # Filtering model for the search box.
        # Use this instead of using self.storemodel directly
        self.modelFilter = self.storemodel.filter_new()
        self.modelFilter.set_visible_func(
            self._setRowVisible, data=searchEntry)

        # TreeView
        # Displays icon, name, type, length
        self.treeview = Gtk.TreeView(model=self.modelFilter)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.connect(
            "button-press-event", self._treeViewButtonPressEventCb)
        self.treeview.connect(
            "button-release-event", self._treeViewButtonReleaseEventCb)
        self.treeview.connect("row-activated", self._itemOrRowActivatedCb)
        self.treeview.set_headers_visible(False)
        self.treeview.set_property("search_column", COL_SEARCH_TEXT)
        tsel = self.treeview.get_selection()
        tsel.set_mode(Gtk.SelectionMode.MULTIPLE)
        tsel.connect("changed", self._viewSelectionChangedCb)

        pixbufcol = Gtk.TreeViewColumn(_("Icon"))
        pixbufcol.set_expand(False)
        pixbufcol.set_spacing(SPACING)
        self.treeview.append_column(pixbufcol)
        pixcell = Gtk.CellRendererPixbuf()
        pixcell.props.xpad = PADDING
        pixcell.props.ypad = PADDING
        pixcell.set_alignment(0, 0)
        pixbufcol.pack_start(pixcell, True)
        pixbufcol.add_attribute(pixcell, 'pixbuf', COL_ICON_64)

        namecol = Gtk.TreeViewColumn(_("Information"))
        self.treeview.append_column(namecol)
        namecol.set_expand(True)
        namecol.set_spacing(SPACING)
        namecol.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)
        namecol.set_min_width(150)
        txtcell = Gtk.CellRendererText()
        txtcell.set_property("ellipsize", Pango.EllipsizeMode.START)
        txtcell.set_alignment(0, 0)
        namecol.pack_start(txtcell, True)
        namecol.add_attribute(txtcell, "markup", COL_INFOTEXT)

        # IconView
        self.iconview = Gtk.IconView(model=self.modelFilter)
        self.iconview_scrollwin.add(self.iconview)
        self.iconview.connect(
            "button-press-event", self._iconViewButtonPressEventCb)
        self.iconview.connect(
            "button-release-event", self._iconViewButtonReleaseEventCb)
        self.iconview.connect("item-activated", self._itemOrRowActivatedCb)
        self.iconview.connect(
            "selection-changed", self._viewSelectionChangedCb)
        self.iconview.set_item_orientation(Gtk.Orientation.VERTICAL)
        self.iconview.set_property("has_tooltip", True)
        self.iconview.set_tooltip_column(COL_INFOTEXT)
        self.iconview.props.item_padding = PADDING / 2
        self.iconview.props.margin = PADDING / 2
        self.iconview_cursor_pos = None

        cell = Gtk.CellRendererPixbuf()
        self.iconview.pack_start(cell, False)
        self.iconview.add_attribute(cell, "pixbuf", COL_ICON_128)

        cell = Gtk.CellRendererText()
        cell.props.alignment = Pango.Alignment.CENTER
        cell.props.xalign = 0.5
        cell.props.yalign = 0.0
        cell.props.xpad = 0
        cell.props.ypad = 0
        cell.set_property("ellipsize", Pango.EllipsizeMode.START)
        self.iconview.pack_start(cell, False)
        self.iconview.add_attribute(cell, "markup", COL_SEARCH_TEXT)

        self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        # The _progressbar that shows up when importing clips
        self._progressbar = Gtk.ProgressBar()
        self._progressbar.set_show_text(True)

        # Connect to project.  We must remove and reset the callbacks when
        # changing project.
        project_manager = self.app.project_manager
        project_manager.connect(
            "new-project-loading", self._new_project_loading_cb)
        project_manager.connect("new-project-loaded", self._newProjectLoadedCb)
        project_manager.connect("new-project-failed", self._newProjectFailedCb)
        project_manager.connect("project-closed", self._projectClosedCb)

        # Drag and Drop
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [URI_TARGET_ENTRY, FILE_TARGET_ENTRY],
                           Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag_data_received", self._drag_data_received_cb)

        self._setupViewAsDragAndDropSource(self.treeview)
        self._setupViewAsDragAndDropSource(self.iconview)

        # Hack so that the views have the same method as self
        self.treeview.getSelectedItems = self.getSelectedItems

        actions_group = Gio.SimpleActionGroup()
        self.insert_action_group("medialibrary", actions_group)
        self.app.shortcuts.register_group("medialibrary", _("Media Library"), position=50)

        self.remove_assets_action = Gio.SimpleAction.new("remove-assets", None)
        self.remove_assets_action.connect("activate", self._removeAssetsCb)
        actions_group.add_action(self.remove_assets_action)
        self.app.shortcuts.add("medialibrary.remove-assets", ["<Primary>Delete"],
                               _("Remove the selected assets"))

        self.insert_at_end_action = Gio.SimpleAction.new("insert-assets-at-end", None)
        self.insert_at_end_action.connect("activate", self._insertEndCb)
        actions_group.add_action(self.insert_at_end_action)
        self.app.shortcuts.add("medialibrary.insert-assets-at-end", ["Insert"],
                               _("Insert selected assets at the end of the timeline"))

        self._updateActions()

        # Set the state of the view mode toggle button.
        self._listview_button.set_active(self.clip_view == SHOW_TREEVIEW)
        # Make sure the proper view is displayed.
        self._displayClipView()

        # Add all the child widgets.
        self.pack_start(toolbar, False, False, 0)
        self.pack_start(self._welcome_infobar, False, False, 0)
        self.pack_start(self._project_settings_infobar, False, False, 0)
        self.pack_start(self._import_warning_infobar, False, False, 0)
        self.pack_start(self.iconview_scrollwin, True, True, 0)
        self.pack_start(self.treeview_scrollwin, True, True, 0)
        self.pack_start(self._progressbar, False, False, 0)

    def finalize(self):
        self.debug("Finalizing %s", self)

        self.app.project_manager.disconnect_by_func(self._new_project_loading_cb)
        self.app.project_manager.disconnect_by_func(self._newProjectLoadedCb)
        self.app.project_manager.disconnect_by_func(self._newProjectFailedCb)
        self.app.project_manager.disconnect_by_func(self._projectClosedCb)

        if not self._project:
            self.debug("No project set...")
            return

        for asset in self._project.list_assets(GES.Extractable):
            disconnectAllByFunc(asset, self.__assetProxiedCb)
            disconnectAllByFunc(asset, self.__assetProxyingCb)

        self.__disconnectFromProject()

    @staticmethod
    def compare_basename(model, iter1, iter2, unused_user_data):
        """Compares two model elements.

        Args:
            iter1 (Gtk.TreeIter): The iter identifying the first model element.
            iter2 (Gtk.TreeIter): The iter identifying the second model element.
        """
        uri1 = model[iter1][COL_URI]
        uri2 = model[iter2][COL_URI]
        basename1 = GLib.path_get_basename(uri1).lower()
        basename2 = GLib.path_get_basename(uri2).lower()
        if basename1 < basename2:
            return -1
        if basename1 == basename2:
            if uri1 < uri2:
                return -1
        return 1

    def getAssetForUri(self, uri):
        for path in self.modelFilter:
            asset = path[COL_ASSET]
            info = asset.get_info()
            asset_uri = info.get_uri()
            if asset_uri == uri:
                self.debug("Found asset: %s for uri: %s", asset, uri)
                return asset

        self.warning("Did not find any asset for uri: %s", uri)

    def _setupViewAsDragAndDropSource(self, view):
        view.drag_source_set(0, [], Gdk.DragAction.COPY)
        view.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, [URI_TARGET_ENTRY], Gdk.DragAction.COPY)
        view.drag_source_add_uri_targets()
        view.connect("drag-data-get", self._dndDragDataGetCb)
        view.connect_after("drag-begin", self._dndDragBeginCb)
        view.connect("drag-end", self._dndDragEndCb)

    def __updateViewCb(self, unused_model, unused_path, unused_iter=None):
        if not len(self.storemodel):
            self._welcome_infobar.show_all()
        else:
            self._welcome_infobar.hide()

    def _importSourcesCb(self, unused_action):
        self.show_import_assets_dialog()

    def _removeAssetsCb(self, unused_action, unused_parameter):
        """Removes the selected assets from the project."""
        model = self.treeview.get_model()
        paths = self.getSelectedPaths()
        if not paths:
            return
        # use row references so we don't have to care if a path has been
        # removed
        rows = [Gtk.TreeRowReference.new(model, path)
                for path in paths]

        with self.app.action_log.started("assets-removal", toplevel=True):
            for row in rows:
                asset = model[row.get_path()][COL_ASSET]
                target = asset.get_proxy_target()
                self._project.remove_asset(asset)
                self.app.gui.editor.timeline_ui.purgeAsset(asset.props.id)

                if target:
                    self._project.remove_asset(target)
                    self.app.gui.editor.timeline_ui.purgeAsset(target.props.id)

        # The treeview can make some of the remaining items selected, so
        # make sure none are selected.
        self._unselectAll()

    def _insertEndCb(self, unused_action, unused_parameter):
        self.app.gui.editor.timeline_ui.insertAssets(self.getSelectedAssets(), -1)

    def _searchEntryChangedCb(self, entry):
        # With many hundred clips in an iconview with dynamic columns and
        # ellipsizing, doing needless searches is very expensive.
        # Realistically, nobody expects to search for only one character,
        # and skipping that makes a huge difference in responsiveness.
        if len(entry.get_text()) != 1:
            self.modelFilter.refilter()

    def _searchEntryIconClickedCb(self, entry, icon_pos, unused_event):
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            entry.set_text("")
        elif icon_pos == Gtk.EntryIconPosition.PRIMARY:
            self._selectUnusedSources()
            # Focus the container so the user can use Ctrl+Delete, for example.
            if self.clip_view == SHOW_TREEVIEW:
                self.treeview.grab_focus()
            elif self.clip_view == SHOW_ICONVIEW:
                self.iconview.grab_focus()

    def _setRowVisible(self, model, iter, data):
        """Toggles the visibility of a liststore row."""
        text = data.get_text().lower()
        if not text:
            # Avoid silly warnings.
            return True
        # We must convert to markup form to be able to search for &, ', etc.
        text = GLib.markup_escape_text(text)
        return text in model.get_value(iter, COL_INFOTEXT).lower()

    def _connectToProject(self, project):
        """Connects signal handlers to the specified project."""
        project.connect("asset-added", self._assetAddedCb)
        project.connect("asset-loading-progress", self._assetLoadingProgressCb)
        project.connect("asset-removed", self._assetRemovedCb)
        project.connect("error-loading-asset", self._errorCreatingAssetCb)
        project.connect("proxying-error", self._proxyingErrorCb)
        project.connect("settings-set-from-imported-asset", self.__projectSettingsSetFromImportedAssetCb)

    def _setClipView(self, view_type):
        """Sets which clip view to use when medialibrary is showing clips.

        Args:
            view_type (int): One of SHOW_TREEVIEW or SHOW_ICONVIEW.
        """
        self.app.settings.lastClipView = view_type
        # Gather some info before switching views
        paths = self.getSelectedPaths()
        self._viewUnselectAll()
        # Now that we've got all the info, we can actually change the view type
        self.clip_view = view_type
        self._displayClipView()
        for path in paths:
            self._viewSelectPath(path)

    def _displayClipView(self):
        if self.clip_view == SHOW_TREEVIEW:
            self.iconview_scrollwin.hide()
            self.treeview_scrollwin.show_all()
        elif self.clip_view == SHOW_ICONVIEW:
            self.treeview_scrollwin.hide()
            self.iconview_scrollwin.show_all()

    def _filter_unsupported(self, filter_info):
        """Returns whether the specified item should be displayed."""
        if filter_info.mime_type not in SUPPORTED_MIMETYPES:
            return False

        if ProxyManager.is_proxy_asset(filter_info.uri):
            return False

        return True

    def show_import_assets_dialog(self):
        """Pops up the "Import Sources" dialog box."""
        dialog = Gtk.FileChooserDialog()
        dialog.set_title(_("Select One or More Files"))
        dialog.set_action(Gtk.FileChooserAction.OPEN)
        dialog.set_icon_name("pitivi")
        dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                           _("Add"), Gtk.ResponseType.OK)
        dialog.props.extra_widget = FileChooserExtraWidget(self.app)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        dialog.set_modal(True)
        dialog.set_transient_for(self.app.gui)
        dialog.set_current_folder(self.app.settings.lastImportFolder)
        dialog.connect('response', self._importDialogBoxResponseCb)
        previewer = PreviewWidget(self.app.settings)
        dialog.set_preview_widget(previewer)
        dialog.set_use_preview_label(False)
        dialog.connect('update-preview', previewer.update_preview_cb)

        # Filter for the "known good" formats by default
        filter = Gtk.FileFilter()
        filter.set_name(_("Supported file formats"))
        filter.add_custom(Gtk.FileFilterFlags.URI |
                          Gtk.FileFilterFlags.MIME_TYPE,
                          self._filter_unsupported)
        for formatter in GES.list_assets(GES.Formatter):
            for extension in formatter.get_meta("extension").split(","):
                if not extension:
                    continue
                filter.add_pattern("*.%s" % extension)
        dialog.add_filter(filter)

        # ...and allow the user to override our whitelists
        default = Gtk.FileFilter()
        default.set_name(_("All files"))
        default.add_pattern("*")
        dialog.add_filter(default)

        # Add a shortcut for the project folder (if saved)
        if self._project.uri:
            shortcut = os.path.dirname(self._project.uri)
            dialog.add_shortcut_folder_uri(shortcut)

        dialog.show()

    def _addAsset(self, asset):
        if self.app.proxy_manager.is_proxy_asset(asset) and \
                not asset.props.proxy_target:
            self.info("%s is a proxy asset but has no target, "
                      "not displaying it.", asset.props.id)
            return

        self.debug("Adding asset %s", asset.props.id)

        self._pending_assets.append(asset)

        if self._project.loaded:
            self._flushPendingAssets()

    def update_asset_thumbs(self, asset_uris):
        for row in self.storemodel:
            if row[COL_ASSET].props.id in asset_uris:
                row[COL_THUMB_DECORATOR].disregard_previewer()

    def _flushPendingAssets(self):
        self.debug("Flushing %d pending model rows", len(self._pending_assets))
        for asset in self._pending_assets:
            thumbs_decorator = AssetThumbnail(asset, self.app.proxy_manager)
            name = info_name(asset)

            self.storemodel.append((thumbs_decorator.small_thumb,
                                    thumbs_decorator.large_thumb,
                                    beautify_asset(asset),
                                    asset,
                                    asset.props.id,
                                    name,
                                    thumbs_decorator))

            thumbs_decorator.connect("thumb-updated", self.__thumb_updated_cb, asset)

        del self._pending_assets[:]

    def __thumb_updated_cb(self, asset_thumbnail, asset):
        """Handles the thumb-updated signal of the AssetThumbnails in the model."""
        tree_iter = None
        for row in self.storemodel:
            if asset == row[COL_ASSET]:
                tree_iter = row.iter
                break

        if not tree_iter:
            return

        self.storemodel.set_value(tree_iter,
                                  COL_ICON_64,
                                  asset_thumbnail.small_thumb)
        self.storemodel.set_value(tree_iter,
                                  COL_ICON_128,
                                  asset_thumbnail.large_thumb)

    # medialibrary callbacks

    def _assetLoadingProgressCb(self, project, progress, estimated_time):
        self._progressbar.set_fraction(progress / 100)

        proxying_files = []
        for row in self.storemodel:
            asset = row[COL_ASSET]
            row[COL_INFOTEXT] = beautify_asset(asset)

            if not asset.ready:
                proxying_files.append(asset)
                asset_previewer = row[COL_THUMB_DECORATOR]
                if asset_previewer.state != AssetThumbnail.IN_PROGRESS:
                    asset_previewer.refresh()
                    row[COL_ICON_64] = asset_previewer.small_thumb
                    row[COL_ICON_128] = asset_previewer.large_thumb

        if progress == 0:
            self._startImporting(project)
            return

        if project.loaded:
            if estimated_time:
                self.__last_proxying_estimate_time = beautify_ETA(int(
                    estimated_time * Gst.SECOND))

            # Translators: this string indicates the estimated time
            # remaining until an action (such as rendering) completes.
            # The "%s" is an already-localized human-readable duration,
            # such as "31 seconds", "1 minute" or "1 hours, 14 minutes".
            # In some languages, "About %s left" can be expressed roughly as
            # "There remains approximatively %s" (to handle gender and plurals)
            template = ngettext("Transcoding %d asset: %d%% (About %s left)",
                                "Transcoding %d assets: %d%% (About %s left)",
                                len(proxying_files))
            progress_message = template % (
                len(proxying_files), progress,
                self.__last_proxying_estimate_time)
            self._progressbar.set_text(progress_message)

        if progress == 100:
            self._doneImporting()

    def __assetProxyingCb(self, proxy, unused_pspec):
        if not self.app.proxy_manager.is_proxy_asset(proxy):
            self.info("Proxy is not a proxy in our terms (handling deleted proxy"
                      " files while loading a project?) - ignore it")

            return

        self.debug("Proxy is %s - %s", proxy.props.id,
                   proxy.get_proxy_target())
        self.__removeAsset(proxy)

        if proxy.get_proxy_target() is not None:
            # Re add the proxy so its emblem icon is updated.
            self._addAsset(proxy)

    def __assetProxiedCb(self, asset, unused_pspec):
        self.debug("Asset proxied: %s -- %s", asset, asset.props.id)
        proxy = asset.props.proxy
        self.__removeAsset(asset)
        if not proxy:
            self._addAsset(asset)

        if self._project.loaded:
            self.app.gui.editor.timeline_ui.update_clips_asset(asset, proxy)

    def _assetAddedCb(self, unused_project, asset):
        """Checks whether the asset added to the project should be shown."""
        self._last_imported_uris.add(asset.props.id)

        if asset in [row[COL_ASSET] for row in self.storemodel]:
            self.info("Asset %s already in!", asset.props.id)
            return

        if isinstance(asset, GES.UriClipAsset) and not asset.error:
            self.debug("Asset %s added: %s", asset, asset.props.id)
            asset.connect("notify::proxy", self.__assetProxiedCb)
            asset.connect("notify::proxy-target", self.__assetProxyingCb)
            if asset.get_proxy():
                self.debug("Not adding asset %s, its proxy is used instead: %s",
                           asset.props.id,
                           asset.get_proxy().props.id)
                return

            self._addAsset(asset)

    def _assetRemovedCb(self, unused_project, asset):
        if isinstance(asset, GES.UriClipAsset):
            self.debug("Disconnecting %s - %s", asset, asset.props.id)
            asset.disconnect_by_func(self.__assetProxiedCb)
            asset.disconnect_by_func(self.__assetProxyingCb)
            self.__removeAsset(asset)

    def __removeAsset(self, asset):
        """Removes the specified asset."""
        uri = asset.get_id()
        # Find the corresponding line in the storemodel and remove it.
        found = False
        for row in self.storemodel:
            if uri == row[COL_URI]:
                self.storemodel.remove(row.iter)
                found = True
                break

        if not found:
            self.info("Failed to remove %s as it was not found"
                      "in the liststore", uri)

    def _proxyingErrorCb(self, unused_project, asset):
        self.__removeAsset(asset)
        self._addAsset(asset)

    def _errorCreatingAssetCb(self, unused_project, error, id, type):
        """Gathers asset loading errors."""
        if GObject.type_is_a(type, GES.UriClip):
            if self.app.proxy_manager.is_proxy_asset(id):
                self.debug("Error %s with a proxy"
                           ", not showing the error message", error)
                return

            error = (id, str(error.domain), error)
            self._errors.append(error)

    def _startImporting(self, project):
        self.__last_proxying_estimate_time = _("Unknown")
        self.import_start_time = time.time()
        self._welcome_infobar.hide()
        self._progressbar.show()

    def _doneImporting(self):
        self.debug("Importing took %.3f seconds",
                   time.time() - self.import_start_time)
        self._flushPendingAssets()
        self._progressbar.hide()
        if self._errors:
            errors_amount = len(self._errors)
            btn_text = ngettext("View error", "View errors", errors_amount)
            # Translators: {0:d} is just like %d (integer number variable)
            text = ngettext("An error occurred while importing.",
                            "{0:d} errors occurred while importing.",
                            errors_amount)
            # Do the {0:d} (aka "%d") substitution using "format" instead of %,
            # avoiding tracebacks as %d would be missing in the singular form:
            text = text.format(errors_amount)

            self._view_error_button.set_label(btn_text)
            self._warning_label.set_text(text)
            self._import_warning_infobar.show_all()

        self._selectLastImportedUris()

    def __projectSettingsSetFromImportedAssetCb(self, unused_project, asset):
        asset_path = path_from_uri(asset.get_id())
        file_name = os.path.basename(asset_path)
        message = _("The project settings have been set to match file '%s'") % file_name
        self._project_settings_label.set_text(message)
        self._project_settings_infobar.show()

    def _selectLastImportedUris(self):
        if not self._last_imported_uris:
            return
        self._selectSources(self._last_imported_uris)
        self._last_imported_uris = set()

    # Error Dialog Box callbacks

    def _errorDialogBoxCloseCb(self, dialog):
        dialog.destroy()

    def _errorDialogBoxResponseCb(self, dialog, unused_response):
        dialog.destroy()

    # Import Sources Dialog Box callbacks

    def _importDialogBoxResponseCb(self, dialogbox, response):
        self.debug("response: %r", response)
        if response == Gtk.ResponseType.OK:
            lastfolder = dialogbox.get_current_folder()
            # get_current_folder() is None if file was chosen from 'Recents'
            if not lastfolder:
                lastfolder = GLib.path_get_dirname(dialogbox.get_filename())
            self.app.settings.lastImportFolder = lastfolder
            dialogbox.props.extra_widget.saveValues()
            filenames = dialogbox.get_uris()
            self._project.addUris(filenames)
            if self.app.settings.closeImportDialog:
                dialogbox.destroy()
        else:
            dialogbox.destroy()

    def _sourceIsUsed(self, asset):
        """Checks whether the specified asset is present in the timeline."""
        layers = self._project.ges_timeline.get_layers()
        for layer in layers:
            for clip in layer.get_clips():
                if clip.get_asset() == asset:
                    return True
        return False

    def _selectUnusedSources(self):
        """Selects the assets not used by any clip in the project's timeline."""
        unused_sources_uris = []
        for asset in self._project.list_assets(GES.UriClip):
            if not self._sourceIsUsed(asset):
                unused_sources_uris.append(asset.get_id())
        self._selectSources(unused_sources_uris)

    def _selectSources(self, sources_uris):
        # Hack around the fact that making selections (in a treeview/iconview)
        # deselects what was previously selected
        if self.clip_view == SHOW_TREEVIEW:
            self.treeview.get_selection().select_all()
        elif self.clip_view == SHOW_ICONVIEW:
            self.iconview.select_all()

        model = self.treeview.get_model()
        selection = self.treeview.get_selection()
        for row in model:
            if row[COL_URI] not in sources_uris:
                if self.clip_view == SHOW_TREEVIEW:
                    selection.unselect_iter(row.iter)
                elif self.clip_view == SHOW_ICONVIEW:
                    self.iconview.unselect_path(row.path)

    def _unselectAll(self):
        if self.clip_view == SHOW_TREEVIEW:
            self.treeview.get_selection().unselect_all()
        elif self.clip_view == SHOW_ICONVIEW:
            self.iconview.unselect_all()

    # UI callbacks

    def __projectSettingsSetInfobarCb(self, infobar, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.app.gui.editor.showProjectSettingsDialog()
        infobar.hide()

    def _clipPropertiesCb(self, unused_widget):
        """Shows the clip properties in a dialog.

        Allows selecting and applying them as the new project settings.
        """
        paths = self.getSelectedPaths()
        if not paths:
            self.debug("No item selected")
            return
        # Only use the first item.
        path = paths[0]
        asset = self.storemodel[path][COL_ASSET]
        dialog = ClipMediaPropsDialog(self._project, asset)
        dialog.dialog.set_transient_for(self.app.gui)
        dialog.run()

    def __warningInfobarCb(self, infobar, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.__show_errors()
        self._resetErrorList()
        infobar.hide()

    def _resetErrorList(self):
        self._errors = []
        self._import_warning_infobar.hide()

    def __show_errors(self):
        """Shows a dialog with the import errors."""
        title = ngettext("Error while analyzing a file",
                         "Error while analyzing files",
                         len(self._errors))
        headline = ngettext("The following file can not be used with Pitivi.",
                            "The following files can not be used with Pitivi.",
                            len(self._errors))
        error_dialogbox = FileListErrorDialog(title, headline)
        error_dialogbox.connect("close", self._errorDialogBoxCloseCb)
        error_dialogbox.connect("response", self._errorDialogBoxResponseCb)

        for uri, reason, extra in self._errors:
            error_dialogbox.addFailedFile(uri, reason, extra)
        error_dialogbox.window.set_transient_for(self.app.gui)
        error_dialogbox.window.show()

    def _toggleViewTypeCb(self, widget):
        if widget.get_active():
            self._setClipView(SHOW_TREEVIEW)
        else:
            self._setClipView(SHOW_ICONVIEW)

    def __get_path_under_mouse(self, view, event):
        """Gets the path of the item under the mouse cursor.

        Returns:
            Gtk.TreePath: The item at the current mouse position, if any.
        """
        if isinstance(view, Gtk.TreeView):
            path = None
            tup = view.get_path_at_pos(int(event.x), int(event.y))
            if tup:
                path, column, x, y = tup
            return path
        elif isinstance(view, Gtk.IconView):
            return view.get_path_at_pos(int(event.x), int(event.y))
        else:
            raise RuntimeError("Unknown view type: %s" % type(view))

    def _rowUnderMouseSelected(self, view, event):
        path = self.__get_path_under_mouse(view, event)
        if not path:
            return False
        if isinstance(view, Gtk.TreeView):
            tree_selection = view.get_selection()
            return tree_selection.path_is_selected(path)
        elif isinstance(view, Gtk.IconView):
            return view.path_is_selected(path)
        else:
            raise RuntimeError("Unknown view type: %s" % type(view))

    def _viewGetFirstSelected(self):
        paths = self.getSelectedPaths()
        return paths[0]

    def _viewHasSelection(self):
        paths = self.getSelectedPaths()
        return bool(len(paths))

    def _viewGetPathAtPos(self, event):
        if self.clip_view == SHOW_TREEVIEW:
            pathinfo = self.treeview.get_path_at_pos(
                int(event.x), int(event.y))
            return pathinfo[0]
        elif self.clip_view == SHOW_ICONVIEW:
            return self.iconview.get_path_at_pos(int(event.x), int(event.y))

    def _viewSelectPath(self, path):
        if self.clip_view == SHOW_TREEVIEW:
            selection = self.treeview.get_selection()
            selection.select_path(path)
        elif self.clip_view == SHOW_ICONVIEW:
            self.iconview.select_path(path)

    def _viewUnselectAll(self):
        if self.clip_view == SHOW_TREEVIEW:
            selection = self.treeview.get_selection()
            selection.unselect_all()
        elif self.clip_view == SHOW_ICONVIEW:
            self.iconview.unselect_all()

    def __stopUsingProxyCb(self, unused_action, unused_parameter):
        prefer_original = self.app.settings.proxyingStrategy == ProxyingStrategy.NOTHING
        self._project.disable_proxies_for_assets(self.getSelectedAssets(),
                                                 hq_proxy=not prefer_original)

    def __useProxiesCb(self, unused_action, unused_parameter):
        self._project.use_proxies_for_assets(self.getSelectedAssets())

    def __use_scaled_proxies_cb(self, unused_action, unused_parameter):
        self._project.use_proxies_for_assets(self.getSelectedAssets(),
                                             scaled=True)

    def __deleteProxiesCb(self, unused_action, unused_parameter):
        prefer_original = self.app.settings.proxyingStrategy == ProxyingStrategy.NOTHING
        self._project.disable_proxies_for_assets(self.getSelectedAssets(),
                                                 delete_proxy_file=True,
                                                 hq_proxy=not prefer_original)

    def __open_containing_folder_cb(self, unused_action, unused_parameter):
        assets = self.getSelectedAssets()
        if len(assets) != 1:
            return
        parent_path = os.path.dirname(path_from_uri(assets[0].get_id()))
        Gio.AppInfo.launch_default_for_uri(Gst.filename_to_uri(parent_path), None)

    def __edit_nested_clip_cb(self, unused_action, unused_parameter):
        assets = self.getSelectedAssets()
        if len(assets) != 1:
            return

        path = os.path.abspath(path_from_uri(assets[0].get_id()))
        subprocess.Popen([sys.argv[0], path])

    def __createMenuModel(self):
        if self.app.proxy_manager.proxyingUnsupported:
            return None, None

        assets = self.getSelectedAssets()
        if not assets:
            return None, None

        action_group = Gio.SimpleActionGroup()
        menu_model = Gio.Menu()

        if len(assets) == 1:
            action = Gio.SimpleAction.new("open-folder", None)
            action.connect("activate", self.__open_containing_folder_cb)
            action_group.insert(action)
            text = _("Open containing folder")
            menu_model.append(text, "assets.%s" % action.get_name().replace(" ", "."))

        if len(assets) == 1 and assets[0].props.is_nested_timeline:
            action = Gio.SimpleAction.new("edit-nested-clip", None)
            action.connect("activate", self.__edit_nested_clip_cb)
            action_group.insert(action)
            text = _("Edit")
            menu_model.append(text, "assets.%s" % action.get_name().replace(" ", "."))

        image_assets = [asset for asset in assets
                        if asset.is_image()]

        if len(assets) == len(image_assets):
            return menu_model, action_group

        proxies = [asset.get_proxy_target() for asset in assets
                   if self.app.proxy_manager.is_proxy_asset(asset)]
        hq_proxies = [asset.get_proxy_target() for asset in assets
                      if self.app.proxy_manager.is_hq_proxy(asset)]
        scaled_proxies = [asset.get_proxy_target() for asset in assets
                          if self.app.proxy_manager.is_scaled_proxy(asset)]
        in_progress = [asset.creation_progress for asset in assets
                       if asset.creation_progress < 100]

        if hq_proxies:
            action = Gio.SimpleAction.new("unproxy-asset", None)
            action.connect("activate", self.__stopUsingProxyCb)
            action_group.insert(action)
            text = ngettext("Do not use Optimised Proxy for selected asset",
                            "Do not use Optimised Proxies for selected assets",
                            len(proxies) + len(in_progress))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

            action = Gio.SimpleAction.new("delete-proxies", None)
            action.connect("activate", self.__deleteProxiesCb)
            action_group.insert(action)

            text = ngettext("Delete corresponding proxy file",
                            "Delete corresponding proxy files",
                            len(proxies) + len(in_progress))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

        if in_progress:
            action = Gio.SimpleAction.new("unproxy-asset", None)
            action.connect("activate", self.__stopUsingProxyCb)
            action_group.insert(action)
            text = ngettext("Do not use Proxy for selected asset",
                            "Do not use Proxies for selected assets",
                            len(proxies) + len(in_progress))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

            action = Gio.SimpleAction.new("delete-proxies", None)
            action.connect("activate", self.__deleteProxiesCb)
            action_group.insert(action)

            text = ngettext("Delete corresponding proxy file",
                            "Delete corresponding proxy files",
                            len(proxies) + len(in_progress))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

        if scaled_proxies:
            action = Gio.SimpleAction.new("unproxy-asset", None)
            action.connect("activate", self.__stopUsingProxyCb)
            action_group.insert(action)
            text = ngettext("Do not use Scaled Proxy for selected asset",
                            "Do not use Scaled Proxies for selected assets",
                            len(proxies) + len(in_progress))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

            action = Gio.SimpleAction.new("delete-proxies", None)
            action.connect("activate", self.__deleteProxiesCb)
            action_group.insert(action)

            text = ngettext("Delete corresponding proxy file",
                            "Delete corresponding proxy files",
                            len(proxies) + len(in_progress))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

        if len(proxies) != len(assets) and len(in_progress) != len(assets):
            action = Gio.SimpleAction.new("use-proxies", None)
            action.connect("activate", self.__useProxiesCb)
            action_group.insert(action)
            text = ngettext("Use Optimised Proxy for selected asset",
                            "Use Optimised Proxies for selected assets", len(assets))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

            action = Gio.SimpleAction.new("use-scaled-proxies", None)
            action.connect("activate", self.__use_scaled_proxies_cb)
            action_group.insert(action)
            text = ngettext("Use Scaled Proxy for selected asset",
                            "Use Scaled Proxies for selected assets", len(assets))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

        return menu_model, action_group

    def __maybeShowPopoverMenu(self, view, event):
        res, button = event.get_button()
        if not res or button != 3:
            return False

        if not self._rowUnderMouseSelected(view, event):
            path = self.__get_path_under_mouse(view, event)
            if path:
                if isinstance(view, Gtk.IconView):
                    view.unselect_all()
                    view.select_path(path)
                else:
                    selection = view.get_selection()
                    selection.unselect_all()
                    selection.select_path(path)

        model, action_group = self.__createMenuModel()
        if not model or not model.get_n_items():
            return True

        popover = Gtk.Popover.new_from_model(view, model)
        popover.insert_action_group("assets", action_group)
        popover.props.position = Gtk.PositionType.BOTTOM

        if self.clip_view == SHOW_TREEVIEW:
            scrollwindow = self.treeview_scrollwin
        elif self.clip_view == SHOW_ICONVIEW:
            scrollwindow = self.iconview_scrollwin

        rect = Gdk.Rectangle()
        rect.x = event.x - scrollwindow.props.hadjustment.props.value
        rect.y = event.y - scrollwindow.props.vadjustment.props.value
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        popover.show_all()

        return True

    def _treeViewButtonPressEventCb(self, treeview, event):
        self._updateDraggedPaths(treeview, event)

        Gtk.TreeView.do_button_press_event(treeview, event)

        selection = self.treeview.get_selection()
        if self._draggedPaths:
            for path in self._draggedPaths:
                selection.select_path(path)

        return True

    def _updateDraggedPaths(self, view, event):
        if event.type == getattr(Gdk.EventType, '2BUTTON_PRESS'):
            # It is possible to double-click outside of clips:
            if self.getSelectedPaths():
                # Here we used to emit "play", but
                # this is now handled by _itemOrRowActivatedCb instead.
                pass
            chain_up = False
        elif not event.get_state() & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            chain_up = not self._rowUnderMouseSelected(view, event)
        else:
            chain_up = True

        if not chain_up:
            self._draggedPaths = self.getSelectedPaths()
        else:
            self._draggedPaths = None

    def _treeViewButtonReleaseEventCb(self, treeview, event):
        self._draggedPaths = None
        selection = self.treeview.get_selection()
        state = event.get_state() & (
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
        path = self.treeview.get_path_at_pos(event.x, event.y)

        if self.__maybeShowPopoverMenu(treeview, event):
            self.debug("Returning after showing popup menu")
            return

        if not state and not self.dragged:
            selection.unselect_all()
            if path:
                selection.select_path(path[0])

    def _viewSelectionChangedCb(self, unused):
        self._updateActions()

    def _updateActions(self):
        selected_count = len(self.getSelectedPaths())
        self.remove_assets_action.set_enabled(selected_count)
        self.insert_at_end_action.set_enabled(selected_count)
        # Some actions can only be done on a single item at a time:
        self._clipprops_button.set_sensitive(selected_count == 1)

    def _itemOrRowActivatedCb(self, unused_view, path, *unused_args):
        """Plays the asset identified by the specified path.

        This can happen when an item is double-clicked, or
        Space, Shift+Space, Return or Enter is pressed.
        This method is the same for both iconview and treeview.
        """
        asset = self.modelFilter[path][COL_ASSET]
        self.emit('play', asset)

    def _iconViewButtonPressEventCb(self, iconview, event):
        self._updateDraggedPaths(iconview, event)

        Gtk.IconView.do_button_press_event(iconview, event)

        if self._draggedPaths:
            for path in self._draggedPaths:
                self.iconview.select_path(path)

        self.iconview_cursor_pos = self.iconview.get_path_at_pos(
            event.x, event.y)

        return True

    def _iconViewButtonReleaseEventCb(self, iconview, event):
        self._draggedPaths = None

        control_mask = event.get_state() & Gdk.ModifierType.CONTROL_MASK
        shift_mask = event.get_state() & Gdk.ModifierType.SHIFT_MASK
        modifier_active = control_mask or shift_mask

        if self.__maybeShowPopoverMenu(iconview, event):
            self.debug("Returning after showing popup menu")
            return

        if not modifier_active and self.iconview_cursor_pos:
            current_cursor_pos = self.iconview.get_path_at_pos(
                event.x, event.y)

            if current_cursor_pos == self.iconview_cursor_pos:
                if iconview.path_is_selected(current_cursor_pos):
                    iconview.unselect_all()
                    iconview.select_path(current_cursor_pos)

    def __disconnectFromProject(self):
        self._project.disconnect_by_func(self._assetAddedCb)
        self._project.disconnect_by_func(self._assetLoadingProgressCb)
        self._project.disconnect_by_func(self._assetRemovedCb)
        self._project.disconnect_by_func(self._proxyingErrorCb)
        self._project.disconnect_by_func(self._errorCreatingAssetCb)
        self._project.disconnect_by_func(self.__projectSettingsSetFromImportedAssetCb)

    def _new_project_loading_cb(self, unused_project_manager, project):
        assert not self._project

        self._project = project
        self._resetErrorList()
        self.storemodel.clear()
        self._welcome_infobar.show_all()
        self._connectToProject(project)

    def _newProjectLoadedCb(self, unused_project_manager, project):
        # Make sure that the sources added to the project are added
        self._flushPendingAssets()

    def _newProjectFailedCb(self, unused_project_manager, unused_uri, unused_reason):
        self.storemodel.clear()
        self._project = None

    def _projectClosedCb(self, unused_project_manager, unused_project):
        self.__disconnectFromProject()
        self._project_settings_infobar.hide()
        self.storemodel.clear()
        self._project = None

    def __paths_walked_cb(self, uris):
        """Handles the end of the path walking when importing dragged dirs."""
        if not uris:
            return

        if not self._project:
            return

        # At the end of the import operation, these will be selected.
        self._last_imported_uris = set(uris)
        assets = self._project.assetsForUris(uris)
        if assets:
            # All the files have already been added.
            # This is the only chance we have to select them.
            self._selectLastImportedUris()
        else:
            self._project.addUris(uris)

    def _drag_data_received_cb(self, unused_widget, unused_context, unused_x,
                               unused_y, selection, targettype, unused_time):
        """Handles data being dragged onto self."""
        self.debug("targettype: %d, selection.data: %r",
                   targettype, selection.get_data())
        uris = selection.get_uris()
        # Scan in the background what was dragged and
        # import whatever can be imported.
        self.app.threads.addThread(PathWalker, uris, self.__paths_walked_cb)

    # Used with TreeView and IconView
    def _dndDragDataGetCb(self, unused_view, unused_context, data, unused_info, unused_timestamp):
        paths = self.getSelectedPaths()
        uris = [self.modelFilter[path][COL_URI] for path in paths]
        data.set_uris(uris)

    def _dndDragBeginCb(self, unused_view, context):
        self.info("Drag operation begun")
        self.dragged = True
        paths = self.getSelectedPaths()

        if not paths:
            context.drag_abort(int(time.time()))
        else:
            row = self.modelFilter[paths[0]]

            icon = row[COL_ICON_128]
            icon_height = icon.get_height()
            icon_width = icon.get_width()

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, icon_width, icon_height)
            ctx = cairo.Context(surface)
            # Center the icon around the cursor.
            ctx.translate(icon_width / 2, icon_height / 2)
            surface.set_device_offset(-icon_width / 2, -icon_height / 2)

            Gdk.cairo_set_source_pixbuf(ctx, icon, 0, 0)
            ctx.paint_with_alpha(0.35)

            Gtk.drag_set_icon_surface(context, surface)

    def _dndDragEndCb(self, unused_view, unused_context):
        self.info("Drag operation ended")
        self.dragged = False

    def getSelectedPaths(self):
        """Gets which treeview or iconview items are selected.

        Returns:
            List[Gtk.TreePath]: The paths identifying the items.
        """
        if self.clip_view == SHOW_TREEVIEW:
            return self._getSelectedPathsTreeView()
        elif self.clip_view == SHOW_ICONVIEW:
            return self._getSelectedPathsIconView()

    def _getSelectedPathsTreeView(self):
        model, rows = self.treeview.get_selection().get_selected_rows()
        return rows

    def _getSelectedPathsIconView(self):
        paths = self.iconview.get_selected_items()
        paths.reverse()
        return paths

    def getSelectedItems(self):
        """Gets the URIs of the selected items."""
        if self._draggedPaths:
            return [self.modelFilter[path][COL_URI]
                    for path in self._draggedPaths]
        return [self.modelFilter[path][COL_URI]
                for path in self.getSelectedPaths()]

    def getSelectedAssets(self):
        """Gets the selected assets."""
        if self._draggedPaths:
            return [self.modelFilter[path][COL_ASSET]
                    for path in self._draggedPaths]
        return [self.modelFilter[path][COL_ASSET]
                for path in self.getSelectedPaths()]

    def activateCompactMode(self):
        self._import_button.set_is_important(False)
