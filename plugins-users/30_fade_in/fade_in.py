# Tested with Pitivi 0.98-827-gdd262c24
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas


class FadeIn(GObject.Object, Peas.Activatable):
    """ Create a fade in in the selected clip.
        Print is used for debugging goal
        Keyframecurve class in elements.py

    """
    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        self.app = self.object.app
        self.fade_in_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_JUSTIFY_RIGHT)
        self.fade_in_button.set_tooltip_text(" Create a fade in in the selected clip")
        self.fade_in_button.show()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.fade_in_button)
        self.fade_in_button.connect("clicked", self.__clicked_fade_in_cb)

    def __clicked_fade_in_cb(self, unused_button):
        """The video and audio are faded in from the start until the playhead position """
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
                print("duration = ", clip.get_duration())
                print("start = ", start)
            #  from timeline l 1986
                ges_track_elements = clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
                ges_track_elements += clip.find_track_elements(None, GES.TrackType.AUDIO, GES.Source)

                offset_t = timeline.layout.playhead_position - clip.props.start
                if offset_t <= 0 or offset_t >= clip.props.duration:
                    return
                offset_t += clip.props.in_point
                print("offset_t = ", offset_t)
                # Put keyframes on the selected clip
                for ges_track_element in ges_track_elements:
                    keyframe_curve_t = ges_track_element.ui.keyframe_curve
                    offsets = keyframe_curve_t._keyframes.get_offsets()
                    print("offsets -1 = ", offsets)
                    keyframe_curve_t.toggle_keyframe(offset_t)
                # The keyframes of the inpoint are set to 0.0
                for ges_track_element in ges_track_elements:
                    keyframe_curve = ges_track_element.ui.keyframe_curve
                    offsets = keyframe_curve._keyframes.get_offsets()
                    # from elements.py (l 244)
                    print("kf", keyframe_curve.props)
                    print("offsets 0 = ", offsets)
                    offset = offsets[0][0]
                    offsets[0][1] = 0
                    print("offset 2= ", offset, offsets[0][1])
                    keyframe_curve._move_keyframe(int(offset), inpoint, 0)
                    print("offsets = ", offsets)
                    print("Fin track --------")

    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)

    def _keyframe_cb(self, timeline):
        """Put a keyframe on the selected clip.
            comes from timeline.py line 1980 """
        ges_clip = timeline.selection.getSingleClip(GES.Clip)
        if ges_clip is None:
            return
        ges_track_elements = ges_clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
        ges_track_elements += ges_clip.find_track_elements(None, GES.TrackType.AUDIO, GES.Source)

        offset = timeline.layout.playhead_position - ges_clip.props.start
#        offset = self._project.pipeline.getPosition() - ges_clip.props.start
        if offset <= 0 or offset >= ges_clip.props.duration:
            return
        offset += ges_clip.props.in_point

        with self.app.action_log.started("Toggle keyframe", toplevel=True):
            for ges_track_element in ges_track_elements:
                keyframe_curve = ges_track_element.ui.keyframe_curve
                keyframe_curve.toggle_keyframe(offset)
#    project = self.timeline.app.project_manager.current_project
