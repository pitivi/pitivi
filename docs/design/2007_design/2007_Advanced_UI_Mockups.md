# 2007 Advanced UI

Also known as Brandon's Design.

## Basic Design

In basic design goal is to provide as much direct-manipulation as
possible. In this case, properties interpolation graphs are overlaid
atop source widgets directly. The properties can be shown/hidden with
the property selection popup at the bottom of the source. In addition,
the interpolation mode can be set for the currently selected
interpolation graph. The interpolation graph is manipulated with
“keyframes” which are dragable handles that adjust the timestamp and
keyframe.

-   When a source in the timeline moves, the viewer needs to seek just
    before that source's in point in the timeline.
-   When the user adjusts the in-point or out-point of a source, the
    viewer needs to seek to the new in or out point in the source
-   When the user adjusts a keyframe, the viewer needs to seek to that
    point in the timeline and show the user a preview of the change

![](images/Advaced_ui_separated_keyframes.png)

## Separated-keyframes variant

The basic design doesn't address the problem of keyframes in
SimpleEffects, which don't have room to display interpolation graphs. In
this variant, the keyframe interpolation graphs have been moved directly
below the timeline. Selecting any object (or group of objects, the
color-balance effect in this mock-up is selected) causes its properties
to be displayed in the property editing region below. Not shown are the
key-frame handles, which would not become visible until objects within
the key-frame window are selected.

All keyframed properties are initially flat lines. These lines can be
moved up or down simply by clicking/dragging.

At this point it is not yet clear which variant would be preferable. It
is also not yet clear how the user will add or remove key-frames.
Possibilities are:

-   click directly on the graph and a new keyframe appears if one hasn't
    been created (means that the line as a whole isn't movable. have to
    select both end-points)
-   select a keyfame then click “add” (user can't control where new
    frame is added, so a second adjustment step is required)

![](images/Advaced_ui_separated_keyframes.png)

## Expanded/Contracted Variant

The similar to the basic design, but objects can be expanded to take up
a maximal amount of screen space. This extra space is used to display
the interpolation graphs.

![](images/Advanced_ui_expanded_contracted.png)

# Kiddo's Design

## General Timeline Overview

Features in this mockup:

-   nice looking clips representation on the timeline, maybe in cairo?
-   arrows on the left and right sides of the clips to allow setting the
    beginning/end (only works in the advanced timeline, because the
    clips' widths are proportional to their duration). If the user zooms
    out or the clip is too short, these arrows should “squeeze”
    themselves, and, below a certain threshold, disappear completely.
    The user will still be able to manipulate the begin/end points by
    dragging the sides (borders) of the clip.
-   thumbnails displayed when enough space is available *and when the
    user has not deactivated them in the preferences*
-   notice how the proportions of the various components of the UI are
    different from the simple timeline. Here, the video preview and
    media library are smaller, pushed to the top, to leave a lot more
    space for the timeline itself. In a multitrack non-linear editor,
    you want the timeline to be the main zone of interaction and
    maximize the amount of space you have to play with it
-   waveform previews for audio, ripped straight out of
    [Jokosher](http://www.jokosher.org)
-   the layer buttons on the left are there just for making the mockup
    look less empty, they should be replaced by relevant ones
-   notice the transition indicators on the bottom clip and the
    top-right clip: some white “curve” allows you to see the speed of
    transitions such as crossfades and fade-in/out
-   the clip displayed on the layer “bg actors” has a motion curve (the
    thing called “velocity curve” in Vegas Video). You might want to
    look at Jokosher's code that was used for their audio volume curves,
    it would be great to be able to control the volume/opacity/speed of
    an audio/video clip using curves everywhere as “keyframes”.
-   this user interface's **audio and video tracks are separated**. Do
    not be fooled by the looks. It was just me being lazy (and
    forgetting to show audio tracks everywhere). Basically, what you are
    seeing in this mockup is a bunch of “silent clips with no audio” (or
    clips whose audio tracks were removed in favor of one sound track)
-   “pyrotechs” and “bg actors” are just track “names” (or “labels”)
-   this was made from a screenshot of the French version of pitivi, so
    a few terms might seem odd. For example “Piste vidéo” means “Video
    track”.
-   this whole timeline is \*HUGE\*. This would be in a case where the
    user has big toolbars in his gnome preferences, and where he
    stretched up the layer's height (because, realistically, the layer
    heights should be maybe ½ of that to avoid eating up too much screen
    height).

![](Pitivi-advanced-mockup.png "Pitivi-advanced-mockup.png")

I would be a strong proponent in favor of **having only one timeline for
PiTiVi, the advanced one**. I mean, I really don't think that a
multitrack UI like that is harder than the “imovie-simplified like”
counterpart. This multitrack interface **is** scalable from the newbie
to the professional, *if* you design, *think* the user interface really
well (you can leave that to me ;). **I believe a “direct manipulation”
multitrack “time-proportional” timeline interface kicks the hell out of
the current “simplified interface”**, and will need no significant
learning curve, even for grandma. The rest can be done with nice
tutorial screencasts that I would gladly provide, and that would give
the advantage of not splitting the coding workforce over two timelines.
Do one thing, and do it so well that grandma's jaw drops (not from
natural cause)! --[Kiddo](User:Kiddo.md) 23:28, 10 June 2007
(BST)
