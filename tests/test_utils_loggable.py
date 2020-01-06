# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
#
# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
import unittest

from pitivi.utils import loggable as log


class LogTester(log.Loggable):
    log_category = 'testlog'


class LogFunctionTester(log.Loggable):

    def log_function(self, fmt, *args):
        return (("override " + fmt), ) + args[1:]


class TestWithHandler(unittest.TestCase):

    def setUp(self):
        self.level = None
        self.object = None
        self.category = None
        self.file = None
        self.line = None
        self.message = None

        # we want to remove the default handler so it doesn't show up stuff
        log.reset()

    def handler(self, level, obj, category, file, line, message):
        self.level = level
        self.object = obj
        self.category = category
        self.file = file
        self.line = line
        self.message = message.split(' ', 1)[1]


class TestLog(TestWithHandler):

    def setUp(self):
        TestWithHandler.setUp(self)
        self.tester = LogTester()

    # just test for parsing semi- or non-valid FLU_DEBUG variables

    def test_set_debug(self):
        log.set_debug(":5")
        log.set_debug("*")
        log.set_debug("5")

    # test for adding a log handler

    def test_limit_invisible(self):
        log.set_debug("testlog:%d" % log.INFO)
        log.add_limited_log_handler(self.handler)

        # log 2 we shouldn't get
        self.tester.log("not visible")
        self.assertFalse(self.category)
        self.assertFalse(self.level)
        self.assertFalse(self.message)

        self.tester.debug("not visible")
        self.assertFalse(self.category)
        self.assertFalse(self.level)
        self.assertFalse(self.message)

    def test_limited_visible(self):
        log.set_debug("testlog:%d" % log.INFO)
        log.add_limited_log_handler(self.handler)

        # log 3 we should get
        self.tester.info("visible")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.INFO)
        self.assertEqual(self.message, 'visible')

        self.tester.warning("also visible")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.WARN)
        self.assertEqual(self.message, 'also visible')

    def test_format_strings(self):
        log.set_debug("testlog:%d" % log.INFO)
        log.add_limited_log_handler(self.handler)

        self.tester.info("%d %s", 42, 'the answer')
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.INFO)
        self.assertEqual(self.message, '42 the answer')

    def test_limited_error(self):
        log.set_debug("testlog:%d" % log.ERROR)
        log.add_limited_log_handler(self.handler)

        self.tester.error("error")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.ERROR)
        self.assertEqual(self.message, 'error')

    def test_log_handler_limited_levels(self):
        log.set_debug("testlog:%d" % log.INFO)
        log.add_limited_log_handler(self.handler)

        # now try debug and log again too
        log.set_debug("testlog:%d" % log.LOG)

        self.tester.debug("debug")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.DEBUG)
        self.assertEqual(self.message, 'debug')

        self.tester.log("log")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.LOG)
        self.assertEqual(self.message, 'log')

    # test that we get all log messages

    def test_log_handler(self):
        log.set_debug("testlog:%d" % log.INFO)
        log.add_log_handler(self.handler)

        self.tester.log("visible")
        self.assertEqual(self.message, 'visible')

        self.tester.warning("also visible")
        self.assertEqual(self.message, 'also visible')


class TestOwnLogHandler(TestWithHandler):

    def setUp(self):
        TestWithHandler.setUp(self)
        self.tester = LogFunctionTester()

    def test_own_log_handler_limited(self):
        """Checks our own log handler correctly mangles the message."""
        log.set_debug("testlog:%d" % log.INFO)
        log.add_log_handler(self.handler)

        self.tester.log("visible")
        self.assertEqual(self.message, 'override visible')

    def test_log_handler_assertion(self):
        self.assertRaises(TypeError, log.add_limited_log_handler, None)


class TestGetExceptionMessage(unittest.TestCase):

    def func3(self):
        self.func2()

    def func2(self):
        self.func1()

    def func1(self):
        raise TypeError("I am in func1")

    def test_level2(self):
        try:
            self.func2()
            self.fail("Should not get to this point")
        except TypeError as e:
            self.verify_exception(e)

    def test_level3(self):
        try:
            self.func3()
            self.fail("Should not get to this point")
        except TypeError as e:
            self.verify_exception(e)

    def verify_exception(self, e):
        message = log.get_exception_message(e)
        self.assertTrue("func1()" in message, message)
        self.assertTrue("test_utils_loggable.py" in message, message)
        self.assertTrue("TypeError" in message, message)


class TestLogSettings(unittest.TestCase):

    def test_set(self):
        old = log.get_log_settings()
        log.set_debug('*:5')
        self.assertNotEqual(old, log.get_log_settings())

        log.set_log_settings(old)
        self.assertEqual(old, log.get_log_settings())


class TestLogNames(unittest.TestCase):

    def test_get_level_code(self):
        self.assertEqual(1, log.get_level_int('ERROR'))
        self.assertEqual(2, log.get_level_int('WARN'))
        self.assertEqual(3, log.get_level_int('FIXME'))
        self.assertEqual(4, log.get_level_int('INFO'))
        self.assertEqual(5, log.get_level_int('DEBUG'))
        self.assertEqual(6, log.get_level_int('LOG'))

    def test_get_level_name(self):
        self.assertEqual('ERROR', log.get_level_name(1))
        self.assertEqual('WARN', log.get_level_name(2))
        self.assertEqual('FIXME', log.get_level_name(3))
        self.assertEqual('INFO', log.get_level_name(4))
        self.assertEqual('DEBUG', log.get_level_name(5))
        self.assertEqual('LOG', log.get_level_name(6))
