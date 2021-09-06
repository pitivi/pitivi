# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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
import collections.abc
import errno
import fnmatch
import os
import re
import sys
import threading
import time
import traceback
import types


# environment variables controlling levels for each category
_DEBUG = "*:1"
# name of the environment variable controlling our logging
_ENV_VAR_NAME = None
# package names we should scrub filenames for
_PACKAGE_SCRUB_LIST = []

# dynamic dictionary of categories already seen and their level
_categories = {}

# log handlers registered
_log_handlers = []
_log_handlers_limited = []

_initialized = False
_enable_crack_output = False

_stdout = None
_stderr = None
_old_hup_handler = None
_outfile = None


# public log levels
(ERROR,
 WARN,
 FIXME,
 INFO,
 DEBUG,
 LOG) = list(range(1, 7))

COLORS = {ERROR: 'RED',
          WARN: 'YELLOW',
          FIXME: 'MAGENTA',
          INFO: 'GREEN',
          DEBUG: 'BLUE',
          LOG: 'CYAN'}

_FORMATTED_LEVELS = []
_LEVEL_NAMES = ['ERROR', 'WARN', 'FIXME', 'INFO', 'DEBUG', 'LOG']


class TerminalController:
    """A class for generating formatted output to a terminal.

    `TerminalController` defines a set of instance variables whose
    values are initialized to the control sequence necessary to
    perform a given action.  These can be simply included in normal
    output to the terminal:

        >>> term = TerminalController()
        >>> print('This is '+term.GREEN+'green'+term.NORMAL)

    Alternatively, the `render()` method can used, which replaces
    '${action}' with the string required to perform 'action':

        >>> term = TerminalController()
        >>> print(term.render('This is ${GREEN}green${NORMAL}'))

    If the terminal doesn't support a given action, then the value of
    the corresponding instance variable will be set to ''.  As a
    result, the above code will still work on terminals that do not
    support color, except that their output will not be colored.
    Also, this means that you can test whether the terminal supports a
    given action by simply testing the truth value of the
    corresponding instance variable:

        >>> term = TerminalController()
        >>> if term.CLEAR_SCREEN:
        ...     print('This terminal supports clearning the screen.')

    Finally, if the width and height of the terminal are known, then
    they will be stored in the `COLS` and `LINES` attributes.

    Args:
        term_stream (Optional): The stream that will be used for terminal
            output; if this stream is not a tty, then the terminal is
            assumed to be a dumb terminal (i.e., have no capabilities).
    """

    # Cursor movement:
    BOL = ''             # : Move the cursor to the beginning of the line
    UP = ''              # : Move the cursor up one line
    DOWN = ''            # : Move the cursor down one line
    LEFT = ''            # : Move the cursor left one char
    RIGHT = ''           # : Move the cursor right one char

    # Deletion:
    CLEAR_SCREEN = ''    # : Clear the screen and move to home position
    CLEAR_EOL = ''       # : Clear to the end of the line.
    CLEAR_BOL = ''       # : Clear to the beginning of the line.
    CLEAR_EOS = ''       # : Clear to the end of the screen

    # Output modes:
    BOLD = ''            # : Turn on bold mode
    BLINK = ''           # : Turn on blink mode
    DIM = ''             # : Turn on half-bright mode
    REVERSE = ''         # : Turn on reverse-video mode
    NORMAL = ''          # : Turn off all modes

    # Cursor display:
    HIDE_CURSOR = ''     # : Make the cursor invisible
    SHOW_CURSOR = ''     # : Make the cursor visible

    # Terminal size:
    COLS = None          # : Width of the terminal (None for unknown)
    LINES = None         # : Height of the terminal (None for unknown)

    # Foreground colors:
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''

    # Background colors:
    BG_BLACK = BG_BLUE = BG_GREEN = BG_CYAN = ''
    BG_RED = BG_MAGENTA = BG_YELLOW = BG_WHITE = ''

    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1
    CLEAR_SCREEN=clear CLEAR_EOL=el CLEAR_BOL=el1 CLEAR_EOS=ed BOLD=bold
    BLINK=blink DIM=dim REVERSE=rev UNDERLINE=smul NORMAL=sgr0
    HIDE_CURSOR=cinvis SHOW_CURSOR=cnorm""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    def __init__(self, term_stream=sys.stdout):
        # Curses isn't available on all platforms
        try:
            import curses
        except ImportError:
            return

        # If the stream isn't a tty, then assume it has no capabilities.
        if not term_stream.isatty():
            return

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try:
            curses.setupterm()
        except curses.error:
            return

        # Look up numeric capabilities.
        TerminalController.COLS = curses.tigetnum('cols')
        TerminalController.LINES = curses.tigetnum('lines')

        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._tigetstr(cap_name) or b'')

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            for i, color in zip(list(range(len(self._COLORS))), self._COLORS):
                setattr(self, color, curses.tparm(set_fg, i) or b'')
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            for i, color in zip(list(range(len(self._ANSICOLORS))),
                                self._ANSICOLORS):
                setattr(self, color, curses.tparm(set_fg_ansi, i) or b'')
        set_bg = self._tigetstr('setb')
        if set_bg:
            for i, color in zip(list(range(len(self._COLORS))), self._COLORS):
                setattr(self, 'BG_' + color, curses.tparm(set_bg, i) or b'')
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            for i, color in zip(list(range(len(self._ANSICOLORS))),
                                self._ANSICOLORS):
                setattr(
                    self, 'BG_' + color, curses.tparm(set_bg_ansi, i) or b'')

    def _tigetstr(self, cap_name):
        # String capabilities can include "delays" of the form "$<2>".
        # For any modern terminal, we should be able to just ignore
        # these, so strip them out.
        import curses
        cap = curses.tigetstr(cap_name) or b''
        return re.sub(r'\$<\d+>[/*]?', '', cap.decode()).encode()

    def render(self, template):
        """Replaces each $-substitutions in the specified template string.

        The placeholders are replaced with the corresponding terminal control
        string (if it's defined) or '' (if it's not).
        """
        return re.sub(r'\$\$|\${\w+}', self._render_sub, template)

    def _render_sub(self, match):
        matched_group = match.group()
        if matched_group == '$$':
            return matched_group
        else:
            return getattr(self, matched_group[2:-1])


def get_level_name(level):
    """Returns the name of the specified log level.

    Args:
        level (int): The level we want to know the name.

    Returns:
        str: The name of the level.
    """
    assert isinstance(level, int) and 0 < level <= len(_LEVEL_NAMES), \
        TypeError("Bad debug level")
    return _LEVEL_NAMES[level - 1]


def get_level_int(level_name):
    """Returns the integer value of the levelName.

    Args:
        level_name (str): The string value of the level name.

    Returns:
        int: The value of the level name we are interested in.
    """
    assert isinstance(level_name, str) and level_name in _LEVEL_NAMES, \
        "Bad debug level name"
    return _LEVEL_NAMES.index(level_name) + 1


def get_formatted_level_name(level):
    assert isinstance(level, int) and 0 < level <= len(_LEVEL_NAMES), \
        TypeError("Bad debug level")
    return _FORMATTED_LEVELS[level - 1]


def register_category(category):
    """Registers the specified category in the debug system.

    A level will be assigned to it based on previous calls to setDebug.
    """
    # parse what level it is set to based on _DEBUG
    # example: *:2,admin:4
    global _DEBUG
    global _categories

    level = 0
    chunks = _DEBUG.split(',')
    for chunk in chunks:
        if not chunk:
            continue
        if ':' in chunk:
            spec, value = chunk.split(':')
        else:
            spec = '*'
            value = chunk

        # our glob is unix filename style globbing, so cheat with fnmatch
        # fnmatch.fnmatch didn't work for this, so don't use it
        if category in fnmatch.filter((category, ), spec):
            # we have a match, so set level based on string or int
            if not value:
                continue
            try:
                level = int(value)
            except ValueError:  # e.g. *; we default to most
                level = 5
    # store it
    _categories[category] = level


def get_category_level(category):
    """Gets the debug level at which the specified category is being logged.

    Registers the category and thus assigns a log level if it wasn't registered
    yet.

    Args:
        category (string): The category we are interested in.
    """
    global _categories
    if category not in _categories:
        register_category(category)
    return _categories[category]


def set_log_settings(state):
    """Updates the current log settings.

    This can restore an old saved log settings object returned by
    getLogSettings.

    Args:
        state: The settings to set.
    """
    global _DEBUG
    global _log_handlers
    global _log_handlers_limited

    (_DEBUG,
     _categories,
     _log_handlers,
     _log_handlers_limited) = state

    for category in _categories:
        register_category(category)


def get_log_settings():
    """Fetches the current log settings.

    The returned object can be sent to setLogSettings to restore the
    returned settings

    Returns:
        The current settings.
    """
    return (_DEBUG,
            _categories,
            _log_handlers,
            _log_handlers_limited)


def _can_shortcut_logging(category, level):
    if _log_handlers:
        # we have some loggers operating without filters, have to do
        # everything
        return False
    else:
        return level > get_category_level(category)


def scrub_filename(filename):
    """Scrubs the filename to a relative path."""
    global _PACKAGE_SCRUB_LIST
    for package in _PACKAGE_SCRUB_LIST:
        i = filename.rfind(package)
        if i > -1:
            return filename[i:]

    return filename


def get_file_line(where=-1):
    """Returns the filename and line number for the specified location.

    Args:
        where(int or function): If it's a (negative) integer, looks for
            the code entry in the current stack that is the given number
            of frames above this module.
            If it's a function, look for the code entry of the function.

    Returns:
        str, int, str: file, line, function_name.
    """
    co = None
    lineno = None
    name = None

    if isinstance(where, types.FunctionType):
        co = where.__code__
        lineno = co.co_firstlineno
        name = co.co_name
    elif isinstance(where, types.MethodType):
        co = where.__func__.__code__
        lineno = co.co_firstlineno
        name = co.co_name
    else:
        stack_frame = sys._getframe()  # pylint: disable=protected-access
        while stack_frame:
            co = stack_frame.f_code
            if not co.co_filename.endswith('loggable.py'):
                co = stack_frame.f_code
                lineno = stack_frame.f_lineno
                name = co.co_name
                break
            stack_frame = stack_frame.f_back

    if not co:
        return "<unknown file>", 0, None

    return scrub_filename(co.co_filename), lineno, name


def ellipsize(obj):
    """Ellipsizes the representation of the given object."""
    obj_repr = repr(obj)
    if len(obj_repr) < 800:
        return obj_repr

    obj_repr = obj_repr[:60] + ' ... ' + obj_repr[-15:]
    return obj_repr


def get_format_args(start_format, start_args, end_format, end_args, args, kwargs):
    """Creates a format and args to use for logging.

    This avoids needlessly interpolating variables.
    """
    debug_args = start_args[:]
    for arg in args:
        debug_args.append(ellipsize(arg))

    for items in list(kwargs.items()):
        debug_args.extend(items)
    debug_args.extend(end_args)
    fmt = start_format \
        + ', '.join(('%s', ) * len(args)) \
        + (kwargs and ', ' or '') \
        + ', '.join(('%s=%r', ) * len(kwargs)) \
        + end_format
    return fmt, debug_args


def do_log(level, obj, category, message, args, where=-1, file_path=None, line=None):
    """Logs something.

    Args:
        level (int): Debug level.
        obj (str): Object converted to str.
        category (str): Category such as the name of the obj's class.
        message (str): The message to log.
        args (list): The args to apply to the message, if any.
        where (int or function): What to log file and line number for;
            -1 for one frame above log.py; -2 and down for higher up;
            a function for a (future) code object.
        file_path (Optional[str]): The file to show the message as coming from,
            if caller knows best.
        line (Optional[int]): The line to show the message as coming from,
            if caller knows best.

    Returns:
        A dict of calculated variables, if they needed calculating.
        currently contains file and line; this prevents us from
        doing this work in the caller when it isn't needed because
        of the debug level.
    """
    ret = {}

    if args:
        message = message % args
    funcname = None

    if level > get_category_level(category):
        handlers = _log_handlers
    else:
        handlers = _log_handlers + _log_handlers_limited

    if handlers:
        if file_path is None and line is None:
            (file_path, line, funcname) = get_file_line(where=where)
        ret['filePath'] = file_path
        ret['line'] = line
        if funcname:
            message = "\033[00m\033[32;01m%s:\033[00m %s" % (funcname, message)
        for handler in handlers:
            try:
                handler(level, obj, category, file_path, line, message)
            except TypeError as e:
                raise SystemError("handler %r unusable" % handler) from e

    return ret


def error_object(obj, cat, fmt, *args):
    """Logs a fatal error message in the specified category.

    This will also raise a `SystemExit`.
    """
    do_log(ERROR, obj, cat, fmt, args)


def warning_object(obj, cat, fmt, *args):
    """Logs a warning message in the specified category.

    This is used for non-fatal problems.
    """
    do_log(WARN, obj, cat, fmt, args)


def fixme_object(obj, cat, fmt, *args):
    """Logs a fixme message in the specified category.

    This is used for not implemented codepaths or known issues in the code.
    """
    do_log(FIXME, obj, cat, fmt, args)


def info_object(obj, cat, fmt, *args):
    """Logs an informational message in the specified category."""
    do_log(INFO, obj, cat, fmt, args)


def debug_object(obj, cat, fmt, *args):
    """Logs a debug message in the specified category."""
    do_log(DEBUG, obj, cat, fmt, args)


def log_object(obj, cat, fmt, *args):
    """Logs a log message.

    Used for debugging recurring events.
    """
    do_log(LOG, obj, cat, fmt, args)


def safeprintf(file, fmt, *args):
    """Writes to a file object, ignoring errors."""
    try:
        if args:
            file.write(fmt % args)
        else:
            file.write(fmt)
    except IOError as e:
        if e.errno == errno.EPIPE:
            # if our output is closed, exit; e.g. when logging over an
            # ssh connection and the ssh connection is closed
            # pylint: disable=protected-access
            os._exit(os.EX_OSERR)
        # otherwise ignore it, there's nothing you can do


def print_handler(level, obj, category, file, line, message):
    """Writes to stderr.

    The output will be different depending the value of "_enable_crack_output";
    in Pitivi's case, that is True when the GST_DEBUG env var is defined.

    Args:
        level (str): The debug level.
        obj (Optional[str]): The object the message is about, or None.
        category (str): Category such as the name of the obj's class.
        file (str): The source file where the message originates.
        line (int): The line number in the file where the message originates.
        message (str): The message to be logged.
    """
    global _outfile

    # Make the file path more compact for readability
    file = os.path.relpath(file)
    where = "(%s:%d)" % (file, line)

    # If GST_DEBUG is not set, we can assume only PITIVI_DEBUG is set, so don't
    # show a bazillion of debug details that are not relevant to Pitivi.
    if not _enable_crack_output:
        safeprintf(_outfile, '%s %-8s %-17s %-2s %s %s\n',
                   get_formatted_level_name(level), time.strftime("%H:%M:%S"),
                   category, obj, message, where)
    else:
        if obj:
            obj = '"' + obj + '"'
        else:
            obj = ""
        # level   pid     object   cat      time
        # 5 + 1 + 7 + 1 + 32 + 1 + 17 + 1 + 15 == 80
        safeprintf(
            _outfile, '%s [%5d] [0x%12x] %-32s %-17s %-15s %-4s %s %s\n',
            get_formatted_level_name(level), os.getpid(),
            threading.current_thread().ident,
            obj[:32], category, time.strftime("%b %d %H:%M:%S"), "",
            message, where)
    _outfile.flush()


def log_level_name(level):
    fmt = '%-5s'
    return fmt % (_LEVEL_NAMES[level - 1], )


def _as_string(string_or_bytes):
    if isinstance(string_or_bytes, bytes):
        return string_or_bytes.decode()
    else:
        return string_or_bytes


def _preformat_levels(enable_color_output):
    terminal_controller = TerminalController()
    for level in ERROR, WARN, FIXME, INFO, DEBUG, LOG:
        if enable_color_output:
            formatter = ''.join(
                (_as_string(terminal_controller.BOLD),
                 _as_string(getattr(terminal_controller, COLORS[level])),
                 log_level_name(level),
                 _as_string(terminal_controller.NORMAL)))
        else:
            formatter = log_level_name(level)
        _FORMATTED_LEVELS.append(formatter)

# "public" useful API

# setup functions


def init(env_var_name, enable_color_output=True, enable_crack_output=True):
    """Initializes the logging system.

    Needs to be called before using the log methods.

    Args:
        env_var_name (str): The name of the environment variable with additional
            settings.
        enable_color_output (Optional[bool]): Whether to colorize the output.
        enable_crack_output (Optional[bool]): Whether to print detailed info.
    """
    global _initialized
    global _outfile
    global _enable_crack_output
    _enable_crack_output = enable_crack_output

    if _initialized:
        return

    global _ENV_VAR_NAME
    _ENV_VAR_NAME = env_var_name

    _preformat_levels(enable_color_output)

    if env_var_name in os.environ:
        # install a log handler that uses the value of the environment var
        set_debug(os.environ[env_var_name])
    filename_env_var_name = env_var_name + "_FILE"

    if filename_env_var_name in os.environ:
        # install a log handler that uses the value of the environment var
        # pylint: disable=consider-using-with
        _outfile = open(os.environ[filename_env_var_name], "w+", encoding="UTF-8")
    else:
        _outfile = sys.stderr

    add_limited_log_handler(print_handler)

    _initialized = True


def set_debug(string):
    """Sets the DEBUG string.

    This controls the log output.
    """
    global _DEBUG
    global _ENV_VAR_NAME
    global _categories

    _DEBUG = string
    debug('log', "%s set to %s" % (_ENV_VAR_NAME, _DEBUG))

    # reparse all already registered category levels
    for category in _categories:
        register_category(category)


def get_debug():
    """Returns the currently active DEBUG string."""
    global _DEBUG
    return _DEBUG


def set_package_scrub_list(*packages):
    """Sets the package names to scrub from filenames.

    Filenames from these paths in log messages will be scrubbed to their
    relative file path instead of the full absolute path.

    Args:
        *packages (List[str]): The packages names to scrub.
    """
    global _PACKAGE_SCRUB_LIST
    _PACKAGE_SCRUB_LIST = packages


def reset():
    """Resets the logging system, removing all log handlers."""
    global _log_handlers, _log_handlers_limited, _initialized

    _log_handlers = []
    _log_handlers_limited = []
    _initialized = False


def add_log_handler(func):
    """Adds a custom log handler.

    The log handler receives all the log messages.

    Args:
        func (function): A function object with prototype
            (level, obj, category, message) where level is either
            ERROR, WARN, INFO, DEBUG, or LOG, and the rest of the arguments are
            strings or None. Use getLevelName(level) to get a printable name
            for the log level.

    Raises:
        TypeError: When func is not a callable.
    """
    if not isinstance(func, collections.abc.Callable):
        raise TypeError("func must be callable")

    if func not in _log_handlers:
        _log_handlers.append(func)


def add_limited_log_handler(func):
    """Adds a custom limited log handler.

    The log handler receives only the messages passing the filter.

    Args:
        func (function): A function object with prototype
            (level, obj, category, message) where level is either
            ERROR, WARN, INFO, DEBUG, or LOG, and the rest of the arguments are
            strings or None. Use getLevelName(level) to get a printable name
            for the log level.

    Raises:
        TypeError: When func is not a callable.
    """
    if not isinstance(func, collections.abc.Callable):
        raise TypeError("func must be callable")

    if func not in _log_handlers_limited:
        _log_handlers_limited.append(func)


def remove_log_handler(func):
    """Removes a registered log handler.

    Raises:
        ValueError: When func is not registered.
    """
    _log_handlers.remove(func)


def remove_limited_log_handler(func):
    """Removes a registered limited log handler.

    Raises:
        ValueError: When func is not registered.
    """
    _log_handlers_limited.remove(func)

# public log functions


def error(cat, fmt, *args):
    error_object(None, cat, fmt, *args)


def warning(cat, fmt, *args):
    warning_object(None, cat, fmt, *args)


def fixme(cat, fmt, *args):
    fixme_object(None, cat, fmt, *args)


def info(cat, fmt, *args):
    info_object(None, cat, fmt, *args)


def debug(cat, fmt, *args):
    debug_object(None, cat, fmt, *args)


def log(cat, fmt, *args):
    log_object(None, cat, fmt, *args)

# public utility functions


def get_exception_message(exception, frame=-1, filename=None):
    """Returns a short message based on an exception.

    Useful for debugging.
    Tries to find where the exception was triggered.
    """
    stack = traceback.extract_tb(sys.exc_info()[2])
    if filename:
        stack = [f for f in stack if f[0].find(filename) > -1]
    # import code; code.interact(local=locals())
    (filename, line, func, text) = stack[frame]
    filename = scrub_filename(filename)
    exc = exception.__class__.__name__
    msg = ""
    # a shortcut to extract a useful message out of most exceptions
    # for now
    if str(exception):
        msg = ": %s" % str(exception)
    return "exception %(exc)s at %(filename)s:%(line)s: %(func)s()%(msg)s" \
        % locals()


# base class for loggable objects


class BaseLoggable:
    """Base class for objects that want to be able to log messages.

    The levels of severity for the messages are, in order from least
    to most: log, debug, info, warning, error.

    Attributes:
        log_category (str): The category under which the messages will be filed.
            Can be used to set a display filter.
    """

    def error(self, *args):
        """Logs an error.

        By default this will also raise an exception.
        """
        if _can_shortcut_logging(self.log_category, ERROR):
            return
        error_object(self.log_object_name(),
                     self.log_category, *self.log_function(*args))

    def warning(self, *args):
        """Logs a warning.

        Used for non-fatal problems.
        """
        if _can_shortcut_logging(self.log_category, WARN):
            return
        warning_object(
            self.log_object_name(), self.log_category, *self.log_function(*args))

    def fixme(self, *args):
        """Logs a fixme.

        Used for FIXMEs.
        """
        if _can_shortcut_logging(self.log_category, FIXME):
            return
        fixme_object(self.log_object_name(),
                     self.log_category, *self.log_function(*args))

    def info(self, *args):
        """Logs an informational message.

        Used for normal operation.
        """
        if _can_shortcut_logging(self.log_category, INFO):
            return
        info_object(self.log_object_name(),
                    self.log_category, *self.log_function(*args))

    def debug(self, *args):
        """Logs a debug message.

        Used for debugging.
        """
        if _can_shortcut_logging(self.log_category, DEBUG):
            return
        debug_object(self.log_object_name(),
                     self.log_category, *self.log_function(*args))

    def log(self, *args):
        """Logs a log message.

        Used for debugging recurring events.
        """
        if _can_shortcut_logging(self.log_category, LOG):
            return
        log_object(self.log_object_name(),
                   self.log_category, *self.log_function(*args))

    def do_log(self, level, where, fmt, *args, **kwargs):
        """Logs a message at the specified level.

        Args:
            level (int): The log level.
            where (int or function): How many frames to go back from
                the last log frame, must be negative; or a function
                (to log for a future call).
            fmt (str): The string template for the message.
            *args: The arguments used when converting the `fmt`
                string template to the message.
            **kwargs: The pre-calculated values from a previous do_log call.

        Returns:
            dict: The calculated variables, to be reused in a
                 call to do_log that should show the same location.
        """
        if _can_shortcut_logging(self.log_category, level):
            return {}
        args = self.log_function(*args)
        return do_log(level, self.log_object_name(), self.log_category,
                      fmt, args, where=where, **kwargs)

    def log_function(self, *args):
        """Processes the arguments applied to the message template.

        Default just returns the arguments unchanged.
        """
        return args

    def log_object_name(self):
        """Gets the name of this object."""
        for name in ['logName', 'name']:
            if hasattr(self, name):
                return getattr(self, name)

        return None

    def handle_exception(self, exc):
        self.warning(get_exception_message(exc))


class Loggable(BaseLoggable):

    def __init__(self, log_category=None):
        if log_category:
            self.log_category = log_category
        elif not hasattr(self, 'log_category'):
            self.log_category = self.__class__.__name__.lower()

    def log_object_name(self):
        res = BaseLoggable.log_object_name(self)
        if not res:
            return "<%s at 0x%x>" % (self.__class__.__name__, id(self))
        return res

    def error(self, fmt, *args):
        if _can_shortcut_logging(self.log_category, ERROR):
            return
        do_log(ERROR, self.log_object_name(), self.log_category,
               fmt, self.log_function(*args), where=-2)
