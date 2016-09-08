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
import threading
import time
from gettext import gettext as _
from gettext import ngettext
from hashlib import md5
from urllib.parse import unquote
from urllib.parse import urlparse

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

from pitivi.check import missing_soft_deps
from pitivi.configure import get_pixmap_dir
from pitivi.configure import get_ui_dir
from pitivi.dialogs.clipmediaprops import ClipMediaPropsDialog
from pitivi.dialogs.filelisterrordialog import FileListErrorDialog
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.settings import GlobalSettings
from pitivi.timeline.previewers import getThumbnailCache
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import disconnectAllByFunc
from pitivi.utils.misc import get_proxy_target
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import PathWalker
from pitivi.utils.misc import quote_uri
from pitivi.utils.proxy import ProxyingStrategy
from pitivi.utils.proxy import ProxyManager
from pitivi.utils.ui import beautify_asset
from pitivi.utils.ui import beautify_ETA
from pitivi.utils.ui import beautify_length
from pitivi.utils.ui import FILE_TARGET_ENTRY
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import info_name
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
    str, object, str, str, str, object)

(COL_ICON_64,
 COL_ICON_128,
 COL_INFOTEXT,
 COL_ASSET,
 COL_URI,
 COL_LENGTH,
 COL_SEARCH_TEXT,
 COL_THUMB_DECORATOR) = list(range(len(STORE_MODEL_STRUCTURE)))

# This whitelist is made from personal knowledge of file extensions in the wild,
# from gst-inspect |grep demux,
# http://en.wikipedia.org/wiki/Comparison_of_container_formats and
# http://en.wikipedia.org/wiki/List_of_file_formats#Video
# ...and looking at the contents of /usr/share/mime
SUPPORTED_FILE_FORMATS = {
    "video": ("3gpp", "3gpp2", "dv", "mp2t", "mp4", "mpeg", "ogg", "quicktime", "webm", "x-flv", "x-matroska", "x-mng", "x-ms-asf", "x-msvideo", "x-ms-wmp", "x-ms-wmv", "x-ogm+ogg", "x-theora+ogg", "mp2t"),  # noqa
    "application": ("mxf",),
    # Don't forget audio formats
    "audio": ("aac", "ac3", "basic", "flac", "mp2", "mp4", "mpeg", "ogg", "opus", "webm", "x-adpcm", "x-aifc", "x-aiff", "x-aiffc", "x-ape", "x-flac+ogg", "x-m4b", "x-matroska", "x-ms-asx", "x-ms-wma", "x-speex", "x-speex+ogg", "x-vorbis+ogg", "x-wav"),  # noqa
    # ...and image formats
    "image": ("jp2", "jpeg", "png", "svg+xml")}

SUPPORTED_MIMETYPES = []
for category, mime_types in SUPPORTED_FILE_FORMATS.items():
    for mime in mime_types:
        SUPPORTED_MIMETYPES.append(category + "/" + mime)


class FileChooserExtraWidget(Gtk.Grid, Loggable):
    def __init__(self, app):
        Loggable.__init__(self)
        Gtk.Grid.__init__(self)
        self.app = app

        self.set_row_spacing(SPACING)
        self.set_column_spacing(SPACING)

        self.__close_after = Gtk.CheckButton(label=_("Close after importing files"))
        self.__close_after.set_active(self.app.settings.closeImportDialog)
        self.attach(self.__close_after, 0, 0, 1, 2)

        self.__automatic_proxies = Gtk.RadioButton.new_with_label(
            None, _("Create proxies when the media format is not supported officially"))
        self.__automatic_proxies.set_tooltip_markup(
            _("Let Pitivi decide when to"
              " create proxy files and when not. The decision will be made"
              " depending on the file format, and how well it is supported."
              " For example H.264, FLAC files contained in QuickTime will"
              " not be proxied, but AAC, H.264 contained in MPEG-TS will.\n\n"
              "<i>This is the only option officially supported by the"
              " Pitivi developers and thus is the safest."
              "</i>"))

        self.__force_proxies = Gtk.RadioButton.new_with_label_from_widget(
            self.__automatic_proxies, _("Create proxies for all files"))
        self.__force_proxies.set_tooltip_markup(
            _("Use proxies for every imported file"
              " whatever its current media format is."))
        self.__no_proxies = Gtk.RadioButton.new_with_label_from_widget(
            self.__automatic_proxies, _("Do not use proxy files"))

        if self.app.settings.proxyingStrategy == ProxyingStrategy.ALL:
            self.__force_proxies.set_active(True)
        elif self.app.settings.proxyingStrategy == ProxyingStrategy.NOTHING:
            self.__no_proxies.set_active(True)
        else:
            self.__automatic_proxies.set_active(True)

        self.attach(self.__automatic_proxies, 1, 0, 1, 1)
        self.attach(self.__force_proxies, 1, 1, 1, 1)
        self.attach(self.__no_proxies, 1, 2, 1, 1)
        self.show_all()

    def saveValues(self):
        self.app.settings.closeImportDialog = self.__close_after.get_active()
        if self.__force_proxies.get_active():
            self.app.settings.proxyingStrategy = ProxyingStrategy.ALL
        elif self.__no_proxies.get_active():
            self.app.settings.proxyingStrategy = ProxyingStrategy.NOTHING
        else:
            self.app.settings.proxyingStrategy = ProxyingStrategy.AUTOMATIC


class ThumbnailsDecorator(Loggable):
    EMBLEMS = {}
    PROXIED = "asset-proxied"
    NO_PROXY = "no-proxy"
    IN_PROGRESS = "asset-proxy-in-progress"
    ASSET_PROXYING_ERROR = "asset-proxying-error"

    DEFAULT_ALPHA = 255

    for status in [PROXIED, IN_PROGRESS, ASSET_PROXYING_ERROR]:
        EMBLEMS[status] = []
        for size in [32, 64]:
            EMBLEMS[status].append(GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(get_pixmap_dir(), "%s.svg" % status), size, size))

    def __init__(self, thumbs, asset, proxy_manager):
        Loggable.__init__(self)
        self.src_64, self.src_128 = thumbs
        self.__asset = asset
        self.proxy_manager = proxy_manager
        self.decorate()

    def __setState(self):
        asset = self.__asset
        target = asset.get_proxy_target()
        if target and not target.get_error():
            # The asset is a proxy.
            self.state = self.PROXIED
        elif asset.proxying_error:
            self.state = self.ASSET_PROXYING_ERROR
        elif self.proxy_manager.is_asset_queued(asset):
            self.state = self.IN_PROGRESS
        else:
            self.state = self.NO_PROXY

    def decorate(self):
        self.__setState()
        if self.state == self.NO_PROXY:
            self.thumb_64 = self.src_64
            self.thumb_128 = self.src_128
            return

        self.thumb_64 = self.src_64.copy()
        self.thumb_128 = self.src_128.copy()
        for thumb, src in zip([self.thumb_64, self.thumb_128],
                              self.EMBLEMS[self.state]):
            # We need to set dest_y == offset_y for the source image
            # not to be cropped, that API is weird.
            if thumb.get_height() < src.get_height():
                src = src.copy()
                src = src.scale_simple(src.get_width(),
                                       thumb.get_height(),
                                       GdkPixbuf.InterpType.BILINEAR)

            src.composite(thumb, dest_x=0,
                          dest_y=thumb.get_height() - src.get_height(),
                          dest_width=src.get_width(),
                          dest_height=src.get_height(),
                          offset_x=0,
                          offset_y=thumb.get_height() - src.get_height(),
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

        self.pending_rows = []

        self.app = app
        self._errors = []
        self._missing_thumbs = []
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
        self._project_settings_set_infobar = Gtk.InfoBar()
        self._project_settings_set_infobar.hide()
        self._project_settings_set_infobar.set_message_type(Gtk.MessageType.OTHER)
        self._project_settings_set_infobar.set_show_close_button(True)
        self._project_settings_set_infobar.add_button(_("Project Settings"), Gtk.ResponseType.OK)
        self._project_settings_set_infobar.connect("response", self.__projectSettingsSetInfobarCb)
        fix_infobar(self._project_settings_set_infobar)
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
        pixcell.props.xpad = 6
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
        namecol.pack_start(txtcell, True)
        namecol.add_attribute(txtcell, "markup", COL_INFOTEXT)

        namecol = Gtk.TreeViewColumn(_("Duration"))
        namecol.set_expand(False)
        self.treeview.append_column(namecol)
        txtcell = Gtk.CellRendererText()
        txtcell.set_property("yalign", 0.0)
        namecol.pack_start(txtcell, True)
        namecol.add_attribute(txtcell, "markup", COL_LENGTH)

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
        self.iconview.props.item_padding = 3
        self.iconview.props.margin = 3
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
        self.connect("drag_data_received", self._dndDataReceivedCb)

        self._setupViewAsDragAndDropSource(self.treeview)
        self._setupViewAsDragAndDropSource(self.iconview)

        # Hack so that the views have the same method as self
        self.treeview.getSelectedItems = self.getSelectedItems

        actions_group = Gio.SimpleActionGroup()
        self.insert_action_group("medialibrary", actions_group)
        self.app.shortcuts.register_group("medialibrary", _("Media Library"))

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
        self.pack_start(self._project_settings_set_infobar, False, False, 0)
        self.pack_start(self._import_warning_infobar, False, False, 0)
        self.pack_start(self.iconview_scrollwin, True, True, 0)
        self.pack_start(self.treeview_scrollwin, True, True, 0)
        self.pack_start(self._progressbar, False, False, 0)

        self.thumbnailer = MediaLibraryWidget._getThumbnailer()

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
    def _getThumbnailer():
        if "GnomeDesktop" in missing_soft_deps:
            return None
        from gi.repository import GnomeDesktop
        # We need to instanciate the thumbnail factory on the main thread...
        size_normal = GnomeDesktop.DesktopThumbnailSize.NORMAL
        return GnomeDesktop.DesktopThumbnailFactory.new(size_normal)

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
        view.connect("drag-begin", self._dndDragBeginCb)
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

        with self.app.action_log.started("remove asset from media library"):
            for row in rows:
                asset = model[row.get_path()][COL_ASSET]
                target = asset.get_proxy_target()
                self._project.remove_asset(asset)
                self.app.gui.timeline_ui.purgeAsset(asset.props.id)

                if target:
                    self._project.remove_asset(target)
                    self.app.gui.timeline_ui.purgeAsset(target.props.id)

        # The treeview can make some of the remaining items selected, so
        # make sure none are selected.
        self._unselectAll()

    def _insertEndCb(self, unused_action, unused_parameter):
        self.app.gui.timeline_ui.insertAssets(self.getSelectedAssets(), -1)

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

    def _getIcon(self, iconname, alternate=None, size=48):
        icontheme = Gtk.IconTheme.get_default()
        pixdir = get_pixmap_dir()
        icon = None
        try:
            icon = icontheme.load_icon(iconname, size, 0)
        except:
            # empty except clause is bad but load_icon raises Gio.Error.
            # Right, *gio*.
            if alternate:
                icon = GdkPixbuf.Pixbuf.new_from_file(
                    os.path.join(pixdir, alternate))
            else:
                icon = icontheme.load_icon("dialog-question", size, 0)
        return icon

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

    def __filter_unsupported(self, filter_info):
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
                          self.__filter_unsupported)
        dialog.add_filter(filter)

        # ...and allow the user to override our whitelists
        default = Gtk.FileFilter()
        default.set_name(_("All files"))
        default.add_pattern("*")
        dialog.add_filter(default)

        dialog.show()

    def _getThumbnailInDir(self, dir, hash):
        """Gets pixbufs for the specified thumbnail.

        Args:
            dir (str): The directory where the thumbnails can be found.
            hash (str): The hash identifying the image.

        Returns:
            List[GdkPixbuf.Pixbuf]: The thumb_64 and thumb_128 if available,
                None otherwise.
        """
        path_128 = dir + "normal/" + hash + ".png"
        interpolation = GdkPixbuf.InterpType.BILINEAR

        # The cache dirs might have resolutions of 256 and/or 128,
        # while we need 128 (for iconview) and 64 (for listview).
        # First, try the 128 version since that's the native resolution we want.
        try:
            thumb_128 = GdkPixbuf.Pixbuf.new_from_file(path_128)
            w, h = thumb_128.get_width(), thumb_128.get_height()
            thumb_64 = thumb_128.scale_simple(w / 2, h / 2, interpolation)
            return thumb_64, thumb_128
        except GLib.GError:
            # path_128 doesn't exist, try the 256 version.
            path_256 = dir + "large/" + hash + ".png"
            try:
                thumb_256 = GdkPixbuf.Pixbuf.new_from_file(path_256)
                w, h = thumb_256.get_width(), thumb_256.get_height()
                thumb_128 = thumb_256.scale_simple(w / 2, h / 2, interpolation)
                thumb_64 = thumb_256.scale_simple(w / 4, h / 4, interpolation)
                return thumb_64, thumb_128
            except GLib.GError:
                return None, None

    def _generateThumbnails(self, uri):
        if not self.thumbnailer:
            return None
        # This way of getting the mimetype feels awfully convoluted but
        # seems to be the proper/reliable way in a GNOME context
        asset_file = Gio.file_new_for_uri(uri)
        info = asset_file.query_info(attributes="standard::*",
                                     flags=Gio.FileQueryInfoFlags.NONE,
                                     cancellable=None)
        mime = Gio.content_type_get_mime_type(info.get_content_type())
        mtime = os.path.getmtime(path_from_uri(uri))
        if not self.thumbnailer.can_thumbnail(uri, mime, mtime):
            self.debug("Thumbnailer says it can't thumbnail %s", uri)
            return None
        pixbuf_128 = self.thumbnailer.generate_thumbnail(uri, mime)
        if not pixbuf_128:
            self.debug("Thumbnailer failed thumbnailing %s", uri)
            return None
        self.thumbnailer.save_thumbnail(pixbuf_128, uri, mtime)
        pixbuf_64 = pixbuf_128.scale_simple(
            64, 64, GdkPixbuf.InterpType.BILINEAR)
        return pixbuf_128, pixbuf_64

    def _addAsset(self, asset):
        # 128 is the normal size for thumbnails, but for *icons* it looks
        # insane
        LARGE_SIZE = 96
        info = asset.get_info()

        if self.app.proxy_manager.is_proxy_asset(asset) and \
                not asset.props.proxy_target:
            self.info("%s is a proxy asset but has no target, "
                      "not displaying it.", asset.props.id)
            return

        self.debug("Adding asset %s", asset.props.id)

        # The code below tries to read existing thumbnails from the freedesktop
        # thumbnails directory (~/.thumbnails). The filenames are simply
        # the file URI hashed with md5, so we can retrieve them easily.
        video_streams = [
            stream_info for stream_info in info.get_stream_list()
            if isinstance(stream_info, GstPbutils.DiscovererVideoInfo)]
        real_uri = get_proxy_target(asset).props.id
        if video_streams:
            # From the freedesktop spec: "if the environment variable
            # $XDG_CACHE_HOME is set and not blank then the directory
            # $XDG_CACHE_HOME/thumbnails will be used, otherwise
            # $HOME/.cache/thumbnails will be used."
            # Older version of the spec also mentioned $HOME/.thumbnails
            quoted_uri = quote_uri(real_uri)
            thumbnail_hash = md5(quoted_uri.encode()).hexdigest()
            try:
                thumb_dir = os.environ['XDG_CACHE_HOME']
                thumb_64, thumb_128 = self._getThumbnailInDir(
                    thumb_dir, thumbnail_hash)
            except KeyError:
                thumb_64, thumb_128 = (None, None)
            if thumb_64 is None:
                thumb_dir = os.path.expanduser("~/.cache/thumbnails/")
                thumb_64, thumb_128 = self._getThumbnailInDir(
                    thumb_dir, thumbnail_hash)
            if thumb_64 is None:
                thumb_dir = os.path.expanduser("~/.thumbnails/")
                thumb_64, thumb_128 = self._getThumbnailInDir(
                    thumb_dir, thumbnail_hash)
            if thumb_64 is None:
                if asset.is_image():
                    thumb_64 = self._getIcon("image-x-generic")
                    thumb_128 = self._getIcon(
                        "image-x-generic", None, LARGE_SIZE)
                else:
                    thumb_cache = getThumbnailCache(asset)
                    thumb_64 = thumb_cache.getPreviewThumbnail()
                    if not thumb_64:
                        thumb_64 = self._getIcon("video-x-generic")
                        thumb_128 = self._getIcon("video-x-generic",
                                                  None, LARGE_SIZE)
                    else:
                        thumb_128 = thumb_64.scale_simple(
                            128, thumb_64.get_height() * 2,
                            GdkPixbuf.InterpType.BILINEAR)
        else:
            thumb_64 = self._getIcon("audio-x-generic")
            thumb_128 = self._getIcon("audio-x-generic", None, LARGE_SIZE)

        thumbs_decorator = ThumbnailsDecorator([thumb_64, thumb_128], asset,
                                               self.app.proxy_manager)
        if info.get_duration() == Gst.CLOCK_TIME_NONE:
            duration = ''
        else:
            duration = beautify_length(info.get_duration())
        name = info_name(asset)
        self.pending_rows.append((thumbs_decorator.thumb_64,
                                  thumbs_decorator.thumb_128,
                                  beautify_asset(asset),
                                  asset,
                                  asset.props.id,
                                  duration,
                                  name,
                                  thumbs_decorator))
        self._flushPendingRows()

    def _flushPendingRows(self):
        self.debug("Flushing %d pending model rows", len(self.pending_rows))
        for row in self.pending_rows:
            self.storemodel.append(row)

        del self.pending_rows[:]

    # medialibrary callbacks

    def _assetLoadingProgressCb(self, project, progress, estimated_time):
        self._progressbar.set_fraction(progress / 100)

        for row in self.storemodel:
            row[COL_INFOTEXT] = beautify_asset(row[COL_ASSET])

        if progress == 0:
            self._startImporting(project)
            return

        if project.loaded:
            num_proxying_files = [asset
                                  for asset in project.loading_assets
                                  if not asset.ready]
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
                                len(num_proxying_files))
            progress_message = template % (
                len(num_proxying_files), progress,
                self.__last_proxying_estimate_time)
            self._progressbar.set_text(progress_message)
            self._last_imported_uris.update([asset.props.id for asset in
                                             project.loading_assets])

        if progress == 100:
            self._doneImporting()

    def __assetProxyingCb(self, proxy, unused_pspec):
        self.debug("Proxy is %s", proxy.props.id)
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
            self.app.gui.timeline_ui.switchProxies(asset)

    def _assetAddedCb(self, unused_project, asset):
        """Checks whether the asset added to the project should be shown."""
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
        self.debug("%s Disconnecting %s - %s", self, asset, asset.props.id)
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
        self._flushPendingRows()
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

        missing_thumbs = self._missing_thumbs
        self._missing_thumbs = []
        if missing_thumbs:
            self.info("Generating missing thumbnails: %d", len(missing_thumbs))
            self._thumbs_process = threading.Thread(
                target=MediaLibraryWidget._generateThumbnailsThread, args=(self, missing_thumbs))
            self._thumbs_process.start()

        self._selectLastImportedUris()

    def __projectSettingsSetFromImportedAssetCb(self, unused_project, asset):
        asset_path = path_from_uri(asset.get_id())
        file_name = os.path.basename(asset_path)
        message = _("The project settings have been set to match file '%s'") % file_name
        label = Gtk.Label(message)
        label.set_line_wrap(True)
        content_area = self._project_settings_set_infobar.get_content_area()
        for widget in content_area.get_children():
            content_area.remove(widget)
        content_area.add(label)
        self._project_settings_set_infobar.show_all()

    def _selectLastImportedUris(self):
        if not self._last_imported_uris:
            return
        self._selectSources(self._last_imported_uris)
        self._last_imported_uris = set()

    def _generateThumbnailsThread(self, missing_thumbs):
        for uri in missing_thumbs:
            thumbnails = self._generateThumbnails(uri)
            if not thumbnails:
                continue
            pixbuf_128, pixbuf_64 = thumbnails
            # Search through the model for the row corresponding to the asset.
            found = False
            for row in self.storemodel:
                if uri == row[COL_URI]:
                    found = True
                    # Finally, show the new pixbuf in the UI
                    if pixbuf_128:
                        row[COL_ICON_128] = pixbuf_128
                    if pixbuf_64:
                        row[COL_ICON_64] = pixbuf_64
                    break
            if not found:
                # Can happen if the user removed the asset in the meanwhile.
                self.log(
                    "%s needed a thumbnail, but vanished from storemodel", uri)

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
            self.app.gui.showProjectSettingsDialog()
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
            self.__showErrors()
        self._resetErrorList()
        infobar.hide()

    def _resetErrorList(self):
        self._errors = []
        self._import_warning_infobar.hide()

    def __showErrors(self):
        """Shows a dialog with the import errors."""
        if len(self._errors) > 1:
            msgs = (_("Error while analyzing files"),
                    _("The following files can not be used with Pitivi."))
        else:
            msgs = (_("Error while analyzing a file"),
                    _("The following file can not be used with Pitivi."))
        error_dialogbox = FileListErrorDialog(*msgs)
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

    def __getPathUnderMouse(self, view, event):
        if isinstance(view, Gtk.TreeView):
            path = None
            tup = view.get_path_at_pos(int(event.x), int(event.y))
            if tup:
                path, column, x, y = tup
            return path
        elif isinstance(view, Gtk.IconView):
            return view.get_path_at_pos(int(event.x), int(event.y))
        else:
            raise RuntimeError(
                "Unknown media library view type: %s" % type(view))

    def _rowUnderMouseSelected(self, view, event):
        path = self.__getPathUnderMouse(view, event)
        if isinstance(view, Gtk.TreeView):
            path = None
            tup = view.get_path_at_pos(int(event.x), int(event.y))
            if tup:
                path, column, x, y = tup
            if path:
                selection = view.get_selection()

                return selection.path_is_selected(path) and selection.count_selected_rows() > 0
        elif isinstance(view, Gtk.IconView):
            path = view.get_path_at_pos(int(event.x), int(event.y))
            if path:
                selection = view.get_selected_items()
                return view.path_is_selected(path) and len(selection)
        else:
            raise RuntimeError(
                "Unknown media library view type: %s" % type(view))

        return False

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

    def __stopUsingProxyCb(self,
                           unused_action,
                           unused_parameter):
        self._project.disableProxiesForAssets(self.getSelectedAssets())

    def __useProxiesCb(self, unused_action, unused_parameter):
        self._project.useProxiesForAssets(self.getSelectedAssets())

    def __deleteProxiesCb(self, unused_action, unused_parameter):
        self._project.disableProxiesForAssets(self.getSelectedAssets(), delete_proxy_file=True)

    def __createMenuModel(self):
        if self.app.proxy_manager.proxyingUnsupported:
            return None, None

        assets = self.getSelectedAssets()
        if not assets:
            return None, None

        action_group = Gio.SimpleActionGroup()
        menu_model = Gio.Menu()

        proxies = [asset.get_proxy_target() for asset in assets
                   if asset.get_proxy_target()]
        in_progress = [asset.creation_progress for asset in assets
                       if asset.creation_progress < 100]

        if proxies or in_progress:
            action = Gio.SimpleAction.new("unproxy-asset", None)
            action.connect("activate", self.__stopUsingProxyCb)
            action_group.insert(action)
            text = ngettext("Do not use proxy for selected asset",
                            "Do not use proxies for selected assets",
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
            text = ngettext("Use proxy for selected asset",
                            "Use proxies for selected assets", len(assets))

            menu_model.append(text, "assets.%s" %
                              action.get_name().replace(" ", "."))

        return menu_model, action_group

    def __maybeShowPopoverMenu(self, view, event):
        res, button = event.get_button()
        if not res or button != 3:
            return False

        if not self._rowUnderMouseSelected(view, event):
            path = self.__getPathUnderMouse(view, event)
            if path:
                if isinstance(view, Gtk.IconView):
                    view.unselect_all()
                    view.select_path(path)
                else:
                    selection = view.get_selection()
                    selection.unselect_all()
                    selection.select_path(path)

        model, action_group = self.__createMenuModel()
        if not model:
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
        self._flushPendingRows()

    def _newProjectFailedCb(self, unused_project_manager, unused_uri, unused_reason):
        self.storemodel.clear()
        self._project = None

    def _projectClosedCb(self, unused_project_manager, unused_project):
        self.__disconnectFromProject()
        self._project_settings_set_infobar.hide()
        self.storemodel.clear()
        self._project = None

    def _addUris(self, uris):
        if self._project:
            self._project.addUris(uris)
        else:
            self.warning(
                "Adding uris to project, but the project has changed in the meantime")
        return False

    # Drag and Drop
    def _dndDataReceivedCb(self, unused_widget, unused_context, unused_x,
                           unused_y, selection, targettype, unused_time):
        self.debug("targettype: %d, selection.data: %r",
                   targettype, selection.get_data())

        directories = []
        filenames = []

        uris = selection.get_uris()
        # Filter out the empty uris.
        uris = [x for x in uris if x]
        for raw_uri in uris:
            # Strip out NULL chars first.
            raw_uri = raw_uri.strip('\x00')
            uri = urlparse(raw_uri)
            if uri.scheme == 'file':
                path = unquote(uri.path)
                if os.path.isfile(path):
                    filenames.append(raw_uri)
                elif os.path.isdir(path):
                    directories.append(raw_uri)
                else:
                    self.warning("Unusable file: %s, %s", raw_uri, path)
            else:
                self.fixme(
                    "Importing remote files is not implemented: %s", raw_uri)

        if directories:
            # Recursively import from folders that were dragged into the
            # library
            self.app.threads.addThread(PathWalker, directories, self._addUris)
        if filenames:
            self._last_imported_uris.update(filenames)
            assets = self._project.assetsForUris(list(self._last_imported_uris))
            if assets:
                # All the files have already been added.
                self._selectLastImportedUris()
            else:
                self._project.addUris(filenames)

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
            Gtk.drag_set_icon_pixbuf(context, row[COL_ICON_64], 0, 0)

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
