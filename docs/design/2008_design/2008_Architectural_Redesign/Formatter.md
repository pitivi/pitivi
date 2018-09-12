# Formatter

A **Formatter** is responsible for:

-   Storing a [Project](design/2008_design/2008_Architectural_Redesign/Project.md) and all of
    its contents for later usage, **and/or**
-   Creating a [Project](design/2008_design/2008_Architectural_Redesign/Project.md) and all of
    its contents.

A default `Formatter` will always be available for storing/creating
projects under the internal PiTiVi project file format.

New `Formatter`s can be provided through plugins.

A non-exhaustive list of potential `Formatter`s:

-   AAF, used by FCP, Avid, ...
-   Playlists:
    -   EDL
    -   ASX
    -   ...
-   Application specific formats for Cinelerra, kino, kdenlive, ...
-   Application specific formats for FCP, Premiere Pro, Sony Vegas, ...
-   Online storages
    -   MetaVid

A `Formatter` can provide its own type of ObjectFactory provided it is a
subclass of a known valid ObjectFactory (SourceFactory,
OperationFactory).

# Capabilities

-   `loadProject(`*`location`*`)` : returns a new
    [Project](design/2008_design/2008_Architectural_Redesign/Project.md) fully loaded.
-   `storeProject(`*`project`*`, `*`location`*`)` : stores the given
    [Project](design/2008_design/2008_Architectural_Redesign/Project.md) at the given location.
-   `canHandle(`*`location`*`)` : Test whether the `Formatter` can
    handle the given location.
