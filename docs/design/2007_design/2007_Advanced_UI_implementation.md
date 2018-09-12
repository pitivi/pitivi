# Implementation

## Design Overview

![Inheritance Diagram](images/Advanced_inheritance.png)

This document **does not reflect the existing codebase**, but rather a
road map for future development. Some of this design has been
implemented in the 2008\_SOC\_BLEWIS branch, and these changes will be
gradually merged into trunk.

The goal of the design is to build a UI which supports the following
features:

-   multi-track editing
-   multi-layer editing\*
-   multiple selection
-   noun-verb interaction
-   direct manipulation
-   edge snapping
-   multiple-level undo/redo support

(\*) It is important to distinguish between a **track**, and a **layer**
in application terminology. Existing video editors use the term
**track** to refer to a UI object which represents a stream of video
with a sequence of sources. PiTiVi refers to this as a **composition**.
The term **track** in PiTiVi means a separate channel of output: for
example, audio and video are in separate tracks. The Timeline class
contains one TimelineComposition for each of its output tracks.
Currently these are hard-coded to audiocomp and videocomp, but in the
future multiple audio and video output tracks will be supported. This
will enable things like multi-language sound tracks, or multi-angle
video sequences.

This is distinguished from the concept of a **layer** which is directly
related to the notion of **compositing**. Within a track, sources have a
property called **priority** which determines what will appear when the
play-head reaches a given position in the timeline. By default, the
source with the lowest numerical priority is displayed. Adding effects
to a composition enables multiple sources to be composited together.
Priority is used to determine which sources will be used by an effect as
input.

## The MVC/Observer Design Pattern

PiTiVi relies heavily on MVC and Observer design patterns to decouple
the core of the application from the user interface. Core objects emit
signals which prompt changes in the UI. UI elements wrap core objects to
manipulate data, which in turn emit signals. The observer pattern allows
the user interface to listen for changes in the core without coupling
the core to the UI.

We use pygobject to provide support for the observer pattern in the
core. The user interface depends on pygtk and pygoocanvas, both of which
are based on GObject.

## Files

The advanced UI is implemented in several files in the pitivi/ui
directory in the source tree:

-   util.py
-   complexinterface.py
-   complextimeline.py
-   ruler.py

## Interfaces

-   Selectable
-   Draggable
-   SelectableDraggable
-   Magnetic

## Classes

-   History
-   ComplexTimelineObject
    -   ComplexTimelineFile
-   Content
    -   AudioContent
    -   VideoContent
-   Handle
-   EditMarker
-   ComplexTrack
-   ComplexTimelineCanvas
-   ComplexTimelineWidget

# Utilities

The util.py file provides a number of convenience functions for working
with goocanvas, including an easy way of creating canvas item objects,
as well as generic support for drag-and-drop and selections. This file
also provides the SmartGroup class, which extends goocanvas.Group with
automatic recalculation of size and position.

The code in this file is intended to be as reusable and generic as
possible. Its goal is to overcome some limitations of goocanvas which
make programming dynamic, reactive interfaces more challenging than
necessary. Code in this file is also used by the simple timeline.

## SmartGroup

SmartGroup is also used to implement HList and VList, which are
container classes that enforce positioning constraints on their
children. They work more-or-less like HBox and VBox in gtk. What you
need to know about smart group is:

-   The smart group keeps track of its own position: Setting the x or y
    properties on a smartgroup will cause all the group's children to
    move accordingly.
-   The smart group keeps track of its size: If any of the group's
    children change size or position, the group recomputes its width and
    height properties.

This is currently accomplished by using property notification signals.
SmartGroup overrides the add\_child method and connects to the
notify::x, notify::y, notify::width, and notify::height signals for each
of its children.

## Convenience Functions

These functions all take an item as input and return the appropriate
property. They make expressions involving these properties more readable
and more compact.

-   width(item)
-   height(item)
-   left(item)
-   right(item)
-   top(item)
-   bottom(item)
-   center(item)

This function handles getting coordinates from an event object and
converting them into the canvas space:

-   event\_coords(canvas, event)

These functions manipulate object size and position

-   pos(item)
-   set\_pos(item, pos), where pos is a tuple (x, y)
-   size(item)
-   set\_size(item, size), where size is a tuple (width, height)

These functions activate dragging and selection management:

-   manage\_selection(canvas, changed\_cb)
-   make\_selectable(canvas, item)
-   make\_dragable(canvas, item, start\_cb, transform, end\_cb,
    moved\_cb)

## SmartCanvas

This class is yet to be implemented. Intended to provide internal
support for some of the convenience functions described above:

### Methods

-   manage\_selection(), activates internal selection management,
    deprecates top-level function with same name
-   make\_selectable(), activates selection management on a given
    object, deprecates top-level function with same name.
-   make\_selection\_dragable(),

# Interfaces

All the interfaces used in the complex UI are kept in
complexinterface.py.

## Zoomable

This interface allows for sharing a single gtk.Adjustment among multiple
client objects. When the adjustment's value changes, the the Zoomable
object's zoomratio property is set, and its zoomChanged() method called.

Implementing classes must define a zoomChanged() method. This method
should perform any drawing or size adjustments.

Zoomable containers have the option of defining a
setChildZoomAdjustment() method, which they can use to set the zoom
adjustment on all of their children. In general, however, a container
should set the child's zoom adjustment whenever the child is added to
the container.

## Draggable

This interface encapsulates handling the mouse events required to make
an object dragable with the mouse. Objects can simply extending from
this interface to get basic drag-and-drop functionality. If more complex
drag-and-drop behavior is required, this interface provides some hook
functions which can be overridden by implementing classes.

### Methods

-   dragStart -- a hook which is called to notify the object that
    dragging is about to begin
-   dragEnd -- a hook which is called to notify the object that dragging
    has ended
-   dragMotion -- a hook which is called to notify the object that its
    position should be updated.

## Selectable

This encapsulates the notion of an object which may be included in the
current UI selection. This is kept strictly separate from Dragable, as
there is a use case for selectable objects which cannot be moved by the
user, as well as a use case for dragable objects which should never
become part of the current selection. Objects are selected with
Select(), and deselected with Deselect(). Objects are notified of their
selection status through the selected() and deselected() method calls.

Being part of the selection implies that the object represents data that
can be manipulated. To this end, all Selectable objects provide a
core\_object property. The list of all selected core objects can be
obtained with the getSelectedCoreObjects class method.

The current selection is a set of Selectable objects, and any command
which affects the current selection operates on these objects (or the
core objects which they represent). To facilitate this, the interface
provides class methods to iterate over all instances of selectable
objects in various ways.

### Properties

-   core\_object

### Methods

-   (absract) selected -- notifies the object it has been selected
-   (absract) deselected -- notifies the object it has been deselected
-   select -- places this item in the current selection
-   deselect -- removes this item from the current selection
-   (abstract) delete -- removes the core object from application data
    structures
-   (abstract) copy -- places a representation of the core object into
    the application clipboard
-   @classmethod getSelected -- returns a list of all selected
    selectable objects
-   @classmethod getSelectedCoreObjects -- returns the pitivi core
    object for every object that has been selected
-   @classmethod deleteSelected -- deletes all selected objects

## SelectableDraggable(Selectable, Dragable)

This is the explicit merging of the Selectable/Dragable interfaces.
Objects which are both selectable and dragable should implement this
interface, rather than the two ancestors independently. The reason is
that this interface provides support for manipulating selections of
movable items: i.e., if the user has multiple items selected and moves
one of them, all the other items should move in unison.

### Methods

-   dragStart -- relays dragStart message to all other selected
    SelectableDraggable objects
-   dragEnd -- relays dragEnd message to all other selected
    SelectableDraggable objects
-   dragMove -- relays dragmove message to all other selected
    SelectableDraggable objects
-   (abstract) setPos -- implemented by derived objects, sets the
    position of the core object represented by this object
-   @classmethod selectedDragStart
-   @classmethod selectedDragEnd
-   @classmethod selectedDragMove

## Magnetic

Encapsulates the concept of an important point on the timeline to which
timestamps should be snapped during mouse operations. The class keeps
track of all its instances in a sorted list, and uses binary search to
implement the class method snapTime(), and snapObj, which actually
implement magnetic edge snapping.

### Properties

-   flags -- when the control point is magnetic to the cursor, values
    are RESIZE, MOVE, RAZOR, COMMAND, ALL

The flags property is a bit-field defining when a magnetic point will be
used.

-   RESIZE -- control point is magnetic during resize operations
-   MOVE -- control point is magnetic during drag operations
-   RAZOR -- control point is magnetic to razor tool, or during trimming
-   COMMAND -- control point can be the input to a command which
    operates on current selection
-   ALL -- equal to RESIZE | MOVE | RAZOR | COMMAND

### Methods

-   setTime -- update this magnet's time value
-   @classmethod snapTime(time, flags) -- snap the input time to the
    nearest magnet according to flags
-   @classmethod snapObj(start, duration, flags) -- snap start or end
    time to the nearest magnet, according to flags)

# Classes

These classes implement the majority of the pitivi's advanced (or
complex) user interface, and can be found in complextimeline.py.

## History

This class manages the command history for the user interface. It
maintains a stack of actions and their inverses.

### Properites

-   undo\_actions -- stack of (function, data, inverse\_function,
    inverse\_data) tuples
-   redo\_actions -- stack of (function, data, inverse\_function,
    inverse\_data) tuples

### Methods

-   undoLast -- pop the top of the undo stack, push onto the redo stack
    and execute the inverse operation
-   redoLast -- pop the redo stack, push the undo stack, and execute the
    non-inverse operation
-   pushAction -- add a new tuple to the top of the history stack.
-   peek -- return the top of the undo stack
-   poke -- update the top of the undo stack in place
-   pop -- pop from the undo stack without performing any action or
    pushing the redo stack (for example, to clear a canceled operation
    from the undo stack)
-   clear -- clears the undo/redo stack

## ComplexTimelineWidget(gtk.HBox)

This widget contains the timeline canvas and the ruler. It is also
responsible for showing and hiding toolbar actions associated with the
complex timeline.

## ComplexTimelineCanvas(goocanvas.Canvas, Zoomable)

(currently called ComplexLayers, will be renamed before the next
release)

This class *is* the timeline. The canvas creates one ComplexTrack item
for ComplexTrack item for each top-level composition within a timeline.
PiTiVi core doesn't yet support multi-track editing, but this support is
planned. ComplexTracks should be able to handle creating/destroying
tracks dynamically.

In addition to the timeline itself, this widget keeps track of a number
of important details about the timeline: current edit points, playhead
position, current tool (only razor or pointer, at present), and the
current selection.

Mouse and pointer events received by this widget are routed to the
selection or the current active tool. Keyboard events are handled here
directly depending on the current active tool.

### The Selection

The primary goal of the editing canvas is to allow the user to modify
the selection as they see fit, and then apply changes to the selected
object. The selection consists of a set of objects implementing the
Selectable interface.

The canvas keeps track of whether or not objects are selected. Objects
in the timeline always pass pointer events up to their parent group. If
an event reaches the root item group, a test is performed to determine
if the object should be added to the current selection. If this test
passes, the objects select() method is called.

The selection also identifies a primary object: this is the object with
which the user is directly interacting with, i.e. the source of the
pointer event. Certain operations make the most sense in the context of
a single active object. For example, if the user selects several sources
and then drags one of them, this object will be used as a reference
point for edge snapping.

Finally, the user is provided with a few tool-bar commands which
manipulate the selection explicitly.

### Selection Management Methods

-   deleteSelected()
-   copySelected()
-   moveSelected()
-   clearSelection()
-   selectBeforeCurrent()
-   selectAfterCurrent()

### Selection Manipulation Methods

-   copySelected()
-   deleteSelected()
-   moveSelected()
-   linkSelected()
-   unlinkSelected()
-   collapseSelected()

Commands which operate on the selection are sent to this widget, which
iterates over the selection and performs operations on every element
contained therein.

### Other

-   activateRazor()
-   deactivateRazor()

## ComplexTrack(SmartGroup, Zoomable)

This class is a container for pitivi tracks.

-   Time is represented by horizontal position, in proportion to the
    current zoom ratio
-   Priority is represented by vertical position, with the top of the
    canvas representing the highest priority.

This class encapsulates an internal view of a TimelineComposition
object. Each ComplexTrack manages exactly one TimelineComposition, and
connects to the following signals:

-   source-added
-   source-removed
-   effect-added
-   effect-removed
-   transition-added
-   transition-removed

These signals are all sent to the same pair of signal handlers,
\_objectAdded, \_objectRemoved, respectively. This function takes an
additional parameter, klass, which is a reference to the sublclass of
ComplexTimelineObject which should be instantiated.

## Handle(Rect, Dragable, Magnetic)

This object is used by ComplexTimelineObject to represent the in/out
edit points of the object. A handle is a goocanvas.Rect item which
implements the Dragable, and Magnetic interfaces. It is not directly
selectable. A handle object does not directly set its position, but
instead hands off mouse events to a callback function, motion\_callback.

### Properties

-   width
-   height
-   active\_color
-   normal\_color
-   motion\_callback
-   cursor

### Methods

-   \_\_init\_\_ -- sets up initial properties, and stores the
    motion\_callback
-   dragBegin -- sets item's color to the active color
-   dragEnd -- sets item to the the normal color, updates magnet
    timestamp
-   dragMotion -- calls the motion\_callback, after performing some
    transformations

## ComplexTimelineObject(Group, Zoomable, SelectableDragable)

Corresponds to pitivi.timeline.objects.TimelineObject. It is a base
class for all objects represented in the ComplexTimeline. When created,
it is given a reference to a TimelineObject, and connects to that
object's `start-duration-changed` signal. When the core object's start
and duration change, the UI object's horizontal position and width are
updated. When the core object's layer position changes, the vertical
position is updated.

Every TimelineObject has a reference to a Content object which is
displayed inside of the TimelineObject. This object may be audio or
video. The Content object can change height or visibility depending on
its state. The parent ComplexTimelineObject must keep track of the
height of its content region and adjust its height accordingly.

ComplexTimelineObjects have drag handles which allow them to be directly
resized. See the Handle class documentation for more information.

### Properties

-   background -- background rectangle
-   coreobject -- the core PiTiVi object which this timelineobject
    represents
-   content -- Content object
-   inpoint -- Handle, representing the in point of the source
-   outpoint -- Handle, representing the out point of the source

### Methods

-   dragMotion -- calls setStartPoint, Magnetic.snapTime(), and
    selectable.dragMotion() to adjust the object's position.
-   (private) startDurationChanged -- handler for the coreobject's
    start-duration-changed signal
-   setStartPoint -- sets coreobject's start property
-   setInPoint -- callback given to inpoint as its motion callback,
    which sets coreobject's start/duration properties
-   setOutPoint -- callback given to outpoint as its motion callback
    which sets coreobject's duration property

## TimelineFileObject(TimelineObject)

This class derives from TimelineObject. It overrides the signal handlers
which set the in/out edit points so that they also set the
media-start/media-duration points.

### Methods

-   setInPoint
-   setOutPoint

## Content(Smartgroup)

Abstract base class for the content region of ComplexTimelineObject. The
content region displays a representation of the core object associated
with the Content object's parent ComplexTimelineObject. Content regions
may be expanded, contracted, or minimized. When expanded, the full
preview image is visible, and the widget is expanded to maximum height
so that the keyframe editor can be used. When contracted, only the
preview image is visible. When minimized, the content region is
completely hidden.

### Properties

-   width
-   height
-   name
-   content\_image
-   keyframes
-   coreobject

### Methods

-   expand()
-   contract()
-   minimize()
-   make\_content\_image -- creates a generic image thumbnail.

## AudioContent(Content)

Overrides make\_content\_image to create an audio waveform from audio
stream data.

### Methods

-   make\_content\_image

## VideoContent(Content)

Overrides make\_content\_image to create a thumbnail sequence.

### Methods

-   make\_content\_image

## Marker(goocanvas.Polygon, SelectableDragable, Magnetic)

Similar to a handle, but can be the selected, which implies that it
contains a reference to a core object.

## ScaleRuler(gtk.Layout, Zoomable)

This file contains the ScaleRuler class, a zoomable timeline ruler. It
should share the same gtk.Adjustment objects for both zooming and
horizontal scrolling.
