# Hacking on Pitivi

## The Pitivi development environment

### Setup Pitivi

The official way of getting your environment up and running is by using
[flatpak](http://flatpak.org/).

You first need to [get flatpak](http://flatpak.org/getting.html)
making sure you also install flatpak-builder, which might be provided by an
additional package on some distributions (please tell us if it is the case
for yours so we can make a list here).

Create a development environment folder and get the [Pitivi source code](https://git.gnome.org/browse/pitivi/tree/) into it:
```
$ mkdir pitivi-dev && cd pitivi-dev
$ git clone https://git.gnome.org/browse/pitivi
$ cd pitivi/
```

Finally to enter the dev env you just need to run:
```
$ source bin/pitivi-env
```

Run `pitivi` while inside the environment to launch Pitivi. Next you should run the unittests.
```
(ptv-flatpak) $ pitivi
(ptv-flatpak) $ nosetests tests/test_*.py
```

After you hack the source code simply run `pitivi` again to see how your changes work.

### Update the environment

To update the dependencies installed in the dev env run:
```
(ptv-flatpak) $ ptvenv --update
```

That will actually clean the prefix, update all dependencies from their
git repos and tarballs as defined in the [flatpak manifest](https://git.gnome.org/browse/pitivi/tree/build/flatpak/pitivi.template.json) (located
at build/flatpak/pitivi.template.json)

### Work on some Pitivi dependencies in the development environment

If you have to work on say, [GStreamer Editing Services](https://gstreamer.freedesktop.org/modules/gst-editing-services.html)
you can clone it into your `pitivi-dev` folder:
```
(ptv-flatpak) $ git clone git://anongit.freedesktop.org/gstreamer/gst-editing-services
```

Install it in the sandbox by running in the dev env:
```
(ptv-flatpak) $ autogen
(ptv-flatpak) $ make install
```

`autogen` is an alias which runs `./autogen.sh` with the right arguments
for the flatpak sandbox.
`make` is also an alias which runs the real `make` inside the sandbox,
thus `make install` will install your changes in the sandbox.

NOTE: When updating the environment, it will use your
local dependencies repositories instead of remote
repositories, which means you have to update them yourself.
Also beware that it will not take into account not committed
changes.

## Coding Style Guide

We rely on the [Python Style Guide PEP-8](https://www.python.org/dev/peps/pep-0008/)

The only exception to it is regarding the "80 columns" rule.
Since Python is a very concise/compact language, we can afford to be
a little bit more flexible on the line length than languages such as C.

When deciding whether or not you should split your line when it exceeds
79 characters, ask yourself: "Does it truly improve legibility?"

What this translates to is:

- Avoid having very long lines.

- When the contents only slightly exceeds the 80 chars limit,
consider keeping it on one line. Otherwise it just hurts legibility and
gives a weird "shape" to the code.

### Names
The function names, method names and other class attributes should be
small_caps_with_underscore. For example:
``` lang=python
def some_function():
    return ""

class MyClass:

    def a_really_important_method(self):
        self.do_something()

    @property
    def water_level(self):
        """The level of the water in meters."""
        return self.__water_level
```

To illustrate how private a method or other class field is, prepend
one or two underscores:
``` lang=python
  class MyClass:

     def public_method(self):
         ...

     def _protected_method(self):
         ...

     def __private_method(self):
         ...
```

Unused arguments in methods should be prefixed with `unused_`.
The most common place where this would happen is in callbacks from
gobject signals. For example, below we don't use the second argument,
but we do use `pad`.

``` lang=python
     def __pad_added_cb(self, unused_element, pad):
        self.do_something_with(pad)
```

The name of a callback method should:

  - be prepended with two underscores since it's private
  - be appended with `cb`

``` lang=python
  class MyClass:

     def some_method(self):
         self.someobject.connect('event', self.__some_object_event_cb)

     def __some_object_event_cb(self, object, arg):
         print "our callback was called"
```

### Imports order
You can guess the order of the imported modules by looking at some py files.
The pre-commit hook has authority in this case as it will reorder the imports
if the order is not good.
