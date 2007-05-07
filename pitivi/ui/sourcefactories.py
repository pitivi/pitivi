# PiTiVi , Non-linear video editor
#
#       ui/sourcefactories.py
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

"""
Source and effects list widgets
"""

import os
import time
import string
import gobject
import gtk
import gst
import pango
import threading
from urllib import unquote

import pitivi.instance as instance
import pitivi.dnd as dnd
from pitivi.configure import get_pixmap_dir
from pitivi.signalgroup import SignalGroup
from pitivi.threads import Thread

from filelisterrordialog import FileListErrorDialog

from gettext import gettext as _

def beautify_length(length):
    sec = length / gst.SECOND
    mins = sec / 60
    sec = sec % 60
    if mins < 60:
        return "%02dm%02ds" % (mins, sec)
    hours = mins / 60
    mins = mins % 60
    return "%02dh%02dm%02ds" % (hours, mins, sec)

class SourceFactoriesWidget(gtk.Notebook):
    """
    Widget for the various source factories (files, effects, live,...)
    """

    def __init__(self):
        """ initialize """
        gtk.Notebook.__init__(self)
        self._createUi()

    def _createUi(self):
        """ set up the gui """
        self.set_tab_pos(gtk.POS_TOP)
        self.sourcelist = SourceListWidget()
        self.append_page(self.sourcelist, gtk.Label(_("Clips")))

        ## FIXME: The following are deactivated until they do more than just
        ##      display things.

##         self.audiofxlist = AudioFxListWidget()
##         #self.audiofxlist.set_sensitive(False)
##         self.append_page(self.audiofxlist, gtk.Label("Audio FX"))
##         self.videofxlist = VideoFxListWidget()
##         #self.videofxlist.set_sensitive(False)
##         self.append_page(self.videofxlist, gtk.Label("Video FX"))
##         self.transitionlist = TransitionListWidget()
##         self.transitionlist.set_sensitive(False)
##         self.append_page(self.transitionlist, gtk.Label("Transitions"))


(COL_ICON,
 COL_INFOTEXT,
 COL_FACTORY,
 COL_URI,
 COL_LENGTH) = range(5)

class SourceListWidget(gtk.VBox):
    """ Widget for listing sources """

    def __init__(self):
        gtk.VBox.__init__(self)

        # Store
        # icon, infotext, objectfactory, uri, length
        self.storemodel = gtk.ListStore(gtk.gdk.Pixbuf, str, object, str, str)

        self.set_border_width(5)
        self.set_spacing(6)

        # Scrolled Window
        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_NEVER,gtk.POLICY_AUTOMATIC)
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
        self._lastFolder = None

        # TreeView
        # Displays icon, name, type, length
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview.connect("button-press-event", self._treeViewButtonPressEventCb)
        self.treeview.connect("row-activated", self._rowActivatedCb)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_headers_visible(False)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_MULTIPLE)

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
        self._connectToProject(instance.PiTiVi.current)
        instance.PiTiVi.connect("new-project", self._newProjectCb)

        # default pixbufs
        icontheme = gtk.icon_theme_get_default()
        self.filepixbuf = icontheme.load_icon("misc", 32, 0)
        self.audiofilepixbuf = icontheme.load_icon("audio-x-generic", 32, 0)
        self.videofilepixbuf = icontheme.load_icon("video-x-generic", 32, 0)

        # Drag and Drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.URI_TUPLE, dnd.FILE_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag_data_received", self._dndDataReceivedCb)

        self.treeview.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                      [dnd.URI_TUPLE, dnd.FILESOURCE_TUPLE],
                                      gtk.gdk.ACTION_COPY)
        self.treeview.connect("drag_begin", self._dndTreeBeginCb)
        self.treeview.connect("drag_data_get", self._dndDataGetCb)

        # Hack so that the views have the same method as self
        self.treeview.getSelectedItems = self.getSelectedItems

        # Error dialog box
        self.errorDialogBox = None

    def _connectToProject(self, project):
        """Connect signal handlers to a project.

        This first disconnects any handlers connected to an old project.
        If project is None, this just disconnects any connected handlers.

        """
        self.project_signals.connect(project.sources, "file_added", None, self._fileAddedCb)
        self.project_signals.connect(project.sources, "file_removed", None, self._fileRemovedCb)
        self.project_signals.connect(project.sources, "not_media_file", None, self._notMediaFileCb)
        self.project_signals.connect(project.sources, "ready", None, self._sourcesStoppedImportingCb)
        self.project_signals.connect(project.sources, "starting", None, self._sourcesStartedImportingCb)


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
            gst.debug("displaying tree view")
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
            gst.debug("hiding tree view")
            self.remove(self.scrollwin)
            self.scrollwin.hide()
            self.pack_start(self.textbox)
            self.reorder_child(self.textbox, 0)
            self.txtlabel.show()
            self.showingTreeView = False

    def _dragMotionCb(self, unused_layout, unused_context, x, unused_y,
                      unused_timestamp):
        gst.log("motion")
        gobject.idle_add(self._displayTreeView, True, False)

    def showImportSourcesDialog(self, select_folders=False):
        if self._importDialog:
            return

        if select_folders:
            chooser_action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
            dialogtitle = _("Import a folder")
        else:
            chooser_action = gtk.FILE_CHOOSER_ACTION_OPEN
            dialogtitle = _("Import a clip")

        self._importDialog = gtk.FileChooserDialog(dialogtitle, None,
                                                   chooser_action,
                                                   (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE,
                                                    gtk.STOCK_ADD, gtk.RESPONSE_OK))

        self._importDialog.set_default_response(gtk.RESPONSE_OK)
        self._importDialog.set_select_multiple(True)
        self._importDialog.set_modal(False)
        if self._lastFolder:
            self._importDialog.set_current_folder(self._lastFolder)
        self._importDialog.connect('response', self._dialogBoxResponseCb, select_folders)
        self._importDialog.connect('close', self._dialogBoxCloseCb)
        self._importDialog.show()

    def addFiles(self, list):
        """ Add files to the list """
        instance.PiTiVi.current.sources.addUris(list)

    def addFolders(self, list):
        """ walks the trees of the folders in the list and adds the files it finds """
        instance.PiTiVi.threads.addThread(PathWalker, list, instance.PiTiVi.current.sources.addUris)

    # sourcelist callbacks

    def _fileAddedCb(self, unused_sourcelist, factory):
        """ a file was added to the sourcelist """
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(factory.thumbnail)
        except:
            if factory.is_video:
                thumbnail = self.videofilepixbuf
            elif factory.is_audio:
                thumbnail = self.audiofilepixbuf
        else:
            if not factory.video_info_stream:
                desiredheight = 64 * pixbuf.get_height() / pixbuf.get_width()
            else:
                vi = factory.video_info_stream
                desiredheight = int(64 / float(vi.dar))
            thumbnail = pixbuf.scale_simple(64, desiredheight, gtk.gdk.INTERP_BILINEAR)
        self.storemodel.append([thumbnail,
                                factory.getPrettyInfo(),
                                factory,
                                factory.name,
                                "<b>%s</b>" % beautify_length(factory.length)])
        self._displayTreeView()

    def _fileRemovedCb(self, unused_sourcelist, uri):
        """ the given uri was removed from the sourcelist """
        # find the good line in the storemodel and remove it
        model = self.storemodel
        for row in model:
            if uri == row[COL_URI]:
                model.remove(row.iter)
                break
        if not len(model):
            self._displayTreeView(False)

    def _notMediaFileCb(self, unused_sourcelist, uri, reason, extra):
        """ The given uri isn't a media file """
        self.infostub.addErrors(uri, reason, extra)

    def _sourcesStartedImportingCb(self, unused_sourcelist):
        if not self.infostub.showing:
            self.pack_start(self.infostub, expand=False)
        self.infostub.startingImport()

    def _sourcesStoppedImportingCb(self, unused_sourcelist):
        self.infostub.stoppingImport()

    def _removeInfoStub(self, infostub):
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
        gst.debug("response:%r" % response)
        if response == gtk.RESPONSE_OK:
            self._lastFolder = dialogbox.get_current_folder()
            filenames = dialogbox.get_uris()
            if select_folders:
                self.addFolders(filenames)
            else:
                self.addFiles(filenames)
        else:
            dialogbox.destroy()
            self._importDialog = None

    def _dialogBoxCloseCb(self, unused_dialogbox):
        gst.debug("closing")
        self._importDialog = None


    ## UI Button callbacks

    def _addButtonClickedCb(self, unused_widget=None):
        """ called when a user clicks on the add button """
        self.showImportSourcesDialog()

    def _removeButtonClickedCb(self, unused_widget=None):
        """ Called when a user clicks on the remove button """
        tsel = self.treeview.get_selection()
        if tsel.count_selected_rows() < 1:
            return
        model, selected = tsel.get_selected_rows()
        # Sort the list in reverse order so we remove from
        # the end and make sure that the paths are always valid
        selected.sort(reverse=True)
        for path in selected:
            uri = model[path][COL_URI]
            del instance.PiTiVi.current.sources[uri]

    def _errorDialogButtonClickedCb(self, unused_widget=None):
        """ called when the user click on the import errors button """
        if self.errorDialogBox:
            self.errorDialogBox.show()
        if self.errorDialogButton.parent:
            self.bothbox.remove(self.errorDialogButton)

    def _playButtonClickedCb(self, unused_widget):
        """ Called when a user clicks on the play button """
        # get the selected filesourcefactory
        model, paths = self.treeview.get_selection().get_selected_rows()
        if len(paths) < 1:
            return
        path = paths[0]
        factory = model[path][COL_FACTORY]
        gst.debug("Let's play %s" % factory.name)
        instance.PiTiVi.playground.playTemporaryFilesourcefactory(factory)

    def _treeViewButtonPressEventCb(self, unused_treeview, event):
        if event.button == 3:
            self.popup.popup(None, None, None, event.button, event.time)

    def _rowActivatedCb(self, unused_treeview, path, unused_column):
        factory = self.storemodel[path][COL_FACTORY]
        instance.PiTiVi.playground.playTemporaryFilesourcefactory(factory)

    def _newProjectCb(self, unused_pitivi, project):
        # clear the storemodel
        self.storemodel.clear()

        # synchronize the storemodel with the new project's sourcelist
        for uri, factory in project.sources:
            if factory:
                if factory.thumbnail:
                    thumbnail = gtk.gdk.pixbuf_new_from_file(factory.thumbnail)
                    desiredheight = 64 * thumbnail.get_height() / thumbnail.get_width()
                    thumbnail = thumbnail.scale_simple(64, desiredheight, gtk.gdk.INTERP_BILINEAR)
                name = os.path.basename(unquote(factory.name))
                if factory.is_video:
                    if not factory.thumbnail:
                        thumbnail = self.videofilepixbuf
                else:
                    if not factory.thumbnail:
                        thumbnail = self.audiofilepixbuf
                # FIXME : update with new table structure (icon, infotext, objectfactory, uri
                self.storemodel.append([thumbnail, name, factory, factory.name,
                                "<b>%s</b>" % beautify_length(factory.length)])

        self._connectToProject(project)


    ## Drag and Drop

    def _dndDataReceivedCb(self, unused_widget, unused_context, unused_x,
                           unused_y, selection, targetType, unused_time):
        def isfile(path):
            if path[:7] == "file://":
                # either it's on local system and we know if it's a directory
                return os.path.isfile(path[7:])
            elif "://" in path:
                # or it's not, in which case we assume it's a file
                return True
            # or it's on local system with "file://"
            return os.path.isfile(path)

        gst.debug("targetType:%d, selection.data:%r" % (targetType, selection.data))
        directories = []
        if targetType == dnd.TYPE_URI_LIST:
            incoming = [x.strip('\x00') for x in selection.data.strip().split("\r\n") if x.strip('\x00')]
            filenames = [x for x in incoming if isfile(x)]
            directories = [x for x in incoming if not isfile(x)]
        elif targetType == dnd.TYPE_TEXT_PLAIN:
            incoming = selection.data.strip()
            if isfile(incoming):
                filenames = [incoming]
            else:
                directories = [incoming]
        if directories:
            self.addFolders(directories)
        self.addFiles(filenames)

    def _dndTreeBeginCb(self, unused_widget, context):
        gst.info("tree drag_begin")
        model, paths = self.treeview.get_selection().get_selected_rows()
        if len(paths) < 1:
            context.drag_abort(int(time.time()))
        else:
            row = model[paths[0]]
            self.treeview.drag_source_set_icon_pixbuf(row[COL_ICON])

    def getSelectedItems(self):
        """ returns a list of selected items uri """
        model, rows = self.treeview.get_selection().get_selected_rows()
        return [model[path][COL_URI] for path in rows]

    def _dndDataGetCb(self, unused_widget, unused_context, selection,
                      targetType, unused_eventTime):
        gst.info("data get, type:%d" % targetType)
        uris = self.getSelectedItems()
        if len(uris) < 1:
            return
        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            selection.set(selection.target, 8,
                          uris[0])
        elif targetType == dnd.TYPE_URI_LIST:
            selection.set(selection.target, 8,
                          string.join(uris, "\n"))

class AudioFxListWidget(gtk.VBox):
    """ Widget for listing video effects """

    def __init__(self):
        gtk.VBox.__init__(self)
        self.set_border_width(5)

        # model
        self.storemodel = gtk.ListStore(str, str, object)

        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_NEVER,
                                  gtk.POLICY_AUTOMATIC)
        self.pack_start(self.scrollwin)

        self.iconview = gtk.IconView(self.storemodel)
        self.treeview = gtk.TreeView(self.storemodel)

        namecol = gtk.TreeViewColumn(_("Name"))
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", 0)

        namecol = gtk.TreeViewColumn(_("Description"))
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", 1)

        self.scrollwin.add(self.treeview)

        self._fillUpModel()

    def _fillUpModel(self):
        for factory in instance.PiTiVi.effects.simple_audio:
            self.storemodel.append([factory.get_longname(),
                                    factory.get_description(),
                                    factory])

(COL_NAME,
 COL_DESCRIPTION,
 COL_FACTORY) = range(3)

class VideoFxListWidget(gtk.VBox):
    """ Widget for listing video effects """

    def __init__(self):
        gtk.VBox.__init__(self)
        self.set_border_width(5)

        # model
        self.storemodel = gtk.ListStore(str, str, object)

        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_NEVER,
                                  gtk.POLICY_AUTOMATIC)
        self.pack_start(self.scrollwin)

        self.iconview = gtk.IconView(self.storemodel)
        self.treeview = gtk.TreeView(self.storemodel)

        namecol = gtk.TreeViewColumn(_("Name"))
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", COL_NAME)

        namecol = gtk.TreeViewColumn(_("Description"))
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", COL_DESCRIPTION)

        self.scrollwin.add(self.treeview)

        self._fillUpModel()

    def _fillUpModel(self):
        for factory in instance.PiTiVi.effects.simple_video:
            self.storemodel.append([factory.get_longname(),
                                    factory.get_description(),
                                    factory])


class TransitionListWidget(gtk.VBox):
    """ Widget for listing transitions """

    def __init__(self):
        gtk.VBox.__init__(self)
        self.iconview = gtk.IconView()
        self.treeview = gtk.TreeView()
        self.pack_start(self.iconview)

class InfoStub(gtk.HBox):
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
        self.errors = []
        self.showing = False
        self._importingmessage = _("Importing clips...")
        self._errorsmessage = _("Error(s) occured while importing")
        self._errormessage = _("An error occured while importing")
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
        # show error dialog
        dbox = FileListErrorDialog(
            _("Error while analyzing files"),
            _("The following files can not be used with PiTiVi."))
        dbox.connect("close", self._errorDialogBoxCloseCb)
        dbox.connect("response", self._errorDialogBoxResponseCb)
        for uri,reason,extra in self.errors:
            dbox.addFailedFile(uri, reason, extra)
        dbox.show()
        # reset error list
        self.errors = []
        self.hide()

    def show(self):
        gst.log("showing")
        self.show_all()
        self.showing = True

    def hide(self):
        gst.log("hiding")
        gtk.VBox.hide(self)
        self.showing = False


class PathWalker(Thread):
    """
    Thread for recursively searching in a list of directories
    """

    def __init__(self, paths, callback):
        Thread.__init__(self)
        gst.log("New PathWalker for %s" % paths)
        self.paths = paths
        self.callback = callback
        self.stopme = threading.Event()

    def process(self):
        for folder in self.paths:
            gst.log("folder %s" % folder)
            if folder.startswith("file://"):
                folder = folder[len("file://"):]
            for path, dirs, files in os.walk(folder):
                if self.stopme.isSet():
                    return
                uriList = []
                for afile in files:
                    uriList.append("file://%s" % os.path.join(path, afile))
                if uriList:
                    self.callback(uriList)

    def abort(self):
        self.stopme.set()
