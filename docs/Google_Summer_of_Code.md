# Google Summer of Code

The [Google “Summer of Code” program] is available for students only. If
we accept your project proposal, in June-July-August you work on your
project while being paid by Google. Mid-term and end-term we evaluate
your work.

See the section at the top of the [contributing page] for details why
Pitivi is important.

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

Our policy is to ignore “theoretical” applications — to be eligible,
you must show you're capable. Best is to get involved early-on and
make one or more contributions prior to applying. Read more about our stance in
this blog post: “[Applying for a GSoC project is all about early
involvement and commitment]”. If you are interested, the best thing you
can do is to come to our [IRC channel] now, to make sure we have enough
time to get to know you.

  [Google “Summer of Code” program]: https://summerofcode.withgoogle.com/
  [contributing page]: http://www.pitivi.org/?go=contributing
  [Applying for a GSoC project is all about early involvement and
  commitment]: http://jeff.ecchi.ca/blog/2014/02/15/applying-for-a-gsoc-project-is-all-about-early-involvement-and-commitment/
  [IRC channel]: http://www.pitivi.org/?go=contact

## Who we are looking for

We are looking for smart and talented developers interested in
multimedia and video editing.

You need to be highly **communicative**. Stuck on a problem? We need to
know. Achieved a milestone or solved a really nasty problem? The *entire
world* needs to know. We require to see you in our IRC channel, that's
where you can meet the team, where you follow what's going on and that's
where we'll communicate. Email is not sufficient. If you're new to IRC,
check out [IRCCloud] and [riot.im].

You must have experience with Python or C, depending on your project.
Knowledge of [Git], GStreamer and [related technologies] is a plus.
Familiarity with [Test-Driven Development] is a plus.

  [riot.im]: https://riot.im/app
  [IRCCloud]: https://www.irccloud.com
  [Git]: Git.md
  [related technologies]: Architecture.md
  [Test-Driven Development]: http://en.wikipedia.org/wiki/Test-driven_development

## What we offer

You can improve the lives of thousands of users by working on a tangible
and fun project.

On the technical side, it might interest you that we use GES/GStreamer
as backend, GTK for the UI, the Meson build system, and Flatpak to
distribute our own builds to users. You have a fantastic learning
opportunity to play with these [technologies]. We'll direct you to make
great use of the tight-knit GStreamer and GTK communities so you have
high-quality feedback throughout your project.

Flatpak additionally allows us to have a [development environment] with
all the dependencies in a sandbox, which is very easy to set up.
This means you won't have to mess your system to be able to build
the latest GStreamer. Since all of us will be using the same
dependencies, there will be no friction due to the complex dependencies.

  [development environment]: HACKING.md
  [technologies]: Architecture.md

## How to apply and get started

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
    [small bug to fix] and have a go at it. Keep us in the loop. The
    earlier you start contributing, the more likely you know what you're
    getting into. Don't start contributing in March/April: we highly
    encourage you to start getting involved in January/February, or even
    earlier, to have time to try another team if we are not a good fit
    for you.
4.  Find a cool feature you need in Pitivi and tell us. Start making a
    design doc on how you plan to implement it. Feel free to pick
    a project from the list of [GSoC project ideas] we thought about.
5.  Fill out the [application] and apply officially to the Google's
    Summer of Code [website].

  [our official stance]: http://jeff.ecchi.ca/blog/2014/02/15/applying-for-a-gsoc-project-is-all-about-early-involvement-and-commitment/
  [Being selected as a Summer of Code student]: http://ploum.net/be-selected-student-for-soc/
  [IRC channel]: http://www.pitivi.org/?go=contact
  [development environment]: HACKING.md
  [Test suite]: Testing.md
  [small bug to fix]: https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=4.+Newcomers
  [application]: https://wiki.gnome.org/Outreach/SummerOfCode/Students#Fill_out_the_Application
  [website]: https://summerofcode.withgoogle.com/

## Project ideas

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
you're not sure where you can be most useful, have a look at our list
of [GSoC project ideas]. Deadlines for applying are approaching fast,
hurry up!

See [Past GSoCs] for details on what the previous GSoC students did.

  [architecture]: Architecture.md
  [GES]: GES.md
  [Pitivi]: http://www.pitivi.org/manual/mainwindow.html
  [GSoC project ideas]: GSoC_Ideas.md
  [Past GSoCs]: Past_GSoCs.md
