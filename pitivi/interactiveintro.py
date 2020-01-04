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
from gi.repository import GObject
from gi.repository import Gtk

from pitivi.configure import get_data_dir
from pitivi.configure import get_pixmap_dir

INTERACTIVE_INTRO_CSS = """

@keyframes intro-highlighted {
  from { box-shadow: 0px 0px 10px @theme_selected_bg_color, inset 0px 0px 4px  @theme_selected_bg_color; }
  to   { box-shadow: 0px 0px 4px  @theme_selected_bg_color, inset 0px 0px 10px @theme_selected_bg_color; }
}

@keyframes icon-highlight {
  from { -gtk-icon-shadow: 4px -1px 8px alpha(#f5ed02, 0); }
  to   { -gtk-icon-shadow: 4px -1px 8px alpha(#f5ed02, 0.9); }
}

.intro-highlighted{
animation: intro-highlighted 1.5s infinite alternate;
}

.pitivi-icon {
  animation: icon-highlight 2s infinite alternate;
}

#popover{
  color: rgb(26, 12, 1);
  font-size: 18pt;
  font-weight: bold;
  text-shadow: 1px 1px 2px grey;
}

.button{
  margin: 10px;
}

.vbox{
  margin: 10px;
}
"""

class InteractiveIntro(GObject.Object):
    """Interactive GUI intro for newcomers."""

    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app
        self.current_widget_index = 0
        self.advance_handler_id = 0
        self.intro_button = None
        self.tips = self._create_tips()
        self.__setup_css()

    def _create_tips(self):
        # pylint: disable=W0212
        return [(self.app.gui.editor.intro_button, _("Let's begin with quick overview"), 3000),
                (self.app.gui.editor.headerbar, _("Here Comes Your Project Title"), 3000),
                (self.app.gui.editor.save_button, _("To save your project you have this"), 3000),
                (self.app.gui.editor.viewer.buttons_container, _("This is your media playback"), 3000),
                (self.app.gui.editor.timeline_ui, _("Here is your timeline"), 3000),
                (self.app.gui.editor.timeline_ui.toolbar, _("Here are your timeline tools"), 3000),
                (self.app.gui.editor.medialibrary, _("Here you can view your imported media"), 3000),
                (self.app.gui.editor.medialibrary._import_button, _("From Here you can import your favourite media"), 4000),
                (self.app.gui.editor.intro_button, _("For more productivity we have shortcuts for you Just press [ctrl]+F1 to see"), 3000),
                (self.app.gui.editor.intro_button, _("For additional Help you can also refer to User Manual provided"), 3000),
                (self.app.gui.editor.intro_button, _("Good Bye!"), 2000)
                ]

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(INTERACTIVE_INTRO_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def create_intro_button(self):
        icon = os.path.join(get_data_dir(), "icons/hicolor/symbolic/apps/", "org.pitivi.Pitivi-symbolic.svg")
        img = Gtk.Image()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon)
        img.set_from_pixbuf(pixbuf)
        img.get_style_context().add_class("pitivi-icon")
        intro_button = Gtk.Button()
        intro_button.set_image(img)
        intro_button.get_style_context().add_class("intro-highlighted")
        intro_button.set_always_show_image(True)
        intro_button.props.no_show_all = True

        return intro_button

    def toggle_playback(self):
        if self.running:
            self.stop_tour()
        elif not self.running:
            self.show_control_popover()

    @property
    def running(self):
        return self.advance_handler_id != 0

    def show_control_popover(self):
        # pylint: disable=attribute-defined-outside-init
        self.intro_popover = Gtk.Popover()
        self.intro_popover.set_position(Gtk.PositionType.BOTTOM)

        self.intro_label = Gtk.Label()
        self.intro_label.set_line_wrap(True)
        self.intro_label.set_max_width_chars(24)
        self.intro_label.set_name("popover")

        icon = os.path.join(get_pixmap_dir(), "intro-bigimage.svg")
        img = Gtk.Image()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon, 60, 60, True)
        img.set_from_pixbuf(pixbuf)

        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.get_style_context().add_class("vbox")
        vbox.pack_start(img, False, False, 5)
        vbox.pack_end(self.intro_label, False, False, 5)

        self.intro_popover.add(vbox)

        self.overview_button = Gtk.Button.new_with_label(_("Start Overview"))
        self.overview_button.get_style_context().add_class("button")
        self.overview_button.connect("clicked", self._overview_button_clicked_cb)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.overview_button, False, True, 10)

        self.intro_button.show()

        self.select_intro_popover = Gtk.Popover()
        self.select_intro_popover.add(vbox)
        self.select_intro_popover.set_relative_to(self.intro_button)
        self.select_intro_popover.set_position(Gtk.PositionType.BOTTOM)
        self.select_intro_popover.show_all()
        self.select_intro_popover.popup()

    def stop_tour(self):
        if self.advance_handler_id is not None:
            GObject.source_remove(self.advance_handler_id)
        widget = self.tips[self.current_widget_index-1][0]
        widget.get_style_context().remove_class("intro-highlighted")
        self.current_widget_index = 0
        self.advance_handler_id = 0
        self.intro_button.hide()

    def _overview_button_clicked_cb(self, unused_widget):
        self.select_intro_popover.popdown()
        self.start_overview()

    def start_overview(self):
        self.interactive_overview_show_popup_func()

    def interactive_overview_show_popup_func(self):
        if self.current_widget_index == len(self.tips):
            self.stop_tour()
            return False
        widget, text, timeout = self.tips[self.current_widget_index]
        if self.current_widget_index > 0:
            prev_widget = self.tips[self.current_widget_index-1][0]
            prev_widget.get_style_context().remove_class("intro-highlighted")
        widget.get_style_context().add_class("intro-highlighted")
        self.intro_label.set_markup(text)
        self.intro_popover.set_relative_to(widget)
        self.intro_popover.show_all()
        self.intro_popover.popup()
        self.current_widget_index += 1
        self.advance_handler_id = GObject.timeout_add(timeout, self.interactive_overview_show_popup_func)
        return False
