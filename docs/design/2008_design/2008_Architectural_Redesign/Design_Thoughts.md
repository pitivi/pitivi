# Design Thoughts

This is a listing, not entirely sorted, of thoughts, remarks, things to
do, regarding PiTiVi's design, uses, etc...

Eventually, these ideas/thoughts/remarks ... will end up being split up
for a full-size (re)design/refactor document.

They could be sorted as following:

-   Coding Style : Urgent
-   Core Features
-   (long term) goals
-   Vision (use cases ?)

## Code Review

-   What is too slow ?
-   What is not flexible enough ?
-   What is not re-usable ?
-   What is hard to use ?
-   What is unclear ?
-   What is not needed ?
-   What is in the wrong location ?
    -   Split up code

Actual inline-review done in the 'code-review' branch here :
<http://gitorious.org/projects/pitivi/repos/mainline>

## Fundamental issues and goals

These issues/goals are not ordered, since they are all equally
important.

-   **No code shall access private values directly**
    -   Use setter/getter and python 'property' mapper
    -   Ex: `myprop = property(_get_myprop,_set_myprop)`

<!-- -->

-   **Core code shall NOT contain any UI-specific code** (and
    vice-versa)
    -   This breaks the fundamental Core/UI separation
    -   Any code in *core* that has ui-specific code should be moved to
        pitivi.ui modules
    -   And the opposite for core code in the UI (ex.
        `pitivi.ui.plumber`)

<!-- -->

-   **All Core/UI classes can be subclassable for specific usage**
    -   This is essential for full pitivi flexibility, for having all
        kinds of plugins, for having different UI, etc...

<!-- -->

-   **Splitup code in subdirectories/submodules**
    -   Maybe not as much as one class per file... but that would be a
        good goal
    -   Definitely ONE base class per file though

<!-- -->

-   **UI is NOT compulsory** ==&gt; **pitivi can be used as a LIBRARY**
    -   There are several tools for which we need all the code from
        pitivi core without a UI implementation
    -   Ex : rendering backends, command-line/scripting tools, ....
    -   Disambiguate the naming somewhere
        -   `pitivi` : python module/library
        -   `PiTiVi` : application using the `pitivi` module
    -   Still, we should have most of the UI logic in that library, but
        without any forced implementation (like qt/gtk/win32...)

<!-- -->

-   **No gnome/gtk/gobject/gst specific code in base classes**
    -   This should go in subclasses
    -   Create our own event-based interface (to remove dependency on
        gobject.GObject)
        -   Johan might have ideas about this

<!-- -->

-   **Use `generators/yield` wherever it can be applied**
    -   Speedup and memory usage improvement

<!-- -->

-   **The only HARD DEPENDENCIES of pitivi are python core libraries and
    gstreamer**
    -   All other dependencies are optional and should be used from
        plugins

<!-- -->

-   **Remove the global instance code**
    -   No code should depend on a single instance of application and
        project
    -   Needed to be able to load many projects in one instance (amongst
        other things)
    -   The majority of the pitivi module should be non-application
        modules

<!-- -->

-   **Unit tests for pitivi core**

<!-- -->

-   **Prepare for Python 3**
    -   Article/presentation by Guido about this :
        <http://www.artima.com/weblogs/viewpost.jsp?thread=227041>

## Code Review

Not at all sorted

### File save/load

It seriously needs to be rethinked.

-   Allow formats to create their own subclasses of core classes
    -   Subclassing FileSource to add format-specific information
    -   Subclassing FileSourceWidget to show that format-specific
        information in the UI
-   Pluggable format support
-   See Undo/Redo
-   We need a native PiTiVi format
-   Need to be able to save files used in the project
-   Handle files/directories being moved, or loading the project on a
    different computer
-   Simple support for playlists (ELD, PLS, ASX ?)

### Undo/Redo

-   Some actions might be specific to a plugin

### Layer support in compositions

-   This is currently implemented using hacks

### TimelineObjects

-   Actually use ObjectFactory for producing its content
-   Remove limitation of only one brother per object
-   Allow re-using identical source/composition many times in a
    composition
    -   Fully synchronized (modifications to one instance are spread to
        all instances)
    -   Not synchronized (they're copies)
    -   Half synchronized (only some properties modifications are
        synchronized to all instances)

### ObjectFactory

-   Clarify its usage
    -   It contains the global information of objects you can use in the
        timeline
    -   For \*any\* object you can use in the timeline (source, fx,
        transition, composition, etc....)
-   Create notion of `SubObjectFactory`
    -   They use a smaller area/time of the *parent* object (cutting a
        captured video)
    -   Or they could be **corrected/modified** versions of the original
        source (i.e. they have extra effects applied to the source)
        -   Colour balance correction
        -   Audio Correction
        -   Media conversion (ex : Use `goom` to make a video stream out
            of an audio track)
            -   The 'media-converted' ones could maybe done on the fly
                if you add a file of a given media type (ex:audio) into
                a track of another media type (ex:video).
-   Allow easy transcoding, re-rendering or re-muxing of
    SubObjectFactory.
-   Allow adding extra (meta)data

### Logging

-   Switch to a smarter and more efficient debugging system
    -   Use logging module ?
    -   do as `flumotion` ?

### Plugin system

-   Figure out how to cleanly solve the problem of plugins extending
    both CORE and UI classes
    -   flumotion use some kind of bundles for this

### SmartBin and Playground

This was originally created to cope with 0.8 issues

-   Do we still need the playground ??
-   SmartBin isn't flexible enough
    -   We might need to have more than two running at the same time
    -   Doesn't support being connected to more than one sink
    -   Need to support features like Viewing Video while recording
        Video AND Audio

An idea might be to have `Producer`s and `Consumer`s.

-   Producer
    -   Can be a Timeline, live stream, File source, camera, webcam ,...
        (more or less like SmartBin now)
    -   It has a clean way of querying what it can produce
    -   We can connect multiple times to a stream (Audio, Video, ...) it
        produces
-   Consumer
    -   Can be an Encoder, Hardware sinks, Raw File renderer, Network
        Stream renderer, ...
    -   Has a buffering property

### Naming inconsistencies

Make sure the naming is coherent and comprehensible

-   Get rid of the notions of 'threads' in bins (sooooo 0.8)
-   Use proper naming from the editing world
-   Add a glossary in the documentation

### Temporary files

Thumbnails, captures, etc...

-   Where do we store them ?
-   How do we manage them ?

### Hardware source and sinks

-   Move plumber to core
-   Have some discovery utility (i.e. several audio/video sinks)
    -   Have it subclassable
        -   Use HAL on linux
        -   Use ??? on win, etc....
-   Have some generic classification system (os/system agnostic)
    -   Audio
    -   Video
    -   Source
        -   Local
        -   Camera
        -   Network
    -   Sink
        -   Local
        -   Network
    -   ???
-   See SmartBin and Playground above

### Cache rendering

-   needed for complex videos/operation
-   Have a caching system for frame forward/backward operation
    -   Would act like a queue, except it would intercept seeks, do the
        original one, then do a second \[1s before, 1s after\] seek to
        have the data available straight away for step-by-step seeking

### Losless editing

-   For I-frame only codecs (DV, JPEG,...), we should be able to only
    decode/process/encode parts that have be modified
    -   Would require gnonlin and core pitivi classes to support non-raw
        streams

### Capture support

-   Have base classes for capture support in core
-   See Hardware source and sinks
-   We **absolutely** need support for DV and HDV

### Flexible 'source provider/browser' support

Currently we only get sources from local files (even worse, it's using
gnome-specific things)

-   Make it generic
-   It provides ObjectFactory objects
-   Allow access to various kinds of source provider
    -   Local providers (filesystem, F-Spot, Gnome media (SoC project),
        ...)
    -   Network providers (Media Asset Management)
    -   P2P ? Using telepathy and tubes ?
-   Source providers might have extra information ==&gt; ObjectFactory
    subclasses
-   Figure out what's the best way to solve this issue
    1.  Use a source provider (let's say youtube) and grab some files
    2.  You want to modify those files (let's say apply a colourbalance,
        or cut out what you need) to have SubObjectFactory
    3.  You save your project (where/how do you save those files ? Do we
        leave them as a youtube link ?)
    4.  You reload your project... but you don't need the youtube
        browser anymore (you've already got your sources)

    -   -   **PROBLEM** Disambiguate SourceProvider and SourceBrowser.
            I'd say the difference is that stuff from SourceProvider(s)
            have to be moved in the SourceBrowser before being used in
            the timeline.

-   See also the ideas in ObjectFactory above

### Marker points / KeyFrames

Here keyframes are not I-frames but 'key positions'

-   Add support in:
    -   ObjectFactory (interesting points, user-introduced data, could
        be stored with/along the file...)
    -   TimelineObject (instance specific property modification)
    -   UI

### Source flexibility

-   Support multiple versions of one source
    -   Ex :
        -   low resolution versus HD/4K
        -   Distributed/P2P files (first download lowest resolution)
    -   Use thumbnail when file not available yet.
-   if it's a network URI, option to save it locally
    -   detect if remote source has changed
-   Support for separate index (save/load support)
-   Add basic tests to make sure the sources will behave properly with
    pitivi
    -   ex : testing seeking support
    -   If not, propose transcoding, or plugin to download, etc...

### Multiple Video support

There's two different use-cases in fact

-   Steroscopic or multi-angle support (multiple video tracks)
-   Editing together multiple videos from the same scene (one video
    track)
    -   You want a way to view all the input videos at the same time,
        synchronized, so you know which ones to select at any given
        point
    -   This of it as a non-live mixing-desk

### Effect support

-   Have a `gst_launch` plugin where users can create their own freeform
    effect pipeline
-   Allow concatenation/coupling of existing effects into a bigger one
    -   Bonus for adding some scripting in it !
-   Have Audio+Video effects
    -   They're in fact two/more separate effects that have
        synchronization
    -   Ex : photo flash effect : you want to have the 'flash' sound in
        sync with the 'whiteout'/still frame on the video side

### Scripting/Template/Scenario system

Allow easy creation of (parts of) the Timeline

-   Should have a clean content/Script separation
    -   Ex : Interview script : have the interview person's name
        separated from the actual video on which to overlay his name
-   Allow subclassing
    -   Ex : You can create different ways of displaying the
        interviewee's name, different ways to blend in/out, ...
-   Have a repository for those scripts/scenarios
    -   People can easily share/use/reuse existing scenarios

### Text/Subtitle support

How do we handle this properly ?

-   Text track ?
-   Use case : karaoke/subtitle overlay

### Missing feature support

Allow cleanly support Projects using unavailable
subclasses/plugins/effects.

-   Might not be available
-   Might be proprietary/custom
-   Older version of PiTiVi
    -   Provide a way to upgrade the feature/plugin

### Central/Distributed repository of PiTiVi plugins

### Missing (GStreamer) plugin support

Distributions should support this !

### Easy transcoding of sources

-   Allow transcoding sources only
-   Useful also for making sources more editing-friendly
-   Or to have lower resolution versions to work with

### GNonLin

Optimize the following use cases

-   Resizing/Trimming
    -   By end (modifying media\_duration + duration)
    -   By beginning (modifying
        media\_start+start+media\_duration+duration)
-   Moving many objects at once

One idea for this would be to have a 'block-rebuild' property on
GnlComposition that would mark down that is has (or not) to rebuild the
internal stack, but postpone it until the property has been set back to
False.

### GStreamer

-   interlaced support
    -   caps (differentiate raw frame/fields)
    -   Buffer Flags (TFF, Repeat)
    -   ... and obviously support in virtually all relevant plugins
-   Perfect Profesionnal Colourspace support
    -   Various Subsampling + Chroma placement (right now we don't make
        a difference between 4:2:0 jpeg/mpeg2/dv-ntsc ... whereas they
        have different chroma placement)
    -   Various Clamping matrices (HDYC for example)
    -   FAST and bit-accurate converters
        -   This might require making a generic colourspace converter
            bin which searches all required/available colourspace
            converters

### Website

-   We need more screenshots
-   Propose nightly builds

## Use Cases

These are some (long term) ideas I have

### Effect ideas

-   GoogleMaps/OpenStreetMap plugin
    -   Use maps to show a trip
    -   Zoom-in/zoom-out/move from location to location between the
        various steps
    -   Could use photo geotags to automatically known where to go

<!-- -->

-   Photo Flash
    -   Could be a nice way to do transitions when doing slideshows
    -   Could have a 'flash' sound on the audio track, sync-ed with it

<!-- -->

-   Film-reel at slow-speed
    -   Start from a still frame/picture
    -   Gradually speed up the movie
    -   You see the 'film-reel border' moving (i.e. at some points the
        inter-frame black borders will be visible)
    -   Have a flickering soundtrack
