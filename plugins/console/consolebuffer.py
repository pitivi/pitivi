# pylint: disable=missing-docstring
# -*- coding: utf-8 -*-
# Pitivi Developer Console
# Copyright (c) 2017-2018, Fabian Orccon <cfoch.fabian@gmail.com>
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
import code
import sys

from gi.repository import GObject
from gi.repository import Gtk
from utils import FakeOut
from utils import swap_std


class ConsoleHistory(GObject.Object):
    """Represents a console commands history."""

    __gsignals__ = {
        "pos-changed": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self._pos = 0
        self._history = [""]

    def add(self, cmd):
        """Adds a command line to the history."""
        if not cmd.strip():
            return

        if len(self._history) > 1 and cmd == self._history[-2]:
            return

        self._history[-1] = cmd
        self._history.append("")
        self._pos = len(self._history) - 1

    def get(self):
        """Gets the command line at the current position."""
        return self._history[self._pos]

    # pylint: disable=invalid-name
    def up(self, cmd):
        """Sets the current command line with the previous used command line."""
        if self._pos > 0:
            self._history[self._pos] = cmd
            self._pos -= 1
            self.emit("pos-changed")

    def down(self, cmd):
        """Sets the current command line with the next available used command line."""
        if self._pos < len(self._history) - 1:
            self._history[self._pos] = cmd
            self._pos += 1
            self.emit("pos-changed")


class ConsoleBuffer(Gtk.TextBuffer):

    def __init__(self, namespace):
        Gtk.TextBuffer.__init__(self)

        self.insert_at_cursor(sys.ps1)
        self.prompt_mark = self.create_mark("after-prompt", self.get_end_iter(), left_gravity=True)

        self._stdout = FakeOut(self)
        self._stderr = FakeOut(self)
        self._console = code.InteractiveConsole(namespace)

        self.history = ConsoleHistory()
        namespace["__history__"] = self.history
        self.history.connect("pos-changed", self.__history_pos_changed_cb)

    def process_command_line(self):
        """Process the current input command line executing it if complete."""
        cmd = self.get_command_line()
        self.history.add(cmd)

        with swap_std(self._stdout, self._stderr):
            self.write("\n")
            is_command_incomplete = self._console.push(cmd)

        if is_command_incomplete:
            prompt = sys.ps2
        else:
            prompt = sys.ps1
        self.write(prompt)

        self.move_mark(self.prompt_mark, self.get_end_iter())
        self.place_cursor(self.get_end_iter())

    def is_cursor(self, before=False, at=False, after=False):
        """Compares the position of the cursor compared to the prompt."""
        prompt_iter = self.get_iter_at_mark(self.prompt_mark)
        cursor_iter = self.get_iter_at_mark(self.get_insert())
        res = cursor_iter.compare(prompt_iter)
        return (before and res == -1) or (at and res == 0) or (after and res == 1)

    def write(self, text):
        """Writes a text to the buffer."""
        self.insert(self.get_end_iter(), text)

    def get_command_line(self):
        """Gets the last command line after the prompt.

        A command line can be a single line or multiple lines for example when
        a function or a class is defined.
        """
        after_prompt_iter = self.get_iter_at_mark(self.prompt_mark)
        end_iter = self.get_end_iter()
        return self.get_text(after_prompt_iter, end_iter, include_hidden_chars=False)

    def set_command_line(self, cmd):
        """Inserts a command line after the prompt."""
        after_prompt_iter = self.get_iter_at_mark(self.prompt_mark)
        end_iter = self.get_end_iter()
        self.delete(after_prompt_iter, end_iter)
        self.write(cmd)

    def __history_pos_changed_cb(self, history):
        cmd = history.get()
        self.set_command_line(cmd)
