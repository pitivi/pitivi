# PyGST Tutorial/Getting Started

Developing applications with GStreamer is primarily about creating and
modifying pipelines and providing an interface to control those
pipelines. GStreamer is a programming environment unto itself and is
inherently capable of performing complex tasks. It ships with a utility
called `gst-launch` which allows building and running pipelines using a
command-line syntax. This tool comes in handy for testing and debugging,
but is also useful for other tasks including: transcoding, transmuxing,
and effects processing. However, gst-launch-0.10 also hides a great deal
of complexity from the user. We will not be using `gst-launch`, or its
cousin `gst-parse-launch()` much from here on out. We will dive directly
into gstreamer in all its glory.

# What is GStreamer?

It's worth pausing a moment to reflect on what GStreamer actually is.
GStreamer is a media-processing framework organized around the
[dataflow](http://en.wikipedia.org/wiki/Dataflow) paradigm. In brief,
this means that computations are represented as directed, acyclic
[graphs](http://en.wikipedia.org/wiki/Graph_(data_structure)) through
which data 'flows'. Data buffers are passed from node to node though the
graph, starting at *source* nodes, and ending at *sink* nodes. At each
node, a different operation is performed on the data.

In GStreamer terminology, the top-level graph is called a *pipeline*,
and nodes within the graph are called *elements*. The *edges* connecting
elements are referred to as *links*. Elements can only be connected to
each other through connection points called *pads*; however, GStreamer
elements have convenience methods that allow them to link directly to
other elements. This allows us to forget about pads most of the time.

Programming in GStreamer at the API level can be counter-intuitive. The
application runs in a GObject main-loop, and Business logic is often
spread across several layers of signal handlers. Depending on the
situation your code may be called from either the main thread, or one of
many of element threads created automatically by GStreamer. The main
thing is to remember that GStreamer pipelines are just graphs. In all of
these examples, the graph-structure of the underlying pipeline is
emphasized.

# The First GStreamer Demo

Our first task is to set up a suitable environment for experimenting
with GStreamer, particularly with video. We'd like to get the minimal
set of features going: an output window, some minimal controls, and a
minimal GStreamer pipeline for displaying video. We want it to look
something like this:

![screenshot of first demo](demo_1.png "screenshot of first demo")

[source for this example](demo.py.md)

First things first. Every PyGST application needs to start with some
boilerplate:

    #!/usr/bin/env python
    import gobject
    gobject.threads_init()
    import gst

Note that the call to `gobject.threads_init()` occurs before importing
anything else, including `gst`. Since we're also using PyGTK, we have a
few other imports to include:

    import pygtk
    pygtk.require("2.0")
    import gtk
    gtk.gdk.threads_init()
    import sys
    import os

**Note**: I have been informed that we also need to call
gtk.gdk.threads\_init()

So, where do we go from here? I'll assume you're all familiar enough
with GTK to know how to create the GUI. Let's focus specifically on the
section of the window which displays the image: the viewer widget. A
good place to start is to observe that directed graphs have sources and
sinks, and our output window would definitely be a sink in the graph.
So, let's try searching for a sink element and see what we come up with.
The `gst-inspect-0.10` utility will be helpful here:

<code>

    $ gst-inspect-0.10 | grep sink
    multifile:  multifilesink: Multi-File Sink
    cacasink:  cacasink: A colored ASCII art video sink
    autodetect:  autoaudiosink: Auto audio sink
    autodetect:  autovideosink: Auto video sink
    aasink:  aasink: ASCII art video sink
    ossaudio:  osssink: Audio Sink (OSS)
    udp:  dynudpsink: UDP packet sender
    udp:  multiudpsink: UDP packet sender
    udp:  udpsink: UDP packet sender
    halelements:  halaudiosink: HAL audio sink
    alsaspdif:  alsaspdifsink: S/PDIF ALSA audiosink
    debug:  testsink: Test plugin
    xvimagesink:  xvimagesink: Video sink
    dfbvideosink:  dfbvideosink: DirectFB video sink
    ximagesink:  ximagesink: Video sink
    ...

</code>

Yeesh! There's a lot of plug-ins in GStreamer. However, if you look
towards the bottom of the list you'll see the `ximagesink` element.
That's the one we want. As an exercise, type
`$ gst-inspect-0.10 ximagesink` and read what it says. `gst-inspect` is
your first resource for learning about what GStreamer can do. However,
in this case the output from `gst-iqnspect` is limited. There are two
important things about `ximagesink` that you will not find here. More
about that later. For now, take my word for it that `gst-` `inspect`
will tell you that `ximagesink` has a one sink pad which accepts decoded
video data. We have reached square one.

In the interest of brevity, I'll also mention that it is a good idea to
have a `videoscale` and a `ffmpegcolorspace` element between the source
data and the output sink. This way, if your input comes in some form
which your display can't handle, it will be automatically converted. So,
our pipeline is beginning to take shape. It looks kinda like this:

![](demo_pipeline_1.png "demo_pipeline_1.png")

There are two bubbles in this diagram which represent unsolved problems.
The first is “Where do we get the input?”. The answer to the first
question will be the subject of later chapters. For now, we'll use
`videotestsrc` to make sure everything is working. The magic method is
to be overridden by future subclasses to create new demos. In this demo,
it simply connects a test source to the rest of the pipeline.

         ...

        def magic(self, pipeline, sink, args):
            """This is where the magic happens"""
            src = gst.element_factory_make("videotestsrc", "src")
            pipeline.add(src)
            src.link(sink)

The the second question is “How do we connect the `ximagesink` to the
output window?”. The answer to this is unfortunately a rather advanced
topic for an introductory demo. You don't have to worry about
understanding this code just yet. We will revisit it in more depth in
the article on pipeline `Bus` objects. Long story short, the
`ximagesink` object puts a request to get the xwindow-id onto the bus.
When we get that message, we call `set_xwindow_id()`. If we do not do
this, the sink element will create a new window.

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

        # ... end of excerpt

[source for this example](demo.py.md)
