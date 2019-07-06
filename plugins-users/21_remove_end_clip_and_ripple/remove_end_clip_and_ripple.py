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
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas


class EndClipRemoverAndMove(GObject.Object, Peas.Activatable):
    """ Put the playhead on the last image of the new clip
        Select the clip and click on the toolbar button
        The end of the clip is removed
        The clips whose start is after the playhead position are also moved to keep the relative positions
        Limitation ! if a clip is in another layer and there is a gap with the next clip
            if the gap is < the removed part
        it is moved but  makes  a crossfade with the next clip
        TODO
            The playhead comes back for 2 seconds before the new end of the clip (playhead position)
            The play becomes on to verify the result

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

        with self.app.action_log.started("add clip", toplevel=True):
            timeline = self.app.gui.editor.timeline_ui.timeline
            duration_timeline = timeline.ges_timeline.props.duration
            position = timeline.layout.playhead_position
            print("duration_timeline = ", duration_timeline)
            print("position = ", position)
            clips = sorted(timeline.selection, key=lambda x: x.get_start())
            # If only a clip selected
            if len(clips) == 1:
                clip = clips[0]
                start = clip.get_start()
                end = start + clip.get_duration()
                gap = end - position
                # if the playhead is inside the selected clip, operate
                if start < position and end > position:
                    # We create a new clip wich was the end of the selected clip
                    clip.split(position)

        # Slide the clips after the playhead position
                    clips_after = []  # List of the clips after the playhead_position
                    layers = timeline.ges_timeline.get_layers()
                    for layer in layers:
                        for clip_a in layer.get_clips():
                            if clip_a.get_start() >= position:
                                clips_after.append(clip_a)
                                print("clip append = ", clip_a, "\n")
                    # clips sorted by the starts of the clips
                    clips_after = sorted(clips_after, key=lambda x: x.get_start())
                    print("------- fin append")

                    for clip_aa in clips_after:
                        # The first clip (= end of the selected clip) is removed
                        if clip_aa == clips_after[0]:
                            l_parent = clip_aa.get_layer()
                            print("Parent = ", l_parent)
                            l_parent.remove_clip(clip_aa)
                            continue
                        ec = clip_aa.get_start() - gap
                        print("start", clip_aa.get_start(), "gap = ", gap, "ec = ", ec, "\n")
                        clip_aa.set_start(ec)
                        print("clip modif = ", clip_aa, "\n")
                    duration_timeline = timeline.ges_timeline.props.duration
                    print("duration_timeline = ", duration_timeline)
        # End of Slide the clips after the playhead position

#        # Verify
#                    # put the playhead 2 seconds before the start of the clip
#                    timeline.layout.playhead_position = start - SEC_2
# TODO The play bar moves but not the position in the pipeline
# #                    print(self.app.project_manager.current_project.pipeline.getPosition())
#                    print("position - 2 = ", position, start, timeline.layout.playhead_position)
#                    # Play to easily verify the cut
#                    self.app.project_manager.current_project.pipeline.play()
#                    self.app.gui.editor.focusTimeline()
#        # End of Verify

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
