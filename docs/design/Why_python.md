# Why Python?

We like Python. It is a simple, fast and elegant programming language.
It allows **faster**, **agile** and **robust** software development.
Some people wrongly assume that Python applications are automatically
slow and bloated. This is untrue for many reasons:

-   Python is actually surprisingly fast in many cases.
-   Python is **not the performance bottleneck** here. Seriously.
    **GStreamer and [GES](GES.md) are the components doing the
    heavy work, and they are written in C**. Pitivi is basically just a
    pretty user interface on top of those.
-   Most performance issues on desktop apps are not micro-optimization
    problems, but I/O bound operations or “stupid algorithms/methods
    that do unnecessary work”. Federico Mena Quintero did a great
    presentation
    ([video](http://video.fosdem.org/2007/FOSDEM2007-ProfilingDesktopApplication.ogg),
    [slides](http://people.gnome.org/~federico/docs/2007-02-FOSDEM/html/index.html))
    along those lines a couple of years ago.

Most of what I highlighted above can also be found in Python's page on
[speed](http://wiki.python.org/moin/PythonSpeed) and [performance
tips](http://wiki.python.org/moin/PythonSpeed/PerformanceTips).
