# -*- Mode: Python; test-case-name: test_log -*-
# vi:si:et:sw=4:sts=4:ts=4

# This file is released under the standard PSF license.

"""
Logging module.

Five levels of log information are defined.
These are, in order of decreasing verbosity: log, debug, info, warning, error.

This module provides a Loggable class for objects, as well as various
convenience methods for logging in general, and for logging with Twisted
and failures in particular.

Maintainer: U{Thomas Vander Stichele <thomas at apestaart dot org>}
"""

import errno
import sys
import os
import fnmatch
import time
import types
import traceback
import thread

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

_stdout = None
_stderr = None
_old_hup_handler = None


# public log levels
(ERROR,
 WARN,
 INFO,
 DEBUG,
 LOG) = range(1, 6)

COLORS = {ERROR: 'RED',
          WARN: 'YELLOW',
          INFO: 'GREEN',
          DEBUG: 'BLUE',
          LOG: 'CYAN'}

_FORMATTED_LEVELS = []
_LEVEL_NAMES = ['ERROR', 'WARN', 'INFO', 'DEBUG', 'LOG']


def getLevelName(level):
    """
    Return the name of a log level.
    @param level: The level we want to know the name
    @type level: int
    @return: The name of the level
    @rtype: str
    """
    assert isinstance(level, int) and level > 0 and level < 6, \
           TypeError("Bad debug level")
    return getLevelNames()[level - 1]


def getLevelNames():
    """
    Return a list with the level names
    @return: A list with the level names
    @rtype: list of str
    """
    return _LEVEL_NAMES


def getLevelInt(levelName):
    """
    Return the integer value of the levelName.
    @param levelName: The string value of the level name
    @type levelName: str
    @return: The value of the level name we are interested in.
    @rtype: int
    """
    assert isinstance(levelName, str) and levelName in getLevelNames(), \
        "Bad debug level name"
    return  getLevelNames().index(levelName)+1


def getFormattedLevelName(level):
    assert isinstance(level, int) and level > 0 and level < 6, \
           TypeError("Bad debug level")
    return _FORMATTED_LEVELS[level - 1]


def registerCategory(category):
    """
    Register a given category in the debug system.
    A level will be assigned to it based on previous calls to setDebug.
    """
    # parse what level it is set to based on _DEBUG
    # example: *:2,admin:4
    global _DEBUG
    global _levels
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
            except ValueError: # e.g. *; we default to most
                level = 5
    # store it
    _categories[category] = level


def getCategoryLevel(category):
    """
    @param category: string

    Get the debug level at which this category is being logged, adding it
    if it wasn't registered yet.
    """
    global _categories
    if not category in _categories:
        registerCategory(category)
    return _categories[category]


def setLogSettings(state):
    """Update the current log settings.
    This can restore an old saved log settings object returned by
    getLogSettings
    @param state: the settings to set
    """

    global _DEBUG
    global _log_handlers
    global _log_handlers_limited

    (_DEBUG,
     _categories,
     _log_handlers,
     _log_handlers_limited) = state

    for category in _categories:
        registerCategory(category)


def getLogSettings():
    """Fetches the current log settings.
    The returned object can be sent to setLogSettings to restore the
    returned settings
    @returns: the current settings
    """
    return (_DEBUG,
            _categories,
            _log_handlers,
            _log_handlers_limited)


def _canShortcutLogging(category, level):
    if _log_handlers:
        # we have some loggers operating without filters, have to do
        # everything
        return False
    else:
        return level > getCategoryLevel(category)


def scrubFilename(filename):
    '''
    Scrub the filename to a relative path for all packages in our scrub list.
    '''
    global _PACKAGE_SCRUB_LIST
    for package in _PACKAGE_SCRUB_LIST:
        i = filename.rfind(package)
        if i > -1:
            return filename[i:]

    return filename


def getFileLine(where=-1):
    """
    Return the filename and line number for the given location.

    If where is a negative integer, look for the code entry in the current
    stack that is the given number of frames above this module.
    If where is a function, look for the code entry of the function.

    @param where: how many frames to go back up, or function
    @type  where: int (negative) or function

    @return: tuple of (file, line)
    @rtype:  tuple of (str, int)
    """
    co = None
    lineno = None
    name = None

    if isinstance(where, types.FunctionType):
        co = where.func_code
        lineno = co.co_firstlineno
        name = co.co_name
    elif isinstance(where, types.MethodType):
        co = where.im_func.func_code
        lineno = co.co_firstlineno
        name = co.co_name
    else:
        stackFrame = sys._getframe()
        while stackFrame:
            co = stackFrame.f_code
            if not co.co_filename.endswith('log.py'):
                # wind up the stack according to frame
                while where < -1:
                    stackFrame = stackFrame.f_back
                    where += 1
                co = stackFrame.f_code
                lineno = stackFrame.f_lineno
                name = co.co_name
                break
            stackFrame = stackFrame.f_back

    if not co:
        return "<unknown file>", 0

    return scrubFilename(co.co_filename), lineno, name


def ellipsize(o):
    """
    Ellipsize the representation of the given object.
    """
    r = repr(o)
    if len(r) < 800:
        return r

    r = r[:60] + ' ... ' + r[-15:]
    return r


def getFormatArgs(startFormat, startArgs, endFormat, endArgs, args, kwargs):
    """
    Helper function to create a format and args to use for logging.
    This avoids needlessly interpolating variables.
    """
    debugArgs = startArgs[:]
    for a in args:
        debugArgs.append(ellipsize(a))

    for items in kwargs.items():
        debugArgs.extend(items)
    debugArgs.extend(endArgs)
    format = startFormat \
              + ', '.join(('%s', ) * len(args)) \
              + (kwargs and ', ' or '') \
              + ', '.join(('%s=%r', ) * len(kwargs)) \
              + endFormat
    return format, debugArgs


def doLog(level, object, category, format, args, where=-1,
    filePath=None, line=None):
    """
    @param where:     what to log file and line number for;
                      -1 for one frame above log.py; -2 and down for higher up;
                      a function for a (future) code object
    @type  where:     int or callable
    @param filePath:  file to show the message as coming from, if caller
                      knows best
    @type  filePath:  str
    @param line:      line to show the message as coming from, if caller
                      knows best
    @type  line:      int

    @return: dict of calculated variables, if they needed calculating.
             currently contains file and line; this prevents us from
             doing this work in the caller when it isn't needed because
             of the debug level
    """
    ret = {}

    if args:
        message = format % args
    else:
        message = format

    # first all the unlimited ones
    if _log_handlers:
        if filePath is None and line is None:
            (filePath, line, funcname) = getFileLine(where=where)
        ret['filePath'] = filePath
        ret['line'] = line
        if funcname:
            message = "\033[00m\033[32;01m%s:\033[00m %s" % (funcname, message)
        for handler in _log_handlers:
            try:
                handler(level, object, category, file, line, message)
            except TypeError, e:
                raise SystemError("handler %r raised a TypeError: %s" % (
                    handler, getExceptionMessage(e)))

    if level > getCategoryLevel(category):
        return ret

    if _log_handlers_limited:
        if filePath is None and line is None:
            (filePath, line, funcname) = getFileLine(where=where)
        ret['filePath'] = filePath
        ret['line'] = line
        if funcname:
            message = "\033[00m\033[32;01m%s:\033[00m %s" % (funcname, message)
        for handler in _log_handlers_limited:
            # set this a second time, just in case there weren't unlimited
            # loggers there before
            try:
                handler(level, object, category, filePath, line, message)
            except TypeError:
                raise SystemError("handler %r raised a TypeError" % handler)

        return ret


def errorObject(object, cat, format, *args):
    """
    Log a fatal error message in the given category.
    This will also raise a L{SystemExit}.
    """
    doLog(ERROR, object, cat, format, args)

    # we do the import here because having it globally causes weird import
    # errors if our gstreactor also imports .log, which brings in errors
    # and pb stuff
    if args:
        raise SystemExit(format % args)
    else:
        raise SystemExit(format)


def warningObject(object, cat, format, *args):
    """
    Log a warning message in the given category.
    This is used for non-fatal problems.
    """
    doLog(WARN, object, cat, format, args)


def infoObject(object, cat, format, *args):
    """
    Log an informational message in the given category.
    """
    doLog(INFO, object, cat, format, args)


def debugObject(object, cat, format, *args):
    """
    Log a debug message in the given category.
    """
    doLog(DEBUG, object, cat, format, args)


def logObject(object, cat, format, *args):
    """
    Log a log message.  Used for debugging recurring events.
    """
    doLog(LOG, object, cat, format, args)


def safeprintf(file, format, *args):
    """Write to a file object, ignoring errors.
    """
    try:
        if args:
            file.write(format % args)
        else:
            file.write(format)
    except IOError, e:
        if e.errno == errno.EPIPE:
            # if our output is closed, exit; e.g. when logging over an
            # ssh connection and the ssh connection is closed
            os._exit(os.EX_OSERR)
        # otherwise ignore it, there's nothing you can do


def stderrHandler(level, object, category, file, line, message):
    """
    A log handler that writes to stderr.

    @type level:    string
    @type object:   string (or None)
    @type category: string
    @type message:  string
    """

    o = ""
    if object:
        o = '"' + object + '"'

    where = "(%s:%d)" % (file, line)

    # level   pid     object   cat      time
    # 5 + 1 + 7 + 1 + 32 + 1 + 17 + 1 + 15 == 80
    safeprintf(sys.stderr, '%s [%5d] [0x%12x] %-32s %-17s %-15s %-4s %s %s\n',
               getFormattedLevelName(level), os.getpid(), thread.get_ident(),
               o[:32], category,
               time.strftime("%b %d %H:%M:%S")
               , "", message, where)
    sys.stderr.flush()


def _preformatLevels(noColorEnvVarName):
    format = '%-5s'

    try:
        import termcolor
    except ImportError:
        # we don't need to catch this if termcolor is in same package as
        # log.py
        termcolor = None

    if (noColorEnvVarName is not None
        and termcolor is not None
        and (noColorEnvVarName not in os.environ
             or not os.environ[noColorEnvVarName])):

        t = termcolor.TerminalController()
        formatter = lambda level: ''.join((t.BOLD, getattr(t, COLORS[level]),
                            format % (_LEVEL_NAMES[level-1], ), t.NORMAL))
    else:
        formatter = lambda level: format % (_LEVEL_NAMES[level-1], )

    for level in ERROR, WARN, INFO, DEBUG, LOG:
        _FORMATTED_LEVELS.append(formatter(level))

### "public" useful API

# setup functions


def init(envVarName, enableColorOutput=False):
    """
    Initialize the logging system and parse the environment variable
    of the given name.
    Needs to be called before starting the actual application.
    """
    global _initialized

    if _initialized:
        return

    global _ENV_VAR_NAME
    _ENV_VAR_NAME = envVarName

    if enableColorOutput:
        _preformatLevels(envVarName + "_NO_COLOR")
    else:
        _preformatLevels(None)

    if envVarName in os.environ:
        # install a log handler that uses the value of the environment var
        setDebug(os.environ[envVarName])
    addLimitedLogHandler(stderrHandler)

    _initialized = True


def setDebug(string):
    """Set the DEBUG string.  This controls the log output."""
    global _DEBUG
    global _ENV_VAR_NAME
    global _categories

    _DEBUG = string
    debug('log', "%s set to %s" % (_ENV_VAR_NAME, _DEBUG))

    # reparse all already registered category levels
    for category in _categories:
        registerCategory(category)


def getDebug():
    """
    Returns the currently active DEBUG string.
    @rtype: str
    """
    global _DEBUG
    return _DEBUG


def setPackageScrubList(*packages):
    """
    Set the package names to scrub from filenames.
    Filenames from these paths in log messages will be scrubbed to their
    relative file path instead of the full absolute path.

    @type packages: list of str
    """
    global _PACKAGE_SCRUB_LIST
    _PACKAGE_SCRUB_LIST = packages


def reset():
    """
    Resets the logging system, removing all log handlers.
    """
    global _log_handlers, _log_handlers_limited, _initialized

    _log_handlers = []
    _log_handlers_limited = []
    _initialized = False


def addLogHandler(func):
    """
    Add a custom log handler.

    @param func: a function object with prototype (level, object, category,
                 message) where level is either ERROR, WARN, INFO, DEBUG, or
                 LOG, and the rest of the arguments are strings or None. Use
                 getLevelName(level) to get a printable name for the log level.
    @type func:  a callable function

    @raises TypeError: if func is not a callable
    """

    if not callable(func):
        raise TypeError("func must be callable")

    if func not in _log_handlers:
        _log_handlers.append(func)


def addLimitedLogHandler(func):
    """
    Add a custom log handler.

    @param func: a function object with prototype (level, object, category,
                 message) where level is either ERROR, WARN, INFO, DEBUG, or
                 LOG, and the rest of the arguments are strings or None. Use
                 getLevelName(level) to get a printable name for the log level.
    @type func:  a callable function

    @raises TypeError: TypeError if func is not a callable
    """
    if not callable(func):
        raise TypeError("func must be callable")

    if func not in _log_handlers_limited:
        _log_handlers_limited.append(func)


def removeLogHandler(func):
    """
    Remove a registered log handler.

    @param func: a function object with prototype (level, object, category,
                 message) where level is either ERROR, WARN, INFO, DEBUG, or
                 LOG, and the rest of the arguments are strings or None. Use
                 getLevelName(level) to get a printable name for the log level.
    @type func:  a callable function

    @raises ValueError: if func is not registered
    """
    _log_handlers.remove(func)


def removeLimitedLogHandler(func):
    """
    Remove a registered limited log handler.

    @param func: a function object with prototype (level, object, category,
                 message) where level is either ERROR, WARN, INFO, DEBUG, or
                 LOG, and the rest of the arguments are strings or None. Use
                 getLevelName(level) to get a printable name for the log level.
    @type func:  a callable function

    @raises ValueError: if func is not registered
    """
    _log_handlers_limited.remove(func)

# public log functions


def error(cat, format, *args):
    errorObject(None, cat, format, *args)


def warning(cat, format, *args):
    warningObject(None, cat, format, *args)


def info(cat, format, *args):
    infoObject(None, cat, format, *args)


def debug(cat, format, *args):
    debugObject(None, cat, format, *args)


def log(cat, format, *args):
    logObject(None, cat, format, *args)

# public utility functions


def getExceptionMessage(exception, frame=-1, filename=None):
    """
    Return a short message based on an exception, useful for debugging.
    Tries to find where the exception was triggered.
    """
    stack = traceback.extract_tb(sys.exc_info()[2])
    if filename:
        stack = [f for f in stack if f[0].find(filename) > -1]
    #import code; code.interact(local=locals())
    (filename, line, func, text) = stack[frame]
    filename = scrubFilename(filename)
    exc = exception.__class__.__name__
    msg = ""
    # a shortcut to extract a useful message out of most exceptions
    # for now
    if str(exception):
        msg = ": %s" % str(exception)
    return "exception %(exc)s at %(filename)s:%(line)s: %(func)s()%(msg)s" \
        % locals()


def reopenOutputFiles():
    """
    Reopens the stdout and stderr output files, as set by
    L{outputToFiles}.
    """
    if not _stdout and not _stderr:
        debug('log', 'told to reopen log files, but log files not set')
        return

    def reopen(name, fileno, *args):
        oldmask = os.umask(0026)
        try:
            f = open(name, 'a+', *args)
        finally:
            os.umask(oldmask)

        os.dup2(f.fileno(), fileno)

    if _stdout:
        reopen(_stdout, sys.stdout.fileno())

    if _stderr:
        reopen(_stderr, sys.stderr.fileno(), 0)
        debug('log', 'opened log %r', _stderr)


def outputToFiles(stdout=None, stderr=None):
    """
    Redirect stdout and stderr to named files.

    Records the file names so that a future call to reopenOutputFiles()
    can open the same files. Installs a SIGHUP handler that will reopen
    the output files.

    Note that stderr is opened unbuffered, so if it shares a file with
    stdout then interleaved output may not appear in the order that you
    expect.
    """
    global _stdout, _stderr, _old_hup_handler
    _stdout, _stderr = stdout, stderr
    reopenOutputFiles()

    def sighup(signum, frame):
        info('log', "Received SIGHUP, reopening logs")
        reopenOutputFiles()
        if _old_hup_handler:
            info('log', "Calling old SIGHUP hander")
            _old_hup_handler(signum, frame)

    debug('log', 'installing SIGHUP handler')
    import signal
    handler = signal.signal(signal.SIGHUP, sighup)
    if handler == signal.SIG_DFL or handler == signal.SIG_IGN:
        _old_hup_handler = None
    else:
        _old_hup_handler = handler


# base class for loggable objects


class Loggable(object):
    """
    Base class for objects that want to be able to log messages with
    different level of severity.  The levels are, in order from least
    to most: log, debug, info, warning, error.

    @cvar logCategory: Implementors can provide a category to log their
       messages under.
    """


    def writeMarker(self, marker, level):
        """
        Sets a marker that written to the logs. Setting this
        marker to multiple elements at a time helps debugging.
        @param marker: A string write to the log.
        @type marker: str
        @param level: The log level. It can be log.WARN, log.INFO,
        log.DEBUG, log.ERROR or log.LOG.
        @type  level: int
        """
        logHandlers = {WARN: self.warning,
                       INFO: self.info,
                       DEBUG: self.debug,
                       ERROR: self.error,
                       LOG: self.log}
        logHandler = logHandlers.get(level)
        if logHandler:
            logHandler('%s', marker)

    def error(self, *args):
        """Log an error.  By default this will also raise an exception."""
        if _canShortcutLogging(self.logCategory, ERROR):
            return
        errorObject(self.logObjectName(), self.logCategory,
            *self.logFunction(*args))

    def warning(self, *args):
        """Log a warning.  Used for non-fatal problems."""
        if _canShortcutLogging(self.logCategory, WARN):
            return
        warningObject(self.logObjectName(), self.logCategory,
            *self.logFunction(*args))

    def info(self, *args):
        """Log an informational message.  Used for normal operation."""
        if _canShortcutLogging(self.logCategory, INFO):
            return
        infoObject(self.logObjectName(), self.logCategory,
            *self.logFunction(*args))

    def debug(self, *args):
        """Log a debug message.  Used for debugging."""
        if _canShortcutLogging(self.logCategory, DEBUG):
            return
        debugObject(self.logObjectName(), self.logCategory,
            *self.logFunction(*args))

    def log(self, *args):
        """Log a log message.  Used for debugging recurring events."""
        if _canShortcutLogging(self.logCategory, LOG):
            return
        logObject(self.logObjectName(), self.logCategory,
            *self.logFunction(*args))

    def doLog(self, level, where, format, *args, **kwargs):
        """
        Log a message at the given level, with the possibility of going
        higher up in the stack.

        @param level: log level
        @type  level: int
        @param where: how many frames to go back from the last log frame;
                      or a function (to log for a future call)
        @type  where: int (negative), or function

        @param kwargs: a dict of pre-calculated values from a previous
                       doLog call

        @return: a dict of calculated variables, to be reused in a
                 call to doLog that should show the same location
        @rtype:  dict
        """
        if _canShortcutLogging(self.logCategory, level):
            return {}
        args = self.logFunction(*args)
        return doLog(level, self.logObjectName(), self.logCategory,
            format, args, where=where, **kwargs)

    def warningFailure(self, failure, swallow=True):
        """
        Log a warning about a Twisted Failure. Useful as an errback handler:
        d.addErrback(self.warningFailure)

        @param swallow: whether to swallow the failure or not
        @type  swallow: bool
        """
        if _canShortcutLogging(self.logCategory, WARN):
            if swallow:
                return
            return failure
        warningObject(self.logObjectName(), self.logCategory,
            *self.logFunction(getFailureMessage(failure)))
        if not swallow:
            return failure

    def logFunction(self, *args):
        """Overridable log function.  Default just returns passed message."""
        return args

    def logObjectName(self):
        """Overridable object name function."""
        # cheat pychecker
        for name in ['logName', 'name']:
            if hasattr(self, name):
                return getattr(self, name)

        return None

    def handleException(self, exc):
        self.warning(getExceptionMessage(exc))

# Twisted helper stuff

# private stuff
_initializedTwisted = False

# make a singleton
__theTwistedLogObserver = None


def _getTheTwistedLogObserver():
    # used internally and in test
    global __theTwistedLogObserver

    if not __theTwistedLogObserver:
        __theTwistedLogObserver = TwistedLogObserver()

    return __theTwistedLogObserver


# public helper methods


def getFailureMessage(failure):
    """
    Return a short message based on L{twisted.python.failure.Failure}.
    Tries to find where the exception was triggered.
    """
    exc = str(failure.type)
    msg = failure.getErrorMessage()
    if len(failure.frames) == 0:
        return "failure %(exc)s: %(msg)s" % locals()

    (func, filename, line, some, other) = failure.frames[-1]
    filename = scrubFilename(filename)
    return "failure %(exc)s at %(filename)s:%(line)s: %(func)s(): %(msg)s" \
        % locals()


def warningFailure(failure, swallow=True):
    """
    Log a warning about a Failure. Useful as an errback handler:
    d.addErrback(warningFailure)

    @param swallow: whether to swallow the failure or not
    @type  swallow: bool
    """
    warning('', getFailureMessage(failure))
    if not swallow:
        return failure


def logTwisted():
    """
    Integrate twisted's logger with our logger.

    This is done in a separate method because calling this imports and sets
    up a reactor.  Since we want basic logging working before choosing a
    reactor, we need to separate these.
    """
    global _initializedTwisted

    if _initializedTwisted:
        return

    debug('log', 'Integrating twisted logger')

    # integrate twisted's logging with us
    from twisted.python import log as tlog

    # this call imports the reactor
    # that is why we do this in a separate method
    from twisted.spread import pb

    # we don't want logs for pb.Error types since they
    # are specifically raised to be handled on the other side
    observer = _getTheTwistedLogObserver()
    observer.ignoreErrors([pb.Error, ])
    tlog.startLoggingWithObserver(observer.emit, False)

    _initializedTwisted = True


# we need an object as the observer because startLoggingWithObserver
# expects a bound method


class TwistedLogObserver(Loggable):
    """
    Twisted log observer that integrates with our logging.
    """
    logCategory = "logobserver"

    def __init__(self):
        self._ignoreErrors = [] # Failure types

    def emit(self, eventDict):
        method = log # by default, lowest level
        edm = eventDict['message']
        if not edm:
            if eventDict['isError'] and 'failure' in eventDict:
                f = eventDict['failure']
                for failureType in self._ignoreErrors:
                    r = f.check(failureType)
                    if r:
                        self.debug("Failure of type %r, ignoring" %
                                   failureType)
                        return

                self.log("Failure %r" % f)

                method = debug # tracebacks from errors at debug level
                msg = "A twisted traceback occurred."
                if getCategoryLevel("twisted") < WARN:
                    msg += "  Run with debug level >= 2 to see the traceback."
                # and an additional warning
                warning('twisted', msg)
                text = f.getTraceback()
                safeprintf(sys.stderr, "\nTwisted traceback:\n")
                safeprintf(sys.stderr, text + '\n')
            elif 'format' in eventDict:
                text = eventDict['format'] % eventDict
            else:
                # we don't know how to log this
                return
        else:
            text = ' '.join(map(str, edm))

        fmtDict = {'system': eventDict['system'],
                   'text': text.replace("\n", "\n\t")}
        msgStr = " [%(system)s] %(text)s\n" % fmtDict
        # because msgstr can contain %, as in a backtrace, make sure we
        # don't try to splice it
        method('twisted', msgStr)

    def ignoreErrors(self, *types):
        for failureType in types:
            self._ignoreErrors.append(failureType)

    def clearIgnores(self):
        self._ignoreErrors = []
