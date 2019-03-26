# Bug reporting

Welcome, testers!

To report a bug/problem in the software, or request a new
feature/enhancement, [create a
task](https://gitlab.gnome.org/GNOME/pitivi/issues/new?issue%5Bassignee_id%5D=&issue%5Bmilestone_id%5D=)
and set Projects: Pitivi.

Bug reporting and feature requests are managed with GNOME's
[GitLab](https://gitlab.gnome.org/). You need to create
an account to file tasks and comment on them. Take a look at the
[existing list of bugs/feature
requests](https://gitlab.gnome.org/GNOME/pitivi/issues) to see if
your problem has already been reported.

# Providing debugging information

## Sharing sample files, projects, and “scenarios”

In some cases we might ask you to share **sample media files** with us
to debug a particular issue. If you don't have your own hosting space,
we have a FTP account with unlimited space available for this purpose,
provided by [idmark.ca](http://idmark.ca).

1.  Using a FTP client (such as FileZilla, available on most Linux
    distributions), connect to “idmark.ca” using the username
    “pitivisamples@idmark.ca” (@idmark.ca is part of the username). Ask
    [us](The_people.md) for the password on IRC.
2.  Please follow our simple naming convention and put your files in a
    folder called with the ID of the bug report (eg. T3553) so we can
    find it easily.
3.  Your uploaded files will be in a private staging folder (only
    visible through FTP); once reviewed, we may move your uploaded files
    to <http://pitivi.ecchi.ca/user-contributed-samples/> for ease of
    access.

You can also share in a similar way a **project archive** containing the
project and all the media is uses:

1.  Use the “Select unused clips” feature to easily remove unused media
    from your project, this will help you save space (and upload time).
2.  Click the menu button top-right and choose the “Export project as
    tarball...” menu item. Save the .xges\_tar file somewhere. It will
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

## Stack traces for crashes

When reporting a **crash** or when the application freezed **deadlock**,
it would be good to provide a **stack trace**.

### When running with Flatpak

1. Make sure you have the GNOME Sdk and Debug symbols installed:

```
GNOME_REPO=$(flatpak info org.gnome.Platform//3.32 | grep Origin | awk '{ print $2 }')
for i in $(flatpak list | grep org.pitivi.Pitivi/ | awk '{ print $1 }'); do
  flatpak install --user $GNOME_REPO $(flatpak info $i |grep Runtime |awk '{ print $2 }' |sed s/Platform/Sdk/)
  flatpak update --user $(flatpak info $i |grep Runtime |awk '{ print $2 }' |sed s/Platform/Sdk/)
  flatpak install --user $GNOME_REPO $(flatpak info $i |grep Runtime |awk '{ print $2 }' |sed s/Platform/Sdk.Debug/)
  flatpak update --user $(flatpak info $i |grep Runtime |awk '{ print $2 }' |sed s/Platform/Sdk.Debug/)
done
```

2. Start a shell in the Pitivi bundle environment.

```
flatpak run -d --command=bash org.pitivi.Pitivi
```
In the development environment, you do this by running `ptvenv` instead.

3. Start Pitivi inside gdb

```
gdb python3 -ex 'run /app/bin/pitivi'
```

When Pitivi crashes, run `bt full` to get the backtrace. When Pitivi
freezes, press Ctrl+Z and run `thread apply all bt` to get the
backtraces for all the threads.

### When running from the packages of your Linux distro

See GNOME's [Getting
Traces](https://wiki.gnome.org/Community/GettingInTouch/Bugzilla/GettingTraces)
instructions for some comprehensive documentation and tips on the
subject.

For those of you who already know how to install the relevant debug
packages etc, we provide you with some simple reminders below of
commands that can be particularly useful in Pitivi's context.

When you want to “attach” to an existing Python process (useful for
deadlocks, where the application will be hung instead of crashed):

```
gdb python3 THE_PITIVI_PROCESS_NUMBER
```

When you want to run Pitivi entirely in gdb from the start:

```
gdb python3 $(which pitivi)
set pagination 0  # avoids the need to press Enter to “scroll”
run
```

When Pitivi crashes, run `bt full` to get the backtrace. When Pitivi
freezes, press Ctrl+Z and run `thread apply all bt` to get the
backtraces for all the threads.

## Debug logs

When you need to know what’s going on inside pitivi, you can launch it
with a debug level. In
[loggable.py](https://git.gnome.org/browse/pitivi/tree/pitivi/utils/loggable.py#n50),
there are five levels: ( <span style="color:red;">ERROR</span>,
<span style="color:yellow; background-color:gray;">WARN</span>,
<span style="color:magenta;">FIXME</span>,
<span style="color:green;">INFO</span>,
<span style="color:blue;">DEBUG</span>,
<span style="color:cyan;">LOG</span> ) = range(1, 7). As such, if you
want to see errors and warnings only, you launch

```
PITIVI_DEBUG=2 bin/pitivi
```

...and if you want to see everything you do

```
PITIVI_DEBUG=6 bin/pitivi
```

If that's “too much” and you want to focus on particular parts of the
code, you can do so. For example, you can get output from the `Timeline`
and `MediaLibraryWidget` classes only:

```
PITIVI_DEBUG=timeline:6,medialibrarywidget:6 bin/pitivi
```

Here are various examples of commands you can use to generate detailed
debug logs that include not only Pitivi's debug output, but also
GStreamer's:

A basic log can be obtained by running:

```
PITIVI_DEBUG=*:5 GST_DEBUG=2 bin/pitivi > debug.log 2>&1
```

To get debugging information from Non-Linear Engine, you could use:

```
PITIVI_DEBUG=5 GST_DEBUG=3,nle*:5,python:5 bin/pitivi > debug.log 2>&1
```

The information most likely to be useful would probably be the debug
info from [GES](GES.md) in addition to Pitivi's:

```
PITIVI_DEBUG=5 GST_DEBUG=ges:5 bin/pitivi > debug.log 2>&1;
```

Some additional tips:

-   When using GST\_DEBUG, the resulting logs will most likely be too
    big to be attached to a bug report directly. Instead, compress them
    (in gzip, bzip2 or lzma format) before attaching them to a bug
    report.

# Python performance profiling

In the rare cases where a performance problem is caused by our UI code,
you can profile Pitivi itself, with this command (and yes,
`JUMP_THROUGH_HOOPS` is needed for this case, it is an environment
variable of
[bin/pitivi](https://git.gnome.org/browse/pitivi/tree/bin/pitivi.in):

```
JUMP_THROUGH_HOOPS=1 python3 -m cProfile -s time -o pitivi_performance.profile bin/pitivi
```

The resulting `pitivi_performance.profile` file can then be processed
to create a visual representation of where the most time was spent and
which functions were called the most often in the code. See also [Jeff's
blog posts on profiling](http://jeff.ecchi.ca/blog/tag/profiling/).
