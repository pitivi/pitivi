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
from contextlib import contextmanager
from io import TextIOBase

from gi.repository import Gtk


@contextmanager
def swap_std(stdout=None, stderr=None):
    """Swaps temporarily stdout and stderr with the respective arguments."""
    try:
        if stdout:
            sys.stdout, stdout = stdout, sys.stdout
        if stderr:
            sys.stderr, stderr = stderr, sys.stderr
        yield
    finally:
        if stdout:
            sys.stdout = stdout
        if stderr:
            sys.stderr = stderr


class FakeOut(TextIOBase):
    """Replacement for sys.stdout/err which redirects writes."""

    def __init__(self, buf):
        TextIOBase.__init__(self)
        self.buf = buf

    def write(self, string):
        self.buf.write(string)

    def writelines(self, lines):
        self.buf.write(lines)


class ConsoleBuffer(Gtk.TextBuffer):

    AFTER_PROMPT_MARK = "after-prompt"

    def __init__(self, namespace):
        Gtk.TextBuffer.__init__(self)

        self.insert_at_cursor(sys.ps1)
        self.create_mark(self.AFTER_PROMPT_MARK, self.get_end_iter(), True)

        self._stdout = FakeOut(self)
        self._stderr = FakeOut(self)
        self._console = code.InteractiveConsole(namespace)

    def process_command_line(self):
        """Process the current input command line executing it if complete."""
        cmd = self.get_command_line()
        after_prompt_mark = self.get_mark(self.AFTER_PROMPT_MARK)

        with swap_std(self._stdout, self._stderr):
            print()
            is_command_incomplete = self._console.push(cmd)

        if is_command_incomplete:
            prompt = sys.ps2
        else:
            prompt = sys.ps1

        self.insert(self.get_end_iter(), prompt)
        self.move_mark(after_prompt_mark, self.get_end_iter())
        self.place_cursor(self.get_end_iter())

    def is_cursor_at_start(self):
        """Returns whether the cursor is exactly after the prompt."""
        after_prompt_iter = self.get_iter_at_mark_name(self.AFTER_PROMPT_MARK)
        cursor_iter = self.get_iter_at_mark_name("insert")
        return after_prompt_iter.compare(cursor_iter) == 0

    def is_cursor_before_last_prompt(self):
        """Returns whether the cursor is exactly before the last prompt"""
        after_prompt_iter = self.get_iter_at_mark_name(ConsoleBuffer.AFTER_PROMPT_MARK)
        pos_iter = self.get_iter_at_mark_name("insert")
        return pos_iter.compare(after_prompt_iter) != -1

    def write(self, text):
        """Writes a text to the buffer."""
        self.insert(self.get_end_iter(), text)

    def get_iter_at_mark_name(self, mark_name):
        """Gets an iterator with the position of the specified mark."""
        return self.get_iter_at_mark(self.get_mark(mark_name))

    def get_command_line(self):
        """Gets the last command line after the prompt.

        A command line can be a single line or multiple lines for example when
        a function or a class is defined.
        """
        after_prompt_iter = self.get_iter_at_mark_name(self.AFTER_PROMPT_MARK)
        end_iter = self.get_end_iter()
        return self.get_text(after_prompt_iter, end_iter, False)

    def set_command_line(self, cmd):
        """Inserts a command line after the prompt."""
        after_prompt_iter = self.get_iter_at_mark_name(self.AFTER_PROMPT_MARK)
        end_iter = self.get_end_iter()
        self.delete(after_prompt_iter, end_iter)
        self.insert(self.get_end_iter(), cmd)
