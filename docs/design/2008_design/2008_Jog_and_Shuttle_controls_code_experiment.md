## Code Experiment

![wxPython prototype seeker with warning about inaccurate codec and some
(green)
markers.](Gst-demo_wx_player-warning.png "wxPython prototype seeker with warning about inaccurate codec and some (green) markers.")

![wxPython prototype seeker with selected interval between in & out
point and visual mouseover effect on
jog.](Gst-demo_wx_player-interval.png "wxPython prototype seeker with selected interval between in & out point and visual mouseover effect on jog.")

![pygtk prototype seeker with hscale for time ruler, shuttle and
jog.](Schermafdruk-gst-seeker-gtk.png "pygtk prototype seeker with hscale for time ruler, shuttle and jog.")

![pygtk prototype seeker with mouseover effect on blend entry and
warning with information. There is 12% difference between seek and query
time in this
video.](Schermafdruk-gst-seeker-gtk-1.png "pygtk prototype seeker with mouseover effect on blend entry and warning with information. There is 12% difference between seek and query time in this video.")

### About

I have been developing pystreamer, a MVC framework for python and
gstreamer. It provides amongst other things a prototype for better frame
seeking with gstreamer, which can be a starting point for pitivi. (It is
not the purpose to put the whole library in pitivi, I will rewrite it
customized for pitivi so it can be applied as a patch.) The prototype is
an attempt to deliver the control that serious video editors want. As it
has just been developed, it might contain some rough edges still. I will
discuss it following its MVC structure:

Model (gstreamer) &lt;-&gt; Controller (pure python) &lt;-&gt; View
(pygtk/wxpython)

### Source Code

You can grab the sources with bazaar:

    bzr branch lp:pystreamer

You need both wxpython (sudo apt-get install python-wxgtk) as pygtk to
explore the demos at the full potential. You can start the demos by:

    ./gst-player-gtk uri
    ./gst-player-wx uri
    ./gst-seeker-wx uri
    ./gst-seeker-gtk uri

uri is for example `file:///home/user/some movie.ogg`

== Model = Player (gstreamer) ==

There are two important aspects of frame seeking:

-   stability: if you seek to a certain position, it should always
    return the same frame
-   precision: if the framerate is n frames as second, seeking should be
    possible to each of the n frames

With the right codecs, gstreamer performs well, but with inaccurate
codecs gstreamer (playbin) will fail on these two issues.

### Frame Stability

#### The Problem

With inaccurate codecs gstreamer behave badly:

1.  seek to position x with gst.SEEK\_FLAG\_ACCURATE
2.  wait until gstreamer has finished seeking
3.  query the position which is returned as y

You would expect that x is equal to y, but gstreamer provides different
values. This makes video editing impossible. (You can see this effect in
Totem by seeking to the end of the movie with an inaccurate codec. You
won't go to the end of the movie, but playback resumes much earlier.)
The most simple solution is to disable frame seeking for inaccurate
codecs or to transcode it to a better codec.

A better solution would be to find a solution which can guarantee
stability for any video codec. After doing some experiments and tests I
found out that:

-   gstreamer always returns the same y for the same x. So it should be
    possible to find a method so that y = f(x).
-   x is always bigger than y, so in order to go the last frame we have
    to seek past the duration of the movie. So the seek timeline is
    longer than the query timeline.

Based on these two observations, we need an algorithm which does the
following:

1.  x is corrected to a later position c
2.  c is seeked
3.  when seeking is finished, query the position which returns the same
    x

#### The Solution

So how can we correct x into z? We need to find the reverse method of f,
let's call it i. This means that x=f(z) and z=i(x). I first thought it
might be just a linear function, but that was not the case. So I
developed a frame correction algorithm which uses linear interpolation
between known values of (x,f(x)) to predict (x,i(x)) or (x, z). You can
find the source code of this in the
pystreamer/player/frameMixin/Mixin.seek method. I've tested it with a
couple of videos with really bad codecs and it always seems to succeed.
As pitivi will be used by all kinds of end users, it is nice that they
don't have to worry about codecs or transcode it first in another codec.

The algorithm knows after two seeks if the codec is accurate or not. If
it is accurate, it will show a success icon and the correction algorithm
disables itself. If it is incorrect, it will calculate and show a
warning sign. By clicking on the warning icon, you can optionally show
the incorrectness. The incorrectness is the average difference between
seeked and queried positions in percent.

Of course it makes seeking a bit more slow for inaccurate codecs, but
the speed remains acceptable. Moreover for video editing, frame
stability/precision is more important than speed. (I guess because
gstreamer is mainly used in media players not editors, speed was
prioritized rather than precision.)

### Frame Precision

Unfortunately AFAIK there is nothing to do about this. The only option
is here transcode the video to a better codec. However I found out that
even with bad codecs it is possible to extract some frames out of a
second instead of all of them. Probably if you work with bad codecs,
that should be ok.

## Controller

The controller mimics the gobject signal system. Both the Player and the
View are based on pystreamer/controller/controller\_object.base which
allows them to emit signals, which are processed by the controller to
link the two. The controller is 100% python and does not depend on gst,
gobject, wxpython, pygtk, ...

## View

### Features

The view supports many features, which might be interesting for pitivi:

-   set in & out point
-   markers
-   shuttle seeking
-   jog seeking
-   buttons for frame navigation (go to or play between in/out point, go
    to previous/next frame, go to previous/next marker)
-   support for light and dark themes
-   special button icons for video editing (svg sources are included)

### Base

The view code which is independent of the toolkit is in pystreamer/view.
It uses some ui\_\* methods which are overridden by specific toolkit
methods. The events are buffered with timer threads so that the UI stays
as responsive as possible. The timer thread will not send seek events
for every user event, but rather keep track and only request a next seek
when the previous one was finished.

### wxPython

The wxPython prototype is quite complete. It provides three custom
controls. The screenshots are working code, not just mock-ups.

#### Blended Text

-   pystreamer/view/uiWx/lib/BlendedTextCtrl.py
-   this is rather semi-custom as it is a native control which has been
    extendend
-   it looks like a StaticTextCtrl (label) but with a mouse over it
    looks like a TextCtrl (entry)
-   this is to avoid clutter and to make the view widget more quiet
-   it is used for the current time, the in and out point.

#### Timeline Ruler

-   pystreamer/view/uiWx/TimeRulerCtrl.py
-   custom control
-   this provides a timeline which shows the duration of the clip
-   it uses native icons for the cursor and for the markers
-   it shows visual feedback of selected interval between in & out point
-   intelligent algorithm for showing time labels

#### Jog Control

-   pystreamer/view/uiWx/lib/JogCtrl.py
-   custom control
-   supports disabled look
-   suppors native colour highlight on mouseover
-   very polished look
-   support for dragging and mousewheel scrolling
-   one pixel = one frame (So dragging the mouse 25 pixels, will seek to
    25 frames away.)
-   different methods for dragging and scrolling to give the best user
    experience

### pyGtk

The pygtk prototype is less complete in custom controls, but is equally
functional.

#### Screenshots

#### Blended Text

-   pystreamer/view/uiGtk/lib/BlendEntry.py
-   this is rather semi-custom as it is a native control which has been
    extendend
-   it looks like a gtk.Label but with a mouse over it looks like a
    gtk.Entry, what it really is
-   see also blended text of wxpython

#### Timeline Ruler

-   pystreamer/view/uiGtk/HScaleRuler.py
-   just a gtk.HScale, so less accurate
-   no in & outpoint interval feedback
-   no markers
-   todo: write a custom control for this

#### Jog Control

-   pystreamer/view/uiGtk/HScaleJog.py
-   just a gtk.HScale
-   modified behaviour to make the hscale behave as a jog (eg remains
    sensitive outside its area)
-   see also jog control of wxpython
-   todo: write a custom control for this

## Known issues

-   with inaccurate codecs: sometimes after a difficult seek, the player
    doesn't start again. A solution could be that seeking pauses the
    video, but it would be nice if it doesn't have to.
-   pygtk: I am wondering how I can determine if a dark or normal theme
    is used. I am only able to retrieve the right background color after
    the window has been realized with window.get\_style().bg But how can
    I know this before?
-   pygtk: How to hide optionally some widgets such as the warning
    information?
-   keyboard bindings need to be added
