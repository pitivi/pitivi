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
import os
import tempfile
from unittest import mock
from unittest import TestCase

import numpy
from gi.repository import GES
from gi.repository import Gst

from pitivi.timeline.previewers import get_wavefile_location_for_uri
from pitivi.timeline.previewers import THUMB_HEIGHT
from pitivi.timeline.previewers import ThumbnailCache
from tests import common
from tests.test_media_library import BaseTestMediaLibrary


SIMPSON_WAVFORM_VALUES = [
    0.111346248025012, 0.53654970100915411, 0.96175315399329631, 1.3869566069774386,
    1.8121600599615806, 2.237363512945723, 2.662566965929865, 3.0877704189140069,
    3.5129738718981489, 3.9381773248822909, 3.9381773248822909, 3.8973170554102357,
    3.8564567859381809, 3.8155965164661261, 3.7747362469940708, 3.7338759775220156,
    3.6930157080499608, 3.652155438577906, 3.6112951691058508, 3.5704348996337956,
    3.5704348996337956, 3.7087058267020998, 3.846976753770404, 3.9852476808387078,
    4.1235186079070116, 4.2617895349753159, 4.4000604620436201, 4.5383313891119244,
    4.6766023161802277, 4.8148732432485319, 4.8148732432485319, 4.7940769006009409,
    4.7732805579533499, 4.7524842153057598, 4.7316878726581688, 4.7108915300105778,
    4.6900951873629868, 4.6692988447153958, 4.6485025020678057, 4.6277061594202147,
    4.6277061594202138, 4.6929619636223059, 4.7582177678243989, 4.8234735720264919,
    4.8887293762285848, 4.9539851804306778, 5.0192409846327699, 5.0844967888348629,
    5.1497525930369559, 5.215008397239048, 5.2150083972390462, 5.1875374713467179,
    5.1600665454543897, 5.1325956195620606, 5.1051246936697314, 5.0776537677774032,
    5.0501828418850749, 5.0227119159927458, 4.9952409901004167, 4.9677700642080884,
    4.9677700642080893, 4.9202183773912216, 4.8726666905743539, 4.8251150037574861,
    4.7775633169406184, 4.7300116301237507, 4.682459943306883, 4.6349082564900153,
    4.5873565696731475, 4.5398048828562798, 4.5398048828562807, 4.6475893807495776,
    4.7553738786428745, 4.8631583765361706, 4.9709428744294666, 5.0787273723227635,
    5.1865118702160604, 5.2942963681093564, 5.4020808660026525, 5.5098653638959494,
    5.5098653638959485, 5.4723412189420966, 5.4348170739882438, 5.397292929034391,
    5.359768784080539, 5.3222446391266871, 5.2847204941728343, 5.2471963492189815,
    5.2096722042651296, 5.1721480593112776, 5.1721480593112776, 5.1391459925110219,
    5.106143925710767, 5.0731418589105122, 5.0401397921102564, 5.0071377253100007,
    4.9741356585097458, 4.941133591709491, 4.9081315249092352, 4.8751294581089795,
    4.8751294581089812, 4.7707539946969515, 4.66637853128492, 4.5620030678728902,
    4.4576276044608587, 4.353252141048829, 4.2488766776367974, 4.1445012142247668,
    4.0401257508127362, 3.9357502874007055, 3.9357502874007029, 3.9029687270533486,
    3.8701871667059953, 3.837405606358641, 3.8046240460112877, 3.7718424856639334,
    3.7390609253165801, 3.7062793649692258, 3.6734978046218725, 3.6407162442745182,
    3.6407162442745191, 0.0]


class TestPreviewers(BaseTestMediaLibrary):

    def testCreateThumbnailBin(self):
        pipeline = Gst.parse_launch("uridecodebin name=decode uri=file:///some/thing"
                                    " waveformbin name=wavebin ! fakesink qos=false name=faked")
        self.assertTrue(pipeline)
        wavebin = pipeline.get_by_name("wavebin")
        self.assertTrue(wavebin)

    def testWaveFormAndThumbnailCreated(self):
        sample_name = "1sec_simpsons_trailer.mp4"
        self.runCheckImport([sample_name])

        sample_uri = common.get_sample_uri(sample_name)
        asset = GES.UriClipAsset.request_sync(sample_uri)

        thumb_cache = ThumbnailCache.get(asset)
        width, height = thumb_cache.getImagesSize()
        self.assertEqual(height, THUMB_HEIGHT)
        self.assertTrue(thumb_cache[0] is not None)
        self.assertTrue(thumb_cache[Gst.SECOND / 2] is not None)

        wavefile = get_wavefile_location_for_uri(sample_uri)
        self.assertTrue(os.path.exists(wavefile), wavefile)

        with open(wavefile, "rb") as fsamples:
            samples = list(numpy.load(fsamples))

        self.assertEqual(samples, SIMPSON_WAVFORM_VALUES)


class TestThumbnailCache(TestCase):

    def test_get(self):
        with self.assertRaises(ValueError):
            ThumbnailCache.get(1)
        with mock.patch("pitivi.timeline.previewers.xdg_cache_home") as xdg_config_home,\
                tempfile.TemporaryDirectory() as temp_dir:
            xdg_config_home.return_value = temp_dir
            sample_uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")
            cache = ThumbnailCache.get(sample_uri)
            self.assertIsNotNone(cache)

            asset = GES.UriClipAsset.request_sync(sample_uri)
            self.assertEqual(ThumbnailCache.get(asset), cache)
