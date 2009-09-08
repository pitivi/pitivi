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
from pitivi.ui.pathwalker import PathWalker
from pitivi.ui.filelisterrordialog import FileListErrorDialog
from pitivi.configure import get_pixmap_dir
from pitivi.signalgroup import SignalGroup
from pitivi.stream import VideoStream, AudioStream, TextStream, \
        MultimediaStream
from pitivi.settings import GlobalSettings
from pitivi.utils import beautify_length
from pitivi.ui.common import beautify_factory, factory_name, \
    beautify_stream
from pitivi.log.loggable import Loggable
from pitivi.sourcelist import SourceListError

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

(COL_ICON,
 COL_INFOTEXT,
 COL_FACTORY,
 COL_URI,
 COL_LENGTH,
 COL_SEARCH_TEXT) = range(6)

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

        # Store
        # icon, infotext, objectfactory, uri, length
        self.storemodel = gtk.ListStore(gtk.gdk.Pixbuf, str, object, str, str,
            str)

        # Scrolled Window
        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        # Popup Menu
        self.popup = gtk.Menu()
        additem = gtk.ImageMenuItem(_("Add Clips..."))
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        additem.set_image(image)

        remitem = gtk.ImageMenuItem(_("Remove Clip"))
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        remitem.set_image(image)
        playmenuitem = gtk.MenuItem(_("Play Clip"))
        playmenuitem.connect("activate", self._playButtonClickedCb)
        additem.connect("activate", self._addButtonClickedCb)
        remitem.connect("activate", self._removeButtonClickedCb)
        additem.show()
        remitem.show()
        playmenuitem.show()
        self.popup.append(additem)
        self.popup.append(remitem)
        self.popup.append(playmenuitem)

        # import sources dialogbox
        self._importDialog = None

        # TreeView
        # Displays icon, name, type, length
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview.connect("button-press-event", self._treeViewButtonPressEventCb)
        self.treeview.connect("row-activated", self._rowActivatedCb)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_headers_visible(False)
        self.treeview.set_property("search_column", COL_SEARCH_TEXT)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_MULTIPLE)
        tsel.connect("changed", self._treeSelectionChanged)

        pixbufcol = gtk.TreeViewColumn(_("Icon"))
        pixbufcol.set_expand(False)
        pixbufcol.set_spacing(5)
        self.treeview.append_column(pixbufcol)
        pixcell = gtk.CellRendererPixbuf()
        pixcell.props.xpad = 6
        pixbufcol.pack_start(pixcell)
        pixbufcol.add_attribute(pixcell, 'pixbuf', COL_ICON)

        namecol = gtk.TreeViewColumn(_("Information"))
        self.treeview.append_column(namecol)
        namecol.set_expand(True)
        namecol.set_spacing(5)
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

        # Start up with tree view
        self.scrollwin.add(self.treeview)

        # Explanatory message label
        textbox = gtk.EventBox()
        textbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('white'))
        textbox.show()

        txtlabel = gtk.Label()
        txtlabel.set_padding(10, 10)
        txtlabel.set_line_wrap(True)
        txtlabel.set_line_wrap_mode(pango.WRAP_WORD)
        txtlabel.set_justify(gtk.JUSTIFY_CENTER)
        txtlabel.set_markup(
            _("<span size='x-large'>Import your clips by dragging them here or "
              "by using the buttons above.</span>"))
        textbox.add(txtlabel)
        self.txtlabel = txtlabel

        self.textbox = textbox

        self.pack_start(self.textbox, expand=True, fill=True)
        self.reorder_child(self.textbox, 0)
        self.showingTreeView = False

        self.dragMotionSigId = self.txtlabel.connect("drag-motion",
                                                     self._dragMotionCb)

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
        self.treeview.connect("drag_begin", self._dndTreeBeginCb)
        self.treeview.connect("drag_data_get", self._dndDataGetCb)

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
                _("_Remove from project"), None, None,
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
        #self.project_signals.connect(
        #    project.sources, "missing-plugins", None, self._missingPluginsCb)
        self.project_signals.connect(
            project.sources, "ready", None, self._sourcesStoppedImportingCb)
        self.project_signals.connect(
            project.sources, "starting", None, self._sourcesStartedImportingCb)


    ## Explanatory message methods

    def _displayTreeView(self, displayed=True, usesignals=True):
        """ Display the tree view in the scrolled window.
        If displayed is False, then the default explanation message will be
        shown.
        If usesignals is True, then signals on the mesagewindow will be
        (dis)connected
        """
        if displayed:
            if self.showingTreeView:
                return
            self.debug("displaying tree view")
            self.remove(self.textbox)
            self.txtlabel.hide()
            if usesignals:
                if self.dragMotionSigId:
                    self.txtlabel.disconnect(self.dragMotionSigId)
                    self.dragMotionSigId = 0
            self.pack_start(self.scrollwin)
            self.reorder_child(self.scrollwin, 0)
            self.scrollwin.show_all()
            self.showingTreeView = True
        else:
            if not self.showingTreeView:
                return
            self.debug("hiding tree view")
            self.remove(self.scrollwin)
            self.scrollwin.hide()
            self.pack_start(self.textbox)
            self.reorder_child(self.textbox, 0)
            self.txtlabel.show()
            self.showingTreeView = False

    def _dragMotionCb(self, unused_layout, unused_context, unused_x, unused_y,
                      unused_timestamp):
        self.log("motion")
        gobject.idle_add(self._displayTreeView, True, False)

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
        self.app.current.sources.addUris(files)

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
            else:
                desiredheight = int(64 / float(video[0].dar))
                thumbnail = pixbuf.scale_simple(64,
                        desiredheight, gtk.gdk.INTERP_BILINEAR)
        else:
            if video:
                thumbnail = self.videofilepixbuf
            else:
                thumbnail = self.audiofilepixbuf

        if not factory.duration or factory.duration == gst.CLOCK_TIME_NONE:
            duration = ''
        else:
            duration = beautify_length(factory.duration)

        self.storemodel.append([thumbnail,
            beautify_factory(factory),
            factory,
            factory.uri,
            duration,
            factory_name(factory)])
        self._displayTreeView()

    # sourcelist callbacks

    def _sourceAddedCb(self, unused_sourcelist, factory):
        """ a file was added to the sourcelist """
        self._addFactory(factory)

    def _sourceRemovedCb(self, sourcelist, uri, factory):
        """ the given uri was removed from the sourcelist """
        # find the good line in the storemodel and remove it
        model = self.storemodel
        for row in model:
            if uri == row[COL_URI]:
                model.remove(row.iter)
                break
        if not len(model):
            self._displayTreeView(False)

    def _discoveryErrorCb(self, unused_sourcelist, uri, reason, extra):
        """ The given uri isn't a media file """
        self.infostub.addErrors(uri, reason, extra)

    def _missingPluginsCb(self, sourcelist, uri, details, descriptions):
        #self.infostub.addErrors(uri, "Missing plugins", "\n".join(descriptions))
        pass

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
        tsel = self.treeview.get_selection()
        if tsel.count_selected_rows() < 1:
            return
        model, selected = tsel.get_selected_rows()
        # Sort the list in reverse order so we remove from
        # the end and make sure that the paths are always valid
        selected.sort(reverse=True)
        for path in selected:
            uri = model[path][COL_URI]
            self.app.current.sources.removeUri(uri)

    ## UI Button callbacks

    def _addButtonClickedCb(self, unused_widget=None):
        """ called when a user clicks on the add button """
        self.showImportSourcesDialog()

    def _removeButtonClickedCb(self, unused_widget=None):
        """ Called when a user clicks on the remove button """
        self._removeSources()

    def _playButtonClickedCb(self, unused_widget):
        """ Called when a user clicks on the play button """
        # get the selected filesourcefactory
        model, paths = self.treeview.get_selection().get_selected_rows()
        if len(paths) < 1:
            return
        path = paths[0]
        factory = model[path][COL_FACTORY]
        self.debug("Let's play %s", factory.uri)
        self.emit('play', factory)

    _dragStarted = False
    _dragButton = None
    _dragX = 0
    _dragY = 0
    _ignoreRelease = False

    def _rowUnderMouseSelected(self, treeview, event):
        result = treeview.get_path_at_pos(int(event.x), int(event.y))
        if result:
            path = result[0]
            selection = treeview.get_selection()

            return selection.path_is_selected(path) and selection.count_selected_rows() > 1

        return False

    def _nothingUnderMouse(self, treeview, event):
        return not bool(treeview.get_path_at_pos(int(event.x), int(event.y)))

    def _treeViewButtonPressEventCb(self, treeview, event):
        chain_up = True

        if event.button == 3:
            self.popup.popup(None, None, None, event.button, event.time)
            chain_up = False

        else:

            if not event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK):
                chain_up = not self._rowUnderMouseSelected(treeview, event)

            self._dragStarted = False
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

    def _treeSelectionChanged(self, tsel):
        if self.getSelectedItems():
            self.selection_actions.set_sensitive(True)
        else:
            self.selection_actions.set_sensitive(False)

    def _rowActivatedCb(self, unused_treeview, path, unused_column):
        factory = self.storemodel[path][COL_FACTORY]
        self.emit('play', factory)

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
        def isfile(path):
            if path[:7] == "file://":
                # either it's on local system and we know if it's a directory
                return os.path.isfile(path[7:])
            elif "://" in path:
                # or it's not, in which case we assume it's a file
                return True
            # or it's on local system with "file://"
            return os.path.isfile(path)

        self.debug("targettype:%d, selection.data:%r", targettype, selection.data)
        directories = []
        if targettype == dnd.TYPE_URI_LIST:
            incoming = [unquote(x.strip('\x00')) for x in selection.data.strip().split("\r\n") if x.strip('\x00')]
            filenames = [x for x in incoming if isfile(x)]
            directories = [x for x in incoming if not isfile(x)]
        elif targettype == dnd.TYPE_TEXT_PLAIN:
            incoming = selection.data.strip()
            if isfile(incoming):
                filenames = [incoming]
            else:
                directories = [incoming]
        if directories:
            self.addFolders(directories)
        try:
            self.addUris(filenames)
        except SourceListError:
            # filenames already present in the sourcelist
            pass

    def _dndTreeBeginCb(self, unused_widget, context):
        self.info("tree drag_begin")
        model, paths = self.treeview.get_selection().get_selected_rows()
        if len(paths) < 1:
            context.drag_abort(int(time.time()))
        else:
            row = model[paths[0]]
            context.set_icon_pixbuf(row[COL_ICON], 0, 0)

    def getSelectedItems(self):
        """ returns a list of selected items uri """
        model, rows = self.treeview.get_selection().get_selected_rows()
        return [model[path][COL_URI] for path in rows]

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
        self.set_spacing(6)
        anim = gtk.gdk.PixbufAnimation(get_pixmap_dir() + "/busy.gif")
        self.busyanim = gtk.image_new_from_animation(anim)

        self.erroricon = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING,
                                                  gtk.ICON_SIZE_SMALL_TOOLBAR)

        self.infolabel = gtk.Label(self._importingmessage)
        self.infolabel.set_alignment(0, 0.5)

        self.questionbutton = gtk.Button()
        self.questionbutton.set_image(gtk.image_new_from_stock(gtk.STOCK_INFO,
                                                               gtk.ICON_SIZE_SMALL_TOOLBAR))
        self.questionbutton.connect("clicked", self._questionButtonClickedCb)
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

    def show(self):
        self.log("showing")
        self.show_all()
        self.showing = True

    def hide(self):
        self.log("hiding")
        gtk.VBox.hide(self)
        self.showing = False
gobject.type_register(SourceList)
