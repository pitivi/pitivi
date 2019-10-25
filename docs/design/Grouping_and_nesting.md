# Grouping and nesting

This page is intended to discuss the following concepts:

-   Infinite clip grouping (vs the old “grouping vs linking” approach)
-   “Compound” clips (a more visual form of grouping)
-   Nested timelines/projects

For the following objects:

-   Management of clips on the timeline canvas
-   Project management in general

# Proposal: Recursive Pitivi

When managing video projects of more than trivial complexity, it is
often crucial to be able to treat a group of objects on the timeline as
a unified object, from a user interface perspective. We are interested
in finding methods of grouping that provide maximum user productivity at
minimum development cost.

## Recursion via GStreamer

At one extreme, the minimum development cost approach is one that
requires exactly no code within Pitivi (or GES). Instead, we may create
a new gstreamer decoder element (e.g. pitividec) that takes as its input
the contents of a Pitivi project file. This decoder would reuse the GES
core to expose an interface equivalent to decodebin.

Once such an element is appropriately registered, decodebin,
uridecodebin, and playbin will be able to play Pitivi project files as
if they were video clips. This means that Pitivi project files would,
with no additional code, become playable in gstreamer-based players such
as Totem (subject to CPU limitations, of course). Naturally, it also
means that they are importable as clips into Pitivi itself, for use in
higher-level timelines.

In effect, this approach is equivalent to rendering out the project to
an intermediate clip that is then imported into another project, except
that it avoids the cost in disk space and compression loss. A
sufficiently advanced implementation might also negotiate output
parameters such as resolution to avoid unnecessary scaling.

### Limitations

The disadvantage of this approach is that it does not provide the full
flexibility of traditional grouping mechanisms. There is no way to
“ungroup” (i.e. to flatten a part of the group hierarchy). There is no
way to edit a group within the context of the larger project. This
functionality may be worth implementing but it is not sufficient on its
own to satisfy all our group management needs.

## Internal Recursion

To provide more advanced functionality, we will require recursion that
is not opaque to the Pitivi user interface. In Pitivi, source clips are
immutable, and this invariant seems worth preserving for the sake of
predictable behavior. Therefore, if groups are to be editable (and
distinct from ordinary clips), they should not be implemented via the
standard clip mechanism as described above.

To allow the user interface to behave differently for groups than for
individual clips, while still preserving a simple recursive structure,
one solution is to have entire Pitivi sub-projects defined within a
single project file, and inserted into the timeline as a
timeline-object. Then the “group” action generates a subproject
equivalent to the selected items, deletes those items from the timeline,
and adds the subproject-object to the timeline in their place. “Ungroup”
does the reverse.

### Possible implementation in GES

We should have a GESTimelineTimelineObject class (better name to be
found?), This class is a subclass of GESTimelineSource thus it is a
wrapper around GnlSource (which is a GstBin itself), this bin would
contain a GESTimeline. Then the TrackObject of this TimelineObject
contain GESTrack themselves. We should have 3 ways of creating a
GESTimelineTimelineObject:

```
   ges_timeline_timeline_object_new()
   ges_timeline_timeline_object_new_from_objects (GList *timeline_object) /*So we can group them easyly */
   ges_timeline_timeline_object_new_from_project (const gchar *project_file_uri)
```

The timeline contained in a GESTimelineTimelineObject can obviously also
contain themselves a GESTimelineTimelineObject so we can infinitely
recurse.

#### New Classes

```
   GESTimelineSource
       +---- GESTimelineTimelineObject

   GESTrackSource
       +---- GESTrackTrackObject
```

### UI Niceties

Because the UI can easily determine that a timeline-object is in fact a
group, that object may be treated specially for UI purposes. In addition
to exposing an Ungroup action, the object may also present an “Edit
Group” option. This would open a new timeline (perhaps a new Pitivi
window) showing the contents of the group, allowing the user to make
alterations without the clutter of the entire super-project.

### Open Questions

Should it be possible to cut, stretch, or apply effects to a group?
Doing so potentially makes it impossible to “ungroup” (if, for example,
effects are applied on top of transitions), and certainly makes
ungrouping require a certain amount of tricky logic to propagate global
actions (like chopping out a chunk in time) down to the source clips. (I
think that it should be possible to apply such effects and arbitrary
operations to a group, and that Ungroup should simply be disabled until
all modifications to the group are removed.)

Should groups be displayed in the superproject with “holes” in time
where there is an empty time in the subproject timeline, or should they
simply be continuous? Should there be a mode where even more of the
internal structure is visible? (I think that, for a first
implementation, leaving them as continuous in the superproject UI is
entirely sufficient and dramatically simpler to implement than the
alternatives.)

Is the duration of a group fixed or variable? If it is fixed, then we
will need some UI to indicate a timeline of fixed duration (in the
subproject editor). If it is variable, then what happens when the user
uses the subproject editor to make the contents of the group longer?
Should it expand in the super-project, or should excess time be ignored.
(I think excess time should be ignored, with duration controlled
exclusively from the super-project. Ideally, it should be possible to
modify duration (and start-point) non-destructively from the
super-project, and the subproject editor UI should indicate which
portions of its timeline are actually in use in the super-project.)

Should it be possible to copy a group by reference or only by value?
i.e. can there exist multiple objects in a timeline that refer to the
same subproject? (I think copy-by-reference is too valuable to give up,
but careful UI design will be required to avoid creating massive
confusion. A unique name for each subproject, displayed in every
superproject timeline-object that references it, might help.)

### Limitations

If a group is representable as a single object, then it cannot span
non-contiguous layers in the timeline. Specifically, in current video
editors it is possible to create a group that contains (partially
transparent) content at Layer 1 and Layer 3 but none at Layer 2, so that
a timeline object that is not part of the group may be blended between
two objects that are part of the group. (In my view, this behavior is
not really desirable, and the simplicity of “a group is a timeline
object” is worth the loss of functionality.)

# Infinite clip grouping

The notion of grouping/linking as it was in [0.15](releases/0.15.md) and
earlier is nonsensical from a user's point of view. More details in [bug
583266](https://bugzilla.gnome.org/show_bug.cgi?id=583266).

As a user, I want infinite grouping (like in Inkscape), not have to make
a theoretical distinction between linking and grouping.
