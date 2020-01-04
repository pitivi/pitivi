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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk


class InteractiveIntro(GObject.Object):
    """Interactive GUI intro for newcomers."""

    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app
        self.running = False
        self.current_widget_group_index = 0
        self.current_widget_index = 0
        self.current_widget_timeout = None
        self.current_widget_group = None
        # self.tips = collections.OrderedDict()
        self.tips = []


    def start_tour(self):
        # pylint: disable=attribute-defined-outside-init
        self.running = True

        self.intro_popover = Gtk.Popover()
        self.intro_popover.set_position(Gtk.PositionType.BOTTOM)

        self.intro_label = Gtk.Label()
        self.intro_label.set_property("margin", 10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.intro_label, False, True, 10)
        self.intro_popover.add(vbox)

        self.overview_label = Gtk.Label()
        overview_label = _("Overview")
        self.overview_label.set_markup("<a href = '#'><span underline = 'none' foreground = '#595c54'><big>"+overview_label+"</big></span></a>")
        self.overview_label.connect("activate-link", self._overview_label_activate_link_cb)
        self.overview_label.set_property('margin', 10)

        self.tutorial_label = Gtk.Label()
        tutorial_label = _("Tutorial")
        self.tutorial_label.set_markup("<a href = '#'><span underline = 'none' foreground = '#595c54'><big>"+tutorial_label+"</big></span></a>")
        self.tutorial_label.connect("activate-link", self._tutorial_label_activate_link_cb)
        self.tutorial_label.set_property("margin", 10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.overview_label, False, True, 10)
        vbox.pack_start(self.tutorial_label, False, True, 10)

        self.select_intro_popover = Gtk.Popover()
        self.select_intro_popover.add(vbox)
        self.select_intro_popover.set_relative_to(self.app.gui.editor.intro_button)
        self.select_intro_popover.set_position(Gtk.PositionType.BOTTOM)
        self.select_intro_popover.show_all()
        self.select_intro_popover.popup()

    def stop_tour(self):
        self.running = False
        if self.current_widget_group is not None:
            GObject.source_remove(self.current_widget_group)
        if self.current_widget_timeout is not None:
            GObject.source_remove(self.current_widget_timeout)
        self.current_widget_index = 0
        self.current_widget_group_index = 0
        self.tips = []

    def _overview_label_activate_link_cb(self, unused_widget, unused_param):
        self.select_intro_popover.popdown()
        if self.current_widget_timeout is not None:
            GObject.source_remove(self.current_widget_timeout)
        self.current_widget_timeout = GObject.timeout_add(200, self.start_next_intro)

    def _tutorial_label_activate_link_cb(self, unused_widget, unused_param):
        pass

    def continue_next_intro(self):
        self.tips = []
        self.current_widget_index = 0
        if self.current_widget_timeout is not None:
            GObject.source_remove(self.current_widget_timeout)
        self.current_widget_timeout = GObject.timeout_add(200, self.start_next_intro)

    def start_next_intro(self):
        if self.current_widget_group_index == 0:
            self.headerbar_overview()
        elif self.current_widget_group_index == 1:
            self.viewer_overview()
        elif self.current_widget_group_index == 2:
            self.timeline_overview()
        elif self.current_widget_group_index == 3:
            self.app.gui.editor.main_tabs.set_current_page(0)
            self.medialibrary_overview()
        elif self.current_widget_group_index == 4:
            self.app.gui.editor.main_tabs.set_current_page(1)
            self.effectlist_overview()
        elif self.current_widget_group_index == 5:
            self.app.gui.editor.intro_button.hide()
            self.stop_tour()

    def headerbar_overview(self):
        if len(self.tips) == 0:
            tips = [(self.app.gui.editor.intro_button, _("Let's begin with quick overview")),
                    (self.app.gui.editor.headerbar, _("Here Comes Your \n Project Title.")),
                    (self.app.gui.editor.save_button, _("To save your project \n you have this.")),
                    (self.app.gui.editor.render_button, _("When you are done \n Here you have all your \n Export settings.")),
                    (self.app.gui.editor.menu_button, _("Here you have your menu items.")),
                    (self.app.gui.editor.undo_button, _("Undo Button.\n or you can press \n[ctrl]+Z.)")),
                    (self.app.gui.editor.redo_button, _("Redo Button.\n or you can press \n[ctrl]+[shift]+Z._(")),
                    (self.app.gui.editor.intro_button, _("Ok! now let's \nbegin with Viewer"))
                    ]
            self.tips.extend(tips)
        self.current_widget_group = GObject.timeout_add(1500, self.interactive_overview_show_popup)

    def viewer_overview(self):
        if len(self.tips) == 0:
            tips = [(self.app.gui.editor.viewer, _("This is your \nmedia playback.")),
                    (self.app.gui.editor.viewer.start_button, _("Seek to start")),
                    (self.app.gui.editor.viewer.back_button, _("Seek back \none second")),
                    (self.app.gui.editor.viewer.playpause_button, _("Play/Pause")),
                    (self.app.gui.editor.viewer.forward_button, _("Seek forward \none second")),
                    (self.app.gui.editor.viewer.end_button, _("Seek to end")),
                    (self.app.gui.editor.viewer.undock_button, _("You can also Undock \n viewer by this button.")),
                    (self.app.gui.editor.viewer.timecode_entry, _("Current position")),
                    (self.app.gui.editor.intro_button, _("Ok! now let's begin\n with timeline"))
                    ]
            self.tips.extend(tips)
        self.current_widget_group = GObject.timeout_add(1500, self.interactive_overview_show_popup)

    def timeline_overview(self):
        if len(self.tips) == 0:
            tips = [(self.app.gui.editor.timeline_ui.timeline, _("Here is your timeline.")),
                    (self.app.gui.editor.timeline_ui.zoom_box, _("From here you can Zoom \n timeline for more clearity.")),
                    (self.app.gui.editor.timeline_ui.timeline.add_layer_button, _("To add Layers")),
                    (self.app.gui.editor.timeline_ui.toolbar, _("You can cut/join/copy \n clips from these.")),
                    (self.app.gui.editor.timeline_ui.markers, _("These markers point to frames,\n if you zoom in you can see them!")),
                    (self.app.gui.editor.intro_button, _("Ok, now let's\n move to media and \neffects part"))
                    ]
            self.tips.extend(tips)
        self.current_widget_group = GObject.timeout_add(1500, self.interactive_overview_show_popup)

    def medialibrary_overview(self):
        # pylint: disable=W0212
        if len(self.tips) == 0:
            tips = [(self.app.gui.editor.medialibrary, _("Here you can view \n your imported media.")),
                    (self.app.gui.editor.medialibrary._import_button, _("By this button you can \n import your favourite media.")),
                    (self.app.gui.editor.medialibrary._clipprops_button, _("From you can set your clip Properties")),
                    (self.app.gui.editor.medialibrary._listview_button, _("And now comes the\n coolest part \n [ Effects ]")),
                    (self.app.gui.editor.intro_button, _("And now comes the\n coolest part \n [ Effects ]"))
                    ]
            self.tips.extend(tips)
        self.current_widget_group = GObject.timeout_add(1500, self.interactive_overview_show_popup)

    def effectlist_overview(self):
        if len(self.tips) == 0:
            tips = [(self.app.gui.editor.effectlist, _("Here you have all your \n Effects and Filters.")),
                    (self.app.gui.editor.effectlist.audio_togglebutton, _("You can also \nadd Music/Audio")),
                    (self.app.gui.editor.effectlist.view, _("We have a \nlot of them!")),
                    (self.app.gui.editor.intro_button, _("Cool right!")),
                    (self.app.gui.editor.intro_button, _("I hope it was \n help helpfull!")),
                    (self.app.gui.editor.intro_button, _("Wait! That's not it.")),
                    (self.app.gui.editor.intro_button, _("For more productivity \n we have  \n shortcuts for you \n Just press [ctrl]+F1 \n to see")),
                    (self.app.gui.editor.intro_button, _("Till the time you \n explore these.")),
                    (self.app.gui.editor.intro_button, _("You will have more \n Features and Utilities.")),
                    (self.app.gui.editor.intro_button, _("For additional Help \n you can also refer to \n User Manual provided.")),
                    (self.app.gui.editor.intro_button, _("Good Bye!"))
                    ]
            self.tips.extend(tips)
        self.current_widget_group = GObject.timeout_add(1500, self.interactive_overview_show_popup)

    def interactive_overview_show_popup(self):
        if self.current_widget_index == len(self.tips):
            self.current_widget_group_index += 1
            self.continue_next_intro()
            return False
        widget, text = self.tips[self.current_widget_index]
        self.intro_label.set_markup("<span><b>\n"+str(text)+"</b></span>")
        self.intro_popover.set_relative_to(widget)
        self.intro_popover.show_all()
        self.intro_popover.popup()
        self.current_widget_index += 1
        return True
