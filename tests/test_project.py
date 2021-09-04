# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
# Copyright (c) 2013, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the pitivi.project module."""
# pylint: disable=consider-using-with,protected-access
import collections
import os
import tempfile
import time
from unittest import mock

from gi.repository import GES
from gi.repository import Gst

from pitivi.medialibrary import AssetThumbnail
from pitivi.medialibrary import MediaLibraryWidget
from pitivi.project import Project
from pitivi.project import ProjectManager
from pitivi.utils.misc import path_from_uri
from pitivi.utils.proxy import ProxyingStrategy
from tests import common


class ProjectManagerListener():

    def __init__(self, manager):
        self.manager = manager
        self.connect_to_project_manager()
        self._reset()

    def _reset(self):
        self.signals = []

    def connect_to_project_manager(self):
        for signal in ("new-project-loading", "new-project-loaded",
                       "new-project-created", "new-project-failed", "missing-uri",
                       "closing-project", "project-closed"):
            self.manager.connect(signal, self._record_signal, signal)

    def _record_signal(self, *args):
        signal = args[-1]
        args = args[1:-1]
        self.signals.append((signal, args))

        return True


class TestProjectManager(common.TestCase):

    def setUp(self):
        super().setUp()
        self.setup_app()

    def setup_app(self, app=None):
        if not app:
            app = mock.MagicMock()
        self.manager = ProjectManager(app)
        self.listener = ProjectManagerListener(self.manager)
        self.signals = self.listener.signals

    def test_loading_missing_project_file(self):
        """Checks new-project-failed is emitted for unsuitable formatters."""
        project_uri = Gst.filename_to_uri(tempfile.NamedTemporaryFile().name)
        self.manager.load_project(project_uri)

        # loading
        name, args = self.signals[0]
        self.assertEqual(project_uri, args[0].get_uri(), self.signals)

        # failed
        name, args = self.signals[1]
        self.assertEqual("new-project-failed", name)
        signal_uri, unused_message = args
        self.assertEqual(project_uri, signal_uri, self.signals)

    def test_new_blank_project_signals(self):
        self.manager.new_blank_project()

        name, _args = self.signals[0]
        self.assertEqual("new-project-loading", name, self.signals)

        name, _args = self.signals[1]
        self.assertEqual("new-project-created", name, self.signals)

        name, _args = self.signals[2]
        self.assertEqual("new-project-loaded", name, self.signals)

    def test_missing_uri_forwarded(self):
        self.setup_app(app=common.create_pitivi_mock())
        mainloop = common.create_main_loop()

        def missing_uri_cb(self, project, error, clip_asset, result):
            result[0] = True
            mainloop.quit()

        result = [False]
        self.manager.connect("missing-uri", missing_uri_cb, result)

        with common.cloned_sample():
            asset_uri = common.get_sample_uri("missing.png")
            with common.created_project_file(asset_uri) as uri:
                self.assertIsNotNone(self.manager.load_project(uri))
                mainloop.run()
        self.assertTrue(result[0], "missing-uri has not been emitted")

    def test_loaded(self):
        mainloop = common.create_main_loop()

        def new_project_loaded_cb(project_manager, project):
            mainloop.quit()

        self.manager.connect("new-project-loaded", new_project_loaded_cb)

        with common.cloned_sample("flat_colour1_640x480.png"):
            asset_uri = common.get_sample_uri("flat_colour1_640x480.png")
            with common.created_project_file(asset_uri=asset_uri) as uri:
                project = self.manager.load_project(uri)
                self.assertIsNotNone(project)
                mainloop.run()

        self.assertFalse(project.at_least_one_asset_missing)
        self.assertTrue(project.loaded)
        self.assertFalse(project.has_unsaved_modifications())

    def test_close_running_project_no_project(self):
        self.assertTrue(self.manager.close_running_project())
        self.assertFalse(self.signals)

    def test_close_running_project_refuse_from_signal(self):
        def closing_cb(manager, project):
            return False

        self.manager.current_project = mock.Mock()
        self.manager.current_project.uri = "file:///ciao"
        self.manager.connect("closing-project", closing_cb)

        self.assertFalse(self.manager.close_running_project())
        self.assertEqual(1, len(self.signals))
        name, args = self.signals[0]
        self.assertEqual("closing-project", name)
        project = args[0]
        self.assertTrue(project is self.manager.current_project)

    def test_close_running_project(self):
        project = self.manager.new_blank_project()
        self.assertTrue(self.manager.close_running_project())
        self.assertEqual(5, len(self.signals), self.signals)

        name, args = self.signals[-2]
        self.assertEqual("closing-project", name)
        self.assertEqual(args[0], project)

        name, args = self.signals[-1]
        self.assertEqual("project-closed", name)
        self.assertEqual(args[0], project)

        self.assertTrue(self.manager.current_project is None)

    def test_new_blank_project(self):
        self.assertIsNotNone(self.manager.new_blank_project())
        self.assertEqual(3, len(self.signals))

        name, args = self.signals[0]
        self.assertEqual("new-project-loading", name)
        project = args[0]
        self.assertTrue(project.get_uri() is None)

        name, args = self.signals[1]
        self.assertEqual("new-project-created", name)
        project = args[0]
        self.assertEqual(project.get_uri(), project.uri)

        name, args = self.signals[2]
        self.assertEqual("new-project-loaded", name)
        project = args[0]
        self.assertTrue(project is self.manager.current_project)

    def test_marker_container(self):
        project = self.manager.new_blank_project()
        self.assertIsNotNone(project)
        self.assertIsNotNone(project.ges_timeline)
        self.assertIsNotNone(project.ges_timeline.get_marker_list("markers"))

    def test_save_project(self):
        self.manager.new_blank_project()

        unused, path = tempfile.mkstemp(suffix=".xges")
        unused, path2 = tempfile.mkstemp(suffix=".xges")
        try:
            uri = "file://" + os.path.abspath(path)
            uri2 = "file://" + os.path.abspath(path2)

            # Save the project.
            self.assertTrue(self.manager.save_project(uri=uri, backup=False))
            self.assertTrue(os.path.isfile(path))

            # Wait a bit.
            time.sleep(0.1)

            # Save the project at a new location.
            self.assertTrue(self.manager.save_project(uri2, backup=False))
            self.assertTrue(os.path.isfile(path2))

            # Make sure the old path and the new path have different mtimes.
            mtime = os.path.getmtime(path)
            mtime2 = os.path.getmtime(path2)
            self.assertLess(mtime, mtime2)

            # Wait a bit more.
            time.sleep(0.1)

            # Save project again under the new path (by omitting uri arg)
            self.assertTrue(self.manager.save_project(backup=False))

            # regression test for bug 594396
            # make sure we didn't save to the old URI
            self.assertEqual(mtime, os.path.getmtime(path))
            # make sure we did save to the new URI
            self.assertLess(mtime2, os.path.getmtime(path2))
        finally:
            os.remove(path)
            os.remove(path2)

    def test_make_backup_uri(self):
        uri = "file:///tmp/x.xges"
        self.assertEqual(uri + "~", self.manager._make_backup_uri(uri))

    def test_backup_project(self):
        self.manager.new_blank_project()

        # Assign an uri to the project where it's saved by default.
        unused, xges_path = tempfile.mkstemp(suffix=".xges")
        uri = "file://" + os.path.abspath(xges_path)
        self.manager.current_project.uri = uri
        # This is where the automatic backup file is saved.
        backup_uri = self.manager._make_backup_uri(uri)

        # Save the backup
        self.assertTrue(self.manager.save_project(
            self.manager.current_project, backup=True))
        self.assertTrue(os.path.isfile(path_from_uri(backup_uri)))

        self.manager.close_running_project()
        self.assertFalse(os.path.isfile(path_from_uri(backup_uri)),
                         "Backup file not deleted when project closed")


class TestProjectLoading(common.TestCase):

    def test_loaded_callback(self):
        mainloop = common.create_main_loop()

        def loaded_cb(project, timeline):
            # If not called, the timeout of the mainloop will fail the test.
            mainloop.quit()

        # Create a blank project and save it.
        project = common.create_project()
        project.connect("loaded", loaded_cb)
        mainloop.run()
        # The blank project loading succeeded emitting signal "loaded".

        self.assertIsNotNone(project.ges_timeline)
        self.assertEqual(len(project.ges_timeline.get_layers()), 1)

        # Load the blank project and make sure "loaded" is triggered.
        unused, xges_path = tempfile.mkstemp()
        uri = "file://%s" % xges_path
        try:
            # Save so we can close it without complaints.
            project.save(project.ges_timeline, uri, None, overwrite=True)

            project2 = common.create_project()
            project2.connect("loaded", loaded_cb)
            mainloop.run()
            # The blank project loading succeeded emitting signal "loaded".

            self.assertIsNotNone(project2.ges_timeline)
            self.assertEqual(len(project2.ges_timeline.get_layers()), 1)
        finally:
            os.remove(xges_path)

    def test_asset_added_signal(self):
        app = common.create_pitivi()
        project = app.project_manager.new_blank_project()
        proxy_manager = app.proxy_manager

        mainloop = common.create_main_loop()

        def asset_added_cb(project, asset, assets):
            assets.append(asset)

        assets = []
        project.connect("asset-added", asset_added_cb, assets)

        def proxy_ready_cb(unused_proxy_manager, asset, proxy):
            mainloop.quit()

        proxy_manager.connect("proxy-ready", proxy_ready_cb)

        uris = [common.get_sample_uri("tears_of_steel.webm")]
        project.add_uris(uris)

        mainloop.run()

        self.assertEqual(len(assets), 1, assets)

    def load_project_with_missing_proxy(self):
        """Loads a project with missing proxies."""
        uris = [common.get_sample_uri("1sec_simpsons_trailer.mp4")]
        proxy_uri = uris[0] + ".232417.proxy.mov"
        xges = r"""<ges version='0.3'>
  <project properties='properties;' metadatas='metadatas, name=(string)&quot;New\ Project&quot;, author=(string)Unknown, render-scale=(double)100;'>
    <encoding-profiles>
    </encoding-profiles>
    <ressources>
      <asset id='%(uri)s' extractable-type-name='GESUriClip' properties='properties, supported-formats=(int)6, duration=(guint64)1228000000;' metadatas='metadatas, audio-codec=(string)&quot;MPEG-4\ AAC\ audio&quot;, maximum-bitrate=(uint)130625, bitrate=(uint)130625, datetime=(datetime)2007-02-19T05:03:04Z, encoder=(string)Lavf54.6.100, container-format=(string)&quot;ISO\ MP4/M4A&quot;, video-codec=(string)&quot;H.264\ /\ AVC&quot;, file-size=(guint64)232417;'  proxy-id='file:///home/thiblahute/devel/pitivi/flatpak/pitivi/tests/samples/1sec_simpsons_trailer.mp4.232417.proxy.mov' />
      <asset id='%(proxy_uri)s' extractable-type-name='GESUriClip' properties='properties, supported-formats=(int)6, duration=(guint64)1228020833;' metadatas='metadatas, container-format=(string)Matroska, audio-codec=(string)Opus, language-code=(string)en, encoder=(string)Lavf54.6.100, bitrate=(uint)64000, video-codec=(string)&quot;Motion\ JPEG&quot;, file-size=(guint64)4695434;' />
    </ressources>
    <timeline properties='properties, auto-transition=(boolean)true, snapping-distance=(guint64)0;' metadatas='metadatas, duration=(guint64)0;'>
      <track caps='video/x-raw(ANY)' track-type='4' track-id='0' properties='properties, async-handling=(boolean)false, message-forward=(boolean)true, caps=(string)&quot;video/x-raw\(ANY\)&quot;, restriction-caps=(string)&quot;video/x-raw\,\ width\=\(int\)720\,\ height\=\(int\)576\,\ framerate\=\(fraction\)25/1&quot;, mixing=(boolean)true;' metadatas='metadatas;'/>
      <track caps='audio/x-raw(ANY)' track-type='2' track-id='1' properties='properties, async-handling=(boolean)false, message-forward=(boolean)true, caps=(string)&quot;audio/x-raw\(ANY\)&quot;, restriction-caps=(string)&quot;audio/x-raw\,\ format\=\(string\)S32LE\,\ channels\=\(int\)2\,\ rate\=\(int\)44100\,\ layout\=\(string\)interleaved&quot;, mixing=(boolean)true;' metadatas='metadatas;'/>
      <layer priority='0' properties='properties, auto-transition=(boolean)true;' metadatas='metadatas, volume=(float)1;'>
        <clip id='0' asset-id='%(proxy_uri)s' type-name='GESUriClip' layer-priority='0' track-types='6' start='0' duration='1228000000' inpoint='0' rate='0' properties='properties, name=(string)uriclip0, mute=(boolean)false, is-image=(boolean)false;' >
          <source track-id='1' children-properties='properties, GstVolume::mute=(boolean)false, GstVolume::volume=(double)1;'>
            <binding type='direct' source_type='interpolation' property='volume' mode='1' track_id='1' values =' 0:0.10000000000000001  1228000000:0.10000000000000001 '/>
          </source>
          <source track-id='0' children-properties='properties, GstFramePositioner::alpha=(double)1, GstDeinterlace::fields=(int)0, GstFramePositioner::height=(int)720, GstDeinterlace::mode=(int)0, GstFramePositioner::posx=(int)0, GstFramePositioner::posy=(int)0, GstDeinterlace::tff=(int)0, GstFramePositioner::width=(int)1280;'>
            <binding type='direct' source_type='interpolation' property='alpha' mode='1' track_id='0' values =' 0:1  1228000000:1 '/>
          </source>
        </clip>
      </layer>
      <groups>
      </groups>
    </timeline>
</project>
</ges>""" % {"uri": uris[0], "proxy_uri": proxy_uri}
        app = common.create_pitivi(proxying_strategy=ProxyingStrategy.ALL)
        app.recent_manager.remove_item = mock.Mock(return_value=True)
        proxy_manager = app.proxy_manager
        project_manager = app.project_manager
        medialib = MediaLibraryWidget(app)

        mainloop = common.create_main_loop()

        proj_uri = self.create_project_file_from_xges(xges)

        def closing_project_cb(*args, **kwargs):
            # Do not ask whether to save project on closing.
            return True

        def proxy_ready_cb(proxy_manager, asset, proxy):
            self.assertEqual(proxy.props.id, proxy_uri)
            mainloop.quit()

        project_manager.connect("closing-project", closing_project_cb)
        proxy_manager.connect_after("proxy-ready", proxy_ready_cb)

        app.project_manager.load_project(proj_uri)
        return mainloop, app, medialib, proxy_uri

    def test_load_project_with_missing_proxy(self):
        """Checks loading a project with missing proxies."""
        with common.cloned_sample("1sec_simpsons_trailer.mp4"):
            mainloop, _app, medialib, proxy_uri = self.load_project_with_missing_proxy()
            mainloop.run()

        self.assertEqual(medialib.store.get_n_items(), 1)
        self.assertEqual(medialib.store[0].asset.props.id,
                         proxy_uri)
        self.assertEqual(medialib.store[0].thumb_decorator.state,
                         AssetThumbnail.PROXIED)

    def test_load_project_with_missing_proxy_progress_tracking(self):
        """Checks progress tracking of loading project with missing proxies."""
        from gi.repository import GstTranscoder

        with common.cloned_sample("1sec_simpsons_trailer.mp4"):
            # Disable proxy generation by not making it start ever.
            # This way we are sure it will not finish before we test
            # the state while it is being rebuilt.
            with mock.patch.object(GstTranscoder.Transcoder, "run_async"):
                mainloop, app, medialib, _proxy_uri = self.load_project_with_missing_proxy()
                uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")

                app.project_manager.connect("new-project-loaded", lambda x, y: mainloop.quit())
                mainloop.run()

        self.assertEqual(medialib.store.get_n_items(), 1)
        self.assertEqual(medialib.store[0].asset.props.id,
                         uri)
        self.assertEqual(medialib.store[0].thumb_decorator.state,
                         AssetThumbnail.IN_PROGRESS)

    def test_load_project_with_missing_proxy_stop_generating_and_proxy(self):
        """Checks cancelling creation of a missing proxies and forcing it again."""
        from gi.repository import GstTranscoder

        with common.cloned_sample("1sec_simpsons_trailer.mp4"):
            # Disable proxy generation by not making it start ever.
            # This way we are sure it will not finish before we test
            # stop generating the proxy and restart it.
            with mock.patch.object(GstTranscoder.Transcoder, "run_async"):
                mainloop, app, medialib, proxy_uri = self.load_project_with_missing_proxy()

                app.project_manager.connect("new-project-loaded", lambda x, y: mainloop.quit())
                mainloop.run()
                asset = medialib.store[0].asset
                app.project_manager.current_project.disable_proxies_for_assets([asset])

            row = medialib.store[0]
            asset = row.asset
            self.assertEqual(medialib._progressbar.get_fraction(), 1.0)
            uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")
            self.assertEqual(asset.props.id, uri)
            self.assertEqual(asset.ready, True)
            self.assertEqual(asset.creation_progress, 100)
            self.assertEqual(row.thumb_decorator.state,
                             AssetThumbnail.NO_PROXY)

            app.project_manager.current_project.use_proxies_for_assets([asset])
            mainloop.run()

        row = medialib.store[0]
        asset = row.asset
        self.assertEqual(medialib._progressbar.is_visible(), False)
        self.assertEqual(asset.props.id, proxy_uri)
        self.assertEqual(asset.ready, True)
        self.assertEqual(asset.creation_progress, 100)
        self.assertEqual(row.thumb_decorator.state,
                         AssetThumbnail.PROXIED)

    def test_loading_project_with_moved_asset(self):
        """Loads a project with moved asset."""
        app = common.create_pitivi(proxying_strategy=ProxyingStrategy.NOTHING)

        proj_uri = self.create_project_file_from_xges("""<ges version='0.3'>
            <project properties='properties;' metadatas='metadatas;'>
                <ressources>
                    <asset id='file://this/is/a/moved/asset.mp4' extractable-type-name='GESUriClip'
                        properties='properties, supported-formats=(int)6, duration=(guint64)1228000000;' metadatas='metadatas' />
                </ressources>
            </project>
            </ges>""")
        project_manager = app.project_manager
        medialib = MediaLibraryWidget(app)

        mainloop = common.create_main_loop()

        def new_project_loaded_cb(*args, **kwargs):
            mainloop.quit()

        def missing_uri_cb(project_manager, project, unused_error, asset):
            return common.get_sample_uri("1sec_simpsons_trailer.mp4")

        project_manager.connect("missing-uri", missing_uri_cb)
        project_manager.connect("new-project-loaded", new_project_loaded_cb)

        project_manager.load_project(proj_uri)
        with common.cloned_sample("1sec_simpsons_trailer.mp4"):
            mainloop.run()
        self.assertEqual(medialib._progressbar.get_fraction(), 1.0)

    def test_loading_project_with_moved_assets_and_deleted_proxy(self):
        """Loads a project with moved asset and deleted proxy file."""
        mainloop = common.create_main_loop()

        created_proxies = []

        def proxy_ready_cb(unused_proxy_manager, asset, proxy):
            created_proxies.append(asset)
            if len(created_proxies) == 2:
                mainloop.quit()

        app = common.create_pitivi(proxying_strategy=ProxyingStrategy.ALL)
        app.proxy_manager.connect("proxy-ready", proxy_ready_cb)

        proj_uri = self.create_project_file_from_xges(r"""<ges version='0.3'>
  <project properties='properties;' metadatas='metadatas, name=(string)&quot;New\ Project&quot;, author=(string)Unknown, render-scale=(double)100, format-version=(string)0.3;'>
    <ressources>
      <asset id='file:///nop/1sec_simpsons_trailer.mp4' extractable-type-name='GESUriClip' properties='properties, supported-formats=(int)6, duration=(guint64)1228000000;' metadatas='metadatas, audio-codec=(string)&quot;MPEG-4\ AAC\ audio&quot;, maximum-bitrate=(uint)130625, bitrate=(uint)130625, datetime=(datetime)2007-02-19T05:03:04Z, encoder=(string)Lavf54.6.100, container-format=(string)&quot;ISO\ MP4/M4A&quot;, video-codec=(string)&quot;H.264\ /\ AVC&quot;, file-size=(guint64)232417;'  proxy-id='file:///nop/1sec_simpsons_trailer.mp4.232417.proxy.mov' />
      <asset id='file:///nop/tears_of_steel.webm' extractable-type-name='GESUriClip' properties='properties, supported-formats=(int)6, duration=(guint64)2003000000;' metadatas='metadatas, container-format=(string)Matroska, language-code=(string)und, application-name=(string)Lavc56.60.100, encoder=(string)&quot;Xiph.Org\ libVorbis\ I\ 20150105\ \(\342\233\204\342\233\204\342\233\204\342\233\204\)&quot;, encoder-version=(uint)0, audio-codec=(string)Vorbis, nominal-bitrate=(uint)80000, bitrate=(uint)80000, video-codec=(string)&quot;VP8\ video&quot;, file-size=(guint64)223340;' proxy-id='file:///nop/tears_of_steel.webm.223340.proxy.mov'/>
      <asset id='file:///nop/1sec_simpsons_trailer.mp4.232417.proxy.mov' extractable-type-name='GESUriClip' properties='properties, supported-formats=(int)6, duration=(guint64)1228020833;' metadatas='metadatas, container-format=(string)Matroska, audio-codec=(string)Opus, language-code=(string)en, encoder=(string)Lavf54.6.100, bitrate=(uint)64000, video-codec=(string)&quot;Motion\ JPEG&quot;, file-size=(guint64)4694708;' />
      <asset id='file:///nop/tears_of_steel.webm.223340.proxy.mov' extractable-type-name='GESUriClip' properties='properties, supported-formats=(int)6, duration=(guint64)2003000000;' metadatas='metadatas, container-format=(string)Matroska, language-code=(string)und, application-name=(string)Lavc56.60.100, encoder=(string)&quot;Xiph.Org\ libVorbis\ I\ 20150105\ \(\342\233\204\342\233\204\342\233\204\342\233\204\)&quot;, encoder-version=(uint)0, audio-codec=(string)Vorbis, nominal-bitrate=(uint)80000, bitrate=(uint)80000, video-codec=(string)&quot;VP8\ video&quot;, file-size=(guint64)223340;' />
    </ressources>
</project>
</ges>""")
        project_manager = app.project_manager
        medialib = MediaLibraryWidget(app)

        # Remove proxy
        with common.cloned_sample("1sec_simpsons_trailer.mp4", "tears_of_steel.webm"):
            def new_project_loaded_cb(*args, **kwargs):
                mainloop.quit()

            missing_uris = []

            def missing_uri_cb(project_manager, project, unused_error, asset):
                missing_uris.append(asset.props.id)
                return common.get_sample_uri(os.path.basename(asset.props.id))

            project_manager.connect("missing-uri", missing_uri_cb)
            project_manager.connect("new-project-loaded", new_project_loaded_cb)

            project_manager.load_project(proj_uri)
            mainloop.run()
            self.assertEqual(len(missing_uris), 1,
                             "missing_uri_cb should be called only once, got %s." % missing_uris)
            self.assertEqual(medialib._progressbar.get_fraction(), 1.0)
            mainloop.run()
            self.assertEqual(medialib.store.get_n_items(), 2,
                             "We should have one asset displayed in the MediaLibrary.")

            self.assertEqual(medialib.store[0].thumb_decorator.state, AssetThumbnail.PROXIED)
            self.assertEqual(medialib.store[1].thumb_decorator.state, AssetThumbnail.PROXIED)


class TestProjectSettings(common.TestCase):

    def test_audio(self):
        project = common.create_project()
        self.assertEqual(project.audiochannels, 2)
        self.assertEqual(project.audiorate, 96000)

        project.audiochannels = 6
        self.assertEqual(project.audiochannels, 6)
        project.audiorate = 44100
        self.assertEqual(project.audiorate, 44100)

    def test_video(self):
        project = common.create_project()
        self.assertEqual(project.videowidth, 1920)
        self.assertEqual(project.videoheight, 1080)
        self.assertEqual(project.videorate, Gst.Fraction(30, 1))

        project.videowidth = 3840
        self.assertEqual(project.videowidth, 3840)
        project.videoheight = 2160
        self.assertEqual(project.videoheight, 2160)
        project.videorate = Gst.Fraction(50, 7)
        self.assertEqual(project.videorate, Gst.Fraction(50, 7))

    def test_set_audio_prop(self):
        timeline = common.create_timeline_container()
        project = timeline.app.project_manager.current_project
        project.add_uris([common.get_sample_uri("mp3_sample.mp3")])

        audio_track = [t for t in project.ges_timeline.get_tracks() if isinstance(t, GES.AudioTrack)][0]
        mainloop = common.create_main_loop()

        def progress_cb(project, progress, estimated_time):
            if progress == 100:
                mainloop.quit()

        project.connect_after("asset-loading-progress", progress_cb)
        mainloop.run()

        expected = Gst.Caps("audio/x-raw,channels=(int)2,rate=(int)44100")
        ccaps = audio_track.props.restriction_caps
        self.assertTrue(ccaps.is_equal_fixed(expected), "%s != %s" % (ccaps, expected))

        project.audiochannels = 6

        expected = Gst.Caps("audio/x-raw,channels=(int)6,rate=(int)44100")
        ccaps = audio_track.props.restriction_caps
        self.assertTrue(ccaps.is_equal_fixed(expected), "%s != %s" % (ccaps, expected))

    def test_initialization(self):
        mainloop = common.create_main_loop()
        uris = collections.deque([
            common.get_sample_uri("flat_colour1_640x480.png"),
            common.get_sample_uri("tears_of_steel.webm"),
            common.get_sample_uri("1sec_simpsons_trailer.mp4")])

        def loaded_cb(project, timeline):
            project.add_uris([uris.popleft()])

        def progress_cb(project, progress, estimated_time):
            if progress == 100:
                if uris:
                    project.add_uris([uris.popleft()])
                else:
                    mainloop.quit()

        # Create a blank project and add some assets.
        project = common.create_project()
        self.assertTrue(project._has_default_video_settings)
        self.assertTrue(project._has_default_audio_settings)

        project.connect_after("loaded", loaded_cb)
        project.connect_after("asset-loading-progress", progress_cb)

        mainloop.run()

        assets = project.list_assets(GES.UriClip)
        self.assertEqual(3, len(assets), assets)

        self.assertFalse(project._has_default_video_settings)
        self.assertFalse(project._has_default_audio_settings)

        # The audio settings should match tears_of_steel.webm
        self.assertEqual(1, project.audiochannels)
        self.assertEqual(44100, project.audiorate)

        # The video settings should match tears_of_steel.webm
        self.assertEqual(960, project.videowidth)
        self.assertEqual(400, project.videoheight)
        self.assertEqual(Gst.Fraction(24, 1), project.videorate)

    def test_load(self):
        project = Project(uri="fake.xges", app=common.create_pitivi_mock())
        self.assertEqual(project.name, "fake")
        self.assertFalse(project._has_default_video_settings)
        self.assertFalse(project._has_default_audio_settings)

    def test_name(self):
        project = Project(common.create_pitivi_mock())

        project.uri = "file:///tmp/A%20B.xges"
        self.assertEqual(project.name, "A B")

        project.uri = "file:///tmp/%40%23%24%5E%26%60.xges"
        self.assertEqual(project.name, "@#$^&`")

    def test_scaled_proxy_size(self):
        app = common.create_pitivi_mock(default_scaled_proxy_width=123,
                                        default_scaled_proxy_height=456)
        manager = ProjectManager(app)
        project = manager.new_blank_project()
        self.assertFalse(project.has_scaled_proxy_size())
        self.assertEqual(project.scaled_proxy_width, 123)
        self.assertEqual(project.scaled_proxy_height, 456)

        with tempfile.NamedTemporaryFile() as temp_file:
            uri = Gst.filename_to_uri(temp_file.name)
            manager.save_project(uri=uri, backup=False)
            app2 = common.create_pitivi_mock(default_scaled_proxy_width=12,
                                             default_scaled_proxy_height=45)
            project2 = ProjectManager(app2).load_project(uri)
            self.assertFalse(project2.has_scaled_proxy_size())
            self.assertEqual(project2.scaled_proxy_width, 12)
            self.assertEqual(project2.scaled_proxy_height, 45)

        project.scaled_proxy_width = 123
        project.scaled_proxy_height = 456
        self.assertTrue(project.has_scaled_proxy_size())
        self.assertEqual(project.scaled_proxy_width, 123)
        self.assertEqual(project.scaled_proxy_height, 456)

        with tempfile.NamedTemporaryFile() as temp_file:
            manager.save_project(uri=uri, backup=False)
            app2 = common.create_pitivi_mock(default_scaled_proxy_width=1,
                                             default_scaled_proxy_height=4)
            project2 = ProjectManager(app2).load_project(uri)
            self.assertTrue(project2.has_scaled_proxy_size())
            self.assertEqual(project2.scaled_proxy_width, 123)
            self.assertEqual(project2.scaled_proxy_height, 456)


class TestExportSettings(common.TestCase):

    def test_master_attributes(self):
        self._check_master_attribute("muxer", dependant_attr="containersettings")
        self._check_master_attribute("vencoder", dependant_attr="vcodecsettings")
        self._check_master_attribute("aencoder", dependant_attr="acodecsettings")

    def _check_master_attribute(self, attr, dependant_attr):
        """Test changing the specified attr has effect on its dependent attr."""
        project = common.create_project()

        attr_value1 = "%s_value1" % attr
        attr_value2 = "%s_value2" % attr

        setattr(project, attr, attr_value1)
        setattr(project, dependant_attr, {})
        getattr(project, dependant_attr)["key1"] = "v1"

        setattr(project, attr, attr_value2)
        setattr(project, dependant_attr, {})
        getattr(project, dependant_attr)["key2"] = "v2"

        setattr(project, attr, attr_value1)
        self.assertTrue("key1" in getattr(project, dependant_attr))
        self.assertFalse("key2" in getattr(project, dependant_attr))
        self.assertEqual("v1", getattr(project, dependant_attr)["key1"])
        setattr(project, dependant_attr, {})

        setattr(project, attr, attr_value2)
        self.assertFalse("key1" in getattr(project, dependant_attr))
        self.assertTrue("key2" in getattr(project, dependant_attr))
        self.assertEqual("v2", getattr(project, dependant_attr)["key2"])
        setattr(project, dependant_attr, {})

        setattr(project, attr, attr_value1)
        self.assertFalse("key1" in getattr(project, dependant_attr))
        self.assertFalse("key2" in getattr(project, dependant_attr))

        setattr(project, attr, attr_value2)
        self.assertFalse("key1" in getattr(project, dependant_attr))
        self.assertFalse("key2" in getattr(project, dependant_attr))

    def test_set_rendering(self):
        """Checks the set_rendering method."""
        mainloop = common.create_main_loop()

        def loaded_cb(project, timeline):
            project.add_uris([common.get_sample_uri("tears_of_steel.webm")])

        def progress_cb(project, progress, estimated_time):
            if progress == 100:
                mainloop.quit()

        # Create a blank project and add some assets.
        project = common.create_project()

        project.connect_after("loaded", loaded_cb)
        project.connect_after("asset-loading-progress", progress_cb)

        mainloop.run()

        # The video settings should match tears_of_steel.webm
        self.assertEqual(project.videowidth, 960)
        self.assertEqual(project.videoheight, 400)

        project.render_scale = 3
        # Pretend we're rendering.
        project.set_rendering(True)
        self.assertEqual(project.videowidth, 28)
        self.assertEqual(project.videoheight, 12)

        # Pretend we're not rendering anymore.
        project.set_rendering(False)
        self.assertEqual(project.videowidth, 960)
        self.assertEqual(project.videoheight, 400)

    def test_set_safe_area_sizes(self):
        """Checks to ensure that the safe areas values are set correctly."""
        project = common.create_project()
        title_horizontal_factor = 0.8
        title_vertical_factor = 0.9
        action_horizontal_factor = 0.6
        action_vertical_factor = 0.7

        project.set_safe_areas_sizes(title_horizontal_factor,
                                     title_vertical_factor,
                                     action_horizontal_factor,
                                     action_vertical_factor)

        self.assertEqual(project.title_safe_area_horizontal, title_horizontal_factor)
        self.assertEqual(project.title_safe_area_vertical, title_vertical_factor)
        self.assertEqual(project.action_safe_area_horizontal, action_horizontal_factor)
        self.assertEqual(project.action_safe_area_vertical, action_vertical_factor)
