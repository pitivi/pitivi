# Elements basics.py

    #!/usr/bin/env python

    """
    gst.Element basics, this is a modified script of Brandon Lewis
    """

    # PiTiVi does this for you, but in any stand-alone gstreamer script you need
    # to do this before anything else
    import gobject
    gobject.threads_init()

    # import gst and gtk
    import gst
    import gtk


    class NewElement(gst.Element):
        """ A basic, buffer forwarding gstreamer element """

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

        def _sink_setcaps(self, pad, caps):
            #we negotiate our capabilities here, this function is called
            #as autovideosink accepts anything, we just say yes we can handle the
            #incoming data
            return True

        def _sink_chain(self, pad, buf):
            #this is where we do filtering
            #and then push a buffer to the next element, returning a value saying
            # it was either successful or not.
            return self.srcpad.push(buf)

    #here we register our class with glib, the c-based object system used by
    #gstreamer
    gobject.type_register(NewElement)





    ## this code creates the following pipeline, equivalent to
    ## gst-launch-0.10 videotestsrc ! videoscale ! ffmpegcolorspace !
    ### NewElement ! autovideosink

    # first create individual gstreamer elements

    source = gst.element_factory_make("videotestsrc")
    print "making new element"
    newElement = NewElement()
    print "made new element"
    vscale = gst.element_factory_make("videoscale")
    cspace = gst.element_factory_make("ffmpegcolorspace")
    vsink  = gst.element_factory_make("autovideosink")

    # create the pipeline

    p = gst.Pipeline()
    p.add(source, vscale, cspace, newElement,
        vsink)
    gst.element_link_many(source, vscale, cspace, newElement,
        vsink)
    # set pipeline to playback state

    p.set_state(gst.STATE_PLAYING)

    # start the main loop, pitivi does this already.

    gtk.main()
