# pylint: disable=missing-docstring
# -*- coding: utf-8 -*-
# Pitivi Developer Console
# Copyright (c) 2017, Fabian Orccon <cfoch.fabian@gmail.com>
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
import sys
from contextlib import contextmanager
from io import TextIOBase


def get_iter_at_mark(buf, mark):
    """Gets the iterator of a GtkTextBuffer at a given mark name."""
    return buf.get_iter_at_mark(buf.get_mark(mark))


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


def display_autocompletion(last_obj, matches, text_buffer,
                           old_command, new_command):
    """Print possible matches (to FakeOut)."""
    if len(matches) == 1:
        tokens = matches[0].split(last_obj)
        if len(tokens) >= 1:
            print(tokens[1], end="")
    elif len(matches) > 1:
        if new_command.startswith(old_command):
            # Complete the rest of the command if they have a common prefix.
            rest = new_command.replace(old_command, "")
            text_buffer.insert(text_buffer.get_end_iter(), rest)
        print()
        for match in matches:
            print(match)


class FakeOut(TextIOBase):
    """Replacement for sys.stdout/err which redirects writes."""

    def __init__(self, console):
        TextIOBase.__init__(self)
        self.console = console

    def write(self, string):
        self.console.write(string)

    def writelines(self, lines):
        self.console.write(lines)

    def errors(self, error):
        self.console.write(error)
