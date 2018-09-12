# Streams

**Stream** objects help to solve two problems:

-   Identifying a data stream
-   Describing a data stream

## Identifying data streams

**ObjectFactories** can produce and/or consume data streams. But we need
some help for the following cases:

-   How many **Stream**s can it handle ?
-   How to differentiate between the different **Stream**s an
    ObjectFactory handles ?
    -   A SourceFactory might provide several audio streams, we need to
        be able to:
        -   List them
        -   Pick one
        -   Use that **Stream** with a SingleStreamDecodebin and have it
            pick THAT stream (and not another one)
-   What **Stream** is used upstream/downstream for a given **Stream**
    (Ex : A DV Video file contains a `Raw Video Stream` which is
    inherited from a `DV Video Stream`, itself inherited from a
    `DV System Stream`.)

## Describing data streams

In order to differentiate between Audio and Video data streams (or any
other media for that matter), **Stream** objects provide a description.

-   The equivalent `gst.Caps` for that given stream
-   Are two **Stream**s compatible ? If not, what can I use to make them
    compatible ?
-   They can have stream-specific metadata (i.e. mp3 bitrate, h264
    profile, ...)
