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
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk


INTERACTIVE_INTRO_CSS = """
@keyframes intro-highlight {
  from { box-shadow: 0px 0px 10px @theme_selected_bg_color, inset 0px 0px 4px  @theme_selected_bg_color; }
  to   { box-shadow: 0px 0px 4px  @theme_selected_bg_color, inset 0px 0px 10px @theme_selected_bg_color; }
}

.intro-highlight {
  animation: intro-highlight 1.5s infinite alternate;
}


#control-popover > box > button {
  margin: 10px;
}


#intro-popover {
  background-color: @theme_selected_bg_color;
}

#intro-popover > box {
  margin: 10px;
}

#intro-popover > box > label {
  font-size: 18pt;
  font-weight: bold;
  margin: 10px;
  color: @theme_fg_color;
}
"""


class InteractiveIntro(GObject.Object):
    """Interactive GUI intro for newcomers.

    Attributes:
        intro_action (Gio.SimpleAction): The action for showing the control
            popover.
        intro_button (Gtk.Button): The button to be displayed in the headerbar
            for showing the control popover.
        widget (Gtk.Widget): The current widget being highlighted.
    """

    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app
        self.widget = None
        self.parent_widget = None
        self.tips = []
        self._advance_handler_id = 0
        self._hiding_popover_when_advancing = False

        self.__setup_css()

        self.intro_action = Gio.SimpleAction.new("interactive-intro", None)
        self.intro_action.connect("activate", self._control_intro_cb)

        self.intro_button = self.__create_intro_button()

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(INTERACTIVE_INTRO_CSS.encode("UTF-8"))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def __create_intro_button(self):
        """Creates a button for controlling the intro."""
        button = Gtk.Button.new_from_icon_name(
            "org.pitivi.Pitivi-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_always_show_image(True)
        button.props.no_show_all = True
        button.props.relief = Gtk.ReliefStyle.NONE
        # We could set_action_name, but we don't know here the group
        # in which the action will be added, so it's simpler this way.
        button.connect("clicked", self._intro_button_clicked_cb)
        return button

    def __create_popover(self, text):
        popover = Gtk.Popover()
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_modal(True)
        popover.connect("closed", self._intro_popover_closed_cb)
        popover.set_name("intro-popover")

        label = Gtk.Label()
        label.set_markup(text)
        label.set_line_wrap(True)
        label.set_max_width_chars(24)

        img = Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.DIALOG)

        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(img, False, False, 5)
        vbox.pack_end(label, False, False, 5)
        vbox.show_all()

        popover.add(vbox)

        return popover

    def _intro_popover_closed_cb(self, unused_widget):
        if self._hiding_popover_when_advancing:
            if self.parent_widget:
                self.parent_widget.hide()
                self.parent_widget = None
            return

        self.stop_tour()

    def _control_intro_cb(self, unused_action, unused_param):
        """Handles the activation of the interactive intro action."""
        if self.running:
            self.stop_tour()
        else:
            self.show_control_popover()

    def _intro_button_clicked_cb(self, button):
        self.intro_action.activate()

    @property
    def running(self):
        return self._advance_handler_id != 0

    def show_control_popover(self):
        # pylint: disable=attribute-defined-outside-init
        overview_button = Gtk.Button.new_with_label(_("Start Overview"))
        overview_button.connect("clicked", self._overview_button_clicked_cb)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(overview_button, False, True, 10)

        self.intro_button.show()
        self.intro_button.get_style_context().add_class("intro-highlight")

        self.control_popover = Gtk.Popover()
        self.control_popover.set_name("control-popover")
        self.control_popover.add(vbox)
        self.control_popover.set_relative_to(self.intro_button)
        self.control_popover.show_all()
        self.control_popover.popup()
        self.control_popover.connect("closed", self._control_popover_closed_cb)

    def _control_popover_closed_cb(self, unused_widget):
        self.intro_button.get_style_context().remove_class("intro-highlight")

    def set_current_widget(self, widget):
        """Switches the focus to a new widget, highlighting it."""
        if self.widget:
            self.widget.get_style_context().remove_class("intro-highlight")
            self.widget = None

        if widget:
            self.widget = widget
            self.widget.get_style_context().add_class("intro-highlight")

            if isinstance(self.widget, Gtk.ModelButton):
                self.parent_widget = self._find_parent(self.widget, Gtk.Popover)
                if self.parent_widget:
                    self.parent_widget.popup()

    def _find_parent(self, widget, parent_class):
        while widget:
            if isinstance(widget, parent_class):
                return widget

            widget = widget.props.parent

        return None

    def stop_tour(self):
        if self._advance_handler_id:
            GLib.source_remove(self._advance_handler_id)
            self._advance_handler_id = 0

        self.set_current_widget(None)

        self.intro_button.hide()

    def _overview_button_clicked_cb(self, unused_widget):
        """Starts the UI overview."""
        self.control_popover.popdown()
        editor = self.app.gui.editor
        self.tips = [
            (self.intro_button, _("Welcome to Pitivi!"),
             Gtk.PositionType.BOTTOM, False, 4000),
            (editor.medialibrary.scrollwin, _("Drag files here to import them"),
             Gtk.PositionType.RIGHT, True, 5000),
            (editor.timeline_ui.timeline, _("Drag clips in the timeline to arrange them"),
             Gtk.PositionType.TOP, True, 7000),
            (editor.timeline_ui.ruler, _("Right-click anywhere to move the playhead"),
             Gtk.PositionType.TOP, True, 6000),
            (editor.viewer.playpause_button, _("Preview with the play button"),
             Gtk.PositionType.TOP, False, 5000),
            (editor.render_button, _("Export your project to share it"),
             Gtk.PositionType.BOTTOM, False, 5000),
            (editor.keyboard_shortcuts_button, _("See all the keyboard shortcuts"),
             Gtk.PositionType.LEFT, False, 6000)]

        self.advance_popover_func(previous_popover=None)

    def advance_popover_func(self, previous_popover):
        """Moves the popover to the next widget."""
        if previous_popover:
            self._hiding_popover_when_advancing = True
            try:
                previous_popover.popdown()
            finally:
                self._hiding_popover_when_advancing = False

        if not self.tips:
            self.stop_tour()
            return False

        widget, text, position_type, center, timeout = self.tips.pop(0)
        self.set_current_widget(widget)

        popover = self.__create_popover(text)
        popover.set_relative_to(widget)

        if center:
            rect = Gdk.Rectangle()
            rect.x = widget.get_allocated_width() / 2
            rect.y = widget.get_allocated_height() / 2
            rect.width = 4
            rect.height = 4
            popover.set_pointing_to(rect)

        popover.set_position(position_type)
        popover.popup()

        self._advance_handler_id = GLib.timeout_add(timeout, self.advance_popover_func, popover)
        return False
