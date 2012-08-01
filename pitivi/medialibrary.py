# PiTiVi , Non-linear video editor
#
#       pitivi/medialibrary.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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
Handles the list of source for a project
"""

import gst
import ges
import gobject
import gtk
import pango
import os
import time

from urllib import unquote
from gettext import gettext as _
from hashlib import md5
from gst.pbutils import Discoverer, DiscovererVideoInfo

from pitivi.configure import get_pixmap_dir
from pitivi.settings import GlobalSettings
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.dialogs.filelisterrordialog import FileListErrorDialog
from pitivi.dialogs.clipmediaprops import clipmediapropsDialog
from pitivi.utils.ui import beautify_length
from pitivi.utils.misc import PathWalker, quote_uri
from pitivi.utils.signal import SignalGroup, Signallable
from pitivi.utils.loggable import Loggable
import pitivi.utils.ui as dnd
from pitivi.utils.ui import beautify_info, info_name, SPACING, PADDING

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

(COL_ICON,
 COL_ICON_LARGE,
 COL_INFOTEXT,
 COL_FACTORY,
 COL_URI,
 COL_LENGTH,
 COL_SEARCH_TEXT,
 COL_SHORT_TEXT) = range(8)

(LOCAL_FILE,
 LOCAL_DIR,
 REMOTE_FILE,
 NOT_A_FILE) = range(4)

ui = '''
<ui>
    <menubar name="MainMenuBar">
        <menu action="Library">
            <placeholder name="MediaLibrary" >
                <menuitem action="ImportSources" />
                <menuitem action="ImportSourcesFolder" />
                <separator />
                <menuitem action="SelectUnusedSources" />
                <separator />
                <menuitem action="InsertEnd" />
                <menuitem action="RemoveSources" />
                <menuitem action="PreviewClip" />
                <menuitem action="ClipProps" />
            </placeholder>
        </menu>
    </menubar>
    <toolbar name="MainToolBar">
        <placeholder name="MediaLibrary">
            <toolitem action="ImportSources" />
        </placeholder>
    </toolbar>
</ui>
'''

INVISIBLE = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir(),
    "invisible.png"))


class MediaLibraryError(Exception):
    pass


class MediaLibrary(Signallable, Loggable):
    discovererClass = Discoverer

    """
    Contains the sources for a project, stored as SourceFactory objects.

    @ivar discoverer: The discoverer object used internally
    @type discoverer: L{Discoverer}
    @ivar nb_files_to_import: The number of URIs on the last addUris call.
    @type nb_files_to_import: int
    @ivar nb_imported_files: The number of URIs loaded since the last addUris
    call.
    @type nb_imported_files: int

    Signals:
     - C{source-added} : A source has been discovered and added to the MediaLibrary.
     - C{source-removed} : A source was removed from the MediaLibrary.
     - C{discovery-error} : The given uri is not a media file.
     - C{nothing-to-import} : All the given uri were already imported
     - C{ready} : No more files are being discovered/added.
     - C{starting} : Some files are being discovered/added.
    """

    __signals__ = {
        "source-added": ["info"],
        "source-removed": ["uri"],
        "discovery-error": ["uri", "reason"],
        "nothing-to-import": [],
        "ready": [],
        "starting": [],
        }

    def __init__(self):
        Loggable.__init__(self)
        Signallable.__init__(self)
        # A (URI -> SourceFactory) map.
        self._sources = {}
        # A list of SourceFactory objects.
        self._ordered_sources = []
        self._resetImportCounters()

        self.discoverer = self.discovererClass.new(gst.SECOND)
        self.discoverer.connect("discovered", self.addDiscovererInfo)
        self.discoverer.connect("finished", self.finishDiscovererCb)
        self.discoverer.start()

    def _resetImportCounters(self):
        self.nb_files_to_import = 0
        self.nb_imported_files = 0

    def finishDiscovererCb(self, unused_discoverer):
        self.debug("Got the discoverer's finished signal")
        self._resetImportCounters()
        self.emit("ready")

    def addUris(self, uris):
        """
        Add c{uris} to the source list.

        The uris will be analyzed before being added.
        """
        self.emit("starting")
        self.debug("Adding %s", uris)
        self.nb_files_to_import += len(uris)
        for uri in uris:
            # Ensure we have a correctly encoded URI according to RFC 2396.
            # Otherwise, in some cases we'd get rogue characters that break
            # searching for duplicates
            uri = quote_uri(uri)
            if uri not in self._sources:
                self.discoverer.discover_uri_async(uri)
                self.debug("Added a uri to discoverer async")
            else:
                self.nb_files_to_import -= 1
                self.debug('"%s" is already in the media library' % uri)
        if self.nb_files_to_import == 0:
            # This is a cornercase hack for when you try to import a bunch of
            # clips that are all present in the media library already.
            # This will allow the progressbar to hide.
            self.emit("nothing-to-import")
        else:
            self.debug("Done adding all URIs to discoverer async")

    def removeUri(self, uri):
        """
        Remove the info for c{uri} from the source list.
        """
        # In theory we don't need quote_uri here, but since removeUri is public,
        # we can never be too sure.
        uri = quote_uri(uri)
        try:
            info = self._sources.pop(uri)
        except KeyError:
            raise MediaLibraryError("URI not in the medialibrary", uri)
        try:
            self._ordered_sources.remove(info)
        except ValueError:
            # this can only happen if discoverer hasn't finished scanning the
            # source, so info must be None
            assert info is None

        self.debug("Removing %s", uri)
        self.emit("source-removed", uri, info)

    def getInfoFromUri(self, uri):
        """
        Get the source corresponding to C{uri}.
        """
        # Make sure the URI is properly quoted, as other modules calling this
        # method do not necessarily provide URIs encoded in the same way.
        uri = quote_uri(uri)
        info = self._sources.get(uri)
        if info is None:
            raise MediaLibraryError("URI not in the medialibrary", uri)
        return info

    def addDiscovererInfo(self, discoverer, info, error):
        """
        Add the specified SourceFactory to the list of sources.
        """
        if error:
            self.emit("discovery-error", info.get_uri(), error.message)
        else:
            uri = info.get_uri()
            if self._sources.get(uri, None) is not None:
                raise MediaLibraryError("We already have info for this URI", uri)
            self._sources[uri] = info
            self._ordered_sources.append(info)
            self.nb_imported_files += 1
            self.emit("source-added", info)

    def getSources(self):
        """ Returns the list of sources used.

        The list will be ordered by the order in which they were added.

        @return: A list of SourceFactory objects which must not be changed.
        """
        return self._ordered_sources


class MediaLibraryWidget(gtk.VBox, Loggable):
    """ Widget for listing sources """

    __gsignals__ = {
        'play': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                (gobject.TYPE_PYOBJECT,))}

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self.settings = instance.settings
        self._errors = []
        self._project = None
        self.dummy_selected = []

        # Store
        # icon, infotext, objectfactory, uri, length
        self.storemodel = gtk.ListStore(gtk.gdk.Pixbuf, gtk.gdk.Pixbuf,
            str, object, str, str, str, str)

        # Scrolled Windows
        self.treeview_scrollwin = gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.iconview_scrollwin = gtk.ScrolledWindow()
        self.iconview_scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.iconview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        # Popup Menu
        self.popup = gtk.Menu()
        self.popup_remitem = gtk.ImageMenuItem(_("_Remove from Project"))
        self.popup_playmenuitem = gtk.MenuItem(_("_Preview Clip"))
        self.popup_clipprop = gtk.MenuItem(_("_Clip Properties..."))
        self.popup_insertEnd = gtk.MenuItem(_("Insert at _End of Timeline"))
        self.popup_remitem.connect("activate", self._removeClickedCb)
        self.popup_playmenuitem.connect("activate", self._previewClickedCb)
        self.popup_clipprop.connect("activate", self._clipPropertiesCb)
        self.popup_insertEnd.connect("activate", self._insertEndCb)
        self.popup.append(self.popup_insertEnd)
        self.popup.append(self.popup_remitem)
        self.popup.append(self.popup_playmenuitem)
        self.popup.append(self.popup_clipprop)
        self.popup.show_all()

        # import sources dialogbox
        self._importDialog = None

        # Search/filter box
        self.search_hbox = gtk.HBox()
        self.search_hbox.set_spacing(SPACING)
        self.search_hbox.set_border_width(3)  # Prevents being flush against the notebook
        searchLabel = gtk.Label(_("Search:"))
        searchEntry = gtk.Entry()
        searchEntry.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY, "gtk-clear")
        searchEntry.connect("changed", self._searchEntryChangedCb)
        searchEntry.connect("focus-in-event", self._disableKeyboardShortcutsCb)
        searchEntry.connect("focus-out-event", self._enableKeyboardShortcutsCb)
        searchEntry.connect("icon-press", self._searchEntryIconClickedCb)
        self.search_hbox.pack_start(searchLabel, expand=False)
        self.search_hbox.pack_end(searchEntry, expand=True)
        # Filtering model for the search box.
        # Use this instead of using self.storemodel directly
        self.modelFilter = self.storemodel.filter_new()
        self.modelFilter.set_visible_func(self._setRowVisible, data=searchEntry)

        # TreeView
        # Displays icon, name, type, length
        self.treeview = gtk.TreeView(self.modelFilter)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.connect("button-press-event", self._treeViewButtonPressEventCb)
        self.treeview.connect("focus-in-event", self._disableKeyboardShortcutsCb)
        self.treeview.connect("focus-out-event", self._enableKeyboardShortcutsCb)
        self.treeview.connect("row-activated", self._itemOrRowActivatedCb)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_headers_visible(False)
        self.treeview.set_property("search_column", COL_SEARCH_TEXT)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_MULTIPLE)
        tsel.connect("changed", self._viewSelectionChangedCb)

        pixbufcol = gtk.TreeViewColumn(_("Icon"))
        pixbufcol.set_expand(False)
        pixbufcol.set_spacing(SPACING)
        self.treeview.append_column(pixbufcol)
        pixcell = gtk.CellRendererPixbuf()
        pixcell.props.xpad = 6
        pixbufcol.pack_start(pixcell)
        pixbufcol.add_attribute(pixcell, 'pixbuf', COL_ICON)

        namecol = gtk.TreeViewColumn(_("Information"))
        self.treeview.append_column(namecol)
        namecol.set_expand(True)
        namecol.set_spacing(SPACING)
        namecol.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        namecol.set_min_width(150)
        txtcell = gtk.CellRendererText()
        txtcell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(txtcell)
        namecol.add_attribute(txtcell, "markup", COL_INFOTEXT)

        namecol = gtk.TreeViewColumn(_("Duration"))
        namecol.set_expand(False)
        self.treeview.append_column(namecol)
        txtcell = gtk.CellRendererText()
        txtcell.set_property("yalign", 0.0)
        namecol.pack_start(txtcell)
        namecol.add_attribute(txtcell, "markup", COL_LENGTH)

        # IconView
        self.iconview = gtk.IconView(self.modelFilter)
        self.iconview_scrollwin.add(self.iconview)
        self.iconview.connect("button-press-event", self._iconViewButtonPressEventCb)
        self.iconview.connect("focus-in-event", self._disableKeyboardShortcutsCb)
        self.iconview.connect("focus-out-event", self._enableKeyboardShortcutsCb)
        self.iconview.connect("item-activated", self._itemOrRowActivatedCb)
        self.iconview.connect("selection-changed", self._viewSelectionChangedCb)
        self.iconview.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.iconview.set_property("has_tooltip", True)
        self.iconview.set_tooltip_column(COL_INFOTEXT)
        self.iconview.set_text_column(COL_SHORT_TEXT)
        self.iconview.set_pixbuf_column(COL_ICON_LARGE)
        self.iconview.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self.iconview.set_item_width(138)  # Needs to be icon width +10

        # Explanatory message InfoBar
        self.infobar = gtk.InfoBar()

        txtlabel = gtk.Label()
        txtlabel.set_padding(PADDING, PADDING)
        txtlabel.set_line_wrap(True)
        txtlabel.set_line_wrap_mode(pango.WRAP_WORD)
        txtlabel.set_justify(gtk.JUSTIFY_CENTER)
        txtlabel.set_text(
            _('Add media to your project by dragging files and folders here or '
              'by using the "Import Files..." button.'))
        self.infobar.add(txtlabel)
        self.txtlabel = txtlabel

        # The infobar that shows up if there are _errors when importing clips
        self._import_warning_infobar = gtk.InfoBar()
        self._import_warning_infobar.set_message_type(gtk.MESSAGE_WARNING)
        content_area = self._import_warning_infobar.get_content_area()
        actions_area = self._import_warning_infobar.get_action_area()
        self._warning_label = gtk.Label()
        self._warning_label.set_line_wrap(True)
        self._warning_label.set_line_wrap_mode(pango.WRAP_WORD)
        self._warning_label.set_justify(gtk.JUSTIFY_CENTER)
        self._view_error_btn = gtk.Button()
        self._hide_infobar_btn = gtk.Button()
        self._hide_infobar_btn.set_label(_("Hide"))
        self._view_error_btn.connect("clicked", self._viewErrorsButtonClickedCb)
        self._hide_infobar_btn.connect("clicked", self._hideInfoBarClickedCb)
        content_area.add(self._warning_label)
        actions_area.add(self._view_error_btn)
        actions_area.add(self._hide_infobar_btn)

        # The _progressbar that shows up when importing clips
        self._progressbar = gtk.ProgressBar()

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
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.URI_TARGET_ENTRY, dnd.FILE_TARGET_ENTRY],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag_data_received", self._dndDataReceivedCb)

        self.treeview.drag_source_set(0, [], gtk.gdk.ACTION_COPY)
        self.treeview.connect("motion-notify-event",
            self._treeViewMotionNotifyEventCb)
        self.treeview.connect("button-release-event",
            self._treeViewButtonReleaseCb)
        self.treeview.connect("drag_begin", self._dndDragBeginCb)
        self.treeview.connect("drag_data_get", self._dndDataGetCb)

        self.iconview.drag_source_set(0, [], gtk.gdk.ACTION_COPY)
        self.iconview.connect("motion-notify-event",
            self._iconViewMotionNotifyEventCb)
        self.iconview.connect("button-release-event",
            self._iconViewButtonReleaseCb)
        self.iconview.connect("drag_begin", self._dndDragBeginCb)
        self.iconview.connect("drag_data_get", self._dndDataGetCb)

        # Hack so that the views have the same method as self
        self.treeview.getSelectedItems = self.getSelectedItems

        # always available
        actions = (
            ("ImportSources", gtk.STOCK_ADD, _("_Import Files..."),
            None, _("Add media files to your project"),
            self._importSourcesCb),

            ("ImportSourcesFolder", gtk.STOCK_ADD, _("Import _Folders..."),
            None, _("Add the contents of a folder as clips in your project"),
            self._importSourcesFolderCb),

            # Translators: "select" means "find" rather than "choose"
            ("SelectUnusedSources", None, _("Select Unused Media"),
            None, _("Select clips that have not been used in the project"),
            self._selectUnusedSourcesCb),
        )

        # only available when selection is non-empty
        selection_actions = (
            ("RemoveSources", gtk.STOCK_DELETE, _("_Remove from Project"),
            "<Control>Delete", None, self._removeSourcesCb),

            ("InsertEnd", gtk.STOCK_COPY, _("Insert at _End of Timeline"),
            "Insert", None, self._insertEndCb),

            ("PreviewClip", gtk.STOCK_MEDIA_PLAY, _("_Preview Clip"),
            None, None, self._previewClickedCb),

            ("ClipProps", None, _("_Clip Properties..."),
            None, None, self._clipPropertiesCb),
        )

        actiongroup = gtk.ActionGroup("medialibrarypermanent")
        actiongroup.add_actions(actions)
        actiongroup.get_action("ImportSources").props.is_important = True
        uiman.insert_action_group(actiongroup, 0)

        self.selection_actions = gtk.ActionGroup("medialibraryselection")
        self.selection_actions.add_actions(selection_actions)
        self.selection_actions.set_sensitive(False)
        uiman.insert_action_group(self.selection_actions, 0)
        uiman.add_ui_from_string(ui)

        # clip view menu items
        view_menu_item = uiman.get_widget('/MainMenuBar/View')
        view_menu = view_menu_item.get_submenu()
        seperator = gtk.SeparatorMenuItem()
        self.treeview_menuitem = gtk.RadioMenuItem(label=_("Show Clips as a List"))
        self.iconview_menuitem = gtk.RadioMenuItem.new_with_label(group=[self.treeview_menuitem],
                label=_("Show Clips as Icons"))

        # update menu items with current clip view before we connect to item
        # signals
        if self.settings.lastClipView == SHOW_TREEVIEW:
            self.treeview_menuitem.set_active(True)
            self.iconview_menuitem.set_active(False)
        else:
            self.treeview_menuitem.set_active(False)
            self.iconview_menuitem.set_active(True)

        # we only need to connect to one menu item because we get a signal
        # from each radio item in the group
        self.treeview_menuitem.connect("toggled", self._treeViewMenuItemToggledCb)

        view_menu.append(seperator)
        view_menu.append(self.treeview_menuitem)
        view_menu.append(self.iconview_menuitem)
        self.treeview_menuitem.show()
        self.iconview_menuitem.show()
        seperator.show()

        # add all child widgets
        self.pack_start(self.infobar, expand=False, fill=False)
        self.pack_start(self._import_warning_infobar, expand=False, fill=False)
        self.pack_start(self.search_hbox, expand=False)
        self.pack_start(self.iconview_scrollwin)
        self.pack_start(self.treeview_scrollwin)
        self.pack_start(self._progressbar, expand=False)

        # display the help text
        self.clip_view = self.settings.lastClipView
        self._displayClipView()

    def _importSourcesCb(self, unused_action):
        self.showImportSourcesDialog()

    def _importSourcesFolderCb(self, unused_action):
        self.showImportSourcesDialog(True)

    def _removeSourcesCb(self, unused_action):
        self._removeSources()

    def _selectUnusedSourcesCb(self, widget):
        self._selectUnusedSources()

    def _insertEndCb(self, unused_action):
        sources = []
        for uri in self.getSelectedItems():
            sources.append(ges.TimelineFileSource(uri))

        self.app.gui.timeline_ui.insertEnd(sources)

        self._sources_to_insert = self.getSelectedItems()

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

    def _searchEntryIconClickedCb(self, entry, unused, unsed1):
        entry.set_text("")

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
        icontheme = gtk.icon_theme_get_default()
        pixdir = get_pixmap_dir()
        icon = None
        try:
            icon = icontheme.load_icon(iconname, 48, 0)
        except:
            # empty except clause is bad but load_icon raises gio.Error.
            # Right, *gio*.
            if alternate:
                icon = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, alternate))
            else:
                icon = icontheme.load_icon("dialog-question", 48, 0)
        return icon

    def _connectToProject(self, project):
        """Connect signal handlers to a project.

        This first disconnects any handlers connected to an old project.
        If project is None, this just disconnects any connected handlers.
        """
        self.project_signals.connect(project.medialibrary,
            "source-added", None, self._sourceAddedCb)
        self.project_signals.connect(project.medialibrary,
            "source-removed", None, self._sourceRemovedCb)
        self.project_signals.connect(project.medialibrary,
            "discovery-error", None, self._discoveryErrorCb)
        self.project_signals.connect(project.medialibrary,
            "nothing-to-import", None, self._hideProgressBarCb)
        self.project_signals.connect(project.medialibrary,
            "ready", None, self._sourcesStoppedImportingCb)
        self.project_signals.connect(project.medialibrary,
            "starting", None, self._sourcesStartedImportingCb)

    def _setClipView(self, show):
        """ Set which clip view to use when medialibrary is showing clips. If
        none is given, the current one is used. Show: one of SHOW_TREEVIEW or
        SHOW_ICONVIEW """

        # save current selection
        paths = self.getSelectedPaths()

        # update saved clip view
        self.settings.lastClipView = show
        self.clip_view = show

        # transfer selection to next view
        self._viewUnselectAll()
        for path in paths:
            self._viewSelectPath(path)

        self._displayClipView()

    def _displayClipView(self):

        # first hide all the child widgets
        self.treeview_scrollwin.hide()
        self.iconview_scrollwin.hide()

        # pick the widget we're actually showing
        if self.clip_view == SHOW_TREEVIEW:
            self.debug("displaying tree view")
            widget = self.treeview_scrollwin
        elif self.clip_view == SHOW_ICONVIEW:
            self.debug("displaying icon view")
            widget = self.iconview_scrollwin

        if not len(self.storemodel):
            self._displayHelpText()

        # now un-hide the view
        widget.show_all()

    def _displayHelpText(self):
        """Display the InfoBar help message"""
        self.infobar.hide_all()
        self.txtlabel.show()
        self.infobar.show()

    def showImportSourcesDialog(self, select_folders=False):
        """Pop up the "Import Sources" dialog box"""
        if self._importDialog:
            return

        if select_folders:
            chooser_action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
            dialogtitle = _("Select One or More Folders")
        else:
            chooser_action = gtk.FILE_CHOOSER_ACTION_OPEN
            dialogtitle = _("Select One or More Files")

        close_after = gtk.CheckButton(_("Close after importing files"))
        close_after.set_active(self.app.settings.closeImportDialog)

        self._importDialog = gtk.FileChooserDialog(dialogtitle, None,
                                           chooser_action,
                                           (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE,
                                            gtk.STOCK_ADD, gtk.RESPONSE_OK))
        self._importDialog.set_icon_name("pitivi")
        self._importDialog.props.extra_widget = close_after
        self._importDialog.set_default_response(gtk.RESPONSE_OK)
        self._importDialog.set_select_multiple(True)
        self._importDialog.set_modal(False)
        self._importDialog.set_current_folder(self.app.settings.lastImportFolder)
        self._importDialog.connect('response', self._dialogBoxResponseCb, select_folders)
        self._importDialog.connect('close', self._dialogBoxCloseCb)
        if not select_folders:
            # Only show the preview widget when not in folder import mode
            pw = PreviewWidget(self.app)
            self._importDialog.set_preview_widget(pw)
            self._importDialog.set_use_preview_label(False)
            self._importDialog.connect('update-preview', pw.add_preview_request)
        self._importDialog.show()

    def _addFolders(self, folders):
        """ walks the trees of the folders in the list and adds the files it finds """
        self.app.threads.addThread(PathWalker, folders, self.app.current.medialibrary.addUris)

    def _updateProgressbar(self):
        """
        Update the _progressbar with the ratio of clips imported vs the total
        """
        current_clip_iter = self.app.current.medialibrary.nb_imported_files
        total_clips = self.app.current.medialibrary.nb_files_to_import
        progressbar_text = _("Importing clip %(current_clip)d of %(total)d" %
            {"current_clip": current_clip_iter,
            "total": total_clips})
        self._progressbar.set_text(progressbar_text)
        if current_clip_iter == 0:
            self._progressbar.set_fraction(0.0)
        elif total_clips != 0:
            self._progressbar.set_fraction((current_clip_iter - 1) / float(total_clips))

    def _addDiscovererInfo(self, info):
        # The code below tries to read existing thumbnails from the freedesktop
        # thumbnails directory (~/.thumbnails). The filenames are simply
        # the file URI hashed with md5, so we can retrieve them easily.
        if [i for i in info.get_stream_list() if\
            isinstance(i, DiscovererVideoInfo)]:
            thumbnail_hash = md5(info.get_uri()).hexdigest()
            thumb_dir = os.path.expanduser("~/.thumbnails/")
            thumb_path_normal = thumb_dir + "normal/" + thumbnail_hash + ".png"
            thumb_path_large = thumb_dir + "large/" + thumbnail_hash + ".png"
            # Pitivi used to consider 64 pixels as normal and 96 as large
            # However, the fdo spec specifies 128 as normal and 256 as large.
            # We will thus simply use the "normal" size and scale it down.
            try:
                thumbnail = gtk.gdk.pixbuf_new_from_file(thumb_path_normal)
                thumbnail_large = thumbnail
                thumbnail_height = int(thumbnail.get_height() / 2)
                thumbnail = thumbnail.scale_simple(64, thumbnail_height, \
                    gtk.gdk.INTERP_BILINEAR)
            except:
                # TODO gst discoverer should create missing thumbnails.
                thumbnail = self.videofilepixbuf
                thumbnail_large = thumbnail
        else:
            thumbnail = self.audiofilepixbuf
            thumbnail_large = self.audiofilepixbuf

        if info.get_duration() == gst.CLOCK_TIME_NONE:
            duration = ''
        else:
            duration = beautify_length(info.get_duration())

        short_text = None
        uni = unicode(info_name(info), 'utf-8')

        if len(uni) > 34:
            short_uni = uni[0:29]
            short_uni += unicode('...')
            short_text = short_uni.encode('utf-8')
        else:
            short_text = info_name(info)

        self.storemodel.append([thumbnail,
            thumbnail_large,
            beautify_info(info),
            info,
            info.get_uri(),
            duration,
            info_name(info),
            short_text])

    # medialibrary callbacks

    def _sourceAddedCb(self, unused_medialibrary, factory):
        """ a file was added to the medialibrary """
        self._updateProgressbar()
        self._addDiscovererInfo(factory)
        if len(self.storemodel):
            self.infobar.hide_all()
            self.search_hbox.show_all()

    def _sourceRemovedCb(self, unused_medialibrary, uri, unused_info):
        """ the given uri was removed from the medialibrary """
        # find the good line in the storemodel and remove it
        model = self.storemodel
        for row in model:
            if uri == row[COL_URI]:
                model.remove(row.iter)
                break
        if not len(model):
            self._displayHelpText()
            self.search_hbox.hide()
        self.debug("Removing %s", uri)

    def _discoveryErrorCb(self, unused_medialibrary, uri, reason, extra=None):
        """ The given uri isn't a media file """
        error = (uri, reason, extra)
        self._errors.append(error)

    def _sourcesStartedImportingCb(self, unused_medialibrary):
        self._progressbar.show()

    def _sourcesStoppedImportingCb(self, unused_medialibrary):
        self._progressbar.hide()
        if self._errors:
            if len(self._errors) > 1:
                self._warning_label.set_text(_("Errors occurred while importing."))
                self._view_error_btn.set_label(_("View errors"))
            else:
                self._warning_label.set_text(_("An error occurred while importing."))
                self._view_error_btn.set_label(_("View error"))

            self._import_warning_infobar.show_all()

    def _hideProgressBarCb(self, unused_medialibrary):
        """
        This is only called when all the uris we tried to import were already
        present in the media library. We then need to hide the progressbar
        because the media library is not going to emit the "ready" signal.
        """
        self._progressbar.hide()

    ## Error Dialog Box callbacks

    def _errorDialogBoxCloseCb(self, unused_dialog):
        self._error_dialogbox.destroy()
        self._error_dialogbox = None

    def _errorDialogBoxResponseCb(self, unused_dialog, unused_response):
        self._error_dialogbox.destroy()
        self._error_dialogbox = None

    ## Import Sources Dialog Box callbacks

    def _dialogBoxResponseCb(self, dialogbox, response, select_folders):
        self.debug("response:%r", response)
        if response == gtk.RESPONSE_OK:
            lastfolder = dialogbox.get_current_folder()
            self.app.settings.lastImportFolder = lastfolder
            self.app.settings.closeImportDialog = \
                dialogbox.props.extra_widget.get_active()
            filenames = dialogbox.get_uris()
            if select_folders:
                self._addFolders(filenames)
            else:
                self.app.current.medialibrary.addUris(filenames)
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
        if paths == None or paths < 1:
            return
        # use row references so we don't have to care if a path has been removed
        rows = []
        for path in paths:
            row = gtk.TreeRowReference(model, path)
            rows.append(row)

        self.app.action_log.begin("remove clip from source list")
        for row in rows:
            uri = model[row.get_path()][COL_URI]
            self.app.current.medialibrary.removeUri(uri)
        self.app.action_log.commit()

    def _sourceIsUsed(self, uri):
        """Check if a given URI is present in the timeline"""
        layers = self.app.current.timeline.get_layers()
        for layer in layers:
            for tlobj in layer.get_objects():
                tlobj_uri = quote_uri(tlobj.get_uri())
                if tlobj_uri == uri:
                    return True
        return False

    def _selectUnusedSources(self):
        """
        Select, in the media library, unused sources in the project.
        """
        sources = self.app.current.medialibrary.getSources()
        unused_sources_uris = []

        model = self.treeview.get_model()
        selection = self.treeview.get_selection()
        for source in sources:
            if not self._sourceIsUsed(source.get_uri()):
                unused_sources_uris.append(source.get_uri())

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

    def _previewClickedCb(self, unused_widget=None):
        """ Called when a user clicks on the Preview Clip button """
        paths = self.getSelectedPaths()[0]  # Only use the first item
        model = self.treeview.get_model()
        self.debug("Let's play %s", model[paths][COL_URI])
        self.emit('play', model[paths][COL_URI])

    def _clipPropertiesCb(self, unused_widget=None):
        """
        Show the clip properties (resolution, framerate, audio channels...)
        and allow setting them as the new project settings.
        """
        paths = self.getSelectedPaths()[0]  # Only use the first item
        model = self.treeview.get_model()
        factory = model[paths][COL_FACTORY]
        d = clipmediapropsDialog(self.app.current,
                                factory.get_audio_streams(),
                                factory.get_video_streams())
        d.run()

    def _hideInfoBarClickedCb(self, unused_button):
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

    def _treeViewMenuItemToggledCb(self, unused_widget):
        if self.treeview_menuitem.get_active():
            show = SHOW_TREEVIEW
        else:
            show = SHOW_ICONVIEW
        self._setClipView(show)

    _dragStarted = False
    _dragSelection = False
    _dragButton = None
    _dragX = 0
    _dragY = 0
    _ignoreRelease = False

    def _rowUnderMouseSelected(self, view, event):
        if isinstance(view, gtk.TreeView):
            path, column, x, y = view.get_path_at_pos(int(event.x), int(event.y))
            if path:
                selection = view.get_selection()
                return selection.path_is_selected(path) and selection.count_selected_rows() > 0
        elif isinstance(view, gtk.IconView):
            path = view.get_path_at_pos(int(event.x), int(event.y))
            if path:
                selection = view.get_selected_items()
                return view.path_is_selected(path) and len(selection)
        else:
                assert False

        return False

    def _nothingUnderMouse(self, view, event):
        return not bool(view.get_path_at_pos(int(event.x), int(event.y)))

    def _viewShowPopup(self, view, event):
        """
        Handle the sensitivity of popup menu items when right-clicking.
        """
        # Default values
        self.popup_remitem.set_sensitive(False)
        self.popup_playmenuitem.set_sensitive(False)
        self.popup_clipprop.set_sensitive(False)
        self.popup_insertEnd.set_sensitive(False)

        multiple_selected = len(self.getSelectedPaths()) > 1
        if view != None and self._rowUnderMouseSelected(view, event):
            # An item was already selected, then the user right-clicked on it
            self.popup_insertEnd.set_sensitive(True)
            self.popup_remitem.set_sensitive(True)
            if not multiple_selected:
                self.popup_playmenuitem.set_sensitive(True)
                self.popup_clipprop.set_sensitive(True)
        elif view != None and (not self._nothingUnderMouse(view, event)):
            if not event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK):
                # An item was previously selected, and the user
                # right-clicked on a different item (selecting it).
                self._viewUnselectAll()
                multiple_selected = False
            elif self.clip_view == SHOW_TREEVIEW and self._viewHasSelection() \
                    and (event.state & gtk.gdk.SHIFT_MASK):
                # FIXME: when does this section ever get called?
                selection = self.treeview.get_selection()
                start_path = self._viewGetFirstSelected()
                end_path = self._viewGetPathAtPos(event)
                self._viewUnselectAll()
                selection.select_range(start_path, end_path)

            self._viewSelectPath(self._viewGetPathAtPos(event))
            self.popup_insertEnd.set_sensitive(True)
            self.popup_remitem.set_sensitive(True)
            if not multiple_selected:
                self.popup_playmenuitem.set_sensitive(True)
                self.popup_clipprop.set_sensitive(True)

        # If none of the conditions above match,
        # An item may or may not have been selected,
        # but the user right-clicked outside it.
        # In that case, the sensitivity values will stay to the default.
        self.popup.popup(None, None, None, event.button, event.time)

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

        if event.type == gtk.gdk._2BUTTON_PRESS:
            if self.getSelectedPaths() != []:
                # It is possible to double-click outside of clips!
                self._previewClickedCb()
            chain_up = False
        elif event.button == 3:
            self._viewShowPopup(treeview, event)
            chain_up = False

        else:

            if not event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK):
                chain_up = not self._rowUnderMouseSelected(treeview, event)

            self._dragStarted = False
            self._dragSelection = False
            self._dragButton = event.button
            self._dragX = int(event.x)
            self._dragY = int(event.y)

        if chain_up:
            gtk.TreeView.do_button_press_event(treeview, event)
        else:
            treeview.grab_focus()

        self._ignoreRelease = chain_up

        return True

    def _treeViewMotionNotifyEventCb(self, treeview, event):
        if not self._dragButton:
            return True

        if self._nothingUnderMouse(treeview, event):
            return True

        if treeview.drag_check_threshold(self._dragX, self._dragY,
            int(event.x), int(event.y)):
            context = treeview.drag_begin(
                [dnd.URI_TARGET_ENTRY, dnd.FILESOURCE_TARGET_ENTRY],
                gtk.gdk.ACTION_COPY,
                self._dragButton,
                event)
            self._dragStarted = True
        return False

    def _treeViewButtonReleaseCb(self, treeview, event):
        if event.button == self._dragButton:
            self._dragButton = None
            if (not self._ignoreRelease) and (not self._dragStarted):
                treeview.get_selection().unselect_all()
                result = treeview.get_path_at_pos(int(event.x), int(event.y))
                if result:
                    path = result[0]
                    treeview.get_selection().select_path(path)
        return False

    def _viewSelectionChangedCb(self, unused):
        if self._viewHasSelection():
            self.selection_actions.set_sensitive(True)
        else:
            self.selection_actions.set_sensitive(False)

    def _itemOrRowActivatedCb(self, unused_view, path, *unused_column):
        """
        When Space, Shift+Space, Return or Enter is pressed, preview the clip.
        This method is the same for both iconview and treeview.
        """
        path = self.modelFilter[path][COL_URI]
        self.emit('play', path)

    def _iconViewMotionNotifyEventCb(self, iconview, event):
        if not self._dragButton:
            return True

        if self._dragSelection:
            return False

        if self._nothingUnderMouse(iconview, event):
            return True

        if iconview.drag_check_threshold(self._dragX, self._dragY,
            int(event.x), int(event.y)):
            context = iconview.drag_begin(
                [dnd.URI_TARGET_ENTRY, dnd.FILESOURCE_TARGET_ENTRY],
                gtk.gdk.ACTION_COPY,
                self._dragButton,
                event)
            self._dragStarted = True
        return False

    def _iconViewButtonPressEventCb(self, iconview, event):
        chain_up = True

        if event.type == gtk.gdk._2BUTTON_PRESS:
            if self.getSelectedPaths() != []:
                # It is possible to double-click outside of clips!
                self._previewClickedCb()
            chain_up = False
        elif event.button == 3:
            self._viewShowPopup(iconview, event)
            chain_up = False
        else:
            if not event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK):
                chain_up = not self._rowUnderMouseSelected(iconview, event)

            self._dragStarted = False
            self._dragSelection = self._nothingUnderMouse(iconview, event)
            self._dragButton = event.button
            self._dragX = int(event.x)
            self._dragY = int(event.y)

        if chain_up:
            gtk.IconView.do_button_press_event(iconview, event)
        else:
            iconview.grab_focus()

        self._ignoreRelease = chain_up

        return True

    def _iconViewButtonReleaseCb(self, iconview, event):
        if event.button == self._dragButton:
            self._dragButton = None
            self._dragSelection = False
            if (not self._ignoreRelease) and (not self._dragStarted):
                iconview.unselect_all()
                path = iconview.get_path_at_pos(int(event.x), int(event.y))
                if path:
                    iconview.select_path(path)
        return False

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

    def _newProjectFailedCb(self, unused_pitivi, unused_reason, unused_uri):
        self.storemodel.clear()
        self.project_signals.disconnectAll()
        self._project = None

    ## Drag and Drop
    def _dndDataReceivedCb(self, unused_widget, unused_context, unused_x,
                           unused_y, selection, targettype, unused_time):
        def get_file_type(path):
            if path[:7] == "file://":
                if os.path.isfile(path[7:]):
                    return LOCAL_FILE
                return LOCAL_DIR
            elif "://" in path:  # we concider it is a remote file
                return REMOTE_FILE
            return NOT_A_FILE

        self.debug("targettype:%d, selection.data:%r", targettype, selection.data)
        directories = []
        if targettype == dnd.TYPE_URI_LIST:
            filenames = []
            directories = []
            remote_files = []
            incoming = [unquote(x.strip('\x00')) for x in selection.data.strip().split("\r\n")
                        if x.strip('\x00')]
            for x in incoming:
                filetype = get_file_type(x)
                if filetype == LOCAL_FILE:
                    filenames.append(x)
                elif filetype == LOCAL_DIR:
                    directories.append(x)
                elif filetype == REMOTE_FILE:
                    remote_files.append(x)
        elif targettype == dnd.TYPE_TEXT_PLAIN:
            incoming = selection.data.strip()
            file_type = get_file_type(incoming)
            if file_type == LOCAL_FILE:
                filenames = [incoming]
            elif file_type == LOCAL_DIR:
                directories = [incoming]
        if directories:
            self._addFolders(directories)

        if remote_files:
            #TODO waiting for remote files downloader support to be implemented
            pass

        self.app.current.medialibrary.addUris(filenames)

    #used with TreeView and IconView
    def _dndDragBeginCb(self, view, context):
        self.info("tree drag_begin")
        paths = self.getSelectedPaths()

        if len(paths) < 1:
            context.drag_abort(int(time.time()))
        else:
            row = self.modelFilter[paths[0]]
            context.set_icon_pixbuf(row[COL_ICON], 0, 0)

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
        return [self.modelFilter[path][COL_URI]
            for path in self.getSelectedPaths()]

    def _dndDataGetCb(self, unused_widget, context, selection,
                      targettype, unused_eventtime):
        self.info("data get, type:%d", targettype)
        uris = self.getSelectedItems()
        if len(uris) < 1:
            return
        selection.set(selection.target, 8, '\n'.join(uris))
        context.set_icon_pixbuf(INVISIBLE, 0, 0)

gobject.type_register(MediaLibraryWidget)
