# Hacking on Pitivi

## The pitivi development environment

### Setup pitivi

The official way of getting your environment up and running is by using
[flatpak](http://flatpak.org/)

You first need to [get flatpak](http://flatpak.org/getting.html)
making sure you also install flatpak-builder, which might be provided by an
additional package on some distributions (please tell us if it is the case
for yours so we can make a list here).

Then, create a development environment folder and get the [https://git.gnome.org/browse/pitivi/tree/ Pitivi source code] into it:

$ mkdir pitivi-dev && cd pitivi-dev
$ git clone https://git.gnome.org/browse/pitivi
$ cd pitivi/

Finally you just need to run:

$ source bin/pitivi-env

Run `pitivi` while inside the environment to launch Pitivi. Next you should run the unittests.
After you edit the source code simply run `pitivi` to see how your changes work.

### Update the environment

In the `pitivi-env` you can simply run:

```
ptvenv --update
```

That will actually clean the prefix, update all dependencies from their
git repos and tarballs as defined in the flatpak manifest (located
in build/flatpak/pitivi.template.json)

### Work on some pitivi dependencies in the development environment

If you have to work on say, [GStreamer Editing Service](https://gstreamer.freedesktop.org/modules/gst-editing-services.html)
you can clone it into you `pitivi-dev`:

```
    git clone git://anongit.freedesktop.org/gstreamer/gst-editing-services
```

Then you can just hack on it, run `autogen` to run `./autogen.sh` with the right arguments for the flatpak sandbox,
and run `make install` to install your changes inside the sandbox (your changes won’t be taken into accout
without installing).

NOTE: When updating the environment, it will use your
local dependencies repositories instead of remote
repositories, which means you have to update them yourself.
Also beware that it will not take into account not committed
changes.

# Coding Style Guide

- We rely on the Python Style Guide PEP-8
	(http://www.python.org/doc/peps/pep-0008/)

  The only exception to it is regarding the "80 columns" rule.
  Since Python is a very concise/compact language, we can afford to be
  a little bit more flexible on the line length than languages such as C.

  When deciding whether or not you should split your line when it exceeds
  79 characters, ask yourself: "does it truly improve legibility?"

  What this translates to is:
    - Try to respect the "80 columns/chars" rule of PEP8 when reasonable,
      that is when the line is really too long.

    - When the contents can fit within the 80 chars,
      or when it only "slightly" exceeds that limit, keep it on one line.
      Otherwise, it just hurts legibility and gives a weird "shape" to the code.

      As you can see, it depends on the context
      and what you think makes the most easily readable code.


  For translatable multiline strings, use Python's implicit line continuation
  instead of manually concatenating with the plus (+) sign. For example, this
  is incorrect, gettext will consider it as two separate strings:
        _("<b>First line</b>\n" +
          "Some second line that is too long to fit on the first line anyway"

  Instead, this is the translator-friendly version:
        _("<b>First line</b>\n"
          "Some second line that is too long to fit on the first line anyway"

- for method names we use the small_caps_with_underscore style
  Ex :

``` lang=python
  class MyClass:

     def a_really_important_method(self):
         self.do_something()
```

- for callbacks, the name of the methods used should:
  - follow same conventions as normal method names
  - be prepended with two underscores since it's private
  - be appended with Cb
  Ex :

``` lang=python
  class MyClass:

     def some_method(self):
         self.someobject.connect('event', self.__some_object_event_cb)

     def __some_object_event_cb(self, object, arg):
         print "our callback was called"
```

- for function names, we use the small_caps_with_underscore style.
  This enables clear separation between functions and methods.

- for other class attributes we use the same calling convention as
  for functions:
  Ex :

``` lang=python
    @property
    def water_level(self):
        """ The level of the water in meters"""
        return self.__water_level
```

- unused arguments in method should be prefixed by 'unused_'.
  The most common place where this would happen is in callbacks from gobject
  signals:
  Ex : (we don't use the second argument, but we do use pad)

``` lang=python
     def _padAddedCb(self, unused_element, pad):
        ...
```

- The following naming should be used for class properties/methods:
  * public : <name>
  * protected : _<name>
  * private : __<name>

- Imported modules should be done in this order:
  * system modules
  * top-level pitivi modules (ex : pitivi.project)
  * modules in the same directory
