# PyGST Tutorial/Elements: basics

The purpose of this tutorial is to give you a basic working PyGst
plugin, and explain what each part does succinctly. This is a jumpstart,
not a replacement for the GStreamer Plugin Tutorial.

I will try to walk you through creating a new element that acts as a
filter (has both a sink and source, this one won't actually do any
filtering :)), which receives a buffer and pushes it forward. As such it
should help you avoid the pain.

:   source

## explanations

:   We will only be talking about the code in NewElement, the rest can
    be found in the [ source](elements_basics.py.md).
:   still needs a lot of work.

The image below shows the most important parts of a filter element, the
sink a gst.Pad, the elements chain function and the source a gst.Pad.

![filter element](Filter_element.elements_basics.png "filter element")

The image below shows how data flows through elements, and what type
each element is.

![source filter and sink
elements](Src-filter-sink.elemets-basics.png "source filter and sink elements")

All new elements are derived from gst.Element or a class derived from
gst.Element, gst.PushSrc is such an example. There are several basic
steps common to all plugins which include registering the element with
gstreamer, and initialising the plugin like you would any other object.
When initialising a derivied gst.Element you must do several things,
create the gst.Pads which describe media streams (buffers) the element
can receive and send, and make the pads by calling the
gst.Element.add\_pad(gst.Pad) method. You must also override the
functions specific to what you are trying to do, we are creating a
filter (an element which both receives and sends buffers) in this case
we must at minimum override the gst.Pad.set\_caps function which is used
to negotiate which type of buffers can be received and the gst.Pad.chain
function which handles incoming buffers.

NewElement is derived from gst.Element

    class NewElement(gst.Element):
        """ A basic, buffer forwarding gstreamer element """

Every new class derived from gst.Element (or another class derived from
gst.Element) must register it's self

        #here we register our plugin details
        __gstdetails__ = (
            "NewElement plugin",
            "newelement.py",
            "gst.Element, that passes a buffer from source to sink (a filter)",
            "Stephen Griffiths <scgmk5@gmail.com>")

        #source pad (template): we send buffers forward through here
        _srctemplate = gst.PadTemplate ('src',
            gst.PAD_SRC,
            gst.PAD_ALWAYS,
            gst.caps_new_any())

        #sink pad (template): we receive buffers from our sink pad
        _sinktemplate = gst.PadTemplate ('sink',
            gst.PAD_SINK,
            gst.PAD_ALWAYS,
            gst.caps_new_any())

        #register our pad templates
        __gsttemplates__ = (_srctemplate, _sinktemplate)

When we initialise the class, we must create the pads required to
communicate with other elements.

        def __init__(self, *args, **kwargs):
            #initialise parent class
            gst.Element.__init__(self, *args, **kwargs)

            #source pad, outgoing data
            self.srcpad = gst.Pad(self._srctemplate)

            #sink pad, incoming data
            self.sinkpad = gst.Pad(self._sinktemplate)
            self.sinkpad.set_setcaps_function(self._sink_setcaps)
            self.sinkpad.set_chain_function(self._sink_chain)

            #make pads available
            self.add_pad(self.srcpad)
            self.add_pad(self.sinkpad)

the pad setcaps function is called when we need to negotiate the
capabilities of our element relative to the element we are negotiating
with.

        def _sink_setcaps(self, pad, caps):
            #we negotiate our capabilities here, this function is called
            #as autovideosink accepts anything, we just say yes we can handle the
            #incoming data
            return True

the pad chain function is called on sink caps (the ones receiving data),
a buffer is received and pushed forward. Normally this is where we would
make changes to a buffer.

        def _sink_chain(self, pad, buf):
            #this is where we do filtering
            #and then push a buffer to the next element, returning a value saying
             it was either successful or not.
            return self.srcpad.push(buf)

### source

[elements\_basics.py](elements_basics.py.md)

## Other Resources

-   [GStreamer
    documentation](http://gstreamer.freedesktop.org/documentation/)
-   [PyGST documentation](http://pygstdocs.berlios.de/)
