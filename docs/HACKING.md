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
(ptv-flatpak) $ make check
```

After you hack the source code simply run `pitivi` again to see how your changes work.

### Development Workflow

We use [Phabricator tasks](https://phabricator.freedesktop.org/tag/pitivi/) to track all bugs and feature requests; feel free to open a task if you have found a bug or
wish to see a feature implemented if it doesn't exist already.
You can even subscribe to tasks on Phabricator to keep yourself updated with their progress.
If you're a newcomer wanting to contribute, you can start with tasks tagged [Pitivi tasks for newcomers](https://phabricator.freedesktop.org/tag/pitivi_tasks_for_newcomers/) to get involved.

To fix a task, it's best to get in touch with us on our IRC channel `#pitivi` on Freenode, to see if it's still meaningful, then if all is well:

1. Assign the task to yourself in Phabricator.
2. Create a new branch with a meaningful name. Make sure to set its [remote-tracking branch](https://git-scm.com/book/en/v2/Git-Branching-Remote-Branches/), as it determines the default commit range to attach.
For example, if you're going to work on task [T7674](https://phabricator.freedesktop.org/T7674/), the branch could be called T7674-import-img or
T7674-fix-import, i.e. `git checkout -b T7674-import-img origin/master`.
3. Once you have made your changes, you need to create a commit. Follow the [GNOME guidelines](https://wiki.gnome.org/Newcomers/CodeContributionWorkflow#Commit_guidelines)
for creating commits.

    Be aware that when you create a commit, `pre-commit` is executed to perform checks on the changes and in some cases it does
some automatic fixes. When this happens, make sure those are included in the commit you want to create.
4. Now you're all set to push your first diff!

    ```
    $ git-phab attach --task TXXXX
    ```

Optionally, you can set git-phab to automatically push your WIP branches to a personal remote repository:

1. Add your cloned remote Pitivi repository as a remote to your local repository:

    ```
    $ git remote add github https://github.com/NICK/pitivi.git
    $ git remote set-url github https://github.com/NICK/pitivi.git
    $ git remote set-url --push github git@github.com:NICK/pitivi.git
    $ git remote show github | grep URL
      Fetch URL: https://github.com/NICK/pitivi.git
      Push  URL: git@github.com:NICK/pitivi.git
    ```
2. Set git-phab remote to your cloned remote Pitivi repository:

    ```
    $ git config phab.remote github
    ```

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

### Imports order
You can guess the order of the imported modules by looking at some py files.
The pre-commit hook has authority in this case as it will reorder the imports
if the order is not good.
