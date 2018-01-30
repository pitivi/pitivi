# PyGST Tutorial/Demos/Audio video crossfade.py

    #!/usr/bin/env python

    """A short Audio-Video example"""
    import gobject
    gobject.threads_init()
    import gst
    import pygtk
    pygtk.require("2.0")
    import gtk
    import sys
    import os
    from audio_video import AVDemo, create_decodebin

    class AVCrossfade(AVDemo):
        """Base class implementing boring, boiler-plate code.
        Sets up a basic gstreamer environment which includes:

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

        def onPad(self, decoder, pad, target):
            tpad = target.get_compatible_pad(pad)
            if tpad:
                pad.link(tpad)

        def addVideoChain(self, pipeline, name, decoder, mixer):
            alpha = gst.element_factory_make("alpha")
            alpha.props.alpha = 1.0
            videoscale = gst.element_factory_make("videoscale")
            videorate = gst.element_factory_make("videorate")
            colorspace = gst.element_factory_make("ffmpegcolorspace")
            queue = gst.element_factory_make("queue")

            pipeline.add(alpha, videoscale, videorate, colorspace, queue)
            decoder.connect("pad-added", self.onPad, videorate)
            videorate.link(videoscale)
            videoscale.link(colorspace)
            colorspace.link(queue)
            queue.link(alpha)
            alpha.link(mixer)

            setattr(self, "alpha%s" % name, alpha)

        def addAudioChain(self, pipeline, name, decoder, adder):
            volume = gst.element_factory_make("volume")
            volume.props.volume = 0.5
            audioconvert = gst.element_factory_make("audioconvert")
            audiorate = gst.element_factory_make("audioresample")
            queue = gst.element_factory_make("queue")

            pipeline.add(volume, audioconvert, audiorate, queue)
            decoder.connect("pad-added", self.onPad, audioconvert)
            audioconvert.link(audiorate)
            audiorate.link(queue)
            queue.link(volume)
            volume.link(adder)

            setattr(self, "vol%s" % name, volume)

        def addSourceChain(self, pipeline, name, filename, mixer, adder):
            src = gst.element_factory_make("filesrc")
            src.props.location = filename
            dcd = create_decodebin()

            pipeline.add(src, dcd)
            src.link(dcd)
            self.addVideoChain(pipeline, name, dcd, mixer)
            self.addAudioChain(pipeline, name, dcd, adder)

        def magic(self, pipeline, (videosink, audiosink), args):
            """This is where the magic happens"""
            mixer = gst.element_factory_make("videomixer")
            adder = gst.element_factory_make("adder")
            pipeline.add(mixer, adder)

            mixer.link(videosink)
            adder.link(audiosink)
            self.addSourceChain(pipeline, "A", args[0], mixer, adder)
            self.addSourceChain(pipeline, "B", args[1], mixer, adder)
            self.alphaB.props.alpha = 0.5

        def onValueChanged(self, adjustment):
            balance = self.balance.get_value()
            crossfade = self.crossfade.get_value()
            self.volA.props.volume = (2 - balance) * (1 - crossfade)
            self.volB.props.volume = balance * crossfade
            self.alphaB.props.alpha = crossfade

        def customWidgets(self):
            self.crossfade = gtk.Adjustment(0.5, 0, 1.0)
            self.balance = gtk.Adjustment(1.0, 0.0, 2.0)
            crossfadeslider = gtk.HScale(self.crossfade)
            balanceslider = gtk.HScale(self.balance)
            self.crossfade.connect("value-changed", self.onValueChanged)
            self.balance.connect("value-changed", self.onValueChanged)

            ret = gtk.Table()
            ret.attach(gtk.Label("Crossfade"), 0, 1, 0, 1)
            ret.attach(crossfadeslider, 1, 2, 0, 1)
            ret.attach(gtk.Label("Balance"), 0, 1, 1, 2)
            ret.attach(balanceslider, 1, 2, 1, 2)
            return ret

    # if this file is being run directly, create the demo and run it
    if __name__ == '__main__':
        AVCrossfade().run()
