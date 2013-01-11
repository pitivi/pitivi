# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
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
from gi.repository import GObject
from gi._glib import GError
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GdkPixbuf

import os
import time

from urllib import unquote
from gettext import gettext as _
from hashlib import md5
from gi.repository.GstPbutils import DiscovererVideoInfo

from pitivi.configure import get_ui_dir, get_pixmap_dir
from pitivi.settings import GlobalSettings
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.dialogs.filelisterrordialog import FileListErrorDialog
from pitivi.dialogs.clipmediaprops import clipmediapropsDialog
from pitivi.utils.ui import beautify_length
from pitivi.utils.misc import PathWalker
from pitivi.utils.signal import SignalGroup
from pitivi.utils.loggable import Loggable
import pitivi.utils.ui as dnd
from pitivi.utils.ui import beautify_info, info_name, SPACING

from pitivi.utils.ui import TYPE_PITIVI_FILESOURCE

MAX_SHORT_NAME_LENGTH = 32

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
    str, object, str, str, str, str)

(COL_ICON,
 COL_ICON_LARGE,
 COL_INFOTEXT,
 COL_ASSET,
 COL_URI,
 COL_LENGTH,
 COL_SEARCH_TEXT,
 COL_SHORT_TEXT) = range(len(STORE_MODEL_STRUCTURE))

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
SUPPORTED_FILE_FORMATS = {"video": ("3gpp", "3gpp2", "dv", "mp4", "mpeg", "ogg", "quicktime", "webm", "x-flv", "x-matroska", "x-mng", "x-ms-asf", "x-msvideo", "x-ms-wmp", "x-ms-wmv", "x-ogm+ogg", "x-theora+ogg"),
    "application": ("mxf"),
    # Don't forget audio formats
    "audio": ("aac", "ac3", "basic", "flac", "mp2", "mp4", "mpeg", "ogg", "opus", "webm", "x-adpcm", "x-aifc", "x-aiff", "x-aiffc", "x-ape", "x-flac+ogg", "x-m4b", "x-matroska", "x-ms-asx", "x-ms-wma", "x-speex", "x-speex+ogg", "x-vorbis+ogg", "x-wav"),
    # ...and image formats
    "image": ("jp2", "jpeg", "png", "svg+xml")}
# Stuff that we're not too confident about but might improve eventually:
OTHER_KNOWN_FORMATS = ("video/mp2t")


def compare_simple(model, iter1, iter2, user_data):
    if model[iter1][user_data] < model[iter2][user_data]:
        return -1
    # Each element is unique, there is a strict order.
    return 1


class MediaLibraryWidget(Gtk.VBox, Loggable):
    """ Widget for listing sources """

    __gsignals__ = {
        'play': (GObject.SignalFlags.RUN_LAST, None,
                (GObject.TYPE_PYOBJECT,))}

    def __init__(self, instance, uiman):
        Gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.pending_rows = []

        self.app = instance
        self._errors = []
        self._project = None
        self._draggedPaths = None
        self.dragged = False
        self.clip_view = self.app.settings.lastClipView

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "medialibrary.ui"))
        builder.connect_signals(self)
        self._welcome_infobar = builder.get_object("welcome_infobar")
        self._import_warning_infobar = builder.get_object("warning_infobar")
        self._warning_label = builder.get_object("warning_label")
        self._view_error_button = builder.get_object("view_error_button")
        toolbar = builder.get_object("medialibrary_toolbar")
        toolbar.get_style_context().add_class("inline-toolbar")
        self._remove_button = builder.get_object("media_remove_button")
        self._clipprops_button = builder.get_object("media_props_button")
        self._insert_button = builder.get_object("media_insert_button")
        self._listview_button = builder.get_object("media_listview_button")
        searchEntry = builder.get_object("media_search_entry")

        # Store
        self.storemodel = Gtk.ListStore(*STORE_MODEL_STRUCTURE)
        self.storemodel.set_sort_func(COL_URI, compare_simple, user_data=COL_URI)
        # Prefer to sort the media library elements by URI
        # rather than show them randomly.
        self.storemodel.set_sort_column_id(COL_URI, Gtk.SortType.ASCENDING)

        # Scrolled Windows
        self.treeview_scrollwin = Gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        self.iconview_scrollwin = Gtk.ScrolledWindow()
        self.iconview_scrollwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.iconview_scrollwin.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        # import sources dialogbox
        self._importDialog = None

        # Filtering model for the search box.
        # Use this instead of using self.storemodel directly
        self.modelFilter = self.storemodel.filter_new()
        self.modelFilter.set_visible_func(self._setRowVisible, data=searchEntry)

        # TreeView
        # Displays icon, name, type, length
        self.treeview = Gtk.TreeView(self.modelFilter)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.connect("button-press-event", self._treeViewButtonPressEventCb)
        self.treeview.connect("button-release-event", self._treeViewButtonReleaseEventCb)
        self.treeview.connect("focus-in-event", self._disableKeyboardShortcutsCb)
        self.treeview.connect("focus-out-event", self._enableKeyboardShortcutsCb)
        self.treeview.connect("row-activated", self._itemOrRowActivatedCb)
        self.treeview.set_property("rules_hint", True)
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
        pixbufcol.add_attribute(pixcell, 'pixbuf', COL_ICON)

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
        self.iconview = Gtk.IconView(self.modelFilter)
        self.iconview_scrollwin.add(self.iconview)
        self.iconview.connect("button-press-event", self._iconViewButtonPressEventCb)
        self.iconview.connect("button-release-event", self._iconViewButtonReleaseEventCb)
        self.iconview.connect("focus-in-event", self._disableKeyboardShortcutsCb)
        self.iconview.connect("focus-out-event", self._enableKeyboardShortcutsCb)
        self.iconview.connect("item-activated", self._itemOrRowActivatedCb)
        self.iconview.connect("selection-changed", self._viewSelectionChangedCb)
        self.iconview.set_item_orientation(Gtk.Orientation.VERTICAL)
        self.iconview.set_property("has_tooltip", True)
        self.iconview.set_tooltip_column(COL_INFOTEXT)
        self.iconview.props.item_padding = 3
        self.iconview.props.margin = 3

        cell = Gtk.CellRendererPixbuf()
        self.iconview.pack_start(cell, False)
        self.iconview.add_attribute(cell, "pixbuf", COL_ICON_LARGE)

        cell = Gtk.CellRendererText()
        cell.props.alignment = Pango.Alignment.CENTER
        cell.props.xalign = 0.5
        cell.props.yalign = 0.0
        cell.props.xpad = 0
        cell.props.ypad = 0
        cell.props.width = 128
        cell.props.wrap_width = 128
        self.iconview.pack_start(cell, False)
        self.iconview.add_attribute(cell, "text", COL_SHORT_TEXT)

        self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        # The _progressbar that shows up when importing clips
        self._progressbar = Gtk.ProgressBar()
        self._progressbar.set_show_text(True)

        # Connect to project.  We must remove and reset the callbacks when
        # changing project.
        self.project_signals = SignalGroup()
        self.app.connect("new-project-created", self._newProjectCreatedCb)
        self.app.connect("new-project-loaded", self._newProjectLoadedCb)
        self.app.connect("new-project-failed", self._newProjectFailedCb)

        # default pixbufs
        self.audiofilepixbuf = self._getIcon("audio-x-generic")
        self.videofilepixbuf = self._getIcon("video-x-generic")

        # Drag and Drop
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [dnd.URI_TARGET_ENTRY, dnd.FILE_TARGET_ENTRY],
                           Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag_data_received", self._dndDataReceivedCb)

        self._setup_view_for_drag_and_drop(self.treeview, [("pitivi/file-source", 0, TYPE_PITIVI_FILESOURCE)])
        self._setup_view_for_drag_and_drop(self.iconview, [Gtk.TargetEntry.new("pitivi/file-source", 0, TYPE_PITIVI_FILESOURCE)])

        # Hack so that the views have the same method as self
        self.treeview.getSelectedItems = self.getSelectedItems

        # Keyboard shortcuts for some items in the gtkbuilder file
        selection_actions = (
            ("RemoveSources", Gtk.STOCK_DELETE, _("_Remove from Project"),
            "<Control>Delete", None, self._removeSourcesCb),

            ("InsertEnd", Gtk.STOCK_COPY, _("Insert at _End of Timeline"),
            "Insert", None, self._insertEndCb),
        )
        self.selection_actions = Gtk.ActionGroup("medialibraryselection")
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
        self.pack_start(self._progressbar, False, True, 0)

    def _setup_view_for_drag_and_drop(self, view, target_entries):
        view.drag_source_set(0, [], Gdk.DragAction.COPY)
        view.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, target_entries, Gdk.DragAction.COPY)
        view.drag_source_set_target_list(None)
        view.drag_source_add_uri_targets()
        view.drag_source_add_text_targets()

        view.connect("drag_begin", self._dndDragBeginCb)
        view.connect("drag-end", self._dndDragEndCb)

    def _importSourcesCb(self, unused_action):
        self.showImportSourcesDialog()

    def _removeSourcesCb(self, unused_action):
        self._removeSources()

    def _insertEndCb(self, unused_action):
        self.app.gui.timeline_ui.insertEnd(self.getSelectedAssets())

    def _disableKeyboardShortcutsCb(self, *unused_args):
        """
        Disable the Delete keyboard shortcut and playback shortcuts
        to prevent accidents or being unable to type various characters.

        This is used when focusing the search entry, icon on tree view widgets.
        """
        self.app.gui.setActionsSensitive(False)

    def _enableKeyboardShortcutsCb(self, *unused_args):
        """
        When focusing out of media library widgets,
        re-enable the timeline keyboard shortcuts.
        """
        self.app.gui.setActionsSensitive(True)

    def _trackObjectAddedCb(self, source, trackobj):
        """ After an object has been added to the first track, position it
        correctly and request the next source to be processed. """
        timeline = self.app.current.timeline
        layer = timeline.get_layers()[0]  # FIXME Get the longest layer

        # Handle the case where we just inserted the first clip
        if len(layer.get_objects()) == 1:
            source.props.start = 0
        else:
            source.props.start = timeline.props.duration

        # We only need one TrackObject to estimate the new duration.
        # Process the next source.
        source.disconnect_by_func(self._trackObjectAddedCb)
        self._insertNextSource()

    def _searchEntryChangedCb(self, entry):
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
        if text == "":
            return True  # Avoid silly warnings
        else:
            return text in model.get_value(iter, COL_INFOTEXT).lower()

    def _getIcon(self, iconname, alternate=None):
        icontheme = Gtk.IconTheme.get_default()
        pixdir = get_pixmap_dir()
        icon = None
        try:
            icon = icontheme.load_icon(iconname, 48, 0)
        except:
            # empty except clause is bad but load_icon raises Gio.Error.
            # Right, *gio*.
            if alternate:
                icon = GdkPixbuf.Pixbuf.new_from_file(os.path.join(pixdir, alternate))
            else:
                icon = icontheme.load_icon("dialog-question", 48, 0)
        return icon

    def _connectToProject(self, project):
        """Connect signal handlers to a project.

        This first disconnects any handlers connected to an old project.
        If project is None, this just disconnects any connected handlers.
        """
        self.project_signals.connect(project, "asset-added", None,
                self._assetAddedCb)
        self.project_signals.connect(project, "asset-removed", None,
                self._assetRemovedCb)
        self.project_signals.connect(project, "error-loading-asset",
                 None, self._errorCreatingAssetCb)
        self.project_signals.connect(project, "done-importing", None,
                self._sourcesStoppedImportingCb)
        self.project_signals.connect(project, "start-importing", None,
                self._sourcesStartedImportingCb)

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

    def showImportSourcesDialog(self):
        """Pop up the "Import Sources" dialog box"""
        if self._importDialog:
            return

        chooser_action = Gtk.FileChooserAction.OPEN
        dialogtitle = _("Select One or More Files")

        close_after = Gtk.CheckButton(_("Close after importing files"))
        close_after.set_active(self.app.settings.closeImportDialog)

        self._importDialog = Gtk.FileChooserDialog(dialogtitle, None,
                                           chooser_action,
                                           (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,
                                            Gtk.STOCK_ADD, Gtk.ResponseType.OK))
        self._importDialog.set_icon_name("pitivi")
        self._importDialog.props.extra_widget = close_after
        self._importDialog.set_default_response(Gtk.ResponseType.OK)
        self._importDialog.set_select_multiple(True)
        self._importDialog.set_modal(False)
        self._importDialog.set_current_folder(self.app.settings.lastImportFolder)
        self._importDialog.connect('response', self._dialogBoxResponseCb)
        self._importDialog.connect('close', self._dialogBoxCloseCb)
        pw = PreviewWidget(self.app)
        self._importDialog.set_preview_widget(pw)
        self._importDialog.set_use_preview_label(False)
        self._importDialog.connect('update-preview', pw.add_preview_request)
        # Filter for the "known good" formats by default
        filt_supported = Gtk.FileFilter()
        filt_known = Gtk.FileFilter()
        filt_supported.set_name(_("Supported file formats"))
        for category in SUPPORTED_FILE_FORMATS:
            # Category can be "video", "audio", "image", "application"
            for mime in SUPPORTED_FILE_FORMATS[category]:
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
        current_clip_iter = self.app.current.nb_imported_files
        total_clips = self.app.current.nb_files_to_import

        progressbar_text = _("Importing clip %(current_clip)d of %(total)d" %
            {"current_clip": current_clip_iter,
            "total": total_clips})
        self._progressbar.set_text(progressbar_text)
        if current_clip_iter == 0:
            self._progressbar.set_fraction(0.0)
        elif total_clips != 0:
            self._progressbar.set_fraction((current_clip_iter - 1) / float(total_clips))

    def _getThumbnailInDir(self, dir, hash):
        thumb_path_normal = dir + "normal/" + hash + ".png"

        try:
            thumbnail = GdkPixbuf.Pixbuf.new_from_file(thumb_path_normal)
            thumbnail_large = thumbnail
            thumbnail_height = int(thumbnail.get_height() / 2)
            thumbnail = thumbnail.scale_simple(64, thumbnail_height,
                GdkPixbuf.InterpType.BILINEAR)

            return thumbnail, thumbnail_large
        except GError:
            return None, None

    def _addAsset(self, asset):
        info = asset.get_info()

        # The code below tries to read existing thumbnails from the freedesktop
        # thumbnails directory (~/.thumbnails). The filenames are simply
        # the file URI hashed with md5, so we can retrieve them easily.
        video_streams = [i for i in info.get_stream_list() if isinstance(i, DiscovererVideoInfo)]
        if len(video_streams) > 0:
            # From the freedesktop spec: "if the environment variable
            # $XDG_CACHE_HOME is set and not blank then the directory
            # $XDG_CACHE_HOME/thumbnails will be used, otherwise
            # $HOME/.cache/thumbnails will be used."
            # Older version of the spec also mentioned $HOME/.thumbnails
            thumbnail_hash = md5(info.get_uri()).hexdigest()
            try:
                thumb_dir = os.environ['XDG_CACHE_HOME']
                thumbnail, thumbnail_large = self._getThumbnailInDir(thumb_dir, thumbnail_hash)
            except KeyError:
                thumbnail, thumbnail_large = (None, None)
            if thumbnail is None:
                thumb_dir = os.path.expanduser("~/.cache/thumbnails/")
                thumbnail, thumbnail_large = self._getThumbnailInDir(thumb_dir, thumbnail_hash)
            if thumbnail is None:
                thumb_dir = os.path.expanduser("~/.thumbnails/")
                thumbnail, thumbnail_large = self._getThumbnailInDir(thumb_dir, thumbnail_hash)
            if thumbnail is None:
                thumbnail = self.videofilepixbuf
                # TODO gst discoverer should create missing thumbnails.
                thumbnail_large = thumbnail
        else:
            thumbnail = self.audiofilepixbuf
            thumbnail_large = self.audiofilepixbuf

        if info.get_duration() == Gst.CLOCK_TIME_NONE:
            duration = ''
        else:
            duration = beautify_length(info.get_duration())

        name = info_name(info)
        short_name = None
        uni = unicode(name, 'utf-8')

        if len(uni) > MAX_SHORT_NAME_LENGTH:
            short_uni = uni[0:MAX_SHORT_NAME_LENGTH - 1] + u"…"
            short_name = short_uni.encode('utf-8')
        else:
            short_name = name

        self.pending_rows.append((thumbnail,
                                  thumbnail_large,
                                  beautify_info(info),
                                  asset,
                                  info.get_uri(),
                                  duration,
                                  name,
                                  short_name))
        if len(self.pending_rows) > 50:
            self.flush_pending_rows()

    def flush_pending_rows(self):
        for row in self.pending_rows:
            self.storemodel.append(row)
        del self.pending_rows[:]

    # medialibrary callbacks

    def _assetAddedCb(self, unused_project, asset,
            current_clip_iter=None, total_clips=None):
        """ a file was added to the medialibrary """
        if isinstance(asset, GES.AssetFileSource):
            self._updateProgressbar()
            self._addAsset(asset)

    def _assetRemovedCb(self, unsued_project, asset):
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
        self.debug("Removing %s", uri)

    def _errorCreatingAssetCb(self, unsued_project, error, id, type):
        """ The given uri isn't a media file """
        if GObject.type_is_a(type, GES.TimelineFileSource):
            error = (id, str(error.domain), error)
            self._errors.append(error)
            self._updateProgressbar()

    def _sourcesStartedImportingCb(self, unsued_project):
        self.import_start_time = time.time()
        self._welcome_infobar.hide()
        self._progressbar.show()

    def _sourcesStoppedImportingCb(self, unsued_project):
        self.debug("Importing took %.3f seconds" % (time.time() - self.import_start_time))
        self.flush_pending_rows()
        self._progressbar.hide()
        if self._errors:
            if len(self._errors) > 1:
                self._warning_label.set_text(_("Errors occurred while importing."))
                self._view_error_button.set_label(_("View errors"))
            else:
                self._warning_label.set_text(_("An error occurred while importing."))
                self._view_error_button.set_label(_("View error"))

            self._import_warning_infobar.show_all()

    ## Error Dialog Box callbacks

    def _errorDialogBoxCloseCb(self, unused_dialog):
        self._error_dialogbox.destroy()
        self._error_dialogbox = None

    def _errorDialogBoxResponseCb(self, unused_dialog, unused_response):
        self._error_dialogbox.destroy()
        self._error_dialogbox = None

    ## Import Sources Dialog Box callbacks

    def _dialogBoxResponseCb(self, dialogbox, response):
        self.debug("response:%r", response)
        if response == Gtk.ResponseType.OK:
            lastfolder = dialogbox.get_current_folder()
            self.app.settings.lastImportFolder = lastfolder
            self.app.settings.closeImportDialog = \
                dialogbox.props.extra_widget.get_active()
            filenames = dialogbox.get_uris()
            self.app.current.addUris(filenames)
            if self.app.settings.closeImportDialog:
                dialogbox.destroy()
                self._importDialog = None
        else:
            dialogbox.destroy()
            self._importDialog = None

    def _dialogBoxCloseCb(self, unused_dialogbox):
        self.debug("closing")
        self._importDialog = None

    def _removeSources(self):
        """
        Determine which clips are selected in the icon or list view,
        and ask MediaLibrary to remove them from the project.
        """
        model = self.treeview.get_model()
        paths = self.getSelectedPaths()
        if paths is None or paths < 1:
            return
        # use row references so we don't have to care if a path has been removed
        rows = []
        for path in paths:
            row = Gtk.TreeRowReference.new(model, path)
            rows.append(row)

        self.app.action_log.begin("remove clip from source list")
        for row in rows:
            asset = model[row.get_path()][COL_ASSET]
            self.app.current.remove_asset(asset)
        self.app.action_log.commit()

    def _sourceIsUsed(self, asset):
        """Check if a given URI is present in the timeline"""
        layers = self.app.current.timeline.get_layers()
        for layer in layers:
            for tlobj in layer.get_objects():
                if tlobj.get_asset() == asset:
                    return True
        return False

    def _selectUnusedSources(self):
        """
        Select, in the media library, unused sources in the project.
        """
        assets = self.app.current.list_assets(GES.TimelineFileSource)
        unused_sources_uris = []

        model = self.treeview.get_model()
        selection = self.treeview.get_selection()
        for asset in assets:
            if not self._sourceIsUsed(asset):
                unused_sources_uris.append(asset.get_uri())

        # Hack around the fact that making selections (in a treeview/iconview)
        # deselects what was previously selected
        if self.clip_view == SHOW_TREEVIEW:
            self.treeview.get_selection().select_all()
        elif self.clip_view == SHOW_ICONVIEW:
            self.iconview.select_all()

        for row in model:
            if row[COL_URI] not in unused_sources_uris:
                if self.clip_view == SHOW_TREEVIEW:
                    selection.unselect_iter(row.iter)
                else:
                    self.iconview.unselect_path(row.path)

    ## UI callbacks

    def _removeClickedCb(self, unused_widget=None):
        """ Called when a user clicks on the remove button """
        self._removeSources()

    def _clipPropertiesCb(self, unused_widget=None):
        """
        Show the clip properties (resolution, framerate, audio channels...)
        and allow setting them as the new project settings.
        """
        paths = self.getSelectedPaths()[0]  # Only use the first item
        model = self.treeview.get_model()
        info = model[paths][COL_ASSET].get_info()
        d = clipmediapropsDialog(self.app.current,
                                info.get_audio_streams(),
                                info.get_video_streams())
        d.run()

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
                    _("The following files can not be used with PiTiVi."))
        else:
            msgs = (_("Error while analyzing a file"),
                    _("The following file can not be used with PiTiVi."))
        self._error_dialogbox = FileListErrorDialog(*msgs)
        self._error_dialogbox.connect("close", self._errorDialogBoxCloseCb)
        self._error_dialogbox.connect("response", self._errorDialogBoxResponseCb)
        for uri, reason, extra in self._errors:
            self._error_dialogbox.addFailedFile(uri, reason, extra)
        self._error_dialogbox.window.show()
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
            assert False

        return False

    def _nothingUnderMouse(self, view, event):
        return not bool(view.get_path_at_pos(int(event.x), int(event.y)))

    def _viewGetFirstSelected(self):
        paths = self.getSelectedPaths()
        return paths[0]

    def _viewHasSelection(self):
        paths = self.getSelectedPaths()
        return bool(len(paths))

    def _viewGetPathAtPos(self, event):
        if self.clip_view == SHOW_TREEVIEW:
            pathinfo = self.treeview.get_path_at_pos(int(event.x), int(event.y))
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
        chain_up = True

        if event.type == getattr(Gdk.EventType, '2BUTTON_PRESS'):
            # It is possible to double-click outside of clips:
            if self.getSelectedPaths() != []:
                # Here we used to emit "play", but
                # this is now handled by _itemOrRowActivatedCb instead.
                pass
            chain_up = False
        elif not event.get_state() & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            chain_up = not self._rowUnderMouseSelected(treeview, event)

        if not chain_up:
            self._draggedPaths = self.getSelectedPaths()
        else:
            self._draggedPaths = None

        Gtk.TreeView.do_button_press_event(treeview, event)

        ts = self.treeview.get_selection()
        if self._draggedPaths:
            for path in self._draggedPaths:
                ts.select_path(path)

        return True

    def _treeViewButtonReleaseEventCb(self, treeview, event):
        ts = self.treeview.get_selection()
        state = event.get_state() & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
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
        path = self.modelFilter[path][COL_URI]
        self.emit('play', path)

    def _iconViewButtonPressEventCb(self, iconview, event):
        chain_up = True

        if event.type == getattr(Gdk.EventType, '2BUTTON_PRESS'):
            # It is possible to double-click outside of clips:
            if self.getSelectedPaths() != []:
                # Here we used to emit "play", but
                # this is now handled by _itemOrRowActivatedCb instead.
                pass
            chain_up = False
        elif not event.get_state() & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            chain_up = not self._rowUnderMouseSelected(iconview, event)

        if not chain_up:
            self._draggedPaths = self.getSelectedPaths()
        else:
            self._draggedPaths = None

        Gtk.IconView.do_button_press_event(iconview, event)

        if self._draggedPaths:
            for path in self._draggedPaths:
                self.iconview.select_path(path)

        self._ignoreRelease = chain_up

        return True

    def _iconViewButtonReleaseEventCb(self, iconview, event):
        state = event.get_state() & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
        path = self.iconview.get_path_at_pos(event.x, event.y)

        if not state and not self.dragged:
            iconview.unselect_all()
            if path:
                iconview.select_path(path)

    def _newProjectCreatedCb(self, app, project):
        if not self._project is project:
            self._project = project
            self._resetErrorList()
            self.storemodel.clear()
            self._connectToProject(project)

    def _newProjectLoadedCb(self, unused_pitivi, project):
        if not self._project is project:
            self._project = project
            self.storemodel.clear()
            self._connectToProject(project)

        # Make sure that the sources added to the project are added added
        self.flush_pending_rows()

    def _newProjectFailedCb(self, unused_pitivi, unused_reason, unused_uri):
        self.storemodel.clear()
        self.project_signals.disconnectAll()
        self._project = None

    ## Drag and Drop
    def _dndDataReceivedCb(self, unused_widget, unused_context, unused_x,
                           unused_y, selection, targettype, unused_time):

        self.debug("targettype:%d, selection.data:%r", targettype, selection.get_data())

        directories = []
        remote_files = []
        filenames = []

        uris = selection.get_data().split("\r\n")
        uris = filter(lambda x: x != "", uris)

        for uri in uris:
            uri = unquote(uri.strip('\x00'))
            if os.path.isfile(uri[7:]):
                filenames.append(uri)
            elif os.path.isdir(uri[7:]):
                directories.append(uri)
            elif "://" in uri:
                #FIXME Very dubious check.
                remote_files.append(uri)

        if len(directories):
            # Recursively import from folders that were dragged into the library
            self.app.threads.addThread(PathWalker, directories,
                                    self.app.current.addUris)
        if len(remote_files):
            #TODO waiting for remote files downloader support to be implemented
            pass
        if len(filenames):
            self.app.current.addUris(filenames)

    #used with TreeView and IconView
    def _dndDragBeginCb(self, view, context):
        self.info("tree drag_begin")
        self.dragged = True
        paths = self.getSelectedPaths()

        if len(paths) < 1:
            context.drag_abort(int(time.time()))
        else:
            row = self.modelFilter[paths[0]]
            Gtk.drag_set_icon_pixbuf(context, row[COL_ICON], 0, 0)

    def _dndDragEndCb(self, view, context):
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
