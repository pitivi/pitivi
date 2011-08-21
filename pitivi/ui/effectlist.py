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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import gobject
import gtk
import pango
import os
import time

from gettext import gettext as _
from xml.sax.saxutils import escape

import pitivi.ui.dnd as dnd

from pitivi.configure import get_pixmap_dir

from pitivi.log.loggable import Loggable
from pitivi.effects import AUDIO_EFFECT, VIDEO_EFFECT
from pitivi.ui.common import SPACING
from pitivi.settings import GlobalSettings

SHOW_TREEVIEW = 1
SHOW_ICONVIEW = 2

HIDDEN_EFFECTS = ["frei0r-filter-scale0tilt"]

GlobalSettings.addConfigSection('effect-library')
GlobalSettings.addConfigOption('lastEffectView',
    section='effect-library',
    key='last-effect-view',
    type_=int,
    default=SHOW_ICONVIEW)

(COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_EFFECT_TYPE,
 COL_EFFECT_CATEGORIES,
 COL_FACTORY,
 COL_ELEMENT_NAME,
 COL_ICON) = range(7)

INVISIBLE = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir(),
    "invisible.png"))


class EffectList(gtk.VBox, Loggable):
    """ Widget for listing effects """

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self.settings = instance.settings

        self._dragButton = None
        self._dragStarted = False
        self._dragSelection = False
        self._dragX = 0
        self._dragY = 0

        #Tooltip handling
        self._current_effect_name = None
        self._current_tooltip_icon = None

        #Searchbox and combobox
        hfilters = gtk.HBox()
        hfilters.set_spacing(SPACING)
        hfilters.set_border_width(3)  # Prevents being flush against the notebook
        self.effectType = gtk.combo_box_new_text()
        self.effectType.append_text(_("Video effects"))
        self.effectType.append_text(_("Audio effects"))
        self.effectCategory = gtk.combo_box_new_text()
        self.effectType.set_active(VIDEO_EFFECT)

        hfilters.pack_start(self.effectType, expand=True)
        hfilters.pack_end(self.effectCategory, expand=True)

        hsearch = gtk.HBox()
        hsearch.set_spacing(SPACING)
        hsearch.set_border_width(3)  # Prevents being flush against the notebook
        searchStr = gtk.Label(_("Search:"))
        self.searchEntry = gtk.Entry()
        self.searchEntry.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY, "gtk-clear")
        hsearch.pack_start(searchStr, expand=False)
        hsearch.pack_end(self.searchEntry, expand=True)

        # Store
        self.storemodel = gtk.ListStore(str, str, int, object, object, str, gtk.gdk.Pixbuf)

        # Scrolled Windows
        self.treeview_scrollwin = gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.iconview_scrollwin = gtk.ScrolledWindow()
        self.iconview_scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.iconview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        # TreeView
        # Displays name, description
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_property("has_tooltip", True)
        self.treeview.set_property("headers-clickable", False)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_SINGLE)

        namecol = gtk.TreeViewColumn(_("Name"))
        namecol.set_sort_column_id(COL_NAME_TEXT)
        self.treeview.append_column(namecol)
        namecol.set_spacing(SPACING)
        namecol.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        namecol.set_fixed_width(150)
        namecell = gtk.CellRendererText()
        namecell.props.xpad = 6
        namecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", COL_NAME_TEXT)

        desccol = gtk.TreeViewColumn(_("Description"))
        desccol.set_sort_column_id(COL_DESC_TEXT)
        self.treeview.append_column(desccol)
        desccol.set_expand(True)
        desccol.set_spacing(SPACING)
        desccol.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        desccol.set_min_width(150)
        desccell = gtk.CellRendererText()
        desccell.props.xpad = 6
        desccell.set_property("ellipsize", pango.ELLIPSIZE_END)
        desccol.pack_start(desccell)
        desccol.add_attribute(desccell, "text", COL_DESC_TEXT)

        self.iconview = gtk.IconView(self.storemodel)
        self.iconview.set_pixbuf_column(COL_ICON)
        self.iconview.set_text_column(COL_NAME_TEXT)
        self.iconview.set_item_width(102)
        self.iconview_scrollwin.add(self.iconview)
        self.iconview.set_property("has_tooltip", True)

        self.effectType.connect("changed", self._effectTypeChangedCb)

        self.effectCategory.connect("changed", self._effectCategoryChangedCb)

        self.searchEntry.connect("changed", self.searchEntryChangedCb)
        self.searchEntry.connect("button-press-event", self.searchEntryActivateCb)
        self.searchEntry.connect("focus-out-event", self.searchEntryDesactvateCb)
        self.searchEntry.connect("icon-press", self.searchEntryIconClickedCb)

        self.treeview.connect("button-press-event", self._buttonPressEventCb)
        self.treeview.connect("select-cursor-row", self._enterPressEventCb)
        self.treeview.connect("motion-notify-event", self._motionNotifyEventCb)
        self.treeview.connect("query-tooltip", self._queryTooltipCb)
        self.treeview.connect("button-release-event", self._buttonReleaseCb)
        self.treeview.drag_source_set(0, [], gtk.gdk.ACTION_COPY)
        self.treeview.connect("drag_begin", self._dndDragBeginCb)
        self.treeview.connect("drag_data_get", self._dndDataGetCb)

        self.iconview.connect("button-press-event", self._buttonPressEventCb)
        self.iconview.connect("activate-cursor-item", self._enterPressEventCb)
        self.iconview.connect("query-tooltip", self._queryTooltipCb)
        self.iconview.drag_source_set(0, [], gtk.gdk.ACTION_COPY)
        self.iconview.connect("motion-notify-event", self._motionNotifyEventCb)
        self.iconview.connect("button-release-event", self._buttonReleaseCb)
        self.iconview.connect("drag_begin", self._dndDragBeginCb)
        self.iconview.connect("drag_data_get", self._dndDataGetCb)
        # Delay the loading of the available effects so the application
        # starts faster.
        gobject.idle_add(self._loadAvailableEffectsCb)

        self.pack_start(hfilters, expand=False)
        self.pack_start(hsearch, expand=False)
        self.pack_end(self.treeview_scrollwin, expand=True)
        self.pack_end(self.iconview_scrollwin, expand=True)

        #create the filterModel
        self.modelFilter = self.storemodel.filter_new()
        self.modelFilter.set_visible_func(self._setRowVisible, data=None)
        self.treeview.set_model(self.modelFilter)
        self.iconview.set_model(self.modelFilter)

        self._addMenuItems(uiman)
        self.show_categories(VIDEO_EFFECT)

        hfilters.show_all()
        hsearch.show_all()

    def _loadAvailableEffectsCb(self):
        self._addFactories(self.app.effects.getAllVideoEffects(), VIDEO_EFFECT)
        self._addFactories(self.app.effects.getAllAudioEffects(), AUDIO_EFFECT)
        return False

    def _addMenuItems(self, uiman):
        view_menu_item = uiman.get_widget('/MainMenuBar/View')
        view_menu = view_menu_item.get_submenu()
        seperator = gtk.SeparatorMenuItem()
        self.treeview_menuitem = gtk.RadioMenuItem(None,
                _("Show Video Effects as a List"))
        self.iconview_menuitem = gtk.RadioMenuItem(self.treeview_menuitem,
                _("Show Video Effects as Icons"))

        if self.settings.lastEffectView == SHOW_TREEVIEW:
            self.treeview_menuitem.set_active(True)
            self.iconview_menuitem.set_active(False)
        else:
            self.treeview_menuitem.set_active(False)
            self.iconview_menuitem.set_active(True)

        self.treeview_menuitem.connect("toggled", self._treeViewMenuItemToggledCb)
        view_menu.append(seperator)
        view_menu.append(self.treeview_menuitem)
        view_menu.append(self.iconview_menuitem)
        self.treeview_menuitem.show()
        self.iconview_menuitem.show()
        seperator.show()

        self.effect_view = self.settings.lastEffectView

    def _addFactories(self, elements, effectType):
        for element in elements:
            name = element.get_name()
            if name not in HIDDEN_EFFECTS:
                effect = self.app.effects.getFactoryFromName(name)
                self.storemodel.append([effect.getHumanName(),
                                         effect.getDescription(), effectType,
                                         effect.getCategories(),
                                         effect, name,
                                         self.app.effects.getEffectIcon(name)])
                self.storemodel.set_sort_column_id(COL_NAME_TEXT, gtk.SORT_ASCENDING)

    def show_categories(self, effectType):
        self.effectCategory.get_model().clear()
        self._effect_type_ref = effectType

        if effectType is VIDEO_EFFECT:
            for categorie in self.app.effects.video_categories:
                self.effectCategory.append_text(categorie)
        else:
            for categorie in self.app.effects.audio_categories:
                self.effectCategory.append_text(categorie)

        if self.treeview_menuitem.get_active() == False:
            self.effect_view = SHOW_ICONVIEW
        self._displayEffectView()
        self.effectCategory.set_active(0)

    def _displayEffectView(self):
        self.treeview_scrollwin.hide()
        self.iconview_scrollwin.hide()

        if self.effect_view == SHOW_TREEVIEW or\
                        self._effect_type_ref == AUDIO_EFFECT:
            widget = self.treeview_scrollwin
            self.effect_view = SHOW_TREEVIEW
        else:
            widget = self.iconview_scrollwin

        widget.show_all()

    def _dndDragBeginCb(self, view, context):
        self.info("tree drag_begin")
        if self.effect_view == SHOW_ICONVIEW:
            path = self.iconview.get_selected_items()
        elif self.effect_view == SHOW_TREEVIEW:
            path = self.treeview.get_selection().get_selected_rows()[1]

        if len(path) < 1:
            context.drag_abort(int(time.time()))
        else:
            if self._current_tooltip_icon:
                context.set_icon_pixbuf(self._current_tooltip_icon, 0, 0)

    def _rowUnderMouseSelected(self, view, event):
        result = view.get_path_at_pos(int(event.x), int(event.y))
        if result:
            path = result[0]
            if self.effect_view == SHOW_TREEVIEW or\
                        self._effect_type_ref == AUDIO_EFFECT:
                selection = view.get_selection()
                return selection.path_is_selected(path) and\
                                selection.count_selected_rows() > 0
            elif self.effect_view == SHOW_ICONVIEW:
                selection = view.get_selected_items()
                return view.path_is_selected(path) and len(selection)
        return False

    def _enterPressEventCb(self, view, event=None):
        factory_name = self.getSelectedItems()
        self.app.gui.clipconfig.effect_expander.addEffectToCurrentSelection(factory_name)

    def _buttonPressEventCb(self, view, event):
        chain_up = True

        if event.button == 3:
            chain_up = False
        elif event.type is gtk.gdk._2BUTTON_PRESS:
            factory_name = self.getSelectedItems()
            self.app.gui.clipconfig.effect_expander.addEffectToCurrentSelection(factory_name)
        else:
            chain_up = not self._rowUnderMouseSelected(view, event)

            self._dragStarted = False
            self._dragSelection = False
            self._dragButton = event.button
            self._dragX = int(event.x)
            self._dragY = int(event.y)

        if chain_up and self.effect_view is SHOW_TREEVIEW:
            gtk.TreeView.do_button_press_event(view, event)
        elif chain_up and self.effect_view is SHOW_ICONVIEW:
            gtk.IconView.do_button_press_event(view, event)
        else:
            view.grab_focus()

        return True

    def _iconViewButtonReleaseCb(self, treeview, event):
        if event.button == self._dragButton:
            self._dragButton = None
        return False

    def _treeViewMenuItemToggledCb(self, unused_widget):
        if self.effect_view is SHOW_ICONVIEW:
            show = SHOW_TREEVIEW
        else:
            show = SHOW_ICONVIEW
        self.settings.lastEffectView = show
        self.effect_view = show
        self._displayEffectView()

    def _motionNotifyEventCb(self, view, event):
        chain_up = True

        if not self._dragButton:
            return True

        if self._nothingUnderMouse(view, event):
            return True

        if not event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.SHIFT_MASK):
            chain_up = not self._rowUnderMouseSelected(view, event)

        if view.drag_check_threshold(self._dragX, self._dragY,
            int(event.x), int(event.y)):
            context = view.drag_begin(
                self._getDndTuple(),
                gtk.gdk.ACTION_COPY,
                self._dragButton,
                event)
            self._dragStarted = True

        if self.effect_view is SHOW_TREEVIEW:
            if chain_up:
                gtk.TreeView.do_button_press_event(view, event)
            else:
                view.grab_focus()

        return False

    def _queryTooltipCb(self, view, x, y, keyboard_mode, tooltip):
        context = view.get_tooltip_context(x, y, keyboard_mode)

        if context is None:
            return False

        if self.effect_view is SHOW_TREEVIEW or\
                    self._effect_type_ref == AUDIO_EFFECT:
            view.set_tooltip_row(tooltip, context[1][0])
        elif self.effect_view is SHOW_ICONVIEW and\
                     self._effect_type_ref == VIDEO_EFFECT:
            view.set_tooltip_item(tooltip, context[1][0])
        name = self.modelFilter.get_value(context[2], COL_ELEMENT_NAME)
        if self._current_effect_name != name:
            self._current_effect_name = name
            icon = self.modelFilter.get_value(context[2], COL_ICON)
            self._current_tooltip_icon = icon

        longname = escape(self.modelFilter.get_value(context[2],
                COL_NAME_TEXT).strip())
        description = escape(self.modelFilter.get_value(context[2],
                COL_DESC_TEXT))
        txt = "<b>%s:</b>\n%s" % (longname, description)
        if self.effect_view == SHOW_ICONVIEW:
            tooltip.set_icon(None)
        else:
            tooltip.set_icon(self._current_tooltip_icon)
        tooltip.set_markup(txt)

        return True

    def _buttonReleaseCb(self, treeview, event):
        if event.button == self._dragButton:
            self._dragButton = None
        return False

    def getSelectedItems(self):
        if self.effect_view == SHOW_TREEVIEW or\
                        self._effect_type_ref == AUDIO_EFFECT:
            model, rows = self.treeview.get_selection().get_selected_rows()
            path = self.modelFilter.convert_path_to_child_path(rows[0])
        elif self.effect_view == SHOW_ICONVIEW:
            path = self.iconview.get_selected_items()
            path = self.modelFilter.convert_path_to_child_path(path[0])

        return self.storemodel[path][COL_ELEMENT_NAME]

    def _dndDataGetCb(self, unused_widget, context, selection,
                      targettype, unused_eventtime):
        self.info("data get, type:%d", targettype)
        factory = self.getSelectedItems()
        if len(factory) < 1:
            return

        selection.set(selection.target, 8, factory)
        context.set_icon_pixbuf(INVISIBLE, 0, 0)

    def _effectTypeChangedCb(self, combobox):
        self.modelFilter.refilter()
        self.show_categories(combobox.get_active())

    def _effectCategoryChangedCb(self, combobox):
        self.modelFilter.refilter()

    def searchEntryChangedCb(self, entry):
        self.modelFilter.refilter()

    def searchEntryIconClickedCb(self, entry, unused, unsed1):
        entry.set_text("")

    def searchEntryDesactvateCb(self, entry, event):
        self.app.gui.setActionsSensitive("default", True)

    def searchEntryActivateCb(self, entry, event):
        self.app.gui.setActionsSensitive("default", False)

    def _setRowVisible(self, model, iter, data):
        if self.effectType.get_active() == model.get_value(iter, COL_EFFECT_TYPE):
            if model.get_value(iter, COL_EFFECT_CATEGORIES) is None:
                return False
            if self.effectCategory.get_active_text() in model.get_value(iter, COL_EFFECT_CATEGORIES):
                text = self.searchEntry.get_text().lower()
                return text in model.get_value(iter, COL_DESC_TEXT).lower() or\
                       text in model.get_value(iter, COL_NAME_TEXT).lower()
            else:
                return False
        else:
            return False

    def _nothingUnderMouse(self, view, event):
        return not bool(view.get_path_at_pos(int(event.x), int(event.y)))

    def _getDndTuple(self):
        if self.effectType.get_active() == VIDEO_EFFECT:
            return [dnd.VIDEO_EFFECT_TUPLE, dnd.EFFECT_TUPLE]
        else:
            return [dnd.AUDIO_EFFECT_TUPLE, dnd.EFFECT_TUPLE]
