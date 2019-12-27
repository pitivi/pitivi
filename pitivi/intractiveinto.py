# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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


import configparser
import os
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from pitivi.pitivintrolist import test_list

GObject.threads_init()

class IntractiveIntro(GObject.Object):
    """ Intractive Intro which will guide you threw Pitivi """


    __gsignals__ = {
        "run-next-intro": (GObject.SignalFlags.RUN_LAST, None, (object,))
    }


    def __init__(self, app):
        GObject.Object.__init__(self)
        self.app = app

    def interactive_intro_start_tour(self, unused_widget):
        self.interactive_intro_index=0
        self.current_intro_group_index=0
        self.gObjectTimeout_intro=None
        self.gObjectTimeout=None

        self.intro_popover=Gtk.Popover()
        self.intro_popover.set_position(Gtk.PositionType.BOTTOM)
        self.intro_label = Gtk.Label()
        self.intro_label.set_property('margin',10)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.intro_label, False, True, 10)
        self.intro_popover.add(vbox)

        self.select_intro_popover=Gtk.Popover()

        self.overview_label = Gtk.Label()
        self.overview_label.set_markup("<a href='#'><span underline='none' foreground='#595c54'><big>Overview</big></span></a>")
        self.overview_label.connect("activate-link", self.overview_lable_cb)
        self.overview_label.set_property('margin',10)

        self.tutorial_label = Gtk.Label()
        self.tutorial_label.set_markup("<a href='#'><span underline='none' foreground='#595c54'><big>Tutorial</big></span></a>")
        self.tutorial_label.connect("activate-link", self.tutorial_lable_cb)
        self.tutorial_label.set_property('margin',10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.overview_label, False, True, 10)
        vbox.pack_start(self.tutorial_label, False, True, 10)
        self.select_intro_popover.add(vbox)
        self.select_intro_popover.set_relative_to(self.app.gui.editor.intro_button)
        self.select_intro_popover.set_position(Gtk.PositionType.BOTTOM)
        self.select_intro_popover.show_all()
        self.select_intro_popover.popup()
        self.connect("run-next-intro",self.continue_next_intro)
        self.widgits_list=[]
        self.intro_text_list=[]

    def interactive_intro_stop_tour(self, unused_widget):
        if self.gObjectTimeout != None:
            GObject.source_remove(self.gObjectTimeout)
        if self.gObjectTimeout_intro != None:
            GObject.source_remove(self.gObjectTimeout_intro)
        self.interactive_intro_index=0
        self.current_intro_group_index=0
        self.select_intro_popover.popdown()

    def overview_lable_cb(self, unused_widget, unused_param):
        self.select_intro_popover.popdown()
        if self.gObjectTimeout_intro != None:
            GObject.source_remove(self.gObjectTimeout_intro)
        self.gObjectTimeout_intro = GObject.timeout_add(200,self.start_next_intro)

    def tutorial_lable_cb(self, unused_widget, unused_param):
        pass

    def continue_next_intro(self,unused_widget, unused_param):
        self.widgits_list=[]
        self.interactive_intro_index=0
        # if self.gObjectTimeout_intro != None:
        #     GObject.source_remove(self.gObjectTimeout_intro)
        self.gObjectTimeout_intro = GObject.timeout_add(200,self.start_next_intro)

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
            self.app.gui.editor.is_intro_button_visible=False
        else:
             return False

    def headerbar_overview(self):
        if len(self.widgits_list) == 0:
            widgits_list= [self.app.gui.editor.intro_button,self.app.gui.editor.headerbar,self.app.gui.editor.save_button,
                      self.app.gui.editor.render_button,self.app.gui.editor.menu_button,
                      self.app.gui.editor.undo_button,self.app.gui.editor.redo_button,
                      self.app.gui.editor.intro_button]
            self.widgits_list.extend(widgits_list)
        self.intro_text_list=test_list[0:8]
        if self.gObjectTimeout != None:
            GObject.source_remove(self.gObjectTimeout)
        self.gObjectTimeout = GObject.timeout_add(1500,self.interactive_overview_show_popup)

    def viewer_overview(self):
        if len(self.widgits_list) == 0:
            widgits_list= [self.app.gui.editor.viewer, self.app.gui.editor.viewer.start_button,
                                self.app.gui.editor.viewer.back_button, self.app.gui.editor.viewer.playpause_button,
                                self.app.gui.editor.viewer.forward_button, self.app.gui.editor.viewer.end_button,
                                self.app.gui.editor.viewer.undock_button,self.app.gui.editor.viewer.timecode_entry,
                                self.app.gui.editor.intro_button]
            self.widgits_list.extend(widgits_list)
        self.intro_text_list=test_list[8:17]
        # if self.gObjectTimeout != None:
        #     GObject.source_remove(self.gObjectTimeout)
        self.gObjectTimeout = GObject.timeout_add(1500,self.interactive_overview_show_popup)

    def timeline_overview(self):
        if len(self.widgits_list) == 0:
            widgits_list= [self.app.gui.editor.timeline_ui.timeline,self.app.gui.editor.timeline_ui.zoom_box,
                           self.app.gui.editor.timeline_ui.timeline.add_layer_button,self.app.gui.editor.timeline_ui.toolbar,
                           self.app.gui.editor.timeline_ui.markers,self.app.gui.editor.intro_button]
            self.widgits_list.extend(widgits_list)
        self.intro_text_list=test_list[17:23]
        # if self.gObjectTimeout != None:
        #     GObject.source_remove(self.gObjectTimeout)
        self.gObjectTimeout = GObject.timeout_add(1500,self.interactive_overview_show_popup)

    def medialibrary_overview(self):
        if len(self.widgits_list) == 0:
            widgits_list= [self.app.gui.editor.medialibrary,self.app.gui.editor.medialibrary._import_button,
                           self.app.gui.editor.medialibrary._clipprops_button,self.app.gui.editor.medialibrary._listview_button,
                           self.app.gui.editor.intro_button]
            self.widgits_list.extend(widgits_list)
        self.intro_text_list=test_list[23:28]
        # if self.gObjectTimeout != None:
        #     GObject.source_remove(self.gObjectTimeout)
        self.gObjectTimeout = GObject.timeout_add(1500,self.interactive_overview_show_popup)

    def effectlist_overview(self):
        if len(self.widgits_list) == 0:
            widgits_list= [self.app.gui.editor.effectlist,self.app.gui.editor.effectlist.audio_togglebutton,
                           self.app.gui.editor.effectlist.view,self.app.gui.editor.intro_button,
                           self.app.gui.editor.intro_button,self.app.gui.editor.intro_button,
                           self.app.gui.editor.intro_button,self.app.gui.editor.intro_button,
                           self.app.gui.editor.intro_button,self.app.gui.editor.intro_button,
                           self.app.gui.editor.intro_button]
            self.widgits_list.extend(widgits_list)
        self.intro_text_list=test_list[28:39]
        # if self.gObjectTimeout != None:
        #     GObject.source_remove(self.gObjectTimeout)
        self.gObjectTimeout = GObject.timeout_add(1500,self.interactive_overview_show_popup)

    def interactive_overview_show_popup(self):
        if self.interactive_intro_index == len(self.widgits_list):
            self.intro_popover.popdown()
            self.current_intro_group_index+=1
            self.emit("run-next-intro", None)
            return False
        self.intro_label.set_markup('<span><b>\n'+str(self.intro_text_list[self.interactive_intro_index])+'</b></span>')
        self.intro_popover.set_relative_to(self.widgits_list[self.interactive_intro_index])
        self.intro_popover.show_all()
        self.intro_popover.popup()
        self.interactive_intro_index+=1
        return True
