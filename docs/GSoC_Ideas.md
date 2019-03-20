---
short-description: GSoC project ideas we thought about
...

# GSoC Project Ideas

These ideas can be used as a base for writing a detailed project proposal if you want to apply for a [GSoC internship](Google_Summer_of_Code.md). You are welcome to come up with your own ideas.

To create a detailed proposal, use [GNOME's GSoC application template](https://wiki.gnome.org/Outreach/SummerOfCode/Students#Fill_out_the_Application).

## Focus on the music
 * Brief explanation: Often people want to pick a nice tune and then sync their weekend clips on it. To make this easy, Pitivi can detect the beats using a 3rd party library, and allow aligning and cutting the clips to the beat. It might sound easy, but the entire experience should be super-polished so everybody can do it.
 * Requirements: Python, C. Minimal experience contributing to Pitivi.
 * Mentor: Mathieu Duponchelle

## Face blurring
 * Brief explanation: We should make it easy to blur faces. We can use an existing 3rd party plugin to analyze the video and report the location of the faces. The resulting data can be used to blur a specific face. The challenge is making this process as friendly as possible.
 * Requirements: Python. Minimal experience contributing to Pitivi.
 * Mentor: Mathieu Duponchelle

## Closing credits
* Brief explanation: For [end credits](https://en.wikipedia.org/wiki/Closing_credits) and other advanced text display, we could use the new [GStreamer WPE](https://www.youtube.com/watch?v=no7rvUk8GqM) element in [gst-plugins-bad](https://gitlab.freedesktop.org/gstreamer/gst-plugins-bad/tree/master/ext/wpe), which can display an HTML page as a video element. The first task would be to create a scroll mechanism by extending the GStreamer navigation event API with a scroll event type, and adding support in GstWPE. As GstWPE is a live source it does not allow seeking (getting frames at random positions), so the second task would be to add logic in Pitivi for creating an HQ proxy file out of the page being scrolled, which can be used in the project timeline as any other video clip. The third part would be a simple UI in Pitivi for easily creating the closing credits HTML, and managing the proxy file.
* Requirements: C, Python. Minimal experience contributing to Pitivi.
* Mentor: Philippe Normand

## Media Library improvements
 * Brief explanation: The first task would be to refactor the Media Library, to [replace the two separate widgets](https://gitlab.gnome.org/GNOME/pitivi/issues/1343) we use for the list view and the icon view with a single flexible [Gtk.FlowBox](https://lazka.github.io/pgi-docs/#Gtk-3.0/classes/FlowBox.html#Gtk.FlowBox) widget. The second task would be to [allow basic tagging of clips in the Media Library](https://gitlab.gnome.org/GNOME/pitivi/issues/537), and extend the search functionality to work on tags. The remaining time could be allocated to prepare for advanced clips filtering in the Media Library, based on tags.
 * Requirements: Python, eye for detail. Minimal experience contributing to Pitivi.
 * Mentor: Alexandru "aleb" Băluț

## Effects usability
 * Brief explanation: The main task would be to improve the Effects discovery experience, and find a way to make a set of [whitelisted effects easily accessible](https://gitlab.gnome.org/GNOME/pitivi/issues/2146). We should take into account also the effects used most often by the user. Depending on what ideas we explore and how much this takes, a potential second task is related to the consistency of the UI for configuring effects. For example, quite a few effects for which the configuration UI is generated automatically allow specifying a color, but the UI is very rough—We should create a polished widget to be reused in all these cases for selecting or specifying a color.
 * Requirements: Python, eye for detail. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.
 * Mentor: Alexandru "aleb" Băluț

## Timeline interval
 * Brief explanation: The initial task would be to allow the user to specify an [interval on the timeline](https://gitlab.gnome.org/GNOME/pitivi/issues/1842). The next tasks follow up on this: playing the interval in a loop, or [rendering only the interval](https://gitlab.gnome.org/GNOME/pitivi/issues/1006) instead of the entire timeline of the project, or zoom-fitting the timeline on the selected interval.
 * Requirements: Python. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.
 * Mentor: Alexandru "aleb" Băluț

## Render experience
 * Brief explanation: The Render dialog has options the users should not normally need to care about. This will be an exploratory task involving usability studies with people. You'll have the opportunity to learn about usability studies. We'll be in close contact with the GNOME Designers team. The experience when using the Encoder Settings dialog could similarly be improved for one or more important encoders.
 * Requirements: Python, eye for detail. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.
 * Mentor: Alexandru "aleb" Băluț

## Render queue
 * Brief explanation: Currently when starting a render, the edit functionality is blocked until the render is done. The main task would be to render in the background. The second task would be to have a render queue with a simple management UI.
 * Requirements: Python. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.
 * Mentor: Mathieu Duponchelle

## Nested timelines/projects
 * Brief explanation: The user should be able to use a project as if it was a clip in the timeline, allowing to [separate the scene in different sub projects](https://gitlab.gnome.org/GNOME/pitivi/issues/500) to better organize complex projects. The focus will be on the User Interface to expose the feature that needs to be finalized in [GStreamer Editing Services](GES.md). A usability study can be performed, which you have the opportunity to learn about.
 * Requirements: Python. Minimal experience contributing to Pitivi. Experience with the GStreamer Editing Services would be a big plus.
 * Mentor: Thibault "thiblahute" Saunier

## Fix GPU support in Pitivi
 * Brief explanation: GStreamer has pretty good GPU support through the OpenGL set of plugins, but Pitivi/GES is not able to take full advantage of that infrastructure yet, mainly because of lack of testing and bug fixing on our side. This project is about enabling GL plugins for compositing and rendering and fix any issue that shows up. The second part would be about making sure hardware accelerated decoders can be used in the pipelines.
 * Requirements: C. Experience with GStreamer is mandatory. Minimal experience contributing to Pitivi. Experience with OpenGL is a plus.
 * Mentor: Thibault "thiblahute" Saunier
