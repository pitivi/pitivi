# PyGST Tutorial/Effects

This article discusses effects and mixing of video. We cover two demos:
a simple video processing demo, and a slightly more complicated
video-mixing demo.

# Applying Effects

In GStreamer, effects are just elements. To apply an effect to a video
stream, you simply link it into the pipeline between the source and the
sink. Let's say you wanted to adjust the color balance on a video clip
before displaying it:

![](color_balance_pipeline.png "color_balance_pipeline.png")

Some effects take a number of parameters. These are controlled by
setting properties on the element. This is represented by the red arrow
in this pipeline, because these parameters are set from outside of the
GStreamer pipeline.

# Simple Effect Demo

Let's use what we've learned to create a simple video-processing
application.

![Color Balance Demo](simple_effect_1.png "Color Balance Demo")

[source for this example](simple-effect.py.md)

First, a word about `decodebin`. There are two variants: `decodebin` and
`decodebin2`. We want `decodebin2` if it is available, but if not we
fall back on `decodebin`. This is embodied in the following routine,
which we will be re-using often.

    def create_decodebin():
        try:
            return gst.element_factory_make("decodebin2")
        except:
            return gst.element_factory_make("decodebin")

We override the `magic()` method of our previous demo to create a
pipeline similar to the one shown above.

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

The only tricky part here is that the a `decodebin` has no pads when
it's first created: it cannot be linked into the pipeline straightaway.
So, we register a handler for the `pad-added` signal which connects any
dynamic pads to the pipeline.

That was easy enough. So, what about the UI? We want to be able to
adjust the hue, saturation, etc. *in real time*. The first thing is to
figure out which properties `videobalance` supports. We use
`gst-inspect` for this:

    $ gst-inspect-0.10 videobalance
    ...
    Element Properties:
      name                : The name of the object
                            flags: readable, writable
                            String. Default: null Current: "videobalance0"
      qos                 : handle QoS messages
                            flags: readable, writable
                            Boolean. Default: false Current: true
      contrast            : contrast
                            flags: readable, writable
                            Double. Range:               0 -               2 Default:               1
    Current:               1
      brightness          : brightness
                            flags: readable, writable
                            Double. Range:              -1 -               1 Default:               0
    Current:               0
      hue                 : hue
                            flags: readable, writable
                            Double. Range:              -1 -               1 Default:               0
    Current:               0
      saturation          : saturation
                            flags: readable, writable
                            Double. Range:               0 -               2 Default:               1
    Current:               1

Yeesh! Let's clarify this with the following table:

  Property       Type      Range        Default
  -------------- --------- ------------ ---------
  “contrast”     `float`   \[0 - 2\]    1
  “brightness”   `float`   \[-1 - 1\]   0
  “hue”          `float`   \[-1 - 1\]   0
  “saturation”   `float`   \[0 -2\]     1

That's much better. Now we can see we that all the properties are
floating point values within a specific range. This indicates that a
`gtk.Scale` widget would be a good choice for representing the value of
each property. So, we will create a widget for each property, and link
the value of the widget to the value of the property. To accomplish
this, all we need do is connect the `gtk.HScale` widget's
`value-changed` signal, to a callback which calls `set_property()` on
the `videobalance` element.

[source for this example](simple-effect.py.md)

## Exercises

-   Modify the demo to work with a different effect
    -   First use `gst-inspect-0.10 | grep 'filter'` to find an
        appealing effect
    -   Then use `gst-inspect-0.10 `*`your`` ``effect`* to learn about
        its properties.
    -   Finally, insert the effect into the pipeline and write a
        user-interface to control its properties.

# Mixing Sources

Compositing is the mainstay of visual effects. I'll create a simple
example to illustrate how compositing can be done in GStreamer. Note
that there are some issues with this demo that we do not address here:
in particular, what happens when one of the sources finishes playing.

![](crossfade.png "crossfade.png")

[source for this example](cross-fade.py.md)

We're going to create a video cross-fader that will mix between two
arbitrary sources. We will specify the sources on the command line, and
use a slider to do live adjustment of the amount of cross-fade.

## The Crossfade Pipeline

![](crossfade_pipeline.png "crossfade_pipeline.png")

Compositing is done with the `videomixer` element. The `videomixer` can
accommodate any number of sources, though the performance of your
machine will limit how much processing you can do. An important thing to
understand is that `videomixer` only operates on <em> YUVA </em>
streams. What that means is that the input video stream must be in the
<em> YUV </em> color-space, and must contain an alpha channel. Sometimes
streams are in the <em> RGB </em> color-space, and do not have alpha
channels. Therefore, we will first use `ffmpegcolorspace` to
automatically convert the source video to YUV (if necessary), and then
add an alpha channel to our video using the `alpha` element. The `alpha`
element has the `alpha` property, effectively allowing us to set the
transparency of our sources.

The first step is to create our sources. We create the sources in the
same way as we did for the color-balance demo shown above, except that
we create a separate `ffmpegcolorspace` and `alpha` element for each
source.

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

The second step is to build up our pipeline. Aside from the `decodebin`,
all the elements in the pipeline use static pads.

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

For the user interface, we only need to create one `gtk.HScale()`
element. We'll call its value “Crossfade”. Its `value-` `changed` signal
handler looks like this:

            def onValueChanged(widget):
                if self.srcBalpha:
                    self.srcBalpha.set_property("alpha", widget.get_value())

## What the alpha Value Means

The slider only controls the alpha channel of the second source. This
might seem confusing. If so, you are probably thinking the `videomixer`
works in the same way as an audio mixer -- that the alpha channel
represents the “volume” of the source in the output “mix.” This is not
quite the case. It is true that if you set both sources' alpha value to
zero, you will only see the background pattern (black); however, you
will not see both sources if you set both alpha values to 1. Instead,
you will only see srcB. An alpha value of 1 represents opacity. In order
to have an even blend of both sources, you set the alpha of the srcA to
1, and set the alpha of srcB to 0.5. This will make more sense if you
think of the `videomixer` as composed of “layers” stacked atop one
another. If the front-most source is completely opaque, you cannot see
the layers behind.

[source for this example](cross-fade.py.md)

## Exercises

We use the `alpha` element here to apply a solid alpha; however, the
`alpha` can do several other methods of compositing.

1.  Create a demo that can do chroma key with either red, green, or blue
    screen.
2.  Create a demo that can use an arbitrary key color
3.  Modify your solution to the previous example to allow an eye-dropper
    type tool to select the color.
4.  Use `v4l2src` to allow a webcam or capture card to supply the video
    input for one of the sources.
