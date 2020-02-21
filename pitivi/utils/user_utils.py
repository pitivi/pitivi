# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019 Pitivi project
# Author Jean-Paul Favier
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
import os

from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.timeline import SELECT


class Alert(GObject.Object):
    """Show a window with title and message ; emit a sound if a sound file parameter."""

    def __init__(self, title, message, file_sound=""):
        GObject.Object.__init__(self)
        self.file_sound = file_sound
        self.alert(title, message)

    def alert(self, title, message):
        """Window."""
        self.win = Gtk.Window()
        self.win.set_default_size(200, 100)
        box = Gtk.VBox()
        button = Gtk.Button("OK")
        button.connect("clicked", self.on_clicked_ok)

        self.win.set_title(title)
        label = Gtk.Label(message)

        self.win.add(box)
        box.add(label)
        box.add(button)
        self.win.show_all()
        self.sound(self.file_sound)

# pylint: disable=unused-argument
    def on_clicked_ok(self, widget):
        print("clicked")
        self.win.destroy()

# pylint: disable=no-self-use
    def sound(self, file):
        import sys
#        if sys.platform.startswith("win32"): # Non tested
#            import winsound
#            winsound.PlaySound("xxxxxxxx.wav", winsound.SND_FILENAME)
#    #            winsound.MessageBeep()
        if sys.platform.startswith("linux"):
            dir_sound = os.path.abspath('..')
            # development version
            prepath = "pitivi-prefix/files/share/sounds"
#            # production version
#            prepath = "usr/share/sounds"
            file_sound = os.path.join(dir_sound, prepath,
                                      "freedesktop/stereo/" + file)
#            file_sound = os.path.join(dir_sound,
#                                      "pitivi-prefix/files/share/sounds/freedesktop/stereo/" + file)
            if os.path.isfile(file_sound):
                sound_alert = Gst.ElementFactory.make("playbin", "player")
                sound_alert.set_property('uri', 'file://' + file_sound)
                sound_alert.set_state(Gst.State.PLAYING)


class ChoiceWin(GObject.Object):
    """Show a window with title and question ; emit a sound if there is a sound file parameter."""

    def __init__(self, message="", title="", type_choice="", file_sound=""):

        GObject.Object.__init__(self)
        self.item_type = {"Information": Gtk.MessageType.INFO, "Warning": Gtk.MessageType.WARNING, \
                        "Question": Gtk.MessageType.QUESTION, "Error": Gtk.MessageType.ERROR}
        self.type = type_choice
        self.result = ""
        self.sound(file_sound)
        self.dialog(title, message)

    def dialog(self, title, message):
        self.m_d = Gtk.MessageDialog(None, 0, self.item_type.get(self.type),
                                     Gtk.ButtonsType.OK_CANCEL, title)
        self.m_d.format_secondary_text(message)

        if self.type in self.item_type.keys():
            response = self.m_d.run()
            if response == Gtk.ResponseType.OK:
                print("OK button")
                self.result = "OK"
            elif response == Gtk.ResponseType.CANCEL:
                print("CANCEL button")
                self.result = "CANCEL"
            self.m_d.destroy()
        else:
            self.m_d.destroy()
            print("pass")

# pylint: disable=no-self-use
    def sound(self, file):
        import sys
#        if sys.platform.startswith("win32"): # Non tested
#            import winsound
#            winsound.PlaySound("xxxxxxxx.wav", winsound.SND_FILENAME)
#    #            winsound.MessageBeep()
        if sys.platform.startswith("linux"):
            dir_sound = os.path.abspath('..')
            file_sound = os.path.join(dir_sound,
                                      "pitivi-prefix/files/share/sounds/freedesktop/stereo/" + file)
            if os.path.isfile(file_sound):
                sound_alert = Gst.ElementFactory.make("playbin", "player")
                sound_alert.set_property('uri', 'file://' + file_sound)
                sound_alert.set_state(Gst.State.PLAYING)

class ChoiceWin1(GObject.Object):
    """Show a window with title and question ; emit a sound if there is a sound file parameter."""

    def __init__(self, message="", title="", type_choice="", file_sound=""):

        GObject.Object.__init__(self)
        self.item_type = {"Information": Gtk.MessageType.INFO, "Warning": Gtk.MessageType.WARNING, \
                        "Question": Gtk.MessageType.QUESTION, "Error": Gtk.MessageType.ERROR}
        self.type = type_choice
        self.result = ""
        self.sound(file_sound)
        self.dialog(title, message)

    def dialog(self, title, message):
        self.m_d = Gtk.MessageDialog(None, 0, self.item_type.get(self.type),
                                     Gtk.ButtonsType.CANCEL, "Remove but clip(s) on another layer(s)")
        text_tooltip = "between the start and the end of all selected clips"+\
                    " or selection of non adjacent clips:\n\n" +\
                    "\nClip layer : the layer will not be in sync with other layers" + \
                    "\nAll : all layers are in sync but you delete them (or a part of)"
        self.m_d.format_secondary_text(message)
        self.m_d.add_button("Clip layer\nrippled only", 40)
        self.m_d.add_button("All layers\nrippled", 50)
        self.m_d.set_title(title)
        self.m_d.set_tooltip_text(text_tooltip)

        if self.type in self.item_type.keys():
            response = self.m_d.run()
            if response == 40:
                print("148 Clip")
                self.result = "CLIP"
            elif response == 50:
                print("151 ALL")
                self.result = "ALL"
            elif response == Gtk.ResponseType.CANCEL:
                print("CANCEL button")
                self.result = "CANCEL"
            self.m_d.destroy()
        else:
            self.m_d.destroy()
            print("pass")

# pylint: disable=no-self-use
    def sound(self, file):
        import sys
#        if sys.platform.startswith("win32"): # Non tested
#            import winsound
#            winsound.PlaySound("xxxxxxxx.wav", winsound.SND_FILENAME)
#    #            winsound.MessageBeep()
        if sys.platform.startswith("linux"):
            dir_sound = os.path.abspath('..')
            file_sound = os.path.join(dir_sound,
                                      "pitivi-prefix/files/share/sounds/freedesktop/stereo/" + file)
            if os.path.isfile(file_sound):
                sound_alert = Gst.ElementFactory.make("playbin", "player")
                sound_alert.set_property('uri', 'file://' + file_sound)
                sound_alert.set_state(Gst.State.PLAYING)


class ClipPopupMenu(GObject.Object):
    """Show a window with menu if right click on a clip : delete, copy, cut and split.

    Show another if outside of any clip : paste.
    """

    def __init__(self, app, widget, clip="", layer=None):
        GObject.Object.__init__(self)
        self.app = app
        self.layer = layer
        self.tlc = self.app.gui.editor.timeline_ui  # TimelineContainer
        self.timeline = self.app.gui.editor.timeline_ui.timeline  # timeline
        self.pipeline = self.app.project_manager.current_project.pipeline
        print("tlc ", self.tlc)
        print("tl select = ", self.timeline.selection)
        if clip == "":
            print("140 clip = ", clip)
            self.clip_menu_outside(widget)
        else:
            if sorted(self.timeline.selection) != []:
                print("Selection = ", sorted(self.timeline.selection))
                self.clips = sorted(self.timeline.selection, key=lambda x: x.get_start())
                print("clipscpm = ", self.clips)
                self.clip_menu_on(clip)
            else:
                print("No selection")
                title = "No selection"
                message = "You have to select at least one clip."
                Alert(title, message, "service-logout.oga")
                self.app.gui.editor.focus_timeline()

    def clip_menu_on(self, clip):
        """Popup when right click on a selected clip."""
        popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        b_cp = Gtk.Button(label="Copy")
        vbox.pack_start(b_cp, False, True, 10)
        b_ct = Gtk.Button(label="Cut")
        vbox.pack_start(b_ct, False, True, 10)
        b_dl = Gtk.Button(label="Delete")
        vbox.pack_start(b_dl, False, True, 10)
        b_sp = Gtk.Button(label="Split")
        vbox.pack_start(b_sp, False, True, 10)

        b_dl.connect("clicked", self.delete_clips)
        b_cp.connect("clicked", self.copy_clips)
        b_ct.connect("clicked", self.cut_clips)
        b_sp.connect("clicked", self.split_clip)

        popover.add(vbox)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_relative_to(clip)
        popover.show_all()
        popover.popup()
        print("popup on")

    def clip_menu_outside(self, widget):
        """Popup when right click on a selected clip."""
        popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        b_p = Gtk.Button(label="Paste")
        vbox.pack_start(b_p, False, True, 10)
        vbox.pack_start(Gtk.ModelButton("Xxxx"), False, True, 10)

        b_p.connect("clicked", self.paste_clip)

        popover.add(vbox)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_relative_to(widget)
        popover.show_all()
        popover.popup()
        print("popup out")

    # pylint: disable=unused-argument
    def delete_clips(self, widget):
        self.tlc.dl_clips()
        print("Del")

    # pylint: disable=unused-argument
    def copy_clips(self, widget):
        self.tlc.cp_clips()
        self.app.gui.editor.focus_timeline()

    # pylint: disable=unused-argument
    def cut_clips(self, widget):
        self.tlc.ct_clips()
        self.app.gui.editor.focus_timeline()

    # pylint: disable=unused-argument
    def split_clip(self, widget):
        with self.app.action_log.started("split clip",\
            finalizing_action=CommitTimelineFinalizingAction(self.pipeline), toplevel=True):
            # pylint: disable=protected-access
            self.tlc._split_elements(self.timeline.selection.selected)
            self.timeline.selection.set_selection([], SELECT)
        self.app.gui.editor.focus_timeline()

    # pylint :disable=unused-argument
    def paste_clip(self, widget):
        if not self.tlc.c_p:
            self.tlc.info("Nothing to paste.")
            print("N to p")
            print("Nothing to paste.")
            title = "Nothing to paste."
            message = "You have to copy at least one clip before pasting."
            Alert(title, message, "service-logout.oga")
            self.app.gui.editor.focus_timeline()
            return
        else:
            print("tlc copiedgroup", self.tlc.c_p)
            self.tlc.pst_clips()
            # copy of  tlc.__pasteClipsCb
#            with self.app.action_log.started("paste",
#                        finalizing_action=CommitTimelineFinalizingAction(self.pipeline),
#                        toplevel=True):
#                print("scp1 = ", self.tlc.cp)
#                position = self.tlc._project.pipeline.getPosition()
#                print("position", position)
#                copied_group_shallow_copy = self.tlc.cp.paste(position)
#                print("cgsc = ", copied_group_shallow_copy)
#                try:
#                    self.tlc.cp = copied_group_shallow_copy.copy(True)
#                    self.tlc.cp.props.serialize = False
#                finally:
#                    copied_group_shallow_copy.ungroup(recursive=False)
        self.timeline.selection.set_selection([], SELECT)
        self.app.gui.editor.focus_timeline()
