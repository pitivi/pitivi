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

import os
import os.path
import time
import string
import gobject
import gtk
import gst
from urllib import unquote
import pitivi.dnd as dnd
from pitivi.configure import get_pixmap_dir

def beautify_length(length):
    sec = length / gst.SECOND
    min = sec / 60
    sec = sec % 60    
    return "%02dm%02ds" % (min, sec)

class SourceFactoriesWidget(gtk.Notebook):
    """
    Widget for the various source factories (files, effects, live,...)
    """

    def __init__(self, pitivi):
        """ initialize """
        gtk.Notebook.__init__(self)
        self.pitivi = pitivi
        self._create_gui()

    def _create_gui(self):
        """ set up the gui """
        self.set_tab_pos(gtk.POS_BOTTOM)
        self.sourcelist = SourceListWidget(self.pitivi)
        self.append_page(self.sourcelist, gtk.Label("Sources"))
        self.audiofxlist = AudioFxListWidget(self.pitivi)
        self.audiofxlist.set_sensitive(False)
        self.append_page(self.audiofxlist, gtk.Label("Audio FX"))
        self.videofxlist = VideoFxListWidget(self.pitivi)
        self.videofxlist.set_sensitive(False)
        self.append_page(self.videofxlist, gtk.Label("Video FX"))
        self.transitionlist = TransitionListWidget(self.pitivi)
        self.transitionlist.set_sensitive(False)
        self.append_page(self.transitionlist, gtk.Label("Transitions"))

gobject.type_register(SourceFactoriesWidget)


class SourceListWidget(gtk.VBox):
    """ Widget for listing sources """

    def __init__(self, pitivi):
        gtk.VBox.__init__(self)
        self.pitivi = pitivi

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
        playmenuitem.connect("activate", self.play_button_clicked_cb)
        additem.connect("activate", self.add_button_clicked_cb)
        remitem.connect("activate", self.remove_button_clicked_cb)
        additem.show()
        remitem.show()
        playmenuitem.show()
        self.popup.append(additem)
        self.popup.append(remitem)
        self.popup.append(playmenuitem)

        # TreeView
        # Displays icon, name, type, length
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview.connect("button-press-event", self.treeview_button_press_event_cb)
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
        self.iconview.connect("button-press-event", self.iconview_button_press_event_cb)

        # buttons (list/icon view, add, remove)
        button = gtk.Button(stock=gtk.STOCK_ADD)
        button.connect("clicked", self.add_button_clicked_cb)
        rbut = gtk.Button(stock=gtk.STOCK_REMOVE)
        rbut.connect("clicked", self.remove_button_clicked_cb)
        self.listviewbutton = gtk.ToggleButton("List View")
        self.listviewbutton.connect("toggled", self._listviewbutton_toggled_cb)
        self.iconviewbutton = gtk.ToggleButton("Icon View")
        self.iconviewbutton.connect("toggled", self._iconviewbutton_toggled_cb)        
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
        self.pitivi.current.sources.connect("file_added", self._file_added_cb)
        self.pitivi.current.sources.connect("file_removed", self._file_removed_cb)
        self.pitivi.current.sources.connect("file_is_valid", self._file_is_valid_cb)

        self.pitivi.connect("new-project", self._new_project_cb)

        # default pixbufs
        pixdir = get_pixmap_dir()
        self.filepixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, "pitivi-file.png"))
        self.audiofilepixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, "pitivi-sound.png"))
        self.videofilepixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, "pitivi-video.png"))
        
        # Drag and Drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.DND_URI_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag_data_received", self._dnd_data_received)

        self.iconview.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                      [dnd.DND_URI_TUPLE, dnd.DND_FILESOURCE_TUPLE],
                                      gtk.gdk.ACTION_COPY)
        self.iconview.connect("drag_begin", self._dnd_icon_begin)
        self.iconview.connect("drag_data_get", self._dnd_icon_data_get)
        self.treeview.drag_source_set(gtk.gdk.BUTTON1_MASK,
                                      [dnd.DND_URI_TUPLE, dnd.DND_FILESOURCE_TUPLE],
                                      gtk.gdk.ACTION_COPY)
        self.treeview.connect("drag_begin", self._dnd_tree_begin)
        self.treeview.connect("drag_data_get", self._dnd_tree_data_get)

    def use_treeview(self):
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

    def use_iconview(self):
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

    def _listviewbutton_toggled_cb(self, button):
        if button.get_active():
            self.use_treeview()
            self.iconviewbutton.set_active(False)

    def _iconviewbutton_toggled_cb(self, button):
        if button.get_active():
            self.use_iconview()
            self.listviewbutton.set_active(False)

    def _file_added_cb(self, sourcelist, uri):
        """ a file was added to the sourcelist """
        self.storemodel.append([self.filepixbuf,
                                os.path.basename(unquote(uri)),
                                "Analyzing...", "N/A", None, uri])

    def _file_removed_cb(self, sourcelist, uri):
        """ the given uri was removed from the sourcelist """
        # find the good line in the storemodel and remove it
        piter = self.storemodel.get_iter_first()
        while piter:
            if uri == self.storemodel.get_value(piter, 5):
                self.storemodel.remove(piter)
                break
            piter = self.storemodel.iter_next(piter)

    def _file_is_valid_cb(self, sourcelist, factory):
        """ a uri was found as being a valid media file """
        # update info in storemodel
        # hookup callbacks
        gst.debug("%s is a valid media file" % factory.name)
        factory.connect("notify::is-audio", self._fact_type_cb)
        factory.connect("notify::is-video", self._fact_type_cb)
        factory.connect("notify::length", self._fact_length_cb)
        factory.connect("notify::thumbnail", self._fact_thumbnail_cb)
        factory.connect("notify::audio-info", self._fact_infoupdate_cb)
        factory.connect("notify::video-info", self._fact_infoupdate_cb)
        piter = self.storemodel.get_iter_first()
        while piter:
            if factory.name == self.storemodel.get_value(piter, 5):
                self.storemodel.set(piter, 2, factory.get_pretty_info())
                if factory.is_video:
                    self.storemodel.set(piter, 0, self.videofilepixbuf)
                elif factory.is_audio:
                    self.storemodel.set(piter, 0, self.audiofilepixbuf)
                self.storemodel.set(piter, 4, factory)
                gst.info("added stuff")
                break
            piter = self.storemodel.iter_next(piter)
        gst.info("finished")
        
    def _fact_type_cb(self, factory, property):
        """ type of factory was updated """
        gst.info("type changed")
        piter = self.storemodel.get_iter_first()
        while piter:
            if factory == self.storemodel.get_value(piter, 4):
                self.storemodel.set(piter, 2, factory.get_pretty_info())
                if not factory.thumbnail:
                    if factory.is_video:
                        self.storemodel.set(piter, 0, self.videofilepixbuf)
                    elif factory.is_audio:
                        self.storemodel.set(piter, 0, self.audiofilepixbuf)
                break
            piter = self.storemodel.iter_next(piter)

    def _fact_infoupdate_cb(self, factory, property):
        """ info on the factory was updated """
        piter = self.storemodel.get_iter_first()
        while piter:
            if factory == self.storemodel.get_value(piter, 4):
                self.storemodel.set(piter, 2, factory.get_pretty_info())
                break
            piter = self.storemodel.iter_next(piter)

    def _fact_length_cb(self, factory, property):
        """ length of factory was updated """
        gst.info("length changed")
        piter = self.storemodel.get_iter_first()
        while piter:
            if factory == self.storemodel.get_value(piter, 4):
                self.storemodel.set(piter, 3, beautify_length(factory.length))
                break
            piter = self.storemodel.iter_next(piter)

    def _fact_thumbnail_cb(self, factory, property):
        """ a thumbnail is available """
        gst.info("thumbnail available")
        pixbuf = gtk.gdk.pixbuf_new_from_file(factory.thumbnail)
        desiredheight = 128 * pixbuf.get_height() / pixbuf.get_width()
        pixbuf = pixbuf.scale_simple(128, desiredheight, gtk.gdk.INTERP_BILINEAR)
        piter = self.storemodel.get_iter_first()
        while piter:
            if factory == self.storemodel.get_value(piter, 4):
                self.storemodel.set(piter, 0, pixbuf)
            piter = self.storemodel.iter_next(piter)

    def add_files(self, list):
        """ Add files to the list """
        self.pitivi.current.sources.add_uris(list)
            
    def add_button_clicked_cb(self, widget):
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
            self.add_files(filenames)
        dialog.destroy()

    def remove_button_clicked_cb(self, widget):
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
            del self.pitivi.current.sources[uri]

    def play_button_clicked_cb(self, widget):
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
        self.pitivi.playground.play_temporary_filesourcefactory(factory)

    def treeview_button_press_event_cb(self, treeview, event):
        if event.button == 3:
            self.popup.popup(None, None, None, event.button, event.time)

    def iconview_button_press_event_cb(self, treeview, event):
        if event.button == 3:
            self.popup.popup(None, None, None, event.button, event.time)

    def _new_project_cb(self, pitivi, project):
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
        
        self.pitivi.current.sources.connect("file_added", self._file_added_cb)
        self.pitivi.current.sources.connect("file_removed", self._file_removed_cb)
        self.pitivi.current.sources.connect("file_is_valid", self._file_is_valid_cb)

##     def _dnd_motion_cb(self, widget, context, x, y, timestamp):
##         context.drag_status(gtk.gdk.ACTION_COPY, timestamp)
##         return True

##     def _dnd_drop_cb(self, widget, context, x, y, timestamp):
##         print "drag drop"
##         print '\n'.join([str(t) for t in context.targets])
##         print "\n"
##         context.finish()
##         return True

    def _dnd_data_received(self, widget, context, x, y, selection, targetType,
                           time):
        filenames = [x.strip() for x in selection.data.strip().split("\n")]
        self.add_files(filenames)

    def _dnd_icon_begin(self, widget, context):
        gst.info("icon drag_begin")
        items = self.iconview.get_selected_items()
        gst.info("got %d items" % len(items))
        if len(items) < 1:
            context.drag_abort(int(time.time()))
        else:
            if len(items) == 1:
                thumbnail = self.storemodel.get_value(self.storemodel.get_iter(items[0]), 0)
                self.iconview.drag_source_set_icon_pixbuf(thumbnail)
        

    def _dnd_tree_begin(self, widget, context):
        gst.info("tree drag_begin")
        model, rows = self.treeview.get_selection().get_selected_rows()
        if len(rows) < 1:
            context.drag_abort(int(time.time()))

    def _dnd_icon_data_get(self, widget, context, selection, targetType, eventTime):
        # calls context.drag_abort(time) if not in a valide place
        gst.info("icon list data_get, type: %d" % targetType)
        # get the list of selected uris
        uris = [self.storemodel.get_value(self.storemodel.get_iter(x), 5) for x in self.iconview.get_selected_items()]
        if len(uris) < 1:
            return
        if targetType == dnd.DND_TYPE_PITIVI_FILESOURCE:
            selection.set(selection.target, 8,
                          uris[0])
        elif targetType == dnd.DND_TYPE_URI_LIST:
            selection.set(selection.target, 8,
                          string.join(uris, "\n"))

    def _dnd_tree_data_get(self, widget, context, selection, targetType, eventTime):
        # calls context.drag_abort(time) if not in a valide place
        gst.info("tree list data_get, type: %d" % targetType)
        # get the list of selected uris
        model, rows = self.treeview.get_selection().get_selected_rows()
        uris = [self.storemodel.get_value(self.storemodel.get_iter(x), 5) for x in rows]
        if len(uris) < 1:
            return
        if targetType == dnd.DND_TYPE_PITIVI_FILESOURCE:
            selection.set(selection.target, 8,
                          uris[0])
        elif targetType == dnd.DND_TYPE_URI_LIST:
            selection.set(selection.target, 8,
                          string.join(uris, "\n"))

gobject.type_register(SourceListWidget)

class AudioFxListWidget(gtk.VBox):
    """ Widget for listing audio effects """

    def __init__(self, pitivi):
        self.pitivi = pitivi
        gtk.VBox.__init__(self)
        self.iconview = gtk.IconView()
        self.treeview = gtk.TreeView()
        self.pack_start(self.iconview)

gobject.type_register(AudioFxListWidget)

class VideoFxListWidget(gtk.VBox):
    """ Widget for listing video effects """

    def __init__(self, pitivi):
        self.pitivi = pitivi
        gtk.VBox.__init__(self)
        self.iconview = gtk.IconView()
        self.treeview = gtk.TreeView()
        self.pack_start(self.iconview)

gobject.type_register(VideoFxListWidget)

class TransitionListWidget(gtk.VBox):
    """ Widget for listing transitions """

    def __init__(self, pitivi):
        self.pitivi = pitivi
        gtk.VBox.__init__(self)
        self.iconview = gtk.IconView()
        self.treeview = gtk.TreeView()
        self.pack_start(self.iconview)

gobject.type_register(TransitionListWidget)
