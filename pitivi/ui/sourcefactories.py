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
    min = sec / 60
    sec = sec % 60    
    return "%02dm%02ds" % (min, sec)

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
        self.set_tab_pos(gtk.POS_BOTTOM)
        self.sourcelist = SourceListWidget()
        self.append_page(self.sourcelist, gtk.Label("Sources"))
        self.audiofxlist = AudioFxListWidget()
        #self.audiofxlist.set_sensitive(False)
        self.append_page(self.audiofxlist, gtk.Label("Audio FX"))
        self.videofxlist = VideoFxListWidget()
        #self.videofxlist.set_sensitive(False)
        self.append_page(self.videofxlist, gtk.Label("Video FX"))
        self.transitionlist = TransitionListWidget()
        self.transitionlist.set_sensitive(False)
        self.append_page(self.transitionlist, gtk.Label("Transitions"))



class SourceListWidget(gtk.VBox):
    """ Widget for listing sources """

    def __init__(self):
        gtk.VBox.__init__(self)

        # Store
        # icon, name, type(audio/video), length, objectfactory, uri
        self.storemodel = gtk.ListStore(gtk.gdk.Pixbuf, str, str, str, object, str)

        self.set_border_width(5)

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

        # TreeView
        # Displays icon, name, type, length
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview.connect("button-press-event", self._treeViewButtonPressEventCb)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_MULTIPLE)
        
        pixbufcol = gtk.TreeViewColumn("Icon")
        self.treeview.append_column(pixbufcol)
        pixcell = gtk.CellRendererPixbuf()
        pixbufcol.pack_start(pixcell)
        pixbufcol.add_attribute(pixcell, 'pixbuf', 0)

        namecol = gtk.TreeViewColumn("Name")
        self.treeview.append_column(namecol)
        txtcell = gtk.CellRendererText()
        namecol.pack_start(txtcell)
        namecol.add_attribute(txtcell, "text", 1)

        typecol = gtk.TreeViewColumn("Info")
        self.treeview.append_column(typecol)
        txtcell = gtk.CellRendererText()
        typecol.pack_start(txtcell)
        typecol.add_attribute(txtcell, "text", 2)

        lencol = gtk.TreeViewColumn("Length")
        self.treeview.append_column(lencol)
        txtcell = gtk.CellRendererText()
        lencol.pack_start(txtcell)
        lencol.add_attribute(txtcell, "text", 3)

        # IconView
        self.iconview = gtk.IconView(self.storemodel)
        self.iconview.set_pixbuf_column(0)
        self.iconview.set_text_column(1)
        self.iconview.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self.iconview.connect("button-press-event", self._iconViewButtonPressEventCb)

        # buttons (list/icon view, add, remove)
        button = gtk.Button(stock=gtk.STOCK_ADD)
        button.connect("clicked", self._addButtonClickedCb)
        rbut = gtk.Button(stock=gtk.STOCK_REMOVE)
        rbut.connect("clicked", self._removeButtonClickedCb)
        self.listviewbutton = gtk.ToggleButton("List View")
        self.listviewbutton.connect("toggled", self._listViewButtonToggledCb)
        self.iconviewbutton = gtk.ToggleButton("Icon View")
        self.iconviewbutton.connect("toggled", self._iconViewButtonToggledCb)        
        bothbox = gtk.HBox()
        bothbox.pack_end(button, expand=False)
        bothbox.pack_end(rbut, expand=False)
        bothbox.pack_end(self.listviewbutton, expand=False)
        bothbox.pack_end(self.iconviewbutton, expand=False)
        self.pack_start(bothbox, expand=False)

        # Start up with tree view
        self.iconviewmode = True
        self.scrollwin.add(self.iconview)
        self.iconviewbutton.set_active(True)

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

        self.iconview.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                      [dnd.URI_TUPLE, dnd.FILESOURCE_TUPLE],
                                      gtk.gdk.ACTION_COPY)
        self.iconview.connect("drag_begin", self._dndIconBeginCb)
        self.iconview.connect("drag_data_get", self._dndDataGetCb)
        
        self.treeview.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                      [dnd.URI_TUPLE, dnd.FILESOURCE_TUPLE],
                                      gtk.gdk.ACTION_COPY)
        self.treeview.connect("drag_begin", self._dndTreeBeginCb)
        self.treeview.connect("drag_data_get", self._dndDataGetCb)
        
        # Hack so that the views have the same method as self
        self.iconview.getSelectedItems = self.getSelectedItems
        self.treeview.getSelectedItems = self.getSelectedItems

        # Error dialog box
        self.errorDialogBox = None

    def useTreeView(self):
        """ use the treeview """
        gst.info("Use tree view")
        if not self.iconviewmode:
            return
        else:
            self.scrollwin.remove(self.iconview)
            self.iconview.hide()
        self.scrollwin.add(self.treeview)
        self.treeview.show()
        self.iconviewmode = False

    def useIconView(self):
        """ use the iconview """
        gst.info("use icon view")
        if self.iconviewmode:
            return
        else:
            self.scrollwin.remove(self.treeview)
            self.treeview.hide()
        self.scrollwin.add(self.iconview)
        self.iconview.show()
        self.iconviewmode = True

    def _fileAddedCb(self, sourcelist, factory):
        """ a file was added to the sourcelist """
        if not factory.thumbnail:
            if factory.is_video:
                thumbnail = self.videofilepixbuf
            elif factory.is_audio:
                thumbnail = self.audiofilepixbuf
        else:
            # FIXME : Use DAR from factory
            pixbuf = gtk.gdk.pixbuf_new_from_file(factory.thumbnail)
            desiredheight = 128 * pixbuf.get_height() / pixbuf.get_width()
            thumbnail = pixbuf.scale_simple(128, desiredheight, gtk.gdk.INTERP_BILINEAR)
        if factory.is_video:
            if factory.is_audio:
                desc = "Audio/Video"
            else:
                desc = "Video"
        else:
            desc = "Audio"
        self.storemodel.append([thumbnail,
                                os.path.basename(unquote(factory.name)),
                                desc,
                                beautify_length(factory.length),
                                factory,
                                factory.name])

    def _fileRemovedCb(self, sourcelist, uri):
        """ the given uri was removed from the sourcelist """
        # find the good line in the storemodel and remove it
        piter = self.storemodel.get_iter_first()
        while piter:
            if uri == self.storemodel.get_value(piter, 5):
                self.storemodel.remove(piter)
                break
            piter = self.storemodel.iter_next(piter)

    def _notMediaFileCb(self, sourcelist, uri, reason):
        """ The given uri isn't a media file """
        # popup a dialog box and fill up with reasons
        if not self.errorDialogBox:
            # construct and display it
            self.errorDialogBox = DiscovererErrorDialog()
            self.errorDialogBox.connect('close', self._errorDialogBoxCloseCb)
            self.errorDialogBox.connect('response', self._errorDialogBoxResponseCb)
            self.errorDialogBox.show()
        self.errorDialogBox.addFailedFile(uri, reason)

    def addFiles(self, list):
        """ Add files to the list """
        instance.PiTiVi.current.sources.addUris(list)

    ## Error Dialog Box callbacks

    def _errorDialogBoxCloseCb(self, dialog):
        self.errorDialogBox.destroy()
        self.errorDialogBox = None

    def _errorDialogBoxResponseCb(self, dialog, response):
        self.errorDialogBox.destroy()
        self.errorDialogBox = None


    ## UI Button callbacks
            
    def _addButtonClickedCb(self, widget):
        """ called when a user clicks on the add button """
        dialog = gtk.FileChooserDialog("Import a file", None,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_select_multiple(True)
        response = dialog.run()
        filenames = None
        dialog.hide()
        if response == gtk.RESPONSE_OK:
            filenames = dialog.get_uris()
            self.addFiles(filenames)
        dialog.destroy()

    def _removeButtonClickedCb(self, widget):
        """ Called when a user clicks on the remove button """
        if self.iconviewmode:
            selected = self.iconview.get_selected_items()
        else:
            tsel = self.treeview.get_selection()
            if tsel.count_selected_rows() < 1:
                return
            store, selected = tsel.get_selected_rows()
        uris = [self.storemodel.get_value(self.storemodel.get_iter(path), 5) for path in selected]
        for uri in uris:
            del instance.PiTiVi.current.sources[uri]

    def _playButtonClickedCb(self, widget):
        """ Called when a user clicks on the play button """
        # get the selected filesourcefactory
        if self.scrollwin.get_children()[0] == self.treeview:
            model, paths = self.treeview.get_selection().get_selected_rows()
        else:
            paths = self.iconview.get_selected_items()
        if len(paths) < 1:
            return
        factory = self.storemodel.get_value(self.storemodel.get_iter(paths[0]), 4)
        gst.debug("Let's play %s" % factory.name)
        instance.PiTiVi.playground.playTemporaryFilesourcefactory(factory)

    def _listViewButtonToggledCb(self, button):
        if button.get_active():
            self.useTreeView()
            self.iconviewbutton.set_active(False)

    def _iconViewButtonToggledCb(self, button):
        if button.get_active():
            self.useIconView()
            self.listviewbutton.set_active(False)


    def _treeViewButtonPressEventCb(self, treeview, event):
        if event.button == 3:
            self.popup.popup(None, None, None, event.button, event.time)

    def _iconViewButtonPressEventCb(self, treeview, event):
        if event.button == 3:
            self.popup.popup(None, None, None, event.button, event.time)

    def _newProjectCb(self, pitivi, project):
        # clear the storemodel
        self.storemodel.clear()

        # synchronize the storemodel with the new project's sourcelist
        for uri, factory in project.sources:
            if factory:
                length = beautify_length(factory.length)
                if factory.thumbnail:
                    thumbnail = gtk.gdk.pixbuf_new_from_file(factory.thumbnail)
                    desiredheight = 128 * thumbnail.get_height() / thumbnail.get_width()
                    thumbnail = thumbnail.scale_simple(128, desiredheight, gtk.gdk.INTERP_BILINEAR)
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
                self.storemodel.append([thumbnail, name, desc, length, factory, factory.name])
        
        instance.PiTiVi.current.sources.connect("file_added", self._fileAddedCb)
        instance.PiTiVi.current.sources.connect("file_removed", self._fileRemovedCb)


    ## Drag and Drop

    def _dndDataReceivedCb(self, widget, context, x, y, selection, targetType,
                           time):
        gst.debug("targetType:%d, selection.data:%r" % (targetType, selection.data))
        if targetType == dnd.TYPE_URI_LIST:
            filenames = [x.strip('\x00') for x in selection.data.strip().split("\n")]
        elif targetType == dnd.TYPE_TEXT_PLAIN:
            filenames = [selection.data.strip()]
        self.addFiles(filenames)

    def _dndIconBeginCb(self, widget, context):
        gst.info("icon drag_begin")
        items = self.iconview.get_selected_items()
        gst.info("got %d items" % len(items))
        if len(items) < 1:
            context.drag_abort(int(time.time()))
        else:
            if len(items) == 1:
                thumbnail = self.storemodel.get_value(self.storemodel.get_iter(items[0]), 0)
                self.iconview.drag_source_set_icon_pixbuf(thumbnail)
        

    def _dndTreeBeginCb(self, widget, context):
        gst.info("tree drag_begin")
        model, rows = self.treeview.get_selection().get_selected_rows()
        if len(rows) < 1:
            context.drag_abort(int(time.time()))

    def getSelectedItems(self):
        """ returns a list of selected items uri """
        if self.iconviewmode:
            uris = [self.storemodel.get_value(self.storemodel.get_iter(x), 5) for x in self.iconview.get_selected_items()]
        else:
            model, rows = self.treeview.get_selection().get_selected_rows()
            uris = [self.storemodel.get_value(self.storemodel.get_iter(x), 5) for x in rows]
        return uris

    def _dndDataGetCb(self, widget, context, selection, targetType, eventTime):
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
        self.treeview = self.widgets["treeview"]
        self._setUpTreeView()

    def _setUpTreeView(self):
        self.storemodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview.set_model(self.storemodel)

        txtcell = gtk.CellRendererText()
        uricol = gtk.TreeViewColumn("File", txtcell, text=0)
        self.treeview.append_column(uricol)

        txtcell2 = gtk.CellRendererText()
        reasoncol = gtk.TreeViewColumn("Reason", txtcell2, text=1)
        self.treeview.append_column(reasoncol)

    def addFailedFile(self, uri, reason="Unknown reason"):
        """Add the given uri to the list of failed files. You can optionnaly
        give a string identifying the reason why the file failed to be
        discovered
        """
        gst.debug("Uri:%s, reason:%s" % (uri, reason))
        self.storemodel.append([str(uri), str(reason)])

    ## Callbacks from glade

    def _closeCb(self, dialog):
        self.emit('close')

    def _responseCb(self, dialog, response):
        self.emit('response', response)
