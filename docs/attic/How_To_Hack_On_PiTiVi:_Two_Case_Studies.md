# How To Hack On PiTiVi: Two Case Studies

You can think of this article as a complement to the more traditional
API reference. Rather than laboriously enumerate class relationships and
API speficications, we will follow the implementation of two features
from the initial concept to the final implementation. Along the way, we
introduce various components of PiTiVi's design on an as-needed basis.
Hopefully, you'll emerge on the other side with a better understanding
of how to modify PiTiVi.

The two features we will be examining are *interpolation curves* and
*still images*. *Interpolation cuves* are an example of an intrusive
change that expands PiTiVi's fundamental capabilities. We will see how
adding capabilities to TrackObjects creates rippling changes in many
other parts of PiTiVi. *Still Image* support is a good example of how to
implement new SourceFactory objects and how to implement new GStreamer
objects in python.

# Interpolators

Many NLEs provide a mechanism for editing time-varying values, such as
audio volume and clip opacity. GStreamer exposes this ability through
`gst.Controller` and supporting classes. The design documents for pitivi
show a number of mock-ups which include keyframe curves overlaid
directly atop track-objects in the time-line. We will develop this
feature using the `gst.Controller` API to provide the actual
functionality.

## Proof Of Concept Demo

First, we should familiarize ourselves with the `gst.Controller` API.
Let's create an automated of existing `videobalance` demo.

![](Color_balance_pipeline.png "Color_balance_pipeline.png")

    Excerpt 1

The trick now is to control one or more of the `videobalance` element's
properties with a `gst.Controller`. First we create a controller, and
bind it to the element's properties.

    Excerpt 1

Then, we add a series of control points. Since we're trying to test out
this functionality, let's choose a test pattern that will be easy to
detect.

![](interpolator_test_pattern.png "interpolator_test_pattern.png")

The code to add this curve is pretty straightforward:

    We create the

## UI Interaction Demo

This next demo is a prototype keyframe interface.

## Defining the API

## Dummy Back-end Implementation

## Develop and Test the UI

## Making the Back-end Do Something

### Providing Access to Required Elements

## Extending the Project Formatters

## Integrating into the Undo System

## Unsolved Issues

# Still Images

## Proof of Concept Demo

## Initial Implementation

### Changes to Discoverer

### New SourceFactory Type

## Issues with the Freeze Element

## Writing a Python Freeze Element

## Final Implementation
