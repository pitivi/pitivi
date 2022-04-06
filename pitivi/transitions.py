# -*- coding: utf-8 -*-
# Pitivi video editor
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
import os
from gettext import gettext as _
from typing import Optional

from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import Gtk

from pitivi.configure import get_pixmap_dir
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import disconnect_all_by_func
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SPACING


(COL_TRANSITION_ASSET,
 COL_NAME,
 COL_ICON_NAME,
 COL_DESCRIPTION) = list(range(4))

BORDER_LOOP_THRESHOLD = 50000


class TransitionsListWidget(Gtk.Box, Loggable):
    """Widget for configuring the selected transition.

    Attributes:
        app (Pitivi): The app.
        element (GES.VideoTransition): The transition being configured.
    """

    def __init__(self, app):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self.element = None
        self._pixdir = os.path.join(get_pixmap_dir(), "transitions")
        self.set_orientation(Gtk.Orientation.VERTICAL)
        # Whether a child widget has the focus.
        self.container_focused = False

        # Searchbox
        self.searchbar = Gtk.Box()
        self.searchbar.set_orientation(Gtk.Orientation.HORIZONTAL)
        # Prevents being flush against the notebook
        self.searchbar.set_border_width(3)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, "edit-clear-symbolic")
        self.search_entry.set_placeholder_text(_("Search..."))
        self.searchbar.pack_end(self.search_entry, True, True, 0)

        self.props_widgets = Gtk.Grid()
        self.props_widgets.props.margin = PADDING
        self.props_widgets.props.column_spacing = SPACING

        self.border_mode_normal = Gtk.RadioButton(
            group=None, label=_("Normal"))
        self.border_mode_normal.set_active(True)
        self.props_widgets.attach(self.border_mode_normal, 0, 0, 1, 1)

        self.border_mode_loop = Gtk.RadioButton(
            group=self.border_mode_normal, label=_("Loop"))
        self.props_widgets.attach(self.border_mode_loop, 0, 1, 1, 1)

        self.border_scale = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, None)
        self.border_scale.set_draw_value(False)
        self.props_widgets.attach(self.border_scale, 1, 0, 1, 2)

        self.invert_checkbox = Gtk.CheckButton(label=_("Reverse direction"))
        self.invert_checkbox.props.margin_top = SPACING
        self.props_widgets.attach(self.invert_checkbox, 1, 2, 1, 1)

        # Set the default values
        self.__update_border_scale()

        self.infobar = Gtk.InfoBar()
        fix_infobar(self.infobar)
        self.infobar.props.message_type = Gtk.MessageType.OTHER
        txtlabel = Gtk.Label()
        txtlabel.set_line_wrap(True)
        txtlabel.set_text(
            _("Create a transition by overlapping two adjacent clips on the "
              "same layer. Click the transition on the timeline to change "
              "the transition type."))
        self.infobar.get_content_area().add(txtlabel)

        self.storemodel = Gtk.ListStore(GES.Asset, str, str, str)
        # Create the filterModel for searching
        self.model_filter = self.storemodel.filter_new()

        self.iconview_scrollwin = Gtk.ScrolledWindow()
        self.iconview_scrollwin.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        self.iconview = Gtk.IconView(model=self.model_filter)
        cell_renderer = Gtk.CellRendererPixbuf()
        cell_renderer.props.stock_size = Gtk.IconSize.DIALOG
        self.iconview.pack_start(cell_renderer, expand=False)
        self.iconview.add_attribute(cell_renderer, "icon-name", COL_ICON_NAME)

        self.iconview.set_item_width(48 + SPACING)
        self.iconview.set_property("has_tooltip", True)

        self.iconview_scrollwin.add(self.iconview)

        self.search_entry.connect("changed", self._search_entry_changed_cb)
        self.search_entry.connect("icon-press", self._search_entry_icon_press_cb)
        self.iconview.connect("query-tooltip", self._iconview_query_tooltip_cb)

        # Speed-up startup by only checking available transitions on idle
        GLib.idle_add(self._load_available_transitions_cb)

        self.pack_start(self.infobar, False, False, 0)
        self.pack_start(self.searchbar, False, False, 0)
        self.pack_start(self.iconview_scrollwin, True, True, 0)
        self.pack_start(self.props_widgets, False, False, 0)

        self.infobar.show_all()
        self.iconview_scrollwin.show_all()
        self.iconview.hide()
        self.props_widgets.set_sensitive(False)
        self.props_widgets.hide()
        self.searchbar.hide()

    def do_set_focus_child(self, child):
        Gtk.Box.do_set_focus_child(self, child)
        action_log = self.app.action_log
        if not action_log:
            # This happens when the user is editing a transition and
            # suddenly closes the window. Don't bother.
            return
        if child:
            if not self.container_focused:
                self.container_focused = True
                action_log.begin("Change transaction", toplevel=True)
        else:
            if self.container_focused:
                self.container_focused = False
                action_log.commit("Change transaction")

    def __connect_ui(self):
        self.iconview.connect("selection-changed", self._transition_selected_cb)
        self.border_scale.connect("value-changed", self._border_scale_cb)
        self.invert_checkbox.connect("toggled", self._invert_checkbox_cb)
        self.border_mode_normal.connect("released", self._border_type_changed_cb)
        self.border_mode_loop.connect("released", self._border_type_changed_cb)
        self.element.connect("notify::border", self.__updated_cb)
        self.element.connect("notify::invert", self.__updated_cb)
        self.element.connect("notify::transition-type", self.__updated_cb)

    def __updated_cb(self, element, unused_param):
        self._update_ui()

    def __disconnect_ui(self):
        self.iconview.disconnect_by_func(self._transition_selected_cb)
        self.border_scale.disconnect_by_func(self._border_scale_cb)
        self.invert_checkbox.disconnect_by_func(self._invert_checkbox_cb)
        self.border_mode_normal.disconnect_by_func(self._border_type_changed_cb)
        self.border_mode_loop.disconnect_by_func(self._border_type_changed_cb)
        disconnect_all_by_func(self.element, self.__updated_cb)

# UI callbacks

    def _transition_selected_cb(self, unused_widget):
        transition_asset = self.get_selected_item()
        if not transition_asset:
            # Nothing to apply. The user clicked between icons.
            return False

        self.debug("New transition type selected: %s", transition_asset.get_id())

        self.element.get_parent().set_asset(transition_asset)
        self._update_ui()

        self.app.write_action("element-set-asset",
                              asset_id=transition_asset.get_id(),
                              element_name=self.element.get_name())
        self.app.project_manager.current_project.pipeline.flush_seek()

        return True

    def _border_scale_cb(self, widget):
        value = widget.get_value()
        self.debug("User changed the border property to %s", value)
        self.element.set_border(int(value))
        self.app.project_manager.current_project.pipeline.flush_seek()

    def _invert_checkbox_cb(self, widget):
        value = widget.get_active()
        self.debug("User changed the invert property to %s", value)
        self.element.set_inverted(value)
        self.app.project_manager.current_project.pipeline.flush_seek()

    def _border_type_changed_cb(self, widget):
        self.__update_border_scale(widget == self.border_mode_loop)

    def __update_border_scale(self, loop=False, border=None):
        # The "border" property in gstreamer is unlimited, but if you go over
        # 25 thousand it "loops" the transition instead of smoothing it.
        if border is not None:
            loop = border >= BORDER_LOOP_THRESHOLD
        if loop:
            self.border_scale.set_range(50000, 500000)
            self.border_scale.clear_marks()
            self.border_scale.add_mark(
                50000, Gtk.PositionType.BOTTOM, _("Slow"))
            self.border_scale.add_mark(
                200000, Gtk.PositionType.BOTTOM, _("Fast"))
            self.border_scale.add_mark(
                500000, Gtk.PositionType.BOTTOM, _("Epileptic"))
        else:
            self.border_scale.set_range(0, 25000)
            self.border_scale.clear_marks()
            self.border_scale.add_mark(0, Gtk.PositionType.BOTTOM, _("Sharp"))
            self.border_scale.add_mark(
                25000, Gtk.PositionType.BOTTOM, _("Smooth"))

    def _search_entry_changed_cb(self, entry):
        self.model_filter.refilter()

    def _search_entry_icon_press_cb(self, entry, icon_pos, event):
        entry.set_text("")

# UI methods

    def _load_available_transitions_cb(self):
        """Loads the transitions types and icons into the storemodel."""
        for trans_asset in GES.list_assets(GES.TransitionClip):
            name = trans_asset.get_id()
            icon_name = name if self._get_icon(name) else "dialog-question-symbolic"
            description = trans_asset.get_meta(GES.META_DESCRIPTION)
            self.storemodel.append([trans_asset, name, icon_name, description])

        # Now that the UI is fully ready, enable searching
        self.model_filter.set_visible_func(self._set_row_visible_func, data=None)
        # Alphabetical/name sorting instead of based on the ID number
        self.storemodel.set_sort_column_id(COL_NAME, Gtk.SortType.ASCENDING)

    def activate(self, element):
        """Hides the infobar and shows the transitions UI."""
        if isinstance(element, GES.AudioTransition):
            return
        self.element = element
        self._update_ui()
        self.iconview.show_all()
        self.props_widgets.show_all()
        self.searchbar.show_all()
        self.__connect_ui()
        # We REALLY want the infobar to be hidden as space is really constrained
        # and yet GTK 3.10 seems to be racy in showing/hiding infobars, so
        # this must happen *after* the tab has been made visible/switched to:
        self.infobar.hide()

    def _update_ui(self):
        transition_type = self.element.get_transition_type()
        self.props_widgets.set_sensitive(
            transition_type != GES.VideoStandardTransitionType.CROSSFADE)
        self.__select_transition(transition_type)
        border = self.element.get_border()
        self.__update_border_scale(border=border)
        self.border_scale.set_value(border)
        self.invert_checkbox.set_active(self.element.is_inverted())
        loop = border >= BORDER_LOOP_THRESHOLD
        if loop:
            self.border_mode_loop.activate()
        else:
            self.border_mode_normal.activate()

    def __select_transition(self, transition_type):
        """Selects the specified transition type in the iconview."""
        model = self.iconview.get_model()
        for row in model:
            asset = row[COL_TRANSITION_ASSET]
            if transition_type.value_nick == asset.get_id():
                path = model.get_path(row.iter)
                self.iconview.select_path(path)
                self.iconview.scroll_to_path(path, False, 0, 0)

    def deactivate(self):
        """Shows the infobar and hides the transitions UI."""
        self.__disconnect_ui()
        self.iconview.unselect_all()
        self.iconview.hide()
        self.props_widgets.hide()
        self.searchbar.hide()
        self.infobar.show()

    def _get_icon(self, transition_nick: str) -> Optional[GdkPixbuf.Pixbuf]:
        """Gets an icon pixbuf for the specified transition nickname."""
        try:
            return GdkPixbuf.Pixbuf.new_from_file(
                os.path.join(self._pixdir, transition_nick + ".png"))
        except GLib.Error:
            return None

    def _iconview_query_tooltip_cb(self, view, x, y, keyboard_mode, tooltip):
        is_row, x, y, model, path, iter_ = view.get_tooltip_context(
            x, y, keyboard_mode)
        if not is_row:
            return False

        view.set_tooltip_item(tooltip, path)

        icon_name = model.get_value(iter_, COL_ICON_NAME)
        tooltip.set_icon_from_icon_name(icon_name, Gtk.IconSize.DIALOG)

        longname = model.get_value(iter_, COL_NAME)
        description = model.get_value(iter_, COL_DESCRIPTION)
        markup = "<b>{}:</b>\n{}".format(GLib.markup_escape_text(longname),
                                         GLib.markup_escape_text(description))
        tooltip.set_markup(markup)
        return True

    def get_selected_item(self):
        path = self.iconview.get_selected_items()
        if not path:
            return None
        return self.model_filter[path[0]][COL_TRANSITION_ASSET]

    def _set_row_visible_func(self, model, model_iter, data):
        """Filters the icon view to show only the search results."""
        text = self.search_entry.get_text().lower()
        return text in model.get_value(model_iter, COL_DESCRIPTION).lower() or \
            text in model.get_value(model_iter, COL_NAME).lower()
