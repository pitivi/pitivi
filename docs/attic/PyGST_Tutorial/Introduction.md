# Introduction

This series of articles is intended to pick up where others leave off.
The choice of subject matter has an emphasis on video, which PiTiVi
hackers should find particularly relevant.

## Intended Audience

I'm going to assume that the reader is very familiar with python, and
has some basic knowledge about `gst-python`. In particular, Read the
following material before continuing:

-   <http://www.jonobacon.org/?p=750>
-   <http://www.jonobacon.org/?p=851>

These articles are written in a tutorial format. You may also wish to
refer to the official PyGST and GStreamer references. The C
documentation is often more helpful than the PyGST documentation.

-   <http://pygstdocs.berlios.de/>
-   <http://pygstdocs.berlios.de/pygst-tutorial/> (direct link to
    official tutorial)
-   <http://gstreamer.freedesktop.org/data/doc/gstreamer/head/manual/html/index.html>

This article is primarily about GStreamer and gnonlin, so I'm not going
to spend a lot of time about explaining the basics of PyGTK or the
GObject programming model. In particular, you should understand the
GObject concepts of *signals* and *properties*.

## How to Contact

This material is evolving, and I encourage readers to send feedback to.
You can write me at brandon\_lewis AT alum dot berkeley dot edu. I am
also in `#pitivi` channel on IRC.

## Running the Examples

The examples are intended to be run from the command line, and the
meaning of the arguments varies from example to example. Most of the
examples import at least demo.py, so you should save all the all
examples into the same directory. At the moment I cannot upload files
with a .py extension directly into the wiki, so you must manually copy
and paste the example source into a text editor. Apologies for the
inconvenience.

## A Word of Caution

This information is for educational purposes only. It is provided free
of charge, use at your own risk.
