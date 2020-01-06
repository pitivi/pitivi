# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the transitions module."""
from pitivi.transitions import TransitionsListWidget
from tests import common


class TransitionsListWidgetTest(common.TestCase):
    """Tests for the TransitionsListWidget class."""

    def test_transition_types_loaded(self):
        """Checks the transition types are properly detected."""
        app = common.create_pitivi_mock()
        widget = TransitionsListWidget(app)
        mainloop = common.create_main_loop()
        mainloop.run(until_empty=True)
        self.assertGreater(len(widget.storemodel), 10)
