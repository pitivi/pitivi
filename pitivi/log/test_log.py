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

from twisted.trial import unittest

import log

__version__ = "$Rev: 7162 $"


class LogTester(log.Loggable):
    logCategory = 'testlog'


class LogFunctionTester(log.Loggable):

    def logFunction(self, format, *args):
        return (("override " + format), ) + args[1:]


class TestLog(unittest.TestCase):

    def setUp(self):
        self.category = self.level = self.message = None
        self.tester = LogTester()
        # we want to remove the default handler so it doesn't show up stuff
        log.reset()

    # just test for parsing semi- or non-valid FLU_DEBUG variables

    def testSetDebug(self):
        log.setDebug(":5")
        log.setDebug("*")
        log.setDebug("5")

    # test for adding a log handler

    def handler(self, level, object, category, file, line, message):
        self.level = level
        self.object = object
        self.category = category
        self.file = file
        self.line = line
        self.message = message

    def testLimitInvisible(self):
        log.setDebug("testlog:3")
        log.addLimitedLogHandler(self.handler)

        # log 2 we shouldn't get
        self.tester.log("not visible")
        assert not self.category
        assert not self.level
        assert not self.message

        self.tester.debug("not visible")
        assert not self.category
        assert not self.level
        assert not self.message

    def testLimitedVisible(self):
        log.setDebug("testlog:3")
        log.addLimitedLogHandler(self.handler)

        # log 3 we should get
        self.tester.info("visible")
        assert self.category == 'testlog'
        assert self.level == log.INFO
        assert self.message == 'visible'

        self.tester.warning("also visible")
        assert self.category == 'testlog'
        assert self.level == log.WARN
        assert self.message == 'also visible'

    def testFormatStrings(self):
        log.setDebug("testlog:3")
        log.addLimitedLogHandler(self.handler)

        self.tester.info("%d %s", 42, 'the answer')
        assert self.category == 'testlog'
        assert self.level == log.INFO
        assert self.message == '42 the answer'

    def testLimitedError(self):
        log.setDebug("testlog:3")
        log.addLimitedLogHandler(self.handler)

        self.assertRaises(SystemExit, self.tester.error, "error")
        assert self.category == 'testlog'
        assert self.level == log.ERROR
        assert self.message == 'error'

    def testLogHandlerLimitedLevels(self):
        log.setDebug("testlog:3")
        log.addLimitedLogHandler(self.handler)

        # now try debug and log again too
        log.setDebug("testlog:5")

        self.tester.debug("debug")
        assert self.category == 'testlog'
        assert self.level == log.DEBUG
        assert self.message == 'debug'

        self.tester.log("log")
        assert self.category == 'testlog'
        assert self.level == log.LOG
        assert self.message == 'log'

    # test that we get all log messages

    def testLogHandler(self):
        log.setDebug("testlog:3")
        log.addLogHandler(self.handler)

        self.tester.log("visible")
        assert self.message == 'visible'

        self.tester.warning("also visible")
        assert self.message == 'also visible'


class TestOwnLogHandler(unittest.TestCase):

    def setUp(self):
        self.category = self.level = self.message = None
        self.tester = LogFunctionTester()

    def handler(self, level, object, category, file, line, message):
        self.level = level
        self.object = object
        self.category = category
        self.file = file
        self.line = line
        self.message = message

    # test if our own log handler correctly mangles the message

    def testOwnLogHandlerLimited(self):
        log.setDebug("testlog:3")
        log.addLogHandler(self.handler)

        self.tester.log("visible")
        assert self.message == 'override visible'

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
            self.fail()
        except TypeError, e:
            self.verifyException(e)

    def testLevel3(self):
        try:
            self.func3()
            self.fail()
        except TypeError, e:
            self.verifyException(e)

    def verifyException(self, e):
        message = log.getExceptionMessage(e)
        self.failUnless("func1()" in message)
        self.failUnless("test_log.py" in message)
        self.failUnless("TypeError" in message)


class TestLogSettings(unittest.TestCase):

    def testSet(self):
        old = log.getLogSettings()
        log.setDebug('*:5')
        self.assertNotEquals(old, log.getLogSettings())

        log.setLogSettings(old)
        self.assertEquals(old, log.getLogSettings())


class TestWriteMark(unittest.TestCase):

    def handler(self, level, object, category, file, line, message):
        self.level = level
        self.object = object
        self.category = category
        self.file = file
        self.line = line
        self.message = message

    def testWriteMarkInDebug(self):
        loggable = log.Loggable()
        log.setDebug("4")
        log.addLogHandler(self.handler)
        marker = 'test'
        loggable.writeMarker(marker, log.DEBUG)
        self.assertEquals(self.message, marker)

    def testWriteMarkInWarn(self):
        loggable = log.Loggable()
        log.setDebug("2")
        log.addLogHandler(self.handler)
        marker = 'test'
        loggable.writeMarker(marker, log.WARN)
        self.assertEquals(self.message, marker)

    def testWriteMarkInInfo(self):
        loggable = log.Loggable()
        log.setDebug("3")
        log.addLogHandler(self.handler)
        marker = 'test'
        loggable.writeMarker(marker, log.INFO)
        self.assertEquals(self.message, marker)

    def testWriteMarkInLog(self):
        loggable = log.Loggable()
        log.setDebug("5")
        log.addLogHandler(self.handler)
        marker = 'test'
        loggable.writeMarker(marker, log.LOG)
        self.assertEquals(self.message, marker)

    def testWriteMarkInError(self):
        loggable = log.Loggable()
        log.setDebug("4")
        log.addLogHandler(self.handler)
        marker = 'test'
        self.assertRaises(SystemExit, loggable.writeMarker, marker, log.ERROR)
        self.assertEquals(self.message, marker)


class TestLogNames(unittest.TestCase):

    def testGetLevelNames(self):
        self.assertEquals(['ERROR', 'WARN', 'INFO', 'DEBUG', 'LOG'],
                          log.getLevelNames())

    def testGetLevelCode(self):
        self.assertEquals(1, log.getLevelInt('ERROR'))
        self.assertEquals(2, log.getLevelInt('WARN'))
        self.assertEquals(3, log.getLevelInt('INFO'))
        self.assertEquals(4, log.getLevelInt('DEBUG'))
        self.assertEquals(5, log.getLevelInt('LOG'))

    def testGetLevelName(self):
        self.assertEquals('ERROR', log.getLevelName(1))
        self.assertEquals('WARN', log.getLevelName(2))
        self.assertEquals('INFO', log.getLevelName(3))
        self.assertEquals('DEBUG', log.getLevelName(4))
        self.assertEquals('LOG', log.getLevelName(5))

if __name__ == '__main__':
    unittest.main()
