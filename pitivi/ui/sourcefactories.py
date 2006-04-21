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
import os.path
import time
import string
import gobject
import gtk
import gst
import pango
from urllib import unquote

import pitivi.instance as instance
import pitivi.dnd as dnd
from pitivi.configure import get_pixmap_dir
from glade import GladeWindow

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
        self.append_page(self.sourcelist, gtk.Label("Sources"))

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



class SourceListWidget(gtk.VBox):
    """ Widget for listing sources """

    def __init__(self):
        gtk.VBox.__init__(self)

        # Store
        # icon, infotext, objectfactory, uri, length
        self.storemodel = gtk.ListStore(gtk.gdk.Pixbuf, str, object, str, str)

        self.set_border_width(5)
        self.set_size_request(300, -1)

        # Scrolled Window
        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
        self.pack_start(self.scrollwin)

        # Popup Menu
        self.popup = gtk.Menu()
        additem = gtk.MenuItem("Add Sources...")
        remitem = gtk.MenuItem("Remove Sources...")
        playmenuitem = gtk.MenuItem("Play")
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
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_MULTIPLE)
        
        pixbufcol = gtk.TreeViewColumn("Icon")
        pixbufcol.set_expand(False)
        pixbufcol.set_spacing(5)
        self.treeview.append_column(pixbufcol)
        pixcell = gtk.CellRendererPixbuf()
        pixbufcol.pack_start(pixcell)
        pixbufcol.add_attribute(pixcell, 'pixbuf', 0)

        namecol = gtk.TreeViewColumn("Information")
        self.treeview.append_column(namecol)
        namecol.set_expand(True)
        namecol.set_spacing(5)
        txtcell = gtk.CellRendererText()
        txtcell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(txtcell)
        namecol.add_attribute(txtcell, "markup", 1)

        namecol = gtk.TreeViewColumn("Duration")
        namecol.set_expand(False)
        self.treeview.append_column(namecol)
        txtcell = gtk.CellRendererText()
        txtcell.set_property("yalign", 0.0)
        namecol.pack_start(txtcell)
        namecol.add_attribute(txtcell, "markup", 4)

        # buttons (list/icon view, add, remove)
        button = gtk.Button(stock=gtk.STOCK_ADD)
        button.connect("clicked", self._addButtonClickedCb)
        rbut = gtk.Button(stock=gtk.STOCK_REMOVE)
        rbut.connect("clicked", self._removeButtonClickedCb)
        bothbox = gtk.HBox()
        bothbox.pack_start(button, expand=False)
        bothbox.pack_start(rbut, expand=False)
        self.pack_start(bothbox, expand=False)

        # Start up with tree view
        self.scrollwin.add(self.treeview)

        # callbacks from discoverer
        # TODO : we must remove and reset the callbacks when changing project
        instance.PiTiVi.current.sources.connect("file_added", self._fileAddedCb)
        instance.PiTiVi.current.sources.connect("file_removed", self._fileRemovedCb)
        instance.PiTiVi.current.sources.connect("not_media_file", self._notMediaFileCb)

        instance.PiTiVi.connect("new-project", self._newProjectCb)

        # default pixbufs
        pixdir = get_pixmap_dir()
        self.filepixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, "pitivi-file.png"))
        self.audiofilepixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, "pitivi-sound.png"))
        self.videofilepixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, "pitivi-video.png"))
        
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

    def showImportSourcesDialog(self):
        if self._importDialog:
            return
        self._importDialog = gtk.FileChooserDialog("Import a file", None,
                                                   gtk.FILE_CHOOSER_ACTION_OPEN,
                                                   (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                    gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        self._importDialog.set_default_response(gtk.RESPONSE_OK)
        self._importDialog.set_select_multiple(True)
        self._importDialog.set_modal(False)
        self._importDialog.connect('response', self._dialogBoxResponseCb)
        self._importDialog.connect('close', self._dialogBoxCloseCb)
        self._importDialog.show()
        
    def addFiles(self, list):
        """ Add files to the list """
        instance.PiTiVi.current.sources.addUris(list)


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
            # FIXME : Use DAR from factory
            #pixbuf = gtk.gdk.pixbuf_new_from_file(factory.thumbnail)
            if not factory.video_info_stream:
                desiredheight = 64 * pixbuf.get_height() / pixbuf.get_width()
            else:
                vi = factory.video_info_stream
                desiredheight = 64 * vi.dar.denom / vi.dar.num
            thumbnail = pixbuf.scale_simple(64, desiredheight, gtk.gdk.INTERP_BILINEAR)
        if factory.is_video:
            if factory.is_audio:
                desc = "Audio/Video"
            else:
                desc = "Video"
        else:
            desc = "Audio"
        self.storemodel.append([thumbnail,
                                "<b>%s</b>\n<small>%s</small>" % (os.path.basename(unquote(factory.name)), factory.getPrettyInfo()),
                                factory,
                                factory.name,
                                "<b>%s</b>" % beautify_length(factory.length)])

    def _fileRemovedCb(self, unused_sourcelist, uri):
        """ the given uri was removed from the sourcelist """
        # find the good line in the storemodel and remove it
        piter = self.storemodel.get_iter_first()
        while piter:
            if uri == self.storemodel.get_value(piter, 3):
                self.storemodel.remove(piter)
                break
            piter = self.storemodel.iter_next(piter)

    def _notMediaFileCb(self, unused_sourcelist, uri, reason):
        """ The given uri isn't a media file """
        # popup a dialog box and fill up with reasons
        if not self.errorDialogBox:
            # construct and display it
            self.errorDialogBox = DiscovererErrorDialog()
            self.errorDialogBox.connect('close', self._errorDialogBoxCloseCb)
            self.errorDialogBox.connect('response', self._errorDialogBoxResponseCb)
            self.errorDialogBox.show()
        self.errorDialogBox.addFailedFile(uri, reason)


    ## Error Dialog Box callbacks

    def _errorDialogBoxCloseCb(self, unused_dialog):
        self.errorDialogBox.destroy()
        self.errorDialogBox = None

    def _errorDialogBoxResponseCb(self, unused_dialog, unused_response):
        self.errorDialogBox.destroy()
        self.errorDialogBox = None


    ## Import Sources Dialog Box callbacks
        
    def _dialogBoxResponseCb(self, dialogbox, response):
        gst.debug("response:%r" % response)
        dialogbox.hide()
        if response == gtk.RESPONSE_OK:
            filenames = dialogbox.get_uris()
            self.addFiles(filenames)
        dialogbox.destroy()
        self._importDialog = None

    def _dialogBoxCloseCb(self, dialogbox):
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
        store, selected = tsel.get_selected_rows()
        uris = [self.storemodel.get_value(self.storemodel.get_iter(path), 3) for path in selected]
        for uri in uris:
            del instance.PiTiVi.current.sources[uri]

    def _playButtonClickedCb(self, unused_widget):
        """ Called when a user clicks on the play button """
        # get the selected filesourcefactory
        model, paths = self.treeview.get_selection().get_selected_rows()
        if len(paths) < 1:
            return
        factory = self.storemodel.get_value(self.storemodel.get_iter(paths[0]), 2)
        gst.debug("Let's play %s" % factory.name)
        instance.PiTiVi.playground.playTemporaryFilesourcefactory(factory)

    def _treeViewButtonPressEventCb(self, unused_treeview, event):
        if event.button == 3:
            self.popup.popup(None, None, None, event.button, event.time)

    def _rowActivatedCb(self, unused_treeview, path, unused_column):
        factory = self.storemodel.get_value(self.storemodel.get_iter(path), 2)
        instance.PiTiVi.playground.playTemporaryFilesourcefactory(factory)

    def _newProjectCb(self, unused_pitivi, project):
        # clear the storemodel
        self.storemodel.clear()

        # synchronize the storemodel with the new project's sourcelist
        for uri, factory in project.sources:
            if factory:
                length = beautify_length(factory.length)
                if factory.thumbnail:
                    thumbnail = gtk.gdk.pixbuf_new_from_file(factory.thumbnail)
                    desiredheight = 64 * thumbnail.get_height() / thumbnail.get_width()
                    thumbnail = thumbnail.scale_simple(64, desiredheight, gtk.gdk.INTERP_BILINEAR)
                name = os.path.basename(unquote(factory.name))
                if factory.is_video:
                    if factory.is_audio:
                        desc = "Audio/Video"
                    else:
                        desc = "Video"
                    if not factory.thumbnail:
                        thumbnail = self.videofilepixbuf
                else:
                    desc = "Audio"
                    if not factory.thumbnail:
                        thumbnail = self.audiofilepixbuf
                # FIXME : update with new table structure (icon, infotext, objectfactory, uri
                self.storemodel.append([thumbnail, name, factory, factory.name,
                                "<b>%s</b>" % beautify_length(factory.length)])
        
        instance.PiTiVi.current.sources.connect("file_added", self._fileAddedCb)
        instance.PiTiVi.current.sources.connect("file_removed", self._fileRemovedCb)


    ## Drag and Drop

    def _dndDataReceivedCb(self, unused_widget, unused_context, unused_x,
                           unused_y, selection, targetType, unused_time):
        gst.debug("targetType:%d, selection.data:%r" % (targetType, selection.data))
        if targetType == dnd.TYPE_URI_LIST:
            filenames = [x.strip('\x00') for x in selection.data.strip().split("\r\n") if x.strip('\x00')]
        elif targetType == dnd.TYPE_TEXT_PLAIN:
            filenames = [selection.data.strip()]
        self.addFiles(filenames)

    def _dndTreeBeginCb(self, unused_widget, context):
        gst.info("tree drag_begin")
        model, rows = self.treeview.get_selection().get_selected_rows()
        if len(rows) < 1:
            context.drag_abort(int(time.time()))

    def getSelectedItems(self):
        """ returns a list of selected items uri """
        model, rows = self.treeview.get_selection().get_selected_rows()
        uris = [self.storemodel.get_value(self.storemodel.get_iter(x), 3) for x in rows]
        return uris

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

        namecol = gtk.TreeViewColumn("Name")
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", 0)
        
        namecol = gtk.TreeViewColumn("Description")
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

        namecol = gtk.TreeViewColumn("Name")
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", 0)
        
        namecol = gtk.TreeViewColumn("Description")
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", 1)
        
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


class DiscovererErrorDialog(GladeWindow):
    """ Dialog box for showing errors from discovering files """
    glade_file = "discoverererrordialog.glade"
    __gsignals__ = {
        'close': (gobject.SIGNAL_RUN_LAST,
                  gobject.TYPE_NONE,
                  ( )),
        'response': (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT, ))
        }

    def __init__(self):
        GladeWindow.__init__(self)
        self.window.set_modal(False)
        self.treeview = self.widgets["treeview"]
        self.window.set_geometry_hints(min_width=400, min_height=300)
        self._setUpTreeView()

    def _setUpTreeView(self):
        self.storemodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview.set_model(self.storemodel)

        txtcell = gtk.CellRendererText()
        txtcell.set_property("ellipsize", pango.ELLIPSIZE_START)
        uricol = gtk.TreeViewColumn("File", txtcell, text=0)
        uricol.set_expand(True)
        self.treeview.append_column(uricol)

        txtcell2 = gtk.CellRendererText()
        txtcell2.set_property("ellipsize", pango.ELLIPSIZE_END)
        reasoncol = gtk.TreeViewColumn("Reason", txtcell2, text=1)
        reasoncol.set_expand(True)
        self.treeview.append_column(reasoncol)

    def addFailedFile(self, uri, reason="Unknown reason"):
        """Add the given uri to the list of failed files. You can optionnaly
        give a string identifying the reason why the file failed to be
        discovered
        """
        gst.debug("Uri:%s, reason:%s" % (uri, reason))
        self.storemodel.append([str(uri), str(reason)])

    ## Callbacks from glade

    def _closeCb(self, unused_dialog):
        self.emit('close')

    def _responseCb(self, unused_dialog, response):
        self.emit('response', response)
