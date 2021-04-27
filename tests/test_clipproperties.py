# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2014, Alex Băluț <alexandru.balut@gmail.com>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Tests for the pitivi.clipproperties module."""
# pylint: disable=protected-access,no-self-use,import-outside-toplevel,no-member
import tempfile
from unittest import mock

from gi.repository import GES
from gi.repository import Gst

from tests import common


class TransformationPropertiesTest(common.TestCase):
    """Tests for the TransformationProperties widget."""

    @common.setup_timeline
    @common.setup_clipproperties
    def test_spin_buttons_read(self):
        """Checks the spin buttons update when the source properties change."""
        timeline = self.transformation_box.app.gui.editor.timeline_ui.timeline
        spin_buttons = self.transformation_box.spin_buttons

        # Add a clip and select it
        clip = self.add_clips_simple(timeline, 1)[0]
        timeline.selection.select([clip])

        # Check that spin buttons display the correct values by default
        source = self.transformation_box.source
        self.assertIsNotNone(source)
        for prop in ["posx", "posy", "width", "height"]:
            self.assertIn(prop, spin_buttons)
            ret, source_value = source.get_child_property(prop)
            self.assertTrue(ret)
            spin_btn_value = spin_buttons[prop].get_value_as_int()
            self.assertEqual(spin_btn_value, source_value)

        # Change the source properties and check the spin buttons update
        # correctly.
        new_values = {"posx": 20, "posy": -50, "width": 70, "height": 450}
        for prop, new_val in new_values.items():
            self.assertTrue(source.set_child_property(prop, new_val))
            spin_btn_value = spin_buttons[prop].get_value_as_int()
            self.assertEqual(new_val, spin_btn_value)

    @common.setup_timeline
    @common.setup_clipproperties
    def test_clip_size_aspect_ratio_lock(self):
        """Checks if aspect ratio is maintained when clip size is linked."""
        # Add a clip and select it
        clip = self.add_clips_simple(self.timeline_container.timeline, 1)[0]
        self.timeline_container.timeline.selection.select([clip])
        source = self.transformation_box.source
        self.assertIsNotNone(source)

        self._check_aspect_ratio_constraining(source, initial_size=(960, 400), width=1440, height=None, expected_width=None, expected_height=600)
        self._check_aspect_ratio_constraining(source, initial_size=(320, 240), width=None, height=720, expected_width=960, expected_height=None)
        self._check_aspect_ratio_constraining(source, initial_size=(100, 100), width=25, height=None, expected_width=None, expected_height=25)

    def _check_aspect_ratio_constraining(self, source, initial_size, width, height, expected_width, expected_height):
        width_spin = self.transformation_box.spin_buttons["width"]
        height_spin = self.transformation_box.spin_buttons["height"]
        width_spin.set_value(initial_size[0])
        height_spin.set_value(initial_size[1])

        # Lock the aspect ratio.
        self.clipproperties.transformation_expander._aspect_ratio_button_clicked_cb(None)
        self.assertIsNotNone(self.clipproperties.transformation_expander._aspect_ratio)

        # Make a change to one of the spin button's value.
        if width is not None:
            width_spin.set_value(width)
            expected_width = width
        if height is not None:
            height_spin.set_value(height)
            expected_height = height
        self.assertEqual(source.get_child_property("width"), (True, expected_width))
        self.assertEqual(source.get_child_property("height"), (True, expected_height))

        # Unlock the aspect ratio.
        self.clipproperties.transformation_expander._aspect_ratio_button_clicked_cb(None)
        self.assertIsNone(self.clipproperties.transformation_expander._aspect_ratio)

        # Change the width independently.
        width_spin.set_value(expected_width * 2)
        self.assertEqual(source.get_child_property("width"), (True, expected_width * 2))
        self.assertEqual(source.get_child_property("height"), (True, expected_height))

        # Change the height independently.
        height_spin.set_value(expected_height * 4)
        self.assertEqual(source.get_child_property("width"), (True, expected_width * 2))
        self.assertEqual(source.get_child_property("height"), (True, expected_height * 4))

    @common.setup_timeline
    @common.setup_clipproperties
    def test_spin_buttons_write(self):
        """Checks the spin buttons changing updates the source properties."""
        timeline = self.transformation_box.app.gui.editor.timeline_ui.timeline
        spin_buttons = self.transformation_box.spin_buttons

        # Add a clip and select it
        clip = self.add_clips_simple(timeline, 1)[0]
        timeline.selection.select([clip])
        source = self.transformation_box.source
        self.assertIsNotNone(source)

        # Get current spin buttons values
        current_spin_values = {}
        for prop in ["posx", "posy", "width", "height"]:
            current_spin_values[prop] = spin_buttons[prop].get_value_as_int()

        changes = [
            ("posx", -300), ("posy", 450), ("width", 1), ("height", 320),
            ("posx", 230), ("posx", 520), ("posy", -10), ("posy", -1000),
            ("width", 600), ("width", 1000), ("height", 1), ("height", 1000)
        ]

        # Change the spin buttons values and check the source properties are
        # updated correctly.
        for prop, new_value in changes:
            spin_buttons[prop].set_value(new_value)
            current_spin_values[prop] = new_value
            for source_prop in ["posx", "posy", "width", "height"]:
                ret, source_value = source.get_child_property(source_prop)
                self.assertTrue(ret)
                self.assertEqual(current_spin_values[source_prop], source_value)

    @common.setup_timeline
    @common.setup_clipproperties
    def test_spin_buttons_source_change(self):
        """Checks the spin buttons update when the selected clip changes."""
        timeline = self.transformation_box.app.gui.editor.timeline_ui.timeline
        spin_buttons = self.transformation_box.spin_buttons

        # Add two clips and select the first one
        clips = self.add_clips_simple(timeline, 2)
        timeline.selection.select([clips[0]])
        source = self.transformation_box.source
        self.assertIsNotNone(source)

        # Change the spin buttons values
        new_values = {"posx": 45, "posy": 10, "width": 450, "height": 25}
        for prop, new_val in new_values.items():
            spin_buttons[prop].set_value(new_val)

        # Select the second clip and check the spin buttons values update
        # correctly
        timeline.selection.select([clips[1]])
        source = self.transformation_box.source
        self.assertIsNotNone(source)
        for prop in ["posx", "posy", "width", "height"]:
            ret, source_value = source.get_child_property(prop)
            self.assertTrue(ret)
            self.assertEqual(spin_buttons[prop].get_value_as_int(), source_value)

        # Select the first clip again and check spin buttons values
        timeline.selection.select([clips[0]])
        for prop in ["posx", "posy", "width", "height"]:
            self.assertEqual(spin_buttons[prop].get_value_as_int(), new_values[prop])

    @common.setup_timeline
    @common.setup_clipproperties
    def test_keyframes_activate(self):
        """Checks transformation properties keyframes activation."""
        timeline = self.transformation_box.app.gui.editor.timeline_ui.timeline

        # Add a clip and select it
        clip = self.add_clips_simple(timeline, 1)[0]
        timeline.selection.select([clip])
        source = self.transformation_box.source
        self.assertIsNotNone(source)
        inpoint = source.props.in_point
        duration = source.props.duration

        # Check keyframes are deactivated by default
        for prop in ["posx", "posy", "width", "height"]:
            self.assertIsNone(source.get_control_binding(prop))

        # Get current source properties
        initial_values = {}
        for prop in ["posx", "posy", "width", "height"]:
            ret, value = source.get_child_property(prop)
            self.assertTrue(ret)
            initial_values[prop] = value

        # Activate keyframes and check the default keyframes are created
        self.transformation_box._activate_keyframes_btn.set_active(True)
        for prop in ["posx", "posy", "width", "height"]:
            control_binding = source.get_control_binding(prop)
            self.assertIsNotNone(control_binding)
            control_source = control_binding.props.control_source
            keyframes = [(item.timestamp, item.value) for item in control_source.get_all()]
            self.assertEqual(keyframes, [(inpoint, initial_values[prop]),
                                         (inpoint + duration, initial_values[prop])])

    @common.setup_timeline
    @common.setup_clipproperties
    def test_keyframes_add(self):
        """Checks keyframe creation."""
        timeline = self.transformation_box.app.gui.editor.timeline_ui.timeline
        pipeline = timeline._project.pipeline
        spin_buttons = self.transformation_box.spin_buttons

        # Add a clip and select it
        clip = self.add_clips_simple(timeline, 1)[0]
        timeline.selection.select([clip])
        source = self.transformation_box.source
        self.assertIsNotNone(source)
        start = source.props.start
        inpoint = source.props.in_point
        duration = source.props.duration

        # Activate keyframes
        self.transformation_box._activate_keyframes_btn.set_active(True)

        # Add some more keyframes
        offsets = [1, int(duration / 2), duration - 1]
        for prop in ["posx", "posy", "width", "height"]:
            for index, offset in enumerate(offsets):
                timestamp, value = inpoint + offset, offset * 10
                with mock.patch.object(pipeline, "get_position") as get_position:
                    get_position.return_value = start + offset
                    spin_buttons[prop].set_value(value)

                control_source = source.get_control_binding(prop).props.control_source
                keyframes = [(item.timestamp, item.value) for item in control_source.get_all()]
                self.assertEqual((timestamp, value), keyframes[index + 1])

    @common.setup_timeline
    @common.setup_clipproperties
    def test_keyframes_navigation(self):
        """Checks keyframe navigation."""
        timeline = self.transformation_box.app.gui.editor.timeline_ui.timeline
        pipeline = timeline._project.pipeline

        # Add a clip and select it
        clip = self.add_clips_simple(timeline, 1)[0]
        timeline.selection.select([clip])
        source = self.transformation_box.source
        self.assertIsNotNone(source)
        start = source.props.start
        inpoint = source.props.in_point
        duration = source.props.duration

        # Activate keyframes and add some more keyframes
        self.transformation_box._activate_keyframes_btn.set_active(True)
        offsets = [1, int(duration / 2), duration - 1]
        for prop in ["posx", "posy", "width", "height"]:
            for offset in offsets:
                timestamp, value = inpoint + offset, offset * 10
                control_source = source.get_control_binding(prop).props.control_source
                control_source.set(timestamp, value)

        # Add edge keyframes in the offsets array
        offsets.insert(0, 0)
        offsets.append(duration)

        # Test keyframe navigation
        prev_index = 0
        next_index = 1
        for position in range(duration + 1):
            prev_keyframe_ts = offsets[prev_index] + inpoint
            next_keyframe_ts = offsets[next_index] + inpoint

            with mock.patch.object(pipeline, "get_position") as get_position:
                get_position.return_value = start + position
                with mock.patch.object(pipeline, "simple_seek") as simple_seek:
                    self.transformation_box._prev_keyframe_btn.clicked()
                    simple_seek.assert_called_with(prev_keyframe_ts)
                    self.transformation_box._next_keyframe_btn.clicked()
                    simple_seek.assert_called_with(next_keyframe_ts)

            if position + 1 == next_keyframe_ts and next_index + 1 < len(offsets):
                next_index += 1
            if position in offsets and position != 0:
                prev_index += 1

    @common.setup_timeline
    @common.setup_clipproperties
    def test_reset_to_default(self):
        """Checks "reset to default" button."""
        timeline = self.transformation_box.app.gui.editor.timeline_ui.timeline

        # Add a clip and select it
        clip = self.add_clips_simple(timeline, 1)[0]
        timeline.selection.select([clip])
        source = self.transformation_box.source
        self.assertIsNotNone(source)

        # Change source properties
        new_values = {"posx": 20, "posy": -50, "width": 70, "height": 450}
        for prop, new_val in new_values.items():
            self.assertTrue(source.set_child_property(prop, new_val))

        # Activate keyframes
        self.transformation_box._activate_keyframes_btn.set_active(True)

        # Press "reset to default" button
        clear_button = self.transformation_box.builder.get_object("clear_button")
        clear_button.clicked()

        # Check that control bindings were erased and the properties were
        # reset to their default values
        for prop in ["posx", "posy", "width", "height"]:
            self.assertIsNone(source.get_control_binding(prop))
            ret, value = source.get_child_property(prop)
            self.assertTrue(ret)
            self.assertEqual(value, source.ui.default_position[prop])

    @common.setup_timeline
    @common.setup_clipproperties
    def test_operator(self):
        timeline = self.app.gui.editor.timeline_ui.timeline

        clip, = self.add_clips_simple(timeline, 1)
        timeline.selection.select([clip])
        source = self.compositing_box._video_source
        self.assertIsNotNone(source)
        ret, value = source.get_child_property("operator")
        self.assertEqual((ret, value.value_nick), (True, "over"))

        self.compositing_box.blending_combo.set_active_id("source")
        ret, value = source.get_child_property("operator")
        self.assertEqual((ret, value.value_nick), (True, "source"))

        self.compositing_box.blending_combo.set_active_id("over")
        ret, value = source.get_child_property("operator")
        self.assertEqual((ret, value.value_nick), (True, "over"))

        self.app.action_log.undo()
        ret, value = source.get_child_property("operator")
        self.assertEqual((ret, value.value_nick), (True, "source"))

        self.app.action_log.undo()
        ret, value = source.get_child_property("operator")
        self.assertEqual((ret, value.value_nick), (True, "over"))

        self.app.action_log.redo()
        ret, value = source.get_child_property("operator")
        self.assertEqual((ret, value.value_nick), (True, "source"))

        self.app.action_log.redo()
        ret, value = source.get_child_property("operator")
        self.assertEqual((ret, value.value_nick), (True, "over"))


class TitlePropertiesTest(common.TestCase):
    """Tests for the TitleProperties class."""

    def _get_title_source_child_props(self):
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 1, clips)
        self.assertIsInstance(clips[0], GES.TitleClip)
        source, = clips[0].get_children(False)
        return {p: source.get_child_property(p)
                for p in ("text",
                          "x-absolute", "y-absolute",
                          "valignment", "halignment",
                          "font-desc",
                          "color",
                          "foreground-color",
                          "outline-color",
                          "draw-shadow")}

    @common.setup_timeline
    @common.setup_clipproperties
    def test_create_title(self):
        """Exercise creating a title clip."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)

        self.clipproperties.create_title_clip_cb(None)
        properties1 = self._get_title_source_child_props()
        self.assertTrue(properties1["text"][0])
        self.assertNotEqual(properties1["text"][1], "", "Title clip does not have an initial text")

        self.action_log.undo()
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 0, clips)

        self.action_log.redo()
        properties2 = self._get_title_source_child_props()
        self.assertDictEqual(properties1, properties2)

    @common.setup_timeline
    @common.setup_clipproperties
    def test_modify_title(self):
        """Exercise modifying the title."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)

        self.clipproperties.create_title_clip_cb(None)
        properties1 = self._get_title_source_child_props()

        # Modify the title.
        mod_title = "Modifed Title"
        self.clipproperties.title_expander.textbuffer.props.text = mod_title
        properties2 = self._get_title_source_child_props()
        self.assertEqual(properties2["text"], (True, mod_title))
        self.assertNotEqual(properties1["text"], properties2["text"])

        # Undo modify title.
        self.action_log.undo()
        properties3 = self._get_title_source_child_props()
        self.assertDictEqual(properties1, properties3)

        # Redo modify title.
        self.action_log.redo()
        properties4 = self._get_title_source_child_props()
        self.assertDictEqual(properties2, properties4)

    @common.setup_timeline
    @common.setup_clipproperties
    def test_modify_outline_color(self):
        """Exercise modifying the outline color."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)

        self.clipproperties.create_title_clip_cb(None)
        properties1 = self._get_title_source_child_props()

        # Modify the outline color.
        mod_outline_color = 0xFFFFFFFF
        color_button_mock = mock.Mock()
        color_picker_mock = mock.Mock()
        color_picker_mock.calculate_argb.return_value = mod_outline_color
        self.clipproperties.title_expander._color_picker_value_changed_cb(color_picker_mock, color_button_mock, "outline-color")
        properties2 = self._get_title_source_child_props()
        self.assertEqual(properties2["outline-color"], (True, mod_outline_color))
        self.assertNotEqual(properties1["outline-color"], properties2["outline-color"])

        # Undo modify outline color.
        self.action_log.undo()
        properties3 = self._get_title_source_child_props()
        self.assertDictEqual(properties1, properties3)

        # Redo modify outline color.
        self.action_log.redo()
        properties4 = self._get_title_source_child_props()
        self.assertDictEqual(properties2, properties4)

    @common.setup_timeline
    @common.setup_clipproperties
    def test_modify_drop_shadow(self):
        """Exercise modifying the drop shadow."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)

        self.clipproperties.create_title_clip_cb(None)
        properties1 = self._get_title_source_child_props()

        # Modify the drop shadow.
        drop_shadow = False
        drop_shadow_checkbox_mock = mock.Mock()
        drop_shadow_checkbox_mock.get_active.return_value = drop_shadow
        self.clipproperties.title_expander._drop_shadow_checkbox_cb(drop_shadow_checkbox_mock)

        properties2 = self._get_title_source_child_props()
        self.assertEqual(properties2["draw-shadow"], (True, drop_shadow))
        self.assertNotEqual(properties1["draw-shadow"], properties2["draw-shadow"])

        # Undo modify drop shadow.
        self.action_log.undo()
        properties3 = self._get_title_source_child_props()
        self.assertDictEqual(properties1, properties3)

        # Redo modify drop shadow.
        self.action_log.redo()
        properties4 = self._get_title_source_child_props()
        self.assertDictEqual(properties2, properties4)

    @common.setup_timeline
    @common.setup_clipproperties
    def test_selection_does_nothing(self):
        """Checks de/selection do not create undoable operations."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)
        self.clipproperties.create_title_clip_cb(None)
        self.assertEqual(len(self.action_log.undo_stacks), 1)
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 1, clips)

        self.timeline_container.timeline.selection.unselect(clips)
        self.assertEqual(len(self.action_log.undo_stacks), 1)

        self.timeline_container.timeline.selection.select(clips)
        self.assertEqual(len(self.action_log.undo_stacks), 1)

    @common.setup_timeline
    @common.setup_clipproperties
    def test_xxx(self):
        """Exercise creating a title clip."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)

        # Create the first clip.
        self.clipproperties.create_title_clip_cb(None)
        clip1, = self.layer.get_clips()
        source1, = clip1.get_children(False)
        self.clipproperties.title_expander.textbuffer.props.text = "TC1"
        self.assertEqual(source1.get_child_property("text"), (True, "TC1"))

        # Make place for the second clip at the beginning of the layer.
        clip1.props.start = clip1.props.duration

        # Create the second clip.
        self.clipproperties.create_title_clip_cb(None)
        clip2, clip1_ = self.layer.get_clips()
        self.assertIs(clip1_, clip1)
        source2, = clip2.get_children(False)
        self.clipproperties.title_expander.textbuffer.props.text = "TC2"
        self.assertEqual(source2.get_child_property("text"), (True, "TC2"))

        self.assertEqual(source2.get_child_property("text"), (True, "TC2"))
        self.assertEqual(source1.get_child_property("text"), (True, "TC1"))

        # Switch back to clip1.
        self.timeline_container.timeline.selection.select([clip1])
        self.assertEqual(source1.get_child_property("text"), (True, "TC1"))
        self.assertEqual(source2.get_child_property("text"), (True, "TC2"))

        # Switch back to clip2.
        self.timeline_container.timeline.selection.select([clip2])
        self.assertEqual(source1.get_child_property("text"), (True, "TC1"))
        self.assertEqual(source2.get_child_property("text"), (True, "TC2"))


class ClipPropertiesTest(common.TestCase):
    """Tests for the ClipProperties class."""

    @common.setup_timeline
    @common.setup_clipproperties
    def test_alignment_editor(self):
        """Exercise aligning a clip using the alignment editor."""
        self.project.pipeline.get_position = mock.Mock(return_value=0)

        timeline = self.timeline_container.timeline
        clip = self.add_clips_simple(timeline, 1)[0]
        timeline.selection.select([clip])
        source = self.transformation_box.source
        self.assertIsNotNone(source)

        height = source.get_child_property("height").value
        width = source.get_child_property("width").value

        self.assertEqual(source.get_child_property("posx").value, 0)
        self.assertEqual(source.get_child_property("posy").value, 0)

        alignment_editor = self.transformation_box.alignment_editor
        event = mock.MagicMock()
        event.x = 0
        event.y = 0
        alignment_editor._motion_notify_event_cb(None, event)
        alignment_editor._button_release_event_cb(None, None)

        self.assertEqual(source.get_child_property("posx").value, -width)
        self.assertEqual(source.get_child_property("posy").value, -height)

        self.action_log.undo()

        self.assertEqual(source.get_child_property("posx").value, 0)
        self.assertEqual(source.get_child_property("posy").value, 0)

        self.action_log.redo()

        self.assertEqual(source.get_child_property("posx").value, -width)
        self.assertEqual(source.get_child_property("posy").value, -height)


class SpeedPropertiesTest(common.TestCase):
    """Tests for the TransformationProperties widget."""

    def assert_applied_rate(self, sources_count, rate, duration):
        self.assertEqual(len(self.speed_box._time_effects), sources_count)
        self.assertEqual(self.speed_box.props.rate, rate)
        self.assertEqual(self.speed_box._clip.props.duration, duration)
        for effect, propname in self.speed_box._time_effects.values():
            self.assertTrue(propname in ["rate", "tempo"], propname)
            self.assertEqual(effect.get_child_property(propname).value, rate)

        self.assertEqual(self.speed_box._speed_adjustment.props.value, rate)

    def assert_clip_speed_child_props(self, clip, audio, video, value):
        if audio:
            self.assertEqual(clip.get_child_property("tempo").value, value)
        if video:
            self.assertEqual(clip.get_child_property("GstVideoRate::rate").value, value)

    def _check_clip_speed(self, audio=False, video=False):
        sources_count = len([source for source in [audio, video] if source])

        clip, = self.layer.get_clips()

        duration = self.project.ges_timeline.get_frame_time(self.project.ges_timeline.get_frame_at(Gst.SECOND))
        self.project.ges_timeline.props.snapping_distance = duration
        self.assertEqual(self.speed_box._sources, {})
        self.assertEqual(self.speed_box._time_effects, {})

        self.timeline_container.timeline.selection.select([clip])

        self.assertEqual(len(self.speed_box._sources), sources_count, self.speed_box._sources)
        self.assertEqual(self.speed_box._time_effects, {})

        clip.props.duration = duration
        self.assertEqual(self.speed_box._clip.props.duration, duration)

        self.speed_box._speed_adjustment.props.value = 2.0
        self.assert_applied_rate(sources_count, 2.0, int(duration / 2))

        self.speed_box._speed_adjustment.props.value = 0.5
        self.assert_applied_rate(sources_count, 0.5, int(duration / 2) * 4)

        self.action_log.undo()
        self.assert_applied_rate(sources_count, 2.0, int(duration / 2))

        self.action_log.undo()
        self.assert_applied_rate(sources_count, 1.0, duration)

        self.action_log.redo()
        self.assert_applied_rate(sources_count, 2.0, int(duration / 2))

        self.action_log.redo()
        self.assert_applied_rate(sources_count, 0.5, int(duration / 2) * 4)

        self.timeline_container.timeline.selection.select([])
        self.assertEqual(self.speed_box._sources, {})
        self.assertEqual(self.speed_box._time_effects, {})

        self.timeline_container.timeline.selection.select([clip])
        self.assert_applied_rate(sources_count, 0.5, int(duration / 2) * 4)

        self.action_log.undo()
        self.assert_applied_rate(sources_count, 2.0, int(duration / 2))

        self.timeline_container.timeline.selection.select([])
        self.assertEqual(self.speed_box._sources, {})
        self.assertEqual(self.speed_box._time_effects, {})

        self.action_log.undo()
        self.assert_clip_speed_child_props(clip, audio, video, 1.0)

        self.action_log.redo()
        self.assert_clip_speed_child_props(clip, audio, video, 2.0)

        self.action_log.redo()
        self.assert_clip_speed_child_props(clip, audio, video, 0.5)

        self.timeline_container.timeline.selection.select([clip])
        total_duration = clip.props.duration
        self.project.pipeline.get_position = mock.Mock(return_value=duration)
        self.timeline_container.split_action.activate()

        clip1, clip2 = self.layer.get_clips()
        self.assertEqual(clip1.props.start, 0)
        self.assertEqual(clip1.props.duration, duration)
        self.assertEqual(clip2.props.start, duration)
        self.assertEqual(clip2.props.duration, total_duration - duration)
        self.assertEqual(self.project.ges_timeline.props.snapping_distance, duration)

        # 0.1 would lead to clip1 totally overlapping clip2, ensure it is a noop
        self.speed_box._speed_adjustment.props.value = 0.1
        self.assert_applied_rate(sources_count, 0.5, duration)
        self.assertEqual(self.project.ges_timeline.props.snapping_distance, duration)

        self.action_log.undo()
        self.assert_applied_rate(sources_count, 0.5, int(duration / 2) * 4)

        # Undoing should undo the split
        clip1, = self.layer.get_clips()

        # redo the split
        self.action_log.redo()
        clip1, clip2 = self.layer.get_clips()
        self.assertEqual(self.speed_box._clip, clip1)
        self.assert_applied_rate(sources_count, 0.5, duration)
        self.assertEqual(self.project.ges_timeline.props.snapping_distance, duration)

        self.speed_box._speed_adjustment.props.value = 1.0
        self.assert_applied_rate(sources_count, 1.0, int(duration / 2))

        self.speed_box._speed_adjustment.props.value = 0.5
        self.assert_applied_rate(sources_count, 0.5, int(duration / 2) * 2)

        self.speed_box.set_clip(None)
        self.assertEqual(self.speed_box._sources, {})
        self.assertEqual(self.speed_box._time_effects, {})

    @common.setup_project_with_clips(assets_names=["1sec_simpsons_trailer.mp4"])
    @common.setup_clipproperties
    def test_clip_speed_av(self):
        self._check_clip_speed(audio=True, video=True)

    @common.setup_project_with_clips(assets_names=["mp3_sample.mp3"])
    @common.setup_clipproperties
    def test_clip_speed_a(self):
        self._check_clip_speed(audio=True)

    @common.setup_project_with_clips(assets_names=["30fps_numeroted_frames_blue.webm"])
    @common.setup_clipproperties
    def test_clip_speed_v(self):
        self._check_clip_speed(video=True)

    @common.setup_project_with_clips(assets_names=["mp3_sample.mp3", "30fps_numeroted_frames_blue.webm"])
    @common.setup_clipproperties
    def test_widgets_updated_when_switching_clips(self):
        clip1, clip2 = self.layer.get_clips()
        clip1_duration = clip1.props.duration
        clip2_duration = clip2.props.duration

        self.timeline_container.timeline.selection.select([clip1])
        self.assertIs(self.speed_box._clip, clip1)
        self.assert_applied_rate(0, 1.0, clip1_duration)

        self.speed_box._speed_adjustment.props.value = 2.0
        self.assert_applied_rate(1, 2.0, clip1_duration / 2)

        self.timeline_container.timeline.selection.select([clip2])
        self.assertIs(self.speed_box._clip, clip2)
        self.assert_applied_rate(0, 1.0, clip2_duration)

        self.timeline_container.timeline.selection.select([clip1])
        self.assert_applied_rate(1, 2.0, clip1_duration / 2)

    @common.setup_project_with_clips(assets_names=["1sec_simpsons_trailer.mp4"])
    @common.setup_clipproperties
    def test_load_project_clip_speed(self):
        sources_count = 2
        clip, = self.layer.get_clips()
        clip.props.duration = Gst.SECOND

        self.timeline_container.timeline.selection.select([clip])
        self.speed_box._speed_adjustment.props.value = 0.5
        self.assert_applied_rate(sources_count, 0.5, 2 * Gst.SECOND)

        with tempfile.NamedTemporaryFile() as temp_file:
            uri = Gst.filename_to_uri(temp_file.name)
            project_manager = self.app.project_manager
            self.assertTrue(project_manager.save_project(uri=uri, backup=False))

            mainloop = common.create_main_loop()

            project_manager.connect("new-project-loaded", lambda *args: mainloop.quit())
            project_manager.connect("closing-project", lambda *args: True)
            self.assertTrue(project_manager.close_running_project())
            project_manager.load_project(uri)
            mainloop.run()

        new_clip, = self.layer.get_clips()
        self.assertNotEqual(new_clip, clip)

        self.timeline_container.timeline.selection.select([new_clip])
        self.assert_applied_rate(sources_count, 0.5, 2 * Gst.SECOND)
