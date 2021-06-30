# Roadmap

This is intended to be a **general overview** of the very
important or big features/improvements we are working on, or planning.
For a list of smaller features see [fun tasks for
newcomers](https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=4.+Newcomers).

What keeps us busy in general?

-   **Fixing bugs**. Improving reliability and ease of use is never
    “done”. We have
    [tons](https://gitlab.gnome.org/GNOME/pitivi/issues) of work.
    [Help](https://www.pitivi.org/contribute) is very welcome!
-   **Improving GStreamer**. This benefits not only Pitivi, but other
    multimedia applications as well.
-   **Working on features**. With you!

# High-level roadmap

We'll invest in stability and cool features.

# Major features

Besides the items below we care about, see also the list of
[GSoC project ideas](GSoC_Ideas.md).

## Motion ramping, time stretching

We're working on [adding
support](https://gitlab.gnome.org/GNOME/pitivi/issues/632) for simple speed
changing.

Once this is done, we'll stretch the time so we finish faster the speed ramping.

## Cut and export a video without re-encoding it

See [issue 2475](https://gitlab.gnome.org/GNOME/pitivi/-/issues/2475).

## Effects UI

Some effects like [alphaspot](https://gitlab.gnome.org/GNOME/pitivi/issues/2098)
and [color corrector](https://gitlab.gnome.org/GNOME/pitivi/issues/660) already
have a custom UI. The overall experience can be smoother.

Still to do:
- [green screen compositing](https://gitlab.gnome.org/GNOME/pitivi/issues/966),
- [audio equalizer](https://gitlab.gnome.org/GNOME/pitivi/issues/1551)

## Hardware-accelerated decoding and encoding

Since GStreamer 1.2, the basic infrastructure allowing us to cleanly take
advantage of the video decoding capabilities of modern graphic cards is there.
We need to ensure that our planned usecases are properly supported with the most
common graphic drivers (through VA-API) and to make the integration work in
Pitivi.
