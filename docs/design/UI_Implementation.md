# UI Implementation

This document **does not reflect the existing codebase**, but rather a
road map for future development, and a general introduction to the
PiTiVi design philosophy.

# Todo

-   document markers
-   document keyframes
-   explain the concept of a receiver.

# Concepts

The goal of the design is to build a UI which supports the following
features:

-   basic editing
-   basic effects
-   compositing
-   multi-track editing
-   multi-layer editing\*
-   multiple selection
-   noun-verb interaction
-   direct manipulation wherever possible
-   leaving behavior up to the core implementation

(\*) It is important to distinguish between a **track**, and a **layer**
in application terminology. Existing video editors use the term
**track** to refer to a UI object which represents a stream of video
with a sequence of sources. PiTiVi refers to this as a **composition**.
The term **track** in PiTiVi means a separate channel of output: for
example, audio and video are in separate tracks.

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

In core, we have our own pure-python implementation of “signals”. The
user interface depends on pygtk and pygoocanvas, both of which are based
on GObject. We use “receivers” to automatically connect appropriate
signal handler methods to objects which emit them.

# UI Framework Design

The majority of the UI uses pygtk. The timeline portion also relies on
goocanvas. This section is about the pygoocanvas portion of the UI.

Objects visible in the timeline will either descend from or mix-in the
View class, available in the view module. Instances of the view class
create an instance of Controller which handles low-level input events
and translates these into higher-level commands which it passes onto the
model.

## Views

View objects appear exclusively in the time-line component of the UI.
Each view represents some object in the current timeline. Views must
update their appearance when the object they represent changes. While in
most cases, this will be accomplished by connecting to model signals, it
is up to the individual view object to do this. No infrastructure is
provided by the View base class. In general, views should multiply from
View and some subclass of goocanvas.Item. The controller code connects
to specific signals, and expects that these signals will have the same
signature as defined in goocanvas.Item.

Views provide a public interface for controlling appearance. There are 3
independent visual states:

-   focused/unfocused
-   active/inactive
-   selected/deselected.

A fourth state, normal, is defined as being simultaneously unfocused,
inactive, and deselected.

## Controllers

View classes have a class attribute, Controller, which can be reference
to BaseController. Views automatically instantiate and connect to an
instance of this class during initialization. Derived Views can redefine
this attribute to any subclass of Controller -- even one defined as an
inner class -- if they wish to override default functionality. This
design is intended to keep a tight integration between a View and its
Controller.

Controllers provide a high-level public interface for handling the
following kinds of interaction

-   key press events
-   mouse clicks
-   mouse drags
-   focus changes
