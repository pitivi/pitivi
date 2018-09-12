# Timeline

The **Timeline** object:

Those TimelineObjects can control one or many TrackObjects from one or
many Tracks of the Timeline.

The goal of the **Timeline** is to offer an API suited for fast UI
coding. The UI can then decide whether to listen to events/modifications
taking place on the overall Timeline, or on the individual Tracks.

> This allows both creating simple and complex UI while offering the
> same interfaces

**All of the following editing actions must be done on the `Timeline`,
`TimelineObject`(s) or `TimelineSelection`s** and not on the `Track`(s)
or `TrackObject(s)`:

-   Adding objects to the Timeline
-   Removing objects from the Timeline
-   Linking and Unlinking objects
-   Grouping and Ungrouping objects
-   Moving objects
-   Changing objects priority
-   Trimming, Sliding, Rolling, and all other actions modifying any of
    `start duration in-point out-point priority`.

## Contents

-   One or many **Track**s corresponding to the **Project Settings**.
    There is one **Track** per output **Stream**s (Most projects will
    therefore have 2 Tracks, one for the Audio stream and one for the
    Video stream).
-   An ordered collection of **TimelineObjects**. Those objects can be
    Sources (producing content) or Operations (modifying content).
-   A list of **Selections**, grouping several existing TimelineObject.
    -   This is a convenience for modifying several distinct
        TimelineObjects at the same time.
    -   A **TimelineObject** can belong to several **TimelineSelection**
    -   A **TimelineSelection** can control one or many properties to
        keep the modifications of those properties in sync
        (start-position, priority, in-point, out-point, ...)
-   The **TimelineFactory**, used in the
    [Pipelines](design/2008_design/2008_Architectural_Redesign/Pipeline.md) (for viewing,
    rendering, ...).

## Timeline properties

`tracks` : Ordered list of `Tracks` controlled by the `Timeline`
`selections` : List of `TimelineSelection` in use.
`objects` : Ordered list of `TimelineObject` controlled by the `Timeline`. First ordered by `start` property, and then by `priority`.
`factory` : The `TimelineFactory` to use in `Pipeline`s.

## Track properties

`objects` : Ordered list of `TrackObject`s controlled by the Track.
`stream` : The `Stream` of the Track.

## TimelineObject properties

![](images/Anatomy_of_timeline_object.png)

`factory` : The ObjectFactory this TimelineObject corresponds to.
:   None is an accepted value

`start` : The position of the TimelineObject.
`duration` : The duration of the TimelineObject.
`in-point` : The in-point of the contents of the TimelineObject.
`out-point` : The out-point of the contents of the TimelineObject.
`priority` : The priority of the TimelineObject.
`min-start` : The earliest time to which we can set the start property of the TimelineObject with the trimStart method
`max-duration` : The maximum value we can set the duration property of the TimelienObject to

<!-- -->

; `track-objects` :: The TrackObject(s) it the TimelineObject controls.
; `track` : the track to which the object belongs
; `object` : The actual TrackObject
; `time-offset` : The offset between the TimelineObject `start` position and the TrackObject `start` position. ALWAYS POSITIVE.
; `priority-offset` : The offset between the TimelineObject `priority` and the TrackObject `priority`. ALWAYS POSITIVE.

## TimelineSelection properties

`objects` : The list of TimelineObject controlled by the `TimelineSelection`

## TrackObject properties

![](images/Anatomy_of_trackobject.png)

`parent` : The `TimelineObject` controlling this `TrackObject`. All the properties below **MUST NOT BE MODIFIED DIRECTLY** but through the `parent` TimelineObject.
`start` : The position of the TrackObject.
`duration` : The duration of the TrackObject.
`in-point` : The in-point of the contents of the TrackObject.
`out-point` : The out-point of the contents of the TrackObject.
`priority` : The priority of the TrackObject.

# Relationships

## Between Timeline and Track(s)

The diagram below shows the relationship between Timeline, Tracks,
TimelineObject and TrackObjects.

Each TimelineObject controls at least one TrackObject in any of the
Timeline's Tracks.

> We can see here that the two first TimelineObject control one
> TrackObject per Track. But the last TimelineObject only controls a
> TrackObject in the first Track.

Each TrackObject of a given TimelineObject can have a relative offset

> This can be seen with the 2nd TimelineObject where the TrackObject it
> controls in the second track doesn't start at the same position.

![Relationship between Timeline and
Track](Timeline-track-relationship.png "Relationship between Timeline and Track")

## Between containers, TimelineObject and ObjectFactory

The following diagram shows the relationship between:

-   Containers
    -   Timeline
    -   Track
-   Objects
    -   At the Timeline level : TimelineObject
    -   At the Track level : TrackObject
-   ObjectFactory
    -   At the Timeline level : ObjectFactory
    -   At the Track level : Streams(s) of an ObjectFactory

![Relationship between TimelineObject, Containers and
ObjectFactory](Timeline-track-objectfactory-relationship.png "Relationship between TimelineObject, Containers and ObjectFactory")

With the diagram above, the use-case of adding a source file to a
Timeline becomes trivial:

-   Pick the ObjectFactory corresponding to your source file
-   Add it to the Timeline
    -   The Timeline creates a TimelineObject compatible with the given
        ObjectFactory type
        > Timelines can therefore reject incompatible ObjectFactory like
        > Live devices

    -   The timeline looks for what Streams the ObjectFactory can
        consume/provide
    -   For each of the Streams that the ObjectFactory handles:
        -   Find a Track with a compatible Stream
            > The user can of course choose his own Stream&lt;=&gt;Track
            > mapping

        -   Create a TrackObject for that ObjectFactory Stream
        -   Add the TrackObject to the Track
        -   Link the TrackObject to the newly created TimelineObject

## Between TrackObject and GStreamer

The following diagram shows:

-   On the left, the class hierarchy for TrackObject
-   On the right, the class hierarchy for the various GNonLin GStreamer
    elements.

The links between TrackObject(s) and GnlObject(s) show their
relationship. ![Relationship between TrackObject(s) and the GStreamer
element they
control](Trackobject-gnonlin-relationship.png "fig:Relationship between TrackObject(s) and the GStreamer element they control")

# Use cases

## Unlinking two TrackObjects

![Unlinking two TrackObjects coming from the same
ObjectFactory](Timeline-object-unlinking.png "Unlinking two TrackObjects coming from the same ObjectFactory")

We have a TimelineObject 'X' controlling two TrackObject 'A' and 'B'
coming from a common ObjectFactory 'O'. This is the most common case
when adding a Audio+Video File to the Timeline.

We want to handle the TrackObject(s) separately. Maybe to offset them,
maybe to remove one of the TrackObject, ...

-   We ask to unlink a certain TrackObject (B) from its controlling
    TimelineObject (X).
-   The TimelineObject (X) looks for the ObjectFactory (O) from which
    the TrackObject (B) was created. In this case there's only one
    ObjectFactory, but there could be several in the case of
    LinkedSources.
-   It creates a new empty TimelineObject (Y) for the selected
    ObjectFactory (O). That new TimelineObject is a complete clone
    of (X) except for the list of TrackObject(s) it controls.
-   It removes the TrackObject (B) from the list of objects it's
    tracking. This means that:
    -   \(B) temporarily has no controlling TimelineObject.
    -   The TrackObject (B) has NOT been removed from the Track to which
        it belonged.
-   It adds the TrackObject (B) to the list of objects controlled by the
    new TimelineObject (Y).

## Linking Two TrackObjects

### That come from the same ObjectFactory

![Linking two TrackObjects coming from the same
ObjectFactory](Timeline-object-linking-simple.png "Linking two TrackObjects coming from the same ObjectFactory")

This is the case when we had two TrackObjects originally belonging to
the same TimelineObject, but which we unlinked.

-   We ask to link a TrackObject (B) to a TimelineObject (X).
-   The TimelineObject (X) compares the originating ObjectFactory of the
    TrackObject (B) and sees they are the same.
-   The TimelineObject (X) unsets the TrackObject (B) from its current
    parent TimelineObject (Y)
    -   If (Y) is no longer controlling any TrackObjects, we remove it
        from the Timeline.
-   The TimelineObject (X) adds the TrackObject (B) to its list of
    controlled TrackObject.

### That come from different ObjectFactory

![Linking two TrackObjects coming from different
ObjectFactory](Timeline-object-linking-advanced.png "Linking two TrackObjects coming from different ObjectFactory")

This is for the more generic case of linking two TrackObjects. A common
example is when we recorded Audio and Video on separate devices/files.

-   We ask to link TrackkObject (B) to TrackObject (A)
-   We see they belong to originated from completely different
    ObjectFactory, requiring a new TimelineObject to control the two.
-   Since we don't want to lose the original relationships between
    TrackObject and ObjectFactory, we create a LinkedtimelineObject
    (XY), wrapping the two previously existing TimelineObject (X and Y).
    -   **Possibility** : Since all TimelineObject have a counterpart
        ObjectFactory, we could automatically create a
        LinkedObjectFactory for the LinkedTimelineObject (XY) we just
        created
        -   This allows infinite reuse of objects created in the
            Timeline.

# Remaining issues

-   Does core need to provide some help for the UI's marker/keyframe
    handling ?
-   How do we 'properly' handle the different kinds of linkage in
    LinkedTimelineObject
    -   Some people might just want to have synchronized 'start'
        positions, but independent priorities for the TrackObjects.
    -   Some people might want to have the priorities synchronized, but
        freely move the positions of the TrackObjects.
