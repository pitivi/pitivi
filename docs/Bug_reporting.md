# Bug reporting

Welcome, testers!

Bug reporting and feature requests are managed with GNOME's
[GitLab](https://gitlab.gnome.org/). You need to create
an account to file issues and comment on them. Take a quick look at the
[existing list of bugs and feature
requests](https://gitlab.gnome.org/GNOME/pitivi/issues) to see if
your problem has already been reported.

To report a bug/problem in the software, [create an
issue](https://gitlab.gnome.org/GNOME/pitivi/-/issues/).
Ideally you can describe exactly the steps *anyone* can follow to
reproduce the bug. The more details, the better.

# Providing debugging information

## Sharing sample files, projects, and “scenarios”

To be able to reproduce an issue, we might ask you to share **sample
media files** with us. If the file is too large to attach to the GitLab
issue, you can use for example [Dropbox](https://www.dropbox.com/),
[Google Drive](https://drive.google.com/), [MEGA](https://mega.nz/) or
other service to share such media.

You can also share in a similar way a **project archive** containing the
project and all the media is uses:

1.  Use the “Select unused clips” feature to easily remove unused media
    from your project, this will help you save space (and upload time).
2.  Click the menu button top-right and choose the “Export project as
    tarball...” menu item. Save the `.xges_tar` file somewhere. It will
    contain your project file and its associated media.
3.  Upload it as described above.

In addition to the project archive, it is extremely helpful to provide
**“scenario” files**. These are automatically generated each time you
use a project and contain the operations you made. Combined with the
project archive, these allow us to perform exactly the actions that have
occurred to trigger the bug. This makes reproducing the issue on our
machines a very easy and reliable process, which saves you a ton of
time! Here's **how to provide scenario files to facilitate the
process:**

1.  Save your project, right before triggering the bug.
2.  Trigger the bug (make Pitivi crash or freeze).
3.  Get the last/newest scenario file from `~/.cache/pitivi/scenarios/`
    or `~/.var/app/org.pitivi.Pitivi/cache/pitivi/scenarios/`
4.  Upload it as described above, so we can reproduce your issue and
    integrate it into our test suite so that it does not happen again in
    the future!


## Back traces for crashes and deadlocks

When reporting a **crash** (application window disappears) or a
**deadlock** (application is frozen), we can't do much without a
**back trace**.

First try to see if you can locate a coredump file created by your
system automatically when a **crash** takes place. For example:

```
$ coredumpctl list | tail
Wed 2019-08-28 23:02:20 CEST  31783  1000   100  11 present   /usr/bin/python3.7
$ coredumpctl info 31783
           PID: 31783 (python3)
       Storage: /var/lib/systemd/coredump/core.python3.1000.e907bb24f9c14aafb3ec0c900ee5bc4a.31783.1567026134000000.lz4
$ lz4 -d /var/lib/systemd/coredump/core.python3.1000.e907bb24f9c14aafb3ec0c900ee5bc4a.31783.1567026134000000.lz4 ~/coredump
```

A coredump can be investigated using gdb. Look below for the proper way
to start gdb, but at the end instead of `gdb python3 -ex ...` simply run
`gdb python3 ~/coredump`.

Alternatively, if you are missing a coredump, start Pitivi in gdb as
described below, then try to reproduce the crash.

Finally, in gdb run `bt full` to get the back trace for the crash.

> Tip: To avoid the need to press Enter to “scroll” in gdb,
> run `set pagination 0`.

For a **deadlock**, start Pitivi in gdb as described below, press Ctrl+Z
and run `thread apply all bt` to get the backtraces for all the threads.

### When running in the development environment

1. Install the GNOME SDK Debug symbols and update them, see below.

2. Enter the sandbox:

```
ptvenv
```

3. Start Pitivi inside gdb:

```
gdb python3 -ex "run $PITIVI_REPO_DIR/bin/pitivi"
```

### When running with Flatpak

1. Install the GNOME SDK and its Debug symbols and update them:

```
flatpak --user install flathub org.gnome.Sdk/x86_64/47
flatpak --user install flathub org.gnome.Sdk.Debug/x86_64/47
flatpak --user update          org.gnome.Sdk/x86_64/47
flatpak --user update          org.gnome.Sdk.Debug/x86_64/47
```

2. Start a shell in the Pitivi flatpak sandbox:

```
flatpak run -d --command=bash org.pitivi.Pitivi
```

3. Start Pitivi inside gdb:

```
gdb python3 -ex "run /app/bin/pitivi"
```

### When running from the packages of your Linux distro

GNOME's [Getting Stack Traces] has excellent documentation and tips
on the subject, including how to install the relevant debug
packages. Below is a quick reminder for those already familiar with
the process.

When you want to “attach” to an existing Python process (useful for
deadlocks, where the application will be hung instead of crashed):

```
gdb python3 THE_PITIVI_PROCESS_NUMBER
```

When you want to run Pitivi entirely in gdb from the start:

```
gdb python3 -ex "run $(which pitivi)"
```


## Debug logs

When you need to know what’s going on inside Pitivi, you can launch it
with a debug level. In
[loggable.py](https://gitlab.gnome.org/GNOME/pitivi/blob/master/pitivi/utils/loggable.py#L61),
there are six levels: ( <span style="color:red;">ERROR</span>,
<span style="color:yellow; background-color:gray;">WARN</span>,
<span style="color:magenta;">FIXME</span>,
<span style="color:green;">INFO</span>,
<span style="color:blue;">DEBUG</span>,
<span style="color:cyan;">LOG</span> ) = range(1, 7). As such, if you
want to see errors and warnings only, you launch

```
PITIVI_DEBUG=2 pitivi
```

...and if you want to see everything you do

```
PITIVI_DEBUG=6 pitivi
```

If that's “too much” and you want to focus on particular parts of the
code, you can do so. For example, you can get output from the `Timeline`
and `MediaLibraryWidget` classes only:

```
PITIVI_DEBUG=timeline:6,medialibrarywidget:6 pitivi
```

Here are various examples of commands you can use to generate detailed
debug logs that include not only Pitivi's debug output, but also
GStreamer's:

A basic log can be obtained by running:

```
PITIVI_DEBUG=*:5 GST_DEBUG=2 pitivi > debug.log 2>&1
```

To get debugging information from Non-Linear Engine, you could use:

```
PITIVI_DEBUG=5 GST_DEBUG=3,nle*:5,python:5 pitivi > debug.log 2>&1
```

The information most likely to be useful would probably be the debug
info from [GES](GES.md) in addition to Pitivi's:

```
PITIVI_DEBUG=5 GST_DEBUG=ges:5 pitivi > debug.log 2>&1;
```


> When using GST\_DEBUG, the resulting logs will most likely be too
> big to be attached to a bug report directly. Instead, compress them
> (in gzip, bzip2 or lzma format) before attaching them to a bug report.


# Python performance profiling

In the rare cases where a performance problem is caused by our UI code,
you can profile Pitivi itself, with this command (and yes,
`JUMP_THROUGH_HOOPS` is needed for this case, it is an environment
variable of
[bin/pitivi](https://gitlab.gnome.org/GNOME/pitivi/blob/master/bin/pitivi.in):

```
JUMP_THROUGH_HOOPS=1 python3 -m cProfile -s time -o pitivi_performance.profile bin/pitivi
```

The resulting `pitivi_performance.profile` file can then be processed
to create a visual representation of where the most time was spent and
which functions were called the most often in the code. See also [Jeff's
blog posts on profiling](http://jeff.ecchi.ca/blog/tag/profiling/).

[Getting Stack Traces]: https://wiki.gnome.org/Community/GettingInTouch/Bugzilla/GettingTraces
