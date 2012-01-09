#!/usr/bin/env python
#
#       signal.py
#
# Copyright (c) 2006, Richard Boulton <richard@tartarus.org>
# Copyright (C) 2012 Thibault Saunier <thibaul.saunier@collabora.com>
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.

"""
    Helpers classes to handle signals
"""

from random import randint


class SignalGroup:
    """
    A group of signals, which can be disconnected easily.

    Used to make it easy to keep signals attached to the current project.
    """
    def __init__(self):
        self.signal_handler_ids = {}

    def connect(self, object, signal, sid, callback, *args):
        """Connect a signal.

         _ `object` is the object which defines the signal.
         _ `signal` is the name of the signal to connect to.
         _ `id` is a unique (within this SignalGroup) identifer for the signal to
           connect to.  If this is None, the value of `signal` will be used
           instead.
         _ `callback` is the callable to call on the signal.
         _ `args` are any extra arguments to pass to the callback.

        If there is already a connected signal in the group with the specified
        unique identifier, this signal will first be disconnected.

        """
        if sid is None:
            sid = signal

        if sid in self.signal_handler_ids:
            old_object, handler_id = self.signal_handler_ids[sid]
            old_object.disconnect(handler_id)
            del self.signal_handler_ids[sid]

        handler_id = object.connect(signal, callback, *args)
        self.signal_handler_ids[id] = (object, handler_id)

    def disconnect(self, sid):
        """Disconnect the signal with the specified unique identifier.

        If there is no such signal, this returns without having any effect.

        """
        if id in self.signal_handler_ids:
            old_object, handler_id = self.signal_handler_ids.pop(sid)
            old_object.disconnect(handler_id)

    def disconnectAll(self):
        """Disconnect all signals in the group.

        """
        for old_object, handler_id in self.signal_handler_ids.itervalues():
            old_object.disconnect(handler_id)
        self.signal_handler_ids = {}

    def disconnectForObject(self, obj):
        """
        Disconnects all signal in the group connect on the given object
        """
        assert obj != None
        objids = [sid for sid in self.signal_handler_ids.keys() if self.signal_handler_ids[sid][0] == obj]
        for sid in objids:
            old_object, handler_id = self.signal_handler_ids.pop(id)
            old_object.disconnect(handler_id)


class Signallable(object):
    """
    Signallable interface

    @cvar __signals__: The signals the class can emit as a dictionnary of
     - Key : signal name
     - Value : List of arguments (can be None)
    @type __signals__: Dictionnary of L{str} : List of L{str}
    """

    class SignalGroup:
        # internal
        def __init__(self, signallable):
            self.siglist = signallable.get_signals()
            # self.ids is a dictionnary of
            # key: signal name (string)
            # value: list of:
            #    (callback (callable),
            #     args (list),
            #     kwargs (dictionnary))
            self.ids = {}
            self.callback_ids = {}
            # self.handlers is a dictionnary of callback ids per
            # signals.
            self.handlers = {}
            for signame in self.siglist.keys():
                self.handlers[signame] = []

        def connect(self, signame, cb, args, kwargs):
            """ connect """
            # get a unique id
            if not signame in self.handlers.keys():
                raise Exception("Signal %s is not one of %s" % (signame,
                ",\n\t".join(self.handlers.keys())))
            if not callable(cb):
                raise Exception("Provided callable '%r' is not callable" % cb)

            uuid = randint(0, 2 ** 64)
            while uuid in self.ids:
                uuid = randint(0, 2 ** 64)

            self.ids[uuid] = (cb, args, kwargs)
            self.callback_ids.setdefault(cb, []).append(uuid)
            self.handlers[signame].append(uuid)
            return uuid

        def disconnect(self, sigid):
            """ disconnect """
            try:
                cb = self.ids[sigid][0]
                del self.ids[sigid]
            except KeyError:
                raise Exception("unknown signal id")

            for lists in self.handlers.itervalues():
                try:
                    lists.remove(sigid)
                except ValueError:
                    continue

                self.callback_ids.get(cb, []).remove(sigid)

        def disconnect_by_function(self, function):
            try:
                sig_ids = self.callback_ids[function]
            except KeyError:
                raise Exception("function is not a known callback")

            for sigid in list(sig_ids):
                self.disconnect(sigid)

            del self.callback_ids[function]

        def emit(self, signame, *args, **kwargs):
            """ emit """
            # emits the signal,
            # will concatenate the given args/kwargs with
            # the ones supplied in .connect()
            res = None
            # Create a copy because if the handler being executed disconnects,
            # the next handler will not be called.
            signame_handlers = list(self.handlers[signame])
            for sigid in signame_handlers:
                if sigid not in self.handlers[signame]:
                    # The handler has been disconnected in the meantime!
                    continue
                # cb: callable
                cb, orar, kwar = self.ids[sigid]
                ar = args[:] + orar
                kw = kwargs.copy()
                kw.update(kwar)
                res = cb(*ar, **kw)
            return res

    # key : name (string)
    # value : signature (list of any strings)
    __signals__ = {}

    def emit(self, signame, *args, **kwargs):
        """
        Emit the given signal.

        The provided kwargs should contain *at-least* the arguments declared
        in the signal declaration.

        The object emitting the signal will be provided as the first
        argument of the callback

        @return: The first non-None return value given by the callbacks if they
        provide any non-None return value.
        """
        if not hasattr(self, "_signal_group"):
            # if there's no SignalGroup, that means nothing is
            # connected
            return None
        return self._signal_group.emit(signame, self,
                                       *args, **kwargs)

    def connect(self, signame, cb, *args, **kwargs):
        """
        Connect a callback (with optional arguments) to the given
        signal.

        * signame : the name of the signal
        * cb : the callback (needs to be a callable)
        * args/kwargs : (optional) arguments
        """
        if not hasattr(self, "_signal_group"):
            self._signal_group = self.SignalGroup(self)

        return self._signal_group.connect(signame,
                                           cb, args, kwargs)

    def disconnect(self, sigid):
        """
        Disconnect signal using give signal id
        """
        if not hasattr(self, "_signal_group"):
            raise Exception("This class doesn't have any signals !")

        self._signal_group.disconnect(sigid)

    def disconnect_by_function(self, function):
        """
        Disconnect signal using give signal id
        """
        if not hasattr(self, "_signal_group"):
            raise Exception("This class doesn't have any signals !")

        self._signal_group.disconnect_by_function(function)

    disconnect_by_func = disconnect_by_function

    @classmethod
    def get_signals(cls):
        """ Get the full list of signals implemented by this class """
        sigs = {}
        for cla in cls.mro():
            if "__signals__" in cla.__dict__:
                sigs.update(cla.__signals__)
            if cla == Signallable:
                break
        return sigs
