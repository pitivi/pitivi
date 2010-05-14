# PiTiVi , Non-linear video editor
#
#       ui/effectlist.py
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

from pitivi.factories.operation import VideoEffectFactory, AudioEffectFactory

from pitivi.settings import GlobalSettings
from pitivi.utils import beautify_length

from xml.sax.saxutils import escape

from pitivi.log.loggable import Loggable

(COL_ICON,
 COL_ICON_LARGE,
 COL_INFOTEXT,
 COL_FACTORY,
 COL_URI,
 COL_LENGTH,
 COL_SEARCH_TEXT,
 COL_SHORT_TEXT) = range(8)

INVISIBLE = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir(), 
                                                      "invisible.png"))

class EffectList(gtk.VBox, Loggable):
    """ Widget for listing effects """

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self.settings = instance.settings

        #TODO check that
        self._dragButton = False
        self.tooltip = None
        
        # Store
        # icon, icon, infotext, objectfactory
        self.storemodel = gtk.ListStore(gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, str, object, 
                                        str, str)

        # Scrolled Windows
        self.treeview_scrollwin = gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        # TreeView
        # Displays icon, name, type
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_headers_visible(False)
        self.treeview.set_property("search_column", COL_SEARCH_TEXT)
        self.treeview.set_property("has_tooltip", True)
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

        self.treeview.connect("motion-notify-event",
            self._treeViewMotionNotifyEventCb)
        self.treeview.connect("query-tooltip",
            self._treeViewQueryTooltipCb)

        self.pack_start(self.treeview_scrollwin)
        #Get all available effects
        self._addFactories(self._getEffects())
        self.treeview_scrollwin.show_all()

    def _addFactories(self, effects):
        #TODO find a way to associate an icon to each effect
        thumbnail_file = os.path.join (os.getcwd(), "icons", "24x24", "pitivi.png")

        pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnail_file)
        for effect in effects:
            #Check how it would look the best
            visualname = ("<b>Name: </b>" + escape(unquote(effect.get_longname())) + "\n" +
                    "<b>Description: </b>"+ effect.get_description())

            factory = self._getFactoryFromEffect(effect)
            self.storemodel.append ([pixbuf, pixbuf, visualname,
                                    factory, effect.get_description(), "test"])

    def _treeViewMotionNotifyEventCb(self, treeview, event):
        pass

    def _treeViewQueryTooltipCb(self, treeview, x, y, keyboard_mode, tooltip):
        pos = treeview.get_path_at_pos(x,y)[0][0]
        self.tooltip = tooltip 
        tooltip.set_text(treeview.get_model()[pos][4])
        return True


    def _getEffects():
        pass
    
    def _getFactoryFromEffect(self, effect):
        pass

class VideoEffectList (EffectList):

    def __init__(self, instance, uiman):
        EffectList.__init__(self,instance, uiman)

    def _getEffects(self):
        return self.app.effects.simple_video

    def _getFactoryFromEffect(self, effect):
        return VideoEffectFactory(effect.get_name())

class AudioEffectList (EffectList):

    def __init__(self, instance, uiman):
        EffectList.__init__(self,instance, uiman)

    def _getEffects(self):
        return self.app.effects.simple_audio

    def _getFactoryFromEffect(self, effect):
        return AudioEffectFactory(effect.get_name())
        
gobject.type_register(EffectList)
