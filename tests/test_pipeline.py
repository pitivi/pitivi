# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Thibault Saunier <tsaunier@gnome.org>
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
from unittest import mock

from gi.repository import GLib
from gi.repository import Gst

from pitivi.utils import pipeline
from tests import common


class MockedPipeline(pipeline.Pipeline):

    def __init__(self):
        pipeline.Pipeline.__init__(self, common.create_pitivi_mock())
        self.state_calls = {}
        self._timeline = mock.MagicMock()

    def set_state(self, state):
        self.state_calls[state] = self.state_calls.get(state, 0) + 1

    def post_fake_error_message(self):
        message = mock.Mock()
        message.type = Gst.MessageType.ERROR
        error = GLib.Error.new_literal(Gst.core_error_quark(),
                                       "fake", Gst.CoreError.TOO_LAZY)
        message.parse_error = mock.MagicMock(return_value=(error, "fake"))
        self._busMessageCb(None, message)


class TestPipeline(common.TestCase):

    def pipeline_died_cb(self, pipeline):
        self.pipeline_died = True

    def test_recovery(self):
        pipe = MockedPipeline()
        pipe.pause()

        self.pipeline_died = False
        pipe.connect("died", self.pipeline_died_cb)

        states = {Gst.State.PAUSED: 1}
        self.assertEqual(pipe.state_calls, states)
        self.assertFalse(self.pipeline_died)

        for i in range(1, pipeline.MAX_RECOVERIES + 2):
            pipe.post_fake_error_message()
            states = {Gst.State.PAUSED: i + 1, Gst.State.NULL: i}
            self.assertEqual(pipe.state_calls, states)
            self.assertEqual(pipe._attempted_recoveries, i)
            self.assertFalse(self.pipeline_died)

        states = {Gst.State.PAUSED: pipeline.MAX_RECOVERIES + 2,
                  Gst.State.NULL: pipeline.MAX_RECOVERIES + 1}

        pipe.post_fake_error_message()
        self.assertTrue(self.pipeline_died)

        states = {Gst.State.PAUSED: pipeline.MAX_RECOVERIES + 2,
                  Gst.State.NULL: pipeline.MAX_RECOVERIES + 1}
        self.assertEqual(pipe.state_calls, states)
        self.assertEqual(pipe._attempted_recoveries,
                         pipeline.MAX_RECOVERIES + 1)
