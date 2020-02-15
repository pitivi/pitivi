---
short-description: GSoC project ideas we thought about
...

# GSoC Project Ideas

These ideas can be used as a base for writing a detailed project proposal if you want to apply for a [GSoC internship](Google_Summer_of_Code.md). You are welcome to come up with your own ideas.

To create a detailed proposal, use [GNOME's GSoC application template](https://wiki.gnome.org/Outreach/SummerOfCode/Students#Fill_out_the_Application).

## Render experience
 * Brief explanation: The render dialog should be simplified to avoid overwhelming the users, while still allowing full control. The dialog with the advanced settings of the encoders should similarly be improved for the officially supported encoders. In preparation, the render dialog should be [refactored into a perspective](https://gitlab.gnome.org/GNOME/pitivi/issues/2382).
 * Requirements: Python, eye for detail. Minimal experience contributing to Pitivi.
 * Mentor: Alexandru "aleb" Băluț

## Focus on the music
 * Brief explanation: Often people want to pick a nice tune and then sync their weekend clips on it. To make this easy, Pitivi can detect the beats using a 3rd party library, and allow aligning and cutting the clips to the beat. It might sound easy, but the entire experience should be super-polished so everybody can do it.
 * Requirements: Python, C. Minimal experience contributing to Pitivi.
 * Mentor: Mathieu Duponchelle

## Face blurring
 * Brief explanation: We should make it easy to blur faces. We can use an existing 3rd party plugin to analyze the video and report the location of the faces. The resulting data can be used to blur a specific face. The challenge is [making this process as friendly as possible](https://gitlab.gnome.org/GNOME/pitivi/issues/1942).
 * Requirements: Python. Minimal experience contributing to Pitivi.
 * Mentor: Mathieu Duponchelle

## Closing credits
* Brief explanation: For [end credits](https://en.wikipedia.org/wiki/Closing_credits) and other advanced text display, we could use the new [GStreamer WPE](https://www.youtube.com/watch?v=no7rvUk8GqM) element in [gst-plugins-bad](https://gitlab.freedesktop.org/gstreamer/gst-plugins-bad/tree/master/ext/wpe), which can display an HTML page as a video element. As GstWPE is a live source it does not allow seeking (getting frames at random positions), we have to add logic in Pitivi for seamlessly creating a video file out of an animated HTML page. The resulting file can be used in the project timeline as any other video clip. You'd have to extend the UI with a new [perspective](https://gitlab.gnome.org/GNOME/pitivi/blob/master/pitivi/perspective.py) for managing the closing credits HTML, and the corresponding video files.
* Requirements: Python. Minimal experience contributing to Pitivi.
* Mentor: Philippe Normand

## Media Library improvements
 * Brief explanation: The first task would be to refactor the Media Library, to [replace the two separate widgets](https://gitlab.gnome.org/GNOME/pitivi/issues/1343) we use for the list view and the icon view with a single flexible [Gtk.FlowBox](https://lazka.github.io/pgi-docs/#Gtk-3.0/classes/FlowBox.html#Gtk.FlowBox) widget. The second task would be to [allow basic tagging of clips in the Media Library](https://gitlab.gnome.org/GNOME/pitivi/issues/537), and extend the search functionality to work on tags. The remaining time could be allocated to prepare for advanced clips filtering in the Media Library, based on tags.
 * Requirements: Python, eye for detail. Minimal experience contributing to Pitivi.
 * Mentor: Alexandru "aleb" Băluț

## Cut perspective
 * Brief explanation: The most tedious process of video editing is the initial cutting and structuring of the global timeline. A new perspective similar to the [EditorPerspective](https://gitlab.gnome.org/GNOME/pitivi/blob/master/pitivi/editorperspective.py) will offer a [second timeline representation](https://gitlab.gnome.org/GNOME/pitivi/issues/2381) above the timeline, that is always zoom-fitted. This could build on the [markers functionality](https://gitlab.gnome.org/GNOME/pitivi/blob/master/pitivi/timeline/markers.py) to allow for pre-insertion trimming.
 * Requirements: Python. Minimal experience contributing to Pitivi.
 * Mentor: Thibault "thiblahute" Saunier

## Fix GPU support in Pitivi
 * Brief explanation: GStreamer has pretty good GPU support through the OpenGL set of plugins, but Pitivi/GES is not able to take full advantage of that infrastructure yet, mainly because of lack of testing and bug fixing on our side. This project is about enabling GL plugins for compositing and rendering, and fixing any issue that shows up. The second part would be about making sure hardware accelerated decoders can be used in the pipelines.
 * Requirements: C. Experience with GStreamer is mandatory. Minimal experience contributing to Pitivi. Experience with OpenGL is a plus.
 * Mentor: Thibault "thiblahute" Saunier
