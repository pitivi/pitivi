# -*- coding: utf-8 -*-
# -*- Mode: Python; test-case-name: test_log -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.
# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.
# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.
# Headers in this file shall remain intact.
import unittest

from pitivi.utils import loggable as log

__version__ = "$Rev: 7162 $"


class LogTester(log.Loggable):
    logCategory = 'testlog'


class LogFunctionTester(log.Loggable):

    def logFunction(self, fmt, *args):
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

    def testSetDebug(self):
        log.setDebug(":5")
        log.setDebug("*")
        log.setDebug("5")

    # test for adding a log handler

    def testLimitInvisible(self):
        log.setDebug("testlog:%d" % log.INFO)
        log.addLimitedLogHandler(self.handler)

        # log 2 we shouldn't get
        self.tester.log("not visible")
        self.assertFalse(self.category)
        self.assertFalse(self.level)
        self.assertFalse(self.message)

        self.tester.debug("not visible")
        self.assertFalse(self.category)
        self.assertFalse(self.level)
        self.assertFalse(self.message)

    def testLimitedVisible(self):
        log.setDebug("testlog:%d" % log.INFO)
        log.addLimitedLogHandler(self.handler)

        # log 3 we should get
        self.tester.info("visible")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.INFO)
        self.assertEqual(self.message, 'visible')

        self.tester.warning("also visible")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.WARN)
        self.assertEqual(self.message, 'also visible')

    def testFormatStrings(self):
        log.setDebug("testlog:%d" % log.INFO)
        log.addLimitedLogHandler(self.handler)

        self.tester.info("%d %s", 42, 'the answer')
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.INFO)
        self.assertEqual(self.message, '42 the answer')

    def testLimitedError(self):
        log.setDebug("testlog:%d" % log.ERROR)
        log.addLimitedLogHandler(self.handler)

        self.tester.error("error")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.ERROR)
        self.assertEqual(self.message, 'error')

    def testLogHandlerLimitedLevels(self):
        log.setDebug("testlog:%d" % log.INFO)
        log.addLimitedLogHandler(self.handler)

        # now try debug and log again too
        log.setDebug("testlog:%d" % log.LOG)

        self.tester.debug("debug")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.DEBUG)
        self.assertEqual(self.message, 'debug')

        self.tester.log("log")
        self.assertEqual(self.category, 'testlog')
        self.assertEqual(self.level, log.LOG)
        self.assertEqual(self.message, 'log')

    # test that we get all log messages

    def testLogHandler(self):
        log.setDebug("testlog:%d" % log.INFO)
        log.addLogHandler(self.handler)

        self.tester.log("visible")
        self.assertEqual(self.message, 'visible')

        self.tester.warning("also visible")
        self.assertEqual(self.message, 'also visible')


class TestOwnLogHandler(TestWithHandler):

    def setUp(self):
        TestWithHandler.setUp(self)
        self.tester = LogFunctionTester()

    # test if our own log handler correctly mangles the message

    def testOwnLogHandlerLimited(self):
        log.setDebug("testlog:%d" % log.INFO)
        log.addLogHandler(self.handler)

        self.tester.log("visible")
        self.assertEqual(self.message, 'override visible')

    def testLogHandlerAssertion(self):
        self.assertRaises(TypeError, log.addLimitedLogHandler, None)


class TestGetExceptionMessage(unittest.TestCase):

    def func3(self):
        self.func2()

    def func2(self):
        self.func1()

    def func1(self):
        raise TypeError("I am in func1")

    def testLevel2(self):
        try:
            self.func2()
            self.fail("Should not get to this point")
        except TypeError as e:
            self.verifyException(e)

    def testLevel3(self):
        try:
            self.func3()
            self.fail("Should not get to this point")
        except TypeError as e:
            self.verifyException(e)

    def verifyException(self, e):
        message = log.getExceptionMessage(e)
        self.assertTrue("func1()" in message, message)
        self.assertTrue("test_log.py" in message, message)
        self.assertTrue("TypeError" in message, message)


class TestLogSettings(unittest.TestCase):

    def testSet(self):
        old = log.getLogSettings()
        log.setDebug('*:5')
        self.assertNotEqual(old, log.getLogSettings())

        log.setLogSettings(old)
        self.assertEqual(old, log.getLogSettings())


class TestLogNames(unittest.TestCase):

    def testGetLevelNames(self):
        self.assertEqual(['ERROR', 'WARN', 'FIXME', 'INFO', 'DEBUG', 'LOG'],
                         log.getLevelNames())

    def testGetLevelCode(self):
        self.assertEqual(1, log.getLevelInt('ERROR'))
        self.assertEqual(2, log.getLevelInt('WARN'))
        self.assertEqual(3, log.getLevelInt('FIXME'))
        self.assertEqual(4, log.getLevelInt('INFO'))
        self.assertEqual(5, log.getLevelInt('DEBUG'))
        self.assertEqual(6, log.getLevelInt('LOG'))

    def testGetLevelName(self):
        self.assertEqual('ERROR', log.getLevelName(1))
        self.assertEqual('WARN', log.getLevelName(2))
        self.assertEqual('FIXME', log.getLevelName(3))
        self.assertEqual('INFO', log.getLevelName(4))
        self.assertEqual('DEBUG', log.getLevelName(5))
        self.assertEqual('LOG', log.getLevelName(6))
