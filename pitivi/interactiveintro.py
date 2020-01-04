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
import enum
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk

class Intro(enum.Enum):
    RUNNING = 0
    PAUSED = 1
    STOPED = 2

class InteractiveIntro(GObject.Object):
    """Interactive GUI intro for newcomers."""

    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app
        self.status = Intro.STOPED
        self.current_widget_index = 0
        self.current_widget_group_timeout = None
        self.tips = self._create_tips()

    def _create_tips(self):
        # pylint: disable=W0212
        return [(self.app.gui.editor.intro_button, _("Let's begin with quick overview")),
                (self.app.gui.editor.headerbar, _("Here Comes Your Project Title")),
                (self.app.gui.editor.save_button, _("To save your project you have this")),
                (self.app.gui.editor.render_button, _("When you are done Here you have all your Export settings")),
                (self.app.gui.editor.viewer, _("This is your .media playback")),
                (self.app.gui.editor.timeline_ui.timeline, _("Here is your timeline")),
                (self.app.gui.editor.medialibrary, _("Here you can view your imported media")),
                (self.app.gui.editor.medialibrary._import_button, _("By this button you can import your favourite media")),
                (self.app.gui.editor.effectlist, _("Here you have all your Effects and Filters")),
                (self.app.gui.editor.intro_button, _("For more productivity we have shortcuts for you Just press [ctrl]+F1 to see")),
                (self.app.gui.editor.intro_button, _("For additional Help you can also refer to User Manual provided")),
                (self.app.gui.editor.intro_button, _("Good Bye!"))
                ]

    def control_intro(self):
        if self.status == Intro.RUNNING:
            self.pause_tour()
        elif self.status == Intro.PAUSED:
            self.stop_tour()
        elif self.status == Intro.STOPED:
            self.start_tour()

    def pause_tour(self):
        # pylint: disable=attribute-defined-outside-init
        self.status = Intro.PAUSED
        if self.current_widget_group_timeout is not None:
            GObject.source_remove(self.current_widget_group_timeout)
        self.intro_popover.popdown()

        self.resume_popover = Gtk.Popover()
        self.resume_popover.set_position(Gtk.PositionType.BOTTOM)

        self.resume_label = Gtk.Label()
        resume_label = _("Resume Intro")
        self.resume_label.set_markup("<a href = '#'><span underline = 'none' foreground = '#595c54'><big>"+resume_label+"</big></span></a>")
        self.resume_label.connect("activate-link", self.resume_tour_label_cb)
        self.resume_label.set_property("margin", 10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.resume_label, False, True, 10)
        self.resume_popover.add(vbox)
        self.resume_popover.set_relative_to(self.app.gui.editor.intro_button)
        self.resume_popover.show_all()
        self.resume_popover.popup()

    def resume_tour_label_cb(self, widget, unused_param):
        self.resume_popover.popdown()
        self.status = Intro.RUNNING
        self.start_overview()

    def start_tour(self):
        # pylint: disable=attribute-defined-outside-init
        self.status = Intro.RUNNING

        self.intro_popover = Gtk.Popover()
        self.intro_popover.set_position(Gtk.PositionType.BOTTOM)

        self.intro_label = Gtk.Label()
        self.intro_label.set_property("margin", 10)
        self.intro_label.props.wrap = True

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.intro_label, False, True, 10)
        self.intro_popover.add(vbox)

        self.overview_label = Gtk.Label()
        overview_label = _("Overview")
        self.overview_label.set_markup("<a href = '#'><span underline = 'none' foreground = '#595c54'><big>"+overview_label+"</big></span></a>")
        self.overview_label.connect("activate-link", self._overview_label_activate_link_cb)
        self.overview_label.set_property("margin", 10)

        self.tutorial_label = Gtk.Label()
        tutorial_label = _("Tutorial")
        self.tutorial_label.set_markup("<a href = '#'><span underline = 'none' foreground = '#595c54'><big>"+tutorial_label+"</big></span></a>")
        self.tutorial_label.connect("activate-link", self._tutorial_label_activate_link_cb)
        self.tutorial_label.set_property("margin", 10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.overview_label, False, True, 10)
        vbox.pack_start(self.tutorial_label, False, True, 10)

        self.app.gui.editor.intro_button.show()
        self.current_widget_group_timeout = None

        self.select_intro_popover = Gtk.Popover()
        self.select_intro_popover.add(vbox)
        self.select_intro_popover.set_relative_to(self.app.gui.editor.intro_button)
        self.select_intro_popover.set_position(Gtk.PositionType.BOTTOM)
        self.select_intro_popover.show_all()
        self.select_intro_popover.popup()

    def stop_tour(self):
        self.status = Intro.STOPED
        self.current_widget_index = 0
        self.tips = []
        self.app.gui.editor.intro_button.hide()

    def _overview_label_activate_link_cb(self, unused_widget, unused_param):
        self.select_intro_popover.popdown()
        self.start_overview()

    def _tutorial_label_activate_link_cb(self, unused_widget, unused_param):
        self.select_intro_popover.popdown()

    def start_overview(self):
        self.current_widget_group_timeout = GObject.timeout_add(2000, self.interactive_overview_show_popup)

    def interactive_overview_show_popup(self):
        if self.current_widget_index == len(self.tips):
            self.stop_tour()
            return False
        widget, text = self.tips[self.current_widget_index]
        self.intro_label.set_markup("<span><b>"+str(text)+"</b></span>")
        self.intro_popover.set_relative_to(widget)
        self.intro_popover.show_all()
        self.intro_popover.popup()
        self.current_widget_index += 1
        return True
