# Project loading and saving

File load/save support in PiTiVi is seemingly simple; however, it has do
be done properly, or user experience will suffer. That is the motivation
for this rather lengthy design document.

The following document is partially based on a patch supplied by Richard
Boulton, including comments and documentation strings. As the patch no
longer cleanly applies, I have been asked to re-work it into a design
document so that we can determine how best to incorporate his ideas.

# Use Cases

There are 4 states and 4 commands, giving the user a total of 14
possible scenarios that users might encounter (the initial state does
not allow for two of the commands).

## “Save” vs. “Save As”

“Save As” will be treated as a special case of “Save” for the purposes
of this document. When the “Save As” command is issued, the user will be
asked to supply a file path, and the project will be saved. From then
on, pitivi will be editing the file pointed to by the new file path,
rather than the previous one. In all other respects, “Save As” is
identical to “Save”. When a “Save” command is given on a new project,
the scenario will be identical to the “Save As” scenario.

## Overwriting Modified Files

Before saving, PiTiVi checks to see if the file has been modified since
the last save. When a file has changed on disk, the user will be
prompted to ask if it is acceptable to overwrite the file. PiTiVi will
not check to see if the file has been altered except in these
circumstances.

## PiTiVi Save States Visible to User

1.  Initial state
    1.  Pitivi can be launched with, or without the path to a project
        which can be automatically loaded
2.  Unmodified project state
    1.  pitivi is running, and the current project is unmodified since
        the last save operation
3.  Modified project state
    1.  pitivi is running, and the current project has been modified
        since the last save operation.
    2.  A save operation implicitly returns PiTiVi to the unmodified
        state

## PiTiVi Save/Load Commands Visible to User

1.  New project
2.  Save Project
3.  Save Project As
4.  Load Project

## Things Invisible to User

PiTiVi only edits a single project at a time. Consequently, implicit in
the New, Save, and Save As commands is the “Close Project” command.
Since PiTiVi's UI must always display a project, a “Close Project”
command would be identical to the “New Project” command. Based on this,
it makes sense to omit “Close Project” from the UI. Nevertheless, it
should still be considered a command that is part of this module, for
the sake of code reuse.

## Load/Save Behavior

PiTiVi should follow the established convention for large applications
of keeping unsaved changes in a temporary file to minimize the potential
amount of work lost due to crashes, power failures, accidental quits,
etc. After a user-specifiable interval, unsaved changes will be saved to
a temporary file. In addition to this, PiTiVi should not directly
overwrite a file when saving, but instead back up the original file
first.

## PiTiVi Use Cases Visible to User

1.  Initial State, No Project Path Argument
    1.  PiTiVi initializes and displays a blank project
2.  Initial State, With Project Path Argument
    1.  PiTivi initializes and loads the specified project from disk
3.  Unmodified Project State, New Project Command
    1.  A new project is loaded.
4.  Unmodified Project State, Save Project Command
    1.  Nothing happens
5.  Unmodified Project State, Save Project As Command
    1.  A dialog prompts the user for a new project path
    2.  The current project is saved under this new path
6.  Unmodified Project State, Load Project Command
    1.  A dialog prompts the user to open a new file
    2.  The new file is loaded, replacing the current project
7.  Unmodified Project State, Save Project Command, File Changed On Disk
    1.  A Dialog is displayed presenting choices of “Overwrite”, “Save
        As”, and Cancel
        1.  overwrite: the project is saved over the top of the original
        2.  user interaction proceeds as if “Save As” had been issued
        3.  cancel: the save operation is canceled
8.  Unmodified Project State, Save Project As Command, (or file already
    exists)
    1.  File chooser dialog prompts user for filepath
    2.  If the file exists at all, then the overwrite confirmation
        dialog is displayed offering the following choices
        1.  overwrite: the project is saved over the top of the existing
            file
        2.  save as: file is saved over the top of the existing file
        3.  cancel: the save operation is canceled
9.  Unmodified Project State, Load Project Command, File Changed On Disk
    1.  Identical to Unmodified, Load Project where original file is
        unchanged
10. Modified Project State, New Project Command
    1.  Close Project confirmation dialog displayed, presenting choices
        of “Save”, “Don't Save”, and “Cancel”
        1.  Cancel: a new project is not created, and the old project is
            not saved
        2.  Don't Save: the new project will replace the current, and it
            will not be saved
        3.  Save: The project is saved, and a new project is created.
11. Modified Project State, Save Project Command
    1.  If the project has not been saved before, this scenario is
        identical to choosing “Save As”.
    2.  If the project has been saved before, the project simply
        overwrites the old one on disk.
12. Modified Project State, Save As Project Command
    1.  A dialog prompts the user save a new file
    2.  The file is saved under the new path
    3.  PiTiVi continues editing the project under the new pathname
13. Modified Project State, Load Project Command
    1.  Close Project Confirmation Dialog displayed, presenting choices
        of “Save”, “Don't Save”, and “Cancel”
        1.  Cancel: the project is not loaded, and the old project is
            not saved
        2.  Don't Save: the current project will not be saved, but the
            user will be prompted to load a project
        3.  Save: The project is saved, and the user is prompted to load
            a project
14. Modified Project State, Save Project Command, File Changed On Disk
    1.  A confirm overwrite dialog is displayed presenting choices of
        “Overwrite”, “Save As”, and “Cancel”
15. Modified Project State, Save As Project Command, File Changed On
    Disk
    1.  Identical to Modified State, Save As
16. Modified Project State, Load Project Command, File Changed On Disk
    1.  Identical to Modified State, Load Project Command

# Application Logic

The high level application logic is relatively straight forward. The
coding will not be, due to the nature of the GObject/Gtk. The logic is
divided into four operations. these are “New”, “Load”, “Save”, and
“Close”. The “Close” process is not directly operation by the user, but
is performed any time the current project is to be replaced.

Image:New flowchart.png|Logic for creating a new project Image:Load
flowchart.png|Logic for loading an existing project Image:Save
flowchart.png|Logic for saving a project (both “Save” and “Save As”)
Image:Close flowchart.png|Logic for closing a project

At the lower level, the application logic will be implemented through
signals, and callbacks.

The core classes will provide public methods for initiating the
operations of saving, loading, and creating new projects. If the core
needs user input, it will emit the appropriate signal, passing a
reference to a callback. If the UI determines that further action is
necessary by the system, the UI then returns control to the system by
calling the callback. This means that system code could be split into
two functions, the public interface which initiates the action, and the
deferred callback which finalizes the action.

# Native file format

While PiTiVi should make every effort to support a wide range of file
formats, most of these will be through external plugins. PiTiVi provides
a reference implementation that uses Python's cPickle module to
serialize and deserialize data in the intermediate format.

# Pluggable Saving Backend

One goal of PiTiVis is to work work with a wide variety of project file
formats.

The `ProjectSaver` class coordinates the work of saving, loading, and
validating project data. The class works with an intermediate format
which concisely represents the project. Everything contained within a
project (sources, transitions, effects, compositions, settings, etc)
must implement the `Serializable` interface, which includes the
`toDataFormat()` and `fromDataFormat()` methods. These methods convert
to and from this intermediate format.

Multiple file formats can be supported by sub-classing `ProjectSaver`
These classes must provide `dump()` and `load()` methods for the file
format they implement. Users of the ProjecSaver's public interface can
use the methods `saveToFile(), openFrom File, listFormats()`, and
`newProjectSaver`. These methods are summarized in the following table:

<table>
<tr>
<td>
<strong>Method Name</strong>

</td>
<td>
parameters

</td>
<td>
purpose

</td>
</tr>
<tr>
<td>
`saveToFile`

</td>
<td>
`tree, output_stream`

<td>
write project data to file

</td>
</tr>
<tr>
<td>
`openFromFile`

</td>
<td>
`tree, output_stream`

<td>
read project data from file

</td>
</tr>
<tr>
<td>
`@classmethod newProjectSaver`

</td>
<td>
`fmt` - string representing the project file format

<td>
return a new projectSaver instance

</td>
</tr>
<tr>
<td>
`@classmethod listFormats`

</td>
<td>
<td>
return a list of strings representing project file formats

</td>
</tr>
</table>
## The intermediate data structure

The following example assumes the following:

-   There are 5 media sources located in the same directory as the
    project
    -   Three video files `video1.ogm, video2.ogm`, and `video4.ogm`
    -   Two audio files `audio1.ogg`, and `audio2.ogg`
-   The project output format is 320x240 resolution, 15fps video and

Of these sources, only 4 have been added to the timeline (time-stamps
given in h:mm:ss.sss):

-   video1.ogm:
    -   media-start: 0:00:02:0.000
    -   media-duration: 0:00:37.000
    -   start: 0:00:00.000
    -   duration: 0:00:37.000
-   video2.ogm:
    -   media-start: 0:00:00:0.000
    -   media-duration: 0:00:30.242
    -   start: 0:00:00.37.000
    -   duration: 0:00:30.242
-   video1.ogm:
    -   start: 0:01:7.242
    -   duration: 0:00:20.0
    -   media-start: 00:30:00.000
    -   media-duration: 00:00:20.0
-   audio1.ogm
    -   media-start: 00:00:00.000
    -   media-duration: 00:01:27.242
    -   start: 00:00:00.000
    -   duration: 00:01:27.242
-   audio2.ogm:
    -   media-start: 0:00:00:00.000
    -   media-duration: 0:00:05.200
    -   start: 0:00:45.127
    -   duration: 0:00:5.2

In this example, media-duration and timeline duration correspond. This
is not necessarily the case, however.

The equivalent python data structure will look like this (currently
incomplete):

```
project = {

“timeline” : {
    “compositions” :
    (
        {
              “type”: “video”,
              “sources” :
              (
                    {
                        “project-source” : <ref to video1.ogm source definition>,
                        “start”:0,
                        “duration”: 37000,
                        “media-start”: 120000,
                        “media-duration”: 37000
                    }
                    {
                        “project-source” : <ref to video2.ogm source definition>,
                        “start”: 37000,
                        “duration”: 30242,
                        “media-start”: 67242,
                        “media-duration”: 30242,
                    }
                    {
                        “project-source” : <rref to video1.ogm source definition>,
                        “start”: 67242,
                        “duration”: 20000,
                        “media-start”: 30000,
                        “media-duration”: 20000
                    }
              )
         },

         {
            “type” : “audio”,
            “sources” : (
                  {
                        “project-source” : <ref to audio1.ogg source definition>,
                        “start”: 0,
                        “duration”: 87242,
                        “media-start”: 0,
                        “media-duration”: 87242
                    }
                    {
                        “project-source” : <ref to audio2.ogg source definition>,
                        “start”: 45127,
                        “duration”: 5200,
                        “media-start”: 0,
                        “media-duration”: 5200
                    }
             )
         }
    )
  },

  “sources” : ....

  “settings” : ....
}
```

More specifically, the project is composed python dictionaries, tuples,
and strings. It could be thought of as a “tree” but it is really more of
a “deep dictionary,” with several levels of nesting. Each dictionary
contains a key called “datatype” which identifies what the kind of
object it is. Optional keys are not required to exist, but you must
handle them if they do.

### Project

The project is the root of the “tree.” It is a dictionary, with three
keys:

-   `datatype` -- “project”
-   `timeline` -- maps to a tuple of “Composition” dictionaries (see
    below)
-   `sources` -- maps to a “source-list”
-   `settings` --maps to a dictionary of project-specific settings (the
    ExportSettings field of a Project object)

### Compositions

The composition field represents a PiTiVi timeline composition element.
There is one main timeline per project, but sub-compositions can be
represented as well. A sub composition is represented as a source
dictionary whose ID field refers to a composition dictionary as defined
here. This allows multiple instances of the same composition in the
timeline, as well as allowing only part of the composition to be used.

-   `datatype` -- “timeline-composition”
-   `sources` -- maps to a tuple containing source dictionaries. (see
    below)
-   `effects` (optional) -- maps to a tuple of effects dictionaries (see
    bleow)
-   `transitions` (optional) -- maps a tuple of transitions dictionaries
    (see below)

#### Source (composition)

This represents a source object in a timeline. It is a dictionary
containing the following keys:

-   `datatype` -- “timeline-source”, “timeline-live-source”,
    “timeline-blank-source”
-   `id` -- maps to a reference to a source in this project's sources
    list or to a composition
-   `start` -- maps to an integer in gnonlin time format (milliseconds).
    the start of the source in the timeline.
-   `duration` -- maps to an integer in gnonlin time format. how long
    the source lasts in the timeline.

There is also the FileSource, which has the same properties as above,
but also the following:

-   `datatype` -- “timeline-file-source”
-   `media-start` -- where the source starts in the media, in gnonlin
    time units
-   `media-duration` -- how long the source plays the media, in gnonlin
    time units
-   `volume` (optional) -- a real number, 0 being mute, 1 being original
    source volume, and &gt; 1 being some multiple of source volume.

### SourceList

Represents a list of source factories in a project. Source factories are
objects which can create timeline sources. The source-list is a
dictionary containing:

-   `datatype` -- “source-list”
-   `source-factories` -- maps to a list containing “source-factory”
    dictionaries.

#### Source Factory

Represents a source factory in the project sources list. It is a
dictionary containing the following keys:

-   `datatype` -- “file-source-factory”, “operation-factory”,
    “simple-operation-factory”, “transition-factory”, “SMPTE-factory”
-   `uid` -- an id mapping to the object's unique id

### Settings

Project-specific settings are as follows. This section is incomplete

-   `datatype` -- “export-settings”
-   `videowidth`
-   `videoheight`
-   `videorate`
-   `audiochans`
-   `audiorate`
-   `audiodepth`
-   `vencoder`
-   `aencoder`
-   `containersettings`
-   `acodecsettings`
-   `vcodecsettings`

### Formats for Unimplemented Features

A number of features are planned for future releases of PiTiVi. Handling
these is currently considered optional, and these specifications are
subject to change.

#### Transitions

Transitions and effects have not yet been implemented in PiTiVi. This
This represents a transition object in a timeline. It is a dictionary
containing the following keys:

-   `type` -- maps to a string naming the transition to apply. valid
    names have not yet been established.
-   `start` -- the start of the transition in the timeline, (see
    Source(Timeline) above)
-   `duration` -- maps to the duration of the transition in the timeline
    (see Source(Timeline above)
-   `parameters` -- maps to the parameters of the transition, which are
    specific to each transition. specifications for these have yet to be
    established.

#### Effects

-   `type` -- maps to a string naming the effect to apply. valid names
    have not yet been established
-   `start` -- maps to the start of the effect in the timeline (see
    Source(Timeline above)
-   `duration` -- maps to the duration of the effect in the timeline
    (see Source(Timeline) above)
-   `parameters` -- maps to the parameters of the effect, which are
    specific to each effect. specifications for these have yet to be
    established.

## Implementing other File Formats

TODO: explain how to implement a file format as a plugin

Support for a variety of formats will be provided by plugins which
implement the `ProjectSaver` interface. A reference implementation
exists in projectsaver.py, called PickleFormat.

When implementing a custom file format, you should subclass
ProjectSaver. Your child class should define:

-   the doc string for the class. It should contain a brief,
    human-readable description of the file format your class implements
-   `__file_format__` -- a string used by pitivi to represent your
    format
-   `__extensions__` -- a list of valid file extensions for the module.
-   `dump(tree, output_stream)` -- a method which converts the
    intermediate representation `tree` into your file format, and writes
    it to the open file object `output_stream`
-   <code>load(input\_stream) -- a method which reads from the open file
    object `input_stream` and returns an object in the intermediate
    representation

## Test Cases

### Unit Test Cases

#### Test Serialization of Objects

1.  Test the serialization methods of each kind of object. Create an
    object with known parameters, then test that the python object
    returned is as expected
2.  Test deserialization methods of each kind of object. Create a python
    data structure with known parameters, check that the timeline object
    returned is as expected

#### Test tree traversal code

1.  Create a complicated project data structure with nested
    compositions. Test that it is properly converted into a Project
    object.
2.  Test project serialization code. Create a complicated project using
    the available interface functions. Test that the project is properly
    serialized into python data structure. Do deep comparison of
    generated tree and expected tree

#### Test file processing code

1.  Take a tree representing a complicated project, and save it to a
    file. Load the file back from disk, and compare the trees. They
    should be identical. Note: here we can saving/loading of features
    which are not yet implemented in PiTiVi.
2.  Test everything. Create a project using the available interface.
    Save the project using the high-level interface. Load the project.
    The two projects should be identical.
