# GSoC

The [Google “Summer of Code” program] is available for students and recent
graduates. Check section "7.1. Eligibility" in the [Rules] to see if you are
eligible.

Interested students write and submit a detailed project proposal. If the
proposal is accepted, you work on your project while being paid by Google.
Mid-term and end-term the student and the mentor both submit evaluations to
Google.

See the section at the top of the [contributing page] for details why
Pitivi is important, if you're still not convinced.

While a GSoC with us is one of the most fun and rewarding experiences you can
get, you need to consider it as *professional work*. We expect you to be a
reliable, hard-working person. If things don't go well because for example your
roommates are noisy, you don't have air conditioning, or your internet
connection is unreliable, and you can't fix it, tell us so we can terminate your
internship. **No excuses!**

Our policy is to ignore “theoretical” applications — to be eligible, you must
show you're capable. Best is to get involved early-on and make one or more
contributions prior to applying. We will base ourselves 90% on your involvement
and demonstrated ability to contribute code to Pitivi. The more good-quality
patches you’ve made, the more chances you have.

  [Google “Summer of Code” program]: https://summerofcode.withgoogle.com/
  [Rules]: https://summerofcode.withgoogle.com/rules/
  [contributing page]: https://www.pitivi.org/contribute

## Who we are looking for

We are looking for smart and talented developers interested in
multimedia and video editing.

The time is very short. To make the most out of it, you need to be highly
**communicative**. Particularly when you are stuck on a problem or don't see any
way out. We require to see you in our [chat room], that's where you can meet the
team, where you follow what's going on and that's where we communicate.

You must have experience with Python or C, depending on your project.
Knowledge of [Git], GStreamer and [related technologies] is a plus.
Familiarity with [Test-Driven Development] is a plus.

  [chat room]: https://app.element.io/#/room/#pitivi:matrix.org
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

The dependencies for a video editor are very complex. But thanks to Flatpak we
have a [development environment] with all the dependencies in a sandbox, which
is very easy to set up. This means you won't have to mess your system to be able
to build the latest GStreamer. Since all of us will be using the same
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

Therefore, you should proceed like this:

1.  Come to our [chat room] and stick around.
2.  Setup your [development environment] and run the [Test suite].
    Explore the development version of Pitivi, what works well and what
    doesn't, etc.
3.  To get a better idea of how comfortable you are with the code and
    community, make some small contributions to the code. Pick some
    [small bug to fix] and have a go at it. Keep us in the loop.
    Ideally you start getting involved in January/February, or even
    earlier, to have time to try another team if we are not a good fit.
4.  Find a cool feature you need in Pitivi and tell us. Start making a
    design doc on how you plan to implement it. Feel free to pick
    a project from the list of blessed [GSoC project ideas].
5.  Fill out the [application template] and apply officially to the
    Google's Summer of Code [website].

  [chat room]: https://app.element.io/#/room/#pitivi:matrix.org
  [development environment]: HACKING.md
  [Test suite]: Testing.md
  [small bug to fix]: https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=4.+Newcomers
  [GSoC project ideas]: GSoC_Ideas.md
  [application template]: GSoC_Application.md
  [website]: https://summerofcode.withgoogle.com/
