# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Pratyush Tiwari <pratyushtiwarimj@gmail.com>
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

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pitivi.configure import get_pixmap_dir

INTERACTIVE_INTRO_CSS = """
@keyframes intro-highlighted {
  from { box-shadow: 0px 0px 10px @theme_selected_bg_color, inset 0px 0px 4px  @theme_selected_bg_color; }
  to   { box-shadow: 0px 0px 4px  @theme_selected_bg_color, inset 0px 0px 10px @theme_selected_bg_color; }
}

.intro-highlighted {
  animation: intro-highlighted 1.5s infinite alternate;
}

#popover {
  font-size: 18pt;
  font-weight: bold;
  margin: 10px;
  color: @theme_fg_color;
}

.big_img {
  color: @theme_bg_color;
}

.button {
  margin: 10px;
}

.vbox {
  margin: 10px;
}
"""


class InteractiveIntro(GObject.Object):
    """Interactive GUI intro for newcomers."""

    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app
        self.current_widget = None
        self.advance_handler_id = 0
        self.intro_button = self.__create_intro_button()
        self.tips = []
        self.__setup_css()
        self.intro_popover, self.intro_label = self.__create_popover()
        self.intro_action = Gio.SimpleAction.new("interactive-intro", None)
        self.intro_action.connect("activate", self.interactive_intro_cb)

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(INTERACTIVE_INTRO_CSS.encode("UTF-8"))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def __create_intro_button(self):
        icon = Gtk.IconTheme.lookup_icon(Gtk.IconTheme.get_default(), "org.pitivi.Pitivi-symbolic", 15, Gtk.IconLookupFlags.FORCE_SVG)
        pixbuf = icon.load_icon()
        img = Gtk.Image()
        img.set_from_pixbuf(pixbuf)
        intro_button = Gtk.Button()
        intro_button.set_image(img)
        intro_button.set_always_show_image(True)
        intro_button.props.no_show_all = True
        return intro_button

    def __create_popover(self):
        intro_popover = Gtk.Popover()
        intro_popover.set_position(Gtk.PositionType.BOTTOM)
        intro_popover.set_modal(True)
        intro_popover.connect("closed", self.stop_tour)

        intro_label = Gtk.Label()
        intro_label.set_line_wrap(True)
        intro_label.set_max_width_chars(24)
        intro_label.set_name("popover")

        icon = os.path.join(get_pixmap_dir(), "intro-bigimage.svg")
        img = Gtk.Image()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon, 60, 60, True)
        img.set_from_pixbuf(pixbuf)

        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.get_style_context().add_class("vbox")
        vbox.pack_start(img, False, False, 5)
        vbox.pack_end(intro_label, False, False, 5)

        intro_popover.add(vbox)
        intro_popover.show_all()

        return intro_popover, intro_label

    def interactive_intro_cb(self, unused_action, unused_param):
        if self.running:
            self.stop_tour(None)
        else:
            self.show_control_popover()

    @property
    def running(self):
        return self.advance_handler_id != 0

    def show_control_popover(self):
        # pylint: disable=attribute-defined-outside-init
        self.overview_button = Gtk.Button.new_with_label(_("Start Overview"))
        self.overview_button.get_style_context().add_class("button")
        self.overview_button.connect("clicked", self._overview_button_clicked_cb)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.overview_button, False, True, 10)

        self.intro_button.show()

        self.select_intro_popover = Gtk.Popover()
        self.select_intro_popover.add(vbox)
        self.select_intro_popover.set_relative_to(self.intro_button)
        self.select_intro_popover.set_position(Gtk.PositionType.TOP)
        self.select_intro_popover.show_all()
        self.select_intro_popover.popup()

    def set_current_widget(self, widget):
        if self.current_widget:
            self.current_widget.get_style_context().remove_class("intro-highlighted")
            self.current_widget = None

        if widget:
            self.current_widget = widget
            self.current_widget.get_style_context().add_class("intro-highlighted")

    def stop_tour(self, unused_widget):
        if self.advance_handler_id:
            GLib.source_remove(self.advance_handler_id)
            self.advance_handler_id = 0

        self.set_current_widget(None)

        self.intro_button.hide()

    def _overview_button_clicked_cb(self, unused_widget):
        self.select_intro_popover.popdown()
        # pylint: disable=protected-access
        editor = self.app.gui.editor
        self.tips = [
            (self.intro_button, _("Welcome to Pitivi!"), Gtk.PositionType.BOTTOM, 3000),
            (editor.medialibrary, _("Drag files here to import them"), Gtk.PositionType.RIGHT, 5000),
            (editor.timeline_ui.timeline, _("Drag and arrange clips in the timeline"), Gtk.PositionType.TOP, 7000),
            (editor.timeline_ui.ruler, _("Right-click to move the playhead"), Gtk.PositionType.TOP, 6000),
            (editor.viewer.playpause_button, _("Preview with the play button"), Gtk.PositionType.BOTTOM, 5000),
            (editor.render_button, _("Export your project to share it"), Gtk.PositionType.BOTTOM, 5000),
            (self.intro_button, _("See all the keyboard shortcuts with Ctrl+F1"), Gtk.PositionType.BOTTOM, 5000)]
        self.advance_popover_func()

    def advance_popover_func(self):
        if not self.tips:
            self.stop_tour(None)
            return False

        self.intro_popover.disconnect_by_func(self.stop_tour)
        self.intro_popover.popdown()

        # Without this, the popover sometimes appears and quickly disappears.
        self.intro_popover.hide()
        self.intro_popover.connect("closed", self.stop_tour)
        widget, text, position_type, timeout = self.tips.pop(0)
        self.set_current_widget(widget)

        self.intro_label.set_markup(text)
        self.intro_popover.set_relative_to(widget)
        self.intro_popover.set_position(position_type)
        self.intro_popover.popup()

        self.advance_handler_id = GLib.timeout_add(timeout, self.advance_popover_func)
        return False
