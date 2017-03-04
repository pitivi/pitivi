# Dependencies

This page is intended for contributors wishing to work with the
**development version**. Otherwise, take a look at [the download
page](http://www.pitivi.org/?go=download) on the main website.

To build Pitivi, you will need the latest devel packages for gstreamer,
pygst, and all related packages. Generally speaking, you will need:

-   The latest GStreamer 1.x and plugins including headers (if your
    distro doesn't provide it). Since we often fix issues upstream in
    GStreamer, even the latest stable GStreamer 1.x releases might not
    be enough, we sometimes depend on GStreamer from git. Follow the
    [HACKING](HACKING.md) instruction to setup everything.
-   GObject introspection including header files (if your distro doesn't
    provide it)
-   automake
-   libtool
-   intltool and itstool
-   Python 3 including header files
-   PyGObject including header files
-   GTK 3 including header files
-   development headers for OpenGL/OpenGLU through Mesa (used for
    glimagesink if you're building GStreamer)
-   gtk-doc-tools, yelp-tools, gnome-doc-utils
-   gdk-pixbuf2
-   gnome-common
-   matplotlib
-   numpy
-   PulseAudio and ALSA header files

Optional but very much recommended:

-   gnome-desktop3 (for thumbnails in the media library)
-   libnotify's python bindings
-   libcanberra's python bindings (pycanberra)

Specifically, if you want to know the **exact versions of our current
dependencies**, have a look at the bottom of
[check.py](http://git.gnome.org/browse/pitivi/tree/pitivi/check.py),
specifically the “HARD\_DEPENDENCIES” and “SOFT\_DEPENDENCIES”
variables.

You can use the following commands to do that in one go:

## On Fedora

For starters, copy-paste this paragraph into a terminal to get the basic
Pitivi dependencies, as well as various build dependencies for
GStreamer:

`sudo dnf install \`\
`   gcc gcc-c++ yasm-devel python3-devel \`\
`   bison flex intltool itstool libtool libxml2-devel meson ninja-build \`\
`   gnome-common gnome-desktop3-devel gnome-doc-utils gtk3-devel gtk-doc yelp-tools \`\
`   gstreamer1*-devel mesa-libGL-devel mesa-libGLU-devel \`\
`   python3-cairo-devel cairo-gobject-devel \`\
`   pygobject3-devel gdk-pixbuf2-devel \`\
`   python3-matplotlib python3-matplotlib-gtk3 python3-numpy python3-canberra ninja-build \`\
`   redhat-rpm-config`

And then, if you need to build GStreamer (quite likely;
[pitivi/check.py](http://git.gnome.org/browse/pitivi/tree/pitivi/check.py)
or the environment script will tell you which version is required), you
need to ensure that you have all the required dependencies to build the
various GStreamer plugins. See the next section below.

### GStreamer's dependencies

The yum-builddep utility installs the RPMS needed to build a specific
package by looking at that package's source RPM in your yum
repositories. It only works for one package at a time; this python
script invokes it for each of the relevant packages. Some of the
packages are from the [rpmfusion](http://rpmfusion.org) repository so
make sure you have that repository enabled before running the script.
Copy and paste the following script into a .py file, make it executable
and run it as root:

`#!/usr/bin/env python`\
`import sys, os, pwd`

`print(`“`Will`` ``get`` ``the`` ``build`` ``deps`` ``from`` ``gstreamer1`` ``packages`”`)`\
`duck = [`“`gstreamer1`”`,`\
`    `“`gstreamer1-plugins-base`”`,`\
`    `“`gstreamer1-plugins-good`”`,`\
`    `“`gstreamer1-plugins-bad`”`,`\
`    `“`gstreamer1-plugins-bad-nonfree`”`,`\
`    `“`gstreamer1-plugins-ugly`”`,`\
`    `“`python-gstreamer1`”`,`\
`    `“`gstreamer1-libav`”`,`\
`    `“`pitivi`”`]`

`user = pwd.getpwuid(os.getuid())[0]`\
`if user ==`“`root`”`:`\
`    for wat in duck:`\
`        os.system(`“`dnf`` ``builddep`` ``-y`` ``%s`”` % wat)`\
`else:`\
`    print(`“`You`` ``must`` ``be`` ``root`` ``to`` ``run`` ``this`` ``script.`”`)`\
`    sys.exit(1)`

Also, to be able to build gst-transcoder, you will need to do this hack
on Fedora after installing “ninja-build”:

`sudo ln -s /usr/bin/ninja-build /usr/bin/ninja`

## On Ubuntu/Debian

You can simply paste the following, which should (hopefully) solve your
dependencies. This was reportedly working on Ubuntu 12.10 but package
names change all the time, so if something is missing (or you have a
better way to solve the deps), please tell us about it.

`# Basic build tools:`\
`sudo apt-get install git build-essential automake libtool itstool gtk-doc-tools yelp-tools gnome-common gnome-doc-utils yasm flex bison`

`# Stuff related to introspection, GTK, canvases, and various other dependencies:`\
`sudo apt-get install libgirepository1.0-dev python3-dev python3-gi python-gi-dev \`\
`python3-cairo-dev libcairo2-dev python3-gi-cairo python3-matplotlib python3-numpy \`\
`libgdk-pixbuf2.0-dev libpulse-dev libgtk-3-dev \`\
`libxml2-dev \`

`# GStreamer 1.x, if you're lucky and your distro packages are recent enough:`\
`sudo apt-get install gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-alsa gstreamer1.0-pulseaudio \`\
`libgstreamer-plugins-bad1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer1.0-dev libgstreamer1.0-0`

`# GStreamer plugins' full set of dependencies to build all the codecs:`\
`sudo apt-get build-dep gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly`\
`sudo apt-get install libglu1-mesa-dev`

## In a Virtual Env

If you are using python virtual environments to do your development, you
aren't going to be able to use the python library packages listed above
for your install, and the packages are not available via install tools.
Install everything \*else\* listed above (keep python-dev)and then
install the following packages.

replace (ENV) with the path to your virtual env (e.g.
/home/aleks/src/python-def/ )

WARNING: the versions used here may change, but the general build
process should still hold. If you get errors about version mismatches,
just grab the appropriate ones and start over.

### PyCairo

Download py2cairo-1.10.0 from the appropriate place, extract it, then:

`./configure --prefix=(ENV)`\
`make && make install`

I don't recall any special overrides, but depending on your distro, you
may need to do something like this if configure complains that it can't
find cairo.h:

`CFLAGS=-I/usr/include/cairo/ ./configure --prefix=(ENV)`\
`make && make install`

### PyGObject

Download pygobject-3.0.0 from the appropriate place, extract it, cd into
it, then:

`PYCAIRO_LIBS=(ENV)/include/pycairo/ PYCAIRO_CFLAGS=-I(ENV)/pycairo/ CFLAGS=-I/usr/include/cairo/ ./configure --prefix=(ENV)`\
`make && make install`

### PyGST

grab gst-python from git, cd to it, ./autogen.sh This is going to FAIL.
after that, do this:

`PYGOBJECT_LIBS=(ENV)/include/pygobject-3.0/ PYGOBJECT_CFLAGS=-I(ENV)/include/pygobject-3.0/ ./configure --prefix=(ENV)`\
`make && make install`
