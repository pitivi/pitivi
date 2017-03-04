# GES

GES (GStreamer Editing Services) is a cross-platform library that sits
on top of [GStreamer](http://en.wikipedia.org/wiki/GStreamer) and
Non-Linear Engine. GES simplifies the
creation of multimedia editing applications. Basically, GES is a
complete [SDK](http://en.wikipedia.org/wiki/Sdk) for making a video
editor (but not only that).

Traditionally, Pitivi was a user interface and a homemade video editing
“core” (or “backend”) that interacted directly with
[GNonLin](attic/GNonLin.md). Starting in version
[0.91](releases/0.91.md), Pitivi's core has been replaced by GES. This
means that Pitivi is mostly only a user interface on top of GES.
Starting in version [0.95](releases/0.95.md), GNonLin has been replaced
by Non-Linear Engine to improve stability.

GES does not aim at serving the needs of Pitivi only: we are building
the platform of the future and breaking the cycle of failed projects.
Indeed, other applications are already using GES or migrating to it.

> *“Pitivi is one of the 'generous' projects that develops not just an
> editor, but a set of libraries to implement editors. \[Applications
> built on top of those libraries\] are not really re-inventing the
> wheel, they can piggyback on top of the work that these folks are
> doing, and then implement UI features that they care about the
> most.”*\
> — Bassam Kurdali, director of [Elephants
> Dream](https://en.wikipedia.org/wiki/Elephants_Dream) and
> [Tube](http://urchn.org).﻿

In addition to the fact that GES encourages code reuse among audio/video
editing software, here are some concrete advantages that we've noticed
while porting Pitivi to GES:

-   It solves many architectural issues of the past.
-   It vastly simplifies Pitivi development:
    -   More than 20 000 lines of code have been removed from Pitivi as
        a result
    -   [A big
        cleanup](http://jeff.ecchi.ca/blog/2012/01/12/spring-clean-up-in-january/)
        of the Pitivi codebase was done in early 2011, significantly
        reducing the amount of modules/files to deal with.
    -   No more confusion between the UI and backend parts
    -   Much less GStreamer knowledge is required to contribute to
        Pitivi itself.
-   It has much better performance.

Further reading for contributors:

-   See the [Architecture](Architecture.md) page for a visual
    overview of the relationship between Pitivi, GES, Non-Linear Engine
    and other components.
-   Read the [GES API reference
    documentation](http://gstreamer.freedesktop.org/data/doc/gstreamer/head/gstreamer-editing-services/html/)
    if you need to interact with GES. This documentation can also be
    found locally in the “docs/libs/html/” subdirectory of your GES git
    checkout.
-   [The initial GES
    announcement](http://blogs.gnome.org/edwardrv/2009/11/30/the-result-of-the-past-few-months-of-hacking/),
    which explains why GES was created, what its various components are
    and how it fits with GStreamer.
