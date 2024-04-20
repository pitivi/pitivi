---
short-description: What the GSoC students did in the previous years
...

# Past GSoCs

See [Google Summer of Code](Google_Summer_of_Code.md) for how to get involved.

## 2023

-   [Jainil Patel](https://jainl28patel.github.io/posts/Pitivi_Gsoc_finalReport/) continued the monumental task of porting the app to GTK4. Great progress.
-   [Rhythm Narula](https://medium.com/@rhythm.narula26/gsoc-pitivi-project-crafting-closing-credits-clip-generator-5454088a570d) researched how to integrate a Closing Credits Clip Generator, working on top of the GTK4 branch.

## 2022

-   [Thejas Kiran P S](https://thejaskiranps.github.io/blog/posts/final/) did great enhancements to the timeline.
-   [Aryan Kaushik](https://aryank.in/posts/2022-09-11-pitivi-gsoc-final-report/) paved the way to porting of the UI codebase from GTK3 to GTK4. Great progress.

## 2021

-   [Piotrek Brzeziński](https://thewildtree.github.io/) integrated
    [librosa](https://librosa.org/) to allow [detecting music
    beats](https://thewildtree.github.io/2021/08/22/gsoc-summary/). The beats
    are displayed as markers on the clip. GES had to be extended so that clips
    snap to these markers when dragged.
-   [Pratyush Tiwari](https://unhired-coder.github.io/index.html) refactored the
    timeline to be able to introduce, in addition to the zoomed-in timeline, a
    second timeline which is always zoom-fitted. This allows [quick operations
    across different regions of the
    timeline](https://unhired-coder.github.io/project.html).

## 2020

-   [Abhishek Kumar Singh](https://gaharavara.github.io)
    refactored the Media Library to use a single `Gtk.FlowBox` for both the
    Icon view and the List view modes. This allowed implementing [tagging of
    the clips](https://gaharavara.github.io/gsoc-2020-final-report/) in the
    Media Library.
-   [Ayush Mittal](https://ayush9398.github.io/blog/) simplified the Render
    Dialog to avoid overwhelming people, while still allowing full control.
    The new UI asks only about the desired render preset and quality,
    [taking care of the
    rest](https://ayush9398.github.io/blog/GSOC'20-work-product).
-   [Vivek R](https://123vivekr.github.io/) implemented object tracking.
    This required a new GStreamer element which uses
    [OpenCV](https://docs.opencv.org/4.4.0/d2/d0a/tutorial_introduction_to_tracker.html)
    to track an object.
    A new UI perspective allows tracking objects and editing the tracked data.
    For now it's possible to [cover each tracked
    object](https://123vivekr.github.io/2020/08/29/pitivi-gsoc-work-product.html)
    with a colored rectangle.

## 2019

-   [Millan Castro](https://millancv.github.io/) implemented [timeline
    markers](https://millancv.github.io//GSoC-3/).
-   [Swayamjeet Swain](https://swaynethoughts.wordpress.com/)
    implemented support for [nested
    timelines](https://swaynethoughts.wordpress.com/2019/08/25/gsoc-2019-final-report/).
-   [Yatin Maan](https://yatinmaan.github.io/) improved the [effects
    usability](https://yatinmaan.github.io/2019/08/26/GSoC-19-Final-Report/).
    The Effects Library has been refactored to provide a better experience.

## 2018

-   [Harish Fulara](https://harishfulara07.wordpress.com/) implemented
    a framework for showing different UI perspectives. The existing
    main UI has been refactored into the EditorPerspective, and
    the welcome dialog has been replaced by a new gorgeous and modern
    [GreeterPerspective](https://harishfulara07.wordpress.com/2018/08/13/gsoc-2018-final-report-pitivi-ui-polishing/).
-   [Suhas Nayak](https://suhas2go.github.io) worked on the slow motion
    support in [GES](GES.md), but had to interrupt.
-   [Yatin Maan](https://yatinmaan.github.io/) implemented support
    for [Scaled Proxies](https://yatinmaan.github.io/2018/08/14/GSoC-18-Final-Report/).

## 2017

-   [Fabián Orccón](https://cfoch.github.io/) implemented a
    [plugin system](https://cfoch.github.io/tech/2017/08/28/wrap-up-and-code-submission.html)
    which has been merged. We noticed too late the excellent additional
    Developer Console plugin had licensing issues, and it has been
    merged one year later after Fabian graciously made time to rewrite it.
-   [Suhas Nayak](https://suhas2go.github.io) implemented a [framework for
    supporting custom UI for effects](https://suhas2go.github.io/gnome/pitivi/2017/08/28/GSoCFinalReport/),
    instead of the UI generated automatically. Suhas used the new framework to
    provide a polished UI for the `frei0r-filter-3-point-color-balance` and
    `alpha` effects.
-   [Ștefan-Adrian Popa](https://stefanpopablog.wordpress.com) implemented
    the UI for the [Ken-Burns
    effect](https://stefanpopablog.wordpress.com/2017/08/22/gsoc-2017-coming-to-an-end/),
    including keyframing the placement and zoom of the clips by interacting with
    the viewer. Additionally, Ștefan fixed a lot of bugs [most of them unrelated
    to his main
    task](https://gist.github.com/stefanzzz22/260fa2be10bccd7404af87152ecd5a88).

## 2016

-   [Jakub Brindza](https://github.com/jakubbrindza) implemented
    [customizable keyboard
    shortcuts](http://www.jakubbrindza.com/2016/08/gsoc-with-pitivi.html).

## 2014

-   [Fabián Orccón](https://cfoch.github.io/) worked on the Pitivi,
    GES, GStreamer stack to allow using image sequences.
-   [Lubosz Sarnecki](https://lubosz.wordpress.com/) worked on
    implementing a new OpenGL based transformation effect to be used for
    the transformation UI.

## 2013

-   Anton Belka worked on the initial
    implementation of proxies in [GES](GES.md) (see [proxy
    editing requirements](design/Proxy_editing_requirements.md)).
-   Joris Valette started work on slow/fast-motion in GStreamer.
-   [Mathieu Duponchelle](https://mathieuduponchelle.blogspot.com/)
    worked on heavy bugfixing all across the Pitivi, [GES](GES.md) and
    GStreamer stack, allowing us to release [0.91](releases/0.91.md) at
    the end of the summer.
-   [Simon Corsin](https://github.com/rFlex) worked on various pieces
    alongside Mathieu, such as the new waveforms renderer.

## 2012

-   Matas Brazdeikis implemented a new UI [Test
    suite](Testing.md) using Dogtail. He also started the
    implementation of a title editing user interface.
-   [Paul Lange](https://palango.wordpress.com/) implemented a manual
    layer controls user interface for the timeline.
-   Volodymyr Rudoy spent some time
    designing the GES “Materials” (now known as Assets) API.

In addition, we also co-mentored Pēteris Krišjānis who worked on an
audio waveform generation and display library for GStreamer (see his
[post-summer
report](https://pecisk.blogspot.com/2012/11/state-of-libwaveform-after-gsoc.html)).

## 2011

-   Feroze Naina worked on adding [profiles for rendering](Feroze_gsoc.md).
-   [Lubosz Sarnecki](https://lubosz.wordpress.com/) implemented a nifty
    user interface for [resizing/cropping clips directly in the
    viewer](https://lubosz.wordpress.com/2016/09/26/making-viewer-uis-for-pitivi/).
-   [Mathieu Duponchelle](https://mathieuduponchelle.blogspot.com/)
    started to port PiTiVi to GES after having worked on the GES Python
    bindings and the GES Pitivi formatter.

## 2010

-   [Thibault Saunier](https://blogs.gnome.org/tsaunier/) implemented
    with the core backend developers special effects. He also worked in
    close collaboration with [Jeff](https://gitlab.gnome.org/jfft) on the user
    interface and testing.

## 2008

-   [Brandon Lewis](https://dotsony.blogspot.com/) worked on the [advanced
    timeline](https://dotsony.blogspot.com/search?updated-min=2008-01-01T00:00:00-08:00&updated-max=2009-01-01T00:00:00-08:00&max-results=41).
-   [Sarath Lakshman](http://www.sarathlakshman.com/about/) implemented
    [webcam capture](http://www.sarathlakshman.com/2008/09/28/pitivi-hacks).

## 2007

-   [Brandon Lewis](https://dotsony.blogspot.com/) worked on the [simple
    timeline](Google_SoC_2007_-_Simple_Timeline.md).
