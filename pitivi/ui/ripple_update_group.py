# PiTiVi , Non-linear video editor
#
#       ui/projectsettings.py
#
# Copyright (c) 2010, Brandon Lewis <brandon.lewis@collabora.co.uk>
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


class RippleUpdateGroup(object):

    """Allows for event-driven spreadsheet-like ripple updates without
    infinite loops.

    This class allows you to express an event-driven sequence of operations in
    terms of a directed graph. It is not a constraint solver: The goal is to
    allow the programmer to reduce complex logic to a set of simple functions
    and predicates combined declaratively.

    Events propagate through the graph in breadth first order. During an
    update cycle, each vertex is visited only once, so cycles can exist in the
    graph without creating infinite loops.

    Each vertex represents a unique object. The following may also be
    associated with a vertex:

        - the name of a signal on the object. when this signal fires, it
          triggers an update cycle beginning at this object. during an update
          cycle, further signal emissions from this or any other vertex will
          be ignored to prevent infinite loops.

        - an update function, which will be called when the vertex is visited
          as part of an update cycle. It will not be called when the object
          emits a signal.

        - zero or more user-specified arguments, passed to the
          update_function.

    An edge between two verticies represents a sequence of operations. If an
    edge exists from object A to object B, then whenever A is perfomred, B
    should be performed too -- unless it has already been visited as part of
    this update cycle.

    In addition to a a pair of objects, each edge also has the following
    assoicated with it:

        - a predicate function. called during an update cycle when this edge
          is reached, and before any other processing is done. If this
          function returns false, it will be as if this edge otherwise did not
          exist.

        - a function to be called whenver the edge is visited during an update
          cycle. this function will not be called if the condition function
          returns False."""

    def __init__(self, *widgets):
        self.arcs = {}
        self.update_funcs = {}
        self.ignore_new_signals = False
        for widget in widgets:
            self.add_vertex(*widget)

    def add_vertex(self, widget, update_func=None, signal=None, *args):
        if signal:
            widget.connect(signal, self._widget_value_changed)
        self.update_funcs[widget] = (update_func, args)
        self.arcs[widget] = []

    def add_edge(self, a, b, predicate = None,
        edge_func = None):
        self.arcs[a].append((b, predicate, edge_func))

    def add_bi_edge(self, a, b, predicate = None,
        edge_func = None):
        self.add_edge(a, b, predicate, edge_func)
        self.add_edge(b, a, predicate, edge_func)

    def _widget_value_changed(self, widget, *unused):
        if self.ignore_new_signals:
            return

        self.ignore_new_signals = True
        self._updateValues(widget)
        self.ignore_new_signals = False

    def _updateValues(self, widget):
        queue = [(widget, v) for v in self.arcs[widget]]
        visited = set([widget])
        while queue:
            parent, (cur, predicate, edge_func) = queue.pop(0)

            # ignore nodes we've seen
            if cur in visited:
                continue

            # check whether conditions permit this edge to be followed
            if predicate and (not predicate()):
                continue

            # if so call the edge function
            if edge_func:
                edge_func()

            # visit node
            update_func, args = self.update_funcs[cur]
            if update_func:
                update_func(parent, cur, *args)
            visited.add(cur)

            # enqueue children
            queue.extend(((cur, v) for v in self.arcs[cur]))
