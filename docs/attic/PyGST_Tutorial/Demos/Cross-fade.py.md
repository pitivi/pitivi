# Cross-fade.py

    #!/usr/bin/env python
    """Extends basic demo with a gnl composition"""
    import gobject
    gobject.threads_init()
    from demo import Demo, DemoException
    import gtk
    import gst
    import sys
    import os

    def create_decodebin():
        try:
            return gst.element_factory_make("decodebin2")
        except:
            return gst.element_factory_make("decodebin")

    class SimpleCrossfadeDemo(Demo):
        __name__ = "Demo of crosfade  without using gnonlin"
        __usage__ = '''python %s sourceA sourceB
        live crossfading between two sources''' % sys.argv[0]
        __def_size__ = (320, 420)

        def magic(self, pipeline, sink, args):

            def onPad(obj, pad, target):
                sinkpad = target.get_compatible_pad(pad, pad.get_caps())
                if sinkpad:
                    pad.link(sinkpad)
                return True

            assert len(sys.argv) == 3
            assert os.path.exists(sys.argv[1])
            assert os.path.exists(sys.argv[2])

            # <excerpt 1>
            src = gst.element_factory_make("filesrc")
            src.set_property("location", sys.argv[1])

            srcAdecode = create_decodebin()
            srcAconvert = gst.element_factory_make("ffmpegcolorspace")
            srcAalpha = gst.element_factory_make("alpha")
            srcAalpha.set_property("alpha", 1.0)

            srcB = gst.element_factory_make("filesrc")
            srcB.set_property("location", sys.argv[2])
            srcBdecode = create_decodebin()
            srcBconvert = gst.element_factory_make("ffmpegcolorspace")
            srcBalpha = gst.element_factory_make("alpha")
            srcBalpha.set_property("alpha", 0.5)

            mixer = gst.element_factory_make("videomixer")
            mixer.set_property("background", "black")
            # </excerpt>

            # <excerpt 2>
            pipeline.add(mixer)

            pipeline.add(src, srcAdecode, srcAconvert, srcAalpha)
            src.link(srcAdecode)
            srcAdecode.connect("pad-added", onPad, srcAconvert)
            srcAconvert.link(srcAalpha)
            srcAalpha.link(mixer)

            pipeline.add(srcB, srcBdecode, srcBconvert, srcBalpha)
            srcB.link(srcBdecode)
            srcBdecode.connect("pad-added", onPad, srcBconvert)
            srcBconvert.link(srcBalpha)
            srcBalpha.link(mixer)

            mixer.link(sink)

            # remember the alpha elements
            self.srcBalpha = srcBalpha
            # </excerpt>


        # overriding from parent
        def customWidgets(self):
            """Create a control for each property in the videobalance
            widget"""

            # <excerpt 3>
            # to be called a property value needs to change
            def onValueChanged(widget):
                if self.srcBalpha:
                    self.srcBalpha.set_property("alpha", widget.get_value())
            # </excerpt>

            lower = 0
            upper = 1
            default = 0.5

            # create a place to hold our controls
            controls = gtk.VBox()
            labels = gtk.VBox()

            widget = gtk.HScale(); label = gtk.Label("Crossfade")

            # set appropriate attributes
            widget.set_update_policy(gtk.UPDATE_CONTINUOUS)
            widget.set_draw_value(True)
            widget.set_range(lower, upper)
            widget.set_value(default)

            # connect to our signal handler, specifying the property
            # to adjust
            widget.connect("value-changed", onValueChanged)

            # pack widget into box
            controls.pack_start(widget, True, True)
            labels.pack_start(label, True, False)

            layout = gtk.HBox()
            layout.pack_start(labels, False, False)
            layout.pack_end(controls, True, True)
            return layout

    if __name__ == '__main__':
        SimpleCrossfadeDemo().run()
