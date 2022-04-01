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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Tests for the render module."""
# pylint: disable=protected-access,no-self-use
import os
import shutil
import tempfile
from unittest import mock
from unittest import skipUnless

from gi.repository import GES
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import Gtk

from pitivi.render import Encoders
from pitivi.render import extension_for_muxer
from pitivi.render import PresetsManager
from pitivi.render import Quality
from pitivi.render import quality_adapters
from pitivi.render import QualityAdapter
from pitivi.timeline.timeline import TimelineContainer
from pitivi.utils.proxy import ProxyingStrategy
from pitivi.utils.ui import get_combo_value
from pitivi.utils.ui import set_combo_value
from tests import common
from tests.test_medialibrary import BaseTestMediaLibrary


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


def setup_render_presets(*profiles):
    """Temporary directory setup for testing render profiles."""
    def setup_wrapper(func):

        def wrapped(self):
            with tempfile.TemporaryDirectory() as tmp_presets_dir:
                os.mkdir(os.path.join(tmp_presets_dir, "test"))

                for profile in profiles:
                    path = os.path.join(os.environ["PITIVI_TOP_LEVEL_DIR"], "tests/test-encoding-targets/test", profile + ".gep")
                    tmp_path = os.path.join(tmp_presets_dir, "test", profile + ".gep")
                    shutil.copy(path, tmp_path)

                os.environ["GST_ENCODING_TARGET_PATH"] = tmp_presets_dir
                func(self)

        return wrapped

    return setup_wrapper


class TestPresetsManager(common.TestCase):

    @skipUnless(*encoding_target_exists("youtube"))
    @skipUnless(*factory_exists("x264enc"))
    def test_initial_preset(self):
        project = common.create_project()
        manager = PresetsManager(project)

        self.assertEqual(manager.initial_preset().name, "youtube")

    def test_missing_x264(self):
        # Simulate no encoder being available for the profile's format.
        targets = GstPbutils.encoding_list_all_targets()
        for target in targets:
            for profile in target.get_profiles():
                for sub_profile in profile.get_profiles():
                    raw_caps = "audio/non_existing_whatever_it_s_true"
                    sub_profile.get_format = mock.Mock(return_value=raw_caps)

        with mock.patch.object(GstPbutils, "encoding_list_all_targets") as encoding_list_all_targets:
            encoding_list_all_targets.return_value = targets

            project = common.create_project()
            manager = PresetsManager(project)

            self.assertIsNone(manager.initial_preset())


class TestQualityAdapter(common.TestCase):
    """Tests for the QualityAdapter class."""

    def check_adapter(self, adapter, expected_qualities):
        qualities = []
        for prop_value in range(len(expected_qualities)):
            vcodecsettings = {adapter.prop_name: prop_value}
            quality = adapter.calculate_quality(vcodecsettings)
            qualities.append(quality)
        self.assertListEqual(qualities, expected_qualities)

    def test_calculate_quality(self):
        self.check_adapter(QualityAdapter({"prop1": (0, 3, 5)}),
                           [Quality.LOW, Quality.LOW, Quality.LOW, Quality.MEDIUM, Quality.MEDIUM, Quality.HIGH])
        self.check_adapter(QualityAdapter({"prop1": (100, 3, 2)}),
                           [Quality.HIGH, Quality.HIGH, Quality.HIGH, Quality.MEDIUM, Quality.LOW, Quality.LOW])

        self.check_adapter(quality_adapters[Encoders.X264],
                           [Quality.HIGH] * 19 + [Quality.MEDIUM] * 3 + [Quality.LOW] * 29)
        self.check_adapter(quality_adapters[Encoders.VP8],
                           [Quality.LOW] * 47 + [Quality.MEDIUM] * 16 + [Quality.HIGH] * 1)
        self.check_adapter(quality_adapters[Encoders.THEORA],
                           [Quality.LOW] * 48 + [Quality.MEDIUM] * 15 + [Quality.HIGH] * 1)
        self.check_adapter(quality_adapters[Encoders.JPEG],
                           [Quality.LOW] * 85 + [Quality.MEDIUM] * 15 + [Quality.HIGH] * 1)


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
            preset_manager = PresetsManager(project.app)
            preset_manager.load_all()
            for preset_item in preset_manager.model:
                # Preset name is only set when the project loads it
                project.set_container_profile(preset_item.profile)
                muxer = preset_item.profile.get_preset_name()
                self.assertIsNotNone(extension_for_muxer(muxer), preset_item.profile)

    def create_simple_project(self):
        """Creates a Project with a layer a clip."""
        timeline_container = common.create_timeline_container()
        app = timeline_container.app
        project = app.project_manager.current_project
        if not project.ges_timeline.get_layers():
            project.ges_timeline.append_layer()

        mainloop = common.create_main_loop()

        def asset_added_cb(project, asset):
            mainloop.quit()

        project.connect("asset-added", asset_added_cb)
        uris = [common.get_sample_uri("tears_of_steel.webm")]
        project.add_uris(uris)
        mainloop.run()

        layer, = project.ges_timeline.get_layers()
        asset, = project.list_assets(GES.UriClip)
        layer.add_asset(asset, 0, 0, Gst.CLOCK_TIME_NONE, GES.TrackType.UNKNOWN)

        return project

    def create_rendering_dialog(self, project):
        """Creates a RenderingDialog ready for testing."""
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
        with mock.patch.object(dialog, "start_action"):
            with mock.patch.object(RenderingProgressDialog, "__new__"):
                with mock.patch.object(dialog, "_pipeline"):
                    return dialog._render_button_clicked_cb(None)

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
    @setup_render_presets("test")
    def test_loading_preset(self):
        """Checks preset values are properly exposed in the UI."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)

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

        dialog._preset_selection_menubutton_clicked_cb(None)

        for preset_name, values in test_data:
            self.select_render_preset(dialog, preset_name)

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
    @setup_render_presets("test-remove")
    def test_remove_profile(self):
        """Tests removing EncodingProfile and re-saving it."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)
        self.select_render_preset(dialog, "test-remove")

        # Check the "test" profile is selected
        self.assertEqual(dialog.presets_manager.cur_preset_item.name, "test-remove")

        # If EncodingTarget has single profile, PresetItem's name is same as that of the EncodingTarget.
        profile_name = dialog.presets_manager.cur_preset_item.name

        if self.assertEqual(profile_name, "test-remove"):
            # Remove current profile and verify it has been removed
            dialog.presets_manager.action_remove.activate()
            self.assertIsNone(dialog.presets_manager.cur_preset_item)
            self.assertEqual(dialog.preset_label.get_text(), "Custom")

    def check_simple_rendering_profile(self, profile_name=None):
        """Checks that rendering with the specified profile works."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)
        if profile_name:
            self.select_render_preset(dialog, profile_name)
        self.render(dialog)

    def render(self, dialog):
        """Renders pipeline from @dialog."""
        from pitivi.render import RenderingProgressDialog
        with tempfile.TemporaryDirectory() as temp_dir:
            # Start rendering
            with mock.patch.object(dialog.fileentry, "get_text",
                                   return_value=os.path.join(temp_dir, "outfile")):
                with mock.patch.object(RenderingProgressDialog, "__new__"):
                    dialog._render_button_clicked_cb(None)

            message = dialog._pipeline.get_bus().timed_pop_filtered(
                Gst.CLOCK_TIME_NONE,
                Gst.MessageType.EOS | Gst.MessageType.ERROR)
            self.assertIsNotNone(message)
            Gst.debug_bin_to_dot_file_with_ts(
                dialog._pipeline, Gst.DebugGraphDetails.ALL,
                "test_rendering_with_profile.dot")

            struct = message.get_structure()
            self.assertEqual(message.type, Gst.MessageType.EOS,
                             struct.to_string() if struct else message)

            result_file = Gst.filename_to_uri(os.path.join(temp_dir, "outfile"))
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
            timeline_container = TimelineContainer(self.app, editor_state=self.app.gui.editor.editor_state)
            timeline_container.set_project(project)

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
                dialog._scale_spinbutton_changed_cb(None)
                self.render(dialog)

            self.mainloop.run(until_empty=True)

            video_source = clip.find_track_element(None, GES.VideoUriSource)
            self.assertEqual(video_source.get_child_property("width")[1], 320)
            self.assertEqual(video_source.get_child_property("height")[1], 240)

    # pylint: disable=invalid-name
    def test_rendering_with_scaled_proxies(self):
        """Tests rendering with scaled proxies."""
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.NOTHING)

            project = self.app.project_manager.current_project
            proxy_manager = self.app.proxy_manager
            timeline_container = TimelineContainer(self.app, editor_state=self.app.gui.editor.editor_state)
            timeline_container.set_project(project)
            rendering_asset = None

            asset, = project.list_assets(GES.UriClip)
            proxy = self.check_add_proxy(asset, scaled=True)

            layer, = project.ges_timeline.get_layers()
            clip = proxy.extract()
            layer.add_clip(clip)

            # Patch the function that reverts assets to proxies after rendering.
            from pitivi.render import RenderDialog
            old_use_proxy_assets = RenderDialog._use_proxy_assets

            def check_use_proxy_assets(self):
                nonlocal layer, asset, rendering_asset
                clip, = layer.get_clips()
                rendering_asset = clip.get_asset()
                old_use_proxy_assets(self)

            RenderDialog._use_proxy_assets = check_use_proxy_assets
            try:
                dialog = self.create_rendering_dialog(project)
                self.render(dialog)
                self.mainloop.run(until_empty=True)
            finally:
                RenderDialog._use_proxy_assets = old_use_proxy_assets

            # Check rendering did not use scaled proxy
            self.assertFalse(proxy_manager.is_scaled_proxy(rendering_asset))
            # Check asset was replaced with scaled proxy after rendering
            self.assertTrue(proxy_manager.is_scaled_proxy(clip.get_asset()))

    # pylint: disable=invalid-name
    def test_rendering_with_unsupported_asset_scaled_proxies(self):
        """Tests rendering with scaled proxies."""
        sample_name = "30fps_numeroted_frames_red.mkv"
        with common.cloned_sample(sample_name):
            self.check_import([sample_name], proxying_strategy=ProxyingStrategy.AUTOMATIC)

            project = self.app.project_manager.current_project
            proxy_manager = self.app.proxy_manager
            timeline_container = TimelineContainer(self.app, editor_state=self.app.gui.editor.editor_state)
            timeline_container.set_project(project)
            rendering_asset = None

            asset, = project.list_assets(GES.UriClip)
            with mock.patch.object(proxy_manager,
                                   "is_asset_format_well_supported",
                                   return_value=False):
                proxy = self.check_add_proxy(asset, scaled=True)

                # Check that HQ proxy was created
                hq_uri = self.app.proxy_manager.get_proxy_uri(asset)
                self.assertTrue(os.path.exists(Gst.uri_get_location(hq_uri)), hq_uri)

                layer, = project.ges_timeline.get_layers()
                clip = proxy.extract()
                layer.add_clip(clip)

                def _use_proxy_assets():
                    nonlocal layer, asset, rendering_asset
                    clip, = layer.get_clips()
                    rendering_asset = clip.get_asset()
                    old_use_proxy_assets()

                dialog = self.create_rendering_dialog(project)
                old_use_proxy_assets = dialog._use_proxy_assets
                dialog._use_proxy_assets = _use_proxy_assets
                self.render(dialog)
                self.mainloop.run(until_empty=True)

                # Check rendering used HQ proxy
                self.assertTrue(proxy_manager.is_hq_proxy(rendering_asset))
                # Check asset was replaced with scaled proxy after rendering
                self.assertTrue(proxy_manager.is_scaled_proxy(clip.get_asset()))

    @skipUnless(*encoding_target_exists("youtube"))
    # pylint: disable=invalid-name
    def test_rendering_with_youtube_profile(self):
        """Tests rendering a simple timeline with the youtube profile."""
        self.check_simple_rendering_profile("youtube")

    @skipUnless(*encoding_target_exists("youtube"))
    def test_preset_reset_when_changing_muxer(self):
        """Tests setting the container profile manually."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)
        self.select_render_preset(dialog, "youtube")

        # The container and video encoder profiles in the "youtube"
        # EncodingTarget are "qtmux" and "x264enc". They have a common
        # "preset" called "Profile YouTube".
        # When changing the container manually from qt4mux to mp4mux
        # the container profile's "preset" needs to be reset, otherwise
        # rendering will hang because mp4mux is missing the
        # "Profile YouTube" preset.
        self.assertTrue(set_combo_value(dialog.muxer_combo,
                                        Gst.ElementFactory.find("mp4mux")))

        self.render(dialog)

    def test_preset_changes_file_extension(self):
        """Test file extension changes according to the chosen preset."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)
        self.select_render_preset(dialog, "youtube")
        self.assertTrue(dialog.fileentry.get_text().endswith("mov"))

        self.select_render_preset(dialog, "dvd")
        self.assertTrue(dialog.fileentry.get_text().endswith("mpeg"))

        self.select_render_preset(dialog, "youtube")
        self.assertTrue(dialog.fileentry.get_text().endswith("mov"))

    def select_render_preset(self, dialog, profile_name):
        """Sets the preset value for an existing dialog."""
        row = None
        for item in dialog.presets_manager.model:
            if item.name == profile_name:
                row = mock.Mock()
                row.preset_item = item
                break
        self.assertIsNotNone(row)

        dialog._preset_listbox_row_activated_cb(None, row)
        self.assertEqual(dialog.presets_manager.cur_preset_item.name, profile_name)

    @skipUnless(*encoding_target_exists("dvd"))
    def test_rendering_with_dvd_profile(self):
        """Tests rendering a simple timeline with the DVD profile."""
        self.check_simple_rendering_profile("dvd")

    def test_rendering_with_default_profile(self):
        """Tests rendering a simple timeline with the default profile."""
        self.check_simple_rendering_profile()

    @skipUnless(*encoding_target_exists("youtube"))
    def test_setting_caps_fields_in_advanced_dialog(self):
        """Tests setting special advanced setting (which are actually set on caps)."""
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)
        self.select_render_preset(dialog, "youtube")

        dialog.window = None  # Make sure the dialog window is never set to Mock.
        dialog._video_settings_button_clicked_cb(None)
        self.assertEqual(dialog.dialog.elementsettings.get_caps_values(), {"profile": "high"})

        dialog.dialog.elementsettings.caps_widgets["profile"].set_widget_value("baseline")
        self.assertEqual(dialog.dialog.elementsettings.get_caps_values(), {"profile": "baseline"})

        caps = dialog.dialog.get_caps()
        self.assert_caps_equal(caps, "video/x-h264,profile=baseline")

        dialog.dialog.ok_btn.clicked()
        self.assert_caps_equal(project.video_profile.get_format(), "video/x-h264,profile=baseline")

        dialog._video_settings_button_clicked_cb(None)

        caps = dialog.dialog.get_caps()
        self.assert_caps_equal(caps, "video/x-h264,profile=baseline")

    def check_quality_widget(self, dialog, vencoder, vcodecsettings, preset, sensitive, value):
        if vencoder:
            self.assertEqual(dialog.project.vencoder, vencoder)
        if vcodecsettings is not None:
            self.assertDictEqual(dialog.project.vcodecsettings, vcodecsettings)

        if preset:
            self.assertEqual(dialog.presets_manager.cur_preset_item.name, preset)
        else:
            self.assertIsNone(dialog.presets_manager.cur_preset_item)

        self.assertEqual(dialog.quality_scale.props.sensitive, sensitive)
        self.assertEqual(dialog.quality_adjustment.props.value, value)

    @skipUnless(*encoding_target_exists("dvd"))
    @skipUnless(*encoding_target_exists("youtube"))
    @skipUnless(*factory_exists("pngenc"))
    def test_quality_widget(self):
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)
        self.check_quality_widget(dialog,
                                  vencoder="x264enc", vcodecsettings={"quantizer": 21, "pass": 5},
                                  preset="youtube",
                                  sensitive=True, value=Quality.MEDIUM)

        self.assertEqual(project.video_profile.get_preset_name(), "x264enc")
        dialog.quality_adjustment.props.value = Quality.HIGH
        self.check_quality_widget(dialog,
                                  vencoder="x264enc", vcodecsettings={"quantizer": 18, "pass": 5},
                                  preset="youtube",
                                  sensitive=True, value=Quality.HIGH)

        self.select_render_preset(dialog, "dvd")
        self.check_quality_widget(dialog,
                                  vencoder=None, vcodecsettings={},
                                  preset="dvd",
                                  sensitive=False, value=Quality.LOW)

        self.select_render_preset(dialog, "youtube")
        self.assertEqual(project.video_profile.get_preset_name(), "x264enc")
        self.check_quality_widget(dialog,
                                  vencoder="x264enc", vcodecsettings={"quantizer": 21, "pass": 5},
                                  preset="youtube",
                                  sensitive=True, value=Quality.MEDIUM)

        self.assertTrue(set_combo_value(dialog.video_encoder_combo,
                                        Gst.ElementFactory.find("pngenc")))
        self.check_quality_widget(dialog,
                                  vencoder="pngenc", vcodecsettings={},
                                  preset=None,
                                  sensitive=False, value=Quality.LOW)

        self.select_render_preset(dialog, "youtube")
        self.check_quality_widget(dialog,
                                  vencoder="x264enc", vcodecsettings={"quantizer": 21, "pass": 5},
                                  preset="youtube",
                                  sensitive=True, value=Quality.MEDIUM)

    def test_preset_persistent(self):
        """Checks the render preset is remembered when loading a project."""
        project = self.create_simple_project()
        self.assertEqual(project.muxer, "webmmux")
        self.assertEqual(project.vencoder, "vp8enc")
        self.assertDictEqual(project.vcodecsettings, {})

        dialog = self.create_rendering_dialog(project)
        self.check_quality_widget(dialog,
                                  vencoder="x264enc", vcodecsettings={"quantizer": 21, "pass": 5},
                                  preset="youtube",
                                  sensitive=True, value=Quality.MEDIUM)

        project_manager = project.app.project_manager
        with tempfile.NamedTemporaryFile() as temp_file:
            uri = Gst.filename_to_uri(temp_file.name)
            project_manager.save_project(uri=uri, backup=False)

            app2 = common.create_pitivi()
            project2 = app2.project_manager.load_project(uri)
            timeline_container = TimelineContainer(app2, editor_state=app2.gui.editor.editor_state)
            timeline_container.set_project(project2)
            common.create_main_loop().run(until_empty=True)
            self.assertEqual(project2.muxer, "qtmux")
            self.assertEqual(project2.vencoder, "x264enc")
            self.assertTrue(set({"quantizer": 21, "pass": 5}.items()).issubset(set(project2.vcodecsettings.items())))

        dialog2 = self.create_rendering_dialog(project2)
        self.assertTrue(set({"quantizer": 21, "pass": 5}.items()).issubset(set(project2.vcodecsettings.items())))
        self.check_quality_widget(dialog2,
                                  vencoder="x264enc", vcodecsettings=None,
                                  preset="youtube",
                                  sensitive=True, value=Quality.MEDIUM)

    def test_project_audiorate(self):
        """Checks the project audiorate when opening the Render dialog."""
        project = self.create_simple_project()
        # This is the audiorate from tears_of_steel.webm.
        self.assertEqual(project.audiorate, 44100)

        unused_dialog = self.create_rendering_dialog(project)

        # The audio rate is changed because the default render preset
        # has an audio encoder which does not support 44100.
        self.assertEqual(project.audiorate, 48000)

    def test__get_filesize_estimate(self):
        project = self.create_simple_project()
        dialog = self.create_rendering_dialog(project)
        dialog.current_position = 1
        from pitivi import render
        with mock.patch.object(render, "path_from_uri"):
            with mock.patch("pitivi.render.os.stat") as os_stat:
                os_stat.return_value.st_size = 0
                self.assertIsNone(dialog._get_filesize_estimate())
