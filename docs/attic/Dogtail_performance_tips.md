# Dogtail performance tips

Here are some tips and tricks to make Dogtail test scripts that go as
fast as possible. Feel free to expand and improve this page with your
findings.

While we already set the delays variables to be much faster than the
defaults, Dogtail can still be slow when you need to “search” through a
lot of widgets. Generally speaking, here are some principles:

-   Avoid recursive toplevel searches. If you know the widget you're
    looking for is directly inside the mainwindow, use recursive=False.
-   Confine searches to specific dialogs or widgets
-   Use attributes (ex: “.button”) to avoid searches
-   If you're going to use a widget more than once, keep a reference to
    it by storing it in a variable.

This yields some highly visible performance improvements. It can be the
difference between 80 seconds and 55 seconds for a test.

Some easy tips that will help you for the items above:

1.  Look at the variables provided in the setUp method of test\_base.py.
    Those are available for every test and allow you to get the widgets
    (or subwidgets) you need much faster.
2.  Use helper\_functions.py to access common operations (such as
    opening the file chooser/importing files). These have been optimized
    to be faster.

[Category:Developer
documentation](Category:Developer_documentation.md)
