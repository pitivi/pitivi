# Roadmap

This is intended to be a **general overview** of the very
important or big features/improvements we are working on, or planning.
For a list of smaller features see [fun tasks for
newcomers](https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=4.+Newcomers).

What keeps us busy in general?

-   **Fixing bugs**. Improving reliability and ease of use is never
    “done”. We have
    [tons](https://gitlab.gnome.org/GNOME/pitivi/issues) of work.
    [Help](http://www.Pitivi.org/?go=contributing) is very welcome!
-   **Improving GStreamer**. This benefits not only Pitivi, but other
    multimedia applications as well.
-   **Working on features**: Until we reach [1.0](releases/1.0.md), only
    if they improve stability.

# High-level roadmap

Any time estimates here are mostly wild guesses. Do not treat them as
hard deadlines. This aims mostly at giving an idea of how milestones
follow each other.

-   2018 Q4: release [1.0](releases/1.0.md) with ponies and rainbows

See [Current events](Current_events.md) for past items.

# Major features

## Plugin system

-   Status: [done](https://gitlab.gnome.org/GNOME/pitivi/issues/1480),
    but we still need a [developer
    console](https://gitlab.gnome.org/GNOME/pitivi/issues/2055), and
    [documentation with
    examples](https://gitlab.gnome.org/GNOME/pitivi/issues/2089).
-   **This is very important**. A plugin would have access to the entire
    app. Being in Python, it will be extremely easy to quickly write
    useful plugins without having to compile anything. Pitivi plugins
    will allow manipulating the timeline clips and clip effects
    automatically, thus allowing great flexibility for custom solutions.
    See for example [audio
    normalization](https://gitlab.gnome.org/GNOME/pitivi/issues/638)
    or the [autoaligner
    resurrection](https://gitlab.gnome.org/GNOME/pitivi/issues/1345).

## Motion ramping, time stretching

-   Status: started
-   See [issue 632](https://gitlab.gnome.org/GNOME/pitivi/issues/632)

## Effects UI

-   Status: some effects like
    [alphaspot](https://gitlab.gnome.org/GNOME/pitivi/issues/2098) and
    [color corrector](https://gitlab.gnome.org/GNOME/pitivi/issues/660)
    already have a custom UI. The overall experience can be smoother.
-   Still to do: [green screen
    compositing](https://gitlab.gnome.org/GNOME/pitivi/issues/966),
    [audio equalizer](https://gitlab.gnome.org/GNOME/pitivi/issues/1551)

## Advanced layer management

-   See [issue 930](https://gitlab.gnome.org/GNOME/pitivi/issues/930#note_68393)

## A better title editor

-   The current title editor UI is very simple. Please join us to make
    it work up to your expectations! See the existing [title editor
    issues](https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=titles+editor).

## MAM/DAM

-   [Digital asset
    management](http://en.wikipedia.org/wiki/Digital_asset_management)
    is the ability to manage huge amounts of media (video clips, sounds,
    images, etc.). This feature is very much needed for professional
    editing; it allows handling multiple simultaneous camera angles,
    multiple takes of the same scene, multiple sound sources, etc.
-   Potentially being addressed by the Novacut team with
    [dmedia](https://launchpad.net/dmedia)

## Hardware-accelerated decoding and encoding

-   Since GStreamer 1.2, the basic infrastructure allowing us to cleanly
    take advantage of the video decoding capabilities of modern graphic
    cards is there. We need to ensure that our planned usecases are
    properly supported with the most common graphic drivers (through
    VA-API) and to make the integration work in Pitivi.

## Proxy editing

-   Status: [done](https://gitlab.gnome.org/GNOME/pitivi/issues/743) but
    the proxy experience can be better
-   See [proxy editing
    requirements](design/Proxy_editing_requirements.md) for the “spec”
    of how this feature should behave
