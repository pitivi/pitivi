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
import builtins
import code
import keyword
import os
import re
import sys

from gi.repository import GObject
from gi.repository import Gtk
from utils import display_autocompletion
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
        self._history = []

    def add(self, command):
        """Adds a command line to the history."""
        if command.strip():
            if self._history and command == self._history[-1]:
                return
            if self._history and not self._history[-1].strip():
                self._history.pop()
            self._history.append(command)
            self._pos = len(self._history) - 1

    def get(self):
        """Gets the command line at the current position."""
        return self._history[self._pos]

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
                return
        if self._history:
            self.emit("pos-changed")

    def down(self, current_command):
        """Sets the current command line with the next available used command line."""
        if self._pos < len(self._history) - 1:
            self._history[self._pos] = current_command
            self._pos += 1
            self.emit("pos-changed")


class ConsoleBuffer(Gtk.TextBuffer):

    AFTER_PROMPT_MARK = "after-prompt"

    def __init__(self, namespace):
        Gtk.TextBuffer.__init__(self)

        self.insert_at_cursor(sys.ps1)
        self.create_mark(self.AFTER_PROMPT_MARK, self.get_end_iter(), True)

        self.prompt = sys.ps1
        self._stdout = FakeOut(self)
        self._stderr = FakeOut(self)
        self._console = code.InteractiveConsole(namespace)

        self.history = ConsoleHistory()
        namespace["__history__"] = self.history
        self.history.connect("pos-changed", self.__history_pos_changed_cb)

        self.connect("insert-text", self.__insert_text_cb)

    def process_command_line(self):
        """Process the current input command line executing it if complete."""
        cmd = self.get_command_line()
        self.history.add(cmd)
        after_prompt_mark = self.get_mark(self.AFTER_PROMPT_MARK)

        with swap_std(self._stdout, self._stderr):
            self.write("\n")
            is_command_incomplete = self._console.push(cmd)

        if is_command_incomplete:
            self.prompt = sys.ps2
        else:
            self.prompt = sys.ps1
        self.write(self.prompt)

        self.move_mark(after_prompt_mark, self.get_end_iter())
        self.place_cursor(self.get_end_iter())

    def is_cursor_at_prompt(self):
        """Returns whether the cursor is exactly after the prompt."""
        after_prompt_iter = self.get_iter_at_mark_name(self.AFTER_PROMPT_MARK)
        cursor_iter = self.get_iter_at_mark_name("insert")
        return after_prompt_iter.compare(cursor_iter) == 0

    def is_cursor_before_prompt(self):
        """Returns whether the cursor is exactly before the last prompt."""
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

    def show_autocompletion(self, command):
        """Prints the autocompletion to the view."""
        matches, last, new_command = self.get_autocompletion_matches(command)
        namespace = {
            "last": last,
            "matches": matches,
            "buf": self,
            "command": command,
            "new_command": new_command,
            "display_autocompletion": display_autocompletion
        }
        with swap_std(self._stdout, self._stderr):
            # pylint: disable=eval-used
            eval("display_autocompletion(last, matches, buf, command, new_command)",
                 namespace, self._console.locals)
        if len(matches) > 1:
            self.__refresh_prompt(new_command)

    def get_autocompletion_matches(self, input_text):
        """
        Given an input text, return possible matches for autocompletion.
        """
        # pylint: disable=bare-except, eval-used, too-many-branches, too-many-locals
        # Try to get the possible full object to scan.
        # For example, if input_text is "func(circle.ra", we obtain "circle.ra".
        identifiers = re.findall(r"[_A-Za-z][\w\.]*\w$", input_text)
        if identifiers:
            maybe_scannable_object = identifiers[0]
        else:
            maybe_scannable_object = input_text

        pos = maybe_scannable_object.rfind(".")
        if pos != -1:
            # In this case, we cannot scan "circle.ra", so we scan "circle".
            scannable_object = maybe_scannable_object[:pos]
        else:
            # This is the case when input was more simple, like "circ".
            scannable_object = maybe_scannable_object
        namespace = {"scannable_object": scannable_object}
        try:
            if pos != -1:
                str_eval = "dir(eval(scannable_object))"
            else:
                str_eval = "dir()"
            maybe_matches = eval(str_eval, namespace, self._console.locals)
        except:
            return [], maybe_scannable_object, input_text
        if pos != -1:
            # Get substring after last dot (.)
            rest = maybe_scannable_object[(pos + 1):]
        else:
            rest = scannable_object
        # First, assume we are parsing an object.
        matches = [match for match in maybe_matches if match.startswith(rest)]

        # If not matches, maybe it is a keyword or builtin function.
        if not matches:
            tmp_matches = keyword.kwlist + dir(builtins)
            matches = [
                match for match in tmp_matches if match.startswith(rest)]

        if not matches:
            new_input_text = input_text
        else:
            maybe_scannable_pos = input_text.find(maybe_scannable_object)
            common = os.path.commonprefix(matches)
            if pos == -1:
                new_input_text = input_text[:maybe_scannable_pos] + common
            else:
                new_input_text = input_text[:maybe_scannable_pos] + maybe_scannable_object[:pos] + "." + common

        return matches, rest, new_input_text

    def __refresh_prompt(self, text=""):
        after_prompt_mark = self.get_mark(self.AFTER_PROMPT_MARK)

        # Prepare the new line
        end_iter = self.get_end_iter()
        self.insert(end_iter, self.prompt)
        end_iter = self.get_end_iter()
        self.move_mark(after_prompt_mark, end_iter)
        self.place_cursor(end_iter)
        self.write(text)

    def __insert_text_cb(self, buf, it, text, user_data):
        command = self.get_command_line()
        if text == "\t" and command.strip() != "":
            # If input text is '\t' and command doesn't start with spaces or tab
            # prevent GtkTextView to insert the text "\t" for autocompletion.
            GObject.signal_stop_emission_by_name(buf, "insert-text")
            self.show_autocompletion(command)

    def __history_pos_changed_cb(self, history):
        cmd = history.get()
        self.set_command_line(cmd)
