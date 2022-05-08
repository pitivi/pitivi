# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Michael Westburg <michael.westberg@huskers.unl.edu>
# Copyright (c) 2020, Matt Lowe <mattlowe13@huskers.unl.edu>
# Copyright (c) 2020, Aaron Byington <aabyington4@gmail.com>
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
"""Tests for the pitivi.peakmeter module."""
from gi.repository import GLib

from pitivi.project import ProjectManager
from pitivi.viewer.peak_meter import MIN_PEAK
from pitivi.viewer.viewer import ViewerContainer
from tests import common


class TestPeakMeter(common.TestCase):
    """Tests for the peak meter."""

    def test_peak_meter_update(self):
        """Checks that the peak value updates correctly when audio is played."""
        app = common.create_pitivi_mock()
        app.project_manager = ProjectManager(app)

        viewer = ViewerContainer(app)
        self.assertListEqual(viewer.peak_meters, [])

        uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")
        xges = r"""<ges version='0.7'>
  <project properties='properties;' metadatas='metadatas, author=(string)Author, scaled_proxy_width=(int)0, scaled_proxy_height=(int)0, render-scale=(double)100, format-version=(string)0.7;'>
    <encoding-profiles>
      <encoding-profile name='pitivi-profile' description='Pitivi encoding profile' type='container' preset-name='webmmux' format='video/webm' >
        <stream-profile parent='pitivi-profile' id='0' type='video' presence='0' format='video/x-vp8, profile=(string){ 0, 1, 2, 3 }' preset-name='vp8enc' restriction='video/x-raw, width=(int)1080, height=(int)1920, framerate=(fraction)30/1, pixel-aspect-ratio=(fraction)1/1' pass='0' variableframerate='0' />
        <stream-profile parent='pitivi-profile' id='1' type='audio' presence='0' format='audio/x-vorbis, rate=(int)[ 1, 200000 ], channels=(int)[ 1, 255 ]' preset-name='vorbisenc' restriction='audio/x-raw, rate=(int)48000, channels=(int)2' />
      </encoding-profile>
    </encoding-profiles>
    <ressources>
      <asset id='%(uri)s' extractable-type-name='GESUriClip' properties='properties, supported-formats=(int)6, duration=(guint64)1228000000;' metadatas='metadatas, video-codec=(string)&quot;H.264\ /\ AVC&quot;, bitrate=(uint)1370124, datetime=(datetime)2007-02-19T05:03:04Z, encoder=(string)Lavf54.6.100, container-format=(string)&quot;ISO\ MP4/M4A&quot;, audio-codec=(string)&quot;MPEG-4\ AAC\ audio&quot;, maximum-bitrate=(uint)130625, file-size=(guint64)232417;' >
        <stream-info id='11c5d3bc5140b4cd95fc0c2b7125dff3b9c6db88183a85200821b61365719f91/002' extractable-type-name='GESAudioUriSource' properties='properties, track-type=(int)2;' metadatas='metadatas;' caps='audio/mpeg, mpegversion=(int)4, framed=(boolean)true, stream-format=(string)raw, level=(string)2, base-profile=(string)lc, profile=(string)lc, codec_data=(buffer)1190, rate=(int)48000, channels=(int)2'/>
        <stream-info id='11c5d3bc5140b4cd95fc0c2b7125dff3b9c6db88183a85200821b61365719f91/001' extractable-type-name='GESVideoUriSource' properties='properties, track-type=(int)4;' metadatas='metadatas;' caps='video/x-h264, stream-format=(string)avc, alignment=(string)au, level=(string)3.1, profile=(string)high, codec_data=(buffer)0164001fffe100176764001facd94050045a1000003e90000bb800f183196001000668ebe3cb22c0, width=(int)1280, height=(int)544, framerate=(fraction)24000/1001, pixel-aspect-ratio=(fraction)1/1, interlace-mode=(string)progressive, chroma-format=(string)4:2:0, bit-depth-luma=(uint)8, bit-depth-chroma=(uint)8, parsed=(boolean)true'/>
      </asset>
      <asset id='crossfade' extractable-type-name='GESTransitionClip' properties='properties, supported-formats=(int)6;' metadatas='metadatas, description=(string)GES_VIDEO_STANDARD_TRANSITION_TYPE_CROSSFADE;' >
      </asset>
    </ressources>
    <timeline properties='properties, auto-transition=(boolean)true, snapping-distance=(guint64)6420600;' metadatas='metadatas, markers=(GESMarkerList)&quot;EMPTY&quot;, duration=(guint64)2456000000;'>
      <track caps='video/x-raw(ANY)' track-type='4' track-id='0' properties='properties, message-forward=(boolean)true, restriction-caps=(string)&quot;video/x-raw\,\ width\=\(int\)1080\,\ height\=\(int\)1920\,\ framerate\=\(fraction\)30/1\,\ pixel-aspect-ratio\=\(fraction\)1/1&quot;, id=(string)87987a781a347bd399437dc56c9c6cd7;' metadatas='metadatas;'/>
      <track caps='audio/x-raw(ANY)' track-type='2' track-id='1' properties='properties, message-forward=(boolean)true, restriction-caps=(string)&quot;audio/x-raw\,\ rate\=\(int\)48000\,\ channels\=\(int\)2&quot;, id=(string)866a7d96e4e467e9f07ac713d07551de;' metadatas='metadatas;'/>
      <layer priority='0' properties='properties, auto-transition=(boolean)true;' metadatas='metadatas, volume=(float)1;'>
        <clip id='0' asset-id='%(uri)s' type-name='GESUriClip' layer-priority='0' track-types='6' start='0' duration='1228000000' inpoint='0' rate='0' properties='properties, name=(string)uriclip1;' metadatas='metadatas;'>
          <source track-id='1' properties='properties, track-type=(int)2, has-internal-source=(boolean)true;'  children-properties='properties, GstVolume::mute=(boolean)false, GstVolume::volume=(double)1;'>
            <binding type='direct' source_type='interpolation' property='volume' mode='1' track_id='1' values =' 0:0.10000000000000001  1228000000:0.10000000000000001 '/>
          </source>
          <source track-id='0' properties='properties, track-type=(int)4, has-internal-source=(boolean)true;'  children-properties='properties, GstFramePositioner::alpha=(double)1, GstDeinterlace::fields=(int)0, GstFramePositioner::height=(int)459, GstDeinterlace::mode=(int)0, GstFramePositioner::posx=(int)0, GstFramePositioner::posy=(int)730, GstDeinterlace::tff=(int)0, GstVideoDirection::video-direction=(int)8, GstFramePositioner::width=(int)1080;'>
            <binding type='direct' source_type='interpolation' property='alpha' mode='1' track_id='0' values =' 0:1  1228000000:1 '/>
          </source>
        </clip>
        <clip id='1' asset-id='%(uri)s' type-name='GESUriClip' layer-priority='0' track-types='6' start='1228000000' duration='1228000000' inpoint='0' rate='0' properties='properties, name=(string)uriclip2;' metadatas='metadatas;'>
          <source track-id='1' properties='properties, track-type=(int)2, has-internal-source=(boolean)true;'  children-properties='properties, GstVolume::mute=(boolean)false, GstVolume::volume=(double)1;'>
            <binding type='direct' source_type='interpolation' property='volume' mode='1' track_id='1' values =' 0:0.10000000000000001  1228000000:0.10000000000000001 '/>
          </source>
          <source track-id='0' properties='properties, track-type=(int)4, has-internal-source=(boolean)true;'  children-properties='properties, GstFramePositioner::alpha=(double)1, GstDeinterlace::fields=(int)0, GstFramePositioner::height=(int)459, GstDeinterlace::mode=(int)0, GstFramePositioner::posx=(int)0, GstFramePositioner::posy=(int)730, GstDeinterlace::tff=(int)0, GstVideoDirection::video-direction=(int)8, GstFramePositioner::width=(int)1080;'>
            <binding type='direct' source_type='interpolation' property='alpha' mode='1' track_id='0' values =' 0:1  1228000000:1 '/>
          </source>
        </clip>
      </layer>
      <groups>
      </groups>
    </timeline>
  </project>
</ges>""" % {"uri": uri}

        proj_uri = self.create_project_file_from_xges(xges)
        project = app.project_manager.load_project(proj_uri)
        # Before the project finished loading it has one audio channel.
        self.assertEqual(project.audiochannels, 1)

        mainloop = common.create_main_loop()

        def project_loaded_cb(project, timeline):
            mainloop.quit()

        project.connect_after("loaded", project_loaded_cb)
        mainloop.run()
        # After the project finishes loading it has the correct number of
        # audio channels.
        self.assertEqual(project.audiochannels, 2)

        self.assertEqual(len(viewer.peak_meters), 0)
        viewer.set_project(project)
        # After setting the project we should have two peak meters.
        self.assertEqual([meter.peak for meter in viewer.peak_meters], [MIN_PEAK, MIN_PEAK])

        # Check that after starting playback we get "peak" values on the bus.
        def bus_message_cb(bus, message):
            if message.get_structure().get_value("peak") is not None:
                mainloop.quit()

        def begin_playback():
            project.pipeline.play()
            project.pipeline.get_bus().connect("message::element", bus_message_cb)

        GLib.idle_add(begin_playback)
        mainloop.run()

        peaks = [meter.peak for meter in viewer.peak_meters]
        for peak in peaks:
            self.assertGreaterEqual(0, peak, peaks)
            self.assertGreaterEqual(peak, MIN_PEAK, peaks)

    @common.setup_project(["tears_of_steel.webm"])
    def test_peak_meter_channels_update(self):
        """Checks that the peak meter channels updates correctly when audio channels changes."""
        viewer = ViewerContainer(self.app)
        viewer.set_project(self.project)

        self.assertEqual(self.project.audiochannels, 1)
        self.assertEqual(len(viewer.peak_meters), 1)

        self.project.audiochannels = 6
        self.assertEqual(len(viewer.peak_meters), 6)
