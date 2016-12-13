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
"""Tests for the utils.pipeline module."""
# pylint: disable=protected-access,no-self-use
from unittest import mock

from gi.repository import GES
from gi.repository import GLib
from gi.repository import Gst

from pitivi.utils.pipeline import MAX_RECOVERIES
from pitivi.utils.pipeline import Pipeline
from tests import common


class TestPipeline(common.TestCase):
    """Tests for the Pipeline class."""

    @staticmethod
    def post_fake_error_message(pipeline):
        """Simulates an error message on the specified Pipeline."""
        message = mock.Mock()
        message.type = Gst.MessageType.ERROR
        error = GLib.Error.new_literal(Gst.core_error_quark(),
                                       "fake", Gst.CoreError.TOO_LAZY)
        message.parse_error = mock.MagicMock(return_value=(error, "fake"))
        pipeline._busMessageCb(None, message)

    def test_recovery(self):
        """Checks the recovery mechanism."""
        pipe = Pipeline(common.create_pitivi_mock())
        pipe.set_timeline(GES.Timeline())

        pipeline_died_cb = mock.Mock()
        pipe.connect("died", pipeline_died_cb)

        with mock.patch.object(pipe, "set_state") as set_state:
            pipe.pause()
            set_state.assert_called_once_with(Gst.State.PAUSED)
        self.assertEqual(pipe._attempted_recoveries, 0)
        self.assertFalse(pipeline_died_cb.called)

        for i in range(MAX_RECOVERIES):
            with mock.patch.object(pipe, "set_state") as set_state:
                set_state.return_value = Gst.StateChangeReturn.SUCCESS
                self.post_fake_error_message(pipe)
                set_state.assert_has_calls([mock.call(Gst.State.NULL),
                                            mock.call(Gst.State.PAUSED)])
                self.assertEqual(set_state.call_count, 2)
            self.assertEqual(pipe._attempted_recoveries, i + 1)
            self.assertFalse(pipeline_died_cb.called)

        with mock.patch.object(pipe, "set_state") as set_state:
            self.post_fake_error_message(pipe)
            set_state.assert_not_called()
        self.assertTrue(pipeline_died_cb.called)
        self.assertEqual(pipe._attempted_recoveries, MAX_RECOVERIES)
