# -*- coding: utf-8 -*-
# Pitivi video editor
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
"""Tests for the utils.misc module."""
# pylint: disable=protected-access,no-self-use
import os
from unittest import mock

from gi.repository import GdkPixbuf
from gi.repository import Gst

from pitivi.utils.misc import PathWalker
from pitivi.utils.misc import scale_pixbuf
from tests import common


class MiscMethodsTest(common.TestCase):
    """Tests methods in utils.misc module."""

    def check_pixbuf_scaling(self, pixbuf_width, pixbuf_height,
                             width, height,
                             expected_width, expected_height):
        """Checks pixbuf scaling."""
        pixbuf = mock.Mock()
        pixbuf.props.width = pixbuf_width
        pixbuf.props.height = pixbuf_height
        _ = scale_pixbuf(pixbuf, width, height)
        pixbuf.scale_simple.assert_called_once_with(expected_width, expected_height, GdkPixbuf.InterpType.BILINEAR)

    def test_scale_pixbuf(self):
        """Tests pixbuf scaling."""
        # Larger, same aspect ratio.
        self.check_pixbuf_scaling(200, 100, 20, 10, 20, 10)
        # Larger, wider aspect ratio.
        self.check_pixbuf_scaling(200, 50, 20, 10, 20, 5)
        # Larger, taller aspect ratio.
        self.check_pixbuf_scaling(100, 200, 20, 10, 5, 10)

        # Smaller.
        self.check_pixbuf_scaling(1, 1, 20, 10, 1, 1)
        self.check_pixbuf_scaling(20, 1, 20, 10, 20, 1)
        self.check_pixbuf_scaling(1, 10, 20, 10, 1, 10)


class PathWalkerTest(common.TestCase):
    """Tests for the `PathWalker` class."""

    def _scan(self, uris):
        """Uses the PathWalker to scan URIs."""
        mainloop = common.create_main_loop()
        received_uris = []

        def done_cb(uris):
            received_uris.extend(uris)
            mainloop.quit()
        walker = PathWalker(uris, done_cb)
        walker.run()
        mainloop.run()
        return received_uris

    def test_scanning(self):
        """Checks the scanning of the URIs."""
        valid_uri = common.get_sample_uri("tears_of_steel.webm")
        uris = self._scan([valid_uri,
                           common.get_sample_uri("missing.webm"),
                           "https://pitivi.org/very_real.webm"])
        self.assertEqual(len(uris), 1, uris)
        self.assertIn(valid_uri, uris)

    def test_scanning_dir(self):
        """Checks the scanning of the directory URIs."""
        assets_dir = os.path.dirname(os.path.abspath(__file__))
        valid_dir_uri = Gst.filename_to_uri(os.path.join(assets_dir, "samples"))
        uris = [valid_dir_uri]
        received_uris = self._scan(uris)
        self.assertGreater(len(received_uris), 1, received_uris)
        valid_uri = common.get_sample_uri("tears_of_steel.webm")
        self.assertIn(valid_uri, received_uris)
