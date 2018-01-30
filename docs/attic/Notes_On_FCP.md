# Notes On FCP

These are some of the notes I made while reading tutorials for Final Cut
Pro, version 6. I have only done some minor editing, and they appear in
nearly their original form. These are just my observations from viewing
screenshots: It is very possible that I have mis-interpreted or missed
some important details altogether.

-Brandon

# The Notes

there are three kinds of tasks

-   acquisition
-   editing
-   mastering/output

timeline clips only have name and single thumbnail. single playback head
decends from timeline ruler across entire timeline video and audio
tracks are separated from each other in separate panes.

each track (audio/video) contains: enable/disable button, label, lock,
two other unidentified markings. tracks appear slightly translucent,
with 3d beveled edges.

zoom control appears to be logarithmic scale, and is a horizontal
slider. rather unsightly mix of aqua, carbon, and custom widgets.

when you import the first clip, final cut asks you if you want to
conform the project/sequence settings to the clip.

smoothcam filter (wow)

filters can be applied to clips in the browser or in the timeline

some filters need to “analyze” the clip before being used. this data is
saved separately from the clip.

you can normalize audio clips to a peak decibel

you can make realtime adjustments to filters applied to a clip, but
there is also a keyframe editor.

audio volume is adjustable by manipulating keyframes overlaid on top of
the waveform (rendered into the audio clip)

portions of the timeline can be sent to other studio applications. when
you save the project in another studio application, the relevant portion
of the final cut timeline is updated in place.

in general apple seems to have broken off pieces of the post production
workflow into separate applications that all understand finalcut's file
format (and possibly use other mechanisms to communicate)...this might
be a UI design choice -- to emphasize the application scope, or it might
simply be to help maximize revenues.

do we have a codec alternative for ProRes 422?

effects are edited with the “canvas” window, which presents a clip
viewer on top, and an editing timeline on the bottom for setting
keyframes.

FCP has stock objects, like colour mattes which can help create title
keys, frames, and backdrops.

FCP allows the use of external title applications

transitions seem to come before the clips they modify, in line with them
on the same track. not yet clear to me whether the visual size of the
transition has anything to do with its duration, or whether the visual
width of the modified clip changes (shrinks) in response to the
transition's presence.
