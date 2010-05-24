# PiTiVi , Non-linear video editor
#
#       ui/effectlist.py
#
# Copyright (c) 2010, Thibault Saunier <tsaunier@gnome.org>
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
from pitivi.factories.operation import EffectFactory

from pitivi.settings import GlobalSettings
from pitivi.utils import beautify_length

from xml.sax.saxutils import escape

from pitivi.log.loggable import Loggable

(COL_ICON,
 COL_ICON_LARGE,
 COL_INFOTEXT,
 COL_FACTORY,
 COL_SEARCH_TEXT,
 COL_SHORT_TEXT) = range(6)

class EffectList(gtk.VBox, Loggable):
    """ Widget for listing effects """

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self.settings = instance.settings

        #TODO check that
        self._dragButton = None
        self._dragStarted = False
        self._dragSelection = False
        self._dragX = 0
        self._dragY = 0
        self._ignoreRelease = False

        # Store
        # icon, icon, infotext, objectfactory
        self.storemodel = gtk.ListStore(gtk.gdk.Pixbuf, gtk.gdk.Pixbuf,
                                        str, object, str, str)

        # Scrolled Windows
        self.treeview_scrollwin = gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        # TreeView
        # Displays icon, long_name
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_headers_visible(False)
        self.treeview.set_property("search_column", COL_SEARCH_TEXT)
        self.treeview.set_property("has_tooltip", True)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_SINGLE)

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

        self.treeview.connect("button-press-event",
                              self._treeViewButtonPressEventCb)
        self.treeview.connect("motion-notify-event",
                              self._treeViewMotionNotifyEventCb)
        self.treeview.connect("query-tooltip",
                              self._treeViewQueryTooltipCb)
        self.treeview.connect("button-release-event",
            self._treeViewButtonReleaseCb)
        self.treeview.connect("drag_begin",
                              self._dndDragBeginCb)

        self.pack_start(self.treeview_scrollwin)
        #Get all available effects
        self._addFactories(self._getEffects())
        self.treeview_scrollwin.show_all()

    def _addFactories(self, effects):
        #TODO find a way to associate an icon to each effect
        thumbnail_file = os.path.join (os.getcwd(), "icons", "24x24", "pitivi.png")
        pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnail_file)

        for effect in effects:
            #TODO Check how it would look the best
            visualname = ("<b>Name: </b>" + escape(unquote(effect.get_longname())) + "\n" +
                    "<b>Description: </b>"+ effect.get_description())

            factory = self._getFactoryFromEffect(effect)
            self.storemodel.append ([pixbuf, pixbuf, visualname,
                                    factory, effect.get_description(),
                                    factory.name])

    def _dndDragBeginCb(self, view, context):
        self.info("tree drag_begin")
        path = self.treeview.get_selection().get_selected_rows()[1]

        if len(path) < 1:
            context.drag_abort(int(time.time()))
        else:
            row = self.storemodel[path[0]]
            context.set_icon_pixbuf(row[COL_ICON], 0, 0)

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

    def _treeViewButtonPressEventCb(self, treeview, event):
        chain_up = True

        if event.button == 3:
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

    def _treeViewButtonReleaseCb(self, treeview, event):
        if event.button == self._dragButton:
            self._dragButton = None
            #   TODO: What does it do?
            #   if (not self._ignoreRelease) and (not self._dragStarted):
            #    treeview.get_selection().unselect_all()
            #    result = treeview.get_path_at_pos(int(event.x), int(event.y))
            #    if result:
            #        path = result[0]
            #        treeview.get_selection().select_path(path)
        return False

    def _treeViewMotionNotifyEventCb(self, treeview, event):
        chain_up = True

        if not self._dragButton:
            return True

        if self._nothingUnderMouse(treeview, event):
            return True

        if not event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK):
            chain_up = not self._rowUnderMouseSelected(treeview, event)

        if treeview.drag_check_threshold(self._dragX, self._dragY,
            int(event.x), int(event.y)):
            context = treeview.drag_begin(
                self._getDndTuple(),
                gtk.gdk.ACTION_COPY,
                self._dragButton,
                event)
            self._dragStarted = True

        if chain_up:
            gtk.TreeView.do_button_press_event(treeview, event)
        else:
            treeview.grab_focus()

        self._ignoreRelease = chain_up

        return False

    def _treeViewQueryTooltipCb(self, treeview, x, y, keyboard_mode, tooltip):
        pos = treeview.get_path_at_pos(x,y)[0]
        treeview.set_tooltip_row (tooltip, pos)
        tooltip.set_text(treeview.get_model()[pos[0]][4])
        return True

    def _insertEndCb(self, unused_action):
        print "T34T"

    def _nothingUnderMouse(self, view, event):
        return not bool(view.get_path_at_pos(int(event.x), int(event.y)))

    def _getEffects():
        raise NotImplementedError()

    def _getFactoryFromEffect(self, effect):
        return EffectFactory(effect.get_name())

    def _getDndTuple(self):
        raise NotImplementedError()

class VideoEffectList (EffectList):

    def __init__(self, instance, uiman):
        EffectList.__init__(self,instance, uiman)

    def _getEffects(self):
        return self.app.effects.simple_video
    def _getDndTuple(self):
        return  [dnd.VIDEO_EFFECT_TUPLE, dnd.EFFECT_TUPLE]

class AudioEffectList (EffectList):

    def __init__(self, instance, uiman):
        EffectList.__init__(self,instance, uiman)

    def _getEffects(self):
        return self.app.effects.simple_audio

    def _getDndTuple(self):
        return  [dnd.AUDIO_EFFECT_TUPLE, dnd.EFFECT_TUPLE]

gobject.type_register(EffectList)
