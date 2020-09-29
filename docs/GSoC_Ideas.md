---
short-description: GSoC project ideas we like
...

# GSoC Project Ideas

These ideas shall be used as a base for writing a detailed project proposal if
you want to apply for a [GSoC internship](Google_Summer_of_Code.md). You are
welcome to come up with your own ideas.

To create a detailed proposal, use our [GSoC application
template](GSoC_Application.md).


## Cut perspective

The most tedious process of video editing is the initial cutting and structuring
of the global timeline. A new perspective similar to the
[EditorPerspective](https://gitlab.gnome.org/GNOME/pitivi/blob/master/pitivi/editorperspective.py)
will offer a [second timeline
representation](https://gitlab.gnome.org/GNOME/pitivi/issues/2381) above the
timeline, that is always zoom-fitted.

Requirements: Python. Minimal experience contributing to Pitivi including unit
tests.


## Timeline enhancements

Fixing timeline issues and making small enhancements would improve a lot the
timeline usability, making it a delight to use Pitivi. See
[GitLab](https://gitlab.gnome.org/GNOME/pitivi/-/issues?label_name%5B%5D=6.+Component%3A+Timeline).

Requirements: Python. Minimal experience contributing to Pitivi including unit
tests.


## Focus on the music

Often people want to pick a nice tune and then sync their weekend clips on it.
To make this easy, Pitivi can detect the beats using a 3rd party library, and
allow aligning and cutting the clips to the beat. It might sound easy, but the
entire experience should be super-polished so it works nice and everybody can do
it.

Requirements: Python, C. Minimal experience contributing to Pitivi including
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

Requirements: Python. Minimal experience contributing to Pitivi including unit
tests.


## Fix GPU support in Pitivi

GStreamer has pretty good GPU support through the OpenGL set of plugins, but
Pitivi/GES is not able to take full advantage of that infrastructure yet, mainly
because of lack of testing and bug fixing on our side. This project is about
enabling GL plugins for compositing and rendering, and fixing any issue that
shows up. The second part would be about making sure hardware accelerated
decoders can be used in the pipelines.

Requirements: C. Experience with GStreamer is mandatory. Minimal experience
contributing to Pitivi including unit tests. Experience with OpenGL is a plus.
