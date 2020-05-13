These QA Scenarios are here to check the expected behaviours of Pitivi
under many situations.

If you see a problem in one of them, [create an issue](Bug_reporting.md)
on GitLab, indicating:

-   which QA Scenario doesn't go through,
-   (optionally) the media files you used,
-   At which step it failed and what happened
-   Which version of Pitivi was used

# Standard QA Scenarios

## Test Import

1.  Start Pitivi
    -   Pitivi should appear
2.  Choose Import from Toolbar
    -   Import Sources Dialog should appear
3.  Select Several Sources and click the “Import Button”
    -   Sources should appear in the sourcelist, or the import warning notification should appear
    -   Icons on files with video data should be shown
4.  Select one clip in the file browser and press the “insert” key
    -   the clip should be inserted at the end of the timeline
5.  Select two files (using shift- or control-click) and press the “insert” key
    -   Both clips are inserted at end of timeline in the order in which they are sorted in the clip browser.
6.  Drag and drop one file from the clip browser to the timeline
    -   An instance of the clip should appear under the cursor as soon as it enters the timeline.
    -   When the button is released, the clip should remain in the timeline at the location it was dropped.
7.  Select several clips in the clip library and drag them to the timeline, but do not release the mouse
    -   The clips should appear in the same order that they are sorted in the timeline under the cursor, as in (5)
8.  Move the pointer outside of the timeline area
    -   Pitivi should remove the clips from the timeline
9.  Move the pointer back inside the timeline area
    -   The clips should re-appear as they were before being removed
10. Release the mouse within the timeline.
    -   Make sure the clips are added at the mouse position.
11. Repeat steps 8 and 9, then release the mouse button outside the timeline
    -   Make sure that no clips are added to the timeline
12. Add several instances of a factory to the timeline
13. Choose Project &gt; “Remove from Project” to remove the clip from the timeline
    -   Make sure every instance of the factory is removed from the timeline.


## Test Preview

1. Start with at least two clips in the timeline.
2. Press 'Play/Pause' button on the viewer.
    - Playback button icon should change from 'Play' to 'Paused'
    - Watch the preview output carefully. There should be no glitche
    - When the playhead crosses clip boundaries, playback should remain smooth
    - When the playhead moves off-screen, the timeline should scroll to center the playhead in the window.
3. Press the 'Play/Pause' button on the viewer again.
    - Playback should immediately cease.
4. Scroll the timeline so that the playhead moves off screen (increase zoom level if necessary)
    -   The timeline scroll position should not jitter, nor snap back to the playhead while the playhead is paused.
5. Repeat (2) - (4), using the keyboard shortcuts
6. Repeat (2) - (4) alternating alternating between using the playback button and the keyboard shortcuts.
    -   In particular, make sure the icon on the play/pause button is updated properly.
7. Click and drag on the volume curve on one of the clips. Move it to just above the bottom of the clip.
8. Play that portion of the clip
    - The volume should sound softer

## Test Audio-Only Clips

-   add at least one video track to timeline
-   add and audio clip to the timeline

## Test Still Images

## Test Ruler

1. Start with at least one clip in the Timeline
2. click on the timeline ruler.
    - The timeline playhead marker should appear under the mouse pointer
    - The viewer should display the timeline at the timestamp represented by the playhead
3. Scrub the mouse over the ruler
    - The playhead should track the mouse position closely
    - The viewer should update continuously while the mouse is moving

## Test Clips

1. Start with at least two clips in the timeline
2. Click and drag the middle of one of the clips.
   -   the trimming handles at the start and end of the clips should highlight as the mouse moves over them
   -   the clip should move smoothly, even when vigorously scrubbed back and forth
   -   the viewer should not update during this operation **this will change when we support live previews**
   -   if thumbnails are enabled, they should appear properly even while the clip is being moved
   -   the clip should snap to the edges of other clips, but not to its original coordinates
   -   check that audio track moves downward so that tracks do not intermingle
   -   when moved beyond the edges of the timeline window, the timeline should scroll
   -   when moving leftward from the right edge (end) of the timeline, there should be no change in scroll position unless the clip moves past the left edge of the timeline.
   -   you should not be able to move the start of the clip past the beginning of the timeline
   -   at all times the shaded portion of the timeline ruler should show the true length of the entire timeline.                                                               |
3. Click and drag the middle of one of the clips in the top-most, moving it up and down.
   -   The layer position of the clip in the track should change
   -   The track containing the clip should expand (pushing all clips lower tracks downward).
   -   The vertical position of layers and controls adjacent to the timeline should update to match                                                                            |
4. Click and drag the left handle of a movie clip (not a still image)
   -   Only the left handle should highlight as the mouse moves over it
   -   The start point of the clip should be trimmed as closely as possible to the mouse position
       -   You should not be able to expand the clip beyond its native duration
       -   You should not be able to move the handle beyond the right edge of the clip
   -   When the start keyframe of an audio clip moves out of view, a “remote handle” should appear matching its vertical position.                                             |
5. Repeat step (4) for the right handle of the same clip
6. Double click on the volume curve on one of the audio clips (preferably one with start &gt; 0)
    A new key frame control point should appear under the mouse location
7. Click and drag the key frame
    The curve should change shape as the key frame moves
8. Position the playhead at the start of this clip and press play
    The volume of the clip should rise and fall with the keyframe curve.
9. Double click the keyframe control point
    The control point should disappear
10. Double click both the start and end points
    These points should never disappear
11. Trim the start of the clip
12. Double-click the volume curve
    - Make sure the new keyrame appears in the correct location, right under the mouse pointer.

## Test Zooming

1. Start with at least one clip in the timeline
2. Zoom in and out using the buttons on the toolbar
   -   Clips should resize appropriately
   -   The zooming should have a smooth feel to it
   -   The scroll position should adjust to keep the playhead as close to the center of the window as possible
   -   If thumbnails and waveforms are enabled, they should update quickly
   -   The ruler's tick marks should adjust to the new zoom ratio
   -   Both the scroll wheel and the tool bar buttons should have the same effect                               |
3. Repeat step (2) moving the cursor over the timeline ruler and turning the mouse scroll wheel back and forth.

## Test Selection

1. Start with at least 3 clips in the Timeline
2. Click a clip to select it
   -   The clip should tint to the selection color to indicate that it is selected.
3. Click another clip
   -   This clip should become selected, and the old clip deselected.
4. Shift+Click on a third clip
   -   Both the second and third clips should now be selected
5. Click-and-drag the middle of one of the selected clips
   -   Both selected clips should move in unison, and their distance from each other should remain unchanged
6. Ctrl+Click on one of the two selected clips
   -   This clip should be deselected, but the other clip should still remain selected
7. Click and Drag on blank canvas
   -   The marquee should appear between the initial mouse-down coordinates and the current location of the cursor
   -   When the mouse is released, all the clips touching the marquee should be selected
   -   Make sure that thumbnails are drawn properly under the marquee (no smearing or other distortions).           |

## Test Roll Editing

1. Start with at least four clips in the timeline, arranged so that there are no gaps between them. These clips will be referred to as A, B, C, D going from left to right.
  -   The end of clip A should be trimmed about 50% from the true end of the clip
  -   Clip B should be longer than clip A
  -   The start of clip B should be about trimmed 25% from the true start of the clip
  -   Clips C, and D and should be left alone                                                                                                                               |                                                                                                                   |
2. While holding shift, click-and-drag the end handle of clip A
   -   The end of clip A should be trimmed in sync with the start of clip B
   -   Make sure the start handle of clip B is clamped between the true start of clip B and the end handle of clip B
   -   Make sure the end handle of clip A is clamped between the true end of clip A and the start of clip A           |
3. Repeat step (2) using the start-handle of clip B.
   -   The behavior should be identical.
4. Arrange the clips so that A and B are on the same layer, while C and D are on different layers, but snapped to the end point of clip A
5. Clear the selection
6. Repeat steps (2) and (3)
   -   Only clips A and B should be affected by the roll edit
7. select clips C and D
8. Repeat steps (2) and (3)
   -   Only clips A, C, and D should be affected by the roll edit

## Test Ripple Editing

1. Start with at least four clips in the timeline, arranged so that there are no gaps between them. These clips will be referred to as A, B, C, D going from left to right.
  -   The end of clip A should be trimmed about 50% from the true end of the clip
  -   Clip B should be longer than clip A
  -   The start of clip B should be about trimmed 25% from the true start of the clip
  -   Clips C, and D and should be left alone                                                                                                                               |                                                                                                                   |
2. While holding control, click-and-drag the end handle of clip A
   -   Clips B-D should move relative to the end handle of clip A
   -   Make sure the end handle of clip A is clamped between the true end of clip A and the start of clip A           |
3. While holding control, click-and-drag the start handle of clip D
   -   Clips A-C should move relative to the start handle of clip D
   -   Make sure the start handle of clip D is clamped between the true start of clip D and the end handle of clip D  |
4. Arrange the clips so that A and B are in the same layer, while C and D are on different layers, but snapped to the end point of clip A
5. Clear the selection
6. Repeat (2) and (3)
    -   Only clips A and B should be affected by the ripple edit
7. Select clips C and D
8. Repeat (2) and (3)
    -   Only clips A, C, and D should be affected by the ripple edit.
9. Arrange clips A, B, C, D so they appear in sequence, left to right

10. Select clips A, B
    -   Make sure clips C and D are deselected
11. Begin dragging clip B
    -   Clips A and B should be moving together
12. While dragging, press and hold the shift key
    -   Clips C, and D should now be moving with clips A and B, preserving the original offsets
13. Move the mouse as far as possible to the left
   -   It should not be possible to set the start time of clips A, B, C or D less to less than 0
   -   While ripple mode is engaged, the relative offsets of clips A, B, C, and D should remain constant              |
14. While continuing to drag, release the shift key
    -   Clips C and D should return to their original positions

## Test Slip-and-Slide Editing

## Test Delete

1. Start with an empty timeline
   -   The delete button should be insensitive
2. Add at least 3 clips to the timeline

3. Select one clip
   -   The delete button should be come sensitive
4. Press Delete
   -   The selected clip should be removed from the timeline
   -   The delete button should become insensitive                 |
5. Select at lest two more clips, and press delete
   -   All the selected clips should be removed from the timeline
   -   The delete button should once again become insensitive      |

## Test Group / Ungroup

## Test Link / Unlink

1. Start with at least 3 clips in the timeline and the selection cleared
    -   The 'Link' command button should be insensitive
    -   The 'Unlink' command button should be insensitive
2. Select two of the clips
    -   The 'Link' command button should become sensitive
    -   The 'Unlink' command button should remain insensitive
3. Press the 'Link' command button
    -   The 'Link' command button should become insensitive.
    -   The 'Unlink' command button should become sensitive.
4. Move both of the linked clips in turn
    -   Moving either clip should cause both linked clips to move in unison
5. Clear the selection
    -   Both 'Link' and 'Unlink' commands should be insensitive.
6. Select one of the linked clips
    -   The 'Unlink' command should be sensitive
8. Add a clip that is not linked to the selection
    -   The 'Link' commands should be sensitive
    -   The 'Unlink' command should be insensitive
9. Press the 'Link' command
    -   The 'Link' command should now be insensitive
10. Click and drag all three linked clips
    -   Dragging any of the linked clips should cause all three to move in unison.
11. Select just one of the linked clips and press 'Unlink'
    -   The Link and Unlink commands should be insensitive
    -   Moving this unlinked clip should not affect either of the two linked clips
    -   Moving either of the linked clips should not affect the unlinked clip
12. Select the two remaining linked clips in the timeline.
    -   The link command should be insensitive
    -   The unlink command should be sensitive
13. Press the 'Unlink' command
    -   The link command should be sensitive
    -   The unlink command should be insensitive
14. Move each of the three clips involved in this test in turn.
    -   All of the clips should now move independently
15. Create two groups of linked clips, call them A and B
16. Select one clip each from A and B
    -   The link command should be sensitive
17. Press the link button
    -   The unlink command should be sensitive
    -   All the clips in A and B should now be part of the same link (clicking and dragging on any of them will move all of them)
19. Delete one of the linked clips
    -   It should be removed from the timeline, but the others should remain
    -   Make sure the other clips are still linked together
    -   Make sure no tracebacks appear on console
20. Select and delete at least two linked clips
21. Select the and delete the remaining linked clips and at least one non-linked clip
    -   Make sure there are no tracebacks

## Test Split

1. Start with at least one clip in thee timeline.
    -   Make sure you are somewhat familiar with it, so that you can spot problems during playback.
2. Click the razor tool
    -   a vertical trimming bar should appear across the timeline at the horizontal mouse position.
3. Click somewhere on the clip
    -   The clip should be divided into two clips at the mouse position
4. Preview the timeline
    -   Playback across the two pieces should be identical with the original clip.
5. Repeat (2) - (4) on each of the half of the clip, leaving a total of four clips
    -   Playback across all four pieces should be identical with the original clip.
6. Click the razor tool
    -   The vertical bar should appear as before
7. Click the razor tool again (to deactivate the razor tool)
    -   The vertical trimming bar should not be visible when the pointer moves over the canvas
8. Click on a clip
    -   The clip should become selected
    -   The clip should not be split
9. Position the playhead somewhere in the middle of a clip
    -   when the mouse moves near the playhead, the trimming bar should snap to the position of the playhead
10. With the trimming bar locked to the playhead, click on the clip.
    -   Make sure that the clip is split exactly at the playhead position (not at the mouse position). Zoom in, if necessary, to verify this.
11. Add several keyframe control points to an audio clip's volume curve, and adjust them so that the curve forms a distinctive pattern.
12. Split this clip
    The keyframe curve should be duplicated exactly. Verify this by extending both halves of the clip to full length and comparing the shape of the curves.

## Test Rendering

## Test File Load and Save

1. Start with several clips in the project and timeline.
    -   Make a few edits
2. Save the project
3. Take a screen-shot of the timeline
4. Reload the project
    -   The project should match the screen-shot exactly
5. Make a small change to the project and then save it. Take a new screenshot
    -   The save-as dialog should not appear.
6. Choose save-as
    -   The save-as dialog should appear -   The current folder of the save-as dialog should be the same folder as the current project
7. Attempt to overwrite the current project
    -   The overwrite confirmation dialog should present itself
8. Choose cancel
    -   Check the modification date/time of the file to make sure it was not overwritten.
9. Try to overwrite the current file, this time choosing “Ok” from the confirmatino dialog
    -   Check that modification date/time of the file to make sure it has been overwritten
10. Continue working with the file
    -   Verify that all of Pitivi other functions still work correctly on the loaded file.

## Test New Project

-   create a complicated project
-   hit new
-   repeat standard test suite
-   test keyboard shortcuts
    -   try to locate a specific frame using only the keyboard

## Test Peak Meter

1. Create and open a new Pitivi project
2. Import 'mp3_sample.mp3' from the 'tests/samples' directory into the media library
3. Insert a 'mp3_sample.mp3' clip from the media library into the timeline
    -   The timeline should only contain the 'mp3_sample.mp3' clip and nothing else
4. Position the seeker at the beginning of the clip on the timeline
5. Press the 'play' button on the viewer controls
    -   The height of the two peak meters should start changing during playback of the clip but should stop once the clip ends
6. Detach the viewer by pressing the 'detach viewer' button on the viewer controls
    -   The peak meters should appear on the right side of the viewer in the external viewer window that pops up
7. Close the external viewer window
    -   The peak meters should appear again in their original location on the right side of the viewer
8. Drag the corner on the viewer container to resize the viewer container to the minimum size
    -   The peak meters should now be sized smaller in response to the smaller viewer container
9. Go to project settings and set the number of audio channels to '8 (7.1)'
    -   There should now be eight peak bars in total displayed next to the viewer

## Test Preferences

# User provided Scenarios

If you want to propose a QA Scenario, Create a page (Called
'`User QA Scenario ##`') and link it here. After reviewing of the steps
and expected behaviours, it will be moved in the above category.
