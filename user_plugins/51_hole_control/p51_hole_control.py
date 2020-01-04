# -*- coding: utf-8 -*-
# Tested with Pitivi 0.98-827-gdd262c24
# Pitivi video editor
# Copyright (c) 2019 Pitivi project
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
# Boston, MA 02110-1301, USA.from gi.repository import GObject
import os

from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Peas

from pitivi.configure import get_pixmap_dir
from pitivi.utils.user_utils import Alert

SEC_1 = Gst.SECOND  # 1000000000  # 1 second in nano seconds


class BlackHoleFinder(GObject.Object, Peas.Activatable):
    """Verify if black video is not wished for a render without black.

    The playhead position show the start of the black
    If there is no black the playhead goes to the end of the timeline
    and the popup shows the duration of the film.
    Print is used for debugging goal
    """

    object = GObject.Property(type=GObject.Object)
    #  pylint: disable=attribute-defined-outside-init

    def do_activate(self):
        self.app = self.object.app
        dir_img = os.path.join(get_pixmap_dir(), "question-mark.png")
        image = Gtk.Image.new_from_file(dir_img)
        self.button = Gtk.ToolButton.new(icon_widget=image)
        self.button.set_tooltip_text("Verify if no black video in the timeline")
        self.button.show_all()
#        self.button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_GO_DOWN)
#        self.button.show()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.button)
        self.button.connect("clicked", self.__clicked_hole_search_cb)
#        self.button.connect("clicked", BlackVideoFinder.search_black_video)

    def __clicked_hole_search_cb(self, unused_button):
        """ """
    #  Undoing action :
    # http://developer.pitivi.org/Advanced_plugin.html#making-it-shine
        with self.app.action_log.started("add clip", toplevel=True):
            timeline = self.app.gui.editor.timeline_ui.timeline
            self.duration_timeline = timeline.ges_timeline.props.duration
            print("self.duration_timeline = ", self.duration_timeline)
            timeline.layout.playhead_position = 0

            self.clips = []
            self.media_types = GES.TrackType(0)
            layers = timeline.ges_timeline.get_layers()
            self.list_clips_in_timeline(layers)
            ok = 1
            previous = self.clips[0]
            if previous.get_start() > 0:  # a black at the start of the timeline
                ok = 0
                print("Black hole    ------", timeline.layout.playhead_position)
                self.alert(0)
            else:
                # Now we compare from the second clip
                # Remember the end the most long in all layers
                max_position = previous.get_start() + previous.get_duration()
                for clip_s in self.clips[1:]:
                    if ok == 0:  # a black at the start of the timeline
                        break
                    if clip_s.get_start() <= max_position:
                        if max_position <= clip_s.get_start() + clip_s .get_duration():
                            max_position = clip_s.get_start() + clip_s .get_duration()
                        previous = clip_s
                        print(".")
#                        continue
                    else:
                        # The playhead bar is put on the beginning of the black
                        self.app.project_manager.current_project.pipeline.simple_seek(max_position)
                        ok = 0
                        print("Black hole    ------", timeline.layout.playhead_position)
                        self.alert(max_position)
                        break
            self.app.gui.editor.focus_timeline()
            if ok == 1:
                self.app.project_manager.current_project.pipeline.simple_seek(self.duration_timeline)
                print("No black hole")
                self.alert(self.duration_timeline)

    def list_clips_in_timeline(self, layers):
        for layer in layers:
            for clip_a in layer.get_clips():
                for child in clip_a.get_children(False):
                    track = child.get_track()
                    if not track:
                        continue
                    self.media_types = track.props.track_type
                    # Only video
                    if self.media_types == GES.TrackType.VIDEO:
                        self.clips.append(clip_a)
                        print("clip append = ", clip_a, "\n")
        self.clips = sorted(self.clips, key=lambda x: x.get_start())
        print("Nb of clips", len(self.clips), "\n")

    def alert(self, position):
        position_s = int(position / SEC_1)
        if position == self.duration_timeline:
            title = "Success"
            message = "OK\nNo Black in the video.\nThe duration of the film is :\n"
            message += "     " + self.conversion_h_m_s(position_s)
        else:
            title = "Warning"
            message = "Black in the video at \n"
            message += "     " + self.conversion_h_m_s(position_s) + "\n\n"
            message += " Is it wished ?"
        if title == "Success":
            Alert(title, message, "service-login.oga")
        else:
            Alert(title, message, "service-logout.oga")

    #  pylint: disable=no-self-use
    def conversion_h_m_s(self, time):
        # from https://openclassrooms.com/forum/sujet/python-convertir-des-secondes-en-hh-mm-ss-23739
        message = ""
        hour = int(time / 3600)
        if hour > 0:
            message += str(hour) + " h "
        time %= 3600
        minute = int(time / 60)
        if minute > 0:
            message += str(minute) + " mn "
        time %= 60
        time = int(time)
        message += str(time) + " s"
        return message

    #  pylint: disable=unused-argument
    def on_clicked(self, widget):
        print("clicked")
        self.win.destroy()

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
