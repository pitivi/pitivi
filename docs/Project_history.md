# Project history

*[Wikipedia's page] is currently more complete than this page. The goal
here is to explain, eventually, some events and design decisions
(without needing to cite everything). You can see the overall project
activity throughout the years [on Open Hub].*

PiTiVi was started in 2004 as an “end of studies” project by Edward
Hervey and his classmates at the French computer engineering school
Epitech. The “PiTiVi” name came from the combination of “Epitech” and
“TV”.

In 2005-2007, development stalled due to various factors, including the
fact that Edward (the only active PiTiVi developer at that time) was
hired by Fluendo to work on GStreamer. Improving GStreamer was necessary
in order for PiTiVi to be usable, but this meant that PiTiVi did not get
as much direct development attention. During that time, PiTiVi was also
rewritten in Python (it was initially written in C). A more detailed
[explanation] can be read in this blog post by Edward in 2007.

In early 2008, it was decided that PiTiVi had outgrown its original
design specifications and needed to be re-architected. The result was
the [2008 Architectural Redesign]. In late 2008/early 2009, it was
[announced] that Collabora Multimedia would invest developer time in
improving PiTiVi (and hire [additional developers] to accelerate its
pace). The results of Collabora's help on that front were dramatic, as
can be seen in the significant amount of commits in 2009-2010.

In late 2009/early 2010, the [GES] library was created to address many
architectural problems around non-linear editing with GStreamer.
Starting in 2011, efforts on the PiTiVi side have been focused on
porting to GES, cleaning and stabilizing the whole stack (PiTiVi, GES,
GNonLin, GStreamer and related technologies like GObject introspection)
while fixing longstanding bugs and adding new features.

As part of a website and branding facelift in 2013, the traditionally
camel-cased “PiTiVi” name was [changed] to simply “Pitivi”.

To this day, the project lives on, thanks to the continued efforts of
[many dedicated people].

  [Wikipedia's page]: http://en.wikipedia.org/wiki/PiTiVi
  [on Open Hub]: https://www.openhub.net/p/pitivi
  [explanation]: http://blogs.gnome.org/edwardrv/2007/07/01/is-that-a-video-editor/
  [2008 Architectural Redesign]: design/2008_design/2008_Architectural_Redesign.md
  [announced]: http://blogs.gnome.org/uraeus/2008/10/09/supporting-pitivi/
  [additional developers]: http://blogs.gnome.org/uraeus/2008/12/02/new-team-member/
  [GES]: GES.md
  [changed]: https://bugzilla.gnome.org/show_bug.cgi?id=705756
  [many dedicated people]: https://www.openhub.net/p/pitivi/contributors/summary
