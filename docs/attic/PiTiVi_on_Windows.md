# Status

Andoni Morales [sent a post to
gst-devel](http://www.nabble.com/Re:--gst-devel---PiTiVi-running-on-Windows-XP-td23885580.html)
with a screenshot of pitivi 0.13.1 running on windows, which got the
ball rolling. Andoni develops
[LongoMatch](http://www.longomatch.ylatuya.es/) a gstreamer/gnonlin app
that runs on windows, even with an installer!

Andoni also set up [WinBuilds for
Gstreamer](http://www.gstreamer-winbuild.ylatuya.es) which we'll
definitely need. However, no-one's heard from Andoni since, I guess he's
busy working on LongoMatch :)

I gave it a go and got fairly close, but not being a hardcore gstreamer
dev, and with the versions continually moving underneath my feet, I
didn't get it all the way.

-   Summary: Obscure bug in pygstreamer that may or may not be fixed
    with fresh builds of winbuilds and python bindings...

# Dependencies

Starting with PiTiVi 0.13.3, you need the latest version of Gstreamer
for windows you can get. You also need a compatible version of
GST-python, both of these come from
[WinBuilds](http://www.gstreamer-winbuild.ylatuya.es/doku.php?id=download)

As of today, you'll need python 2.5, as we'll see in a minute...

You also need GTK for windows, and pygtk. GTK comes from [gnome win32
binaries](http://ftp.gnome.org/pub/GNOME/binaries/win32/gtk+/) but as
for what version, that's a rabbit hole we need to follow first.

To use PyGtk, we need PyGObject and PyCairo. Fortunately, these all come
from [pygtk.org](http://www.pygtk.org/downloads.html) The latest version
of PyGtk is 2.12 at the time of writing, so that dicatates what bundle
of GTK we download. The matching version of PyGObject only has a Python
2.5 installer, which is where our python 2.5 requirement comes from.

For PyCairo, I just picked the latest version with a python 2.5
installer, but I didn't get far enough to verify that.

You'll also need libglade, which is not part of GTK. You can get it from
[gnome win32
binaries](http://ftp.gnome.org/pub/GNOME/binaries/win32/libglade/) I
just installed the latest.

## Installation

The Py\* packages have installers which “do the right thing” for your
python intallation. GTK is simply a bundle of dlls, which need to be
added to your path. From System Properties (winkey-break or right click
“my computer” and choose properties") click on Advanced, then
Environment Variables at the bottom. You need to add the path to the
extract gtk bin directory to the PATH variable, for either the system or
the user, doesn't matter.

libglade just has a single dll that needs to be in the path as well. I
found that easiest by just dropping it into the GTK bin directory.

## Verifying the setup

### PyGst and GST

To test that gst and pygst are installed correctly, importing them
shouldn't give any errors...

    Python 2.5.4 (r254:67916, Dec 23 2008, 15:10:54) [MSC v.1310 32 bit (Intel)] on
    win32
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import pygst
    >>> pygst.require("0.10")
    >>> import gst
    >>>

### PyGtk and GTK and glade

Just like for gst, importing this should work too....

    Python 2.5.4 (r254:67916, Dec 23 2008, 15:10:54) [MSC v.1310 32 bit (Intel)] on
    win32
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import pygtk
    >>> pygtk.require("2.0")
    >>> import gtk
    C:\python25\lib\site-packages\gtk-2.0\gtk\__init__.py:69: Warning: Passing a non
    -NULL package to g_win32_get_package_installation_directory() is deprecated and
    it is ignored.
      _gtk.init_check()
    >>> from gtk import glade
    >>>

The warning seeeems to be harmless....

# PiTiVi itself!

PiTiVi uses autotools to generate a few things, mostly detecting the
libraries and setting up translations. I didn't have autotools, and
didn't feel like installing them. You can edit bin/pitivi.in to manually
fix the paths, and if you're happy running without i18n, you can skip
building the translation files too.

I wasn't clever enough to fix the paths though.... :(

    C:\junk\pitivi-0.13.3>\python25\python bin\pitivi.py
    Couldn't set locale !, reverting to C locale
    C:\python25\lib\site-packages\gtk-2.0\gtk\__init__.py:69: Warning: Passing a non
    -NULL package to g_win32_get_package_installation_directory() is deprecated and
    it is ignored.
      _gtk.init_check()
    Couldn't set locale !, reverting to C locale
    Traceback (most recent call last):
      File "bin\pitivi.py", line 118, in <module>
        _run_pitivi()
      File "bin\pitivi.py", line 111, in _run_pitivi
        import pitivi.application as ptv
      File "C:\junk\pitivi-0.13.3\bin\pitivi.py", line 118, in <module>
        _run_pitivi()
      File "C:\junk\pitivi-0.13.3\bin\pitivi.py", line 111, in _run_pitivi
        import pitivi.application as ptv
    ImportError: No module named application

I'm sure someone with an ounce of pythonfoo could fix that, so I
proceeded to do the steps manually, and here we reach the end of the
line, a bizarre bug in gstreamer? `bilboed-pi` suggests that this is
caused by PiTiVi 0.13.3 requiring pygst 0.10.16.x, while the current
winbuilds only provides 0.10.15.1. `laszlok` reported that he gets this
error singledecodebin in python2.5 and pygst is compiled for python2.6
So there's possibly another bug there. Bilboed-pi wants to push Andoni
and co to update winbuilds so we can get 0.10.16.x and we can try again.

    C:\junk\pitivi-0.13.3>\python25\python
    Python 2.5.4 (r254:67916, Dec 23 2008, 15:10:54) [MSC v.1310 32 bit (Intel)] on
    win32
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import pygtk
    >>> pygtk.require("2.0")
    >>> import gtk
    C:\python25\lib\site-packages\gtk-2.0\gtk\__init__.py:69: Warning: Passing a non
    -NULL package to g_win32_get_package_installation_directory() is deprecated and
    it is ignored.
      _gtk.init_check()
    >>> import gobject
    >>> gobject.threads_init()
    >>> gobject.threads_init()
    >>> from gtk import glade
    >>> import pygst
    >>> pygst.require("0.10")
    >>> import gst
    >>> import pitivi.application
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "application.py", line 41, in <module>
      File "pitivi\device.py", line 28, in <module>
        from pitivi.factories.base import ObjectFactory, SourceFactory
      File "pitivi\factories\base.py", line 29, in <module>
        from pitivi.elements.singledecodebin import SingleDecodeBin
      File "pitivi\elements\singledecodebin.py", line 409, in <module>
        gobject.type_register(SingleDecodeBin)
    TypeError: __gsttemplates__ attribute neither a tuple nor a GstPadTemplate!
    >>>
