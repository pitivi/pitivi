Pitivi is a video editor built upon the GStreamer Editing Services.
It aims to be an intuitive and flexible application
that can appeal to newbies and professionals alike.

This fork aims to make the work in the timeline more easy with the mouse.
The most common command buttons are as far as possible group around the toolbar,
unlike the undo-redo button (in the left up corner) and the toolbar (in the right bottom corner).
 The oficial design can be modified with the menu <Preferences> in a new tab <Editor>
See the "Pitivi_editor.png", "Popup.png" and "Title.png" above.


Features :

DESIGN
- The toolbar can be horizontal
- New buttons in the toolbar for plugins
- The viewer can be centered in the editor gui
- The duration of the timeline is showed under the viewer

FUNCTIONS
- Headplay position with the left mouse button on the ruler
- Fade in or out in three clicks
- Cut the start or the end of a selected clip and move all the next clips in three clcks
- Pop up menu (right click on selected clips) to cut, copy, delete or split
- Pop up menu (right click out of any clip) to paste
- Verify if there is a black in the video (used before a render)
- Alerts with pop up windows and sounds
- Play after a fade a cut, delete to see if the operation is what the user wishes

EXPERIMENTAL
- Titler
     - police font,size or color for each character
     - Background color
     - Center horizontal, vertical or both
     - Fade in, out or both
     - duration
     - experimental credits up or down

For the list of dependencies, look at pitivi/check.py
- "Hard" dependencies are required for Pitivi to function properly
- "Soft" dependencies are recommended for an optimal user experience
  (packagers should add them as recommended or required packages).

Your involvement is what keeps this project moving forward.
See the "contributing" section of http://www.pitivi.org to get started.
