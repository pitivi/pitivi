---
short-description: GSoC project ideas we like
...

# GSoC Project Ideas

To apply for a [GSoC internship] you need to make a project proposal. The scope
of your GSoC project will probably cover only Pitivi, but it could very well
span multiple codebases:

-   [Pitivi], which is the user interface. Written in Python. *For those
    who love design and graphical user interaction.*
-   [GES], the high-level video editing GStreamer library that powers
    Pitivi and other applications. Written in C. *For those who wish to
    improve an easy to use, powerful and flexible library for
    audio/video editing.*
-   GStreamer, for low-level work, such as improving filters/effects,
    codecs, hardware decoding/encoding acceleration, analysis, etc.
    Written in C. *For those seeking a challenging audio and video
    experience where optimization is key.*

We'd love to see GSoC proposals originating from an itch you need to scratch.
You are welcome to ask around and **bring your own ideas**. If you're not sure
where you can be most useful, have a look at our list of ideas below. These
shall be used as a base for writing a detailed project proposal.

See [Past GSoCs] for details on what the previous GSoC students did.

To create a detailed proposal, use our [GSoC application template].
Deadlines for applying are approaching fast, hurry up!

  [Pitivi]: https://www.pitivi.org/manual/mainwindow.html
  [GES]: GES.md
  [Past GSoCs]: Past_GSoCs.md
  [GSoC internship]: Google_Summer_of_Code.md
  [GSoC application template]: GSoC_Application.md


## Timeline enhancements

Fixing timeline issues and making small enhancements would improve a lot the
timeline usability, making it a delight to use Pitivi. See
[GitLab](https://gitlab.gnome.org/GNOME/pitivi/-/issues?label_name%5B%5D=6.+Component%3A+Timeline).

**Requirements**: Python. Minimal experience contributing to Pitivi including
unit tests.


## Closing credits

For [end credits](https://en.wikipedia.org/wiki/Closing_credits) and other
advanced text display, we could use the new [GStreamer
WPE](https://www.youtube.com/watch?v=no7rvUk8GqM) element in
[gst-plugins-bad](https://gitlab.freedesktop.org/gstreamer/gst-plugins-bad/tree/master/ext/wpe),
which can display an HTML page as a video element. As GstWPE is a live source it
does not allow seeking (getting frames at random positions), we have to add
logic in Pitivi for seamlessly creating a video file out of an animated HTML
page. The resulting file can be used in the project timeline as any other video
clip. You'd have to extend the UI with a new
[perspective](https://gitlab.gnome.org/GNOME/pitivi/blob/master/pitivi/perspective.py)
for managing the closing credits HTML, and the corresponding video files.

**Requirements**: Python. Minimal experience contributing to Pitivi including
unit tests.


## Fix GPU support in Pitivi

GStreamer has pretty good GPU support through the OpenGL set of plugins, but
Pitivi/GES is not able to take full advantage of that infrastructure yet, mainly
because of lack of testing and bug fixing on our side. This project is about
enabling GL plugins for compositing and rendering, and fixing any issue that
shows up. The second part would be about making sure hardware accelerated
decoders can be used in the pipelines.

**Requirements**: C. Experience with GStreamer is mandatory. Minimal experience
contributing to Pitivi including unit tests. Experience with OpenGL is a plus.


## GTK 4

Initially the development environment should be migrated onto a GTK 4 runtime
and then the app should be ported following the [migration guide from GTK 3 to
GTK 4](https://developer.gnome.org/gtk4/unstable/gtk-migrating-3-to-4.html).

**Requirements**: Python. Minimal experience contributing to Pitivi including
unit tests. Experience developing GTK apps is a plus.


## External audio editing integration

The audio editing features in Pitivi are likely to stay at a basic level so we
can focus on the video editing functionality. Once a video segment is finished,
it would be great to be able to export the entire audio and work on it with an
audio editor such as [Audacity](https://www.audacityteam.org). See for example
how the experimental Blender-Audacity integration
[works](https://www.youtube.com/watch?v=f61Zvb8AipA) and its
[Python implementation](https://github.com/tin2tin/audacity_tools_for_blender).

**Requirements**: Python. Minimal experience contributing to Pitivi including
unit tests. Experience developing GTK apps is a plus.
