# High-level Design

**High Level overview**

# Overall

![Top-level organisation](Top-level-uicore.png "Top-level organisation")

PiTiVi is comprised of two main parts:

-   The **Core**, containing all the project- and timeline-related
    components, a plugin-system and various tools.
-   The **User Interface**, optional, offering a graphical interface to
    use Core

# Core

![Contents of Core](Top-level-core-only.png "Contents of Core")

Core contains several essential components, of which the most important
are:

-   The **Application**, which organizes the projects and pipelines, as
    well as general application settings.
-   The **Projects**, centralizing information on editing projects,
    including timeline, sources used, settings, ...
-   The [**Pipelines**](design/2008_design/2008_Architectural_Redesign/Pipeline.md), allowing
    combining some Actions (View, Record, Stream,...) with Producers
    (Timeline, File, Camera, VCR, ...) and Consumers (Loudspeakers,
    Screen, File, Network stream,...)
-   A **Plugin System**, allowing adding/modifying/extending features in
    various parts of PiTiVi.
-   Some **Tools**, amongst which Browsers (To search/organize/discover
    content) and Formatters (To handle various editing projects file
    formats).
-   Some **utilities**, use by various components of core, like a
    Discoverer (to discover the multimedia properties of contents) and
    Thumbnailer (To generically produce thumbnails of contents)

## Application

This object represents a running instance of PiTiVi.

It contains:

-   The **Settings** of the application, user-interface and plugins
-   One or more **Project**(s), corresponding to the various
    [Timelines](design/2008_design/2008_Architectural_Redesign/Timeline.md) currently opened.
-   One or more [**Pipeline**(s)](design/2008_design/2008_Architectural_Redesign/Pipeline.md),
    corresponding to the various processing pipelines currently used.

If a User Interface is used, the Application object is its core
counterpart.

![Project/Pipeline relationship and
contents](Top-level-project-pipeline.png "Project/Pipeline relationship and contents")

### Project

Represents an editing project, corresponding to ONE
[Timeline](design/2008_design/2008_Architectural_Redesign/Timeline.md).

It contains:

-   The **Settings** of the project and timeline
-   The **History** of all events that happened on the Project and the
    Timeline.
-   The **SourceBin** which are a list of the SourceFactory being used
    in this project. All sources used in the Timeline are present in
    that list, but it can also contains sources not (yet) used in the
    Timeline.
-   The [**Timeline**](design/2008_design/2008_Architectural_Redesign/Timeline.md). All the
    timeline editing is done through this object.

### Pipeline

Pipelines are where the media processing takes place. It is the grouping
of three things:

-   **Producer**(s) which are generally the contents we're using (Ex:
    Timeline, File, Network Stream, WebCam, DV VCR, ...)
-   **Consumer**(s) which convert/process/display streams from the
    Producers (Ex: Encoding to File, Outputting to Screen/Speakers,
    Streaming, recording to DV VCR, ...)
-   **Action**(s) which represent meaningful usage of the various
    producers and consumers (Ex: Record from Webcam, (Pre)View timeline,
    Render Timeline, Capture from DV VCR, ...)

## Plugin System

**TO BE DEFINED**

## Tools

### Browser

![Browser](images/Browser-functional.png "Browser")

Browser are a unified way of searching/browsing for contents and
devices, or more generally speaking *Media Assets*.

This includes, but is not limited to:

-   Local File Browser
-   Hardware Device Browser
-   Effect/Operations Browser
-   Media Asset Management Browser
-   Online Service Browser (ex: youtube, flickr, archive.org, ...)

See [Browsers](design/2008_design/2008_Architectural_Redesign/Browsers.md) for
more details.

### Formatter

![Formatter](Formatter-functional.png "Formatter")

Formatter are responsible for loading/storing Projects from/to various
file formats.

Formatters can also provide subclasses of existing core objects in order
to store/provide format-specific information.

See [Formatter](design/2008_design/2008_Architectural_Redesign/Formatter.md)
for more details.

## Utilities

### Discoverer

### Thumbnailer

# Issues still not clear

## UI bundles

We need to provide some kind of mapping for which UI widget should be
used for which core component, including subclasses.
