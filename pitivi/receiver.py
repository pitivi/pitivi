def handler(attribute, signal):
    """Registers a method in a subclass of receiver as a handler"""
    def decorator(method):
        method.__sender__ = attribute
        method.__signal__ = signal
        return method
    return decorator

def set_sender(attrname):

    def inner(self, new_instance):
        # get the attribute
        attr = self.__senders__[attrname]
        if attr:
            # disconnect all the previous signal handlers
            for sigid in self.__sigids__[attrname].itervalues():
                attr.disconnect(sigid)
            setattr(self, attr, None)
        if new_instance:
            # save the instance
            self.__senders__[attrname]
            for signal, handler in self.__handlers__[attrname].iteritems():
                self.__sigids__[attrname][signal] = new_instance.connect(signal, 
                    handler)
    inner.__name__ = "set_" + attrname
    return inner

def get_sender(attrname):
    def inner(self):
        return self.__senders__[attrname]
    inner.__name__ = "get_" + attrname
    return inner

class ReceiverMeta(type):

    def __new__(meta, classname, bases, attributes):
        handlers = {}
        out = dict(attributes)
        for attrname, value in attributes.iteritems():
            if hasattr(value, "__sender__") and hasattr(value, "__signal__"):
                sender = value.__sender__
                signal = value.__signal__
                handlers.setdefault(sender, {})[signal] = value
                out[sender] = property(get_sender(sender),
                    set_sender(sender))
        out["__handlers__"] = handlers
        out["__sigids__"] = {}
        return type.__new__(meta, classname, bases, out)

class Receiver(object):

    """Automatically connects appropriate signal handler methods to attributes
    designated as "senders". Subclasses simply declare signal handler methods
    with the @receiver.handler(<attribute>, <signal>)"""

    __metaclass__ = ReceiverMeta
