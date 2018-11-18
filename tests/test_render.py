# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Alex Băluț <alexandru.balut@gmail.com>
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
# Boston, MA 02110-1301, USA.
"""Tests for the render module."""
# pylint: disable=protected-access,no-self-use
# pylint: disable=too-many-locals
import os
import tempfile
from unittest import mock
from unittest import skipUnless

from gi.repository import GES
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import Gtk

from pitivi.preset import EncodingTargetManager
from pitivi.render import Encoders
from pitivi.render import extension_for_muxer
from pitivi.timeline.timeline import TimelineContainer
from pitivi.utils.ui import get_combo_value
from pitivi.utils.ui import set_combo_value
from tests import common
from tests.test_media_library import BaseTestMediaLibrary


def factory_exists(*factories):
    """Checks if @factories exists."""
    for factory in factories:
        if not Gst.ElementFactory.find(factory):
            return False, "%s not present on the system" % (factory)

    return True, ""


def encoding_target_exists(tname):
    """Checks if a GstEncodingTarget called @name exists."""
    for target in GstPbutils.encoding_list_all_targets():
        if tname in target.get_name().split(";"):
            return True, ""
    return False, "EncodingTarget %s not present on the system" % tname


def find_preset_row_index(combo, name):
    """Finds @name in @combo."""
    for i, row in enumerate(combo.get_model()):
        if row[0] == name:
            return i

    return None


class TestRender(BaseTestMediaLibrary):
    """Tests for functions."""

    def test_extensions_supported(self):
        """Checks we associate file extensions to the well supported muxers."""
        for muxer, unused_audio, unused_video in Encoders.SUPPORTED_ENCODERS_COMBINATIONS:
            self.assertIsNotNone(extension_for_muxer(muxer), muxer)

    def test_extensions_presets(self):
        """Checks we associate file extensions to the muxers of the presets."""
        project = self.create_simple_project()
        with mock.patch("pitivi.preset.xdg_data_home") as xdg_data_home:
            xdg_data_home.return_value = "/pitivi-dir-which-does-not-exist"
            preset_manager = EncodingTargetManager(project.app)
            preset_manager.loadAll()
            self.assertTrue(preset_manager.presets)
            for unused_name, container_profile in preset_manager.presets.items():
                # Preset name is only set when the project loads it
                project.set_container_profile(container_profile)
                muxer = container_profile.get_preset_name()
                self.assertIsNotNone(extension_for_muxer(muxer), container_profile)

    def create_simple_project(self):
        """Creates a Project with a layer a clip."""
        timeline_container = common.create_timeline_container()
        app = timeline_container.app
        project = app.project_manager.current_project
        if not project.ges_timeline.get_layers():
            project.ges_timeline.append_layer()

        mainloop = common.create_main_loop()

        def asset_added_cb(project, asset):  # pylint: disable=missing-docstring
            mainloop.quit()

        project.connect("asset-added", asset_added_cb)
        uris = [common.get_sample_uri("tears_of_steel.webm")]
        project.addUris(uris)
        mainloop.run()

        layer, = project.ges_timeline.get_layers()
        asset, = project.list_assets(GES.UriClip)
        layer.add_asset(asset, 0, 0, Gst.CLOCK_TIME_NONE, GES.TrackType.UNKNOWN)

        return project

    def create_rendering_dialog(self, project):
        """Creates a RenderingDialog ready for testing"""
        from pitivi.render import RenderDialog

        class MockedBuilder(Gtk.Builder):
            """Specialized builder suitable for RenderingDialog testing."""

            # pylint: disable=arguments-differ
            def get_object(self, name):
                """Get @name widget or a MagicMock for render dialog window."""
                if name == "render-dialog":
                    return mock.MagicMock()

                return super().get_object(name)

        with mock.patch.object(Gtk.Builder, "__new__", return_value=MockedBuilder()):
            return RenderDialog(project.app, project)

    def test_launching_rendering(self):
        """Checks no exception is raised when clicking the render button."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)

        from pitivi.render import RenderingProgressDialog
        with mock.patch.object(dialog, "startAction"):
            with mock.patch.object(RenderingProgressDialog, "__new__"):
                with mock.patch.object(dialog, "_pipeline"):
                    return dialog._renderButtonClickedCb(None)

    @skipUnless(*factory_exists("x264enc", "matroskamux"))
    def test_encoder_restrictions(self):
        """Checks the mechanism to respect encoder specific restrictions."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)

        # Explicitly set the encoder
        self.assertTrue(set_combo_value(dialog.muxer_combo,
                                        Gst.ElementFactory.find("matroskamux")))
        self.assertTrue(set_combo_value(dialog.video_encoder_combo,
                                        Gst.ElementFactory.find("x264enc")))

        # Set encoding profile
        if getattr(GstPbutils.EncodingProfile, "copy"):  # Available only in > 1.11
            profile = project.container_profile.copy()
            vprofile, = [p for p in profile.get_profiles()
                         if isinstance(p, GstPbutils.EncodingVideoProfile)]
            vprofile.set_restriction(Gst.Caps("video/x-raw"))
            project.set_container_profile(profile)

    @skipUnless(*factory_exists("vorbisenc", "theoraenc", "oggmux",
                                "opusenc", "vp8enc"))
    def test_loading_preset(self):
        """Checks preset values are properly exposed in the UI."""
        def preset_changed_cb(combo, changed):
            """Callback for the "combo::changed" signal."""
            changed.append(1)

        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)

        preset_combo = dialog.render_presets.combo
        changed = []
        preset_combo.connect("changed", preset_changed_cb, changed)

        test_data = [
            ("test", {"aencoder": "vorbisenc",
                      "vencoder": "theoraenc",
                      "muxer": "oggmux"}),
            ("test_ogg-vp8-opus", {
                "aencoder": "opusenc",
                "vencoder": ["vp8enc", "vaapivp8enc"],
                "muxer": "oggmux"}),
            ("test_fullhd", {
                "aencoder": "vorbisenc",
                "vencoder": "theoraenc",
                "muxer": "oggmux",
                "videowidth": 1920,
                "videoheight": 1080,
                "videorate": Gst.Fraction(120, 1)}),
            ("test_ogg-vp8-opus", {
                "aencoder": "opusenc",
                "vencoder": ["vp8enc", "vaapivp8enc"],
                "muxer": "oggmux"}),
            ("test_fullhd", {
                "aencoder": "vorbisenc",
                "vencoder": "theoraenc",
                "muxer": "oggmux",
                "videowidth": 1920,
                "videoheight": 1080,
                "videorate": Gst.Fraction(120, 1)}),
        ]

        attr_dialog_widget_map = {
            "videorate": dialog.frame_rate_combo,
            "aencoder": dialog.audio_encoder_combo,
            "vencoder": dialog.video_encoder_combo,
            "muxer": dialog.muxer_combo,
        }

        for preset_name, values in test_data:
            i = find_preset_row_index(preset_combo, preset_name)
            self.assertNotEqual(i, None)

            del changed[:]
            preset_combo.set_active(i)
            self.assertEqual(changed, [1], "Preset %s" % preset_name)

            for attr, val in values.items():
                val = val if isinstance(val, list) else [val]
                combo = attr_dialog_widget_map.get(attr)
                if combo:
                    combo_value = get_combo_value(combo)
                    if isinstance(combo_value, Gst.ElementFactory):
                        combo_value = combo_value.get_name()
                    self.assertIn(combo_value, val, preset_name)

                self.assertIn(getattr(project, attr), val)

    @skipUnless(*factory_exists("vorbisenc", "theoraenc", "oggmux",
                                "opusenc", "vp8enc"))
    def test_remove_profile(self):
        """Tests removing EncodingProfile and re-saving it."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)
        preset_combo = dialog.render_presets.combo
        i = find_preset_row_index(preset_combo, "test")
        self.assertIsNotNone(i)
        preset_combo.set_active(i)

        # Check the 'test' profile is selected
        active_iter = preset_combo.get_active_iter()
        self.assertEqual(preset_combo.props.model.get_value(active_iter, 0), "test")

        # Remove current profile and verify it has been removed
        dialog.render_presets.action_remove.activate()
        profile_names = [i[0] for i in preset_combo.props.model]
        active_iter = preset_combo.get_active_iter()
        self.assertEqual(active_iter, None)
        self.assertEqual(preset_combo.get_child().props.text, "")

        # Re save the current EncodingProfile calling it the same as before.
        preset_combo.get_child().set_text("test")
        self.assertTrue(dialog.render_presets.action_save.get_enabled())
        dialog.render_presets.action_save.activate(None)
        self.assertEqual([i[0] for i in preset_combo.props.model],
                         sorted(profile_names + ["test"]))
        active_iter = preset_combo.get_active_iter()
        self.assertEqual(preset_combo.props.model.get_value(active_iter, 0), "test")

    def setup_project_with_profile(self, profile_name):
        """Creates a simple project, open the render dialog and select @profile_name."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)

        # Select wanted profile
        preset_combo = dialog.render_presets.combo
        if profile_name:
            i = find_preset_row_index(preset_combo, profile_name)
            self.assertIsNotNone(i)
            preset_combo.set_active(i)

        return project, dialog

    def check_simple_rendering_profile(self, profile_name):
        """Checks that rendering with the specified profile works."""
        self.render(self.setup_project_with_profile(profile_name)[1])

    def render(self, dialog):
        """Renders pipeline from @dialog."""
        from pitivi.render import RenderingProgressDialog
        with tempfile.TemporaryDirectory() as temp_dir:
            # Start rendering
            with mock.patch.object(dialog.filebutton, "get_uri",
                                   return_value=Gst.filename_to_uri(temp_dir)):
                with mock.patch.object(dialog.fileentry, "get_text", return_value="outfile"):
                    with mock.patch.object(RenderingProgressDialog, "__new__"):
                        dialog._renderButtonClickedCb(None)

            message = dialog._pipeline.get_bus().timed_pop_filtered(
                10 * Gst.SECOND,
                Gst.MessageType.EOS | Gst.MessageType.ERROR)
            self.assertIsNotNone(message)
            Gst.debug_bin_to_dot_file_with_ts(
                dialog._pipeline, Gst.DebugGraphDetails.ALL,
                "test_rendering_with_profile.dot")

            result_file = Gst.filename_to_uri(os.path.join(temp_dir, "outfile"))
            struct = message.get_structure()
            self.assertEqual(message.type, Gst.MessageType.EOS,
                             struct.to_string() if struct else message)
            asset = GES.UriClipAsset.request_sync(result_file)
            self.assertIsNotNone(asset)

            if message:
                dialog._pipeline.get_bus().post(message)

    def test_rendering_with_scale(self):
        """Tests rendering with a smaller scale."""
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name])

            project = self.app.project_manager.current_project
            timeline_container = TimelineContainer(self.app)
            timeline_container.setProject(project)

            assets = project.list_assets(GES.UriClip)
            asset, = [a for a in assets if "proxy" in a.props.id]
            layer, = project.ges_timeline.get_layers()
            clip = asset.extract()
            layer.add_clip(clip)
            video_source = clip.find_track_element(None, GES.VideoUriSource)
            self.assertEqual(video_source.get_child_property("width")[1], 320)
            self.assertEqual(video_source.get_child_property("height")[1], 240)

            dialog = self.create_rendering_dialog(project)

            # Simulate setting the scale to 10%.
            with mock.patch.object(dialog.scale_spinbutton, "get_value",
                                   return_value=10):
                dialog._scaleSpinbuttonChangedCb(None)
                self.render(dialog)

            self.mainloop.run(until_empty=True)

            video_source = clip.find_track_element(None, GES.VideoUriSource)
            self.assertEqual(video_source.get_child_property("width")[1], 320)
            self.assertEqual(video_source.get_child_property("height")[1], 240)

    @skipUnless(*encoding_target_exists("youtube"))
    # pylint: disable=invalid-name
    def test_rendering_with_youtube_profile(self):
        """Tests rendering a simple timeline with the youtube profile."""
        self.check_simple_rendering_profile("youtube")

    @skipUnless(*encoding_target_exists("dvd"))
    def test_rendering_with_dvd_profile(self):
        """Tests rendering a simple timeline with the DVD profile."""
        self.check_simple_rendering_profile("dvd")

    # pylint: disable=invalid-name
    def test_rendering_with_default_profile(self):
        """Tests rendering a simple timeline with the default profile."""
        self.check_simple_rendering_profile(None)

    @skipUnless(*encoding_target_exists("youtube"))
    def test_setting_caps_fields_in_advanced_dialog(self):
        """Tests setting special advanced setting (which are actually set on caps)."""
        project, dialog = self.setup_project_with_profile("youtube")

        dialog.window = None  # Make sure the dialog window is never set to Mock.
        dialog._videoSettingsButtonClickedCb(None)
        self.assertEqual(dialog.dialog.elementsettings.get_caps_values(), {"profile": "high"})

        dialog.dialog.elementsettings.caps_widgets["profile"].setWidgetValue("baseline")
        self.assertEqual(dialog.dialog.elementsettings.get_caps_values(), {"profile": "baseline"})

        caps = dialog.dialog.get_caps()
        self.assert_caps_equal(caps, "video/x-h264,profile=baseline")

        dialog.dialog.ok_btn.emit("clicked")
        self.assert_caps_equal(project.video_profile.get_format(), "video/x-h264,profile=baseline")

        dialog._videoSettingsButtonClickedCb(None)

        caps = dialog.dialog.get_caps()
        self.assert_caps_equal(caps, "video/x-h264,profile=baseline")
