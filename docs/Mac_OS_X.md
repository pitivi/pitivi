# Mac OS X

Mac OS X is a funny kind of Unix, but it's a Unix and should be able to
run Pitivi easily. It's also popular -- even lots of open source types
lug around a MacBook of some kind. Think of applications as a free
software gateway drug! ;)

If you are interested to help please [get in
touch](http://www.pitivi.org/?go=contact)!

## Current status

We're working on a system to build and package Pitivi for Mac
using GStreamer's Cerbero build system.

At the moment it's alpha quality. See the list of [macOS
issues](https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=on+Mac+OS+X)
for details.

Besides fixing bugs, we need to also prepare a DMG the [Homebrew
formula](https://github.com/aleb/homebrew-gui/blob/master/pitivi.rb) a
proper Mac app. Help is welcome!

## Building

Clone our Cerbero repository which includes `recipes/pitivi.recipe`:
```
$ git clone https://gitlab.gnome.org/aleb/cerbero-pitivi.git
```

Follow the instructions in the [README](https://gitlab.gnome.org/aleb/cerbero-pitivi/blob/pitivi-master/README.md)
to bootstrap the system.

Start the build. This takes ~1h30m on my laptop:
```
$ cd cerbero-pitivi
$ ./cerbero-uninstall build pitivi
```

To start Pitivi, run in a terminal:

```
$ ./build/dist/darwin_x86_64/bin/pitivi
```


## Particularities

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

Have a look at [HACKING](HACKING.md) for some inspiration. Feel free
to add some suggestions here if you find a useful workflow.
