# PyGST Tutorial/Combining Audio and Video

So far, our demos have been video-only for the sake of clarity. A few
people have asked for some specific examples explaining how to get audio
and video together in the same pipeline, so this article focuses
specifically on these challenges.

# Audio Elements

GStreamer also has various audio sink elements, but for the sake of
simplicity we can just use `autoaudiosink`, which figures out the
correct type for us. Working with audio sinks is much easier than
working with video sinks.

We have seen that GStreamer offers some utility elements for video,
including `videoscale` and `ffmpegcolorspace`. We also have a similar
elements for audio, including: `audioconvert` and `audioresample`.

# What Happens Inside Decodebin

Media files have a hierarchical structure. The top level of this is the
container format, and within that are one or more media streams. Files
with audio and video information have at least one audio and one video
stream. In order to completely decode a movie file, the container format
must first be read and interpreted in order to extract the encoded
streams. Then the streams must be decompressed and possibly converted to
a format suitable for processing or display. In gstreamer terminology,
the container format is read with a “demuxer”, which is short for
“demultiplexer”, and streams are decompressed with “decoders”.

For example, let's say you wanted to decode an mpeg2 audio video stream:

![](mpeg2_decode_pipeline.png "mpeg2_decode_pipeline.png")

Or how about Motion-JPEG in an AVI container with mp3 audio:

![](avi_mjpeg_mp3_audio.png "avi_mjpeg_mp3_audio.png")

You could create an add-hoc pipeline for each independent scenario, but
that's not very flexible. Most container formats support a wide variety
of codecs, and the number of combinations of containers and codecs
supported by GStreamer is huge. Creating separate pipelines for each
scenario is impractical. What decodebin does is read a little bit of
information from its sink pad. Once it has worked out what container
format and streams are present in the data, it creates the appropriate
chain demuxers and decoders. It creates one source pad for each
individual stream in the file. Therefore if a file contains one video
stream and one audio stream, decodebin creates two pads: one for video,
and one for audio. GStreamer refers to this type of behavior as
*autoplugging* and elements which do this type of thing as
“autopluggers”. Because decodebin can't know what's in a stream until it
reads it, the pads are not created until the pipeline transitions into
the ready or paused states. This is why we must link decodebin to other
elements in the “pad-added” signal.

In previous examples, we were only interested in the video stream, so we
simply ignored any pad that that wasn't compatible with our video
colorspace converter. Now we have two possible targets to link when a
pad is created, and we need to be careful that the audio and video
source pads are linked to the appropriate processing elements.

## Your first Attempt

Suppose we want to play the a file, what do you suppose the pipeline
will look like? Go ahead, grab a napkin and a pen and take a wild stab
at drawing the pipeline for this example.

Done?

You probably drew something like the following:

![](wrong_pipeline.png "wrong_pipeline.png")

You can try and run this pipeline with the following gst-launch command
(be sure to set `${FILENAME}` to a suitable path before trying these
examples):

```
gst-launch-0.10 filesrc location=${FILENAME} ! decodebin name=decode \
decode. ! ffmpegcolorspace ! ximagesink \
decode. ! audioconvert ! autoaudiosink
```

So far so good. Now suppose we want to transcode instead. This means we
will pipe decoded audio and video through *encoders* and then into a
*muxer*, which will output to a filesink. We will use motion-jpeg with
raw audio in an avi container. The resulting pipeline looks like this in
`gst-launch` syntax:

```
gst-launch-0.10 filesrc location=${FILENAME} ! decodebin name=decode \
decode. ! ffmpegcolorspace ! jpegenc ! avimux name=muxer \
decode. ! audioconvert ! muxer. \
muxer. ! filesink location=${FILENAME}.avi sync=false
```

This example probably works well enough, but now suppose we want a
preview of the compressed video, so we can tune our quality settings:

```
gst-launch-0.10 filesrc location=${FILENAME} ! decodebin name=decode \
decode. ! ffmpegcolorspace ! jpegenc ! tee ! avimux name=muxer \
tee0. ! jpegdec ! ffmpegcolorspace ! autovideosink sync=false \
decode. ! audioconvert !muxer. \
muxer. ! filesink location=${FILENAME}.avi sync=false
```

This looks perfectly reasonable, but probably will not work -- this is
because you need something else we haven't seen yet: `queues`.

## Queues

The `queue` element is used to allow concurrent execution of streams
within a pipeline. Essentially, it forces elements linked *downstream*
to do their processing in a separate thread. This is especially
important when multiplexing, and when using multiple sink elements.
Consequences of not using queues when required include link errors,
audio / video sync issues, and deadlocks.

When working with multiple streams in gstreamer, use the following rules
of thumb:

-   Always add a queue before any sink element when the pipeline
    contains multiple sinks
-   Always add a queue before each input to a *muxer* (an element which
    combines several input streams into one output stream)

One thing to be aware of is that queues introduce *latency*. The
placement of queues within a pipeline can affect the responsiveness of
the pipeline to things like property changes.

Here's the proper version of the previous transcoding example, complete
with queues:

```
gst-launch-0.10 filesrc location=${FILENAME} ! decodebin name=decode \
decode. ! ffmpegcolorspace ! jpegenc ! tee ! queue ! avimux name=muxer \
tee0. ! jpegdec ! ffmpegcolorspace ! queue ! autovideosink sync=false \
decode. ! queue ! audioconvert !muxer. \
muxer. ! queue ! filesink location=${FILENAME}.avi sync=false
```

# Movie Player Demo

In this example we will write a simple movie player applet that can
handle both audio and video. The UI for this example is basically the
same as demo.py, so there's little to say about it. Let's jump straight
into creating the piepline, which looks like this:

[source for this example](audio_video.py.md)

![](audio_video_playback_pipeline.png "audio_video_playback_pipeline.png")

We override `createPipeline` so that it creates two sinks:

        def createPipeline(self, w):
            """Given a window, creates a pipeline and connects it to the window"""

            # ... duplicate code omitted for brevity

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

In `magic()`, the main difference is accepting the extra parameters, and
creating the audio and video queues:

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

Our dynamic linking code must now take into account one of two possible
targets:

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

[source for this example](audio_video.py.md)

# Video DJ Example

**Note: Currently there is an issue with the `volume` element which
prevents this example from working as well as it should. The audio
latency is much higher than it should be.**

[source for this example](audio_video_crossfade.py.md)

We've seen how to construct a simple pipeline that uses both audio and
video. Now, let's re-visit the video crossfade example, this time
cross-fading both audio and video. As with video, we need two kinds of
elements: an element to control audio volume, and an element to perform
the mixing. The volume element is called `volume` and the audio mixing
element is called `adder`. Adder requires that the incoming streams be
of the same type, width, depth, and rate, so we also need `audioconvert`
and `audioresample` to sanitize the incoming streams.

Go ahead: try to draw the pipeline for this example before looking at
the solution.

[audio\_crossfade\_pipeline.png](audio_crossfade_pipeline.png.md)

Notice that there are some recurring chains of elements. For audio, we
see this chain appear twice:

![](audio_crossfade_chain.png "audio_crossfade_chain.png")

And for video, this chain appears twice:

![](video_crossfade_chain.png "video_crossfade_chain.png")

To simplify the code for this example, i've factored out the audio and
video code into separate methods. First we make our `pad-added`
signal-handler a proper method so that we can connect to it multiple
places:

        def onPad(self, decoder, pad, target):
            tpad = target.get_compatible_pad(pad)
            if tpad:
                pad.link(tpad)

This method creates a chain of audio elements between `decoder` and
`adder`. At the end, we save the volume element as an instance attribute
to that the UI can its properites. This purpose of the `name` parameter
is to help generate a unique attribute names. Notice that we are passing
the target of the dynamic link as a user-parameter of the decoder's
`connect` method.

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

Now the code to create the chain of video elements. Notice how similar
it is in structure to the audio version:

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

For each input, we add a `filesrc` and decoder, then we combine the
audio and video chains.

        def addSourceChain(self, pipeline, name, filename, mixer, adder):
            src = gst.element_factory_make("filesrc")
            src.props.location = filename
            dcd = create_decodebin()

            pipeline.add(src, dcd)
            src.link(dcd)
            self.addVideoChain(pipeline, name, dcd, mixer)
            self.addAudioChain(pipeline, name, dcd, adder)

Now our `magic` method is fairly concise. All we have to do is create
the `videomixer`, `adder` and connect them to our source element-chains.

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

The UI layout is similar to the video-only example, but with an extra
control: a balance adjuster so the user can compensate if the volume
varies significantly between sources A and B.

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

When the slider moves, we want to set the alpha only on source B, as we
did in the video-only example. But we need to set the volume on both
audio sources to complimentary values. We also perform the balance
computation entirely in the UI.

        def onValueChanged(self, adjustment):
            balance = self.balance.get_value()
            crossfade = self.crossfade.get_value()
            self.volA.props.volume = (2 - balance) * (1 - crossfade)
            self.volB.props.volume = balance * crossfade
            self.alphaB.props.alpha = crossfade

[source for this example](audio_video_crossfade.py.md)

## Exercises

1.  Modify this example to work with an arbitrary number of sources.
    Hint: create a separate alpha slider for each source.
2.  Lookup `v4l2src` and `autoaudiosrc` using `gst-inspect`. Use what
    you learn replace one of the sources with input from the a webcam
    and sound card.
3.  Notice that this example does not place any queues between the
    mixing and sink elements. This is to minimize the latency of the
    slider control.
    1.  Insert queues between the `videomixer` and `ximagesink`, as well
        as between the `adder` and `autoaudiosink` elements. How does
        this affect the demo?
    2.  Try changing the properties of the queues. In particular, see
        how changing `max-size-time` and `min-threshold-time` affects
        latency. See if you can reduce latency to usable levels.
4.  In this example, we factored out code to create recurring portions
    of our pipeline into separate methods. GStreamer has a more general
    way to abstract repeating combinations of elements, called a *Bin*.
    We've already seen one example of such an element, `decodebin`.
    Rewrite this example so that common sections of code are factored
    into separate Bins. Hint: you also need to learn about *Ghost Pads*.
