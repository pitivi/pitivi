# 2011 ― Rendering Presets Proposal

## What is its ultimate goal?

The ultimate goal of this project is to make it easier for PiTiVi users
to intuitively edit and share videos.

## What components will it have?

I will be creating modules for PiTiVi using GStreamer.

## What benefits does it have for GStreamer and its community?

Currently, PiTiVi is the one of the leading video editors on Linux which
uses GStreamer. It is bundled with Ubuntu. It is very simple to use but
lacks a few essential features which, if implemented, would greatly
expand its userbase. It would be a major boost for the GStreamer and
PiTiVi community.

## Why you’d like to complete this particular project?

While PiTiVi has many necessary functions, it is lacking in the
following areas:

### 1. Rendering presets

Most users want the output formatted for a specific device or service –
YouTube, iPod, iPhone, DVD, mobile, etc. Presently, the user would have
to manually specify the codecs, container and codec settings like
resolution, frame rate,etc. He would have to either be familiar with the
codecs or would have to google it up.

   1. The user should just be able to click on the output format and render. This would enable us to expand the userbase to people without much codec knowledge.
   2. User can add, remove and rename presets and edit codec settings within the render dialog menu.
   3. The presets should be stored separately and the user should be able to import and export presets from GUI.
   4. Enable us to bundle a default set of rendering and project setting presets

Presets Suggested : iPod , iPad, PlayStation 3, DVD (NTSC, PAL), HTML5 (
Theora + Vorbis ), Flash video (for embedding), HD (using mkv -&gt; good
compression)

Reference : [](design/Rendering_Profiles.md)

### 2. Upload to video services

Users should by able to easily upload their videos to YouTube, Vimeo,
Archive.org and DailyMotion from PiTiVi using their respective APIs
through the intuitive GUI.

Create a uploader class to make integrating other video services in the
future easier.

Support limitations of each – file size, splitting

### 3. Fix UI Bugs

Users have reported for multiple GUI enhancements. Though they have
normal priority, coding it would greatly improve the easy of use

Easy:

   1. Bug 622079 – Use current clip’s parameter -> Club with render profile setting
   2. Bug 608682 – Ability to add markers to identify scenes and as a visual reminder in timeline, Add with Insert -> Marker and keyboard shortcut
   3. Bug 594485 – Ask for confirmation before deleting previously rendered file
   4. Bug 630374 -Add the ability to export the image currently seen in the viewer
   5. Bug 608108 – More details in unsaved dialog box
   6. Bug 578671 – Catch encoder exceptions and show in debugger window
   7. Bug 586071 & Bug 622563 – Custom labeling of clips

Moderate 1:

   1. Bug 575464 – Vertical timeline markers for every defined duration (10 seconds)
   2. Bug 596131 – Implement color-correction like white balance using GStreamer ( GES? )
   3. Bug 603738 – Hide toolbar + timeline in fullscreen

Moderate 2:

   1. Bug 637078 – Ability to render only selected portion of the timeline
   2. Bug 632319 – Manual layer interface
   3. Bug 593919 – Implement cropping/panning/zooming for clips
   4. Bug 642129 – Change properties (resize, time duration) of multiple photos at one go.

## How do you plan to achieve completion of your project?

Following is a breakup of the project goals. Estimated time for each
target is in braces.

`   Up to May 23 – Study PiTiVi code. Gain indepth knowledge of GStreamer and codec settings and GooCanvas.`
`   Target 1 ( 2-3 weeks ) – Implement Preset Manager for Render`
`   Target 2 ( 2 weeks ) – Implement video uploading to YouTube, Vimeo, Archive.org and DailyMotion from GUI`
`   Target 3 ( 1 week ) – Code Cleanup – Mid-term Evaluation`
`   Target 4 ( 2 weeks ) – Implement Easy GUI enhancements`
`   Target 5 ( 2 weeks ) – Implement Moderate 1 GUI enhancements`
`   Target 6 ( 2 weeks ) – Implement Moderate 2 GUI enhancements`
`   Target 5 ( 1 week ) – Final Code Cleanup and Documentation`

## What will showable at mid-term ?

At midterm, Render profile presets and video uploading service would be
ready

## About Me

My Name is Feroze Naina, and I’m currently doing my B.Eng in Chennai,
India.

<https://github.com/feroze/>
