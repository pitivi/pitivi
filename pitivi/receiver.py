from signalinterface import Signallable
from types import MethodType

class receiver(object):

    """A descriptor which wrapps signal connect and disconnect for a single
    object (the sender). Signal handlers may be registered with the
    add_handler() method, after which point the handler will be automatically
    connected when the property value is set. Prior to connecting new signal
    handlers, old handlers are disconnected."""

    def __init__(self):
        object.__init__(self)
        self.sender = None
        self.handlers = {}
        self.sigids = {}
        self._first_connect = True

    def __get__(self, instance, blah):
        return self.sender

    def __set__(self, instance, value):
        # explicitly check for None, because sometimes valid instances have a
        # False truth value. We don't want to forget to disconnect any signals,
        # and at the same time we don't want to fail to connect a valid
        # instance of, say, an empty container.
        if self.sender != None:
            for id in self.sigids.itervalues():
                self.sender.disconnect(id)
            self.sender = None
            self.sigids = {}
        if value != None:
            for sig, hdlr in self.handlers.iteritems():
                value.connect(sig, MethodType(hdlr, instance))
            self.sender = value

    def __del__(self, instance):
        raise NotImplementedError

    def add_handler(self, signal, handler):
        self.handlers[signal] = handler

def handler(property, signal):

    """A decorator which registers a given function as a signal handler for
    the signal <signal> of object <property>. Property should be a receiver
    object created with receiver().""" 

    def __handler__(func):
        property.add_handler(signal, func)
        return func

    return __handler__
