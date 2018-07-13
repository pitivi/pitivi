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
"""The developer console widget:"""
import sys
from code import InteractiveConsole

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from utils import FakeOut
from utils import get_iter_at_mark
from utils import swap_std


class ConsoleHistory:
    """Represents a console commands history."""

    def __init__(self, console):
        self.console = console
        self._history = []
        self._pos = 0

    def add(self, command):
        """Adds a command line to the history."""
        if command.strip():
            if self._history and command == self._history[-1]:
                return
            if self._history and not self._history[-1].strip():
                self._history.pop()
            self._history.append(command)
            self._pos = len(self._history) - 1

    # pylint: disable=invalid-name
    def up(self, current_command):
        """Sets the current command line with the previous used command line."""
        if self._pos > 0:
            if self._pos < len(self._history) - 1:
                self._history[self._pos] = current_command
                self._pos -= 1
            elif self._pos == len(self._history) - 1:
                if self._history[-1] != current_command:
                    self._history.append(current_command)
                else:
                    self._pos -= 1
            else:
                return True
        if self._history:
            self.console.set_command_line(self._history[self._pos])
            GLib.idle_add(self.console.scroll_to_end)
        return True

    def down(self, current_command):
        """Sets the current command line with the next available used command line."""
        if self._pos < len(self._history) - 1:
            self._history[self._pos] = current_command
            self._pos += 1
            self.console.set_command_line(self._history[self._pos])
            GLib.idle_add(self.console.scroll_to_end)
        return True


class ConsoleWidget(Gtk.ScrolledWindow):
    """An emulated Python console.
    The console can be used to access an app, window, or anything through the
    provided namespace. It works redirecting stdout and stderr to a
    GtkTextBuffer. This class is (and should be) independent of the application
    it is integrated with.
    """

    DEFAULT_PS1 = ">>> "
    DEFAULT_PS2 = "... "
    MARK_AFTER_PROMPT = "after-prompt"

    def __init__(self, namespace):
        Gtk.ScrolledWindow.__init__(self)
        self._view = Gtk.TextView()
        self._view.set_editable(True)
        self.add(self._view)

        # Set prompt.
        sys.ps1 = self.DEFAULT_PS1
        sys.ps2 = self.DEFAULT_PS2
        buf = self._view.get_buffer()
        buf.insert_at_cursor(sys.ps1)
        buf.create_mark(self.MARK_AFTER_PROMPT, buf.get_end_iter(), True)

        self.prompt = sys.ps1
        self._stdout = FakeOut(self)
        self._stderr = FakeOut(self)

        self._console = InteractiveConsole(namespace)
        self._history = ConsoleHistory(self)
        namespace["__history__"] = self._history

        # Signals
        self._view.connect("key-press-event", self.__key_press_event_cb)
        buf.connect("mark-set", self.__mark_set_cb)

    def scroll_to_end(self):
        """Scrolls the view to the end."""
        end_iter = self._view.get_buffer().get_end_iter()
        self._view.scroll_to_iter(end_iter, 0.0, False, 0.5, 0.5)
        return False

    def get_command_line(self):
        """Gets the last command line after the prompt.

        A command line can be a single line or many lines for example when
        a function or a class is defined.
        """
        buf = self._view.get_buffer()
        after_prompt_iter = get_iter_at_mark(buf, self.MARK_AFTER_PROMPT)
        end_iter = buf.get_end_iter()
        return buf.get_text(after_prompt_iter, end_iter, False)

    def set_command_line(self, cmd):
        """Inserts a command line after the prompt."""
        buf = self._view.get_buffer()
        after_prompt_iter = get_iter_at_mark(buf, self.MARK_AFTER_PROMPT)
        end_iter = buf.get_end_iter()
        buf.delete(after_prompt_iter, end_iter)
        buf.insert(buf.get_end_iter(), cmd)

    def write(self, text):
        """Writes a text to the text view's buffer."""
        buf = self._view.get_buffer()
        buf.insert(buf.get_end_iter(), text)
        GLib.idle_add(self.scroll_to_end)

    def __key_press_event_cb(self, view, event):
        cmd = self.get_command_line()
        if event.keyval == Gdk.KEY_Return:
            return self._process_command_line(cmd)
        elif event.keyval in (Gdk.KEY_KP_Down, Gdk.KEY_Down):
            return self._history.down(cmd)
        elif event.keyval in (Gdk.KEY_KP_Up, Gdk.KEY_Up):
            return self._history.up(cmd)
        elif event.keyval in (Gdk.KEY_KP_Left, Gdk.KEY_Left, Gdk.KEY_BackSpace):
            return self.__is_cursor_at_start()
        return False

    def _process_command_line(self, cmd):
        buf = self._view.get_buffer()
        after_prompt_mark = buf.get_mark(self.MARK_AFTER_PROMPT)

        self._history.add(cmd)

        with swap_std(self._stdout, self._stderr):
            print()
            is_command_incomplete = self._console.push(cmd)

        if is_command_incomplete:
            self.prompt = sys.ps2
        else:
            self.prompt = sys.ps1

        buf.insert(buf.get_end_iter(), self.prompt)
        buf.move_mark(after_prompt_mark, buf.get_end_iter())
        buf.place_cursor(get_iter_at_mark(buf, self.MARK_AFTER_PROMPT))
        return True

    def __is_cursor_at_start(self):
        """Returns whether the cursor is exactly after the prompt."""
        buf = self._view.get_buffer()
        after_prompt_iter =\
            get_iter_at_mark(buf, self.MARK_AFTER_PROMPT)
        cursor_iter = get_iter_at_mark(buf, "insert")
        return after_prompt_iter.compare(cursor_iter) == 0

    def __mark_set_cb(self, buf, it, name):
        buf = self._view.get_buffer()
        after_prompt_iter = get_iter_at_mark(buf, self.MARK_AFTER_PROMPT)
        pos_iter = get_iter_at_mark(buf, "insert")
        self._view.set_editable(pos_iter.compare(after_prompt_iter) != -1)
