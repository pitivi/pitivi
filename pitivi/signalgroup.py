# PiTiVi , Non-linear video editor
#
#       pitivi/ui/signalgroup.py
#
# Copyright (c) 2006, Richard Boulton <richard@tartarus.org>
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

"""
A group of signals, which can be disconnected easily.

Used to make it easy to keep signals attached to the current project.
"""

class SignalGroup:
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
