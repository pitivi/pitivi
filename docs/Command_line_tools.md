# Command line tools

This is a list of tools to use for developing Pitivi.

# Commands

## ges-launch

Used to play back xges files and render them.

`# Render project.xges to video.ogv.`\
`$ ges-launch-1.0 -l project.xges -o video.ogv`

## gst-launch

Launches GStreamer pipelines.

`# Play a video with the decodebin`\
`$ gst-launch-1.0 filesrc location=foo.ogv ! decodebin ! autovideosink`

## gst-inspect

Lists installed GStreamer plugins.

`# Find all plugins containing `“`2000`”\
`$ gst-inspect-1.0 | grep 2000`

`# List details of matroskamux`\
`$ gst-inspect-1.0 matroskamux`

## gst-discoverer

Prints information of a media file.

`# Print info of foo.mp3`\
`$ gst-discoverer-1.0 foo.mp3`

## gst-validate-launcher

Launches gst validate test suites.

`# -t enables blacklisted tests`\
`$ gst-validate-launcher -t ges.playback.*`

# Building

## cerbero

The GStreamer build system. Used to compile the Pitivi bundle builds or
the GStreamer SDK.

`# Build Pitivi with dependencies`\
`$ cerbero build pitivi`

## Pitivi build environment

Builds Pitivi in an own environment

`# Open shell in Pitivi environment`\
`$ ./bin/pitivi-git-environment.sh`

`# Update git repos and build everything`\
`$ ./bin/pitivi-git-environment.sh --build`

To build less packages the script checks if a sufficient GStreamer
release is installed in your system. To build a git master version in
this case, you need to set this value to a higher version:

in bin/pitivi-git-evironment.sh:

`DEFAULT_GST_VERSION=`“`1.6`”

# Debugging

## GST\_DEBUG

If you want debug information to be printed in general, you have to use
the GST\_DEBUG envoirement variable. Execute commands like so:

`$ GST_DEBUG=3 gst-launch-1.0 videotestsrc ! autovideosink`

You can also filter the debug categories

`$ GST_DEBUG=audiotestsrc:5 gst-launch-1.0 videotestsrc ! autovideosink`

## Pipeline graph

You need graphviz installed for this.

`$ GST_DEBUG_DUMP_DOT_DIR=/tmp/ gst-launch-1.0 videotestsrc ! autovideosink`

Now you can convert the dot files to png:

`$ dot -Tpng file.dot -o file.png`

## gdb

The GNU debugger. A C debugger.

To debug a segfault, you need following syntax to run gdb:

`$ gdb --args python ./bin/pitivi`

`$ gdb --args sh ges-launch-1.0 -l project.xges`
