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
import builtins
import os
import re
import sys
from code import InteractiveConsole
from keyword import kwlist

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango
from utils import display_autocompletion
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

    # pylint: disable=too-many-instance-attributes
    DEFAULT_PS1 = ">>> "
    DEFAULT_PS2 = "... "
    MARK_BEFORE_PROMPT = "before-prompt"
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
        buf.create_mark(self.MARK_BEFORE_PROMPT, buf.get_end_iter(), True)
        buf.insert_at_cursor(sys.ps1)
        buf.create_mark(self.MARK_AFTER_PROMPT, buf.get_end_iter(), True)

        self.prompt = sys.ps1
        self.normal = buf.create_tag("normal")
        self.error = buf.create_tag("error")
        self.command = buf.create_tag("command")
        self._stdout = FakeOut(self, self.normal, sys.stdout.fileno())
        self._stderr = FakeOut(self, self.error, sys.stdout.fileno())

        self._console = InteractiveConsole(namespace)
        self._history = ConsoleHistory(self)
        namespace["__history__"] = self._history

        # Signals
        self._view.connect("key-press-event", self.__key_press_event_cb)
        buf.connect("mark-set", self.__mark_set_cb)
        buf.connect("insert-text", self.__insert_text_cb)

        # Font color and style.
        self._provider = Gtk.CssProvider()
        self._css_values = {
            "textview": {
                "font-family": None,
                "font-size": None,
                "font-style": None,
                "font-variant": None,
                "font-weight": None
            },
            "textview > *": {
                "color": None
            }
        }

    def get_command_line(self):
        """Gets the last command line after the prompt.

        A command line can be a single line or many lines for example when
        a function or a class is defined.
        """
        buf = self._view.get_buffer()
        after_prompt_iter = get_iter_at_mark(buf, self.MARK_AFTER_PROMPT)
        end_iter = buf.get_end_iter()
        return buf.get_text(after_prompt_iter, end_iter, False)

    def scroll_to_end(self):
        """Scrolls the view to the end."""
        end_iter = self._view.get_buffer().get_end_iter()
        self._view.scroll_to_iter(end_iter, 0.0, False, 0.5, 0.5)
        return False

    def set_font(self, font_desc):
        """Sets the font.

        Args:
            font (str): a PangoFontDescription as a string.
        """
        pango_font_desc = Pango.FontDescription.from_string(font_desc)
        self._css_values["textview"]["font-family"] = pango_font_desc.get_family()
        self._css_values["textview"]["font-size"] = "%dpt" % int(pango_font_desc.get_size() / Pango.SCALE)
        self._css_values["textview"]["font-style"] = pango_font_desc.get_style().value_nick
        self._css_values["textview"]["font-variant"] = pango_font_desc.get_variant().value_nick
        self._css_values["textview"]["font-weight"] = int(pango_font_desc.get_weight())
        self._apply_css()
        self.error.set_property("font", font_desc)
        self.command.set_property("font", font_desc)
        self.normal.set_property("font", font_desc)

    def set_color(self, color):
        """Sets the color.

        Args:
            color (Gdk.RGBA): a color.
        """
        self._css_values["textview > *"]["color"] = color.to_string()
        self._apply_css()

    def _apply_css(self):
        css = ""
        for css_klass, props in self._css_values.items():
            css += "%s {" % css_klass
            for prop, value in props.items():
                if value is not None:
                    css += "%s: %s;" % (prop, value)
            css += "} "
        css = css.encode("UTF-8")
        self._provider.load_from_data(css)
        Gtk.StyleContext.add_provider(self._view.get_style_context(),
                                      self._provider,
                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def set_command_line(self, cmd):
        """Inserts a command line after the prompt."""
        buf = self._view.get_buffer()
        after_prompt_iter = get_iter_at_mark(buf, self.MARK_AFTER_PROMPT)
        end_iter = buf.get_end_iter()
        buf.delete(after_prompt_iter, end_iter)
        buf.insert(buf.get_end_iter(), cmd)

    def write(self, text, tag=None):
        """Writes a text to the text view's buffer."""
        buf = self._view.get_buffer()
        if tag is None:
            buf.insert(buf.get_end_iter(), text)
        else:
            buf.insert_with_tags(buf.get_end_iter(), text, tag)
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

    def show_autocompletion(self, command):
        """Prints the autocompletion to the view."""
        matches, last, new_command = self.get_autocompletion_matches(command)
        namespace = {
            "last": last,
            "matches": matches,
            "buf": self._view.get_buffer(),
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
        # pylint: disable=bare-except, eval-used, too-many-branches
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
            tmp_matches = kwlist + dir(builtins)
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
        buf = self._view.get_buffer()

        after_prompt_mark = buf.get_mark(self.MARK_AFTER_PROMPT)

        # Prepare the new line
        end_iter = buf.get_end_iter()
        buf.insert(end_iter, self.prompt)
        end_iter = buf.get_end_iter()
        buf.move_mark(after_prompt_mark, end_iter)
        buf.place_cursor(end_iter)
        self.write(text)

        GLib.idle_add(self.scroll_to_end)
        return True

    def __mark_set_cb(self, buf, it, name):
        after_prompt_iter =\
            buf.get_iter_at_mark(buf.get_mark(self.MARK_AFTER_PROMPT))
        pos_iter = buf.get_iter_at_mark(buf.get_insert())
        self._view.set_editable(pos_iter.compare(after_prompt_iter) != -1)

    def __insert_text_cb(self, buf, it, text, user_data):
        command = self.get_command_line()
        if text == "\t" and not command.isspace():
            # If input text is '\t' and command doesn't start with spaces or tab
            # prevent GtkTextView to insert the text "\t" for autocompletion.
            GObject.signal_stop_emission_by_name(buf, "insert-text")
            self.show_autocompletion(command)

    def _process_command_line(self, cmd):
        buf = self._view.get_buffer()
        before_prompt_mark = buf.get_mark(self.MARK_BEFORE_PROMPT)
        after_prompt_mark = buf.get_mark(self.MARK_AFTER_PROMPT)

        self._history.add(cmd)

        before_prompt_iter = get_iter_at_mark(buf, self.MARK_BEFORE_PROMPT)
        buf.apply_tag(self.command, before_prompt_iter, buf.get_end_iter())

        with swap_std(self._stdout, self._stderr):
            print()
            is_command_incomplete = self._console.push(cmd)

        if is_command_incomplete:
            self.prompt = sys.ps2
        else:
            self.prompt = sys.ps1

        buf.move_mark(before_prompt_mark, buf.get_end_iter())
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
