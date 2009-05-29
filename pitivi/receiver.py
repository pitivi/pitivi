from types import MethodType

class _receiver_data(object):

    sender = None
    sigids = None

class receiver(object):

    """A descriptor which wrapps signal connect and disconnect for a single
    object (the sender). Signal handlers may be registered with the
    add_handler() method, after which point the handler will be automatically
    connected when the property value is set. Prior to connecting new signal
    handlers, old handlers are disconnected."""

    def __init__(self, setter=None):
        object.__init__(self)
        self.handlers = {}
        self.setter = setter

    def __get__(self, instance, blah):
        if hasattr(instance, "_receiver_data"):
            return instance._receiver_data[self].sender
        return None

    def __set__(self, instance, value):
        if not hasattr(instance, "_receiver_data"):
            instance._receiver_data = {}
        if not instance._receiver_data.has_key(self):
            instance._receiver_data[self] = _receiver_data()
            instance._receiver_data[self].sigids = {}
        rd = instance._receiver_data[self]

        # explicitly check for None, because sometimes valid instances have a
        # False truth value. We don't want to forget to disconnect any signals,
        # and at the same time we don't want to fail to connect a valid
        # instance of, say, an empty container.
        if rd.sender != None:
            for sid in rd.sigids.itervalues():
                instance._receiver_data[self].sender.disconnect(sid)
            rd.sender = None
            rd.sigids = {}
        if not (value is None):
            for sig, hdlr in self.handlers.iteritems():
                rd.sigids[sig] = value.connect(sig, MethodType(hdlr,
                    instance))
            rd.sender = value
        if self.setter:
            self.setter(instance)

    def add_handler(self, signal, hdlr):
        self.handlers[signal] = hdlr

def handler(prop, signal):

    """A decorator which registers a given function as a signal handler for
    the signal <signal> of object <property>. Property should be a receiver
    object created with receiver()."""

    def __handler__(func):
        prop.add_handler(signal, func)
        return func

    return __handler__
