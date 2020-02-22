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

from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Peas

from pitivi.configure import get_pixmap_dir
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.timeline import SELECT
from pitivi.utils.user_utils import Alert
from pitivi.utils.user_utils import ChoiceWin1
#from pitivi.utils.user_utils import OverlappingWin
#from pitivi.utils.user_utils import MultiButtonsWin



class ClipsRemoverAndRipple(GObject.Object, Peas.Activatable):
    """Select the clips and click on the toolbar button.

    The clips are copied and removed. The next clips on all the layers are also moved to keep the relative positions
    Like Shortcut : Shift + Del which doesnt work as wanted
    The playhead comes back for 3 seconds before the start of the clip
    The play starts to verify the result

    Print is used for debugging goal
    """

    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        # pylint: disable=attribute-defined-outside-init
        self.app = self.object.app
#        self.button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CUT)
        dir_img = os.path.join(get_pixmap_dir(), "up_cut_ripple.svg")
        if  os.path.isfile(dir_img):
            im = GdkPixbuf.Pixbuf.new_from_file(dir_img)
            image = Gtk.Image.new_from_pixbuf(im)
#            print("im", image)
        self.button = Gtk.ToolButton.new(icon_widget=image)
        self.button.set_tooltip_text("copy and cut the selected clips\n\
        and ripple all the clips after in all the layers\n\
        if the user wants it")
        self.button.show_all()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.button)
        self.button.connect("clicked", self.__clicked_copy_cut_and_slide_cb)

    def __clicked_copy_cut_and_slide_cb(self, unused_button):
        """ """
        # pylint: disable=attribute-defined-outside-init
        self.timeline = self.app.gui.editor.timeline_ui.timeline
#        self.position = self.timeline.layout.playhead_position
        if self.timeline.ges_timeline:
            # Undoing action :
            # http://developer.pitivi.org/Advanced_plugin.html#making-it-shine
            with self.app.action_log.started("delete clip and shift",\
            finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline), \
           toplevel=True):
                start = []
                end = []
                # remove the clips and store their start/end positions
                for clip in self.timeline.selection:
                    if isinstance(clip, GES.TransitionClip):
                        continue
                    start.append(clip.start)
                    print(start)
                    end.append(clip.start + clip.duration)
                if start:
                    self.start_sel = min(start)
                    print("start ", self.start_sel)
                    self.end_sel = max(end)
                    print("end ", self.end_sel)
                    found_overlapping = False
                    # check if any other clips occur during that period
                    found_overlapping = self.test_overlapping()
                    print("found_overlapping = ", found_overlapping)
                    if not found_overlapping:
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
                            self.delete_overlapping(self.start_sel, self.end_sel)
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
                    Alert("No clip", "You have to select at least one clip.", "service-logout.oga")

    def test_overlapping(self):
        """Verify if no clip starts or ends in the timeline selection duration.

        List the clips in ovelapping
        """
        # pylint: disable=chained-comparison
        # pylint: disable=attribute-defined-outside-init
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
                if clip_end > self.start_sel and clip.start < self.end_sel:
                    found_overlapping = True
                    self.list_over.append(clip)
                    print("bk", self.end_sel, clip.start, "---", self.start_sel, clip_end)
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
        print("nfo")
        self.copy_sel()
        for clip in self.timeline.selection:
            layer = clip.get_layer()
            layer.remove_clip(clip)
        # now shift everything following cut time
        shift_by = self.end_sel - self.start_sel
        if self.one_clip is False:
            for layer in self.timeline.ges_timeline.layers:
                for clip in layer.get_clips():
                    if clip.start >= self.end_sel:
                        clip.set_start(clip.start - shift_by)
        else:
            for clip in layer.get_clips():
                if clip.start >= self.end_sel:
                    clip.set_start(clip.start - shift_by)
        if self.app.settings.PlayAfterModif:
            self.verif()

    def copy_sel(self):
        # pylint: disable=protected-access
        print("copy")
        self.app.gui.editor.focus_timeline()
        tlc = self.app.gui.editor.timeline_ui
        group = self.timeline.selection.group()
        print("group = ", group)
        try:
            tlc.__copied_group = group.copy(deep=True)
            print("cpg = ", tlc.__copied_group)
            tlc.__copied_group.props.serialize = False
        finally:
            group.ungroup(recursive=False)
            print("tlc = ", tlc.app.gui.editor.timeline_ui)
            tlc.update_actions()
#        tlc.__copyClipsCb

    def verif(self):
        # Verify : the position is counted in multiple of a frame duration else seek() crashes
        frame_rate = self.app.project_manager.current_project.videorate
        duration_frame = float(Gst.SECOND / frame_rate)
#        print("duration_frame", duration_frame)
        n_frames = int(self.start_sel/duration_frame)
#        print("position", position, n_frames)
        # pylint: disable=attribute-defined-outside-init
        self.start_sel = (n_frames -1) * duration_frame # On the start of the frame position
        if self.start_sel >= 2 * Gst.SECOND:
            self.app.project_manager.current_project.pipeline.simple_seek(self.start_sel - 2 * Gst.SECOND)
        else:
            self.app.project_manager.current_project.pipeline.simple_seek(0)
        # Play to easily verify the cut
        self.app.project_manager.current_project.pipeline.play()
        self.app.gui.editor.focus_timeline()
        # End of Verify
        # Deselect the clips
        self.timeline.selection.set_selection([], SELECT)

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
