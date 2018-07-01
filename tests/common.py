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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
"""
A collection of objects to use for testing
"""
import contextlib
import gc
import os
import shutil
import sys
import tempfile
import traceback
import unittest
from unittest import mock

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk

from pitivi import check
from pitivi.application import Pitivi
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


def handle_uncaught_exception(exctype, value, trace):
    traceback.print_tb(trace)
    print(value, file=sys.stderr)
    sys.exit(1)


def handle_glog(domain, level, message, udata):
    traceback.print_stack()
    print("%s - %s" % (domain, message), file=sys.stderr)
    sys.exit(1)


sys.excepthook, oldHook = handle_uncaught_exception, sys.excepthook

for category in ["GStreamer", "Gtk", "Gdk", "GLib-GObject", "GES"]:
    GLib.log_set_handler(category, GLib.LogLevelFlags.LEVEL_CRITICAL, handle_glog, None)

detect_leaks = os.environ.get("PITIVI_TEST_DETECT_LEAKS", "0") not in ("0", "")
os.environ["PITIVI_USER_CACHE_DIR"] = tempfile.mkdtemp(suffix="pitiviTestsuite")


def __create_settings(proxyingStrategy=ProxyingStrategy.NOTHING,
                      numTranscodingJobs=4,
                      **additional_settings):
    settings = GlobalSettings()
    settings.proxyingStrategy = proxyingStrategy
    settings.numTranscodingJobs = numTranscodingJobs
    for key, value in additional_settings.items():
        setattr(settings, key, value)
    return settings


def create_pitivi_mock(**settings):
    app = mock.MagicMock()

    app.write_action = mock.MagicMock(spec=Pitivi.write_action)
    check.check_requirements()

    app.settings = __create_settings(**settings)
    app.proxy_manager = ProxyManager(app)

    # TODO: Get rid of Zoomable.app.
    from pitivi.utils.timeline import Zoomable
    Zoomable.app = app

    return app


def create_project():
    project_manager = ProjectManager(create_pitivi_mock())
    project_manager.newBlankProject()
    project = project_manager.current_project
    return project


def create_pitivi(**settings):
    app = Pitivi()
    app._setup()
    app.gui = mock.Mock()
    app.settings = __create_settings(**settings)
    return app


def create_timeline_container():
    app = create_pitivi_mock(leftClickAlsoSeeks=False)
    project_manager = ProjectManager(app)
    project_manager.newBlankProject()
    project = project_manager.current_project

    timeline_container = TimelineContainer(app)
    timeline_container.setProject(project)

    timeline = timeline_container.timeline
    timeline.app.project_manager.current_project = project
    timeline.get_parent = mock.MagicMock(return_value=timeline_container)

    app.gui.timeline_ui = timeline_container

    return timeline_container


def create_main_loop():
    mainloop = GLib.MainLoop()
    timed_out = False

    def timeout_cb(unused):
        nonlocal timed_out
        timed_out = True
        mainloop.quit()

    def run(timeout_seconds=5, until_empty=False):
        source = GLib.timeout_source_new_seconds(timeout_seconds)
        source.set_callback(timeout_cb)
        source.attach()
        if until_empty:
            GLib.idle_add(mainloop.quit)
        GLib.MainLoop.run(mainloop)
        source.destroy()
        if timed_out:
            raise Exception("Timed out after %s seconds" % timeout_seconds)

    mainloop.run = run
    return mainloop


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
            c = gc.collect()
            ret += c
            if c == 0:
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
        from pitivi.utils.timeline import Zoomable
        del Zoomable._instances[:]

        self._num_failures = len(getattr(self._result, 'failures', []))
        self._num_errors = len(getattr(self._result, 'errors', []))
        if detect_leaks:
            self.gctrack()

        self.__zoom_level = Zoomable.getCurrentZoomLevel()

        # TODO: Get rid of Previewer.manager.
        assert hasattr(Previewer, "manager")
        Previewer.manager = PreviewGeneratorManager()

    def tearDown(self):
        # don't barf gc info all over the console if we have already failed a
        # test case
        if (self._num_failures < len(getattr(self._result, 'failures', [])) or
                self._num_errors < len(getattr(self._result, 'failures', []))):
            return
        if detect_leaks:
            self.gccollect()
            self.gcverify()
        Zoomable.setZoomLevel(self.__zoom_level)

    # override run() to save a reference to the test result object
    def run(self, result=None):
        if not result:
            result = self.defaultTestResult()
        self._result = result
        unittest.TestCase.run(self, result)

    def toggle_clip_selection(self, ges_clip, expect_selected):
        """Toggles the selection state of @ges_clip."""
        selected = bool(ges_clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED)
        self.assertEqual(ges_clip.selected.selected, selected)

        # Simulate a click on the clip.
        event = mock.Mock(spec=Gdk.EventButton)
        event.x = 0
        event.y = 0
        event.get_button.return_value = (True, 1)
        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = ges_clip.ui
            ges_clip.ui.timeline._button_press_event_cb(None, event)
            with mock.patch.object(ges_clip.ui, "translate_coordinates") as translate_coordinates:
                translate_coordinates.return_value = (0, 0)
                with mock.patch.object(ges_clip.ui.timeline, "_get_layer_at") as _get_layer_at:
                    _get_layer_at.return_value = ges_clip.props.layer, None
                    ges_clip.ui._button_release_event_cb(None, event)

        self.assertEqual(bool(ges_clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED),
                         expect_selected)
        self.assertEqual(ges_clip.selected.selected, expect_selected)

    def assert_caps_equal(self, caps1, caps2):
        if isinstance(caps1, str):
            caps1 = Gst.Caps(caps1)
        if isinstance(caps2, str):
            caps2 = Gst.Caps(caps2)

        self.assertTrue(caps1.is_equal(caps2),
                        "%s != %s" % (caps1.to_string(), caps2.to_string()))


@contextlib.contextmanager
def created_project_file(asset_uri):
    """Creates a project file.

    Yields:
        str: The URI of the new project
    """
    unused_fd, xges_path = tempfile.mkstemp()
    with open(xges_path, "w") as xges:
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


def get_sample_clip(sample):
    uri = get_sample_uri(sample)
    asset = GES.UriClipAsset.request_sync(uri)
    clip = asset.extract()
    return clip


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


def get_clip_children(ges_clip, *track_types, recursive=False):
    for ges_timeline_element in ges_clip.get_children(recursive):
        if not track_types or ges_timeline_element.get_track_type() in track_types:
            yield ges_timeline_element


def create_test_clip(clip_type):
    clip = clip_type()
    clip.selected = Selected()
    clip.ui = None
    return clip
