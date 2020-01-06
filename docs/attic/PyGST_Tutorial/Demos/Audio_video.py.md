# Audio video.py

``` python
#!/usr/bin/env python

"""A short Audio-Video example"""
import gobject
gobject.threads_init()
import gst
import pygtk
pygtk.require("2.0")
import gtk
gtk.gdk.threads_init()
import sys
import os
from demo import Demo

def create_decodebin():
    try:
        return gst.element_factory_make("decodebin2")
    except:
        return gst.element_factory_make("decodebin")

class DemoException(Exception):
    """Base exception class for errors which occur during demos"""

    def __init__(self, reason):
        self.reason = reason

class AVDemo(Demo):
    """Extends base demo with both audio and video sinks
    * a window containing a drawing area and basic media controls
    * a basic gstreamer pipeline using an ximagesink and an autoaudiosink
    * connects the ximagesink to the window's drawing area

    Derived classes need only override magic(), __name__,
    and __usage__ to create new demos."""

    __name__ = "AV Demo"
    __usage__ = "python audio_video.py <filename>"
    __def_win_size__ = (320, 240)

    # this comment allows us to include only a portion of the file
    # in the tutorial for this demo

    def magic(self, pipeline, (videosink, audiosink), args):
        """This is where the magic happens"""

        def onPadAdded(source, pad):
            # first we see if we can link to the videosink
            tpad = videoqueue.get_compatible_pad(pad)
            if tpad:
                pad.link(tpad)
                return
            # if not, we try the audio sink
            tpad = audioqueue.get_compatible_pad(pad)
            if tpad:
                pad.link(tpad)
                return

        src = gst.element_factory_make("filesrc", "src")
        src.props.location = args[0]
        dcd = create_decodebin()
        audioqueue = gst.element_factory_make("queue")
        videoqueue = gst.element_factory_make("queue")
        pipeline.add(src, dcd, audioqueue, videoqueue)

        src.link(dcd)
        videoqueue.link(videosink)
        audioqueue.link(audiosink)
        dcd.connect("pad-added", onPadAdded)

    def createPipeline(self, w):
        """Given a window, creates a pipeline and connects it to the window"""

        # code will make the ximagesink output in the specified window
        def set_xid(window):
        gtk.gdk.threads_enter()
            videosink.set_xwindow_id(window.window.xid)
            videosink.expose()
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

        videosink = gst.element_factory_make("ximagesink", "sink")
        videosink.set_property("force-aspect-ratio", True)
        videosink.set_property("handle-expose", True)
        scale = gst.element_factory_make("videoscale", "scale")
        cspace = gst.element_factory_make("ffmpegcolorspace", "cspace")

        audiosink = gst.element_factory_make("autoaudiosink")
        audioconvert = gst.element_factory_make("audioconvert")

        # pipeline looks like: ... ! cspace ! scale ! sink
        #                      ... ! audioconvert ! autoaudiosink
        self.pipeline.add(cspace, scale, videosink, audiosink,
            audioconvert)
        scale.link(videosink)
        cspace.link(scale)
        audioconvert.link(audiosink)
        return (self.pipeline, (cspace, audioconvert))

# if this file is being run directly, create the demo and run it
if __name__ == '__main__':
    AVDemo().run()
```
