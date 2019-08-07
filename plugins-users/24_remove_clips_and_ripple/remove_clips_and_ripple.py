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
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Peas

from pitivi.utils.timeline import SELECT
from pitivi.utils.user_utils import Alert


class ClipsRemoverAndRipple(GObject.Object, Peas.Activatable):
    """ Select the clips and click on the toolbar button
        The clips are removed. The next clips on all the layers are also moved to keep the relative positions
        Like Shortcut : Shift + Del which doesnt work as I want
            The playhead comes back for 3 seconds before the start of the clip
            The play starts to verify the result

        Print is used for debugging goal
        """
    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        # pylint: disable=attribute-defined-outside-init
        self.app = self.object.app
        self.button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_GO_UP)
        self.button.set_tooltip_text("Remove the selected clips\n\
        and ripple all the clips after in all the layers")
        self.button.show()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.button)
        self.button.connect("clicked", self.__clicked_remove_and_slide_cb)

    def __clicked_remove_and_slide_cb(self, unused_button):
        """ """
        # pylint: disable=attribute-defined-outside-init
        self.timeline = self.app.gui.editor.timeline_ui.timeline
        self.position = self.timeline.layout.playhead_position
        if self.timeline.ges_timeline:
            # Undoing action :
            # http://developer.pitivi.org/Advanced_plugin.html#making-it-shine
            with self.app.action_log.started("delete clip and shift", toplevel=True):
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
                        print("nfo")
                        for clip in self.timeline.selection:
                            layer = clip.get_layer()
                            layer.remove_clip(clip)
                        # now shift everything following cut time
                        shift_by = self.end_sel - self.start_sel
                        for layer in self.timeline.ges_timeline.layers:
                            for clip in layer.get_clips():
                                if clip.start >= self.end_sel:
                                    clip.set_start(clip.start - shift_by)
                        if self.app.settings.PlayAfterModif:
                            self.verif()
                    else:
                        title = "Overlapping Error"
                        message = " No action\n\
                    Clip on another layer or selection on non adjacent clips\n \
                    between the start and the end of all selected clips.\n\n\
                    Use delete only and not delete and slide"
                        Alert(title, message, "service-logout.oga")
                        self.timeline.selection.setSelection([], SELECT)
                else:
                    Alert("No clip", "You have to select at least one clip.", "service-logout.oga")

    def test_overlapping(self):
        """ Verify if no clip starts or ends in the timeline selection duration"""
        # pylint: disable=chained-comparison

        found_overlapping = False
        for layer_e in self.timeline.ges_timeline.layers:
            print("Layer = ", layer_e)
            for clip in layer_e.get_clips():
                print("clip = ", clip)
                # The timeline selection is not tested
                if clip in self.timeline.selection:
                    continue
                clip_end = clip.start + clip.duration
                # Test  like TimelineContainer  def _delete_selected_and_shift()
                if clip_end > self.start_sel and clip.start < self.end_sel:
                    found_overlapping = True
                    print("bk", self.end_sel, clip.start, "---", self.start_sel, clip_end)
                    break
            if found_overlapping:
                print("break")
                break
        return found_overlapping

    def verif(self):
        # Verify
        if self.start_sel >= 2 * Gst.SECOND:
            self.app.project_manager.current_project.pipeline.simple_seek(self.start_sel - 2 * Gst.SECOND)
        else:
            self.app.project_manager.current_project.pipeline.simple_seek(0)
        # Play to easily verify the cut
        self.app.project_manager.current_project.pipeline.play()
        self.app.gui.editor.focusTimeline()
        # End of Verify
        # Deselect the clips
        self.timeline.selection.setSelection([], SELECT)

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
