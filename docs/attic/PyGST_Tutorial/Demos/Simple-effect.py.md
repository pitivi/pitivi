# Simple-effect.py

    #!/usr/bin/env python
    """Extends basic demo with a gnl composition"""

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

    class SimpleEffectDemo(Demo):
        __name__ = "Basic GStreamer Effect Demo"
        __usage__ = '''python %s file
        display file with a color_balance effect''' % sys.argv[0]
        __def_win_size__ = (320, 500)
        # <excerpt 1>
        def magic(self, pipeline, sink, args):

            def onPad(obj, pad, target):
                sinkpad = target.get_compatible_pad(pad, pad.get_caps())
                pad.link(sinkpad)
                return True

            assert os.path.exists(sys.argv[1])

            # create the following pipeline
            # filesrc location = sys.argv[1] ! decodebin ! videobalance ! ...
            src = gst.element_factory_make("filesrc")
            src.set_property("location", sys.argv[1])
            decode = create_decodebin()

            self.balance = gst.element_factory_make("videobalance")

            pipeline.add(src, decode, self.balance)
            src.link(decode)
            decode.connect("pad-added", onPad, self.balance)
            self.balance.link(sink)

            return
        # </excerpt>

        # <excerpt 2>
        # overriding from parent
        def customWidgets(self):
            """Create a control for each property in the videobalance
            widget"""

            # to be called a property value needs to change
            def onValueChanged(widget, prop):
                # set the corresponding property of the videobalance element
                self.balance.set_property(prop, widget.get_value())

            # videobalance has several properties, with the following range
            # and defaults
            properties = [("contrast", 0, 2, 1),
                          ("brightness", -1, 1, 0),
                          ("hue", -1, 1, 0),
                          ("saturation", 0, 2, 1)]

            # create a place to hold our controls
            controls = gtk.VBox()
            labels = gtk.VBox()
            # for every property, create a control and set its attributes
            for prop, lower, upper, default in properties:
                widget = gtk.HScale(); label = gtk.Label(prop)

                # set appropriate attributes
                widget.set_update_policy(gtk.UPDATE_CONTINUOUS)
                widget.set_value(default)
                widget.set_draw_value(True)
                widget.set_range(lower, upper)

                # connect to our signal handler, specifying the property
                # to adjust
                widget.connect("value-changed", onValueChanged, prop)

                # pack widget into box
                controls.pack_start(widget, True, True)
                labels.pack_start(label, True, False)

            layout = gtk.HBox()
            layout.pack_start(labels, False, False)
            layout.pack_end(controls, True, True)
            return layout

        # </excerpt>

    if __name__ == '__main__':
        SimpleEffectDemo().run()
