---
short-description: A list of tools useful when developing Pitivi
...

# Command line tools

This is a list of tools useful when developing Pitivi.

# Commands

## ges-launch

Used to play back xges files and render them.

```
# Render project.xges to video.ogv.
$ ges-launch-1.0 -l project.xges -o video.ogv
```

## gst-launch

Launches GStreamer pipelines.

```
# Play a video with the decodebin
$ gst-launch-1.0 filesrc location=foo.ogv ! decodebin ! autovideosink
```

## gst-inspect

Lists installed GStreamer plugins.

```
# Find all plugins containing "2000"
$ gst-inspect-1.0 | grep 2000
```

```
# List details of matroskamux
$ gst-inspect-1.0 matroskamux
```

## gst-discoverer

Prints information about a media file.

```
# Print info about foo.mp3
$ gst-discoverer-1.0 foo.mp3
```

## gst-validate-launcher

Launches gst validate test suites.

```
# -t enables blacklisted tests
$ gst-validate-launcher -t ges.playback.*
```
