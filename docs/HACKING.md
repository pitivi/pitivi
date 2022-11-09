---
short-description: Using the Pitivi development environment
...

# Hacking on Pitivi

To develop Pitivi on Linux you need to set up a development environment,
as described below. For [other platforms](crossplatform.md), get in
touch with us.

By setting up a development environment, you create a
[flatpak](https://flatpak.org) sandbox containing all the Pitivi
dependencies. The sandbox is then used to run Pitivi and the unittests,
without messing your system.

Start by installing **both** [flatpak](http://flatpak.org/getting.html)
and `flatpak-builder` on your system.

Create a development environment folder and get the [Pitivi source
code](http://gitlab.gnome.org/GNOME/pitivi) into it:

```
$ mkdir pitivi-dev
$ cd pitivi-dev
$ git clone https://gitlab.gnome.org/GNOME/pitivi.git
```

Whenever you want to hack on Pitivi, start a new terminal and enter the
development environment:

```
$ cd pitivi-dev/pitivi && source bin/pitivi-env
-> Setting up the prefix for the sandbox...
Using Pitivi prefix in /.../pitivi-dev/pitivi-prefix
[prefix being built, if not already...]
Running in sandbox: echo Prefix ready
Prefix ready
```

When creating the sandbox from scratch it can take up to a few hours,
depending on your internet connection speed and the CPU. Note the prompt
changes:

```
(ptv-flatpak) $
```

By entering the development environment, you get:
- a [Flatpak sandbox](http://docs.flatpak.org/en/latest/working-with-the-sandbox.html)
with dependencies and some development tools, in `pitivi-dev/pitivi-prefix`
- the [Meson build directory](http://mesonbuild.com/Quick-guide.html),
in `pitivi-dev/pitivi/mesonbuild`
- some aliases for the build tools, such as `ninja`, so they are executed in the sandbox.

Now that you are in the development environment, try running the
[unittests](Testing.md):
```
(ptv-flatpak) $ ptvtests
Running in sandbox: gst-validate-launcher .../pitivi/tests/ptv_testsuite.py
```

Hack away, and check the effect of your changes by simply running:
```
(ptv-flatpak) $ pitivi
```


## Updating the development environment

To update the dependencies installed in the sandbox, run:
```
(ptv-flatpak) $ ptvenv --update
```

That will actually recreate the sandbox prefix, updating all
dependencies from their git repos and tarballs as defined in the
[flatpak
manifest](https://gitlab.gnome.org/GNOME/pitivi/blob/master/build/flatpak/org.pitivi.Pitivi.json).


### How we use the sandbox

The sandbox we set up has access to the host file system. This allows
running the Python modules in `pitivi-dev/pitivi/pitivi/...` on top of
the GNOME + Pitivi dependencies system installed in the sandbox.
Without this trick, you'd have to build and install every time when you
change a `.py` file, to be able to test how it works, which would be
annoying because it takes a non-negligible amount of time.

We don't actually run Pitivi 100% uninstalled. Besides the `.py` files
there are other parts which need to be built when changed or even
installed before using them:

- Select parts of Pitivi are written in C, such as the audio envelope
renderer for the audio clips. Build them with `ninja -C mesonbuild/` or
with our very own alias `build`, which is the same thing. No need to
install them.

- Similarly, `bin/pitivi.py.in` and `pitivi/configure.py.in` also need
to be built with `build`, to regenerate the corresponding `.py` files.

- The translations need to be built and installed, which can be done
with `binstall`. See "Switching locales" below.


## Hacking on Pitivi dependencies (Meson)

If you have to work on say, [GStreamer Editing
Services](https://gstreamer.freedesktop.org/modules/gst-editing-services.html)
which is built using the Meson build system, first clone it into your
`pitivi-dev` folder:
```
(ptv-flatpak) $ cd pitivi-dev
(ptv-flatpak) $ git clone git@gitlab.freedesktop.org:gstreamer/gst-editing-services.git
```

Prepare its build directory using the `setup` alias which runs `meson`. This has
to be done only once:
```
(ptv-flatpak) $ cd pitivi-dev/gst-editing-services
(ptv-flatpak) $ setup
Using Pitivi prefix in /.../pitivi-dev/pitivi-prefix
Running in sandbox: meson mesonbuild/ --prefix=/app --libdir=lib
```

Build and install it in the sandbox:
```
(ptv-flatpak) $ cd pitivi-dev/gst-editing-services
(ptv-flatpak) $ ninja -C mesonbuild/ install
Using Pitivi prefix in /.../pitivi-dev/pitivi-prefix
Running in sandbox: ninja -C mesonbuild/ install
```

In the `(ptv-flatpak)` development environment `meson` and `ninja` are aliases
which run meson and ninja in the flatpak sandbox.

NOTE: When updating the environment with `ptvenv --update`, it will use your
local dependencies repositories it finds in the `pitivi-dev` folder, instead of
the default remote repositories. This means you have to update them yourself.
Also beware that it only takes into account committed changes.


## Hacking on Pitivi dependencies (Autotools, Make, etc)

If the project you are working on is built with other tools, make sure
they are run in the sandbox by using `ptvenv`. For example:

```
(ptv-flatpak) $ cd pitivi-dev/frei0r-plugins-1.4
(ptv-flatpak) $ ptvenv ./autogen.sh
Running in sandbox: ./autogen.sh
(ptv-flatpak) $ ptvenv ./configure
Running in sandbox: ./configure
(ptv-flatpak) $ ptvenv make
Running in sandbox: make
```


## Profiling Pitivi

To profile a Pitivi run, simply set the `PITIVI_PROFILING` environment
variable to 1, like so:

```
(ptv-flatpak) $ PITIVI_PROFILING=1 pitivi
```

A file named `pitivi-runstats` will be created in the current directory, a handy tool to examine it is `gprof2dot.py`, install it with:

```
$ pip install gprof2dot
```

Then run:

```
$ gprof2dot -f pstats pitivi-runstats | dot -Tsvg -o profile.svg
```

You can then inspect the call tree profile with your preferred image viewer:

```
$ xdg-open profile.svg
```


## Switching locales

To see how Pitivi looks in a different locale, use:

```
(ptv-flatpak) $ LANG=fr_FR.UTF-8 pitivi
```

Pay attention the translations in the sandbox are not automatically
updated when you `git pull`. You can update them by updating your
sandbox (`ptvenv --update`) or by reinstalling Pitivi in the sandbox:

```
(ptv-flatpak) $ binstall
[...]
Installing /.../pitivi-dev/pitivi/mesonbuild/po/de.gmo to /app/share/locale/de/LC_MESSAGES/pitivi.mo
[...]
```
