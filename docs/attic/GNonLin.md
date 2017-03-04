# GNonLin

[GNonLin](http://gstreamer.freedesktop.org/data/doc/gstreamer/head/gnonlin/html/)
is a [GStreamer](http://gstreamer.freedesktop.org/) plugin providing a
set of elements to ease handling non-linear streams and dynamic
pipelines. The goals of the GNonLin elements are:

-   To be GStreamer **elements**, and therefore integrating themselves
    perfectly into any GStreamer pipeline,
-   To **not use any specific API**, except for the GStreamer/GObject
    API, making them easy to use with any language already supporting
    the GStreamer API,
-   To provide somewhat of an “editing point-of-view” to using gstreamer
    (sources, effects, position in time, ...),
-   To be non-destructive.

Initially created to be used in video editors, GNonLin was also made
generic so it can be used for audio editors, jukebox applications,
slideshows, live editing, etc.

While GNonLin was historically used as the sole editing backend for
Pitivi, Jokosher and other applications, it is **not** recommended to
use GNonLin directly anymore, unless you have a special appetite for
unwarranted pain and a Ph.D. in nuclear physics. Instead, you should use
[GES](GES.md).
