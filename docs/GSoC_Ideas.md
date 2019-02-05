# Project Ideas for the Google Summer of Code

These ideas can be used as a base for writing a detailed project proposal if you want to apply for a [GSoC internship](Google_Summer_of_Code.md). You are welcome to come up with your own ideas.

## Effects usability (mentor: Alexandru "aleb" Băluț)
 * Brief explanation: The main task would be to improve the Effects discovery experience, and find a way to make a set of whitelisted effects easily accessible. We should take into account also the effects used most often by the user. Depending on what ideas we explore and how much this takes, a potential second task is related to the consistency of the UI for configuring effects. For example, quite a few effects for which the configuration UI is generated automatically allow specifying a color, but the UI is very rough—We should create a polished widget to be reused in all these cases for selecting or specifying a color.
 * Requirements: Python, eye for detail. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.
 * Relevant issue: [#2146](https://gitlab.gnome.org/GNOME/pitivi/issues/2146).

## Media Library improvements (mentor: Alexandru "aleb" Băluț)
 * Brief explanation: The first task would be to refactor the Media Library, to replace the two separate widgets we use for the list view and the icon view with a single flexible [Gtk.FlowBox](https://lazka.github.io/pgi-docs/#Gtk-3.0/classes/FlowBox.html#Gtk.FlowBox) widget. The second task would be to allow basic tagging of clips and search based on tags. A stretch goal would be to prepare for advanced clips filtering in the Media Library, based on tags.
 * Requirements: Python, eye for detail. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.
 * Relevant issues: [#1343](https://gitlab.gnome.org/GNOME/pitivi/issues/1343), [#537](https://gitlab.gnome.org/GNOME/pitivi/issues/537).

## Render UI (mentor: Alexandru "aleb" Băluț)
 * Brief explanation: The main task would be to improve the Render experience. The Render dialog has options the users should not need to care about. This will be an exploratory task, in close contact with the GNOME Designers team. In addition, the experience when using the encoders settings dialog can be improved for important encoders.
 * Requirements: Python, eye for detail. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.

## Render queue (mentor: Mathieu Duponchelle)
 * Brief explanation: Currently when starting a render, the edit functionality is blocked until the render is done. The main task would be to render in the background. The second task would be to have a render queue.
 * Requirements: Python. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.

## Render only a portion of the timeline (mentor: Alexandru "aleb" Băluț)
 * Brief explanation: The user should be able to specify an interval on the timeline, and be able to render only that.
 * Requirements: Python. Minimal experience contributing to Pitivi. Experience with GStreamer would be a big plus.
 * Relevant task: [[https://phabricator.freedesktop.org/T2718|T2718]].

## Nested timelines/projects (mentor: Thibaut "thiblahute" Saunier)
 * Brief explanation: The user should be able to use a project as if it was a clip in the timeline, meaning that he could separate the scene in different sub projects so better organize complex cuts. This project will focus on the User Interface to expose the feature that needs to be finalized in GStreamer Editing Services.
 * Requirements: Python. Minimal experience contributing to Pitivi. Experience with the GStreamer Editing Services would be a big plus.
 * Relevant issue: [#500](https://gitlab.gnome.org/GNOME/pitivi/issues/500).

## Fix GPU support in Pitivi (mentor: Thibaut "thiblahute" Saunier)
 * Brief explanation: GStreamer has pretty good GPU support through the OpenGL set of plugins, but Pitivi/GES is not able to take full advantage of that infrastructure yet, mainly because of lack of testing and bug fixing on our side. This project is about enabling GL plugins for compositing and rendering and fix any issue that raise. The second part would be about making sure hardware accelerated decoders can be used in the pipelines.
 * Requirements: C. Some experience contributing to Pitivi and GStreamer.  Experience with GStreamer is mandatory.  Some experience with OpenGL is a plus.
