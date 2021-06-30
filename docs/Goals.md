# Goals

*This page is about general principles that govern our project. To learn
about our global mission and how we plan to achieve it, read the
[frontpage](https://www.pitivi.org/) of the Pitivi website. You can also take
a look at the [tour](https://www.pitivi.org/tour/) page to find out about
cool features.*

[The people](The_people.md) of Pitivi have been part of the
GStreamer developer community for many years and make sure any issues
are solved as quickly as possible in the lower levels in order to avoid
any bloated feature at the application level. This is what we call an
“upstream first” approach: we fix things everywhere in the [software
stack](Architecture.md) that we depend on,
instead of accumulating hacks “downstream” (in our app).

Pitivi's [Architecture](Architecture.md) is meant to be
uncompromising:

-   No limits on audio/video formats (input/output sizes, resolutions,
    framerates, codecs and container formats, etc.)
-   No limits on the number of tracks/layers used
-   No limits on the number of combined effects
-   Intuitiveness for newbies and flexibility for power users (see
    below)
-   Clean separation of the backend and UI. The backend is
    [GES](GES.md) and it can be reused by anyone wanting to
    create an application on top of it.
-   etc.

In the long term, we not only aim for Pitivi to be an intuitive video
editor for everyone, but also a powerful tool for professionals and
prosumers. **We are not a Windows Movie Maker clone**.

# “Professional? Isn't this supposed to be easy to use?”

*Yes*, and *yes*.

With Pitivi's growing popularity and simple user interface, there seems
to have been a misunderstanding in its mission: many people think our
main goal is to make an application for “video editing newbies”, or to
make a “clone” of Windows Movie Maker or iMovie. This is not entirely
accurate. We have the following goals:

-   Make a powerful, flexible video editor that can appeal to prosumers
    and professionals
-   Design it extremely well. Make its workflow elegant and intuitive.
    If we succeed, this means we also reach the goal of “making it easy
    for everyone to use it” possible.

The confusion also stems from the common misconception that a powerful
application is mutually incompatible with simplicity and efficiency.
This is partly because there are so many **applications with poorly
designed user interfaces**, and partly because the proprietary software
world has conditioned us into thinking that users must be divided in two
groups: “advanced” and “beginners”. There is no reason a video editor
can't allow complex procedures (and make them as easy as possible!)
while being intuitive to learn and efficient to use for basic
operations, even for amateurs. The reason why there has been such a
distinction in the proprietary software world is artificial **market
segmentation** (further reading:
[1](http://www.joelonsoftware.com/articles/CamelsandRubberDuckies.html)
[2](http://www.codinghorror.com/blog/2009/07/oh-you-wanted-awesome-edition.html)
[3](http://en.wikipedia.org/wiki/Market_segmentation)).

Executive summary:

-   We will make not make a crippled application. In the long run, it
    will be powerful and flexible. Do not think that “because it doesn't
    have lots of features right now” means that it was “designed” that
    way. It's just that we need someone to implement those features
    properly.
-   By designing everything carefully, we strive to keep it simple for
    amateurs as well.

# Yeah, so what's your plan?

You should probably take a look at our [Roadmap](Roadmap.md)
page for a rough plan of the “big picture” features we want to tackle
soon. Roadmaps are just rough estimates and objectives, and since Pitivi
is purely a community-driven project,
[contributing](https://www.pitivi.org/contribute) is the best way to
move what matters to you forward!
