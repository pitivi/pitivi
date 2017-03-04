# GStreamer from Git

The following directions will help you set up latest GStreamer from git.
See also [GStreamer using jhbuild](attic/GStreamer_using_jhbuild.md)
for an automated process that is potentially easier (and safer).

# Build system

In order to proceed from here, you need to first have a working build
system. Here are something to get you started; you might need additional
packages or some tinkering. However setting up a build environment is
beyond the scope of this tutorial.

## Fedora

<code>

`$ yum groupinstall `“`Development`` ``Tools`”

</code>

## Ubuntu

At the very least, make sure you have build-essentials and binutils.
<code>

`$ apt-get install build-essential binutils git`\
`$ apt-get build-dep pitivi`

</code>

## Your Distro Here

Add the directions for your distribution

# Set Up \~/bin

We're going to be using a couple of scripts. They'll be easiest to run
if you put them somewhere that's in your current path. I have a
directory called `bin` in my home directory that I use for this purpose.
If you already know how to do this, or you already have \~/bin in your
path, skip this section.

<code>

`$ cd`\
`$ mkdir bin`

</code>

Now edit `~/.bashrc`, and add this line to the end of the file.

`export PATH=`“`~/bin:$PATH`”

Save the file.

Now edit `~/.bash_profile` and make sure it contains the line

`. ~/.bashrc`

Save the file, then type

<code>

`$ exec bash`

</code>

`~/bin` should now be in your current path. To check this, type:

<code>

`$ env | grep PATH`

</code>

You should see a line that starts with `PATH=~/bin`

From now on when you log in or create a new terminal window, `~/bin`
will be in your current path.

# Install build dependencies

Exactly how to do this will vary from system to system.

## Fedora

On Fedora 12 install at least the following packages:

<code>

`$ yum install intltool gtk-doc liboil-devel`

</code>

And to build plugins needed to use Pitivi, install these packages
aswell:

<code>

`$ yum install libogg-devel libvorbis-devel libvisual-devel alsa-lib-devel libtheora-devel`

</code>

## Debian/Ubuntu

On debian/ubuntu the following command should suffice:

Save a list of all gstreamer library package names: <code>

`$ apt-cache search --names-only '^(lib)?gstreamer\S*' | sed 's/`$.*$` -.*/\1 /' > dependencies`

</code>

Install the build dependencies for those packages: <code>

`` $ sudo apt-get build-dep `cat dependencies` ``

</code>

## Your Distro Here

Add the directions for your distribution

## Full List of Dependencies

Someone add the full list of build dependencies here.

# Get Latest Gstreamer

## Create a Sources directory

Find a place for your gstreamer sources to go. You could use /usr/src/,
but I prefer to keep them in my home directory so that I do not need
root privileges to update them. For example:

<code>

`$ mkdir -p ~/src/gstreamer/head`\
`$ cd ~/src/gstreamer/head`

</code>

<b>N.B. that the lowest level directory must be called <i>head</i></b>.
The rest of this tutorial will assume that you are in your sources
directory.

## Checkout Sources

We're going to check out gstreamer from git. Gstreamer is split up into
several modules:

-   gstreamer
-   gst-plugins-base
-   gst-plugins-good
-   gst-plugins-bad
-   gst-plugins-ugly
-   gst-python
-   gnonlin
-   gst-ffmpeg

To check them all out at once...

    $ for i in gstreamer gnonlin gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-python gst-ffmpeg
    do
      git clone git://anongit.freedesktop.org/gstreamer/$i
    done

To check them out individually, where `module-name` is one of the
gstreamer modules, do:

<code>

`$ git clone `[`git://anongit.freedesktop.org/gstreamer/module-name`](git://anongit.freedesktop.org/gstreamer/module-name)

</code>

# Install GST\_Head Script

We do not want to install gstreamer at this point. gstreamer provides
the gst-uninstalled script which allows you to temporarily switch your
Gstreamer to an uninstalled version.

From your sources directory, copy this script to `~/bin` directory:

<code>

`$ cp ~/src/gstreamer/head/gstreamer/scripts/gst-uninstalled ~/bin/gst-head`

</code>

The reason we rename the script is that the bit after the dash (head)
refers to the sub-directory in `~/src/gstreamer` (in our case, head).
This allows you to easily have multiple un-installed versions of
gstreamer.

Now edit this file and look for the `MYGST` line. Change it to this:

<code>

`MYGST=`“`$HOME/src/gstreamer`”

</code>

<b>N.B. Each time you want to use your CVS gstreamer, you will need to
run this script. Run it like this:</b>

<code>

`$ ~/bin/gst-head`

</code>

# Build Sources

This will take a bit of time. If you have a dual- or quad-core computer,
you can replace `make` with `make -j2` in all of the following steps to
speed up the build.

First, we need to build gstreamer:

<code>

`$ cd gstreamer`\
`$ ./autogen.sh`\
`$ make`\
`$ cd ..`

</code>

Now we need to run gst-head. This allows the other plugins to build
against this gstreamer.

<code>

`$ gst-head`

</code>

You'll notice you're now in the sources directory: this is because the
gst-head script starts a subshell in this directory. This is how it is
able to make it appear as though your uninstalled version of gstreamer
is the current version.

Build all the modules using these commands, where `module-name` is one
of the gstreamer modules.

<code>

`$ cd module-name`\
`$ ./autogen.sh`\
`$ make`\
`$ exit`\
`$ gst-head`

</code>

<b>N.B. do <i>not</i> run `make install`</b>

Build the modules in this order:

-   gst-plugins-base
-   gst-plugins-good
-   gst-plugins-bad (optional)
-   gst-plugins-ugly (optional)
-   gst-python
-   gnonlin
-   gst-ffmpeg (optional)

# Congrats

If you got to this step, you should be able to check out the CVS version
of PiTiVi. Make sure you run

<code>

`$ gst-head`

</code>

before you try to start PiTiVi, or PiTiVi will not find your new
versions of gstreamer. You will have to do this once every time you log
in, or every time you want to start PiTiVi in a new terminal. If you
decide you are done using the new version of gstreamer, you can type

<code>

`$ exit`

</code>

in your terminal to exit the subshell started by running gst-head.

# `gst-inspect` is your friend

This section will explain how to use gst-inspect to verify that your
installation is complete.

# Updating
