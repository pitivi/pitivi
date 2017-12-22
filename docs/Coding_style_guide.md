---
short-description: Writing code that looks consistent
...

# Coding Style Guide

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

## Names
The function names, method names and other class attributes should be
small_caps_with_underscore. For example:
``` python
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
``` python
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

``` python
     def __pad_added_cb(self, unused_element, pad):
        self.do_something_with(pad)
```

The name of a callback method should:

  - be prepended with two underscores since it's private
  - be appended with `cb`

``` python
  class MyClass:

     def some_method(self):
         self.someobject.connect('event', self.__some_object_event_cb)

     def __some_object_event_cb(self, object, arg):
         print "our callback was called"
```

## Imports order
You can guess the order of the imported modules by looking at some py files.
The pre-commit hook has authority in this case as it will reorder the imports
if the order is not good.
