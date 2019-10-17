# Mac OS X

Mac OS X is a funny kind of Unix, but it's a Unix and should be able to
run Pitivi. It's also popular -- even lots of open source types lug
around a MacBook of some kind. Think of applications as a free software
gateway drug! ;)

## Current status

Pitivi runs pretty well on Mac, but consider it alpha quality. A few
[bugs](https://phabricator.freedesktop.org/project/view/123/) have been
filed already. If you are interested please [get in
touch](http://www.pitivi.org/?go=contact)!

Besides fixing bugs, we need to prepare somehow out of the [Homebrew
formula](https://github.com/aleb/homebrew-gui/blob/master/pitivi.rb) a
proper Mac app. Help is welcome!

## Installing

First install [Homebrew](http://brew.sh/) then run:

` brew install aleb/gui/pitivi`

To run Pitivi, run in a terminal:

` pitivi`

Please report bugs to
[phabricator](https://phabricator.freedesktop.org/project/view/123/).

## Hacking

Mac OS X has a few major differences from Linux:

-   GTK+ uses Quartz backend instead of X11
-   When building for multi-arch, a single filesystem hierarchy with
    “fat binaries” is used, rather than separate directories for
    libs/executables in each arch.
    -   This causes some issues with gobject-introspection, in that
        attempting to support multi-arch (“Universal”) builds requires
        adjusting paths to the gir files. Currently this has been
        removed from cerbero's build scripts, so you'll only get a
        64-bit build. But this might change again.
-   Applications are usually “bundled” into relocatable 'Foo.app'
    directories which encapsulate their binaries, libraries, and shared
    data.

## Development environment

Have a look at [HACKING](HACKING.md) to see how to clone a local repository.

To be able to run `./configure`, you need to add
`/usr/local/opt/gettext/bin/` to `PATH` so that `msgfmt` can be found.

You should be able to run `bin/pitivi`
