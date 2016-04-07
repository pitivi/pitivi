# -*- coding: utf-8 -*-
#
#       tests/test_undo_project.py
#
# Copyright (c) 2016, Alex Băluț <alexandru.balut@gmail.com>
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
from unittest import TestCase

from pitivi.application import Pitivi
from tests import common


class TestProjectUndo(TestCase):

    def setUp(self):
        app = Pitivi()
        app._startupCb(app)
        self.assertTrue(app.project_manager.newBlankProject())

        self.project = app.project_manager.current_project
        self.action_log = app.action_log

    def test_new_project_has_nothing_to_undo(self):
        mainloop = common.create_main_loop()

        def loaded_cb(project, timeline):
            mainloop.quit()

        self.project.connect_after("loaded", loaded_cb)

        mainloop.run()

        self.assertFalse(self.action_log.is_in_transaction())
        self.assertFalse(self.action_log.undo_stacks)

