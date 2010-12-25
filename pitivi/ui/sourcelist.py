# PiTiVi , Non-linear video editor
#
#       ui/sourcelist.py
#
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gobject
import gst
import gtk
import pango
import os
import time

from urllib import unquote
from gettext import gettext as _
from gettext import ngettext

import pitivi.ui.dnd as dnd
from pitivi.ui.pathwalker import PathWalker, quote_uri
from pitivi.ui.filelisterrordialog import FileListErrorDialog
from pitivi.configure import get_pixmap_dir
from pitivi.signalgroup import SignalGroup
from pitivi.stream import VideoStream, AudioStream, TextStream, \
        MultimediaStream
from pitivi.settings import GlobalSettings
from pitivi.utils import beautify_length
from pitivi.ui.common import beautify_factory, factory_name, \
    beautify_stream, SPACING, PADDING
from pitivi.log.loggable import Loggable
from pitivi.sourcelist import SourceListError

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
            <placeholder name="SourceList" >
                <menuitem action="ImportSources" />
                <menuitem action="ImportSourcesFolder" />
                <menuitem action="RemoveSources" />
                <separator />
                <menuitem action="InsertEnd" />
            </placeholder>
        </menu>
    </menubar>
    <toolbar name="MainToolBar">
        <placeholder name="SourceList">
            <toolitem action="ImportSources" />
        </placeholder>
    </toolbar>
</ui>
'''

INVISIBLE = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir(), 
    "invisible.png"))

class SourceList(gtk.VBox, Loggable):
    """ Widget for listing sources """

    __gsignals__ = {
        'play': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                (gobject.TYPE_PYOBJECT,))
        }

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self.settings = instance.settings

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
        self.popup_importitem = gtk.ImageMenuItem(_("Import clips..."))
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        self.popup_importitem.set_image(image)

        self.popup_remitem = gtk.ImageMenuItem(_("Remove Clip"))
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        self.popup_remitem.set_image(image)
        self.popup_playmenuitem = gtk.MenuItem(_("Play Clip"))
        self.popup_importitem.connect("activate", self._importButtonClickedCb)
        self.popup_remitem.connect("activate", self._removeButtonClickedCb)
        self.popup_playmenuitem.connect("activate", self._playButtonClickedCb)
        self.popup_importitem.show()
        self.popup_remitem.show()
        self.popup_playmenuitem.show()
        self.popup.append(self.popup_importitem)
        self.popup.append(self.popup_remitem)
        self.popup.append(self.popup_playmenuitem)

        # import sources dialogbox
        self._importDialog = None

        # Search/filter box
        self.search_hbox = gtk.HBox()
        self.search_hbox.set_spacing(SPACING)
        self.search_hbox.set_border_width(3)  # Prevents being flush against the notebook
        searchLabel = gtk.Label(_("Search:"))
        searchEntry = gtk.Entry()
        searchEntry.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY, "gtk-clear")
        self.search_hbox.pack_start(searchLabel, expand=False)
        self.search_hbox.pack_end(searchEntry, expand=True)

        # TreeView
        # Displays icon, name, type, length
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.connect("button-press-event", self._treeViewButtonPressEventCb)
        self.treeview.connect("row-activated", self._rowActivatedCb)
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
        self.iconview = gtk.IconView(self.storemodel)
        self.iconview_scrollwin.add(self.iconview)
        self.iconview.connect("button-press-event", self._iconViewButtonPressEventCb)
        self.iconview.connect("selection-changed", self._viewSelectionChangedCb)
        self.iconview.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.iconview.set_text_column(COL_SHORT_TEXT)
        self.iconview.set_pixbuf_column(COL_ICON_LARGE)
        self.iconview.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self.iconview.set_item_width(106)

        # Explanatory message InfoBar
        self.infobar = gtk.InfoBar()

        txtlabel = gtk.Label()
        txtlabel.set_padding(PADDING, PADDING)
        txtlabel.set_line_wrap(True)
        txtlabel.set_line_wrap_mode(pango.WRAP_WORD)
        txtlabel.set_justify(gtk.JUSTIFY_CENTER)
        txtlabel.set_markup(
            _("<span>Import your clips by dragging them here or "
              "by using the buttons above.</span>"))
        self.infobar.add(txtlabel)
        self.txtlabel = txtlabel

        self.infostub = InfoStub()
        self.infostub.connect("remove-me", self._removeInfoStub)

        # Connect to project.  We must remove and reset the callbacks when
        # changing project.
        self.project_signals = SignalGroup()
        self.app.connect("new-project-created",
            self._newProjectCreatedCb)
        self.app.connect("new-project-loaded",
            self._newProjectLoadedCb)
        self.app.connect("new-project-failed",
            self._newProjectFailedCb)

        # default pixbufs
        self.audiofilepixbuf = self._getIcon("audio-x-generic", "pitivi-sound.png")
        self.videofilepixbuf = self._getIcon("video-x-generic", "pitivi-video.png")

        # Drag and Drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.URI_TUPLE, dnd.FILE_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag_data_received", self._dndDataReceivedCb)

        self.treeview.drag_source_set(0,[], gtk.gdk.ACTION_COPY)
        self.treeview.connect("motion-notify-event",
            self._treeViewMotionNotifyEventCb)
        self.treeview.connect("button-release-event",
            self._treeViewButtonReleaseCb)
        self.treeview.connect("drag_begin", self._dndDragBeginCb)
        self.treeview.connect("drag_data_get", self._dndDataGetCb)

        self.iconview.drag_source_set(0,[], gtk.gdk.ACTION_COPY)
        self.iconview.connect("motion-notify-event",
            self._iconViewMotionNotifyEventCb)
        self.iconview.connect("button-release-event",
            self._iconViewButtonReleaseCb)
        self.iconview.connect("drag_begin", self._dndDragBeginCb)
        self.iconview.connect("drag_data_get", self._dndDataGetCb)

        # Hack so that the views have the same method as self
        self.treeview.getSelectedItems = self.getSelectedItems

        # Error dialog box
        self.errorDialogBox = None

        # always available
        actions = (
            ("ImportSources", gtk.STOCK_ADD, _("_Import clips..."),
                None, _("Import clips to use"), self._importSourcesCb),
            ("ImportSourcesFolder", gtk.STOCK_ADD,
                _("Import _folder of clips..."), None,
                _("Import folder of clips to use"), self._importSourcesFolderCb),
        )

        # only available when selection is non-empty 
        selection_actions = (
            ("RemoveSources", gtk.STOCK_DELETE,
                _("_Remove from project"), "<Control>Delete", None,
                self._removeSourcesCb),
            ("InsertEnd", gtk.STOCK_COPY,
                _("Insert at _end of timeline"), "Insert", None,
                self._insertEndCb),
        )

        actiongroup = gtk.ActionGroup("sourcelistpermanent")
        actiongroup.add_actions(actions)
        actiongroup.get_action("ImportSources").props.is_important = True
        uiman.insert_action_group(actiongroup, 0)

        self.selection_actions = gtk.ActionGroup("sourcelistselection")
        self.selection_actions.add_actions(selection_actions)
        self.selection_actions.set_sensitive(False)
        uiman.insert_action_group(self.selection_actions, 0)
        uiman.add_ui_from_string(ui)

        # clip view menu items
        view_menu_item = uiman.get_widget('/MainMenuBar/View')
        view_menu = view_menu_item.get_submenu()
        seperator = gtk.SeparatorMenuItem()
        self.treeview_menuitem = gtk.RadioMenuItem(None,
                _("Show Clips as a List"))
        self.iconview_menuitem = gtk.RadioMenuItem(self.treeview_menuitem,
                _("Show Clips as Icons"))

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
        self.pack_start(self.search_hbox, expand=False)
        self.pack_start(self.iconview_scrollwin)
        self.pack_start(self.treeview_scrollwin)

        # display the help text
        self.clip_view = self.settings.lastClipView
        self._displayClipView()

    def _importSourcesCb(self, unused_action):
        self.showImportSourcesDialog()

    def _importSourcesFolderCb(self, unused_action):
        self.showImportSourcesDialog(True)

    def _removeSourcesCb(self, unused_action):
        self._removeSources()

    def _insertEndCb(self, unused_action):
        self.app.action_log.begin("add clip")
        timeline = self.app.current.timeline
        sources = self.app.current.sources
        start = timeline.duration
        self.app.current.seeker.seek(start)
        for uri in self.getSelectedItems():
            factory = sources.getUri(uri)
            source = timeline.addSourceFactory(factory)
            source.setStart(start)
            start += source.duration
        self.app.action_log.commit()

    def _getIcon(self, iconname, alternate):
        icontheme = gtk.icon_theme_get_default()
        pixdir = get_pixmap_dir()
        icon = None
        try:
            icon = icontheme.load_icon(iconname, 32, 0)
        except:
            # empty except clause is bad but load_icon raises gio.Error.
            # Right, *gio*.
            if not icon:
                icon = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, alternate))
        return icon

    def _connectToProject(self, project):
        """Connect signal handlers to a project.

        This first disconnects any handlers connected to an old project.
        If project is None, this just disconnects any connected handlers.

        """
        self.project_signals.connect(
            project.sources, "source-added", None, self._sourceAddedCb)
        self.project_signals.connect(
            project.sources, "source-removed", None, self._sourceRemovedCb)
        self.project_signals.connect(
            project.sources, "discovery-error", None, self._discoveryErrorCb)
        self.project_signals.connect(
            project.sources, "missing-plugins", None, self._missingPluginsCb)
        self.project_signals.connect(
            project.sources, "ready", None, self._sourcesStoppedImportingCb)
        self.project_signals.connect(
            project.sources, "starting", None, self._sourcesStartedImportingCb)


    ## Explanatory message methods
    
    def _setClipView(self, show):
        """ Set which clip view to use when sourcelist is showing clips. If
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
            dialogtitle = _("Import a folder")
        else:
            chooser_action = gtk.FILE_CHOOSER_ACTION_OPEN
            dialogtitle = _("Import a clip")
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
        self._importDialog.show()

    def addUris(self, files):
        """ Add files to the list """
        try:
            self.app.current.sources.addUris(files)
        except SourceListError as error:
            disclaimer, uri = error.args
            self.error("'%s' is already present in the source list." + uri)

    def addFolders(self, folders):
        """ walks the trees of the folders in the list and adds the files it finds """
        self.app.threads.addThread(PathWalker, folders, self.app.current.sources.addUris)

    def _addFactory(self, factory):
        video = factory.getOutputStreams(VideoStream)
        if video and video[0].thumbnail:
            thumbnail_file = video[0].thumbnail
            try:
                self.debug("attempting to open thumbnail file '%s'",
                        thumbnail_file)
                pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnail_file)
            except:
                self.error("Failure to create thumbnail from file '%s'",
                        thumbnail_file)
                thumbnail = self.videofilepixbuf
                thumbnail_large = self.videofilepixbuf
            else:
                desiredheight = int(64 / float(video[0].dar))
                thumbnail = pixbuf.scale_simple(64,
                        desiredheight, gtk.gdk.INTERP_BILINEAR)
                desiredheight = int(96 / float(video[0].dar))
                thumbnail_large = pixbuf.scale_simple(96,
                        desiredheight, gtk.gdk.INTERP_BILINEAR)
        else:
            if video:
                thumbnail = self.videofilepixbuf
                thumbnail_large = self.videofilepixbuf
            else:
                thumbnail = self.audiofilepixbuf
                thumbnail_large = self.audiofilepixbuf

        if not factory.duration or factory.duration == gst.CLOCK_TIME_NONE:
            duration = ''
        else:
            duration = beautify_length(factory.duration)

        short_text = None
        uni = unicode(factory_name(factory), 'utf-8')

        if len(uni) > 34:
            short_uni = uni[0:29]
            short_uni += unicode('...')
            short_text = short_uni.encode('utf-8')
        else:
            short_text = factory_name(factory)

        self.storemodel.append([thumbnail,
            thumbnail_large,
            beautify_factory(factory),
            factory,
            factory.uri,
            duration,
            factory_name(factory),
            short_text])
        self._displayClipView()

    # sourcelist callbacks

    def _sourceAddedCb(self, unused_sourcelist, factory):
        """ a file was added to the sourcelist """
        self._addFactory(factory)
        if len(self.storemodel):
            self.infobar.hide_all()
            self.search_hbox.show_all()

    def _sourceRemovedCb(self, sourcelist, uri, factory):
        """ the given uri was removed from the sourcelist """
        # find the good line in the storemodel and remove it
        model = self.storemodel
        for row in model:
            if uri == row[COL_URI]:
                model.remove(row.iter)
                break
        if not len(model):
            self._displayHelpText()
            self.search_hbox.hide()

    def _discoveryErrorCb(self, unused_sourcelist, uri, reason, extra):
        """ The given uri isn't a media file """
        self.infostub.addErrors(uri, reason, extra)

    def _missingPluginsCb(self, sourcelist, uri, factory, details, descriptions, cb):
        self.infostub.addErrors(uri, "Missing plugins", "\n".join(descriptions))

    def _sourcesStartedImportingCb(self, unused_sourcelist):
        if not self.infostub.showing:
            self.pack_start(self.infostub, expand=False)
        self.infostub.startingImport()

    def _sourcesStoppedImportingCb(self, unused_sourcelist):
        self.infostub.stoppingImport()

    def _removeInfoStub(self, unused_i):
        self.remove(self.infostub)

    ## Error Dialog Box callbacks

    def _errorDialogBoxCloseCb(self, unused_dialog):
        self.errorDialogBox.destroy()
        self.errorDialogBox = None

    def _errorDialogBoxResponseCb(self, unused_dialog, unused_response):
        self.errorDialogBox.destroy()
        self.errorDialogBox = None

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
                self.addFolders(filenames)
            else:
                self.addUris(filenames)
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
        model = self.storemodel
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
            self.app.current.sources.removeUri(uri)
        self.app.action_log.commit()

    ## UI Button callbacks

    def _importButtonClickedCb(self, unused_widget=None):
        """ Called when a user clicks on the import button """
        self.showImportSourcesDialog()

    def _removeButtonClickedCb(self, unused_widget=None):
        """ Called when a user clicks on the remove button """
        self._removeSources()

    def _playButtonClickedCb(self, unused_widget=None):
        """ Called when a user clicks on the play button """
        # get the selected filesourcefactory
        paths = self.getSelectedPaths()
        model = self.storemodel
        if len(paths) < 1:
            return
        path = paths[0]
        factory = model[path][COL_FACTORY]
        self.debug("Let's play %s", factory.uri)
        self.emit('play', factory)

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
        result = view.get_path_at_pos(int(event.x), int(event.y))
        if result:
            path = result[0]
            if isinstance(view, gtk.TreeView):
                selection = view.get_selection()

                return selection.path_is_selected(path) and selection.count_selected_rows() > 0
            elif isinstance(view, gtk.IconView):
                selection = view.get_selected_items()

                return view.path_is_selected(path) and len(selection)
            else:
                assert False

        return False

    def _nothingUnderMouse(self, view, event):
        return not bool(view.get_path_at_pos(int(event.x), int(event.y)))

    def _viewShowPopup(self, view, event):
        if view != None and self._rowUnderMouseSelected(view, event):
            self.popup_remitem.set_sensitive(True)
            self.popup_playmenuitem.set_sensitive(True)
        elif view != None and (not self._nothingUnderMouse(view, event)):
            if not event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK):
                self._viewUnselectAll()
            elif self.clip_view == SHOW_TREEVIEW and self._viewHasSelection() \
                    and (event.state & gtk.gdk.SHIFT_MASK):
                selection = self.treeview.get_selection()
                start_path = self._viewGetFirstSelected()
                end_path = self._viewGetPathAtPos(event)
                self._viewUnselectAll()
                selection.select_range(start_path, end_path)

            self._viewSelectPath(self._viewGetPathAtPos(event))
            self.popup_remitem.set_sensitive(True)
            self.popup_playmenuitem.set_sensitive(True)
        else:
            self.popup_remitem.set_sensitive(False)
            self.popup_playmenuitem.set_sensitive(False)

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
            self._playButtonClickedCb()
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
                [dnd.URI_TUPLE, dnd.FILESOURCE_TUPLE],
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

    def _rowActivatedCb(self, unused_treeview, path, unused_column):
        factory = self.storemodel[path][COL_FACTORY]
        self.emit('play', factory)

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
                [dnd.URI_TUPLE, dnd.FILESOURCE_TUPLE],
                gtk.gdk.ACTION_COPY,
                self._dragButton,
                event)
            self._dragStarted = True
        return False

    def _iconViewButtonPressEventCb(self, iconview, event):
        chain_up = True

        if event.type == gtk.gdk._2BUTTON_PRESS:
            self._playButtonClickedCb()
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
        # clear the storemodel
        self.storemodel.clear()
        self._connectToProject(project)

    def _newProjectLoadingCb(self, unused_pitivi, uri):
        if not self.infostub.showing:
            self.pack_start(self.infostub, expand=False)
            self.infostub.startingImport()

    def _newProjectLoadedCb(self, unused_pitivi, project):
        pass

    def _newProjectFailedCb(self, unused_pitivi, unused_reason,
        unused_uri):
        self.storemodel.clear()
        self.project_signals.disconnectAll()


    ## Drag and Drop

    def _dndDataReceivedCb(self, unused_widget, unused_context, unused_x,
                           unused_y, selection, targettype, unused_time):
        def get_file_type(path):
            if path[:7] == "file://":
                if os.path.isfile(path[7:]):
                    return LOCAL_FILE
                return LOCAL_DIR
            elif "://" in path: #we concider it is a remote file
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
            self.addFolders(directories)

        if remote_files:
            #TODO waiting for remote files downloader support to be implemented
            pass

        try:
            self.addUris([quote_uri(uri) for uri in filenames])
        except SourceListError:
            # filenames already present in the sourcelist
            pass

    #used with TreeView and IconView
    def _dndDragBeginCb(self, view, context):
        self.info("tree drag_begin")
        paths = self.getSelectedPaths()

        if len(paths) < 1:
            context.drag_abort(int(time.time()))
        else:
            row = self.storemodel[paths[0]]
            context.set_icon_pixbuf(row[COL_ICON], 0, 0)

    def getSelectedPaths(self):
        """ returns a list of selected items uri """
        if self.clip_view == SHOW_TREEVIEW:
            return self.getSelectedPathsTreeView()
        elif self.clip_view == SHOW_ICONVIEW:
            return self.getSelectedPathsIconView()

    def getSelectedPathsTreeView(self):
        model, rows = self.treeview.get_selection().get_selected_rows()
        return rows

    def getSelectedPathsIconView(self):
        paths = self.iconview.get_selected_items()
        paths.reverse()
        return paths

    def getSelectedItems(self):
        return [self.storemodel[path][COL_URI] 
            for path in self.getSelectedPaths()]

    def _dndDataGetCb(self, unused_widget, context, selection,
                      targettype, unused_eventtime):
        self.info("data get, type:%d", targettype)
        uris = self.getSelectedItems()
        if len(uris) < 1:
            return
        selection.set(selection.target, 8, '\n'.join(uris))
        context.set_icon_pixbuf(INVISIBLE, 0, 0)

class InfoStub(gtk.HBox, Loggable):
    """
    Box used to display information on the current state of the lists
    """

    __gsignals__ = {
        "remove-me" : (gobject.SIGNAL_RUN_LAST,
                       gobject.TYPE_NONE,
                       ( ))
        }

    def __init__(self):
        gtk.HBox.__init__(self)
        Loggable.__init__(self)
        self.errors = []
        self.showing = False
        self._importingmessage = _("Importing clips...")
        self._errorsmessage = _("Error(s) occurred while importing")
        self._errormessage = _("An error occurred while importing")
        self._makeUI()

    def _makeUI(self):
        self.set_spacing(SPACING)
        anim = gtk.gdk.PixbufAnimation(get_pixmap_dir() + "/busy.gif")
        self.busyanim = gtk.image_new_from_animation(anim)
        self.busyanim.show()

        self.erroricon = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING,
                                                  gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.erroricon.show()

        self.infolabel = gtk.Label(self._importingmessage)
        self.infolabel.set_alignment(0, 0.5)
        self.infolabel.show()

        self.questionbutton = gtk.Button()
        self.questionbutton.set_image(gtk.image_new_from_stock(gtk.STOCK_INFO,
                                                               gtk.ICON_SIZE_SMALL_TOOLBAR))
        self.questionbutton.connect("clicked", self._questionButtonClickedCb)
        self.questionbutton.show()
        self._questionshowing = False

        self.pack_start(self.busyanim, expand=False)
        self._busyshowing = True
        self.pack_start(self.infolabel, expand=True, fill=True)

    def startingImport(self):
        if self.showing:
            if self.errors:
                # if we're already showing and we have errors, show spinner
                self._showBusyAnim()
        else:
            self._showBusyAnim()
            self.infolabel.set_text(self._importingmessage)
            self._showQuestionButton(False)
            self.show()

    def stoppingImport(self):
        if self.errors:
            self._showErrorIcon()
            if len(self.errors) > 1:
                self.infolabel.set_text(self._errorsmessage)
            else:
                self.infolabel.set_text(self._errormessage)
            self._showQuestionButton()
        else:
            self.hide()
            self.emit("remove-me")

    def addErrors(self, *args):
        self.errors.append(args)

    def _showBusyAnim(self):
        if self._busyshowing:
            return
        self.remove(self.erroricon)
        self.pack_start(self.busyanim, expand=False)
        self.reorder_child(self.busyanim, 0)
        self.busyanim.show()
        self._busyshowing = True

    def _showErrorIcon(self):
        if not self._busyshowing:
            return
        self.remove(self.busyanim)
        self.pack_start(self.erroricon, expand=False)
        self.reorder_child(self.erroricon, 0)
        self.erroricon.show()
        self._busyshowing = False

    def _showQuestionButton(self, visible=True):
        if visible and not self._questionshowing:
            self.pack_start(self.questionbutton, expand=False)
            self.questionbutton.show()
            self._questionshowing = True
        elif not visible and self._questionshowing:
            self.remove(self.questionbutton)
            self._questionshowing = False

    def _errorDialogBoxCloseCb(self, dialog):
        dialog.destroy()

    def _errorDialogBoxResponseCb(self, dialog, unused_response):
        dialog.destroy()

    def _questionButtonClickedCb(self, unused_button):
        if len(self.errors) > 1:
            msgs = (_("Error while analyzing files"),
                    _("The following files can not be used with PiTiVi."))
        else:
            msgs = (_("Error while analyzing a file"),
                    _("The following file can not be used with PiTiVi."))
        # show error dialog
        dbox = FileListErrorDialog(*msgs)
        dbox.connect("close", self._errorDialogBoxCloseCb)
        dbox.connect("response", self._errorDialogBoxResponseCb)
        for uri, reason, extra in self.errors:
            dbox.addFailedFile(uri, reason, extra)
        dbox.show()
        # reset error list
        self.errors = []
        self.hide()
        self.emit("remove-me")

gobject.type_register(SourceList)
