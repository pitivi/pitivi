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
from gi.repository import GObject
from gi.repository import Gtk

GObject.threads_init()

class IntractiveIntro(GObject.Object):
    """Interactive GUI intro for newcomers."""

    __gsignals__ = {
        "run-next-intro": (GObject.SignalFlags.RUN_LAST, None, (object,))
    }

    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app
        self.intractive_intro_index = 0
        self.current_intro_group_index = 0
        self.gobject_timeout_intro = None
        self.gobject_timeout = None
        self.intro_popover = Gtk.Popover()
        self.intro_label = Gtk.Label()
        self.select_intro_popover = Gtk.Popover()
        self.overview_label = Gtk.Label()
        self.tutorial_label = Gtk.Label()
        self.widgets_list = []
        self.running = False
        self.is_intro_button_visible = True

    def start_tour(self, unused_widget):
        self.intro_popover.set_position(Gtk.PositionType.BOTTOM)
        self.intro_label.set_property('margin', 10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.intro_label, False, True, 10)
        self.intro_popover.add(vbox)

        self.overview_label.set_markup("<a href = '#'><span underline = 'none' foreground = '#595c54'><big>Overview</big></span></a>")
        self.overview_label.connect("activate-link", self.overview_lable_cb)
        self.overview_label.set_property('margin', 10)

        self.tutorial_label.set_markup("<a href = '#'><span underline = 'none' foreground = '#595c54'><big>Tutorial</big></span></a>")
        self.tutorial_label.connect("activate-link", self.tutorial_lable_cb)
        self.tutorial_label.set_property('margin', 10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.overview_label, False, True, 10)
        vbox.pack_start(self.tutorial_label, False, True, 10)
        self.select_intro_popover.add(vbox)
        self.select_intro_popover.set_relative_to(self.app.gui.editor.intro_button)
        self.select_intro_popover.set_position(Gtk.PositionType.BOTTOM)
        self.select_intro_popover.show_all()
        self.select_intro_popover.popup()
        self.connect("run-next-intro", self.continue_next_intro)

    def stop_tour(self, unused_widget):
        if self.gobject_timeout is not None:
            GObject.source_remove(self.gobject_timeout)
        if self.gobject_timeout_intro is not None:
            GObject.source_remove(self.gobject_timeout_intro)
        self.intractive_intro_index = 0
        self.current_intro_group_index = 0
        self.select_intro_popover.popdown()
        self.widgets_list = []

    def overview_lable_cb(self, unused_widget, unused_param):
        self.select_intro_popover.popdown()
        if self.gobject_timeout_intro is not None:
            GObject.source_remove(self.gobject_timeout_intro)
        self.gobject_timeout_intro = GObject.timeout_add(200, self.start_next_intro)

    def tutorial_lable_cb(self, unused_widget, unused_param):
        pass

    def continue_next_intro(self, unused_widget, unused_param):
        self.widgets_list = []
        self.intractive_intro_index = 0
        if self.gobject_timeout_intro is not None:
            GObject.source_remove(self.gobject_timeout_intro)
        self.gobject_timeout_intro = GObject.timeout_add(200, self.start_next_intro)

    def start_next_intro(self):
        if self.current_intro_group_index == 0:
            self.headerbar_overview()
        elif self.current_intro_group_index == 1:
            self.viewer_overview()
        elif self.current_intro_group_index == 2:
            self.timeline_overview()
        elif self.current_intro_group_index == 3:
            self.app.gui.editor.main_tabs.set_current_page(0)
            self.medialibrary_overview()
        elif self.current_intro_group_index == 4:
            self.app.gui.editor.main_tabs.set_current_page(1)
            self.effectlist_overview()
        elif self.current_intro_group_index == 5:
            self.app.gui.editor.intro_button.hide()
            self.app.gui.editor.is_intro_button_visible = False
            self.app.gui.editor.running = False
            self.stop_tour(None)

    def headerbar_overview(self):
        if len(self.widgets_list) == 0:
            widgets_list = [(self.app.gui.editor.intro_button, "Let's begin with quick overview"),
                            (self.app.gui.editor.headerbar, "Here Comes Your \n Project Title."),
                            (self.app.gui.editor.save_button, "To save your project \n you have this."),
                            (self.app.gui.editor.render_button, "When you are done \n Here you have all your \n Export settings."),
                            (self.app.gui.editor.menu_button, "Here you have your menu items."),
                            (self.app.gui.editor.undo_button, "Undo Button.\n or you can press \n[ctrl]+Z.)"),
                            (self.app.gui.editor.redo_button, "Redo Button.\n or you can press \n[ctrl]+[shift]+Z. "),
                            (self.app.gui.editor.intro_button, "Ok! now let's \nbegin with Viewer")
                           ]
            self.widgets_list.extend(widgets_list)
        self.gobject_timeout = GObject.timeout_add(1500, self.intractive_overview_show_popup)

    def viewer_overview(self):
        if len(self.widgets_list) == 0:
            widgets_list = [(self.app.gui.editor.viewer, "This is your \nmedia playback."),
                            (self.app.gui.editor.viewer.start_button, "Seek to start"),
                            (self.app.gui.editor.viewer.back_button, "Seek back \none second"),
                            (self.app.gui.editor.viewer.playpause_button, "Play/Pause"),
                            (self.app.gui.editor.viewer.forward_button, "Seek forward \none second"),
                            (self.app.gui.editor.viewer.end_button, "Seek to end"),
                            (self.app.gui.editor.viewer.undock_button, "You can also Undock \n viewer by this button."),
                            (self.app.gui.editor.viewer.timecode_entry, "Current position"),
                            (self.app.gui.editor.intro_button, "Ok! now let's begin\n with timeline")
                           ]
            self.widgets_list.extend(widgets_list)
        self.gobject_timeout = GObject.timeout_add(1500, self.intractive_overview_show_popup)

    def timeline_overview(self):
        if len(self.widgets_list) == 0:
            widgets_list = [(self.app.gui.editor.timeline_ui.timeline, "Here is your timeline."),
                            (self.app.gui.editor.timeline_ui.zoom_box, "From here you can Zoom \n timeline for more clearity."),
                            (self.app.gui.editor.timeline_ui.timeline.add_layer_button, "To add Layers"),
                            (self.app.gui.editor.timeline_ui.toolbar, "You can cut/join/copy \n clips from these."),
                            (self.app.gui.editor.timeline_ui.markers, "These markers point to frames,\n if you zoom in you can see them!"),
                            (self.app.gui.editor.intro_button, "Ok, now let's\n move to media and \neffects part")
                            ]
            self.widgets_list.extend(widgets_list)
        self.gobject_timeout = GObject.timeout_add(1500, self.intractive_overview_show_popup)

    def medialibrary_overview(self):
        # pylint: disable=W0212
        if len(self.widgets_list) == 0:
            widgets_list = [(self.app.gui.editor.medialibrary, "Here you can view \n your imported media."),
                            (self.app.gui.editor.medialibrary._import_button, "By this button you can \n import your favourite media."),
                            (self.app.gui.editor.medialibrary._clipprops_button, "From you can set your clip Properties"),
                            (self.app.gui.editor.medialibrary._listview_button, "And now comes the\n coolest part \n [ Effects ]"),
                            (self.app.gui.editor.intro_button, "And now comes the\n coolest part \n [ Effects ]")
                            ]
            self.widgets_list.extend(widgets_list)
        self.gobject_timeout = GObject.timeout_add(1500, self.intractive_overview_show_popup)

    def effectlist_overview(self):
        if len(self.widgets_list) == 0:
            widgets_list = [(self.app.gui.editor.effectlist, "Here you have all your \n Effects and Filters."),
                            (self.app.gui.editor.effectlist.audio_togglebutton, "You can also \nadd Music/Audio"),
                            (self.app.gui.editor.effectlist.view, "We have a \nlot of them!"),
                            (self.app.gui.editor.intro_button, "Cool right!"),
                            (self.app.gui.editor.intro_button, "I hope it was \n help helpfull!"),
                            (self.app.gui.editor.intro_button, "Wait! That's not it."),
                            (self.app.gui.editor.intro_button, "For more productivity \n we have  \n shortcuts for you \n Just press [ctrl]+F1 \n to see"),
                            (self.app.gui.editor.intro_button, "Till the time you \n explore these."),
                            (self.app.gui.editor.intro_button, "You will have more \n Features and Utilities."),
                            (self.app.gui.editor.intro_button, "For additional Help \n you can also refer to \n User Manual provided."),
                            (self.app.gui.editor.intro_button, "Good Bye!")
                            ]
            self.widgets_list.extend(widgets_list)
        self.gobject_timeout = GObject.timeout_add(1500, self.intractive_overview_show_popup)

    def intractive_overview_show_popup(self):
        if self.intractive_intro_index == len(self.widgets_list):
            self.intro_popover.popdown()
            self.current_intro_group_index += 1
            self.emit("run-next-intro", None)
            return False
        current_intro_element = self.widgets_list[self.intractive_intro_index]
        widget_index = 0
        label_index = 1
        self.intro_label.set_markup('<span><b>\n'+str(current_intro_element[label_index])+'</b></span>')
        self.intro_popover.set_relative_to(current_intro_element[widget_index])
        self.intro_popover.show_all()
        self.intro_popover.popup()
        self.intractive_intro_index += 1
        return True
