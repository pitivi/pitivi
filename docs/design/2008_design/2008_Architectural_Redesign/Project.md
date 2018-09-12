# Project

A **Project** is the object containing everything specific to an
*editing project*.

**Project**s are loaded and saved using the Formatters.

## Contents

-   The **Settings** of the `Project`.
-   The **History** of the actions that brought us to the current state
    of the Project.
-   The **Content Bin**, containing all the `SourceFactory` used in the
    `Timeline`.
-   The [**Timeline**](design/2008_design/2008_Architectural_Redesign/Timeline.md), describing
    how the various objects (sources, operations) are laid out (through
    time and priority).

# Settings

Here we will store the settings of the project, which contains, amongst
other things:

-   Metadata
    -   Description
    -   Author
    -   Project file location/directory
    -   ...
-   Rendering settings
    -   These are the description of the streams
        -   Remark : ... maybe we don't need them since we just need to
            look at the timeline streams to know that ?
-   Project file-format specific settings
    -   Remark : It might actually be better to have those stored in
        `Project` subclasses since the formatter allows that.

**TODO** : Brainstorm what else could be stored there remembering it's
project specific.

# History

The generic idea is that we store every action done on the **Timeline**
and **Content Bin** along with the arguments, and we can then:

-   undo an action
-   redo an action
-   serialize that list of actions

There shouldn't be any (practical) limits to the history.

**TODO** : Create a new page specific to History/Undo/Redo since it has
implications bigger than just for the Project.

# Content Bin

It can only contain *discovered* SourceFactory. That means they contain
*at least* the description of all the contained `Stream`s, its duration.
Remark : A *thumbnail* representing the source might also be enforced.
