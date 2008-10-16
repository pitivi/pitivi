# PiTiVi , Non-linear video editor
#
#       ui/glade.py
#
# Copyright (C) 2004,2005 Fluendo, S.L. (www.fluendo.com). All rights reserved.
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
#

"""
Classes for easily using glade widgets
"""

import os
import sys

import gtk
from gtk.glade import XML, set_custom_handler

# proc := module1.module2.moduleN.proc1().maybe_another_proc()
#  -> eval proc1().maybe_another_proc() in module1.module2.moduleN
def flumotion_glade_custom_handler(unused_xml, proc, name, *unused_args):
    def takewhile(proc, l):
        ret = []
        while l and proc(l[0]):
            ret.append(l[0])
            l.remove(l[0])
        return ret

    def parse_proc(proc):
        parts = proc.split('.')
        assert len(parts) > 1
        modparts = takewhile(str.isalnum, parts)
        assert modparts and parts
        return '.'.join(modparts), '.'.join(parts)

    module, code = parse_proc(proc)
    try:
        __import__(module)
    except Exception, e:
        raise RuntimeError('Failed to load module %s: %s' % (module, e))

    try:
        w = eval(code, sys.modules[module].__dict__)
    except Exception, e:
        raise RuntimeError('Failed call %s in module %s: %s'
                           % (code, module, e))
    w.set_name(name)
    w.show()
    return w
set_custom_handler(flumotion_glade_custom_handler)


class GladeWidget(gtk.VBox):
    '''
    Base class for composite widgets backed by glade interface definitions.

    Example:
    class MyWidget(GladeWidget):
        glade_file = 'my_glade_file.glade'
        ...

    Remember to chain up if you customize __init__().
    '''

    glade_dir = os.path.dirname(os.path.abspath(__file__))
    glade_file = None
    glade_typedict = None

    def __init__(self):
        gtk.VBox.__init__(self)
        try:
            assert self.glade_file
            filepath = os.path.join(self.glade_dir, self.glade_file)
            if self.glade_typedict:
                wtree = XML(filepath, typedict=self.glade_typedict, domain='pitivi')
            else:
                # pygtk 2.4 doesn't like typedict={} ?
                wtree = XML(filepath, domain='pitivi')
        except RuntimeError, e:
            raise RuntimeError('Failed to load file %s from directory %s: %s'
                               % (self.glade_file, self.glade_dir, e))

        win = None
        for widget in wtree.get_widget_prefix(''):
            wname = widget.get_name()
            if isinstance(widget, gtk.Window):
                assert win == None
                win = widget
                continue

            if hasattr(self, wname) and getattr(self, wname):
                raise AssertionError (
                    "There is already an attribute called %s in %r" %
                    (wname, self))
            setattr(self, wname, widget)

        assert win != None
        w = win.get_child()
        win.remove(w)
        self.add(w)
        win.destroy()
        wtree.signal_autoconnect(self)


class GladeWindow(object):
    """
    Base class for dialogs or windows backed by glade interface definitions.

    Example:
    class MyWindow(GladeWindow):
        glade_file = 'my_glade_file.glade'
        ...

    Remember to chain up if you customize __init__(). Also note that GladeWindow
    does *not* descend from GtkWindow, so you can't treat the resulting object
    as a GtkWindow. The show, hide, destroy, and present methods are provided as
    convenience wrappers.
    """

    glade_dir = os.path.dirname(os.path.abspath(__file__))
    glade_file = None
    glade_typedict = None

    window = None

    def __init__(self, parent=None):
        try:
            assert self.glade_file
            filepath = os.path.join(self.glade_dir, self.glade_file)
            if self.glade_typedict:
                wtree = XML(filepath, typedict=self.glade_typedict, domain='pitivi')
            else:
                # pygtk 2.4 doesn't like typedict={} ?
                wtree = XML(filepath, domain='pitivi')
        except RuntimeError, e:
            raise RuntimeError('Failed to load file %s from directory %s: %s'
                               % (self.glade_file, self.glade_dir, e))

        self.widgets = {}
        for widget in wtree.get_widget_prefix(''):
            wname = widget.get_name()
            if isinstance(widget, gtk.Window):
                assert self.window == None
                self.window = widget
                continue

            if wname in self.widgets:
                raise AssertionError("Two objects with same name (%s): %r %r"
                                     % (wname, self.widgets[wname], widget))
            self.widgets[wname] = widget

        if parent:
            self.window.set_transient_for(parent)

        wtree.signal_autoconnect(self)

        self.show = self.window.show
        self.hide = self.window.hide
        self.present = self.window.present
        self.run = self.window.run

    def destroy(self):
        self.window.destroy()
        del self.window
