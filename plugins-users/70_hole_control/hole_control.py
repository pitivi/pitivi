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
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas

SEC_1 = 1000000000  # 1 second in nano seconds


class BlackHoleFinder(GObject.Object, Peas.Activatable):
    """ Verify if black video no wished for a render
            The playhead position show the end of the black
            If no black the playhead goes to the end of the timeline.
        Print is used for debugging goal
    """
    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        self.app = self.object.app
        self.button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_GO_DOWN)
        self.button.set_tooltip_text("Verify if no black video in the timeline")
        self.button.show()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.button)
        self.button.connect("clicked", self.__clicked_hole_search_cb)

    def __clicked_hole_search_cb(self, unused_button):
        """ """
    #  Undoing action :
    # http://developer.pitivi.org/Advanced_plugin.html#making-it-shine
        with self.app.action_log.started("add clip", toplevel=True):
            timeline = self.app.gui.editor.timeline_ui.timeline
            self.duration_timeline = timeline.ges_timeline.props.duration
            print("self.duration_timeline = ", self.duration_timeline)
            timeline.layout.playhead_position = 0

            clips = []
            self.media_types = GES.TrackType(0)
            layers = timeline.ges_timeline.get_layers()
            for layer in layers:
                for clip_a in layer.get_clips():
                    for child in clip_a.get_children(False):
                        track = child.get_track()
                        if not track:
                            continue
                        self.media_types = track.props.track_type
                        # Only video
                        if self.media_types == GES.TrackType.VIDEO:
                            clips.append(clip_a)
                            print("clip append = ", clip_a, "\n")
            clips = sorted(clips, key=lambda x: x.get_start())
            print("Nb of clips", len(clips), "\n")
            ok = 1
            previous = clips[0]
            if previous.get_start() > 0:  # a black at the start of the timeline
                ok = 0
                print("Black hole    ------", timeline.layout.playhead_position)
                self.sound()
                self.alert(0)
            else:
                pass
                # Now we compare from the second clip
                # Remember the end the most long in all layers
                max_position = previous.get_start() + previous.get_duration()
                for clip_s in clips[1:]:
                    if ok == 0:  # a black at the start of the timeline
                        break
                    if clip_s.get_start() <= max_position:
                        if max_position <= clip_s.get_start() + clip_s .get_duration():
                            max_position = clip_s.get_start() + clip_s .get_duration()
                        previous = clip_s
                        print(".")
                        continue
                    else:
                        # The playhead is put on the beginning of the black
                        timeline.layout.playhead_position = max_position
                        timeline.layout.queue_draw()
                        ok = 0
                        print("Black hole    ------", timeline.layout.playhead_position)
                        self.sound()
                        self.alert(max_position)
                        break
            self.app.gui.editor.focusTimeline()
            if ok == 1:
                timeline.layout.playhead_position = self.duration_timeline
                timeline.layout.queue_draw()
                print("No black hole")
                self.alert(max_position)

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)

    def alert(self, position):
        win = Gtk.Window()
        win.set_default_size(200, 100)
        position_s = int(position / SEC_1)
        if position == self.duration_timeline:
            win.set_title("Success")
            message = "OK\nNo Black in the video.\nThe duration of the film is :\n"
            message += self.conversion_h_m_s(position_s)
        else:
            win.set_title("Warning")
            message = "Black in the video at \n"
            message += self.conversion_h_m_s(position_s) + "\n\n"
            message += " Is it wished ?"
        label = Gtk.Label(message)
        win.add(label)
        win.show_all()

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

    def sound(self):
        #  TODO
        pass
#        import sys
# #        if sys.platform.startswith("win32"): # Non tested
# #            import winsound
# #            winsound.PlaySound("/usr/share/sounds/purple/alert.wav", winsound.SND_FILENAME)
# ##            winsound.MessageBeep()
#        if sys.platform.startswith("linux"):
#            import os
#            # aplay is an unknown command in the development environnement
#            os.system("aplay /usr/share/sounds/purple/alert.wav")
