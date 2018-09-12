# 2008.7.28 interview notes

I'll call my friend M. M. Is a 3D animator working for a gaming company,
so his editing needs are somewhat different than the average
videographer or editor. His duties include producing high-quality stills
and shorts for promotional purposes, as well as in-game cinematics
(ICG). Most of his sequences are pre-rendered, and brought in as
sequenced images. In general, the sequences are rendered to their
finished length and only occasionally are the sequences trimmed down.

After lunch with M, he showed me how he performed simple editing tasks
in Adobe Premiere. He discussed how Premiere differed from its
alternatives. For comparison he also performed similar tasks in After
Effects. He commented that Premiere doesn't focus on individual frames.
After Effects is much more focused on frame-accurate editing and
keyframing. M. said that he actually preferred using After Effects for
most editing tasks. He also showed me how Maya handles animation through
two separate interfaces: the dope sheet, and the graph. The dope sheet
hearkens back to traditional 2D animation as a means of timing lip
movements to speech sounds. The property graph directly displays the
mathematics of a property as they change over time.

# M.s Comments

-   When moving one source affects all the sources after it, this is
    called a “ripple edit”.
-   The project's framerate and resolution are completely determined by
    the output media. Usually, the editor \[person\] knows in advance
    what their output format is. Changing these settings is not usually
    done, and when it is, a loss in quality is expected.
-   FCP tries to provide direct manipulation of more abstract editing
    concepts, and high degree of immediate feedback, which is what
    people like about it. It gets the job done, but things don't seem to
    feel as tactile or immediate.(\*)
-   M. claims to have an intuitive feel for “numbers”, meaning numeric
    property values. When he sets a key-frame value on a cross-fade, for
    example, he has a fairly good idea of what 35% means.
-   It's rare that an editor would first move the play-head position to
    a point in the timeline that they wanted to see, and then make a cut
    or an edit.

# My Observations

-   Premiere didn't render effects or transitions in real time even on a
    powerful machine.
-   Premiere doesn't allow sources to overlap each other in the
    timeline. Dropping one source onto another causes the new source to
    be spliced into the existing one. There's no easy way to rejoin the
    source, though you can always stretch the existing source back to
    its original length.
-   Applying a time stretch in premiere was somewhat difficult. In after
    effects, the time remapping feature made complicated frame-rate
    manipulations a fairly straightforward keyframing process.

# M's Suggestions for PiTiVi

-   When moving a source, the viewer should show the frame before the
    source cuts in, rather than the play-head position
-   When trimming a source, the viewer window should show the start
    point in that source, rather than where the play-head position.
-   Put as much functionality directly in the timeline as possible, as
    it's often easier to manipulate.\*

(\*) Statements marked with an asterisk are speculations about other
user's preferences, and should be taken with a grain of salt.
