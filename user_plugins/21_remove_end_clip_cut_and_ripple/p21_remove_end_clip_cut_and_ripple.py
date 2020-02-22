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
import os

from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Peas

from pitivi.utils.timeline import SELECT
from pitivi.utils.user_utils import Alert
from pitivi.utils.user_utils import ChoiceWin1


class EndClipRemoverCutAndRipple(GObject.Object, Peas.Activatable):
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=too-many-instance-attributes
    """The end of the clip is removed.

    Put the playhead on the last image of the new clip
    Select the clip and click on the toolbar button
    The end of the clip is removed
    The clips whose start is after the playhead position are also moved to keep the relative positions
    The playhead comes back for 2 seconds before the new end of the clip (playhead position)
    The play starts to verify the result
    Print is used for debugging goal
    """

    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        self.app = self.object.app
        self.button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_GOTO_LAST)
        self.button.set_tooltip_text("Remove the end of the selected clip,cut if wanted and ripple")
        self.button.show()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.button)
        self.button.connect("clicked", self.__clicked_end_part_cb)

    def __clicked_end_part_cb(self, unused_button):
        """The playhead need to be inside a selected clip."""
        # Undoing action :
        # http://developer.pitivi.org/Advanced_plugin.html#making-it-shine
        with self.app.action_log.started("delete clip and shift", toplevel=True):
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
                if self.start < self.position and self.end > self.position:
                    # check if any other clips occur during the clip
                    found_overlapping = self.test_overlapping()
                    print("found_overlapping = ", found_overlapping)
                    if not found_overlapping:
                        # if the playhead is inside the selected clip, operate
                        # pylint: disable=chained-comparison
                        self.operate_slide()
                    else:
                        title = "Overlapping"
                        text = ""
                        for l_o in self.list_over:
                            file_m = os.path.basename(l_o.get_asset().props.id)
                            text += file_m+"\n"  # .split(".")[0]
                        message = text
                        type_m = "Warning"
                        file_sound = "window-attention.oga"
                        choice = ChoiceWin1(message, title, type_m, file_sound)
                        print("choice = ", choice.result)
                        if choice.result == "ALL":
                            self.one_clip = False
                            self.delete_overlapping(self.start, self.end)
                            self.operate_slide()
                            self.timeline.selection.set_selection([], SELECT)
                            self.app.gui.editor.focus_timeline()
                        elif choice.result == "CLIP":
                            print("clip choosed")
                            self.one_clip = True
                            self.operate_slide()
                            self.timeline.selection.set_selection([], SELECT)
                            self.app.gui.editor.focus_timeline()
                        elif choice.result == "CANCEL":
                            self.timeline.selection.set_selection([], SELECT)
                        else:
                            pass
                else:
                    message = "You have to put the playhead inside the clip."
                    Alert("Playhead out of clip", message, "service-logout.oga")
            else:
                Alert("No or too clips", "You have to select one clip.", "service-logout.oga")
                self.timeline.selection.set_selection([], SELECT)

    def test_overlapping(self):
        """Verify if no clip starts or ends in the timeline selection duration.

        List the clips in ovelapping
        """
        # pylint: disable=chained-comparison
        found_overlapping = False
        self.list_over = []
        for layer_e in self.timeline.ges_timeline.layers:
            print("Layer = ", layer_e)
            for clip in layer_e.get_clips():
                print("clip = ", clip.name)
                # The timeline selection is not tested
                if clip in self.timeline.selection:
                    continue
                clip_end = clip.start + clip.duration
                # Test  like TimelineContainer  def _delete_selected_and_shift()
                if clip_end > self.position and clip.start < self.end:
                    found_overlapping = True
                    self.list_over.append(clip)
                    print("bk", self.end, ">", clip.start, "---", self.start, "<", clip_end)
        return found_overlapping

    def delete_overlapping(self, start_delet, end_delet):
        for l_o in  self.list_over:
            l_o_end = l_o.start + l_o.duration
            # Four cases
            # inside the selection
            case_inside = l_o.start >= start_delet and l_o_end <= end_delet
            # start outside the selection, end inside the selection
            case_start_outside = l_o.start < start_delet and l_o_end <= end_delet
            # start inside the selection, end outside the selection
            case_end_outside = l_o.start >= start_delet and l_o_end > end_delet
            # start outside the selection, end outside the selection
            case_start_end_outside = l_o.start < start_delet and l_o_end > end_delet
            if case_inside:
                lay = l_o.get_layer()
                lay.remove_clip(l_o)
                continue
            if case_start_outside:
                cut = l_o.split(start_delet)
                lay = cut.get_layer()
                lay.remove_clip(cut)
                continue
            if case_end_outside:
                l_o.split(end_delet)
                lay = l_o.get_layer()
                lay.remove_clip(l_o)
                continue
            if case_start_end_outside:
                cut = l_o.split(start_delet)
                print("cut = ", cut)
                clip_r = cut.split(end_delet)
                print("clip_r = ", clip_r)
                lay = cut.get_layer()
                lay.remove_clip(cut)
                continue

    def operate_slide(self):
        clip_r = self.clip.split(self.position)
        self.layer_c.remove_clip(clip_r)
        # Slide the clips after the playhead position
        for layer in self.timeline.ges_timeline.layers:
            for clip_aa in layer.get_clips():
                if clip_aa.get_start() >= self.position:
                    # The first clip (= start of the selected clip) is removed
#                    if clip_aa.get_start() == self.start and clip_aa.get_layer() == self.layer_c:
#                        self.layer_c.remove_clip(clip_aa)
#                        continue
                    # If the start of the first clip is 0 ec = 0
#                    if clip_aa.get_start() == 0:
#                        ec = 0
#                    else:
                    ec = clip_aa.get_start() - self.gap
                    clip_aa.set_start(ec)
                    print("start", clip_aa.get_start(), "gap = ", self.gap, "ec = ", ec, "\n")
                    print("clip modif = ", clip_aa, "\n")
        if self.app.settings.PlayAfterModif:
            self.verif()
        # End of Slide the clips after the playhead position

#    def verif(self):
#        """Play after the remove of the clip end.
#
#        The playhead goes back two seconds or at timeline start
#        """
#        # Verify : the position is counted in multiple of a frame duration else seek() crashes
#        if self.position >= 2 * Gst.SECOND:
#            self.app.project_manager.current_project.pipeline.simple_seek(self.position - 2 * Gst.SECOND)
#        else:
#            self.app.project_manager.current_project.pipeline.simple_seek(0)
#        # Play to easily verify the cut
#        self.app.project_manager.current_project.pipeline.play()
#        self.app.gui.editor.focus_timeline()
#        # End of Verify
#        # Deselect the clip
#        self.timeline.selection.set_selection([], SELECT)

    def verif(self):
        """Play after the remove of the clip end.

        The playhead goes back two seconds or at timeline start
        """
        # Verify : the position is counted in multiple of a frame duration else seek() crashes
        frame_rate = self.app.project_manager.current_project.videorate
        duration_frame = float(Gst.SECOND / frame_rate)
        n_frames = int(self.position/duration_frame)
        self.position = (n_frames -1) * duration_frame # On the start of the frame position
        if self.position >= 2 * Gst.SECOND:
            self.app.project_manager.current_project.pipeline.simple_seek(self.position - 2 * Gst.SECOND)
        else:
            self.app.project_manager.current_project.pipeline.simple_seek(0)
        # Play to easily verify the cut
        self.app.project_manager.current_project.pipeline.play()
        self.app.gui.editor.focus_timeline()
        # End of Verify
        # Deselect the clip
        self.timeline.selection.set_selection([], SELECT)

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
