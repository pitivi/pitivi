# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2015, Thibault Saunier <tsaunier@gnome.org>
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
"""Useful objects for testing."""
# pylint: disable=protected-access
import collections
import contextlib
import gc
import locale
import os
import shutil
import signal
import sys
import tempfile
import traceback
import unittest
from typing import List
from unittest import mock

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.application import Pitivi
from pitivi.clipproperties import ClipProperties
from pitivi.editorstate import EditorState
from pitivi.project import ProjectManager
from pitivi.settings import GlobalSettings
from pitivi.timeline.previewers import Previewer
from pitivi.timeline.previewers import PreviewGeneratorManager
from pitivi.timeline.timeline import TimelineContainer
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.proxy import ProxyingStrategy
from pitivi.utils.proxy import ProxyManager
from pitivi.utils.timeline import Selected
from pitivi.utils.timeline import Zoomable


def handle_uncaught_exception_func(exctype, value, trace):
    traceback.print_tb(trace)
    print(value, file=sys.stderr)
    sys.exit(1)


sys.excepthook = handle_uncaught_exception_func


def handle_glog_func(domain, level, message, udata):
    Gst.debug_print_stack_trace()
    traceback.print_stack()
    print("%s - %s" % (domain, message), file=sys.stderr)
    sys.exit(-11)


# GStreamer Not enabled because of an assertion on caps on the CI server.
# See https://gitlab.gnome.org/thiblahute/pitivi/-/jobs/66570
for category in ["Gtk", "Gdk", "GLib-GObject", "GES"]:
    GLib.log_set_handler(category, GLib.LogLevelFlags.LEVEL_CRITICAL, handle_glog_func, None)

detect_leaks = os.environ.get("PITIVI_TEST_DETECT_LEAKS", "0") not in ("0", "")
os.environ["PITIVI_USER_CACHE_DIR"] = tempfile.mkdtemp(suffix="pitiviTestsuite")
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")


# Disk access can take very long on the CI runners.
GITLAB_CI_TIMEOUT_FACTOR = 10


def factor_timeout(obj, attr_name):
    if not os.environ.get("GITLAB_CI", False):
        return

    attr_backup = "{}_original_timeout_value".format(attr_name)
    if not hasattr(obj, attr_backup):
        original_value = getattr(obj, attr_name)
        setattr(obj, attr_backup, original_value)
        setattr(obj, attr_name, original_value * GITLAB_CI_TIMEOUT_FACTOR)


def __create_settings(proxying_strategy=ProxyingStrategy.NOTHING,
                      num_transcoding_jobs=4,
                      **additional_settings):
    settings = GlobalSettings()
    settings.proxying_strategy = proxying_strategy
    settings.num_transcoding_jobs = num_transcoding_jobs
    for key, value in additional_settings.items():
        setattr(settings, key, value)
    return settings


def create_pitivi_mock(**settings):
    app = mock.MagicMock()
    app.write_action = mock.MagicMock(spec=Pitivi.write_action)
    app.settings = __create_settings(**settings)
    app.gui.editor.editor_state = EditorState(app.project_manager)
    app.proxy_manager = ProxyManager(app)

    app.gui.editor.viewer.action_group = Gio.SimpleActionGroup()

    # TODO: Get rid of Zoomable.app.
    Zoomable.app = app

    return app


def create_project():
    project_manager = ProjectManager(create_pitivi_mock())
    project = project_manager.new_blank_project()
    return project


def create_pitivi(**settings) -> Pitivi:
    """Creates a Pitivi app with the specified settings, ready to be tested."""
    app = Pitivi()
    app._setup()

    app.settings = __create_settings(**settings)

    # Patch a main window object so things depending on it can work properly.
    app.gui = mock.Mock()
    app.gui.editor.viewer.action_group = Gio.SimpleActionGroup()
    app.gui.editor.editor_state = EditorState(app.project_manager)

    return app


def create_timeline_container(app=None, **settings):
    if not app:
        app = create_pitivi_mock(leftClickAlsoSeeks=False, **settings)
        app.project_manager = ProjectManager(app)
        app.project_manager.new_blank_project()

    project = app.project_manager.current_project
    timeline_container = TimelineContainer(app, app.gui.editor.editor_state)
    timeline_container.set_project(project)

    timeline = timeline_container.timeline
    timeline.get_parent = mock.MagicMock(return_value=timeline_container)

    app.gui.editor.timeline_ui = timeline_container

    return timeline_container


def create_main_loop():
    mainloop = GLib.MainLoop()
    timed_out = False

    def timeout_cb(unused):
        nonlocal timed_out
        timed_out = True
        mainloop.quit()

    def run(timeout_seconds=5, until_empty=False):
        # Limit the test running time only when not debugging.
        debugging = os.environ.get("PITIVI_VSCODE_DEBUG", False)
        if not debugging:
            if os.environ.get("GITLAB_CI", False):
                # Disk access can take very long on the CI runners.
                timeout_seconds *= GITLAB_CI_TIMEOUT_FACTOR
            source = GLib.timeout_source_new_seconds(timeout_seconds)
            source.set_callback(timeout_cb)
            source.attach()
        if until_empty:
            GLib.idle_add(mainloop.quit, priority=GLib.PRIORITY_LOW + 1)
        GLib.MainLoop.run(mainloop)
        if not debugging:
            source.destroy()
        if timed_out:
            raise Exception("Timed out after %s seconds" % timeout_seconds)

    mainloop.run = run
    return mainloop


class OperationTimeout(Exception):
    pass


class CheckedOperationDuration:

    def __init__(self, seconds, error_message=None):
        if os.environ.get("GITLAB_CI", False):
            seconds *= GITLAB_CI_TIMEOUT_FACTOR
        if error_message is None:
            error_message = "operation timed out after %s seconds" % seconds
        self.seconds = seconds
        self.error_message = error_message

    def __handle_sigalrm(self, signum, frame):
        raise OperationTimeout(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.__handle_sigalrm)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)


def setup_project(assets_names: List[str]):
    """Sets up a Pitivi instance with no assets on the timeline."""
    assert isinstance(assets_names, list)

    def decorator(func):
        nonlocal assets_names

        def wrapper(self):
            with cloned_sample(*assets_names):
                self.app = create_pitivi()

                self.timeline_container = TimelineContainer(self.app, editor_state=self.app.gui.editor.editor_state)

                def loaded_cb(unused_pm, project):
                    self.timeline_container.set_project(project)
                    self.project = project
                    self.timeline = project.ges_timeline
                    layers = self.timeline.get_layers()
                    if layers:
                        self.layer = layers[0]
                    else:
                        self.layer = self.timeline.append_layer()

                self.app.project_manager.connect("new-project-loaded", loaded_cb)
                self.app.project_manager.new_blank_project()
                self.action_log = self.app.action_log
                project = self.app.project_manager.current_project

                timeline = self.timeline_container.timeline
                timeline.app.project_manager.current_project = project
                timeline.get_parent = mock.MagicMock(return_value=self.timeline_container)
                uris = collections.deque([get_sample_uri(fname) for fname in assets_names])
                mainloop = create_main_loop()

                def project_loaded_cb(project, timeline):
                    project.add_uris([uris.popleft()])

                def progress_cb(project, progress, estimated_time):
                    if progress == 100:
                        if uris:
                            project.add_uris([uris.popleft()])
                        else:
                            mainloop.quit()

                project.connect_after("loaded", project_loaded_cb)
                project.connect_after("asset-loading-progress", progress_cb)
                mainloop.run()

                project.disconnect_by_func(project_loaded_cb)
                project.disconnect_by_func(progress_cb)

                func(self)

            del self.app
            del self.project
            del self.timeline
            del self.layer
            del self.action_log
            del self.timeline_container

        return wrapper

    return decorator


def setup_project_with_clips(assets_names: List[str]):
    """Sets up a Pitivi instance with the specified assets on the timeline."""
    # Ensure this method is not being used directly as a decorator.
    assert isinstance(assets_names, list)

    def decorator(func):
        nonlocal assets_names

        @setup_project(list(set(assets_names)))
        def wrapper(self):
            assets = self.app.project_manager.current_project.list_assets(GES.UriClip)

            # Insert the assets in the same order that we got them.
            assets_by_name = {os.path.basename(asset.get_id()): asset for asset in assets}
            assets = [assets_by_name[name] for name in assets_names]

            self.timeline_container.insert_assets(assets, self.timeline.props.duration)

            func(self)

        return wrapper

    return decorator


def setup_timeline(func):
    def wrapped(self):
        self.app = create_pitivi()
        self.project = self.app.project_manager.new_blank_project()
        self.timeline = self.project.ges_timeline
        self.layer = self.timeline.append_layer()
        self.action_log = self.app.action_log

        self.timeline_container = TimelineContainer(self.app, editor_state=self.app.gui.editor.editor_state)
        self.timeline_container.set_project(self.project)
        self.app.gui.editor.timeline_ui = self.timeline_container

        timeline = self.timeline_container.timeline
        self.assertEqual(timeline.app.project_manager.current_project, self.project)
        timeline.get_parent = mock.MagicMock(return_value=self.timeline_container)

        func(self)

        del self.timeline_container
        del self.action_log
        del self.layer
        del self.timeline
        del self.project
        del self.app

    return wrapped


def setup_clipproperties(func):
    """Wraps a test, providing a usable ClipProperties."""
    def wrapped(self):
        app = self.timeline_container.app

        self.clipproperties = ClipProperties(app)
        self.clipproperties.set_project(self.project, self.timeline_container)

        self.transformation_box = self.clipproperties.transformation_expander
        self.transformation_box._new_project_loaded_cb(None, self.project)

        self.speed_box = self.clipproperties.speed_expander
        self.compositing_box = self.clipproperties.compositing_expander
        self.markers_box = self.clipproperties.marker_expander

        func(self)

        del self.markers_box
        del self.compositing_box
        del self.speed_box
        del self.transformation_box
        del self.clipproperties

    return wrapped


class TestCase(unittest.TestCase, Loggable):
    _tracked_types = (Gst.MiniObject, Gst.Element, Gst.Pad, Gst.Caps)

    def __init__(self, *args):
        Loggable.__init__(self)
        unittest.TestCase.__init__(self, *args)

    def gctrack(self):
        self.gccollect()
        self._tracked = []
        for obj in gc.get_objects():
            if not isinstance(obj, self._tracked_types):
                continue

            self._tracked.append(obj)

    def gccollect(self):
        ret = 0
        while True:
            count = gc.collect()
            ret += count
            if count == 0:
                break
        return ret

    def gcverify(self):
        leaked = []
        for obj in gc.get_objects():
            if not isinstance(obj, self._tracked_types) or \
                    obj in self._tracked:
                continue

            leaked.append(obj)

        # we collect again here to get rid of temporary objects created in the
        # above loop
        self.gccollect()

        for elt in leaked:
            print(elt)
            for i in gc.get_referrers(elt):
                print("   ", i)

        self.assertFalse(leaked, leaked)
        del self._tracked

    def setUp(self):
        # TODO: Get rid of Zoomable._instances.
        del Zoomable._instances[:]

        self._result = None
        self._num_failures = len(getattr(self._result, 'failures', []))
        self._num_errors = len(getattr(self._result, 'errors', []))
        if detect_leaks:
            self.gctrack()

        self.__zoom_level = Zoomable.get_current_zoom_level()

        # TODO: Get rid of Previewer.manager.
        assert hasattr(Previewer, "manager")
        Previewer.manager = PreviewGeneratorManager()

        from pitivi.utils import pipeline
        factor_timeout(pipeline, "WATCHDOG_TIMEOUT")
        factor_timeout(pipeline, "MAX_BRINGING_TO_PAUSED_DURATION")
        factor_timeout(pipeline, "MAX_SET_STATE_DURATION")

    def tearDown(self):
        # don't barf gc info all over the console if we have already failed a
        # test case
        if (self._num_failures < len(getattr(self._result, 'failures', [])) or
                self._num_errors < len(getattr(self._result, 'failures', []))):
            return
        if detect_leaks:
            self.gccollect()
            self.gcverify()
        Zoomable.set_zoom_level(self.__zoom_level)

    # override run() to save a reference to the test result object
    def run(self, result=None):
        if not result:
            result = self.defaultTestResult()
        self._result = result
        unittest.TestCase.run(self, result)

    def create_project_file_from_xges(self, xges):
        unused, xges_path = tempfile.mkstemp(suffix=".xges")
        proj_uri = Gst.filename_to_uri(os.path.abspath(xges_path))

        with open(xges_path, "w", encoding="UTF-8") as xges_file:
            xges_file.write(xges)

        return proj_uri

    def add_clip(self, layer: GES.Layer, start, inpoint=0, duration=10, clip_type=GES.TrackType.UNKNOWN):
        """Creates a clip on the specified layer."""
        asset = GES.UriClipAsset.request_sync(
            get_sample_uri("tears_of_steel.webm"))
        clip = layer.add_asset(asset, start, inpoint, duration, clip_type)
        self.assertIsNotNone(clip)

        return clip

    def add_clips_simple(self, timeline, num_clips):
        """Creates a number of clips on a new layer."""
        layer = timeline.ges_timeline.append_layer()
        clips = [self.add_clip(layer, i * 10) for i in range(num_clips)]
        self.assertEqual(len(clips), num_clips)
        return clips

    def click_clip(self, ges_clip: GES.Clip, expect_selected: bool, ctrl_key: bool = False):
        """Clicks the specified clip."""
        timeline = ges_clip.ui.timeline
        original_control_mask = timeline.get_parent().control_mask
        if ctrl_key:
            # Pretend the Ctrl key is being pressed.
            timeline.get_parent().control_mask = True

        # Simulate a click on the clip.
        event = mock.Mock(spec=Gdk.EventButton)
        event.x = 0
        event.y = 0
        event.get_button.return_value = (True, 1)
        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = ges_clip.ui
            timeline._button_press_event_cb(None, event)
            with mock.patch.object(ges_clip.ui, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (0, 0)
                with mock.patch.object(timeline, "get_layer_at") as get_layer_at:
                    get_layer_at.return_value = ges_clip.props.layer, None
                    ges_clip.ui._button_release_event_cb(None, event)
                    timeline._button_release_event_cb(None, event)

        if ctrl_key:
            timeline.get_parent().control_mask = original_control_mask

        self.assert_clip_selected(ges_clip, expect_selected)

    def assert_clip_selected(self, ges_clip, expect_selected):
        self.assertEqual(bool(ges_clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED),
                         expect_selected)
        self.assertEqual(ges_clip.selected.selected, expect_selected)

        for child in ges_clip.ui.get_children():
            if not hasattr(child, "selected"):
                continue

            self.assertEqual(bool(child.get_state_flags() & Gtk.StateFlags.SELECTED),
                             expect_selected)
            self.assertEqual(child.selected, expect_selected)

    def assert_caps_equal(self, caps1, caps2):
        if isinstance(caps1, str):
            caps1 = Gst.Caps(caps1)
        if isinstance(caps2, str):
            caps2 = Gst.Caps(caps2)

        self.assertTrue(caps1.is_equal(caps2),
                        "%s != %s" % (caps1.to_string(), caps2.to_string()))

    def assert_markers(self, ges_marker_list, expected_properties):
        """Asserts the content of a GES.MarkerList."""
        markers = ges_marker_list.get_markers()
        expected_positions = [properties[0] for properties in expected_properties]
        expected_comments = [properties[1] for properties in expected_properties]

        positions = [ges_marker.props.position for ges_marker in markers]
        self.assertListEqual(positions, expected_positions)

        comments = [ges_marker.get_string("comment") for ges_marker in markers]
        self.assertListEqual(comments, expected_comments)

    def assert_layers(self, layers):
        self.assertEqual(self.timeline.get_layers(), layers)
        self.check_priorities_and_positions(self.timeline.ui, layers, list(range(len(layers))))

    def check_priorities_and_positions(self, timeline, ges_layers,
                                       expected_priorities):
        layers_vbox = timeline.layout.layers_vbox
        mini_layers_vbox = timeline.mini_layout.layers_vbox

        # Check the layers priorities.
        priorities = [ges_layer.props.priority for ges_layer in ges_layers]
        self.assertListEqual(priorities, expected_priorities)

        expected_positions = [priority * 2 + 1
                              for priority in expected_priorities]

        # Check the positions of the Layer widgets.
        positions = [layers_vbox.child_get_property(ges_layer.ui, "position")
                     for ges_layer in ges_layers]
        self.assertListEqual(positions, expected_positions, layers_vbox.get_children())

        # Check the positions of the MiniLayer widgets.
        positions = [mini_layers_vbox.child_get_property(ges_layer.mini_ui, "position")
                     for ges_layer in ges_layers]
        self.assertListEqual(positions, expected_positions, mini_layers_vbox.get_children())

        # Check the positions of the LayerControl widgets.
        controls_vbox = timeline._layers_controls_vbox
        positions = [controls_vbox.child_get_property(ges_layer.control_ui, "position")
                     for ges_layer in ges_layers]
        self.assertListEqual(positions, expected_positions)

        # Check the number of the separators.
        count = len(ges_layers) + 1
        self.assertEqual(len(timeline._separators), count)

        expected_positions = [2 * index for index in range(count)]
        controls_separators, layers_separators, mini_layers_separators = list(zip(*timeline._separators))

        # Check the positions of the Layer separators.
        positions = [layers_vbox.child_get_property(separator, "position")
                     for separator in layers_separators]
        self.assertListEqual(positions, expected_positions)

        # Check the positions of the MiniLayer separators.
        positions = [mini_layers_vbox.child_get_property(separator, "position")
                     for separator in mini_layers_separators]
        self.assertListEqual(positions, expected_positions)

        # Check the positions of the LayerControl separators.
        positions = [controls_vbox.child_get_property(separator, "position")
                     for separator in controls_separators]
        self.assertListEqual(positions, expected_positions)

    def assert_effect_count(self, clip, count):
        effects = [effect for effect in clip.get_children(True)
                   if isinstance(effect, GES.Effect)]
        self.assertEqual(len(effects), count)

    def assert_control_source_values(self, control_source, expected_values, expected_timestamps):
        keyframes = control_source.get_all()

        values = [timed_value.value for timed_value in keyframes]
        self.assertListEqual(values, expected_values)

        timestamps = [timed_value.timestamp for timed_value in keyframes]
        self.assertListEqual(timestamps, expected_timestamps)

    def get_timeline_clips(self):
        for layer in self.timeline.layers:
            for clip in layer.get_clips():
                yield clip

    def get_transition_element(self, ges_layer):
        """Gets the first found GES.VideoTransition clip."""
        for clip in ges_layer.get_clips():
            if isinstance(clip, GES.TransitionClip):
                for element in clip.get_children(False):
                    if isinstance(element, GES.VideoTransition):
                        return element
        return None

    def get_clip_element(self, ges_clip, element_class=GES.VideoSource):
        for element in ges_clip.get_children(False):
            if isinstance(element, element_class):
                return element
        return None

    @staticmethod
    def commit_cb(action_log, stack, stacks):
        stacks.append(stack)

    def _wait_until_project_loaded(self):
        # Run the mainloop so the project is set up properly so that
        # the timeline creates transitions automatically.
        mainloop = create_main_loop()

        def loaded_cb(project, timeline):
            mainloop.quit()
        self.app.project_manager.current_project.connect("loaded", loaded_cb)
        mainloop.run()
        self.assertTrue(self.timeline.props.auto_transition)


@contextlib.contextmanager
def created_project_file(asset_uri):
    """Creates a project file.

    Yields:
        str: The URI of the new project
    """
    unused_fd, xges_path = tempfile.mkstemp()
    with open(xges_path, "w", encoding="UTF-8") as xges:
        xges.write("""
<ges version='0.1'>
  <project>
    <ressources>
      <asset id='%(asset_uri)s' extractable-type-name='GESUriClip' />
    </ressources>
    <timeline>
      <track caps='video/x-raw' track-type='4' track-id='0' />
      <layer priority='0'>
        <clip id='0' asset-id='%(asset_uri)s'
            type-name='GESUriClip' layer-priority='0' track-types='4'
            start='0' duration='2590000000' inpoint='0' rate='0' />
      </layer>
    </timeline>
</project>
</ges>""" % {'asset_uri': asset_uri})

    yield Gst.filename_to_uri(xges_path)

    os.remove(xges_path)


def get_sample_uri(sample, samples_dir=None):
    if not samples_dir:
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        samples_dir = os.path.join(tests_dir, "samples")
    return Gst.filename_to_uri(os.path.join(samples_dir, sample))


@contextlib.contextmanager
def cloned_sample(*samples):
    """Gets a context manager which commits the transaction at the end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        module = globals()
        original_get_sample_uri = module["get_sample_uri"]
        module["get_sample_uri"] = lambda sample: original_get_sample_uri(sample, samples_dir=tmpdir)
        try:
            for sample in samples:
                sample_path = path_from_uri(original_get_sample_uri(sample))
                clone_path = path_from_uri(get_sample_uri(sample))
                shutil.copyfile(sample_path, clone_path)
            yield tmpdir
        finally:
            module["get_sample_uri"] = original_get_sample_uri


def get_clip_children(ges_clip: GES.Clip, *track_types: List[GES.TrackType], recursive: bool = False):
    for ges_timeline_element in ges_clip.get_children(recursive):
        if not track_types or ges_timeline_element.get_track_type() in track_types:
            yield ges_timeline_element


def create_test_clip(clip_type):
    clip = clip_type()
    clip.selected = Selected()
    clip.ui = None
    clip.mini_ui = None
    return clip
