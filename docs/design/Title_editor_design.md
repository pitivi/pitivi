# Title editor design

Here's an attempt at summarizing the current situation for adding text
on video with gstreamer. **Please improve/correct this page with your
knowledge**.

The question in everyone's mind:

> “What we should do in case of titles and text overlays with video
> compositing? Will be they considered as a video clip with
> corresponding properties?”

In the [GES](GES.md) API reference manual, we can see
[GES.TitleSource](http://lazka.github.io/pgi-docs/#GES-1.0/classes/TitleSource.html#GES.TitleSource)
and
[GES.TextOverlay](http://lazka.github.io/pgi-docs/#GES-1.0/classes/TextOverlay.html#GES.TextOverlay).

-   [GES.TitleSource](http://lazka.github.io/pgi-docs/#GES-1.0/classes/TitleSource.html#GES.TitleSource)
    is a title clip/object as you'd imagine it. This is what we are
    using now.
-   [GES.TextOverlay](http://lazka.github.io/pgi-docs/#GES-1.0/classes/TextOverlay.html#GES.TextOverlay),
    on the other hand, is something that is meant to be used really as
    an “overlay on top of an existing video stream” (ex: for subtitles).
    This probably corresponds to the [GStreamer text overlay
    element](http://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-base-plugins/html/gst-plugins-base-plugins-textoverlay.html).

In Pitivi, we would need one UI that does it all: allow creating a title
clip/timeline object that may have a transparent background color. That
way, if the user wants to use it as an overlay on video, he simply needs
to set the background color to be fully transparent. Only one UI, only
one workflow. More flexibility for the user and less confusion. As you
can see in some other applications [like
this](http://jeff.ecchi.ca/public/vegas-title-editor.webm) (or even in
kdenlive, I think), having a single UI to do everything feels great. We
can do a much better design than them, however!

We need to extend titlesource to be able to set a background color, or
even a text border color:

-   This is probably easy/trivial to fix in GES, you just need to expose
    the background-color property of GstVideoTestSrc into
    GESTrackVideoTestSource and the expose that in GESTitleSource.
-   That way, we can ignore textoverlay completely (titlesource will
    just depend on video compositing being reimplemented later on)
