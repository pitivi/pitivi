# Multi-Layer Editing

## Multi-Layer is not Multi-Track

PiTiVi distinguishes between multi-layer and multi-track editing. In
PiTiVi at 'track' is a separate channel of output. A layer is a separate
input stream within a track. Multiple layers in a track combined into a
single output stream. Layers within a track have the same media type as
the track itself.

Tracks, on the other hand, may be retained as separate output streams in
the final output. All sources in a track have the same media type, but
different tracks can have any media type that PiTiVi supports. For
example, a project might involve a DVD featuring multiple angles. The
alternate angles are kept on separate video tracks. Or, a project might
feature separate audio tracks in foreign languages. But there is no
limit to what you can achieve with multiple tracks. For example, a
plug-in might allow creating stereoscopic movies using two synchronized
video tracks. But that's not all: future releases of PiTiVi will support
other media types. Subtitle information could be kept on a subtitle
track, or midi data used to control synthesizers and/or lighting systems
could be kept on a score track and edited alongside the video.

## Multi-Layer Editing

Multi-layer editing is how the notion of priority is handled in the UI.
Numeric priority is mapped to the vertical position of an object in the
timeline. The higher the source, the higher the priority. The lower the
source, the lower the priority. The object with the highest priority is
the output for the track. This object will frequently be a source, but
it may also be an effect. So, for example, two sources can be mixed
together with a superimpose effect.

The user can change the priority of an object by moving it up or down. A
new visual layer will be created if necessary.

## Multi-Track Editing

The current implementation supports a limited form of multi-track
editing: there is one audio and one video track per project. Future
releases will support not just multiple audio and video tracks, but
other media types as well. The key concept of tracks is *linking*.
Linking allows sources within separate tracks to work together.
Individual tracks can also be enabled or disabled for preview and
project rendering. Also, Moving sources between tracks is not ordinarily
possible.

### Linking and Brothers Objects

Linking means that two sources are associated so that whatever is done
to one source is also done to the other. A source can have one linked
source for every separate output track in the project. Currently this
means that video sources can be linked to audio sources, and audio
sources can be linked to video sources. Along with support for variable
numbers of tracks will come support for multi-clip linking. Finally, one
track can be linked to another track, in which case everything that is
done to one track is also done to in accordance with the *brother*
principle. This is the case, for example, between the default audio and
video tracks.

A single file might provide audio and video streams, but these are each
handled separately within PiTiVi. In order to maintain some coherence
between the two streams, we use the concept of a brother. There is a
familial link between the two sources: some piece of genetic information
is shared. An object with siblings always knows how to create or find
its siblings. When an objects siblings are cerated, they are
automatically linked together. So, for example, if a video source is
added to a video track which is linked to an audio track, the video
source's brother(s) are created, and then linked together.

### Linking in the UI

To link sources, the sources must first be selected. Each source must be
in a different output channel, or the link tool will not be active. Once
active, clicking on the link tool links sources together. If any
property common to both sources does not match, the difference between
them will be preserved across multiple edits. So, for example, if an
audio clip leads a video clip by a few seconds, both sources will move
together when dragged, but the offset will be preserved. If one source
is of higher priority (i.e. lower in the timeline), the relative
priority difference will be maintained if one source changes priority.

To unlink sources, select one or more sources. If it is linked, the
unlink tool will become active. Clicking the unlink tool will break the
link between it and any sources to which it is linked. If the sources to
which it is linked are in turn linked to other sources, they're links
will be left intact (unless they too are in the current selection).
