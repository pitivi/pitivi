# 2007 Simple UI Mockups

Here are a collection of UI Mockups for various actions possible with
the Simple UI. Also, you might be interested to see the
[Advanced UI Mockups](design/2007_design/2007_Advanced_UI_Mockups.md).

## Add Media

### Add medias

Medias can be added to the source list by several means:

-   clicking on the 'Add Media' button (shown in mockup below)
-   Dragging from desktop, nautilus, or anything supporting the uri-list
    DND protocol

![](Deroule-addmedia1.png "Deroule-addmedia1.png")

### Medias added

The medias are all shown with an icon and some details in the source
list

![](Deroule-addmedia2.png "Deroule-addmedia2.png")

## Add Scene

### Select scene

The user selects the desired scene from the source list and drags it
onto the timeline

![](Deroule-addscene1.png "Deroule-addscene1.png")

### Scene added

The dropped scene appears on the timeline.

All scenes are colour-coded (random colours) so that you can easily see
in the timeline slider where you sources are. Here, the scene is
coloured in green, and it takes up the whole timeline.

Also notice that the new scene is automatically selected, this is
visible here because it is highlighted in red both in the timeline
slider and in the simple timeline.

![](Deroule-addscene2.png "Deroule-addscene2.png")

### Select another scene

![](Deroule-addscene3.png "Deroule-addscene3.png")

### Other scene added

Just like for the first scene, the new scene is added, with a colour
code, and you can see in the timeline slider that it takes up more room
than the first one since it is longer.

A transition is automatically added between new scenes and existing
ones. This is a sensible default choice, since hard-transitions are
really ugly to look at. The default choice is a fade transition that
takes 1 second.

![](Deroule-addscene4.png "Deroule-addscene4.png")

## Remove Scene

To remove a scene, just press on the cross/delete button at the top
right of the scene.

![](Deroule-removescene1.png "Deroule-removescene1.png")

## Editing Video

These are the various steps for editing a scene, that is : modify the
start/stop duration of a scene.

### Switching to editing mode

To edit a scene, you need to activate the editing mode for that video.
You can do so by clicking on the **Edit** button (highlighted in red in
the mockup below).

![](Deroule-editingvideo1.png "Deroule-editingvideo1.png")

### Editing mode layout

Once in editing mode, the scene takes all the width of the timeline, and
the timeline slider shows which source is selected by highlighting it in
red.

The two viewers at the left and right of the editing view represent the
start and stop position of the scene. The three buttons below each
viewers are:

-   -/+ to move the stop/start position forward or backward by one frame
-   a button to set the current position in the editing slider to the
    start/stop position.

The editing slider represents the whole scene, with the position of the
start/stop points.

![](Deroule-editingvideo2.png "Deroule-editingvideo2.png")

### Moving through the scene

Using the editing slider, it is possible to seek through the scene to
find the adequate start/stop points. Notice that the position is
synchronous with the position in the timeline slider.

![](Deroule-editingvideo3.png "Deroule-editingvideo3.png")

### Setting the start position

Once the user has chosen where the scene should start, you can click on
the 'set start point' button. The editing slider will represent the
start point by graying out everything before that point.

The width of the scene also changes in the timeline slider (FIXME : this
should be visible here, and not in the following mockup).

![](Deroule-editingvideo4.png "Deroule-editingvideo4.png")

### Choosing the stop position

In the same way we did previously, we can seek through the editing
slider to find an adequate stop position.

![](Deroule-editingvideo5.png "Deroule-editingvideo5.png")

### Setting the stop position

Pressing the 'set stop position' (highlighted in red below) will mark
the stop position on the editing slider by graying out everything after
that position.

The duration in the timeline slider will also be changed to show the
modification (FIXME: It is in fact only visible on the following mockup)

![](Deroule-editingvideo6.png "Deroule-editingvideo6.png")

### Leaving the editing mode

To leave the editing mode, simply press the **Done** button (highlited
in red below).

![](Deroule-editingvideo7.png "Deroule-editingvideo7.png")

### Back to timeline view

The scene has shrunk back to the normal size.

![](Deroule-editingvideo8.png "Deroule-editingvideo8.png")

## Add Effect

To apply an effect on a scene, select one from the effect list and drag
it onto a scene.

![](Deroule-addeffect1.png "Deroule-addeffect1.png")

Once added, the effect will appear in the scene's effect slot.

![](Deroule-addeffect2.png "Deroule-addeffect2.png")

## Remove Effect

To remove an effect, click on the remove button in the effect slot
(shown in red below).

![](Deroule-removeeffect1.png "Deroule-removeeffect1.png")

## Add Transition

To add a transition between two scenes, select one from the transitions
list and drag it between two scenes.

![](Deroule-addtransition1.png "Deroule-addtransition1.png")

Once added, it will appear between the two scenes in the timeline.

![](Deroule-addtransition2.png "Deroule-addtransition2.png")

## Change Transition

To modify a transition, select one from the transitions list and drop it
onto an existing transition...

![](Deroule-changetransition1.png "Deroule-changetransition1.png")

... and voila

![](Deroule-changetransition2.png "Deroule-changetransition2.png")

## Remove Transition

To remove an existing transition, click on the cross/delete button at
the top-right of the transition (highlighted in red).

![](Deroule-removetransition1.png "Deroule-removetransition1.png")

![](Deroule-removetransition2.png "Deroule-removetransition2.png")

## Add Starting

![](Deroule-addstarting1.png "fig:Deroule-addstarting1.png")
![](Deroule-addstarting2.png "fig:Deroule-addstarting2.png")
![](Deroule-addstarting3.png "fig:Deroule-addstarting3.png")

## Add Ending

![](Deroule-addending1.png "fig:Deroule-addending1.png")
![](Deroule-addending2.png "fig:Deroule-addending2.png")
![](Deroule-addending3.png "fig:Deroule-addending3.png")
