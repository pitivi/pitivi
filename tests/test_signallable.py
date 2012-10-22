import unittest
from pitivi.utils.signal import Signallable


class myobject(Signallable):

    __signals__ = {
        "signal-oneargs": ["firstarg"],
        "signal-noargs": []}

    def emit_signal_one_args(self, firstarg):
        self.emit("signal-oneargs", firstarg)

    def emit_signal_no_args(self):
        self.emit("signal-noargs")


class mysubobject(myobject):

    __signals__ = {
        "subobject-noargs": None}

    def emit_sub_signal_no_args(self):
        self.emit("subobject-noargs")


def function_cb(testcase):
    testcase.fail("this should not be reached")


class TestSignalisation(unittest.TestCase):
    """
    Test the proper behaviour of pitivi.signalinterface.Signallable
    """

    def setUp(self):
        self.object = myobject()
        self.subobject = mysubobject()
        # internal checks to make sure these objects are clean
        self.assertEquals(hasattr(self.object, "_signal_group"),
                          False)
        self.assertEquals(hasattr(self.subobject, "_signal_group"),
                          False)

        # To detect if signals were triggered
        self.s_oneargs_triggered = 0
        self.s_noargs_triggered = 0
        self.s_subnoargs_triggered = 0

        # values sent by signal
        self.signal_oneargs_firstarg = None
        self.signal_oneargs_signaller = None
        self.signal_oneargs_args = None
        self.signal_oneargs_kwargs = None

        self.signal_noargs_signaller = None
        self.signal_noargs_args = None
        self.signal_noargs_kwargs = None

        self.signal_subnoargs_signaller = None
        self.signal_subnoargs_args = None
        self.signal_subnoargs_kwargs = None

    # default callbacks to be used
    def _cb_oneargs(self, signaller, firstarg=None, *args, **kwargs):
        self.s_oneargs_triggered += 1
        self.signal_oneargs_signaller = signaller
        self.signal_oneargs_firstarg = firstarg
        self.signal_oneargs_args = args
        self.signal_oneargs_kwargs = kwargs

    def _cb_noargs(self, signaller, *args, **kwargs):
        self.s_noargs_triggered += 1
        self.signal_noargs_signaller = signaller
        self.signal_noargs_args = args
        self.signal_noargs_kwargs = kwargs

    def _cb_subnoargs(self, signaller, *args, **kwargs):
        self.s_subnoargs_triggered += 1
        self.signal_suboargs_signaller = signaller
        self.signal_subnoargs_args = args
        self.signal_subnoargs_kwargs = kwargs

    def test01_get_signals(self):
        self.assertEquals(self.object.get_signals(),
                          myobject.__signals__)
        expected = dict(myobject.__signals__)
        expected.update(mysubobject.__signals__)
        self.assertEquals(self.subobject.get_signals(),
                          expected)

    def test02_connect(self):
        def my_cb1(self, firstarg=None):
            pass
        # This should return a uuid
        self.assert_(self.object.connect("signal-oneargs",
                                         my_cb1))

        # you can't connect to unexisting signals !
        self.assertRaises(Exception,
                          self.object.connect,
                          "this-signal-doesn't-exist",
                          my_cb1)

        # you must give a callable as the cb argument
        self.assertRaises(Exception,
                          self.object.connect,
                          "signal-oneargs",
                          5)

    def test03_disconnect(self):
        def my_cb1(self, firstarg=None):
            pass
        sigid = self.object.connect("signal-oneargs", my_cb1)
        self.assert_(sigid)
        self.object.disconnect(sigid)

        # disconnecting something already disconnected should
        # trigger an exception
        self.assertRaises(Exception,
                          self.object.disconnect,
                          sigid)

        # disconnecting a unexisting signal should trigger
        # an exception
        self.assertRaises(Exception,
                          self.object.disconnect,
                          42)

    def test_disconnect_by_function_method(self):
        def my_cb1(self, firstarg):
            self.fail("this should not be called")

        sigid = self.object.connect("signal-oneargs", my_cb1)
        self.object.disconnect_by_function(my_cb1)
        # disconnecting something already disconnected should
        # trigger an exception
        self.assertRaises(Exception,
                          self.object.disconnect,
                          sigid)

        self.object.emit("signal-oneargs", 42)

    def test_disconnect_by_function(self):
        sigid = self.object.connect("signal-oneargs", function_cb, self)
        self.object.disconnect_by_function(function_cb)
        # disconnecting something already disconnected should
        # trigger an exception
        self.assertRaises(Exception,
                          self.object.disconnect,
                          sigid)

        # disconnecting a disconnected function should raise
        self.assertRaises(Exception,
                          self.object.disconnect_by_function,
                          function_cb)

        self.object.emit("signal-oneargs", 42)

    def test_disconnect_while_handling(self):
        # When the handler being called disconnects itself,
        # the next handler must not be skipped.

        def firstCb(unused_object):
            self.object.disconnect_by_function(firstCb)

        def secondCb(unused_object):
            self.called = True

        self.called = False
        self.object.connect("signal-oneargs", firstCb)
        self.object.connect("signal-oneargs", secondCb)
        self.object.emit("signal-oneargs")
        self.assertTrue(self.called)
        del self.called

    def test_disconnect_following_handler_while_handling(self):
        # When the handler being called disconnects a following handler,
        # the following handler must be skipped.

        def firstCb(unused_object):
            self.object.disconnect_by_function(secondCb)

        def secondCb(unused_object):
            self.called = True

        self.called = False
        self.object.connect("signal-oneargs", firstCb)
        self.object.connect("signal-oneargs", secondCb)
        self.object.emit("signal-oneargs")
        self.assertFalse(self.called)
        del self.called

    def test04_emit01(self):
        # signal: no arguments
        # connect: no arguments
        noargsid = self.object.connect("signal-noargs",
                                       self._cb_noargs)
        self.assert_(noargsid)
        self.object.emit_signal_no_args()
        self.assertEquals(self.s_noargs_triggered, 1)
        self.assertEquals(self.signal_noargs_args, ())
        self.assertEquals(self.signal_noargs_signaller, self.object)
        self.assertEquals(self.signal_noargs_kwargs, {})

        # disconnect
        self.object.disconnect(noargsid)

        # let's make sure we're not called anymore
        self.s_noargs_triggered = 0
        self.object.emit_signal_no_args()
        self.assertEquals(self.s_noargs_triggered, 0)

    def test04_emit02(self):
        # signal: no arguments
        # connect: extra arguments
        noargsid = self.object.connect("signal-noargs",
                                       self._cb_noargs,
                                       1, 2, 3,
                                       myvalue=42)
        self.assert_(noargsid)
        self.object.emit_signal_no_args()
        self.assertEquals(self.s_noargs_triggered, 1)
        self.assertEquals(self.signal_noargs_args, (1, 2, 3))
        self.assertEquals(self.signal_noargs_signaller, self.object)
        self.assertEquals(self.signal_noargs_kwargs, {"myvalue": 42})

    def test04_emit03(self):
        # signal: named argument
        # connect: no arguments
        oneargsigid = self.object.connect("signal-oneargs", self._cb_oneargs)
        self.assert_(oneargsigid)
        self.object.emit_signal_one_args(firstarg="yep")
        self.assertEquals(self.s_oneargs_triggered, 1)
        self.assertEquals(self.signal_oneargs_signaller, self.object)
        self.assertEquals(self.signal_oneargs_firstarg, "yep")
        self.assertEquals(self.signal_oneargs_args, ())
        self.assertEquals(self.signal_oneargs_kwargs, {})

    def test04_emit04(self):
        # signal: named argument
        # connect: extra arguments
        oneargsigid = self.object.connect("signal-oneargs", self._cb_oneargs,
                                          1, 2, 3, myvalue=42)
        self.assert_(oneargsigid)
        self.object.emit_signal_one_args(firstarg="yep")
        self.assertEquals(self.s_oneargs_triggered, 1)
        self.assertEquals(self.signal_oneargs_firstarg, "yep")
        self.assertEquals(self.signal_oneargs_signaller, self.object)
        self.assertEquals(self.signal_oneargs_args, (1, 2, 3))
        self.assertEquals(self.signal_oneargs_kwargs, {"myvalue": 42})

    def test05_subclass_emit01(self):
        # making sure a subclass can emit the parent classes
        # signal
        noargsid = self.subobject.connect("signal-noargs",
                                          self._cb_noargs,
                                          1, 2, 3,
                                          myvalue=42)
        self.assert_(noargsid)
        self.subobject.emit_signal_no_args()
        self.assertEquals(self.s_noargs_triggered, 1)
        self.assertEquals(self.signal_noargs_signaller, self.subobject)
        self.assertEquals(self.signal_noargs_args, (1, 2, 3))
        self.assertEquals(self.signal_noargs_kwargs, {"myvalue": 42})

    def test06_multiple_emissions(self):
        # connect two handlers to one signal
        noargsid1 = self.object.connect("signal-noargs",
                                        self._cb_noargs,
                                        1, 2, 3,
                                        myvalue=42)
        self.assert_(noargsid1)
        noargsid2 = self.object.connect("signal-noargs",
                                        self._cb_noargs,
                                        1, 2, 3,
                                        myvalue=42)
        self.assert_(noargsid2)

        # emit the signal...
        self.object.emit_signal_no_args()
        # ...which should have called all the handlers
        self.assertEquals(self.s_noargs_triggered, 2)
        self.assertEquals(self.signal_noargs_args, (1, 2, 3))
        self.assertEquals(self.signal_noargs_kwargs, {"myvalue": 42})

        self.object.disconnect(noargsid1)
        self.object.disconnect(noargsid2)

        self.object.emit_signal_no_args()
        self.assertEquals(self.s_noargs_triggered, 2)

    #FIXME : test return values on emission !
