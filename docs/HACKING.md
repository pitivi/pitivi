---
short-description: Using the Pitivi development environment
...

# Hacking on Pitivi

*Pitivi being a GNOME project, we advice newcomer to follow the*
*[GNOME Newcomers guide](https://wiki.gnome.org/Newcomers/) to setup*
*the Pitivi development environment. Make sure to use the right git repository:*

>   **https://gitlab.gnome.org/GNOME/pitivi.git**

## Setting up advanced development environment

> NOTE: This way of setting the development environment is sensibly more complex
> but also more flexible than the one for newcomers. If you are a  beginner
> or if you usually use [gnome-builder](https://wiki.gnome.org/Apps/Builder)
> as your main IDE, follow, as previously adviced, the
> [GNOME Newcomers guide](https://wiki.gnome.org/Newcomers/)

The official way of getting your environment up and running is by using
[flatpak](http://flatpak.org/). For this you need to
[install flatpak](http://flatpak.org/getting.html) on your system,
along with flatpak-builder. Note flatpak-builder might be provided by an
additional package on some distributions (such as Archlinux).

Create a development environment folder and get the [Pitivi source code](http://gitlab.gnome.org/GNOME/pitivi) into it:

```
$ mkdir pitivi-dev
$ cd pitivi-dev
$ git clone https://gitlab.gnome.org/GNOME/pitivi.git
```

Whenever you want to hack on Pitivi, enter the development environment:
```
$ cd pitivi-dev/pitivi && source bin/pitivi-env
-> Setting up the prefix for the sandbox...
Using Pitivi prefix in /.../pitivi-dev/pitivi-prefix
[prefix being built, if not already...]
Running in sandbox: echo Prefix ready
Prefix ready
```

This can take a while when creating the sandbox from scratch. Note the
prompt changes:
```
(ptv-flatpak) $
```

By entering the development environment, you get:
- a [Flatpak sandbox](http://docs.flatpak.org/en/latest/working-with-the-sandbox.html)
for the dependencies, in `pitivi-dev/pitivi-prefix`
- a [Python virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/)
with development tools, such as
[pre-commit](http://pre-commit.com),
in `pitivi-dev/pitivi/build/flatpak/pyvenv`
- the [Meson build directory](http://mesonbuild.com/Quick-guide.html),
in `pitivi-dev/pitivi/mesonbuild`
- some aliases for the build tools, such as `ninja`, so they are executed in the sandbox.

Now that you are in the development environment, try running the
[unittests](Testing.md):
```
(ptv-flatpak) $ ninja -C mesonbuild/ test
Running in sandbox: ninja -C mesonbuild/ test
```

Hack away, and check the effect of you changes by simply running:
```
(ptv-flatpak) $ pitivi
```


### Updating the development environment

To update the dependencies installed in the sandbox, run:
```
(ptv-flatpak) $ ptvenv --update
```

That will actually recreate the sandbox prefix, updating all
dependencies from their git repos and tarballs as defined in the
[flatpak
manifest](https://git.gnome.org/browse/pitivi/tree/build/flatpak/pitivi.template.json) (located at `build/flatpak/pitivi.template.json`).


### Building the Pitivi C parts

Select parts of Pitivi are written in C and need to be built when changed,
such as the audio envelope renderer for the audio clips. Build them with:
```
(ptv-flatpak) $ ninja -C mesonbuild/
Running in sandbox: ninja -C mesonbuild/
```


### Hacking on Pitivi dependencies (Meson)

If you have to work on say, [GStreamer Editing Services](https://gstreamer.freedesktop.org/modules/gst-editing-services.html)
which is built using the Meson build system, first clone it into your
`pitivi-dev` folder:
```
(ptv-flatpak) $ git clone git://anongit.freedesktop.org/gstreamer/gst-editing-services
```

Prepare its build directory. Once it has been set up, you won't have to
run `meson` again for this build directory.
```
(ptv-flatpak) $ setup
Using Pitivi prefix in /.../pitivi-dev/pitivi-prefix
Running in sandbox: meson mesonbuild/ --prefix=/app --libdir=lib -Ddisable_gtkdoc=true -Ddisable_doc=true
```

Build and install it in the sandbox:
```
(ptv-flatpak) $ ninja -C mesonbuild/ install
Using Pitivi prefix in /.../pitivi-dev/pitivi-prefix
Running in sandbox: ninja -C mesonbuild/ install
```

In the `(ptv-flatpak)` development environment `meson` and `ninja` are
aliases which run meson and ninja in the flatpak sandbox.

NOTE: When updating the environment with `ptvenv --update`,
it will use your local dependencies repositories it finds in the
`pitivi-dev` folder, instead of the default remote repositories.
This means you have to update them yourself.
Also beware that it will not take into account not committed
changes.


### Hacking on Pitivi dependencies (Autotools, Make, etc)

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
