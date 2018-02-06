# Enhanced demo.py

    #!/usr/bin/env python

    """Basic Framework for writing GStreamer Demos in Python"""
    #<excerpt 2>
    import gobject
    gobject.threads_init()
    import gst
    #</excerpt>
    import pygtk
    pygtk.require("2.0")
    import gtk
    gtk.gdk.threads_init()
    import sys
    import os


    class DemoException(Exception):
        """Base exception class for errors which occur during demos"""

        def __init__(self, reason):
            self.reason = reason

    class Demo:
        """Base class implementing boring, boiler-plate code.
        Sets up a basic gstreamer environment which includes:

        * a window containing a drawing area and basic media controls
        * a basic gstreamer pipeline using an ximagesink
        * connects the ximagesink to the window's drawing area

        Derived classes need only override magic(), __name__,
        and __usage__ to create new demos."""

        __name__ = "Enhanced Demo"
        __usage__ = "python demo.py -- runs a simple test demo"
        __def_win_size__ = (320, 240)

        # this comment allows us to include only a portion of the file
        # in the tutorial for this demo
        # <excerpt 1>     ...

        def magic(self, pipeline, sink, args):
            """This is where the magic happens"""
            src = gst.element_factory_make("videotestsrc", "src")
            pipeline.add(src)
            src.link(sink)

        def messageCb(self, bus, message):
            if message.type == gst.MESSAGE_STATE_CHANGED:
                old, new, pending = message.parse_state_changed()
                self.updateButtons(new)
            return gst.BUS_PASS

        def createPipeline(self, w):
            """Given a window, creates a pipeline and connects it to the window"""

            # code will make the ximagesink output in the specified window
            def set_xid(window):
            gtk.gdk.threads_enter()
                sink.set_xwindow_id(window.window.xid)
                sink.expose()
                gtk.gdk.threads_leave()

            # this code receives the messages from the pipeline. if we
            # need to set X11 id, then we call set_xid
            def bus_handler(unused_bus, message):
                if message.type == gst.MESSAGE_ELEMENT:
                    if message.structure.get_name() == 'prepare-xwindow-id':
                        set_xid(w)
                return gst.BUS_PASS

            # create our pipeline, and connect our bus_handler
            self.pipeline = gst.Pipeline()
            bus = self.pipeline.get_bus()
            bus.set_sync_handler(bus_handler)
            bus.add_watch(self.messageCb)

            sink = gst.element_factory_make("ximagesink", "sink")
            sink.set_property("force-aspect-ratio", True)
            sink.set_property("handle-expose", True)
            scale = gst.element_factory_make("videoscale", "scale")
            cspace = gst.element_factory_make("ffmpegcolorspace", "cspace")

            # our pipeline looks like this: ... ! cspace ! scale ! sink
            self.pipeline.add(cspace, scale, sink)
            scale.link(sink)
            cspace.link(scale)
            return (self.pipeline, cspace)

        # ... end of excerpt </excerpt>

        # subclasses can override this method to provide custom controls
        def customWidgets(self):
            return gtk.HBox()

        def createWindow(self):
            """Creates a top-level window, sets various boring attributes,
            creates a place to put the video sink, adds some and finally
            connects some basic signal handlers. Really, really boring.
            """

            # create window, set basic attributes
            w = gtk.Window()
            w.set_size_request(*self.__def_win_size__)
            w.set_title("Gstreamer " + self.__name__)
            w.connect("destroy", gtk.main_quit)

            # declare buttons and their associated handlers
            controls = (
                ("play_button", gtk.ToolButton(gtk.STOCK_MEDIA_PLAY), self.onPlay),
                ("pause_button", gtk.ToolButton(gtk.STOCK_MEDIA_PAUSE), self.onPause),
                ("stop_button", gtk.ToolButton(gtk.STOCK_MEDIA_STOP), self.onStop),
                ("quit_button", gtk.ToolButton(gtk.STOCK_QUIT), gtk.main_quit)
            )

            # as well as the container in which to put them
            box = gtk.HButtonBox()

            # for every widget, connect to its clicked signal and add it
            # to the enclosing box
            for name, widget, handler in controls:
                widget.connect("clicked", handler)
                box.pack_start(widget, True)
                setattr(self, name, widget)
            self.updateButtons(gst.STATE_NULL)

            viewer = gtk.DrawingArea()
            viewer.modify_bg(gtk.STATE_NORMAL, viewer.style.black)

            # we will need this later
            self.xid = None

            # now finally do the top-level layout for the window
            layout = gtk.VBox(False)
            layout.pack_start(viewer)

            # subclasses can override childWidgets() to supply
            # custom controls
            layout.pack_start(self.customWidgets(), False, False)
            layout.pack_end(box, False, False)
            w.add(layout)
            w.show_all()

            # we want to return only the portion of the window which will
            # be used to display the video, not the whole top-level
            # window. a DrawingArea widget is, in fact, an X11 window.
            return viewer

        def onPlay(self, unused_button):
            self.pipeline.set_state(gst.STATE_PLAYING)

        def onPause(self, unused_button):
            self.pipeline.set_state(gst.STATE_PAUSED)

        def onStop(self, unused_button):
            self.pipeline.set_state(gst.STATE_READY)

        def updateButtons(self, state):
            if state == gst.STATE_NULL:
                self.play_button.set_sensitive(True)
                self.pause_button.set_sensitive(False)
                self.stop_button.set_sensitive(False)
            elif state == gst.STATE_READY:
                self.play_button.set_sensitive(True)
                self.pause_button.set_sensitive(False)
                self.stop_button.set_sensitive(False)
            elif state == gst.STATE_PAUSED:
                self.play_button.set_sensitive(True)
                self.pause_button.set_sensitive(False)
                self.stop_button.set_sensitive(True)
            elif state == gst.STATE_PLAYING:
                self.play_button.set_sensitive(False)
                self.pause_button.set_sensitive(True)
                self.stop_button.set_sensitive(True)

        def run(self):
            w = self.createWindow()
            p, s = self.createPipeline(w)
            try:
                self.magic(p, s, sys.argv[1:])
                gtk.main()
            except DemoException, e:
                print e.reason
                print self.__usage__
                sys.exit(-1)

    # if this file is being run directly, create the demo and run it
    if __name__ == '__main__':
        Demo().run()
