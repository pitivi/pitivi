# GStreamer using jhbuild

JHBuild is a build tool that automates the process of building the GNOME
software stack. It is organized somewhat like a package manager and is
cabable of tracking dependencies between packages. JHBuild elminates a
great deal of the work of compiling GStreamer manually.

**Warning: The following instructions are not supported** by the PiTiVi
developers. They are provided for informational purposes only. The
author takes no responsibility for damage you may cause to your system
as a result of attempting to follow these instructions. Proceed at your
own risk! Your results may vary.

# Intended Audience

This document is primarily intended for PiTiVi developers and testers
who need to test PiTiVi against the latest development versions of
gstreamer. It is emphatically **not intended for end users** You are
assumed to be familiar with the process of compiling software from
source, and how to deal with problems when they arise.

These instructions assume a debian-based system. For non-debian systems,
replace the apt-get commands and package names with those appropriate
for your distro.

For more information on JHBUild, see <http://live.gnome.org/Jhbuild>

# Installing GStreamer Using JHBuild

First things first: Make sure your system is up-to-date, and for ubuntu,
make sure universe, multiverse, etc are enabled in System -&gt;
Administration -&gt; Software Sources. Then run:

`sudo apt-get install git-core gettext build-essential \`\
` libglew1.5 libglew1.5-dev python-gtk2-dev autoconf \`\
` automake1.9 cvs libxml2-dev liboil0.3-dev subversion`

Get some coffee...

## Install GStreamer Build Dependencies

`sudo apt-get build-dep libgstreamer0.10-0 libgstreamer-plugins-base0.10-0 \`\
`gstreamer0.10-{plugins-{good,bad,ugly},ffmpeg}`

On Debian and Ubuntu Maverick you may also need to install `autopoint`

`sudo apt-get install autopoint && \`\
`sudo apt-get build-dep libgstreamer0.10-0 libgstreamer-plugins-base0.10-0 \`\
`gstreamer0.10-{plugins-{good,bad,ugly},ffmpeg}`

Get some more coffee...

To have the x264 encoder (for H.264) available, you should also install
the **libx264-dev** package.

## Configure Your Environment

If you do not have \~/bin and \~/src directories, create them:

`cd`\
`mkdir bin`\
`mkdir src`

If \~/bin and \~/.local/bin are not already in your path, do this:

`echo 'export PATH=${HOME}/bin/:${HOME}/.local/bin:${PATH}' >> ~/.bashrc`\
`exec bash`

## Install JHbuild

`cd src`\
`git clone `[`git://git.gnome.org/jhbuild`](git://git.gnome.org/jhbuild)\
`cd jhbuild`\
`make -f Makefile.plain`\
`make -f Makefile.plain install`

## Install gst-jhbuild Script

`cd ~/bin`\
`cat > gst-jhbuild << `“`EOF`”

And paste the following (then press Enter):

    #!/bin/bash

    JHBUILDFILE=$HOME/src/gstreamer/jhbuild/gstreamer.jhbuildrc
    jhbuild -f $JHBUILDFILE "$@"

    EOF

Then run:

`chmod +x gst-jhbuild`

## Install JHBuild Config Files for GStreamer

`cd`\
`mkdir -p src/gstreamer/jhbuild`\
`cd src/gstreamer/jhbuild`\
`cat > gstreamer.jhbuildrc << `“`EOF`”

And paste the following:

    # gstreamer.jhbuildrc

    moduleset = [os.path.expanduser('~/src/gstreamer/jhbuild/gstreamer.modules')]
    modules = [ 'my-gst-all' ]
    checkoutroot = os.path.expanduser('~/src/gstreamer/repos')
    prefix = os.path.expanduser('~/src/gstreamer/install')
    autogenargs = ''
    autogenargs = autogenargs + ' --disable-static'

    # consider commenting this out on a single-core system or using -j3, -j4 or -j7
    # on systems with > 2 cores
    makeargs = "-j2"

    os.environ['ACLOCAL'] = 'aclocal -I ' + prefix + '/share/aclocal/'
    os.environ['INSTALL'] = os.path.expanduser('~/bin/install-check')

    EOF

If you want to disable building documentation (to save time), use the
--disable-gtk-doc parameter, like so:

`autogenargs = autogenargs + ' --disable-static --disable-gtk-doc'`

Then run:

`wget `[`https://github.com/emdash/gst-jhbuild/raw/f5decae2003b02ce0c19eb677c354649a69ceedb/gstreamer.modules`](https://github.com/emdash/gst-jhbuild/raw/f5decae2003b02ce0c19eb677c354649a69ceedb/gstreamer.modules)

Note: the official gstreamer module set is [available
here](http://webcvs.freedesktop.org/gstreamer/jhbuild/gstreamer.modules?revision=HEAD).
Using the official module set may require changes to gstreamer.jhbuildrc

## Build gstreamer

`cd`\
`gst-jhbuild build`

Get lunch...

# Problems

If you're lucky, you'll have a freshly-built copy of gstreamer when you
come back from lunch. If you're unlucky, you'll be staring at a prompt
similar to this one:

    *** Error during phase build of gstreamer: ########## Error running make -j2 *** [1/10]

     [1] Rerun phase build
     [2] Ignore error and continue to install
     [3] Give up on module
     [4] Start shell
     [5] Reload configuration
     [6] Go to phase "wipe directory and start over"
     [7] Go to phase "configure"
     [8] Go to phase "clean"
     [9] Go to phase "distclean"

If a build failure occurs, it's probably because one or more of the
above steps were performed incorrectly. Go back over everything and
figure out what you did wrong. Likely sources of error are missing
dependencies. Beyond that, you are assumed to be familiar with the
process of building software from source and capable of resolving issues
with software compilation. Having said that, sometimes waiting a few
minutes and trying again with option \[6\] will magically just work.

One hint you can use to diagnose problems with gstreamer.jhbuildrc and
gstreamer.modules is to start a subshell and see if the sources build
normally when you run

`make clean && ./autogen.sh && make`

If the sources build normally in this fashion but not using JHBuild, you
can bet that JHBuild or its configuration files are to blame.

Option \[4\] will start a shell at that build phase. You can use it to
tweak the source tree as you see fit, and when you exit the shell you'll
be returned to the menu where you can resume the build process.

**Note:**

-   if you want to continue build at the configuration phase (i.e.
    re-run ./configure), do that from the menu! Otherwise, the install
    phase will fail.
-   if you change gstreamer.jhbuildrc or gstreamer.modules, you can try
    to reload the configuration with option \[5\] but in the author's
    experience, your best bet is to kill and re-start JHBuild.

If you think you've determined that there is a problem with the
gstreamer.jhbuildrc, gstreamer.modules, or these instructions, report
this on the PiTiVi irc channel or on the PiTiVi mailing list. We will
try to keep the JHBuild config files up-to-date.

Keep in mind that the PiTiVi developers want to spend their time working
on PiTiVi, and any issues you have with gstreamer or its dependencies
should be taken up with the developers and maintainers of those
projects. The PiTiVi developers will **not** help you figure out why
gstreamer dependency XYZ won't build on your box.

# Using Your Installation

Running `jhbuild build` does not replace your system libraries. Instead,
you run gstreamer applications in a subshell as follows:

`gst-jhbuild run `<your gstreamer application here>

To simply start a shell (to avoid having to keep typing gst-jhbuild with
repeated invocations):

`gst-jhbuild shell`

When you wish to update GStreamer, run this command:

`gst-jhbuild update && gst-jhbuild build -ac`

Keep in mind that you may encounter build errors when updating as well.
See the Problems section above.
