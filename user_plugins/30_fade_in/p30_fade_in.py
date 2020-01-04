# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019 Pitivi project
# Author Jean-Paul Favier
# Tested with Pitivi 0.98-827-gdd262c24
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

from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Peas

from pitivi.configure import get_pixmap_dir
from pitivi.utils.timeline import SELECT
from pitivi.utils.user_utils import Alert

class FadeIn(GObject.Object, Peas.Activatable):
    """Create a fade in in the selected clip.

    Print is used for debugging goal
    Keyframecurve class in elements.py
    """

    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        #  pylint: disable=attribute-defined-outside-init
        self.app = self.object.app
        dir_img = os.path.join(get_pixmap_dir(), "fadein.svg")
        image = Gtk.Image.new_from_file(dir_img)
        self.fade_in_button = Gtk.ToolButton.new(icon_widget=image)
        self.fade_in_button.show_all()
        self.fade_in_button.set_tooltip_text(" Create a fade in in the selected clip")
#        self.fade_in_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_JUSTIFY_RIGHT)
#        self.fade_in_button.show()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.fade_in_button)
        self.fade_in_button.connect("clicked", self.__clicked_fade_in_cb)

    def __clicked_fade_in_cb(self, unused_button):
        """The video and audio are faded in from the start until the playhead position."""
        #  Undoing action :
        # http://developer.pitivi.org/Advanced_plugin.html
        with self.app.action_log.started("add clip", toplevel=True):
            timeline = self.app.gui.editor.timeline_ui.timeline
            clips = sorted(timeline.selection, key=lambda x: x.get_start())
            if len(clips) == 1:
                clip = clips[0]
                print("clip = ", clip, "\n")
                inpoint = clip.get_inpoint()
                start = clip.get_start()
                end = start + clip.get_duration()
                position = timeline.layout.playhead_position
                print("duration = ", clip.get_duration())
                print("start = ", start)
                #  pylint: disable=chained-comparison
                if inpoint < position and end > position:
                    #  from timeline.py  l 1986
                    ges_track_elements = clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
                    ges_track_elements += clip.find_track_elements(None, GES.TrackType.AUDIO, GES.Source)

                    offset_t = timeline.layout.playhead_position - clip.props.start
                    if offset_t <= 0 or offset_t >= clip.props.duration:
                        return
                    offset_t += clip.props.in_point
                    print("offset_t = ", offset_t)
                    # Put keyframes on the selected clip
                    self.put_keyframes(ges_track_elements, offset_t, inpoint)
                    # Verify
                    if self.app.settings.PlayAfterModif:
                        if start >= 2 * Gst.SECOND:
                            self.app.project_manager.current_project.pipeline.simple_seek(start - 2 * Gst.SECOND)
                        else:
                            self.app.project_manager.current_project.pipeline.simple_seek(0)
                        # Play to easily verify the cut
                        self.app.project_manager.current_project.pipeline.play()
                        self.app.gui.editor.focus_timeline()
                        timeline.selection.set_selection([], SELECT)
                        # End of Verify
                else:
                    Alert("Playhead out of clip",
                          "You have to put the playhead inside the selected clip.", "service-logout.oga")
                    self.app.gui.editor.focus_timeline()
            else:
                Alert("No or too clips", "You have to select one clip.", "service-logout.oga")
                self.app.gui.editor.focus_timeline()

    #  pylint: disable=no-self-use
    def put_keyframes(self, ges_track_elements, offset_t, inpoint):
        # Put keyframes on the selected clip
        for ges_track_element in ges_track_elements:
            keyframe_curve_t = ges_track_element.ui.keyframe_curve
            # Reading only a protected object
            # pylint: disable=protected-access
            offsets = keyframe_curve_t._keyframes.get_offsets()
            print("offsets -1 = ", offsets)
            # case if the keyframes exist, we cannot toggle
            kf_no = 0
            for off in offsets:
                if off[0] == offset_t:
                    print("exists = ", offset_t)
                    kf_no = 1
                    break
#                else:
#                    print("No = ", offset_t)
            if kf_no == 0:
                keyframe_curve_t.toggle_keyframe(offset_t)
        # The keyframes of the inpoint are set to 0.0
        for ges_track_element in ges_track_elements:
            keyframe_curve = ges_track_element.ui.keyframe_curve
            # Reading only a protected object
            # pylint: disable=protected-access
            offsets = keyframe_curve._keyframes.get_offsets()
            # from elements.py (l 244)
            print("kf", keyframe_curve.props)
            print("offsets 0 = ", offsets)
            offset = offsets[0][0]
            offsets[0][1] = 0
            print("offset 2= ", offset, offsets[0][1])
            # Test if keyframes exist between the start and the playhead position and remove them
            for off in offsets:
                print("off[0] = ", off[0])
                if off[0] > 0 and off[0] < offset_t:
                    keyframe_curve.toggle_keyframe(off[0])
            keyframe_curve._move_keyframe(int(offset), inpoint, 0)
            print("offsets = ", offsets)
            print("Fin track --------")

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
