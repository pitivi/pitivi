# 2008 UI Design

![](images/mockup.png)

# To Be Done

-   Project Render interface description
-   Capture Interface description
-   Markers (critical points) and their uses
    -   multi-point split example
-   Export Audio EDL
-   Object add mock-up
-   Select mock-up
-   Property Editor mock-up
-   Timeline Effects mock-up
-   Compositing mock-up
-   Grouping
    -   use cases and illustrations
-   Linking
    -   use cases and illustrations
-   Tweaks
    -   put track disable control on all mock-ups
    -   put new toolbar commands on all mock-ups
        -   select before, after, above, below, entire layer, entire
            track, all, none
        -   enable/disable object
-   Decide which items go in the Preferences dialog or not

## Editing

# Design Principles

1.  Use direct manipulation for most common operations.
2.  Use noun-verb pattern for most other operations (see below)
3.  Minimize the number of modes. Modes are evil.
4.  Use quasi-modes instead of modes
5.  Provide feedback. Change cursor styles, provide real time updates.

## Noun-Verb Interaction

Select what you want, then issue a command to manipulate it.

-   commands are “verbs” which operate on current selection. These
    commands are only sensitive when valid on the current selection.
    -   provide an easy way to add new commands of this type
-   Only conventional “tool” is the split tool. You activate it first,
    then click where you want to cut.
    -   and we provide a non-modal variant of this that operates on the
        current selection.
    -   don't provide an easy way to create other modal tools

# Representative Tasks

Frequent Tasks

-   finding a specific time in the timeline
-   shifting a clip's start position
-   trimming a clip's in or out position
-   splitting a clip into multiple pieces
-   previewing the project
-   adjusting audio volume or video alpha
-   moving sources between layers
-   adding sources to the timeline
-   deleting sources from the timeline
-   adjusting individual object properties
-   applying an effect to a portion of the timeline

Occasional Tasks

-   moving sources between tracks
-   editing multiple objects simultaneously
-   re-using the same sequence of video repeatedly
    -   possibly with slight-variations
-   linking two arbitrary objects so they stay in sync
-   unlinking linked objects
-   color correcting a source with poor white-balance
-   filtering noise from audio
-   marking significant points in a timeline, such as sound bites from
    an interview or instants at which sound effects should play
-   cutting a source in multiple places

Special Tasks

-   transcoding from original to editing-friendly codecs
-   re-conforming a project
    -   i.e. from work-print quality to full-quality
-   exporting from native to external project formats
-   importing external projects to native pitivi projects

# Overview

![](images/mockup-annotated.png)

there are several primary components:

-   viewer
-   timeline
-   clip library (also referred to as sources browser)
-   property editor
-   effect library
-   main toolbar
-   timeline toolbar

These components all share a single window by default. The Viewer,
Timeline, Clip Library, and Clip Editor, and Effect Library can be
detached from the main window by clicking a special “detach” button.
These windows appear as normal top-level windows. When the user closes
one of these windows, the component returns to its default location. In
addition, the clip editor and viewer can be “expanded” so that they
completely fill their parent windows.

## Keyboard

-   shift, ctrl, alt, and ctrl+alt act as quasi-mode modifiers: they
    must be held down to activate special modes.
-   use alphanumeric keys for more esoteric operations: users are used
    to shift, alt, ctrl acting as modifiers.
-   provide Ctr+<key> shortcuts for menu items
-   arrow keys used for seeking

## Selections

![](images/gselect2.png)

When the mouse moves over a selectable item, it becomes highlighted to
indicate its focus.

![](images/gselect3.png)

Single-clicking on items sets the selection to that item. Selection is
indicated by more prominent highlighting.

-   **shift-click** always adds the object to a selection
-   **ctrl-click** toggles whether the item is selected or not
-   **alt-click** always removes the object from the selection

Whatever the method used, selection is an undoable action.

![](images/gselect4.png) ![](images/select5.png)

Click and drag on blank canvas activates selection marquee. While
dragging the selection marquee, objects that will be selected when the
mouse-button is released indicate focus. It is clear which objects
touched by the marquee will be selected.

-   **shift** extends the selection over a **range**
-   **ctrl** sets the selection to the **intersection** of the current
    selection and the objects under the marquee
-   **alt** removes the objects under the marquee from the selection
-   selecting an empty area clears the selection. This means clicking on
    blank canvas also clears the selection.

![](images/gselect_basic.png)

Some tool-bar commands to modify selection. These are track-wise
operations. The operation will be performed for each track which
contains a selected clip. These operations to not apply to selections of
key-frame points within clips, but they do apply to timeline and
track-level markers.

![](images/gselect_before.png)

“Select before” -- select everything between the start of the project
and the current selection

![](images/gselect_after.png)

“Select After” -- select everything between the end of the project and
the current selection

![](images/gselect_above.png)

“Select Above” -- select everything between the top-most layer and the
current selection

![](images/gselect_below.png)

“Select Below”

![](images/gselect_layer.png)

“Select Entire Layer” -- selects everything else in the layer(s) of the
currently selected source(s)

![](images/gselect_track.png)

“Select Entire Track” -- selects everything else in the track(s) of the
currently selected source(s)

![](images/gselect_none.png)

“Select None” -- remove all items from the current selection

![](images/gselect_all.png)

“Select All” -- select the entire project

# Viewer

Used for playing back video from a variety of sources, primarily the
timeline. Provides basic playback controls, as well as single-frame
forward / rewind.

## Functions of the Viewer

-   displays output of timeline at current position of playhead
-   temporary playback of sources from the browser.
-   temporary feedback of editing operations

## Automatic Preview

During certain edit operations, the it would be useful if the viewer
could show visual feedback of the edit in progress. After operation
ends, viewer returns to previous state.

-   during a roll edit between two sources A, B, viewer should split
    between out point of source A and in point of source B
-   during a drag operation, viewer should show the instant just
    before/after the new source will cut in/out. Based on overlap. If no
    overlap, no preview. If overlap of one source, show that source. If
    overlapping one source at each end, split viewer between them.

## Continuous Loop

The user can lock the viewer into a continuous loop over a portion of
the timeline. In this case, all other seeking behavior is disabled. The
user can make continuous adjustments while the loop plays.

-   need some mechanism to define the area over which to loop.
    -   one thought is to place markers. User can select two markers to
        define an an area and then press the loop command.

# Timeline

![](images/gtimeline_detail.png)

The primary component of the UI. This is where the user directly
manipulates sources and effects which will appear in the final output.
It is a time-proportional representation of the edit decision list.
Clips appear as horizontal rectangles, their with proportional to their
duration, and their position along the x axis proportional to the time
at which they start. The metaphor is of virtual strips of film. The user
can “cut” (meaning split), move, resize, and group (splice?) these
strips.

## Seeking and Navigation Controls

-   scrubbing directly on the timeline ruler will seek to that place in
    the timeline
-   left and right arrow keys seek forward/back single frames at the
    current project framerate.
-   Holding down keys causes repeated seeking.
-   Shift + arrow key seeks over 1/2 second interval
-   Alt + arrow key seeks over 30 interval
-   Ctrl multiplies current seek interval by factor of 10
-   Whenever play-head moves out of view, the Timeline widget should
    scroll to center the play-head in view.

## Tracks

![](images/gMulti_track_editing.png)

The timeline is subdivided into **tracks**. Tracks represent separate
output channels with a single media type. Within a track, all objects
have the same media type, and there is at least one track in the
timeline for every type of media that the timeline contains. The user
does not add or remove tracks directly: the user adds objects to the
timeline, and tracks are created as appropriate. Most projects will only
have one audio and one video track.

Tracks can be expanded or contracted. Expanded tracks stack their clips
vertically, according to the clips' layer position (priority). When a
track is collapsed, all sources appear at the same vertical position, as
if contained within a single layer. This single layer can then be
further collapsed.

### Layers

Tracks are themselves subdivided into layers. Layers are priority levels
within a track. For audio, all layers within a track are mixed together
into a single stream. For video, all sources within a track are
composited together in a single stream. The layer position determines
the order in which videos are composited, with the visually topmost
layer appearing as the top-most source in the stream.

![](images/glayer_addition.png) The user can add layers to a given track by
dragging the track's separator bar downward. Similarly, the user can
remove tracks by dragging the layer's separator bar upward; however,
removal of the bottom layer will only be permitted if the layer is
empty. Objects within layers can be stacked arbitrarily. This is
particularly useful for effects, which operate lower-priority objects
within the timeline.

### Managing Vertical Complexity

![Expanded Layer](images/expanded_layer.png)

Ordinarily, layers take up a fair amount of space. This is to make room
for thumbnails, waveforms, and keyframes.

![Collapsed Layer](images/contracted_layer.png)

Layers and tracks can be contracted to save space. The user can contract
a layer by clicking their expander widgets on the far left side of the
timeline.

![](images/gcontracted_track.png)

This can also be done for entire tracks

### Sources and Effects

![](images/gtimelineobject_detail.png)

Sources and effects (within a track) are content streams of a single
media type. Sources are clips which provide data. Effects are filters
which consume lower priority clips as input and produce filtered output.

Both Source and effect objects have properties. All properties can be
manipulated via the property browser, but some of properties, like audio
volume or video alpha, will be so commonly used that they are embedded
directly onto the widget. These “embedded” interpolation curves are
manipulated in exactly the same way as interpolation curves in the
property editor (see the Default Property Editor section) for more info.

### Moving Timeline Objects

Objects in the timeline can move in both horizontal and vertical axis.
The semantics, however, change depending on the type of object. For all
objects, the horizontal (x) axis is interpreted as the time axis. For
sources an effects, the vertical (y) axis the source's layer position
within a track (tracks are shown visually stacked, but moving a source
between tracks is accomplished through a different mechanism).

### Moving Horizontally

-   All objects in the current selection move simultaneously.
-   Edge snapping when moving multiple items needs to be carefully
    designed so that it is not destructive. A conservative approach
    would be to snap only the beginning and end of the entire selection.

### Edge / Frame Snapping

All objects have edge snapping enabled during horizontal motion. At this
point, we believe this is the most common use case. This edge snapping
effect is intended to be subtle, with a deaband of only a few pixels.

-   Active by default, disabled while holding shift.
-   Exact behavior defined in core. Basic idea is that certain
    timestamps in the timeline act as “magnetic” points which objects
    will tend to “stick” to when they get close enough.
    -   this is already implemented. Just needs to be refined a bit.

### Temporary Deactivation

![](images/gdeactivated_objects.png)

Objects in the timeline can be temporarily deactivated. The deactivate
command is in found in the timeline toolbar, and will deactivate
whatever objects are in the current selection. The reactivate command
undoes this operation.

An entire track can also be suppressed. To do this, click the disable
toggle near the track's name on the left side of the timeline.

## Adding Objects

### Adding a Clip

![](images/gadd_clip1.png) The user chooses the clip from the clip browser by
clicking and dragging.

![](images/gadd_clip2.png) When the object enters the timeline, the timeline
responds by showing how the timeline will change. In this case the clip
has both audio and video streams, so objects appear in both audio and
video tracks.

![](images/gadd_clip3.png) The user can move objects to desired layers and
time offsets.

![](images/gadd_clip4.png) By holding the appropriate modifier key, the user
can push existing objects out of the way...

![](images/gadd_clip5.png) ...or add a source into a new layer.

### Adding an Effect

Effects can be dropped into the timeline in almost exactly the same way
as clips. The main difference is that effects come from the effects
library.

![](images/gadd_effect1.png) User selects the effects library from the tab.

![](images/gadd_effect2.png) When adding effects into a new layer, the layer
is initially collapsed.

## Fine Tuning: Trimming Objects

Trimming a clip is always possible by clicking/dragging on source
trimming handles. By default, the in or out point of a clip should be
edge-snapped (so that it is easy to put the clip back the way it was).
The UI should constrain the setting of in/out point so that sources
can't be stretched beyond maximum native duration. **clicking and
dragging a trimming handle should not change the current selection**

![](images/gtrim1.png)

First, the user moves the mouse over the desired clip's trimming handle

![](images/gtrim2.png)

The cursor changes to a left- or right-edge trimming cursor.

![](images/gtrim3.png)

Click-and drag sets the in or out point of the clip as appropriate.

### Roll Edits

A variant of trimming, which works when two clips are adjacent in the
same layer. Sets the in-point of the left clip an the out-point of the
right clip, keeping the total duration of both sources the constant.
Roll edits are activated by holding the appropriate modifier key while
dragging a trimming handle. Note that this is only expected to work when
it is possible to set the in/out points of both sources to the same
point in time.

![](images/groll1.png)

First the user places the mouse over the appropriate trimming handle.

![](images/groll2.png)

The user holds down the appropriate modifier key. Cursor changes from
trimming to roll-edit cursor.

![](images/groll3.png)

When the user drags the mouse, the edit points are set as appropriate.

![](images/gtrim3.png)

However, if the user releases the roll-edit modifier key, the edit
reverts to the default trimming operation.

### Ripple Edits

This is another variant on basic trimming. The source who's trimming
handle is being manipulated is trimmed as usual, however the adjacent
source(s) are rightward in the appropriate direction, so that the
trimming does not create a gap between the sources. This shifting
carries down the entire length of the track, keeping sources in the same
relative position.

![](images/gripple1.png)

User places cursor over the desired source's trimming handle.

![](images/gripple2.png)

User holds the appropriate modifier key. Cursor changes to ripple cursor

![](images/gripple3.png)

User drags the the mouse. Adjacent sources are shifted.

![](images/gripple4.png)

The user can also hold an additional modifier key to make the ripple
edit work across multiple layers.

If the user releases the ripple-edit modifier key, the edit reverts to
the default trimming operation.

### Time Stretch

Another variant on basic trimming. The source's in/out points are not
set as normal, but rather the source keeps the same in/out points and
the source is sped up or slowed down to accommodate the new duration.
Timestretch only applies to sources of finite length, such as files.

## Linking

There are two methods of combining timeline objects together: linking
and grouping. Linking allows the user to keep distinct timeline objects
synchronized. Moving one object causes all of its linked “sibling”
objects to move. The relative offset between siblings is preserved.

![](images/glink1.png) ![](images/link2.png)

Some clips will be linked by default (for example, audio and video from
the same file).

![](images/glink1.png) ![](images/link3.png)

But the user can link arbitrary objects together as well.

To link objects:

-   set the selection to the objects you wish to link
-   click the “link” command from the timeline toolbar
-   the objects will now remain synchronized

To unlink objects:

-   select one or more objects
-   choose the “unlink” command
-   each object will be unlinked from its siblings separately (the rest
    of the siblings remain linked).

## Grouping

Grouping is similar to linking in that multiple objects are combined,
but different in that the resulting group is treated as a single object.
The user can make multiple “clones” of a single “master”, and changes to
the master will ripple out to each of the clones. Unlike linking,
grouping creates a new “clip” in the Clip Library. Effects applied to
the group apply to the output of the group as a whole, rather than the
topmost object in the group.

![](images/ggrouping1.png) ![](images/grouping2.png)

To group objects:

-   select one or more objects
-   choose the “group” command
-   the original objects are removed from timeline, and the resulting
    group object is substituted.

To ungroup objects:

-   select one or more groups
-   choose the “ungroup” command

TODO: how will we edit the groups? Two approaches: recursive editing, or
“expanding” in place. What are the pros and cons of each? Other issues:
full, partial, or no synchronization of clones.

# Clip Library (formerly Source Browser)

![](images/gclip_library.png)

Contains a list of all the clips in the project. The user can drag
external files onto this component to add them to the project (an import
tool bar command also works. The user adds clips to the Timeline by
dragging them them from the Clip Library and dropping them onto the
Timeline.

The Clip Library also provides commands to manipulate the clips in the
project:

-   remove clips from the library
-   set default edit (in/out) points of a clip
-   convert clips from one media type to another:
    -   e.g. convert audio stream to video stream with a visualization
        filter
    -   e.g. convert midi stream to audio stream with synthesizer plugin
-   re-conform or transcode clips
    -   e.g. re-capture material from a tape at a different resolution
    -   e.g. convert a file “in-place” from MPEG to MJPEG
        -   doesn't replace original file on disk, just in project
        -   and you can revert to the original at any time
-   pre-process and filter clips
    -   e.g. video color correction
    -   e.g. audio noise filtering

# Property Editor

Sharing the same tab view as the source browser is the property editor.
While the timeline is meant to provide a film-strip metaphor, the
property interface allows the user to change the more abstract
properties of the currently selected timeline object(s) (for example,
audio balance, or image color correction). The type of controls
presented are determined by the current selection:

-   accessible at all times by clicking on its tab
-   default interface which simply presents a control for every
    available property should work in the majority of cases
    -   time-varying properties are presented on an interpolation graph
-   but we also need custom editors for specific media types:
    -   still images require a custom interface
    -   animations (image collections) require still another
    -   advanced compositing tools
    -   many effect plug-ins will want to define their own UI
-   In addition, the property editor is displayed whenever the current
    selection changes (unless the change has cleared the selection, in
    which case you see the source library instead).

## Default Property Editor

![](images/gdefault_property_editor.png)

**Goals**

-   auto-generated for arbitrary objects
-   useful in the majority of cases
-   better than nothing when no specific UI exists
-   useful when multiple objects of different types are selected -- the
    common properties can be presented and edited simultaneously.

**Features** The default editor lets you set all of the otherwise hidden
properties of an object. It's will be most usable when the mapping
between an object's properties and their effect on the output is
straightforward. For example, audio volume, our video alpha. The current
implementation of the videobox element is a good example of what won't
work well with this module (a more dedicated UI focused on
cropping/panning would needed).

A few object properties will be static (i.e. they are time invariant).
These will be displayed as standard GTK+ Widgets. Other properties are
“controllable” (i.e. time-varying). The user can directly manipulate the
interpolation curves for these properties through curve control points
objects, which we refer to as “key-frames.” A [partial
prototype](Keyframe_Editing.md) of this design is available.

-   all curves will be plotted on a single graph
-   key-frames points define critical points of an interpolation curve
    -   moving a key-frame horizontally changes its time-stamp
    -   the curve is always plotted between keyframes in sorted order
        (see the key-frame demo)
    -   moving a key-frame vertically sets its value
-   graph supports exactly the same selection idioms as the timeline
-   curves have different colors so they can be visually separated
-   a legend maps colors to curves (labels also appear alongside each
    curve)
    -   click-and-drag on a curve moves all its points vertically by the
        same delta

![](images/gproperties_curve.png)

The user can add key-frames in two different ways ways:

-   double-clicking the curve
-   selecting two key-frames on the same curve and clicking the
    “add-point” command in the tool-bar. this adds a point half-way
    between the two selected points.

The user can delete key-frame points in two different ways:

-   double-clicking a point
-   selecting one or more points and pressing the delete-point button in
    the tool-bar

GStreamer supports different interpolation modes, but only for the
entire curve. Changing the interpolation mode for a single point isn't
possible (we'll have to write our own interpolation code). On the other
hand, it makes sense to treat interpolation mode as a per-point option.
For now setting the interpolation mode on a point will simply set the
interpolation mode on its parent curve.

-   select the desired curve, or a single keyframe of a curve
-   set the desired mode by choosing from the interpolation mode pop-up
    menu in the timeline toolbar.
-   this should also work if multiple curves / key-frames from multiple
    curves are selected.

## Image Property Editor

The user can add still images to the timeline. By default the image is
letterboxed to the current project resolution, but these defaults can be
changed to suit the users's needs.

![](images/gimage_source1.png) First the user selects the image in the
timeline

![](images/gimage_source2.png) The image property editor appears in the
property browser.

![](images/gimgage_source3.png) The user can crop the image to an arbitrary
region.

![](images/gimage_source4.png)

![](images/gimage_source5.png) The user can scale the image as appropriate.

![](images/gimage_source6.png) The user can also set the orientation of the
image.

## Animation Property Editor

NEEDS WORK

Specify sets of pictures which will be displayed in sequence:

-   set duration or framerate
-   set cropping, rotation, scaling
-   transitions between frames? (Ray Harryhausen famously used
    cross-fading between frames for smoother motion)

Other Ideas:

-   background / cell paradigm -- user chooses a back drop, and can
    composite multiple layers of translucent/transparent cells

## Motion Transform Editor

NEEDS WORK

For the “motion transform” effect object (yet to be implemented)

Needs to support the following properties over time

-   cropping
-   scaling
-   rotation

Also need to be able to set the color and/or alpha of the “background”.

Ideas...parametric curves on a 2-d plane? Looping previews?

## Advanced Compositing Editor

NEEDS WORK

Chroma key

-   set thresholds, choose key color (eye-dropper?)

Blue/Green/Red screen

-   set thresholds

Should thresholds and key-color be time varying? Definitely need at
least a local preview. Using the viewer would be better.

## Title Card Editor

The title card editor might look something like this.
![Title Card Editor](images/title_card_editor.png)

# Effect Library

The effect library lists all of the available effects, whether delivered
through plug-ins or internal to PiTiVi. The user can drag-and-drop
effects into the timeline in the same way they can with clips.

# Toolbars

## Main Toolbar

Provides application-level commands:

-   new project
-   open project
-   save project
-   render project
-   full-screen/window mode
-   import clips to project

## Timeline Toolbar

Flush with the edge of the screen in full-screen mode, for easy access
to commands.

Finally, there is one modal tool -- the split tool -- which splits a
clip or effect object into two segments.

Zooming Controls:

-   zoom in
-   zoom out
-   ??

Provides a list of commands which operate on the current selection.

-   delete
-   link
-   unlink
-   group
-   ungroup
-   collapse
-   select right of
-   select left of

In addition, other commands will appear or become sensitive depending on
context - i.e. the current selection.

When one or more curves is in the selection:

-   interpolation mode combo box
-   add and delete point commands

### Zooming and Scrolling

-   Center on scroll position
-   Provide “center on playhead” command
-   Zoom control should provide meaningful zoom levels: 1, 5, 10 frames,
    1, 5, 10, seconds, 1, 5, 10 minutes.
    -   or would we rather have continuous zoom?. After Effects / vegas
        seem to have a very slick continuous zoom.

# Preferences Dialog

This is a list of every imaginable setting that could possibly go in
there. It is intended to be reviewed mercilessly, so that we decide to
accept/deny their inclusion.

-   thumbnail height, expanded/collapsed
-   whether thumbnails are visible
-   whether waveforms are visible
-   previewing options
    -   to be elaborated. May just be part of the menus so that it can
        be accessed in real-time?
-   location of scratch disks
-   default project format (for new projects)
-   hotkey configuration
-   direct manipulation
-   autosave
-   default location to use when opening a file or importing clips
    (last folder, arbitrary location)
-   color values for the timeline ruler and the background of clips
-   whether edge snapping is enabled by default
-   the size of deadband to use for edge snapping
