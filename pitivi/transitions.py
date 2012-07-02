# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
#
#       transitions.py
#
# Copyright (c) 2012, Jean-François Fortin Tam <nekohayo@gmail.com>
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

import ges
import glib
import gtk
import os
import gobject

from gettext import gettext as _

from pitivi.configure import get_pixmap_dir
from pitivi.utils.loggable import Loggable
from pitivi.utils.signal import Signallable
from pitivi.utils.ui import SPACING, PADDING

(COL_TRANSITION_ID,
 COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_ICON) = range(4)


class TransitionsListWidget(Signallable, gtk.VBox, Loggable):

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)
        Signallable.__init__(self)

        self.app = instance
        self.element = None
        self._pixdir = os.path.join(get_pixmap_dir(), "transitions")
        icon_theme = gtk.icon_theme_get_default()
        self._question_icon = icon_theme.load_icon("dialog-question", 48, 0)

        #Tooltip handling
        self._current_transition_name = None
        self._current_tooltip_icon = None

        #Searchbox
        self.searchbar = gtk.HBox()
        self.searchbar.set_spacing(SPACING)
        self.searchbar.set_border_width(3)  # Prevents being flush against the notebook
        searchStr = gtk.Label(_("Search:"))
        self.searchEntry = gtk.Entry()
        self.searchEntry.set_icon_from_stock(gtk.ENTRY_ICON_SECONDARY, "gtk-clear")
        self.searchbar.pack_start(searchStr, expand=False)
        self.searchbar.pack_end(self.searchEntry, expand=True)

        self.props_widgets = gtk.VBox()
        borderTable = gtk.Table(rows=2, columns=3)

        self.border_mode_normal = gtk.RadioButton(group=None, label=_("Normal"))
        self.border_mode_loop = gtk.RadioButton(group=self.border_mode_normal, label=_("Loop"))
        self.border_mode_normal.set_active(True)
        self.borderScale = gtk.HScale()
        self.borderScale.set_draw_value(False)

        borderTable.attach(self.border_mode_normal, 0, 1, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL)
        borderTable.attach(self.border_mode_loop, 1, 2, 0, 1, xoptions=gtk.FILL, yoptions=gtk.FILL)
        # The ypadding is a hack to make the slider widget align with the radiobuttons.
        borderTable.attach(self.borderScale, 2, 3, 0, 2, ypadding=SPACING * 2)

        self.invert_checkbox = gtk.CheckButton(_("Reverse direction"))
        self.invert_checkbox.set_border_width(SPACING)

        self.props_widgets.add(borderTable)
        self.props_widgets.add(self.invert_checkbox)

        # Set the default values
        self._borderTypeChangedCb()

        self.infobar = gtk.InfoBar()
        txtlabel = gtk.Label()
        txtlabel.set_padding(PADDING, PADDING)
        txtlabel.set_line_wrap(True)
        txtlabel.set_text(
            _("Create a transition by overlapping two adjacent clips on the "
                "same layer. Click the transition on the timeline to change "
                "the transition type."))
        self.infobar.add(txtlabel)
        self.infobar.show_all()

        self.storemodel = gtk.ListStore(str, str, str, gtk.gdk.Pixbuf)

        self.iconview_scrollwin = gtk.ScrolledWindow()
        self.iconview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        # FIXME: the "never" horizontal scroll policy in GTK2 messes up iconview
        # Re-enable this when we switch to GTK3
        # See also http://python.6.n6.nabble.com/Cannot-shrink-width-of-scrolled-textview-tp1945060.html
        #self.iconview_scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        self.iconview = gtk.IconView(self.storemodel)
        self.iconview.set_pixbuf_column(COL_ICON)
        # We don't show text because we have a searchbar and the names are ugly
        #self.iconview.set_text_column(COL_NAME_TEXT)
        self.iconview.set_item_width(48 + 10)
        self.iconview_scrollwin.add(self.iconview)
        self.iconview.set_property("has_tooltip", True)

        self.searchEntry.connect("changed", self._searchEntryChangedCb)
        self.searchEntry.connect("focus-in-event", self._searchEntryActivateCb)
        self.searchEntry.connect("focus-out-event", self._searchEntryDeactivateCb)
        self.searchEntry.connect("icon-press", self._searchEntryIconClickedCb)
        self.iconview.connect("selection-changed", self._transitionSelectedCb)
        self.iconview.connect("query-tooltip", self._queryTooltipCb)
        self.borderScale.connect("value-changed", self._borderScaleCb)
        self.invert_checkbox.connect("toggled", self._invertCheckboxCb)
        self.border_mode_normal.connect("released", self._borderTypeChangedCb)
        self.border_mode_loop.connect("released", self._borderTypeChangedCb)

        # Speed-up startup by only checking available transitions on idle
        gobject.idle_add(self._loadAvailableTransitionsCb)

        self.pack_start(self.infobar, expand=False)
        self.pack_start(self.searchbar, expand=False)
        self.pack_start(self.iconview_scrollwin, expand=True)
        self.pack_start(self.props_widgets, expand=False)

        # Create the filterModel for searching
        self.modelFilter = self.storemodel.filter_new()
        self.iconview.set_model(self.modelFilter)

        self.infobar.show()
        self.iconview_scrollwin.show_all()
        self.iconview.set_sensitive(False)
        self.props_widgets.set_sensitive(False)
        self.props_widgets.show_all()
        self.searchbar.hide_all()

# UI callbacks

    def _transitionSelectedCb(self, event):
        selected_item = self.getSelectedItem()
        if not selected_item:
        # The user clicked between icons
            return False
        transition_id = int(selected_item)
        transition = self.available_transitions.get(transition_id)
        self.debug("New transition type selected: %s" % transition)
        if transition.value_nick == "crossfade":
            self.props_widgets.set_sensitive(False)
        else:
            self.props_widgets.set_sensitive(True)

        # Avoid deadlocks by seeking to 0 before changing type
        position = self.app.current.pipeline.getPosition()
        self.app.current.pipeline.simple_seek(0)

        self.element.set_transition_type(transition)

        # Seek back into the previous position, refreshing the preview
        self.app.current.pipeline.simple_seek(position)

        return True

    def _borderScaleCb(self, range_changed):
        value = range_changed.get_value()
        self.debug("User changed the border property to %s" % value)
        self.element.set_border(int(value))
        # FIXME: Currently creates deadlocks, reactivate it when
        # fixed
        #self.app.current.seeker.flush(True)

    def _invertCheckboxCb(self, widget):
        value = widget.get_active()
        self.debug("User changed the invert property to %s" % value)
        self.element.set_inverted(value)
        self.app.current.seeker.flush()

    def _borderTypeChangedCb(self, widget=None):
        """
        The "border" property in gstreamer is unlimited, but if you go over
        25 thousand it "loops" the transition instead of smoothing it.
        """
        if widget == self.border_mode_loop:
            self.borderScale.set_range(50000, 500000)
            self.borderScale.clear_marks()
            self.borderScale.add_mark(50000, gtk.POS_BOTTOM, _("Slow"))
            self.borderScale.add_mark(200000, gtk.POS_BOTTOM, _("Fast"))
            self.borderScale.add_mark(500000, gtk.POS_BOTTOM, _("Epileptic"))
        else:
            self.borderScale.set_range(0, 25000)
            self.borderScale.clear_marks()
            self.borderScale.add_mark(0, gtk.POS_BOTTOM, _("Sharp"))
            self.borderScale.add_mark(25000, gtk.POS_BOTTOM, _("Smooth"))

    def _searchEntryChangedCb(self, entry):
        self.modelFilter.refilter()

    def _searchEntryIconClickedCb(self, entry, unused, unsed1):
        entry.set_text("")

    def _searchEntryDeactivateCb(self, entry, event):
        self.app.gui.setActionsSensitive(True)

    def _searchEntryActivateCb(self, entry, event):
        self.app.gui.setActionsSensitive(False)

# GES callbacks

    def _transitionTypeChangedCb(self, element, unused_prop):
        transition = element.get_transition_type()
        try:
            self.iconview.disconnect_by_func(self._transitionSelectedCb)
        except TypeError:
            pass
        finally:
            self.selectTransition(transition)
            self.iconview.connect("button-release-event", self._transitionSelectedCb)

    def _borderChangedCb(self, element, unused_prop):
        """
        The "border" transition property changed in the backend. Update the UI.
        """
        value = element.get_border()
        try:
            self.borderScale.disconnect_by_func(self._borderScaleCb)
        except TypeError:
            pass
        finally:
            self.borderScale.set_value(float(value))
            self.borderScale.connect("value-changed", self._borderScaleCb)

    def _invertChangedCb(self, element, unused_prop):
        """
        The "invert" transition property changed in the backend. Update the UI.
        """
        value = element.is_inverted()
        try:
            self.invert_checkbox.disconnect_by_func(self._invertCheckboxCb)
        except TypeError:
            pass
        finally:
            self.invert_checkbox.set_active(value)
            self.invert_checkbox.connect("toggled", self._invertCheckboxCb)

# UI methods

    def _loadAvailableTransitionsCb(self):
        """
        Get the list of transitions from GES and load the associated thumbnails.
        """
        # TODO: rewrite this method when GESRegistry exists
        self.available_transitions = {}
        # GES currently has transitions IDs up to 512
        # Number 0 means "no transition", so we might just as well skip it.
        for i in range(1, 513):
            try:
                transition = ges.VideoStandardTransitionType(i)
            except ValueError:
                # We hit a gap in the enum
                pass
            else:
                self.available_transitions[transition.numerator] = transition
                self.storemodel.append([str(transition.numerator),
                                        str(transition.value_nick),
                                        str(transition.value_name),
                                        self._getIcon(transition.value_nick)])

        # Now that the UI is fully ready, enable searching
        self.modelFilter.set_visible_func(self._setRowVisible, data=None)
        # Alphabetical/name sorting instead of based on the ID number
        #self.storemodel.set_sort_column_id(COL_NAME_TEXT, gtk.SORT_ASCENDING)

    def activate(self, element):
        """
        Hide the infobar and make the transitions UI sensitive.
        """
        self.element = element
        self.element.connect("notify::border", self._borderChangedCb)
        self.element.connect("notify::invert", self._invertChangedCb)
        self.element.connect("notify::type", self._transitionTypeChangedCb)
        transition = element.get_transition_type()
        if transition.value_nick == "crossfade":
            self.props_widgets.set_sensitive(False)
        else:
            self.props_widgets.set_sensitive(True)
        self.iconview.set_sensitive(True)
        self.infobar.hide()
        self.searchbar.show_all()
        self.selectTransition(transition)
        self.app.gui.switchContextTab("transitions")

    def selectTransition(self, transition):
        """
        For a given transition type, select it in the iconview if available.
        """
        model = self.iconview.get_model()
        for row in model:
            if int(transition.numerator) == int(row[COL_TRANSITION_ID]):
                path = model.get_path(row.iter)
                self.iconview.select_path(path)
                self.iconview.scroll_to_path(path, False, 0, 0)

    def deactivate(self):
        """
        Show the infobar and make the transitions UI insensitive.
        """
        try:
            self.element.disconnect_by_func(self._borderChangedCb)
            self.element.disconnect_by_func(self._invertChangedCb)
            self.element.disconnect_by_func(self._transitionTypeChangedCb)
        except TypeError:
            pass
        except AttributeError:
            # This happens when selecting a normal track object before any
            # transition object has been created. Normal track objects don't
            # have these signals, so we just ignore them. Anyway, we just want
            # to deactivate the UI now.
            pass
        self.iconview.unselect_all()
        self.iconview.set_sensitive(False)
        self.props_widgets.set_sensitive(False)
        self.infobar.show()
        self.searchbar.hide_all()

    def _getIcon(self, transition_nick):
        """
        If available, return an icon pixbuf for a given transition nickname.
        """
        name = transition_nick + ".png"
        icon = None
        try:
            icon = gtk.gdk.pixbuf_new_from_file(os.path.join(self._pixdir, name))
        except:
            icon = self._question_icon
        return icon

    def _queryTooltipCb(self, view, x, y, keyboard_mode, tooltip):
        context = view.get_tooltip_context(x, y, keyboard_mode)
        if context is None:
            return False

        view.set_tooltip_item(tooltip, context[1][0])

        name = self.modelFilter.get_value(context[2], COL_TRANSITION_ID)
        if self._current_transition_name != name:
            self._current_transition_name = name
            icon = self.modelFilter.get_value(context[2], COL_ICON)
            self._current_tooltip_icon = icon

        longname = self.modelFilter.get_value(context[2], COL_NAME_TEXT).strip()
        description = self.modelFilter.get_value(context[2], COL_DESC_TEXT)
        txt = "<b>%s:</b>\n%s" % (glib.markup_escape_text(longname),
                                  glib.markup_escape_text(description),)
        tooltip.set_markup(txt)
        return True

    def getSelectedItem(self):
        path = self.iconview.get_selected_items()
        if path == []:
            return None
        return self.modelFilter[path[0]][COL_TRANSITION_ID]

    def _setRowVisible(self, model, iter, data):
        """
        Filters the icon view depending on the search results
        """
        text = self.searchEntry.get_text().lower()
        return text in model.get_value(iter, COL_DESC_TEXT).lower() or\
            text in model.get_value(iter, COL_NAME_TEXT).lower()
        return False
