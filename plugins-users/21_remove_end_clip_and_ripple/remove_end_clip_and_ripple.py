# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019 Pitivi project
# Author Jean-Paul Favier
# Tested with Pitivi 0.98-827-gdd262c24
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
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Peas

from pitivi.utils.timeline import SELECT
from pitivi.utils.user_utils import Alert


class EndClipRemoverAndMove(GObject.Object, Peas.Activatable):
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=too-many-instance-attributes
    """ Put the playhead on the last image of the new clip
        Select the clip and click on the toolbar button
        The end of the clip is removed
        The clips whose start is after the playhead position are also moved to keep the relative positions
            The playhead comes back for 3 seconds before the new end of the clip (playhead position)
            The play starts to verify the result
        Print is used for debugging goal
        """

    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        self.app = self.object.app
        self.button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_GOTO_LAST)
        self.button.set_tooltip_text("Remove the end of the selected clip and ripple")
        self.button.show()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.button)
        self.button.connect("clicked", self.__clicked_end_part_cb)

    def __clicked_end_part_cb(self, unused_button):
        """ The playhead need to be inside a selected clip """

        # Undoing action :
        # http://developer.pitivi.org/Advanced_plugin.html#making-it-shine
        with self.app.action_log.started("add clip", toplevel=True):
            self.timeline = self.app.gui.editor.timeline_ui.timeline
            duration_timeline = self.timeline.ges_timeline.props.duration
            self.position = self.timeline.layout.playhead_position
            print("duration_timeline = ", duration_timeline)
            print("position = ", self.position)

            clips = sorted(self.timeline.selection, key=lambda x: x.get_start())
            print("clips = ", clips)
            if len(clips) == 1:
                self.clip = clips[0]
                self.layer_c = self.clip.get_layer()
                self.start = self.clip.get_start()
                self.end = self.start + self.clip.get_duration()
                self.gap = self.end - self.position
                clips_after_s = self.clip_after_position_sort()
                # check if any other clips occur during the clip
                found_overlapping = self.test_overlapping()
                print("found_overlapping = ", found_overlapping)
                if not found_overlapping:
                    # operate if the playhead is inside the selected clip
                    # pylint: disable=chained-comparison
                    if self.start < self.position and self.end > self.position:
                        # We create a new clip wich was the end of the selected clip and remove it
                        clip_r = self.clip.split(self.position)
                        self.layer_c.remove_clip(clip_r)
                        for clip_aa in clips_after_s:
                            ec = clip_aa.get_start() - self.gap
                            print("start", clip_aa.get_start(), "gap = ", self.gap, "ec = ", ec, "\n")
                            clip_aa.set_start(ec)
                            print("clip modif = ", clip_aa, "\n")
                        if self.app.settings.PlayAfterModif:
                            self.verif()
                    else:
                        title = "Playhead out of clip"
                        message = "You have to put the playhead inside the clip."
                        Alert(title, message, "service-logout.oga")
                else:
                    title = "Overlapping Error"
                    message = " No action\n\
                Clip(s) on another layer(s)\n \
                between the start and the end of selected clip.\n\n\
                Use delete only and not delete and slide"
                    Alert(title, message, "service-logout.oga")
            else:
                Alert("No or too clips", "You have to select one clip.", "service-logout.oga")
                # End of Slide the clips after the playhead position

    def test_overlapping(self):
        found_overlapping = False
        for layer_e in self.timeline.ges_timeline.layers:
            print("Layer = ", layer_e)
            for clip in layer_e.get_clips():
                print("clip = ", clip)
                if clip in self.timeline.selection:
                    continue
                clip_end = clip.start + clip.duration
                # Test like TimelineContainer  def _delete_selected_and_shift()
                if clip_end > self.position and clip.start < self.end:
                    found_overlapping = True
                    print("bk", self.end, clip.start, "---", self.start, clip_end)
                    break
            if found_overlapping:
                print("break")
                break
        return found_overlapping

    def clip_after_position_sort(self):
        # List of the clips after the playhead_position
        clips_after = []
        layers = self.timeline.ges_timeline.get_layers()
        for layer in layers:
            for clip_a in layer.get_clips():
                if clip_a.get_start() >= self.position:
                    clips_after.append(clip_a)
                    print("clip append = ", clip_a, "\n")
        # clips sorted by the starts of the clips
        clips_after = sorted(clips_after, key=lambda x: x.get_start())
        print("------- fin append")
        return clips_after

    def operate(self):
        self.clip.split(self.position)
        # Slide the clips after the playhead position
        for layer in self.timeline.ges_timeline.layers:
            for clip_aa in layer.get_clips():
                if clip_aa.get_start() >= self.start:
                    # The first clip (= start of the selected clip) is removed
                    if clip_aa.get_start() == self.start and clip_aa.get_layer() == self.layer_c:
                        self.layer_c.remove_clip(clip_aa)
                        continue
                    # If the start of the first clip is 0 ec = 0
                    if clip_aa.get_start() == 0:
                        ec = 0
                    else:
                        ec = clip_aa.get_start() - self.gap
                    clip_aa.set_start(ec)
                    print("start", clip_aa.get_start(), "gap = ", self.gap, "ec = ", ec, "\n")
                    print("clip modif = ", clip_aa, "\n")
        if self.app.settings.PlayAfterModif:
            self.verif()
        # End of Slide the clips after the playhead position

    def verif(self):
        # Verify
        if self.position >= 2 * Gst.SECOND:
            self.app.project_manager.current_project.pipeline.simple_seek(self.position - 2 * Gst.SECOND)
        else:
            self.app.project_manager.current_project.pipeline.simple_seek(0)
        # Play to easily verify the cut
        self.app.project_manager.current_project.pipeline.play()
        self.app.gui.editor.focusTimeline()
        # End of Verify
        # Deselect the clip
        self.timeline.selection.setSelection([], SELECT)

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
