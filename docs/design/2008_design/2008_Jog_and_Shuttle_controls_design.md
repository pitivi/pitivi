## 2008 Jog and Shuttle controls

This is just a proposal for bringing frame seeking to the user interface
in advanced mode. If you want to follow the development progress read
[2008 Jog and Shuttle controls code
experiment](design/2008_design/2008_Jog_and_Shuttle_controls_code_experiment.md)

## Screen Mockups

### With standard gtk controls

![](Frame_player.png "Frame_player.png")

### With a custom jog control

![](Frame_player_jog.png "Frame_player_jog.png")

Glade source file is available upon request.

## Implementation

### Controls

-   current: a linkbutton control with which a random position can be
    manually entered
-   zoom: this is of lower priority which allows to set the zooming
    level of the image (either fit or a percentage)
-   total: total time of the clip
-   jog: with the left mouse down you can jump to previous frames by
    moving left or to next frames by moving right
-   shuttle: with the left mouse down you can rewind or forward with
    variable speeds

The current and total controls should be able to display in units of
frames or time.

### Steps

1.  current & total
2.  jog (not custom control)
3.  shuttle
4.  refactor so that it can work as a widget independently of pitivi
    with plain pipelines
5.  zoom
6.  jog (as custom control)

## About myself

I am willing to work on this but will need mentoring. My background:

-   graduated as architect and visual/video artist (I care about
    aesthetics and UI design)
-   experience of python (no C or C++)
-   plenty of gui experience with wxpython
-   author of SPE (Python IDE - <http://pythonide.stani.be>), Phatch
    (Photo Batch Processor - <http://photobatch.stani.be>) & sdxf.
-   new to pygtk and gstreamer -&gt; mentoring needed
-   I don't have a lot of time so I prefer to focus on something I need
    myself and I can finish
-   working on ubuntu
