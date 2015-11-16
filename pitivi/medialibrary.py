# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/medialibrary.py
#
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

from gi.repository import Gst
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GdkPixbuf
from gi.repository.GstPbutils import DiscovererVideoInfo

import os
import threading
import time

from gettext import ngettext, gettext as _
from hashlib import md5
from urllib.parse import unquote
from urllib.parse import urlparse

from pitivi.check import missing_soft_deps
from pitivi.configure import get_ui_dir, get_pixmap_dir
from pitivi.dialogs.clipmediaprops import ClipMediaPropsDialog
from pitivi.dialogs.filelisterrordialog import FileListErrorDialog
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import PathWalker, quote_uri, path_from_uri
from pitivi.utils.ui import beautify_info, beautify_length, info_name, \
    URI_TARGET_ENTRY, FILE_TARGET_ENTRY, SPACING

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
    str, object, str, str, str)

(COL_ICON_64,
 COL_ICON_128,
 COL_INFOTEXT,
 COL_ASSET,
 COL_URI,
 COL_LENGTH,
 COL_SEARCH_TEXT) = list(range(len(STORE_MODEL_STRUCTURE)))

ui = '''
<ui>
    <accelerator action="RemoveSources" />
    <accelerator action="InsertEnd" />
</ui>
'''

# This whitelist is made from personal knowledge of file extensions in the wild,
# from gst-inspect |grep demux,
# http://en.wikipedia.org/wiki/Comparison_of_container_formats and
# http://en.wikipedia.org/wiki/List_of_file_formats#Video
# ...and looking at the contents of /usr/share/mime
SUPPORTED_FILE_FORMATS = {
    "video": ("3gpp", "3gpp2", "dv", "mp2t", "mp4", "mpeg", "ogg", "quicktime", "webm", "x-flv", "x-matroska", "x-mng", "x-ms-asf", "x-msvideo", "x-ms-wmp", "x-ms-wmv", "x-ogm+ogg", "x-theora+ogg"),
    "application": ("mxf",),
    # Don't forget audio formats
    "audio": ("aac", "ac3", "basic", "flac", "mp2", "mp4", "mpeg", "ogg", "opus", "webm", "x-adpcm", "x-aifc", "x-aiff", "x-aiffc", "x-ape", "x-flac+ogg", "x-m4b", "x-matroska", "x-ms-asx", "x-ms-wma", "x-speex", "x-speex+ogg", "x-vorbis+ogg", "x-wav"),
    # ...and image formats
    "image": ("jp2", "jpeg", "png", "svg+xml")}
# Stuff that we're not too confident about but might improve eventually:
OTHER_KNOWN_FORMATS = ("video/mp2t",)


class MediaLibraryWidget(Gtk.Box, Loggable):

    """ Widget for listing sources """

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_LAST, None,
                 (GObject.TYPE_PYOBJECT,))}

    def __init__(self, app, uiman):
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
        self.import_start_time = time.time()
        self._last_imported_uris = []

        self.set_orientation(Gtk.Orientation.VERTICAL)
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "medialibrary.ui"))
        builder.connect_signals(self)
        self._welcome_infobar = builder.get_object("welcome_infobar")
        self._import_warning_infobar = builder.get_object("warning_infobar")
        self._import_warning_infobar.hide()
        self._warning_label = builder.get_object("warning_label")
        self._view_error_button = builder.get_object("view_error_button")
        toolbar = builder.get_object("medialibrary_toolbar")
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        self._import_button = builder.get_object("media_import_button")
        self._remove_button = builder.get_object("media_remove_button")
        self._clipprops_button = builder.get_object("media_props_button")
        self._insert_button = builder.get_object("media_insert_button")
        self._listview_button = builder.get_object("media_listview_button")
        searchEntry = builder.get_object("media_search_entry")

        # Store
        self.storemodel = Gtk.ListStore(*STORE_MODEL_STRUCTURE)
        self.storemodel.set_sort_func(
            COL_URI, MediaLibraryWidget.compare_basename)
        # Prefer to sort the media library elements by URI
        # rather than show them randomly.
        self.storemodel.set_sort_column_id(COL_URI, Gtk.SortType.ASCENDING)

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

        # import sources dialogbox
        self._importDialog = None

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
        txtcell.set_property("ellipsize", Pango.EllipsizeMode.END)
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
        cell.set_property("ellipsize", Pango.EllipsizeMode.END)
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
            "new-project-created", self._newProjectCreatedCb)
        project_manager.connect("new-project-loaded", self._newProjectLoadedCb)
        project_manager.connect("new-project-failed", self._newProjectFailedCb)

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

        # Keyboard shortcuts for some items in the gtkbuilder file
        selection_actions = (
            ("RemoveSources", Gtk.STOCK_DELETE, _("_Remove from Project"),
             "<Control>Delete", None, self._removeSourcesCb),

            ("InsertEnd", Gtk.STOCK_COPY, _("Insert at _End of Timeline"),
             "Insert", None, self._insertEndCb),
        )
        self.selection_actions = Gtk.ActionGroup(name="medialibraryselection")
        self.selection_actions.add_actions(selection_actions)
        self.selection_actions.set_sensitive(False)
        uiman.insert_action_group(self.selection_actions, 0)
        uiman.add_ui_from_string(ui)

        # Set the state of the view mode toggle button.
        self._listview_button.set_active(self.clip_view == SHOW_TREEVIEW)
        # Make sure the proper view is displayed.
        self._displayClipView()

        # Add all the child widgets.
        self.pack_start(toolbar, False, False, 0)
        self.pack_start(self._welcome_infobar, False, False, 0)
        self.pack_start(self._import_warning_infobar, False, False, 0)
        self.pack_start(self.iconview_scrollwin, True, True, 0)
        self.pack_start(self.treeview_scrollwin, True, True, 0)
        self.pack_start(self._progressbar, False, False, 0)

        self.thumbnailer = MediaLibraryWidget._getThumbnailer()

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
        """
        Compare the model elements identified by the L{Gtk.TreeIter} elements.
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
                self.debug("Found asset: %s for uri: %s" % (asset, uri))
                return asset

        self.warning("Did not find any asser for uri: %s" % (uri))

    def _setupViewAsDragAndDropSource(self, view):
        view.drag_source_set(0, [], Gdk.DragAction.COPY)
        view.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, [URI_TARGET_ENTRY], Gdk.DragAction.COPY)
        view.drag_source_add_uri_targets()
        view.connect("drag-data-get", self._dndDragDataGetCb)
        view.connect("drag-begin", self._dndDragBeginCb)
        view.connect("drag-end", self._dndDragEndCb)

    def _importSourcesCb(self, unused_action):
        self._showImportSourcesDialog()

    def _removeSourcesCb(self, unused_action):
        self._removeSources()

    def _insertEndCb(self, unused_action):
        self.app.gui.timeline_ui.insertEnd(self.getSelectedAssets())

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

    def _setRowVisible(self, model, iter, data):
        """
        Toggle the visibility of a liststore row.
        Used for the search box.
        """
        text = data.get_text().lower()
        if not text:
            return True  # Avoid silly warnings
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
        """
        Connect signal handlers to a project.
        """
        project.connect("asset-added", self._assetAddedCb)
        project.connect("asset-removed", self._assetRemovedCb)
        project.connect("error-loading-asset", self._errorCreatingAssetCb)
        project.connect("done-importing", self._sourcesStoppedImportingCb)
        project.connect("start-importing", self._sourcesStartedImportingCb)

        # The start-importing signal would have already been emited at that
        # time, make sure to catch if it is the case
        if project.nb_remaining_file_to_import > 0:
            self._sourcesStartedImportingCb(project)

    def _setClipView(self, view_type):
        """
        Set which clip view to use when medialibrary is showing clips.
        view_type: one of SHOW_TREEVIEW or SHOW_ICONVIEW
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

        if not len(self.storemodel):
            self._welcome_infobar.show_all()

    def _showImportSourcesDialog(self):
        """Pop up the "Import Sources" dialog box"""
        if self._importDialog:
            return

        chooser_action = Gtk.FileChooserAction.OPEN
        dialogtitle = _("Select One or More Files")

        close_after = Gtk.CheckButton(label=_("Close after importing files"))
        close_after.set_active(self.app.settings.closeImportDialog)

        self._importDialog = Gtk.FileChooserDialog(
            title=dialogtitle, transient_for=None, action=chooser_action)

        self._importDialog.set_icon_name("pitivi")
        self._importDialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                                       _("Add"), Gtk.ResponseType.OK)
        self._importDialog.props.extra_widget = close_after
        self._importDialog.set_default_response(Gtk.ResponseType.OK)
        self._importDialog.set_select_multiple(True)
        self._importDialog.set_modal(True)
        self._importDialog.set_transient_for(self.app.gui)
        self._importDialog.set_current_folder(
            self.app.settings.lastImportFolder)
        self._importDialog.connect('response', self._dialogBoxResponseCb)
        previewer = PreviewWidget(self.app.settings)
        self._importDialog.set_preview_widget(previewer)
        self._importDialog.set_use_preview_label(False)
        self._importDialog.connect(
            'update-preview', previewer.add_preview_request)
        # Filter for the "known good" formats by default
        filt_supported = Gtk.FileFilter()
        filt_known = Gtk.FileFilter()
        filt_supported.set_name(_("Supported file formats"))
        for category, mime_types in SUPPORTED_FILE_FORMATS.items():
            for mime in mime_types:
                filt_supported.add_mime_type(category + "/" + mime)
                filt_known.add_mime_type(category + "/" + mime)
        # Also allow showing known but not reliable demuxers
        filt_known.set_name(_("All known file formats"))
        for fullmime in OTHER_KNOWN_FORMATS:
            filt_known.add_mime_type(fullmime)
        # ...and allow the user to override our whitelists
        default = Gtk.FileFilter()
        default.set_name(_("All files"))
        default.add_pattern("*")
        self._importDialog.add_filter(filt_supported)
        self._importDialog.add_filter(filt_known)
        self._importDialog.add_filter(default)
        self._importDialog.show()

    def _updateProgressbar(self):
        """
        Update the _progressbar with the ratio of clips imported vs the total
        """
        # The clip iter has a +1 offset in the progressbar label (to refer to
        # the actual # of the clip we're processing), but there is no offset
        # in the progressbar itself (to reflect the process being incomplete).
        current_clip_iter = self.app.project_manager.current_project.nb_imported_files
        total_clips = self.app.project_manager.current_project.nb_remaining_file_to_import + \
            current_clip_iter

        progressbar_text = (_("Importing clip %(current_clip)d of %(total)d") %
            {"current_clip": current_clip_iter + 1,
            "total": total_clips})
        self._progressbar.set_text(progressbar_text)
        if current_clip_iter == 0:
            self._progressbar.set_fraction(0.0)
        elif total_clips != 0:
            self._progressbar.set_fraction(
                current_clip_iter / float(total_clips))

    def _getThumbnailInDir(self, dir, hash):
        """
        For a given thumbnail cache directory and file URI hash, see if there're
        thumbnails available and return them in resolutions that pitivi expects.

        The cache dirs might have resolutions of 256 and/or 128,
        while we need 128 (for iconview) and 64 (for listview).
        """
        path_256 = dir + "large/" + hash + ".png"
        path_128 = dir + "normal/" + hash + ".png"
        interpolation = GdkPixbuf.InterpType.BILINEAR

        # First, try the 128 version since that's the native resolution we
        # want:
        try:
            thumb_128 = GdkPixbuf.Pixbuf.new_from_file(path_128)
            w, h = thumb_128.get_width(), thumb_128.get_height()
            thumb_64 = thumb_128.scale_simple(w / 2, h / 2, interpolation)
            return thumb_64, thumb_128
        except GLib.GError:
            # path_128 doesn't exist, try the 256 version
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
            # TODO: Use thumbnails generated with GStreamer.
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

        # The code below tries to read existing thumbnails from the freedesktop
        # thumbnails directory (~/.thumbnails). The filenames are simply
        # the file URI hashed with md5, so we can retrieve them easily.
        video_streams = [
            i for i in info.get_stream_list() if isinstance(i, DiscovererVideoInfo)]
        if len(video_streams) > 0:
            # From the freedesktop spec: "if the environment variable
            # $XDG_CACHE_HOME is set and not blank then the directory
            # $XDG_CACHE_HOME/thumbnails will be used, otherwise
            # $HOME/.cache/thumbnails will be used."
            # Older version of the spec also mentioned $HOME/.thumbnails
            quoted_uri = quote_uri(info.get_uri())
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
                    thumb_64 = self._getIcon("video-x-generic")
                    thumb_128 = self._getIcon(
                        "video-x-generic", None, LARGE_SIZE)
                # TODO ideally gst discoverer should create missing thumbnails.
                self.log(
                    "Missing a thumbnail for %s, queuing", path_from_uri(quoted_uri))
                self._missing_thumbs.append(quoted_uri)
        else:
            thumb_64 = self._getIcon("audio-x-generic")
            thumb_128 = self._getIcon("audio-x-generic", None, LARGE_SIZE)

        if info.get_duration() == Gst.CLOCK_TIME_NONE:
            duration = ''
        else:
            duration = beautify_length(info.get_duration())

        name = info_name(info)

        self.pending_rows.append((thumb_64,
                                  thumb_128,
                                  beautify_info(info),
                                  asset,
                                  info.get_uri(),
                                  duration,
                                  name))
        if len(self.pending_rows) > 50:
            self._flushPendingRows()

    def _flushPendingRows(self):
        self.debug("Flushing %d pending model rows", len(self.pending_rows))
        for row in self.pending_rows:
            self.storemodel.append(row)
        del self.pending_rows[:]

    # medialibrary callbacks

    def _assetAddedCb(self, unused_project, asset,
                      unused_current_clip_iter=None, unused_total_clips=None):
        """ a file was added to the medialibrary """
        if isinstance(asset, GES.UriClipAsset):
            self._updateProgressbar()
            self._addAsset(asset)

    def _assetRemovedCb(self, unused_project, asset):
        """ the given uri was removed from the medialibrary """
        # find the good line in the storemodel and remove it
        model = self.storemodel
        uri = asset.get_id()
        for row in model:
            if uri == row[COL_URI]:
                model.remove(row.iter)
                break
        if not len(model):
            self._welcome_infobar.show_all()
        self.debug("Removing: %s", uri)

    def _errorCreatingAssetCb(self, unused_project, error, id, type):
        """ The given uri isn't a media file """
        if GObject.type_is_a(type, GES.UriClip):
            error = (id, str(error.domain), error)
            self._errors.append(error)
            self._updateProgressbar()

    def _sourcesStartedImportingCb(self, project):
        self.import_start_time = time.time()
        self._welcome_infobar.hide()
        self._progressbar.show()
        if project.loaded:
            # Some new files are being imported.
            self._last_imported_uris += [asset.props.id for asset in project.get_loading_assets()]

    def _sourcesStoppedImportingCb(self, unused_project):
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

    def _selectLastImportedUris(self):
        if not self._last_imported_uris:
            return
        self._selectSources(self._last_imported_uris)
        self._last_imported_uris = []

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

    def _dialogBoxResponseCb(self, dialogbox, response):
        self.debug("response: %r", response)
        if response == Gtk.ResponseType.OK:
            lastfolder = dialogbox.get_current_folder()
            self.app.settings.lastImportFolder = lastfolder
            self.app.settings.closeImportDialog = \
                dialogbox.props.extra_widget.get_active()
            filenames = dialogbox.get_uris()
            self.app.project_manager.current_project.addUris(filenames)
            if self.app.settings.closeImportDialog:
                dialogbox.destroy()
                self._importDialog = None
        else:
            dialogbox.destroy()
            self._importDialog = None

    def _removeSources(self):
        """
        Determine which clips are selected in the icon or list view,
        and ask MediaLibrary to remove them from the project.
        """
        model = self.treeview.get_model()
        paths = self.getSelectedPaths()
        if not paths:
            return
        # use row references so we don't have to care if a path has been
        # removed
        rows = []
        for path in paths:
            row = Gtk.TreeRowReference.new(model, path)
            rows.append(row)

        self.app.action_log.begin("remove clip from source list")
        for row in rows:
            asset = model[row.get_path()][COL_ASSET]
            self.app.project_manager.current_project.remove_asset(asset)
        self.app.action_log.commit()

    def _sourceIsUsed(self, asset):
        """Check if a given URI is present in the timeline"""
        layers = self.app.project_manager.current_project.timeline.get_layers()
        for layer in layers:
            for clip in layer.get_clips():
                if clip.get_asset() == asset:
                    return True
        return False

    def _selectUnusedSources(self):
        """
        Select, in the media library, unused sources in the project.
        """
        project = self.app.project_manager.current_project
        unused_sources_uris = []
        for asset in project.list_assets(GES.UriClip):
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
                else:
                    self.iconview.unselect_path(row.path)

    # UI callbacks

    def _removeClickedCb(self, unused_widget=None):
        """ Called when a user clicks on the remove button """
        self._removeSources()

    def _clipPropertiesCb(self, unused_widget=None):
        """
        Show the clip properties (resolution, framerate, audio channels...)
        and allow setting them as the new project settings.
        """
        paths = self.getSelectedPaths()
        if not paths:
            self.debug("No item selected")
            return
        # Only use the first item.
        path = paths[0]
        asset = self.storemodel[path][COL_ASSET]
        dialog = ClipMediaPropsDialog(
            self.app.project_manager.current_project, asset)
        dialog.dialog.set_transient_for(self.app.gui)
        dialog.run()

    def _warningInfoBarDismissedCb(self, unused_button):
        self._resetErrorList()

    def _resetErrorList(self):
        self._errors = []
        self._import_warning_infobar.hide()

    def _viewErrorsButtonClickedCb(self, unused_button):
        """
        Show a FileListErrorDialog to display import _errors.
        """
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
        # Reset the error list, since the user has read them.
        self._resetErrorList()

    def _toggleViewTypeCb(self, widget):
        if widget.get_active():
            self._setClipView(SHOW_TREEVIEW)
        else:
            self._setClipView(SHOW_ICONVIEW)

    def _rowUnderMouseSelected(self, view, event):
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

    def _treeViewButtonPressEventCb(self, treeview, event):
        self._updateDraggedPaths(treeview, event)

        Gtk.TreeView.do_button_press_event(treeview, event)

        ts = self.treeview.get_selection()
        if self._draggedPaths:
            for path in self._draggedPaths:
                ts.select_path(path)

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

    def _treeViewButtonReleaseEventCb(self, unused_treeview, event):
        ts = self.treeview.get_selection()
        state = event.get_state() & (
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
        path = self.treeview.get_path_at_pos(event.x, event.y)

        if not state and not self.dragged:
            ts.unselect_all()
            if path:
                ts.select_path(path[0])

    def _viewSelectionChangedCb(self, unused):
        selected_items = len(self.getSelectedPaths())
        if selected_items:
            self.selection_actions.set_sensitive(True)
            self._remove_button.set_sensitive(True)
            self._insert_button.set_sensitive(True)
            # Some actions can only be done on a single item at a time:
            self._clipprops_button.set_sensitive(False)
            if selected_items == 1:
                self._clipprops_button.set_sensitive(True)
        else:
            self.selection_actions.set_sensitive(False)
            self._remove_button.set_sensitive(False)
            self._insert_button.set_sensitive(False)
            self._clipprops_button.set_sensitive(False)

    def _itemOrRowActivatedCb(self, unused_view, path, *unused_column):
        """
        When an item is double-clicked, or
        Space, Shift+Space, Return or Enter is pressed, preview the clip.
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
        control_mask = event.get_state() & Gdk.ModifierType.CONTROL_MASK
        shift_mask = event.get_state() & Gdk.ModifierType.SHIFT_MASK
        modifier_active = control_mask or shift_mask
        if not modifier_active and self.iconview_cursor_pos:
            current_cursor_pos = self.iconview.get_path_at_pos(
                event.x, event.y)

            if current_cursor_pos == self.iconview_cursor_pos:
                if iconview.path_is_selected(current_cursor_pos):
                    iconview.unselect_all()
                    iconview.select_path(current_cursor_pos)

    def _newProjectCreatedCb(self, unused_app, project):
        if self._project is not project:
            self._project = project
            self._resetErrorList()
            self.storemodel.clear()
            self._welcome_infobar.show_all()
            self._connectToProject(project)

    def _newProjectLoadedCb(self, unused_app, project, unused_fully_ready):
        if self._project is not project:
            self._project = project
            self.storemodel.clear()
            self._connectToProject(project)

        # Make sure that the sources added to the project are added added
        self._flushPendingRows()

    def _newProjectFailedCb(self, unused_pitivi, unused_reason, unused_uri):
        self.storemodel.clear()
        self._project = None

    def _addUris(self, uris):
        if self.app.project_manager.current_project:
            self.app.project_manager.current_project.addUris(uris)
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
            self._last_imported_uris += filenames
            project = self.app.project_manager.current_project
            assets = project.assetsForUris(self._last_imported_uris)
            if assets:
                # All the files have already been added.
                self._selectLastImportedUris()
            else:
                project.addUris(filenames)

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
        """ Returns a list of selected treeview or iconview items """
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
        """ Returns a list of selected items URIs """
        if self._draggedPaths:
            return [self.modelFilter[path][COL_URI]
                    for path in self._draggedPaths]
        return [self.modelFilter[path][COL_URI]
                for path in self.getSelectedPaths()]

    def getSelectedAssets(self):
        """ Returns a list of selected items URIs """
        if self._draggedPaths:
            return [self.modelFilter[path][COL_ASSET]
                    for path in self._draggedPaths]
        return [self.modelFilter[path][COL_ASSET]
                for path in self.getSelectedPaths()]

    def activateCompactMode(self):
        self._import_button.set_is_important(False)
