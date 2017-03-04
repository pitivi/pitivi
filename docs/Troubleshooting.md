# Troubleshooting

This is a list of some known issues that are recurrent in users reports.
Issues will be removed as they get fixed (or relatively soon
afterwards). See also the list of [bugs related to
rendering](https://bugzilla.gnome.org/buglist.cgi?query_format=advanced;bug_status=UNCONFIRMED;bug_status=NEW;bug_status=ASSIGNED;bug_status=REOPENED;bug_status=NEEDINFO;component=rendering;product=pitivi).
See [Bug reporting](Bug_reporting.md) for instructions on how to
get debug logs to be used for debugging and troubleshooting.

**Tip: restart Pitivi between tries**:

> When an error happens, it is possible that Pitivi may enter an
> inconsistent state (ie: the UI is not responsive anymore, or actions
> don't seem to do anything). Sometimes, restarting Pitivi may solve the
> problem. To be exact, it is a good practice to restart it between
> tries when trying to investigate and isolate bugs. In the next version
> of Pitivi based on [GES](GES.md), rendering errors will be
> [shown to
> you](http://jeff.ecchi.ca/blog/2013/04/28/no-more-stuck-render-dialogs/).

## I use cinnamon and I can't select clips in the timeline !

As of April 2014, we have spotted that issue. A bug report has been
opened against cinnamon here :
<https://github.com/linuxmint/Cinnamon/issues/2993>. Until the next
version of cinnamon, the solution is to “unset CLUTTER\_DISABLE\_XINPUT”
before launching pitivi.

## Rendering hangs at 1 second (or less) remaining

This is a known bug with Pitivi 0.15.x. There are several ways you can
reduce the probability of this happening:

-   If you have extremely long clips (ie: hours) or heavy media files
    (ie: gigabytes) in your timeline, try with smaller clips for the
    sake of testing
-   Make sure the audio track and the video track cover the whole
    timeline, without gaps. This means you must have at least one audio
    clip under the playhead at all times, and that the beginning/end of
    the timeline must match between video and audio.
-   If you're using PNG images, try with JPEGs instead.

These tricks are not guaranteed to work in all situations, but they are
some of the most common causes of rendering failing.

## Rendering doesn't start (stuck at “estimating”)

This might be due to many reasons, including an invalid codecs
combination, incorrect codec settings, or something else.

### “The rendered files weighs 0 bytes!”

That's [bug 692316](https://bugzilla.gnome.org/show_bug.cgi?id=692316),
which is most likely fixed for future versions of Pitivi
([0.91](releases/0.91.md) and newer). In that case, the workaround is
simply to try starting the render again.

### Make sure you have the proper codecs

Some codecs in GStreamer (such as Dirac) are not reliable for use with
Pitivi. When rendering, we recommend you try the following combinations
of containers and codecs:

-   Webm
    -   VP8 video
    -   Vorbis audio
-   OGG
    -   Theora video
    -   Vorbis audio
-   Matroska
    -   x264enc (H.264 video)
    -   AAC audio

Starting with Pitivi [0.91](releases/0.91.md), this will not be an issue
anymore, as bad quality codecs will not show up.

### Incorrect codec settings

Some codecs require video resolution width and height to be multiples of
4, 8 or 16. Typically, always make sure that they're at least multiples
of 2. Otherwise, some video codecs won't encode at all, sometimes
they'll encode with suboptimal or broken results.

## Playback performance is bad

See [Performance problems](Performance_problems.md).

## What are the recommended rendering settings to export to YouTube?

“Why don't Theora files work on YouTube?”

-   Youtube doesn't support Theora 1.1 videos. Uploading such files will
    result in a garbled/corrupt green video.

For files destined to YouTube, you could use this combination:

-   Container: Matroska (.mkv): matroskamux
-   Video codec: H.264: x264enc
-   Audio codec: AAC
