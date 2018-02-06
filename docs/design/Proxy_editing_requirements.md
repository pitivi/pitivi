# Proxy editing requirements

See [T2455](https://phabricator.freedesktop.org/T2455) to learn about
proxy editing and why we want this in [GES](GES.md) and Pitivi.
This page is meant to brainstorm:

-   User interface/user experience (UX) possibilities and requirements
-   GES API requirements deriving from that. This also touches on media
    assets management in general.

Prior art if you don't know what proxy editing “feels” like:

-   [In Edius](http://www.youtube.com/watch?v=SyUvp0YqLpc). This is an
    interesting example of a badly designed UI: pretty much all the
    options/preferences presented there are useless, the application
    should be smart enough to make those choices!
-   [In FCP X](http://www.youtube.com/watch?v=MnZx3JxoR-A) (alternative
    [longer version](http://www.youtube.com/watch?v=aL7gE-my4_c))
-   [In Sony Vegas](http://www.youtube.com/watch?v=4PE6tDjgDEY)
-   Others we should be looking at in particular? Some particularly
    great (short and to the point) video tutorials of other apps we
    ought to see? Let us know.

# User experience

As [T2455](https://phabricator.freedesktop.org/T2455) indicates, we can
envision two types of user experience: a semi-automatic and a
fully-automated one. Since Pitivi is not the only application (now and
in the future) using GES, we need to design the GES API to be flexible
enough to accommodate the design needs of both kinds of applications.

In both cases, the experience must be:

-   Intuitive: it should be a very easily discoverable feature
-   With good visual indications of the process and progress. We should
    probably have some sort of “yellow/green light” (red for errors)
    icons somewhere near each clip in the media library to indicate the
    status of individual proxies. Remains to be seen how we can do this
    with iconview mode and listview mode without going insane.
-   Fluid, with no negative performance impacts from the act of
    generating the clip “proxies”

## Icons representation

Since the Media Library's iconview is meant to be compact and
minimalistic (and has a fair amount of technical limitations), we could
use the following icon metaphor system to indicate the states of proxies
for assets:

  Status icon   Icon's opacity   Thumbnail's opacity   Meaning
  ------------- ---------------- --------------------- ----------------------------------------------------------
  None          N/A              100%                  Proxies are disabled for this asset
  Gears/sync?   100%             50%                   A proxy is currently being generated for this asset
  Checkmark     70%?             100%                  Proxies are present and ready for this asset
  ⚠ (warning)   100%             100%                  The proxy could not be generated for this asset
  ⚠ or X        100%             50%                   A proxy file is present, but the original file is absent

## Manual/semi-automated UX

In this mode, users would manually select which assets/clips use
proxies, and when the proxies are generated. There would be no
“automated” background processing. This is probably not what we want in
Pitivi in terms of the default user experience, however the GES API
should support that scenario. We could still provide this feature in
pitivi by:

1.  Having an option in the preferences, under the “Performance”
    section: “Automatically create proxies for clips in the media
    library”
2.  If that option is disabled, show a toolbar button in the media
    library that, when clicked, generates the proxies for selected
    clips.

However this also means temporarily providing a “Cancel” button while
those clips' proxies are being generated. Additionally to the “status
lights” icons mentioned earlier, we could perhaps show a progressbar
(with a “Stop” button on its right) below the media library (similar to
when we're importing clips).

Jakub commented:

> “Semi-automatic - I don't grok this experience. Why would I want to
> explicitly hold the burden of being a transcoding manager? I like the
> validity checking and ability to explicitly re-render a proxy though.
> Ran into issues in both kdenlive and FCPX where I spent ages looking
> for a faulty proxy.”

To balance things, Bassam commented:

> "manual vs. automatic: however the ui is chosen, this should be a per
> project setting, not a choice of a different application. both
> workflows are valid, and the same person might opt for one or another
> depending on the specifics of the project. \[...\]

## Fully-automated UX

Otherwise, the default behavior would be to transparently (and
intelligently) create proxies for everything, in the background. When a
proxy file does not exist for an asset (clip), create it and use it as
soon as it has been created.

Performance requirements in the automated scenario are even more
important than in the semi-automated scenario; while users can expect
some delay (as long as there is a visual progress indication) when they
manually trigger an action, they must absolutely *not* feel
delays/sluggishness when such actions are triggered automatically. The
generation of proxy clips in the background should not negatively impact
system performance.

Jakub has a different opinion than Jeff's or Bassam's, suggesting (?)
that we make proxy generation a modal (blocking, in terms of UI)
operation:

> "You mention the problem of indicating the transcoding process as if
> you could continue working with original assets and have that not stop
> you from editing work with original media. In case of offline editing
> (either having assets on external drive, or networked/cloud storage),
> the indication can be summed up to “tell me when my assets are safe to
> disconnect and I'm able to proceed editing offline”. For low
> performing systems, the background transcoding is just an illusion,
> you cannot really edit until your assets are transcoded. So I think
> both cases are best addressed by providing an aggregate progressbar
> telling me when all assets referenced from the project are transcoded,
> rather than colorcoding individual clips, or worrying about preview
> overlays. \[...\] For offline editing I would agree not choking the
> system competely with transcoding might be a good thing, but for the
> low performing system case you want the transcoding process to take
> the foreground so that the assets are ready sooner. You really can't
> do any 4k editing on a laptop and expect to also transcode proxies in
> the background."

# GES API requirements

## Control

-   Proxies generation/processing needs to be pause-able
    -   When pitivi starts playback (or render) and needs the system's
        resources
    -   When the user pauses proxy generation (in the case of the
        semi-automated UX)
-   Proxies generation needs to be cancel-able
    -   When the user asks to stop generating proxies for selected clips
        (in the case of the semi-automated UX)
-   The ability to “force” regenerating the proxies for a given asset
    (for whatever reason)
-   Delete a proxy (or all proxies) for a given asset
-   Relocate/move proxies for a given asset or for all assets
-   Ability to manually replace an offline asset.

## Data integrity checking

-   Need a way to detect incomplete or invalid proxies, to handle
    various scenarios:
    -   The user has quit the application before it was done processing
    -   The application crashed
    -   The source file has changed (use a md5 on the first few bytes of
        the file like in pitivi/previewers.py and store that hash in the
        GES Asset?)

## Signalling/notifying

-   For each asset, report the proxies' encoding progress, so the
    application UI can show progressbars or some other form of visual
    indications
-   Provide a way to signal to the application that an asset has its
    original offline, or its proxy offline, or whatever situation we can
    imagine, so the UI can let the user know about it.
-   Tolerate and signal errors/failures.

## Fault tolerance and sandboxing

-   Tolerate and signal errors/failures.
-   Processing should probably happen in a separate/sandboxed process,
    to ensure that GES/applications can't crash because of something
    going wrong during the processing of a proxy
-   GES needs to handle the notion that an asset and/or any of its
    proxies can go offline/online. For example, if the original clip is
    not available but the proxy version is present, consider the
    original “offline” and use the proxy version.
    -   The way we handle “missing” media needs to change: currently
        Pitivi just refuses to handle “partial” projects, but in theory
        it should “deal with it”. Even if all the assets of a clip
        (including proxies) are offline.
    -   If an asset or its proxies were moved/renamed externally, allow
        specifying the new location (already mostly implemented in GES
        assets?), but don't force it. Proxies/assets for which the user
        has not provided replacements are to be marked as temporarily
        “offline” (we should also save info about the last time it was
        seen, its metadata/attributes, etc.).

## Additional API flexibility

-   Multiple ways to handle offline assets for rendering and export:
    -   “Draft render” mode (low quality render using only the proxies
        instead of the original clips), as some applications might like
        to offer that feature.
    -   Rendering to a multimedia output file requires original assets
        to be “online”. Otherwise, if only proxies are available, we
        can:
        -   Warn the user about reduced quality. If some assets have no
            originals and no proxies, show a serious warning.
        -   Export only an EDL (edit decision list), but that's [another
            story](https://bugzilla.gnome.org/show_bug.cgi?id=674605)
-   Provide a way to specify which containers, codecs and settings (ex:
    video resolution, bitrate/quality) to use for proxies. This will
    probably use a technology similar to what we see in Pitivi's render
    dialogs.
-   Allow multiple proxies per asset (for multiple resolutions, for
    example). The application should be able to request a proxy to match
    a particular context (ex: a maximum resolution or something); for
    example, multicam editing could use very small versions if there is
    a big number (ex: 16) of camera angles to be displayed
    simultaneously. Or the media library could automatically show a
    playing thumbnail-sized video preview when putting the mouse over a
    clip.
-   Ability to save, in a project formatter's data, the following
    per-project overrides of the global app settings:
    -   A custom folder path for the proxies for that project (see also
        the “where to store the proxies?” item in the “outstanding
        questions” section on this page).
    -   Whether this project prefers fully-automated (or manual)
        handling of proxies (Bassam said: “However the ui is chosen,
        this should be a per project setting, not a choice of a
        different application. Both workflows are valid, and the same
        person might opt for one or another depending on the specifics
        of the project.”)

# Outstanding questions

-   Where to store the proxies? (beyond the obvious question of disk
    space and tidiness, there's the question of people working across
    networks that raises interesting questions)
    -   In pitivi we could default to the XDG user cache dir (which in
        this case would turn out to be \~/.cache/pitivi/proxies/)
    -   ...but Bassam insists that this can be overridden on a
        per-project basis. So in the project settings UI, we could have
        a checkbox to “Use a custom directory to store proxies” that
        enables a gtk folder chooser button right besides it. Unchecking
        the checkbox would clear the project's custom directory.
-   Filenames of the actual proxy files depending on their location
    (global cache folder vs project folder?). For example, if a clip is
    called “foo.MOV”, should the proxies be called foo-360p.gesproxy, or
    foo--proxy-360p.webm, or C462NTH353.webm in the hidden cache folder,
    or...?
-   Codecs? So far we're hesitating between MJPEG and VP8. MJPEG is
    handsdown the fastest codec to seek and to encode, since it is so
    simple and every frame is a keyframe - however, the filesize is
    rather big. VP8 is more configurable and can be made to approximate
    MJPEG's seeking performance, but it is significantly more expensive
    to encode.
-   Resolutions, and how to handle aspect ratios. That is, how do you
    determine the appropriate resolution depending on the aspect ratio
    and resolution of the source material?
    -   Going with a hardcoded percentage (ex: 50% of the original's
        resolution) can be bound to fail in scenarios where the original
        has a huge native resolution (such as 4K).
    -   Alternatively, one can imagine a hardcoded (or configurable)
        “max resolution”, where clips bigger than that resolution will
        have proxies created to “fit the box” (in terms of width and
        height, whichever comes first). Hardcoding the box resolution
        might be problematic as computers become more powerful and
        screen resolutions increase.
    -   Ideally, we need a clever algorithm to figure out all of this
        automatically. Any rough ideas of the logic here? Let us know.
        Solutions where the software can be smart enough to figure the
        optimal resolution to use, instead of having the user deal with
        it, are preferred.
-   Handling “tarball export” in Pitivi
