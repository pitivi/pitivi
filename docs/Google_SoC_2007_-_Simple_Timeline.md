# 2007 ― Simple Timeline

This branch of PiTiVi has been superceded by PiTiVi 0.11, which
incorporates many of these changes. This page is left as a record of
my participation in Summer of Code.

# Main

Our goal for this summer is to finish the Simple Timeline. I started by
adding some of the features presented in the [Simple UI
Mockups](design/2007_design/2007_Simple_UI_Mockups.md) illustrations. I am now turning
my attention to file load and save support, even though not all of the
simple UI has been implemented. File Load/Save is now high priority. In
addition, I have been creating [Design Docs](design.md) for
myself, and for other people who wish to contribute.

During the development of PiTiVi this summer, we have discovered a
number of gstreamer and gnonlin bugs. This means that <b>the pitivi-soc
branch depends on GStreamer &gt;= 10.9 </b>. If you are interested in
trying out PiTiVi, or hacking it, you will need to follow the directions
on the Gstreamer Setup Page to configure your environment.

## UI Enhancement Screenshots

Image:SimpleSourceWidget.png|improved source widget
Image:SimpleEditingWidget.png|new editing widget
Image:Editing\_widget\_in\_action.png|functional editing widget in
action Image:Editing widget in action 08-07-07.png|editing slider now
features horizontal bar indicating start and stop positions Image:Simple
timeline 08-07-07.png|timeline has been cosmetically tweaked
Image:Source\_navigation\_widget.png|mockup of editing slider

## Subversion branch

All work is first being done in the PITIVI\_SOC\_2007 branch before
being merged in trunk.

WebSVN : <http://svn.gnome.org/viewcvs/pitivi/branches/PITIVI_SOC_2007/>

Anonymous checkout :

` svn co `[`svn://svn.gnome.org/svn/pitivi/branches/PITIVI_SOC_2007/`](svn://svn.gnome.org/svn/pitivi/branches/PITIVI_SOC_2007/)` pitivi-soc`

## Recent Changes

### Aug 21, 2007

The coding period for SoC has ended. I did do a rather large commit, but
this has left the SoC branch in a somewhat messy state, as most of the
code is completely untested. I would like to continue working on this,
but for the next two days I will be occupied with school and family
issues. Thursday and friday are out, because my car needs attention
(water pump leak), and instruction begins on the 27th. So it's not
looking good for the short term.

On the whole, I feel pleased with my earlier work, but I am a bit
disappointed at the lack of progress during the later half of the
summer. Stay tuned for future developments. I think this was a great
experience, and I feel that I have learned a great deal from
participating in Summer of Code.

### Aug 15, 2007

I tried to make a go at the UI, but it got hairy really fast. I was
afraid to commit unfinished code, but I ended up waiting too long. I
changed a bunch of internal stuff, so I gave up on trying to commit
that. I'm working now on the backend, after having had a chance to
discuss the architecture a bit with Edward. In between, I had to study
for a final exam for a class in which I took an incomplete.

### Aug 4, 2007

Finished writing the core application logic for file load and save, as
well as all the test cases. I spent most of the making the application
logic actually <i>pass</i> the test cases =P. I'm debating between
shifting focus towards the UI or towards file parsing/output. File
output would be the easiest to implement, UI the next easiest, with file
parsing being the most difficult. But, I could start working on the UI
right away, whereas I will need to converse with Edward before beginning
work on the file format itself.

Edward, if you're able to read this, let me know what you think.

### Aug 1, 2007

I've gotten a bit bogged down in design work, and I've decided to just
start coding what I have. I have a feeling the rest will become clear
once I start making progress. I'm hoping to have the application logic
finished by the end of the week, and the UI going by the start of next
week. This has taken far too long, and I really need to get cracking at
implementing the file format (which is the hard/interesting part).

### July 26, 2007

I've been working on the design documents, and creating file/load save
test cases. My goal is to have the application logic for file load/save
committed to the SoC branch some time next week. I've been focusing
mostly on design at the moment. Today I spent some time splitting up the
design docs page into separate elements. I also am having to compile
GStreamer from CVS to catch up to the latest gstreamer bug fixes.

### July 24, 2007

Began thinking about the issue of file load/save support. I started by
examining the patch supplied by Richard Boulton almost a year ago, which
implemented the complete application logic for handling saving and
loading of projects. The patch does not, however, implement reading and
writing of the project file itself. The patch no longer cleanly applies,
so I did my best to apply it manually. I then created a new patch, which
I've uploaded to bugzilla. It's still only a partial patch, and it
breaks parts of the UI. My goal for the next day or so is to extract the
best parts of his design, and then implement my own solution. I'll
probably use some of his code in the system, but will definitely be
re-implementing the UI.

Part of the work on implementing file load/save support is creating a
design document. Edward suggested that I put all my [Design
Docs](design.md) up on the Wiki.

### July 22, 2007

Posted a mockup of the editing slider widget.

#### Comments here

### July 20, 2007

I've been at GUADEC all week, and I've used some of that time to hack on
PiTiVi. With edward's help, the volume slider on the source widget
actually changes the volume for the clip. Today I committed a new
revision to the SoC branch which adds a cancel button to the editing
widget. This required some internal changes to the editing widget, but
nothing too serious. Meanwhile, Edward is working on making the advanced
UI more functional. He's got partial support for moving clips in the
advanced timeline, but has run afoul of some gstreamer bugs.

I'm considering replacing the slider with a gtk.ScaleButton, since that
would allow the source widget to shrink down even more while allowing
the slider to grow to a more manageable size. I'm also thinking about a
custom widget for seeking that would eventually replace the simple
gtk.HScales we've been using. It feature a much slimmer cursor, would
support zooming, display a timescale, provide fancy navigation input
such as jog/shuttle, and would directly show the media start/stop
points. I'm currently trying to design things on paper, but maybe i'll
post a vector drawing to the wiki for comments.

Project load/save support is in the early stages of design now. We are
hoping to have this finished by the end of the summer, but it is a major
chunk of work. Several contributors have begun submitting patches to
help make this task easier. Edward is also beginning to explain to me
the intricacies of the effects/transition system in pitivi.

### July 08, 2007

Today I split out the editing slider code into a new class / file. While
I was at it I created a helper widget to display the start and end
points of each clip above the slider. I also made it so that the start
and stop trim buttons gray out when you drag the slider past the start
or stop of the clip. This prevents you from setting the end before the
start, or vice versa. Meanwhile, Edward Hervey has tracked down the
source of a bug that caused PiTiVi to crash when dragging new sources
into the timeline.

### July 07, 2007

Today I made great progress. I did a number of cosmetic tweaks to get
the size of the SimpleSourceWidgets down (which in turn shrinks the
timeline itself). I also changed the way the those widgets are packed so
that resizing them does more to increase the size of the thumbnail
image. I also made it so that the thumbnail in each SimpleSourceWidget
is updated when it's source's start point changes.

### July 06, 2007

I've decided to start leaving messages on a weekly basis, so that
there's a visible history of progress. Finally fixed thumbnail aspect
ratio scaling issues, as well as tracking down a bug that was preventing
them from updating.

### May/June 2007

The two components I have been focusing on are the SimpleSourceWidget
and the SimpleEditingWidget. The SimpleSourceWidget and SimpleEditing
widgets are almost fully functional. I am now working on cleaning up
certain aspects of the editing widget, and perfecting the slider code.

In the course of creating a generic way of extracting thumbnails, we
have uncoverd a host of gstreamer bugs which make editing impractical
for files supported by certain gstreamer plugins, an area which is
outside of my domain.
