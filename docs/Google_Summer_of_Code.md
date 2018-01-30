# Google Summer of Code

The [Google “Summer of Code” program] is available for students only. If
we accept your project proposal, in June-July-August you work on your
project while being paid by Google. Mid-term and end-term we evaluate
your work.

On the technical side, it might interest you that we use GES/GStreamer
as backend, GTK for the UI, the Meson build system, and Flatpak to make
builds for users. Flatpak also allows us to have a sandboxed development
which means it's very easy to setup, you are set up in no time, and you
don't have to run a virtual machine or f\*\*k up your system to be able
to build the latest GStreamer and Pitivi. See the section at the top of
the [contributing page] for details why Pitivi is important.

While a GSoC with us is one of the most fun and rewarding experiences
you can get, you need to consider it as *professional work*:

-   **GSoC projects are on a “full-time” basis, not “part-time”**. What
    this means is that you should not apply if you have some strange
    schedule where, for example, you have school exams for many weeks
    between early May and late August. If you have school
    exams/obligations during the summer, *you need to mention them* and
    account for them in your schedule.
-   **No excuses!** We expect you to be a reliable, hard-working person.
    If things don't go well because for example your roommates are
    noisy, you don't have air conditioning, or your internet connection
    is unreliable, and you can't fix it, tell us so we can terminate
    your GSoC.

Since 2014, our official policy is to ignore “theoretical” applications
— to be eligible, you **must** have gotten involved early-on and made at
least one contribution prior to applying. Read more about our stance in
this blog post: “[Applying for a GSoC project is all about early
involvement and commitment]”. If you are interested, the best thing you
can do is to come to our [IRC channel] now, to make sure we have enough
time to get to know you.

  [Google “Summer of Code” program]: https://developers.google.com/open-source/gsoc/
  [contributing page]: http://www.pitivi.org/?go=contributing
  [Applying for a GSoC project is all about early involvement and
  commitment]: http://jeff.ecchi.ca/blog/2014/02/15/applying-for-a-gsoc-project-is-all-about-early-involvement-and-commitment/
  [IRC channel]: http://www.pitivi.org/?go=contact

# Who we are looking for

We are looking for smart and talented developers interested in
multimedia and video editing.

You need to be highly **communicative**. Stuck on a problem? We need to
know. Achieved a milestone or solved a really nasty problem? The *entire
world* needs to know. We require to see you in our IRC channel, that's
where you can meet the team, where you follow what's going on and that's
where we'll communicate. Email is not sufficient. If you're new to IRC,
check out [IRCCloud] and [riot.im]

You must have experience with Python or C, depending on your project.
Knowledge of [Git], GStreamer and [related technologies] is a plus.
Familiarity with [Test-Driven Development] is a plus.

  [riot.im]: https://riot.im/app
  [IRCCloud]: https://www.irccloud.com/pricing
  [Git]: Git.md
  [related technologies]: Architecture.md
  [Test-Driven Development]: http://en.wikipedia.org/wiki/Test-driven_development

# What we offer

You have a fantastic learning opportunity to play with [technologies]
such as GStreamer, GTK+, Python, etc. We'll direct you to make great use
of the tight-knit GStreamer and GTK communities so you have high-quality
feedback throughout your project.

You can improve the lives of thousands of users by working on a tangible
and fun project.

You have the opportunity to present your accomplishments to others at
[GUADEC] where you can also meet with us. In past years the travel
expenses for GSoC students have been covered by GNOME.

See more [reasons for contributing].

  [technologies]: Architecture.md
  [GUADEC]: http://en.wikipedia.org/wiki/GNOME_Users_And_Developers_European_Conference
  [reasons for contributing]: http://www.pitivi.org/?go=contributing

# How to apply and get started

![](images/Challenge-Accepted.png "Challenge-Accepted.png")

You don't have to be a veteran hacker but it is important that you prove
to us — and to yourself — that you *know* what you're getting into and
that you can handle it. You need to demonstrate that you have sufficient
technical skills, motivation, and have some familiarity with the
application and its source code. This also ensures that you get to know
members of the community and have sufficient time and information to
properly plan your project.

See also [our official stance] (as of 2014) on the matter and Lionel
Dricot's blog post on “[Being selected as a Summer of Code student]”.

Therefore, you should proceed like this:

1.  Come to our [IRC channel] and stick around.
2.  Setup your [development environment] and run the [Test suite].
    Explore the development version of Pitivi, what works well and what
    doesn't, etc. See how you like it.
3.  To get a better idea of how comfortable you are with the code and
    community, make some small contributions to the code. Pick some
    small [bugs] to fix or pick a “small” task in the [Pitivi tasks for
    newcomers] list and have a go at it. Keep us in the loop. The
    earlier you start contributing, the more likely you know what you're
    getting into. Don't start contributing in March/April: we highly
    encourage you to start getting involved in January/February, or even
    earlier, to have time to try another team if we are not a good fit
    for you.
4.  Find a cool feature you need in Pitivi and tell us. Start making a
    design doc on how you plan to implement it.
5.  Fill out the [application] and apply officially to the Google's
    Summer of Code [website] under both the GNOME or GStreamer mentoring
    organizations, depending on your project.

  [our official stance]: http://jeff.ecchi.ca/blog/2014/02/15/applying-for-a-gsoc-project-is-all-about-early-involvement-and-commitment/
  [Being selected as a Summer of Code student]: http://ploum.net/be-selected-student-for-soc/
  [IRC channel]: http://www.pitivi.org/?go=contact
  [development environment]: https://github.com/pitivi/pitivi/blob/master/docs/HACKING.md
  [Test suite]: Testing.md
  [bugs]: https://phabricator.freedesktop.org/project/view/15/
  [Pitivi tasks for newcomers]: https://phabricator.freedesktop.org/tag/pitivi_tasks_for_newcomers/
  [application]: https://wiki.gnome.org/Outreach/SummerOfCode/Students#Fill_out_the_Application
  [website]: https://developers.google.com/open-source/gsoc/

# Project ideas
Pitivi is a very modular video editor, whose [architecture] heavily
depends on technologies like [GES] and GStreamer. The scope of your GSoC
project will probably cover only Pitivi, but it could very well span
multiple codebases:

-   [Pitivi], which is the user interface. Written in Python. *For those
    who love design and graphical user interaction.*
-   [GES], the high-level video editing GStreamer library that powers
    Pitivi and other applications. Written in C. *For those who wish to
    improve an easy to use, powerful and flexible library for
    audio/video editing.*
-   GStreamer, for low-level work, such as improving filters/effects,
    codecs, hardware decoding/encoding acceleration, analysis, etc.
    Written in C. *For those seeking a challenging audio and video
    experience where optimization is key.*

We'd love to see GSoC proposals originating from an itch you need to
scratch. You are welcome to ask around and **bring your own ideas**. If
you're not sure where you can be most useful, have a look at the “large”
tasks in the [Pitivi tasks for newcomers] list. They are fun cool
features very suitable for a GSoC project. See the [roadmap] for our
overall vision for the project. Deadlines for applying are approaching
fast, hurry up!

See [Past GSoCs] for details on what the previous GSoC students did.

  [architecture]: Architecture.md
  [GES]: GES.md
  [Pitivi]: http://www.pitivi.org/manual/mainwindow.html
  [Pitivi tasks for newcomers]: https://phabricator.freedesktop.org/tag/pitivi_tasks_for_newcomers/
  [roadmap]: Roadmap.md
  [Past GSoCs]: Past_GSoCs.md
