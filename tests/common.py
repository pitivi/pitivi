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
import tempfile
import unittest
from unittest import mock

from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk

from pitivi import check
from pitivi.application import Pitivi
from pitivi.project import ProjectManager
from pitivi.settings import GlobalSettings
from pitivi.timeline.timeline import TimelineContainer
from pitivi.utils.loggable import Loggable
from pitivi.utils.proxy import ProxyingStrategy
from pitivi.utils.proxy import ProxyManager
from pitivi.utils.timeline import Selected

detect_leaks = os.environ.get("PITIVI_TEST_DETECT_LEAKS", "0") not in ("0", "")
os.environ["PITIVI_USER_CACHE_DIR"] = tempfile.mkdtemp("pitiviTestsuite")


def clean_pitivi_mock(app):
    app.settings = None
    app.proxy_manager = None


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
    app = create_pitivi_mock()
    project_manager = ProjectManager(app)
    project_manager.newBlankProject()
    project = project_manager.current_project

    timeline_container = TimelineContainer(app)
    timeline_container.setProject(project)

    timeline = timeline_container.timeline
    timeline.app.project_manager.current_project = project
    timeline.get_parent = mock.MagicMock(return_value=timeline_container)

    app.gui.timeline_ui = timeline_container
    timeline.app.settings.leftClickAlsoSeeks = False

    return timeline_container


def create_main_loop():
    mainloop = GLib.MainLoop()
    timed_out = False

    def quit_cb(unused):
        nonlocal timed_out
        timed_out = True
        mainloop.quit()

    def run(timeout_seconds=5):
        source = GLib.timeout_source_new_seconds(timeout_seconds)
        source.set_callback(quit_cb)
        source.attach()
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
        self._num_failures = len(getattr(self._result, 'failures', []))
        self._num_errors = len(getattr(self._result, 'errors', []))
        if detect_leaks:
            self.gctrack()

    def tearDown(self):
        # don't barf gc info all over the console if we have already failed a
        # test case
        if (self._num_failures < len(getattr(self._result, 'failures', [])) or
                self._num_errors < len(getattr(self._result, 'failures', []))):
            return
        if detect_leaks:
            self.gccollect()
            self.gcverify()

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
        event = mock.Mock()
        event.get_button.return_value = (True, 1)
        with mock.patch.object(Gtk, "get_event_widget") as get_event_widget:
            get_event_widget.return_value = ges_clip.ui
            ges_clip.ui.timeline._button_press_event_cb(None, event)
        ges_clip.ui._button_release_event_cb(None, event)

        self.assertEqual(bool(ges_clip.ui.get_state_flags() & Gtk.StateFlags.SELECTED),
                         expect_selected)
        self.assertEqual(ges_clip.selected.selected, expect_selected)


@contextlib.contextmanager
def created_project_file(asset_uri="file:///icantpossiblyexist.png"):
    """
    Create a project file.

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


def get_sample_uri(sample):
    assets_dir = os.path.dirname(os.path.abspath(__file__))

    return "file://%s" % os.path.join(assets_dir, "samples", sample)


def clean_proxy_samples():
    _dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
    proxy_manager = ProxyManager(mock.MagicMock())

    for f in os.listdir(_dir):
        if f.endswith(proxy_manager.proxy_extension):
            f = os.path.join(_dir, f)
            os.remove(f)


def create_test_clip(clip_type):
    clip = clip_type()
    clip.selected = Selected()
    clip.ui = None
    return clip
